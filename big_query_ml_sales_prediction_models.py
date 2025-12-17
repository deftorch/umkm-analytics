-- ============================================
-- BigQuery ML Models untuk Prediksi Penjualan
-- ============================================

-- 1. CREATE DATASET (Run sekali saja)
CREATE SCHEMA IF NOT EXISTS `umkm_analytics`
OPTIONS(
  location='asia-southeast2',
  description='Dataset untuk analisis UMKM'
);

-- ============================================
-- 2. FEATURE ENGINEERING VIEW
-- ============================================
CREATE OR REPLACE VIEW `umkm_analytics.ml_features` AS
WITH daily_features AS (
  SELECT 
    product_id,
    product_name,
    category,
    sale_date,
    AVG(price) as avg_price,
    AVG(discount_percent) as avg_discount,
    SUM(sales_count) as daily_sales,
    AVG(rating) as avg_rating,
    MAX(review_count) as review_count,
    -- Time features
    EXTRACT(DAYOFWEEK FROM sale_date) as day_of_week,
    EXTRACT(DAY FROM sale_date) as day_of_month,
    EXTRACT(MONTH FROM sale_date) as month,
    EXTRACT(YEAR FROM sale_date) as year,
    -- Is weekend?
    CASE 
      WHEN EXTRACT(DAYOFWEEK FROM sale_date) IN (1, 7) THEN 1 
      ELSE 0 
    END as is_weekend,
    -- Price category
    CASE 
      WHEN AVG(price) < 50000 THEN 'LOW'
      WHEN AVG(price) < 200000 THEN 'MEDIUM'
      ELSE 'HIGH'
    END as price_category
  FROM `umkm_analytics.cleaned_sales_data`
  GROUP BY product_id, product_name, category, sale_date
),
lagged_features AS (
  SELECT 
    *,
    -- Lag features (sales 1, 7, 30 hari sebelumnya)
    LAG(daily_sales, 1) OVER (PARTITION BY product_id ORDER BY sale_date) as sales_lag_1,
    LAG(daily_sales, 7) OVER (PARTITION BY product_id ORDER BY sale_date) as sales_lag_7,
    LAG(daily_sales, 30) OVER (PARTITION BY product_id ORDER BY sale_date) as sales_lag_30,
    -- Moving averages
    AVG(daily_sales) OVER (
      PARTITION BY product_id 
      ORDER BY sale_date 
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as sales_ma_7,
    AVG(daily_sales) OVER (
      PARTITION BY product_id 
      ORDER BY sale_date 
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as sales_ma_30
  FROM daily_features
)
SELECT * FROM lagged_features
WHERE sales_lag_1 IS NOT NULL;  -- Remove first rows without lag features


-- ============================================
-- 3. LINEAR REGRESSION MODEL untuk Prediksi Sales
-- ============================================
CREATE OR REPLACE MODEL `umkm_analytics.sales_prediction_lr`
OPTIONS(
  model_type='LINEAR_REG',
  input_label_cols=['daily_sales'],
  data_split_method='SEQ',
  data_split_col='sale_date',
  data_split_eval_fraction=0.2,
  enable_global_explain=TRUE
) AS
SELECT
  daily_sales,
  avg_price,
  avg_discount,
  avg_rating,
  review_count,
  day_of_week,
  month,
  is_weekend,
  sales_lag_1,
  sales_lag_7,
  sales_ma_7,
  price_category,
  category
FROM `umkm_analytics.ml_features`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND sale_date < CURRENT_DATE();


-- ============================================
-- 4. BOOSTED TREE MODEL (Lebih akurat)
-- ============================================
CREATE OR REPLACE MODEL `umkm_analytics.sales_prediction_boosted`
OPTIONS(
  model_type='BOOSTED_TREE_REGRESSOR',
  input_label_cols=['daily_sales'],
  data_split_method='SEQ',
  data_split_col='sale_date',
  data_split_eval_fraction=0.2,
  max_iterations=50,
  learning_rate=0.1,
  enable_global_explain=TRUE
) AS
SELECT
  daily_sales,
  avg_price,
  avg_discount,
  avg_rating,
  review_count,
  day_of_week,
  month,
  is_weekend,
  sales_lag_1,
  sales_lag_7,
  sales_ma_7,
  price_category,
  category
FROM `umkm_analytics.ml_features`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
  AND sale_date < CURRENT_DATE();


-- ============================================
-- 5. EVALUATE MODELS
-- ============================================

-- Evaluate Linear Regression
SELECT
  'Linear Regression' as model_name,
  *
FROM ML.EVALUATE(MODEL `umkm_analytics.sales_prediction_lr`);

-- Evaluate Boosted Tree
SELECT
  'Boosted Tree' as model_name,
  *
FROM ML.EVALUATE(MODEL `umkm_analytics.sales_prediction_boosted`);


-- ============================================
-- 6. FEATURE IMPORTANCE
-- ============================================
SELECT
  feature,
  importance
FROM ML.FEATURE_IMPORTANCE(MODEL `umkm_analytics.sales_prediction_boosted`)
ORDER BY importance DESC
LIMIT 10;


-- ============================================
-- 7. MAKE PREDICTIONS untuk 7 hari ke depan
-- ============================================
CREATE OR REPLACE TABLE `umkm_analytics.sales_predictions` AS
WITH latest_data AS (
  SELECT *
  FROM `umkm_analytics.ml_features`
  WHERE sale_date = (SELECT MAX(sale_date) FROM `umkm_analytics.ml_features`)
),
future_dates AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(CURRENT_DATE(), DATE_ADD(CURRENT_DATE(), INTERVAL 7 DAY))) AS date
),
prediction_input AS (
  SELECT
    l.product_id,
    l.product_name,
    l.category,
    f.date as prediction_date,
    l.avg_price,
    l.avg_discount,
    l.avg_rating,
    l.review_count,
    EXTRACT(DAYOFWEEK FROM f.date) as day_of_week,
    EXTRACT(MONTH FROM f.date) as month,
    CASE WHEN EXTRACT(DAYOFWEEK FROM f.date) IN (1, 7) THEN 1 ELSE 0 END as is_weekend,
    l.daily_sales as sales_lag_1,
    l.sales_lag_7,
    l.sales_ma_7,
    l.price_category
  FROM latest_data l
  CROSS JOIN future_dates f
)
SELECT
  product_id,
  product_name,
  category,
  prediction_date,
  predicted_daily_sales,
  CURRENT_TIMESTAMP() as prediction_timestamp
