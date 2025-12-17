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
WHERE sales_lag_1 IS NOT NULL;
