from fastapi import FastAPI

import uvicorn
import google.generativeai as genai
import os

from src.config import settings
from src.routers import discourse_routes

# Initialize FastAPI app
app = FastAPI(title="Discourse Bot API")

# Initialize Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# Include routers
app.include_router(
    discourse_routes.router,
    prefix="/api",
    tags=["discourse"]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
