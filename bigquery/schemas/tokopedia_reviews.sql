-- ============================================
-- BigQuery Schema untuk Tokopedia Product Reviews
-- Dataset: salmanabdu/tokopedia-product-reviews-2025
-- ============================================

-- Table: tokopedia_reviews
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
    -- Metadata
    ingestion_date DATE DEFAULT CURRENT_DATE()
)
PARTITION BY review_date
CLUSTER BY product_category, sentiment_label
OPTIONS(
    description='Tokopedia product reviews data from Kaggle'
);

-- ============================================
-- Views untuk Analisis
-- ============================================

-- View: Ringkasan per Kategori
CREATE OR REPLACE VIEW `umkm_analytics.v_category_summary` AS
SELECT 
    product_category,
    COUNT(DISTINCT product_id) as total_products,
    COUNT(review_id) as total_reviews,
    ROUND(AVG(rating), 2) as avg_rating,
    SUM(sold_count) as total_sold,
    ROUND(AVG(product_price), 0) as avg_price,
    COUNTIF(sentiment_label = 'Positive') as positive_reviews,
    COUNTIF(sentiment_label = 'Negative') as negative_reviews,
    COUNTIF(sentiment_label = 'Neutral') as neutral_reviews
FROM `umkm_analytics.tokopedia_reviews`
GROUP BY product_category
ORDER BY total_reviews DESC;

-- View: Top Products by Rating
CREATE OR REPLACE VIEW `umkm_analytics.v_top_rated_products` AS
SELECT 
    product_id,
    product_name,
    product_category,
    product_price,
    ROUND(AVG(rating), 2) as avg_rating,
    COUNT(review_id) as review_count,
    SUM(sold_count) as total_sold
FROM `umkm_analytics.tokopedia_reviews`
GROUP BY product_id, product_name, product_category, product_price
HAVING review_count >= 5
ORDER BY avg_rating DESC, review_count DESC
LIMIT 100;

-- View: Sentiment Analysis Summary
CREATE OR REPLACE VIEW `umkm_analytics.v_sentiment_analysis` AS
SELECT 
    product_category,
    sentiment_label,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY product_category), 2) as percentage
FROM `umkm_analytics.tokopedia_reviews`
GROUP BY product_category, sentiment_label
ORDER BY product_category, count DESC;

-- View: Daily Review Trends
CREATE OR REPLACE VIEW `umkm_analytics.v_daily_trends` AS
SELECT 
    review_date,
    COUNT(review_id) as total_reviews,
    ROUND(AVG(rating), 2) as avg_rating,
    COUNTIF(sentiment_label = 'Positive') as positive,
    COUNTIF(sentiment_label = 'Negative') as negative
FROM `umkm_analytics.tokopedia_reviews`
GROUP BY review_date
ORDER BY review_date DESC;
