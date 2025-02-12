# Discourse Bot Deployment Guide

This guide explains how to deploy the Discourse Bot to Google Cloud Platform using Terraform and Cloud Run.

## Project Structure

```
.
├── Dockerfile              # Container configuration
├── discourse_bot.py        # Main application code
├── requirements.txt        # Python dependencies
└── terraform/             # Infrastructure as Code
    ├── main.tf            # Main Terraform configuration
    ├── variables.tf       # Variable definitions
    ├── outputs.tf         # Output definitions
    ├── provider.tf        # Provider configuration
    └── terraform.tfvars   # (Create from terraform.tfvars.example)
```

## Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
2. [Terraform](https://www.terraform.io/downloads.html)
3. [Docker](https://docs.docker.com/get-docker/)
4. A Google Cloud Project with billing enabled

## Deployment Steps

### 1. Authentication

```bash
# Login to Google Cloud
gcloud auth login

# Configure Docker authentication for Artifact Registry
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

### 2. Set Environment Variables

Copy the example Terraform variables file and update it with your GCP project details:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your project information:

```hcl
project_id = "your-project-id"
region     = "asia-northeast1"  # Default region, change if needed
```

### 3. Store Secrets in Secret Manager

Before deploying, you need to store your secrets in Google Cloud Secret Manager. You can do this using the Google Cloud Console or gcloud CLI:

```bash
# Store each secret (repeat for each environment variable)
echo -n "your-secret-value" | gcloud secrets create discourse-api-key --data-file=-
echo -n "your-secret-value" | gcloud secrets create discourse-base-url --data-file=-
echo -n "your-secret-value" | gcloud secrets create discourse-api-username --data-file=-
echo -n "your-secret-value" | gcloud secrets create app-api-key --data-file=-
echo -n "your-secret-value" | gcloud secrets create gemini-api-key --data-file=-
```

### 4. Build and Push Docker Image

From the root directory:

```bash
# Build the Docker image
docker build -t asia-northeast1-docker.pkg.dev/[PROJECT_ID]/discourse-bot-repo/discourse-bot:latest .

# Push the image to Artifact Registry
docker push asia-northeast1-docker.pkg.dev/[PROJECT_ID]/discourse-bot-repo/discourse-bot:latest
```

### 5. Deploy with Terraform

From the terraform directory:

```bash
# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply
```

After successful deployment, Terraform will output the service URL where your bot is accessible.

## Environment Variables

The following environment variables are required and should be stored in Secret Manager:

- `DISCOURSE_API_KEY`: Your Discourse API key
- `DISCOURSE_BASE_URL`: Your Discourse instance URL
- `DISCOURSE_API_USERNAME`: Your Discourse username
- `APP_API_KEY`: Your application API key
- `GEMINI_API_KEY`: Your Google Gemini API key

## Infrastructure Components

The deployment creates the following resources:

- Artifact Registry Repository for Docker images
- Cloud Run service for the bot
- Secret Manager secrets for environment variables
- Necessary IAM permissions and API enablement

## Cleanup

To remove all created resources:

```bash
cd terraform
terraform destroy
```

Note: This will remove all resources created by Terraform, including the deployed service and secrets.
