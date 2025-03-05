from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security.api_key import APIKeyHeader
from typing import List, Dict, Any

from src.config import settings
from src.models.schemas import TopicCreate, WebhookPayload
from src.services.topic_service import TopicService
from src.services.moderation import ModerationService
from src.clients.discourse_client import DiscourseClient
from src.services.vector_search import VectorSearchService
from src.clients.slack_client import SlackClient

router = APIRouter()

# Configure API key authentication
api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=True)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """APIキーを検証する"""
    if api_key != settings.APP_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

async def get_services():
    """サービスのインスタンスを取得する"""
    discourse_client = DiscourseClient(settings.DISCOURSE_BASE_URL, settings.DISCOURSE_API_KEY)
    moderation_service = ModerationService(discourse_client)
    vector_search_service = VectorSearchService()
    slack_client = SlackClient()
    topic_service = TopicService(discourse_client, moderation_service, vector_search_service, slack_client)
    return topic_service, moderation_service

@router.get("/categories", response_model=List[Dict[str, Any]])
async def list_categories(
    api_key: str = Depends(verify_api_key),
    services: tuple[TopicService, ModerationService] = Depends(get_services)
):
    """利用可能なカテゴリーの一覧を取得するエンドポイント"""
    topic_service, _ = services
    return await topic_service.list_categories()

@router.post("/topics")
async def create_topic(
    topic: TopicCreate,
    api_key: str = Depends(verify_api_key),
    services: tuple[TopicService, ModerationService] = Depends(get_services)
):
    """新しいトピックを作成するエンドポイント"""
    topic_service, _ = services
    return await topic_service.create_topic(topic)

@router.post("/webhook")
async def webhook_handler(
    request: Request,
    payload: WebhookPayload,
    services: tuple[TopicService, ModerationService] = Depends(get_services)
):
    """Discourseからのwebhookを処理するエンドポイント"""
    topic_service, moderation_service = services
    
    # Webhookのシグネチャを検証（必要に応じて実装）
    # 投稿の重複チェック
    if 'title' in payload.post and 'raw' in payload.post:
        similarity_result = await topic_service.check_topic_duplication(
            title=payload.post['title'],
            content=payload.post['raw']
        )
    
    # 投稿のモデレーションを非同期で処理
    await moderation_service.handle_moderation(payload.post)
    
    # 投稿をVertexAIにインデックス
    if 'topic_id' in payload.post and 'title' in payload.post and 'raw' in payload.post:
        await topic_service.vector_search_service.index_topic(
            topic_id=payload.post['topic_id'],
            title=payload.post['title'],
            content=payload.post['raw']
        )
    
    return {"status": "processing"}
