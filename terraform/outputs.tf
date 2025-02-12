output "cloud_run_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.service.status[0].url
}

output "vpc_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc.id
}

output "subnet_id" {
  description = "The ID of the subnet"
  value       = google_compute_subnetwork.subnet.id
}

output "vpc_connector_id" {
  description = "The ID of the VPC connector"
  value       = google_vpc_access_connector.connector.id
}

output "service_account_email" {
  description = "The email of the service account used by Cloud Run"
  value       = google_service_account.cloud_run_sa.email
}

output "artifact_registry_repository" {
  description = "The name of the Artifact Registry repository"
  value       = google_artifact_registry_repository.repo.name
}