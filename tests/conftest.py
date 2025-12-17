import pytest

@pytest.fixture
def sample_data():
    return {
        "product_id": "P1",
        "price": 100
    }
