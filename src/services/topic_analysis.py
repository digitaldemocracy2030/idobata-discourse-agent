from typing import Dict, Any, Tuple
from src.clients.summary_client import SummaryClient
from src.clients.slack_client import SlackClient
from src.clients.discourse_client import DiscourseClient
from src.config.settings import POSTS_THRESHOLD, DRY_RUN_MODE
from src.utils.utils import remove_html_tags
import pandas as pd
import google.generativeai as genai
import json

class TopicAnalysisService:
    def __init__(
        self,
        discourse_client: DiscourseClient,
        summary_client: SummaryClient,
        slack_client: SlackClient
    ):
        self.discourse_client = discourse_client
        self.summary_client = summary_client
        self.slack_client = slack_client
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def _create_or_get_project(self, topic_id: int, title: str) -> str:
        """トピックに対応するSummaryプロジェクトを作成または取得"""
        try:
            # プロジェクト一覧を取得して既存プロジェクトを確認
            projects = self.summary_client.list_projects()
            for project in projects:
                if project.get("name") == f"topic_{topic_id}":
                    print(f"project found!:{project}")
                    return project.get("_id")

            # 新規プロジェクトを作成
            print(f"creating project!")
            project = self.summary_client.create_project(
                name=f"topic_{topic_id}",
                description=title,
                extraction_topic="ディスカッションの論点と意見の分布"
            )
            return project.get("id")
        except Exception as e:
            raise Exception(f"Failed to create/get summary project: {str(e)}")

    async def _import_posts_to_summary(self, project_id: str, topic_id: int) -> None:
        """トピックの投稿をsummaryにインポート"""
        try:
            # トピックの全投稿を取得
            posts = await self.discourse_client.get_topic_posts(topic_id)
            # コメントをsummaryの形式に変換
            comments = [
                {
                    "content": remove_html_tags(post.get("cooked", "")),
                    "sourceType": "other",
                    "sourceUrl": f"https://large-scale-conversation-sandbox.discourse.group/t/{topic_id}/{post.get('post_number')}"
                }
                for post in posts
            ]
            print(f"comment length:{len(posts)}")
            # 一括インポート
            self.summary_client.bulk_import_comments(project_id, comments)
        except Exception as e:
            raise Exception(f"Failed to import posts to summary: {str(e)}")

    async def analyze_topic(self, topic_id: int) -> Tuple[str, str]:
        """トピックを分析してsummaryで処理"""
        try:
            # トピックの基本情報を取得
            topic_info = await self.discourse_client.get_topic(topic_id)
            title = topic_info.get("title", "")

            # summaryプロジェクトを作成または取得
            project_id = await self._create_or_get_project(topic_id, title)

            # 投稿をsummaryにインポート
            await self._import_posts_to_summary(project_id, topic_id)

            # 論点を自動生成
            self.summary_client.generate_questions(project_id)

            # プロジェクト全体の分析を実行

            overallAnalysis = self.summary_client.get_project_analysis(
                project_id,
                force_regenerate=True
            )
            print(f"分析結果:{overallAnalysis}")

            return project_id, overallAnalysis.get("overallAnalysis", "分析結果を取得できませんでした")


        except Exception as e:
            raise Exception(f"Failed to analyze topic: {str(e)}")

    async def analyze_topic_if_needed(self, topic_id: int, force_analyze: bool = False) -> None:
        """投稿数をチェックし、閾値に達していれば分析を実行する"""
        try:
            # 投稿数を取得
            current_count = await self.discourse_client.get_topic_post_count(topic_id)
            
            # 投稿数をログ出力
            print(f"Topic {topic_id} post count: {current_count} (threshold: {POSTS_THRESHOLD})")
            
            # 投稿数が閾値に達しているかチェック
            if (current_count > 0 and current_count % POSTS_THRESHOLD == 0) or force_analyze:
                # 分析を実行
                project_id, analysis_result = await self.analyze_topic(topic_id)
                # 分析結果を投稿用のフォーマットに整形
                content = self.generate_post_message(project_id)
                print(content)
                if DRY_RUN_MODE:
                    print("dry run send slack")
                    print(f"{content}")
                    # dry runモードの場合、Discourseへの投稿はスキップしてSlackのみに通知
                    await self.slack_client.send_notification(
                        f"[dry run] トピック {topic_id} の分析が完了しました。\n"
                        f"プロジェクトID: {project_id}\n"
                        f"全体の分析: {analysis_result}\n"
                        f"投稿内容: {content}\n"
                        f"投稿数: {current_count}\n"
                    )
                else:
                    # 通常モードの場合は分析結果を投稿
                    await self.discourse_client.create_reply(
                        topic_id,
                        content
                    )
                    # Slackに通知
                    await self.slack_client.send_notification(
                        f"トピック {topic_id} の分析が完了しました。\n"
                        f"プロジェクトID: {project_id}\n"
                        f"全体の分析: {analysis_result}\n"
                        f"投稿内容: {content}\n"
                        f"投稿数: {current_count}"
                    )
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_message = f"Error analyzing topic {topic_id}: {str(e)}\n\nTraceback:\n{error_trace}"
            print(error_message)
            # エラーをSlackに通知
            #await self.slack_client.send_notification(
            #    f"トピック {topic_id} の分析中にエラーが発生しました：{str(e)}\n\nTraceback:\n{error_trace}"
            #)


    # questionsとanalysisをiterateしやすい形にまとめる
    def merge_stance_and_analysis(self, row):
        merged_stances = []
        for stance in row.stances:
            stance_id = stance["id"]
            if stance_id in row.analysis:
                merged = {**stance, **row.analysis[stance_id]}
            else:
                merged = stance.copy()
            merged_stances.append(merged)
        return merged_stances

    def build_question_prompt(self, row):
        stance_part = ""

        for s in row.merged_stances:
            stance_part += f"""
            スタンス名:  {s["name"]}

            コメント一覧:
            """
            for c in s["comments"]:
                stance_part += f"- {c}\n"

        p = f"""
        ### 論点
        {row.text}
        (question_id: {row.id})

        ### スタンス一覧
        {stance_part}
        """

        return p


    def build_choice_prompt(self, project, q_df):
        p = f"""
            # 依頼内容
            あなたは、建設的な政治的議論を行うフォーラムのファシリテーターです。

            「{project["name"]}」というトピックについて、自動抽出された論点が複数個渡されるので、
            その中から、議論が盛り上がるトピックのランキングをIDを配列にして返してください。

            議論が盛り上がる要素として、以下の点を考慮してください。

            1.論点同士にトレードオフがあること
            2.抽象度が低すぎないこと

            回答は、json形式で、直接パースできる形式でフォーマットで返してください。
            ```json などは絶対につけないでください。

            {{
                "ranking": ["q_id_1", "q_id_1", ], // question_id の配列
                "reason": "そのような順序にした理由"
            }}

            ## 内容
            {"".join(q_df.apply(self.build_question_prompt, axis=1))}
        """

        cleaned = "\n".join(line.lstrip() for line in p.splitlines())
        return cleaned

    # 投稿本文を作成するメッセージ用プロンプト
    def build_posting_message_prompt(self, project, row, iframe_tag):
        p = f"""
            # 依頼内容
            あなたは、建設的な政治的議論を行うフォーラムのファシリテーターです。

            「{project["name"]}」というトピックについて、特に盛り上がっている論点があるので、
            その点について現在までの議論の要約を行ったうえで、あらたなコメントを投稿する際のテキストを考えてください。

            # 注意点
        テキストを考えるにあたって、以下の点に気をつけてください。

            ### 論点ごとのトレードオフを明示する、もしくは用意する
            「どのオプションも同時に進めれば良い」という意見が成立すると、議論の価値は薄れるので、トレードオフがすでにある場合はその点を強調してください。
            トレードオフがあまりない場合は、「リソースには限りがあるという前提で、まず始めるなら...」など、トレードオフを意識させるような限定を加えてください。

            ### 二項対立にしすぎない
            論点を強調しすぎると、「どちらが」というふうに限定的な意見が集まりがちになります。
            しかし本来、オプションは多様なはずなので、「それ以外の視点も歓迎」するような一言を必要に応じて加えてください。

            ### コメントを書き込みやすくする
            議論が深まると、新しく議論に参加するのが難しくなりがちです。
            そのような状況でも、議論をしやすくするよう、書き込みやすくする工夫をしてください。

            ### 埋め込みリンクを最初のひとことの後に埋め込む
            掲示板の機能で、以下のiframeを埋め込むことが可能です。
            序盤に埋め込んで視覚的にこれまでの議論をわかりやすくしてください。
            iframe経由で、ユーザーは、円グラフで派閥名と人数を知ることができます。

            実際のタグ: {iframe_tag}
            # 具体的な投稿のサンプル

            ================================
            > 現在までの議論をもとに、AIによる意見まとめが生成されました！
            > ぜひ見てみてくださいね。

            > <iframe src="https://delib.takahiroanno.com/embed/67bdc8cc1e9569d867825cc6?question=e6ef864a-8870-4c54-960f-be596193e4ca"></iframe>


            > 特に「 都のAI倫理ガイドラインは、生成AIプラットフォーム提供開始までに整備すべきか？」という点について、特に多様な意見が出ているようです。

            > # 新たな論点

            > 都のAI倫理ガイドラインは、生成AIプラットフォーム提供開始までに整備すべきか？


            > ## 1. 子育て支援最優先派

            > このスタンスでは、生成AIによる教育支援や子育て支援への活用に重点が置かれています。AIを活用した学習支援ツールやチャットボットによる相談窓口などが提案されています。

            > メリット: 学習困難な子供への効果的な支援、保護者の負担軽減、24時間対応可能な相談窓口の提供などが期待できます。
            > デメリット: AIによる教育の偏り、プライバシー保護、AIの倫理的な問題、導入・運用コスト、教師の役割の変化など、慎重に検討すべき課題が多く存在します。

            > ## 2. 手続き簡素化重点派

            > このスタンスでは、生成AIを活用した行政手続きのデジタル化、効率化に焦点を当てています。深セン市の事例を参考に、行政サービスの迅速化、情報の一元管理などが提案されています。

            > メリット: 行政手続きの簡素化による都民の利便性向上、行政職員の業務負担軽減、迅速な情報提供などが期待できます。
            > デメリット: システム導入・運用コスト、データセキュリティ、個人情報保護、AIによる誤判定のリスク、デジタルデバイドの問題など、課題も多くあります。

            > ## 3. 健康増進オールインワン派

            > このスタンスでは、健康診断情報と生成AIを組み合わせたパーソナライズされた予防医療システムの構築を目指しています。

            > メリット: 個別最適化された予防医療による健康増進、医療費削減効果が期待できます。
            > デメリット: 個人情報保護の厳格な対策が必要、医療データの精度と信頼性、AIの判断の透明性、導入コストなどが課題となります。


            > 上記3つのスタンス以外にも、様々な活用方法が考えられます。例えば、観光情報提供、防災対策、環境問題への対応など、生成AIは多様な分野で活用できる可能性を秘めています。

            > 上記を参考に、あなたの意見を教えて下さい！
            ================================


            # 回答フォーマット
            回答は、以下のフォーマットで記載してください。
            {{
                "post_text": "実際にそのまま掲示板に投稿できるテキスト。マークダウン形式。"
            }}
            # 論点
            {row.text}

            ## スタンスとコメント
        """

        for s in row.merged_stances:
            p += f"""
            スタンス名: {s["name"]}  \n代表的なコメント:
            """
            for c in s["comments"]:
                p += f"- {c}\n"

        cleaned = "\n".join(line.lstrip() for line in p.splitlines())
        return cleaned

    def generate_post_message(self, project_id):
        project = self.summary_client.get_project(project_id)
        questions = project["questions"]
        print(f"questions:{questions}")
        q_df = pd.DataFrame.from_dict(questions)

        print("Fetching project info...")
        q_df["analysis"] = q_df.id.apply(lambda id: self.summary_client.get_stance_analysis(project_id, question_id = id)["stanceAnalysis"])
        q_df["merged_stances"] = q_df.apply(self.merge_stance_and_analysis, axis=1)

        print("Choosing most controversial question...")
        choice_prompt = self.build_choice_prompt(project, q_df)
        print("Choice Prompt: ", choice_prompt)
        choice_result = self.model.generate_content(choice_prompt, generation_config={"response_mime_type": "application/json"})
        rankings = json.loads(choice_result.text)
        most_controversial_question_id = rankings["ranking"][0]
        target_question = q_df[q_df["id"] == most_controversial_question_id].iloc[0]

        embed_link = f"https://delib.takahiroanno.com/embed/{project_id}?question={target_question.id}"
        iframe_tag = f'<iframe src="{embed_link}" width="100%" height="500px"></iframe>'
        print("Target question: ", target_question.text[0:50])
        print("Embed Link: ", embed_link)

        print("Generating post message...")
        posting_message_prompt = self.build_posting_message_prompt(project, target_question, iframe_tag)
        result = self.model.generate_content(posting_message_prompt, generation_config={"response_mime_type": "application/json"})
        post_text = json.loads(result.text)["post_text"]

        print(f"Message generated\n. {post_text}")
        return post_text
