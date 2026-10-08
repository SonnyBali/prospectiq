"""Explicit paid verification of the approved deployed synthetic ProspectIQ demo.

Requires --paid-synthetic-chat: submits exactly one HTTP chat request to the server,
which uses OpenAI and incurs API cost. Synthetic sessions/history/traces and one
review draft are stored in the application database. No administrative, CRM
delivery, research/queue/provisioning, live voice, microphone or call route is used.
Only the approved HTTPS hosts are allowed; redirects and external links are not
followed. Output contains checks, a request ID and numeric server usage estimates,
never credentials, session/CSRF tokens, cookies, prompts or response bodies.
The default checks the canonical domain. To verify the temporary recruiter demo
as a native same-origin workflow, explicitly set both --base-url and --origin to
the verified public Cloud Run URL below. Only the canonical origin and that exact
temporary origin may supply the browser Origin header.
"""
import argparse
import json
import math
from urllib.parse import urlparse

import httpx

CANONICAL_ORIGIN = "https://prospect.firewireads.com"
NATIVE_DEMO_ORIGIN = "https://prospectiq-s4gztnjt6a-uc.a.run.app"
APPROVED_ORIGINS = {
    CANONICAL_ORIGIN,
    NATIVE_DEMO_ORIGIN,
    "https://prospectiq-1051896753015.us-central1.run.app",
}


class SmokeFailure(Exception):
    """A fixed diagnostic safe to include in verification output."""


def require(condition, diagnostic):
    if not condition:
        raise SmokeFailure(diagnostic)


def approved_origin(value):
    parsed = urlparse(value)
    require(parsed.scheme == "https" and not parsed.username and not parsed.password
            and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment,
            "bare_approved_https_origin_required")
    value = value.rstrip("/")
    require(value in APPROVED_ORIGINS, "origin_not_explicitly_approved")
    return value


