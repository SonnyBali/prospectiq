"""An extra demo origin grants no additional access to private prospect sessions."""
from dataclasses import replace
from datetime import timedelta
import secrets

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.config import Settings
from app.db import AccessLink, BrowserSession, Prospect, now
from app.demo import DEMO_ID
from app.main import create_app, digest

CANONICAL = "https://prospect.firewireads.com"
DEMO = "https://prospectiq-s4gztnjt6a-uc.a.run.app"


def demo_application(settings):
    return create_app(replace(settings, public_origin=CANONICAL, demo_origin=DEMO, secure_cookies=True))


def synthetic_session(client):
    response = client.get("/api/demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["prospect"]["id"] == DEMO_ID and payload["prospect"]["synthetic"] is True
    return {"X-CSRF-Token": payload["csrf_token"], "Origin": DEMO}


def test_extra_origin_public_fixture_simulator_chat_and_logout_work(settings):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        headers = synthetic_session(client)
        simulation = client.post("/api/simulate", headers=headers, json={"monthly_leads": 400})
        assert simulation.status_code == 200
        assert simulation.json()["results"]["monthly_revenue"] == 10800
        chat = client.post("/api/chat", headers=headers, json={"message": "Review fictional after-hours calls"})
        assert chat.status_code == 200 and chat.json()["provider"] == "guided_demo"
        assert client.post("/api/simulate", headers={**headers, "Origin": CANONICAL}, json={}).status_code == 200
        assert client.delete("/api/session", headers=headers).status_code == 200
        assert client.get("/api/history").status_code == 401


def test_extra_demo_host_is_not_indexed_and_retains_strict_tracking_policy(settings):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        response = client.get("/")
        assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
        assert f'href="{CANONICAL}/"' in response.text
        directives = {parts[0]: set(parts[1:]) for section in response.headers["content-security-policy"].split(";")
                      if (parts := section.split())}
        assert directives["script-src"] == {"'self'"}
        assert directives["connect-src"] == {"'self'"}
        assert directives["img-src"] == {"'self'", "data:"}
        assert "facebook" not in response.headers["content-security-policy"]
        assert "googletagmanager" not in response.headers["content-security-policy"]
    with TestClient(demo_application(settings), base_url=CANONICAL) as client:
        assert "x-robots-tag" not in client.get("/").headers


@pytest.mark.parametrize("origin", ["https://unknown.example", DEMO + ":443", DEMO + "/", "http://prospectiq-s4gztnjt6a-uc.a.run.app"])
def test_extra_origin_rejects_unconfigured_or_nonexact_origins(settings, origin):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        headers = synthetic_session(client)
        assert client.post("/api/simulate", headers={**headers, "Origin": origin}, json={}).status_code == 403


def test_extra_origin_still_requires_correct_csrf(settings):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        synthetic_session(client)
        assert client.post("/api/simulate", headers={"Origin": DEMO}, json={}).status_code == 403
        assert client.post("/api/simulate", headers={"Origin": DEMO, "X-CSRF-Token": "wrong"}, json={}).status_code == 403


@pytest.mark.parametrize("host", ["unknown.example", "prospect.firewireads.com"])
def test_extra_origin_must_match_actual_request_host(settings, host):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        headers = synthetic_session(client)
        assert client.post("/api/simulate", headers={**headers, "Host": host}, json={}).status_code == 403


@pytest.mark.parametrize("prospect_id,synthetic", [
    ("private-real", False), ("private-synthetic", True), (DEMO_ID, True),
])
def test_capability_sessions_cannot_use_extra_origin_even_with_valid_csrf(settings, prospect_id, synthetic):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        token = secrets.token_urlsafe(32)
        with client.app.state.db() as db:
            if prospect_id != DEMO_ID:
                fixture = db.get(Prospect, DEMO_ID)
                db.add(Prospect(id=prospect_id, profile={**fixture.profile, "company_name": "Private test fixture"},
                                synthetic=synthetic, sources=[{**source, "is_synthetic": synthetic} for source in fixture.sources],
                                intelligence=fixture.intelligence, research_status="complete", research_completed_at=now()))
                db.flush()
            db.add(AccessLink(token_hash=digest(token), prospect_id=prospect_id,
                              expires_at=now() + timedelta(hours=1)))
            db.commit()
        # Canonical exchange is unchanged, even when the request reaches the service URL.
        access = client.post("/api/access", headers={"Origin": CANONICAL}, json={"token": token})
        assert access.status_code == 200
        headers = {"X-CSRF-Token": access.json()["csrf_token"], "Origin": DEMO}
        assert client.post("/api/simulate", headers=headers, json={}).status_code == 403
        assert client.post("/api/simulate", headers={**headers, "Origin": CANONICAL}, json={}).status_code == 200


def test_capability_exchange_remains_canonical_only(settings):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        token = secrets.token_urlsafe(32)
        with client.app.state.db() as db:
            db.add(AccessLink(token_hash=digest(token), prospect_id=DEMO_ID, expires_at=now() + timedelta(hours=1)))
            db.commit()
        assert client.post("/api/access", headers={"Origin": DEMO}, json={"token": token}).status_code == 403
        assert client.post("/api/access", headers={"Origin": CANONICAL}, json={"token": token}).status_code == 200


@pytest.mark.parametrize("change", ["nonsynthetic_fixture", "different_synthetic_prospect"])
def test_extra_origin_requires_both_public_fixture_identity_and_synthetic_flag(settings, change):
    with TestClient(demo_application(settings), base_url=DEMO) as client:
        headers = synthetic_session(client)
        with client.app.state.db() as db:
            fixture = db.get(Prospect, DEMO_ID)
            if change == "nonsynthetic_fixture":
                fixture.synthetic = False
            else:
                another = Prospect(id="other-synthetic", profile=fixture.profile, synthetic=True,
                                   sources=fixture.sources, intelligence=fixture.intelligence,
                                   research_status="complete", research_completed_at=now())
                db.add(another)
                db.flush()
                current = db.scalar(select(BrowserSession).where(
                    BrowserSession.token_hash == digest(client.cookies.get("prospectiq_session"))))
                current.prospect_id = another.id
            db.commit()
        assert client.post("/api/simulate", headers=headers, json={}).status_code == 403


@pytest.mark.parametrize("value", [
    "http://public.example", "https://demo.example/path", "https://demo.example?token=x",
    "https://demo.example#token", "https://user:password@demo.example", "ftp://demo.example", "https://",
])
def test_demo_origin_rejects_invalid_configuration(value):
    with pytest.raises(ValueError):
        Settings(demo_origin=value).validate()


@pytest.mark.parametrize("value", [DEMO, "http://127.0.0.1:8093", "http://localhost:8093", ""])
def test_demo_origin_accepts_https_or_loopback_development(value):
    Settings(demo_origin=value).validate()


def test_demo_origin_loads_from_environment(monkeypatch):
    monkeypatch.setenv("DEMO_ORIGIN", DEMO)
    assert Settings.from_env().demo_origin == DEMO


def test_unconfigured_extra_origin_does_not_grant_an_exception(settings):
    app = create_app(replace(settings, public_origin=CANONICAL, secure_cookies=True))
    with TestClient(app, base_url=DEMO) as client:
        headers = synthetic_session(client)
        assert client.post("/api/simulate", headers=headers, json={}).status_code == 403
