"""Reel storyboard, render, and social-copy tools."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from agent.config import get_settings
from agent.models import ORACLE_PALETTE, SARVAM_VOICES, Scene, Storyboard
from agent.paths import resolve_existing_under, safe_under, slugify

logger = logging.getLogger(__name__)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _storyboards_root() -> Path:
    return get_settings().storyboards_dir


def _output_root() -> Path:
    return get_settings().output_dir


def _validate_voice(voice: str) -> str:
    if voice not in SARVAM_VOICES:
        allowed = ", ".join(sorted(SARVAM_VOICES))
        raise ValueError(f"unknown voice {voice!r}; allowed: {allowed}")
    return voice


def extract_key_points(content: str, limit: int = 6) -> list[str]:
    """Pull short teaching points from free text or bullet lists."""
    raw = (content or "").replace("\r\n", "\n").strip()
    if not raw:
        return ["Master the fundamentals."]

    lines = [line.strip(" -\t*") for line in raw.split("\n") if line.strip()]
    if len(lines) >= 2:
        points = [line for line in lines if len(line) > 8]
    else:
        points = [part.strip() for part in _SENTENCE_RE.split(raw) if len(part.strip()) > 20]

    if not points:
        points = [raw[:160]]
    return points[:limit]


def build_storyboard(
    topic: str,
    content: str,
    reel_number: int,
    total_reels: int,
    voice: str,
    series_title: str,
    handle: str | None = None,
    theme: str | None = None,
) -> Storyboard:
    settings = get_settings()
    voice = _validate_voice(voice)
    handle = handle or settings.default_handle
    theme = theme or settings.default_theme
    key_points = extract_key_points(content)

    next_up = (
        f"Part {reel_number + 1}"
        if reel_number < total_reels
        else "the series recap"
    )
    takeaway = key_points[0]

    scenes = [
        Scene(
            id=1,
            layout="title",
            narration=(
                f"Welcome to {series_title}. Today we cover {topic}. "
                f"This is reel {reel_number} of {total_reels}."
            ),
            visual={
                "title": topic,
                "subtitle": f"{series_title} • Part {reel_number} of {total_reels}",
            },
        ),
        Scene(
            id=2,
            layout="concept",
            narration=f"{topic} is a fundamental concept. {key_points[0]}",
            visual={
                "keyword": topic.upper(),
                "support": key_points[1] if len(key_points) > 1 else "Core concept explanation",
            },
        ),
        _aspects_or_diagram_scene(topic, key_points),
        Scene(
            id=4,
            layout="comparison",
            narration=(
                f"Comparing approaches: traditional methods versus modern {topic} techniques. "
                "The new approach offers significant advantages."
            ),
            visual={
                "heading": f"Traditional vs Modern {topic}",
                "left": {
                    "heading": "Traditional",
                    "points": ["Manual process", "Limited scale", "Error prone", "Slow iteration"],
                },
                "right": {
                    "heading": f"Modern {topic}",
                    "points": ["Automated", "Scalable", "Self-correcting", "Fast iteration"],
                },
            },
        ),
        Scene(
            id=5,
            layout="outro",
            narration=(
                f"That covers {topic}. Key takeaway: {takeaway}. "
                f"Next up: {next_up}. Follow {handle} for daily AI agent tips!"
            ),
            visual={
                "title": topic,
                "cta": f"Follow {handle} for daily AI tips!",
            },
        ),
    ]

    return Storyboard(
        title=f"{series_title}: {topic}",
        handle=handle,
        theme=theme,
        voice=voice,
        tts_provider="sarvam",
        scenes=scenes,
    )


def _aspects_or_diagram_scene(topic: str, key_points: list[str]) -> Scene:
    extra = key_points[2:6]
    if extra:
        return Scene(
            id=3,
            layout="steps",
            narration=f"Key aspects of {topic}: " + "; ".join(extra[:3]),
            visual={
                "heading": f"Key Aspects of {topic}",
                "items": extra,
            },
        )
    return Scene(
        id=3,
        layout="diagram",
        narration=f"Here is how {topic} works in practice.",
        visual={
            "nodes": [
                {"id": "input", "label": "Input", "row": 1, "col": -1},
                {"id": "process", "label": topic, "row": 0, "col": 0},
                {"id": "output", "label": "Output", "row": 1, "col": 1},
                {"id": "feedback", "label": "Feedback Loop", "row": -1, "col": 0},
            ],
            "edges": [
                {"from": "input", "to": "process"},
                {"from": "process", "to": "output"},
                {"from": "output", "to": "feedback"},
                {"from": "feedback", "to": "process"},
            ],
        },
    )


def create_storyboard(
    topic: str,
    content: str,
    reel_number: int = 1,
    total_reels: int = 1,
    voice: str = "anushka",
    series_title: str | None = None,
) -> dict[str, Any]:
    """Create a storyboard JSON for an educational reel."""
    settings = get_settings()
    series_title = series_title or settings.default_series_title
    try:
        storyboard = build_storyboard(
            topic=topic,
            content=content,
            reel_number=reel_number,
            total_reels=total_reels,
            voice=voice,
            series_title=series_title,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    series_dir = _storyboards_root() / slugify(series_title)
    series_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{reel_number:02d}-{slugify(topic)}.json"
    filepath = series_dir / filename
    filepath.write_text(
        json.dumps(storyboard.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    scene_count = len(storyboard.scenes)
    return {
        "status": "success",
        "storyboard_path": str(filepath),
        "topic": topic,
        "voice": storyboard.voice,
        "reel_number": reel_number,
        "total_reels": total_reels,
        "scenes": scene_count,
        "estimated_duration": f"{scene_count * 10}-{scene_count * 15}s",
    }


def _parse_render_output(stdout: str) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for line in stdout.splitlines():
        if "TTS engine:" in line:
            info["voice"] = line.split("voice:")[-1].strip() if "voice:" in line else "sarvam"
        elif "@" in line and "fps" in line:
            for part in line.split("|"):
                part = part.strip()
                if "x" in part and "fps" in part:
                    info["resolution"] = part.split("@")[0].strip()
                elif part.endswith("s") and part[0].isdigit():
                    info["duration"] = part
    return info


def render_reel(
    storyboard_path: str,
    output_filename: str | None = None,
    preview: bool = False,
) -> dict[str, Any]:
    """Render a reel from a storyboard JSON via the reelgen CLI."""
    settings = get_settings()
    try:
        board_path = resolve_existing_under(_storyboards_root(), storyboard_path)
    except (ValueError, FileNotFoundError) as exc:
        return {"status": "error", "error": f"Storyboard not found: {exc}"}

    if output_filename:
        name = Path(output_filename).name
        if not name.endswith(".mp4"):
            return {"status": "error", "error": "output_filename must be an .mp4 basename"}
        output_path = safe_under(_output_root(), name)
    else:
        output_path = _output_root() / f"{board_path.stem}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not settings.sarvam_api_key:
        return {"status": "error", "error": "SARVAM_API_KEY is not set"}

    cmd = [
        settings.reelgen_executable(),
        "-m",
        settings.reelgen_module,
        "build",
        str(board_path),
        "--out",
        str(output_path),
    ]
    if preview:
        cmd.append("--preview")

    env = os.environ.copy()
    env["SARVAM_API_KEY"] = settings.sarvam_api_key

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=settings.render_timeout_seconds,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": f"Render timeout ({settings.render_timeout_seconds}s)",
        }
    except FileNotFoundError as exc:
        return {"status": "error", "error": f"reelgen executable not found: {exc}"}
    except OSError as exc:
        return {"status": "error", "error": str(exc)}

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "Unknown error")[-1000:]
        logger.error("reelgen failed: %s", stderr)
        return {"status": "error", "error": stderr}

    output_info = _parse_render_output(result.stdout or "")
    return {
        "status": "success",
        "output_path": str(output_path),
        "duration": output_info.get("duration"),
        "resolution": output_info.get("resolution"),
        "voice": output_info.get("voice"),
    }


def batch_render_reels(
    series_title: str,
    topics: list[dict[str, Any]],
    preview: bool = False,
) -> dict[str, Any]:
    """Create storyboards and render each topic in a series."""
    results: list[dict[str, Any]] = []
    for index, topic_info in enumerate(topics, 1):
        topic = topic_info.get("topic")
        if not topic:
            results.append({"status": "error", "error": "topic is required", "topic": ""})
            continue
        sb_result = create_storyboard(
            topic=topic,
            content=topic_info.get("content", ""),
            reel_number=index,
            total_reels=len(topics),
            voice=topic_info.get("voice", "anushka"),
            series_title=series_title,
        )
        if sb_result["status"] != "success":
            results.append(
                {
                    "topic": topic,
                    "status": "error",
                    "error": sb_result.get("error"),
                }
            )
            continue
        output_name = (
            f"{slugify(series_title)}-{index:02d}-{slugify(topic)}-hd.mp4"
        )
        render_result = render_reel(sb_result["storyboard_path"], output_name, preview)
        render_result["topic"] = topic
        results.append(render_result)

    success_count = sum(1 for item in results if item.get("status") == "success")
    return {
        "status": "completed",
        "series": series_title,
        "total": len(topics),
        "successful": success_count,
        "results": results,
    }


def generate_social_copy(
    topic: str,
    reel_number: int = 1,
    total_reels: int = 1,
    series_title: str | None = None,
    voice: str = "anushka",
    duration: str = "60s",
) -> dict[str, Any]:
    """Generate platform-optimized social media copy."""
    settings = get_settings()
    series_title = series_title or settings.default_series_title
    handle = settings.default_handle
    try:
        _validate_voice(voice)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    hashtags = {
        "instagram": (
            "#AIAgents #AgenticAI #Oracle #GenAI #MachineLearning "
            "#TechEducation #ArtificialIntelligence #AIEngineering "
            "#DeveloperTools #Innovation"
        ),
        "twitter": "#AIAgents #AgenticAI #GenAI",
        "linkedin": (
            "#AIAgents #AgenticAI #SoftwareEngineering #MachineLearning "
            "#OracleCloud #GenAI #TechLeadership"
        ),
        "youtube": (
            "AI Agents, Agentic AI, Oracle, Generative AI, Machine Learning, "
            "Software Engineering, AI Architecture, Production AI"
        ),
    }

    copy = {
        "youtube": {
            "title": f"{topic} | {series_title} Part {reel_number}/{total_reels}",
            "description": (
                f"Learn about {topic} in this {duration} reel from the {series_title} series.\n\n"
                f"Part {reel_number} of {total_reels}.\n\n"
                "Key topics covered:\n"
                "- Core concepts and fundamentals\n"
                "- Practical implementation\n"
                "- Comparison with traditional approaches\n"
                "- Best practices and pitfalls\n\n"
                "This series covers AI agent basics through production deployment "
                "on Oracle Cloud Infrastructure.\n\n"
                f"Follow {handle} for daily AI agent deep dives!\n\n"
                f"{hashtags['youtube']}"
            ),
            "tags": ["AI Agents", "Agentic AI", "Oracle", "GenAI", "Machine Learning", topic],
        },
        "instagram": {
            "caption": (
                f"{topic}\n\n"
                f"Part {reel_number} of {total_reels} in the {series_title} series.\n\n"
                "Key takeaways:\n"
                "- Core concepts explained simply\n"
                "- Practical implementation guide\n"
                "- Traditional vs modern comparison\n"
                "- Production best practices\n\n"
                f"{duration} of AI agent knowledge.\n\n"
                f"Follow {handle} for daily AI agent tips!\n\n"
                f"{hashtags['instagram']}"
            ),
            "hashtags": hashtags["instagram"],
        },
        "twitter": {
            "text": (
                f"{topic} - Part {reel_number}/{total_reels}\n\n"
                f"{series_title} covers this concept in {duration}.\n\n"
                "Key points:\n"
                "- Core concepts\n"
                "- Practical implementation\n"
                "- Best practices\n\n"
                f"{hashtags['twitter']}\n\n"
                f"Follow {handle}"
            ),
            "hashtags": hashtags["twitter"],
        },
        "linkedin": {
            "headline": f"{topic} | {series_title} Series",
            "post": (
                f"**{topic}** — Part {reel_number} of {total_reels} in the {series_title} series.\n\n"
                f"In this {duration} deep dive, we cover:\n"
                "- The core concepts and why they matter\n"
                "- Practical implementation approaches\n"
                "- Traditional vs modern comparison\n"
                "- Production best practices and pitfalls\n\n"
                "This series goes from AI agent fundamentals to production deployment "
                "on Oracle Cloud Infrastructure — reasoning patterns (ReAct, CoT, ToT), "
                "agent architectures, safety guardrails, and enterprise deployment.\n\n"
                f"What's your experience with {topic.lower()}?\n\n"
                f"{hashtags['linkedin']}\n\n"
                f"Follow {handle} for production agent patterns."
            ),
        },
    }
    return {"status": "success", "topic": topic, "social_copy": copy}


def register_tools() -> list[Any]:
    """Return tool callables for ADK agent registration."""
    return [
        create_storyboard,
        render_reel,
        batch_render_reels,
        generate_social_copy,
    ]


# Re-export palette/voices for existing API consumers.
__all__ = [
    "ORACLE_PALETTE",
    "SARVAM_VOICES",
    "batch_render_reels",
    "build_storyboard",
    "create_storyboard",
    "extract_key_points",
    "generate_social_copy",
    "register_tools",
    "render_reel",
]
