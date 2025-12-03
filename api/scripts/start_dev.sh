#!/bin/bash

# Development startup script for Nexus-AI Platform API

echo "🚀 Starting Nexus-AI Platform API Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your configuration"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set up DynamoDB tables
echo "🗄️  Setting up DynamoDB tables..."
python scripts/setup_tables.py

# Start services with docker-compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d dynamodb-local

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Note: Async tasks are handled by ThreadPoolExecutor, no separate worker needed

# Start FastAPI application
echo "🌐 Starting FastAPI application..."
echo "API will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
# Note: No Celery Flower needed - tasks are handled internally

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload