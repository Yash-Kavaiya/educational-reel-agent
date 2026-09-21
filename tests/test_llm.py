from __future__ import annotations

from agent.llm import DEFAULT_AGENT_MODEL, DEFAULT_JEV_MODEL, gateway_model_id
from agent.config import get_settings


def test_gateway_model_id_prefixes_vercel():
    assert gateway_model_id("inclusionai/ling-3.0-flash-fin-free") == (
        "vercel_ai_gateway/inclusionai/ling-3.0-flash-fin-free"
    )
    assert gateway_model_id("typesafe-ai/jev") == "vercel_ai_gateway/typesafe-ai/jev"


def test_gateway_model_id_keeps_existing_prefix():
    already = "vercel_ai_gateway/inclusionai/ling-3.0-flash-fin-free"
    assert gateway_model_id(already) == already


def test_gateway_model_id_empty_uses_default():
    assert gateway_model_id("") == f"vercel_ai_gateway/{DEFAULT_AGENT_MODEL}"


def test_default_settings_use_ling_and_jev(isolated_dirs):
    settings = get_settings()
    assert settings.adk_model == DEFAULT_AGENT_MODEL
    assert settings.jev_model == DEFAULT_JEV_MODEL
    assert gateway_model_id(settings.adk_model).startswith("vercel_ai_gateway/")


def test_gateway_api_key_aliases(isolated_dirs, monkeypatch):
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "test-key")
    monkeypatch.delenv("VERCEL_AI_GATEWAY_API_KEY", raising=False)
    settings = get_settings()
    assert settings.gateway_api_key == "test-key"
