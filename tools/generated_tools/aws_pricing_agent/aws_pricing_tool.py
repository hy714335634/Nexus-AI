#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AWS Pricing Tool

This module provides tools for interacting with AWS services to retrieve pricing information
for various AWS services including EC2, EBS, S3, network traffic, ELB, RDS, ElastiCache, 
and OpenSearch services. It supports both on-demand and reserved instance pricing across
all AWS regions including China regions.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
DEFAULT_REGION = "us-east-1"
SUPPORTED_SERVICES = [
    "AmazonEC2", "AmazonEBS", "AmazonS3", "AmazonCloudFront", 
    "AmazonRDS", "AmazonElastiCache", "AmazonOpenSearch", "AmazonELB"
]
SERVICE_CODE_MAP = {
    "ec2": "AmazonEC2",
    "ebs": "AmazonEBS",
    "s3": "AmazonS3",
    "network": "AmazonCloudFront",
    "elb": "AmazonELB",
    "rds": "AmazonRDS",
    "elasticache": "AmazonElastiCache",
    "opensearch": "AmazonOpenSearch"
}

# Helper functions
def decimal_default(obj):
    """Helper function to convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def format_response(status: bool, data: Any = None, error: str = None) -> Dict:
    """Format the response in a consistent way."""
    response = {
        "success": status
    }
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return response

@tool
def use_aws(region: str, service_name: str, operation_name: str, parameters: Dict[str, Any], 
            label: str, profile_name: str = None) -> str:
    """Make a boto3 client call with the specified service, operation, and parameters. Boto3 operations are snake_case.

    Args:
        region (str): Region name for calling the operation on AWS boto3
        service_name (str): The name of the AWS service
        operation_name (str): The name of the operation to perform
        parameters (Dict[str, Any]): The parameters for the operation
        label (str): Label of AWS API operations human readable explanation. This is useful for communicating with human.
        profile_name (str, optional): Optional: AWS profile name to use from ~/.aws/credentials. Defaults to default profile if not specified.

    Returns:
        str: JSON string containing the response or error information
    """
    try:
        # Create boto3 session and client
        session_kwargs = {}
        if profile_name:
            session_kwargs["profile_name"] = profile_name
        
        session = boto3.Session(**session_kwargs)
        client = session.client(service_name, region_name=region)
        
        # Get the operation as a callable
        operation = getattr(client, operation_name)
        
        # Call the operation with the provided parameters
        response = operation(**parameters)
        
        # Format and return the response
        return json.dumps(format_response(True, response), default=decimal_default)
    
    except (ClientError, BotoCoreError) as e:
        error_message = f"AWS Error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))
    
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_aws_pricing(service_code: str, region: str, filters: List[Dict[str, Any]] = None, 
                   max_results: int = 10) -> str:
    """Get AWS pricing information for a specific service in a region.

    Args:
        service_code (str): AWS service code (ec2, ebs, s3, network, elb, rds, elasticache, opensearch)
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        filters (List[Dict[str, Any]], optional): List of filters to apply to the pricing data
        max_results (int, optional): Maximum number of results to return. Defaults to 10.

    Returns:
        str: JSON string containing pricing information
    """
    try:
        # Map service code to AWS service code
        if service_code.lower() in SERVICE_CODE_MAP:
            aws_service_code = SERVICE_CODE_MAP[service_code.lower()]
        else:
            return json.dumps(format_response(False, None, f"Unsupported service code: {service_code}"))
        
        # Create pricing client (pricing API is only available in us-east-1 and ap-south-1)
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        
        # Prepare filters
        service_filters = [
            {'Type': 'TERM_MATCH', 'Field': 'serviceCode', 'Value': aws_service_code}
        ]
        
        # Add region filter
        if region:
            # Map region to region description
            region_map = {
                'us-east-1': 'US East (N. Virginia)',
                'us-east-2': 'US East (Ohio)',
                'us-west-1': 'US West (N. California)',
                'us-west-2': 'US West (Oregon)',
                'ca-central-1': 'Canada (Central)',
                'eu-north-1': 'EU (Stockholm)',
                'eu-west-1': 'EU (Ireland)',
                'eu-west-2': 'EU (London)',
                'eu-west-3': 'EU (Paris)',
                'eu-central-1': 'EU (Frankfurt)',
                'ap-northeast-1': 'Asia Pacific (Tokyo)',
                'ap-northeast-2': 'Asia Pacific (Seoul)',
                'ap-northeast-3': 'Asia Pacific (Osaka)',
                'ap-southeast-1': 'Asia Pacific (Singapore)',
                'ap-southeast-2': 'Asia Pacific (Sydney)',
                'ap-south-1': 'Asia Pacific (Mumbai)',
                'sa-east-1': 'South America (Sao Paulo)',
                'cn-north-1': 'China (Beijing)',
                'cn-northwest-1': 'China (Ningxia)'
            }
            
            region_description = region_map.get(region, region)
            service_filters.append({
                'Type': 'TERM_MATCH', 
                'Field': 'regionCode' if 'cn-' in region else 'location', 
                'Value': region if 'cn-' in region else region_description
            })
        
        # Add custom filters if provided
        if filters:
            for filter_item in filters:
                if 'Field' in filter_item and 'Value' in filter_item:
                    service_filters.append({
                        'Type': 'TERM_MATCH',
                        'Field': filter_item['Field'],
                        'Value': filter_item['Value']
                    })
        
        # Get pricing information
        response = pricing_client.get_products(
            ServiceCode=aws_service_code,
            Filters=service_filters,
            MaxResults=max_results
        )
        
        # Process and format the response
        pricing_data = []
        for price_item in response.get('PriceList', []):
            if isinstance(price_item, str):
                price_item = json.loads(price_item)
            pricing_data.append(price_item)
        
        result = {
            "service": aws_service_code,
            "region": region,
            "pricing_data": pricing_data,
            "next_token": response.get('NextToken')
        }
        
        return json.dumps(format_response(True, result), default=decimal_default)
    
    except (ClientError, BotoCoreError) as e:
        error_message = f"AWS Error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))
    
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_ec2_instance_pricing(region: str, instance_type: str = None, 
                           tenancy: str = "Shared", offering_class: str = "standard", 
                           term_type: str = "OnDemand") -> str:
    """Get EC2 instance pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        instance_type (str, optional): EC2 instance type (e.g., t3.micro, m5.large)
        tenancy (str, optional): Tenancy type (Shared, Dedicated, Host). Defaults to "Shared".
        offering_class (str, optional): Offering class (standard, convertible). Defaults to "standard".
        term_type (str, optional): Term type (OnDemand, Reserved). Defaults to "OnDemand".

    Returns:
        str: JSON string containing EC2 pricing information
    """
    try:
        filters = []
        
        # Add instance type filter if provided
        if instance_type:
            filters.append({
                'Field': 'instanceType',
                'Value': instance_type
            })
        
        # Add tenancy filter
        filters.append({
            'Field': 'tenancy',
            'Value': tenancy
        })
        
        # Add term type filter
        filters.append({
            'Field': 'termType',
            'Value': term_type
        })
        
        # Add operating system filter (Linux)
        filters.append({
            'Field': 'operatingSystem',
            'Value': 'Linux'
        })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('ec2', region, filters, 100))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            price_dimensions = None
            
            if term_type == 'OnDemand':
                on_demand_terms = terms.get('OnDemand', {})
                if on_demand_terms:
                    first_key = next(iter(on_demand_terms))
                    price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            else:
                reserved_terms = terms.get('Reserved', {})
                if reserved_terms:
                    first_key = next(iter(reserved_terms))
                    price_dimensions = reserved_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            instance_info = {
                'instanceType': attributes.get('instanceType'),
                'vCPU': attributes.get('vcpu'),
                'memory': attributes.get('memory'),
                'storage': attributes.get('storage'),
                'operatingSystem': attributes.get('operatingSystem'),
                'tenancy': attributes.get('tenancy'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(instance_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting EC2 pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_ebs_pricing(region: str, volume_type: str = None) -> str:
    """Get EBS volume pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        volume_type (str, optional): EBS volume type (e.g., gp2, io1, st1)

    Returns:
        str: JSON string containing EBS pricing information
    """
    try:
        filters = []
        
        # Add volume type filter if provided
        if volume_type:
            filters.append({
                'Field': 'volumeType',
                'Value': volume_type
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('ebs', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            volume_info = {
                'volumeType': attributes.get('volumeType'),
                'maxIopsvolume': attributes.get('maxIopsvolume'),
                'maxThroughputvolume': attributes.get('maxThroughputvolume'),
                'storageMedia': attributes.get('storageMedia'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(volume_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting EBS pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_s3_pricing(region: str, storage_class: str = None) -> str:
    """Get S3 storage pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        storage_class (str, optional): S3 storage class (e.g., Standard, Standard-IA, Glacier)

    Returns:
        str: JSON string containing S3 pricing information
    """
    try:
        filters = []
        
        # Add storage class filter if provided
        if storage_class:
            filters.append({
                'Field': 'storageClass',
                'Value': storage_class
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('s3', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            storage_info = {
                'storageClass': attributes.get('storageClass'),
                'volumeType': attributes.get('volumeType'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(storage_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting S3 pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_rds_pricing(region: str, instance_type: str = None, engine: str = None) -> str:
    """Get RDS instance pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        instance_type (str, optional): RDS instance type (e.g., db.t3.micro, db.m5.large)
        engine (str, optional): Database engine (e.g., MySQL, PostgreSQL, Oracle)

    Returns:
        str: JSON string containing RDS pricing information
    """
    try:
        filters = []
        
        # Add instance type filter if provided
        if instance_type:
            filters.append({
                'Field': 'instanceType',
                'Value': instance_type
            })
        
        # Add engine filter if provided
        if engine:
            filters.append({
                'Field': 'databaseEngine',
                'Value': engine
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('rds', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            reserved_terms = terms.get('Reserved', {})
            
            # Process on-demand pricing
            on_demand_price = None
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
                if price_dimensions:
                    first_price_key = next(iter(price_dimensions))
                    on_demand_price = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            # Process reserved pricing (1 year, no upfront)
            reserved_price = None
            if reserved_terms:
                for term_key in reserved_terms:
                    term = reserved_terms[term_key]
                    term_attributes = term.get('termAttributes', {})
                    if (term_attributes.get('LeaseContractLength') == '1yr' and 
                        term_attributes.get('PurchaseOption') == 'No Upfront'):
                        price_dimensions = term.get('priceDimensions', {})
                        if price_dimensions:
                            first_price_key = next(iter(price_dimensions))
                            reserved_price = price_dimensions[first_price_key].get('pricePerUnit', {})
                            break
            
            instance_info = {
                'instanceType': attributes.get('instanceType'),
                'databaseEngine': attributes.get('databaseEngine'),
                'deploymentOption': attributes.get('deploymentOption'),
                'licenseModel': attributes.get('licenseModel'),
                'location': attributes.get('location'),
                'onDemandPrice': on_demand_price,
                'reservedPrice1yrNoUpfront': reserved_price
            }
            
            processed_data.append(instance_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting RDS pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_elasticache_pricing(region: str, instance_type: str = None, cache_engine: str = None) -> str:
    """Get ElastiCache pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        instance_type (str, optional): ElastiCache node type (e.g., cache.t3.micro, cache.m5.large)
        cache_engine (str, optional): Cache engine (Redis, Memcached)

    Returns:
        str: JSON string containing ElastiCache pricing information
    """
    try:
        filters = []
        
        # Add instance type filter if provided
        if instance_type:
            filters.append({
                'Field': 'instanceType',
                'Value': instance_type
            })
        
        # Add cache engine filter if provided
        if cache_engine:
            filters.append({
                'Field': 'cacheEngine',
                'Value': cache_engine
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('elasticache', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            cache_info = {
                'instanceType': attributes.get('instanceType'),
                'cacheEngine': attributes.get('cacheEngine'),
                'memory': attributes.get('memory'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(cache_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting ElastiCache pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_opensearch_pricing(region: str, instance_type: str = None) -> str:
    """Get OpenSearch service pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        instance_type (str, optional): OpenSearch instance type (e.g., t3.small.search, m5.large.search)

    Returns:
        str: JSON string containing OpenSearch pricing information
    """
    try:
        filters = []
        
        # Add instance type filter if provided
        if instance_type:
            filters.append({
                'Field': 'instanceType',
                'Value': instance_type
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('opensearch', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            search_info = {
                'instanceType': attributes.get('instanceType'),
                'memory': attributes.get('memory'),
                'vcpu': attributes.get('vcpu'),
                'usagetype': attributes.get('usagetype'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(search_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting OpenSearch pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_elb_pricing(region: str, load_balancer_type: str = None) -> str:
    """Get Elastic Load Balancing (ELB) pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        load_balancer_type (str, optional): Load balancer type (e.g., ALB, NLB, CLB)

    Returns:
        str: JSON string containing ELB pricing information
    """
    try:
        filters = []
        
        # Add load balancer type filter if provided
        if load_balancer_type:
            lb_type_map = {
                "ALB": "LoadBalancerType-Application",
                "NLB": "LoadBalancerType-Network",
                "CLB": "LoadBalancerType-Classic"
            }
            lb_type = lb_type_map.get(load_balancer_type.upper(), load_balancer_type)
            
            filters.append({
                'Field': 'usagetype',
                'Value': lb_type
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('elb', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            elb_info = {
                'usagetype': attributes.get('usagetype'),
                'operation': attributes.get('operation'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(elb_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting ELB pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_network_pricing(region: str, data_direction: str = None) -> str:
    """Get network data transfer pricing information.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        data_direction (str, optional): Data transfer direction (e.g., In, Out, InterRegion)

    Returns:
        str: JSON string containing network pricing information
    """
    try:
        filters = []
        
        # Add data direction filter if provided
        if data_direction:
            direction_map = {
                "in": "DataTransfer-In",
                "out": "DataTransfer-Out",
                "interregion": "DataTransfer-Regional"
            }
            direction = direction_map.get(data_direction.lower(), data_direction)
            
            filters.append({
                'Field': 'transferType',
                'Value': direction
            })
        
        # Get pricing information
        result = json.loads(get_aws_pricing('network', region, filters, 50))
        
        if not result.get('success'):
            return json.dumps(result)
        
        # Process the pricing data to make it more readable
        pricing_data = result['data']['pricing_data']
        processed_data = []
        
        for item in pricing_data:
            product = item.get('product', {})
            attributes = product.get('attributes', {})
            
            # Get price information
            terms = item.get('terms', {})
            on_demand_terms = terms.get('OnDemand', {})
            price_dimensions = None
            
            if on_demand_terms:
                first_key = next(iter(on_demand_terms))
                price_dimensions = on_demand_terms[first_key].get('priceDimensions', {})
            
            # Extract price
            price_per_unit = None
            if price_dimensions:
                first_price_key = next(iter(price_dimensions))
                price_per_unit = price_dimensions[first_price_key].get('pricePerUnit', {})
            
            network_info = {
                'transferType': attributes.get('transferType'),
                'fromLocation': attributes.get('fromLocation'),
                'toLocation': attributes.get('toLocation'),
                'location': attributes.get('location'),
                'price': price_per_unit
            }
            
            processed_data.append(network_info)
        
        result['data']['pricing_data'] = processed_data
        return json.dumps(result, default=decimal_default)
    
    except Exception as e:
        error_message = f"Error getting network pricing: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def get_available_instance_types(region: str, service: str = "ec2") -> str:
    """Get available instance types for a specific region and service.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        service (str, optional): AWS service (ec2, rds, elasticache, opensearch). Defaults to "ec2".

    Returns:
        str: JSON string containing available instance types
    """
    try:
        service_code = service.lower()
        
        if service_code not in SERVICE_CODE_MAP:
            return json.dumps(format_response(False, None, f"Unsupported service: {service}"))
        
        # Create appropriate client based on service
        if service_code == "ec2":
            client = boto3.client('ec2', region_name=region)
            
            # Get available instance types
            paginator = client.get_paginator('describe_instance_types')
            instance_types = []
            
            for page in paginator.paginate():
                for instance_type in page['InstanceTypes']:
                    instance_info = {
                        'instanceType': instance_type['InstanceType'],
                        'vCPU': instance_type['VCpuInfo']['DefaultVCpus'],
                        'memory': instance_type['MemoryInfo']['SizeInMiB'] / 1024,  # Convert to GiB
                        'architecture': instance_type['ProcessorInfo']['SupportedArchitectures'],
                        'currentGeneration': instance_type.get('CurrentGeneration', False)
                    }
                    instance_types.append(instance_info)
            
            # Sort by current generation (newest first) and instance type
            instance_types.sort(key=lambda x: (not x['currentGeneration'], x['instanceType']))
            
            return json.dumps(format_response(True, {
                'service': service,
                'region': region,
                'instanceTypes': instance_types
            }))
        
        else:
            # For other services, use pricing API to get instance types
            aws_service_code = SERVICE_CODE_MAP[service_code]
            pricing_client = boto3.client('pricing', region_name='us-east-1')
            
            # Map region to region description
            region_map = {
                'us-east-1': 'US East (N. Virginia)',
                'us-east-2': 'US East (Ohio)',
                'us-west-1': 'US West (N. California)',
                'us-west-2': 'US West (Oregon)',
                'ca-central-1': 'Canada (Central)',
                'eu-north-1': 'EU (Stockholm)',
                'eu-west-1': 'EU (Ireland)',
                'eu-west-2': 'EU (London)',
                'eu-west-3': 'EU (Paris)',
                'eu-central-1': 'EU (Frankfurt)',
                'ap-northeast-1': 'Asia Pacific (Tokyo)',
                'ap-northeast-2': 'Asia Pacific (Seoul)',
                'ap-northeast-3': 'Asia Pacific (Osaka)',
                'ap-southeast-1': 'Asia Pacific (Singapore)',
                'ap-southeast-2': 'Asia Pacific (Sydney)',
                'ap-south-1': 'Asia Pacific (Mumbai)',
                'sa-east-1': 'South America (Sao Paulo)',
                'cn-north-1': 'China (Beijing)',
                'cn-northwest-1': 'China (Ningxia)'
            }
            
            region_description = region_map.get(region, region)
            
            # Get instance types
            response = pricing_client.get_attribute_values(
                ServiceCode=aws_service_code,
                AttributeName='instanceType'
            )
            
            instance_types = []
            for attribute in response['AttributeValues']:
                instance_types.append(attribute['Value'])
            
            # Sort instance types
            instance_types.sort()
            
            return json.dumps(format_response(True, {
                'service': service,
                'region': region,
                'instanceTypes': instance_types
            }))
    
    except (ClientError, BotoCoreError) as e:
        error_message = f"AWS Error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))
    
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))

@tool
def recommend_instance_types(region: str, vcpu_min: int, memory_min: float, 
                           service: str = "ec2", current_generation_only: bool = True) -> str:
    """Recommend instance types based on minimum requirements.

    Args:
        region (str): AWS region code (e.g., us-east-1, eu-west-1, cn-north-1)
        vcpu_min (int): Minimum number of vCPUs required
        memory_min (float): Minimum memory in GiB required
        service (str, optional): AWS service (ec2, rds, elasticache, opensearch). Defaults to "ec2".
        current_generation_only (bool, optional): Only include current generation instances. Defaults to True.

    Returns:
        str: JSON string containing recommended instance types
    """
    try:
        if service.lower() != "ec2":
            return json.dumps(format_response(False, None, 
                                            "This function currently only supports EC2 instance recommendations"))
        
        # Get available instance types
        result = json.loads(get_available_instance_types(region, service))
        
        if not result.get('success'):
            return json.dumps(result)
        
        instance_types = result['data']['instanceTypes']
        
        # Filter based on requirements
        recommended_instances = []
        for instance in instance_types:
            if instance['vCPU'] >= vcpu_min and instance['memory'] >= memory_min:
                if not current_generation_only or instance.get('currentGeneration', False):
                    recommended_instances.append(instance)
        
        # Sort by vCPU and memory (closest match first)
        recommended_instances.sort(key=lambda x: (x['vCPU'] - vcpu_min) + (x['memory'] - memory_min))
        
        # Limit to top 10 recommendations
        recommended_instances = recommended_instances[:10]
        
        return json.dumps(format_response(True, {
            'service': service,
            'region': region,
            'requirements': {
                'vCPU': vcpu_min,
                'memory': memory_min
            },
            'recommendedInstances': recommended_instances
        }))
    
    except Exception as e:
        error_message = f"Error recommending instances: {str(e)}"
        logger.error(error_message)
        return json.dumps(format_response(False, None, error_message))