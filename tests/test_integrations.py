from types import SimpleNamespace as NS
from unittest.mock import Mock

import httpx
import pytest

from app.integrations import (
    CloudResearchQueue, HighLevelClient, IntegrationUnavailable,
    SecretStore, VertexResearch, cloud_sql_creator, public_https_url,
)


def crm_client(contact):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"contact": contact}))
    return HighLevelClient("private-test-token", "firewire", client=httpx.Client(transport=transport), sleep=lambda _: None)


@pytest.mark.parametrize("tenant", [None, "another-brand"])
def test_personalization_rejects_wrong_or_unproven_tenant(tenant):
    with pytest.raises(IntegrationUnavailable, match="tenant verification"):
        crm_client({"id": "contact1", "locationId": tenant, "firstName": "Synthetic"}).get_contact("contact1")


def test_personalization_rejects_wrong_contact_identity():
    with pytest.raises(IntegrationUnavailable, match="identity verification"):
        crm_client({"id": "other", "locationId": "firewire"}).get_contact("contact1")


def test_contact_read_normalizes_company_and_retains_suppression():
    contact = crm_client({"id": "contact1", "locationId": "firewire", "companyName": "Synthetic Co", "firstName": "Test", "dnd": True}).get_contact("contact1")
    assert contact["company_name"] == "Synthetic Co"
    assert contact["dnd"] is True
    assert contact["location_id"] == "firewire"


@pytest.mark.parametrize("settings", [{"SMS": {"status": "active"}}, {"Email": {}}, "invalid"])
def test_channel_suppression_or_unknown_channel_policy_blocks_followup(settings):
    contact = crm_client({"id": "contact1", "locationId": "firewire", "dnd": False, "dndSettings": settings}).get_contact("contact1")
    assert contact["dnd"] is True


def test_missing_global_suppression_policy_blocks_followup():
    contact = crm_client({"id": "contact1", "locationId": "firewire"}).get_contact("contact1")
    assert contact["dnd"] is True


