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
