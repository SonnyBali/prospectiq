# ProspectIQ · FireWireAds AI Opportunity Intelligence

A personalized Python AI application for business opportunity research: HighLevel → FastAPI → Google Vertex research → OpenAI Responses → secure dashboard → isolated Voice AI → operator-reviewed HighLevel follow-up.

This is an isolated application alongside the existing FireWire Sales OS, website, voice agents, and CRM workflows. **The owner-approved Cloud Run application is deployed with Cloud SQL persistence at https://prospect.firewireads.com.** Managed TLS, strict HTTPS health, actual Chrome dashboard/simulator/OpenAI chat, and Google/Facebook page-view network requests are verified. Analytics account-side receipt/reporting is untested. Source is published in the public [SonnyBali/prospectiq repository](https://github.com/SonnyBali/prospectiq); its initial [GitHub CI run passed](https://github.com/SonnyBali/prospectiq/actions/runs/37796011001). See [live-release.md](docs/live-release.md) for current deployment, source and version-tag checkpoints.

**[Open the verified recruiter demo](https://prospect.firewireads.com/).** Try the fictional Copperline company dashboard, real OpenAI chat, Python revenue simulator and actual session request traces. The receptionist demonstration is a recording; live agents remain disabled. Follow the [three-minute interview walkthrough](docs/interview-guide.md). The [verified native backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) accepts only the built-in public synthetic session and runs no marketing trackers.

## Small complete version

- Synthetic recruiter dashboard with interactive chat, evidence citations, company intelligence, a revenue simulator, and an Engineering View of actual session requests.
- Official OpenAI Python SDK, configurable Responses model, Pydantic Structured Outputs, stored conversation history, token accounting and configured-rate cost estimates. `store=False`; API keys are read server-side from Secret Manager.
- Extractive factual observations and a constrained solution catalogue, including recruiter briefing, scheduling and communication review. A citation ID alone cannot validate a statement. Complete stored excerpts preserve context; recommendations use reviewed server templates and are labeled hypotheses. Recruiting questions receive a direct reviewed workflow proposal without unrelated revenue figures.
- A pure Python/Decimal simulator calculates authoritative outcomes. The advisor receives its results and the API adds an exact numerical explanation. AI cannot modify calculator outputs.
- Secure private dashboards for imported completed research or tenant/cohort-approved CRM profiles: expiring hashed access links, HTTP-only cookies, CSRF, revocation, session isolation and shared/per-session AI call budgets.
- Vertex Search-grounded research adapter, Cloud Tasks OIDC worker with retry lease and cached completion, Cloud SQL PostgreSQL connector, durable usage/review records and JSON Cloud Logging events.
- Recorded FireWire receptionist walkthrough. Agent/scenario selection, a separate-origin browser voice adapter using the existing public LeadConnector embed protocol, and a call-based configuration path. Live provider interaction stays disabled until an isolated demo is audited and tested.
- SQL-backed draft implementation requests; a separate administrative approval gate exists for an internal HighLevel review task. Live CRM delivery, customer outreach, calendar booking, campaign enrollment, and live voice interactions remain disabled for this release.
- Public canonical/OG/Twitter metadata, locally served share image and favicons, and privacy-gated FireWireAds marketing identifiers. Actual canonical-host Google/Facebook page-view requests were observed. Account-side reporting is untested; no synthetic lead or booking conversion was emitted.

## Run locally

Python 3.12 is the verified development version. Use Python 3.11+ with an isolated environment:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock
.venv/Scripts/python.exe -m pip install --no-deps -e .
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --no-access-log
```

Open `http://127.0.0.1:8090`. Without cloud configuration, chat is explicitly labeled **Guided demo**, a scripted evidence preview. The simulator and stored synthetic dashboard work without credentials. It is never labeled OpenAI output.

For real interactive OpenAI, authenticate Google locally, then set **secret names**, model and public origin. Do not paste API keys into `.env`, source, browser storage, or commands:

```powershell
$env:GOOGLE_CLOUD_PROJECT='ai-leadscore'
$env:OPENAI_SECRET_NAME='OPENAI_API_KEY'
$env:OPENAI_MODEL='gpt-4.1-mini'
# For this existing developer account when ADC is unavailable:
$env:PROSPECTIQ_ALLOW_GCLOUD_FALLBACK='true'
$env:PUBLIC_ORIGIN='http://127.0.0.1:8090'
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --no-access-log
```

Application Default Credentials are preferred; the explicit gcloud fallback is local-only and disabled on Cloud Run. Copy the optional verified model pricing settings from `.env.example` to enable estimated cost. Without complete configured pricing, costs are `null`, never invented. Rate changes require updating the configuration/reference.

New private links use `/p?client=<opaque-prospect-id>#<secret-token>`: the query identifies the company without authorizing access, while the fragment capability is exchanged through POST and removed before DOM/API work. Reloads require a cookie session for the same client. Legacy `/p#<token>` links remain supported. Two private dashboards passed 18 HTTP checks and actual Chrome cited-advisor checks, using retained public-source research and Google attribution. The dedicated HighLevel trigger target/project tags were verified by API; per-recipient redirect remains unverified and the 30-minute follow-up workflow is a saved draft. See [client-links.md](docs/client-links.md). The default prospect link lifetime is 72 hours and session lifetime is eight hours. Administrative access is disabled unless `ADMIN_SECRET_NAME` is set. Public demo data is always synthetic; private contact fields never appear in Engineering View.

## Verification and limits

See [verification.md](docs/verification.md) for dated local and deployed readbacks. The ready Cloud Run service serves traffic in `ai-leadscore/us-central1`; the exact current revision and immutable image are maintained in [live-release.md](docs/live-release.md). Dedicated PostgreSQL 16 instance `prospectiq-db` is `RUNNABLE`; the connector, schema, chat/history/draft persistence, scoped Secret Manager access, and deployed request/usage events in Cloud Logging were verified. Strict HTTPS `/health` at the Cloud Run endpoint returned database connected and advisor mode OpenAI.

The **v1.1 source passed 222 pytest tests on Windows and in the rebuilt Linux image**, 38 offline private-entry/disclosure VM cases and 346 analytics privacy assertions. Ruff passed. The canonical service is Ready on `prospectiq-00007-n2g` with 100% traffic. Its corrected Google attribution frame displayed eight Search suggestion links in Chrome with no console errors or warnings; a recruiting question returned a direct cited Python/FastAPI proposal without unrelated revenue figures. The post-fix canonical smoke passed 25 HTTP checks, and two private dashboards passed 18 checks. Canonical OpenAPI returned version `1.1.0`. Public source and the initial CI run are verified. [v1.1.0](https://github.com/SonnyBali/prospectiq/releases/tag/v1.1.0) provides versioned files; [Actions](https://github.com/SonnyBali/prospectiq/actions) shows the result for each source commit. See [v1.1 release notes](RELEASE_NOTES_v1.1.md) and [live-release.md](docs/live-release.md) for exact evidence and image digest.

Earlier serving-release evidence includes 123 tests on Windows/Linux and 298 analytics assertions, canonical/native 25-check workflows, SQL-backed history/drafts and Chrome simulator/chat/Engineering checks. Current totals are above. Actual HighLevel recipient redirect/timed delivery, isolated live voice audio and account-side analytics reporting remain unverified.

The canonical hostname still serves `ai-leadscore/us-central1`. A separate deployment in `firewireads-platform` is Ready at [its native public synthetic demo URL](https://prospectiq-504110803281.us-central1.run.app/), with its own PostgreSQL database, scoped runtime identity and server-side secrets. Its actual Cloud Tasks OIDC → Vertex Google Search → OpenAI → Cloud SQL cache flow completed with eight sources and Google attribution; matching worker request/usage events were independently read from Cloud Logging. The test had no CRM contact, issued no access link and sent no outreach. Target CRM link writes stay disabled until domain/data migration; the canonical service is unchanged. Exact resource and publication checkpoints are in [live-release.md](docs/live-release.md).

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/voice.js
node --check app/static/analytics.js
node scripts/test_private_entry.mjs
node scripts/test_analytics.mjs
# Explicit paid, synthetic-only complete advisor check:
.venv/Scripts/python.exe scripts/smoke_live_advisor.py
# Read-only resource/credential inventory; no tasks or CRM writes:
.venv/Scripts/python.exe scripts/verify_integrations.py --allow-gcloud-fallback
```

## Run with Docker

From this application directory, with Docker's Linux engine running:

```powershell
docker build --tag prospectiq:local .
docker run --detach --name prospectiq-local-demo --publish 127.0.0.1:8093:8080 --env PUBLIC_ORIGIN=http://127.0.0.1:8093 --env OPENAI_SECRET_NAME= --env ADMIN_SECRET_NAME= --env ALLOW_CRM_FOLLOWUP=false --env ALLOW_CLOUD_TASKS=false prospectiq:local
.venv/Scripts/python.exe scripts/smoke_http.py --base-url http://127.0.0.1:8093
```

Open `http://127.0.0.1:8093`. With these local flags, the container runs as user 10001 with synthetic data and **Guided demo** chat. No host credentials are mounted. `smoke_http.py` refuses provider-backed chat and checks the simulator, history, citations, session privacy, CSRF, draft-only requests and actual HTTP traces. The local SQLite database lives inside this development container and is lost if the container is removed; the deployed service uses Cloud SQL instead. If the named container already exists, resume it with `docker start prospectiq-local-demo`; stop it with `docker stop prospectiq-local-demo`.

## Code and interview map

| File | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI orchestration, session/admin authorization, cached dashboards, research state, usage budgets and follow-up gates |
| `app/simulator.py` | Pure deterministic Decimal arithmetic; no AI/network dependencies |
| `app/schemas.py` | Input validation and typed Structured Outputs contracts |
| `app/advisor.py` | Official Responses SDK, conversation context, extractive grounding, abstention and token/cost accounting |
| `app/db.py` | SQLAlchemy models; local SQLite and Cloud SQL PostgreSQL lifecycle |
| `app/integrations.py` | Secret Manager, tenant-bound HighLevel, Google research, authenticated Cloud Tasks and Cloud SQL connector |
| `app/voice.py` | Optional separate-origin native voice adapter; no private APIs, credentials, or database |
| `app/static/` | Responsive dashboard; JavaScript presents Python outputs and uses no provider credentials |
| `tests/` | Offline functional, SDK-shape, concurrency, safety and complete-pipeline regressions |

Read [architecture.md](docs/architecture.md), [interview-guide.md](docs/interview-guide.md), [client-links.md](docs/client-links.md), [integration-inventory.md](docs/integration-inventory.md), [deployment.md](docs/deployment.md), and the current [release record](docs/live-release.md). The repository includes Docker and GitHub Actions verification. The approved cloud release is recorded separately; CI has no deployment step.

Official references: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [model support](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [model pricing](https://developers.openai.com/api/docs/pricing). Google/HighLevel references are linked in the integration inventories.
