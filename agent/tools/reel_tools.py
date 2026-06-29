"""
Tools for Oracle Reel Creator Agent
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Oracle brand palette
ORACLE_PALETTE = {
    "bg": "#0D0D0D",
    "bg_accent": "#1A0A0A",
    "text": "#F5F0F0",
    "muted": "#A08080",
    "accent": "#E01C24",
    "accent2": "#FF6600",
    "highlight": "#FF9900",
    "node": "#1A0A0A",
    "node_edge": "#E01C24",
}

# Sarvam voices
SARVAM_VOICES = {
    "anushka": "Professional female - general tech, announcements",
    "arvind": "Professional male - technical tutorials",
    "meera": "Warm female - educational content",
    "kabir": "Deep male - serious/technical",
    "diya": "Energetic female - social media",
    "arya": "Neutral - international",
    "pavithra": "Tamil/English - South India",
}

# Base paths
BASE_DIR = Path("/home/yashk")
STORYBOARDS_DIR = BASE_DIR / "storyboards"
OUTPUT_DIR = BASE_DIR / "output"
REELGEN_PYTHON = BASE_DIR / "venv-adk" / "bin" / "python"


def get_reelgen_env() -> Dict[str, str]:
    """Get environment with Sarvam API key and paths."""
    env = os.environ.copy()
    env["SARVAM_API_KEY"] = "sk_d34oxkqo_XIp3G3YdGLLHYO7SfWqpZKZO"
    env["PYTHONPATH"] = str(BASE_DIR / "miniconda3" / "lib" / "python3.13" / "site-packages")
    return env


def create_storyboard(
    topic: str,
    content: str,
    reel_number: int = 1,
    total_reels: int = 1,
    voice: str = "anushka",
    series_title: str = "Oracle AI Agents"
) -> Dict[str, Any]:
    """
    Create a storyboard JSON for an Oracle-branded reel.
    
    Args:
        topic: The main topic/title of the reel
        content: Detailed content to cover in the reel
        reel_number: Which reel in a series (1-based)
        total_reels: Total reels in series
        voice: Sarvam AI voice to use
        series_title: Title of the series
    
    Returns:
        Dict with storyboard path and metadata
    """
    # Validate voice
    if voice not in SARVAM_VOICES:
        voice = "anushka"
    
    # Create series directory
    series_dir = STORYBOARDS_DIR / series_title.lower().replace(" ", "-")
    series_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate storyboard based on content analysis
    storyboard = _generate_storyboard_structure(
        topic, content, reel_number, total_reels, voice, series_title
    )
    
    # Save storyboard
    filename = f"{reel_number:02d}-{topic.lower().replace(' ', '-')}.json"
    filepath = series_dir / filename
    
    with open(filepath, "w") as f:
        json.dump(storyboard, f, indent=2)
    
    return {
        "status": "success",
        "storyboard_path": str(filepath),
        "topic": topic,
        "voice": voice,
        "scenes": len(storyboard["scenes"]),
        "estimated_duration": f"{len(storyboard['scenes']) * 10}-{len(storyboard['scenes']) * 15}s"
    }


def _generate_storyboard_structure(
    topic: str,
    content: str,
    reel_number: int,
    total_reels: int,
    voice: str,
    series_title: str
) -> Dict[str, Any]:
    """Generate a 5-6 scene storyboard structure."""
    
    # Parse content into key points (simplified)
    key_points = _extract_key_points(content)
    
    scenes = [
        {
            "id": 1,
            "layout": "title",
            "narration": f"Welcome to {series_title}. Today we cover {topic}. This is reel {reel_number} of {total_reels}.",
            "visual": {
                "title": topic,
                "subtitle": f"{series_title} • Part {reel_number} of {total_reels}"
            }
        },
        {
            "id": 2,
            "layout": "concept",
            "narration": f"{topic} is a fundamental concept. {key_points[0] if key_points else 'Let me explain the core idea.'}",
            "visual": {
                "keyword": topic.upper(),
                "support": key_points[1] if len(key_points) > 1 else "Core concept explanation"
            }
        },
        {
            "id": 3,
            "layout": "steps" if len(key_points) > 2 else "diagram",
            "narration": f"Key aspects of {topic}: " + "; ".join(key_points[2:5]) if len(key_points) > 2 else f"Here's how {topic} works in practice.",
            "visual": {
                "heading": f"Key Aspects of {topic}",
                "items": key_points[2:6] if len(key_points) > 2 else ["Core mechanism", "Implementation", "Best practices", "Common pitfalls"]
            } if len(key_points) > 2 else {
                "nodes": [
                    {"id": "input", "label": "Input", "row": 1, "col": -1},
                    {"id": "process", "label": topic, "row": 0, "col": 0},
                    {"id": "output", "label": "Output", "row": 1, "col": 1},
                    {"id": "feedback", "label": "Feedback Loop", "row": -1, "col": 0}
                ],
                "edges": [
                    {"from": "input", "to": "process"},
                    {"from": "process", "to": "output"},
                    {"from": "output", "to": "feedback"},
                    {"from": "feedback", "to": "process"}
                ]
            }
        },
        {
            "id": 4,
            "layout": "comparison",
            "narration": f"Comparing approaches: Traditional methods versus modern {topic} techniques. The new approach offers significant advantages.",
            "visual": {
                "heading": f"Traditional vs Modern {topic}",
                "left": {
                    "heading": "Traditional",
                    "points": ["Manual process", "Limited scale", "Error prone", "Slow iteration"]
                },
                "right": {
                    "heading": f"Modern {topic}",
                    "points": ["Automated", "Scalable", "Self-correcting", "Fast iteration"]
                }
            }
        },
        {
            "id": 5,
            "layout": "outro",
            "narration": f"That covers {topic}. Key takeaway: {key_points[0] if key_points else 'Master the fundamentals.'} Next up: {f'Part {reel_number + 1}' if reel_number < total_reels else 'the complete series recap'}. Follow @genai_guru for daily AI agent tips!",
            "visual": {
                "title": topic,
                "cta": f"Follow @genai_guru for daily AI tips!"
            }
        }
    ]
    
    return {
        "title": f"{series_title}: {topic}",
        "handle": "@genai_guru",
        "theme": "oracle",
        "voice": voice,
        "tts_provider": "sarvam",
        "scenes": scenes
    }


def _extract_key_points(content: str) -> List[str]:
    """Extract key points from content (simplified)."""
    # Simple extraction - split by sentences and take first few
    sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
    return sentences[:6] if sentences else [content[:100]]


def render_reel(
    storyboard_path: str,
    output_filename: Optional[str] = None,
    preview: bool = False
) -> Dict[str, Any]:
    """
    Render a reel from a storyboard JSON.
    
    Args:
        storyboard_path: Path to storyboard JSON file
        output_filename: Optional output filename
        preview: If True, render at 540x960 for fast preview
    
    Returns:
        Dict with render status and output path
    """
    storyboard_path = Path(storyboard_path)
    if not storyboard_path.exists():
        return {"status": "error", "error": f"Storyboard not found: {storyboard_path}"}
    
    # Determine output path
    if output_filename:
        output_path = OUTPUT_DIR / output_filename
    else:
        output_path = OUTPUT_DIR / f"{storyboard_path.stem}.mp4"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = [
        str(REELGEN_PYTHON), "-m", "reelgen", "build",
        str(storyboard_path),
        "--out", str(output_path)
    ]
    
    if preview:
        cmd.append("--preview")
    
    # Run render
    env = get_reelgen_env()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
        
        if result.returncode == 0:
            # Extract info from output
            output_info = _parse_render_output(result.stdout)
            return {
                "status": "success",
                "output_path": str(output_path),
                "duration": output_info.get("duration"),
                "resolution": output_info.get("resolution"),
                "voice": output_info.get("voice")
            }
        else:
            return {
                "status": "error",
                "error": result.stderr[-1000:] if result.stderr else "Unknown error"
            }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Render timeout (10 min)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _parse_render_output(stdout: str) -> Dict[str, Any]:
    """Parse render output for metadata."""
    info = {}
    for line in stdout.split("\n"):
        if "Reel ready:" in line:
            # Extract path
            pass
        elif "TTS engine:" in line:
            info["voice"] = line.split("voice:")[-1].strip() if "voice:" in line else "sarvam"
        elif "@" in line and "fps" in line:
            # Parse resolution and duration
            parts = line.split("|")
            for part in parts:
                part = part.strip()
                if "x" in part and "fps" in part:
                    info["resolution"] = part.split("@")[0].strip()
                elif "s" in part and part[0].isdigit():
                    info["duration"] = part
    return info


def batch_render_reels(
    series_title: str,
    topics: List[Dict[str, Any]],
    preview: bool = False
) -> Dict[str, Any]:
    """
    Batch render multiple reels for a series.
    
    Args:
        series_title: Title of the series
        topics: List of dicts with topic, content, voice, etc.
        preview: If True, render previews
    
    Returns:
        Dict with batch render results
    """
    results = []
    series_dir = STORYBOARDS_DIR / series_title.lower().replace(" ", "-")
    
    for i, topic_info in enumerate(topics, 1):
        # Create storyboard
        sb_result = create_storyboard(
            topic=topic_info["topic"],
            content=topic_info.get("content", ""),
            reel_number=i,
            total_reels=len(topics),
            voice=topic_info.get("voice", "anushka"),
            series_title=series_title
        )
        
        if sb_result["status"] != "success":
            results.append({"topic": topic_info["topic"], "status": "error", "error": sb_result.get("error")})
            continue
        
        # Render
        output_name = f"{series_title.lower().replace(' ', '-')}-{i:02d}-{topic_info['topic'].lower().replace(' ', '-')}-hd.mp4"
        render_result = render_reel(sb_result["storyboard_path"], output_name, preview)
        render_result["topic"] = topic_info["topic"]
        results.append(render_result)
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    
    return {
        "status": "completed",
        "series": series_title,
        "total": len(topics),
        "successful": success_count,
        "results": results
    }


def generate_social_copy(
    topic: str,
    reel_number: int = 1,
    total_reels: int = 1,
    series_title: str = "Oracle AI Agents",
    voice: str = "anushka",
    duration: str = "60s"
) -> Dict[str, Any]:
    """
    Generate platform-optimized social media copy.
    
    Args:
        topic: Reel topic
        reel_number: Reel number in series
        total_reels: Total reels
        series_title: Series title
        voice: Sarvam voice used
        duration: Reel duration
    
    Returns:
        Dict with social copy for each platform
    """
    hashtags = {
        "instagram": "#AIAgents #AgenticAI #Oracle #GenAI #MachineLearning #TechEducation #ArtificialIntelligence #AIEngineering #DeveloperTools #Innovation",
        "twitter": "#AIAgents #AgenticAI #GenAI",
        "linkedin": "#AIAgents #AgenticAI #SoftwareEngineering #MachineLearning #OracleCloud #GenAI #TechLeadership",
        "youtube": "AI Agents, Agentic AI, Oracle, Generative AI, Machine Learning, Software Engineering, AI Architecture, Production AI"
    }
    
    copy = {
        "youtube": {
            "title": f"{topic} | {series_title} Part {reel_number}/{total_reels}",
            "description": f"""Learn about {topic} in this {duration} reel from the {series_title} series.

