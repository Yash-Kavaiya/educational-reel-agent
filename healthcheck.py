#!/usr/bin/env python3
"""HTTP health check used by Docker HEALTHCHECK and Cloud Run probes."""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    port = os.getenv("PORT", "8080")
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return 0 if 200 <= response.status < 300 else 1
    except (urllib.error.URLError, TimeoutError, OSError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
