# FireWireAds voice integration inventory

Audit date: October 8, 2026 (Asia/Singapore). Read-only inspection; no provider configuration, deployment, phone call, microphone permission, contact write, message, booking, payment, or workflow execution was performed.

The existing browser integration can be reused, but the current production agents are not isolated recruiter demonstrations. Keep their widgets and telephone numbers disabled in ProspectIQ. The published recorded HVAC walkthrough is the immediately usable demonstration of the existing system; label it as a recording and keep it separate from the synthetic prospect data.

## What was verified

| Component | Evidence | Tested boundary |
| --- | --- | --- |
| Public FireWireAds homepage | `https://firewireads.com/` returned HTTP 200 and contains Sunny/live voice labels | Public page retrieval, not an AI conversation |
| Shared voice controller | Public `https://storage.googleapis.com/firewireads-shared-assets-1051896753015/widget/firewire-command-console.js` returned HTTP 200, version `2026.10.02.12`, and matched `canonical-widget/firewire-command-console.js` exactly | Source equality and availability, not live microphone/audio exchange |
| Sunny, plumbing, and law widgets | Public `GET https://services.leadconnectorhq.com/chat-widget/public/config/{widgetId}` with the same `widget-id` header returned HTTP 200 | Configuration names, tenant, widget mode, and agent linkage; no call started |
| HighLevel voice inventory | Authenticated read-only `GET /voice-ai/agents?locationId=aFnKcmUdTSPIjo7lCaix&pageSize=50`, API version `v3` | Seven current agent configurations and action metadata read successfully in the verified FireWire tenant |
| Published recorded HVAC walkthrough | Normal Chrome loaded the article and `#fw-live-demo-video`; media reported duration `533.757007` seconds, dimensions `720 × 1280`, `readyState=4`, and no media error | Visible `0:49 · Voice conversation` chapter click started playback; playback advanced from `49.16` to `59.49` seconds. Audit tab then closed. This was prerecorded media, not a live call |
| Plumbing and law public pages | `https://plumber.firewireads.com/` and `https://law.firewireads.com/` returned HTTP 200 with their Ace labels | Page availability; runtime hydration and conversations were not tested |

Direct command-line requests to the blog article/media encountered HTTP 403, while normal Chrome playback succeeded. This is a material embedding compatibility constraint: display video load errors and a link to the original article. Do not bypass site protection or download/rehost the asset as a workaround.

## Existing demos and current action exposure

All seven agents returned `saveCallSummaryAsNote=true` and configured post-call notification recipients. A missing explicit workflow therefore does not establish isolation. These configurations can still create provider sessions, call logs, CRM notes, and notifications.

| Existing agent | Agent ID | Demonstration role / public linkage | Current configured actions | ProspectIQ reuse decision |
| --- | --- | --- | --- | --- |
| Sunny | `6841f81419b88afca92edfd0` | Public default FireWire voice agent; widget describes “FireWire AI Automation Specialist.” Sales/audit, qualification, and appointment context appear in its prompt. | Knowledge base, contact-field data extraction, one call-end workflow; inbound business telephone assigned | Reuse integration pattern only. Do not load this production widget or offer its phone number as an isolated demo |
| Jerry | `6830b2cc2e9a2b6431943746` | Existing telephone agent; no selected portfolio browser widget identified | Knowledge base and contact-field extraction; inbound business telephone assigned | Do not treat a business phone assignment as a safe demonstration number |
| Ace for Hvac | `6aba191ab0a4c82c4307000c` | Appointment-setting configuration | `APPOINTMENT_BOOKING` action has an attached calendar | Keep disabled; booking can touch a real calendar |
| Ace HVAC Service Demo | `6abe38395deba841f0f3bcf2` | Receptionist/service-intake demonstration with follow-up and appointment context | Confirmed-mobile link-send `CAP` action; legacy SMS, phone extraction, and workflow actions whose names start with `DISABLED` | Keep disabled. Action names are not proof of technical deactivation; the API response has no enabled-state field |
| Ace for Plumbing | `6abf71235deba87a9ff43df4` | Dedicated public plumbing widget | Knowledge base, contact-field extraction, one call-end workflow | Keep production widget disabled until a separate isolated agent/widget is authorized and audited |
| Ace for Law | `6abf8965bdf8ff03f925fae3` | Dedicated public legal intake demonstration widget | No explicit actions or call-end workflows returned; summary/notification settings remain active | Keep disabled. No explicit action does not mean no CRM/provider side effects |
| My Agent 658 | `68b3aa4bad0bd9465f80811e` | Unassigned configuration; no demonstrated role identified | No explicit actions returned; summary/notification settings remain active | Do not present as tested or operational |

