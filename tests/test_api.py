import pytest
from fastapi.testclient import TestClient

from foco_social.api import app

KEYWORDS = ["debate", "encuesta", "fraude", "voto", "inflacion"]


@pytest.fixture
def client(sample_csv, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # sin .env del desarrollador
    monkeypatch.setenv("DATA_PATH", str(sample_csv))
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_options_reports_methods_and_llm(client):
    body = client.get("/api/options").json()
    assert {"kmeans", "lda"} <= set(body["methods"])
    assert body["llm_available"] is False
    assert body["dataset_has_labels"] is True


def test_run_without_llm_returns_topics_assignments_and_metrics(client):
    resp = client.post(
        "/api/runs",
        json={"theme": "elecciones", "keywords": KEYWORDS, "n_topics": 3, "use_llm": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["llm"] is None
    assert len([t for t in body["topics"] if t["level"] == 1]) == 3
    assert len(body["assignments"]) == body["stats"]["n_tweets"]
    assert -1 <= body["metrics"]["topics"]["ari"] <= 1


def test_run_with_llm_but_none_configured_is_rejected(client):
    resp = client.post("/api/runs", json={"theme": "elecciones", "keywords": KEYWORDS})
    assert resp.status_code == 503


def test_run_with_no_matches_returns_404(client):
    resp = client.post(
        "/api/runs", json={"theme": "nada", "keywords": ["zzzz-no-existe"], "use_llm": False}
    )
    assert resp.status_code == 404


def test_invalid_request_returns_422(client):
    assert client.post("/api/runs", json={"theme": "elecciones", "depth": 9}).status_code == 422


def test_vercel_entrypoint_exposes_the_same_app():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "api" / "index.py"
    spec = importlib.util.spec_from_file_location("vercel_entry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.app is app
