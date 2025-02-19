# Discourse Bot Deployment Guide

This guide explains how to deploy the Discourse Bot to Google Cloud Platform using Terraform and Cloud Run.

## Project Structure

```
.
├── .github/
│   └── workflows/          # GitHub Actions workflows
│       └── deploy.yml      # Deployment workflow
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

## Deployment Methods

You can deploy this application either manually or using GitHub Actions for CI/CD.

### Method 1: GitHub Actions (Recommended)

#### 1. Set up Workload Identity Federation

1. Create a Workload Identity Pool:
```bash
gcloud iam workload-identity-pools create "github-actions-pool" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

2. Create a Workload Identity Provider:
```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

3. Create a Service Account:
```bash
gcloud iam service-accounts create "github-actions-service-account" \
  --project="${PROJECT_ID}" \
  --display-name="GitHub Actions Service Account"
```

4. Grant necessary permissions:
```bash
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:github-actions-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:github-actions-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:github-actions-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

5. Allow the GitHub repository to impersonate the service account:
```bash
gcloud iam service-accounts add-iam-policy-binding "github-actions-service-account@${PROJECT_ID}.iam.gserviceaccount.com" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/${GITHUB_REPO}"
```

#### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `WIF_PROVIDER`: Workload Identity Provider resource name
- `WIF_SERVICE_ACCOUNT`: Service account email
- `DISCOURSE_API_KEY`: Your Discourse API key
- `DISCOURSE_API_USERNAME`: Your Discourse username
- `DISCOURSE_URL`: Your Discourse instance URL

### Method 2: Manual Deployment

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

## ローカル開発

### 環境のセットアップ

1. GCP認証の設定:
```bash
# GCPにログイン
gcloud auth login

# アプリケーションのデフォルト認証情報を設定
gcloud auth application-default login

# Artifact Registry用のDockerの認証を設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

2. `.env`ファイルを作成:
```bash
cp .env.example .env
```

3. `.env`ファイルを編集して必要な環境変数を設定

### Docker Composeでの実行

開発サーバーの起動:
```bash
docker-compose up
```

バックグラウンドで実行する場合:
```bash
docker-compose up -d
```

コンテナの停止:
```bash
docker-compose down
```

変更を反映させてリビルド:
```bash
docker-compose up --build
```
