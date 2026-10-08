"""Google grounding attribution may embed only in an authenticated same-origin frame."""
from pathlib import Path
import re
from urllib.parse import urlparse

import pytest


def directives(response):
    return {parts[0]: set(parts[1:]) for section in response.headers["content-security-policy"].split(";")
            if (parts := section.split())}


def test_authenticated_attribution_is_same_origin_and_scriptless(client, imported_company, admin_headers):
    html = "<p>Google Search grounding attribution fixture</p>"
    imported = client.post("/api/admin/prospects/import", headers=admin_headers,
                           json={**imported_company, "research_attribution_html": html})
    assert imported.status_code == 200
    opened = client.post("/api/access", json={"token": urlparse(imported.json()["dashboard_url"]).fragment,
                                             "client_id": imported.json()["prospect_id"]})
    assert opened.status_code == 200
    response = client.get("/api/research-attribution")
    assert response.status_code == 200 and response.text == html
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    policy = directives(response)
    assert policy["frame-ancestors"] == {"'self'"}
    assert policy["script-src"] == {"'none'"}
    assert policy["default-src"] == {"'none'"}
    assert policy["base-uri"] == {"'none'"}
    assert policy["form-action"] == {"'none'"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


def test_attribution_requires_session(client):
    response = client.get("/api/research-attribution")
    assert response.status_code == 401
    assert "Google Search grounding attribution fixture" not in response.text


@pytest.mark.parametrize("route", ["/p", "/p?client=unverified", "/api/dashboard", "/health"])
def test_attribution_exception_does_not_relax_other_private_responses(client, route):
    response = client.get(route)
    policy = directives(response)
    assert response.headers["x-frame-options"] == "DENY"
    assert policy["frame-ancestors"] == {"'none'"}
    assert policy["script-src"] == {"'self'"}
    assert policy["connect-src"] == {"'self'"}


def test_attribution_iframe_retains_origin_but_cannot_execute_scripts():
    source = (Path(__file__).parents[1] / "app/static/app.js").read_text(encoding="utf-8")
    frame = source.split('frame.src = "/api/research-attribution";', 1)[1].split("attribution.append(frame);", 1)[0]
    sandbox = re.search(r'frame\.setAttribute\("sandbox", "([^\"]+)"\)', frame)
    assert sandbox is not None
    assert set(sandbox[1].split()) == {"allow-same-origin", "allow-popups", "allow-popups-to-escape-sandbox"}
    assert "allow-scripts" not in sandbox[1].split()
