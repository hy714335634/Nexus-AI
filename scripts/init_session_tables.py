#!/usr/bin/env python3
"""
Initialize AgentSessions and AgentSessionMessages tables
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.database.dynamodb_client import DynamoDBClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize session tables"""
    logger.info("Initializing AgentSessions and AgentSessionMessages tables...")
    
    try:
        db_client = DynamoDBClient()
        
        # Create the new tables
        logger.info("Creating AgentSessions table...")
        db_client._create_agent_sessions_table()
        
        logger.info("Creating AgentSessionMessages table...")
        db_client._create_agent_session_messages_table()
        
        logger.info("Tables created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

if __name__ == '__main__':
    main()
