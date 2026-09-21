from __future__ import annotations

from pathlib import Path

import pytest

from agent.paths import resolve_existing_under, safe_under, slugify


def test_slugify_strips_punctuation_and_case():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  AI Agents  ") == "ai-agents"


def test_slugify_empty_becomes_untitled():
    assert slugify("***") == "untitled"
    assert slugify("") == "untitled"


def test_safe_under_allows_relative_child(tmp_path: Path):
    child = safe_under(tmp_path, "series/file.json")
    assert child == (tmp_path / "series" / "file.json").resolve()


def test_safe_under_rejects_parent_escape(tmp_path: Path):
    with pytest.raises(ValueError, match="escapes root"):
        safe_under(tmp_path, "../secret.json")


def test_safe_under_rejects_absolute_outside(tmp_path: Path):
    outsider = Path.cwd().resolve()
    if outsider.is_relative_to(tmp_path.resolve()):
        pytest.skip("cwd is inside tmp")
    with pytest.raises(ValueError, match="escapes root"):
        safe_under(tmp_path, outsider / "nope.json")


def test_resolve_existing_under_requires_file(tmp_path: Path):
    target = tmp_path / "board.json"
    target.write_text("{}", encoding="utf-8")
    assert resolve_existing_under(tmp_path, "board.json") == target.resolve()
    with pytest.raises(FileNotFoundError):
        resolve_existing_under(tmp_path, "missing.json")
