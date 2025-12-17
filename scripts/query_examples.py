"""
Sample Python queries to interact with the data
"""

from google.cloud import bigquery
import pandas as pd
import os

PROJECT_ID = os.environ.get('GCP_PROJECT')
DATASET_ID = 'umkm_analytics'

def get_daily_sales_summary():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT
        summary_date,
        SUM(total_sales) as daily_sales
    FROM `{PROJECT_ID}.{DATASET_ID}.daily_summary`
    GROUP BY summary_date
    ORDER BY summary_date DESC
    LIMIT 30
    """
    return client.query(query).to_dataframe()

def get_top_products():
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT
        product_name,
        total_sales,
        avg_rating
    FROM `{PROJECT_ID}.{DATASET_ID}.product_performance`
    ORDER BY total_sales DESC
    LIMIT 10
    """
    return client.query(query).to_dataframe()

if __name__ == "__main__":
    print("Daily Sales Summary:")
    print(get_daily_sales_summary())
    print("\nTop Products:")
    print(get_top_products())
