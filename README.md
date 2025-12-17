# Sistem Analisis Tren Harga & Penjualan UMKM
## Platform Big Data untuk UMKM Indonesia

![Architecture](https://img.shields.io/badge/GCP-Architecture-blue)
![Python](https://img.shields.io/badge/Python-3.9-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Daftar Isi
- [Overview](#overview)
- [Arsitektur](#arsitektur)
- [Fitur Utama](#fitur-utama)
- [Prerequisites](#prerequisites)
- [Setup & Deployment](#setup--deployment)
- [Struktur Project](#struktur-project)
- [Penggunaan](#penggunaan)
- [Monitoring](#monitoring)
- [Cost Estimation](#cost-estimation)

---

## 🎯 Overview

Sistem ini membantu UMKM Indonesia untuk:
- ✅ Menganalisis tren harga produk
- ✅ Memprediksi penjualan
- ✅ Memahami perilaku konsumen
- ✅ Mengoptimalkan strategi pricing
- ✅ Membuat keputusan berbasis data

**Teknologi**: Google Cloud Platform (Full Stack)

---

## 🏗️ Arsitektur

```
┌─────────────────┐
│  Data Sources   │
│  (API/Dataset)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloud Scheduler           │
│   (Trigger setiap hari)     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Pub/Sub Topic             │
│   (Event trigger)           │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloud Function            │
│   (Data Ingestion)          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloud Storage             │
│   gs://umkm-data-lake/raw/  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloud Composer (Airflow)  │
│   (ETL Orchestration)       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   BigQuery                  │
│   (Data Warehouse)          │
└────────┬────────────────────┘
         │
         ├──────────────────────────┐
         │                          │
         ▼                          ▼
┌────────────────┐      ┌──────────────────┐
│  BigQuery ML   │      │  Looker Studio   │
│  (Prediksi)    │      │  (Dashboard)     │
└────────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Cloud Monitoring          │
│   (Logs & Alerts)           │
└─────────────────────────────┘
```

---

## ✨ Fitur Utama

### 1. Data Ingestion Otomatis
- Pengambilan data harian dari sumber eksternal
- Support untuk multiple data sources
- Error handling & retry mechanism

### 2. ETL Pipeline
- Data cleaning & normalization
- Data validation
- Incremental loading
- Partitioning otomatis

### 3. Analytics & ML
- Analisis tren harga
- Segmentasi produk
- Prediksi penjualan (BQML)
- Anomaly detection

### 4. Dashboard Interaktif
- Real-time visualization
- Filter dinamis
- Export ke PDF/Excel
- Mobile responsive

### 5. Monitoring & Alerting
- Pipeline health monitoring
- Cost tracking
- Error alerts via email
- Performance metrics

---

## 📦 Prerequisites

### 1. Google Cloud Account
- Aktifkan billing
- Quota sufficient untuk:
  - Cloud Functions: 10 instances
  - BigQuery: 1TB processed/month
  - Cloud Storage: 100GB

### 2. Tools yang Diperlukan
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Install Python 3.9+
python --version

# Install dependencies
pip install -r requirements.txt
```

### 3. API yang Harus Diaktifkan
```bash
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable composer.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable monitoring.googleapis.com
```

---

## 🚀 Setup & Deployment

### Step 1: Clone Repository
```bash
git clone https://github.com/your-repo/umkm-analytics.git
cd umkm-analytics
```

### Step 2: Konfigurasi Environment
```bash
# Copy template config
cp config/config.template.yaml config/config.yaml

# Edit dengan GCP project ID Anda
nano config/config.yaml
```

### Step 3: Setup GCP Resources
```bash
# Jalankan setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Step 4: Deploy Components
```bash
# Deploy semua komponen
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Step 5: Verifikasi
```bash
# Cek status deployment
./scripts/verify.sh
```

---

## 📁 Struktur Project

```
umkm-analytics/
│
├── cloud-functions/          # Cloud Functions code
│   ├── data-ingestion/
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── README.md
│   └── data-validation/
│
├── composer-dags/            # Airflow DAGs
│   ├── etl_pipeline.py
│   ├── ml_training.py
│   └── utils/
│
├── bigquery/                 # SQL scripts
│   ├── schemas/
│   ├── transformations/
│   └── ml-models/
│
├── looker-studio/            # Dashboard configs
│   └── dashboard-template.json
│
├── monitoring/               # Monitoring configs
│   ├── alerts.yaml
│   └── dashboards/
│
├── scripts/                  # Deployment scripts
│   ├── setup.sh
│   ├── deploy.sh
│   ├── verify.sh
│   └── teardown.sh
│
├── tests/                    # Unit & integration tests
│   ├── test_ingestion.py
│   └── test_etl.py
│
├── config/                   # Configuration files
│   ├── config.yaml
│   └── secrets.yaml
│
├── docs/                     # Documentation
│   ├── architecture.md
│   ├── api-docs.md
│   └── troubleshooting.md
│
├── requirements.txt
├── README.md
└── LICENSE
```

---

## 🎮 Penggunaan

### Menjalankan Manual Trigger
```bash
# Trigger data ingestion
gcloud functions call ingest-data --data '{}'

# Trigger ETL pipeline
gcloud composer environments run umkm-composer \
  --location asia-southeast2 \
  dags trigger -- etl_pipeline
```

### Query BigQuery
```bash
# Via CLI
bq query --use_legacy_sql=false \
'SELECT * FROM `umkm-analytics.sales.daily_summary` LIMIT 10'

# Via Python
python scripts/query_example.py
```

### Akses Dashboard
1. Buka Looker Studio: https://lookerstudio.google.com
2. Pilih "UMKM Analytics Dashboard"
3. Refresh data jika diperlukan

---

## 📊 Monitoring

### Cloud Monitoring Dashboard
- URL: https://console.cloud.google.com/monitoring
- Metrics yang dimonitor:
  - Function execution time
  - BigQuery query costs
  - Data pipeline success rate
  - Storage usage

### Log Analysis
```bash
# View logs
gcloud logging read "resource.type=cloud_function" --limit 50

# Real-time logs
gcloud logging tail "resource.type=cloud_function"
```

### Alerts Setup
- Email alerts untuk:
  - Pipeline failures (> 3 dalam 1 jam)
  - High BigQuery costs (> $10/day)
  - Storage quota (> 80%)

---

## 💰 Cost Estimation

### Monthly Costs (Estimasi untuk 1000 produk):

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Functions | 10K invocations | $0.40 |
| Cloud Storage | 50GB | $1.00 |
| BigQuery | 100GB processed | $5.00 |
| Cloud Composer | Small env | $150 |
| Networking | 10GB egress | $1.20 |
| **Total** | | **~$157/month** |

**Tips Hemat**:
- Gunakan committed use discounts
- Setup lifecycle policies
- Optimize query dengan partitioning
- Monitor dengan budget alerts

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

## 👥 Team

- **Developer**: Your Team
- **Contact**: your-email@example.com
- **Documentation**: [Wiki](https://github.com/your-repo/wiki)

---

## 🔗 Links

- [GCP Documentation](https://cloud.google.com/docs)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [Airflow Guides](https://airflow.apache.org/docs/)

---

**Last Updated**: December 2025