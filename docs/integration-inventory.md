# Integration inventory

Inspection preceded implementation on October 8, 2026. The user confirmed this is a new application. There was no existing ProspectIQ repository; the application is isolated in this directory.

The owner subsequently approved a dedicated cloud release. The main Cloud Run service is ready; dedicated Cloud SQL PostgreSQL persistence and deployed Cloud Logging events are verified. Latest source/built-image checks passed 123 pytest tests on Windows and Linux. The [primary recruiter demo](https://prospect.firewireads.com/) passed strict HTTPS health and actual Chrome dashboard/simulator/cited OpenAI chat/history/Engineering checks. Google/Meta page-view requests were observed; account-side reporting is untested. The [native backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) remains verified and runs no marketing trackers. See [live-release.md](live-release.md) for the exact current revision/image and release evidence.

| Existing asset | What was established | Reuse or build decision |
| --- | --- | --- |
| FireWire Sales OS Python client | Existing tenant validation, Secret Manager credentials, bounded HighLevel backoff and private dashboard health were inspected/read live | Reused the safety patterns in a new provider module; existing scoring code was not edited |
| Opportunity Audit frontend template | Existing brand, audit/calendar flow and shared voice launcher were inspected | New API-backed dashboard built for personalization, simulator, research evidence, session chat and Engineering View |
| Shared canonical voice widgets | Three live browser configurations and seven agent configurations were inspected | Reuse public embed protocol in a separate-origin adapter. Production IDs are explicitly blocked; all live launch remains disabled by default |
| Public HVAC receptionist walkthrough | Video loaded and advanced in Chrome, with no call/microphone or business action | Immediately usable recorded demonstration, clearly distinguished from the synthetic company and live audio |
| Google Cloud project `ai-leadscore` | Initial secret/resource reads and Vertex grounding worked; the approved release subsequently verified dedicated Run/SQL/runtime identity, named-secret use and deployed request/usage logging | Main public demo backend deployed; dedicated live research queue/worker dispatch remains disabled and untested |
| OpenAI secret | Official Responses call and complete synthetic advisor workflow passed | New configurable typed SDK adapter; server-only secret access, cited extractive observations, history, quotas and accounting |

Credential names verified during the initial inspection: `OPENAI_API_KEY`, `FIREWIRE_GHL_API_KEY`, `FIREWIRE_GHL_LOCATION_ID`. Vertex uses Google IAM. Dedicated administrative/database secrets were subsequently provisioned through the Secret Manager SDK, with values kept out of the committed application, command arguments and verification output. The deployed identity receives access scoped to named secrets; administrative and live CRM actions remain separately gated.

Built: FastAPI, SQLAlchemy persistence, synthetic fixture, cached research import, tenant/cohort CRM import, OIDC worker orchestration, secure access, OpenAI advisor, calculator, responsive dashboard, request traces, draft follow-up, server-only internal-task delivery adapter, separate-origin voice adapter, tests, Docker, CI and interview/deployment documentation. The approved public backend now runs with PostgreSQL; implemented adapters are not automatically treated as live integrations.

Earlier local Docker verification succeeded: image build, localhost guided dashboard, 25 HTTP checks with zero provider calls, 85 then-current offline pytest tests in Linux, runtime UID 10001 and dependency consistency. No credentials were mounted in that local check. The latest built image/source passed 123 pytest tests; canonical and native same-origin backend checks each passed 25 checks with actual OpenAI, SQL persistence and independently matched request/usage events in Cloud Logging. Asset/SEO/CSP checks passed. Actual canonical Google/Meta page-view network requests were observed; account-side receipt/reporting is separate and untested.

Operational gaps remain explicit: account-side analytics receipt/reporting; dedicated live queue/worker dispatch; demo-isolated voice audio; live CRM task creation; and GitHub publication/CI. The complete CRM→research→dashboard→review workflow passes **offline with mocked providers**; the public deployed synthetic workflow does not establish an end-to-end live CRM/research/task chain.

Detailed evidence: [cloud-inventory.md](cloud-inventory.md) and [voice-inventory.md](voice-inventory.md).
