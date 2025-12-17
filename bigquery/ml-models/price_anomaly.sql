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
