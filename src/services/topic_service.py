from typing import Dict, Any, List, Tuple
from fastapi import HTTPException

from src.clients.discourse_client import DiscourseClient
from src.services.moderation import ModerationService
from src.services.vector_search import VectorSearchService
from src.models.schemas import TopicCreate, TopicSimilarityResponse

class TopicService:
    def __init__(
        self,
        discourse_client: DiscourseClient,
        moderation_service: ModerationService,
        vector_search_service: VectorSearchService
    ):
        self.discourse_client = discourse_client
        self.moderation_service = moderation_service
        self.vector_search_service = vector_search_service

    async def list_categories(self) -> List[Dict[str, Any]]:
        """利用可能なカテゴリーの一覧を取得"""
        try:
            return await self.discourse_client.get_categories()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch categories: {str(e)}"
            )

    async def create_topic(self, topic: TopicCreate) -> Dict[str, Any]:
        """新しいトピックを作成"""
        # コンテンツの適切性をチェック
        is_appropriate, explanation = await self.moderation_service.check_content_appropriateness(topic.content)
        if not is_appropriate:
            raise HTTPException(
                status_code=400,
                detail=f"Inappropriate content: {explanation}"
            )

        # 既存のトピックとの類似性をチェック
        recent_topics = await self.discourse_client.get_recent_topics()
        
        # ベクトル検索による類似性チェック
        is_duplicate_vector, explanation_vector, similar_topic_id_vector = (
            await self.vector_search_service.check_topic_similarity(topic.title, topic.content)
        )
        
        # Geminiによる類似性チェック
        is_duplicate_text, explanation_text, similar_topic_id_text = (
            await self.moderation_service.check_topic_similarity(topic.content, recent_topics)
        )
        
        # どちらかの方法で重複が検出された場合
        if is_duplicate_vector or is_duplicate_text:
            similar_topic_id = similar_topic_id_vector or similar_topic_id_text
            explanation = explanation_vector if is_duplicate_vector else explanation_text
            raise HTTPException(
                status_code=400,
                detail=f"Similar topic found: {explanation}. Similar topic ID: {similar_topic_id}"
            )

        try:
            # トピックを作成
            result = await self.discourse_client.create_topic(
                title=topic.title,
                content=topic.content,
                category_id=topic.category_id
            )
            
            # ベクトル検索インデックスに追加
            if result and 'topic_id' in result:
                await self.vector_search_service.index_topic(
                    result['topic_id'],
                    topic.title,
                    topic.content
                )
            
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create topic: {str(e)}"
            )
