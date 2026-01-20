#!/bin/bash

# Development startup script for Nexus-AI Platform API v2

echo "🚀 Starting Nexus-AI Platform API v2 Development Environment"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your configuration"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set up DynamoDB tables (v2)
echo "🗄️  Setting up DynamoDB tables..."
python scripts/init_infrastructure.py --tables-only

# Start services with docker-compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d dynamodb-local

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Start FastAPI application (v2)
echo "🌐 Starting FastAPI application..."
echo "API will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"

uvicorn api.v2.main:app --host 0.0.0.0 --port 8000 --reload