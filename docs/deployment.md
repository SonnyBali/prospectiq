# Deployment and release verification

The owner approved the dedicated ProspectIQ cloud release on October 8, 2026. Cloud Run and Cloud SQL are deployed in `ai-leadscore/us-central1` and their backend workflow was verified. Exact serving revision, traffic, immutable image and subsequent image publications are maintained in [live-release.md](live-release.md). **[The primary recruiter demo is live](https://prospect.firewireads.com/):** DNS/TLS, strict HTTPS health, Chrome dashboard/simulator/real OpenAI chat and Google/Facebook page-view network requests are verified. Account-side analytics receipt/reporting remains untested.

The dedicated `firewireads-platform` deployment is also Ready at [its native synthetic demo URL](https://prospectiq-504110803281.us-central1.run.app/), revision `prospectiq-00003-tdc`, 100% traffic. Its actual Cloud Tasks OIDC → Vertex Google Search → OpenAI → SQL cache flow completed and independently matched worker logs. The branded hostname/data have not migrated from `ai-leadscore`; target CRM link writes remain disabled. Live CRM delivery, outreach, bookings and live voice remain unverified. Public source and the initial remote CI run are verified; versioned files and per-commit CI pointers are in the release record.

## Isolated resources and current boundaries

| Resource | Use | Current checkpoint |
| --- | --- | --- |
| Cloud Run `prospectiq` | Public synthetic demo and capability-protected prospect/dashboard/admin API | Ready service; strict HTTPS health at the service URL returns SQL connected and OpenAI mode. Exact serving revision/traffic/image are in the release record |
| Authenticated research route | `/api/internal/research`, with OIDC identity validation | Actual target-project Tasks dispatch and completion verified; a separate `prospectiq-research` service remains an optional deployment layout |
| Cloud SQL PostgreSQL `prospectiq-db` | Dedicated durable tables with encrypted connector connections and backups | SQL Admin API enabled; PostgreSQL 16 `db-f1-micro` is `RUNNABLE`; database/user `prospectiq`, connector/schema and deployed persistence verified |
| Cloud Tasks research queue | Dedicated queue, bounded retry/backoff and dispatch concurrency | Target-project enqueue/OIDC/worker/Google/OpenAI/SQL chain passed; canonical-project dispatch not established by this test |
| Runtime/service identities | Dedicated runtime/task callers | Cloud SQL/named-secret access and target task caller's service-scoped invocation verified; actual OIDC worker request completed |
| Dedicated administrative/database secrets | Administrative capability and DB password | Provisioned through the Secret Manager SDK; values stay server-side and out of source/command arguments |
| Existing secret `OPENAI_API_KEY` | Server-side Responses credential, scoped Secret Accessor | Actual deployed OpenAI and scoped runtime secret access verified |
| Existing FireWire CRM secrets | Tenant/cohort contact reads and optionally internal review-task delivery | Reads verified; writes disabled/unverified |
| Optional separate-origin voice service | `app.voice:app`; native controls for a dedicated isolated widget | Adapter only; provider/audio unverified |
| Canonical hostname | `prospect.firewireads.com` mapped to the application root | DNS, managed TLS Ready/CertificateProvisioned, strict HTTPS health and actual Chrome dashboard/simulator/OpenAI chat verified; Google/Facebook page-view requests observed, account reporting untested |
| Cloud Logging | Request and provider-usage events collected from the deployed service | Matching deployed `request_processed` and `advisor_usage` events read directly |

The approved portfolio configuration uses Cloud Run one CPU, 1 GiB, concurrency four, minimum zero and maximum one instance. Cloud SQL uses PostgreSQL 16, shared-core `db-f1-micro`, zonal availability and 10 GB SSD, with backups and deletion protection. Cloud SQL has continuing instance/storage/backup costs even when Cloud Run has no traffic. Exact resource evidence and cost/availability context are in [live-release.md](live-release.md).

## Build and local container verification

With Docker's Linux engine running, execute these from the `prospectiq` application directory:

```powershell
docker build --tag prospectiq:local .
docker run --detach --name prospectiq-local-demo --publish 127.0.0.1:8093:8080 --env PUBLIC_ORIGIN=http://127.0.0.1:8093 --env OPENAI_SECRET_NAME= --env ADMIN_SECRET_NAME= --env ALLOW_CRM_FOLLOWUP=false --env ALLOW_CLOUD_TASKS=false prospectiq:local
.venv/Scripts/python.exe scripts/smoke_http.py --base-url http://127.0.0.1:8093
```

Earlier development check, October 8, 2026, with Docker Engine 29.2.1, Linux x86_64: the initial image built and `prospectiq-local-demo` served the guided synthetic dashboard at `http://127.0.0.1:8093`. The HTTP smoke passed 25 checks with zero provider calls; the then-current 85 pytest tests passed inside that image with the test directory mounted read-only. Runtime UID 10001, dependency consistency and loopback-only binding were verified. No host credentials were mounted. The current source/image passed 222 pytest tests on Windows/Linux, Ruff, JavaScript syntax, 38 private-entry VM cases and 346 analytics privacy assertions. Build verification is distinct from ready deployment traffic.

## Optional recruiter demo origin

`DEMO_ORIGIN` allows one exact HTTPS origin to host the built-in public synthetic fixture. It does not extend private capability access, administrative/research routes or CRM prospect sessions to that host. `PUBLIC_ORIGIN` remains the canonical origin for private access. Native demo responses are noindex, CSRF remains enforced, and marketing scripts remain blocked outside the canonical host. The additional origin-security tests cover these boundaries.

The [native recruiter backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) remains verified. On October 8, the serving deployment passed 25 native same-origin HTTP checks and Chrome verified real cited OpenAI chat, an edited Python scenario, session history and Engineering View. Native script inspection found only same-origin assets; marketing trackers remain blocked by design. Private prospect access still requires the canonical origin. Use [prospect.firewireads.com](https://prospect.firewireads.com/) as the primary link. Exact deployment and request evidence are in [live-release.md](live-release.md) and [verification.md](verification.md).

Cloud Run terminates HTTPS at its trusted ingress. The deployed runtime trusts forwarded scheme information with `FORWARDED_ALLOW_IPS='*'` so secure-origin checks see that HTTPS scheme. This setting applies to the managed Cloud Run ingress deployment; do not copy it to a directly exposed server with untrusted proxy headers.

The image excludes local databases, `.env`, tests/artifacts and credentials, uses Python 3.12, installs pinned dependencies and runs as a nonroot user. Build from this application directory. SQLite data is local to the development container and is lost on removal; the deployed application uses Cloud SQL. Use `docker stop prospectiq-local-demo` to stop it and `docker start prospectiq-local-demo` to resume an existing container; do not rerun the creation command while that name exists. Local container evidence and actual deployed connector/provider evidence are recorded separately.

## Configuration and subsequent research-worker setup

The v1.1 client-link/disclosure extension is deployed and verified: `/p?client=<nonsecret-id>#<secret-token>`, client-bound reloads and private root-query CSP/noindex/tracking isolation. The fragment never enters the initial ingress request URL. Two private dashboards passed 18 HTTP checks and Chrome cited-advisor checks with cached real public research/Google attribution. The dedicated HighLevel trigger target/project tags passed direct API readback; per-recipient redirect remains unverified and the click→30-minute human email/SMS workflow is saved as a draft. See [client-links.md](client-links.md) for the contract and sequence. Native communications remain separate from implementation-plan drafts and the internal review-task delivery gate. The serving project remains `ai-leadscore`; `firewireads-platform` preparation is not a completed migration.

Both projects' database/runtime/secret provisioning is verified. The dedicated project also has a completed task/worker research test. The following configuration outline is a reproduction guide, not an instruction to change either deployment or migrate existing data. Target `ALLOW_CLOUD_TASKS=true` and `ALLOW_CRM_LINKS=false`; preserve the CRM gate until canonical-domain/database migration is separately verified.

1. Enable only the approved required APIs: Cloud Run, Cloud Build/Artifact Registry if building remotely, Cloud Tasks, Cloud SQL Admin, Secret Manager, Vertex AI and Cloud Logging.
2. Provision a dedicated PostgreSQL instance/database/user and backup policy. Store its password in Secret Manager. Grant runtime `Cloud SQL Client` and access only to the required named secrets. Use VPC egress/private IP as appropriate; `PROSPECTIQ_SQL_PRIVATE_IP=true` selects connector private IP and still requires network connectivity.
3. Create dashboard/research service accounts and task caller. Grant the task caller `Cloud Run Invoker` on the private research service; grant only the enqueuing runtime identity task creation plus permission to act as that task service account. Cloud Run deployment identity/service agent permissions must also be verified. Vertex research requires appropriate Vertex permissions.
4. Choose the dashboard's final HTTPS origin. Cloud Run runtime rejects local SQLite and requires the Cloud SQL instance/password-secret configuration. `SECURE_COOKIES=true` and `PUBLIC_ORIGIN=https://...` must agree. Reconfigure after receiving the actual canonical service URL rather than minting temporary links.
5. Create the dedicated queue with modest dispatch/concurrency limits and retry backoff. The worker URL includes `/api/internal/research`; the OIDC audience is the canonical service origin. Worker application validation and private Cloud Run invoker IAM both apply.
6. Configure `OPENAI_SECRET_NAME`, `OPENAI_MODEL`, complete model-specific price/reference settings, `ADMIN_SECRET_NAME`, SQL settings and queue/worker settings. Keep `ALLOW_CRM_FOLLOWUP=false`. Set `ALLOW_CLOUD_TASKS=true` only after dispatch is approved. For the requested client-link handoff, verify the dedicated `contact.prospectiq_dashboard_url` field and native trigger link before configuring `GHL_DASHBOARD_URL_FIELD_ID`, `GHL_DASHBOARD_TRIGGER_LINK_ID` and enabling `ALLOW_CRM_LINKS`. Audit existing field-change automations. Use the exact FireWire tenant secret and the explicit `prospectiq-approved` cohort tag; the shared location also contains other brands' contacts.

A command outline for an approved container deployment is below. Substitute owner-reviewed values; do not execute placeholder commands or reuse production Sales OS service names:

```powershell
# Main service outline; substitute reviewed values, never credential values.
gcloud run deploy prospectiq --project APPROVED_PROJECT --region APPROVED_REGION --image APPROVED_IMAGE --service-account APPROVED_RUNTIME_IDENTITY --allow-unauthenticated --cpu 1 --memory 1Gi --max-instances 1 --concurrency 4 --timeout 300 --set-env-vars APPROVED_NON_SECRET_CONFIGURATION
# Optional separate private worker layout; the verified target currently uses its authenticated research route.
gcloud run deploy prospectiq-research --project APPROVED_PROJECT --region APPROVED_REGION --image APPROVED_IMAGE --service-account APPROVED_RESEARCH_IDENTITY --no-allow-unauthenticated --max-instances 1 --concurrency 1 --timeout 300 --set-env-vars APPROVED_NON_SECRET_CONFIGURATION
```

Secret values are not environment arguments here. `SecretStore` fetches values by configured names with runtime IAM. Never paste passwords/API keys into URLs, build arguments, command history, source, CI secrets output or the public UI. The worker route rejects unverified OIDC identity. Configure the exact approved worker route, caller and audience; a separate private service additionally requires its own invocation IAM.

The same image/SQL schema can support both services. Startup schema creation and demo seeding were verified against PostgreSQL and use advisory locks. The application uses `Base.metadata.create_all` for a new database; it does not migrate existing tables. Future schema changes need reviewed versioned migrations and backup/rollback procedures. Existing development SQLite files from earlier revisions need an explicit schema update or a fresh test database.

## Remaining release and integration verification

Canonical and native same-origin backend checks each passed 25 checks with real synthetic OpenAI, SQL-backed history/drafts/isolation and exact Cloud Logging readback. Both URLs passed actual Chrome chat, simulator, history and Engineering View checks. The primary canonical URL passed strict HTTPS health, with Google/Facebook page-view requests observed. Service-URL static/SEO/private-noindex/CSP checks are verified. Exact revision/image and request usage are maintained in [live-release.md](live-release.md) and [verification.md](verification.md).

- Verify ready revisions, serving traffic, canonical URLs and database connection using deployed health and direct resource readback.
- Verify account-side analytics receipt/reporting separately from the observed browser page-view requests; do not treat synthetic demo activity as a lead or booking conversion.
- Use a synthetic or owner-approved test CRM cohort. Dispatch one approved task, confirm its OIDC identity, wait for `complete`, inspect stored source/attribution and intelligence, and verify cached retries do not regenerate. Check Cloud Logging events without exposing bodies or tokens.
- Exchange a private test capability link; check company personalization, no model call on initial load, expiry, revocation and isolation from the public demo.
- Keep follow-up delivery disabled until a specific internal-task write is authorized. Then verify direct task readback and confirm no outreach/enrollment occurred.
- Use a dedicated provider sandbox/demo-only voice agent. Remove workflow/notification/booking/payment side effects. Enable a separate-origin adapter only after browser load/audio/start/end/unsupported-response and post-call readback checks establish isolation. Until then show the recording and disabled live choices.
- Record exact deployment/verification evidence and remaining limits. Roll back to the prior verified revision on failure; do not mark queued/partial requests as delivered.

## Optional browser voice adapter

The native embed protocol is reused from FireWire's inspected controller, rather than loading its production widget bundle. Serve `app.voice:app` separately with **only** an audited nonproduction widget and its allowed parent origin. This service uses no database, CRM credentials or Secret Manager.

```powershell
# Only after a dedicated demo widget is authorized and its side effects audited.
$env:DEMO_VOICE_WIDGET_ID='APPROVED_DEMO_PUBLIC_WIDGET_ID'
$env:DEMO_VOICE_ISOLATED='true'
$env:VOICE_ALLOWED_PARENT_ORIGIN='http://127.0.0.1:8091'
.venv/Scripts/python.exe -m uvicorn app.voice:app --host 127.0.0.1 --port 8092 --no-access-log
```

Configure the main server with the matching widget ID/isolated flag and `DEMO_VOICE_BROWSER_ORIGIN=http://127.0.0.1:8092`. In deployment, use a distinct HTTPS origin. The frontend validates that the voice iframe is on a different origin, delegates microphone access only to it and requires an explicit launch click. A second click loads native provider controls. No real widget was activated during development, so audio remains unverified.

## GitHub readiness

The public [repository](https://github.com/SonnyBali/prospectiq) is anonymously accessible at initial commit `d731821b25859e2ee2be1d5830fefe5cb64e970b`; [initial CI 37796011001 passed](https://github.com/SonnyBali/prospectiq/actions/runs/37796011001). The workflow tests Python/JavaScript, builds Docker and runs a credential-free loopback container smoke. Cleanup removes only the named CI container; it has no cloud credentials or deploy step. The 74-file publication privacy audit found no source/target secret or private-artifact matches. Consult [Actions](https://github.com/SonnyBali/prospectiq/actions) for the final fix commit and [Releases](https://github.com/SonnyBali/prospectiq/releases) for version-tag publication; initial CI does not prove a subsequent commit passed.