Part {reel_number} of {total_reels}.

Key topics covered:
- Core concepts and fundamentals
- Practical implementation
- Comparison with traditional approaches
- Best practices and pitfalls

This series covers everything from AI agent basics to production deployment on Oracle Cloud Infrastructure.

Follow @genai_guru for daily AI agent deep dives!

{hashtags['youtube']}""",
            "tags": ["AI Agents", "Agentic AI", "Oracle", "GenAI", "Machine Learning", topic]
        },
        "instagram": {
            "caption": f"""{topic} 🤖

Part {reel_number} of {total_reels} in the {series_title} series.

Key takeaways:
✅ Core concepts explained simply
✅ Practical implementation guide
✅ Traditional vs modern comparison
✅ Production best practices

{duration} of pure AI agent knowledge.

Follow @genai_guru for daily AI agent tips!

{hashtags['instagram']}""",
            "hashtags": hashtags['instagram']
        },
        "twitter": {
            "text": f"""{topic} - Part {reel_number}/{total_reels} 🧵

{series_title} series covers this fundamental concept in {duration}.

Key points:
• Core concepts
• Practical implementation  
• Best practices

Thread with details 👇

{hashtags['twitter']}

Follow @genai_guru!""",
            "hashtags": hashtags['twitter']
        },
        "linkedin": {
            "headline": f"{topic} | {series_title} Series",
            "post": f"""**{topic}** — Part {reel_number} of {total_reels} in the {series_title} series.

In this {duration} deep dive, we cover:
• The core concepts and why they matter
• Practical implementation approaches
• Traditional vs modern comparison
• Production best practices and pitfalls

This series takes you from AI agent fundamentals to production deployment on Oracle Cloud Infrastructure — covering reasoning patterns (ReAct, CoT, ToT), agent architectures, safety guardrails, and enterprise deployment.

What's your experience with {topic.lower()}? The agent loop architecture is where I see most teams underinvest.

{hashtags['linkedin']}

Follow @genai_guru for production agent patterns!"""
        }
    }
    
    return {
        "status": "success",
        "topic": topic,
        "social_copy": copy
    }


# For ADK tool registration
def register_tools():
    """Return all tools for ADK agent."""
    return [
        create_storyboard,
        render_reel,
        batch_render_reels,
        generate_social_copy,
    ]