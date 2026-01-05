#!/bin/bash

# ============================================
# Setup Script untuk UMKM Analytics Platform
# VERSI FREE TIER - Tanpa Cloud Composer
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_skip() {
    echo -e "${YELLOW}⊘ SKIP: $1${NC}"
}

# ============================================
# Load Configuration
# ============================================
print_info "Loading configuration..."

if [ ! -f "config/config.yaml" ]; then
    print_error "config.yaml not found. Please create it from config.template.yaml"
    exit 1
fi

# Extract config values (requires yq tool)
if ! command -v yq &> /dev/null; then
    print_error "yq not found. Installing to ~/.local/bin..."
    mkdir -p ~/.local/bin
    wget -qO ~/.local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
    chmod +x ~/.local/bin/yq
    export PATH="$HOME/.local/bin:$PATH"
fi

PROJECT_ID=$(yq eval '.gcp.project_id' config/config.yaml)
REGION=$(yq eval '.gcp.region' config/config.yaml)
BUCKET_NAME=$(yq eval '.storage.bucket_name' config/config.yaml)
DATASET_ID=$(yq eval '.bigquery.dataset_id' config/config.yaml)

print_success "Configuration loaded"
print_info "Project ID: $PROJECT_ID"
print_info "Region: $REGION"

# ============================================
# Check Prerequisites
# ============================================
print_info "Checking prerequisites..."

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK"
    exit 1
fi
print_success "gcloud CLI found"

# Set project
gcloud config set project $PROJECT_ID
print_success "Project set to $PROJECT_ID"

# ============================================
# Enable Required Google Cloud APIs (FREE TIER ONLY)
# ============================================
print_info "Enabling FREE TIER Google Cloud APIs..."

# APIs yang gratis / free tier
FREE_APIS=(
    "cloudfunctions.googleapis.com"
    "bigquery.googleapis.com"
    "storage.googleapis.com"
    "cloudscheduler.googleapis.com"
    "pubsub.googleapis.com"
    "secretmanager.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
)

# APIs yang butuh billing - SKIP
PAID_APIS=(
    "composer.googleapis.com"
    "cloudbuild.googleapis.com"
)

for api in "${FREE_APIS[@]}"; do
    print_info "Enabling $api..."
    if gcloud services enable $api --project=$PROJECT_ID 2>&1; then
        print_success "$api enabled"
    else
        print_error "Failed to enable $api (may require billing)"
    fi
done

for api in "${PAID_APIS[@]}"; do
    print_skip "$api (requires billing - skipped)"
done

# ============================================
# Create Service Account for Cloud Functions
# ============================================
print_info "Creating service accounts..."

# Cloud Function Service Account
CF_SA="cloud-function-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $CF_SA &>/dev/null 2>&1; then
    print_info "Service account $CF_SA already exists"
else
    gcloud iam service-accounts create cloud-function-sa \
        --display-name="Cloud Function Service Account" \
        --project=$PROJECT_ID 2>/dev/null || print_info "Service account may already exist"
    print_success "Created $CF_SA"
fi

# Grant roles to Cloud Function SA
print_info "Granting roles to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/storage.objectCreator" \
    --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/pubsub.publisher" \
    --quiet 2>/dev/null || true

print_success "Granted roles to Cloud Function SA"

# Skip Composer SA since we're not using Composer
print_skip "Composer Service Account (not using Composer)"

# ============================================
# Create Cloud Storage Bucket
# ============================================
print_info "Creating Cloud Storage bucket..."

if gsutil ls -b gs://$BUCKET_NAME &>/dev/null 2>&1; then
    print_info "Bucket gs://$BUCKET_NAME already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME 2>/dev/null || print_info "Bucket may already exist or name is taken"
    print_success "Created bucket gs://$BUCKET_NAME"
fi

# Create folder structure
print_info "Creating bucket folder structure..."
gsutil ls gs://$BUCKET_NAME/raw/ &>/dev/null 2>&1 || echo "" | gsutil cp - gs://$BUCKET_NAME/raw/.keep 2>/dev/null || true
gsutil ls gs://$BUCKET_NAME/processed/ &>/dev/null 2>&1 || echo "" | gsutil cp - gs://$BUCKET_NAME/processed/.keep 2>/dev/null || true
gsutil ls gs://$BUCKET_NAME/archive/ &>/dev/null 2>&1 || echo "" | gsutil cp - gs://$BUCKET_NAME/archive/.keep 2>/dev/null || true

