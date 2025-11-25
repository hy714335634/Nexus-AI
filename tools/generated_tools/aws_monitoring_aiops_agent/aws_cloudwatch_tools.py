"""
AWS CloudWatch client tool for interacting with CloudWatch metrics and alarms.
"""

from typing import Dict, List, Any, Optional, Union, Tuple
import json
import time
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from strands import tool

@tool
def boto3_cloudwatch_client(
    region: str,
    operation: str,
    parameters: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: int = 1,
) -> str:
    """
    Interact with AWS CloudWatch API using boto3.
    
    This tool provides a unified interface for CloudWatch metrics and alarms operations,
    supporting multiple regions, pagination, and error handling with automatic retries.
    
    Args:
        region: AWS region name (e.g., 'us-east-1', 'eu-west-1')
        operation: CloudWatch API operation to perform (e.g., 'get_metric_data', 'describe_alarms')
        parameters: Dictionary of parameters for the specified operation
        max_retries: Maximum number of retry attempts for transient errors (default: 3)
        retry_delay: Initial delay between retries in seconds, with exponential backoff (default: 1)
    
    Returns:
        JSON string containing the operation results or error information
        
    Supported operations:
        - list_metrics: List available CloudWatch metrics
        - get_metric_data: Retrieve metric data points
        - get_metric_statistics: Get statistics for a specific metric
        - describe_alarms: Get information about CloudWatch alarms
        - describe_alarm_history: Get alarm history
        - set_alarm_state: Set the state of an alarm for testing
    """
    try:
        # Initialize CloudWatch client
        session = boto3.Session(region_name=region)
        cloudwatch = session.client('cloudwatch')
        
        # Track pagination for operations that support it
        all_results = {}
        next_token = None
        retry_count = 0
        
        while True:
            try:
                # Add next token to parameters if it exists
                if next_token:
                    parameters['NextToken'] = next_token
                
                # Execute the requested operation
                if operation == 'list_metrics':
                    response = cloudwatch.list_metrics(**parameters)
                elif operation == 'get_metric_data':
                    response = cloudwatch.get_metric_data(**parameters)
                elif operation == 'get_metric_statistics':
                    response = cloudwatch.get_metric_statistics(**parameters)
                elif operation == 'describe_alarms':
                    response = cloudwatch.describe_alarms(**parameters)
                elif operation == 'describe_alarm_history':
                    response = cloudwatch.describe_alarm_history(**parameters)
                elif operation == 'set_alarm_state':
                    response = cloudwatch.set_alarm_state(**parameters)
                else:
                    return json.dumps({
                        'error': f"Unsupported operation: {operation}",
                        'supported_operations': [
                            'list_metrics', 'get_metric_data', 'get_metric_statistics',
                            'describe_alarms', 'describe_alarm_history', 'set_alarm_state'
                        ]
                    })
                
                # Process response based on operation
                if not all_results:
                    # First page of results
                    all_results = {k: v for k, v in response.items() if k != 'ResponseMetadata'}
                else:
                    # Merge subsequent pages
                    for key, value in response.items():
                        if key != 'ResponseMetadata':
                            if isinstance(value, list) and key in all_results:
                                all_results[key].extend(value)
                            else:
                                all_results[key] = value
                
                # Check for next token
                next_token = response.get('NextToken')
                if not next_token:
                    break
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Handle throttling errors with retry logic
                if error_code in ['Throttling', 'ThrottlingException', 'RequestLimitExceeded'] and retry_count < max_retries:
                    retry_count += 1
                    wait_time = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                else:
                    return json.dumps({
                        'error': str(e),
                        'error_code': error_code,
                        'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
                    })
        
        # Return successful results
        return json.dumps(all_results)
        
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'operation': operation,
            'region': region
        })


