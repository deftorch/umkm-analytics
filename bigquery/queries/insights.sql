SELECT
  product_name,
  category,
  prediction_date,
  ROUND(predicted_daily_sales, 0) as predicted_sales
FROM `umkm_analytics.sales_predictions`
WHERE prediction_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY predicted_daily_sales DESC
LIMIT 10;
