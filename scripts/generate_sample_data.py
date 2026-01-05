"""
Script untuk Generate Sample Data UMKM
Jalankan di Google Colab atau lokal
Output: CSV file yang siap upload ke BigQuery
"""

import csv
import random
from datetime import datetime, timedelta
import os

# ============================================
# KONFIGURASI
# ============================================
NUM_PRODUCTS = 100
NUM_TRANSACTIONS = 500
OUTPUT_DIR = "data/sample"

# Data kategori UMKM Indonesia
CATEGORIES = [
    'Makanan & Minuman',
    'Fashion & Pakaian', 
    'Elektronik',
    'Kesehatan & Kecantikan',
    'Rumah Tangga',
    'Kerajinan Tangan',
    'Pertanian',
    'Jasa'
]

# Nama produk per kategori
PRODUCTS_BY_CATEGORY = {
    'Makanan & Minuman': [
        'Keripik Singkong', 'Sambal Bu Rudy', 'Kopi Toraja', 'Rendang Padang',
        'Dodol Garut', 'Bakpia Jogja', 'Kue Lapis', 'Teh Pucuk', 'Jamu Tradisional',
        'Madu Hutan', 'Gula Aren', 'Kerupuk Udang', 'Abon Sapi', 'Ikan Asin'
    ],
    'Fashion & Pakaian': [
        'Batik Pekalongan', 'Tenun Ikat', 'Kebaya Modern', 'Sarung Samarinda',
        'Tas Anyaman', 'Sepatu Kulit', 'Kaos Distro', 'Hijab Premium',
        'Sandal Jepit', 'Topi Anyaman', 'Gelang Etnik', 'Kalung Mutiara'
    ],
    'Elektronik': [
        'Charger Universal', 'Kabel Data', 'Earphone Murah', 'Powerbank Lokal',
        'Lampu LED', 'Kipas Mini', 'Speaker Bluetooth', 'Holder HP'
    ],
    'Kesehatan & Kecantikan': [
        'Sabun Herbal', 'Minyak Kayu Putih', 'Masker Wajah', 'Lulur Tradisional',
        'Shampoo Lidah Buaya', 'Minyak Kemiri', 'Bedak Dingin', 'Lipstik Lokal'
    ],
    'Rumah Tangga': [
        'Sapu Ijuk', 'Ember Plastik', 'Rak Bambu', 'Tikar Pandan',
        'Tempat Sampah', 'Gantungan Baju', 'Keset Kaki', 'Taplak Meja Batik'
    ],
    'Kerajinan Tangan': [
        'Wayang Kulit', 'Ukiran Kayu', 'Patung Bali', 'Lukisan Kaca',
        'Tas Rajut', 'Boneka Kayu', 'Topeng Malang', 'Keramik Kasongan'
    ],
    'Pertanian': [
        'Beras Organik', 'Sayur Hidroponik', 'Buah Lokal', 'Rempah Segar',
        'Pupuk Organik', 'Bibit Tanaman', 'Minyak Kelapa', 'Santan Instan'
    ],
    'Jasa': [
        'Jasa Jahit', 'Laundry Kiloan', 'Catering Rumahan', 'Service HP',
        'Cuci Motor', 'Potong Rambut', 'Fotocopy', 'Warnet'
    ]
}

# Lokasi UMKM
LOCATIONS = [
    'Jakarta Selatan', 'Jakarta Pusat', 'Bandung', 'Surabaya', 'Yogyakarta',
    'Semarang', 'Medan', 'Makassar', 'Denpasar', 'Malang', 'Solo',
    'Palembang', 'Bekasi', 'Tangerang', 'Depok', 'Bogor'
]

# Nama toko/seller UMKM
SELLER_PREFIXES = ['Toko', 'UD', 'CV', 'Warung', 'Gerai', 'Kedai', 'Rumah']
SELLER_NAMES = ['Berkah', 'Jaya', 'Makmur', 'Sejahtera', 'Barokah', 'Maju', 
                'Sentosa', 'Abadi', 'Prima', 'Sukses', 'Mandiri', 'Gemilang']


def generate_seller_name():
    """Generate nama seller UMKM yang realistis"""
    prefix = random.choice(SELLER_PREFIXES)
    name = random.choice(SELLER_NAMES)
    suffix = random.randint(1, 99)
    return f"{prefix} {name} {suffix}"


