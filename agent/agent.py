"""ADK root agent. Importable by `adk web` and the FastAPI runner."""

from __future__ import annotations

from google.adk.agents import Agent

from agent.config import get_settings
from agent.prompts import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_NAME, ROOT_INSTRUCTION
from agent.tools.reel_tools import (
    batch_render_reels,
    create_storyboard,
    generate_social_copy,
    render_reel,
)
from agent.tools.youtube_tools import upload_video_to_youtube

_settings = get_settings()

root_agent = Agent(
    name=ROOT_AGENT_NAME,
    model=_settings.adk_model,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_INSTRUCTION,
    tools=[
        create_storyboard,
        render_reel,
        generate_social_copy,
        batch_render_reels,
        upload_video_to_youtube,
    ],
)
