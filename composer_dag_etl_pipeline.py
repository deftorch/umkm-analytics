"""
Apache Airflow DAG untuk ETL Pipeline
Orchestrates data transformation dari raw ke cleaned data di BigQuery
"""

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateEmptyTableOperator,
    BigQueryInsertJobOperator,
    BigQueryCheckOperator
)
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import (
    GCSToBigQueryOperator
)
from airflow.providers.google.cloud.operators.gcs import (
    GCSListObjectsOperator,
    GCSDeleteObjectsOperator
)
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import logging

# Configuration
PROJECT_ID = 'your-project-id'
DATASET_ID = 'umkm_analytics'
BUCKET_NAME = 'umkm-data-lake'
RAW_FOLDER = 'raw'
PROCESSED_FOLDER = 'processed'

# Default arguments
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email': ['admin@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1)
}

# Create DAG
dag = DAG(
    'etl_sales_pipeline',
    default_args=default_args,
    description='ETL pipeline for UMKM sales data',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'sales', 'umkm']
)


# Python functions
def check_new_files(**context):
    """Check if there are new files to process"""
    from google.cloud import storage
    
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blobs = list(bucket.list_blobs(prefix=f"{RAW_FOLDER}/"))
    
    # Filter files from last 24 hours
    new_files = [
        blob.name for blob in blobs 
        if blob.time_created.date() >= datetime.now().date()
    ]
    
    logging.info(f"Found {len(new_files)} new files to process")
    
    if not new_files:
        logging.warning("No new files found, skipping pipeline")
        return False
    
    context['task_instance'].xcom_push(key='file_count', value=len(new_files))
    return True


def validate_raw_data(**context):
    """Validate data quality in raw table"""
    from google.cloud import bigquery
    
    client = bigquery.Client()
    
    # Check for duplicates
    query = f"""
    SELECT COUNT(*) as duplicate_count
    FROM (
        SELECT product_id, timestamp, COUNT(*) as cnt
        FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales_data`
        WHERE DATE(ingestion_date) = CURRENT_DATE()
        GROUP BY product_id, timestamp
        HAVING cnt > 1
    )
    """
    
    result = list(client.query(query).result())[0]
    duplicate_count = result.duplicate_count
    
    if duplicate_count > 0:
        logging.warning(f"Found {duplicate_count} duplicate records")
    
    # Check for null values in critical fields
    query = f"""
    SELECT 
        COUNTIF(product_id IS NULL) as null_product_id,
        COUNTIF(price IS NULL) as null_price,
        COUNTIF(category IS NULL) as null_category
    FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales_data`
    WHERE DATE(ingestion_date) = CURRENT_DATE()
    """
    
    result = list(client.query(query).result())[0]
    
    total_nulls = result.null_product_id + result.null_price + result.null_category
    
    if total_nulls > 0:
        logging.warning(f"Found {total_nulls} null values in critical fields")
    
    context['task_instance'].xcom_push(key='data_quality', value={
        'duplicates': duplicate_count,
        'nulls': total_nulls
    })
    
    return True


def generate_summary_stats(**context):
    """Generate summary statistics"""
    from google.cloud import bigquery
    
    client = bigquery.Client()
    
    query = f"""
    SELECT 
        COUNT(DISTINCT product_id) as unique_products,
        COUNT(*) as total_records,
        AVG(price) as avg_price,
        SUM(sales_count) as total_sales
    FROM `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
    WHERE DATE(sale_date) = CURRENT_DATE()
    """
    
    result = list(client.query(query).result())[0]
    
    stats = {
        'unique_products': result.unique_products,
        'total_records': result.total_records,
        'avg_price': float(result.avg_price),
        'total_sales': result.total_sales
    }
    
    logging.info(f"Summary stats: {stats}")
    context['task_instance'].xcom_push(key='summary_stats', value=stats)
    
    return stats


