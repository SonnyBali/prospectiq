"""Run an owner-approved real Cloud Tasks research verification for FireWireAds.

Seeds one public-company verification record in the dedicated database, asks the
deployed admin API to enqueue it, and reads completion without printing source
bodies or credentials. No contacts, messages, voice calls or domains are changed.
An ignored state file makes retries reconcile the existing target instead of
creating more records. API/model calls incur normal Google/OpenAI costs.
"""
import argparse
import json
import os
from pathlib import Path
import time

from google.cloud import secretmanager
from google.cloud.sql.connector import Connector
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Prospect
from provision_firewire_project import verify_identity

PROJECT = "firewireads-platform"
ORIGIN = "https://prospectiq-504110803281.us-central1.run.app"
STATE = Path("artifacts/firewire-research-verification.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-account", default=os.getenv("FIREWIRE_GCP_EXPECTED_ACCOUNT", ""))
    parser.add_argument("--create-test-target", action="store_true")
    args = parser.parse_args()
    credentials, _, _ = verify_identity(True, args.expected_account)
    secrets = secretmanager.SecretManagerServiceClient(credentials=credentials)
    def secret(name):
        return secrets.access_secret_version(name=f"projects/{PROJECT}/secrets/{name}/versions/latest",
                                             timeout=20).payload.data.decode()
    password = secret("PROSPECTIQ_DB_PASSWORD")
    with Connector(credentials=credentials, refresh_strategy="LAZY") as connector:
        def connect():
            return connector.connect(f"{PROJECT}:us-central1:prospectiq-db", "pg8000", user="prospectiq",
                                     password=password, db="prospectiq", timeout=30)
        engine = create_engine("postgresql+pg8000://", creator=connect)
        try:
            with Session(engine) as db:
                if STATE.exists():
                    saved = json.loads(STATE.read_text())
                    assert saved["project"] == PROJECT
                    target = db.get(Prospect, saved["prospect_id"])
                    assert target and target.profile["company_name"] == "FireWireAds" and not target.synthetic
                else:
                    if not args.create_test_target:
                        raise RuntimeError("Explicit verification target creation required")
                    target = Prospect(profile={"first_name": "team", "company_name": "FireWireAds",
                                               "industry": "Digital marketing", "website": "https://firewireads.com/"},
                                      synthetic=False, research_status="pending")
                    db.add(target)
                    db.commit()
                    STATE.parent.mkdir(exist_ok=True)
                    STATE.write_text(json.dumps({"project": PROJECT, "prospect_id": target.id}), encoding="utf-8")
                target_id = target.id
            with httpx.Client(base_url=ORIGIN, timeout=45, follow_redirects=False) as client:
                response = client.post(f"/api/admin/prospects/{target_id}/research",
                                       headers={"X-Admin-Key": secret("PROSPECTIQ_ADMIN_KEY")})
                if response.status_code != 200:
                    raise RuntimeError(f"Research enqueue HTTP {response.status_code}; bodies omitted")
                print(json.dumps({"phase": "enqueue", "status": response.json()["status"],
                                  "request_id": response.headers.get("x-request-id")}), flush=True)
            deadline = time.monotonic() + 100
            while time.monotonic() < deadline:
                with Session(engine) as db:
                    current = db.get(Prospect, target_id)
                    if current.research_status == "complete":
                        assert current.sources and current.intelligence and current.research_completed_at
                        print(json.dumps({"status": "PASS", "project": PROJECT, "source_count": len(current.sources),
                                          "google_attribution": bool(current.research_attribution_html),
                                          "intelligence_cached": True, "crm_contact_bound": bool(current.crm_contact_id),
                                          "messages_sent": 0, "capabilities_issued": 0}))
                        return
                    if current.research_status == "failed":
                        raise RuntimeError("Research worker failed; reconcile saved target and safe Cloud Logging events")
                time.sleep(4)
            print(json.dumps({"status": "PENDING", "project": PROJECT, "action": "reconcile saved target before retry"}))
            raise SystemExit(2)
        finally:
            engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "not_verified", "error_type": type(error).__name__,
                          "diagnostics": "credentials, source bodies and private identifiers omitted"}))
        raise SystemExit(1) from None
