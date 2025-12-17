"""
Apache Airflow DAG for ML Training Pipeline
Retrains and deploys ML models based on new data
"""

from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryInsertJobOperator
)
from datetime import datetime, timedelta

# Configuration
PROJECT_ID = 'your-project-id'
DATASET_ID = 'umkm_analytics'

default_args = {
    'owner': 'data-team',
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=10)
}

dag = DAG(
    'ml_training_pipeline',
    default_args=default_args,
    schedule_interval='@weekly',
    catchup=False
)

with dag:
    # 1. Train Linear Regression Model
    train_lr_model = BigQueryInsertJobOperator(
        task_id='train_lr_model',
        configuration={
            'query': {
                'query': f"""
                CREATE OR REPLACE MODEL `{PROJECT_ID}.{DATASET_ID}.sales_prediction_lr`
                OPTIONS(
                  model_type='LINEAR_REG',
                  input_label_cols=['daily_sales'],
                  data_split_method='SEQ',
                  data_split_col='sale_date',
                  data_split_eval_fraction=0.2
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
                FROM `{PROJECT_ID}.{DATASET_ID}.ml_features`
                WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
                """,
                'useLegacySql': False
            }
        }
    )

    # 2. Train Boosted Tree Model
    train_boosted_model = BigQueryInsertJobOperator(
        task_id='train_boosted_model',
        configuration={
            'query': {
                'query': f"""
                CREATE OR REPLACE MODEL `{PROJECT_ID}.{DATASET_ID}.sales_prediction_boosted`
                OPTIONS(
                  model_type='BOOSTED_TREE_REGRESSOR',
                  input_label_cols=['daily_sales'],
                  data_split_method='SEQ',
                  data_split_col='sale_date',
                  data_split_eval_fraction=0.2,
                  max_iterations=50
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
                FROM `{PROJECT_ID}.{DATASET_ID}.ml_features`
                WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
                """,
                'useLegacySql': False
            }
        }
    )

    # 3. Evaluate and Compare (Simplified)
    evaluate_models = BigQueryInsertJobOperator(
        task_id='evaluate_models',
        configuration={
            'query': {
                'query': f"""
                SELECT
                  'Boosted Tree' as model_name,
                  *
                FROM ML.EVALUATE(MODEL `{PROJECT_ID}.{DATASET_ID}.sales_prediction_boosted`)
                UNION ALL
                SELECT
                  'Linear Regression' as model_name,
                  *
                FROM ML.EVALUATE(MODEL `{PROJECT_ID}.{DATASET_ID}.sales_prediction_lr`)
                """,
                'useLegacySql': False
            }
        }
    )

    train_lr_model >> train_boosted_model >> evaluate_models
