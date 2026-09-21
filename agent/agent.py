"""ADK root agent. Importable by `adk web` and the FastAPI runner.

Chat and tools run on InclusionAI Ling 3.0 Flash Fin (free) through
LiteLLM + Vercel AI Gateway. TypeSafe Jev is registered as an evaluation tool.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent

from agent.llm import build_agent_model
from agent.prompts import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_NAME, ROOT_INSTRUCTION
from agent.tools.eval_tools import evaluate_with_jev
from agent.tools.reel_tools import (
    batch_render_reels,
    create_storyboard,
    generate_social_copy,
    render_reel,
)
from agent.tools.youtube_tools import upload_video_to_youtube

root_agent = LlmAgent(
    name=ROOT_AGENT_NAME,
    model=build_agent_model(),
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_INSTRUCTION,
    tools=[
        create_storyboard,
        render_reel,
        generate_social_copy,
        batch_render_reels,
        upload_video_to_youtube,
        evaluate_with_jev,
    ],
)
