# Discourse Bot API

A FastAPI-based bot for interacting with Discourse forums. This API provides endpoints for creating topics and listing categories.

## Setup

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables by copying `.env.example` and updating with your values:
```bash
cp .env.example .env
```

Required environment variables:
- `DISCOURSE_API_KEY`: Your Discourse API key
- `DISCOURSE_BASE_URL`: Your Discourse instance URL (e.g., https://community.yourdomain.com)
- `APP_API_KEY`: API key for authenticating with this bot API

## Running the Server

Start the server with:
```bash
uvicorn discourse_bot:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

### Authentication

All endpoints require an API key passed in the `X-API-Key` header.

### Endpoints

#### GET /categories
Lists all available Discourse categories.

**Response**: JSON object containing all categories in your Discourse instance.

#### POST /topics
Creates a new topic in Discourse.

**Parameters**:
- `title`: Topic title
- `content`: Topic content/body
- `category_id`: ID of the category to post in

**Response**: JSON object containing the created topic details.

### Interactive Documentation

FastAPI provides interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
