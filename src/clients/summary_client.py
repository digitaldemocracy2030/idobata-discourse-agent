import os
import requests
import json
import pandas as pd

# 要約クライアント
class SummaryClient:
    def __init__(self, base_url="http://localhost:3001/api", admin_api_key=None):
        """
        初期化時にベースURLとAdmin APIキーを設定します。
        admin_api_keyが指定されていない場合は、環境変数ADMIN_API_KEYから取得します。
        """
        self.base_url = base_url
        self.admin_api_key = admin_api_key or os.getenv("ADMIN_API_KEY")

    def _headers(self, admin_required=False):
        """
        API呼び出し時のヘッダーを生成します。
        admin_requiredがTrueの場合、x-api-keyヘッダーを追加します。
        """
        headers = {}
        if admin_required:
            if not self.admin_api_key:
                raise ValueError("Admin APIキーが必要です。環境変数ADMIN_API_KEYを設定してください。")
            headers["x-api-key"] = self.admin_api_key
        return headers

    # プロジェクト管理 API

    def list_projects(self):
        """
        [GET] /projects
        全てのプロジェクト一覧を取得（Admin権限必要）。
        """
        url = f"{self.base_url}/projects"
        response = requests.get(url, headers=self._headers(admin_required=True))
        return response.json()

    def create_project(self, name, description, extraction_topic):
        """
        [POST] /projects
        新規プロジェクトを作成（Admin権限必要）。
        """
        url = f"{self.base_url}/projects"
        payload = {
            "name": name,
            "description": description,
            "extractionTopic": extraction_topic
        }
        response = requests.post(url, headers=self._headers(admin_required=True), json=payload)
        return response.json()

    def get_project(self, project_id):
        """
        [GET] /projects/:projectId
        指定されたプロジェクトIDのプロジェクト情報を取得（認証不要）。
        """
        url = f"{self.base_url}/projects/{project_id}"
        response = requests.get(url)
        return response.json()

    def update_project(self, project_id, name, description, extraction_topic, questions=None):
        """
        [PUT] /projects/:projectId
        指定されたプロジェクトを更新（Admin権限必要）。
        """
        url = f"{self.base_url}/projects/{project_id}"
        payload = {
            "name": name,
            "description": description,
            "extractionTopic": extraction_topic
        }
        if questions is not None:
            payload["questions"] = questions
        response = requests.put(url, headers=self._headers(admin_required=True), json=payload)
        return response.json()

    def generate_questions(self, project_id):
        """
        [POST] /projects/:projectId/generate-questions
        プロジェクト内容に基づき論点を自動生成（Admin権限必要）。
        """
        url = f"{self.base_url}/projects/{project_id}/generate-questions"
        response = requests.post(url, headers=self._headers(admin_required=True))
        return response.json()

    # コメント管理 API

    def get_project_comments(self, project_id):
        """
        [GET] /projects/:projectId/comments
        プロジェクトの全コメント一覧を取得（認証不要）。
        """
        url = f"{self.base_url}/projects/{project_id}/comments"
        response = requests.get(url)
        return response.json()

    def add_comment(self, project_id, content, source_type, source_url):
        """
        [POST] /projects/:projectId/comments
        指定プロジェクトに新規コメントを追加（Admin権限必要）。
        """
        url = f"{self.base_url}/projects/{project_id}/comments"
        payload = {
            "content": content,
            "sourceType": source_type,
            "sourceUrl": source_url
        }
        response = requests.post(url, headers=self._headers(admin_required=True), json=payload)
        return response.json()

    def bulk_import_comments(self, project_id, comments):
        """
        [POST] /projects/:projectId/comments/bulk
        複数のコメントを一括インポート（Admin権限必要）。
        コメントは以下の形式の辞書のリストを渡します:
            {
                "content": "コメント内容",
                "sourceType": "ソースタイプ",
                "sourceUrl": "ソースURL"
            }
        """
        url = f"{self.base_url}/projects/{project_id}/comments/bulk"
        payload = {"comments": comments}
        response = requests.post(url, headers=self._headers(admin_required=True), json=payload)
        return response.json()

    # 分析レポート API

    def get_stance_analysis(self, project_id, question_id, force_regenerate=False, custom_prompt=None):
        """
        [GET] /projects/:projectId/questions/:questionId/stance-analysis
        指定論点の立場分析レポートを取得します。
        基本取得は認証不要ですが、forceRegenerate=Trueの場合はAdmin権限が必要です。
        """
        url = f"{self.base_url}/projects/{project_id}/questions/{question_id}/stance-analysis"
        params = {"forceRegenerate": str(force_regenerate).lower()}
        if custom_prompt:
            params["customPrompt"] = custom_prompt
        response = requests.get(url, headers=self._headers(admin_required=force_regenerate), params=params)
        print(f"stance_analysis:{response.json()}")
        return response.json()

    def get_project_analysis(self, project_id, force_regenerate=False, custom_prompt=None):
        """
        [GET] /projects/:projectId/analysis
        プロジェクト全体の分析レポートを取得します。
        基本取得は認証不要ですが、forceRegenerate=Trueの場合はAdmin権限が必要です。
        """
        url = f"{self.base_url}/projects/{project_id}/analysis"
        params = {"forceRegenerate": str(force_regenerate).lower()}
        if custom_prompt:
            params["customPrompt"] = custom_prompt
        response = requests.get(url, headers=self._headers(admin_required=force_regenerate), params=params)
        return response.json()

    def export_project_csv(self, project_id):
        """
        [GET] /projects/:projectId/export-csv
        プロジェクトの分析データをCSV形式でエクスポート（Admin権限必要）。
        """
        url = f"{self.base_url}/projects/{project_id}/export-csv"
        response = requests.get(url, headers=self._headers(admin_required=True))
        return response.content

    # プロンプト管理 API

    def get_default_prompts(self):
        """
        [GET] /prompts/default
        システムで使用される各種デフォルトプロンプトを取得（Admin権限必要）。
        """
        url = f"{self.base_url}/prompts/default"
        response = requests.get(url, headers=self._headers(admin_required=True))
        return response.json()