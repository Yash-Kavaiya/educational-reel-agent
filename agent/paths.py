"""Path and filename helpers. Fail closed on traversal."""

from __future__ import annotations

from pathlib import Path
import re

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_len: int = 80) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return (slug or "untitled")[:max_len]


def safe_under(root: Path, relative: str | Path) -> Path:
    """Resolve relative against root. Reject absolute paths and `..` escapes."""
    root_resolved = root.resolve()
    candidate = Path(relative)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root_resolved / candidate).resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"path escapes root: {relative}")
    return resolved


def resolve_existing_under(root: Path, user_path: str) -> Path:
    path = safe_under(root, user_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return path
