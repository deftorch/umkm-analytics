# Infrastructure Architecture

## Overview
The UMKM Analytics Platform is designed to be a scalable, serverless data platform on Google Cloud Platform.

## Components

### 1. Data Ingestion
- **Cloud Functions**: Python-based serverless functions for ingesting data from APIs or generating sample data.
- **Pub/Sub**: Decouples ingestion from processing.
- **Cloud Scheduler**: Triggers ingestion periodically.

### 2. Data Storage
- **Cloud Storage (GCS)**: Stores raw JSON files in a data lake structure.
- **BigQuery**: Enterprise data warehouse for structured data and analytics.

### 3. Data Processing (ETL)
- **Cloud Composer (Airflow)**: Orchestrates the ETL pipeline.
  - Validates raw data.
  - Loads data into BigQuery.
  - Transforms and cleans data using SQL.
  - Aggregates data for reporting.

### 4. Machine Learning
- **BigQuery ML**: Runs ML models directly inside the data warehouse.
  - `sales_prediction`: Forecasts future sales.
  - `price_anomaly`: Detects pricing irregularities.
  - `product_clustering`: Segments products for marketing.

### 5. Visualization
- **Looker Studio**: Connects to BigQuery for interactive dashboards.

## Data Flow
1. `data-ingestion` function fetches data -> Saves to GCS -> Publishes to Pub/Sub.
2. Pub/Sub or Schedule triggers Airflow DAG.
3. Airflow loads GCS data to BigQuery `raw_sales_data`.
4. SQL transformations clean data into `cleaned_sales_data`.
5. Aggregations created in `daily_summary` and `product_performance`.
6. ML models are retrained weekly on `cleaned_sales_data`.
7. Predictions are stored in `sales_predictions`.
8. Dashboards read from analytical tables.