def generate_products():
    """Generate daftar produk"""
    products = []
    product_id = 1
    
    for category, product_names in PRODUCTS_BY_CATEGORY.items():
        for name in product_names:
            # Generate harga berdasarkan kategori
            if category == 'Elektronik':
                base_price = random.randint(25000, 500000)
            elif category == 'Fashion & Pakaian':
                base_price = random.randint(50000, 750000)
            elif category == 'Makanan & Minuman':
                base_price = random.randint(10000, 150000)
            elif category == 'Kerajinan Tangan':
                base_price = random.randint(75000, 1000000)
            else:
                base_price = random.randint(15000, 250000)
            
            product = {
                'product_id': f'UMKM{product_id:05d}',
                'product_name': name,
                'category': category,
                'price': base_price,
                'original_price': int(base_price * random.uniform(1.0, 1.3)),
                'stock': random.randint(10, 500),
                'seller_name': generate_seller_name(),
                'seller_location': random.choice(LOCATIONS),
                'rating': round(random.uniform(3.5, 5.0), 1),
                'review_count': random.randint(0, 500)
            }
            products.append(product)
            product_id += 1
    
    return products


def generate_transactions(products, num_transactions):
    """Generate transaksi penjualan"""
    transactions = []
    
    # Generate tanggal dalam 90 hari terakhir
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    for i in range(num_transactions):
        product = random.choice(products)
        
        # Random date
        random_days = random.randint(0, 90)
        sale_date = start_date + timedelta(days=random_days)
        
        # Quantity berdasarkan harga (produk murah = lebih banyak terjual)
        if product['price'] < 50000:
            quantity = random.randint(1, 20)
        elif product['price'] < 200000:
            quantity = random.randint(1, 10)
        else:
            quantity = random.randint(1, 5)
        
        # Discount random
        discount_percent = random.choice([0, 0, 0, 5, 10, 15, 20, 25])
        actual_price = product['price'] * (1 - discount_percent/100)
        
        transaction = {
            'transaction_id': f'TRX{i+1:06d}',
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'category': product['category'],
            'price': product['price'],
            'discount_percent': discount_percent,
            'actual_price': int(actual_price),
            'quantity': quantity,
            'total_amount': int(actual_price * quantity),
            'seller_name': product['seller_name'],
            'seller_location': product['seller_location'],
            'sale_date': sale_date.strftime('%Y-%m-%d'),
            'sale_month': sale_date.strftime('%Y-%m'),
            'day_of_week': sale_date.strftime('%A')
        }
        transactions.append(transaction)
    
    return transactions


def save_to_csv(data, filename, fieldnames):
    """Simpan data ke CSV"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✓ Saved {len(data)} records to {filename}")


def main():
    print("=" * 50)
    print("  UMKM Sample Data Generator")
    print("=" * 50)
    print()
    
    # Generate products
    print("Generating products...")
    products = generate_products()
    print(f"  Generated {len(products)} products")
    
    # Generate transactions
    print("Generating transactions...")
    transactions = generate_transactions(products, NUM_TRANSACTIONS)
    print(f"  Generated {len(transactions)} transactions")
    
    # Save to CSV
    print("\nSaving to CSV files...")
    
    # Products CSV
    product_fields = ['product_id', 'product_name', 'category', 'price', 
                      'original_price', 'stock', 'seller_name', 'seller_location',
                      'rating', 'review_count']
    save_to_csv(products, f"{OUTPUT_DIR}/products.csv", product_fields)
    
    # Transactions CSV (untuk raw_sales table)
    transaction_fields = ['transaction_id', 'product_id', 'product_name', 'category',
                          'price', 'discount_percent', 'actual_price', 'quantity',
                          'total_amount', 'seller_name', 'seller_location', 
                          'sale_date', 'sale_month', 'day_of_week']
    save_to_csv(transactions, f"{OUTPUT_DIR}/transactions.csv", transaction_fields)
    
    # Summary statistics
    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    print(f"  Total Products: {len(products)}")
    print(f"  Total Transactions: {len(transactions)}")
    print(f"  Categories: {len(CATEGORIES)}")
    print(f"  Date Range: 90 days")
    print(f"  Total Revenue: Rp {sum(t['total_amount'] for t in transactions):,}")
    print()
    print("  Files created:")
    print(f"    - {OUTPUT_DIR}/products.csv")
    print(f"    - {OUTPUT_DIR}/transactions.csv")
    print()
    print("  Next: Upload these CSV files to BigQuery!")
    print("=" * 50)


if __name__ == "__main__":
    main()
