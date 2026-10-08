"""Verify issued private pages without printing credentials or sending messages.

Read capability links only from an ignored local artifact. Verifies exact page
identity, cached real research, source attribution, cookie scope and Python
calculations. This makes no model calls or CRM changes.
"""
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ORIGIN = "https://prospect.firewireads.com"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--links-file", type=Path, required=True)
    args = parser.parse_args()
    if args.links_file.resolve().parent != Path("artifacts").resolve():
        raise ValueError("Private links must stay in ignored artifacts directory")
    saved = json.loads(args.links_file.read_text(encoding="utf-8"))
    checks = 0
    for page in saved["pages"]:
        parsed = urlparse(page["dashboard_url"])
        assert f"{parsed.scheme}://{parsed.netloc}" == ORIGIN and parsed.path == "/p"
        assert parse_qs(parsed.query) == {"client": [page["prospect_id"]]}
        with httpx.Client(base_url=ORIGIN, follow_redirects=False, timeout=60) as client:
            shell = client.get("/p", params={"client": page["prospect_id"]})
            assert shell.status_code == 200 and "noindex" in shell.headers["x-robots-tag"]
            assert "googletagmanager.com" not in shell.headers["content-security-policy"]
            access = client.post("/api/access", headers={"Origin": ORIGIN},
                                 json={"token": parsed.fragment, "client_id": page["prospect_id"]})
            assert access.status_code == 200
            dashboard = access.json()
            assert dashboard["prospect"]["id"] == page["prospect_id"]
            assert dashboard["prospect"]["first_name"] == page["first_name"]
            assert dashboard["prospect"]["company_name"] == saved["company"]
            assert dashboard["prospect"]["synthetic"] is False and dashboard["sources"]
            assert dashboard["has_research_attribution"] is True
            assert all(source["is_synthetic"] is False for source in dashboard["sources"])
            assert "HttpOnly" in access.headers["set-cookie"] and "Secure" in access.headers["set-cookie"]
            assert client.get("/api/dashboard", params={"client": "another-client"}).status_code == 401
            assert client.get("/api/dashboard", params={"client": page["prospect_id"]}).status_code == 200
            scenario = client.post("/api/simulate", json=dashboard["simulator_defaults"],
                                   headers={"Origin": ORIGIN, "X-CSRF-Token": dashboard["csrf_token"]})
            assert scenario.status_code == 200 and scenario.json()["results"]["monthly_revenue"] == 8100
            assert client.get("/api/research-attribution").status_code == 200
            assert client.get("/api/engineering").status_code == 200
            checks += 8
        with httpx.Client(base_url=ORIGIN, follow_redirects=False, timeout=30) as anonymous:
            assert anonymous.get("/api/dashboard", params={"client": page["prospect_id"]}).status_code == 401
            checks += 1
    print(json.dumps({"status": "PASS", "pages": len(saved["pages"]), "http_checks": checks,
                      "cached_real_research": True, "client_scope": True,
                      "private_tracking_blocked": True, "outreach_sent": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "not_verified", "error_type": type(error).__name__,
                          "diagnostics": "private links and response bodies omitted"}))
        raise SystemExit(1) from None
