#!/bin/bash
# Entrypoint for Educational Reel Agent (Cloud Run / local Linux)

set -euo pipefail

export PORT="${PORT:-8080}"
export HOST="${HOST:-0.0.0.0}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export PYTHONPATH="/app:${PYTHONPATH:-}"
export OUTPUT_DIR="${OUTPUT_DIR:-/app/output}"
export STORYBOARDS_DIR="${STORYBOARDS_DIR:-/app/storyboards}"
export LOGS_DIR="${LOGS_DIR:-/app/logs}"
export YOUTUBE_CREDENTIALS_FILE="${YOUTUBE_CREDENTIALS_FILE:-/secrets/youtube_credentials.json}"
export YOUTUBE_TOKEN_FILE="${YOUTUBE_TOKEN_FILE:-/secrets/youtube_token.json}"

mkdir -p "$OUTPUT_DIR" "$STORYBOARDS_DIR" "$LOGS_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Educational Reel Agent on ${HOST}:${PORT}"
log "Project: ${GOOGLE_CLOUD_PROJECT:-unset}"
log "Region: ${GOOGLE_CLOUD_REGION:-us-central1}"

LEVEL="$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')"

exec python -m uvicorn agent.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LEVEL" \
    --access-log \
    --workers 1
