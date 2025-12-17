#!/bin/bash

# Backup script to export BigQuery data and copy GCS data to a backup bucket

# source config/config.yaml
# NOTE: config.yaml is YAML, not shell script. We should use yq to parse it.
PROJECT_ID=$(yq eval ".gcp.project_id" config/config.yaml)
REGION=$(yq eval ".gcp.region" config/config.yaml)
BUCKET_NAME=$(yq eval ".storage.bucket_name" config/config.yaml)
DATASET_ID=$(yq eval ".bigquery.dataset_id" config/config.yaml)

BACKUP_BUCKET="${BUCKET_NAME}-backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Creating backup bucket if not exists..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$BACKUP_BUCKET || true

echo "Backing up BigQuery data..."
# Export tables to GCS
tables=("raw_sales_data" "cleaned_sales_data" "daily_summary" "product_performance")

for table in "${tables[@]}"
do
    echo "Exporting $table..."
    bq extract \
    --destination_format NEWLINE_DELIMITED_JSON \
    "$PROJECT_ID:$DATASET_ID.$table" \
    "gs://$BACKUP_BUCKET/bigquery/$TIMESTAMP/$table/*.json"
done

echo "Backing up Cloud Storage data..."
gsutil -m cp -r "gs://$BUCKET_NAME/*" "gs://$BACKUP_BUCKET/storage/$TIMESTAMP/"

echo "Backup complete. Data saved to gs://$BACKUP_BUCKET/$TIMESTAMP/"