No private contacts, telephone numbers, notification addresses, calendar identifiers, workflow identifiers, prompts, or credentials are reproduced in this inventory.

## Public widget linkage and existing code

These are public embed identifiers, not API credentials. Do not infer underlying vendor identity from the provider marker `r` returned in public configuration; the verified integration boundary is HighLevel/LeadConnector Voice AI.

| Widget | Widget ID | Public configuration verified |
| --- | --- | --- |
| Default FireWire/Sunny | `6a76e48422509c8ee2247714` | `chat-type=voiceAiChat`, sticky placement, agent Sunny, FireWire tenant |
| Ace for Plumbing | `6abf71b7cdeb03a6d5287556` | `chat-type=voiceAiChat`, sticky/avatar placement, plumbing agent, contact form disabled |
| Ace for Law | `6abe29f12b6d9dcee841fc67` | `chat-type=voiceAiChat`, sticky/avatar placement, law agent, contact form disabled |

Source paths are relative to the FireWireAds repository root:

- `canonical-widget/firewire-global-ai-widget-loader.js`: current shared asset loader (`2026.10.02.12`), text widget `66b18a3492c831b660b2c07f`, shared CSS/controller loading, and duplicate-load guard.
- `canonical-widget/firewire-command-console.js:630`: waits for text hydration, then loads a separate voice host. Host mapping at lines 634–660 selects plumbing/law; unknown hosts default to Sunny. Native LeadConnector controls are styled, not replaced with a custom voice protocol.
- `canonical-widget/highlevel-loader.html` and `canonical-widget/firewire-shared-widget-snippet.php`: existing page embedding paths.
- `plumber-funnel/app/site-integrations.tsx`, `law-funnel/app/site-integrations.tsx`, and `hvac-funnel/app/site-integrations.tsx`: one shared loader per site.
- `cary-alva-proposal/app/FireWireVoiceChatbot.tsx`: React version of the same text-first hydration sequence, using the default Sunny widget and public loader.
- `cary-alva-proposal/app/FireWireAgentDock.tsx`: existing native-shadow-DOM launcher and voice/chat opening controls.
- `template-sources/firewire-ai-opportunity-audit/app/site-config.ts` and `app/audit-integrations.tsx`: audit-page example using Sunny and the shared loader.
- `scripts/preview_voice_call_states.mjs`: replay/assertions for captured native active/ended call markup. This verifies lifecycle styling against a fixture, not a new live voice call.
- `outputs/widget-repair-2026-10-02/native-ended-capture.json`: previous captured native widget markup, not proof of a current isolated configuration.
- `firewire-sales-os/src/highlevel.mjs`: existing server-side Secret Manager helper, verified FireWire tenant guard, paced HighLevel HTTP client, and version `v3` support.

The shared controller has plumbing/law hostname mappings but no HVAC hostname mapping. `hvac-funnel/app/site-config.ts` labels Ace, while an unmapped deployment would receive Sunny from the shared controller. `hvac.firewireads.com` did not resolve during this audit. Do not report the HVAC public browser integration as operational without verifying the actual deployment hostname and widget linkage.

## Working recorded demonstration

