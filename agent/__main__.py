"""python -m agent → FastAPI."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("agent.main:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