print_success "Bucket structure created"

# Set lifecycle policy
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["raw/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["processed/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME 2>/dev/null || print_info "Could not set lifecycle policy"
print_success "Lifecycle policy set"

# ============================================
# Create BigQuery Dataset
# ============================================
print_info "Creating BigQuery dataset..."

if bq ls -d --project_id=$PROJECT_ID $DATASET_ID &>/dev/null 2>&1; then
    print_info "Dataset $DATASET_ID already exists"
else
    bq mk --location=$REGION --dataset \
        --description="Dataset for UMKM Analytics" \
        $PROJECT_ID:$DATASET_ID 2>/dev/null || print_info "Dataset may already exist"
    print_success "Created dataset $DATASET_ID"
fi

# ============================================
# Create Pub/Sub Topics
# ============================================
print_info "Creating Pub/Sub topics..."

TOPICS=("data-ingestion-trigger" "etl-pipeline-trigger")

for topic in "${TOPICS[@]}"; do
    if gcloud pubsub topics describe $topic --project=$PROJECT_ID &>/dev/null 2>&1; then
        print_info "Topic $topic already exists"
    else
        gcloud pubsub topics create $topic --project=$PROJECT_ID 2>/dev/null || true
        print_success "Created topic $topic"
    fi
done

# Create subscriptions
for topic in "${TOPICS[@]}"; do
    sub_name="${topic}-sub"
    if gcloud pubsub subscriptions describe $sub_name --project=$PROJECT_ID &>/dev/null 2>&1; then
        print_info "Subscription $sub_name already exists"
    else
        gcloud pubsub subscriptions create $sub_name \
            --topic=$topic \
            --ack-deadline=600 \
            --project=$PROJECT_ID 2>/dev/null || true
        print_success "Created subscription $sub_name"
    fi
done

# ============================================
# Setup Secrets (Optional)
# ============================================
print_info "Setting up Secret Manager..."

# Create sample API key secret (replace with real key)
if gcloud secrets describe api-key --project=$PROJECT_ID &>/dev/null 2>&1; then
    print_info "Secret api-key already exists"
else
    echo "sample-api-key-replace-with-real" | gcloud secrets create api-key \
        --data-file=- \
        --replication-policy="automatic" \
        --project=$PROJECT_ID 2>/dev/null || print_info "Could not create secret"
    print_success "Created secret api-key"
fi

# ============================================
# Create Cloud Scheduler Jobs (Replaces Composer)
# ============================================
print_info "Creating Cloud Scheduler jobs..."

# Check if App Engine is initialized (required for Cloud Scheduler)
if ! gcloud app describe --project=$PROJECT_ID &>/dev/null 2>&1; then
    print_info "Initializing App Engine..."
    gcloud app create --region=$REGION --project=$PROJECT_ID 2>/dev/null || print_info "App Engine may already exist"
    print_success "App Engine initialized"
fi

# Daily ingestion job
if gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION --project=$PROJECT_ID &>/dev/null 2>&1; then
    print_info "Scheduler job daily-sales-ingestion already exists"
else
    gcloud scheduler jobs create pubsub daily-sales-ingestion \
        --location=$REGION \
        --schedule="0 1 * * *" \
        --time-zone="Asia/Jakarta" \
        --topic="data-ingestion-trigger" \
        --message-body='{"trigger":"scheduled"}' \
        --project=$PROJECT_ID 2>/dev/null || print_info "Could not create scheduler job"
    print_success "Created scheduler job daily-sales-ingestion"
fi

# ============================================
# Summary
# ============================================
echo ""
print_success "============================================"
print_success "FREE TIER Setup completed!"
print_success "============================================"
echo ""
print_info "Resources created (FREE TIER):"
echo "  - Cloud Storage: gs://$BUCKET_NAME"
echo "  - BigQuery Dataset: $PROJECT_ID:$DATASET_ID"
echo "  - Pub/Sub Topics: data-ingestion-trigger, etl-pipeline-trigger"
echo "  - Service Account: $CF_SA"
echo "  - Scheduler Jobs: daily-sales-ingestion"
echo ""
print_skip "Skipped (requires billing):"
echo "  - Cloud Composer (Apache Airflow)"
echo "  - Cloud Build"
echo ""
print_info "Alternative for Composer:"
echo "  - Use Cloud Functions + Cloud Scheduler for ETL orchestration"
echo "  - Or run Airflow locally with Docker"
echo ""
print_success "Ready for deployment!"
