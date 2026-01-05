
import os
import pandas as pd
from google.cloud import bigquery

# Config
PROJECT_ID = 'ipsd-483408'
DATASET_ID = 'umkm_analytics'

def upload_table(file_path, table_name):
    client = bigquery.Client(project=PROJECT_ID)
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    
    print(f"Reading {file_path}...")
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df)} rows.")
    
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    
    print(f"Uploading to {table_id}...")
    job = client.load_table_from_dataframe(
        df, table_id, job_config=job_config
    )
    job.result()
    print(f"✅ Uploaded to {table_id}")

def main():
    try:
        # Upload transactions
        upload_table('data/sample/transactions.csv', 'raw_sales')
        
        # Upload reviews
        upload_table('data/kaggle/tokopedia_product_reviews_2025.csv', 'tokopedia_reviews')
        
        print("🎉 All uploads complete!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
