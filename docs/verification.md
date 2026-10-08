# Verification record

October 8, 2026 (Asia/Singapore). The initial local/read-only checks were followed by an owner-approved Cloud Run and Cloud SQL release. This document preserves both stages; [live-release.md](live-release.md) is the current release checkpoint. No live task dispatch, CRM task delivery, customer outreach, live voice call, booking, GitHub push, or remote CI run has been performed.

## Version 1.1 source and release preparation

| Check | Current evidence |
| --- | --- |
| Full source/image suite | 212 pytest tests passed on Windows and in the rebuilt Linux image; Linux run completed in 17.24 seconds |
| Private entry/disclosure | 38 offline frontend VM cases and JavaScript syntax passed; query identifies the prospect, secret fragment authorizes access, and client mismatch/retry/tracking guards are exercised |
| Analytics privacy | 346 offline assertions passed; no provider SDKs were fetched by this test |
| Recruiter catalogue | Four reviewed recruiter/research hypotheses; focused advisor/security suite passed 40 tests and Ruff. Prompt and acceptance use the same catalogue; relevant cited excerpts are required |
| Docker/image/deployment | Rebuilt `v1.1.0-release` image passed Linux tests and was published immutably. Revision `prospectiq-00006-ksp` became Ready at `2026-10-08T14:43:29Z`, 100% traffic, in `ai-leadscore/us-central1`. Exact digest is in the release record |
| Canonical v1.1 smoke/logging | 25 HTTP checks passed with actual synthetic OpenAI request `e5b6b07d9113434aa233e8299c4cc952`: 1,659 input / 247 output tokens, estimated $0.0010588. Python scenario remained $10,800 monthly/$129,600 annual/nine expected customers; history/traces/cookie/privacy/logout passed. Independent Cloud Logging matched completed OpenAI usage and HTTP 200, 3,418.88 ms, revision `prospectiq-00006-ksp`, event timestamp `2026-10-08T14:44:12.617159Z` |
| Private dashboard HTTP checks | Two private dashboards passed 18 HTTP checks. The check observed 14 retained real public sources and saved Google attribution, client-ID/cookie binding, wrong-ID rejection, query-only unauthorized access and strict private CSP/tracking isolation. No private client details or capabilities are reproduced |
| Private Chrome advisor | Actual OpenAI response returned cited recruiter-briefing/candidate-scheduling hypotheses; 4,316 input / 513 output tokens, displayed cost estimate $0.002547. This is dashboard evidence, not an automated hiring decision or delivered CRM workflow |
| API version | Strict canonical HTTPS OpenAPI returned HTTP 200, `info.version=1.1.0`, verified at the 14:49 UTC checkpoint |
| Publication privacy audit | 70 candidate files passed comparison against four actual Secret Manager values and five private-artifact fingerprints, zero findings. Secret values and private artifacts are not published |
| HighLevel configuration | Dedicated native global trigger link points to the exact contact-field target; four project tags passed direct API readback HTTP 200. Tags not assigned to contacts by this verification; per-recipient redirect unverified |
| Timed follow-up | Requested native 30-minute email/SMS workflow is saved as a draft, not operational; no delivered follow-up claim |
| GitHub v1.1 publication | Public [SonnyBali/prospectiq](https://github.com/SonnyBali/prospectiq) repository created; source push/tag and remote CI results remain unverified |
| Google project preparation | Current verified service remains in `ai-leadscore/us-central1`; `firewireads-platform` preparation is underway. Source/image success does not establish migration |

These source checks do not replace deployed workflow evidence. The current release checklist is in [RELEASE_NOTES_v1.1.md](../RELEASE_NOTES_v1.1.md); the exact last verified serving revision remains in [live-release.md](live-release.md).

## Approved serving release before v1.1

| Check | Result and evidence |
| --- | --- |
| Serving revision | Ready Cloud Run service in `ai-leadscore/us-central1`; exact current revision, traffic and immutable image are maintained in [live-release.md](live-release.md). Image-build/publication success is tracked separately from deployment readiness |
| Recorded source/image checks | The earlier serving release passed 123 pytest tests on Windows/Linux, including 28 origin-security tests, Ruff, JavaScript syntax and 298 analytics assertions. The current v1.1 source checkpoint is recorded separately above |
| Strict HTTPS service health | The Cloud Run endpoint returned HTTP 200 with database connected and advisor mode OpenAI |
| Cloud SQL | SQL Admin API enabled; dedicated PostgreSQL 16 `prospectiq-db`, `db-f1-micro`, is `RUNNABLE`; database/user `prospectiq`, actual Python connector/schema and deployed chat/history/draft persistence verified |
| Runtime and secrets | Dedicated service identity with Cloud SQL Client and access scoped to named secrets; deployed Secret Manager/OpenAI/SQL use verified without exposing values |
| Primary recruiter URL | [Canonical public synthetic demo](https://prospect.firewireads.com/), actual Chrome dashboard/simulator/real OpenAI chat verified, no console errors or warnings. [Native backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) remains verified, synthetic-only and noindex, with same-origin CSRF and no marketing trackers |
| Canonical Chrome simulator/chat | Leads 300→400 returned Python $10,800 monthly/$129,600 annual/$10,303 monthly revenue less AI cost. Actual OpenAI request `cb51f002eba24c19a4ce1faff11daef0` returned E2/E3 citations and 1,167 input / 275 output tokens. Independent Cloud Logging read at `2026-10-08T13:58:05Z` recorded estimate $0.0009068; UI rounds to $0.000907 |
| Canonical Chrome history/engineering | Two SQL-backed messages loaded through history. Engineering View showed chat HTTP 200 in 3,328.73 ms with matching usage, simulator HTTP 200 in 16.21 ms and history HTTP 200 in 21.98 ms |
| Canonical same-origin backend smoke | 25 checks passed at `https://prospect.firewireads.com`, `same_origin=true`. Request `c3c1cbcd99f5462099572e1469ba551a` used 1,168 input / 310 output / zero cached tokens, estimate $0.0009632. Independent Cloud Logging at `2026-10-08T14:01:23Z` matched completed `advisor_usage` and `request_processed`, HTTP 200, revision `prospectiq-00005-t7w` |
| Native same-origin backend smoke | Ready revision `prospectiq-00005-t7w` passed 25 HTTP checks at that native origin, including real synthetic OpenAI and SQL-backed history, drafts, session isolation and traces |
| Native backend OpenAI usage | Request `4dfe9e7cc28b41b9ad3d4ab6aaf4341d`: 1,168 input / 262 output tokens, estimated $0.0008864; configured-rate estimate, not an invoice |
| Cloud Logging ingestion | Matching request/usage events for that exact native smoke request were independently read on revision `prospectiq-00005-t7w` at `2026-10-08T13:51:07Z` |
| Native Chrome simulator | Monthly leads 300→400 produced $10,800 monthly opportunity, $129,600 annual opportunity, nine expected customers and $10,303 monthly revenue less AI cost, all returned by Python |
| Native Chrome OpenAI/history/engineering | Request `526a9d5621224312a29fcb1f0357f338`: 1,167 input / 316 output tokens, estimated $0.0009724, independently read in Cloud Logging at `2026-10-08T13:51:27Z`. Response cited E2/E3 and showed the exact submitted scenario. Session history and Engineering View showed HTTP 200 in 4,038.13 ms with actual usage |
| Native Chrome recorded voice | Recording CTA opened the existing MP4 player, `readyState=4`, duration 533.757 seconds, no media error, paused. No live voice/microphone/call; earlier local evidence separately establishes recorded playback advancing |
| Native Chrome scripts/console | No console errors or warnings; script DOM contained only same-origin scripts. Third-party marketing loading is intentionally blocked at the native URL; this is not canonical marketing-ingestion evidence |
| Subsequent deployed request | `/api/demo` request `094262d62ac049229113b66fc61af1e1`, HTTP 200, independently verified in Cloud Logging on the second revision. This is dated backend evidence, not a final-host browser check |
| Canonical hostname | Correct `prospect` CNAME and public DNS resolution verified. Mapping Ready/CertificateProvisioned became true at `2026-10-08T13:48:42Z`. Strict HTTPS `/health` returned HTTP 200 with SQL connected and OpenAI mode; actual Chrome dashboard/simulator/OpenAI chat verified |
| Marketing and share assets | Service URL returned HTTP 200 for marketing statics, 1200×630 share PNG, 32px favicon, 180px Apple icon, SVG, robots and sitemap; private `/p` noindex and strict CSP were checked. Canonical Chrome observed Google Analytics `G-6JM91XZMX2` and Ads `AW-17005023254` loaders and page-view collect requests, plus Meta pixel `502483969150258` loader/config and `PageView` requests. Account-side receipt/reporting is untested; no synthetic lead or booking conversion |
| Remaining release gaps | Dedicated Cloud Tasks dispatch, live CRM internal-task delivery, isolated voice audio and GitHub CI remain disabled or untested. The full CRM→queued research→dashboard→review chain is verified offline, not end-to-end live |

## Earlier local, provider and release checks

The following table preserves earlier development/provider checks and the initial deployed smoke on October 8. The API-disabled/no-deployment observations concern the pre-release audit and are superseded by the approved deployment checkpoint above.

| Check | Result and evidence |
| --- | --- |
| Earlier pytest | 85 tests passed at this earlier check, including simulator boundaries, real SDK shape through mock transport, complete offline pipeline, session/CSRF/revocation/privacy, parallel/shared quotas, DND, tenant/source identity, safe provider errors, worker races and approval gates; subsequent serving-release and v1.1 totals are recorded separately above |
| Ruff | Passed for app/tests/scripts |
| JavaScript | `node --check` passed for dashboard and isolated voice adapter |
| Dependency consistency | `pip check` passed; installed versions pinned in `requirements.lock` |
| Full real OpenAI advisor smoke | Passed with synthetic fixture, official SDK, Secret Manager, Responses `store=False`, model `gpt-4.1-mini`; cited recommendations, unsupported-profit/competitor abstention, history, unchanged simulator and session-scoped traces verified |
| Advisor smoke usage | Two requests: 1,154 input / 323 output tokens, estimated $0.0009784; 964 input / 43 output tokens, estimated $0.0004544. Estimates use verified model-specific rates, not an invoice |
| Browser OpenAI chat | Actual local requests `4d94eec57629465fb4c2d70a6401409c` and `b5d022f7c540499aa95bc51a08d2fb32` returned citations/provider usage. The latter used 1,252 input / 258 output, estimated $0.000914 |
| Browser simulator | Leads 300→500 produced $13,500 monthly/$162,000 annual/11.25 expected customers in guided mode; 300→400 produced $10,800/$129,600/nine in real OpenAI mode. Chat's submitted scenario snapshot uses returned Python results |
| Browser history/engineering/draft | Session-scoped chat/history, actual trace readback and a draft-only implementation request passed. No CRM write/outreach occurred |
| Responsive/render | Chrome desktop and effective 300px CSS mobile viewport passed with no horizontal overflow; mobile advisor shortcut worked; console checks found no errors. See frontend-verification.md |
| Recorded voice playback | Existing public HVAC MP4 loaded (readyState 4, duration 533.757s, 720×1280), played forward and paused. No microphone/call/workflow was started |
| Secret Manager | Official SDK safely accessed three existing named secrets; no values printed or placed in source/browser |
| HighLevel | Direct tenant-bound contact read succeeded; aggregate field-presence output only. Seven existing agent configurations and three public widget linkages were inspected. No writes |
| Vertex research | Official Google SDK returned seven grounded public FireWireAds sources and Search Suggestions attribution; no CRM data sent |
| Earlier Cloud Run/Tasks/Logging audit | Existing resource health/metadata/log read succeeded before ProspectIQ deployment. These initial reads did not establish the new chain; actual ProspectIQ deployment/logging evidence is recorded above |
| Earlier Cloud SQL audit | SQL Admin API was disabled at the initial read-only audit. It was subsequently enabled and the dedicated connector/schema/persistence verified during the approved release |
| Cloud Tasks dispatch | OIDC/task shape and orchestration are tested offline. Dedicated live queue creation/dispatch remain untested |
| Live isolated browser/call voice | Adapter/configuration guards tested offline. Dedicated demo provider/audio/lifecycle/side effects remain untested and disabled |
| Live CRM internal task | Tenant/suppression/create/readback code tested with fakes; no provider mutation invoked |
| Earlier Docker image/runtime | Built `prospectiq:local` with Docker Engine 29.2.1, Linux x86_64. Container `prospectiq-local-demo` was bound only to `127.0.0.1:8093`; UID 10001 and `pip check` passed, no credentials/mounts supplied |
| Docker HTTP workflow | `scripts/smoke_http.py` passed 25 HTTP checks: health/SQLite, dashboard/assets, synthetic session, CSRF/origin, default and edited simulator, guided chat/citations/history/request trace, cross-session privacy, local draft and logout. Zero provider calls |
| Earlier Linux image pytest | 85 tests passed inside the initial local image with the test directory mounted read-only. The later serving image passed 123; v1.1 Linux results are tracked separately above |
| Third-revision backend smoke | Revision `prospectiq-00003-6w7` passed 25 HTTP checks with the canonical Origin header supplied at the service address. Request `ccfaeea91ba34a3d9505cead9252739a` used 1,168 input / 301 output tokens, estimated $0.0009488; matching Cloud Logging events were independently read at `2026-10-08T13:31:44Z`. This precedes the native-origin verification above |
| Initial deployed backend smoke | Earlier release passed 25 HTTP checks; synthetic OpenAI request `23a52a4c9d4d4235a9232d61cfc51e4b` used 1,168 input / 234 output tokens, estimated $0.0008416, with matching Cloud Logging events. This is historical deployed evidence, superseded by the native-origin smoke above |
| GitHub CI | Workflow includes lint/tests/JavaScript, image build and credential-free loopback container smoke with named-container cleanup. No GitHub run or publication performed |

The Python environment emitted one upstream Starlette TestClient deprecation warning for its HTTPX backend; all behavior tests passed. This is a future test-dependency migration issue, not a failed runtime check.

For reproduction, run the README commands. `scripts/smoke_live_advisor.py` is an explicit paid synthetic-only test; resource inventory reports statuses individually and does not provision/dispatch/send. Browser evidence is detailed in [frontend-verification.md](frontend-verification.md); source/voice/cloud boundaries are detailed in the inventories. Local, deployed backend, and final-host browser results are distinct evidence. The latest hostname/certificate/revision checkpoint is in [live-release.md](live-release.md).
