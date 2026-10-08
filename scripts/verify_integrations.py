"""Read-only infrastructure verification; never prints secrets or CRM records.

Usage: python scripts/verify_integrations.py --project ai-leadscore
Optional --contact-id reads one tenant-bound contact and emits field presence.
Optional --openai-probe makes one paid, synthetic Responses API request.
No tasks are created, APIs enabled, resources provisioned or outbound CRM writes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.integrations import HighLevelClient, SecretStore, VertexResearch


def gcloud_json(*arguments: str):
    command = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not command:
        return {"status": "unavailable", "reason": "gcloud_not_installed"}, None
    try:
        result = subprocess.run(
            [command, *arguments, "--format=json", "--quiet"],
            capture_output=True, text=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode:
            # Classify without echoing provider response bodies or user data.
            error = result.stderr
            reason = "api_disabled" if "SERVICE_DISABLED" in error or "not enabled" in error else "permission_or_configuration"
            return {"status": "unavailable", "reason": reason}, None
        return {"status": "metadata_verified"}, json.loads(result.stdout or "null")
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"status": "unavailable", "reason": "probe_failed"}, None


def verify(args) -> dict:
    report = {"observed_at": datetime.now(timezone.utc).isoformat(), "project": args.project, "services": {}}
    services = report["services"]
    status, config = gcloud_json("config", "list")
    report["gcloud"] = {**status, "project_matches": (config or {}).get("core", {}).get("project") == args.project}

    status, enabled = gcloud_json("services", "list", "--enabled", f"--project={args.project}")
    enabled_apis = {item.get("config", {}).get("name") for item in enabled or []}
    report["enabled_apis"] = {**status, "relevant": sorted(enabled_apis & {
        "run.googleapis.com", "cloudtasks.googleapis.com", "secretmanager.googleapis.com",
        "logging.googleapis.com", "sqladmin.googleapis.com", "aiplatform.googleapis.com",
    })}

    status, run = gcloud_json("run", "services", "list", f"--project={args.project}", "--platform=managed")
    relevant = [item for item in run or [] if "firewire" in item.get("metadata", {}).get("name", "") or "prospectiq" in item.get("metadata", {}).get("name", "")]
    services["cloud_run"] = {**status, "resources": [{
        "name": item["metadata"]["name"], "url": item.get("status", {}).get("url"),
        "revision": item.get("status", {}).get("latestReadyRevisionName"),
    } for item in relevant], "prospectiq_deployed": any("prospectiq" in item["metadata"]["name"] for item in relevant)}
    # Only the existing FireWire dashboard's health path is probed. No redirects.
    dashboard = next((item for item in relevant if item["metadata"]["name"] == "firewire-hot-dashboard"), None)
    if dashboard:
        url = dashboard.get("status", {}).get("url", "")
        try:
            # Public health contains no CRM record request. Body is discarded.
            response = httpx.get(url + "/health", timeout=15, follow_redirects=False)
            services["cloud_run"]["existing_dashboard_health_http"] = response.status_code
        except (httpx.HTTPError, ValueError):
            services["cloud_run"]["existing_dashboard_health_http"] = "unavailable"

    status, queues = gcloud_json("tasks", "queues", "list", f"--project={args.project}", f"--location={args.region}")
    services["cloud_tasks"] = {**status, "region": args.region, "queues": [{"name": item.get("name"), "state": item.get("state")} for item in queues or []], "enqueue_tested": False}
    if "sqladmin.googleapis.com" in enabled_apis:
        status, instances = gcloud_json("sql", "instances", "list", f"--project={args.project}")
        services["cloud_sql"] = {**status, "instances": [{"name": item.get("name"), "state": item.get("state"), "database_version": item.get("databaseVersion")} for item in instances or []], "connection_tested": False}
    else:
        services["cloud_sql"] = {"status": "unavailable", "reason": "sql_admin_api_not_enabled", "connection_tested": False}

    status, entries = gcloud_json("logging", "read", 'resource.type="cloud_run_revision" AND resource.labels.service_name="firewire-hot-dashboard"', f"--project={args.project}", "--limit=1")
    services["cloud_logging"] = {**status, "entry_found": bool(entries), "write_tested": False}

    status, secrets = gcloud_json("secrets", "list", f"--project={args.project}")
    relevant_secrets = {"OPENAI_API_KEY", "FIREWIRE_GHL_API_KEY", "FIREWIRE_GHL_LOCATION_ID", "GoogleGemini", "PROSPECTIQ_DB_PASSWORD", "PROSPECTIQ_ADMIN_KEY", "PROSPECTIQ_TOKEN_PEPPER"}
    available = sorted(item.get("name", "").rsplit("/", 1)[-1] for item in secrets or [] if item.get("name", "").rsplit("/", 1)[-1] in relevant_secrets)
    services["secret_manager"] = {**status, "available_names": available, "access": {}}
    store = SecretStore(args.project, allow_gcloud_fallback=args.allow_gcloud_fallback)
    private_values = {}
    for name in ("OPENAI_API_KEY", "FIREWIRE_GHL_API_KEY", "FIREWIRE_GHL_LOCATION_ID"):
        if name not in available:
            continue
        try:
            private_values[name] = store.get(name)
            services["secret_manager"]["access"][name] = "nonempty_access_verified"
        except Exception:
            services["secret_manager"]["access"][name] = "unavailable"

    services["highlevel"] = {"status": "not_tested", "reason": "contact_id_not_supplied"}
    if args.contact_id:
        try:
            expected = args.location_id
            actual = private_values.get("FIREWIRE_GHL_LOCATION_ID", "")
            if actual != expected:
                raise RuntimeError("tenant_mismatch")
            contact = HighLevelClient(private_values.get("FIREWIRE_GHL_API_KEY", ""), expected).get_contact(args.contact_id)
            services["highlevel"] = {"status": "contact_read_verified", "tenant_verified": True, "field_presence": {field: bool(contact.get(field)) for field in ("first_name", "company_name", "website")}, "record_output": False}
        except Exception:
            services["highlevel"] = {"status": "unavailable", "reason": "credential_tenant_or_contact_probe_failed"}

    services["vertex_research"] = {"status": "api_enabled_not_invoked" if "aiplatform.googleapis.com" in enabled_apis else "unavailable", "generation_tested": False}
    if args.vertex_probe:
        try:
            result = VertexResearch(args.project, args.region, args.vertex_model, allow_gcloud_fallback=args.allow_gcloud_fallback).research("FireWireAds", "https://firewireads.com")
            services["vertex_research"] = {
                "status": "grounded_research_verified", "generation_tested": True,
                "model": args.vertex_model, "source_count": len(result["sources"]),
                "supported_notes": bool(result["notes"]),
                "attribution_returned": bool(result["search_suggestions_html"]),
                "crm_data_sent": False,
            }
        except Exception:
            services["vertex_research"] = {"status": "unavailable", "reason": "public_business_grounded_probe_failed", "generation_tested": True}
    services["openai"] = {"status": "not_tested", "reason": "explicit_openai_probe_flag_required"}
    if args.openai_probe:
        try:
            from openai import OpenAI
            with OpenAI(api_key=private_values["OPENAI_API_KEY"], timeout=20, max_retries=0) as client:
                response = client.responses.create(model=args.openai_model, input="Synthetic integration test. Reply with READY only.", max_output_tokens=32, store=False)
            usage = response.usage
            services["openai"] = {
                "status": "responses_verified", "model": response.model,
                "input_tokens": usage.input_tokens if usage else None,
                "output_tokens": usage.output_tokens if usage else None,
                "synthetic_only": True, "stored": False,
            }
        except Exception:
            services["openai"] = {"status": "unavailable", "reason": "synthetic_responses_probe_failed"}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="ai-leadscore")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--allow-gcloud-fallback", action="store_true", help="Explicit local CLI credentials when ADC is absent")
    parser.add_argument("--location-id", default="aFnKcmUdTSPIjo7lCaix")
    parser.add_argument("--contact-id", help="One authorized FireWire contact ID; never included in output")
    parser.add_argument("--openai-probe", action="store_true", help="One paid synthetic Responses request")
    parser.add_argument("--vertex-probe", action="store_true", help="One paid public FireWireAds grounded research request; no CRM data")
    parser.add_argument("--vertex-model", default=os.environ.get("VERTEX_MODEL", "gemini-2.5-flash"))
    parser.add_argument("--openai-model", default=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"))
    args = parser.parse_args()
    print(json.dumps(verify(args), indent=2))


if __name__ == "__main__":
    main()
