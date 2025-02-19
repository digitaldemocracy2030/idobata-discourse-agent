# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY discourse_bot.py .

# Expose port 8000
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "discourse_bot:app", "--host", "0.0.0.0", "--port", "8000"]