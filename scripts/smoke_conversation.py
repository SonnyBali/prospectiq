"""Explicit paid regression verification of the public synthetic advisor conversation.

Requires --paid-synthetic-chat. A single synthetic session receives exactly three
HTTP chat requests, each of which may make multiple OpenAI calls for generation
and review. Returned usage and API-call totals are reported without alteration.
No research, CRM, draft-follow-up, voice, provisioning or private-contact route
is used. Both verification sessions are ended and checked for unauthorized access.
Only the canonical and dedicated FireWire staging HTTPS origins are accepted.
Redirects are never followed. Output contains fixed diagnostics/checks, safe
request IDs and numeric usage, never session/CSRF tokens, cookies, prompts or
response bodies. Session cleanup is also attempted when a check fails.
"""

import argparse
import json
import math
import re

import httpx

from smoke_deployed import (
    CANONICAL_ORIGIN,
    FIREWIRE_NATIVE_ORIGIN,
    SmokeFailure,
    approved_origin,
    require,
)

CONVERSATION_ORIGINS = {CANONICAL_ORIGIN, FIREWIRE_NATIVE_ORIGIN}
MESSAGES = (
    "For this fictional company, recommend one way to improve after-hours calls.",
    "How does it work?",
    "Cost?",
)


def normalized_reply(reply):
    """Ignore capitalization, punctuation and spacing when detecting repetition."""
    return " ".join(re.findall(r"\w+", reply.casefold()))


def validated_usage(chat):
    require(chat.get("provider") == "openai", "actual_openai_provider_required")
    usage = chat.get("usage")
    require(isinstance(usage, dict), "actual_provider_usage_missing")
    for field in ("input_tokens", "output_tokens", "api_calls"):
        require(type(usage.get(field)) is int and usage[field] > 0, "actual_provider_usage_missing")
    require(type(usage.get("cached_input_tokens")) is int
            and 0 <= usage["cached_input_tokens"] <= usage["input_tokens"], "invalid_cached_provider_usage")
    cost = usage.get("estimated_cost_usd")
    require(cost is None or (type(cost) in {int, float} and math.isfinite(cost) and cost >= 0),
            "invalid_server_cost_estimate")
    require(cost is None or bool(usage.get("price_reference")), "cost_estimate_reference_missing")
    return {field: usage[field] for field in (
        "input_tokens", "output_tokens", "cached_input_tokens", "api_calls", "estimated_cost_usd")}


