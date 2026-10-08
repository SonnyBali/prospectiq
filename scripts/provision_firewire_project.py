"""Owner-authorized FireWireAds project bootstrap; read-only unless --apply.

Preserves source resources, CLI defaults and ADC configuration. Billing identity
and secret values remain in memory. Uses official Google Auth/Secret Manager SDK
and official Resource Manager, Billing and Service Usage REST APIs. No deployments,
domains, databases, customer tasks, provider calls or service-account keys.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import google.auth
from requests.exceptions import RequestException
from google.auth.transport.requests import AuthorizedSession
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound
from google.oauth2.credentials import Credentials

SOURCE = "ai-leadscore"
DEFAULT_TARGET = "firewireads-platform"
DISPLAY_NAME = "FireWireAds Platform"
SECRETS = ("OPENAI_API_KEY", "FIREWIRE_GHL_API_KEY", "FIREWIRE_GHL_LOCATION_ID", "PROSPECTIQ_ADMIN_KEY")
APIS = ("run.googleapis.com", "sqladmin.googleapis.com", "cloudtasks.googleapis.com",
        "secretmanager.googleapis.com", "logging.googleapis.com", "artifactregistry.googleapis.com",
        "aiplatform.googleapis.com", "compute.googleapis.com", "iam.googleapis.com",
        "iamcredentials.googleapis.com", "cloudresourcemanager.googleapis.com", "serviceusage.googleapis.com")
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class SetupError(RuntimeError):
    pass


def gcloud(*args):
    executable = shutil.which("gcloud") or shutil.which("gcloud.cmd") or shutil.which("gcloud.ps1")
    if not executable and os.name == "nt":
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Cloud SDK/google-cloud-sdk/bin/gcloud.ps1"
        executable = str(candidate) if candidate.is_file() else None
    if not executable:
        raise SetupError("Google Cloud CLI is required for the active-account guard")
    command = [executable]
    if executable.lower().endswith(".ps1"):
        shell = shutil.which("pwsh") or shutil.which("powershell.exe")
        if not shell:
            raise SetupError("PowerShell is required to invoke this installed Google Cloud CLI")
        command = [shell, "-NoProfile", "-NonInteractive", "-File", executable]
    result = subprocess.run([*command, *args, "--quiet"], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise SetupError("Google Cloud CLI read failed; diagnostics omitted")
    return result.stdout.strip()


def request(session, method, url, *, label, **kwargs):
    for attempt in range(4):
        try:
            response = session.request(method, url, timeout=30, **kwargs)
        except RequestException as error:
            raise SetupError(f"{label}: transport {type(error).__name__}; diagnostics omitted") from None
        if response.status_code != 429 or attempt == 3:
            break
        print(json.dumps({"phase": label, "status": "QUOTA_BACKOFF", "attempt": attempt + 1}), flush=True)
        time.sleep(5 * (2 ** attempt))
    if not response.ok:
        raise SetupError(f"{label}: HTTP {response.status_code}; provider body omitted")
    return response.json()


def wait_operation(session, operation, base, label):
    print(json.dumps({"phase": label, "operation": operation.get("name"), "status": "PENDING"}), flush=True)
    deadline = time.monotonic() + 240
    while not operation.get("done"):
        if time.monotonic() >= deadline:
            raise SetupError(f"{label}: operation still pending; reconcile this project before retry")
        time.sleep(3)
        operation = request(session, "GET", f"{base}/{operation['name']}", label=label + "_read")
    if operation.get("error"):
        raise SetupError(f"{label}: operation failed; diagnostics omitted")
    return operation.get("response", {})


def verify_identity(allow_cli, expected_account):
    active = gcloud("auth", "list", "--filter=status:ACTIVE", "--format=value(account)")
    if active.lower() != expected_account:
        raise SetupError("Active CLI identity does not match the authorized FireWireAds account")
    default_project = gcloud("config", "get-value", "project")
    adc, _ = google.auth.default(scopes=SCOPES)
    if hasattr(adc, "with_quota_project"):
        adc = adc.with_quota_project(None)  # In-memory only; userinfo does not accept its quota header.
    with AuthorizedSession(adc) as session:
        identity = request(session, "GET", "https://www.googleapis.com/oauth2/v2/userinfo", label="adc_identity")
    adc_matches = identity.get("email", "").lower() == expected_account
    if not adc_matches and not allow_cli:
        raise SetupError("ADC identity differs; use --use-verified-cli-identity without changing ADC")
    credentials = adc
    if allow_cli:
        token = gcloud("auth", "print-access-token", f"--account={expected_account}")
        credentials = Credentials(token=token)
        with AuthorizedSession(credentials) as session:
            verified = request(session, "GET", "https://www.googleapis.com/oauth2/v2/userinfo", label="cli_token_identity")
        if verified.get("email", "").lower() != expected_account:
            raise SetupError("CLI token identity does not match the authorized FireWireAds account")
    return credentials, default_project, adc_matches


def verify_owned_project(session, target, project, expected_account):
    if project.get("state") != "ACTIVE":
        raise SetupError("Existing target project is not ACTIVE; no alternate project will be created")
    policy = request(session, "POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{target}:getIamPolicy",
                     label="target_owner_read", json={"options": {"requestedPolicyVersion": 3}})
    owner = any(binding.get("role") == "roles/owner" and not binding.get("condition")
                and f"user:{expected_account}" in binding.get("members", []) for binding in policy.get("bindings", []))
    if not owner:
        raise SetupError("Existing target ownership was not verified; no configuration or alternate project creation")
    if project.get("displayName") != DISPLAY_NAME or project.get("labels", {}).get("brand") != "firewireads":
        raise SetupError("Owned target lacks expected FireWireAds identity labels; preserve it and reconcile collision")


def setup(target, apply=False, allow_cli=False, expected_account=""):
    if not re.fullmatch(r"firewireads-[a-z0-9-]{6,18}[a-z0-9]", target) or target == SOURCE:
        raise SetupError("Target must be a dedicated firewireads- project ID, at most 30 characters")
    if not expected_account or "@" not in expected_account:
        raise SetupError("Supply the authorized owner identity with --expected-account or FIREWIRE_GCP_EXPECTED_ACCOUNT")
    expected_account = expected_account.strip().lower()
    credentials, original_default, adc_matches = verify_identity(allow_cli, expected_account)
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    reports = []
    with AuthorizedSession(credentials) as session:
        source_billing = request(session, "GET", f"https://cloudbilling.googleapis.com/v1/projects/{SOURCE}/billingInfo",
                                 label="source_billing_read")
        billing_name = source_billing.get("billingAccountName")
        if not billing_name or not source_billing.get("billingEnabled"):
            raise SetupError("Source project has no enabled billing account; no project creation")
        billing = request(session, "GET", f"https://cloudbilling.googleapis.com/v1/{billing_name}", label="billing_open_read")
        if not billing.get("open"):
            raise SetupError("Source billing account is closed; no project creation")
        search = request(session, "GET", "https://cloudresourcemanager.googleapis.com/v3/projects:search",
                         label="target_search", params={"query": f"id:{target}"})
        matches = [item for item in search.get("projects", []) if item.get("projectId") == target]
        project = matches[0] if matches else None
        if project:
            verify_owned_project(session, target, project, expected_account)
        if not apply:
            return {"status": "PLAN", "target_project": target, "display_name": DISPLAY_NAME,
                    "target_owned_existing": bool(project), "source_billing_verified_open": True,
                    "adc_expected_identity": adc_matches, "credential_source": "verified_cli" if allow_cli else "adc",
                    "apis_to_enable": list(APIS), "secrets_to_copy": list(SECRETS), "cloud_mutations": 0}
        # Preflight source access before creating billable target infrastructure.
        print(json.dumps({"phase": "source_secret_preflight", "status": "STARTED"}), flush=True)
        payloads = {name: client.access_secret_version(name=f"projects/{SOURCE}/secrets/{name}/versions/latest",
                                                       timeout=20).payload.data for name in SECRETS}
        if not project:
            operation = request(session, "POST", "https://cloudresourcemanager.googleapis.com/v3/projects",
                                label="target_create", json={"projectId": target, "displayName": DISPLAY_NAME,
                                                            "labels": {"brand": "firewireads"}})
            wait_operation(session, operation, "https://cloudresourcemanager.googleapis.com/v3", "target_create")
            project = request(session, "GET", f"https://cloudresourcemanager.googleapis.com/v3/projects/{target}",
                              label="target_created_read")
            verify_owned_project(session, target, project, expected_account)
            reports.append({"project": target, "action": "created_owner_verified"})
        else:
            reports.append({"project": target, "action": "existing_owner_verified"})
        target_billing_url = f"https://cloudbilling.googleapis.com/v1/projects/{target}/billingInfo"
        target_billing = request(session, "GET", target_billing_url, label="target_billing_read")
        if target_billing.get("billingAccountName") not in (None, "", billing_name):
            raise SetupError("Target already uses another billing account; preserve association")
        if not target_billing.get("billingEnabled"):
            request(session, "PUT", target_billing_url, label="target_billing_link",
                    json={"billingAccountName": billing_name})
        readback = request(session, "GET", target_billing_url, label="target_billing_readback")
        if not readback.get("billingEnabled") or readback.get("billingAccountName") != billing_name:
            raise SetupError("Target billing readback did not verify the source account")
        project_number = project["name"].split("/", 1)[1]
        service_base = f"https://serviceusage.googleapis.com/v1/projects/{project_number}"
        states = {api: request(session, "GET", f"{service_base}/services/{api}", label="api_read").get("state")
                  for api in APIS}
        missing = [api for api, state in states.items() if state != "ENABLED"]
        if missing:
            operation = request(session, "POST", service_base + "/services:batchEnable", label="api_enable",
                                json={"serviceIds": missing})
            wait_operation(session, operation, "https://serviceusage.googleapis.com/v1", "api_enable")
        for api in APIS:
            state = request(session, "GET", f"{service_base}/services/{api}", label="api_readback").get("state")
            if state != "ENABLED":
                raise SetupError(f"{api}: API enabling has not verified ENABLED")
            reports.append({"api": api, "state": state})
        for name, payload in payloads.items():
            destination = f"projects/{target}/secrets/{name}"
            try:
                client.get_secret(name=destination, timeout=20)
            except NotFound:
                client.create_secret(parent=f"projects/{target}", secret_id=name,
                                     secret={"replication": {"automatic": {}}, "labels": {"brand": "firewireads"}},
                                     timeout=20)
            try:
                existing = client.access_secret_version(name=destination + "/versions/latest", timeout=20).payload.data
            except NotFound:
                existing = None
            if existing is not None and existing != payload:
                raise SetupError(f"{name}: existing target value differs; no overwrite")
            if existing is None:
                client.add_secret_version(parent=destination, payload={"data": payload}, timeout=20)
            actual = client.access_secret_version(name=destination + "/versions/latest", timeout=20).payload.data
            if actual != payload:
                raise SetupError(f"{name}: secret copy readback mismatch")
            reports.append({"secret": name, "action": "copied_verified" if existing is None else "existing_equal_verified"})
    if gcloud("config", "get-value", "project") != original_default:
        raise SetupError("CLI default changed concurrently; this helper did not modify it")
    return {"status": "PROJECT_BOOTSTRAP_VERIFIED", "project_id": target, "project_number": project_number,
            "display_name": DISPLAY_NAME, "source_billing_reused_verified": True,
            "adc_expected_identity": adc_matches, "credential_source": "verified_cli" if allow_cli else "adc",
            "cli_default_preserved": True, "source_project_resources_preserved": True, "resources": reports,
            "pending": ["runtime/dispatch service accounts and scoped IAM", "Cloud SQL instance/database/new password",
                        "Artifact Registry repository/image", "Cloud Run service/research queue",
                        "data migration, private links, domain switch and end-to-end verification"],
            "deployments": 0, "customer_messages": 0, "service_account_keys_created": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-project", default=DEFAULT_TARGET)
    parser.add_argument("--expected-account", default=os.getenv("FIREWIRE_GCP_EXPECTED_ACCOUNT", ""),
                        help="Authorized account identity, or set FIREWIRE_GCP_EXPECTED_ACCOUNT locally")
    parser.add_argument("--apply", action="store_true", help="Create/configure only under explicit owner authorization")
    parser.add_argument("--use-verified-cli-identity", action="store_true", help="Use verified FireWireAds CLI credentials in memory")
    args = parser.parse_args()
    try:
        print(json.dumps(setup(args.target_project, args.apply, args.use_verified_cli_identity, args.expected_account)))
        return 0
    except SetupError as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}))
    except Exception as error:
        print(json.dumps({"status": "BLOCKED", "error_type": type(error).__name__, "diagnostics": "omitted"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
