"""
Cloud Function untuk ETL Pipeline
Alternatif GRATIS untuk Cloud Composer/Airflow DAG
Triggered by Pub/Sub message dari data ingestion
"""

import functions_framework
from google.cloud import storage, bigquery
from google.cloud import pubsub_v1
import json
from datetime import datetime, timezone, timedelta
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.environ.get('GCP_PROJECT')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'umkm-data-lake')
DATASET_ID = os.environ.get('DATASET_ID', 'umkm_analytics')


def load_raw_data_from_gcs(bucket_name, blob_name):
    """Load raw data from Cloud Storage"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        content = blob.download_as_string()
        data = json.loads(content)
        
        logger.info(f"Loaded data from gs://{bucket_name}/{blob_name}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to load data from GCS: {e}")
        raise


def transform_data(raw_data):
    """Transform raw data - cleaning and enrichment"""
    try:
        metadata = raw_data.get('metadata', {})
        records = raw_data.get('data', [])
        
        transformed_records = []
        
        for record in records:
            # Clean and transform each record
            transformed = {
                'product_id': str(record.get('product_id', '')),
                'product_name': str(record.get('product_name', '')).strip(),
                'category': str(record.get('category', 'Unknown')),
                'price': float(record.get('price', 0)),
                'original_price': float(record.get('original_price', record.get('price', 0))),
                'discount_percent': int(record.get('discount_percent', 0)),
                'sales_count': int(record.get('sales_count', 0)),
                'rating': float(record.get('rating', 0)),
                'review_count': int(record.get('review_count', 0)),
                'stock': int(record.get('stock', 0)),
                'seller_name': str(record.get('seller_name', '')),
                'seller_location': str(record.get('seller_location', '')),
                'ingestion_date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                'sale_date': datetime.now(timezone.utc).strftime('%Y-%m-%d')
            }
            
            # Calculate revenue
            transformed['revenue'] = transformed['price'] * transformed['sales_count']
            
            transformed_records.append(transformed)
        
        logger.info(f"Transformed {len(transformed_records)} records")
        return transformed_records
        
    except Exception as e:
        logger.error(f"Transform failed: {e}")
        raise


def load_to_bigquery(records, table_id):
    """Load transformed data to BigQuery"""
    try:
        client = bigquery.Client()
        
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_id}"
        
        # Configure load job
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        )
        
        # Convert to newline delimited JSON
        ndjson = '\n'.join(json.dumps(record) for record in records)
        
        # Load data
        job = client.load_table_from_json(
            records,
            table_ref,
            job_config=job_config
        )
        
        job.result()  # Wait for job to complete
        
        logger.info(f"Loaded {len(records)} records to {table_ref}")
        return True
        
    except Exception as e:
        logger.error(f"BigQuery load failed: {e}")
        raise


def generate_daily_summary(date_str=None):
    """Generate daily summary statistics"""
    try:
        client = bigquery.Client()
        
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET_ID}.daily_summary`
        SELECT 
            DATE('{date_str}') as summary_date,
            SUM(revenue) as total_sales,
            SUM(sales_count) as total_quantity,
            AVG(price) as avg_price,
            (SELECT category FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales` 
             WHERE ingestion_date = DATE('{date_str}')
             GROUP BY category 
             ORDER BY SUM(sales_count) DESC 
             LIMIT 1) as top_category
        FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales`
        WHERE ingestion_date = DATE('{date_str}')
        """
        
        job = client.query(query)
        job.result()
        
        logger.info(f"Generated daily summary for {date_str}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        # Don't raise - summary is optional
        return False


@functions_framework.cloud_event
def etl_pipeline(cloud_event):
    """
    Main ETL Pipeline function
    Triggered by Pub/Sub message from data ingestion
    
    Workflow:
    1. Load raw data from GCS
    2. Transform data
    3. Load to BigQuery
    4. Generate daily summary
    """
    try:
        logger.info("Starting ETL Pipeline")
        
        # Parse event data
        import base64
        
        if hasattr(cloud_event.data, 'get'):
            message_data = cloud_event.data.get('message', {}).get('data', '')
        else:
            message_data = ''
            
        if message_data:
            decoded = base64.b64decode(message_data).decode('utf-8')
            event_data = json.loads(decoded)
        else:
            event_data = {}
        
        logger.info(f"Event data: {event_data}")
        
        blob_name = event_data.get('blob_name')
        
        if not blob_name:
            logger.error("No blob_name in event data")
            return {'status': 'error', 'message': 'No blob_name provided'}
        
        # Step 1: Load raw data
        logger.info("Step 1: Loading raw data from GCS")
        raw_data = load_raw_data_from_gcs(BUCKET_NAME, blob_name)
        
        # Step 2: Transform
        logger.info("Step 2: Transforming data")
        transformed_data = transform_data(raw_data)
        
        # Step 3: Load to BigQuery
        logger.info("Step 3: Loading to BigQuery")
        load_to_bigquery(transformed_data, 'raw_sales')
        
        # Step 4: Generate summary
        logger.info("Step 4: Generating daily summary")
        generate_daily_summary()
        
        result = {
            'status': 'success',
            'records_processed': len(transformed_data),
            'blob_name': blob_name,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"ETL Pipeline completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"ETL Pipeline failed: {e}", exc_info=True)
        return {'status': 'error', 'message': str(e)}


@functions_framework.http
def etl_pipeline_http(request):
    """
    HTTP trigger for manual ETL execution
    Useful for testing and backfill
    """
    try:
        from cloudevents.http import CloudEvent
        
        # Get blob_name from request
        request_json = request.get_json(silent=True)
        blob_name = request_json.get('blob_name') if request_json else None
        
        if not blob_name:
            return json.dumps({
                'status': 'error',
                'message': 'blob_name required in request body'
            }), 400
        
        # Create mock event
        attributes = {
            "type": "google.cloud.pubsub.topic.v1.messagePublished",
            "source": "manual-trigger"
        }
        
        import base64
        message_data = base64.b64encode(json.dumps({'blob_name': blob_name}).encode()).decode()
        data = {"message": {"data": message_data}}
        
        event = CloudEvent(attributes, data)
        result = etl_pipeline(event)
        
        return json.dumps(result), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"HTTP trigger failed: {e}")
        return json.dumps({'status': 'error', 'message': str(e)}), 500


@functions_framework.http
def health_check(request):
    """Health check endpoint"""
    return json.dumps({
        'status': 'healthy',
        'service': 'etl-pipeline',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