FROM ML.PREDICT(
  MODEL `umkm_analytics.sales_prediction_boosted`,
  (SELECT * FROM prediction_input)
);


-- ============================================
-- 8. ANOMALY DETECTION - Deteksi Harga Tidak Wajar
-- ============================================
CREATE OR REPLACE MODEL `umkm_analytics.price_anomaly_detection`
OPTIONS(
  model_type='AUTOML_REGRESSOR',
  input_label_cols=['avg_price'],
  budget_hours=1.0
) AS
SELECT
  category,
  sales_count,
  rating,
  review_count,
  discount_percent,
  avg_price
FROM `umkm_analytics.cleaned_sales_data`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH);


-- ============================================
-- 9. CLUSTERING - Segmentasi Produk
-- ============================================
CREATE OR REPLACE MODEL `umkm_analytics.product_clustering`
OPTIONS(
  model_type='KMEANS',
  num_clusters=5,
  standardize_features=TRUE
) AS
SELECT
  AVG(price) as avg_price,
  AVG(sales_count) as avg_sales,
  AVG(rating) as avg_rating,
  AVG(discount_percent) as avg_discount,
  COUNT(*) as frequency
FROM `umkm_analytics.cleaned_sales_data`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
GROUP BY product_id;


-- ============================================
-- 10. VIEW CLUSTERING RESULTS
-- ============================================
CREATE OR REPLACE VIEW `umkm_analytics.product_segments` AS
WITH clusters AS (
  SELECT
    product_id,
    product_name,
    category,
    AVG(price) as avg_price,
    AVG(sales_count) as avg_sales,
    AVG(rating) as avg_rating,
    AVG(discount_percent) as avg_discount,
    COUNT(*) as frequency
  FROM `umkm_analytics.cleaned_sales_data`
  WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
  GROUP BY product_id, product_name, category
)
SELECT
  c.*,
  p.CENTROID_ID as segment,
  CASE p.CENTROID_ID
    WHEN 1 THEN 'High Price, Low Sales'
    WHEN 2 THEN 'Budget Products'
    WHEN 3 THEN 'Best Sellers'
    WHEN 4 THEN 'Premium Products'
    ELSE 'Standard Products'
  END as segment_name
