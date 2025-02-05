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

    async def delete_post(self, post_id: int) -> Dict[Any, Any]:
        """Delete a post"""
        print(f"\nAttempting to delete post {post_id}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/posts/{post_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                print(f"Successfully deleted post {post_id}")
                return response.json()
        except Exception as e:
            print(f"\nError deleting post {post_id}:")
            traceback.print_exc()
            raise

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
            await discourse_client.delete_post(post['id'])
            
            # Post a message indicating the deletion
            await discourse_client.create_reply(
                topic_id=post['topic_id'],
                content="このコメントはガイドラインを違反しているため削除されました"
            )
            
            print(f"\nSuccessfully moderated post {post['id']}")
            print(f"Reason: {explanation}")

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
        
        # Start moderation in the background if it's a post event
        if 'post' in body:
            # Create a task for moderation but don't await it
            asyncio.create_task(handle_moderation(body['post']))
        else:
            print("\nNot a post event, ignoring")
        
        # Always return 200 OK immediately
        return Response(status_code=200)

    except json.JSONDecodeError as e:
        print("\nJSON decode error in webhook handler:")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return Response(status_code=200)
    except Exception as e:
        print("\nUnexpected error in webhook handler:")
        traceback.print_exc()
        return Response(status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)