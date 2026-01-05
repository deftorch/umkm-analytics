"""
Data Loading Utilities dengan Deduplication
Untuk upload data ke BigQuery tanpa duplikat
"""

import pandas as pd
from google.cloud import bigquery
from datetime import datetime


def load_with_deduplication(
    client: bigquery.Client,
    df: pd.DataFrame,
    table_id: str,
    unique_key: str,
    mode: str = "append"
) -> dict:
    """
    Upload data ke BigQuery dengan pengecekan duplikat
    
    Args:
        client: BigQuery client
        df: DataFrame yang akan diupload
        table_id: Full table ID (project.dataset.table)
        unique_key: Kolom yang dijadikan unique identifier (e.g., 'transaction_id', 'review_id')
        mode: 'append' (tambah data baru) atau 'replace' (ganti semua)
    
    Returns:
        dict dengan statistik upload
    """
    
    stats = {
        "total_input": len(df),
        "duplicates_skipped": 0,
        "new_records": 0,
        "status": "success"
    }
    
    if mode == "replace":
        # Mode replace: hapus dan upload ulang semua
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True,
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        stats["new_records"] = len(df)
        print(f"✅ Replaced table with {len(df)} records")
        return stats
    
    # Mode append: cek duplikat dulu
    try:
        # Ambil existing IDs dari BigQuery
        query = f"SELECT DISTINCT {unique_key} FROM `{table_id}`"
        existing_ids = set()
        
        try:
            result = client.query(query).result()
            existing_ids = {row[0] for row in result}
            print(f"📊 Existing records in table: {len(existing_ids)}")
        except Exception as e:
            # Table mungkin belum ada
            print(f"ℹ️ Table baru, tidak ada data existing")
        
        # Filter hanya data baru
        if unique_key in df.columns and len(existing_ids) > 0:
            df_new = df[~df[unique_key].isin(existing_ids)]
            stats["duplicates_skipped"] = len(df) - len(df_new)
            stats["new_records"] = len(df_new)
            
            print(f"📋 Input records: {len(df)}")
            print(f"⏭️ Skipped (already exists): {stats['duplicates_skipped']}")
            print(f"🆕 New records to insert: {len(df_new)}")
            
            if len(df_new) == 0:
                print("ℹ️ No new records to insert")
                return stats
            
            df = df_new
        else:
            stats["new_records"] = len(df)
        
        # Upload data baru
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            autodetect=True,
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        print(f"✅ Inserted {len(df)} new records")
        
    except Exception as e:
        stats["status"] = f"error: {str(e)}"
        print(f"❌ Error: {e}")
    
    return stats


def merge_data(
    client: bigquery.Client,
    source_table: str,
    target_table: str,
    unique_key: str,
    update_columns: list = None
) -> dict:
    """
    MERGE data dari source ke target (UPSERT)
    Update jika sudah ada, insert jika baru
    
    Args:
        client: BigQuery client
        source_table: Staging/temp table
        target_table: Target table
        unique_key: Kolom unique identifier
        update_columns: Kolom yang akan diupdate jika record sudah ada
    """
    
    if update_columns is None:
        update_columns = []
    
    # Build UPDATE clause
    update_clause = ", ".join([f"T.{col} = S.{col}" for col in update_columns])
    if not update_clause:
        update_clause = f"T.{unique_key} = S.{unique_key}"  # dummy update
    
    merge_query = f"""
    MERGE `{target_table}` T
    USING `{source_table}` S
    ON T.{unique_key} = S.{unique_key}
    
    WHEN MATCHED THEN
        UPDATE SET {update_clause}
    
    WHEN NOT MATCHED THEN
        INSERT ROW
    """
    
    print(f"🔄 Merging data from {source_table} to {target_table}...")
    job = client.query(merge_query)
    result = job.result()
    
    print(f"✅ Merge completed!")
    
    return {"status": "success", "rows_affected": job.num_dml_affected_rows}


def check_duplicates(
    client: bigquery.Client,
    table_id: str,
    unique_key: str
) -> pd.DataFrame:
    """
    Cek apakah ada duplikat dalam tabel
    Returns DataFrame dengan record yang duplikat
    """
    
    query = f"""
    SELECT 
        {unique_key},
        COUNT(*) as count
    FROM `{table_id}`
    GROUP BY {unique_key}
    HAVING count > 1
    ORDER BY count DESC
    LIMIT 100
    """
    
    df = client.query(query).to_dataframe()
    
    if len(df) > 0:
        print(f"⚠️ Found {len(df)} duplicate keys!")
    else:
        print(f"✅ No duplicates found")
    
    return df


def remove_duplicates(
    client: bigquery.Client,
    table_id: str,
    unique_key: str,
    keep: str = "first"
) -> dict:
    """
    Hapus duplicate records dari tabel
    
    Args:
        keep: 'first' atau 'last' - record mana yang dipertahankan
    """
    
    order = "ASC" if keep == "first" else "DESC"
    
    query = f"""
    CREATE OR REPLACE TABLE `{table_id}` AS
    SELECT * EXCEPT(row_num)
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY {unique_key} ORDER BY ingestion_date {order}) as row_num
        FROM `{table_id}`
    )
    WHERE row_num = 1
    """
    
    print(f"🧹 Removing duplicates from {table_id}...")
    job = client.query(query)
    job.result()
    
    # Count remaining
    count_query = f"SELECT COUNT(*) as cnt FROM `{table_id}`"
    result = client.query(count_query).result()
    count = list(result)[0].cnt
    
    print(f"✅ Deduplication complete. Remaining records: {count}")
    
    return {"status": "success", "remaining_records": count}


# ============================================
# Contoh Penggunaan
# ============================================
"""
from google.cloud import bigquery
from data_loader import load_with_deduplication, check_duplicates

client = bigquery.Client(project='ipsd-483408')
table_id = 'ipsd-483408.umkm_analytics.raw_sales'

# Load CSV
df = pd.read_csv('transactions.csv')

# Upload dengan deduplication
stats = load_with_deduplication(
    client=client,
    df=df,
    table_id=table_id,
    unique_key='transaction_id',
    mode='append'
)

print(stats)
# Output:
# {
#     "total_input": 500,
#     "duplicates_skipped": 300,
#     "new_records": 200,
#     "status": "success"
# }
"""