@tool
def boto3_logs_client(
    region: str,
    operation: str,
    parameters: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: int = 1,
) -> str:
    """
    Interact with AWS CloudWatch Logs API using boto3.
    
    This tool provides a unified interface for CloudWatch Logs operations,
    supporting multiple regions, pagination, and error handling with automatic retries.
    
    Args:
        region: AWS region name (e.g., 'us-east-1', 'eu-west-1')
        operation: CloudWatch Logs API operation to perform
        parameters: Dictionary of parameters for the specified operation
        max_retries: Maximum number of retry attempts for transient errors (default: 3)
        retry_delay: Initial delay between retries in seconds, with exponential backoff (default: 1)
    
    Returns:
        JSON string containing the operation results or error information
        
    Supported operations:
        - describe_log_groups: List available log groups
        - describe_log_streams: List log streams in a log group
        - get_log_events: Retrieve log events from a log stream
        - filter_log_events: Filter log events across log streams
        - start_query: Start a CloudWatch Logs Insights query
        - get_query_results: Get results from a CloudWatch Logs Insights query
        - stop_query: Stop a running CloudWatch Logs Insights query
    """
    try:
        # Initialize CloudWatch Logs client
        session = boto3.Session(region_name=region)
        logs = session.client('logs')
        
        # Track pagination for operations that support it
        all_results = {}
        next_token = None
        retry_count = 0
        
        while True:
            try:
                # Add next token to parameters if it exists
                if next_token:
                    # Different APIs use different parameter names for pagination tokens
                    if operation in ['get_log_events']:
                        parameters['nextToken'] = next_token
                    else:
                        parameters['nextToken'] = next_token
                
                # Execute the requested operation
                if operation == 'describe_log_groups':
                    response = logs.describe_log_groups(**parameters)
                elif operation == 'describe_log_streams':
                    response = logs.describe_log_streams(**parameters)
                elif operation == 'get_log_events':
                    response = logs.get_log_events(**parameters)
                elif operation == 'filter_log_events':
                    response = logs.filter_log_events(**parameters)
                elif operation == 'start_query':
                    response = logs.start_query(**parameters)
                elif operation == 'get_query_results':
                    response = logs.get_query_results(**parameters)
                elif operation == 'stop_query':
                    response = logs.stop_query(**parameters)
                else:
                    return json.dumps({
                        'error': f"Unsupported operation: {operation}",
                        'supported_operations': [
                            'describe_log_groups', 'describe_log_streams', 'get_log_events',
                            'filter_log_events', 'start_query', 'get_query_results', 'stop_query'
                        ]
                    })
                
                # Process response based on operation
                if not all_results:
                    # First page of results
                    all_results = {k: v for k, v in response.items() if k != 'ResponseMetadata'}
                else:
                    # Merge subsequent pages
                    for key, value in response.items():
                        if key != 'ResponseMetadata':
                            if isinstance(value, list) and key in all_results:
                                all_results[key].extend(value)
                            else:
                                all_results[key] = value
                
                # Check for next token (different APIs use different response keys)
                if operation == 'get_log_events':
                    next_token = response.get('nextForwardToken')
                    # Avoid infinite loops by checking if the token is the same
                    if next_token and next_token == parameters.get('nextToken'):
                        break
                else:
                    next_token = response.get('nextToken')
                
                if not next_token:
                    break
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Handle throttling errors with retry logic
                if error_code in ['Throttling', 'ThrottlingException', 'RequestLimitExceeded'] and retry_count < max_retries:
                    retry_count += 1
                    wait_time = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                else:
                    return json.dumps({
                        'error': str(e),
                        'error_code': error_code,
                        'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
                    })
        
        # Return successful results
        return json.dumps(all_results)
        
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'operation': operation,
            'region': region
        })


