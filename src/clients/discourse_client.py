import httpx
from typing import Dict, Any, List, Tuple

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

    async def get_topic(self, topic_id: int) -> Dict[str, Any]:
        """特定のトピックの詳細を取得する"""
        url = f"{self.base_url}/t/{topic_id}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def get_topic_post_count(self, topic_id: int) -> int:
        """トピックの投稿数を取得する"""
        topic_data = await self.get_topic(topic_id)
        return topic_data.get('posts_count', 0)

    async def analyze_topic(self, topic_id: int, api_key: str) -> Tuple[str, str]:
        """分析APIを使用してトピックを分析する"""
        topic_data = await self.get_topic(topic_id)
        posts = topic_data.get('post_stream', {}).get('posts', [])
        
        # 分析APIのベースURL
        analysis_api_url = "http://localhost:3001/api"
        
        # プロジェクトを作成
        async with httpx.AsyncClient() as client:
            headers = {'x-api-key': api_key}
            project_data = {
                'name': f'Topic Analysis - {topic_id}',
                'description': f'Analysis for topic {topic_id}',
                'extractionTopic': topic_data.get('title', '')
            }
            project_response = await client.post(
                f"{analysis_api_url}/projects",
                headers=headers,
                json=project_data
            )
            project_response.raise_for_status()
            project_id = project_response.json().get('id')

            # コメントを一括インポート
            comments = []
            for post in posts:
                comments.append({
                    'content': post.get('cooked', ''),
                    'sourceType': 'discourse',
                    'sourceUrl': f"{self.base_url}/t/{topic_id}/{post.get('post_number')}"
                })
            
            await client.post(
                f"{analysis_api_url}/projects/{project_id}/comments/bulk",
                headers=headers,
                json={'comments': comments}
            )

            # 分析レポートを取得
            analysis_response = await client.get(
                f"{analysis_api_url}/projects/{project_id}/analysis",
                headers=headers
            )
            analysis_response.raise_for_status()
            
            return project_id, analysis_response.json()

    async def post_analysis_result(self, topic_id: int, analysis_result: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """分析結果をトピックに投稿する"""
        content = f"""
# 投稿分析レポート

このレポートは自動生成された分析結果です。

## 分析結果の詳細
{analysis_result.get('summary', '分析結果なし')}

## 詳細な分析結果の確認
完全な分析結果は以下のURLで確認できます：
http://localhost:3001/projects/{project_id}

---
*この分析は自動で実行されました*
        """
        
        return await self.create_reply(topic_id, content)
