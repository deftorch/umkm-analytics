"""
ETL Script untuk UMKM Analytics
Dijalankan via GitHub Actions atau Google Colab
"""

import os
import pandas as pd
from google.cloud import bigquery

# Configuration
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'ipsd-483408')
DATASET_ID = os.environ.get('BQ_DATASET', 'umkm_analytics')
LOCATION = 'asia-southeast2'


def run_daily_summary_etl():
    """Generate daily summary dari raw_sales"""
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    
    query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.daily_summary` AS
    SELECT 
        sale_date as summary_date,
        COUNT(transaction_id) as total_transactions,
        SUM(total_amount) as total_revenue,
        SUM(quantity) as total_quantity,
        ROUND(AVG(total_amount), 0) as avg_order_value,
        ARRAY_AGG(category ORDER BY total_amount DESC LIMIT 1)[OFFSET(0)] as top_category,
        ARRAY_AGG(product_name ORDER BY total_amount DESC LIMIT 1)[OFFSET(0)] as top_product,
        COUNT(DISTINCT seller_name) as unique_sellers,
        CURRENT_TIMESTAMP() as created_at
    FROM `{PROJECT_ID}.{DATASET_ID}.raw_sales`
    GROUP BY sale_date
    ORDER BY sale_date DESC
    """
    
    print("🔄 Running daily summary ETL...")
    job = client.query(query)
    job.result()
    print("✅ Daily summary generated!")
    
    # Get row count
    count_query = f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.daily_summary`"
    result = client.query(count_query).result()
    for row in result:
        print(f"📊 Total rows in daily_summary: {row.cnt}")


def run_sentiment_aggregation():
    """Aggregate sentiment dari tokopedia_reviews"""
    client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    
    query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.sentiment_summary` AS
    SELECT 
        product_category,
        sentiment_label,
        COUNT(*) as review_count,
        ROUND(AVG(rating), 2) as avg_rating,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY product_category), 2) as percentage,
        CURRENT_TIMESTAMP() as created_at
    FROM `{PROJECT_ID}.{DATASET_ID}.tokopedia_reviews`
    GROUP BY product_category, sentiment_label
    ORDER BY product_category, review_count DESC
    """
    
    print("🔄 Running sentiment aggregation...")
    job = client.query(query)
    job.result()
    print("✅ Sentiment summary generated!")


def main():
    print("=" * 50)
    print("  UMKM Analytics - ETL Pipeline")
    print("=" * 50)
    print(f"Project: {PROJECT_ID}")
    print(f"Dataset: {DATASET_ID}")
    print()
    
    try:
        run_daily_summary_etl()
        run_sentiment_aggregation()
        print()
        print("✅ All ETL jobs completed successfully!")
    except Exception as e:
        print(f"❌ ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
