import google.generativeai as genai
from typing import Tuple, Dict, Any
import traceback

from src.config import settings
from src.clients.discourse_client import DiscourseClient
from src.clients.slack_client import SlackClient
from src.utils.utils import remove_urls, remove_html_tags

class ModerationService:
    def __init__(self, discourse_client: DiscourseClient):
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self.discourse_client = discourse_client
        self.slack_client = SlackClient()

    async def check_content_appropriateness(self, content: str) -> Tuple[bool, str]:
        """
        コンテンツの適切性をGemini APIを使用してチェック
        Returns: (is_appropriate, explanation)
        """
        # コンテンツからURLとHTMLタグを削除
        cleaned_content = remove_html_tags(remove_urls(content))
        prompt = f"""
        Please analyze the following content and determine if it is appropriate for a public forum.
        Consider factors like hate speech, explicit content, harassment, spam, or other inappropriate content.
        Content to analyze: {cleaned_content}
        
        Respond with a clear YES if the content is appropriate, or NO if it's inappropriate.
        Also provide a brief explanation of your decision.
        """
        
        try:
            print("\nAnalyzing content with Gemini API:")
            print(f"Content: {content}")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().lower()
            is_appropriate = response_text.startswith('yes')
            explanation = ' '.join(response_text.split()[1:])  # Remove YES/NO and get explanation
            print(f"Gemini Response: {response_text}")
            return is_appropriate, explanation
        except Exception as e:
            error_msg = f"Error in content appropriateness check: {str(e)}"
            print(error_msg)
            return True, error_msg  # デフォルトで許可する

    async def deep_similarity_check(self, title: str, content: str, candidate_topics: list[Dict[str, Any]]) -> tuple[bool, str, int | None]:
        """
        Gemini APIを使用して新しいコンテンツと類似候補トピックの詳細な類似性をチェック
        Args:
            title: 新規トピックのタイトル
            content: 新規トピックの内容
            candidate_topics: vector_searchとrecentから得られた類似候補トピックのリスト
        Returns:
            (is_duplicate, explanation, similar_topic_id)
        """
        if not candidate_topics:
            return False, "No topics to compare", None

        # 類似候補トピックの情報を整形
        topics_text = "\n".join([
            f"Topic {t['id']}: {t.get('title', '')} - {t.get('excerpt', '')}"
            for t in candidate_topics
        ])
        # 新しいトピックからURLを削除
        new_text = f"Topic : {title} - {content}"

        prompt = f"""
        Compare the following new content with the candidate similar topics and determine if any of them are duplicates or very similar.
        Consider the following aspects:
        1. Core topic or question being addressed
        2. Main points or arguments being made
        3. Purpose or intent of the content
        4. Level of detail and specificity

        New content:
        {new_text}

        Candidate similar topics:
        {topics_text}

        Respond with:
        1. YES if you find a duplicate/very similar topic, or NO if the content is sufficiently different
        2. A detailed explanation of your decision, highlighting key similarities or differences
        3. If YES, provide the ID of the most similar topic. If NO, write 0

        Format your response exactly as: YES/NO | Explanation | Topic ID
        """

        try:
            print("\nPerforming deep similarity check with Gemini API:")
            print(f"New content: {content}")
            print(f"Number of candidate topics: {len(candidate_topics)}")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse response
            parts = response_text.split('|')
            if len(parts) != 3:
                return False, "Invalid response format from AI", None
                
            is_duplicate = parts[0].strip().lower() == 'yes'
            explanation = parts[1].strip()
            topic_id = int(parts[2].strip()) if is_duplicate else None
            
            print(f"Similarity check result: {is_duplicate}, Topic ID: {topic_id}")
            return is_duplicate, explanation, topic_id

        except Exception as e:
            error_msg = f"Error in deep similarity check: {str(e)}"
            print(error_msg)
            return False, error_msg, None

    async def handle_moderation(self, post: Dict[str, Any]) -> None:
        """
        投稿のモデレーションを非同期で処理
        """
        try:
            post_id = post.get('id')
            content = post.get('raw', '')
            
            if not post_id or not content:
                print("Invalid post data")
                return
            
            # コンテンツの適切性をチェック
            is_appropriate, explanation = await self.check_content_appropriateness(content)
            
            if not is_appropriate:
                print(f"Inappropriate content detected in post {post_id}: {explanation}")
# Slackに通知
                notification_message = f"""
投稿ID: {post_id}
コンテンツ: {content}
理由: {explanation}
"""
                await self.slack_client.send_notification(notification_message)
                """
                # 投稿を削除
                await self.discourse_client.delete_post(post_id)
                # 削除の理由を説明するリプライを投稿
                topic_id = post.get('topic_id')
                if topic_id:
                    await self.discourse_client.create_reply(
                        topic_id=topic_id,
                        content=settings.DELETION_MESSAGE
                    )
                """
            
        except Exception as e:
            print(f"Error in moderation handler: {str(e)}")
            traceback.print_exc()
