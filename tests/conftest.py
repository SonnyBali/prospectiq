import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakeSecrets:
    def get(self, name):
        return {"admin-test": "test-admin-key", "FIREWIRE_GHL_LOCATION_ID": "aFnKcmUdTSPIjo7lCaix", "FIREWIRE_GHL_API_KEY": "mock-crm"}[name]


@pytest.fixture
def settings(tmp_path):
    return Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", admin_secret="admin-test")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, FakeSecrets())) as value:
        yield value


@pytest.fixture
def csrf(client):
    return {"X-CSRF-Token": client.get("/api/demo").json()["csrf_token"]}


@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


@pytest.fixture
def imported_company():
    return {"first_name": "Sam", "company_name": "Synthetic Northstar", "industry": "Service business", "website": "https://example.com/northstar", "synthetic": True,
            "sources": [{"id": "northstar_intake", "title": "Synthetic intake", "url": "https://example.com/northstar/intake", "excerpt": "The fictional business uses voicemail for after-hours service requests.", "observed_at": "2026-10-08T00:00:00Z", "is_synthetic": True}]}
