import httpx
import asyncio
import json
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Get environment variables with validation
DISCOURSE_API_KEY = os.getenv('DISCOURSE_API_KEY')
DISCOURSE_API_USERNAME = os.getenv('DISCOURSE_API_USERNAME')
DISCOURSE_BASE_URL = os.getenv('DISCOURSE_BASE_URL')

# Validate environment variables
def validate_env_vars():
    missing_vars = []
    if not DISCOURSE_API_KEY:
        missing_vars.append('DISCOURSE_API_KEY')
    if not DISCOURSE_API_USERNAME:
        missing_vars.append('DISCOURSE_API_USERNAME')
    if not DISCOURSE_BASE_URL:
        missing_vars.append('DISCOURSE_BASE_URL')
    
    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease set these variables in your .env file")
        return False
    return True

async def get_categories():
    if not validate_env_vars():
        return None

    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': DISCOURSE_API_USERNAME,
        'Content-Type': 'application/json'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{DISCOURSE_BASE_URL}/categories.json",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                categories = result.get('category_list', {}).get('categories', [])
                print("\nAvailable categories:")
                for category in categories:
                    print(f"ID: {category['id']}, Name: {category['name']}")
                
                # Return the first available category ID that's not restricted
                for category in categories:
                    if not category.get('read_restricted', True):
                        return category['id']
                return None
            else:
                print(f"\nFailed to fetch categories. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None

    except Exception as e:
        print(f"Error fetching categories: {str(e)}")
        return None

async def create_test_topic():
    if not validate_env_vars():
        return None

    # Get a valid category ID first
    category_id = await get_categories()
    if not category_id:
        print("Failed to find a valid category to post in")
        return None

    # Create a unique title with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"Test Topic for Moderation ({timestamp})"

    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': DISCOURSE_API_USERNAME,
        'Content-Type': 'application/json'
    }

    topic_data = {
        'title': title,
        'raw': 'This is a test topic for testing moderation functionality.',
        'category': category_id
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DISCOURSE_BASE_URL}/posts.json",
                headers=headers,
                json=topic_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\nTopic created successfully:")
                print(f"Topic ID: {result['topic_id']}")
                return result['topic_id']
            else:
                print(f"\nFailed to create topic. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None

    except Exception as e:
        print(f"Error creating topic: {str(e)}")
        print("Please check your DISCOURSE_BASE_URL and ensure it's correct (should include http:// or https://)")
        return None

async def create_inappropriate_post(topic_id):
    if not validate_env_vars():
        return None

    headers = {
        'Api-Key': DISCOURSE_API_KEY,
        'Api-Username': DISCOURSE_API_USERNAME,
        'Content-Type': 'application/json'
    }

    post_data = {
        'topic_id': topic_id,
        'raw': 'This is a very inappropriate test post containing offensive content, hate speech, and vulgar language! @#$%^&*'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DISCOURSE_BASE_URL}/posts.json",
                headers=headers,
                json=post_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\nInappropriate post created successfully:")
                print(f"Post ID: {result['id']}")
                return result['id']
            else:
                print(f"\nFailed to create inappropriate post. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return None

    except Exception as e:
        print(f"Error creating inappropriate post: {str(e)}")
        return None

async def test_inappropriate_post():
    # First create a test topic
    topic_id = await create_test_topic()
    
    if not topic_id:
        print("Cannot proceed with test - failed to create topic")
        return

    try:
        # Create an inappropriate post in the topic
        inappropriate_post_id = await create_inappropriate_post(topic_id)
        
        if inappropriate_post_id:
            print("\nTest completed successfully")
            print(f"Topic ID: {topic_id}")
            print(f"Inappropriate Post ID: {inappropriate_post_id}")
            print("\nWaiting for moderation to process...")
            # Wait a bit for moderation to process
            await asyncio.sleep(5)
        else:
            print("\nTest failed - could not create inappropriate post")

    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    print("Testing inappropriate post moderation...")
    asyncio.run(test_inappropriate_post())