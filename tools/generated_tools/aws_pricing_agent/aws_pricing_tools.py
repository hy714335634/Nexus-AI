"""
AWS Pricing Tools

This module provides tools for interacting with AWS Pricing API and related services.
It supports retrieving pricing information for EC2, S3, VPC/ELB, and RDS services.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
SUPPORTED_SERVICES = {
    'compute': 'AmazonEC2',
    'storage': 'AmazonS3',
    'network': ['AmazonVPC', 'AmazonELB'],
    'database': 'AmazonRDS'
}

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal values from AWS responses."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

@tool
def use_aws(region: str, service_name: str, operation_name: str, parameters: Dict[str, Any], 
            label: str, profile_name: str = None) -> str:
    """Make a boto3 client call with the specified service, operation, and parameters.

    Args:
        region: Region name for calling the operation on AWS boto3
        service_name: The name of the AWS service
        operation_name: The name of the operation to perform
        parameters: The parameters for the operation
        label: Label of AWS API operations human readable explanation
        profile_name: Optional AWS profile name to use from ~/.aws/credentials

    Returns:
        JSON string containing the API call results or error information

    Examples:
        >>> use_aws('us-east-1', 'pricing', 'get_products', 
        ...         {'ServiceCode': 'AmazonEC2', 'Filters': [...]}, 
        ...         '获取EC2实例价格')
    """
    result = {
        "status": "success",
        "service": service_name,
        "operation": operation_name,
        "label": label,
        "region": region,
        "data": None,
        "error": None
    }

    try:
        # Create boto3 session with optional profile
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        # Create the client
        client = session.client(service_name, region_name=region)
        
        # Execute the operation with retry mechanism
        response = _execute_with_retry(client, operation_name, parameters)
        
        # Process the response
        result["data"] = json.loads(json.dumps(response, cls=DecimalEncoder))
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        result["status"] = "error"
        result["error"] = {
            "type": "ClientError",
            "code": error_code,
            "message": error_message,
            "details": str(e)
        }
        logger.error(f"AWS ClientError: {error_code} - {error_message}")
        
    except BotoCoreError as e:
        result["status"] = "error"
        result["error"] = {
            "type": "BotoCoreError",
            "message": str(e),
            "details": str(e)
        }
        logger.error(f"AWS BotoCoreError: {str(e)}")
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = {
            "type": "GeneralException",
            "message": str(e),
            "details": str(e)
        }
        logger.error(f"General exception: {str(e)}")
    
    return json.dumps(result, ensure_ascii=False)

def _execute_with_retry(client: Any, operation_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute AWS operation with retry mechanism.
    
    Args:
        client: Boto3 client
        operation_name: Operation name to call
        parameters: Parameters for the operation
        
    Returns:
        Response from the AWS API
        
    Raises:
        Exception: If all retry attempts fail
    """
    last_exception = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # Get the operation method
            operation = getattr(client, operation_name)
            
            # Call the operation with the parameters
            response = operation(**parameters)
            
            return response
            
        except (ClientError, BotoCoreError) as e:
            last_exception = e
            
            # Check if the error is retryable
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code in ['ThrottlingException', 'RequestLimitExceeded', 'Throttling']:
                # Exponential backoff
                sleep_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Rate limited by AWS. Retrying in {sleep_time} seconds. Attempt {attempt + 1}/{MAX_RETRIES}")
                time.sleep(sleep_time)
            else:
                # Non-retryable error
                raise
    
    # If we get here, all retries failed
    logger.error(f"All {MAX_RETRIES} retry attempts failed")
    raise last_exception

