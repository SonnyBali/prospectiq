# Frontend verification

This document records canonical, native-origin and earlier local Chrome checks on October 8, 2026. The public dashboard used the fictional Copperline Home Services dataset throughout. Current release status is in [live-release.md](live-release.md); account-side analytics reporting remains separate from observed browser requests.

Cloud Run is ready, Cloud SQL connector/schema and deployed chat/history/draft persistence are verified, and deployed request/usage logs were read from Cloud Logging. The serving release recorded below passed 123 pytest tests on Windows/Linux, including 28 origin-security checks, Ruff, JavaScript syntax and 298 analytics privacy assertions. Canonical and native same-origin backend checks each passed 25 checks with real synthetic OpenAI and independently matched Cloud Logging usage. Static/SEO/private-noindex/CSP checks are verified. Current v1.1 source/image/revision checkpoints are tracked separately in [live-release.md](live-release.md).

## Verified canonical recruiter demonstration

**[Open the primary recruiter demo](https://prospect.firewireads.com/).** Managed TLS, strict HTTPS health and actual Chrome workflow are verified. The company data is fictional; no customer outreach or live voice was initiated.

- **Simulator:** monthly leads 300→400 returned Python $10,800 monthly opportunity, $129,600 annual opportunity and $10,303 monthly revenue less AI cost.
- **Actual OpenAI:** request `cb51f002eba24c19a4ce1faff11daef0` returned E2/E3 citations and 1,167 input / 275 output tokens. Independent Cloud Logging at `2026-10-08T13:58:05Z` recorded estimate $0.0009068; UI rounds to $0.000907.
- **History/Engineering View:** two SQL-backed chat messages loaded. The actual chat trace showed HTTP 200 in 3,328.73 ms with usage, simulator HTTP 200 in 16.21 ms and history HTTP 200 in 21.98 ms.
- **Console:** no errors or warnings during the canonical check.
- **Google tags:** resource requests loaded gtag for `G-6JM91XZMX2` and `AW-17005023254`. Browser resources included `www.google-analytics.com/g/collect` with the GA measurement ID and `page_view`, `www.google.com/ccm/collect` with the Ads ID and `page_view`, and `ad.doubleclick.net/ccm/s/collect`.
- **Meta pixel:** `fbevents.js`, signals configuration for `502483969150258` and `www.facebook.com/tr` with that ID and `PageView` were observed.

These are actual observed network requests; account-side analytics receipt/reporting is untested. No synthetic lead or booking conversion was emitted. The canonical same-origin backend smoke independently passed 25 checks; exact request/usage/log evidence is in [verification.md](verification.md). The canonical dashboard and stored conversation were also visually reviewed; local screenshots are excluded from public repository publication.

## Verified native recruiter demonstration

The [native recruiter backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) also passed actual Chrome checks on the ready serving deployment on October 8. The fixture is synthetic; no private prospect data, live voice session or customer workflow was involved.

- **Python simulator:** changing monthly leads from 300 to 400 produced $10,800 monthly opportunity, $129,600 annual opportunity, nine expected customers and $10,303 monthly revenue less AI cost.
- **Actual OpenAI:** browser request `526a9d5621224312a29fcb1f0357f338` returned citations E2/E3 and the exact submitted scenario, with 1,167 input / 316 output tokens. Independent Cloud Logging readback at `2026-10-08T13:51:27Z` recorded an estimated $0.0009724. Estimates are not billing receipts.
- **History and Engineering View:** the history action preserved SQL-backed session messages; the request table displayed that actual chat with HTTP 200, 4,038.13 ms and provider usage.
- **Recorded receptionist:** the recording CTA opened the MP4 player with `readyState=4`, duration 533.757 seconds, no media error and paused playback. This was a recording load, not live audio, microphone access or a call. Earlier local checks below established recorded playback advancing.
- **Scripts and console:** no console errors or warnings; no external scripts were present. Marketing is blocked at the native origin by design, while the canonical-host configuration remains unchanged.

The native dashboard and stored conversation were visually reviewed. Exact serving revision, traffic and image are maintained in [live-release.md](live-release.md). Canonical checks are recorded separately above.

## Earlier verified local interactions

- **Personalized demo dashboard:** synthetic-data banner, company greeting, saved research, recommendations, unknowns, and evidence citation links rendered correctly. Fictional `example.com` evidence URLs are not presented as live research pages.
- **Simulator:** changing monthly leads from 300 to 500 returned $13,500 monthly revenue, $162,000 annual revenue, and 11.25 expected customers. The frontend displayed the Python API results; it did not calculate revenue in JavaScript. The advisor action waits for matching scenario inputs and results.
- **Guided mode:** the local fallback explicitly identified itself as a scripted preview without an OpenAI call. Its scenario explanation included the exact Python result and source citations.
- **Real OpenAI mode:** two synthetic-company requests completed through the configured backend. Request `4d94eec57629465fb4c2d70a6401409c` reported 1,153 input tokens, 221 output tokens, an estimated cost of $0.000815, and a 200 response in 7,223.12 ms in Engineering View. Request `b5d022f7c540499aa95bc51a08d2fb32` reported 1,252 input tokens, 258 output tokens, and an estimated cost of $0.000914. Costs are configured estimates, not billing receipts.
- **Authoritative scenario snapshot in chat:** the latter request displayed the server-returned values separately from model prose: $8,100 monthly revenue, $97,200 annual revenue, $7,603 monthly revenue less AI cost, and 6.75 expected new customers. The frontend checks that returned assumptions match the submitted assumptions. The snapshot is labeled as the scenario submitted with that message.
- **Engineering View:** displayed real local session request IDs, response codes, timings, provider labels, and token totals. At this earlier local check, SQLite, unverified Cloud SQL, unconfigured queue, and disabled CRM writes were shown. Cloud SQL/logging were subsequently verified in the approved deployment; live queue/CRM delivery remain disabled.
- **Draft-only follow-up:** saving synthetic notes returned a draft ID and the explicit message that no CRM write or outreach occurred.
- **Recorded Voice AI demo:** the embedded FireWireAds receptionist recording loaded with `readyState=4`, duration 533.757 seconds, and played to approximately 9.23 seconds before being paused. Playback did not start a live agent, call, booking, or customer workflow. A separate recording link is available if embedded playback fails.
- **Responsive layout:** a requested 390-pixel viewport produced an effective 300 CSS-pixel viewport under the browser's display scaling. Content width matched viewport width with no horizontal overflow. The mobile advisor shortcut worked and hid while the advisor was visible. The desktop advisor fit the short browser viewport with its input and usage information accessible.
- **JavaScript:** `node --check app/static/app.js` passed. Final tested Chrome page produced no console errors or warnings.

## Browser checks still pending

- The private dashboard token exchange, token-fragment removal, and cookie-based page-refresh recovery. Backend tests cover the corresponding authorization behavior; this frontend check did not open a real prospect link.
- Google Search grounding attribution in a sandboxed authenticated iframe. No real research attribution fixture was displayed during these browser checks.
- Session-history retrieval after a fresh page reload.
- Isolated live browser and call demonstrations. The browser adapter opens only after a user click, requires server-enabled configuration, rejects the dashboard's own origin, and loads a separate-origin `browser_url`. Production agents remained blocked. No microphone permission, live provider session, or telephone call was initiated.
- Account-side Google/Meta receipt and reporting. Observed canonical browser page-view requests establish network loading, not downstream analytics reporting.
- Live Cloud Tasks worker execution and isolated voice/CRM delivery remain disabled or untested. Cloud Run, Cloud SQL persistence and Cloud Logging have separate deployed backend evidence in [live-release.md](live-release.md); they are not gaps in the current infrastructure checkpoint.

The UI has a distinct provider badge for guided versus OpenAI mode. Provider credentials remain outside the frontend. All dynamic research and advisor text is rendered through text nodes; evidence links require HTTPS, and external links use `noopener noreferrer`.
