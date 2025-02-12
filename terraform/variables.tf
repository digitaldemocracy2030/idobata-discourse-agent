variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for deployment"
  type        = string
  default     = "asia-northeast1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "discourse-bot"
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8000
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 3
}

variable "vpc_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "cloud-run-vpc"
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string
  default     = "cloud-run-subnet"
}

variable "subnet_ip_range" {
  description = "IP range for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "vpc_connector_name" {
  description = "Name of the VPC connector"
  type        = string
  default     = "cloud-run-connector"
}

variable "vpc_connector_range" {
  description = "IP range for the VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}