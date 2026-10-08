# Personalized client links and HighLevel handoff

Updated October 8, 2026. The public recruiter application and v1.1 client query-link/disclosure extension are deployed and verified at [prospect.firewireads.com](https://prospect.firewireads.com/). Two private dashboards passed 18 HTTP checks and actual Chrome cited-advisor checks using saved public research/Google attribution. The dedicated native HighLevel trigger target/project tags passed API readback; per-recipient redirect remains unverified and the 30-minute follow-up workflow is saved as a draft. Exact serving/image and redacted evidence are in [live-release.md](live-release.md).

## A unique URL for each client

New private access links use this format:

```text
https://prospect.firewireads.com/p?client=<opaque-prospect-id>#<secret-access-token>
```

`client` is the application prospect's nonsecret identifier, not a HighLevel contact ID and not authorization. The fragment holds the random bearer capability. Browsers do not send URL fragments in the initial HTTP request, so Cloud Run's automatic request URL contains the client identifier without the token. The complete URL is still confidential: the fragment grants access and must not be copied into public documentation, screenshots, analytics or logs.

At script startup, the browser removes the fragment before DOM setup or API requests. It retains only the validated client identifier and drops unrelated CRM query parameters. A root entry such as `/?client=<id>#<token>` normalizes to `/p?client=<id>`. The browser sends `{token, client_id}` to the existing canonical-only `POST /api/access`; Python verifies the token digest, expiry, revocation and exact prospect match before issuing an HTTP-only session cookie. The default access-link lifetime is 72 hours and the session lifetime is eight hours.

On reload, `/api/dashboard?client=<id>` requires an existing session for that exact prospect before returning its research. A client identifier alone cannot open a dashboard. The frontend also rejects a returned prospect ID that does not match the link. Duplicate/invalid client identifiers and malformed fragments fail closed; a failed token exchange cannot use the retry button to reveal an older company's cookie. Existing `/p#<token>` links remain supported.

Private entry pages, including root query entries, receive noindex, a restrictive Content Security Policy and a no-referrer policy. They never initialize marketing tracking, including a private synthetic fixture. The public recruiter page continues its separately verified marketing behavior. Tokens stay out of browser storage; provider API keys stay on the server.

## HighLevel contact field and trigger link

The implementation targets one dedicated contact field and one reusable native trigger link within the verified FireWire tenant:

| Resource | Contract |
| --- | --- |
| Contact field | Name `ProspectIQ Dashboard URL`; key `contact.prospectiq_dashboard_url`; contact model, TEXT type |
| Contact field value | That contact's complete, newly issued private URL, including its fragment |
| Global trigger link | Name `ProspectIQ Dashboard`; destination `{{contact.prospectiq_dashboard_url}}` |
| Message merge key | Provider-verified `{{trigger_link.<link-id>}}`; use the actual returned key, not a guessed ID |

The global trigger link is shared configuration; its destination resolves through each recipient's own field. The URL remains specific to that client. The adapter checks resource identity, tenant and readback, blocks ambiguous duplicates, and updates only the dedicated field. A contact update requires a linked nonsynthetic prospect, the approved cohort and permitted suppression state. `ALLOW_CRM_LINKS` defaults to false; field/link setup and any existing automation reacting to that field must be verified before enabling contact updates. An uncertain write is reconciled before retry.

The dedicated native trigger target and four project tags were provisioned and verified through direct API readback; tags were not assigned to contacts by that check. A native recipient test still needs to confirm the merge resolves and preserves the secret fragment through the redirect. The timed workflow is saved as a draft, not operational. Saving a URL does not itself send a message or enroll a workflow.

## Research before the invitation

The intended operational sequence is:

1. Select an owner-approved client, verify the FireWire tenant/cohort and save minimal first-name/company/website context.
2. Run real Google Search-grounded website research through the authenticated research worker. Save supported findings, source URLs/excerpts, observation dates and Google's grounding attribution; generate the company's intelligence with the configured OpenAI advisor.
3. Wait for completed research and intelligence. Only then issue the unique private access URL; a pending or failed research job cannot mint access.
4. Store and directly verify the issued URL in the dedicated HighLevel contact field. Send the invitation using the verified native trigger-link merge key.
5. The client clicks the trigger link, opens their saved dashboard immediately, sees the personalization disclosure, explores cited findings, changes simulator assumptions and asks company-specific questions.
6. HighLevel's trigger-link click starts the requested native workflow. After **30 minutes from the click**, send a short human email and SMS asking what stood out and whether the client has questions. Recipient language, channel permission, DND/opt-out and suppression rules apply. Repeated clicks must not create duplicate follow-ups.

Cached real public-source research, Google attribution and private dashboard exchange were verified. The check observed 14 retained public sources. Live task-worker/queue execution, native recipient merge/redirect and delivered 30-minute email/SMS remain unverified; the native workflow is saved as a draft. No email/SMS was sent and no customer draft was changed by the frontend or documentation work. The timed native workflow is separate from ProspectIQ's implementation-plan draft and separately gated internal HighLevel review task; saving a dashboard draft continues to send no outreach.

## AI personalization and verification

The new disclosure identifies the dashboard as AI-personalized for the company. A Google-attributed research session says it uses saved public website research and explains that findings link to sources while opportunities need the client's confirmation. Imported evidence uses the narrower saved-business-context wording. Synthetic sessions explicitly disclose fictional company data and synthetic evidence. This copy does not invent customer metrics or imply that simulated revenue is observed performance.

The full v1.1 suite passed 212 pytest tests on Windows/Linux. Frontend checks passed JavaScript syntax, 38 offline private-entry/disclosure VM cases and 346 analytics privacy assertions, covering query/legacy exchange, early scrubbing, client-bound reloads, malformed/conflicting links, mismatched identity, failed-exchange retry and private tracking isolation. Deployed private HTTP/browser checks separately verified cached research, client/cookie binding, wrong-ID rejection and private tracking isolation. The saved native workflow is not a delivered follow-up result.

For an interview explanation: “The query identifies which company the page should show, while a secret fragment establishes access. Python binds the capability and cookie to the same prospect. HighLevel tracks the native link click; research is completed before the invitation, so the personalized dashboard loads from saved evidence.”
