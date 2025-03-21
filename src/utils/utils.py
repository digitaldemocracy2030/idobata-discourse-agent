import re
from bs4 import BeautifulSoup

def remove_urls(text: str) -> str:
    """URLを文字列から削除する"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.sub(url_pattern, '', text)

def remove_html_tags(html_text: str) -> str:
    """HTMLテキストからタグを削除する"""
    soup = BeautifulSoup(html_text, 'html.parser')
    return soup.get_text(separator=' ', strip=True)