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
        # 最近のトピックを取得
        recent_topics = await self.discourse_client.get_recent_topics()
        
        # ベクトル検索による類似性チェック
        is_similar_vector, explanation_vector, similar_topic_id_vector = (
            await self.vector_search_service.check_topic_similarity(title, content)
        )

        # 候補トピックのリストを作成
        candidate_topics = []
        
        # ベクトル検索で類似トピックが見つかった場合、それを候補に追加
        if is_similar_vector and similar_topic_id_vector:
            try:
                vector_topic = await self.discourse_client.get_topic(similar_topic_id_vector)
                if vector_topic:
                    candidate_topics.append(vector_topic)
            except Exception as e:
                print(f"Failed to fetch vector search topic: {str(e)}")

        # 最近のトピックから類似候補を追加
        candidate_topics.extend(recent_topics)

        # 重複を除去（同じIDのトピックが複数回含まれないように）
        unique_candidates = {topic['id']: topic for topic in candidate_topics}.values()
        
        # 言語モデルによる詳細な類似性チェック
        is_duplicate, explanation, similar_topic_id = (
            await self.moderation_service.deep_similarity_check(title, content, list(unique_candidates))
        )

        if is_duplicate and similar_topic_id:
            
            # 既存トピックの詳細を取得して通知
            try:
                existing_topic = await self.discourse_client.get_topic(similar_topic_id)
                existing_title = existing_topic.get('title', 'タイトル不明')
                existing_content = extract_text(existing_topic.get('post_stream', {}).get('posts', [{}])[0].get('cooked', '内容不明'))
                
                # 重複検出時のSlackメッセージを送信
                message = (
                    f"⚠類似したトピックが検出されました\n"
                    f"*新規トピック*\n"
                    f"タイトル: {title}\n"
                    f"内容:\n```\n{content}\n```\n\n"
                    f"*既存トピック*\n"
                    f"タイトル: {existing_title}\n"
                    f"内容:\n```\n{existing_content}\n```\n\n"
                    f"*分析結果*: {explanation}\n"
                    f"*類似トピックID*: {similar_topic_id}"
                )
                print(f"Duplicated topic found - ID: {similar_topic_id}")
                await self.slack_client.send_notification(message)
                
                return TopicSimilarityResponse(
                    is_duplicate=True,
                    explanation=explanation,
                    similar_topic_id=similar_topic_id
                )
            except Exception as e:
                print(f"Failed to fetch existing topic details: {str(e)}")
                # エラーが発生しても重複判定は維持
                return TopicSimilarityResponse(
                    is_duplicate=True,
                    explanation=explanation,
                    similar_topic_id=similar_topic_id
                )
        
        print(f"No similar topics found")
        return TopicSimilarityResponse(
            is_duplicate=False,
            explanation="No similar topics found",
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
