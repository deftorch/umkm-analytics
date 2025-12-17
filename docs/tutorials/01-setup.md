# Quick Start Guide

## Prerequisites
- Google Cloud Platform account
- `gcloud` CLI installed and authenticated
- Python 3.9+

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd umkm-analytics
   ```

2. **Configure Environment**
   Edit `config/config.yaml` with your Project ID.

3. **Run Setup Script**
   ```bash
   ./scripts/setup.sh
   ```
   This will enable APIs, create buckets, and datasets.

4. **Deploy Components**
   ```bash
   ./scripts/deploy.sh
   ```
   This deploys Cloud Functions and Airflow DAGs.

5. **Verify Installation**
   ```bash
   ./scripts/verify.sh
   ```

## Usage

- **Trigger Ingestion**:
  ```bash
  gcloud functions call data-ingestion --data '{"message":"trigger"}'
  ```

- **Check Dashboard**:
  Go to Looker Studio and connect to `umkm_analytics.daily_summary`.
