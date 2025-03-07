import aiohttp
from src.config import settings

class SlackClient:
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL

    def _determine_header(self, message: str) -> str:
        """
        メッセージの内容を解析して適切なヘッダーを決定する
        """
        message_lower = message.lower()
        
        # トピック分析関連の通知
        if "[レビュー待ち]" in message:
            return "👀 *トピック分析レビュー待ち*"
        if "分析が完了しました" in message:
            return "📊 *トピック分析が完了しました*"
        if "分析中にエラーが発生" in message:
            return "❌ *トピック分析エラー*"
            
        # モデレーション関連の通知
        if "hate speech" in message_lower or "ヘイトスピーチ" in message_lower:
            return "🤬 *ヘイトスピーチが検出されました*"
        if "explicit content" in message_lower or "露骨" in message_lower:
            return "🔞 *露骨なコンテンツが検出されました*"
        if "harassment" in message_lower or "ハラスメント" in message_lower:
            return "😡 *ハラスメントが検出されました*"
        if "spam" in message_lower or "スパム" in message_lower:
            return "🤖 *スパムが検出されました*"
        if "similar" in message_lower or "類似" in message_lower or "duplicate" in message_lower:
            return "⚠️ *類似したトピックが検出されました*"
            
        # 論点分析関連の通知
        if "論点" in message or "意見の分布" in message:
            return "💭 *新しい論点が検出されました*"
        if "ディスカッション" in message:
            return "🗣️ *ディスカッション分析結果*"
            
        # その他の不適切なコンテンツ
        return "🚫 *不適切なコンテンツが検出されました*"

    async def send_notification(self, message: str) -> None:
        """
        Slackにメッセージを送信する
        """
        if not self.webhook_url:
            print("Slack webhook URL is not configured")
            return

        async with aiohttp.ClientSession() as session:
            try:
                # メッセージの内容を解析してヘッダーを決定
                header = self._determine_header(message)
                
                payload = {
                    "text": message,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": header
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": message
                            }
                        }
                    ]
                }
                
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        print(f"Failed to send Slack notification: {response.status}")
                        
            except Exception as e:
                print(f"Error sending Slack notification: {str(e)}")