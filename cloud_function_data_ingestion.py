"""
Cloud Function untuk Data Ingestion
Mengambil data dari API/sumber eksternal dan menyimpan ke Cloud Storage
"""

import functions_framework
from google.cloud import storage, secretmanager
from google.cloud import pubsub_v1
import requests
import json
from datetime import datetime, timezone
import logging
import os
import random

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.environ.get('GCP_PROJECT')
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'umkm-data-lake')
RAW_FOLDER = os.environ.get('RAW_FOLDER', 'raw')


def get_secret(secret_id):
    """Ambil secret dari Secret Manager"""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        logger.warning(f"Failed to get secret {secret_id}: {e}")
        return None


def generate_sample_data(num_products=50):
    """Generate sample data untuk testing"""
    categories = ['Elektronik', 'Fashion', 'Makanan', 'Kesehatan', 'Rumah Tangga']
    products = []
    
    for i in range(num_products):
        product = {
            'product_id': f'PROD{i:05d}',
            'product_name': f'Produk {i+1}',
            'category': random.choice(categories),
            'price': random.randint(10000, 500000),
            'original_price': random.randint(10000, 500000),
            'discount_percent': random.randint(0, 50),
            'sales_count': random.randint(0, 1000),
            'rating': round(random.uniform(3.0, 5.0), 1),
            'review_count': random.randint(0, 500),
            'stock': random.randint(0, 100),
            'seller_name': f'Seller {random.randint(1, 20)}',
            'seller_location': random.choice(['Jakarta', 'Bandung', 'Surabaya', 'Medan', 'Semarang']),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        products.append(product)
    
    return products


def fetch_from_api(api_url, api_key=None):
    """Fetch data dari external API"""
    try:
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched {len(data)} records from API")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise


def validate_data(data):
    """Validasi basic data sebelum disimpan"""
    required_fields = ['product_id', 'product_name', 'price', 'category']
    validated_data = []
    
    for item in data:
        # Check required fields
        if all(field in item for field in required_fields):
            # Basic data cleaning
            item['price'] = float(item.get('price', 0))
            item['sales_count'] = int(item.get('sales_count', 0))
            validated_data.append(item)
        else:
            logger.warning(f"Item missing required fields: {item.get('product_id', 'unknown')}")
    
    logger.info(f"Validated {len(validated_data)}/{len(data)} records")
    return validated_data


def save_to_gcs(data, bucket_name, folder):
    """Simpan data ke Google Cloud Storage"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # Create filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        blob_name = f"{folder}/{timestamp}.json"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            json.dumps(data, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        
        logger.info(f"Data saved to gs://{bucket_name}/{blob_name}")
        return blob_name
        
    except Exception as e:
        logger.error(f"Failed to save to GCS: {e}")
        raise


def publish_message(topic_name, message_data):
    """Publish message ke Pub/Sub untuk trigger ETL pipeline"""
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(PROJECT_ID, topic_name)
        
        data = json.dumps(message_data).encode('utf-8')
        future = publisher.publish(topic_path, data)
        
        message_id = future.result()
        logger.info(f"Published message to {topic_name}: {message_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
        # Don't raise - ingestion should succeed even if publish fails


@functions_framework.cloud_event
def ingest_data(cloud_event):
    """
    Main function untuk data ingestion
    Triggered by Pub/Sub message from Cloud Scheduler
    """
    try:
        logger.info("Starting data ingestion process")
        
        # Parse event data
        event_data = cloud_event.data
        logger.info(f"Event data: {event_data}")
        
        # Determine data source
        use_sample_data = os.environ.get('USE_SAMPLE_DATA', 'true').lower() == 'true'
        
        if use_sample_data:
            logger.info("Using sample data for testing")
            raw_data = generate_sample_data(num_products=100)
        else:
            # Get API credentials from Secret Manager
            api_url = os.environ.get('API_URL')
            api_key_secret = os.environ.get('API_KEY_SECRET')
            
            api_key = None
            if api_key_secret:
                api_key = get_secret(api_key_secret)
            
            # Fetch from API
            logger.info(f"Fetching data from API: {api_url}")
            raw_data = fetch_from_api(api_url, api_key)
        
        # Validate data
        validated_data = validate_data(raw_data)
        
        if not validated_data:
            logger.error("No valid data to process")
            return {'status': 'error', 'message': 'No valid data'}
        
        # Add metadata
        ingestion_metadata = {
            'ingestion_id': f"ING_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
            'record_count': len(validated_data),
            'source': 'sample' if use_sample_data else 'api'
        }
        
        final_data = {
            'metadata': ingestion_metadata,
            'data': validated_data
        }
        
        # Save to Cloud Storage
        blob_name = save_to_gcs(final_data, BUCKET_NAME, RAW_FOLDER)
        
        # Publish message to trigger ETL pipeline
        etl_trigger_topic = os.environ.get('ETL_TRIGGER_TOPIC', 'etl-pipeline-trigger')
        publish_message(etl_trigger_topic, {
            'blob_name': blob_name,
            'ingestion_id': ingestion_metadata['ingestion_id'],
            'record_count': ingestion_metadata['record_count']
        })
        
        logger.info("Data ingestion completed successfully")
        
        return {
            'status': 'success',
            'ingestion_id': ingestion_metadata['ingestion_id'],
            'record_count': ingestion_metadata['record_count'],
            'blob_name': blob_name
        }
        
    except Exception as e:
        logger.error(f"Data ingestion failed: {e}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e)
        }


@functions_framework.http
def ingest_data_http(request):
    """
    HTTP endpoint untuk manual trigger
    Useful untuk testing dan debugging
    """
    try:
        # Create mock cloud event
        from cloudevents.http import CloudEvent
        
        attributes = {
            "type": "google.cloud.pubsub.topic.v1.messagePublished",
            "source": "manual-trigger"
        }
        data = {"message": {"data": ""}}
        
        event = CloudEvent(attributes, data)
        result = ingest_data(event)
        
        return json.dumps(result), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"HTTP trigger failed: {e}")
        return json.dumps({'status': 'error', 'message': str(e)}), 500


# Health check endpoint
@functions_framework.http
def health_check(request):
    """Health check endpoint"""
    return json.dumps({
        'status': 'healthy',
        'service': 'data-ingestion',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200