from fastapi.testclient import TestClient

from vesper.api import create_app


def test_dashboard_without_credentials_stays_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    monkeypatch.setenv("VESPER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VESPER_MODEL_DIR", str(tmp_path / "models"))
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        status = client.get("/api/status").json()
        assert status["production_validated"] is False
        assert status["decision"] == "NO SIGNAL — SYSTEM INVALID"
        assert "PRODUCTION_MODEL_UNAVAILABLE" in status["failures"]
        assert client.get("/api/signals").json() == []
