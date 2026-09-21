#!/bin/bash
# Deploy Educational Reel Agent to Cloud Run
# Usage: ./scripts/deploy.sh [staging|production] [PROJECT_ID] [REGION]

set -euo pipefail

ENVIRONMENT="${1:-staging}"
PROJECT_ID="${2:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${3:-us-central1}"
REPOSITORY="educational-reel-agent"
SERVICE_NAME="educational-reel-agent"
SERVICE_ACCOUNT="educational-reel-agent@${PROJECT_ID}.iam.gserviceaccount.com"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log() { echo "[INFO] $*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

command -v gcloud >/dev/null || die "gcloud CLI not found"
command -v docker >/dev/null || die "Docker not found"
[[ -n "$PROJECT_ID" && "$PROJECT_ID" != "(unset)" ]] || die "Pass PROJECT_ID or run gcloud config set project"

log "Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  youtube.googleapis.com \
  aiplatform.googleapis.com \
  --project="$PROJECT_ID" --quiet

if ! gcloud artifacts repositories describe "$REPOSITORY" --location="$REGION" --project="$PROJECT_ID" &>/dev/null; then
  gcloud artifacts repositories create "$REPOSITORY" \
    --repository-format=docker --location="$REGION" --project="$PROJECT_ID" \
    --description="Educational Reel Agent images" --quiet
fi

if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" &>/dev/null; then
  gcloud iam service-accounts create "educational-reel-agent" \
    --display-name="Educational Reel Agent" --project="$PROJECT_ID" --quiet
fi

for role in roles/run.invoker roles/secretmanager.secretAccessor roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" --role="$role" --quiet >/dev/null
done

if ! gcloud secrets describe sarvam-api-key --project="$PROJECT_ID" &>/dev/null; then
  [[ -n "${SARVAM_API_KEY:-}" ]] || die "Create secret sarvam-api-key or export SARVAM_API_KEY"
  printf '%s' "$SARVAM_API_KEY" | gcloud secrets create sarvam-api-key --data-file=- --project="$PROJECT_ID" --quiet
fi

cd "$PROJECT_ROOT"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:$(date +%Y%m%d-%H%M%S)"
docker build -t "$IMAGE" -f Dockerfile .
docker push "$IMAGE"

SUFFIX=""
MIN_INSTANCES=0
if [[ "$ENVIRONMENT" == "staging" ]]; then
  SUFFIX="-staging"
elif [[ "$ENVIRONMENT" == "production" ]]; then
  MIN_INSTANCES=1
else
  die "environment must be staging or production"
fi

SERVICE="${SERVICE_NAME}${SUFFIX}"
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --no-allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances="$MIN_INSTANCES" \
  --max-instances=10 \
  --timeout=3600 \
  --concurrency=8 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},LOG_LEVEL=INFO" \
  --set-secrets="SARVAM_API_KEY=sarvam-api-key:latest" \
  --service-account="$SERVICE_ACCOUNT" \
  --project="$PROJECT_ID" \
  --quiet

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')"
log "Deployed $SERVICE -> $URL"
TOKEN="$(gcloud auth print-identity-token)"
curl -fsS -H "Authorization: Bearer ${TOKEN}" "$URL/health"
echo
log "Health OK. Grant roles/run.invoker to callers; the service is not public."
