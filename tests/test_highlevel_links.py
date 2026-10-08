"""Provider contract and policy tests; no credentials or live CRM calls."""
import json

import httpx
import pytest

from app.config import Settings
from app.integrations import HighLevelClient, IntegrationUnavailable


ORIGIN = "https://prospect.firewireads.com"
URL = ORIGIN + "/p?client=prospect-123#" + "private-test-capability-" + "x" * 32
FIELD = {"id": "field1", "locationId": "firewire", "name": "ProspectIQ Dashboard URL",
         "fieldKey": "contact.prospectiq_dashboard_url", "model": "contact", "dataType": "TEXT"}
LINK = {"id": "link1", "locationId": "firewire", "name": "ProspectIQ Dashboard",
        "redirectTo": "{{contact.prospectiq_dashboard_url}}", "fieldKey": "{{trigger_link.link1}}"}


class CRM:
    def __init__(self):
        self.fields, self.links, self.calls = [], [], []
        self.contact = {"id": "contact1", "locationId": "firewire", "dnd": False,
                        "tags": ["prospectiq-approved"], "customFields": [{"id": "untouched", "value": "preserve"}]}
        self.write_status = 200
        self.write_error = None
        self.readback_wrong = False
        self.remove_other_fields = False
        self.provider_body = "never-print-private-provider-body"
        self.direct_link = dict(LINK)

    def handle(self, request):
        self.calls.append((request.method, request.url.path, dict(request.url.params), request.content))
        assert request.headers["version"] == "2021-07-28"
        if request.method != "GET" and self.write_error:
            raise self.write_error
        if request.method != "GET" and self.write_status != 200:
            return httpx.Response(self.write_status, json={"private": self.provider_body})
        path = request.url.path
        if path == "/locations/firewire/customFields":
            if request.method == "POST":
                body = json.loads(request.content)
                assert body == {"name": FIELD["name"], "dataType": "TEXT", "model": "contact"}
                self.fields.append(dict(FIELD))
                return httpx.Response(201, json={"customField": FIELD})
            return httpx.Response(200, json={"customFields": self.fields})
        if path == "/locations/firewire/customFields/field1":
            return httpx.Response(200, json={"customField": {**FIELD, "id": "wrong"} if self.readback_wrong else FIELD})
        if path == "/links/search":
            assert request.url.params["locationId"] == "firewire"
            return httpx.Response(200, json={"links": self.links})
        if path == "/links/" and request.method == "POST":
            assert json.loads(request.content) == {"locationId": "firewire", "name": LINK["name"], "redirectTo": LINK["redirectTo"]}
            self.links.append(dict(LINK))
            return httpx.Response(201, json={"link": LINK})
        if path == "/links/id/link1":
            assert request.url.params["locationId"] == "firewire"
            return httpx.Response(200, json={"link": {**self.direct_link, "fieldKey": "wrong"} if self.readback_wrong else self.direct_link})
        if path == "/contacts/contact1":
            if request.method == "PUT":
                body = json.loads(request.content)
                assert body == {"customFields": [{"id": "field1", "fieldValue": URL}]}
                others = [] if self.remove_other_fields else [field for field in self.contact["customFields"] if field["id"] != "field1"]
                self.contact["customFields"] = [*others, {"id": "field1", "value": "wrong" if self.readback_wrong else URL}]
                return httpx.Response(200, json={"succeeded": True})
            return httpx.Response(200, json={"contact": self.contact})
        return httpx.Response(404, json={"private": self.provider_body})

    def client(self):
        return HighLevelClient("private-test-token", "firewire", sleep=lambda _: None,
                               client=httpx.Client(transport=httpx.MockTransport(self.handle)))


def set_url(client, **kwargs):
    return client.set_dashboard_url("contact1", "field1", URL, cohort_tag="prospectiq-approved", public_origin=ORIGIN, **kwargs)


def test_field_creation_requires_exact_metadata_readback_then_reuses_without_post():
    crm = CRM()
    client = crm.client()
    assert client.ensure_dashboard_field() == {**FIELD, "reused": False}
    assert client.ensure_dashboard_field() == {**FIELD, "reused": True}
    assert sum(method == "POST" for method, *_ in crm.calls) == 1


def test_trigger_creation_readback_uses_official_id_route_and_reuses_without_post():
    crm = CRM()
    client = crm.client()
    assert client.ensure_dashboard_trigger_link() == {**LINK, "reused": False}
    assert client.ensure_dashboard_trigger_link() == {**LINK, "reused": True}
    assert sum(method == "POST" for method, *_ in crm.calls) == 1
    assert any(path == "/links/id/link1" for _, path, *_ in crm.calls)


