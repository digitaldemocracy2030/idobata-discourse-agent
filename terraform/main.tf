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
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
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
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",      # Vertex AI API
    "compute.googleapis.com",         # Compute Engine API (Vector Search依存)
    "storage.googleapis.com",         # Cloud Storage API (Vector Search依存)
  ])

  project = var.project_id
  service = each.key

  disable_dependent_services = true
  disable_on_destroy        = false
}

# Vector Search用のCloud Storage Bucket
resource "google_storage_bucket" "vector_search_bucket" {
  name     = "${var.project_id}-vector-search"
  location = var.region
  uniform_bucket_level_access = true
  force_destroy = true  # バケットの削除を許可
  
  depends_on = [google_project_service.required_apis]
}

# Vertex AI Vector Search Index
resource "google_vertex_ai_index" "vector_search_index" {
  region       = var.region
  display_name = var.vector_search_index_name
  description  = "Vector Search Index for topic similarity detection"
  
  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.vector_search_bucket.name}/index-contents"
    config {
      dimensions = var.embedding_dimension  # テキスト埋め込みの次元数
      approximate_neighbors_count = 50
      shard_size = "SHARD_SIZE_SMALL"
      distance_measure_type = "DOT_PRODUCT_DISTANCE"
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 100
          leaf_nodes_to_search_percent = 5
        }
      }
    }
  }
  
  index_update_method = "STREAM_UPDATE"
  
  depends_on = [
    google_project_service.required_apis,
    google_storage_bucket.vector_search_bucket,
  ]
}

# Vertex AI Vector Search Index Endpoint
resource "google_vertex_ai_index_endpoint" "vector_search_endpoint" {
  region       = var.region
  display_name = var.vector_search_endpoint_name
  description  = "Vector Search Endpoint for topic similarity detection"
  
  depends_on = [
    google_project_service.required_apis
  ]
}

# Vector Search Index Endpointへのデプロイ
resource "google_vertex_ai_index_endpoint_deployed_index" "deployed_index" {
  index_endpoint = google_vertex_ai_index_endpoint.vector_search_endpoint.id
  deployed_index_id = "deployed_index_${replace(var.vector_search_index_name, "-", "_")}"
  display_name = "Deployed ${var.vector_search_index_name}"
  index = google_vertex_ai_index.vector_search_index.id
  
  dedicated_resources {
    machine_spec {
      machine_type = "e2-standard-2"
    }
    min_replica_count = 1
    max_replica_count = 1
  }
  
  depends_on = [
    google_vertex_ai_index.vector_search_index,
    google_vertex_ai_index_endpoint.vector_search_endpoint
  ]
}

# Cloud Run サービスアカウントにVertex AI関連の権限を付与
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "storage_object_user" {
  project = var.project_id
  role    = "roles/storage.objectUser"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}