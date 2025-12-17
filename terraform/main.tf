variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  default     = "asia-southeast2"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "data_lake" {
  name          = "${var.project_id}-data-lake"
  location      = var.region
  force_destroy = true
}

resource "google_bigquery_dataset" "umkm_analytics" {
  dataset_id  = "umkm_analytics"
  description = "Dataset untuk analisis UMKM"
  location    = var.region
}