@tool
def get_ec2_pricing(instance_type: str, region: str, os: str = 'Linux', 
                   tenancy: str = 'Shared', preinstalled_software: str = 'NA') -> str:
    """Get pricing information for a specific EC2 instance type.
    
    Args:
        instance_type: EC2 instance type (e.g., 't2.micro', 'm5.large')
        region: AWS region (e.g., 'us-east-1')
        os: Operating system (default: 'Linux')
        tenancy: Tenancy type (default: 'Shared')
        preinstalled_software: Preinstalled software (default: 'NA')
        
    Returns:
        JSON string containing EC2 pricing information
    """
    filters = [
        {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
        {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': os},
        {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': tenancy},
        {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': preinstalled_software},
        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)},
        {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
    ]
    
    parameters = {
        'ServiceCode': 'AmazonEC2',
        'Filters': filters,
        'MaxResults': 100
    }
    
    result = use_aws(
        region='us-east-1',  # Pricing API is only available in us-east-1
        service_name='pricing',
        operation_name='get_products',
        parameters=parameters,
        label=f'获取EC2 {instance_type}实例在{region}区域的价格'
    )
    
    # Process and simplify the pricing data
    result_data = json.loads(result)
    
    if result_data["status"] == "success" and "data" in result_data:
        # Extract and structure the pricing information
        processed_data = process_ec2_pricing_data(result_data["data"], instance_type, region)
        result_data["data"] = processed_data
    
    return json.dumps(result_data, ensure_ascii=False)

@tool
def get_s3_pricing(region: str, storage_class: str = 'Standard') -> str:
    """Get pricing information for S3 storage.
    
    Args:
        region: AWS region (e.g., 'us-east-1')
        storage_class: S3 storage class (default: 'Standard')
        
    Returns:
        JSON string containing S3 pricing information
    """
    filters = [
        {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)},
        {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': storage_class}
    ]
    
    parameters = {
        'ServiceCode': 'AmazonS3',
        'Filters': filters,
        'MaxResults': 100
    }
    
    result = use_aws(
        region='us-east-1',  # Pricing API is only available in us-east-1
        service_name='pricing',
        operation_name='get_products',
        parameters=parameters,
        label=f'获取S3 {storage_class}存储在{region}区域的价格'
    )
    
    # Process and simplify the pricing data
    result_data = json.loads(result)
    
    if result_data["status"] == "success" and "data" in result_data:
        # Extract and structure the pricing information
        processed_data = process_s3_pricing_data(result_data["data"], region, storage_class)
        result_data["data"] = processed_data
    
    return json.dumps(result_data, ensure_ascii=False)

@tool
def get_rds_pricing(db_instance_class: str, region: str, engine: str = 'MySQL',
                   deployment_option: str = 'Single-AZ') -> str:
    """Get pricing information for RDS database instances.
    
    Args:
        db_instance_class: RDS instance class (e.g., 'db.t3.micro', 'db.m5.large')
        region: AWS region (e.g., 'us-east-1')
        engine: Database engine (default: 'MySQL')
        deployment_option: Deployment option (default: 'Single-AZ')
        
    Returns:
        JSON string containing RDS pricing information
    """
    filters = [
        {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': db_instance_class},
        {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)},
        {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': engine},
        {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': deployment_option}
    ]
    
    parameters = {
        'ServiceCode': 'AmazonRDS',
        'Filters': filters,
        'MaxResults': 100
    }
    
    result = use_aws(
        region='us-east-1',  # Pricing API is only available in us-east-1
        service_name='pricing',
        operation_name='get_products',
        parameters=parameters,
        label=f'获取RDS {db_instance_class} {engine}数据库在{region}区域的价格'
    )
    
    # Process and simplify the pricing data
    result_data = json.loads(result)
    
    if result_data["status"] == "success" and "data" in result_data:
        # Extract and structure the pricing information
        processed_data = process_rds_pricing_data(result_data["data"], db_instance_class, region, engine)
        result_data["data"] = processed_data
    
    return json.dumps(result_data, ensure_ascii=False)

@tool
def get_network_pricing(service: str, region: str, product_type: str = None) -> str:
    """Get pricing information for network services (VPC, ELB).
    
    Args:
        service: Network service ('vpc' or 'elb')
        region: AWS region (e.g., 'us-east-1')
        product_type: Specific product type (e.g., 'LoadBalancer', 'NatGateway')
        
    Returns:
        JSON string containing network service pricing information
    """
    if service.lower() == 'vpc':
        service_code = 'AmazonVPC'
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)}
        ]
        
        if product_type:
            filters.append({'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'*{product_type}*'})
        
        label = f'获取VPC服务在{region}区域的价格'
        
    elif service.lower() == 'elb':
        service_code = 'AmazonELB'
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': get_region_name(region)}
        ]
        
        if product_type:
            filters.append({'Type': 'TERM_MATCH', 'Field': 'usagetype', 'Value': f'*{product_type}*'})
        
        label = f'获取ELB服务在{region}区域的价格'
        
    else:
        return json.dumps({
            "status": "error",
            "error": {
                "type": "InvalidParameter",
                "message": f"Invalid service: {service}. Must be 'vpc' or 'elb'."
            }
        }, ensure_ascii=False)
    
    parameters = {
        'ServiceCode': service_code,
        'Filters': filters,
        'MaxResults': 100
    }
    
    result = use_aws(
        region='us-east-1',  # Pricing API is only available in us-east-1
        service_name='pricing',
        operation_name='get_products',
        parameters=parameters,
        label=label
    )
    
    # Process and simplify the pricing data
    result_data = json.loads(result)
    
    if result_data["status"] == "success" and "data" in result_data:
        # Extract and structure the pricing information
        processed_data = process_network_pricing_data(result_data["data"], service, region, product_type)
        result_data["data"] = processed_data
    
    return json.dumps(result_data, ensure_ascii=False)

# Helper functions

def get_region_name(region_code: str) -> str:
    """Convert region code to region name used in pricing API.
    
    Args:
        region_code: AWS region code (e.g., 'us-east-1')
        
    Returns:
        Region name used in pricing API
    """
    region_names = {
        'us-east-1': 'US East (N. Virginia)',
        'us-east-2': 'US East (Ohio)',
        'us-west-1': 'US West (N. California)',
        'us-west-2': 'US West (Oregon)',
        'af-south-1': 'Africa (Cape Town)',
        'ap-east-1': 'Asia Pacific (Hong Kong)',
        'ap-south-1': 'Asia Pacific (Mumbai)',
        'ap-northeast-1': 'Asia Pacific (Tokyo)',
        'ap-northeast-2': 'Asia Pacific (Seoul)',
        'ap-northeast-3': 'Asia Pacific (Osaka)',
        'ap-southeast-1': 'Asia Pacific (Singapore)',
        'ap-southeast-2': 'Asia Pacific (Sydney)',
        'ap-southeast-3': 'Asia Pacific (Jakarta)',
        'ca-central-1': 'Canada (Central)',
        'eu-central-1': 'EU (Frankfurt)',
        'eu-west-1': 'EU (Ireland)',
        'eu-west-2': 'EU (London)',
        'eu-west-3': 'EU (Paris)',
        'eu-north-1': 'EU (Stockholm)',
        'eu-south-1': 'EU (Milan)',
        'me-south-1': 'Middle East (Bahrain)',
        'sa-east-1': 'South America (Sao Paulo)'
    }
    
    return region_names.get(region_code, region_code)

def process_ec2_pricing_data(raw_data: Dict[str, Any], instance_type: str, region: str) -> Dict[str, Any]:
    """Process and simplify EC2 pricing data.
    
    Args:
        raw_data: Raw pricing data from AWS API
        instance_type: EC2 instance type
        region: AWS region
        
    Returns:
        Processed pricing data
    """
    processed_data = {
        "instance_type": instance_type,
        "region": region,
        "region_name": get_region_name(region),
        "pricing": []
    }
    
    if "PriceList" not in raw_data or not raw_data["PriceList"]:
        return processed_data
    
    for price_item in raw_data["PriceList"]:
        try:
            price_data = json.loads(price_item)
            product = price_data.get("product", {})
            attributes = product.get("attributes", {})
            
            # Extract terms
            on_demand = price_data.get("terms", {}).get("OnDemand", {})
            
            if not on_demand:
                continue
                
            # Get the first price dimension
            offer_key = list(on_demand.keys())[0]
            price_dimensions = on_demand[offer_key].get("priceDimensions", {})
            
            if not price_dimensions:
                continue
                
            dimension_key = list(price_dimensions.keys())[0]
            price_dimension = price_dimensions[dimension_key]
            
            price_info = {
                "operating_system": attributes.get("operatingSystem", ""),
                "vcpu": attributes.get("vcpu", ""),
                "memory": attributes.get("memory", ""),
                "storage": attributes.get("storage", ""),
                "price_per_unit": price_dimension.get("pricePerUnit", {}).get("USD", "0"),
                "currency": "USD",
                "unit": price_dimension.get("unit", ""),
                "description": price_dimension.get("description", "")
            }
            
            processed_data["pricing"].append(price_info)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error processing EC2 pricing data: {str(e)}")
    
    return processed_data

def process_s3_pricing_data(raw_data: Dict[str, Any], region: str, storage_class: str) -> Dict[str, Any]:
    """Process and simplify S3 pricing data.
    
    Args:
        raw_data: Raw pricing data from AWS API
        region: AWS region
        storage_class: S3 storage class
        
    Returns:
        Processed pricing data
    """
    processed_data = {
        "storage_class": storage_class,
        "region": region,
        "region_name": get_region_name(region),
        "pricing": []
    }
    
    if "PriceList" not in raw_data or not raw_data["PriceList"]:
        return processed_data
    
    for price_item in raw_data["PriceList"]:
        try:
            price_data = json.loads(price_item)
            product = price_data.get("product", {})
            attributes = product.get("attributes", {})
            
            # Extract terms
            on_demand = price_data.get("terms", {}).get("OnDemand", {})
            
            if not on_demand:
                continue
                
            # Get the first price dimension
            offer_key = list(on_demand.keys())[0]
            price_dimensions = on_demand[offer_key].get("priceDimensions", {})
            
            if not price_dimensions:
                continue
                
            for dimension_key in price_dimensions:
                price_dimension = price_dimensions[dimension_key]
                
                price_info = {
                    "storage_class": attributes.get("storageClass", ""),
                    "volume_type": attributes.get("volumeType", ""),
                    "price_per_unit": price_dimension.get("pricePerUnit", {}).get("USD", "0"),
                    "currency": "USD",
                    "unit": price_dimension.get("unit", ""),
                    "description": price_dimension.get("description", "")
                }
                
                processed_data["pricing"].append(price_info)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error processing S3 pricing data: {str(e)}")
    
    return processed_data

def process_rds_pricing_data(raw_data: Dict[str, Any], db_instance_class: str, region: str, engine: str) -> Dict[str, Any]:
    """Process and simplify RDS pricing data.
    
    Args:
        raw_data: Raw pricing data from AWS API
        db_instance_class: RDS instance class
        region: AWS region
        engine: Database engine
        
    Returns:
        Processed pricing data
    """
    processed_data = {
        "db_instance_class": db_instance_class,
        "engine": engine,
        "region": region,
        "region_name": get_region_name(region),
        "pricing": []
    }
    
    if "PriceList" not in raw_data or not raw_data["PriceList"]:
        return processed_data
    
    for price_item in raw_data["PriceList"]:
        try:
            price_data = json.loads(price_item)
            product = price_data.get("product", {})
            attributes = product.get("attributes", {})
            
            # Extract terms
            on_demand = price_data.get("terms", {}).get("OnDemand", {})
            
            if not on_demand:
                continue
                
            # Get the first price dimension
            offer_key = list(on_demand.keys())[0]
            price_dimensions = on_demand[offer_key].get("priceDimensions", {})
            
            if not price_dimensions:
                continue
                
            dimension_key = list(price_dimensions.keys())[0]
            price_dimension = price_dimensions[dimension_key]
            
            price_info = {
                "database_engine": attributes.get("databaseEngine", ""),
                "deployment_option": attributes.get("deploymentOption", ""),
                "vcpu": attributes.get("vcpu", ""),
                "memory": attributes.get("memory", ""),
                "price_per_unit": price_dimension.get("pricePerUnit", {}).get("USD", "0"),
                "currency": "USD",
                "unit": price_dimension.get("unit", ""),
                "description": price_dimension.get("description", "")
            }
            
            processed_data["pricing"].append(price_info)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error processing RDS pricing data: {str(e)}")
    
    return processed_data

def process_network_pricing_data(raw_data: Dict[str, Any], service: str, region: str, product_type: str) -> Dict[str, Any]:
    """Process and simplify network pricing data.
    
    Args:
        raw_data: Raw pricing data from AWS API
        service: Network service ('vpc' or 'elb')
        region: AWS region
        product_type: Specific product type
        
    Returns:
        Processed pricing data
    """
    processed_data = {
        "service": service.upper(),
        "product_type": product_type,
        "region": region,
        "region_name": get_region_name(region),
        "pricing": []
    }
    
    if "PriceList" not in raw_data or not raw_data["PriceList"]:
        return processed_data
    
    for price_item in raw_data["PriceList"]:
        try:
            price_data = json.loads(price_item)
            product = price_data.get("product", {})
            attributes = product.get("attributes", {})
            
            # Skip if product_type is specified and doesn't match
            if product_type and product_type.lower() not in attributes.get("usagetype", "").lower():
                continue
                
            # Extract terms
            on_demand = price_data.get("terms", {}).get("OnDemand", {})
            
            if not on_demand:
                continue
                
            # Get the first price dimension
            offer_key = list(on_demand.keys())[0]
            price_dimensions = on_demand[offer_key].get("priceDimensions", {})
            
            if not price_dimensions:
                continue
                
            for dimension_key in price_dimensions:
                price_dimension = price_dimensions[dimension_key]
                
                price_info = {
                    "usage_type": attributes.get("usagetype", ""),
                    "operation": attributes.get("operation", ""),
                    "price_per_unit": price_dimension.get("pricePerUnit", {}).get("USD", "0"),
                    "currency": "USD",
                    "unit": price_dimension.get("unit", ""),
                    "description": price_dimension.get("description", "")
                }
                
                processed_data["pricing"].append(price_info)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error processing network pricing data: {str(e)}")
    
    return processed_data