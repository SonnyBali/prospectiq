"""Operator-only link assignment and fail-closed capability lifecycle."""
from dataclasses import replace
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.db import AccessLink, Prospect, now
from app.integrations import HighLevelClient, IntegrationUnavailable
from app.main import create_app, digest
from conftest import FakeSecrets


ORIGIN = "https://prospect.firewireads.com"
ENDPOINT = "/api/admin/prospects/client1/highlevel-link"


class FakeCRM:
    _contact_fields = staticmethod(HighLevelClient._contact_fields)
    _validate_dashboard_url = staticmethod(HighLevelClient._validate_dashboard_url)

    def __init__(self):
        self.contact = {"id": "contact1", "dnd": False, "tags": ["prospectiq-approved"],
                        "custom_fields": [{"id": "untouched", "value": "preserve"}]}
        self.calls, self.writes = [], []
        self.fail_configuration = False
        self.fail_write = False

    def get_dashboard_field(self, field_id):
        self.calls.append("field")
        assert field_id == "field1"
        if self.fail_configuration:
            raise IntegrationUnavailable("private provider response must not escape")
        return {"id": "field1"}

    def get_dashboard_trigger_link(self, link_id):
        self.calls.append("trigger")
        assert link_id == "link1"
        return {"id": "link1", "fieldKey": "{{trigger_link.link1}}"}

    def get_contact(self, contact_id):
        self.calls.append("contact")
        assert contact_id == "contact1"
        return self.contact

    def set_dashboard_url(self, contact_id, field_id, url, **kwargs):
        assert contact_id == "contact1" and field_id == "field1"
        assert kwargs == {"cohort_tag": "prospectiq-approved", "public_origin": ORIGIN, "synthetic": False}
        self.writes.append(url)
        self.contact["custom_fields"] = [{"id": "untouched", "value": "preserve"}, {"id": field_id, "value": url}]
        if self.fail_write:
            raise RuntimeError("Sensitive unknown write: " + url)
        return {"verified": True}


@pytest.fixture
def link_app(settings, monkeypatch):
    crm = FakeCRM()
    monkeypatch.setattr("app.main.HighLevelClient", lambda *_: crm)
    configured = replace(settings, public_origin=ORIGIN, allow_crm_links=True,
                         ghl_dashboard_field_id="field1", ghl_dashboard_trigger_link_id="link1")
    with TestClient(create_app(configured, FakeSecrets()), base_url=ORIGIN) as client:
        with client.app.state.db() as db:
            db.add(Prospect(id="client1", profile={"first_name": "Client", "company_name": "Real company", "industry": "Services", "website": "https://example.com"},
                            crm_contact_id="contact1", synthetic=False, sources=[], intelligence={"summary": "Cached evidence"},
                            research_status="complete", research_completed_at=now()))
            db.commit()
        yield client, crm


def access_links(client):
    with client.app.state.db() as db:
        return db.scalars(select(AccessLink).where(AccessLink.prospect_id == "client1")).all()


def test_admin_is_required_before_any_provider_call(link_app):
    client, crm = link_app
    assert client.post(ENDPOINT, json={"approved": True}).status_code == 401
    assert not crm.calls and not crm.writes and not access_links(client)


@pytest.mark.parametrize("payload", [{}, {"approved": False}, {"approved": True, "send": True}])
def test_explicit_approval_schema_and_no_extra_actions(link_app, admin_headers, payload):
    client, crm = link_app
    assert client.post(ENDPOINT, headers=admin_headers, json=payload).status_code == 422
    assert not crm.calls and not access_links(client)


def test_link_flag_is_independent_of_follow_up_and_defaults_disabled(settings, monkeypatch, admin_headers):
    crm = FakeCRM()
    monkeypatch.setattr("app.main.HighLevelClient", lambda *_: crm)
    with TestClient(create_app(replace(settings, allow_crm_followup=True), FakeSecrets())) as client:
        assert client.post(ENDPOINT, headers=admin_headers, json={"approved": True}).status_code == 403
    assert not crm.calls


@pytest.mark.parametrize("changes,status", [({"synthetic": True}, 403), ({"crm_contact_id": None}, 403),
                                           ({"research_status": "pending"}, 409), ({"intelligence": None}, 409)])
