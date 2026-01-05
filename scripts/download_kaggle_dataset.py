"""
Script untuk Download Dataset dari Kaggle
Bisa dijalankan di Google Colab atau lokal

Dataset: Tokopedia Product Reviews 2025
Source: https://www.kaggle.com/datasets/salmanabdu/tokopedia-product-reviews-2025
"""

# ============================================
# SETUP - Jalankan di Google Colab
# ============================================
# !pip install kagglehub pandas

import os
import pandas as pd

# ============================================
# METHOD 1: Menggunakan kagglehub
# ============================================
def download_with_kagglehub():
    """Download dataset menggunakan kagglehub library"""
    try:
        import kagglehub
        from kagglehub import KaggleDatasetAdapter
        
        print("Downloading Tokopedia Product Reviews dataset...")
        
        # Download dataset
        df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "salmanabdu/tokopedia-product-reviews-2025",
            "",  # file_path kosong untuk ambil semua
        )
        
        print(f"Dataset loaded: {len(df)} records")
        print("\nColumns:", df.columns.tolist())
        print("\nFirst 5 records:")
        print(df.head())
        
        return df
        
    except Exception as e:
        print(f"Error with kagglehub: {e}")
        print("Trying alternative method...")
        return None


# ============================================
# METHOD 2: Manual download dengan Kaggle API
# ============================================
def download_with_kaggle_api():
    """
    Download menggunakan Kaggle API
    Requires: kaggle.json credentials
    """
    try:
        import kaggle
        
        # Download dataset
        kaggle.api.dataset_download_files(
            'salmanabdu/tokopedia-product-reviews-2025',
            path='./data/kaggle',
            unzip=True
        )
        
        # Load CSV files
        data_dir = './data/kaggle'
        csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        print(f"Downloaded files: {csv_files}")
        
        # Load first CSV
        if csv_files:
            df = pd.read_csv(os.path.join(data_dir, csv_files[0]))
            return df
            
    except Exception as e:
        print(f"Error with Kaggle API: {e}")
        return None


# ============================================
# DATA PROCESSING untuk UMKM Analytics
# ============================================
def process_tokopedia_data(df):
    """
    Process dan transform data Tokopedia ke format UMKM Analytics
    
    Kaggle Dataset Schema:
    - review_text: Raw content of the review
    - review_date: Date of submission (YYYY-MM-DD)
    - review_id: Unique identifier for each review
    - product_name: Full title of the product listing
    - product_category: High-level category (e.g., Elektronik, Kesehatan)
    - product_variant: Specific variant details (Color, Size, Model)
    - product_price: Listing price in Indonesian Rupiah (IDR)
    - product_url: Direct URL to the product page
    - product_id: Unique identifier for the product
    - rating: Customer rating (1-5)
    - sold_count: Total units sold
    - shop_id: Anonymized identifier for the seller
    - sentiment_label: Derived sentiment (Positive, Neutral, Negative)
    """
    print("\nProcessing Tokopedia data for UMKM Analytics...")
    
    # Check available columns
    print("Available columns:", df.columns.tolist())
    print(f"Total records: {len(df)}")
    
    # Create processed dataframe
    processed = df.copy()
    
    # Convert data types
    if 'product_price' in processed.columns:
        processed['product_price'] = pd.to_numeric(processed['product_price'], errors='coerce')
    
    if 'rating' in processed.columns:
        processed['rating'] = pd.to_numeric(processed['rating'], errors='coerce')
    
    if 'sold_count' in processed.columns:
        processed['sold_count'] = pd.to_numeric(processed['sold_count'], errors='coerce')
    
    if 'review_date' in processed.columns:
        processed['review_date'] = pd.to_datetime(processed['review_date'], errors='coerce')
    
    # Add ingestion metadata
    processed['ingestion_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    
    # Print summary statistics
    print("\n📊 Dataset Summary:")
    print(f"   Total Records: {len(processed)}")
    
    if 'product_category' in processed.columns:
        print(f"   Categories: {processed['product_category'].nunique()}")
        print(f"   Top Categories: {processed['product_category'].value_counts().head(5).to_dict()}")
    
    if 'rating' in processed.columns:
        print(f"   Avg Rating: {processed['rating'].mean():.2f}")
    
    if 'sentiment_label' in processed.columns:
        print(f"   Sentiment Distribution:")
        for label, count in processed['sentiment_label'].value_counts().items():
            print(f"      - {label}: {count} ({count/len(processed)*100:.1f}%)")
    
    print(f"\nProcessed {len(processed)} records")
    
    return processed


def save_for_bigquery(df, output_path='data/kaggle/processed_tokopedia.csv'):
    """Save processed data as CSV for BigQuery upload"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSaved to: {output_path}")
    print("Ready for BigQuery upload!")
    
    return output_path


# ============================================
# MAIN EXECUTION
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("  Kaggle Dataset Downloader")
    print("  UMKM Analytics Project")
    print("=" * 50)
    print()
    
    # Try download
    df = download_with_kagglehub()
    
    if df is None:
        df = download_with_kaggle_api()
    
    if df is not None:
        # Process data
        processed_df = process_tokopedia_data(df)
        
        # Save for BigQuery
        output_file = save_for_bigquery(processed_df)
        
        print("\n" + "=" * 50)
        print("  NEXT STEPS:")
        print("=" * 50)
        print("  1. Open BigQuery Console")
        print("  2. Upload", output_file, "to umkm_analytics dataset")
        print("  3. Or use: bq load --source_format=CSV ...")
        print("=" * 50)
    else:
        print("\nFailed to download dataset.")
        print("Please ensure you have Kaggle credentials set up.")
        print("\nAlternative: Download manually from:")
        print("https://www.kaggle.com/datasets/salmanabdu/tokopedia-product-reviews-2025")
