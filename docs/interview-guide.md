# Explain and demonstrate the Python implementation

## A concise introduction

“ProspectIQ turns approved CRM context and stored business research into a personalized opportunity dashboard. I built the orchestration in Python/FastAPI, used the official OpenAI Responses SDK for typed recommendations, and kept revenue arithmetic in a deterministic Python function. Cloud Run, PostgreSQL persistence and request/usage logging are deployed and verified. The public demonstration uses a fictional company, distinguishes evidence from hypotheses, and shows actual request processing.”

Canonical HTTPS, actual OpenAI chat/simulator/history/Engineering View, SQL persistence and Cloud Logging evidence are recorded in [verification.md](verification.md). The dedicated project's Cloud Tasks OIDC → Google research → OpenAI → SQL cache flow is also verified; its test issued no access link and sent no outreach. Canonical-domain/data migration, delivered CRM follow-up and isolated live voice remain unverified. Google/Meta page-view requests were observed; account-side reporting is untested. Current revision evidence is in [live-release.md](live-release.md).

## Three-minute recruiter walkthrough

**[Launch the verified public demo](https://prospect.firewireads.com/).** The dashboard uses fictional public company data. The [native backup](https://prospectiq-s4gztnjt6a-uc.a.run.app/) supports only that built-in synthetic session and runs no marketing trackers.

1. **0:00–0:25 — The business context.** Open the verified public demo link. Point to the synthetic banner and Copperline greeting. Explain that saved research loads from the database without revealing CRM records or making a model request during initial page load.
2. **0:25–1:00 — Python owns the numbers.** Change monthly leads from 300 to 400 while keeping the other default assumptions. Show $10,800 monthly opportunity, $129,600 annual opportunity and nine expected customers. These are hypothetical expected values, not measured revenue or a forecast.
3. **1:00–2:15 — Actual AI and request processing.** Click “Ask the advisor about this scenario.” After the OpenAI response, show a source citation and the submitted-scenario snapshot. Explain that Python supplies those exact values. Expand Engineering View and refresh it; point to the request ID, status, duration, provider and token usage. The cost is a configured estimate, and the traces belong only to this session.
4. **2:15–3:00 — Voice and delivery boundaries.** Open the receptionist demonstration and play a short portion. Explicitly call it a **recording**, not a live voice agent. Sales/appointment live demos remain disabled. Finish by describing the separately verified dedicated-project queued research flow and the still-unverified native CRM delivery.

For a longer interview, ask for audited company profit or verified competitor rankings and inspect the unsupported-claim response. Prepare an implementation plan to demonstrate draft-only persistence: an internal CRM task requires a separate approved administrative action and cohort/suppression checks. No outreach is sent by saving the draft.

The v1.1 client-link/disclosure extension is deployed and verified. Explain its design using [client-links.md](client-links.md): `/p?client=<nonsecret-id>#<secret-token>` identifies the company in the query and authorizes through a secret fragment. The browser removes the fragment before DOM/API work; Python checks that both token and cookie belong to that client. Two private dashboards passed HTTP/browser checks with saved public research/Google attribution and cited recruiter hypotheses. HighLevel's native trigger target/project tags passed API readback; per-recipient redirect remains unverified and the requested click→30-minute human email/SMS workflow is saved as a draft. Explain the verified dashboard separately from the unexecuted native workflow.

## Follow the code in this order

**`schemas.py`: contracts before behavior.** Pydantic bounds rates to fractions, validates money, rejects NaN/Infinity, and defines the response shape. Structured Outputs solves formatting; separate Python checks address evidence/numerical safety. Explain that “valid JSON” and “true claim” are different requirements.

**`simulator.py`: a pure function.** `calculate(SimulatorInput)` has no database/network/model dependency. Decimal arithmetic avoids binary floating-point money surprises. Derived values retain precision until display rounding. Unit tests cover expected-value customers, zero inputs, undefined ratios, invalid currency divisors and monetary rounding. The model never supplies numeric results.

**`advisor.py`: constrained generation.** `OpenAI(...).responses.parse` produces a Pydantic `AdvisorAnswer` using a configurable model. The server builds company/source context and recent session history, sends `store=False`, handles refusal/incomplete output, and reads actual SDK usage. Complete excerpt matching prevents an unsupported statement from borrowing a real citation or dropping a negation. A finite opportunity catalogue keeps unvalidated factual/numerical prose out of recommendations. The model selects solutions/evidence; reviewed templates describe them as hypotheses.

For a recruiting example, ask whether the application can connect to recruiting. The reviewed answer proposes a Python/FastAPI recruiter briefing or scheduling handoff and cites saved recruiting evidence. It leaves candidate ranking and hiring decisions with people. The actual deployed recruiting question passed without unrelated scenario numbers or withheld-content warnings. Google attribution's iframe now preserves its same origin while sandbox/CSP block scripts; other private routes retain denied framing.

**`main.py`: orchestration.** Dependency injection separates authorization, database and provider boundaries. Request processing authenticates a session, validates CSRF, loads cached research, reserves AI budget, calculates a scenario, calls the advisor, persists history/usage and returns citations/results. No research/model request occurs on initial dashboard load.

**`db.py`: persistence and concurrency.** SQLAlchemy works with SQLite locally and pg8000 through Cloud SQL in deployment. Durable tables hold profiles/research, access links, sessions, messages, usage, request traces and review drafts. Tokens are cryptographically random and only their digests are stored. SQL locking enforces shared limits across replicas; a process-local lock alone would not be sufficient. Link revocation invalidates existing sessions.

**`integrations.py`: provider boundaries.** Secret Manager reads keys only on the server. HighLevel checks returned tenant and record identity, preserves unknown/DND policies, and uses bounded 429 retry on reads. Mutations are not blindly retried. Vertex retains only grounding-supported segments with source metadata. Cloud Tasks authenticates the worker and retries at least once; the worker uses compare-and-set state, a lease and cached completion.

**`voice.py`: third-party isolation.** The native LeadConnector embed is reused through a separate service/origin with no private APIs or secrets. That prevents provider JavaScript from reading the personalized application's session. Existing production widget IDs are denied; no microphone/call is started automatically. An adapter and a real isolated audio test are different deliverables.

## Technical questions worth practicing

| Question | Defensible answer |
| --- | --- |
| Why not let the LLM calculate revenue? | Model arithmetic is not an authority. Python produces one reproducible result; the model selects explanatory context, and the API owns displayed numbers. |
| Does schema validation prevent hallucinations? | No. It constrains structure. The application additionally validates sources, preserves full excerpt context, uses a reviewed catalogue and abstains on unsupported content. |
| How is it personalized? | Approved HighLevel first-name/company/website context is saved, research and intelligence are completed before access, and every dashboard/chat session is scoped to one stored prospect. Email/phone stay out of the dashboard. |
| Why a client query and secret fragment? | The query identifies the prospect but grants no access. The browser never sends the fragment in the initial HTTP URL; it exchanges the capability by POST, removes it and uses a cookie. Token/client and cookie/client mismatches fail before returning research. These boundaries passed deployed HTTP/browser checks. |
| How does HighLevel follow up? | The dedicated native trigger target/project tags passed API readback. The design resolves the recipient's dashboard URL field, then starts the requested 30-minute wait and human email/SMS questions. Recipient redirect is unverified and the workflow is saved as a draft, so no timed-delivery claim. It respects suppression/language rules and remains separate from draft-only implementation requests. |
| Is it multi-provider? | OpenAI supplies structured business advice, Google Vertex supplies Search-grounded research, and LeadConnector supplies native voice capabilities. Each has an independent boundary and verification status. |
| What happens on provider failure? | The cached dashboard still loads. Failed chat returns a safe error and consumes an attempt budget; refused/incomplete research does not mint access. A worker failure leaves a retryable state. Unknown CRM delivery is reconciled before another attempt. |
| How do you prevent duplicate actions? | Research uses state CAS and a retry lease; completed retries read the cache. Task delivery claims the draft once and verifies provider readback. It is not a distributed exactly-once guarantee; crash-window reconciliation remains explicit. |
| How are costs tracked? | Actual input, cached-input and output usage from the SDK; estimates use configured model rates and a dated reference. Missing rates yield null. Call limits are not a dollar budget. |
| What is currently operational? | Canonical OpenAI chat, Python simulator, SQL history and Engineering View are browser-verified. Cloud Run/SQL/secrets/logging are verified. The dedicated project additionally completed a live Tasks/Google/OpenAI/SQL research job. Public source and initial GitHub CI passed. The receptionist is a recording; delivered CRM follow-up and isolated live voice remain unverified. |
| What comes next before production? | Canonical-domain/database migration, versioned schema migrations, retention/rate policy, production database sizing/availability, native CRM redirect and delivery verification, account-side analytics readback, and a dedicated isolated voice agent with post-call readback. |

## Verification design

Offline tests require no credentials and exercise behavior rather than calling production systems. They include the official SDK request/parse shape with a mock HTTP transport; complete CRM/research/dashboard/follow-up orchestration with fakes; parallel budget races; cross-session privacy; token revocation; unsafe claims/numbers; DND and tenant rejection; and task outcome reconciliation.

Live smoke tests are separate, explicit and synthetic-only. They establish provider behavior for the tested model/configuration. Browser checks validate the actual served frontend, slider changes, cited chat, numerical snapshots, recorded playback, responsive layout and request traces. Docker/GitHub/cloud claims require their own completed build/run/dispatch verification.