def test_ineligible_prospects_do_not_mint_or_call_crm(link_app, admin_headers, changes, status):
    client, crm = link_app
    with client.app.state.db() as db:
        prospect = db.get(Prospect, "client1")
        for key, value in changes.items():
            setattr(prospect, key, value)
        db.commit()
    assert client.post(ENDPOINT, headers=admin_headers, json={"approved": True}).status_code == status
    assert not crm.calls and not crm.writes and not access_links(client)


def test_missing_prospect_has_no_external_call(link_app, admin_headers):
    client, crm = link_app
    response = client.post(ENDPOINT.replace("client1", "missing"), headers=admin_headers, json={"approved": True})
    assert response.status_code == 404 and not crm.calls


def test_verified_assignment_reuses_exact_active_link_without_second_write(link_app, admin_headers):
    client, crm = link_app
    first = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert first.status_code == 200
    result = first.json()
    parsed = urlparse(result["dashboard_url"])
    assert parsed.scheme == "https" and parsed.netloc == "prospect.firewireads.com" and parsed.path == "/p"
    assert parse_qs(parsed.query) == {"client": ["client1"]} and len(parsed.fragment) >= 32
    assert result["reused"] is False and result["trigger_link_key"] == "{{trigger_link.link1}}"
    links = access_links(client)
    assert len(links) == 1 and links[0].token_hash == digest(parsed.fragment) and not links[0].revoked
    assert parsed.fragment not in links[0].token_hash
    second = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert second.status_code == 200 and second.json()["reused"] is True
    assert second.json()["dashboard_url"] == result["dashboard_url"]
    assert len(crm.writes) == 1 and len(access_links(client)) == 1


@pytest.mark.parametrize("old_state", ["expired", "revoked", "other-client", "invalid-url"])
def test_unusable_stored_link_is_replaced_by_a_new_verified_capability(link_app, admin_headers, old_state):
    client, crm = link_app
    raw = "old-private-capability-" + "a" * 32
    stored = ORIGIN + "/p?client=client1#" + raw
    with client.app.state.db() as db:
        if old_state == "other-client":
            db.add(Prospect(id="other", profile={}, synthetic=False))
            db.flush()
        db.add(AccessLink(token_hash=digest(raw), prospect_id="other" if old_state == "other-client" else "client1",
                          expires_at=now() + timedelta(hours=-1 if old_state == "expired" else 1), revoked=old_state == "revoked"))
        db.commit()
    if old_state == "invalid-url":
        stored = "https://other-brand.example/p?client=client1#" + raw
    crm.contact["custom_fields"].append({"id": "field1", "value": stored})
    response = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert response.status_code == 200 and response.json()["reused"] is False
    assert response.json()["dashboard_url"] != stored and len(crm.writes) == 1


def test_configuration_failure_prevents_mint_and_hides_provider_body(link_app, admin_headers):
    client, crm = link_app
    crm.fail_configuration = True
    response = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert response.status_code == 502 and "private provider" not in response.text
    assert not crm.writes and not access_links(client)


@pytest.mark.parametrize("changes", [{"dnd": True}, {"tags": []}, {"tags": "prospectiq-approved"}])
def test_suppression_and_unverified_cohort_prevent_mint(link_app, admin_headers, changes):
    client, crm = link_app
    crm.contact.update(changes)
    response = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert response.status_code == 403 and not crm.writes and not access_links(client)


def test_unknown_provider_write_revokes_new_capability_without_retry_or_secret_echo(link_app, admin_headers):
    client, crm = link_app
    crm.fail_write = True
    response = client.post(ENDPOINT, headers=admin_headers, json={"approved": True})
    assert response.status_code == 502 and len(crm.writes) == 1
    raw = urlparse(crm.writes[0]).fragment
    assert raw not in response.text and crm.writes[0] not in response.text
    links = access_links(client)
    assert len(links) == 1 and links[0].revoked
    assert client.post("/api/access", json={"token": raw, "client_id": "client1"}).status_code == 401


def test_import_preserves_google_grounding_attribution(client, imported_company, admin_headers):
    payload = {**imported_company, "research_attribution_html": "<p>Verified Google grounding attribution</p>"}
    imported = client.post("/api/admin/prospects/import", headers=admin_headers, json=payload)
    assert imported.status_code == 200
    parsed = urlparse(imported.json()["dashboard_url"])
    opened = client.post("/api/access", json={"token": parsed.fragment, "client_id": imported.json()["prospect_id"]})
    assert opened.status_code == 200
    assert client.get("/api/research-attribution").text == payload["research_attribution_html"]
    assert client.app.version == "1.1.0"
