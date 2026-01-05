-- ============================================
-- BigQuery Schema untuk UMKM Analytics
-- Table: raw_sales (Transaksi Penjualan)
-- ============================================

CREATE TABLE IF NOT EXISTS `umkm_analytics.raw_sales` (
    transaction_id STRING NOT NULL,
    product_id STRING,
    product_name STRING,
    category STRING,
    price FLOAT64,
    discount_percent FLOAT64,
    actual_price FLOAT64,
    quantity INT64,
    total_amount FLOAT64,
    seller_name STRING,
    seller_location STRING,
    sale_date DATE,
    sale_month STRING,
    day_of_week STRING,
    ingestion_date DATE DEFAULT CURRENT_DATE()
)
PARTITION BY sale_date
CLUSTER BY category, seller_location
OPTIONS(
    description='Raw sales transactions data from UMKM',
    labels=[("env", "production"), ("team", "analytics")]
);

-- ============================================
-- Table: tokopedia_reviews
-- ============================================

CREATE TABLE IF NOT EXISTS `umkm_analytics.tokopedia_reviews` (
    review_id STRING NOT NULL,
    review_text STRING,
    review_date DATE,
    product_id STRING,
    product_name STRING,
    product_category STRING,
    product_variant STRING,
    product_price FLOAT64,
    product_url STRING,
    rating INT64,
    sold_count INT64,
    shop_id STRING,
    sentiment_label STRING,
    ingestion_date DATE DEFAULT CURRENT_DATE()
)
PARTITION BY review_date
CLUSTER BY product_category, sentiment_label
OPTIONS(
    description='Tokopedia product reviews from Kaggle dataset'
);

-- ============================================
-- Table: daily_summary
-- ============================================

CREATE TABLE IF NOT EXISTS `umkm_analytics.daily_summary` (
    summary_date DATE NOT NULL,
    total_transactions INT64,
    total_revenue FLOAT64,
    total_quantity INT64,
    avg_order_value FLOAT64,
    top_category STRING,
    top_product STRING,
    unique_sellers INT64,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY summary_date
OPTIONS(
    description='Daily aggregated sales summary'
);

-- ============================================
-- Views untuk Dashboard
-- ============================================

-- View: Ringkasan Penjualan per Kategori
CREATE OR REPLACE VIEW `umkm_analytics.v_category_sales` AS
SELECT 
    category,
    COUNT(transaction_id) as total_transactions,
    SUM(quantity) as total_quantity,
    SUM(total_amount) as total_revenue,
    ROUND(AVG(actual_price), 0) as avg_price,
    COUNT(DISTINCT seller_name) as unique_sellers
FROM `umkm_analytics.raw_sales`
GROUP BY category
ORDER BY total_revenue DESC;

-- View: Top Sellers
CREATE OR REPLACE VIEW `umkm_analytics.v_top_sellers` AS
SELECT 
    seller_name,
    seller_location,
    COUNT(transaction_id) as total_transactions,
    SUM(total_amount) as total_revenue,
    COUNT(DISTINCT category) as categories_sold
FROM `umkm_analytics.raw_sales`
GROUP BY seller_name, seller_location
ORDER BY total_revenue DESC
LIMIT 100;

-- View: Sentiment Analysis Summary
CREATE OR REPLACE VIEW `umkm_analytics.v_tokopedia_sentiment` AS
SELECT 
    product_category,
    sentiment_label,
    COUNT(*) as review_count,
    ROUND(AVG(rating), 2) as avg_rating,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY product_category), 2) as percentage
FROM `umkm_analytics.tokopedia_reviews`
GROUP BY product_category, sentiment_label
ORDER BY product_category, review_count DESC;

-- View: Daily Trends
CREATE OR REPLACE VIEW `umkm_analytics.v_daily_trends` AS
SELECT 
    sale_date,
    COUNT(transaction_id) as transactions,
    SUM(total_amount) as revenue,
    ROUND(AVG(total_amount), 0) as avg_order_value
FROM `umkm_analytics.raw_sales`
GROUP BY sale_date
ORDER BY sale_date DESC;
