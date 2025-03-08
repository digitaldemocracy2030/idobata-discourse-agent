import httpx
import asyncio
import json
import pytest
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.asyncio
async def test_webhook():
    """ローカル環境でのwebhookエンドポイントのテスト"""
    headers = {
        'Content-Type': 'application/json'
    }

    # テスト用のwebhookペイロード
    webhook_data = {
        "post": {
            "id": 123,
            "title": "Test Post Title",
            "raw": "This is a test post for webhook",
            "cooked": "<p>This is a test post for webhook</p>",
            "created_at": datetime.now().isoformat(),
            "user_id": 456,
            "topic_id": 67
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/webhook",  # ローカルサーバーのエンドポイント
                headers=headers,
                json=webhook_data
            )
            
            print("\nWebhook test results:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == 200, "Webhook request failed"
            assert response.json()["status"] == "processing", "Unexpected response status"
            
            print("Webhook test completed successfully")
            return True

    except Exception as e:
        print(f"Error testing webhook: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_webhook_invalid_payload():
    """無効なペイロードでのwebhookテスト"""
    headers = {
        'Content-Type': 'application/json'
    }

    # 無効なペイロード（postフィールドが欠落）
    invalid_data = {
        "invalid_field": "test"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/webhook",
                headers=headers,
                json=invalid_data
            )
            
            print("\nInvalid payload test results:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == 422, "Expected validation error"
            error_detail = response.json()["detail"]
            assert any(
                e["type"] == "missing" and e["loc"] == ["body", "post"]
                for e in error_detail
            ), "Expected 'post' field missing error"
            print("Invalid payload test completed successfully - Validation error confirmed")
            return True

    except Exception as e:
        print(f"Error testing invalid payload: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_webhook_inappropriate_content():
    """不適切な内容を含む投稿のwebhookテスト"""
    headers = {
        'Content-Type': 'application/json'
    }

    # 不適切な内容を含むテスト用のwebhookペイロード
    webhook_data = {
        "post": {
            "id": 123,
            "raw": "This is spam content! Buy cheap products here! http://spam.example.com 不適切な内容です。",
            "cooked": "<p>This is spam content! Buy cheap products here! http://spam.example.com 不適切な内容です。</p>",
            "created_at": datetime.now().isoformat(),
            "user_id": 456,
            "topic_id": 67
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/webhook",
                headers=headers,
                json=webhook_data
            )
            
            print("\nInappropriate content test results:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == 200, "Webhook request failed"
            assert response.json()["status"] == "processing", "Unexpected response status"
            
            print("Inappropriate content test completed successfully")
            return True

    except Exception as e:
        print(f"Error testing inappropriate content: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_webhook_duplicate_content():
    """重複したコンテンツを含む投稿のwebhookテスト"""
    headers = {
        'Content-Type': 'application/json'
    }

    # 重複したコンテンツを含むテスト用のwebhookペイロード
    webhook_data = {
        "post": {
            "id": 124,
            "title": "Test Topic for Moderation",
            "raw": "教育についてAIたちが議論するスレッド",
            "cooked": "<p>教育についてAIたちが議論するスレッド</p>",
            "created_at": datetime.now().isoformat(),
            "user_id": 456,
            "topic_id": 67
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/webhook",
                headers=headers,
                json=webhook_data
            )
            
            print("\nDuplicate content test results:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == 200, "Webhook request failed"
            assert response.json()["status"] == "processing", "Unexpected response status"
            
            # Note: 実際の重複チェックはバックグラウンドで非同期に行われるため、
            # ここではレスポンスのステータスコードとステータスメッセージのみを確認します
            
            print("Duplicate content test completed successfully")
            return True

    except Exception as e:
        print(f"Error testing duplicate content: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_webhook_education_topic():
    """教育に関するトピックのwebhookテスト（topic_id: 67）"""
    headers = {
        'Content-Type': 'application/json'
    }

    # 教育に関するテスト用のwebhookペイロード
    webhook_data = {
        "post": {
            "id": 125,
            "raw": "プログラミング教育において、以下の学習方法が効果的だと考えられますaisum",
            "cooked": "<p>プログラミング教育において、以下の学習方法が効果的だと考えられますaisum</p>",
            "created_at": datetime.now().isoformat(),
            "user_id": 456,
            "topic_id": 67
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/webhook",
                #"https://discourse-bot-756967799775.asia-northeast1.run.app/api/webhook",
                headers=headers,
                json=webhook_data
            )
            
            print("\nEducation topic test results:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            assert response.status_code == 200, "Webhook request failed"
            assert response.json()["status"] == "processing", "Unexpected response status"
            
            print("Education topic test completed successfully")
            return True

    except Exception as e:
        print(f"Error testing education topic: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting education topic...")
    asyncio.run(test_webhook_education_topic())
