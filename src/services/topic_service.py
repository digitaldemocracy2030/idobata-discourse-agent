from typing import Dict, Any, List
from fastapi import HTTPException
from bs4 import BeautifulSoup

from src.clients.discourse_client import DiscourseClient
from src.clients.slack_client import SlackClient
from src.services.moderation import ModerationService
from src.services.vector_search import VectorSearchService
from src.services.topic_analysis import TopicAnalysisService
from src.models.schemas import TopicCreate, TopicSimilarityResponse

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()

class TopicService:
    def __init__(
        self,
        discourse_client: DiscourseClient,
        moderation_service: ModerationService,
        vector_search_service: VectorSearchService,
        slack_client: SlackClient
    ):
        self.discourse_client = discourse_client
        self.moderation_service = moderation_service
        self.vector_search_service = vector_search_service
        self.slack_client = slack_client

    async def list_categories(self) -> List[Dict[str, Any]]:
        """利用可能なカテゴリーの一覧を取得"""
        try:
            return await self.discourse_client.get_categories()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch categories: {str(e)}"
            )

    async def check_topic_duplication(self, title: str, content: str) -> TopicSimilarityResponse:
        """トピックの重複をチェックする"""
        recent_topics = await self.discourse_client.get_recent_topics()
        
        # ベクトル検索による類似性チェック
        is_duplicate_vector, explanation_vector, similar_topic_id_vector = (
            await self.vector_search_service.check_topic_similarity(title, content)
        )
        
        # Geminiによる類似性チェック
        is_duplicate_text, explanation_text, similar_topic_id_text = (
            await self.moderation_service.check_topic_similarity(title, content, recent_topics)
        )
        # どちらかの方法で重複が検出された場合
        if is_duplicate_vector or is_duplicate_text:
            similar_topic_id = similar_topic_id_vector or similar_topic_id_text
            explanation = explanation_vector if is_duplicate_vector else explanation_text
            
            # 既存トピックの内容を取得
            try:
                existing_topic = await self.discourse_client.get_topic(similar_topic_id)
                existing_title = existing_topic.get('title', 'タイトル不明')
                existing_content = extract_text(existing_topic.get('post_stream', {}).get('posts', [{}])[0].get('cooked', '内容不明'))
                
                # 重複検出時のSlackメッセージを送信
                message = (
                    f"⚠類似したトピックが検出されました"
                    f"*新規トピック*\n"
                    f"タイトル: {title}\n"
                    f"内容:\n```\n{content}\n```\n\n"
                    f"*既存トピック*\n"
                    f"タイトル: {existing_title}\n"
                    f"内容:\n```\n{existing_content}\n```\n\n"
                    f"*類似度*: {explanation}\n"
                    f"*類似トピックID*: {similar_topic_id}"
                )
                print(f"Duplicated topic found")
                await self.slack_client.send_notification(message)
            except Exception as e:
                print(f"Failed to fetch existing topic details: {str(e)}")
            
            return TopicSimilarityResponse(
                is_duplicate=True,
                explanation=explanation,
                similar_topic_id=similar_topic_id
            )
        
        print(f"Not duplicated")
        return TopicSimilarityResponse(
            is_duplicate=False,
            explanation="",
            similar_topic_id=None
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

        # 重複チェック
        similarity_result = await self.check_topic_duplication(topic.title, topic.content)
        if similarity_result.is_duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Similar topic found: {similarity_result.explanation}. Similar topic ID: {similarity_result.similar_topic_id}"
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
