# ProspectIQ feedback after a trigger-link click

This is the required FireWireAds workflow behavior and reviewable copy. It does not certify a native workflow as published or any message as delivered. Use the FireWireAds HighLevel location and verified FireWireAds sender/signature. The adjacent comms-system's Houston real-estate executor, credentials, property prompts and broker signature must not be reused.

Trigger on the exact ProspectIQ dashboard trigger link. Reserve one pending feedback pair per contact, suppress repeated clicks while pending, and allow re-entry only after completion, at most once per contact per America/Chicago calendar day. Wait at least 30 minutes after the qualifying click. Stop the pending follow-up if the contact replies during the wait. A click does not establish that the person tried the application.

Send within 09:30–22:00 America/Chicago; Sunday starts at 12:00. If the 30-minute wait ends outside this window, defer until the next permitted window. Re-read current contact/channel eligibility immediately before each send: respect DND, STOP/unsubscribe, suppression, communications pause, missing/invalid destination, existing channel ownership, and applicable contact frequency limits. Do not globally disable caps: authorize only this one email/SMS companion pair, excluding only its already-sent companion from the pair's cap calculation. A failed channel must not cause a duplicate on the successful channel.

Read current tags after the wait and again at each send. Only an exact, trimmed, case-insensitive `Spanish` tag selects Spanish. Every other contact receives English; names, incoming language, history and custom language fields do not change this rule. Native HighLevel actions must implement explicit tag branches for both subject and body at each send; the custom comms-system provider guard does not protect native sends. Block on unavailable tags or language-validation failure. Preserve names, merge fields, URLs and provider control words such as `STOP` when translating.

Keep the note warm and direct, with one easy question. Avoid tracking references, invented claims, booking/calendar links, URLs, emotional check-ins, filler such as “just checking in,” “no pressure,” markdown and dashes. Keep SMS to one or two short sentences, with no greeting or sign-off. Email is a short note with a conversational subject; verify the actual FireWireAds signature before enabling it.

| Channel | English | Spanish, only with the exact tag |
| --- | --- | --- |
| SMS | Allen with FireWireAds here. If you tried ProspectIQ, how did it work for you and what questions came up? | Soy Allen de FireWireAds. Si probaste ProspectIQ, ¿cómo te funcionó y qué preguntas te quedaron? |
| Email subject | {{contact.first_name}}, how did ProspectIQ go? | {{contact.first_name}}, ¿qué tal ProspectIQ? |
| Email body | If you had a chance to try ProspectIQ, how did it work for you and what questions came up? | Si tuviste la oportunidad de probar ProspectIQ, ¿cómo te funcionó y qué preguntas te quedaron? |

Omit the first-name subject prefix if the name is missing or unsuitable. Keep channel status separate: prepared, scheduled, sent and delivered require their own evidence. Log only non-identifying counters, safe status codes and opaque correlation identifiers; never dashboard capability links, contact details, full messages or provider credentials.

The existing 85% trigram repetition guard covers proactive nurture email, and excludes `triggerlink_click_email` and SMS. This flow therefore needs its own pending-event and per-channel deduplication; do not claim the nurture guard protects it.

Policy source audit, 2026-10-08: adjacent `comms-system/src/generator/voice_prompt.js`, `archetype_prompts.js`, `language_policy.js`; `src/ghl/api.js`; `src/sender/drip.js`, `repetition.js`, `batch.js`; `src/decision/compliance_gates.js`; `functions/triggerlink_followup/index.js`; and `docs/spanish-language-rule.md`. This document adapts their general communication rules to FireWireAds and the requested 30-minute feedback pair.
