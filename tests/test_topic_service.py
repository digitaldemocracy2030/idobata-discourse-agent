import pytest
from fastapi import HTTPException
from unittest.mock import Mock, AsyncMock

from src.services.topic_service import TopicService
from src.models.schemas import TopicCreate

@pytest.mark.asyncio
async def test_list_categories_success(mock_topic_service):
    # モックの設定
    expected_categories = [
        {"id": 1, "name": "Category 1"},
        {"id": 2, "name": "Category 2"}
    ]
    mock_topic_service.discourse_client.get_categories.return_value = expected_categories
    
    # テスト実行
    result = await mock_topic_service.list_categories()
    
    # 検証
    assert result == expected_categories
    mock_topic_service.discourse_client.get_categories.assert_called_once()

@pytest.mark.asyncio
async def test_list_categories_failure(mock_topic_service):
    # モックの設定
    mock_topic_service.discourse_client.get_categories.side_effect = Exception("API Error")
    
    # テスト実行とエラー検証
    with pytest.raises(HTTPException) as exc_info:
        await mock_topic_service.list_categories()
    
    assert exc_info.value.status_code == 500
    assert "Failed to fetch categories" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_topic_success(mock_topic_service):
    # モックの設定
    mock_topic_service.moderation_service.check_content_appropriateness.return_value = (True, "Appropriate")
    mock_topic_service.vector_search_service.check_topic_similarity.return_value = (False, "No duplicates", None)
    mock_topic_service.moderation_service.check_topic_similarity.return_value = (False, "No duplicates", None)
    mock_topic_service.discourse_client.get_recent_topics.return_value = []
    
    expected_result = {"topic_id": 123, "title": "Test Topic"}
    mock_topic_service.discourse_client.create_topic.return_value = expected_result
    mock_topic_service.vector_search_service.index_topic.return_value = True
    
    # テストデータ
    topic = TopicCreate(
        title="Test Topic",
        content="Test Content",
        category_id=1
    )
    
    # テスト実行
    result = await mock_topic_service.create_topic(topic)
    
    # 検証
    assert result == expected_result
    mock_topic_service.discourse_client.create_topic.assert_called_once_with(
        title="Test Topic",
        content="Test Content",
        category_id=1
    )
    mock_topic_service.vector_search_service.index_topic.assert_called_once()

@pytest.mark.asyncio
async def test_create_topic_inappropriate_content(mock_topic_service):
    # モックの設定
    mock_topic_service.moderation_service.check_content_appropriateness.return_value = (False, "Inappropriate content")
    
    # テストデータ
    topic = TopicCreate(
        title="Test Topic",
        content="Inappropriate Content",
        category_id=1
    )
    
    # テスト実行とエラー検証
    with pytest.raises(HTTPException) as exc_info:
        await mock_topic_service.create_topic(topic)
    
    assert exc_info.value.status_code == 400
    assert "Inappropriate content" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_create_topic_duplicate_found(mock_topic_service):
    # モックの設定
    mock_topic_service.moderation_service.check_content_appropriateness.return_value = (True, "Appropriate")
    mock_topic_service.vector_search_service.check_topic_similarity.return_value = (True, "Similar topic found", 456)
    mock_topic_service.moderation_service.check_topic_similarity.return_value = (False, "No duplicates", None)
    mock_topic_service.discourse_client.get_recent_topics.return_value = []
    
    # テストデータ
    topic = TopicCreate(
        title="Test Topic",
        content="Duplicate Content",
        category_id=1
    )
    
    # テスト実行とエラー検証
    with pytest.raises(HTTPException) as exc_info:
        await mock_topic_service.create_topic(topic)
    
    assert exc_info.value.status_code == 400
    assert "Similar topic found" in str(exc_info.value.detail)
    assert "456" in str(exc_info.value.detail)
