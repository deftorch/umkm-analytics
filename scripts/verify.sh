#!/bin/bash

# ============================================
# Verification Script - Check Deployment Status
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}ℹ $1${NC}"; }
print_header() { echo -e "${BLUE}━━━ $1 ━━━${NC}"; }

# Load config
PROJECT_ID=$(yq eval '.gcp.project_id' config/config.yaml)
REGION=$(yq eval '.gcp.region' config/config.yaml)
BUCKET_NAME=$(yq eval '.storage.bucket_name' config/config.yaml)
DATASET_ID=$(yq eval '.bigquery.dataset_id' config/config.yaml)

echo ""
print_header "UMKM Analytics Platform - Deployment Verification"
echo ""

TOTAL_CHECKS=0
PASSED_CHECKS=0

# ============================================
# 1. Cloud Storage
# ============================================
print_header "Cloud Storage"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
    print_success "Bucket gs://$BUCKET_NAME exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # Check folders
    for folder in raw processed archive; do
        if gsutil ls gs://$BUCKET_NAME/$folder/ &>/dev/null; then
            echo "  ✓ Folder $folder/ exists"
        fi
    done
    
    # Check for data files
    FILE_COUNT=$(gsutil ls gs://$BUCKET_NAME/raw/*.json 2>/dev/null | wc -l)
    echo "  ℹ Found $FILE_COUNT data files in raw/"
else
    print_error "Bucket gs://$BUCKET_NAME not found"
fi
echo ""

# ============================================
# 2. BigQuery Dataset
# ============================================
print_header "BigQuery"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if bq ls --project_id=$PROJECT_ID $DATASET_ID &>/dev/null; then
    print_success "Dataset $DATASET_ID exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    # Check tables
    TABLES=$(bq ls --project_id=$PROJECT_ID $DATASET_ID | grep TABLE | awk '{print $1}')
    TABLE_COUNT=$(echo "$TABLES" | wc -l)
    echo "  ℹ Found $TABLE_COUNT tables"
    
    # Check for data in tables
    for table in raw_sales_data cleaned_sales_data daily_summary; do
        ROW_COUNT=$(bq query --use_legacy_sql=false --format=csv --project_id=$PROJECT_ID \
            "SELECT COUNT(*) as count FROM \`${PROJECT_ID}.${DATASET_ID}.${table}\`" 2>/dev/null | tail -n 1)
        if [ ! -z "$ROW_COUNT" ]; then
            echo "  ✓ Table $table has $ROW_COUNT rows"
        fi
    done
else
    print_error "Dataset $DATASET_ID not found"
fi
echo ""

# ============================================
# 3. Cloud Functions
# ============================================
print_header "Cloud Functions"
TOTAL_CHECKS=$((TOTAL_CHECKS + 2))

# Check data ingestion function
if gcloud functions describe ingest-data --region=$REGION --gen2 &>/dev/null; then
    print_success "Function ingest-data exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    STATUS=$(gcloud functions describe ingest-data --region=$REGION --gen2 --format='value(state)')
    echo "  ℹ Status: $STATUS"
else
    print_error "Function ingest-data not found"
fi

# Check HTTP function
if gcloud functions describe ingest-data-http --region=$REGION --gen2 &>/dev/null; then
    print_success "Function ingest-data-http exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    HTTP_URL=$(gcloud functions describe ingest-data-http --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo "  ℹ URL: $HTTP_URL"
    
    # Test HTTP endpoint
    print_info "Testing HTTP endpoint..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $HTTP_URL)
    if [ "$HTTP_CODE" == "200" ]; then
        echo "  ✓ HTTP endpoint responding (200 OK)"
    else
        echo "  ⚠ HTTP endpoint returned code: $HTTP_CODE"
    fi
else
    print_error "Function ingest-data-http not found"
fi
echo ""

# ============================================
# 4. Pub/Sub
# ============================================
print_header "Pub/Sub"
TOTAL_CHECKS=$((TOTAL_CHECKS + 2))

for topic in data-ingestion-trigger etl-pipeline-trigger; do
    if gcloud pubsub topics describe $topic &>/dev/null; then
        print_success "Topic $topic exists"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        
        # Check subscriptions
        SUB_COUNT=$(gcloud pubsub subscriptions list --filter="topic:$topic" --format="value(name)" | wc -l)
        echo "  ℹ Subscriptions: $SUB_COUNT"
    else
        print_error "Topic $topic not found"
    fi
done
echo ""

# ============================================
# 5. Cloud Scheduler
# ============================================
print_header "Cloud Scheduler"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION &>/dev/null; then
    print_success "Scheduler job daily-sales-ingestion exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    STATE=$(gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION --format='value(state)')
    SCHEDULE=$(gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION --format='value(schedule)')
    echo "  ℹ State: $STATE"
    echo "  ℹ Schedule: $SCHEDULE"
    
    # Get last run
    LAST_RUN=$(gcloud scheduler jobs describe daily-sales-ingestion --location=$REGION --format='value(lastAttemptTime)')
    if [ ! -z "$LAST_RUN" ]; then
        echo "  ℹ Last run: $LAST_RUN"
    fi
else
    print_error "Scheduler job not found"
fi
echo ""

# ============================================
# 6. Cloud Composer
# ============================================
print_header "Cloud Composer"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

COMPOSER_ENV=$(yq eval '.composer.environment_name' config/config.yaml)
if gcloud composer environments describe $COMPOSER_ENV --location=$REGION &>/dev/null; then
    print_success "Composer environment $COMPOSER_ENV exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    STATE=$(gcloud composer environments describe $COMPOSER_ENV --location=$REGION --format='value(state)')
    echo "  ℹ State: $STATE"
    
    # Get Airflow web UI
    AIRFLOW_URI=$(gcloud composer environments describe $COMPOSER_ENV --location=$REGION --format='value(config.airflowUri)')
    if [ ! -z "$AIRFLOW_URI" ]; then
        echo "  ℹ Airflow UI: $AIRFLOW_URI"
    fi
    
    # Check DAGs
    print_info "Checking DAGs..."
    DAG_COUNT=$(gcloud composer environments storage dags list --environment=$COMPOSER_ENV --location=$REGION 2>/dev/null | wc -l)
    echo "  ℹ DAGs uploaded: $DAG_COUNT"
else
    print_error "Composer environment not found"
fi
echo ""

# ============================================
# 7. Service Accounts
# ============================================
print_header "Service Accounts"
TOTAL_CHECKS=$((TOTAL_CHECKS + 2))

for sa in cloud-function-sa composer-sa; do
    SA_EMAIL="${sa}@${PROJECT_ID}.iam.gserviceaccount.com"
    if gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
        print_success "Service account $sa exists"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        print_error "Service account $sa not found"
    fi
done
echo ""

# ============================================
# 8. Secret Manager
# ============================================
print_header "Secret Manager"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if gcloud secrets describe api-key &>/dev/null; then
    print_success "Secret api-key exists"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    
    VERSIONS=$(gcloud secrets versions list api-key --format="value(name)" | wc -l)
    echo "  ℹ Versions: $VERSIONS"
else
    print_error "Secret api-key not found"
fi
echo ""

# ============================================
# 9. Data Pipeline Health
# ============================================
print_header "Data Pipeline Health"

# Check recent ingestions
print_info "Checking recent data ingestions..."
RECENT_FILES=$(gsutil ls -l gs://$BUCKET_NAME/raw/ 2>/dev/null | grep ".json" | tail -5)
if [ ! -z "$RECENT_FILES" ]; then
    echo "  ✓ Recent ingestion files found"
    echo "$RECENT_FILES" | awk '{print "    " $3 " - " $1}'
else
    echo "  ⚠ No recent ingestion files"
fi

# Check BigQuery latest data
print_info "Checking latest data in BigQuery..."
LATEST_DATE=$(bq query --use_legacy_sql=false --format=csv --project_id=$PROJECT_ID \
    "SELECT MAX(sale_date) as latest FROM \`${PROJECT_ID}.${DATASET_ID}.cleaned_sales_data\`" 2>/dev/null | tail -n 1)
if [ ! -z "$LATEST_DATE" ] && [ "$LATEST_DATE" != "null" ]; then
    echo "  ✓ Latest data: $LATEST_DATE"
else
    echo "  ⚠ No data in cleaned_sales_data table"
fi
echo ""

# ============================================
# 10. Test Query
# ============================================
print_header "Test Queries"

print_info "Running test query..."
bq query --use_legacy_sql=false --format=prettyjson --project_id=$PROJECT_ID \
    "SELECT category, COUNT(*) as count FROM \`${PROJECT_ID}.${DATASET_ID}.cleaned_sales_data\` GROUP BY category ORDER BY count DESC LIMIT 5" 2>/dev/null | head -20

echo ""

# ============================================
# Summary
# ============================================
print_header "Verification Summary"
echo ""

PERCENTAGE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

if [ $PERCENTAGE -eq 100 ]; then
    print_success "All checks passed! ($PASSED_CHECKS/$TOTAL_CHECKS)"
    echo ""
    print_success "🎉 System is fully operational!"
elif [ $PERCENTAGE -ge 80 ]; then
    print_info "Most checks passed ($PASSED_CHECKS/$TOTAL_CHECKS - ${PERCENTAGE}%)"
    echo ""
    print_info "⚠️  System is mostly operational with minor issues"
else
    print_error "Several checks failed ($PASSED_CHECKS/$TOTAL_CHECKS - ${PERCENTAGE}%)"
    echo ""
    print_error "❌ System requires attention"
fi

echo ""
print_info "Quick Links:"
echo "  Cloud Console: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID"
echo "  BigQuery: https://console.cloud.google.com/bigquery?project=$PROJECT_ID"
echo "  Cloud Functions: https://console.cloud.google.com/functions/list?project=$PROJECT_ID"
echo "  Composer: https://console.cloud.google.com/composer/environments?project=$PROJECT_ID"
echo "  Monitoring: https://console.cloud.google.com/monitoring?project=$PROJECT_ID"
echo ""

print_info "Next Steps:"
if [ $PERCENTAGE -lt 100 ]; then
    echo "  1. Review failed checks above"
    echo "  2. Check deployment logs: gcloud logging read --limit 50"
    echo "  3. Re-run deployment if needed: ./scripts/deploy.sh"
fi
echo "  • Monitor pipeline: gcloud logging tail 'resource.type=cloud_function'"
echo "  • View data: bq query --use_legacy_sql=false 'SELECT * FROM \`${PROJECT_ID}.${DATASET_ID}.daily_summary\` LIMIT 10'"
echo "  • Setup Looker Studio dashboard"
echo ""