```text
video_url=https://blog.firewireads.com/wp-content/uploads/2026/10/ai-receptionist-live-demo-web-review.mp4
poster_url=https://blog.firewireads.com/wp-content/uploads/2026/10/Ai-Receiptionist-Live-Example-Cover.jpg
article_url=https://blog.firewireads.com/ai-receptionist-missed-leads/
```

The article labels the walkthrough as a recorded FireWireAds HVAC demonstration. It shows service intake, appointment preference, permission for follow-up, email/text follow-up, and booking/deposit screens. Watching it performs none of those business actions. It is not proof of a completed payment, technician dispatch, recovered revenue, or a live conversation in ProspectIQ.

Related source: `outputs/ai-receptionist-live-demo-2026-10-02/placement-plan.md` and `demo-section.html`. The recording is an existing published example, not the synthetic prospect fixture. Do not copy displayed contact/payment information into the app or imply that the synthetic recruiter scenario generated this recording.

Recommended immediately available choices:

1. **Receptionist — recorded HVAC intake:** play the existing walkthrough with an explicit “Recorded demonstration” label and article fallback.
2. **Sales advisor — synthetic interactive scenario:** use the new company-context advisor with a clearly synthetic company. Voice provider launch remains disabled until an isolated agent is ready.
3. **Appointment setter — synthetic scenario:** preview the qualification/appointment flow without a real booking. Provider launch remains disabled until connected to a test calendar with notifications and follow-up isolated.

Do not label recorded playback or a scripted scenario as a live provider conversation.

## Browser support and credentials

HighLevel officially supports browser microphone/speaker conversations through its Voice AI chat widget. The current public widgets are configured in that mode. A phone-based fallback is unnecessary for this provider's supported browser capability, although end-to-end audio still needs testing for the future isolated widget.

- [HighLevel browser Voice AI setup and supported actions](https://help.gohighlevel.com/support/solutions/articles/155000006648)
- [HighLevel WebRTC voice widget](https://help.gohighlevel.com/support/solutions/articles/155000006056)
- [HighLevel agent actions, web testing, and deployment](https://help.gohighlevel.com/support/solutions/articles/155000004107)
- [Official read-only agent list API](https://marketplace.gohighlevel.com/docs/ghl/voice-ai/get-agents/)

Public widget playback needs only the public widget ID. Administrative inspection/configuration needs a tenant-scoped HighLevel integration token with appropriate voice read/write scopes. Existing local code retrieves `FIREWIRE_GHL_API_KEY` and `FIREWIRE_GHL_LOCATION_ID` from Secret Manager in project `ai-leadscore`; neither value should reach the frontend. The public recorded media needs no API key, although site access protections can affect clients.

## What must be built or verified before live voice is enabled

1. An authorized isolated demonstration agent/widget in a sandbox tenant or an equivalently audited test environment, with synthetic knowledge/context and no production customer identifiers.
2. Remove/disable all production workflows, contact extraction, SMS/email, custom actions, post-call notifications, and real booking/payment paths. If the provider always creates sessions/contacts, document that behavior and keep it in a dedicated test tenant.
3. A server-side allowlist of approved demo widget IDs or verified demo phone numbers. Keep the current production IDs out of this allowlist; do not accept arbitrary frontend identifiers.
4. A single selected provider widget with explicit scenario selection and a user-controlled start. No automatic microphone request or call. Show “browser voice,” “call-based demo,” or “recorded demonstration” accurately.
5. Provider timeout/loading/error handling, source/context boundaries, AI disclosure, and consent/retention information appropriate to the isolated configuration.
6. Authorized end-to-end tests for start/audio/mute/end, unsupported questions, scenario separation, and post-call readback proving no production message, workflow, booking, or customer update. Fixture/UI-only tests do not establish that boundary.

No production agents were edited during this audit. Their configurations remain unchanged; ProspectIQ must leave live voice disabled until this isolation work is explicitly authorized and verified.
