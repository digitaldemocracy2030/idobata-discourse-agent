import os
import sys
from datetime import datetime
import requests
from dotenv import load_dotenv
from openai import OpenAI

# 環境変数の読み込み
load_dotenv()

# API設定
DISCOURSE_API_KEY = os.getenv('DISCOURSE_API_KEY')
DISCOURSE_BASE_URL = os.getenv('DISCOURSE_BASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
USERNAME = 'takahiroanno'

# 必要な環境変数のチェック
if not all([DISCOURSE_API_KEY, DISCOURSE_BASE_URL, OPENAI_API_KEY]):
    print('エラー: 必要な環境変数が設定されていません')
    sys.exit(1)

def get_post(post_id):
    """指定されたIDの投稿を取得"""
    url = f'{DISCOURSE_BASE_URL}/posts/{post_id}.json'
    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': USERNAME
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f'投稿の取得に失敗しました: {e}')
        return None

def generate_additional_content(original_recipe):
    """OpenAIを使用して追加のコンテンツを生成"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "あなたは料理のエキスパートです。既存のレシピに対して、アレンジやコツ、代替材料などの追加情報を提案してください。"
            },
            {
                "role": "user",
                "content": f"以下のレシピに対して、調理のコツやアレンジ方法を追加してください：\n\n{original_recipe}"
            }
        ]
    )
    
    return response.choices[0].message.content

def update_post(post_id, original_content, additional_content):
    """投稿を更新"""
    url = f'{DISCOURSE_BASE_URL}/posts/{post_id}'
    
    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': USERNAME,
        'Content-Type': 'application/json'
    }
    
    updated_content = f"{original_content}\n\n# アレンジとコツ\n\n{additional_content}"
    
    data = {
        'post': {
            'raw': updated_content,
            'edit_reason': 'レシピのアレンジとコツを追加'
        }
    }
    
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        print(f'投稿の更新が成功しました: {response.json()}')
    except requests.exceptions.RequestException as e:
        print(f'投稿の更新に失敗しました: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'エラーの詳細: {e.response.text}')

def main():
    # 更新する投稿のID
    post_id = 78  # 直前に作成した投稿のID
    
    # 既存の投稿を取得
    post = get_post(post_id)
    if not post:
        print('投稿の取得に失敗しました')
        return
    
    print(f"元の投稿内容:\n{post['raw']}\n")
    
    # 追加のコンテンツを生成
    additional_content = generate_additional_content(post['raw'])
    print(f"生成された追加コンテンツ:\n{additional_content}\n")
    
    # 投稿を更新
    update_post(post_id, post['raw'], additional_content)

if __name__ == '__main__':
    main()