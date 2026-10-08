# Live release record

October 8, 2026 (Asia/Singapore). The owner-approved public recruiter demo is now live at [prospect.firewireads.com](https://prospect.firewireads.com): valid HTTPS, synthetic dashboard, real cited OpenAI chat, Python simulator, history and Engineering View were verified in Chrome. The canonical same-origin HTTP smoke passed 25 checks, with matching events independently read from Cloud Logging. [The temporary Cloud Run URL](https://prospectiq-s4gztnjt6a-uc.a.run.app) remains a verified fallback.

## October 9 customer-chat update: live verified

The update replaces the customer conversation's raw research quote blocks, warning/limits panels, E-number citation markers and token/request clutter with short, plain-English replies. The server still validates complete factual excerpts and reviewed recommendations, returns API citations, records usage and exposes actual processing in Engineering View. Exact simulator figures appear when the user asks about their calculated scenario; generic questions about a company's actual revenue do not automatically append those figures. New conversation records store the displayed reply. Legacy server-generated transcripts read back without the old recommendation appendix, preserving stored calculation values.

Verified preparation: 229 pytest tests on Windows in 14.26 seconds; Ruff; 38 private-entry and 12 chat-renderer cases; 346 analytics assertions; and 25 HTTP checks against a fresh credential-free Docker container, with zero provider calls. Deployed image Linux manifest: `sha256:f89527adc50760d95c9ff479238fab8bb616202799b0645f582cbaffa1adb655`; image index: `sha256:317daddc56b56701fb14af54c96a1e17be4569633b8793e811098352167780af`.

Both image-only deployments succeeded. Independent service readback confirms Ready canonical revision `prospectiq-00008-j6t` in `ai-leadscore/us-central1` and Ready staging revision `prospectiq-00004-25b` in `firewireads-platform/us-central1`, each receiving 100% traffic on that same manifest.

Each service passed exactly 25 live HTTP checks and one paid synthetic OpenAI chat. The checks verified a concise `plain_reply` identical to `answer.summary`, under 100 words and without warning/E-number boilerplate, exact unchanged Python results, identical persisted history, API citations, measured usage, session privacy and logout. Canonical request `353bc523fc4e4f349d23fae38f278f50` recorded 1,700 input / 400 output tokens, server estimate `$0.00132`. Staging request `4786e8b2284d4387a01f1c8f9447f601` recorded 1,700 input / 381 output tokens, estimate `$0.0012896`. Independent Cloud Logging matched completed OpenAI usage and HTTP 200 on the respective current revisions.

Actual Chrome on the canonical hostname displayed “An AI receptionist could take messages after hours and pass requests to your team.” without chips, raw quote blocks, cautions or cost/request details. The canonical History button read back both a legacy reply and the new short reply with the concise sentence and no old recommendation appendix. Two cached private dashboards passed 18 HTTP checks, with no provider calls or outreach. The latest working-tree publication scan checked 74 files against four actual source-project secret values and seven private-artifact fingerprints, with zero findings. A separate comparison of the same 74 upload candidates against four actual target-project Secret Manager values also passed with zero findings.

The customer-chat source is available on [main](https://github.com/SonnyBali/prospectiq/tree/main). The original `v1.1.0` tag remains immutable. [Actions](https://github.com/SonnyBali/prospectiq/actions) records CI against each exact source commit.

## October 8 version 1.1 release checkpoint

The owner authorized publication of the v1.1 code and Markdown documentation to a public GitHub repository. Source preparation is distinct from image deployment and repository/tag publication. This public record excludes real contact details, private capability URLs, private exports and local verification artifacts.

- [x] Full v1.1 suite: 222 pytest tests passed on Windows (12.93 seconds) and in the rebuilt Linux image (12.06 seconds).
- [x] Frontend private-entry/disclosure VM: 38 cases passed; JavaScript syntax passed.
- [x] Analytics privacy VM: 346 assertions passed.
- [x] Recruiter catalogue focused advisor/security tests and Ruff passed.
- [x] Local `v1.1.0-release` Docker image rebuilt successfully.
- [x] Immutable registry publication confirmed.
- [x] New Ready Cloud Run revision and 100% serving traffic confirmed.
- [x] Canonical v1.1 workflow: 25 HTTP checks with actual OpenAI passed.
- [x] Canonical v1.1 request/completed usage independently matched in Cloud Logging.
- [x] Two private dashboards: 18 HTTP checks and actual Chrome cited-advisor checks passed.
- [x] Canonical OpenAPI returned HTTP 200 with version `1.1.0`.
- [x] Attribution iframe regression: seven new checks passed; actual Chrome showed eight Google Search suggestion links with no console errors/warnings.
- [x] Dedicated-project Cloud Tasks OIDC → Vertex Google Search → OpenAI → Cloud SQL research completed; worker request/usage independently matched in Cloud Logging.
- [x] Publication privacy audit: 74 candidate files, four actual source-project Secret Manager versions and seven private-artifact fingerprints, zero findings. Comparison against four actual target-project secret versions also produced zero findings.
- [x] Public GitHub source published and anonymously accessible; initial CI run passed.
- Versioned source/downloads: [v1.1.0 release](https://github.com/SonnyBali/prospectiq/releases/tag/v1.1.0). Check [Actions](https://github.com/SonnyBali/prospectiq/actions) for CI against the exact tag commit.

The October 8 immutable image manifest is `sha256:1edf72400d13eabf7377539c78019027de5997be8fdad049a1eb5d1202c3d2b7`. At that checkpoint the canonical hostname served project `ai-leadscore/us-central1`, Ready revision `prospectiq-00007-n2g`, with 100% traffic. Canonical OpenAPI returned HTTP 200/version `1.1.0` at the 14:49 UTC checkpoint. The earlier v1.1 image/revision `prospectiq-00006-ksp` passed 212 tests before the subsequent attribution/recruiting fixes; those counts are historical.

The post-fix canonical smoke passed 25 HTTP checks with actual synthetic OpenAI request `d1b7b6eda1954bb4a3b2d19ac5746012`, 1,686 input / 338 output tokens and estimate `$0.0012152`. Python remains the numerical authority; SQL history/traces, session cookies, privacy and logout passed. The earlier v1.1 request `e5b6b07d9113434aa233e8299c4cc952` independently matched Cloud Logging on revision `prospectiq-00006-ksp` at `2026-10-08T14:44:12.617159Z`, HTTP 200, 3,418.88 ms, 1,659 input / 247 output tokens and estimate `$0.0010588`.

Two private dashboards again passed 18 HTTP checks, including cached public research/Google attribution, client-ID/cookie binding, wrong-ID rejection, query-only unauthorized access and private CSP/tracking isolation. The earlier source check observed 14 retained public sources. The corrected attribution iframe now retains its same origin while sandbox and response CSP block scripts; actual Chrome displayed eight Search suggestion links with zero console errors/warnings. Other private responses retain denied framing and strict marketing isolation.

The actual recruiting question “Can it be connected to recruiting?” returned a direct cited Python/FastAPI recruiter-briefing proposal, without unrelated numbers or a withheld-content warning. Request `0a9b20d18920483d826fa8087c38e1cf` independently matched completed Cloud Logging usage and HTTP 200 on `prospectiq-00007-n2g` at `2026-10-08T15:03:55.637294Z`: 10,752.48 ms, 4,855 input / 333 output tokens, estimated `$0.0024748`. This verifies an advisory proposal, not a deployed recruiting integration. No client names, contact details, prospect identifiers or private capability URLs are included in this record.

The dedicated native HighLevel global trigger link's exact contact-field target and four project tags passed direct API readback HTTP 200; tags were not assigned to contacts by that verification. The native 30-minute feedback workflow was saved and reopened as a draft with four templates, independent Spanish handling and email/SMS permission gates; loop paths were removed and terminal paths limit each channel to one message. Publish is OFF. Global DND/frequency policy, replies during the wait, Sunday handling, send-boundary behavior and delivery remain unresolved. Configuration/draft readback does not establish per-recipient redirect or delivered follow-up.

The public [SonnyBali/prospectiq](https://github.com/SonnyBali/prospectiq) source is anonymously accessible. Initial commit `d731821b25859e2ee2be1d5830fefe5cb64e970b` passed [GitHub CI run 37796011001](https://github.com/SonnyBali/prospectiq/actions/runs/37796011001). Versioned files are linked from [v1.1.0](https://github.com/SonnyBali/prospectiq/releases/tag/v1.1.0); consult [Actions](https://github.com/SonnyBali/prospectiq/actions) for the exact tag commit's result.

The separate `firewireads-platform` project (display name FireWireAds Platform) has verified billing linkage, 13 enabled APIs, four named credential copies checked in memory, a fresh Secret Manager database password, scoped runtime grants and a RUNNABLE PostgreSQL 16 database. An actual connector `SELECT 1` passed. The native target [public synthetic demo](https://prospectiq-504110803281.us-central1.run.app/) serves Ready revision `prospectiq-00003-tdc`, 100% traffic, Ready transition `2026-10-08T15:23:03Z`, using the same image manifest above. Strict health returned HTTP 200, SQL connected and OpenAI mode. Target native smoke passed 25 HTTP checks on `prospectiq-00001-vt5`; request `8d5ff5c0a762445cbab57ad290b94651` reported 1,686 input / 419 output tokens, estimate `$0.0013448`, and independently matched Cloud Logging.

An approved public FireWireAds research job completed the actual Cloud Tasks OIDC → Vertex Google Search → OpenAI → Cloud SQL cache flow with eight sources, retained Google attribution and cached intelligence. Independent Cloud Logging matched worker request `51ddd9d392bf4be3b42863518d6f8f4f` on target revision `prospectiq-00002-9mk` at `2026-10-08T15:22:24.813465Z`: `/api/internal/research` HTTP 200, 25,139.28 ms; completed `gpt-4.1-mini` usage 2,888 input / 416 output / zero cached tokens, estimate `$0.0018208`. The test had no CRM contact, issued no access link and sent no outreach. Target `ALLOW_CLOUD_TASKS=true`; `ALLOW_CRM_LINKS=false` until canonical-domain/database migration. The branded hostname and its existing database remain on the original project. [Release notes](../RELEASE_NOTES_v1.1.md) describe the source behavior. The following pre-v1.1 evidence is historical.

## Verified serving release before v1.1

| Component | Observed state | Remaining verification |
| --- | --- | --- |
| Application tests | This earlier serving release passed 123 pytest tests on Windows/Linux, Ruff, JavaScript syntax and 298 analytics assertions | New v1.1 checks and pending release gates are recorded above |
| Container publication | Fourth image includes marketing/SEO and the restricted temporary public-demo origin. Cloud Run's resolved Linux manifest digest was independently read; both digests are recorded below | No remaining publication/serving verification |
| Cloud SQL Admin API | Enabled in project `ai-leadscore` | None for API enablement |
| Cloud SQL `prospectiq-db` | `RUNNABLE`; database and user `prospectiq` created. Actual pg8000 connector/schema and canonical-host deployed chat, history and draft persistence verified | No remaining connection/persistence verification for this release |
| Runtime identity | Dedicated service account has Cloud SQL Client and access to named secrets. Deployed SQL and OpenAI reads succeeded | Administrative credential use remains separately gated; do not imply a live CRM write |
| Database/admin secrets | Newly generated values stored through the Secret Manager SDK. Database/user initialization used ADC and the SDK, with the password kept out of files and command arguments | No values are included in verification output |
| Cloud Run `prospectiq` | Ready revision `prospectiq-00005-t7w` receives 100% traffic; serving-image digest verified. Ready transition recorded at `2026-10-08T13:50:24Z`; branded browser and automated interactions passed | No remaining serving verification |
| Domain ownership | Ownership of `firewireads.com` verified with Google | None for ownership verification |
| DNS | `prospect` CNAME to `ghs.googlehosted.com` saved in SiteGround. Google and Cloudflare DNS-over-HTTPS returned the expected records; normal Windows HTTPS requests now resolve and succeed | None for current DNS/HTTPS reachability |
| Custom-domain mapping | `Ready=True` and `CertificateProvisioned=True`, transition `2026-10-08T13:48:42Z`. Strict normal HTTPS `https://prospect.firewireads.com/health` returned 200 with SQL connected and OpenAI mode | None for TLS readiness; certificate validation was not bypassed |
| Branded Chrome workflow | Actual synthetic PUBLIC DEMO loaded. Real OpenAI chat returned E2/E3 citations; 400-lead scenario returned $10,800 monthly, $129,600 annual, $10,303 net and nine expected customers. History loaded two messages and Engineering View showed actual chat/simulator/history requests. Console warnings/errors were empty | No remaining recorded browser-workflow verification |
| Canonical same-origin HTTP workflow | `scripts/smoke_deployed.py` passed 25 HTTP checks with `same_origin=true`, URL and Origin both `https://prospect.firewireads.com`, including one paid chat, SQL-backed history/draft/session isolation and logout | No remaining canonical HTTP checks |
| Fallback same-origin HTTP workflow | The same script passed 25 checks on revision `prospectiq-00005-t7w`, URL and Origin both the exact temporary Cloud Run hostname | Verified usable fallback |
| Fallback Chrome and recording | Cited OpenAI chat, simulator, history and Engineering View passed. Recorded receptionist CTA opened the MP4 player: readyState 4, duration 533.757 seconds, no media error; it remained paused | Live voice remains disabled; no live-call claim |
| Cloud Logging | Exact canonical HTTP request `c3c1cbcd99f5462099572e1469ba551a` had completed usage and `/api/chat` HTTP 200 on revision `prospectiq-00005-t7w` at `2026-10-08T14:01:23Z`; browser request `cb51f002eba24c19a4ce1faff11daef0` was independently reconciled at `2026-10-08T13:58:05Z` | No remaining request/usage reconciliation |
| Tracking, SEO and branding | Canonical Chrome observed SDK and page-view requests for GA4 `G-6JM91XZMX2`, Google Ads `AW-17005023254` and Meta Pixel `502483969150258`. Canonical metadata, robots/sitemap, 1200×630 share PNG, 32px favicon, 180px Apple icon and SVG branding are deployed | Browser requests do not verify account dashboard receipt, reporting or attribution; no GTM container was discovered |
| Marketing CSP and private pages | Canonical-host SDK/page-view requests appeared after the public-demo tracking control. Temporary-demo Chrome loaded only same-origin scripts, with no external tags. Private/API/local/direct Cloud Run responses keep strict CSP; extra-URL variants and private pages are noindex | Account-side analytics ingestion remains unverified |

Published image-index digest: `sha256:0801a6b30f10d4c70d08c2fdd796684293679d9215845cb987f12e5292087a75`.

Verified Cloud Run revision `status.imageDigest`, resolving the Linux image manifest: `sha256:b18df0d3ffd6f15f8ab440026026c0dfdf680462ea0323179fee0b5c0796cd42`. The index and platform-manifest digests identify different layers of the same published image; they are not expected to be identical.

The fourth image initially ran as revision `prospectiq-00004`; revision `prospectiq-00005-t7w` uses the same image with corrected Cloud Run proxy configuration. Its HTTPS redirects were verified after that configuration change.

The primary live recruiter demo is `https://prospect.firewireads.com`; private access stays canonical-only. Its managed certificate, strict HTTPS and real Chrome chat/simulator interactions passed. The verified fallback `https://prospectiq-s4gztnjt6a-uc.a.run.app` works through an exact configured `DEMO_ORIGIN`, superseding the earlier backend-only smoke that supplied a canonical Origin header on the temporary address.

Canonical HTTP smoke request `c3c1cbcd99f5462099572e1469ba551a` used model `gpt-4.1-mini`, 1,168 input tokens, 310 output tokens, zero cached input tokens and estimated `$0.0009632`. Matching completed usage and HTTP-200 request events were independently read from Cloud Logging at `2026-10-08T14:01:23Z` on revision `prospectiq-00005-t7w`.

Fallback same-origin HTTP smoke request `4dfe9e7cc28b41b9ad3d4ab6aaf4341d` used 1,168 input tokens, 262 output tokens and estimated `$0.0008864`; its matching events were independently read on the same revision at `2026-10-08T13:51:07Z`.

Actual Chrome chat request `526a9d5621224312a29fcb1f0357f338` used 1,167 input tokens, 316 output tokens and server-estimated cost `$0.0009724` (displayed rounded as `$0.000972`). Matching request and usage events were independently read from Cloud Logging at `2026-10-08T13:51:27Z`. It displayed cited evidence E2/E3 and the unchanged Python scenario: 400 leads, `$10,800` monthly opportunity, `$129,600` annual opportunity, nine expected customers and `$10,303` monthly net. History and Engineering View showed the actual request, HTTP 200, 4,038.13 ms and provider usage. Cost figures are estimates, not invoices; no credentials, prompts or customer records are reproduced here.

Actual branded-host Chrome chat request `cb51f002eba24c19a4ce1faff11daef0` used 1,167 input tokens and 275 output tokens; Cloud Logging independently confirmed exact estimated `$0.0009068` at `2026-10-08T13:58:05Z` (UI rounded to `$0.000907`). It showed E2/E3 citations and the same authoritative 400-lead Python results. History loaded two messages. Engineering View showed chat HTTP 200 in 3,328.73 ms, simulator HTTP 200 in 16.21 ms and history HTTP 200 in 21.98 ms.

Canonical Chrome resource observations included GA4 `g/collect` with `tid=G-6JM91XZMX2` and `en=page_view`, Google Ads `ccm/collect` with `id=AW-17005023254` and `en=page_view`, the related DoubleClick collection request, and Meta `tr` with `id=502483969150258` and `ev=PageView`. These verify browser-side requests, not account dashboard receipt or attribution.

## Deployment configuration

The canonical service's isolated portfolio configuration is in Google Cloud project `ai-leadscore`, region `us-central1`; the new project's current serving/research evidence is recorded above:

- Cloud Run: one CPU, 1 GiB memory, concurrency four, minimum zero instances and maximum one instance.
- Cloud SQL: PostgreSQL 16, Enterprise edition, shared-core `db-f1-micro`, zonal availability and 10 GB SSD storage. Backups are configured for 18:00 UTC with seven retained backups; deletion protection is enabled. Connections require encryption and no authorized-network entries were configured. The Python connector supplies the authenticated encrypted connection.
- Provider credentials stay server-side in Secret Manager. The runtime receives secret names and scoped IAM rather than credentials embedded in the image or dashboard.
- Secure session cookies, request-origin checks, CSRF validation, session-scoped history and PostgreSQL-backed AI call budgets protect the public application.
- `DEMO_ORIGIN` permits only the exact verified temporary hostname, a matching same-origin request, valid CSRF and the public fixture session without an access link. Tests reject unknown origins/hosts and private or other synthetic sessions even with valid CSRF. `PUBLIC_ORIGIN` remains the branded origin.
- `FORWARDED_ALLOW_IPS=*` is configured for Cloud Run's trusted ingress TLS termination so ASGI sees the forwarded HTTPS scheme; the deployed HTTPS redirect was verified. This setting belongs to the Cloud Run ingress deployment, not an arbitrary directly exposed server.
- Startup schema creation and demo seeding use PostgreSQL advisory locks. API request traces are persisted through a threadpool so database I/O does not block the async middleware's event loop.

Cloud Run scaling to zero does **not** stop Cloud SQL. The database has continuing instance/storage/backup costs while the demonstration is idle; stopping an instance also leaves storage and relevant IP charges. See Google's [Cloud SQL stop/start documentation](https://docs.cloud.google.com/sql/docs/postgres/start-stop-restart-instance) and [pricing](https://cloud.google.com/sql/pricing/). This record does not present a monthly cost estimate.

The small shared-core, single-zone database is for a portfolio demonstration. Shared-core and single-zone instances are excluded from the [Cloud SQL SLA](https://cloud.google.com/sql/sla-20250910); an operational customer service needs a separately reviewed sizing, availability and recovery plan.

## Public URL tradeoff

The approved subdomain runs the application at its own root. It does not require changing the existing FireWireAds site's `/api` or `/static` paths. Cloud Run's direct custom-domain mapping is a Preview feature that Google does not recommend for production services; it maps a hostname to `/`, not a path such as `/prospect`. Google recommends an external Application Load Balancer and also supports Firebase Hosting. See [Google's domain-mapping documentation](https://docs.cloud.google.com/run/docs/mapping-custom-domains).

Direct domain mapping keeps this portfolio release small. A customer-facing production rollout should review a load balancer or Firebase Hosting, together with their costs and additional controls. DNS, managed HTTPS and the branded browser chat/simulator workflow are now verified.

## Enabled demonstration boundaries

The public dashboard uses a fictional company and clearly marked synthetic research. Real cited OpenAI chat, calculations, history and Engineering View passed at the branded hostname and native fallback. Python owns the simulator's calculations. Follow-up requests save reviewable application drafts in Cloud SQL.

The requested marketing tags are included for the public synthetic dashboard only, behind an explicit tracking control. Their canonical-host SDK/page-view requests were observed in Chrome. Private prospect pages, noncanonical hosts, URLs with query strings and private access fragments block marketing loading. Canonical-host checks guard the relaxed public-page CSP; private/API/local/direct Cloud Run responses retain strict policies. Account-side ingestion remains unverified. Chat prompts, simulator values, contact profiles and private capability URLs are excluded from marketing events.

Cloud Tasks research dispatch and completion are verified in the separate `firewireads-platform` deployment described above. The canonical service's research dispatch has not been established by that test. Live CRM task delivery, customer outreach, calendar booking and live voice remain disabled or unverified. The existing receptionist recording is available for playback. Sales and appointment agents require an isolated provider demonstration and separate verification. Public source and the initial remote CI run are verified. Versioned files are linked from v1.1.0; Actions records the CI result for each exact commit.

## Remaining operational boundaries

Canonical-domain/database migration to the new project, native HighLevel recipient redirect and delivered timed follow-up, live internal-task delivery, isolated voice-agent audio and latest-fix/tag publication remain separate checkpoints. The new project's verified queue/worker flow does not imply CRM enrollment or outreach. Third-party browser tracking requests are verified; account dashboard reporting and attribution remain unverified.

Branded dashboard and stored advisor conversation were visually reviewed after the canonical chat/history/Engineering checks. Public evidence is the redacted request/usage and resource readback above; local browser artifacts are excluded from repository publication.
