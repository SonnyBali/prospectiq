"""Public share metadata and the actual locally served image files must agree."""
from html.parser import HTMLParser
import struct
import xml.etree.ElementTree as ET


class PageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.links = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta":
            self.meta[values.get("property") or values.get("name")] = values.get("content")
        elif tag == "link":
            self.links.append(values)
        elif tag == "script":
            self.scripts.append(values)


def png_dimensions(content):
    assert content[:8] == b"\x89PNG\r\n\x1a\n"
    assert content[12:16] == b"IHDR"
    return struct.unpack(">II", content[16:24])


def test_public_share_metadata_matches_served_social_image(client):
    page = client.get("/")
    assert page.status_code == 200
    metadata = PageMetadata()
    metadata.feed(page.text)
    canonical = next(link["href"] for link in metadata.links if link.get("rel") == "canonical")
    assert canonical == "https://prospect.firewireads.com/"
    assert metadata.meta["robots"] == "index, follow"
    assert metadata.meta["og:url"] == canonical
    assert metadata.meta["og:image"] == "https://prospect.firewireads.com/static/prospectiq-social.png"
    assert metadata.meta["twitter:image"] == metadata.meta["og:image"]
    assert metadata.meta["twitter:card"] == "summary_large_image"
    assert "synthetic" in metadata.meta["description"]
    local_scripts = [script.get("src") for script in metadata.scripts]
    assert local_scripts.index("/static/analytics.js") < local_scripts.index("/static/app.js")
    assert all(script.get("src", "").startswith("/static/") for script in metadata.scripts)
    image = client.get("/static/prospectiq-social.png")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/png")
    assert png_dimensions(image.content) == (int(metadata.meta["og:image:width"]), int(metadata.meta["og:image:height"])) == (1200, 630)


def test_favicons_have_valid_formats_and_declared_sizes(client):
    svg = client.get("/static/favicon.svg")
    assert svg.status_code == 200
    assert svg.headers["content-type"].startswith("image/svg+xml")
    root = ET.fromstring(svg.content)
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == "0 0 64 64"
    for route, size in [("favicon-32.png", (32, 32)), ("apple-touch-icon.png", (180, 180))]:
        response = client.get(f"/static/{route}")
        assert response.status_code == 200
        assert png_dimensions(response.content) == size
