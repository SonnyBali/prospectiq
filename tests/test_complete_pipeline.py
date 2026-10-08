"""Offline exercise of the complete CRM→research→dashboard→review pipeline.

External methods are fakes. This proves orchestration, not cloud deployment or
live CRM delivery, and uses no customer data or production credential.
"""
from dataclasses import replace
from urllib.parse import urlparse

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import FakeSecrets


def test_complete_pipeline_and_idempotent_retry(settings, monkeypatch):
    state = {"contact_reads": 0, "research_calls": 0, "task_writes": 0, "queue_writes": 0}
    contact = {"id": "crm-test", "location_id": settings.ghl_location, "company_name": "Offline Plumbing", "first_name": "Morgan",
               "website": "https://example.com/plumbing", "tags": [settings.crm_cohort_tag], "dnd": False,
               "email": "never-in-dashboard@example.com", "phone": "never-in-dashboard"}
    class CRM:
        def __init__(self, *args):
            pass
        def get_contact(self, contact_id):
            assert contact_id == "crm-test"
            state["contact_reads"] += 1
            return contact
        def create_followup_task(self, contact_id, title, body):
            state["task_writes"] += 1
            assert contact_id == "crm-test" and title.startswith("ProspectIQ review ")
            return {"id": "internal-task-test"}
    class Queue:
        def __init__(self, *args):
            pass
        def enqueue(self, prospect_id):
            state["queue_writes"] += 1
            return "projects/test/locations/test/queues/test/tasks/offline"
    class Research:
        def __init__(self, *args):
            pass
        def research(self, company_name, website):
            assert company_name == "Offline Plumbing"
            state["research_calls"] += 1
            return {"sources": [{"id": "intake", "title": "Offline research fixture", "url": website, "excerpt": "The offline test business accepts service requests by phone.", "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": False}],
                    "notes": "Grounded fixture", "search_suggestions_html": "<p>Provider attribution fixture</p>"}
    settings = replace(settings, allow_cloud_tasks=True, allow_crm_followup=True, task_queue="offline",
                       worker_url="https://worker.example/api/internal/research", task_service_account="task@example.iam.gserviceaccount.com")
    def identity(token, request, audience):
        assert token == "offline-identity" and audience == "https://worker.example"
        return {"email": settings.task_service_account, "email_verified": True}
    monkeypatch.setattr("app.main.HighLevelClient", CRM)
    monkeypatch.setattr("app.main.CloudResearchQueue", Queue)
    monkeypatch.setattr("app.main.VertexResearch", Research)
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", identity)
    headers = {"X-Admin-Key": "test-admin-key"}
    with TestClient(create_app(settings, FakeSecrets())) as client:
        imported = client.post("/api/admin/prospects/from-crm", headers=headers, json={"contact_id": "crm-test"}).json()
        id_ = imported["prospect_id"]
        assert imported["research_status"] == "pending"
        assert client.post(f"/api/admin/prospects/{id_}/access", headers=headers).status_code == 409
        queued = client.post(f"/api/admin/prospects/{id_}/research", headers=headers)
        assert queued.json()["status"] == "queued"
        worked = client.post("/api/internal/research", headers={"Authorization": "Bearer offline-identity"}, json={"prospect_id": id_})
        assert worked.status_code == 200, worked.text
        assert worked.json()["status"] == "complete"
        retry = client.post("/api/internal/research", headers={"Authorization": "Bearer offline-identity"}, json={"prospect_id": id_})
        assert retry.json()["cached"] is True
        issued = client.post(f"/api/admin/prospects/{id_}/access", headers=headers).json()
        access = client.post("/api/access", json={"token": urlparse(issued["dashboard_url"]).fragment})
        assert access.status_code == 200
        data = access.json()
        assert data["has_research_attribution"] is True
        assert "never-in-dashboard" not in access.text
        assert data["prospect"]["first_name"] == "Morgan"
        assert "attribution fixture" in client.get("/api/research-attribution").text
        csrf = {"X-CSRF-Token": data["csrf_token"]}
        assert client.post("/api/chat", headers=csrf, json={"message": "Review the evidence"}).status_code == 200
        follow = client.post("/api/follow-up", headers=csrf, json={"intent": "Request an implementation plan"}).json()
        assert follow["status"] == "draft"
        assert state["task_writes"] == 0
        delivered = client.post(f"/api/admin/follow-ups/{follow['id']}/deliver", headers=headers, json={"approved": True})
        assert delivered.json()["status"] == "delivered"
        repeated = client.post(f"/api/admin/follow-ups/{follow['id']}/deliver", headers=headers, json={"approved": True})
        assert repeated.json()["status"] == "delivered"
        assert state["task_writes"] == 1 and state["research_calls"] == 1 and state["queue_writes"] == 1
