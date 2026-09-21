from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def isolated_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("STORYBOARDS_DIR", str(tmp_path / "storyboards"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("SARVAM_API_KEY", "")
    monkeypatch.delenv("VERCEL_AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.setenv("DEFAULT_SERIES_TITLE", "Oracle AI Agents")
    monkeypatch.setenv("DEFAULT_HANDLE", "@genai_guru")
    monkeypatch.delenv("REELGEN_PYTHON", raising=False)
    return tmp_path