FROM clusters c
JOIN ML.PREDICT(MODEL `umkm_analytics.product_clustering`, (SELECT * FROM clusters)) p
USING (avg_price, avg_sales, avg_rating, avg_discount, frequency);


-- ============================================
-- 11. RECOMMENDATION QUERY
-- ============================================

-- Top 10 produk yang diprediksi laris minggu depan
SELECT
  product_name,
  category,
  prediction_date,
  ROUND(predicted_daily_sales, 0) as predicted_sales
FROM `umkm_analytics.sales_predictions`
WHERE prediction_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY predicted_daily_sales DESC
LIMIT 10;


-- Produk dengan tren penjualan menurun (perlu promosi)
WITH sales_trend AS (
  SELECT
    product_id,
    product_name,
    category,
    AVG(CASE WHEN sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN sales_count END) as sales_last_week,
    AVG(CASE WHEN sale_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY) AND DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN sales_count END) as sales_prev_week
  FROM `umkm_analytics.cleaned_sales_data`
  WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
  GROUP BY product_id, product_name, category
)
SELECT
  product_name,
  category,
  ROUND(sales_prev_week, 0) as prev_week_sales,
  ROUND(sales_last_week, 0) as last_week_sales,
  ROUND((sales_last_week - sales_prev_week) / sales_prev_week * 100, 1) as change_percent
FROM sales_trend
WHERE sales_prev_week > 0 AND sales_last_week > 0
ORDER BY change_percent ASC
LIMIT 20;


-- ============================================
-- 12. SCHEDULED QUERY untuk Auto-Update Predictions
-- ============================================
-- Run query ini via BigQuery Scheduled Queries setiap hari jam 3 pagi

-- Update predictions table
CREATE OR REPLACE TABLE `umkm_analytics.sales_predictions` AS
WITH latest_data AS (
  SELECT *
  FROM `umkm_analytics.ml_features`
  WHERE sale_date = (SELECT MAX(sale_date) FROM `umkm_analytics.ml_features`)
),
future_dates AS (
  SELECT date
  FROM UNNEST(GENERATE_DATE_ARRAY(CURRENT_DATE(), DATE_ADD(CURRENT_DATE(), INTERVAL 7 DAY))) AS date
),
prediction_input AS (
  SELECT
    l.product_id,
    l.product_name,
    l.category,
    f.date as prediction_date,
    l.avg_price,
    l.avg_discount,
    l.avg_rating,
    l.review_count,
    EXTRACT(DAYOFWEEK FROM f.date) as day_of_week,
    EXTRACT(MONTH FROM f.date) as month,
    CASE WHEN EXTRACT(DAYOFWEEK FROM f.date) IN (1, 7) THEN 1 ELSE 0 END as is_weekend,
    l.daily_sales as sales_lag_1,
    l.sales_lag_7,
    l.sales_ma_7,
    l.price_category
  FROM latest_data l
  CROSS JOIN future_dates f
)
SELECT
  product_id,
  product_name,
  category,
  prediction_date,
  predicted_daily_sales,
  CURRENT_TIMESTAMP() as prediction_timestamp
FROM ML.PREDICT(
  MODEL `umkm_analytics.sales_prediction_boosted`,
  (SELECT * FROM prediction_input)
);