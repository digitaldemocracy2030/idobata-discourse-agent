import aiohttp
from src.config import settings

class SlackClient:
    def __init__(self):
        self.webhook_url = settings.SLACK_WEBHOOK_URL

    async def send_notification(self, message: str) -> None:
        """
        Slackにメッセージを送信する
        """
        if not self.webhook_url:
            print("Slack webhook URL is not configured")
            return

        async with aiohttp.ClientSession() as session:
            try:
                # メッセージタイプに基づいてヘッダーを変更
                header = "🚫 *不適切なコンテンツが検出されました*" if "不適切" in message else "⚠️ *類似したトピックが検出されました*"
                
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