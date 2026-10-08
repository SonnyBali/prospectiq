"""Independent adversarial checks; no cloud credentials or provider requests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import update

from app.advisor import AdvisorResult, safe_answer
from app.config import Settings
from app.db import Prospect
from app.main import create_app
from app.schemas import AdvisorAnswer, Claim, Recommendation, SimulatorInput
from app.simulator import calculate


class ReviewSecrets:
    def get(self, name):
        assert name == "review-admin", "The test must not request a cloud/provider secret"
        return "local-review-key"


class ReviewAdvisor:
    mode = "openai"

    def __init__(self, status="completed", fail=False):
        self.status, self.fail, self.calls = status, fail, 0
        self.lock = Lock()

    def answer(self, prospect, message, history, scenario=None, purpose="chat"):
        with self.lock:
            self.calls += 1
        if self.fail:
            raise RuntimeError("private-provider-response-must-not-leak")
        claims = [Claim(text=prospect.sources[0]["excerpt"], source_ids=[prospect.sources[0]["id"]])]
        if self.status != "completed":
            claims = []
        return AdvisorResult(
            AdvisorAnswer(summary="Independent local test response", claims=claims,
                          recommendations=[], unknowns=[]),
            "openai",
            {"input_tokens": 17, "output_tokens": 9, "cached_input_tokens": 0,
             "estimated_cost_usd": None, "model": "local-review-model", "price_reference": ""},
            self.status,
        )


def application(tmp_path, advisor=None, **overrides):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'review.db'}",
                        admin_secret="review-admin", public_origin="http://testserver", **overrides)
    return create_app(settings, ReviewSecrets(), advisor or ReviewAdvisor())


def demo(client):
    response = client.get("/api/demo")
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_sessions_cannot_read_another_sessions_history_or_engineering(tmp_path):
    app = application(tmp_path)
    with TestClient(app) as client:
        headers = demo(client)
        response = client.post("/api/chat", headers=headers, json={"message": "private-local-conversation-marker"})
        assert response.status_code == 200
        first_request_id = response.json()["request_id"]
        first_cookie = client.cookies.get("prospectiq_session")

        client.cookies.clear()
        assert client.get("/api/history").status_code == 401
        assert client.get("/api/engineering").status_code == 401
        demo(client)
        assert client.cookies.get("prospectiq_session") != first_cookie
        assert client.get("/api/history").json()["messages"] == []
        engineering = client.get("/api/engineering").json()
        assert first_request_id not in str(engineering)
        assert "private-local-conversation-marker" not in str(engineering)
        assert "local-review-key" not in str(engineering)
        assert "csrf_token" not in engineering


def test_mutations_require_csrf_and_reject_foreign_origins(tmp_path):
    with TestClient(application(tmp_path)) as client:
        headers = demo(client)
        for route, body in (("/api/chat", {"message": "hello"}),
                            ("/api/simulate", {}),
                            ("/api/follow-up", {"intent": "Review synthetic scenario"})):
            assert client.post(route, json=body).status_code == 403
            assert client.post(route, headers={"X-CSRF-Token": "wrong"}, json=body).status_code == 403
            assert client.post(route, headers={**headers, "Origin": "https://foreign.example"}, json=body).status_code == 403
        assert client.delete("/api/session").status_code == 403
        assert client.post("/api/simulate", headers=headers, json={}).status_code == 200
        assert client.delete("/api/session", headers=headers).status_code == 200
        assert client.get("/api/history").status_code == 401


def imported_prospect():
    return {
        "first_name": "Synthetic", "company_name": "Independent fictional company",
        "industry": "Synthetic services", "website": "https://example.com/review",
        "synthetic": True,
        "sources": [{"id": "review_source", "title": "Synthetic process fixture",
                     "url": "https://example.com/review", "excerpt": "This fictional company uses a staff callback for inquiries.",
                     "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True}],
    }


def test_link_revocation_invalidates_existing_authenticated_session(tmp_path):
    with TestClient(application(tmp_path)) as client:
        imported = client.post("/api/admin/prospects/import", headers={"X-Admin-Key": "local-review-key"},
                               json=imported_prospect())
        assert imported.status_code == 200
        data = imported.json()
        token = data["dashboard_url"].split("#", 1)[1]
        dashboard = client.post("/api/access", json={"token": token})
        assert dashboard.status_code == 200
        csrf = {"X-CSRF-Token": dashboard.json()["csrf_token"]}
        assert client.get("/api/history").status_code == 200
        assert client.delete(f"/api/admin/prospects/{data['prospect_id']}/access",
                             headers={"X-Admin-Key": "local-review-key"}).status_code == 200
        assert client.get("/api/history").status_code == 401
        assert client.get("/api/engineering").status_code == 401
        assert client.post("/api/chat", headers=csrf, json={"message": "Should be blocked"}).status_code == 401


def test_refused_intelligence_never_mints_access(tmp_path):
    with TestClient(application(tmp_path, ReviewAdvisor(status="refused_or_incomplete"))) as client:
        response = client.post("/api/admin/prospects/import", headers={"X-Admin-Key": "local-review-key"},
                               json=imported_prospect())
        assert response.status_code == 502
        assert "dashboard_url" not in response.json()
        assert "no access link" in response.json()["detail"].lower()


def test_fast_worker_progress_is_not_overwritten_or_misreported(tmp_path, monkeypatch):
    app = application(tmp_path, allow_cloud_tasks=True)

    class ImmediateLocalQueue:
        def __init__(self, *args):
            pass

        def enqueue(self, prospect_id):
            # Reproduce the worker advancing before the enqueue HTTP request returns.
            with app.state.db() as db:
                db.execute(update(Prospect).where(Prospect.id == prospect_id).values(research_status="researching"))
                db.commit()
            return "local-review-task"

    monkeypatch.setattr("app.main.CloudResearchQueue", ImmediateLocalQueue)
    with TestClient(app) as client:
        with app.state.db() as db:
            db.add(Prospect(id="local-review-pending", synthetic=False,
                            profile={"first_name": "Fictional", "company_name": "Fictional queue test",
                                     "industry": "Synthetic fixture", "website": "https://example.com"},
                            research_status="pending"))
            db.commit()
        response = client.post("/api/admin/prospects/local-review-pending/research",
                               headers={"X-Admin-Key": "local-review-key"})
        assert response.status_code == 200
        assert response.json()["status"] == "researching"
        with app.state.db() as db:
            assert db.get(Prospect, "local-review-pending").research_status == "researching"


def test_parallel_requests_cannot_overrun_session_quota(tmp_path):
    advisor = ReviewAdvisor()
    with TestClient(application(tmp_path, advisor, demo_ai_budget=1)) as client:
        headers = demo(client)
        with ThreadPoolExecutor(max_workers=5) as executor:
            statuses = list(executor.map(lambda _: client.post("/api/chat", headers=headers,
                                                               json={"message": "Concurrent request"}).status_code,
                                         range(5)))
        assert statuses.count(200) == 1
        assert statuses.count(429) == 4
        assert advisor.calls == 1


def test_shared_quota_survives_new_browser_session(tmp_path):
    advisor = ReviewAdvisor()
    with TestClient(application(tmp_path, advisor, max_global_ai_calls_per_hour=1)) as client:
        headers = demo(client)
        assert client.post("/api/chat", headers=headers, json={"message": "First session"}).status_code == 200
        client.cookies.clear()
        headers = demo(client)
        assert client.post("/api/chat", headers=headers, json={"message": "New session"}).status_code == 429
        assert advisor.calls == 1


def test_provider_error_is_generic_and_still_consumes_attempt_quota(tmp_path, caplog):
    advisor = ReviewAdvisor(fail=True)
    with TestClient(application(tmp_path, advisor, demo_ai_budget=1)) as client:
        headers = demo(client)
        response = client.post("/api/chat", headers=headers, json={"message": "Fail safely"})
        assert response.status_code == 502
        assert "private-provider-response-must-not-leak" not in response.text
        assert "private-provider-response-must-not-leak" not in caplog.text
        assert client.post("/api/chat", headers=headers, json={"message": "Retry"}).status_code == 429
        assert advisor.calls == 1


def test_model_rationale_cannot_alter_numeric_explanations():
    source = {"id": "facts", "excerpt": "This fictional company uses a staff callback for inquiries."}
    scenario = calculate(SimulatorInput())
    answer = AdvisorAnswer(summary="Guaranteed losses of a billion dollars", claims=[], unknowns=[],
                           recommendations=[Recommendation(title="Revenue scenario review",
                               rationale="Hypothesis: double the revenue to one million dollars. Annual revenue is {{monthly_net}}.",
                               source_ids=["facts"])])
    checked = safe_answer(answer, [source], "Fictional company", scenario)
    text = checked.recommendations[0].rationale
    assert "one million" not in text
    assert "double" not in text
    assert "Annual revenue is" not in text
    assert f"${scenario['results']['monthly_revenue']:,.2f}" in text
    assert f"${scenario['results']['monthly_net']:,.2f}" in text
    assert "billion" not in checked.summary


@pytest.mark.parametrize("unsupported", ["offer emergency repairs.", "", "   "])
def test_extracted_claim_cannot_discard_negation_or_be_empty(unsupported):
    source = {"id": "facts", "excerpt": "The company does not offer emergency repairs."}
    answer = AdvisorAnswer(summary="", claims=[Claim(text=unsupported, source_ids=["facts"])],
                           recommendations=[], unknowns=[])
    assert safe_answer(answer, [source], "Fictional company").claims == []


@pytest.mark.parametrize("field", ["monthly_cost", "average_sale"])
def test_currency_divisors_cannot_accept_extreme_subcent_values(tmp_path, field):
    with TestClient(application(tmp_path)) as client:
        headers = demo(client)
        response = client.post("/api/simulate", headers=headers, json={field: 1e-40})
        assert response.status_code == 422


def test_cloud_run_cannot_start_with_ephemeral_sqlite(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "local-review-only")
    with pytest.raises(ValueError, match="Cloud SQL"):
        Settings(public_origin="https://portfolio.example", secure_cookies=True).validate()


def test_live_voice_requires_explicit_isolation():
    with pytest.raises(ValueError, match="isolated"):
        Settings(voice_widget_id="not-a-production-widget").validate()
    with pytest.raises(ValueError, match="isolated"):
        Settings(voice_phone="synthetic-placeholder").validate()


@pytest.mark.parametrize("rate", ["not-a-number", "NaN", "Infinity", "-0.1"])
def test_invalid_prices_fail_before_provider_requests(rate):
    with pytest.raises(ValueError, match="finite nonnegative"):
        Settings(openai_input_rate=rate, openai_cached_rate="0", openai_output_rate="0",
                 price_reference="Local test pricing reference").validate()


def test_partial_price_configuration_is_rejected():
    with pytest.raises(ValueError, match="all model rates"):
        Settings(openai_input_rate="0.1").validate()
