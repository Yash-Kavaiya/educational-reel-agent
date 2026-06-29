#!/bin/bash
# Entrypoint for Oracle Reel Agent Cloud Run service

set -e

# Default configuration
export PORT=${PORT:-8080}
export HOST=${HOST:-0.0.0.0}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Google Cloud configuration
export GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}
export GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION:-us-central1}

# Application paths
export PYTHONPATH="/app:/app/agent:${PYTHONPATH}"
export OUTPUT_DIR="/app/output"
export STORYBOARDS_DIR="/app/storyboards"
export LOGS_DIR="/app/logs"

# Sarvam AI API key (will be set via Secret Manager in production)
export SARVAM_API_KEY=${SARVAM_API_KEY:-""}

# YouTube OAuth credentials (will be mounted from Secret Manager)
export YOUTUBE_CREDENTIALS_FILE=${YOUTUBE_CREDENTIALS_FILE:-"/secrets/youtube_credentials.json"}
export YOUTUBE_TOKEN_FILE=${YOUTUBE_TOKEN_FILE:-"/secrets/youtube_token.json"}

# Create directories
mkdir -p "$OUTPUT_DIR" "$STORYBOARDS_DIR" "$LOGS_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Starting Oracle Reel Agent on port $PORT"
log "Project: $GOOGLE_CLOUD_PROJECT"
log "Region: $GOOGLE_CLOUD_REGION"

# Check if running in Cloud Run (has PORT env var)
if [ -n "$PORT" ] && [ "$PORT" != "8080" ]; then
    log "Running in Cloud Run environment"
fi

# Start the FastAPI server
log "Starting FastAPI server..."
exec python -m uvicorn agent.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "${LOG_LEVEL,,}" \
    --access-log \
    --workers 1