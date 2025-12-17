# 🚀 Quick Start Guide - UMKM Analytics Platform

Panduan cepat untuk menjalankan sistem analisis UMKM dari awal hingga dashboard.

---

## ⏱️ Estimasi Waktu

- **Setup & Konfigurasi**: 10 menit
- **Deployment**: 30-45 menit (termasuk Cloud Composer)
- **Verifikasi & Testing**: 10 menit
- **Total**: ~1 jam

---

## 📋 Prasyarat

### 1. Google Cloud Account
- Akun GCP dengan billing aktif
- Credit/saldo minimal $10 untuk testing
- Project ID yang sudah dibuat

### 2. Tools yang Diperlukan
```bash
# Cek versi tools
gcloud --version    # Google Cloud SDK
python --version    # Python 3.9+
git --version       # Git
```

### 3. Install Missing Tools
```bash
# Install Google Cloud SDK (jika belum ada)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install yq untuk parsing YAML
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq

# Install Python dependencies
pip install -r requirements.txt
```

---

## 🎯 Step-by-Step Guide

### Step 1: Setup Project (5 menit)

```bash
# 1. Clone repository
git clone https://github.com/your-repo/umkm-analytics.git
cd umkm-analytics

# 2. Login ke GCP
gcloud auth login
gcloud auth application-default login

# 3. Buat GCP Project (jika belum ada)
gcloud projects create umkm-analytics-prod --name="UMKM Analytics"
gcloud config set project umkm-analytics-prod

# 4. Link billing account
# Ganti YOUR_BILLING_ACCOUNT_ID dengan billing account ID Anda
gcloud billing projects link umkm-analytics-prod \
    --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### Step 2: Konfigurasi (5 menit)

```bash
# 1. Copy template config
cp config/config.template.yaml config/config.yaml

# 2. Edit config file
nano config/config.yaml
```

**Edit minimal yang diperlukan:**
```yaml
gcp:
  project_id: "umkm-analytics-prod"  # Ganti dengan project ID Anda
  region: "asia-southeast2"          # Jakarta region
  
storage:
  bucket_name: "umkm-analytics-data"  # Harus unique globally
  
# Setting lainnya bisa tetap default
```

### Step 3: Setup Infrastructure (10 menit)

```bash
# Jalankan setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Script ini akan:**
- ✅ Enable Google Cloud APIs
- ✅ Buat service accounts
- ✅ Setup Cloud Storage buckets
- ✅ Buat BigQuery dataset
- ✅ Setup Pub/Sub topics
- ✅ Konfigurasi Cloud Scheduler

**Output yang diharapkan:**
```
✓ Configuration loaded
✓ gcloud CLI found
✓ Project set to umkm-analytics-prod
✓ All APIs enabled
✓ Service accounts created
✓ Bucket created
✓ BigQuery dataset created
✓ Pub/Sub topics created
✓ Setup completed successfully!
```

### Step 4: Deploy Aplikasi (30-40 menit)

```bash
# Jalankan deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**⏰ CATATAN**: Cloud Composer akan memakan waktu 20-30 menit untuk provision.

**Script ini akan:**
- ✅ Deploy Cloud Functions
- ✅ Setup BigQuery tables
- ✅ Create Composer environment (LAMA!)
- ✅ Upload Airflow DAGs
- ✅ Create ML models
- ✅ Setup monitoring

**Anda bisa monitor progress:**
```bash
# Terminal terpisah - monitor logs
gcloud logging tail "resource.type=cloud_function" --format=json
```

### Step 5: Verifikasi (5 menit)

```bash
# Jalankan verification script
chmod +x scripts/verify.sh
./scripts/verify.sh
```

**Output yang diharapkan:**
```
━━━ UMKM Analytics Platform - Deployment Verification ━━━

━━━ Cloud Storage ━━━
✓ Bucket gs://umkm-analytics-data exists
  ✓ Folder raw/ exists
  ✓ Folder processed/ exists

━━━ BigQuery ━━━
✓ Dataset umkm_analytics exists
  ℹ Found 5 tables
  ✓ Table raw_sales_data has 100 rows

━━━ Cloud Functions ━━━
✓ Function ingest-data exists
✓ Function ingest-data-http exists
  ✓ HTTP endpoint responding (200 OK)

━━━ Verification Summary ━━━
✓ All checks passed! (10/10)
🎉 System is fully operational!
```

### Step 6: Testing Manual (5 menit)

```bash
# 1. Trigger ingestion manual
gcloud pubsub topics publish data-ingestion-trigger --message='{}'

