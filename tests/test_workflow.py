from datetime import timedelta
from urllib.parse import urlparse

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import AccessLink, BrowserSession, FollowUp, Prospect, now


def test_demo_simulator_chat_history_and_real_traces(client, csrf):
    demo = client.get("/api/demo").json()
    assert demo["prospect"]["synthetic"] is True
    assert demo["advisor_mode"] == "guided_demo"
    assert all(source["is_synthetic"] for source in demo["sources"])
    result = client.post("/api/simulate", headers=csrf, json=demo["simulator_defaults"])
    assert result.status_code == 200
    assert result.json()["results"]["monthly_revenue"] == 8100
    chat = client.post("/api/chat", headers=csrf, json={"message": "How can we handle after-hours calls?", "scenario": demo["simulator_defaults"]})
    assert chat.status_code == 200
    assert chat.json()["provider"] == "guided_demo"
    assert chat.json()["citations"]
    assert len(client.get("/api/history").json()["messages"]) == 2
    engine = client.get("/api/engineering").json()
    traces = engine["recent_requests"]
    assert any(t["request_id"] == chat.json()["request_id"] and t["status"] == 200 for t in traces)
    assert "after-hours calls?" not in str(engine)
    assert "test-admin-key" not in str(engine)


def test_csrf_and_origin_are_enforced(client, csrf):
    assert client.post("/api/chat", json={"message": "test"}).status_code == 403
    assert client.post("/api/chat", headers={**csrf, "Origin": "https://attacker.example"}, json={"message": "test"}).status_code == 403
    assert client.post("/api/simulate", headers=csrf, json={"missed_rate": 9}).status_code == 422


def test_chat_only_explains_numbers_when_requested_and_keeps_calculation_unchanged(client, csrf):
    defaults = client.get("/api/demo").json()["simulator_defaults"]
    for question, explain in [("Can it be connected to recruiting?", False), ("Explain my calculated scenario", True)]:
        response = client.post("/api/chat", headers=csrf, json={"message": question, "scenario": defaults})
        assert response.status_code == 200
        body = response.json()
        assert body["scenario_explanation_included"] is explain
        assert body["scenario"]["results"]["monthly_revenue"] == 8100
        assert ("Under your assumptions, Python calculates" in body["answer"]["summary"]) is explain


def test_session_cookie_is_httponly_and_no_cache(client):
    response = client.get("/api/demo")
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_unique_secure_prospect_link_exchanges_and_personalizes(client, admin_headers, imported_company):
    created = client.post("/api/admin/prospects/import", headers=admin_headers, json=imported_company)
    assert created.status_code == 200, created.text
    token = urlparse(created.json()["dashboard_url"]).fragment
    with client.app.state.db() as db:
        assert db.scalar(select(AccessLink)).token_hash != token
    access = client.post("/api/access", json={"token": token})
    assert access.status_code == 200
    data = access.json()
    assert data["prospect"]["first_name"] == "Sam"
    assert data["prospect"]["company_name"] == "Synthetic Northstar"
    assert data["intelligence"]["claims"][0]["source_ids"] == ["northstar_intake"]
    assert "crm_contact_id" not in data["prospect"]


def test_revocation_invalidates_existing_private_session(client, admin_headers, imported_company):
    created = client.post("/api/admin/prospects/import", headers=admin_headers, json=imported_company).json()
    client.post("/api/access", json={"token": urlparse(created["dashboard_url"]).fragment})
    assert client.get("/api/history").status_code == 200
    client.delete(f"/api/admin/prospects/{created['prospect_id']}/access", headers=admin_headers)
    assert client.get("/api/history").status_code == 401


def test_expired_link_cannot_be_exchanged(client, admin_headers, imported_company):
    created = client.post("/api/admin/prospects/import", headers=admin_headers, json=imported_company).json()
    with client.app.state.db() as db:
        db.scalar(select(AccessLink)).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.post("/api/access", json={"token": urlparse(created["dashboard_url"]).fragment}).status_code == 401


def test_history_and_engineering_are_session_scoped(client, csrf):
    client.post("/api/chat", headers=csrf, json={"message": "Sensitive test marker"})
    other = TestClient(client.app)
    other.get("/api/demo")
    assert other.get("/api/history").json()["messages"] == []
    assert all(t["route"] != "/api/chat" for t in other.get("/api/engineering").json()["recent_requests"])
    other.close()


def test_draft_followup_cannot_deliver_to_real_crm(client, csrf, admin_headers):
    result = client.post("/api/follow-up", headers=csrf, json={"intent": "Review implementation", "notes": "Synthetic request"})
    assert result.json()["status"] == "draft"
    with client.app.state.db() as db:
        assert db.get(FollowUp, result.json()["id"]).status == "draft"
    response = client.post(f"/api/admin/follow-ups/{result.json()['id']}/deliver", headers=admin_headers, json={"approved": True})
    assert response.status_code == 403


def test_administrative_operations_fail_closed(client, imported_company):
    assert client.post("/api/admin/prospects/import", json=imported_company).status_code == 401
    assert client.get("/api/admin/follow-ups", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.post("/api/internal/research", json={"prospect_id": "demo-copperline"}).status_code == 503


def test_oversized_request_rejected_before_work(client):
    response = client.post("/api/access", content="x" * 70000, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_no_private_access_issued_before_completed_research(client, admin_headers):
    with client.app.state.db() as db:
        item = Prospect(profile={"company_name": "Pending"}, synthetic=False)
        db.add(item)
        db.commit()
        id_ = item.id
    assert client.post(f"/api/admin/prospects/{id_}/access", headers=admin_headers).status_code == 409


def test_logout_expires_session(client, csrf):
    assert client.delete("/api/session", headers=csrf).status_code == 200
    assert client.get("/api/history").status_code == 401
    with client.app.state.db() as db:
        assert db.scalar(select(BrowserSession)).expires_at <= now()
