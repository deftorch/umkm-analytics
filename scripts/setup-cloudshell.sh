#!/bin/bash

# ============================================
# Setup Script untuk UMKM Analytics Platform
# VERSI CLOUD SHELL - 100% GRATIS (No Billing Required)
# ============================================
# Jalankan di GCP Cloud Shell: https://shell.cloud.google.com
# ============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ $1${NC}"; }
print_skip() { echo -e "${BLUE}⊘ $1${NC}"; }

echo ""
echo "============================================"
echo "  UMKM Analytics - Cloud Shell Setup"
echo "  100% GRATIS (No Billing Required)"
echo "============================================"
echo ""

# ============================================
# Auto-detect Project ID from Cloud Shell
# ============================================
if [ -z "$DEVSHELL_PROJECT_ID" ]; then
    print_info "Not running in Cloud Shell, please set PROJECT_ID manually"
    read -p "Enter your GCP Project ID: " PROJECT_ID
else
    PROJECT_ID="$DEVSHELL_PROJECT_ID"
    print_success "Detected Cloud Shell Project: $PROJECT_ID"
fi

REGION="asia-southeast2"
BUCKET_NAME="${PROJECT_ID}-umkm-data"
DATASET_ID="umkm_analytics"

print_info "Project ID: $PROJECT_ID"
print_info "Region: $REGION"
print_info "Bucket: $BUCKET_NAME"

# ============================================
# Set Project
# ============================================
gcloud config set project $PROJECT_ID
print_success "Project configured"

# ============================================
# Enable FREE APIs Only
# ============================================
print_info "Enabling FREE APIs..."

FREE_APIS=(
    "cloudfunctions.googleapis.com"
    "bigquery.googleapis.com"
    "storage.googleapis.com"
    "pubsub.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
)

for api in "${FREE_APIS[@]}"; do
    print_info "Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID 2>/dev/null && \
        print_success "$api enabled" || \
        print_error "Failed to enable $api"
done

# Skip billing-required APIs
print_skip "SKIP: cloudscheduler.googleapis.com (requires billing) → Use GitHub Actions"
print_skip "SKIP: secretmanager.googleapis.com (requires billing) → Use .env files"
print_skip "SKIP: composer.googleapis.com (requires billing) → Use Cloud Functions"
print_skip "SKIP: cloudbuild.googleapis.com (requires billing) → Use gcloud deploy"

# ============================================
# Create Cloud Storage Bucket
# ============================================
print_info "Creating Cloud Storage bucket..."

if gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
    print_info "Bucket gs://$BUCKET_NAME already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME 2>/dev/null && \
        print_success "Created bucket gs://$BUCKET_NAME" || \
        print_error "Could not create bucket (name may be taken globally)"
fi

# Create folder structure
print_info "Creating folder structure..."
for folder in raw processed archive uploads; do
    echo "" | gsutil cp - gs://$BUCKET_NAME/$folder/.keep 2>/dev/null || true
done
print_success "Folder structure created"

# ============================================
# Create BigQuery Dataset
# ============================================
print_info "Creating BigQuery dataset..."

if bq ls -d --project_id=$PROJECT_ID $DATASET_ID &>/dev/null; then
    print_info "Dataset $DATASET_ID already exists"
else
    bq mk --location=$REGION --dataset \
        --description="UMKM Analytics Dataset" \
        $PROJECT_ID:$DATASET_ID 2>/dev/null && \
        print_success "Created dataset $DATASET_ID" || \
        print_error "Could not create dataset"
fi

# ============================================
# Create BigQuery Tables (Sample Schema)
# ============================================
print_info "Creating BigQuery tables..."

# Raw sales table
bq mk --table \
    --description="Raw sales data from ingestion" \
    --time_partitioning_field=ingestion_date \
    $PROJECT_ID:$DATASET_ID.raw_sales \
    product_id:STRING,product_name:STRING,category:STRING,price:FLOAT,quantity:INTEGER,sale_date:DATE,ingestion_date:DATE \
    2>/dev/null && print_success "Created table: raw_sales" || print_info "Table raw_sales may already exist"

# Daily summary table
bq mk --table \
    --description="Daily sales summary" \
    --time_partitioning_field=summary_date \
    $PROJECT_ID:$DATASET_ID.daily_summary \
    summary_date:DATE,total_sales:FLOAT,total_quantity:INTEGER,avg_price:FLOAT,top_category:STRING \
    2>/dev/null && print_success "Created table: daily_summary" || print_info "Table daily_summary may already exist"

# ============================================
# Create Pub/Sub Topics (for event-driven processing)
# ============================================
print_info "Creating Pub/Sub topics..."

TOPICS=("data-ingestion-trigger" "etl-complete-trigger")

for topic in "${TOPICS[@]}"; do
    gcloud pubsub topics create $topic --project=$PROJECT_ID 2>/dev/null && \
        print_success "Created topic: $topic" || \
        print_info "Topic $topic may already exist"
done

# ============================================
# Create Sample .env file (Alternative to Secret Manager)
# ============================================
print_info "Creating .env template..."

cat > .env.template << 'EOF'
# UMKM Analytics Environment Variables
# Copy this to .env and fill in your values
# DO NOT commit .env to git!

# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=asia-southeast2
GCS_BUCKET=your-bucket-name
BQ_DATASET=umkm_analytics

# API Keys (if needed)
# TOKOPEDIA_API_KEY=your-api-key
# SHOPEE_API_KEY=your-api-key

# Database (if using external DB)
# DB_CONNECTION_STRING=your-connection-string
EOF

print_success "Created .env.template"

# ============================================
# Create GitHub Actions workflow (Alternative to Cloud Scheduler)
# ============================================
print_info "Creating GitHub Actions workflow..."

mkdir -p .github/workflows

cat > .github/workflows/scheduled-ingestion.yml << 'EOF'
# Alternative to Cloud Scheduler (FREE)
# This runs daily at 2 AM UTC (9 AM WIB)

name: Scheduled Data Ingestion

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  ingest:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Run ingestion
        run: python cloud-functions/data-ingestion/main.py
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCS_BUCKET: ${{ secrets.GCS_BUCKET }}
EOF

print_success "Created GitHub Actions workflow"

# ============================================
# Summary
# ============================================
echo ""
echo "============================================"
print_success "SETUP COMPLETE! (100% Free Tier)"
echo "============================================"
echo ""
print_info "Resources Created:"
echo "  ✓ Cloud Storage: gs://$BUCKET_NAME"
echo "  ✓ BigQuery Dataset: $PROJECT_ID:$DATASET_ID"
echo "  ✓ BigQuery Tables: raw_sales, daily_summary"
echo "  ✓ Pub/Sub Topics: data-ingestion-trigger, etl-complete-trigger"
echo ""
print_info "Free Alternatives Used:"
echo "  ⊘ Cloud Scheduler → GitHub Actions (.github/workflows/)"
echo "  ⊘ Secret Manager → .env files (.env.template)"
echo "  ⊘ Cloud Composer → Cloud Functions + Pub/Sub"
echo ""
print_info "Next Steps:"
echo "  1. Copy .env.template to .env and fill values"
echo "  2. Deploy Cloud Functions: gcloud functions deploy ..."
echo "  3. Set up GitHub Secrets for scheduled jobs"
echo "  4. Upload sample data to gs://$BUCKET_NAME/raw/"
echo ""
print_success "Ready to use! 🚀"
