import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.voice import create_voice_app


def test_voice_disabled_without_provider_loading():
    with TestClient(create_voice_app()) as client:
        response = client.get("/")
        assert response.status_code == 503
        assert "loader.js" not in response.text
        assert client.get("/api/demo").status_code == 404


def test_isolated_adapter_has_no_provider_credentials_or_private_api():
    with TestClient(create_voice_app("aaaaaaaaaaaaaaaaaaaaaaaa", True)) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert 'content="aaaaaaaaaaaaaaaaaaaaaaaa"' in response.text
        assert "Load native voice controls" in response.text
        assert "loader.js" not in response.text
        assert "frame-ancestors http://127.0.0.1:8091" in response.headers["content-security-policy"]
        assert client.get("/api/history").status_code == 404


@pytest.mark.parametrize("id_", ["6a76e48422509c8ee2247714", "6abf71b7cdeb03a6d5287556", "6abe29f12b6d9dcee841fc67"])
def test_audited_production_widgets_are_always_blocked(id_):
    with pytest.raises(ValueError, match="non-production"):
        create_voice_app(id_, True)


def test_browser_provider_cannot_run_in_personalized_dashboard_origin():
    with pytest.raises(ValueError, match="separate"):
        Settings(voice_widget_id="aaaaaaaaaaaaaaaaaaaaaaaa", voice_isolated=True,
                 voice_browser_origin="http://127.0.0.1:8090").validate()
