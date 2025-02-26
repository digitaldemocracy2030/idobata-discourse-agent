from fastapi import FastAPI, HTTPException, Header, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from typing import Optional, Dict, Any
import httpx
import os
import json
import traceback
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai
import asyncio

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Discourse Bot API")

# Configure API key authentication
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Discourse configuration
DISCOURSE_API_KEY = os.getenv("DISCOURSE_API_KEY")
DISCOURSE_BASE_URL = os.getenv("DISCOURSE_BASE_URL")
APP_API_KEY = os.getenv("APP_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Constants
DELETION_MESSAGE = "このコメントはガイドラインを違反しているため削除されました"

if not all([DISCOURSE_API_KEY, DISCOURSE_BASE_URL, APP_API_KEY, GEMINI_API_KEY]):
    raise ValueError("Missing required environment variables")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Define request models
class TopicCreate(BaseModel):
    title: str
    content: str
    category_id: int

class WebhookPayload(BaseModel):
    post: Dict[str, Any]

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != APP_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    return api_key

async def check_content_appropriateness(content: str) -> tuple[bool, str]:
    """
    Check if content is appropriate using Gemini API
    Returns: (is_appropriate, explanation)
    """
    prompt = f"""
    Please analyze the following content and determine if it is appropriate for a public forum.
    Consider factors like hate speech, explicit content, harassment, spam, or other inappropriate content.
    Content to analyze: {content}
    
    Respond with a clear YES if the content is appropriate, or NO if it's inappropriate.
    Also provide a brief explanation of your decision.
    """
    
    try:
        print("\nAnalyzing content with Gemini API:")
        print(f"Content: {content}")
        response = model.generate_content(prompt)
        response_text = response.text.strip().lower()
        is_appropriate = response_text.startswith('yes')
        explanation = ' '.join(response_text.split()[1:])  # Remove YES/NO and get explanation
        print(f"Gemini Response: {response_text}")
        return is_appropriate, explanation
    except Exception as e:
        print("\nError in content analysis:")
        traceback.print_exc()
        return False, f"Error analyzing content: {str(e)}"

async def check_topic_similarity(new_content: str, existing_topics: list[Dict[str, Any]]) -> tuple[bool, str, Optional[int]]:
    """
    Check if the new content is similar to existing topics
    Returns: (is_duplicate, explanation, similar_topic_id)
    """
    if not existing_topics:
        return False, "No existing topics to compare", None

    topics_text = "\n".join([
        f"Topic {i+1}: {topic.get('title', '')} - {topic.get('excerpt', '')}"
        for i, topic in enumerate(existing_topics)
    ])

    prompt = f"""
    Please analyze if the following new content is similar to or duplicates any of the existing topics.
    
    New content:
    {new_content}
    
    Existing topics:
    {topics_text}
    
    Respond with:
    - 'DUPLICATE' if the content is very similar to an existing topic (specify which Topic number)
    - 'UNIQUE' if the content is sufficiently different
    
    Also provide a brief explanation of your decision.
    """

    try:
        print("\nChecking topic similarity with Gemini API:")
        response = model.generate_content(prompt)
        response_text = response.text.strip().lower()
        
        is_duplicate = response_text.startswith('duplicate')
        words = response_text.split()
        
        # Try to extract topic number if it's a duplicate
        similar_topic_id = None
        if is_duplicate:
            for i, word in enumerate(words):
                if word == "topic" and i + 1 < len(words):
                    try:
                        topic_num = int(words[i + 1]) - 1  # Convert to 0-based index
                        if 0 <= topic_num < len(existing_topics):
                            similar_topic_id = existing_topics[topic_num].get('id')
                            break
                    except ValueError:
                        continue

        explanation = ' '.join(words[1:])  # Remove DUPLICATE/UNIQUE and get explanation
        print(f"Gemini Response: {response_text}")
        return is_duplicate, explanation, similar_topic_id

    except Exception as e:
        print("\nError in similarity analysis:")
        traceback.print_exc()
        return False, f"Error analyzing similarity: {str(e)}", None

class DiscourseClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Api-Key': api_key,
            'Api-Username': 'system',
            'Content-Type': 'application/json'
        }

    async def create_topic(self, title: str, content: str, category_id: int) -> Dict[Any, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/posts",
                headers=self.headers,
                json={
                    'title': title,
                    'raw': content,
                    'category': category_id
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_categories(self) -> Dict[Any, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/categories.json",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def delete_post(self, post_id: int) -> bool:
        """Delete a post and return success status"""
        print(f"\nAttempting to delete post {post_id}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/posts/{post_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                print(f"Successfully deleted post {post_id} (Status: {response.status_code})")
                return True
        except Exception as e:
            print(f"\nError deleting post {post_id}:")
            traceback.print_exc()
            return False

    async def create_reply(self, topic_id: int, content: str) -> Dict[Any, Any]:
        """Create a reply in a topic"""
        print(f"\nCreating reply in topic {topic_id}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/posts",
                    headers=self.headers,
                    json={
                        'topic_id': topic_id,
                        'raw': content
                    }
                )
                response.raise_for_status()
                print(f"Successfully created reply in topic {topic_id}")
                return response.json()
        except Exception as e:
            print(f"\nError creating reply in topic {topic_id}:")
            traceback.print_exc()
            raise

    async def get_recent_topics(self, limit: int = 20) -> list[Dict[str, Any]]:
        """Get recent topics from Discourse"""
        print(f"\nFetching {limit} recent topics")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/latest.json",
                    headers=self.headers,
                    params={'page': 0}
                )
                response.raise_for_status()
                topics = response.json().get('topic_list', {}).get('topics', [])
                return topics[:limit]
        except Exception as e:
            print("\nError fetching recent topics:")
            traceback.print_exc()
            return []

# Initialize Discourse client
discourse_client = DiscourseClient(DISCOURSE_BASE_URL, DISCOURSE_API_KEY)

async def handle_moderation(post: Dict[str, Any]):
    """
    Asynchronously handle post moderation
    """
    try:
        print("\nStarting moderation for post:")
        print(json.dumps(post, indent=2))

        post_content = post.get('raw', '')
        if not post_content:
            print("No content to moderate")
            return

        # Check content appropriateness
        is_appropriate, explanation = await check_content_appropriateness(post_content)
        print(f"\nModeration result: {'Appropriate' if is_appropriate else 'Inappropriate'}")
        print(f"Explanation: {explanation}")
        
        if not is_appropriate:
            print("\nPost deemed inappropriate, taking action...")
            # Delete the inappropriate post
            if await discourse_client.delete_post(post['id']):
                # Only post a reply if deletion was successful
                await discourse_client.create_reply(
                    topic_id=post['topic_id'],
                    content=DELETION_MESSAGE
                )
                print(f"\nSuccessfully moderated post {post['id']}")
                print(f"Reason: {explanation}")
            else:
                print(f"\nFailed to delete inappropriate post {post['id']}")
            return  # Exit early if content is inappropriate

        # If content is appropriate, check for topic similarity
        print("\nChecking for similar topics...")
        recent_topics = await discourse_client.get_recent_topics(20)
        is_duplicate, similarity_explanation, similar_topic_id = await check_topic_similarity(post_content, recent_topics)
        
        if is_duplicate and similar_topic_id:
            print("\nSimilar topic detected, notifying...")
            duplicate_message = f"""
類似のディスカッションを見つけました。
こちらのトピックもご参照ください: {DISCOURSE_BASE_URL}/t/{similar_topic_id}

類似点: {similarity_explanation}
"""
            await discourse_client.create_reply(
                topic_id=post['topic_id'],
                content=duplicate_message
            )
            print(f"\nNotified about similar topic {similar_topic_id}")
            print(f"Similarity explanation: {similarity_explanation}")

    except Exception as e:
        print("\nError in moderation handler:")
        traceback.print_exc()

@app.get("/categories", dependencies=[Depends(verify_api_key)])
async def list_categories():
    """List all available Discourse categories"""
    try:
        return await discourse_client.get_categories()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/topics", dependencies=[Depends(verify_api_key)])
async def create_topic(topic: TopicCreate):
    """Create a new topic in Discourse"""
    try:
        return await discourse_client.create_topic(
            title=topic.title,
            content=topic.content,
            category_id=topic.category_id
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/")
async def webhook_handler(request: Request):
    """Handle Discourse webhooks for content moderation"""
    try:
        # Get the raw body first
        body_bytes = await request.body()
        
        # Print the raw request body
        print("\nReceived webhook payload (raw):")
        print(body_bytes.decode())
        
        # Parse as JSON
        body = json.loads(body_bytes)
        
        # Print the parsed JSON
        print("\nParsed webhook payload:")
        print(json.dumps(body, indent=2))
        
        # Check if it's a post event
        if 'post' in body:
            post = body['post']
            
            # Skip if post is already deleted
            if post.get('deleted_at') is not None:
                print("\nIgnoring already deleted post")
            # Skip if this is our own deletion notification message
            elif post.get('raw') == DELETION_MESSAGE:
                print("\nIgnoring our own deletion notification message")
            else:
                # Create a task for moderation but don't await it
                asyncio.create_task(handle_moderation(post))
        else:
            print("\nNot a post event, ignoring")
        
        # Send 200 OK status without any response body
        return Response(status_code=200, content=None)

    except json.JSONDecodeError as e:
        print("\nJSON decode error in webhook handler:")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return Response(status_code=200, content=None)
    except Exception as e:
        print("\nUnexpected error in webhook handler:")
        traceback.print_exc()
        return Response(status_code=200, content=None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)