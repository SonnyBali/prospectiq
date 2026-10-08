"""Owner-authorized dedicated Cloud SQL database/user initialization.

Uses ADC and a Secret Manager password directly in memory. Never logs a password,
provider response body or password-bearing command argument. Existing DB/user are
preserved; this helper does not rotate credentials or change unrelated resources.
"""
import json
import time

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import secretmanager

PROJECT = "ai-leadscore"
INSTANCE = "prospectiq-db"
DATABASE = USER = "prospectiq"


def require_success(response, action):
    if not response.ok:
        raise RuntimeError(f"{action} failed with HTTP {response.status_code}; diagnostics omitted")
    return response.json()


def wait_operation(session, operation, action):
    endpoint = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/operations/{operation['name']}"
    deadline = time.monotonic() + 60
    while operation.get("status") != "DONE":
        if time.monotonic() >= deadline:
            raise RuntimeError(f"{action} operation still pending; reconcile before retry")
        time.sleep(3)
        operation = require_success(session.get(endpoint, timeout=15), "operation_read")
    if operation.get("error"):
        raise RuntimeError(f"{action} operation failed; provider diagnostics omitted")


def main():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    with AuthorizedSession(credentials) as session:
        base = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{INSTANCE}"
        state = require_success(session.get(base, timeout=30), "instance_read")
        if state.get("state") != "RUNNABLE":
            raise RuntimeError("Dedicated instance is not ready; wait before database initialization")
        databases = require_success(session.get(base + "/databases", timeout=30), "database_list").get("items", [])
        if DATABASE not in {item["name"] for item in databases}:
            operation = require_success(session.post(base + "/databases", json={"name": DATABASE}, timeout=30), "database_create")
            wait_operation(session, operation, "database_create")
        users = require_success(session.get(base + "/users", timeout=30), "user_list").get("items", [])
        if USER not in {item["name"] for item in users}:
            client = secretmanager.SecretManagerServiceClient(credentials=credentials)
            password = client.access_secret_version(name=f"projects/{PROJECT}/secrets/PROSPECTIQ_DB_PASSWORD/versions/latest").payload.data.decode()
            operation = require_success(session.post(base + "/users", json={"name": USER, "password": password}, timeout=30), "user_create")
            wait_operation(session, operation, "user_create")
        print(json.dumps({"database": DATABASE, "user": USER, "status": "initialization_complete_or_existing"}))


if __name__ == "__main__":
    main()