@pytest.mark.parametrize("include_tenant", [True, False])
def test_real_search_dto_uses_underscore_id_and_requires_direct_resource_verification(include_tenant):
    crm = CRM()
    # Observed provider search shape: _id, name, redirectTo, deleted; no fieldKey.
    candidate = {"_id": "link1", "name": LINK["name"], "redirectTo": LINK["redirectTo"], "deleted": False}
    if include_tenant:
        candidate["locationId"] = "firewire"
    crm.links = [candidate]
    assert crm.client().ensure_dashboard_trigger_link() == {**LINK, "reused": True}
    assert any(path == "/links/id/link1" for _, path, *_ in crm.calls)
    assert all(method == "GET" for method, *_ in crm.calls)


def test_search_dto_with_explicit_foreign_tenant_is_rejected_before_direct_read_or_write():
    crm = CRM()
    crm.links = [{"_id": "link1", "name": LINK["name"], "locationId": "other-brand"}]
    with pytest.raises(IntegrationUnavailable, match="search tenant verification"):
        crm.client().ensure_dashboard_trigger_link()
    assert len(crm.calls) == 1 and crm.calls[0][1] == "/links/search"


@pytest.mark.parametrize("changes", [{"locationId": "other-brand"}, {"locationId": None}, {"id": "other"},
                                     {"fieldKey": "{{trigger_link.other}}"}, {"redirectTo": "https://other-brand.example"}])
def test_sparse_search_dto_never_weakens_direct_tenant_identity_or_destination_validation(changes):
    crm = CRM()
    crm.links = [{"_id": "link1", "name": LINK["name"]}]
    crm.direct_link.update(changes)
    with pytest.raises(IntegrationUnavailable):
        crm.client().ensure_dashboard_trigger_link()
    assert all(method == "GET" for method, *_ in crm.calls)


def test_search_dto_with_conflicting_id_aliases_is_rejected_without_direct_read():
    crm = CRM()
    crm.links = [{"id": "link1", "_id": "other", "name": LINK["name"], "locationId": "firewire"}]
    with pytest.raises(IntegrationUnavailable, match="search identity is ambiguous"):
        crm.client().ensure_dashboard_trigger_link()
    assert len(crm.calls) == 1


@pytest.mark.parametrize("changes", [{"locationId": "other-brand"}, {"model": "opportunity"},
                                     {"dataType": "URL"}, {"fieldKey": "contact.other_field"}])
def test_existing_field_identity_conflicts_never_create_or_write(changes):
    crm = CRM()
    crm.fields = [{**FIELD, **changes}]
    with pytest.raises(IntegrationUnavailable, match="identity or tenant"):
        crm.client().ensure_dashboard_field()
    assert all(method == "GET" for method, *_ in crm.calls)


@pytest.mark.parametrize("changes", [{"locationId": "other-brand"}, {"redirectTo": "https://another-brand.example"},
                                     {"fieldKey": "{{trigger_link.other}}"}])
def test_existing_trigger_conflicts_fail_closed_without_post(changes):
    crm = CRM()
    crm.links = [{**LINK, **changes}]
    with pytest.raises(IntegrationUnavailable):
        crm.client().ensure_dashboard_trigger_link()
    assert all(method == "GET" for method, *_ in crm.calls)


@pytest.mark.parametrize("resource", ["field", "link"])
def test_duplicate_dedicated_resources_are_ambiguous_and_never_mutated(resource):
    crm = CRM()
    if resource == "field":
        crm.fields = [FIELD, {**FIELD, "id": "field2"}]
        action = crm.client().ensure_dashboard_field
    else:
        crm.links = [LINK, {**LINK, "id": "link2", "fieldKey": "{{trigger_link.link2}}"}]
        action = crm.client().ensure_dashboard_trigger_link
    with pytest.raises(IntegrationUnavailable, match="ambiguous"):
        action()
    assert all(method == "GET" for method, *_ in crm.calls)


@pytest.mark.parametrize("resource", ["field", "link"])
def test_created_resource_readback_mismatch_is_unknown_without_second_post(resource):
    crm = CRM()
    crm.readback_wrong = True
    action = crm.client().ensure_dashboard_field if resource == "field" else crm.client().ensure_dashboard_trigger_link
    with pytest.raises(IntegrationUnavailable, match="reconcile before retry"):
        action()
    assert sum(method == "POST" for method, *_ in crm.calls) == 1


@pytest.mark.parametrize("resource", ["field", "link"])
def test_failed_resource_creation_is_not_blindly_retried_or_leaked(resource):
    crm = CRM()
    crm.write_status = 503
    action = crm.client().ensure_dashboard_field if resource == "field" else crm.client().ensure_dashboard_trigger_link
    with pytest.raises(IntegrationUnavailable, match="reconcile before retry") as error:
        action()
    assert crm.provider_body not in str(error.value)
    assert sum(method == "POST" for method, *_ in crm.calls) == 1


