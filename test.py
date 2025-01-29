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

def generate_recipe():
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # レシピの生成
    # タイトル用のリクエスト
    title_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "日本の家庭料理の名前のみを1行で返してください。余計な説明は不要です。"
            },
            {
                "role": "user",
                "content": "今日の献立として、料理名を1つ提案してください。"
            }
        ]
    )
    
    title = title_response.choices[0].message.content.strip()
    
    # レシピ用のリクエスト
    recipe_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "指定された料理のレシピを、材料（分量付き）と手順を箇条書きで説明してください。余計な挨拶や説明は不要です。"
            },
            {
                "role": "user",
                "content": f"{title}のレシピを教えてください。"
            }
        ]
    )
    
    recipe = recipe_response.choices[0].message.content
    
    return title, recipe

def post_to_discourse():
    # レシピの生成
    title, recipe = generate_recipe()
    
    # デバッグ出力
    print(f"生成されたタイトル: {title}")
    print(f"生成されたレシピ: {recipe}")
    
    # 投稿内容
    post_data = {
        'title': title,
        'raw': f'# {title}\n\n{recipe}',  # タイトルを本文の先頭にも表示
        'category': 4,
        'topic_id': None,  # 新しいトピックを作成
        'archetype': 'regular'  # 通常の投稿として作成
    }
    
    # APIエンドポイント
    url = f'{DISCOURSE_BASE_URL}/posts.json'
    
    # ヘッダー設定
    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': USERNAME,
        'Content-Type': 'application/json'
    }
    
    try:
        # 現在時刻を取得してタイトルに追加
        current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_title = f'{title}_{current_time}'
        
        # 新しいトピックを作成
        topic_data = {
            'title': unique_title,
            'raw': f'# {title}\n\n{recipe}',
            'category': 4,
            'embed_url': None,
            'typing_duration_msecs': 6000,
            'composer_open_duration_msecs': 7000
        }
        
        # トピック作成リクエスト
        response = requests.post(f'{DISCOURSE_BASE_URL}/posts.json', json=topic_data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        print(f'投稿が成功しました: {result}')
        
    except requests.exceptions.RequestException as e:
        print(f'エラーが発生しました: {e}')
        if hasattr(e, 'response') and e.response is not None:
            print(f'エラーの詳細: {e.response.text}')

if __name__ == '__main__':
    post_to_discourse()