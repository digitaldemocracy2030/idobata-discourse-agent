# このプロジェクトについて
- オンライン上の政策熟議PFを構築する「いどばたPJ」のリポジトリです。
    - PJ全体の意義・意図は[こちらのスライド](https://docs.google.com/presentation/d/1etZjpfj9v59NW5REC4bOv4QwVq_ApZMFDMQZqPDHb8Q/edit#slide=id.g339b8863127_0_989)のP20からP50を参照ください。
- 本PJは、以下に示す複数のモジュールで構築されています
    - [idobata-agent](https://github.com/takahiroanno2024/idobata-agent/) (フォーラムの投稿に反応し、モデレーションを行うモジュール)
    - [idobata-analyst](https://github.com/takahiroanno2024/idobata-analyst/)（フォーラムやSNSの投稿を分析し、レポートを作成するモジュール）
    - [idobata-infra](https://github.com/takahiroanno2024/idobata-infra/)（フォーラムのインフラを構築する設定）
    - [idobata-sns-agent](https://github.com/takahiroanno2024/idobata-sns-agent/)（SNSの投稿を収集したり、投稿を行うためのモジュール）

## 開発への参加方法について

- 本PJは、開発者の方からのコントリビュートを募集しています！ぜひ一緒に日本のデジタル民主主義を進めましょう！
- プロジェクトのタスクは[GitHub Project](https://github.com/orgs/takahiroanno2024/projects/4)で管理されています。
    - [good first issueタグ](https://github.com/orgs/takahiroanno2024/projects/4/views/1?filterQuery=good+first+issue)がついたIssueは特に取り組みやすくなっています！
- プロジェクトについてのやりとりは、原則[デジタル民主主義2030のSlackの「開発_いどばた」チャンネル](https://w1740803485-clv347541.slack.com/archives/C08FF5MM59C)までお願いします
- コントリビュートにあたっては、本リポジトリのrootディレクトリにあるCLA.md（コントリビューターライセンス）へ同意が必要です。
    - PRのテンプレートに従ってください


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

## テスト

### テストの概要

プロジェクトには以下の種類のテストが含まれています：

- 統合テスト (`tests/integration_test.py`)
- モデレーションサービステスト (`tests/test_moderation_service.py`)
- トピックサービステスト (`tests/test_topic_service.py`)
- ベクター検索サービステスト (`tests/test_vector_search_service.py`)

また、`tests/false_positive`ディレクトリには、モデレーションシステムの誤検知テスト用のサンプルデータが含まれています。

### テストの実行方法

1. テスト依存関係のインストール:
```bash
pip install -r requirements.txt
```

2. すべてのテストを実行:
```bash
pytest
```

3. 特定のテストファイルを実行:
```bash
pytest tests/test_moderation_service.py
```

4. テストカバレッジレポートの生成:
```bash
pytest --cov=src tests/
```

カバレッジレポートはHTML形式でも生成できます：
```bash
pytest --cov=src --cov-report=html tests/
```

### テストデータ

`tests/false_positive`ディレクトリには、モデレーションシステムの誤検知を防ぐためのテストケースが含まれています。これらのテストケースは、正常なコンテンツが誤ってフラグされないことを確認するために使用されます。

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
