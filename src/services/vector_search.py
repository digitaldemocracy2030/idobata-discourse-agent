from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine import MatchingEngineIndex, MatchingEngineIndexEndpoint
import vertexai
from vertexai.language_models import TextEmbeddingModel
from typing import Dict, Any, Tuple
import json

from src.config import settings

class VectorSearchService:
    def __init__(self):
        self.config = settings.get_vector_search_config()
        self.use_vector_search = self.config["enabled"]
        
        if self.use_vector_search:
            vertexai.init(
                project=self.config["project_id"],
                location=self.config["location"]
            )
            try:
                self.vector_search_index = MatchingEngineIndex(
                    index_name=self.config["index_id"]
                )
                self.vector_search_endpoint = MatchingEngineIndexEndpoint(
                    index_endpoint_name=self.config["endpoint_id"]
                )
                self.embedding_model = TextEmbeddingModel.from_pretrained("text-multilingual-embedding-002")
                print(f"Vector Search initialized successfully with index {self.config['index_id']}")
            except Exception as e:
                print(f"Failed to initialize Vector Search: {str(e)}")
                self.use_vector_search = False

    async def get_embeddings(self, text: str) -> list[float]:
        """テキストの埋め込みベクトルを取得"""
        embeddings = self.embedding_model.get_embeddings([text])
        return embeddings[0].values

    async def index_topic(self, topic_id: int, title: str, content: str) -> bool:
        """トピックをベクトルインデックスに追加"""
        if not self.use_vector_search:
            return False

        try:
            combined_text = f"{title}\n{content}"
            embedding = await self.get_embeddings(combined_text)
            
            # トピックをインデックスに追加
            self.vector_search_index.upsert_embeddings(
                embeddings=[embedding],
                ids=[str(topic_id)]
            )
            return True
        except Exception as e:
            print(f"Failed to index topic: {str(e)}")
            return False

    async def check_topic_similarity(
        self, 
        new_title: str, 
        new_content: str, 
        threshold: float = 0.85
    ) -> Tuple[bool, str, int | None]:
        """埋め込みベクトルを使用してトピックの類似性をチェック"""
        if not self.use_vector_search:
            return False, "Vector search is not enabled", None

        try:
            combined_text = f"{new_title}\n{new_content}"
            query_embedding = await self.get_embeddings(combined_text)
            
            # 類似度検索を実行
            response = self.vector_search_endpoint.find_neighbors(
                deployed_index_id=self.config["index_id"],
                queries=[query_embedding],
                num_neighbors=1
            )
            
            if not response.nearest_neighbors:
                return False, "No similar topics found", None
            
            neighbor = response.nearest_neighbors[0][0]
            similarity_score = neighbor.distance
            
            if similarity_score >= threshold:
                # IDから数字部分のみを抽出して変換
                topic_id = ''.join(filter(str.isdigit, neighbor.id))
                return True, f"Similar topic found with score {similarity_score}", int(topic_id) if topic_id else None
            
            return False, f"No similar topics found above threshold {threshold}", None
            
        except Exception as e:
            print(f"Error in similarity check: {str(e)}")
            return False, f"Error in similarity check: {str(e)}", None
