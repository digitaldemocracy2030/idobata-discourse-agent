from typing import Dict, Any, Tuple
from src.clients.ai_summary_client import AISummaryClient
from src.clients.slack_client import SlackClient
from src.clients.discourse_client import DiscourseClient
from src.config.settings import POSTS_THRESHOLD, DRY_RUN_MODE

class TopicAnalysisService:
    def __init__(
        self,
        discourse_client: DiscourseClient,
        ai_summary_client: AISummaryClient,
        slack_client: SlackClient
    ):
        self.discourse_client = discourse_client
        self.bluemo_client = bluemo_client
        self.slack_client = slack_client

    async def _create_or_get_project(self, topic_id: int, title: str) -> str:
        """トピックに対応するBluemoプロジェクトを作成または取得"""
        try:
            # プロジェクト一覧を取得して既存プロジェクトを確認
            projects = self.bluemo_client.list_projects()
            for project in projects:
                if project.get("name") == f"topic_{topic_id}":
                    return project.get("id")

            # 新規プロジェクトを作成
            project = self.bluemo_client.create_project(
                name=f"topic_{topic_id}",
                description=title,
                extraction_topic="ディスカッションの論点と意見の分布"
            )
            return project.get("id")
        except Exception as e:
            raise Exception(f"Failed to create/get Bluemo project: {str(e)}")

    async def _import_posts_to_bluemo(self, project_id: str, topic_id: int) -> None:
        """トピックの投稿をBluemoにインポート"""
        try:
            # トピックの全投稿を取得
            posts = await self.discourse_client.get_topic_posts(topic_id)
            
            # コメントをBluemoの形式に変換
            comments = [
                {
                    "content": post.get("raw", ""),
                    "sourceType": "discourse",
                    "sourceUrl": f"/t/{topic_id}/{post.get('post_number')}"
                }
                for post in posts
            ]
            
            # 一括インポート
            self.bluemo_client.bulk_import_comments(project_id, comments)
        except Exception as e:
            raise Exception(f"Failed to import posts to Bluemo: {str(e)}")

    async def analyze_topic(self, topic_id: int) -> Tuple[str, str]:
        """トピックを分析してBluemoで処理"""
        try:
            # トピックの基本情報を取得
            topic_info = await self.discourse_client.get_topic(topic_id)
            title = topic_info.get("title", "")

            # Bluemoプロジェクトを作成または取得
            project_id = await self._create_or_get_project(topic_id, title)

            # 投稿をBluemoにインポート
            await self._import_posts_to_bluemo(project_id, topic_id)

            # 論点を自動生成
            self.bluemo_client.generate_questions(project_id)

            # プロジェクト全体の分析を実行
            analysis = self.bluemo_client.get_project_analysis(
                project_id,
                force_regenerate=True
            )

            return project_id, analysis.get("content", "分析結果を取得できませんでした")

        except Exception as e:
            raise Exception(f"Failed to analyze topic: {str(e)}")

    async def analyze_topic_if_needed(self, topic_id: int) -> None:
        """投稿数をチェックし、閾値に達していれば分析を実行する"""
        try:
            # 投稿数を取得
            current_count = await self.discourse_client.get_topic_post_count(topic_id)
            
            # 投稿数をログ出力
            print(f"Topic {topic_id} post count: {current_count} (threshold: {POSTS_THRESHOLD})")
            
            # 投稿数が閾値に達しているかチェック
            if current_count > 0 and current_count % POSTS_THRESHOLD == 0:
                # 分析を実行
                project_id, analysis_result = await self.analyze_topic(topic_id)
                
                if DRY_RUN_MODE:
                    # dry runモードの場合、Discourseへの投稿はスキップしてSlackのみに通知
                    await self.slack_client.send_notification(
                        f"[レビュー待ち] トピック {topic_id} の分析が完了しました。\n"
                        f"プロジェクトID: {project_id}\n"
                        f"内容: {analysis_result}\n"
                        f"投稿数: {current_count}\n"
                        f"※チームのレビュー後にDiscourseへ投稿されます"
                    )
                else:
                    # 通常モードの場合は分析結果を投稿
                    await self.discourse_client.post_analysis_result(
                        topic_id,
                        analysis_result,
                        project_id
                    )
                    
                    # Slackに通知
                    await self.slack_client.send_notification(
                        f"トピック {topic_id} の分析が完了しました。\n"
                        f"プロジェクトID: {project_id}\n"
                        f"内容: {analysis_result}\n"
                        f"投稿数: {current_count}"
                    )
        
        except Exception as e:
            error_message = f"Error analyzing topic {topic_id}: {str(e)}"
            print(error_message)
            # エラーをSlackに通知
            await self.slack_client.send_notification(
                f"トピック {topic_id} の分析中にエラーが発生しました：{str(e)}"
            )