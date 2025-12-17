"""
Apache Airflow DAG for Data Quality Checks
Runs checks on BigQuery tables
"""

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCheckOperator
)
from datetime import datetime, timedelta

# Configuration
PROJECT_ID = 'your-project-id'
DATASET_ID = 'umkm_analytics'

default_args = {
    'owner': 'data-team',
    'start_date': datetime(2025, 1, 1),
    'retries': 1
}

dag = DAG(
    'data_quality_checks',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False
)

with dag:
    # Check for negative prices
    check_negative_prices = BigQueryCheckOperator(
        task_id='check_negative_prices',
        sql=f"""
        SELECT COUNT(*)
        FROM `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
        WHERE price < 0
        """,
        use_legacy_sql=False,
        expect_value=0
    )

    # Check for null product IDs
    check_null_product_ids = BigQueryCheckOperator(
        task_id='check_null_product_ids',
        sql=f"""
        SELECT COUNT(*)
        FROM `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
        WHERE product_id IS NULL
        """,
        use_legacy_sql=False,
        expect_value=0
    )

    check_negative_prices >> check_null_product_ids
