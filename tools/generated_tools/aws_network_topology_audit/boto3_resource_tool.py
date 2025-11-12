"""
AWS Network Topology Visualizer - Boto3 Resource Tool

This module provides tools for creating and managing AWS resource objects,
which offer a higher-level, object-oriented interface to AWS services.
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
def boto3_resource(
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
    Create an AWS boto3 resource object with support for cross-region and cross-account access.
    
    This tool creates a boto3 resource for the specified AWS service, with options for
    using different regions, profiles, and assuming roles for cross-account access.
    Resource objects provide a higher-level, object-oriented interface to AWS services.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'dynamodb', 's3')
        region_name: AWS region name (e.g., 'us-east-1'). If None, uses default region.
        profile_name: AWS profile name from ~/.aws/credentials. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        endpoint_url: Alternative endpoint URL for the service
        use_ssl: Whether to use SSL when communicating with the endpoint
        verify: Whether to verify SSL certificates or path to CA bundle
        config: Additional configuration parameters for the resource
        
    Returns:
        Dictionary with resource information and status:
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
        
        # Create resource with specified configuration
        resource_kwargs = {
            'region_name': actual_region
        }
        
        if endpoint_url:
            resource_kwargs['endpoint_url'] = endpoint_url
        
        resource_kwargs['use_ssl'] = use_ssl
        resource_kwargs['verify'] = verify
        
        if config:
            resource_kwargs['config'] = boto3.session.Config(**config)
        
        # Check if service supports resource interface
        resource_services = ['ec2', 's3', 'dynamodb', 'sqs', 'sns', 'iam', 'glacier', 'cloudformation']
        if service_name not in resource_services:
            return {
                "status": "error",
                "error": f"Service '{service_name}' does not support the resource interface. Consider using boto3_client instead."
            }
        
        resource = session.resource(service_name, **resource_kwargs)
        
        # Get available regions for the service
        try:
            ec2_client = session.client('ec2')
            regions_response = ec2_client.describe_regions()
            result["available_regions"] = [region['RegionName'] for region in regions_response['Regions']]
        except ClientError:
            # Some services may not be available in all regions
            logger.warning("Could not retrieve available regions")
            result["available_regions"] = []
        
        # Test the resource with a simple operation
        try:
            if service_name == 'ec2':
                list(resource.vpcs.limit(5))
            elif service_name == 's3':
                list(resource.buckets.limit(5))
            elif service_name == 'dynamodb':
                list(resource.tables.limit(5))
            # Add more service-specific tests as needed
            logger.info(f"Successfully created and tested {service_name} resource in {actual_region}")
        except ClientError as e:
            logger.warning(f"Resource created but test operation failed: {str(e)}")
            # We don't return an error here as the resource was created successfully
        
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
def boto3_multi_region_resource(
    service_name: str,
    regions: List[str],
    profile_name: Optional[str] = None,
    role_arn: Optional[str] = None,
    session_name: str = "NetworkTopologyAudit",
    session_duration: int = 3600,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create multiple AWS boto3 resource objects across different regions.
    
    This tool creates boto3 resources for the specified AWS service across multiple regions,
    which is useful for collecting network resources across an entire AWS environment.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 's3')
        regions: List of AWS region names to create resources for
        profile_name: AWS profile name from ~/.aws/credentials. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        config: Additional configuration parameters for the resources
        
    Returns:
        Dictionary with resource creation results:
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
            "successful_regions": list of regions where resource creation succeeded,
            "failed_regions": list of regions where resource creation failed,
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
        
        # Check if service supports resource interface
        resource_services = ['ec2', 's3', 'dynamodb', 'sqs', 'sns', 'iam', 'glacier', 'cloudformation']
        if service_name not in resource_services:
            return {
                "status": "error",
                "error": f"Service '{service_name}' does not support the resource interface. Consider using boto3_multi_region_client instead."
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
        
        # Create resources for each region
        for region in regions:
            try:
                resource_kwargs = {'region_name': region}
                
                if config:
                    resource_kwargs['config'] = boto3.session.Config(**config)
                
                resource = session.resource(service_name, **resource_kwargs)
                
                # Test the resource with a simple operation
                try:
                    if service_name == 'ec2':
                        list(resource.vpcs.limit(5))
                    elif service_name == 's3':
                        list(resource.buckets.limit(5))
                    elif service_name == 'dynamodb':
                        list(resource.tables.limit(5))
                    # Add more service-specific tests as needed
                    
                    result["regions"][region] = {"status": "success"}
                    result["successful_regions"].append(region)
                except ClientError as e:
                    result["regions"][region] = {
                        "status": "error",
                        "error": f"Resource test failed: {str(e)}"
                    }
                    result["failed_regions"].append(region)
                    
            except Exception as e:
                result["regions"][region] = {
                    "status": "error",
                    "error": f"Failed to create resource: {str(e)}"
                }
                result["failed_regions"].append(region)
        
        # Update overall status based on results
        if len(result["successful_regions"]) == 0:
            result["status"] = "error"
            result["error"] = "Failed to create resources in all specified regions"
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
def boto3_multi_account_resource(
    service_name: str,
    accounts: List[Dict[str, str]],
    region_name: Optional[str] = None,
    session_name: str = "NetworkTopologyAudit",
    session_duration: int = 3600,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create AWS boto3 resource objects across multiple AWS accounts.
    
    This tool creates boto3 resources for the specified AWS service across multiple accounts,
    which is useful for collecting network resources across an organization.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 's3')
        accounts: List of account configurations, each containing:
                 - 'account_id': AWS account ID
                 - 'role_name': Name of the role to assume (will be combined with account_id)
                 - 'profile_name': (optional) AWS profile to use for this account
        region_name: AWS region name to use for all resources. If None, uses default region.
        session_name: Name for the assumed role session
        session_duration: Duration of the assumed role session in seconds (default: 3600)
        config: Additional configuration parameters for the resources
        
    Returns:
        Dictionary with resource creation results:
        {
            "status": "success" or "partial_success" or "error",
            "service": service name,
            "region": region name used,
            "accounts": {
                "account_id1": {"status": "success" or "error", "error": "error message if applicable"},
                "account_id2": {"status": "success" or "error", "error": "error message if applicable"},
                ...
            },
            "successful_accounts": list of account IDs where resource creation succeeded,
            "failed_accounts": list of account IDs where resource creation failed,
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
        
        # Check if service supports resource interface
        resource_services = ['ec2', 's3', 'dynamodb', 'sqs', 'sns', 'iam', 'glacier', 'cloudformation']
        if service_name not in resource_services:
            return {
                "status": "error",
                "error": f"Service '{service_name}' does not support the resource interface. Consider using boto3_multi_account_client instead."
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
                
                # Create resource
                resource_kwargs = {}
                if region_name:
                    resource_kwargs['region_name'] = region_name
                
                if config:
                    resource_kwargs['config'] = boto3.session.Config(**config)
                
                resource = cross_account_session.resource(service_name, **resource_kwargs)
                
                # Test the resource with a simple operation
                try:
                    if service_name == 'ec2':
                        list(resource.vpcs.limit(5))
                    elif service_name == 's3':
                        list(resource.buckets.limit(5))
                    elif service_name == 'dynamodb':
                        list(resource.tables.limit(5))
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
                        "error": f"Resource test failed: {str(e)}",
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
            result["error"] = "Failed to create resources for all specified accounts"
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
def boto3_resource_collection(
    service_name: str,
    resource_type: str,
    region_name: Optional[str] = None,
    profile_name: Optional[str] = None,
    role_arn: Optional[str] = None,
    filters: Optional[List[Dict[str, Any]]] = None,
    max_items: int = 100,
    use_cache: bool = True,
    cache_ttl: int = 3600
) -> Dict[str, Any]:
    """
    Collect AWS resources of a specific type using the boto3 resource interface.
    
    This tool collects AWS resources of a specified type (e.g., VPCs, subnets)
    using the boto3 resource interface, with support for filtering and caching.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 's3')
        resource_type: Type of resource to collect (e.g., 'vpc', 'subnet', 'bucket')
        region_name: AWS region name. If None, uses default region.
        profile_name: AWS profile name. If None, uses default profile.
        role_arn: ARN of IAM role to assume for cross-account access
        filters: List of filters to apply to the resource collection
        max_items: Maximum number of items to collect (default: 100)
        use_cache: Whether to use cached results if available (default: True)
        cache_ttl: Time-to-live for cache in seconds (default: 3600)
        
    Returns:
        Dictionary with collection results:
        {
            "status": "success" or "error",
            "service": service name,
            "resource_type": resource type,
            "region": region name used,
            "profile": profile name used,
            "assumed_role": role ARN if used,
            "count": number of resources collected,
            "resources": list of collected resources,
            "from_cache": whether results were retrieved from cache,
            "error": error message if status is "error"
        }
    """
    try:
        result = {
            "status": "success",
            "service": service_name,
            "resource_type": resource_type,
            "region": region_name,
            "profile": profile_name,
            "assumed_role": role_arn if role_arn else None,
            "count": 0,
            "resources": [],
            "from_cache": False
        }
        
        # Check if service supports resource interface
        resource_services = ['ec2', 's3', 'dynamodb', 'sqs', 'sns', 'iam', 'glacier', 'cloudformation']
        if service_name not in resource_services:
            return {
                "status": "error",
                "error": f"Service '{service_name}' does not support the resource interface."
            }
        
        # Define cache file path
        cache_key = f"{service_name}_{resource_type}_{region_name or 'default'}_{profile_name or 'default'}"
        if role_arn:
            cache_key += f"_{role_arn.split('/')[-1]}"
        if filters:
            cache_key += f"_{hash(json.dumps(filters, sort_keys=True))}"
        
        cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        
        # Check cache if enabled
        if use_cache and os.path.exists(cache_file):
            cache_mtime = os.path.getmtime(cache_file)
            if (cache_ttl == 0) or (time.time() - cache_mtime <= cache_ttl):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    result.update({
                        "count": len(cache_data),
                        "resources": cache_data,
                        "from_cache": True
                    })
                    
                    logger.info(f"Retrieved {len(cache_data)} {resource_type} resources from cache")
                    return result
                except Exception as e:
                    logger.warning(f"Failed to read cache: {str(e)}")
                    # Continue with fresh collection
        
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
        
        # Create resource
        resource = session.resource(service_name, region_name=actual_region)
        
        # Collect resources based on service and resource type
        collected_resources = []
        
        try:
            if service_name == 'ec2':
                if resource_type == 'vpc':
                    collection = resource.vpcs.filter(Filters=filters) if filters else resource.vpcs.all()
                    for item in collection:
                        vpc_data = {
                            'id': item.id,
                            'cidr_block': item.cidr_block,
                            'state': item.state,
                            'is_default': item.is_default,
                            'dhcp_options_id': item.dhcp_options_id,
                            'owner_id': item.owner_id,
                            'tags': [{t['Key']: t['Value']} for t in item.tags] if item.tags else []
                        }
                        collected_resources.append(vpc_data)
                        
                elif resource_type == 'subnet':
                    collection = resource.subnets.filter(Filters=filters) if filters else resource.subnets.all()
                    for item in collection:
                        subnet_data = {
                            'id': item.id,
                            'vpc_id': item.vpc_id,
                            'cidr_block': item.cidr_block,
                            'availability_zone': item.availability_zone,
                            'available_ip_address_count': item.available_ip_address_count,
                            'default_for_az': item.default_for_az,
                            'map_public_ip_on_launch': item.map_public_ip_on_launch,
                            'state': item.state,
                            'tags': [{t['Key']: t['Value']} for t in item.tags] if item.tags else []
                        }
                        collected_resources.append(subnet_data)
                        
                elif resource_type == 'security_group':
                    collection = resource.security_groups.filter(Filters=filters) if filters else resource.security_groups.all()
                    for item in collection:
                        sg_data = {
                            'id': item.id,
                            'name': item.group_name,
                            'description': item.description,
                            'vpc_id': item.vpc_id,
                            'ip_permissions': item.ip_permissions,
                            'ip_permissions_egress': item.ip_permissions_egress,
                            'tags': [{t['Key']: t['Value']} for t in item.tags] if item.tags else []
                        }
                        collected_resources.append(sg_data)
                
                elif resource_type == 'route_table':
                    collection = resource.route_tables.filter(Filters=filters) if filters else resource.route_tables.all()
                    for item in collection:
                        rt_data = {
                            'id': item.id,
                            'vpc_id': item.vpc_id,
                            'routes': [{
                                'destination_cidr_block': r.get('DestinationCidrBlock', ''),
                                'destination_ipv6_cidr_block': r.get('DestinationIpv6CidrBlock', ''),
                                'gateway_id': r.get('GatewayId', ''),
                                'instance_id': r.get('InstanceId', ''),
                                'nat_gateway_id': r.get('NatGatewayId', ''),
                                'transit_gateway_id': r.get('TransitGatewayId', ''),
                                'vpc_peering_connection_id': r.get('VpcPeeringConnectionId', ''),
                                'state': r.get('State', '')
                            } for r in item.routes],
                            'associations': [{
                                'id': a.get('RouteTableAssociationId', ''),
                                'subnet_id': a.get('SubnetId', ''),
                                'gateway_id': a.get('GatewayId', ''),
                                'main': a.get('Main', False)
                            } for a in item.associations],
                            'tags': [{t['Key']: t['Value']} for t in item.tags] if item.tags else []
                        }
                        collected_resources.append(rt_data)
                
                # Add more EC2 resource types as needed
                
            elif service_name == 's3':
                if resource_type == 'bucket':
                    for item in resource.buckets.all():
                        bucket_data = {
                            'name': item.name,
                            'creation_date': item.creation_date.isoformat() if item.creation_date else None
                        }
                        collected_resources.append(bucket_data)
                
            # Add more services and resource types as needed
                
            else:
                return {
                    "status": "error",
                    "error": f"Resource type '{resource_type}' not supported for service '{service_name}'"
                }
            
            # Limit the number of resources
            collected_resources = collected_resources[:max_items]
            
            # Update result
            result.update({
                "count": len(collected_resources),
                "resources": collected_resources
            })
            
            # Cache the results if caching is enabled
            if use_cache:
                try:
                    with open(cache_file, 'w') as f:
                        json.dump(collected_resources, f)
                    logger.info(f"Cached {len(collected_resources)} {resource_type} resources")
                except Exception as e:
                    logger.warning(f"Failed to write cache: {str(e)}")
            
            return result
            
        except ClientError as e:
            return {
                "status": "error",
                "error": f"AWS client error: {str(e)}"
            }
        
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

# Import missing module
import time