@tool
def cloudwatch_logs_insights_query(
    region: str,
    query_string: str,
    log_group_names: List[str],
    start_time: Union[str, int],
    end_time: Union[str, int],
    limit: int = 1000,
    wait_for_results: bool = True,
    timeout_seconds: int = 60,
    max_retries: int = 3,
    retry_delay: int = 1,
) -> str:
    """
    Execute CloudWatch Logs Insights queries and retrieve results.
    
    This tool simplifies the process of running CloudWatch Logs Insights queries
    by handling the asynchronous query execution, waiting for results, and pagination.
    
    Args:
        region: AWS region name (e.g., 'us-east-1', 'eu-west-1')
        query_string: The CloudWatch Logs Insights query to execute
        log_group_names: List of log group names to query
        start_time: Start time for the query in ISO8601 format (e.g., '2023-01-01T00:00:00Z') or Unix timestamp
        end_time: End time for the query in ISO8601 format (e.g., '2023-01-01T01:00:00Z') or Unix timestamp
        limit: Maximum number of log events to return (default: 1000)
        wait_for_results: Whether to wait for query completion (default: True)
        timeout_seconds: Maximum time to wait for query results in seconds (default: 60)
        max_retries: Maximum number of retry attempts for transient errors (default: 3)
        retry_delay: Initial delay between retries in seconds, with exponential backoff (default: 1)
    
    Returns:
        JSON string containing the query results or error information
    """
    try:
        # Initialize CloudWatch Logs client
        session = boto3.Session(region_name=region)
        logs = session.client('logs')
        
        # Convert timestamps if provided as strings
        start_timestamp = start_time
        end_timestamp = end_time
        
        if isinstance(start_time, str):
            start_timestamp = int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        if isinstance(end_time, str):
            end_timestamp = int(datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp() * 1000)
        
        # Start the query
        try:
            start_query_response = logs.start_query(
                logGroupNames=log_group_names,
                startTime=start_timestamp,
                endTime=end_timestamp,
                queryString=query_string,
                limit=limit
            )
            
            query_id = start_query_response['queryId']
            
        except ClientError as e:
            return json.dumps({
                'error': f"Failed to start query: {str(e)}",
                'error_code': e.response['Error']['Code'],
                'request_id': e.response.get('ResponseMetadata', {}).get('RequestId', 'unknown')
            })
        
        # Return immediately if not waiting for results
        if not wait_for_results:
            return json.dumps({
                'status': 'query_started',
                'query_id': query_id,
                'message': 'Query started successfully. Use get_query_results operation with boto3_logs_client to retrieve results.'
            })
        
        # Wait for query to complete
        status = 'Running'
        start_time = time.time()
        retry_count = 0
        all_results = []
        
        while status == 'Running':
            # Check if timeout exceeded
            if time.time() - start_time > timeout_seconds:
                try:
                    logs.stop_query(queryId=query_id)
                except:
                    pass  # Ignore errors when stopping query
                
                return json.dumps({
                    'error': f"Query timeout after {timeout_seconds} seconds",
                    'query_id': query_id,
                    'partial_results': all_results if all_results else None
                })
            
            # Wait before checking status
            time.sleep(1)
            
            try:
                # Get query results
                response = logs.get_query_results(queryId=query_id)
                status = response['status']
                
                # If complete or failed, return results
                if status in ['Complete', 'Failed', 'Cancelled']:
                    if status == 'Failed':
                        return json.dumps({
                            'error': 'Query failed',
                            'query_id': query_id,
                            'status': status
                        })
                    elif status == 'Cancelled':
                        return json.dumps({
                            'error': 'Query was cancelled',
                            'query_id': query_id,
                            'status': status
                        })
                    else:
                        # Process and format results
                        results = response['results']
                        statistics = response.get('statistics', {})
                        
                        # Return formatted results
                        return json.dumps({
                            'status': status,
                            'query_id': query_id,
                            'results': results,
                            'statistics': statistics
                        })
                        
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Handle throttling errors with retry logic
                if error_code in ['Throttling', 'ThrottlingException', 'RequestLimitExceeded'] and retry_count < max_retries:
                    retry_count += 1
                    wait_time = retry_delay * (2 ** (retry_count - 1))  # Exponential backoff
                    time.sleep(wait_time)
                    continue
                else:
                    return json.dumps({
                        'error': str(e),
                        'error_code': error_code,
                        'query_id': query_id,
                        'status': 'error'
                    })
        
    except Exception as e:
        return json.dumps({
            'error': str(e),
            'status': 'error'
        })