# Tunggu 30 detik...

# 2. Cek data masuk ke Cloud Storage
gsutil ls -lh gs://umkm-analytics-data/raw/

# 3. Cek data di BigQuery
bq query --use_legacy_sql=false \
'SELECT COUNT(*) as total FROM `umkm-analytics-prod.umkm_analytics.raw_sales_data`'

# 4. Trigger ETL pipeline manual
gcloud composer environments run umkm-composer \
    --location asia-southeast2 \
    dags trigger -- etl_sales_pipeline

# 5. Cek hasil di cleaned table
bq query --use_legacy_sql=false \
'SELECT category, COUNT(*) as count 
FROM `umkm-analytics-prod.umkm_analytics.cleaned_sales_data` 
GROUP BY category'
```

### Step 7: Setup Dashboard (10 menit)

**A. Via Looker Studio**

1. Buka https://lookerstudio.google.com
2. Klik "Create" → "Data Source"
3. Pilih "BigQuery"
4. Pilih:
   - Project: `umkm-analytics-prod`
   - Dataset: `umkm_analytics`
   - Table: `daily_summary`
5. Klik "Connect"
6. Klik "Create Report"

**B. Buat Visualisasi**

**Chart 1: Total Sales by Category (Pie Chart)**
- Dimension: `category`
- Metric: `total_sales`

**Chart 2: Sales Trend (Time Series)**
- Dimension: `summary_date`
- Metric: `total_sales`

**Chart 3: Average Price by Category (Bar Chart)**
- Dimension: `category`
- Metric: `avg_price`

**Chart 4: Top Products (Table)**
- Data source: `product_performance`
- Dimensions: `product_name`, `category`
- Metrics: `total_sales`, `avg_rating`

---

## 🎮 Daily Operations

### Cara Kerja Sistem

```
1. Cloud Scheduler (jam 1 pagi WIB)
   ↓
2. Trigger Pub/Sub → Cloud Function
   ↓
3. Data masuk ke Cloud Storage (raw/)
   ↓
4. Cloud Composer Airflow DAG (jam 2 pagi)
   ↓
5. ETL: raw → cleaned → aggregates
   ↓
6. Data siap di BigQuery
   ↓
7. Dashboard auto-refresh
```

### Manual Operations

**1. Trigger Ingestion Manual**
```bash
# Via Pub/Sub
gcloud pubsub topics publish data-ingestion-trigger --message='{}'

# Via HTTP
curl -X POST https://YOUR-FUNCTION-URL.run.app
```

**2. Rerun ETL Pipeline**
```bash
gcloud composer environments run umkm-composer \
    --location asia-southeast2 \
    dags trigger -- etl_sales_pipeline
```

**3. Query Data**
```bash
# Top 10 produk terlaris
bq query --use_legacy_sql=false '
SELECT product_name, SUM(sales_count) as total_sales
FROM `umkm-analytics-prod.umkm_analytics.cleaned_sales_data`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY product_name
ORDER BY total_sales DESC
LIMIT 10'
```

**4. Check Predictions**
```bash
bq query --use_legacy_sql=false '
SELECT product_name, prediction_date, predicted_daily_sales
FROM `umkm-analytics-prod.umkm_analytics.sales_predictions`
WHERE prediction_date >= CURRENT_DATE()
ORDER BY predicted_daily_sales DESC
LIMIT 10'
```

---

## 🔍 Monitoring & Troubleshooting

### View Logs

```bash
# Cloud Functions logs
gcloud logging read "resource.type=cloud_function" --limit 50

# Real-time logs
gcloud logging tail "resource.type=cloud_function"

# Filter errors only
gcloud logging read "resource.type=cloud_function AND severity=ERROR" --limit 20

# Airflow logs
gcloud composer environments run umkm-composer \
    --location asia-southeast2 \
    dags list-runs -- etl_sales_pipeline
```

### Common Issues

**Issue 1: No data in BigQuery**
```bash
# Check if Cloud Function ran
gcloud logging read "resource.type=cloud_function AND textPayload:SUCCESS" --limit 5

# Check Cloud Storage
gsutil ls -lh gs://umkm-analytics-data/raw/

# Manual trigger
gcloud pubsub topics publish data-ingestion-trigger --message='{}'
```

**Issue 2: Composer DAG not running**
```bash
# Check Composer status
gcloud composer environments describe umkm-composer --location asia-southeast2

# Access Airflow UI
# Get URL from command above, then open in browser

