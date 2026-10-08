"""Explicit paid, synthetic-only test of the complete application Responses path.

Uses Secret Manager; emits only assertions, request IDs, token/cost totals. Never
imports CRM data, queues research, sends follow-up, or deploys anything.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def smoke(model="gpt-4.1-mini"):
    with tempfile.TemporaryDirectory(prefix="prospectiq-synthetic-") as folder:
        settings = replace(Settings.from_env(), database_url=f"sqlite:///{Path(folder) / 'smoke.db'}", cloud_sql_instance="",
                           openai_secret="OPENAI_API_KEY", openai_model=model, admin_secret="",
                           allow_crm_followup=False, allow_cloud_tasks=False,
                           openai_input_rate="0.40" if model == "gpt-4.1-mini" else "",
                           openai_cached_rate="0.10" if model == "gpt-4.1-mini" else "",
                           openai_output_rate="1.60" if model == "gpt-4.1-mini" else "",
                           price_reference="https://developers.openai.com/api/docs/pricing (verified 2026-10-08)" if model == "gpt-4.1-mini" else "")
        with TestClient(create_app(settings)) as client:
            demo = client.get("/api/demo").json()
            csrf = {"X-CSRF-Token": demo["csrf_token"]}
            inputs = {**demo["simulator_defaults"], "monthly_leads": 200}
            expected = client.post("/api/simulate", headers=csrf, json=inputs).json()
            response = client.post("/api/chat", headers=csrf, json={"message": "For this fictional company, recommend an after-hours opportunity plan and explain my revenue scenario using the Python results.", "scenario": inputs})
            assert response.status_code == 200, f"Advisor request failed safely: HTTP {response.status_code}"
            data = response.json()
            assert data["provider"] == "openai"
            assert data["usage"]["input_tokens"] > 0 and data["usage"]["output_tokens"] > 0
            assert data["scenario"]["results"] == expected["results"]
            assert data["answer"]["claims"] or data["answer"]["recommendations"], "Model returned no supported plan"
            assert data["citations"] and all(s["is_synthetic"] for s in data["citations"])
            unsupported = client.post("/api/chat", headers=csrf, json={"message": "What are this fictional company's audited actual annual profits and verified competitor rankings? Only answer if the stored evidence proves it."})
            assert unsupported.status_code == 200
            unknown = unsupported.json()
            assert not unknown["answer"]["claims"] and not unknown["answer"]["recommendations"], "Unsupported facts must be withheld"
            assert unknown["answer"]["unknowns"]
            assert len(client.get("/api/history").json()["messages"]) == 4
            trace = client.get("/api/engineering").json()["recent_requests"]
            assert any(t["request_id"] == data["request_id"] and t["provider"] == "openai" for t in trace)
            return {"status": "passed", "synthetic_only": True, "model": model, "responses_api": True,
                    "source_citations": True, "unsupported_claim_abstention": True, "history": True,
                    "simulator_unchanged": True, "session_scoped_trace": True,
                    "usage_events": [data["usage"], unknown["usage"]], "request_ids": [data["request_id"], unknown["request_id"]]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-4.1-mini")
    args = parser.parse_args()
    try:
        report = smoke(args.model)
    except Exception as error:
        report = {"status": "failed", "error_type": type(error).__name__, "details": "Inspect local assertions; no provider body or credentials are printed"}
        print(json.dumps(report, indent=2))
        raise SystemExit(1) from None
    print(json.dumps(report, indent=2))
