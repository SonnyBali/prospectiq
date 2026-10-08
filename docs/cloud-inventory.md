# Google Cloud and provider integration inventory

Updated **2026-10-08 (Asia/Singapore)** after the owner-approved cloud release. The project is `ai-leadscore`, region `us-central1`. The main Cloud Run service is ready; dedicated PostgreSQL persistence, scoped runtime secret access, deployed OpenAI and request/usage logging are verified. The [canonical recruiter demo](https://prospect.firewireads.com/) has provisioned managed TLS and passed strict HTTPS health, actual Chrome dashboard/simulator/cited OpenAI chat/history/Engineering checks, and 25 same-origin backend checks. Google/Meta page-view network requests were observed; account-side receipt/reporting is untested. See [live-release.md](live-release.md) for the exact current revision/image and checkpoint.

The earlier read-only inspection on the same date enabled no APIs and provisioned no resources. Its useful provider/source evidence is preserved below and clearly distinguished from the subsequent approved deployment. No live task dispatch, CRM task delivery, customer outreach or live voice interaction was performed.

| Component | Live evidence | ProspectIQ implementation and remaining work |
|---|---|---|
| Cloud Run | Strict HTTPS `/health` returned HTTP 200, database connected and OpenAI mode. Canonical and native same-origin backend checks each passed 25 checks; actual Chrome AI chat/simulator/history/Engineering checks passed. Earlier static/SEO/private-noindex/CSP checks also passed; exact revision/image changes are tracked in the release record. Earlier existing `firewire-hot-dashboard` health evidence is separate. | Use [prospect.firewireads.com](https://prospect.firewireads.com/) as primary. The [native backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) accepts only the built-in public synthetic session, enforces CSRF and runs no marketing trackers. Canonical private access remains unchanged. Google/Meta page-view requests observed; account-side reporting untested. |
| Cloud Tasks | `projects/ai-leadscore/locations/us-central1/queues/heights-portal-launch` was `RUNNING`; queue list and metadata reads succeeded. | `CloudResearchQueue` builds an OIDC authenticated HTTP task with only an internal prospect ID. Unit tests verify its audience, service account and payload. A dedicated ProspectIQ queue/worker identity is required. The unrelated Heights queue is not reused. Live enqueue/dispatch was not tested. |
| Cloud SQL PostgreSQL | The initial audit reported `SERVICE_DISABLED`. The approved release subsequently enabled SQL Admin and provisioned `prospectiq-db`: PostgreSQL 16, `db-f1-micro`, `RUNNABLE`, with database/user `prospectiq`. Actual connector/schema and deployed chat, history, drafts and session persistence were verified. | Cloud SQL Python Connector + pg8000 supplies the encrypted connection and explicit cleanup. Dedicated runtime Cloud SQL Client access is verified. Local SQLite remains a credential-free development option, not the deployed database. |
| Secret Manager | Initial official SDK reads verified `OPENAI_API_KEY`, `FIREWIRE_GHL_API_KEY`, and `FIREWIRE_GHL_LOCATION_ID`. Dedicated administrative/database values were subsequently provisioned through the SDK; deployed SQL/OpenAI reads and scoped runtime access succeeded. Values were never printed or put in source/command arguments. | `SecretStore` uses Application Default Credentials in Cloud Run with access limited to named secrets. The explicitly enabled gcloud fallback is local-only. Administrative credential use and live CRM writes remain separately gated. |
| Cloud Logging | Direct reads matched canonical smoke `c3c1cbcd99f5462099572e1469ba551a` at `2026-10-08T14:01:23Z` and canonical Chrome chat `cb51f002eba24c19a4ce1faff11daef0` at `2026-10-08T13:58:05Z`. Native smoke/browser reads and earlier revisions remain separate evidence in the verification record. | Structured request IDs, provider/model, latency, token totals and configured-rate estimates are collected by Cloud Logging. Prompt/contact bodies, private capabilities, cookies, CSRF tokens and secrets remain excluded. Exact revision/image and final-host readback are maintained in the release record. |
| Google Vertex grounded research | A live official `google-genai` Vertex request using `gemini-2.5-flash` in `us-central1` researched the public FireWireAds website successfully: 7 public grounded sources, supported notes and Search Suggestions attribution returned. No CRM data was sent. | `VertexResearch` uses Google Search grounding and a configurable model/region. Grounding extraction is unit tested. This proves the tested model request; the deployed task-worker/database chain is not yet verified. Attribution must be preserved and rendered with grounded results. |
| OpenAI Responses | Initial official SDK probe: synthetic `store=False`, `gpt-4.1-mini-2025-04-14`, 16 input / 2 output tokens. Canonical backend smoke used 1,168 input / 310 output / zero cached tokens, estimate $0.0009632; actual canonical browser chat used 1,167 input / 275 output, estimate $0.0009068. Both have independently matched Cloud Logging events. No customer data was sent. | Configurable Responses model, typed output, extractive citations, safe unsupported-claim handling, stored history and token/cost accounting are backend- and canonical-browser-tested. Costs are configured estimates, not invoices. |
| HighLevel CRM | A FireWire credential read verified the expected tenant `aFnKcmUdTSPIjo7lCaix`. A direct GET of one contact succeeded and verified its returned tenant and identity. Output contained only presence booleans for first name, company and website. | `HighLevelClient.get_contact()` normalizes personalization data and rejects absent/wrong tenants or identities. Retrieval does not enroll, message or modify the contact. `create_followup_task()` is implemented with suppression checks and exact contact-task readback; tests mock all writes. Live follow-up writes remain gated and were not executed. |

## Reusable code inspected

`firewire-sales-os/python/firewire/client.py` already contains a tenant-bound HighLevel client, paced requests, sequential HTTP 429 backoff, private Google secret access and PII-free event filtering. Its project and tenant settings were rechecked live. The new application carries those safety patterns into an isolated provider module; it does not mutate the Sales OS client or inherit its outbound actions.

Relevant credential **names** observed in the initial audit: `OPENAI_API_KEY`, `FIREWIRE_GHL_API_KEY`, `FIREWIRE_GHL_LOCATION_ID`, and `GoogleGemini`. Dedicated database/admin secrets were added during the approved release; their values remain outside this inventory. `GoogleGemini` metadata existence does not prove access to a particular Google model. Vertex uses cloud IAM rather than that API key.

## How the Python boundaries work

`SecretStore.get()` resolves a secret just before a server-side provider is needed. Importing `integrations.py` starts no network request, which keeps the synthetic demo and test collection independent of production credentials. Credentials never enter dashboard payloads.

`HighLevelClient.get_contact()` performs a bounded, paced read. It verifies `locationId` and `id` before returning normalized fields. The normalized `dnd` flag blocks on global or per-channel suppression, known suppression tags, and missing/malformed policy. Provider exceptions are converted to safe status descriptions without returning provider bodies.

`create_followup_task()` rereads that policy before a single internal-task POST. It reads the resulting task back and verifies its contact, ID, title, body and incomplete state before reporting completion. An unknown mutation/readback outcome is never retried automatically; the caller must reconcile the uniquely titled task. The endpoint's operator approval/cohort gate is also required. No SMS, email, call or workflow enrollment is performed by this method.

`CloudResearchQueue.enqueue()` creates a Google task, not a Python background thread. Its OIDC audience is the configured Cloud Run service origin. The worker must verify its caller and use an idempotent research state transition, because tasks may be delivered more than once. The method is implemented but was only exercised with a fake SDK client.

`VertexResearch.research()` sends company name/website as JSON data to the provider. The application never fetches user-selected URLs locally. Only Google metadata-supported segments become advisor notes, each linked to a source ID; ungrounded model prose is discarded. `excerpt` is the supported model segment, not a verbatim scrape of the page. This is a grounding guard, not independent fact checking. Source freshness is represented by `observed_at` rather than an invented page publication date.

Google Search attribution HTML is preserved as `search_suggestions_html`. A UI that displays grounded results must satisfy the provider's Search Suggestions requirements; use an isolated sandboxed attribution surface rather than injecting provider HTML into the application's main document.

`cloud_sql_creator()` supplies SQLAlchemy a callable that establishes encrypted connector-managed PostgreSQL connections. The caller supplies a Secret Manager password, never a password-bearing database URL. Call `.close()` (or `.connector.close()`) at shutdown. The connector still requires IAM permission and a viable network path.

## Repeat the verification safely

From the `prospectiq` directory, use the project's Python environment:

```powershell
.venv/Scripts/python.exe scripts/verify_integrations.py --project ai-leadscore --allow-gcloud-fallback
.venv/Scripts/python.exe -m pytest tests/test_integrations.py -q
```

The first command reports resource metadata and safe status JSON. It neither provisions resources nor executes queued work. `--contact-id` optionally verifies one authorized CRM record without printing its fields. `--openai-probe` explicitly permits one paid synthetic Responses call; model selection uses `--openai-model` or `OPENAI_MODEL`. `--vertex-probe` permits one paid public FireWireAds research request; model selection uses `--vertex-model` or `VERTEX_MODEL`. Omit those flags when only metadata/credential verification is needed. A successful CLI exit means the inventory ran; examine each service's status before claiming it works.

The earlier integration subset passed **29/29** in the project virtual environment, covering cross-tenant rejection, identity checks, DND/unknown-policy retention, bounded throttling, unsafe reference URLs, grounded-only evidence, secret-error redaction, OIDC task shape, lazy SQL connection/cleanup and safe internal-task readback/reconciliation. Latest source/built-image checks passed **123 pytest tests on Windows and Linux**, Ruff, JavaScript syntax and 298 analytics privacy assertions. Actual deployed SQL connector/schema/persistence and canonical/native public browser workflows are verified. Live Tasks dispatch and HighLevel task writes remain untested and disabled. Canonical browser page-view requests are observed; account-side analytics receipt/reporting remains untested.

## Primary implementation references

- [Google Secret Manager Python access example](https://docs.cloud.google.com/secret-manager/docs/samples/secretmanager-access-secret-version)
- [Cloud Tasks HTTP target authentication](https://docs.cloud.google.com/tasks/docs/creating-http-target-tasks)
- [Cloud SQL PostgreSQL Python connector](https://docs.cloud.google.com/sql/docs/postgres/connect-connectors)
- [Google Search grounding](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-search)
- [Google Gen AI Python SDK reference](https://googleapis.github.io/python-genai/genai.html)
- [HighLevel Get Contact API](https://marketplace.gohighlevel.com/docs/ghl/contacts/get-contact/index.html)
- [HighLevel contact task schema](https://github.com/GoHighLevel/highlevel-api-docs/blob/main/apps/contacts.json)
