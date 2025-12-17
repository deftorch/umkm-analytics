# 📁 Complete Project Structure

```
umkm-analytics/
│
├── README.md                          # Main documentation
├── QUICKSTART.md                      # Quick start guide
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore rules
├── requirements.txt                   # Python dependencies
│
├── config/                            # Configuration files
│   ├── config.yaml                    # Main config (DO NOT commit)
│   ├── config.template.yaml           # Config template
│   └── secrets.yaml.template          # Secrets template
│
├── scripts/                           # Deployment & utility scripts
│   ├── setup.sh                       # Initial setup script
│   ├── deploy.sh                      # Deployment script
│   ├── verify.sh                      # Verification script
│   ├── teardown.sh                    # Cleanup script
│   ├── backup.sh                      # Backup script
│   └── query_examples.py              # Sample Python queries
│
├── cloud-functions/                   # Cloud Functions code
│   │
│   ├── data-ingestion/               # Data ingestion function
│   │   ├── main.py                   # Main function code
│   │   ├── requirements.txt          # Function dependencies
│   │   ├── .gcloudignore            # GCloud ignore
│   │   └── README.md                 # Function documentation
│   │
│   └── data-validation/              # Data validation function
│       ├── main.py
│       ├── requirements.txt
│       └── README.md
│
├── composer-dags/                     # Apache Airflow DAGs
│   │
│   ├── etl_pipeline.py               # Main ETL DAG
│   ├── ml_training.py                # ML model training DAG
│   ├── data_quality.py               # Data quality checks DAG
│   │
│   ├── utils/                        # Utility modules
│   │   ├── __init__.py
│   │   ├── bigquery_helper.py       # BigQuery utilities
│   │   ├── gcs_helper.py            # GCS utilities
│   │   └── validation.py            # Data validation
│   │
│   └── config/                       # DAG configurations
│       ├── etl_config.yaml
│       └── ml_config.yaml
│
├── bigquery/                          # BigQuery SQL scripts
│   │
│   ├── schemas/                      # Table schemas
│   │   ├── create_tables.sql        # Create all tables
│   │   ├── raw_sales.sql            # Raw sales schema
│   │   ├── cleaned_sales.sql        # Cleaned sales schema
│   │   └── aggregates.sql           # Aggregate tables
│   │
│   ├── transformations/              # ETL transformations
│   │   ├── clean_data.sql           # Data cleaning
│   │   ├── aggregate_daily.sql      # Daily aggregations
│   │   ├── product_performance.sql  # Product metrics
│   │   └── category_analysis.sql    # Category analysis
│   │
│   ├── ml-models/                    # ML model SQL
│   │   ├── sales_prediction.sql     # Sales prediction model
│   │   ├── price_anomaly.sql        # Anomaly detection
│   │   └── product_clustering.sql   # Product segmentation
│   │
│   └── queries/                      # Sample queries
│       ├── insights.sql             # Business insights
│       ├── reports.sql              # Standard reports
│       └── troubleshooting.sql      # Debug queries
│
├── looker-studio/                     # Looker Studio configs
│   ├── dashboard-template.json       # Dashboard template
│   ├── executive-report.json         # Executive report
│   └── ml-insights.json              # ML insights dashboard
│
├── monitoring/                        # Monitoring configs
│   │
│   ├── alerts/                       # Alert policies
│   │   ├── function-errors.yaml     # Function error alerts
│   │   ├── high-costs.yaml          # Cost alerts
│   │   └── data-quality.yaml        # Data quality alerts
│   │
│   ├── dashboards/                   # Cloud Monitoring dashboards
│   │   ├── system-health.json       # System health dashboard
│   │   ├── pipeline-performance.json # Pipeline metrics
│   │   └── cost-tracking.json       # Cost tracking
│   │
│   └── log-filters/                  # Log-based metrics
│       ├── ingestion-success.yaml
│       └── etl-failures.yaml
│
├── tests/                             # Tests
│   │
│   ├── unit/                         # Unit tests
│   │   ├── test_ingestion.py        # Cloud Function tests
│   │   ├── test_transformations.py  # Transformation tests
│   │   └── test_validation.py       # Validation tests
│   │
│   ├── integration/                  # Integration tests
│   │   ├── test_pipeline.py         # Full pipeline test
│   │   └── test_bigquery.py         # BigQuery integration
│   │
│   ├── fixtures/                     # Test data
│   │   ├── sample_raw_data.json
│   │   └── expected_output.json
│   │
│   └── conftest.py                   # Pytest configuration
│
├── docs/                              # Documentation
│   │
│   ├── architecture.md               # Architecture details
│   ├── api-docs.md                   # API documentation
│   ├── deployment-guide.md           # Deployment guide
│   ├── troubleshooting.md            # Troubleshooting guide
│   ├── cost-optimization.md          # Cost optimization
│   ├── security-guide.md             # Security best practices
│   │
│   ├── diagrams/                     # Architecture diagrams
│   │   ├── architecture.png
│   │   ├── data-flow.png
│   │   └── deployment-flow.png
│   │
│   └── tutorials/                    # Step-by-step tutorials
│       ├── 01-setup.md
│       ├── 02-first-ingestion.md
│       ├── 03-create-dashboard.md
│       └── 04-ml-predictions.md
│
├── terraform/                         # Infrastructure as Code (Optional)
│   ├── main.tf                       # Main Terraform config
│   ├── variables.tf                  # Variables
│   ├── outputs.tf                    # Outputs
│   └── modules/                      # Terraform modules
│       ├── storage/
│       ├── bigquery/
│       └── functions/
│
├── .github/                           # GitHub specific
│   ├── workflows/                    # GitHub Actions
│   │   ├── deploy.yml               # Auto deployment
│   │   ├── test.yml                 # Run tests
│   │   └── lint.yml                 # Code linting
│   │
│   ├── ISSUE_TEMPLATE/              # Issue templates
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   │
│   └── PULL_REQUEST_TEMPLATE.md     # PR template
│
├── notebooks/                         # Jupyter notebooks
│   ├── exploratory_analysis.ipynb    # Data exploration
│   ├── model_training.ipynb          # ML experimentation
│   └── visualization_examples.ipynb  # Viz examples
│
└── data/                              # Local data (gitignored)
    ├── sample/                       # Sample data for testing
    │   └── products_sample.json
    ├── schemas/                      # Local schema copies
    └── temp/                         # Temporary files


# ============================================
# Individual File Contents Summary
# ============================================

## Core Files

### config/config.yaml
- GCP project settings
- BigQuery configuration
- Storage settings
- Composer/Airflow config
- Monitoring & alerts
- Feature flags

### scripts/setup.sh
- Enable GCP APIs
- Create service accounts
- Setup Cloud Storage
- Create BigQuery datasets
- Configure Pub/Sub
- Initialize Secret Manager

### scripts/deploy.sh
- Deploy Cloud Functions
- Upload Airflow DAGs
- Create BigQuery tables
- Deploy ML models
- Setup monitoring
- Configure alerts

### scripts/verify.sh
- Verify all components
- Check connectivity
- Test data pipeline
- Validate deployments
- Generate health report

## Cloud Functions

### cloud-functions/data-ingestion/main.py
Functions:
- `ingest_data()` - Main ingestion (Pub/Sub trigger)
- `fetch_from_api()` - Fetch from external API
- `validate_data()` - Data validation
- `save_to_gcs()` - Save to Cloud Storage
- `generate_sample_data()` - Generate test data

### cloud-functions/data-ingestion/requirements.txt
```
google-cloud-storage==2.14.0
google-cloud-pubsub==2.19.0
requests==2.31.0
functions-framework==3.5.0
```

## Composer DAGs

### composer-dags/etl_pipeline.py
Tasks:
1. check_new_files - Check for new data
2. load_raw_data - Load to BigQuery raw
3. validate_data - Data quality checks
4. transform_data - Clean & transform
5. create_aggregates - Generate summaries
6. archive_files - Move processed files

### composer-dags/ml_training.py
Tasks:
1. prepare_features - Feature engineering
2. train_model - Train ML model
3. evaluate_model - Model evaluation
4. deploy_model - Deploy if improved

## BigQuery

### bigquery/schemas/create_tables.sql
Tables created:
- raw_sales_data (partitioned by ingestion_date)
- cleaned_sales_data (partitioned by sale_date)
- daily_summary (aggregated metrics)
- product_performance (product-level KPIs)
- sales_predictions (ML predictions)

### bigquery/ml-models/sales_prediction.sql
Models:
- Linear Regression (fast, interpretable)
- Boosted Tree (more accurate)
- Features: price, discount, time, lags

## Tests

### tests/unit/test_ingestion.py
```python
def test_generate_sample_data()
def test_validate_data()
def test_save_to_gcs()
```

### tests/integration/test_pipeline.py
```python
def test_full_pipeline()
def test_etl_transformation()
def test_bigquery_loading()
```

## Documentation Files

### docs/architecture.md
- System architecture
- Component interactions
- Data flow diagrams
- Technology stack

### docs/api-docs.md
- Cloud Function APIs
- BigQuery views/tables
- Example requests/responses

### docs/troubleshooting.md
- Common issues & solutions
- Debugging guides
- FAQ

### docs/cost-optimization.md
- Cost breakdown
- Optimization strategies
- Budget recommendations

## Monitoring

### monitoring/alerts/function-errors.yaml
```yaml
displayName: "High Function Error Rate"
condition: errors > 3 in 5 minutes
notification: email
```

### monitoring/dashboards/system-health.json
Widgets:
- Function execution count
- BigQuery query costs
- Storage usage
- Pipeline success rate
- Data freshness

## Supporting Files

### .gitignore
```
config/config.yaml
config/secrets.yaml
*.pyc
__pycache__/
.env
data/temp/
*.log
```

### requirements.txt
Core dependencies for development:
- google-cloud-* libraries
- pandas, numpy
- pytest
- black, flake8

### LICENSE
MIT License for open source

---

# File Sizes Reference

```
Total Project Size: ~50 MB (excluding data)

Large Files:
- Cloud Composer environment: N/A (managed service)
- BigQuery data: Varies (pay per use)
- Cloud Storage: Varies by usage

Code Files:
- Python: ~100 KB
- SQL: ~50 KB  
- YAML: ~20 KB
- Shell: ~30 KB
- Docs: ~200 KB
```

---

# Git Repository Structure

```
.git/                    # Git metadata
├── hooks/              # Git hooks
├── logs/               # Git logs
└── refs/               # Git references

Branches:
- main                  # Production code
- develop              # Development branch
- feature/*            # Feature branches
- hotfix/*             # Hotfix branches
```

---

# Environment Variables

**Development (.env.dev)**
```
GCP_PROJECT=umkm-analytics-dev
BUCKET_NAME=umkm-dev-data
USE_SAMPLE_DATA=true
```

**Production (.env.prod)**
```
GCP_PROJECT=umkm-analytics-prod
BUCKET_NAME=umkm-prod-data
USE_SAMPLE_DATA=false
API_KEY_SECRET=api-key-prod
```

---

This structure provides a complete, production-ready big data platform specifically designed for UMKM analytics using Google Cloud Platform services.