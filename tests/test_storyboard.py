from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.tools.reel_tools import (
    create_storyboard,
    extract_key_points,
    generate_social_copy,
    render_reel,
)


def test_extract_key_points_from_sentences():
    content = (
        "Agents plan then act. They use tools to change the world. "
        "Memory lets them improve over time."
    )
    points = extract_key_points(content)
    assert len(points) >= 2
    assert any("tools" in point.lower() for point in points)


def test_extract_key_points_from_bullets():
    content = "- First idea here\n- Second idea here\n- Third idea here"
    points = extract_key_points(content)
    assert points[0].startswith("First")
    assert len(points) == 3


def test_create_storyboard_writes_json(isolated_dirs: Path):
    result = create_storyboard(
        topic="ReAct Pattern",
        content="ReAct interleaves reasoning and acting. Tools execute steps. Observations update the plan.",
        reel_number=2,
        total_reels=4,
        voice="arvind",
        series_title="Oracle AI Agents",
    )
    assert result["status"] == "success"
    assert result["reel_number"] == 2
    assert result["scenes"] == 5
    path = Path(result["storyboard_path"])
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["voice"] == "arvind"
    assert data["tts_provider"] == "sarvam"
    assert data["theme"] == "oracle"
    assert len(data["scenes"]) == 5
    assert "ReAct Pattern" in data["title"]


def test_create_storyboard_rejects_unknown_voice(isolated_dirs: Path):
    result = create_storyboard(
        topic="Test",
        content="Enough content to build a storyboard for this topic.",
        voice="not-a-voice",
    )
    assert result["status"] == "error"
    assert "unknown voice" in result["error"]


def test_generate_social_copy_includes_platforms(isolated_dirs: Path):
    result = generate_social_copy(
        topic="Guardrails",
        reel_number=1,
        total_reels=3,
        series_title="Oracle AI Agents",
        voice="meera",
    )
    assert result["status"] == "success"
    copy = result["social_copy"]
    assert "youtube" in copy and "instagram" in copy
    assert "linkedin" in copy and "twitter" in copy
    assert "Guardrails" in copy["youtube"]["title"]
    assert copy["youtube"]["title"].count("|") == 1


def test_render_reel_requires_api_key(isolated_dirs: Path):
    created = create_storyboard(
        topic="Memory",
        content="Short-term memory holds the current turn. Long-term memory stores facts.",
    )
    result = render_reel(created["storyboard_path"])
    assert result["status"] == "error"
    assert "SARVAM_API_KEY" in result["error"]


def test_render_reel_missing_storyboard(isolated_dirs: Path):
    result = render_reel("no-such.json")
    assert result["status"] == "error"
    assert "not found" in result["error"].lower()
