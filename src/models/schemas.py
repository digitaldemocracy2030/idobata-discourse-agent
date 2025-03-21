from pydantic import BaseModel
from typing import Dict, Any

class TopicCreate(BaseModel):
    """新しいトピックを作成するためのスキーマ"""
    title: str
    content: str
    category_id: int

class WebhookPayload(BaseModel):
    """Discourseからのwebhookペイロードのスキーマ"""
    post: Dict[str, Any]

class TopicSimilarityResponse(BaseModel):
    """トピックの類似性チェック結果のスキーマ"""
    is_duplicate: bool
    explanation: str
    similar_topic_id: int | None