def smoke(base_url=CANONICAL_ORIGIN, origin=CANONICAL_ORIGIN, *, allow_paid=False):
    require(allow_paid is True, "explicit_paid_synthetic_chat_opt_in_required")
    base_url = approved_origin(base_url)
    origin = approved_origin(origin)
    require(origin in {CANONICAL_ORIGIN, NATIVE_DEMO_ORIGIN}, "browser_origin_not_explicitly_approved")
    checks = {}
    http_checks = 0
    chat_requests = 0

    def request(client, method, path, expected=200, **kwargs):
        nonlocal http_checks, chat_requests
        if path == "/api/chat":
            require(chat_requests == 0, "additional_chat_request_refused")
            chat_requests += 1
        response = client.request(method, path, **kwargs)
        require(response.status_code == expected, f"{method}_{path}_expected_{expected}_got_{response.status_code}")
        http_checks += 1
        return response

    with httpx.Client(base_url=base_url, timeout=60, follow_redirects=False, trust_env=False) as first, \
            httpx.Client(base_url=base_url, timeout=60, follow_redirects=False, trust_env=False) as second:
        health = request(first, "GET", "/health").json()
        require(health.get("status") == "ok" and health.get("database") == "connected", "health_database_not_ready")
        require(health.get("advisor_mode") == "openai", "openai_not_configured_before_chat")
        checks["health_database_and_openai_configuration"] = True

        index = request(first, "GET", "/")
        require("text/html" in index.headers.get("content-type", "") and "ProspectIQ" in index.text,
                "dashboard_html_missing")
        for path in ("/static/styles.css", "/static/app.js", "/static/voice.html", "/static/voice.js"):
            require(bool(request(first, "GET", path).content), "static_asset_empty")
        checks["dashboard_static_assets"] = True
        request(first, "GET", "/api/history", expected=401)
        response = request(first, "GET", "/api/demo")
        demo = response.json()
        require(demo.get("advisor_mode") == "openai", "openai_not_configured_before_chat")
        require(demo["prospect"]["synthetic"] is True and demo["sources"]
                and all(source["is_synthetic"] is True for source in demo["sources"]), "synthetic_fixture_required")
        require(all(agent["mode"] in {"recorded", "disabled"} for agent in demo["voice_agents"]),
                "live_voice_configuration_refused")
        cookie_header = response.headers.get("set-cookie", "")
        require("HttpOnly" in cookie_header and "Secure" in cookie_header and "SameSite=strict" in cookie_header,
                "secure_session_cookie_policy_failed")
        require(response.headers.get("cache-control") == "no-store"
                and response.headers.get("x-content-type-options") == "nosniff", "response_privacy_headers_failed")
        session_cookie = first.cookies.get("prospectiq_session")
        require(bool(session_cookie) and bool(demo["csrf_token"]), "session_credentials_missing")
        csrf = {"X-CSRF-Token": demo["csrf_token"], "Origin": origin}
        require(request(first, "GET", "/api/dashboard").json()["prospect"] == demo["prospect"],
                "personalized_dashboard_changed")
        engineering = request(first, "GET", "/api/engineering").json()
        require(engineering["integrations"]["database"] == "Cloud SQL configured", "cloud_sql_configuration_required")
        require(engineering["integrations"]["crm"] == "Server-side adapter; writes disabled", "crm_delivery_configuration_refused")
        checks["synthetic_dashboard_secure_session_and_cloud_sql"] = True

        defaults = demo["simulator_defaults"]
        request(first, "POST", "/api/simulate", expected=403, json=defaults)
        request(first, "POST", "/api/simulate", expected=403,
                headers={**csrf, "Origin": "https://invalid-origin.example"}, json=defaults)
        baseline = request(first, "POST", "/api/simulate", headers=csrf, json=defaults).json()
        require(baseline["results"]["monthly_revenue"] == 8100
                and baseline["results"]["annual_revenue"] == 97200
                and baseline["results"]["new_customers"] == 6.75, "default_scenario_mismatch")
        edited = {**defaults, "monthly_leads": 400}
        scenario = request(first, "POST", "/api/simulate", headers=csrf, json=edited).json()
        require(scenario["results"]["monthly_revenue"] == 10800
                and scenario["results"]["annual_revenue"] == 129600
                and scenario["results"]["new_customers"] == 9, "edited_scenario_mismatch")
        checks["csrf_origin_and_python_simulator"] = True

        message = ("For this fictional synthetic company, recommend an after-hours opportunity plan from the stored evidence. "
                   "Explain my revenue scenario using the exact Python results; do not claim actual business performance.")
        chat = request(first, "POST", "/api/chat", headers=csrf,
                       json={"message": message, "scenario": edited}).json()
        require(chat["provider"] == "openai", "actual_openai_provider_required")
        usage = chat["usage"]
        require(type(usage["input_tokens"]) is int and usage["input_tokens"] > 0
                and type(usage["output_tokens"]) is int and usage["output_tokens"] > 0
                and type(usage["cached_input_tokens"]) is int and usage["cached_input_tokens"] >= 0,
                "actual_provider_usage_missing")
        cost = usage["estimated_cost_usd"]
        require(cost is None or (type(cost) in {int, float} and math.isfinite(cost) and cost >= 0),
                "invalid_server_cost_estimate")
        require(cost is None or bool(usage.get("price_reference")), "cost_estimate_reference_missing")
        require(chat["scenario"] == scenario, "advisor_changed_python_scenario")
        source_by_id = {source["id"]: source for source in demo["sources"]}
        require(chat["citations"] and all(source["is_synthetic"] is True and source == source_by_id.get(source["id"])
                                           for source in chat["citations"]), "grounded_synthetic_citations_required")
        require(chat["answer"]["claims"] or chat["answer"]["recommendations"], "supported_advisor_plan_missing")
        require("10,800.00" in chat["answer"]["summary"] and "129,600.00" in chat["answer"]["summary"],
                "authoritative_numerical_explanation_missing")
        checks["one_real_openai_chat_citations_usage_and_unchanged_calculations"] = True

        history = request(first, "GET", "/api/history").json()["messages"]
        require(len(history) == 2 and history[0] == {"role": "user", "content": message}
                and history[1]["role"] == "assistant", "conversation_history_failed")
        trace = request(first, "GET", "/api/engineering")
        traced_chat = next((item for item in trace.json()["recent_requests"] if item["request_id"] == chat["request_id"]), None)
        require(traced_chat is not None and traced_chat["route"] == "/api/chat" and traced_chat["status"] == 200
                and traced_chat["provider"] == "openai", "actual_chat_provider_trace_missing")
        require(traced_chat["usage"] == {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
                                         "estimated_cost_usd": cost}, "trace_provider_usage_mismatch")
        require(message not in trace.text and demo["csrf_token"] not in trace.text and session_cookie not in trace.text,
                "engineering_sensitive_content_found")
        checks["durable_history_and_session_scoped_provider_trace"] = True

        second_demo = request(second, "GET", "/api/demo").json()
        require(second_demo["prospect"]["synthetic"] is True, "second_synthetic_session_required")
        require(request(second, "GET", "/api/history").json()["messages"] == [], "cross_session_history_leak")
        other_trace = request(second, "GET", "/api/engineering")
        require(chat["request_id"] not in other_trace.text and message not in other_trace.text
                and all(item["route"] != "/api/chat" for item in other_trace.json()["recent_requests"]),
                "cross_session_trace_leak")
        checks["cross_session_privacy"] = True

        draft = request(first, "POST", "/api/follow-up", headers=csrf,
                        json={"intent": "Review synthetic deployment verification", "notes": "Synthetic verification; no CRM delivery requested."}).json()
        require(draft["status"] == "draft" and bool(draft["id"]), "follow_up_not_draft")
        checks["synthetic_review_draft_only"] = True
        request(first, "DELETE", "/api/session", headers=csrf)
        request(first, "GET", "/api/history", expected=401)
        request(second, "DELETE", "/api/session",
                headers={"X-CSRF-Token": second_demo["csrf_token"], "Origin": origin})
        request(second, "GET", "/api/engineering", expected=401)
        checks["session_logout"] = True

    return {"status": "PASS", "synthetic_only": True, "browser_origin": origin,
            "same_origin": base_url == origin, "chat_requests": chat_requests,
            "http_checks": http_checks, "checks": checks, "request_id": chat["request_id"],
            "usage": {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
                      "cached_input_tokens": usage["cached_input_tokens"], "estimated_cost_usd": cost},
            "cost_note": "Unmodified server estimate from configured model rates; not an invoice"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=CANONICAL_ORIGIN, help="Exact approved HTTPS dashboard or Cloud Run origin")
    parser.add_argument("--origin", default=CANONICAL_ORIGIN,
                        help="Canonical domain or exact verified temporary demo origin; match --base-url for native same-origin checks")
    parser.add_argument("--paid-synthetic-chat", action="store_true", help="Opt in to one paid synthetic OpenAI chat and one review draft")
    args = parser.parse_args()
    try:
        report = smoke(args.base_url, args.origin, allow_paid=args.paid_synthetic_chat)
    except SmokeFailure as error:
        print(json.dumps({"status": "FAIL", "diagnostic": str(error)}, sort_keys=True))
        raise SystemExit(1) from None
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "diagnostic": "Deployed smoke failed; credentials and response bodies omitted"}, sort_keys=True))
        raise SystemExit(1) from None
    print(json.dumps(report, sort_keys=True))
