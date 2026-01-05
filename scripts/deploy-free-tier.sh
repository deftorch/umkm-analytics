#!/bin/bash

# ============================================
# Deploy Script untuk UMKM Analytics Platform
# VERSI FREE TIER - Tanpa Composer/Secret Manager
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ $1${NC}"; }
print_step() { echo -e "${BLUE}▶ $1${NC}"; }

echo ""
echo "============================================"
echo "  UMKM Analytics - Free Tier Deployment"
echo "============================================"
echo ""

# ============================================
# Load Configuration
# ============================================
if [ -f "config/config.yaml" ]; then
    PROJECT_ID=$(grep -A1 "^gcp:" config/config.yaml | grep "project_id" | cut -d'"' -f2)
    REGION=$(grep -A2 "^gcp:" config/config.yaml | grep "region" | cut -d'"' -f2)
else
    PROJECT_ID="${DEVSHELL_PROJECT_ID:-}"
    REGION="asia-southeast2"
fi

if [ -z "$PROJECT_ID" ]; then
    read -p "Enter GCP Project ID: " PROJECT_ID
fi

BUCKET_NAME="${PROJECT_ID}-umkm-data"
DATASET_ID="umkm_analytics"

print_info "Project ID: $PROJECT_ID"
print_info "Region: $REGION"

# Set project
gcloud config set project $PROJECT_ID

# ============================================
# Step 1: Deploy Data Ingestion Function
# ============================================
print_step "Step 1: Deploying Data Ingestion Cloud Function..."

cd cloud-functions/data-ingestion

# Check if function exists
if gcloud functions describe ingest-sales-data --gen2 --region=$REGION &>/dev/null; then
    print_info "Updating existing function..."
    DEPLOY_CMD="gcloud functions deploy ingest-sales-data"
else
    print_info "Creating new function..."
    DEPLOY_CMD="gcloud functions deploy ingest-sales-data"
fi

$DEPLOY_CMD \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=ingest_data \
    --trigger-topic=data-ingestion-trigger \
    --memory=256MB \
    --timeout=540s \
    --set-env-vars="GCP_PROJECT=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME,USE_SAMPLE_DATA=true" \
    --quiet

print_success "Data Ingestion function deployed"

cd ../..

# ============================================
# Step 2: Deploy ETL Pipeline Function
# ============================================
print_step "Step 2: Deploying ETL Pipeline Cloud Function..."

cd cloud-functions/etl-pipeline

gcloud functions deploy etl-pipeline \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=etl_pipeline \
    --trigger-topic=etl-pipeline-trigger \
    --memory=512MB \
    --timeout=540s \
    --set-env-vars="GCP_PROJECT=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME,DATASET_ID=$DATASET_ID" \
    --quiet

print_success "ETL Pipeline function deployed"

cd ../..

# ============================================
# Step 3: Deploy Data Validation Function
# ============================================
print_step "Step 3: Deploying Data Validation Cloud Function..."

if [ -d "cloud-functions/data-validation" ]; then
    cd cloud-functions/data-validation
    
    gcloud functions deploy validate-sales-data \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=. \
        --entry-point=validate_data \
        --trigger-http \
        --allow-unauthenticated \
        --memory=256MB \
        --timeout=300s \
        --set-env-vars="GCP_PROJECT=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME" \
        --quiet
    
    print_success "Data Validation function deployed"
    cd ../..
else
    print_info "Data validation function not found, skipping..."
fi

# ============================================
# Step 4: Deploy HTTP Trigger for Manual Testing
# ============================================
print_step "Step 4: Deploying HTTP trigger for manual ingestion..."

cd cloud-functions/data-ingestion

gcloud functions deploy ingest-sales-http \
    --gen2 \
    --runtime=python311 \
    --region=$REGION \
    --source=. \
    --entry-point=ingest_data_http \
    --trigger-http \
    --allow-unauthenticated \
    --memory=256MB \
    --timeout=540s \
    --set-env-vars="GCP_PROJECT=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME,USE_SAMPLE_DATA=true" \
    --quiet

print_success "HTTP trigger deployed"

cd ../..

# ============================================
# Step 5: Create BigQuery Tables (if not exist)
# ============================================
print_step "Step 5: Ensuring BigQuery tables exist..."

# Raw sales table
bq mk --table \
    --description="Raw sales data" \
    --time_partitioning_field=ingestion_date \
    $PROJECT_ID:$DATASET_ID.raw_sales \
    product_id:STRING,product_name:STRING,category:STRING,price:FLOAT,original_price:FLOAT,discount_percent:INTEGER,sales_count:INTEGER,rating:FLOAT,review_count:INTEGER,stock:INTEGER,seller_name:STRING,seller_location:STRING,ingestion_date:DATE,sale_date:DATE,revenue:FLOAT \
    2>/dev/null || print_info "Table raw_sales already exists"

# Daily summary table
bq mk --table \
    --description="Daily sales summary" \
    --time_partitioning_field=summary_date \
    $PROJECT_ID:$DATASET_ID.daily_summary \
    summary_date:DATE,total_sales:FLOAT,total_quantity:INTEGER,avg_price:FLOAT,top_category:STRING \
    2>/dev/null || print_info "Table daily_summary already exists"

print_success "BigQuery tables ready"

# ============================================
# Summary
# ============================================
echo ""
echo "============================================"
print_success "DEPLOYMENT COMPLETE! (Free Tier)"
echo "============================================"
echo ""
print_info "Deployed Cloud Functions:"
echo "  ✓ ingest-sales-data (Pub/Sub trigger)"
echo "  ✓ etl-pipeline (Pub/Sub trigger)"
echo "  ✓ ingest-sales-http (HTTP trigger for testing)"
echo ""
print_info "BigQuery Tables:"
echo "  ✓ $DATASET_ID.raw_sales"
echo "  ✓ $DATASET_ID.daily_summary"
echo ""
print_info "Test Commands:"
echo ""
echo "  # Trigger ingestion manually via HTTP"
echo "  curl \$(gcloud functions describe ingest-sales-http --region=$REGION --format='value(url)')"
echo ""
echo "  # Trigger via Pub/Sub"
echo "  gcloud pubsub topics publish data-ingestion-trigger --message='{\"trigger\":\"manual\"}'"
echo ""
echo "  # Check BigQuery data"
echo "  bq query --use_legacy_sql=false 'SELECT * FROM \`$PROJECT_ID.$DATASET_ID.raw_sales\` LIMIT 10'"
echo ""
print_success "Ready to use! 🚀"
