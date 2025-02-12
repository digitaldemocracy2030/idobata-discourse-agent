# VPCネットワークの作成
resource "google_compute_network" "vpc" {
  name                    = var.vpc_name
  auto_create_subnetworks = false
  
  depends_on = [google_project_service.required_apis]
}

# サブネットの作成
resource "google_compute_subnetwork" "subnet" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_ip_range
  network       = google_compute_network.vpc.id
  region        = var.region

  private_ip_google_access = true
}

# Serverless VPC アクセスコネクタの作成
resource "google_vpc_access_connector" "connector" {
  name          = var.vpc_connector_name
  region        = var.region
  ip_cidr_range = var.vpc_connector_range
  network       = google_compute_network.vpc.name
}

# Cloud Run用のサービスアカウント
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name} Cloud Run service"
}

# Artifact Registryリポジトリの作成
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "${var.service_name}-repo"
  format        = "DOCKER"
}

# Cloud Runサービスの作成
resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      service_account_name = google_service_account.cloud_run_sa.email
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/${var.service_name}:latest"
        ports {
          container_port = var.container_port
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"      = var.min_instances
        "autoscaling.knative.dev/maxScale"      = var.max_instances
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.connector.id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_vpc_access_connector.connector,
    google_artifact_registry_repository.repo,
    google_project_service.required_apis
  ]
}

# Cloud Run サービスを公開するIAMポリシー
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_service.service.location
  service  = google_cloud_run_service.service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 必要なAPIの有効化を最初に行うように移動
resource "google_project_service" "required_apis" {
  for_each = toset([
    "vpcaccess.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  
  project = var.project_id
  service = each.key

  disable_dependent_services = true
  disable_on_destroy        = false
}