def smoke(base_url=CANONICAL_ORIGIN, origin=CANONICAL_ORIGIN, *, allow_paid=False):
    require(allow_paid is True, "explicit_paid_synthetic_chat_opt_in_required")
    base_url = approved_origin(base_url)
    origin = approved_origin(origin)
    require(base_url in CONVERSATION_ORIGINS and origin in CONVERSATION_ORIGINS,
            "conversation_origin_not_explicitly_approved")
    require(base_url == origin, "conversation_requires_matching_same_origin")
    checks = {}
    http_checks = 0
    chat_requests = 0
    replies = []
    usage_records = []
    request_ids = []
    cleanup_sessions = []

    def request(client, method, path, expected=200, **kwargs):
        nonlocal http_checks, chat_requests
        require((method, path) in {
            ("GET", "/health"), ("GET", "/api/demo"), ("GET", "/api/history"),
            ("POST", "/api/chat"), ("DELETE", "/api/session"),
        }, "verification_route_not_allowed")
        if path == "/api/chat":
            require(chat_requests < len(MESSAGES), "additional_chat_request_refused")
            chat_requests += 1
        response = client.request(method, path, **kwargs)
        require(response.status_code == expected,
                f"{method}_{path}_expected_{expected}_got_{response.status_code}")
        http_checks += 1
        return response

    with httpx.Client(base_url=base_url, timeout=90, follow_redirects=False, trust_env=False) as first, \
            httpx.Client(base_url=base_url, timeout=90, follow_redirects=False, trust_env=False) as second:
        try:
            health = request(first, "GET", "/health").json()
            require(health.get("status") == "ok" and health.get("database") == "connected"
                    and health.get("advisor_mode") == "openai", "database_and_openai_not_ready")
            checks["health_database_and_openai_configuration"] = True

            request(first, "GET", "/api/history", expected=401)
            response = request(first, "GET", "/api/demo")
            demo = response.json()
            require(demo.get("advisor_mode") == "openai" and demo["prospect"]["synthetic"] is True
                    and demo["sources"] and all(source["is_synthetic"] is True for source in demo["sources"]),
                    "openai_synthetic_fixture_required")
            csrf = {"X-CSRF-Token": demo["csrf_token"], "Origin": origin}
            require(bool(csrf["X-CSRF-Token"]) and bool(first.cookies.get("prospectiq_session")),
                    "session_credentials_missing")
            cleanup_sessions.append((first, csrf))
            cookie_header = response.headers.get("set-cookie", "")
            require("HttpOnly" in cookie_header and "Secure" in cookie_header and "SameSite=strict" in cookie_header,
                    "secure_session_cookie_policy_failed")
            require(request(first, "GET", "/api/history").json()["messages"] == [],
                    "first_session_not_empty")
            checks["fresh_secure_synthetic_session"] = True

            for message in MESSAGES:
                chat = request(first, "POST", "/api/chat", headers=csrf, json={"message": message}).json()
                require(chat.get("advisor_status") == "completed", "accepted_advisor_reply_required")
                usage_records.append(validated_usage(chat))
                request_id = chat.get("request_id")
                require(isinstance(request_id, str) and re.fullmatch(r"[a-f0-9]{32}", request_id) is not None,
                        "safe_request_id_missing")
                request_ids.append(request_id)
                reply = chat.get("plain_reply")
                require(isinstance(reply, str) and reply == chat["answer"]["summary"]
                        and 5 <= len(reply.split()) <= 100, "short_matching_plain_reply_required")
                require(not any(label in reply for label in (
                    "Hypothesis:", "Limits and unknowns", "Evidence-based guidance", "E2", "E3")),
                    "technical_warning_labels_returned")
                require(chat.get("scenario") is None and chat.get("scenario_explanation_included") is False,
                        "unrequested_scenario_numbers_returned")
                replies.append(reply)
            require(chat_requests == 3 and len(set(request_ids)) == 3, "three_distinct_chat_requests_required")
            checks["three_real_openai_chats_with_aggregated_usage"] = True
            checks["three_short_plain_replies_without_scenario_numbers"] = True

            require(len(set(replies)) == 3 and len({normalized_reply(reply) for reply in replies}) == 3,
                    "repeated_advisor_reply")
            checks["distinct_recommendation_workflow_and_cost_replies"] = True

            workflow_words = set(re.findall(r"\w+", replies[1].casefold()))
            require(bool(workflow_words & {"caller", "callers", "call", "calls"})
                    and bool(workflow_words & {"name", "number", "contact", "details", "request", "requests",
                                               "reason", "availability", "message", "messages"})
                    and bool(workflow_words & {"team", "staff", "person", "handoff", "forward", "review", "human"}),
                    "follow_up_workflow_detail_missing")
            checks["how_it_works_explains_intake_and_handoff"] = True

            cost_reply = replies[2].casefold()
            require(any(term in cost_reply for term in ("pricing", "price", "cost", "quote"))
                    and any(term in cost_reply for term in (
                        "quote", "unknown", "not ", "isn't", "isn’t", "don't", "don’t", "confirm", "depends")),
                    "cost_requires_unknown_pricing_or_quote_wording")
            require(not any(character.isdigit() for character in cost_reply)
                    and re.search(r"[$€£¥]|\b(?:usd|dollars?)\b", cost_reply) is None,
                    "unverified_cost_or_simulator_selling_price_returned")
            checks["cost_does_not_invent_price_or_use_simulator_assumption"] = True

            expected_history = [item for message, reply in zip(MESSAGES, replies) for item in (
                {"role": "user", "content": message}, {"role": "assistant", "content": reply})]
            history = request(first, "GET", "/api/history").json()["messages"]
            require(history == expected_history and len(history) == 6, "exact_six_message_history_required")
            checks["history_matches_all_six_conversation_messages"] = True

            second_demo = request(second, "GET", "/api/demo").json()
            require(second_demo["prospect"]["synthetic"] is True, "second_synthetic_session_required")
            second_csrf = {"X-CSRF-Token": second_demo["csrf_token"], "Origin": origin}
            require(bool(second_csrf["X-CSRF-Token"]) and bool(second.cookies.get("prospectiq_session")),
                    "second_session_credentials_missing")
            cleanup_sessions.append((second, second_csrf))
            require(request(second, "GET", "/api/history").json()["messages"] == [], "cross_session_history_leak")
            checks["second_session_has_no_conversation_history"] = True

            for client, headers in tuple(cleanup_sessions):
                request(client, "DELETE", "/api/session", headers=headers)
                cleanup_sessions.remove((client, headers))
                request(client, "GET", "/api/history", expected=401)
            checks["both_sessions_ended_and_unauthorized"] = True
        finally:
            # End only our synthetic sessions; do not retry a paid chat on failure.
            for client, headers in cleanup_sessions:
                try:
                    client.delete("/api/session", headers=headers)
                except Exception:
                    pass

    known_costs = [usage["estimated_cost_usd"] for usage in usage_records]
    totals = {field: sum(usage[field] for usage in usage_records) for field in (
        "input_tokens", "output_tokens", "cached_input_tokens", "api_calls")}
    totals["estimated_cost_usd"] = sum(known_costs) if all(cost is not None for cost in known_costs) else None
    return {"status": "PASS", "synthetic_only": True, "same_origin": True, "chat_requests": chat_requests,
            "http_checks": http_checks, "checks": checks, "request_ids": request_ids,
            "usage_per_chat": usage_records, "usage_totals": totals,
            "cost_note": "Sum of server estimates across all generation and review calls; not an invoice"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=CANONICAL_ORIGIN, help="Exact canonical or dedicated staging HTTPS origin")
    parser.add_argument("--origin", default=CANONICAL_ORIGIN, help="Same approved origin as --base-url")
    parser.add_argument("--paid-synthetic-chat", action="store_true", help="Opt in to exactly three paid synthetic chats")
    args = parser.parse_args()
    try:
        report = smoke(args.base_url, args.origin, allow_paid=args.paid_synthetic_chat)
    except SmokeFailure as error:
        print(json.dumps({"status": "FAIL", "diagnostic": str(error)}, sort_keys=True))
        raise SystemExit(1) from None
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "diagnostic": "Conversation smoke failed; credentials and response bodies omitted"}, sort_keys=True))
        raise SystemExit(1) from None
    print(json.dumps(report, sort_keys=True))
