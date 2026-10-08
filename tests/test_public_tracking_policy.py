"""Public marketing permissions must never extend to prospect pages or APIs."""
from dataclasses import replace
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.main import create_app

ORIGIN = "https://prospect.firewireads.com"


def csp_directives(policy):
    return {parts[0]: set(parts[1:]) for section in policy.split(";") if (parts := section.split())}


def assert_private_csp(response):
    policy = csp_directives(response.headers["content-security-policy"])
    assert policy["script-src"] == {"'self'"}
    assert policy["connect-src"] == {"'self'"}
    assert policy["img-src"] == {"'self'", "data:"}
    assert policy["frame-src"] == {"'self'"}


def test_tracking_csp_is_public_only_and_private_pages_are_not_indexed(settings):
    with TestClient(create_app(replace(settings, public_origin=ORIGIN)), base_url=ORIGIN) as client:
        public = client.get("/")
        policy = csp_directives(public.headers["content-security-policy"])
        assert policy["script-src"] == {
            "'self'", "https://connect.facebook.net", "https://www.googletagmanager.com",
            "https://www.googleadservices.com", "https://googleads.g.doubleclick.net", "https://www.google.com",
        }
        baseline_beacons = {
            "'self'", "https://*.google-analytics.com", "https://www.googleadservices.com",
            "https://googleads.g.doubleclick.net", "https://www.google.com", "https://www.facebook.com",
            "https://www.googletagmanager.com", "https://pagead2.googlesyndication.com",
        }
        assert policy["connect-src"] == baseline_beacons | {"https://ad.doubleclick.net"}
        assert policy["img-src"] == baseline_beacons | {"data:"}
        assert policy["frame-src"] == {"'self'", "https://td.doubleclick.net", "https://www.googletagmanager.com"}
        assert "'unsafe-inline'" not in policy["script-src"] and "'unsafe-eval'" not in policy["script-src"]
        assert "x-robots-tag" not in public.headers
        for route in ("/p", "/api/demo", "/health", "/docs", "/openapi.json"):
            response = client.get(route)
            assert response.status_code == 200
            assert_private_csp(response)
            assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"
        robots = client.get("/robots.txt")
        assert "Disallow: /p" in robots.text and "Disallow: /api/" in robots.text
        assert f"Sitemap: {ORIGIN}/sitemap.xml" in robots.text
        root = ET.fromstring(client.get("/sitemap.xml").content)
        locations = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        assert [location.text for location in locations] == [ORIGIN + "/"]


def test_local_preview_does_not_allow_marketing_providers(client):
    assert_private_csp(client.get("/"))


@pytest.mark.parametrize("base_url", [
    "https://prospectiq-s4gztnjt6a-uc.a.run.app",
    "https://prospectiq-1051896753015.us-central1.run.app",
])
def test_cloud_run_origin_does_not_allow_public_marketing_providers(settings, base_url):
    with TestClient(create_app(replace(settings, public_origin=ORIGIN)), base_url=base_url) as client:
        assert_private_csp(client.get("/"))


@pytest.mark.parametrize("value", [ORIGIN + "/p", ORIGIN + "?token=x", ORIGIN + "#secret", "https://user:password@prospect.firewireads.com"])
def test_public_origin_rejects_paths_queries_fragments_and_credentials(value):
    with pytest.raises(ValueError, match="bare web origin"):
        Settings(public_origin=value).validate()
