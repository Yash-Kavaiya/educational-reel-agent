#!/bin/bash
# Oracle Reel Agent - Cloud Run Deployment Script
# Usage: ./scripts/deploy.sh [staging|production] [PROJECT_ID] [REGION]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-staging}"
PROJECT_ID="${2:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${3:-us-central1}"
REPOSITORY="oracle-reel-agent"
SERVICE_NAME="oracle-reel-agent"
SERVICE_ACCOUNT="oracle-reel-agent@${PROJECT_ID}.iam.gserviceaccount.com"

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
        log_error "GCP Project ID not set. Run 'gcloud config set project YOUR_PROJECT_ID' or pass as argument."
        exit 1
    fi
    
    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 &> /dev/null; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login'."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "secretmanager.googleapis.com"
        "youtube.googleapis.com"
        "aiplatform.googleapis.com"
        "storage.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        log_info "  Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID" --quiet
    done
    
    log_success "All APIs enabled"
}

# Create Artifact Registry repository
create_artifact_registry() {
    log_info "Creating Artifact Registry repository..."
    
    if gcloud artifacts repositories describe "$REPOSITORY" \
        --location="$REGION" \
        --project="$PROJECT_ID" &> /dev/null; then
        log_info "Repository $REPOSITORY already exists"
    else
        gcloud artifacts repositories create "$REPOSITORY" \
            --repository-format=docker \
            --location="$REGION" \
            --project="$PROJECT_ID" \
            --description="Oracle Reel Agent Docker images" \
            --quiet
        log_success "Artifact Registry repository created"
    fi
}

# Create service account
create_service_account() {
    log_info "Creating service account..."
    
    if gcloud iam service-accounts describe "$SERVICE_ACCOUNT" \
        --project="$PROJECT_ID" &> /dev/null; then
        log_info "Service account already exists"
    else
        gcloud iam service-accounts create "oracle-reel-agent" \
            --display-name="Oracle Reel Agent Service Account" \
            --project="$PROJECT_ID" \
            --quiet
        log_success "Service account created"
    fi
    
    # Grant necessary roles
    local roles=(
        "roles/run.invoker"
        "roles/storage.objectViewer"
        "roles/secretmanager.secretAccessor"
        "roles/aiplatform.user"
        "roles/youtube.admin"
    )
    
    for role in "${roles[@]}"; do
        log_info "  Granting $role..."
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="$role" \
            --quiet > /dev/null
    done
    
    log_success "Service account roles configured"
}

# Create secrets in Secret Manager
create_secrets() {
    log_info "Creating secrets in Secret Manager..."
    
    # Sarvam API Key
    if gcloud secrets describe "sarvam-api-key" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret sarvam-api-key already exists"
    else
        echo -n "${SARVAM_API_KEY:-}" | gcloud secrets create "sarvam-api-key" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --quiet
        log_success "Created sarvam-api-key secret"
    fi
    
    # YouTube credentials (OAuth client)
    if gcloud secrets describe "youtube-credentials" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret youtube-credentials already exists"
    else
        if [ -f "$HOME/.youtube_credentials.json" ]; then
            gcloud secrets create "youtube-credentials" \
                --data-file="$HOME/.youtube_credentials.json" \
                --project="$PROJECT_ID" \
                --quiet
            log_success "Created youtube-credentials secret"
        else
            log_warning "YouTube credentials file not found at ~/.youtube_credentials.json"
            log_warning "Create it from Google Cloud Console > APIs & Services > Credentials"
        fi
    fi
    
    # YouTube token (will be created after first auth)
    if gcloud secrets describe "youtube-token" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret youtube-token already exists"
    else
        echo -n "{}" | gcloud secrets create "youtube-token" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --quiet
        log_success "Created youtube-token secret (placeholder)"
    fi
    
    # Grant service account access to secrets
    for secret in "sarvam-api-key" "youtube-credentials" "youtube-token"; do
        gcloud secrets add-iam-policy-binding "$secret" \
            --member="serviceAccount:$SERVICE_ACCOUNT" \
            --role="roles/secretmanager.secretAccessor" \
            --project="$PROJECT_ID" \
            --quiet > /dev/null
    done
}

# Build and push Docker image
build_and_push() {
    log_info "Building and pushing Docker image..."
    
    cd "$PROJECT_ROOT"
    
    # Configure Docker for Artifact Registry
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
    
    # Build image
    local image_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:$(date +%Y%m%d-%H%M%S)"
    local image_latest="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:latest"
    
    log_info "Building image: $image_tag"
    docker build -t "$image_tag" -t "$image_latest" -f Dockerfile .
    
    log_info "Pushing images..."
    docker push "$image_tag"
    docker push "$image_latest"
    
    log_success "Image pushed: $image_tag"
    echo "$image_tag"
}

# Deploy to Cloud Run
deploy_cloud_run() {
    local image="$1"
    local env_suffix=""
    
    if [ "$ENVIRONMENT" = "staging" ]; then
        env_suffix="-staging"
    fi
    
    local service="${SERVICE_NAME}${env_suffix}"
    local min_instances="0"
    local labels="environment=${ENVIRONMENT}"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        min_instances="1"
    fi
    
    log_info "Deploying to Cloud Run: $service"
    
    gcloud run deploy "$service" \
        --image="$image" \
        --region="$REGION" \
        --platform=managed \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --min-instances="$min_instances" \
        --max-instances=10 \
        --timeout=3600 \
        --concurrency=80 \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_REGION=${REGION},LOG_LEVEL=INFO" \
        --set-secrets="SARVAM_API_KEY=projects/${PROJECT_ID}/secrets/sarvam-api-key:latest,YOUTUBE_CREDENTIALS_FILE=projects/${PROJECT_ID}/secrets/youtube-credentials:latest,YOUTUBE_TOKEN_FILE=projects/${PROJECT_ID}/secrets/youtube-token:latest" \
        --service-account="$SERVICE_ACCOUNT" \
        --labels="$labels" \
        --project="$PROJECT_ID" \
        --quiet
    
    # Get service URL
    local url=$(gcloud run services describe "$service" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format='value(status.url)')
    
    log_success "Deployed to Cloud Run: $url"
    echo "$url"
}

# Verify deployment
verify_deployment() {
    local url="$1"
    
    log_info "Verifying deployment at $url..."
    
    sleep 10
    
    for i in {1..15}; do
        if curl -f -s "$url/health" > /dev/null; then
            log_success "Health check passed!"
            curl -s "$url/health" | jq . 2>/dev/null || curl -s "$url/health"
            return 0
        fi
        log_info "Attempt $i/15 failed, retrying in 5s..."
        sleep 5
    done
    
    log_error "Health check failed after 15 attempts"
    return 1
}

# Main deployment flow
main() {
    echo "=========================================="
    echo "Oracle Reel Agent - Cloud Run Deployment"
    echo "=========================================="
    echo "Environment: $ENVIRONMENT"
    echo "Project:     $PROJECT_ID"
    echo "Region:      $REGION"
    echo "=========================================="
    echo ""
    
    check_prerequisites
    enable_apis
    create_artifact_registry
    create_service_account
    create_secrets
    
    local image=$(build_and_push)
    local url=$(deploy_cloud_run "$image")
    verify_deployment "$url"
    
    echo ""
    echo "=========================================="
    log_success "Deployment completed successfully!"
    echo "=========================================="
    echo "Service URL: $url"
    echo "Health Check: $url/health"
    echo "API Docs:     $url/docs"
    echo "=========================================="
}

# Run main
main "$@"