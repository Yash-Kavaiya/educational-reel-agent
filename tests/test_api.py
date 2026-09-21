from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_health_and_root(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "healthy"
        assert body["environment"]["sarvam_configured"] is False

        root = client.get("/")
        assert root.status_code == 200
        assert "endpoints" in root.json()


def test_storyboard_roundtrip(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/storyboards",
            json={
                "topic": "Tool Use",
                "content": "Agents call tools. The model chooses arguments. Results return to the loop.",
                "voice": "anushka",
                "series_title": "Oracle AI Agents",
                "reel_number": 1,
                "total_reels": 1,
            },
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        assert payload["status"] == "success"
        assert payload["scenes"] == 5

        listed = client.get("/api/v1/storyboards", params={"series": "Oracle AI Agents"})
        assert listed.status_code == 200
        files = listed.json()["storyboards"]
        assert files
        filename = files[0]["file"]

        fetched = client.get(f"/api/v1/storyboards/oracle-ai-agents/{filename}")
        assert fetched.status_code == 200
        assert fetched.json()["tts_provider"] == "sarvam"


def test_rejects_path_traversal_on_storyboard(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        response = client.get("/api/v1/storyboards/oracle-ai-agents/..%2F..%2Fsecret.json")
        assert response.status_code in {400, 404}


def test_invalid_voice_is_422(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/storyboards",
            json={"topic": "X", "content": "Some content that is long enough.", "voice": "nope"},
        )
        assert response.status_code == 422


def test_pipeline_refuses_upload_without_render(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/pipeline",
            json={
                "series_title": "Oracle AI Agents",
                "topics": [{"topic": "X", "content": "Hello world content here."}],
                "render": False,
                "upload_youtube": True,
                "generate_social": False,
            },
        )
        assert response.status_code == 400


def test_evaluate_requires_gateway_key(isolated_dirs: Path):
    from agent.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/evaluate",
            json={"state": "Storyboard has five scenes.", "question": "Is the board complete?"},
        )
        assert response.status_code == 400
        assert "VERCEL_AI_GATEWAY_API_KEY" in response.json()["detail"]
