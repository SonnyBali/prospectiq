"""Owner-authorized dedicated FireWireAds SQL/runtime setup after project bootstrap.

Creates only the target runtime identity, scoped grants, fresh password secret and
PG16 shared-core instance/database/user. No old resources, domains or live traffic
change. Pending SQL operation IDs are returned for safe later reconciliation.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import secrets
import sys
import time

from google.api_core.exceptions import NotFound
from google.auth.transport.requests import AuthorizedSession
from google.cloud import secretmanager
from provision_firewire_project import (DEFAULT_TARGET, SECRETS, SetupError, gcloud, request,
                                       verify_identity, verify_owned_project)

SQL_INSTANCE = "prospectiq-db"
SQL_DATABASE = SQL_USER = "prospectiq"
DB_SECRET = "PROSPECTIQ_DB_PASSWORD"

def grant(session, base, role, member, project=False):
    options = {"json": {"options": {"requestedPolicyVersion": 3}}} if project else {"params": {"options.requestedPolicyVersion": 3}}

    def read():
        return request(session, "POST" if project else "GET", base + ":getIamPolicy", label="iam_read", **options)

    def present(policy):
        return any(item.get("role") == role and not item.get("condition") and member in item.get("members", [])
                   for item in policy.get("bindings", []))

    policy = read()
    if not present(policy):
        policy = copy.deepcopy(policy)
        binding = next((item for item in policy.setdefault("bindings", [])
                        if item.get("role") == role and not item.get("condition")), None)
        if binding is None:
            policy["bindings"].append({"role": role, "members": [member]})
        else:
            binding.setdefault("members", []).append(member)
        request(session, "POST", base + ":setIamPolicy", label="iam_grant", json={"policy": policy})
        if not present(read()):
            raise SetupError("IAM grant was not confirmed by readback")


def sql_wait(session, target, operation, seconds=60):
    print(json.dumps({"phase": "sql_operation", "operation": operation.get("name"), "status": operation.get("status")}), flush=True)
    deadline = time.monotonic() + seconds
    while operation.get("status") != "DONE":
        if time.monotonic() >= deadline:
            return False
        time.sleep(3)
        operation = request(session, "GET", f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{target}/operations/{operation['name']}",
                            label="sql_operation_read")
    if operation.get("error"):
        raise SetupError("SQL operation failed; diagnostics omitted")
    return True


def setup_sql(session, client, credentials, target):
    runtime = f"prospectiq-runtime@{target}.iam.gserviceaccount.com"
    iam = f"https://iam.googleapis.com/v1/projects/{target}/serviceAccounts"
    response = session.get(f"{iam}/{runtime}", timeout=30)
    if response.status_code == 404:
        request(session, "POST", iam, label="runtime_create", json={"accountId": "prospectiq-runtime",
                "serviceAccount": {"displayName": "ProspectIQ runtime"}})
    elif not response.ok or response.json().get("disabled"):
        raise SetupError("Target runtime identity unavailable or disabled; preserve existing state")
    secret_name = f"projects/{target}/secrets/{DB_SECRET}"
    try:
        client.get_secret(name=secret_name, timeout=20)
    except NotFound:
        client.create_secret(parent=f"projects/{target}", secret_id=DB_SECRET,
                             secret={"replication": {"automatic": {}}, "labels": {"brand": "firewireads"}}, timeout=20)
    try:
        password = client.access_secret_version(name=secret_name + "/versions/latest", timeout=20).payload.data.decode()
    except NotFound:
        password = secrets.token_urlsafe(48)
        client.add_secret_version(parent=secret_name, payload={"data": password.encode()}, timeout=20)
        if client.access_secret_version(name=secret_name + "/versions/latest", timeout=20).payload.data.decode() != password:
            raise SetupError("Fresh database password secret failed readback")
    member = f"serviceAccount:{runtime}"
    grant(session, f"https://cloudresourcemanager.googleapis.com/v1/projects/{target}", "roles/cloudsql.client", member, project=True)
    for name in (*SECRETS, DB_SECRET):
        grant(session, f"https://secretmanager.googleapis.com/v1/projects/{target}/secrets/{name}",
              "roles/secretmanager.secretAccessor", member)
    base = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{target}/instances/{SQL_INSTANCE}"
    response = session.get(base, timeout=30)
    if response.status_code == 404:
        # A fixed instance ID prevents duplicate instances; conflicts fail closed.
        # Cloud SQL operation listing is unavailable before that instance exists.
        operation = request(session, "POST", base.rsplit("/", 1)[0], label="sql_instance_create", json={
            "name": SQL_INSTANCE, "region": "us-central1", "databaseVersion": "POSTGRES_16",
            "settings": {"tier": "db-f1-micro", "edition": "ENTERPRISE", "availabilityType": "ZONAL",
                         "dataDiskSizeGb": "10", "dataDiskType": "PD_SSD", "storageAutoResize": True,
                         "activationPolicy": "ALWAYS", "deletionProtectionEnabled": True,
                         "userLabels": {"brand": "firewireads"},
                         "ipConfiguration": {"ipv4Enabled": True, "sslMode": "ENCRYPTED_ONLY", "authorizedNetworks": []},
                         "backupConfiguration": {"enabled": True, "startTime": "18:00", "transactionLogRetentionDays": 7,
                                                 "backupRetentionSettings": {"retentionUnit": "COUNT", "retainedBackups": 7}}},
        })
        print(json.dumps({"phase": "sql_instance_create", "project": target, "operation": operation["name"], "status": "PENDING"}), flush=True)
        return {"status": "PENDING", "instance": SQL_INSTANCE, "operation": operation["name"], "iam_verified": True}
    if not response.ok:
        raise SetupError(f"sql_instance_read: HTTP {response.status_code}; diagnostics omitted")
    instance = response.json()
    if instance.get("state") != "RUNNABLE":
        return {"status": "PENDING", "instance": SQL_INSTANCE, "state": instance.get("state"), "iam_verified": True}
    settings = instance.get("settings", {})
    if (instance.get("databaseVersion") != "POSTGRES_16" or instance.get("region") != "us-central1"
            or settings.get("tier") != "db-f1-micro" or settings.get("edition") != "ENTERPRISE"
            or settings.get("availabilityType") != "ZONAL" or settings.get("dataDiskSizeGb") != "10"
            or not settings.get("deletionProtectionEnabled") or not settings.get("backupConfiguration", {}).get("enabled")
            or settings.get("ipConfiguration", {}).get("sslMode") != "ENCRYPTED_ONLY"
            or settings.get("ipConfiguration", {}).get("authorizedNetworks")):
        raise SetupError("Existing target SQL settings differ; preserve instance and reconcile before proceeding")
    databases = request(session, "GET", base + "/databases", label="sql_database_list").get("items", [])
    if SQL_DATABASE not in {item["name"] for item in databases}:
        operation = request(session, "POST", base + "/databases", label="sql_database_create", json={"name": SQL_DATABASE})
        if not sql_wait(session, target, operation):
            return {"status": "PENDING", "operation": operation["name"], "phase": "database_create", "iam_verified": True}
    users = request(session, "GET", base + "/users", label="sql_user_list").get("items", [])
    if SQL_USER not in {item["name"] for item in users}:
        operation = request(session, "POST", base + "/users", label="sql_user_create", json={"name": SQL_USER, "password": password})
        if not sql_wait(session, target, operation):
            return {"status": "PENDING", "operation": operation["name"], "phase": "user_create", "iam_verified": True}
    # Real connector + database authentication check; no tables or customer records are created.
    from google.cloud.sql.connector import Connector
    with Connector(credentials=credentials, refresh_strategy="LAZY") as connector:
        connection = connector.connect(instance["connectionName"], "pg8000", user=SQL_USER, password=password,
                                       db=SQL_DATABASE, timeout=30)
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            if cursor.fetchone()[0] != 1:
                raise SetupError("SQL connector SELECT 1 did not verify")
            cursor.close()
        finally:
            connection.close()
    return {"status": "RUNNABLE_CONNECTOR_VERIFIED", "instance": instance["connectionName"],
            "database": SQL_DATABASE, "user": SQL_USER, "fresh_password_secret": DB_SECRET,
            "runtime_account": runtime, "runtime_cloudsql_client_project_scoped": True,
            "runtime_secret_accessor_scoped_secrets": list((*SECRETS, DB_SECRET)), "customer_records_written": 0}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-project", default=DEFAULT_TARGET)
    parser.add_argument("--expected-account", default=os.getenv("FIREWIRE_GCP_EXPECTED_ACCOUNT", ""))
    parser.add_argument("--apply", action="store_true", help="Apply only under explicit owner authorization")
    parser.add_argument("--use-verified-cli-identity", action="store_true")
    args = parser.parse_args()
    try:
        if not args.expected_account or "@" not in args.expected_account:
            raise SetupError("Supply --expected-account or FIREWIRE_GCP_EXPECTED_ACCOUNT locally")
        if not re.fullmatch(r"firewireads-[a-z0-9-]{6,18}[a-z0-9]", args.target_project):
            raise SetupError("Target must be a dedicated FireWireAds project; source is prohibited")
        expected = args.expected_account.strip().lower()
        credentials, original_default, adc_matches = verify_identity(args.use_verified_cli_identity, expected)
        client = secretmanager.SecretManagerServiceClient(credentials=credentials)
        with AuthorizedSession(credentials) as session:
            project = request(session, "GET", f"https://cloudresourcemanager.googleapis.com/v3/projects/{args.target_project}", label="target_read")
            verify_owned_project(session, args.target_project, project, expected)
            if not args.apply:
                result = {"status": "PLAN", "project": args.target_project, "tier": "db-f1-micro",
                          "database_version": "POSTGRES_16", "edition": "ENTERPRISE", "availability": "ZONAL",
                          "disk_size_gb": 10, "backup_enabled": True, "deletion_protection": True,
                          "database": SQL_DATABASE, "runtime_secret_accessor_scoped_secrets": list((*SECRETS, DB_SECRET)),
                          "runtime_cloudsql_client_project_scoped": True, "cloud_mutations": 0}
            else:
                result = setup_sql(session, client, credentials, args.target_project)
        if gcloud("config", "get-value", "project") != original_default:
            raise SetupError("CLI default changed concurrently; this helper did not modify it")
        result.update({"project": args.target_project, "cli_default_preserved": True,
                       "adc_expected_identity": adc_matches, "source_resources_preserved": True})
        print(json.dumps(result))
        return 0
    except SetupError as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}))
    except Exception as error:
        print(json.dumps({"status": "BLOCKED", "error_type": type(error).__name__, "diagnostics": "omitted"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
