import pytest
from unittest.mock import Mock, AsyncMock
import google.generativeai as genai

from src.services.moderation import ModerationService
from src.config import settings

@pytest.mark.asyncio
async def test_check_content_appropriateness_appropriate():
    # モックの設定
    mock_discourse_client = Mock()
    service = ModerationService(mock_discourse_client)
    
    # Geminiのレスポンスをモック
    mock_response = Mock()
    mock_response.text = "YES This content is appropriate"
    mock_model = Mock()
    mock_model.generate_content = AsyncMock(return_value=mock_response)
    service.model = mock_model
    
    # テスト実行
    content = "This is a good post"
    is_appropriate, explanation = await service.check_content_appropriateness(content)
    
    # 検証
    assert is_appropriate is True
    assert "this content is appropriate" in explanation.lower()

@pytest.mark.asyncio
async def test_check_content_appropriateness_inappropriate():
    # モックの設定
    mock_discourse_client = Mock()
    service = ModerationService(mock_discourse_client)
    
    # Geminiのレスポンスをモック
    mock_response = Mock()
    mock_response.text = "NO This content contains inappropriate language"
    mock_model = Mock()
    mock_model.generate_content = AsyncMock(return_value=mock_response)
    service.model = mock_model
    
    # テスト実行
    content = "This is a bad post with inappropriate content"
    is_appropriate, explanation = await service.check_content_appropriateness(content)
    
    # 検証
    assert is_appropriate is False
    assert "inappropriate" in explanation.lower()

@pytest.mark.asyncio
async def test_handle_moderation_inappropriate_content():
    # モックの設定
    mock_discourse_client = Mock()
    mock_discourse_client.delete_post = AsyncMock()
    mock_discourse_client.create_reply = AsyncMock()
    
    service = ModerationService(mock_discourse_client)
    
    # check_content_appropriatenessの結果をモック
    service.check_content_appropriateness = AsyncMock(return_value=(False, "Inappropriate content"))
    
    # テストデータ
    post = {
        "id": 123,
        "topic_id": 456,
        "raw": "Inappropriate content"
    }
    
    # テスト実行
    await service.handle_moderation(post)
    
    # 検証
    mock_discourse_client.delete_post.assert_called_once_with(123)
    mock_discourse_client.create_reply.assert_called_once_with(
        topic_id=456,
        content=settings.DELETION_MESSAGE
    )

@pytest.mark.asyncio
async def test_check_topic_similarity_duplicate():
    # モックの設定
    mock_discourse_client = Mock()
    service = ModerationService(mock_discourse_client)
    
    # Geminiのレスポンスをモック
    mock_response = Mock()
    mock_response.text = "YES | Very similar content found | 123"
    mock_model = Mock()
    mock_model.generate_content = AsyncMock(return_value=mock_response)
    service.model = mock_model
    
    # テストデータ
    content = "Test content"
    existing_topics = [
        {"id": 123, "title": "Similar topic", "excerpt": "Similar content"}
    ]
    
    # テスト実行
    is_duplicate, explanation, topic_id = await service.check_topic_similarity(content, existing_topics)
    
    # 検証
    assert is_duplicate is True
    assert topic_id == 123
    assert "similar" in explanation.lower()
