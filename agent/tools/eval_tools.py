"""TypeSafe Jev evaluation via Vercel AI Gateway (LiteLLM)."""

from __future__ import annotations

import json
import logging
from typing import Any

from agent.config import get_settings
from agent.llm import apply_gateway_credentials, gateway_model_id

logger = logging.getLogger(__name__)


def evaluate_with_jev(
    state: str,
    question: str,
) -> dict[str, Any]:
    """Ask TypeSafe Jev a structured evaluation question about agent state.

    Jev is an evaluation model, not the reel-creation LLM. Use it to score
    a storyboard, narration, or render result. Requires VERCEL_AI_GATEWAY_API_KEY
    or AI_GATEWAY_API_KEY.
    """
    settings = get_settings()
    key = apply_gateway_credentials()
    if not key:
        return {"status": "error", "error": "VERCEL_AI_GATEWAY_API_KEY is not set"}
    if not (state or "").strip() or not (question or "").strip():
        return {"status": "error", "error": "state and question are required"}

    try:
        import litellm
    except ImportError as exc:
        return {"status": "error", "error": f"litellm is not installed: {exc}"}

    model = gateway_model_id(settings.jev_model)
    messages = [
        {
            "role": "system",
            "content": (
                "You are TypeSafe Jev. Answer with compact JSON only: "
                '{"answer": true|false|"...", "score": 0-1, "reason": "short"}'
            ),
        },
        {
            "role": "user",
            "content": f"State:\n{state.strip()}\n\nQuestion:\n{question.strip()}",
        },
    ]
    try:
        response = litellm.completion(model=model, messages=messages, temperature=0)
        content = response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 — tool contract returns error dicts
        logger.exception("Jev evaluation failed")
        return {"status": "error", "error": str(exc), "model": model}

    parsed: Any = content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                parsed = {"raw": content}

    return {"status": "success", "model": model, "evaluation": parsed}
