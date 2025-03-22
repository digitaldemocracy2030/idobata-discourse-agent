from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from typing import List, Dict, Any
import hashlib
import hmac

from src.config import settings
from src.models.schemas import TopicCreate, WebhookPayload
from src.services.topic_service import TopicService
from src.services.moderation import ModerationService
from src.services.topic_analysis import TopicAnalysisService
from src.clients.discourse_client import DiscourseClient
from src.services.vector_search import VectorSearchService
from src.clients.slack_client import SlackClient
from src.clients.summary_client import SummaryClient

router = APIRouter()

# Configure API key authentication
api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=True)

async def verify_api_key(request: Request, api_key: str):
    """APIキーを検証する"""
    raw_body = await request.body()
    secret = settings.APP_API_KEY
    computed_hash = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if hmac.compare_digest(computed_hash, api_key):
        print("署名検証成功：正規のDiscourse Webhookです")
    else:
        print("署名検証失敗：シークレットが違うか偽のリクエストです")
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )

async def get_services():
    """サービスのインスタンスを取得する"""
    discourse_client = DiscourseClient(settings.DISCOURSE_BASE_URL, settings.DISCOURSE_API_KEY)
    moderation_service = ModerationService(discourse_client)
    vector_search_service = VectorSearchService()
    slack_client = SlackClient()
    summary_client = SummaryClient(settings.SUMMARY_BASE_URL, settings.SUMMARY_API_KEY)
    # 各サービスを初期化
    topic_service = TopicService(
        discourse_client=discourse_client,
        moderation_service=moderation_service,
        vector_search_service=vector_search_service,
        slack_client=slack_client
    )
    topic_analysis_service = TopicAnalysisService(
        discourse_client=discourse_client,
        summary_client=summary_client,
        slack_client=slack_client
    )
    return topic_service, moderation_service, topic_analysis_service

@router.post("/webhook")
async def webhook_handler(
    request: Request,
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(api_key_header),
    services: tuple[TopicService, ModerationService, TopicAnalysisService] = Depends(get_services)
):
    await verify_api_key(request=request, api_key=api_key)
    """Discourseからのwebhookを処理するエンドポイント"""
    topic_service, moderation_service, topic_analysis_service = services
    
    # Webhookのシグネチャを検証（必要に応じて実装）
    # 投稿の重複チェック
    if 'title' in payload.post and 'raw' in payload.post:
        background_tasks.add_task(
            topic_service.check_topic_duplication,
            title=payload.post['title'],
            content=payload.post['raw']
        )
    
    # 投稿のモデレーションを非同期で処理
    await moderation_service.handle_moderation(payload.post)
    
    # 投稿をVertexAIにインデックス
    if 'topic_id' in payload.post and 'title' in payload.post and 'raw' in payload.post:
        background_tasks.add_task(
            topic_service.vector_search_service.index_topic,
            topic_id=payload.post['topic_id'],
            title=payload.post['title'],
            content=payload.post['raw']
        )
    
    # 投稿数をチェックし、必要に応じて分析を実行（titleが存在しない場合のみ）
    if 'topic_id' in payload.post and 'title' not in payload.post:
        force_analysis = "aisum" in payload.post['raw']
        background_tasks.add_task(
            topic_analysis_service.analyze_topic_if_needed,
            payload.post['topic_id'], force_analysis
        )

    return {"status": "processing"}
