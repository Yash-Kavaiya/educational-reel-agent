# Educational Reel Agent - Cloud Run image
# Multi-stage build. Render extras (Manim) are optional via INSTALL_RENDER.

FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    pkg-config \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN python -m venv /opt/venv
COPY requirements.txt requirements-render.txt ./
ARG INSTALL_RENDER=true
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && if [ "$INSTALL_RENDER" = "true" ]; then pip install -r requirements-render.txt; fi

FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libxml2 \
    libxslt1.1 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -m appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    OUTPUT_DIR="/app/output" \
    STORYBOARDS_DIR="/app/storyboards" \
    LOGS_DIR="/app/logs"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY agent/ ./agent/
COPY entrypoint.sh healthcheck.py ./

RUN mkdir -p /app/output /app/storyboards /app/logs \
    && chmod +x /app/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python /app/healthcheck.py

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
