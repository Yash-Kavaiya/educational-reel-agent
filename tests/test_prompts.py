from __future__ import annotations

import re
from pathlib import Path

from agent.prompts import ROOT_AGENT_DESCRIPTION, ROOT_INSTRUCTION

ADK_PLACEHOLDER = re.compile(r"\{+[^{}]*\}+")
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_adk_instructions_have_no_required_placeholders():
    for text in (ROOT_INSTRUCTION, ROOT_AGENT_DESCRIPTION):
        for match in ADK_PLACEHOLDER.finditer(text):
            inner = match.group(0).strip("{}")
            assert not inner.isidentifier(), f"ADK would inject {match.group(0)!r}"


def test_no_hardcoded_secrets_in_source():
    skip = {".git", ".venv", "output", "storyboards", "__pycache__", ".pytest-tmp", "tests"}
    offenders = []
    token_prefix = "sk" + "_"
    assignment = "SARVAM_API_KEY\"] = \""
    for path in REPO_ROOT.rglob("*"):
        if any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".sh", ".yaml", ".yml", ".txt", ".md", ".toml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if token_prefix in text or assignment in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []
