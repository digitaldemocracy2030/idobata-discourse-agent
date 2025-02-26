import httpx
from typing import Dict, Any, List

class DiscourseClient:
    """Discourse APIとの通信を担当するクライアントクラス"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Api-Key': api_key,
            'Api-Username': 'system',
            'Content-Type': 'application/json'
        }

    async def create_topic(self, title: str, content: str, category_id: int) -> Dict[str, Any]:
        """新しいトピックを作成する"""
        url = f"{self.base_url}/posts.json"
        data = {
            'title': title,
            'raw': content,
            'category': category_id,
            'archetype': 'regular'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    async def get_categories(self) -> List[Dict[str, Any]]:
        """利用可能なカテゴリーの一覧を取得する"""
        url = f"{self.base_url}/categories.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()['category_list']['categories']

    async def delete_post(self, post_id: int) -> bool:
        """投稿を削除する"""
        url = f"{self.base_url}/posts/{post_id}"
        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers)
            return response.status_code == 200

    async def create_reply(self, topic_id: int, content: str) -> Dict[str, Any]:
        """トピックに返信を作成する"""
        url = f"{self.base_url}/posts.json"
        data = {
            'topic_id': topic_id,
            'raw': content
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    async def get_recent_topics(self, limit: int = 20) -> List[Dict[str, Any]]:
        """最近のトピックを取得する"""
        url = f"{self.base_url}/latest.json?no_definitions=true&page=0&per_page={limit}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()['topic_list']['topics']
