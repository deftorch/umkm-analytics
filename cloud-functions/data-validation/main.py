"""
Cloud Function for Data Validation
Validates data quality and schema compliance
"""

import functions_framework
import json
import logging
from google.cloud import storage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@functions_framework.cloud_event
def validate_data(cloud_event):
    """
    Validates data uploaded to GCS
    Triggered by GCS object finalize
    """
    data = cloud_event.data

    bucket_name = data["bucket"]
    file_name = data["name"]

    logger.info(f"Validating file: gs://{bucket_name}/{file_name}")

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)

        content = blob.download_as_text()
        json_content = json.loads(content)

        # Check structure
        if 'metadata' not in json_content or 'data' not in json_content:
            raise ValueError("Invalid file structure. Missing 'metadata' or 'data' keys.")

        data_records = json_content['data']

        # Perform validation logic (example)
        valid_records = 0
        invalid_records = 0

        for record in data_records:
            if 'product_id' in record and 'price' in record:
                valid_records += 1
            else:
                invalid_records += 1

        logger.info(f"Validation complete. Valid: {valid_records}, Invalid: {invalid_records}")

        if invalid_records > 0:
            logger.warning(f"Found {invalid_records} invalid records in {file_name}")
            # Potentially move to a quarantine bucket or send alert

    except Exception as e:
        logger.error(f"Error validating file {file_name}: {e}")
        # Handle error
