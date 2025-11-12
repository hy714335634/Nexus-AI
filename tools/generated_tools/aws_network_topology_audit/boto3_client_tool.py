"""
AWS Network Topology Visualizer - Boto3 Client Tool

This module provides tools for creating and managing AWS API clients,
supporting cross-region and cross-account access.
"""

from typing import Dict, List, Optional, Any, Union
import os
import json
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound
from strands import tool

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Cache directory
CACHE_DIR = os.path.join(".cache", "aws_network_topology_visualizer")
os.makedirs(CACHE_DIR, exist_ok=True)

@tool
def boto3_client(
    service_name: str,
    region_name: Optional[str] = None,
    profile_name: Optional[str] = None,
    role_arn: Optional[str] = None,
    session_name: str = "NetworkTopologyAudit",
    session_duration: int = 3600,
    endpoint_url: Optional[str] = None,
    use_ssl: bool = True,
    verify: Union[bool, str] = True,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an AWS boto3 client with support for cross-region and cross-account access.
    
    This tool creates a boto3 client for the specified AWS service, with options for
    using different regions, profiles, and assuming roles for cross-account access.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'vpc', 'cloudformation')
        region_name: AWS region name (e.g., 'us-east-1'). If None, uses default region.
        profile_name: AWS profile name from ~/.aws/credentials. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        endpoint_url: Alternative endpoint URL for the service
        use_ssl: Whether to use SSL when communicating with the endpoint
        verify: Whether to verify SSL certificates or path to CA bundle
        config: Additional configuration parameters for the client
        
    Returns:
        Dictionary with client information and status:
        {
            "status": "success" or "error",
            "service": service name,
            "region": region name used,
            "profile": profile name used,
            "assumed_role": role ARN if used,
            "available_regions": list of available regions for the service,
            "error": error message if status is "error"
        }
    
    Raises:
        Various boto3 and botocore exceptions which are caught and returned as error messages.
    """
    try:
        result = {
            "status": "success",
            "service": service_name,
            "region": region_name,
            "profile": profile_name,
            "assumed_role": role_arn if role_arn else None,
            "available_regions": []
        }
        
        # Create session with profile if specified
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name)
                logger.info(f"Created session using profile: {profile_name}")
            except ProfileNotFound:
                return {
                    "status": "error",
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        else:
            session = boto3.Session()
            logger.info("Created session using default profile")
        
        # Assume role if specified
        if role_arn:
            sts_client = session.client('sts')
            try:
                response = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=session_name,
                    DurationSeconds=session_duration
                )
                
                credentials = response['Credentials']
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=region_name
                )
                logger.info(f"Assumed role: {role_arn}")
                result["assumed_role"] = role_arn
            except ClientError as e:
                return {
                    "status": "error",
                    "error": f"Failed to assume role {role_arn}: {str(e)}"
                }
        
        # Get the actual region being used
        actual_region = region_name or session.region_name
        if not actual_region:
            return {
                "status": "error",
                "error": "No region specified and no default region found in AWS configuration"
            }
        
        result["region"] = actual_region
        
        # Create client with specified configuration
        client_kwargs = {
            'region_name': actual_region
        }
        
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
        
        client_kwargs['use_ssl'] = use_ssl
        client_kwargs['verify'] = verify
        
        if config:
            client_kwargs['config'] = boto3.session.Config(**config)
        
        client = session.client(service_name, **client_kwargs)
        
        # Get available regions for the service
        try:
            ec2_client = session.client('ec2')
            regions_response = ec2_client.describe_regions()
            result["available_regions"] = [region['RegionName'] for region in regions_response['Regions']]
        except ClientError:
            # Some services may not be available in all regions
            logger.warning("Could not retrieve available regions")
            result["available_regions"] = []
        
        # Test the client with a simple operation
        try:
            if service_name == 'ec2':
                client.describe_vpcs(MaxResults=5)
            elif service_name == 'cloudformation':
                client.list_stacks(MaxResults=5)
            # Add more service-specific tests as needed
            logger.info(f"Successfully created and tested {service_name} client in {actual_region}")
        except ClientError as e:
            logger.warning(f"Client created but test operation failed: {str(e)}")
            # We don't return an error here as the client was created successfully
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except ClientError as e:
        return {
            "status": "error",
            "error": f"AWS client error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def boto3_multi_region_client(
    service_name: str,
    regions: List[str],
    profile_name: Optional[str] = None,
    role_arn: Optional[str] = None,
    session_name: str = "NetworkTopologyAudit",
    session_duration: int = 3600,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create multiple AWS boto3 clients across different regions.
    
    This tool creates boto3 clients for the specified AWS service across multiple regions,
    which is useful for collecting network resources across an entire AWS environment.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'vpc')
        regions: List of AWS region names to create clients for
        profile_name: AWS profile name from ~/.aws/credentials. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        config: Additional configuration parameters for the clients
        
    Returns:
        Dictionary with client creation results:
        {
            "status": "success" or "partial_success" or "error",
            "service": service name,
            "profile": profile name used,
            "assumed_role": role ARN if used,
            "regions": {
                "region1": {"status": "success" or "error", "error": "error message if applicable"},
                "region2": {"status": "success" or "error", "error": "error message if applicable"},
                ...
            },
            "successful_regions": list of regions where client creation succeeded,
            "failed_regions": list of regions where client creation failed,
            "error": general error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "service": service_name,
            "profile": profile_name,
            "assumed_role": role_arn if role_arn else None,
            "regions": {},
            "successful_regions": [],
            "failed_regions": []
        }
        
        if not regions:
            return {
                "status": "error",
                "error": "No regions specified"
            }
        
        # Create session with profile if specified
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name)
            except ProfileNotFound:
                return {
                    "status": "error",
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        else:
            session = boto3.Session()
        
        # Assume role if specified
        if role_arn:
            sts_client = session.client('sts')
            try:
                response = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=session_name,
                    DurationSeconds=session_duration
                )
                
                credentials = response['Credentials']
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                result["assumed_role"] = role_arn
            except ClientError as e:
                return {
                    "status": "error",
                    "error": f"Failed to assume role {role_arn}: {str(e)}"
                }
        
        # Create clients for each region
        for region in regions:
            try:
                client_kwargs = {'region_name': region}
                
                if config:
                    client_kwargs['config'] = boto3.session.Config(**config)
                
                client = session.client(service_name, **client_kwargs)
                
                # Test the client with a simple operation
                try:
                    if service_name == 'ec2':
                        client.describe_vpcs(MaxResults=5)
                    elif service_name == 'cloudformation':
                        client.list_stacks(MaxResults=5)
                    # Add more service-specific tests as needed
                    
                    result["regions"][region] = {"status": "success"}
                    result["successful_regions"].append(region)
                except ClientError as e:
                    result["regions"][region] = {
                        "status": "error",
                        "error": f"Client test failed: {str(e)}"
                    }
                    result["failed_regions"].append(region)
                    
            except Exception as e:
                result["regions"][region] = {
                    "status": "error",
                    "error": f"Failed to create client: {str(e)}"
                }
                result["failed_regions"].append(region)
        
        # Update overall status based on results
        if len(result["successful_regions"]) == 0:
            result["status"] = "error"
            result["error"] = "Failed to create clients in all specified regions"
        elif len(result["failed_regions"]) > 0:
            result["status"] = "partial_success"
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def boto3_multi_account_client(
    service_name: str,
    accounts: List[Dict[str, str]],
    region_name: Optional[str] = None,
    session_name: str = "NetworkTopologyAudit",
    session_duration: int = 3600,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create AWS boto3 clients across multiple AWS accounts.
    
    This tool creates boto3 clients for the specified AWS service across multiple accounts,
    which is useful for collecting network resources across an organization.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'vpc')
        accounts: List of account configurations, each containing:
                 - 'account_id': AWS account ID
                 - 'role_name': Name of the role to assume (will be combined with account_id)
                 - 'profile_name': (optional) AWS profile to use for this account
        region_name: AWS region name to use for all clients. If None, uses default region.
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        config: Additional configuration parameters for the clients
        
    Returns:
        Dictionary with client creation results:
        {
            "status": "success" or "partial_success" or "error",
            "service": service name,
            "region": region name used,
            "accounts": {
                "account_id1": {"status": "success" or "error", "error": "error message if applicable"},
                "account_id2": {"status": "success" or "error", "error": "error message if applicable"},
                ...
            },
            "successful_accounts": list of account IDs where client creation succeeded,
            "failed_accounts": list of account IDs where client creation failed,
            "error": general error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "service": service_name,
            "region": region_name,
            "accounts": {},
            "successful_accounts": [],
            "failed_accounts": []
        }
        
        if not accounts:
            return {
                "status": "error",
                "error": "No accounts specified"
            }
        
        for account in accounts:
            account_id = account.get('account_id')
            role_name = account.get('role_name')
            profile_name = account.get('profile_name')
            
            if not account_id or not role_name:
                result["accounts"][account_id or "unknown"] = {
                    "status": "error",
                    "error": "Missing required account_id or role_name"
                }
                result["failed_accounts"].append(account_id or "unknown")
                continue
            
            # Construct the role ARN
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
            
            try:
                # Create session with profile if specified
                if profile_name:
                    try:
                        session = boto3.Session(profile_name=profile_name)
                    except ProfileNotFound:
                        result["accounts"][account_id] = {
                            "status": "error",
                            "error": f"AWS profile '{profile_name}' not found"
                        }
                        result["failed_accounts"].append(account_id)
                        continue
                else:
                    session = boto3.Session()
                
                # Assume role
                sts_client = session.client('sts')
                try:
                    response = sts_client.assume_role(
                        RoleArn=role_arn,
                        RoleSessionName=session_name,
                        DurationSeconds=session_duration
                    )
                    
                    credentials = response['Credentials']
                    cross_account_session = boto3.Session(
                        aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken'],
                        region_name=region_name
                    )
                except ClientError as e:
                    result["accounts"][account_id] = {
                        "status": "error",
                        "error": f"Failed to assume role {role_arn}: {str(e)}"
                    }
                    result["failed_accounts"].append(account_id)
                    continue
                
                # Create client
                client_kwargs = {}
                if region_name:
                    client_kwargs['region_name'] = region_name
                
                if config:
                    client_kwargs['config'] = boto3.session.Config(**config)
                
                client = cross_account_session.client(service_name, **client_kwargs)
                
                # Test the client with a simple operation
                try:
                    if service_name == 'ec2':
                        client.describe_vpcs(MaxResults=5)
                    elif service_name == 'cloudformation':
                        client.list_stacks(MaxResults=5)
                    # Add more service-specific tests as needed
                    
                    result["accounts"][account_id] = {
                        "status": "success",
                        "role_arn": role_arn,
                        "profile": profile_name
                    }
                    result["successful_accounts"].append(account_id)
                except ClientError as e:
                    result["accounts"][account_id] = {
                        "status": "error",
                        "error": f"Client test failed: {str(e)}",
                        "role_arn": role_arn,
                        "profile": profile_name
                    }
                    result["failed_accounts"].append(account_id)
                
            except Exception as e:
                result["accounts"][account_id] = {
                    "status": "error",
                    "error": f"Unexpected error: {str(e)}"
                }
                result["failed_accounts"].append(account_id)
        
        # Update overall status based on results
        if len(result["successful_accounts"]) == 0:
            result["status"] = "error"
            result["error"] = "Failed to create clients for all specified accounts"
        elif len(result["failed_accounts"]) > 0:
            result["status"] = "partial_success"
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }


@tool
def boto3_client_with_retry(
    service_name: str,
    region_name: Optional[str] = None,
    profile_name: Optional[str] = None,
    role_arn: Optional[str] = None,
    max_retries: int = 5,
    retry_delay: int = 2,
    exponential_backoff: bool = True,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create an AWS boto3 client with advanced retry capabilities.
    
    This tool creates a boto3 client with configurable retry settings for improved
    reliability when dealing with API throttling or temporary network issues.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'vpc')
        region_name: AWS region name. If None, uses default region.
        profile_name: AWS profile name. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        max_retries: Maximum number of retry attempts (default: 5)
        retry_delay: Base delay between retries in seconds (default: 2)
        exponential_backoff: Whether to use exponential backoff for retries (default: True)
        config: Additional configuration parameters for the client
        
    Returns:
        Dictionary with client information and retry configuration:
        {
            "status": "success" or "error",
            "service": service name,
            "region": region name used,
            "profile": profile name used,
            "assumed_role": role ARN if used,
            "retry_config": {
                "max_retries": max retries value,
                "retry_delay": retry delay value,
                "exponential_backoff": exponential backoff setting
            },
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "service": service_name,
            "region": region_name,
            "profile": profile_name,
            "assumed_role": role_arn if role_arn else None,
            "retry_config": {
                "max_retries": max_retries,
                "retry_delay": retry_delay,
                "exponential_backoff": exponential_backoff
            }
        }
        
        # Create session with profile if specified
        if profile_name:
            try:
                session = boto3.Session(profile_name=profile_name)
            except ProfileNotFound:
                return {
                    "status": "error",
                    "error": f"AWS profile '{profile_name}' not found. Check your ~/.aws/credentials file."
                }
        else:
            session = boto3.Session()
        
        # Assume role if specified
        if role_arn:
            sts_client = session.client('sts')
            try:
                response = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="NetworkTopologyAudit",
                    DurationSeconds=3600
                )
                
                credentials = response['Credentials']
                session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken'],
                    region_name=region_name
                )
                result["assumed_role"] = role_arn
            except ClientError as e:
                return {
                    "status": "error",
                    "error": f"Failed to assume role {role_arn}: {str(e)}"
                }
        
        # Get the actual region being used
        actual_region = region_name or session.region_name
        if not actual_region:
            return {
                "status": "error",
                "error": "No region specified and no default region found in AWS configuration"
            }
        
        result["region"] = actual_region
        
        # Create retry configuration
        retry_config = {
            'max_attempts': max_retries + 1,  # +1 because it includes the initial attempt
            'mode': 'adaptive' if exponential_backoff else 'standard'
        }
        
        # Create client with retry configuration
        client_config = boto3.session.Config(
            retries=retry_config,
            region_name=actual_region
        )
        
        if config:
            # Merge with user-provided config
            for key, value in config.items():
                setattr(client_config, key, value)
        
        client = session.client(service_name, config=client_config)
        
        # Test the client with a simple operation
        try:
            if service_name == 'ec2':
                client.describe_vpcs(MaxResults=5)
            elif service_name == 'cloudformation':
                client.list_stacks(MaxResults=5)
            # Add more service-specific tests as needed
            logger.info(f"Successfully created and tested {service_name} client in {actual_region} with retry configuration")
        except ClientError as e:
            logger.warning(f"Client created but test operation failed: {str(e)}")
            # We don't return an error here as the client was created successfully
        
        return result
        
    except NoCredentialsError:
        return {
            "status": "error",
            "error": "No AWS credentials found. Configure AWS credentials via environment variables, ~/.aws/credentials, or instance profile."
        }
    except ClientError as e:
        return {
            "status": "error",
            "error": f"AWS client error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}"
        }