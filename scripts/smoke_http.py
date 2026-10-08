"""Verify a running local, credential-free ProspectIQ demo over real HTTP.

Only loopback HTTP origins are accepted. The script refuses provider-backed chat,
never follows external links, and creates only synthetic local session/draft data.
It does not access administrative, cloud, CRM delivery, microphone or call routes.
Responses, session cookies, CSRF tokens and conversation bodies are never printed.
"""
import argparse
import json
import time
from urllib.parse import urlparse

import httpx


class SmokeFailure(Exception):
    """A fixed, non-sensitive diagnostic suitable for CI output."""


def require(condition, diagnostic):
    if not condition:
        raise SmokeFailure(diagnostic)


def local_origin(value):
    parsed = urlparse(value)
    require(parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"},
            "loopback_http_origin_required")
    require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.path in {"", "/"}, "bare_origin_required")
    try:
        parsed.port
    except ValueError:
        raise SmokeFailure("invalid_port") from None
    return value.rstrip("/")


def smoke(base_url="http://127.0.0.1:8093", ready_timeout=30):
    base_url = local_origin(base_url)
    checks = {}
    http_checks = 0

    def request(client, method, path, expected=200, **kwargs):
        nonlocal http_checks
        response = client.request(method, path, **kwargs)
        require(response.status_code == expected, f"{method}_{path}_expected_{expected}_got_{response.status_code}")
        http_checks += 1
        return response

    with httpx.Client(base_url=base_url, timeout=10, follow_redirects=False, trust_env=False) as first, \
            httpx.Client(base_url=base_url, timeout=10, follow_redirects=False, trust_env=False) as second:
        deadline = time.monotonic() + ready_timeout
        while True:
            try:
                health_response = first.get("/health", timeout=2)
                if health_response.status_code == 200:
                    break
            except httpx.RequestError:
                pass
            require(time.monotonic() < deadline, "health_readiness_timeout")
            time.sleep(.5)
        health = health_response.json()
        http_checks += 1
        require(health.get("status") == "ok" and health.get("database") == "connected", "health_database_not_ready")
        require(health.get("advisor_mode") == "guided_demo", "provider_mode_refused_before_chat")
        checks["health_database"] = True

        index = request(first, "GET", "/")
        require("text/html" in index.headers.get("content-type", "") and "ProspectIQ" in index.text,
                "dashboard_html_missing")
        for path in ("/static/styles.css", "/static/app.js", "/static/voice.html", "/static/voice.js"):
            require(bool(request(first, "GET", path).content), "static_asset_empty")
        checks["dashboard_static_assets"] = True

        require(request(first, "GET", "/api/history", expected=401).status_code == 401, "anonymous_history_not_blocked")
        response = request(first, "GET", "/api/demo")
        demo = response.json()
        require(demo.get("advisor_mode") == "guided_demo", "provider_mode_refused_before_chat")
        require(demo["prospect"]["synthetic"] is True and demo["sources"]
                and all(source["is_synthetic"] for source in demo["sources"]), "synthetic_fixture_required")
        require(all(agent["mode"] in {"recorded", "disabled"} for agent in demo["voice_agents"]),
                "live_voice_configuration_refused")
        require("HttpOnly" in response.headers.get("set-cookie", "")
                and "SameSite=strict" in response.headers.get("set-cookie", "")
                and response.headers.get("cache-control") == "no-store", "session_cookie_or_cache_policy_failed")
        csrf = {"X-CSRF-Token": demo["csrf_token"], "Origin": base_url}
        require(request(first, "GET", "/api/dashboard").json()["prospect"] == demo["prospect"],
                "personalized_dashboard_changed")
        engineering = request(first, "GET", "/api/engineering").json()
        require(engineering["integrations"]["database"].startswith("Local SQLite connected"),
                "cloud_database_configuration_refused")
        require(engineering["integrations"]["crm"] == "Server-side adapter; writes disabled", "crm_delivery_configuration_refused")
        checks["synthetic_session_and_safe_configuration"] = True

        defaults = demo["simulator_defaults"]
        request(first, "POST", "/api/simulate", expected=403, json=defaults)
        request(first, "POST", "/api/simulate", expected=403,
                headers={**csrf, "Origin": "https://invalid-origin.example"}, json=defaults)
        checks["csrf_and_origin_enforced"] = True
        baseline = request(first, "POST", "/api/simulate", headers=csrf, json=defaults).json()
        require(baseline["results"]["monthly_revenue"] == 8100
                and baseline["results"]["annual_revenue"] == 97200
                and baseline["results"]["new_customers"] == 6.75, "default_scenario_mismatch")
        edited = {**defaults, "monthly_leads": 400}
        scenario = request(first, "POST", "/api/simulate", headers=csrf, json=edited).json()
        require(scenario["results"]["monthly_revenue"] == 10800
                and scenario["results"]["annual_revenue"] == 129600
                and scenario["results"]["new_customers"] == 9, "edited_scenario_mismatch")
        checks["python_simulator_default_and_edited"] = True

        marker = "Synthetic container smoke: How can we handle after-hours calls?"
        chat = request(first, "POST", "/api/chat", headers=csrf,
                       json={"message": marker, "scenario": edited}).json()
        require(chat["provider"] == "guided_demo" and chat["usage"]["input_tokens"] == 0
                and chat["usage"]["output_tokens"] == 0, "guided_chat_or_zero_usage_failed")
        require(chat["scenario"] == scenario, "advisor_changed_python_scenario")
        require(chat["citations"] and all(source["is_synthetic"] for source in chat["citations"]),
                "synthetic_citations_missing")
        history = request(first, "GET", "/api/history").json()["messages"]
        require(len(history) == 2 and history[0] == {"role": "user", "content": marker}
                and history[1]["role"] == "assistant", "conversation_history_failed")
        trace = request(first, "GET", "/api/engineering")
        engineering = trace.json()
        require(any(item["request_id"] == chat["request_id"] and item["route"] == "/api/chat"
                    and item["status"] == 200 for item in engineering["recent_requests"]), "chat_trace_missing")
        require(marker not in trace.text and demo["csrf_token"] not in trace.text
                and first.cookies.get("prospectiq_session") not in trace.text, "engineering_sensitive_content_found")
        checks["guided_chat_citations_history_and_trace"] = True

        second_demo = request(second, "GET", "/api/demo").json()
        require(request(second, "GET", "/api/history").json()["messages"] == [], "cross_session_history_leak")
        other_trace = request(second, "GET", "/api/engineering")
        require(chat["request_id"] not in other_trace.text and marker not in other_trace.text
                and all(item["route"] != "/api/chat" for item in other_trace.json()["recent_requests"]),
                "cross_session_trace_leak")
        checks["cross_session_privacy"] = True

        draft = request(first, "POST", "/api/follow-up", headers=csrf,
                        json={"intent": "Review synthetic container scenario", "notes": "Local smoke; no delivery requested."}).json()
        require(draft["status"] == "draft" and bool(draft["id"]), "follow_up_not_draft")
        checks["local_draft_only"] = True
        request(first, "DELETE", "/api/session", headers=csrf)
        request(first, "GET", "/api/history", expected=401)
        request(second, "DELETE", "/api/session",
                headers={"X-CSRF-Token": second_demo["csrf_token"], "Origin": base_url})
        request(second, "GET", "/api/engineering", expected=401)
        checks["session_logout"] = True

    return {"status": "PASS", "synthetic_only": True, "provider_calls": 0,
            "http_checks": http_checks, "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8093", help="Running local demo's loopback HTTP origin")
    args = parser.parse_args()
    try:
        report = smoke(args.base_url)
    except SmokeFailure as error:
        print(json.dumps({"status": "FAIL", "diagnostic": str(error)}, sort_keys=True))
        raise SystemExit(1) from None
    except Exception as error:
        print(json.dumps({"status": "FAIL", "error_type": type(error).__name__,
                          "diagnostic": "Unexpected local smoke failure; response bodies and credentials omitted"}, sort_keys=True))
        raise SystemExit(1) from None
    print(json.dumps(report, sort_keys=True))
