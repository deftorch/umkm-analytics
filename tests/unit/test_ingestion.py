import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the cloud function directory to the path so we can import main.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../cloud-functions/data-ingestion')))

from main import ingest_data

# Mocking the request
@pytest.fixture
def mock_cloud_event():
    mock = Mock()
    mock.data = {"message": "test"}
    return mock

def test_ingest_data_success(mock_cloud_event):
    with patch('main.save_to_gcs') as mock_save:
        mock_save.return_value = "test_blob"
        with patch('main.publish_message') as mock_publish:
            response = ingest_data(mock_cloud_event)
            assert response['status'] == 'success'
