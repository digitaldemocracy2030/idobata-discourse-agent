import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.services.topic_analysis import TopicAnalysisService
from src.clients.discourse_client import DiscourseClient
from src.clients.summary_client import SummaryClient
from src.clients.slack_client import SlackClient

@pytest.fixture
def mock_discourse_client():
    client = Mock(spec=DiscourseClient)
    client.get_topic = AsyncMock()
    client.get_topic_posts = AsyncMock()
    client.get_topic_post_count = AsyncMock()
    client.post_analysis_result = AsyncMock()
    return client

@pytest.fixture
def mock_summary_client():
    client = Mock(spec=SummaryClient)
    client.list_projects = Mock()
    client.create_project = Mock()
    client.bulk_import_comments = Mock()
    client.generate_questions = Mock()
    client.get_project_analysis = Mock()
    return client

@pytest.fixture
def mock_slack_client():
    client = Mock(spec=SlackClient)
    client.send_notification = AsyncMock()
    return client

@pytest.fixture
def topic_analysis_service(mock_discourse_client, mock_summary_client, mock_slack_client):
    return TopicAnalysisService(
        discourse_client=mock_discourse_client,
        summary_client=mock_summary_client,
        slack_client=mock_slack_client
    )

@pytest.mark.asyncio
async def test_create_or_get_project_existing(topic_analysis_service, mock_summary_client):
    """既存のプロジェクトを取得するテスト"""
    # モックの設定
    mock_summary_client.list_projects.return_value = [
        {"id": "project-1", "name": "topic_123"}
    ]
    
    # テスト実行
    project_id = await topic_analysis_service._create_or_get_project(123, "テストトピック")
    
    # 検証
    assert project_id == "project-1"
    mock_summary_client.list_projects.assert_called_once()
    mock_summary_client.create_project.assert_not_called()

@pytest.mark.asyncio
async def test_create_or_get_project_new(topic_analysis_service, mock_summary_client):
    """新規プロジェクトを作成するテスト"""
    # モックの設定
    mock_summary_client.list_projects.return_value = []
    mock_summary_client.create_project.return_value = {"id": "new-project"}
    
    # テスト実行
    project_id = await topic_analysis_service._create_or_get_project(123, "テストトピック")
    
    # 検証
    assert project_id == "new-project"
    mock_summary_client.create_project.assert_called_once_with(
        name="topic_123",
        description="テストトピック",
        extraction_topic="ディスカッションの論点と意見の分布"
    )

@pytest.mark.asyncio
async def test_import_posts_to_summary(topic_analysis_service, mock_discourse_client, mock_summary_client):
    """投稿のインポートテスト"""
    # モックの設定
    mock_discourse_client.get_topic_posts.return_value = [
        {"raw": "投稿1", "post_number": 1},
        {"raw": "投稿2", "post_number": 2}
    ]
    
    # テスト実行
    await topic_analysis_service._import_posts_to_summary("project-1", 123)
    
    # 検証
    mock_discourse_client.get_topic_posts.assert_called_once_with(123)
    mock_summary_client.bulk_import_comments.assert_called_once_with(
        "project-1",
        [
            {
                "content": "投稿1",
                "sourceType": "discourse",
                "sourceUrl": "/t/123/1"
            },
            {
                "content": "投稿2",
                "sourceType": "discourse",
                "sourceUrl": "/t/123/2"
            }
        ]
    )

@pytest.mark.asyncio
async def test_analyze_topic(topic_analysis_service, mock_discourse_client, mock_summary_client):
    """トピック分析の実行テスト"""
    # モックの設定
    mock_discourse_client.get_topic.return_value = {"title": "テストトピック"}
    mock_summary_client.list_projects.return_value = []
    mock_summary_client.create_project.return_value = {"id": "project-1"}
    mock_summary_client.get_project_analysis.return_value = {"content": "分析結果"}
    
    # テスト実行
    project_id, analysis = await topic_analysis_service.analyze_topic(123)
    
    # 検証
    assert project_id == "project-1"
    assert analysis == "分析結果"
    mock_discourse_client.get_topic.assert_called_once_with(123)
    mock_summary_client.generate_questions.assert_called_once_with("project-1")
    mock_summary_client.get_project_analysis.assert_called_once_with(
        "project-1",
        force_regenerate=True
    )

