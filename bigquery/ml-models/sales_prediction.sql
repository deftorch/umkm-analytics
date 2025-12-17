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
