#!/bin/bash

# ============================================
# Setup Script untuk UMKM Analytics Platform
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
    print_error "yq not found. Installing..."
    sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
    sudo chmod +x /usr/local/bin/yq
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
# Enable Required APIs
# ============================================
print_info "Enabling required Google Cloud APIs..."

APIS=(
    "cloudfunctions.googleapis.com"
    "composer.googleapis.com"
    "bigquery.googleapis.com"
    "storage.googleapis.com"
    "cloudscheduler.googleapis.com"
    "pubsub.googleapis.com"
    "secretmanager.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
    "cloudbuild.googleapis.com"
)

for api in "${APIS[@]}"; do
    print_info "Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID
    print_success "$api enabled"
done

# ============================================
# Create Service Accounts
# ============================================
print_info "Creating service accounts..."

# Cloud Function Service Account
CF_SA="cloud-function-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $CF_SA &>/dev/null; then
    print_info "Service account $CF_SA already exists"
else
    gcloud iam service-accounts create cloud-function-sa \
        --display-name="Cloud Function Service Account" \
        --project=$PROJECT_ID
    print_success "Created $CF_SA"
fi

# Grant roles to Cloud Function SA
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/storage.objectCreator"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CF_SA" \
    --role="roles/pubsub.publisher"

print_success "Granted roles to Cloud Function SA"

# Composer Service Account
COMPOSER_SA="composer-sa@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $COMPOSER_SA &>/dev/null; then
    print_info "Service account $COMPOSER_SA already exists"
else
    gcloud iam service-accounts create composer-sa \
        --display-name="Composer Service Account" \
        --project=$PROJECT_ID
    print_success "Created $COMPOSER_SA"
fi

# Grant roles to Composer SA
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPOSER_SA" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$COMPOSER_SA" \
    --role="roles/storage.objectAdmin"

print_success "Granted roles to Composer SA"

# ============================================
# Create Cloud Storage Bucket
# ============================================
print_info "Creating Cloud Storage bucket..."

if gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
    print_info "Bucket gs://$BUCKET_NAME already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    print_success "Created bucket gs://$BUCKET_NAME"
fi

# Create folder structure
gsutil ls gs://$BUCKET_NAME/raw/ &>/dev/null || gsutil -m cp /dev/null gs://$BUCKET_NAME/raw/.keep
gsutil ls gs://$BUCKET_NAME/processed/ &>/dev/null || gsutil -m cp /dev/null gs://$BUCKET_NAME/processed/.keep
gsutil ls gs://$BUCKET_NAME/archive/ &>/dev/null || gsutil -m cp /dev/null gs://$BUCKET_NAME/archive/.keep

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

gsutil lifecycle set /tmp/lifecycle.json gs://$BUCKET_NAME
print_success "Lifecycle policy set"

# ============================================
# Create BigQuery Dataset
# ============================================
print_info "Creating BigQuery dataset..."

if bq ls -d --project_id=$PROJECT_ID $DATASET_ID &>/dev/null; then
    print_info "Dataset $DATASET_ID already exists"
else
    bq mk --location=$REGION --dataset \
        --description="Dataset for UMKM Analytics" \
        $PROJECT_ID:$DATASET_ID
    print_success "Created dataset $DATASET_ID"
fi

# ============================================
# Create Pub/Sub Topics
# ============================================
print_info "Creating Pub/Sub topics..."

TOPICS=("data-ingestion-trigger" "etl-pipeline-trigger")

for topic in "${TOPICS[@]}"; do
    if gcloud pubsub topics describe $topic &>/dev/null; then
        print_info "Topic $topic already exists"
    else
        gcloud pubsub topics create $topic --project=$PROJECT_ID
        print_success "Created topic $topic"
    fi
done

# Create subscriptions
for topic in "${TOPICS[@]}"; do
    sub_name="${topic}-sub"
    if gcloud pubsub subscriptions describe $sub_name &>/dev/null; then
        print_info "Subscription $sub_name already exists"
    else
        gcloud pubsub subscriptions create $sub_name \
            --topic=$topic \
            --ack-deadline=600 \
            --project=$PROJECT_ID
        print_success "Created subscription $sub_name"
    fi
done

# ============================================
# Setup Secrets
# ============================================
print_info "Setting up Secret Manager..."

# Create sample API key secret (replace with real key)
if gcloud secrets describe api-key &>/dev/null; then
    print_info "Secret api-key already exists"
else
    echo "sample-api-key-replace-with-real" | gcloud secrets create api-key \
        --data-file=- \
        --replication-policy="automatic" \
        --project=$PROJECT_ID
    print_success "Created secret api-key"
fi

# Grant access to service account
gcloud secrets add-iam-policy-binding api-key \
    --member="serviceAccount:$CF_SA" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# ============================================
# Create Cloud Scheduler Jobs
# ============================================
print_info "Creating Cloud Scheduler jobs..."

# Check if App Engine is initialized (required for Cloud Scheduler)
if ! gcloud app describe &>/dev/null; then
    print_info "Initializing App Engine..."
    gcloud app create --region=$REGION --project=$PROJECT_ID
    print_success "App Engine initialized"
fi

# Daily ingestion job
if gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION &>/dev/null; then
    print_info "Scheduler job daily-sales-ingestion already exists"
else
    gcloud scheduler jobs create pubsub daily-sales-ingestion \
        --location=$REGION \
        --schedule="0 1 * * *" \
        --time-zone="Asia/Jakarta" \
        --topic="data-ingestion-trigger" \
        --message-body='{"trigger":"scheduled"}' \
        --project=$PROJECT_ID
    print_success "Created scheduler job daily-sales-ingestion"
fi

# ============================================
# Setup Monitoring
# ============================================
print_info "Setting up monitoring..."

# Create notification channel
cat > /tmp/notification-channel.json <<EOF
{
  "type": "email",
  "displayName": "Admin Email",
  "labels": {
    "email_address": "admin@example.com"
  }
}
EOF

# Note: You need to manually create notification channels via Console
print_info "Create notification channels manually in Cloud Console"

# Create alert policy for function errors
cat > /tmp/alert-policy.json <<EOF
{
  "displayName": "High Cloud Function Error Rate",
  "conditions": [{
    "displayName": "Cloud Function errors > 3",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_function\" AND severity=\"ERROR\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": 3,
      "duration": "300s"
    }
  }],
  "combiner": "OR"
}
EOF

print_info "Alert policies can be created via Console"

# ============================================
# Setup Budget Alerts
# ============================================
print_info "Setting up budget alerts..."

# Note: Budget alerts need billing account ID
print_info "Set up budget alerts manually in Cloud Console -> Billing"

# ============================================
# Summary
# ============================================
echo ""
print_success "============================================"
print_success "Setup completed successfully!"
print_success "============================================"
echo ""
print_info "Next steps:"
echo "  1. Update secrets in Secret Manager with real API keys"
echo "  2. Set up notification channels in Cloud Monitoring"
echo "  3. Create budget alerts in Cloud Billing"
echo "  4. Run deployment script: ./scripts/deploy.sh"
echo "  5. Verify deployment: ./scripts/verify.sh"
echo ""
print_info "Resources created:"
echo "  - Cloud Storage: gs://$BUCKET_NAME"
echo "  - BigQuery Dataset: $PROJECT_ID:$DATASET_ID"
echo "  - Pub/Sub Topics: data-ingestion-trigger, etl-pipeline-trigger"
echo "  - Service Accounts: $CF_SA, $COMPOSER_SA"
echo "  - Scheduler Jobs: daily-sales-ingestion"
echo ""
print_success "Ready for deployment!"