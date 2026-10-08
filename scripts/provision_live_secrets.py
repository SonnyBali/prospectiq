"""Explicit deployment helper: create two dedicated secrets without printing values.

Requires owner-authorized deployment and authenticated Google ADC. Credentials
are generated in memory and sent directly to Secret Manager, never local files.
Existing secrets/versions are preserved. Runtime IAM is applied by the operator.
"""
import json
import secrets

from google.api_core.exceptions import AlreadyExists
from google.cloud import secretmanager

PROJECT = "ai-leadscore"
NAMES = ("PROSPECTIQ_DB_PASSWORD", "PROSPECTIQ_ADMIN_KEY")


def main():
    client = secretmanager.SecretManagerServiceClient()
    reports = []
    for name in NAMES:
        try:
            client.create_secret(parent=f"projects/{PROJECT}", secret_id=name,
                                 secret={"replication": {"automatic": {}}})
        except AlreadyExists:
            reports.append({"secret": name, "action": "existing_preserved"})
            continue
        value = secrets.token_urlsafe(48).encode()
        client.add_secret_version(parent=f"projects/{PROJECT}/secrets/{name}", payload={"data": value})
        reports.append({"secret": name, "action": "created_with_random_value"})
    print(json.dumps(reports))


if __name__ == "__main__":
    main()
