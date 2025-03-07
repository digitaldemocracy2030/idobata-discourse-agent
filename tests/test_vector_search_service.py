import pytest
from unittest.mock import Mock, AsyncMock, patch
import google.generativeai as genai
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import MatchingEngineIndexEndpoint

from src.services.vector_search import VectorSearchService

@pytest.fixture
def mock_vector_search_config():
    return {
        "enabled": True,
        "project_id": "test-project",
        "location": "us-central1",
        "index_id": "test-index",
        "endpoint_id": "test-endpoint"
    }

@pytest.mark.asyncio
async def test_get_embeddings(mock_vector_search_config):
    with patch('src.services.vector_search.settings.get_vector_search_config', return_value=mock_vector_search_config):
        service = VectorSearchService()
        
        # Geminiのレスポンスをモック
        mock_response = Mock()
        mock_response.embedding = [0.1, 0.2, 0.3]
        mock_model = Mock()
        mock_model.generate_content = AsyncMock(return_value=mock_response)
        
        with patch('google.generativeai.GenerativeModel', return_value=mock_model):
            # テスト実行
            embeddings = await service.get_embeddings("Test content")
            
            # 検証
            assert embeddings == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_index_topic_success(mock_vector_search_config):
    with patch('src.services.vector_search.settings.get_vector_search_config', return_value=mock_vector_search_config):
        service = VectorSearchService()
        service.use_vector_search = True
        
        # モックの設定
        mock_embeddings = [0.1, 0.2, 0.3]
        service.get_embeddings = AsyncMock(return_value=mock_embeddings)
        service.vector_search_index = Mock()
        
        # テスト実行
        result = await service.index_topic(
            topic_id=123,
            title="Test Title",
            content="Test Content"
        )
        
        # 検証
        assert result is True
        service.vector_search_index.upsert_embeddings.assert_called_once_with(
            embeddings=[mock_embeddings],
            ids=["123"]
        )

@pytest.mark.asyncio
async def test_check_topic_similarity_match(mock_vector_search_config):
    with patch('src.services.vector_search.settings.get_vector_search_config', return_value=mock_vector_search_config):
        service = VectorSearchService()
        service.use_vector_search = True
        
        # モックの設定
        mock_embeddings = [0.1, 0.2, 0.3]
        service.get_embeddings = AsyncMock(return_value=mock_embeddings)
        
        # MatchingEngineIndexEndpointのレスポンスをモック
        mock_neighbor = Mock()
        mock_neighbor.distance = 0.9  # 高い類似度
        mock_neighbor.id = "123"
        
        mock_response = Mock()
        mock_response.nearest_neighbors = [[mock_neighbor]]
        
        service.vector_search_endpoint = Mock()
        service.vector_search_endpoint.find_neighbors = Mock(return_value=mock_response)
        service.config = mock_vector_search_config
        
        # テスト実行
        is_similar, explanation, topic_id = await service.check_topic_similarity(
            new_title="Test Title",
            new_content="Test Content",
            threshold=0.85
        )
        
        # 検証
        assert is_similar is True
        assert topic_id == 123
        assert "0.9" in explanation

@pytest.mark.asyncio
async def test_check_topic_similarity_no_match(mock_vector_search_config):
    with patch('src.services.vector_search.settings.get_vector_search_config', return_value=mock_vector_search_config):
        service = VectorSearchService()
        service.use_vector_search = True
        
        # モックの設定
        mock_embeddings = [0.1, 0.2, 0.3]
        service.get_embeddings = AsyncMock(return_value=mock_embeddings)
        
        # MatchingEngineIndexEndpointのレスポンスをモック
        mock_neighbor = Mock()
        mock_neighbor.distance = 0.7  # 低い類似度
        mock_neighbor.id = "123"
        
        mock_response = Mock()
        mock_response.nearest_neighbors = [[mock_neighbor]]
        
        service.vector_search_endpoint = Mock()
        service.vector_search_endpoint.find_neighbors = Mock(return_value=mock_response)
        service.config = mock_vector_search_config
        
        # テスト実行
        is_similar, explanation, topic_id = await service.check_topic_similarity(
            new_title="Test Title",
            new_content="Test Content",
            threshold=0.85
        )
        
        # 検証
        assert is_similar is False
        assert topic_id is None
        assert "0.85" in explanation