# Task 1: Check for new files
with dag:
    check_files = PythonOperator(
        task_id='check_new_files',
        python_callable=check_new_files,
        provide_context=True
    )
    
    # Task 2: Create raw table if not exists
    create_raw_table = BigQueryCreateEmptyTableOperator(
        task_id='create_raw_table',
        dataset_id=DATASET_ID,
        table_id='raw_sales_data',
        schema_fields=[
            {'name': 'product_id', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'product_name', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'category', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'price', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
            {'name': 'original_price', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
            {'name': 'discount_percent', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
            {'name': 'sales_count', 'type': 'INT64', 'mode': 'NULLABLE'},
            {'name': 'rating', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
            {'name': 'review_count', 'type': 'INT64', 'mode': 'NULLABLE'},
            {'name': 'stock', 'type': 'INT64', 'mode': 'NULLABLE'},
            {'name': 'seller_name', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'seller_location', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
            {'name': 'ingestion_date', 'type': 'DATE', 'mode': 'REQUIRED'}
        ],
        time_partitioning={
            'type': 'DAY',
            'field': 'ingestion_date'
        },
        cluster_fields=['category', 'product_id'],
        exists_ok=True
    )
    
    # Task 3: Load data from GCS to BigQuery
    load_raw_data = GCSToBigQueryOperator(
        task_id='load_raw_data',
        bucket=BUCKET_NAME,
        source_objects=[f'{RAW_FOLDER}/*.json'],
        source_format='NEWLINE_DELIMITED_JSON',
        destination_project_dataset_table=f'{PROJECT_ID}.{DATASET_ID}.raw_sales_data',
        write_disposition='WRITE_APPEND',
        create_disposition='CREATE_IF_NEEDED',
        autodetect=False,
        max_bad_records=10,
        schema_update_options=['ALLOW_FIELD_ADDITION']
    )
    
    # Task 4: Validate raw data
    validate_data = PythonOperator(
        task_id='validate_raw_data',
        python_callable=validate_raw_data,
        provide_context=True
    )
    
    # Task Group: Data Transformation
    with TaskGroup('data_transformation') as transform_group:
        
        # Create cleaned table
        create_cleaned_table = BigQueryCreateEmptyTableOperator(
            task_id='create_cleaned_table',
            dataset_id=DATASET_ID,
            table_id='cleaned_sales_data',
            schema_fields=[
                {'name': 'product_id', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'product_name', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'category', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'price', 'type': 'FLOAT64', 'mode': 'REQUIRED'},
                {'name': 'discount_price', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
                {'name': 'discount_percent', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
                {'name': 'sales_count', 'type': 'INT64', 'mode': 'REQUIRED'},
                {'name': 'rating', 'type': 'FLOAT64', 'mode': 'NULLABLE'},
                {'name': 'review_count', 'type': 'INT64', 'mode': 'NULLABLE'},
                {'name': 'stock_status', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'seller_name', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'seller_location', 'type': 'STRING', 'mode': 'NULLABLE'},
                {'name': 'sale_date', 'type': 'DATE', 'mode': 'REQUIRED'},
                {'name': 'sale_timestamp', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'}
            ],
            time_partitioning={
                'type': 'DAY',
                'field': 'sale_date'
            },
            cluster_fields=['category', 'product_id'],
            exists_ok=True
        )
        
        # Transform and clean data
        transform_data = BigQueryInsertJobOperator(
            task_id='transform_data',
            configuration={
                'query': {
                    'query': f"""
                        INSERT INTO `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
                        SELECT DISTINCT
                            product_id,
                            TRIM(product_name) as product_name,
                            UPPER(TRIM(category)) as category,
                            price,
                            ROUND(price * (1 - COALESCE(discount_percent, 0) / 100), 2) as discount_price,
                            discount_percent,
                            COALESCE(sales_count, 0) as sales_count,
                            rating,
                            COALESCE(review_count, 0) as review_count,
                            CASE 
                                WHEN stock = 0 THEN 'OUT_OF_STOCK'
                                WHEN stock < 10 THEN 'LOW_STOCK'
                                ELSE 'IN_STOCK'
                            END as stock_status,
                            seller_name,
                            seller_location,
                            DATE(timestamp) as sale_date,
                            timestamp as sale_timestamp
                        FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales_data`
                        WHERE DATE(ingestion_date) = CURRENT_DATE()
                            AND price > 0
                            AND product_id IS NOT NULL
                    """,
                    'useLegacySql': False,
                    'writeDisposition': 'WRITE_APPEND'
                }
            }
        )
        
        create_cleaned_table >> transform_data
    
    # Task Group: Analytics Tables
    with TaskGroup('create_analytics_tables') as analytics_group:
        
        # Daily summary
        create_daily_summary = BigQueryInsertJobOperator(
            task_id='create_daily_summary',
            configuration={
                'query': {
                    'query': f"""
                        CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.daily_summary`
                        PARTITION BY summary_date AS
                        SELECT 
                            sale_date as summary_date,
                            category,
                            COUNT(DISTINCT product_id) as unique_products,
                            COUNT(*) as total_records,
                            SUM(sales_count) as total_sales,
                            AVG(price) as avg_price,
                            MIN(price) as min_price,
                            MAX(price) as max_price,
                            AVG(discount_percent) as avg_discount,
                            AVG(rating) as avg_rating
                        FROM `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
                        WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                        GROUP BY sale_date, category
                    """,
                    'useLegacySql': False
                }
            }
        )
        
        # Product performance
        create_product_performance = BigQueryInsertJobOperator(
            task_id='create_product_performance',
            configuration={
                'query': {
                    'query': f"""
                        CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.product_performance` AS
                        SELECT 
                            product_id,
                            product_name,
                            category,
                            AVG(price) as avg_price,
                            SUM(sales_count) as total_sales,
                            AVG(rating) as avg_rating,
                            COUNT(*) as days_available,
                            MAX(sale_date) as last_sale_date
                        FROM `{PROJECT_ID}.{DATASET_ID}.cleaned_sales_data`
                        WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                        GROUP BY product_id, product_name, category
                        HAVING total_sales > 0
                        ORDER BY total_sales DESC
                    """,
                    'useLegacySql': False
                }
            }
        )
        
        create_daily_summary >> create_product_performance
    
    # Task: Generate summary statistics
    summary_stats = PythonOperator(
        task_id='generate_summary_stats',
        python_callable=generate_summary_stats,
        provide_context=True
    )
    
    # Task: Archive processed files
    archive_files = GCSDeleteObjectsOperator(
        task_id='archive_processed_files',
        bucket_name=BUCKET_NAME,
        prefix=f'{RAW_FOLDER}/',
        # Note: In production, use GCSToGCSOperator to move instead of delete
    )
    
    # Task: Send success notification
    send_notification = EmailOperator(
        task_id='send_success_notification',
        to='admin@example.com',
        subject='ETL Pipeline Success - {{ ds }}',
        html_content="""
        <h3>ETL Pipeline Completed Successfully</h3>
        <p>Date: {{ ds }}</p>
        <p>Files processed: {{ task_instance.xcom_pull(task_ids='check_new_files', key='file_count') }}</p>
        <p>Summary stats: {{ task_instance.xcom_pull(task_ids='generate_summary_stats', key='summary_stats') }}</p>
        """
    )
    
    # Define task dependencies
    check_files >> create_raw_table >> load_raw_data >> validate_data
    validate_data >> transform_group >> analytics_group >> summary_stats
    summary_stats >> archive_files >> send_notification