def test_contact_patch_verifies_cohort_tenant_target_value_and_untouched_fields():
    crm = CRM()
    client = crm.client()
    assert set_url(client) == {"contact_id": "contact1", "field_id": "field1", "verified": True, "reused": False}
    assert crm.contact["customFields"][0] == {"id": "untouched", "value": "preserve"}
    assert set_url(client)["reused"] is True
    assert sum(method == "PUT" for method, *_ in crm.calls) == 1
    assert not any("messages" in path or "workflow" in path or "tasks" in path for _, path, *_ in crm.calls)


@pytest.mark.parametrize("changes", [{"dnd": True}, {"tags": []}, {"locationId": "other-brand"}, {"id": "other-contact"}])
def test_suppression_cohort_and_contact_identity_blocks_patch(changes):
    crm = CRM()
    crm.contact.update(changes)
    with pytest.raises(IntegrationUnavailable):
        set_url(crm.client())
    assert all(method == "GET" for method, *_ in crm.calls)


@pytest.mark.parametrize("contact_id,synthetic", [("", False), ("demo-copperline", False), ("contact1", True)])
def test_synthetic_or_unlinked_prospects_never_touch_crm(contact_id, synthetic):
    crm = CRM()
    with pytest.raises(IntegrationUnavailable, match="Synthetic or unlinked"):
        crm.client().set_dashboard_url(contact_id, "field1", URL, public_origin=ORIGIN,
                                       cohort_tag="prospectiq-approved", synthetic=synthetic)
    assert crm.calls == []


@pytest.mark.parametrize("url", [
    URL.replace("https://", "http://"), URL.replace("prospect.firewireads.com", "another-brand.example"),
    URL.split("#")[0], URL.replace("?client=prospect-123", "?client=prospect-123&client=other"),
    URL.replace("?client=prospect-123", "?client=prospect-123&email=private@example.com"),
    URL.replace("?client=prospect-123", "?client="), URL.replace("/p?", "/admin?"),
    URL.replace("prospect.firewireads.com", "user:password@prospect.firewireads.com"),
])
def test_private_link_rejects_unapproved_url_shapes_before_any_provider_call(url):
    crm = CRM()
    with pytest.raises(ValueError, match="Dashboard URL requires"):
        crm.client().set_dashboard_url("contact1", "field1", url, cohort_tag="prospectiq-approved", public_origin=ORIGIN)
    assert crm.calls == []


@pytest.mark.parametrize("mismatch", ["target", "other_fields"])
def test_contact_readback_mismatch_is_unknown_and_never_retried(mismatch):
    crm = CRM()
    crm.readback_wrong = mismatch == "target"
    crm.remove_other_fields = mismatch == "other_fields"
    if mismatch == "target":
        # Preserve correct metadata, fail only the post-write contact value.
        handler = crm.handle
        def readback_handler(request):
            if request.url.path == "/locations/firewire/customFields/field1":
                return httpx.Response(200, json={"customField": FIELD})
            return handler(request)
        client = HighLevelClient("private", "firewire", sleep=lambda _: None,
                                 client=httpx.Client(transport=httpx.MockTransport(readback_handler)))
    else:
        client = crm.client()
    with pytest.raises(IntegrationUnavailable, match="outcome unknown; reconcile"):
        set_url(client)
    assert sum(method == "PUT" for method, *_ in crm.calls) == 1


def test_write_timeout_does_not_leak_url_or_provider_error_and_is_not_retried():
    crm = CRM()
    crm.write_error = httpx.ReadTimeout("private provider body " + URL)
    with pytest.raises(IntegrationUnavailable, match="reconcile before retry") as error:
        set_url(crm.client())
    assert URL not in str(error.value)
    assert "private provider body" not in str(error.value)
    assert sum(method == "PUT" for method, *_ in crm.calls) == 1


def test_link_write_flag_is_distinct_from_followup_and_requires_verified_ids(monkeypatch):
    monkeypatch.delenv("ALLOW_CRM_LINKS", raising=False)
    monkeypatch.setenv("ALLOW_CRM_FOLLOWUP", "true")
    assert Settings.from_env().allow_crm_links is False
    assert Settings.from_env().allow_crm_followup is True
    with pytest.raises(ValueError, match="verified dashboard field"):
        Settings(allow_crm_links=True, public_origin=ORIGIN).validate()
    Settings(allow_crm_links=True, public_origin=ORIGIN, ghl_dashboard_field_id="field1",
             ghl_dashboard_trigger_link_id="link1").validate()


def test_link_configuration_identifier_cannot_contain_paths():
    with pytest.raises(ValueError, match="valid resource identifiers"):
        Settings(ghl_dashboard_field_id="../field1").validate()
