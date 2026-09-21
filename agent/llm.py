"""LiteLLM models via Vercel AI Gateway.

Agent chat/tools use InclusionAI Ling 3.0 Flash Fin (free).
TypeSafe Jev is the structured evaluation model (not the tool-calling agent).

https://vercel.com/docs/ai-gateway/ecosystem/framework-integrations/litellm
https://vercel.com/ai-gateway/models/ling-3.0-flash-fin-free
https://vercel.com/ai-gateway/models/jev
"""

from __future__ import annotations

import os

from agent.config import get_settings

VERCEL_GATEWAY_PREFIX = "vercel_ai_gateway/"
DEFAULT_AGENT_MODEL = "inclusionai/ling-3.0-flash-fin-free"
DEFAULT_JEV_MODEL = "typesafe-ai/jev"
GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"


def gateway_model_id(model: str) -> str:
    """Return a LiteLLM model string for Vercel AI Gateway."""
    name = (model or "").strip()
    if not name:
        name = DEFAULT_AGENT_MODEL
    if name.startswith(VERCEL_GATEWAY_PREFIX):
        return name
    if name.startswith(("openai/", "anthropic/", "gemini/")):
        return name
    return f"{VERCEL_GATEWAY_PREFIX}{name}"


def apply_gateway_credentials() -> str:
    """Copy AI Gateway keys into the env vars LiteLLM reads. Return the key (may be empty)."""
    settings = get_settings()
    key = settings.gateway_api_key
    if key:
        os.environ["VERCEL_AI_GATEWAY_API_KEY"] = key
        os.environ.setdefault("AI_GATEWAY_API_KEY", key)
    return key


def build_agent_model():
    """ADK LiteLlm wrapper for Ling (or ADK_MODEL override) via Vercel AI Gateway."""
    apply_gateway_credentials()
    from google.adk.models.lite_llm import LiteLlm

    settings = get_settings()
    return LiteLlm(model=gateway_model_id(settings.adk_model))
