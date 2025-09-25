#!/usr/bin/env python3
"""
Script to set up DynamoDB tables for Nexus-AI Platform API
"""
import asyncio
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database.dynamodb_client import db_client
from api.core.config import settings

def setup_tables():
    """Set up all required DynamoDB tables"""
    print("Setting up DynamoDB tables...")
    print(f"Region: {settings.DYNAMODB_REGION}")
    if settings.DYNAMODB_ENDPOINT_URL:
        print(f"Endpoint: {settings.DYNAMODB_ENDPOINT_URL}")
    
    try:
        db_client.create_tables()
        print("✅ All tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    setup_tables()