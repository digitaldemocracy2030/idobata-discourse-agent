import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
import google.generativeai as genai

from src.main import app
from src.clients.discourse_client import DiscourseClient
from src.services.moderation import ModerationService
from src.services.vector_search import VectorSearchService
from src.services.topic_service import TopicService

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_discourse_client():
    client = Mock(spec=DiscourseClient)
    # AsyncMockを使用してasyncメソッドをモック化
    client.create_topic = AsyncMock()
    client.get_categories = AsyncMock()
    client.delete_post = AsyncMock()
    client.create_reply = AsyncMock()
    client.get_recent_topics = AsyncMock()
    return client

@pytest.fixture
def mock_moderation_service(mock_discourse_client):
    service = Mock(spec=ModerationService)
    service.check_content_appropriateness = AsyncMock()
    service.check_topic_similarity = AsyncMock()
    service.handle_moderation = AsyncMock()
    return service

@pytest.fixture
def mock_vector_search_service():
    service = Mock(spec=VectorSearchService)
    service.get_embeddings = AsyncMock()
    service.index_topic = AsyncMock()
    service.check_topic_similarity = AsyncMock()
    return service

@pytest.fixture
def mock_topic_service(mock_discourse_client, mock_moderation_service, mock_vector_search_service):
    return TopicService(
        discourse_client=mock_discourse_client,
        moderation_service=mock_moderation_service,
        vector_search_service=mock_vector_search_service
    )
