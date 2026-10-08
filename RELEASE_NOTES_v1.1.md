# ProspectIQ v1.1

October 8, 2026. This release adds secure client-specific entry and staffing-focused opportunity hypotheses to the Python/FastAPI application. The public recruiter demonstration is already verified at [prospect.firewireads.com](https://prospect.firewireads.com/). Publication of the v1.1 GitHub repository/tag and deployment of the new serving image are separate checkpoints; use [the release record](docs/live-release.md) for confirmed revision, image and live results.

## Publication and deployment checklist

- [x] Full v1.1 suite: 212 pytest tests passed on Windows and inside the rebuilt Linux image.
- [x] Private-entry/disclosure frontend: 38 offline VM cases passed; JavaScript syntax passed.
- [x] Analytics privacy: 346 offline assertions passed.
- [x] Recruiter catalogue: focused advisor/security tests and Ruff passed.
- [x] Local `v1.1.0-release` Docker image rebuilt successfully.
- [x] Immutable registry image publication confirmed.
- [x] New Cloud Run revision `prospectiq-00006-ksp` Ready with 100% traffic.
- [x] Canonical v1.1 workflow: 25 HTTP checks with actual OpenAI passed.
- [x] Canonical v1.1 request and completed usage independently matched in Cloud Logging.
- [x] Two private dashboards: 18 HTTP checks and actual Chrome cited-advisor checks passed.
- [x] Canonical OpenAPI returned HTTP 200 with version `1.1.0`.
- [x] Pre-publication privacy audit: 70 files, actual-secret comparison and private-artifact fingerprint checks passed with zero findings.
- [ ] Public GitHub repository and v1.1 tag publication confirmed.
- [ ] Actual GitHub CI run completed successfully.

The current live infrastructure remains in `ai-leadscore/us-central1`. `firewireads-platform` is being prepared; no completed migration or serving deployment there is established by these source/image checks. The operational project and serving revision are recorded in [live-release.md](docs/live-release.md).

The dedicated HighLevel global trigger-link target and four project tags passed direct API readback. Tags have not been assigned to contacts by this verification. The timed follow-up workflow is saved as a draft and is not operational; per-recipient redirect and delivered email/SMS remain unverified.

The public [GitHub repository](https://github.com/SonnyBali/prospectiq) is created. Source push, tag and CI remain separate unverified publication checkpoints.

## Client-specific entry and personalization

- Private URLs use `/p?client=<opaque-prospect-id>#<secret-access-token>`. The client query identifies the prospect without authorizing access. The secret stays in the fragment, outside the initial HTTP request URL, and is removed before DOM/API work.
- The existing access exchange now binds the capability to the requested client. Cookie-based reloads must match that same client before research is returned. Root query entries normalize to the private path; legacy fragment links remain supported.
- Invalid or ambiguous links fail closed. A failed exchange cannot use the retry action to display an older company's cookie session. Private entry remains noindex, restrictive in CSP, and outside marketing tracking.
- The dashboard explicitly identifies AI personalization. Fictional demo data remains labeled synthetic; Google-attributed public website research and imported business evidence use distinct, truthful disclosure copy. No customer performance metrics are invented.
- The HighLevel adapter targets the dedicated `contact.prospectiq_dashboard_url` field and one native trigger link resolving each recipient's own URL. Field/link/contact identity, tenant, cohort, suppression and direct readback remain part of the handoff contract. Provisioning, first-client verification and the requested native click→30-minute human email/SMS follow-up require their own live evidence; saving an implementation-plan draft sends no outreach.

See [client-links.md](docs/client-links.md) for the complete contract and intended research-first workflow.

## Recruiter-relevant opportunity hypotheses

The bounded solution catalogue now includes:

- Recruiter briefing assistant
- Candidate scheduling assistant
- Source-grounded company research
- Candidate communication review

One immutable Python catalogue supplies both the model prompt and server acceptance/templates, avoiding separate title lists that drift. These new recommendations require relevant staffing/recruiting or technology terms in their own cited saved excerpts. A company name, a source URL or an uncited relevant source does not establish that relevance. The template text presents a testable hypothesis for human review rather than claiming an integration is operational.

This scope fits the public staffing/RPO and technology context described on [Insight Global's official talent-services page](https://insightglobal.com/services/talent-services/). Production answers still depend on the company's stored source citations; that reference is not hardcoded company knowledge in the advisor. Recommendations do not assume missed calls, revenue losses or private hiring plans, and do not automate candidate ranking or hiring decisions.

Company factual claims still require equality with the complete retained source excerpt. Generated summaries and rationale prose cannot bypass that rule. Python remains the authority for simulator amounts; the existing reviewed revenue-scenario template uses only the server's calculated results. Typed Pydantic parsing through the official SDK's Responses API remains in place, following [OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Verification and remaining boundaries

The full suite passed **212 pytest tests on Windows and in the rebuilt Linux image**; the Linux run completed in 17.24 seconds. Its advisor/catalogue subset separately passed 40 focused advisor/security tests and Ruff; these are a subset, not an additional total. The frontend passed 38 offline private-entry/disclosure VM cases, JavaScript syntax and 346 analytics privacy assertions. These tests used mocks/fixtures and did not call live providers, access real candidate records or send communications.

The deployed canonical v1.1 smoke separately passed 25 HTTP checks with real synthetic OpenAI, SQL history/traces, privacy, cookies and logout. Its exact request/completed usage independently matched Cloud Logging on the serving revision. Two private dashboards passed 18 HTTP checks covering cached public sources/Google attribution, client-bound cookies, wrong-ID rejection, query-only unauthorized access and private CSP/tracking isolation. Actual Chrome private advisor returned cited recruiter-briefing and candidate-scheduling hypotheses. Canonical OpenAPI returned HTTP 200/version `1.1.0`. These results establish the tested dashboard flow; they do not establish native HighLevel redirect or delivered timed follow-up.

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_advisor.py tests/test_security_review.py
.venv/Scripts/python.exe -m ruff check app/advisor.py tests/test_advisor.py
node --check app/static/app.js
node scripts/test_private_entry.mjs
node scripts/test_analytics.mjs
```

The deployed public application already has separate Cloud Run, Cloud SQL, Secret Manager/OpenAI and Cloud Logging evidence. Live queued first-client research, actual HighLevel trigger-link resolution/timed follow-up, isolated live voice audio and GitHub CI must not be inferred from local code/tests. The receptionist demonstration remains a recording. Account-side Google/Meta reporting is separate from the browser page-view requests already observed.

Public release preparation must exclude real client exports, private capability URLs, database files, credentials and private verification artifacts. Use synthetic fixtures and redacted evidence in the repository. [Deployment instructions](docs/deployment.md), [the interview guide](docs/interview-guide.md) and [the verification record](docs/verification.md) explain the implementation and its tested limits.