# Manually trigger DAG
gcloud composer environments run umkm-composer \
    --location asia-southeast2 \
    dags trigger -- etl_sales_pipeline
```

**Issue 3: High costs**
```bash
# Check BigQuery costs
bq query --use_legacy_sql=false '
SELECT
  user_email,
  query,
  total_bytes_processed / POW(10,9) AS GB_processed,
  total_bytes_billed / POW(10,9) * 5 / 1000 AS estimated_cost_usd
FROM `region-asia-southeast2`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY total_bytes_billed DESC
LIMIT 10'

# Set up budget alerts in Console
```

---

## 💰 Cost Optimization Tips

1. **Use Partitioned Tables**
   - Already configured in deployment
   - Always use `WHERE DATE(column) = ...` in queries

2. **Limit BigQuery Preview**
   ```bash
   bq query --use_legacy_sql=false --max_rows=10 'SELECT ...'
   ```

3. **Schedule Heavy Queries**
   - Run ML training only weekly
   - Use scheduled queries for aggregations

4. **Monitor Storage**
   ```bash
   gsutil du -sh gs://umkm-analytics-data/*
   ```

5. **Clean Up Old Data**
   - Lifecycle policies already set
   - Manual cleanup: `gsutil rm -r gs://bucket/old-folder/`

---

## 📊 Sample Queries

### Business Insights

**1. Kategori Paling Laris**
```sql
SELECT 
  category,
  SUM(sales_count) as total_sales,
  AVG(price) as avg_price,
  COUNT(DISTINCT product_id) as num_products
FROM `umkm-analytics-prod.umkm_analytics.cleaned_sales_data`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY category
ORDER BY total_sales DESC;
```

**2. Produk dengan Tren Naik**
```sql
WITH weekly_sales AS (
  SELECT 
    product_name,
    DATE_TRUNC(sale_date, WEEK) as week,
    SUM(sales_count) as weekly_sales
  FROM `umkm-analytics-prod.umkm_analytics.cleaned_sales_data`
  WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 8 WEEK)
  GROUP BY product_name, week
)
SELECT 
  product_name,
  AVG(weekly_sales) as avg_weekly_sales,
  STDDEV(weekly_sales) as stddev_sales
FROM weekly_sales
GROUP BY product_name
HAVING COUNT(*) >= 4
ORDER BY avg_weekly_sales DESC
LIMIT 20;
```

**3. Efektivitas Diskon**
```sql
SELECT 
  CASE 
    WHEN discount_percent = 0 THEN 'No Discount'
    WHEN discount_percent < 20 THEN '1-20%'
    WHEN discount_percent < 40 THEN '20-40%'
    ELSE '40%+'
  END as discount_range,
  AVG(sales_count) as avg_sales,
  COUNT(*) as num_products
FROM `umkm-analytics-prod.umkm_analytics.cleaned_sales_data`
WHERE sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY discount_range
ORDER BY avg_sales DESC;
```

---

## 🆘 Getting Help

### Documentation
- [README.md](README.md) - Overview lengkap
- [Architecture.md](docs/architecture.md) - Detail arsitektur
- [API Docs](docs/api-docs.md) - API reference

### Support
- Email: admin@example.com
- Issues: GitHub Issues
- Slack: #umkm-analytics

### Useful Links
- [GCP Documentation](https://cloud.google.com/docs)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [Airflow Documentation](https://airflow.apache.org/docs/)

---

## ✅ Success Checklist

- [ ] GCP Project created & billing enabled
- [ ] All scripts executable (`chmod +x scripts/*.sh`)
- [ ] Config file updated with project ID
- [ ] Setup script completed successfully
- [ ] Deployment script completed
- [ ] Verification shows 100% pass
- [ ] Manual ingestion test works
- [ ] Data visible in BigQuery
- [ ] Dashboard created in Looker Studio
- [ ] Scheduled jobs running automatically

**🎉 Congratulations! Your UMKM Analytics Platform is ready!**

---

## 🚀 What's Next?

1. **Connect Real Data Sources**
   - Update API keys in Secret Manager
   - Configure real API endpoints
   - Test with production data

2. **Enhance Dashboard**
   - Add more visualizations
   - Create alerts for anomalies
   - Setup email reports

3. **Scale Up**
   - Increase Composer resources
   - Optimize BigQuery queries
   - Add more ML models

4. **Production Hardening**
   - Enable VPC Service Controls
   - Setup backup & disaster recovery
   - Implement CI/CD pipeline

---

**Happy Analytics! 📊**