def followup_client(*, suppressed=False, verified_contact="contact1", write_status=201):
    calls = []

    def handler(request):
        calls.append((request.method, str(request.url)))
        if request.url.path == "/contacts/contact1":
            return httpx.Response(200, json={"contact": {"id": "contact1", "locationId": "firewire", "dnd": suppressed}})
        task = {"id": "task1", "title": "Review synthetic opportunity", "body": "Internal review only", "completed": False, "contactId": verified_contact}
        return httpx.Response(write_status if request.method == "POST" else 200, json={"task": task})

    client = HighLevelClient("private", "firewire", client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    return client, calls


def test_followup_is_complete_only_after_exact_contact_task_readback():
    client, calls = followup_client()
    result = client.create_followup_task("contact1", "Review synthetic opportunity", "Internal review only")
    assert result == {"id": "task1"}
    assert [item[0] for item in calls] == ["GET", "POST", "GET"]


def test_suppressed_contact_never_receives_task_write():
    client, calls = followup_client(suppressed=True)
    with pytest.raises(IntegrationUnavailable, match="Suppressed"):
        client.create_followup_task("contact1", "Review synthetic opportunity", "Internal review only")
    assert all(item[0] == "GET" for item in calls)


def test_followup_mismatched_readback_is_unknown_and_never_retried():
    client, calls = followup_client(verified_contact="another-contact")
    with pytest.raises(IntegrationUnavailable, match="readback mismatch"):
        client.create_followup_task("contact1", "Review synthetic opportunity", "Internal review only")
    assert sum(item[0] == "POST" for item in calls) == 1


def test_failed_task_post_is_not_retried_to_avoid_duplicates():
    client, calls = followup_client(write_status=503)
    with pytest.raises(IntegrationUnavailable, match="reconcile before retry"):
        client.create_followup_task("contact1", "Review synthetic opportunity", "Internal review only")
    assert sum(item[0] == "POST" for item in calls) == 1


def test_highlevel_throttling_is_bounded_and_does_not_reveal_provider_body():
    client = Mock()
    client.get.return_value = httpx.Response(429, json={"secret": "must-not-appear"})
    pauses = []
    reader = HighLevelClient("private", "firewire", client=client, sleep=pauses.append)
    with pytest.raises(IntegrationUnavailable) as error:
        reader.get_contact("contact1")
    assert "must-not-appear" not in str(error.value)
    assert client.get.call_count == 4
    assert {2, 4, 8}.issubset(set(pauses))


@pytest.mark.parametrize("url", [
    "http://company.com", "https://127.0.0.1", "https://metadata.google.internal",
    "https://user:password@company.com", "https://company.com:8000", "https://company.com:bad",
    "file:///secret", "https://localhost", None,
])
def test_research_rejects_nonpublic_or_credential_urls(url):
    with pytest.raises(ValueError):
        public_https_url(url)


def grounded_response(*, url="https://company.com/services"):
    metadata = NS(
        grounding_chunks=[NS(web=NS(uri=url, title="Official Services"))],
        grounding_supports=[NS(segment=NS(text="Synthetic Co offers plumbing services."), grounding_chunk_indices=[0])],
        search_entry_point=NS(rendered_content="<div>Search suggestions</div>"),
    )
    return NS(text="Unsupported invented revenue: $5 million.", candidates=[NS(grounding_metadata=metadata)])


def test_advisor_evidence_contains_only_metadata_supported_claims():
    evidence = VertexResearch.extract_grounded(grounded_response())
    assert "Unsupported" not in evidence["notes"]
    assert "$5 million" not in evidence["notes"]
    assert evidence["notes"].endswith("[g1]")
    assert evidence["sources"][0]["url"] == "https://company.com/services"
    assert evidence["sources"][0]["is_synthetic"] is False
    assert evidence["search_suggestions_html"]


def test_research_fails_closed_when_only_source_is_private():
    with pytest.raises(IntegrationUnavailable, match="no supported public evidence"):
        VertexResearch.extract_grounded(grounded_response(url="https://127.0.0.1/"))


def test_secret_sdk_read_never_embeds_secret_in_errors():
    sdk = Mock()
    sdk.access_secret_version.side_effect = RuntimeError("sensitive-body-api-key")
    with pytest.raises(IntegrationUnavailable) as error:
        SecretStore("test-project", client=sdk).get("OPENAI_API_KEY")
    assert "sensitive-body-api-key" not in str(error.value)


def test_queue_carries_only_internal_id_and_oidc_identity():
    sdk = Mock()
    sdk.queue_path.return_value = "projects/test-project/locations/us-central1/queues/research"
    sdk.create_task.return_value = NS(name="task-name")
    queue = CloudResearchQueue(
        "test-project", "us-central1", "research", "https://worker-example.run.app/internal/research",
        "worker@test-project.iam.gserviceaccount.com", client=sdk,
    )
    assert queue.enqueue("prospect123") == "task-name"
    task = sdk.create_task.call_args.kwargs["request"]["task"]
    assert task.http_request.body == b'{"prospect_id": "prospect123"}'
    assert task.http_request.oidc_token.audience == "https://worker-example.run.app"
    assert task.http_request.oidc_token.service_account_email == "worker@test-project.iam.gserviceaccount.com"


def test_task_identity_cannot_cross_google_project():
    with pytest.raises(ValueError, match="configured project"):
        CloudResearchQueue("test-project", "us-central1", "research", "https://worker-example.run.app/internal/research", "worker@another-project.iam.gserviceaccount.com")


def test_sql_creator_is_lazy_and_releases_connector_resources():
    connector = Mock()
    connection = object()
    connector.connect.return_value = connection
    creator = cloud_sql_creator("test-project:us-central1:prospectiq", "prospectiq", "server-secret", "prospectiq", connector=connector)
    connector.connect.assert_not_called()
    assert creator() is connection
    assert creator.connector is connector
    creator.close()
    connector.close.assert_called_once()
    assert connector.connect.call_args.kwargs["password"] == "server-secret"


def test_sql_provider_error_does_not_expose_password():
    connector = Mock()
    connector.connect.side_effect = RuntimeError("server-secret")
    creator = cloud_sql_creator("test-project:us-central1:prospectiq", "prospectiq", "server-secret", "prospectiq", connector=connector)
    with pytest.raises(IntegrationUnavailable) as error:
        creator()
    assert "server-secret" not in str(error.value)