@pytest.mark.asyncio
@patch("src.services.topic_analysis.POSTS_THRESHOLD", 5)
@patch("src.services.topic_analysis.DRY_RUN_MODE", False)
async def test_analyze_topic_if_needed_threshold_met(
    topic_analysis_service,
    mock_discourse_client,
    mock_summary_client,
    mock_slack_client
):
    """投稿数が閾値に達した場合のテスト"""
    # モックの設定
    mock_discourse_client.get_topic_post_count.return_value = 5
    mock_discourse_client.get_topic.return_value = {"title": "テストトピック"}
    mock_summary_client.list_projects.return_value = []
    mock_summary_client.create_project.return_value = {"id": "project-1"}
    mock_summary_client.get_project_analysis.return_value = {"content": "分析結果"}
    
    # テスト実行
    await topic_analysis_service.analyze_topic_if_needed(123)
    
    # 検証
    mock_discourse_client.post_analysis_result.assert_called_once_with(
        123,
        "分析結果",
        "project-1"
    )
    mock_slack_client.send_notification.assert_called_once()

@pytest.mark.asyncio
@patch("src.services.topic_analysis.POSTS_THRESHOLD", 5)
@patch("src.services.topic_analysis.DRY_RUN_MODE", True)
async def test_analyze_topic_if_needed_dry_run(
    topic_analysis_service,
    mock_discourse_client,
    mock_summary_client,
    mock_slack_client
):
    """DRY_RUN_MODEでの動作テスト"""
    # モックの設定
    mock_discourse_client.get_topic_post_count.return_value = 5
    mock_discourse_client.get_topic.return_value = {"title": "テストトピック"}
    mock_summary_client.list_projects.return_value = []
    mock_summary_client.create_project.return_value = {"id": "project-1"}
    mock_summary_client.get_project_analysis.return_value = {"content": "分析結果"}
    
    # テスト実行
    await topic_analysis_service.analyze_topic_if_needed(123)
    
    # 検証
    mock_discourse_client.post_analysis_result.assert_not_called()
    mock_slack_client.send_notification.assert_called_once()
    assert "[レビュー待ち]" in mock_slack_client.send_notification.call_args[0][0]

@pytest.mark.asyncio
@patch("src.services.topic_analysis.POSTS_THRESHOLD", 5)
async def test_analyze_topic_if_needed_threshold_not_met(
    topic_analysis_service,
    mock_discourse_client,
    mock_summary_client,
    mock_slack_client
):
    """投稿数が閾値に達していない場合のテスト"""
    # モックの設定
    mock_discourse_client.get_topic_post_count.return_value = 3
    
    # テスト実行
    await topic_analysis_service.analyze_topic_if_needed(123)
    
    # 検証
    mock_discourse_client.get_topic.assert_not_called()
    mock_summary_client.list_projects.assert_not_called()
    mock_discourse_client.post_analysis_result.assert_not_called()
    mock_slack_client.send_notification.assert_not_called()

@pytest.mark.asyncio
async def test_analyze_topic_if_needed_error_handling(
    topic_analysis_service,
    mock_discourse_client,
    mock_slack_client
):
    """エラー処理のテスト"""
    # モックの設定
    mock_discourse_client.get_topic_post_count.side_effect = Exception("テストエラー")
    
    # テスト実行
    await topic_analysis_service.analyze_topic_if_needed(123)
    
    # 検証
    mock_slack_client.send_notification.assert_called_once()
    assert "エラーが発生しました" in mock_slack_client.send_notification.call_args[0][0]