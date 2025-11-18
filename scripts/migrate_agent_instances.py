#!/usr/bin/env python3
"""
Migration script to add new fields to AgentInstances table
Adds: agentcore_runtime_arn, agentcore_runtime_alias, agentcore_region, 
      deployment_stage, last_deployment_job_id, model_id, invoke_url, runtime_config
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import boto3
from botocore.exceptions import ClientError
import logging
from datetime import datetime
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REGION = 'us-west-2'
TABLE_NAME = 'AgentInstances'

def get_dynamodb_client():
    """Initialize DynamoDB client"""
    return boto3.resource('dynamodb', region_name=REGION)

def backfill_agent_records():
    """Backfill existing agent records with new fields"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Scan all existing records
        response = table.scan()
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        logger.info(f"Found {len(items)} agent records to migrate")
        
        updated_count = 0
        for item in items:
            agent_id = item.get('agent_id')
            
            # Prepare update expression
            update_expr_parts = []
            expr_attr_values = {}
            
            # Add new fields if they don't exist
            if 'agentcore_runtime_arn' not in item:
                update_expr_parts.append('agentcore_runtime_arn = :runtime_arn')
                expr_attr_values[':runtime_arn'] = None
            
            if 'agentcore_runtime_alias' not in item:
                update_expr_parts.append('agentcore_runtime_alias = :runtime_alias')
                expr_attr_values[':runtime_alias'] = 'DEFAULT'
            
            if 'agentcore_region' not in item:
                update_expr_parts.append('agentcore_region = :region')
                expr_attr_values[':region'] = REGION
            
            if 'deployment_stage' not in item:
                # Set based on existing deployment_status
                deployment_status = item.get('deployment_status', 'pending')
                if deployment_status == 'deployed':
                    stage = 'deployed'
                elif deployment_status == 'failed':
                    stage = 'failed'
                else:
                    stage = 'built'
                update_expr_parts.append('deployment_stage = :stage')
                expr_attr_values[':stage'] = stage
            
            if 'last_deployment_job_id' not in item:
                update_expr_parts.append('last_deployment_job_id = :job_id')
                expr_attr_values[':job_id'] = None
            
            if 'model_id' not in item:
                update_expr_parts.append('model_id = :model_id')
                expr_attr_values[':model_id'] = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
            
            if 'invoke_url' not in item:
                update_expr_parts.append('invoke_url = :invoke_url')
                expr_attr_values[':invoke_url'] = None
            
            if 'runtime_config' not in item:
                update_expr_parts.append('runtime_config = :runtime_config')
                expr_attr_values[':runtime_config'] = {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 4096
                }
            
            # Only update if there are fields to add
            if update_expr_parts:
                update_expression = 'SET ' + ', '.join(update_expr_parts)
                
                try:
                    table.update_item(
                        Key={'agent_id': agent_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expr_attr_values
                    )
                    updated_count += 1
                    logger.info(f"Updated agent: {agent_id}")
                except ClientError as e:
                    logger.error(f"Failed to update agent {agent_id}: {e}")
        
        logger.info(f"Migration completed. Updated {updated_count} records.")
        
    except ClientError as e:
        logger.error(f"Error scanning table: {e}")
        raise

def verify_migration():
    """Verify that migration was successful"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        response = table.scan(Limit=5)
        items = response.get('Items', [])
        
        if not items:
            logger.warning("No items found in table")
            return
        
        logger.info("Sample records after migration:")
        for item in items:
            logger.info(f"Agent: {item.get('agent_id')}")
            logger.info(f"  - deployment_stage: {item.get('deployment_stage')}")
            logger.info(f"  - agentcore_runtime_arn: {item.get('agentcore_runtime_arn')}")
            logger.info(f"  - model_id: {item.get('model_id')}")
            logger.info(f"  - runtime_config: {item.get('runtime_config')}")
            
    except ClientError as e:
        logger.error(f"Error verifying migration: {e}")

if __name__ == '__main__':
    logger.info("Starting AgentInstances table migration...")
    logger.info(f"Region: {REGION}")
    logger.info(f"Table: {TABLE_NAME}")
    
    # Confirm before proceeding
    response = input("Proceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        logger.info("Migration cancelled")
        sys.exit(0)
    
    backfill_agent_records()
    verify_migration()
    
    logger.info("Migration completed successfully!")
