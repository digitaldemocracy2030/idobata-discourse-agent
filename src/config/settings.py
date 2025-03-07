import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API configuration
API_KEY_NAME = "X-API-Key"

# Debug configuration
DRY_RUN_MODE = os.getenv("DRY_RUN_MODE", "false").lower() == "true"

# Slack configuration
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Discourse configuration
DISCOURSE_API_KEY = os.getenv("DISCOURSE_API_KEY")
DISCOURSE_BASE_URL = os.getenv("DISCOURSE_BASE_URL")
APP_API_KEY = os.getenv("APP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Vertex AI configuration
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "asia-northeast1")
VECTOR_SEARCH_INDEX_ID = os.getenv("VECTOR_SEARCH_INDEX_ID")
VECTOR_SEARCH_ENDPOINT_ID = os.getenv("VECTOR_SEARCH_ENDPOINT_ID")
EMBEDDING_ENDPOINT_ID = os.getenv("EMBEDDING_ENDPOINT_ID")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "textembedding-gecko@latest")

# Summary configuration
SUMMARY_API_KEY = os.getenv("SUMMARY_API_KEY")
SUMMARY_BASE_URL = os.getenv("SUMMARY_BASE_URL", "http://localhost:3001/api")
POSTS_THRESHOLD = 6  # 分析を実行する投稿数の閾値

# Constants
DELETION_MESSAGE = "このコメントはガイドラインを違反しているため削除されました"

# Validation
if not all([
    DISCOURSE_API_KEY,
    DISCOURSE_BASE_URL,
    APP_API_KEY,
    GEMINI_API_KEY,
    SUMMARY_API_KEY
]):
    raise ValueError("Missing required environment variables")

# Vector Search configuration
def get_vector_search_config():
    if all([
        VERTEX_PROJECT_ID,
        VERTEX_LOCATION,
        VECTOR_SEARCH_INDEX_ID,
        VECTOR_SEARCH_ENDPOINT_ID,
        EMBEDDING_ENDPOINT_ID
    ]):
        return {
            "enabled": True,
            "project_id": VERTEX_PROJECT_ID,
            "location": VERTEX_LOCATION,
            "index_id": VECTOR_SEARCH_INDEX_ID,
            "endpoint_id": VECTOR_SEARCH_ENDPOINT_ID,
            "embedding_endpoint_id": EMBEDDING_ENDPOINT_ID
        }
    return {"enabled": False}