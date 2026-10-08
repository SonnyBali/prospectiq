"""The unique client query routes a page; only a capability/session authorizes it."""
from dataclasses import replace
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from conftest import FakeSecrets


def issued(client, admin_headers, imported_company):
    response = client.post('/api/admin/prospects/import', headers=admin_headers, json=imported_company)
    assert response.status_code == 200
    value = response.json()
    url = urlparse(value['dashboard_url'])
    return value, url


def test_mint_has_unique_non_authorizing_client_query(client, admin_headers, imported_company):
    first, url = issued(client, admin_headers, imported_company)
    second, second_url = issued(client, admin_headers, imported_company)
    assert url.path == '/p'
    assert parse_qs(url.query) == {'client': [first['prospect_id']]}
    assert url.fragment and url.fragment not in url.query
    assert url.query != second_url.query
    assert first['prospect_id'] != second['prospect_id']
    # The query alone never creates a session, even when it names a real row.
    assert client.get('/api/dashboard', params={'client': first['prospect_id']}).status_code == 401


def test_capability_client_binding_and_session_reload(client, admin_headers, imported_company):
    first, url = issued(client, admin_headers, imported_company)
    second, _ = issued(client, admin_headers, imported_company)
    response = client.post('/api/access', json={'token': url.fragment, 'client_id': second['prospect_id']})
    assert response.status_code == 401
    assert 'set-cookie' not in response.headers
    response = client.post('/api/access', json={'token': url.fragment, 'client_id': first['prospect_id']})
    assert response.status_code == 200
    assert response.json()['prospect']['id'] == first['prospect_id']
    assert client.get('/api/dashboard', params={'client': first['prospect_id']}).status_code == 200
    # An older valid cookie cannot silently render a different company's page.
    wrong = client.get('/api/dashboard', params={'client': second['prospect_id']})
    assert wrong.status_code == 401
    assert 'prospect' not in wrong.json()
    assert client.get('/api/dashboard?client=&client=' + first['prospect_id']).status_code == 401
    assert client.get('/api/dashboard', params={'client': ''}).status_code == 401


def test_legacy_fragment_capability_still_works(client, admin_headers, imported_company):
    first, url = issued(client, admin_headers, imported_company)
    assert client.post('/api/access', json={'token': url.fragment}).status_code == 200
    assert client.get('/api/dashboard').json()['prospect']['id'] == first['prospect_id']


@pytest.mark.parametrize('client_id', ['', 'a b', '../another', '{{contact.id}}', 'x' * 101])
def test_malformed_client_id_fails_closed(client, client_id):
    assert client.post('/api/access', json={'token': 't' * 43, 'client_id': client_id}).status_code == 422


@pytest.mark.parametrize('path', ['/?client=opaque', '/?other=value', '/p?client=opaque'])
def test_query_entry_never_relaxes_marketing_csp(settings, path):
    canonical = replace(settings, public_origin='https://prospect.firewireads.com')
    with TestClient(create_app(canonical, FakeSecrets()), base_url=canonical.public_origin) as client:
        response = client.get(path)
        assert response.status_code == 200
        assert 'googletagmanager.com' not in response.headers['content-security-policy']
        assert response.headers['x-robots-tag'] == 'noindex, nofollow, noarchive'
        assert response.headers['referrer-policy'] == 'no-referrer'
        assert response.headers['cache-control'] == 'no-store'
