"""Educational Reel Creator Agent - ADK package."""

from __future__ import annotations

__all__ = ["root_agent"]


def __getattr__(name: str):
    if name == "root_agent":
        from agent.agent import root_agent

        return root_agent
    raise AttributeError(name)
