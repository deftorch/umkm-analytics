#!/bin/bash

# Teardown script to remove all resources created by setup.sh
# WARNING: This will delete all data in the created buckets and datasets!

# source config/config.yaml
# NOTE: config.yaml is YAML, not shell script. We should use yq to parse it.
PROJECT_ID=$(yq eval ".gcp.project_id" config/config.yaml)
REGION=$(yq eval ".gcp.region" config/config.yaml)
BUCKET_NAME=$(yq eval ".storage.bucket_name" config/config.yaml)
DATASET_ID=$(yq eval ".bigquery.dataset_id" config/config.yaml)
ETL_TRIGGER_TOPIC="etl-pipeline-trigger"
ETL_TRIGGER_SUBSCRIPTION="etl-pipeline-trigger-sub"

echo "WARNING: You are about to delete all resources for project $GCP_PROJECT."
echo "This includes BigQuery datasets, Cloud Storage buckets, and Pub/Sub topics."
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Teardown aborted."
    exit 1
fi

echo "Deleting Cloud Functions..."
gcloud functions delete data-ingestion --region=$REGION --quiet
gcloud functions delete data-validation --region=$REGION --quiet

echo "Deleting Pub/Sub topics and subscriptions..."
gcloud pubsub topics delete $ETL_TRIGGER_TOPIC --quiet
gcloud pubsub subscriptions delete $ETL_TRIGGER_SUBSCRIPTION --quiet

echo "Deleting BigQuery datasets..."
bq rm -r -f -d $PROJECT_ID:$DATASET_ID

echo "Deleting Cloud Storage buckets..."
gsutil -m rm -r gs://$BUCKET_NAME

echo "Teardown complete."
