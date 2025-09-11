"""
AWS Pricing API Tools - Core Module

This module provides core functionality for interacting with AWS Pricing API
to get real-time pricing information for various AWS services.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Union, Any, Tuple
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)
pricing_cache = {}  # Global cache for pricing data

# AWS Region mapping
AWS_REGIONS = {
    # US Regions
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    # Asia Pacific
    "ap-east-1": "Asia Pacific (Hong Kong)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-northeast-3": "Asia Pacific (Osaka)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-southeast-3": "Asia Pacific (Jakarta)",
    # Europe
    "eu-central-1": "Europe (Frankfurt)",
    "eu-west-1": "Europe (Ireland)",
    "eu-west-2": "Europe (London)",
    "eu-west-3": "Europe (Paris)",
    "eu-north-1": "Europe (Stockholm)",
    "eu-south-1": "Europe (Milan)",
    # South America
    "sa-east-1": "South America (São Paulo)",
    # Canada
    "ca-central-1": "Canada (Central)",
    # Middle East
    "me-south-1": "Middle East (Bahrain)",
    # Africa
    "af-south-1": "Africa (Cape Town)",
    # China (requires separate credentials)
    "cn-north-1": "China (Beijing)",
    "cn-northwest-1": "China (Ningxia)"
}

# Operating System mapping
OS_MAPPING = {
    "linux": "Linux",
    "windows": "Windows",
    "rhel": "RHEL",
    "suse": "SUSE",
    "amazon": "Amazon Linux"
}

# Database engine mapping
DB_ENGINE_MAPPING = {
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "oracle-se": "Oracle Standard Edition",
    "oracle-se1": "Oracle Standard Edition One",
    "oracle-se2": "Oracle Standard Edition Two",
    "oracle-ee": "Oracle Enterprise Edition",
    "sqlserver-ex": "SQL Server Express",
    "sqlserver-web": "SQL Server Web",
    "sqlserver-se": "SQL Server Standard",
    "sqlserver-ee": "SQL Server Enterprise",
    "mariadb": "MariaDB",
    "aurora": "Aurora MySQL",
    "aurora-postgresql": "Aurora PostgreSQL"
}

# Helper functions
def _get_cache_key(service: str, filters: Dict[str, Any], region: str) -> str:
    """Generate a cache key based on service, filters and region."""
    filters_str = json.dumps(filters, sort_keys=True)
    return f"{service}:{filters_str}:{region}"

def _is_cache_valid(cache_key: str) -> bool:
    """Check if cache entry is valid (exists and not expired)."""
    if cache_key not in pricing_cache:
        return False
    
    cache_time = pricing_cache[cache_key]["timestamp"]
    current_time = time.time()
    
    return (current_time - cache_time) < CACHE_TTL

def _get_from_cache(cache_key: str) -> Dict[str, Any]:
    """Get pricing data from cache if valid."""
    if _is_cache_valid(cache_key):
        return pricing_cache[cache_key]["data"]
    return None

def _save_to_cache(cache_key: str, data: Dict[str, Any]) -> None:
    """Save pricing data to cache with current timestamp."""
    pricing_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }

def _create_pricing_client(region: str) -> boto3.client:
    """Create a boto3 pricing client for the specified region."""
    # Pricing API is only available in us-east-1 and ap-south-1
    pricing_api_region = "us-east-1"
    if region.startswith("cn-"):
        # For China regions, use the China endpoint
        pricing_api_region = "cn-northwest-1"
    
    try:
        return boto3.client('pricing', region_name=pricing_api_region)
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Failed to create pricing client: {str(e)}")
        raise Exception(f"Failed to create AWS pricing client: {str(e)}")

def _format_price(price: str) -> float:
    """Format price string to float."""
    try:
        return float(Decimal(price))
    except (ValueError, TypeError):
        return 0.0

def _validate_region(region: str) -> str:
    """Validate and normalize AWS region."""
    if not region:
        return "us-east-1"  # Default region
    
    if region.lower() in [r.lower() for r in AWS_REGIONS.keys()]:
        # Find the correctly cased region
        for r in AWS_REGIONS.keys():
            if r.lower() == region.lower():
                return r
    
    # If not found, use default
    logger.warning(f"Region '{region}' not recognized, using default 'us-east-1'")
    return "us-east-1"

def _get_pricing_data(service: str, filters: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    Get pricing data from AWS Pricing API with caching.
    
    Args:
        service: AWS service code (e.g., 'AmazonEC2')
        filters: Filters to apply to the pricing query
        region: AWS region
    
    Returns:
        Dict containing pricing data
    """
    region = _validate_region(region)
    cache_key = _get_cache_key(service, filters, region)
    
    # Check cache first
    cached_data = _get_from_cache(cache_key)
    if cached_data:
        logger.info(f"Using cached pricing data for {service} in {region}")
        return cached_data
    
    # If not in cache, query the API
    try:
        pricing_client = _create_pricing_client(region)
        
        # Add region to filters
        region_name = AWS_REGIONS.get(region, "US East (N. Virginia)")
        filters_with_region = filters.copy()
        filters_with_region.update({
            "location": {"Type": "TERM_MATCH", "Field": "location", "Value": region_name}
        })
        
        # Convert filters to AWS format
        filter_list = []
        for field, value in filters_with_region.items():
            if isinstance(value, dict):
                filter_list.append(value)
            else:
                filter_list.append({
                    "Type": "TERM_MATCH",
                    "Field": field,
                    "Value": value
                })
        
        # Get products
        paginator = pricing_client.get_paginator('get_products')
        response_iterator = paginator.paginate(
            ServiceCode=service,
            Filters=filter_list
        )
        
        # Process results
        products = []
        for response in response_iterator:
            for price_item in response.get('PriceList', []):
                if isinstance(price_item, str):
                    product = json.loads(price_item)
                    products.append(product)
        
        result = {
            "service": service,
            "region": region,
            "products": products,
            "count": len(products)
        }
        
        # Save to cache
        _save_to_cache(cache_key, result)
        
        return result
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error for {service} in {region}: {str(e)}")
        raise Exception(f"Failed to get pricing data from AWS: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error for {service} in {region}: {str(e)}")
        raise Exception(f"Unexpected error when getting pricing data: {str(e)}")

@tool
def get_ec2_instance_types(region: str = "us-east-1") -> str:
    """
    Get available EC2 instance types for a specific region.
    
    Args:
        region: AWS region code (default: us-east-1)
    
    Returns:
        JSON string with available EC2 instance types and their attributes
    """
    try:
        region = _validate_region(region)
        ec2_client = boto3.client('ec2', region_name=region)
        
        # Get instance types available in the region
        response = ec2_client.describe_instance_types()
        instance_types = []
        
        for instance in response.get('InstanceTypes', []):
            instance_info = {
                "instance_type": instance.get('InstanceType'),
                "vcpu": instance.get('VCpuInfo', {}).get('DefaultVCpus'),
                "memory_gib": instance.get('MemoryInfo', {}).get('SizeInMiB') / 1024,
                "architecture": instance.get('ProcessorInfo', {}).get('SupportedArchitectures'),
                "network_performance": instance.get('NetworkInfo', {}).get('NetworkPerformance'),
                "storage": {
                    "type": instance.get('InstanceStorageInfo', {}).get('StorageType'),
                    "total_size_gb": instance.get('InstanceStorageInfo', {}).get('TotalSizeInGB')
                }
            }
            instance_types.append(instance_info)
        
        # Get all instance types using pagination
        while 'NextToken' in response:
            response = ec2_client.describe_instance_types(NextToken=response['NextToken'])
            for instance in response.get('InstanceTypes', []):
                instance_info = {
                    "instance_type": instance.get('InstanceType'),
                    "vcpu": instance.get('VCpuInfo', {}).get('DefaultVCpus'),
                    "memory_gib": instance.get('MemoryInfo', {}).get('SizeInMiB') / 1024,
                    "architecture": instance.get('ProcessorInfo', {}).get('SupportedArchitectures'),
                    "network_performance": instance.get('NetworkInfo', {}).get('NetworkPerformance'),
                    "storage": {
                        "type": instance.get('InstanceStorageInfo', {}).get('StorageType'),
                        "total_size_gb": instance.get('InstanceStorageInfo', {}).get('TotalSizeInGB')
                    }
                }
                instance_types.append(instance_info)
        
        result = {
            "region": region,
            "instance_types": instance_types,
            "count": len(instance_types)
        }
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting EC2 instance types: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting EC2 instance types: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_ec2_pricing(
    instance_type: str,
    region: str = "us-east-1",
    os: str = "linux",
    tenancy: str = "shared"
) -> str:
    """
    Get EC2 instance pricing for a specific instance type, region, and OS.
    
    Args:
        instance_type: EC2 instance type (e.g., t3.micro, m5.large)
        region: AWS region code (default: us-east-1)
        os: Operating system (linux, windows, rhel, suse, amazon) (default: linux)
        tenancy: Instance tenancy (shared, dedicated, host) (default: shared)
    
    Returns:
        JSON string with EC2 pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        os = os.lower()
        if os not in OS_MAPPING:
            return json.dumps({"error": f"Invalid operating system: {os}. Valid options are: {', '.join(OS_MAPPING.keys())}"})
        
        # Define filters for pricing API
        filters = {
            "instanceType": instance_type,
            "operatingSystem": OS_MAPPING[os],
            "tenancy": tenancy.capitalize()
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonEC2", filters, region)
        
        # Process and format the results
        on_demand_prices = []
        reserved_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our exact requirements
            if (product_attributes.get("instanceType") != instance_type or
                product_attributes.get("operatingSystem") != OS_MAPPING[os] or
                product_attributes.get("tenancy") != tenancy.capitalize()):
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price_per_hour": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", "")
                    }
                    on_demand_prices.append(price_info)
            
            # Process Reserved Instance pricing
            reserved_term = terms.get("Reserved", {})
            for term_id, term_details in reserved_term.items():
                term_attributes = term_details.get("termAttributes", {})
                lease_term = term_attributes.get("LeaseContractLength", "")
                purchase_option = term_attributes.get("PurchaseOption", "")
                
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "lease_term": lease_term,
                        "purchase_option": purchase_option
                    }
                    reserved_prices.append(price_info)
        
        # Create the result
        result = {
            "instance_type": instance_type,
            "region": region,
            "operating_system": OS_MAPPING[os],
            "tenancy": tenancy.capitalize(),
            "on_demand_pricing": on_demand_prices,
            "reserved_pricing": reserved_prices
        }
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting EC2 pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting EC2 pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_ebs_pricing(
    volume_type: str,
    region: str = "us-east-1",
    size_gb: Optional[int] = None
) -> str:
    """
    Get EBS volume pricing for a specific volume type and region.
    
    Args:
        volume_type: EBS volume type (gp2, gp3, io1, io2, st1, sc1, standard)
        region: AWS region code (default: us-east-1)
        size_gb: Volume size in GB (optional, for calculating total cost)
    
    Returns:
        JSON string with EBS pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        volume_type = volume_type.lower()
        valid_volume_types = ["gp2", "gp3", "io1", "io2", "st1", "sc1", "standard"]
        
        if volume_type not in valid_volume_types:
            return json.dumps({
                "error": f"Invalid volume type: {volume_type}. Valid options are: {', '.join(valid_volume_types)}"
            })
        
        # Define filters for pricing API
        filters = {
            "volumeType": volume_type
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonEC2", filters, region)
        
        # Process and format the results
        volume_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our exact requirements
            if product_attributes.get("volumeType", "").lower() != volume_type:
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing (EBS only has on-demand)
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "usage_type": product_attributes.get("usagetype", "")
                    }
                    volume_prices.append(price_info)
        
        # Calculate total cost if size is provided
        total_cost = None
        if size_gb is not None and size_gb > 0:
            # Find the storage price (per GB-month)
            storage_price = next(
                (p["price"] for p in volume_prices if "GB-Mo" in p["unit"] or "GB-month" in p["unit"]),
                None
            )
            
            if storage_price is not None:
                total_cost = storage_price * size_gb
        
        # Create the result
        result = {
            "volume_type": volume_type,
            "region": region,
            "pricing": volume_prices
        }
        
        if total_cost is not None:
            result["size_gb"] = size_gb
            result["estimated_monthly_cost"] = total_cost
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting EBS pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting EBS pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_s3_pricing(
    storage_class: str = "standard",
    region: str = "us-east-1",
    storage_gb: Optional[int] = None,
    data_transfer_gb: Optional[int] = None
) -> str:
    """
    Get S3 storage pricing for a specific storage class and region.
    
    Args:
        storage_class: S3 storage class (standard, intelligent_tiering, standard_ia, 
                      onezone_ia, glacier, deep_archive)
        region: AWS region code (default: us-east-1)
        storage_gb: Storage size in GB (optional, for calculating total cost)
        data_transfer_gb: Data transfer out to internet in GB (optional, for calculating transfer cost)
    
    Returns:
        JSON string with S3 pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        storage_class = storage_class.lower().replace("-", "_")
        
        valid_storage_classes = [
            "standard", "intelligent_tiering", "standard_ia", 
            "onezone_ia", "glacier", "deep_archive"
        ]
        
        if storage_class not in valid_storage_classes:
            return json.dumps({
                "error": f"Invalid storage class: {storage_class}. Valid options are: {', '.join(valid_storage_classes)}"
            })
        
        # Map storage class to AWS pricing API terminology
        storage_class_mapping = {
            "standard": "Standard",
            "intelligent_tiering": "Intelligent-Tiering",
            "standard_ia": "Standard - Infrequent Access",
            "onezone_ia": "One Zone - Infrequent Access",
            "glacier": "Glacier",
            "deep_archive": "Glacier Deep Archive"
        }
        
        # Define filters for pricing API
        filters = {
            "storageClass": storage_class_mapping[storage_class]
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonS3", filters, region)
        
        # Process and format the results
        storage_prices = []
        transfer_prices = []
        request_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our storage class
            if product_attributes.get("storageClass", "") != storage_class_mapping[storage_class]:
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "usage_type": product_attributes.get("usagetype", "")
                    }
                    
                    # Categorize pricing information
                    if "TimedStorage" in price_info["usage_type"]:
                        storage_prices.append(price_info)
                    elif "DataTransfer" in price_info["usage_type"]:
                        transfer_prices.append(price_info)
                    elif "Requests" in price_info["usage_type"]:
                        request_prices.append(price_info)
        
        # Calculate total storage cost if storage_gb is provided
        storage_cost = None
        if storage_gb is not None and storage_gb > 0:
            # Find the storage price (per GB-month)
            storage_price = next(
                (p["price"] for p in storage_prices if "GB-Mo" in p["unit"] or "GB-month" in p["unit"]),
                None
            )
            
            if storage_price is not None:
                storage_cost = storage_price * storage_gb
        
        # Calculate data transfer cost if data_transfer_gb is provided
        transfer_cost = None
        if data_transfer_gb is not None and data_transfer_gb > 0:
            # Find the transfer price (per GB)
            transfer_price = next(
                (p["price"] for p in transfer_prices if "GB" in p["unit"] and "Out" in p["description"]),
                None
            )
            
            if transfer_price is not None:
                transfer_cost = transfer_price * data_transfer_gb
        
        # Create the result
        result = {
            "storage_class": storage_class,
            "region": region,
            "storage_pricing": storage_prices,
            "data_transfer_pricing": transfer_prices,
            "request_pricing": request_prices
        }
        
        if storage_cost is not None:
            result["storage_gb"] = storage_gb
            result["estimated_monthly_storage_cost"] = storage_cost
        
        if transfer_cost is not None:
            result["data_transfer_gb"] = data_transfer_gb
            result["estimated_data_transfer_cost"] = transfer_cost
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting S3 pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting S3 pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_rds_pricing(
    instance_type: str,
    engine: str,
    region: str = "us-east-1",
    deployment_option: str = "single-az",
    license_model: str = "license-included"
) -> str:
    """
    Get RDS instance pricing for a specific instance type, database engine, and region.
    
    Args:
        instance_type: RDS instance type (e.g., db.t3.micro, db.m5.large)
        engine: Database engine (mysql, postgresql, oracle-se, oracle-se1, oracle-se2, 
                oracle-ee, sqlserver-ex, sqlserver-web, sqlserver-se, sqlserver-ee, 
                mariadb, aurora, aurora-postgresql)
        region: AWS region code (default: us-east-1)
        deployment_option: Deployment option (single-az or multi-az) (default: single-az)
        license_model: License model (license-included, bring-your-own-license, 
                      general-public-license) (default: license-included)
    
    Returns:
        JSON string with RDS pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        engine = engine.lower()
        
        if engine not in DB_ENGINE_MAPPING:
            return json.dumps({
                "error": f"Invalid database engine: {engine}. Valid options are: {', '.join(DB_ENGINE_MAPPING.keys())}"
            })
        
        # Define filters for pricing API
        filters = {
            "instanceType": instance_type,
            "databaseEngine": DB_ENGINE_MAPPING[engine],
            "deploymentOption": "Single-AZ" if deployment_option.lower() == "single-az" else "Multi-AZ"
        }
        
        # Add license model if applicable
        if license_model:
            license_model_mapping = {
                "license-included": "License included",
                "bring-your-own-license": "Bring your own license",
                "general-public-license": "No license required"
            }
            
            if license_model.lower() in license_model_mapping:
                filters["licenseModel"] = license_model_mapping[license_model.lower()]
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonRDS", filters, region)
        
        # Process and format the results
        on_demand_prices = []
        reserved_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our exact requirements
            if (product_attributes.get("instanceType") != instance_type or
                product_attributes.get("databaseEngine") != DB_ENGINE_MAPPING[engine]):
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price_per_hour": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", "")
                    }
                    on_demand_prices.append(price_info)
            
            # Process Reserved Instance pricing
            reserved_term = terms.get("Reserved", {})
            for term_id, term_details in reserved_term.items():
                term_attributes = term_details.get("termAttributes", {})
                lease_term = term_attributes.get("LeaseContractLength", "")
                purchase_option = term_attributes.get("PurchaseOption", "")
                
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "lease_term": lease_term,
                        "purchase_option": purchase_option
                    }
                    reserved_prices.append(price_info)
        
        # Create the result
        result = {
            "instance_type": instance_type,
            "engine": engine,
            "engine_display_name": DB_ENGINE_MAPPING[engine],
            "region": region,
            "deployment_option": deployment_option,
            "license_model": license_model,
            "on_demand_pricing": on_demand_prices,
            "reserved_pricing": reserved_prices
        }
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting RDS pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting RDS pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_elasticache_pricing(
    node_type: str,
    engine: str = "redis",
    region: str = "us-east-1"
) -> str:
    """
    Get ElastiCache pricing for a specific node type, cache engine, and region.
    
    Args:
        node_type: ElastiCache node type (e.g., cache.t3.micro, cache.m5.large)
        engine: Cache engine (redis or memcached) (default: redis)
        region: AWS region code (default: us-east-1)
    
    Returns:
        JSON string with ElastiCache pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        engine = engine.lower()
        
        if engine not in ["redis", "memcached"]:
            return json.dumps({
                "error": f"Invalid cache engine: {engine}. Valid options are: redis, memcached"
            })
        
        # Define filters for pricing API
        filters = {
            "instanceType": node_type,
            "cacheEngine": engine.capitalize()
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonElastiCache", filters, region)
        
        # Process and format the results
        on_demand_prices = []
        reserved_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our exact requirements
            if (product_attributes.get("instanceType") != node_type or
                product_attributes.get("cacheEngine", "").lower() != engine):
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price_per_hour": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", "")
                    }
                    on_demand_prices.append(price_info)
            
            # Process Reserved Node pricing
            reserved_term = terms.get("Reserved", {})
            for term_id, term_details in reserved_term.items():
                term_attributes = term_details.get("termAttributes", {})
                lease_term = term_attributes.get("LeaseContractLength", "")
                purchase_option = term_attributes.get("PurchaseOption", "")
                
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "lease_term": lease_term,
                        "purchase_option": purchase_option
                    }
                    reserved_prices.append(price_info)
        
        # Create the result
        result = {
            "node_type": node_type,
            "engine": engine,
            "region": region,
            "on_demand_pricing": on_demand_prices,
            "reserved_pricing": reserved_prices
        }
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting ElastiCache pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting ElastiCache pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_opensearch_pricing(
    instance_type: str,
    region: str = "us-east-1",
    storage_gb: Optional[int] = None
) -> str:
    """
    Get OpenSearch Service pricing for a specific instance type, region, and storage.
    
    Args:
        instance_type: OpenSearch instance type (e.g., t3.small.search, m5.large.search)
        region: AWS region code (default: us-east-1)
        storage_gb: Storage size in GB (optional, for calculating total cost)
    
    Returns:
        JSON string with OpenSearch pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        
        # Define filters for pricing API
        filters = {
            "instanceType": instance_type
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonES", filters, region)
        
        # Process and format the results
        instance_prices = []
        storage_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our instance type
            if product_attributes.get("instanceType") != instance_type:
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "usage_type": product_attributes.get("usagetype", "")
                    }
                    
                    # Categorize pricing information
                    if "ESInstance" in price_info["usage_type"]:
                        instance_prices.append(price_info)
                    elif "ESStorage" in price_info["usage_type"]:
                        storage_prices.append(price_info)
        
        # Calculate storage cost if storage_gb is provided
        storage_cost = None
        if storage_gb is not None and storage_gb > 0 and storage_prices:
            # Find the storage price (per GB-month)
            storage_price = next(
                (p["price"] for p in storage_prices if "GB-Mo" in p["unit"] or "GB-month" in p["unit"]),
                None
            )
            
            if storage_price is not None:
                storage_cost = storage_price * storage_gb
        
        # Create the result
        result = {
            "instance_type": instance_type,
            "region": region,
            "instance_pricing": instance_prices,
            "storage_pricing": storage_prices
        }
        
        if storage_cost is not None:
            result["storage_gb"] = storage_gb
            result["estimated_monthly_storage_cost"] = storage_cost
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting OpenSearch pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting OpenSearch pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_loadbalancer_pricing(
    lb_type: str,
    region: str = "us-east-1",
    data_processed_gb: Optional[int] = None
) -> str:
    """
    Get Elastic Load Balancer pricing for a specific load balancer type and region.
    
    Args:
        lb_type: Load balancer type (alb, nlb, clb)
        region: AWS region code (default: us-east-1)
        data_processed_gb: Data processed per month in GB (optional, for calculating total cost)
    
    Returns:
        JSON string with load balancer pricing information
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        lb_type = lb_type.lower()
        
        if lb_type not in ["alb", "nlb", "clb"]:
            return json.dumps({
                "error": f"Invalid load balancer type: {lb_type}. Valid options are: alb, nlb, clb"
            })
        
        # Map load balancer type to AWS pricing API terminology
        lb_type_mapping = {
            "alb": "Application",
            "nlb": "Network",
            "clb": "Classic"
        }
        
        # Define filters for pricing API
        filters = {
            "productFamily": "Load Balancer",
            "usagetype": {"Type": "CONTAINS", "Field": "usagetype", "Value": lb_type_mapping[lb_type].lower()}
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonEC2", filters, region)
        
        # Process and format the results
        lb_hourly_prices = []
        data_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Skip if not matching our load balancer type
            if lb_type_mapping[lb_type] not in product_attributes.get("loadBalancerType", ""):
                continue
            
            # Get pricing terms
            terms = product.get("terms", {})
            
            # Process On-Demand pricing
            on_demand_term = terms.get("OnDemand", {})
            for term_id, term_details in on_demand_term.items():
                for price_id, price_details in term_details.get("priceDimensions", {}).items():
                    price_info = {
                        "price": _format_price(price_details.get("pricePerUnit", {}).get("USD", "0")),
                        "currency": "USD",
                        "description": price_details.get("description", ""),
                        "unit": price_details.get("unit", ""),
                        "usage_type": product_attributes.get("usagetype", "")
                    }
                    
                    # Categorize pricing information
                    if "LoadBalancerUsage" in price_info["usage_type"]:
                        lb_hourly_prices.append(price_info)
                    elif "DataProcessing" in price_info["usage_type"]:
                        data_prices.append(price_info)
        
        # Calculate data processing cost if data_processed_gb is provided
        data_cost = None
        if data_processed_gb is not None and data_processed_gb > 0 and data_prices:
            # Find the data processing price (per GB)
            data_price = next(
                (p["price"] for p in data_prices if "GB" in p["unit"]),
                None
            )
            
            if data_price is not None:
                data_cost = data_price * data_processed_gb
        
        # Create the result
        result = {
            "load_balancer_type": lb_type,
            "load_balancer_display_name": f"{lb_type_mapping[lb_type]} Load Balancer",
            "region": region,
            "hourly_pricing": lb_hourly_prices,
            "data_processing_pricing": data_prices
        }
        
        if data_cost is not None:
            result["data_processed_gb"] = data_processed_gb
            result["estimated_data_processing_cost"] = data_cost
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting load balancer pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting load balancer pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

@tool
def get_network_pricing(
    from_region: str,
    to_region: Optional[str] = None,
    to_internet: bool = False,
    data_transfer_gb: int = 100
) -> str:
    """
    Get AWS data transfer pricing between regions or to the internet.
    
    Args:
        from_region: Source AWS region code
        to_region: Destination AWS region code (optional, if transferring between regions)
        to_internet: Whether the data transfer is to the internet (default: False)
        data_transfer_gb: Amount of data to transfer in GB (default: 100)
    
    Returns:
        JSON string with network data transfer pricing information
    """
    try:
        # Validate inputs
        from_region = _validate_region(from_region)
        if to_region:
            to_region = _validate_region(to_region)
        
        # Define filters for pricing API
        filters = {
            "productFamily": "Data Transfer"
        }
        
        # Get pricing data
        pricing_data = _get_pricing_data("AmazonEC2", filters, from_region)
        
        # Process and format the results
        transfer_prices = []
        
        for product in pricing_data.get("products", []):
            product_attributes = product.get("product", {}).get("attributes", {})
            
            # Filter based on transfer type
            if to_internet and "DataTransfer-Out-Bytes" in product_attributes.get("usagetype", ""):
                # Data transfer to internet
                transfer_prices.append(_process_transfer_price(product, "Internet"))
            elif to_region and "DataTransfer-Regional-Bytes" in product_attributes.get("usagetype", ""):
                # Data transfer between regions
                transfer_prices.append(_process_transfer_price(product, f"Region ({to_region})"))
        
        # Calculate total cost
        total_cost = 0
        applicable_price = None
        
        if transfer_prices:
            # Find the applicable price tier based on data_transfer_gb
            for price in transfer_prices:
                if price.get("begin_range", 0) <= data_transfer_gb <= price.get("end_range", float("inf")):
                    applicable_price = price
                    break
            
            if applicable_price:
                total_cost = applicable_price.get("price", 0) * data_transfer_gb
        
        # Create the result
        result = {
            "from_region": from_region,
            "transfer_type": "Internet" if to_internet else f"Region ({to_region})" if to_region else "Unknown",
            "data_transfer_gb": data_transfer_gb,
            "pricing_tiers": transfer_prices,
            "estimated_cost": total_cost
        }
        
        if to_region:
            result["to_region"] = to_region
        
        return json.dumps(result, default=str)
    
    except (ClientError, BotoCoreError) as e:
        logger.error(f"AWS API error when getting network pricing: {str(e)}")
        return json.dumps({"error": f"AWS API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error when getting network pricing: {str(e)}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

def _process_transfer_price(product: Dict[str, Any], transfer_type: str) -> Dict[str, Any]:
    """Helper function to process data transfer pricing information."""
    product_attributes = product.get("product", {}).get("attributes", {})
    terms = product.get("terms", {})
    
    # Initialize price info
    price_info = {
        "transfer_type": transfer_type,
        "from_location": product_attributes.get("fromLocation", ""),
        "to_location": product_attributes.get("toLocation", ""),
        "price": 0.0,
        "currency": "USD",
        "begin_range": 0,
        "end_range": float("inf")
    }
    
    # Process On-Demand pricing
    on_demand_term = terms.get("OnDemand", {})
    for term_id, term_details in on_demand_term.items():
        for price_id, price_details in term_details.get("priceDimensions", {}).items():
            # Extract price
            price_info["price"] = _format_price(price_details.get("pricePerUnit", {}).get("USD", "0"))
            price_info["description"] = price_details.get("description", "")
            
            # Extract range information from description or rate code
            description = price_details.get("description", "")
            rate_code = price_details.get("rateCode", "")
            
            # Parse range from description (e.g., "first 10 TB / month")
            range_info = _parse_range_from_description(description)
            if range_info:
                price_info["begin_range"] = range_info[0]
                price_info["end_range"] = range_info[1]
    
    return price_info

def _parse_range_from_description(description: str) -> Optional[Tuple[float, float]]:
    """Parse data transfer range from description."""
    # Common patterns in AWS pricing descriptions
    if "first" in description.lower():
        # e.g., "first 10 TB / month"
        try:
            parts = description.lower().split()
            for i, part in enumerate(parts):
                if part == "first" and i + 1 < len(parts):
                    amount = float(parts[i + 1])
                    unit = parts[i + 2]
                    
                    # Convert to GB
                    if "tb" in unit:
                        amount *= 1024  # TB to GB
                    
                    return (0, amount)
        except (ValueError, IndexError):
            pass
    
    if "next" in description.lower():
        # e.g., "next 40 TB / month"
        try:
            parts = description.lower().split()
            for i, part in enumerate(parts):
                if part == "next" and i + 1 < len(parts):
                    amount = float(parts[i + 1])
                    unit = parts[i + 2]
                    
                    # Convert to GB
                    if "tb" in unit:
                        amount *= 1024  # TB to GB
                    
                    # We don't know the beginning, so return None
                    return None
        except (ValueError, IndexError):
            pass
    
    if "over" in description.lower():
        # e.g., "over 150 TB / month"
        try:
            parts = description.lower().split()
            for i, part in enumerate(parts):
                if part == "over" and i + 1 < len(parts):
                    amount = float(parts[i + 1])
                    unit = parts[i + 2]
                    
                    # Convert to GB
                    if "tb" in unit:
                        amount *= 1024  # TB to GB
                    
                    return (amount, float("inf"))
        except (ValueError, IndexError):
            pass
    
    return None

@tool
def calculate_aws_cost(
    resources: List[Dict[str, Any]],
    region: str = "us-east-1"
) -> str:
    """
    Calculate the total cost for a collection of AWS resources.
    
    Args:
        resources: List of resource configurations, each with 'type' and type-specific parameters
        region: AWS region code (default: us-east-1)
    
    Returns:
        JSON string with detailed cost breakdown and total cost
    
    Example resources list:
    [
        {
            "type": "ec2",
            "instance_type": "t3.micro",
            "os": "linux",
            "count": 2
        },
        {
            "type": "ebs",
            "volume_type": "gp3",
            "size_gb": 100
        },
        {
            "type": "s3",
            "storage_class": "standard",
            "storage_gb": 500,
            "data_transfer_gb": 200
        }
    ]
    """
    try:
        # Validate inputs
        region = _validate_region(region)
        
        if not isinstance(resources, list):
            return json.dumps({"error": "Resources must be a list"})
        
        # Process each resource and calculate costs
        cost_items = []
        total_cost = 0.0
        
        for resource in resources:
            resource_type = resource.get("type", "").lower()
            
            if resource_type == "ec2":
                cost_item = _calculate_ec2_cost(resource, region)
            elif resource_type == "ebs":
                cost_item = _calculate_ebs_cost(resource, region)
            elif resource_type == "s3":
                cost_item = _calculate_s3_cost(resource, region)
            elif resource_type == "rds":
                cost_item = _calculate_rds_cost(resource, region)
            elif resource_type == "elasticache":
                cost_item = _calculate_elasticache_cost(resource, region)
            elif resource_type == "opensearch":
                cost_item = _calculate_opensearch_cost(resource, region)
            elif resource_type == "loadbalancer":
                cost_item = _calculate_loadbalancer_cost(resource, region)
            elif resource_type == "network":
                cost_item = _calculate_network_cost(resource, region)
            else:
                cost_item = {
                    "resource_type": resource_type,
                    "error": f"Unsupported resource type: {resource_type}"
                }
            
            cost_items.append(cost_item)
            
            # Add to total if cost was calculated successfully
            if "monthly_cost" in cost_item and cost_item["monthly_cost"] is not None:
                total_cost += cost_item["monthly_cost"]
        
        # Create the result
        result = {
            "region": region,
            "cost_items": cost_items,
            "total_monthly_cost": total_cost,
            "currency": "USD"
        }
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error calculating AWS cost: {str(e)}")
        return json.dumps({"error": f"Error calculating AWS cost: {str(e)}"})

def _calculate_ec2_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate EC2 instance cost."""
    try:
        instance_type = resource.get("instance_type")
        os = resource.get("os", "linux")
        count = int(resource.get("count", 1))
        
        if not instance_type:
            return {"resource_type": "ec2", "error": "Missing instance_type parameter"}
        
        # Get EC2 pricing
        pricing_response = json.loads(get_ec2_pricing(instance_type, region, os))
        
        if "error" in pricing_response:
            return {"resource_type": "ec2", "error": pricing_response["error"]}
        
        # Get on-demand price per hour
        on_demand_prices = pricing_response.get("on_demand_pricing", [])
        if not on_demand_prices:
            return {"resource_type": "ec2", "error": "No pricing information found"}
        
        price_per_hour = on_demand_prices[0].get("price_per_hour", 0)
        monthly_cost = price_per_hour * 24 * 30 * count  # Approximate month as 30 days
        
        return {
            "resource_type": "ec2",
            "instance_type": instance_type,
            "os": os,
            "count": count,
            "price_per_hour": price_per_hour,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "ec2", "error": str(e)}

def _calculate_ebs_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate EBS volume cost."""
    try:
        volume_type = resource.get("volume_type")
        size_gb = int(resource.get("size_gb", 0))
        
        if not volume_type:
            return {"resource_type": "ebs", "error": "Missing volume_type parameter"}
        
        if size_gb <= 0:
            return {"resource_type": "ebs", "error": "Invalid or missing size_gb parameter"}
        
        # Get EBS pricing
        pricing_response = json.loads(get_ebs_pricing(volume_type, region, size_gb))
        
        if "error" in pricing_response:
            return {"resource_type": "ebs", "error": pricing_response["error"]}
        
        monthly_cost = pricing_response.get("estimated_monthly_cost")
        
        return {
            "resource_type": "ebs",
            "volume_type": volume_type,
            "size_gb": size_gb,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "ebs", "error": str(e)}

def _calculate_s3_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate S3 storage cost."""
    try:
        storage_class = resource.get("storage_class", "standard")
        storage_gb = int(resource.get("storage_gb", 0))
        data_transfer_gb = int(resource.get("data_transfer_gb", 0))
        
        # Get S3 pricing
        pricing_response = json.loads(get_s3_pricing(
            storage_class, region, storage_gb, data_transfer_gb
        ))
        
        if "error" in pricing_response:
            return {"resource_type": "s3", "error": pricing_response["error"]}
        
        storage_cost = pricing_response.get("estimated_monthly_storage_cost", 0)
        transfer_cost = pricing_response.get("estimated_data_transfer_cost", 0)
        monthly_cost = storage_cost + transfer_cost if storage_cost and transfer_cost else None
        
        return {
            "resource_type": "s3",
            "storage_class": storage_class,
            "storage_gb": storage_gb,
            "data_transfer_gb": data_transfer_gb,
            "storage_cost": storage_cost,
            "transfer_cost": transfer_cost,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "s3", "error": str(e)}

def _calculate_rds_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate RDS instance cost."""
    try:
        instance_type = resource.get("instance_type")
        engine = resource.get("engine")
        deployment_option = resource.get("deployment_option", "single-az")
        license_model = resource.get("license_model", "license-included")
        count = int(resource.get("count", 1))
        
        if not instance_type or not engine:
            return {"resource_type": "rds", "error": "Missing instance_type or engine parameter"}
        
        # Get RDS pricing
        pricing_response = json.loads(get_rds_pricing(
            instance_type, engine, region, deployment_option, license_model
        ))
        
        if "error" in pricing_response:
            return {"resource_type": "rds", "error": pricing_response["error"]}
        
        # Get on-demand price per hour
        on_demand_prices = pricing_response.get("on_demand_pricing", [])
        if not on_demand_prices:
            return {"resource_type": "rds", "error": "No pricing information found"}
        
        price_per_hour = on_demand_prices[0].get("price_per_hour", 0)
        monthly_cost = price_per_hour * 24 * 30 * count  # Approximate month as 30 days
        
        return {
            "resource_type": "rds",
            "instance_type": instance_type,
            "engine": engine,
            "deployment_option": deployment_option,
            "license_model": license_model,
            "count": count,
            "price_per_hour": price_per_hour,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "rds", "error": str(e)}

def _calculate_elasticache_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate ElastiCache cost."""
    try:
        node_type = resource.get("node_type")
        engine = resource.get("engine", "redis")
        count = int(resource.get("count", 1))
        
        if not node_type:
            return {"resource_type": "elasticache", "error": "Missing node_type parameter"}
        
        # Get ElastiCache pricing
        pricing_response = json.loads(get_elasticache_pricing(node_type, engine, region))
        
        if "error" in pricing_response:
            return {"resource_type": "elasticache", "error": pricing_response["error"]}
        
        # Get on-demand price per hour
        on_demand_prices = pricing_response.get("on_demand_pricing", [])
        if not on_demand_prices:
            return {"resource_type": "elasticache", "error": "No pricing information found"}
        
        price_per_hour = on_demand_prices[0].get("price_per_hour", 0)
        monthly_cost = price_per_hour * 24 * 30 * count  # Approximate month as 30 days
        
        return {
            "resource_type": "elasticache",
            "node_type": node_type,
            "engine": engine,
            "count": count,
            "price_per_hour": price_per_hour,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "elasticache", "error": str(e)}

def _calculate_opensearch_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate OpenSearch cost."""
    try:
        instance_type = resource.get("instance_type")
        storage_gb = int(resource.get("storage_gb", 0))
        count = int(resource.get("count", 1))
        
        if not instance_type:
            return {"resource_type": "opensearch", "error": "Missing instance_type parameter"}
        
        # Get OpenSearch pricing
        pricing_response = json.loads(get_opensearch_pricing(instance_type, region, storage_gb))
        
        if "error" in pricing_response:
            return {"resource_type": "opensearch", "error": pricing_response["error"]}
        
        # Get instance price
        instance_prices = pricing_response.get("instance_pricing", [])
        if not instance_prices:
            return {"resource_type": "opensearch", "error": "No pricing information found"}
        
        # Find hourly price
        instance_price = next(
            (p["price"] for p in instance_prices if "Hrs" in p["unit"]),
            0
        )
        
        instance_monthly_cost = instance_price * 24 * 30 * count  # Approximate month as 30 days
        storage_monthly_cost = pricing_response.get("estimated_monthly_storage_cost", 0)
        
        monthly_cost = instance_monthly_cost + storage_monthly_cost
        
        return {
            "resource_type": "opensearch",
            "instance_type": instance_type,
            "storage_gb": storage_gb,
            "count": count,
            "instance_monthly_cost": instance_monthly_cost,
            "storage_monthly_cost": storage_monthly_cost,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "opensearch", "error": str(e)}

def _calculate_loadbalancer_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate Load Balancer cost."""
    try:
        lb_type = resource.get("lb_type")
        data_processed_gb = int(resource.get("data_processed_gb", 0))
        count = int(resource.get("count", 1))
        
        if not lb_type:
            return {"resource_type": "loadbalancer", "error": "Missing lb_type parameter"}
        
        # Get Load Balancer pricing
        pricing_response = json.loads(get_loadbalancer_pricing(lb_type, region, data_processed_gb))
        
        if "error" in pricing_response:
            return {"resource_type": "loadbalancer", "error": pricing_response["error"]}
        
        # Get hourly price
        hourly_prices = pricing_response.get("hourly_pricing", [])
        if not hourly_prices:
            return {"resource_type": "loadbalancer", "error": "No pricing information found"}
        
        hourly_price = hourly_prices[0].get("price", 0)
        lb_monthly_cost = hourly_price * 24 * 30 * count  # Approximate month as 30 days
        
        data_cost = pricing_response.get("estimated_data_processing_cost", 0)
        monthly_cost = lb_monthly_cost + data_cost
        
        return {
            "resource_type": "loadbalancer",
            "lb_type": lb_type,
            "data_processed_gb": data_processed_gb,
            "count": count,
            "lb_monthly_cost": lb_monthly_cost,
            "data_processing_cost": data_cost,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "loadbalancer", "error": str(e)}

def _calculate_network_cost(resource: Dict[str, Any], region: str) -> Dict[str, Any]:
    """Calculate Network data transfer cost."""
    try:
        from_region = resource.get("from_region", region)
        to_region = resource.get("to_region")
        to_internet = bool(resource.get("to_internet", False))
        data_transfer_gb = int(resource.get("data_transfer_gb", 0))
        
        if not from_region:
            return {"resource_type": "network", "error": "Missing from_region parameter"}
        
        if not to_region and not to_internet:
            return {"resource_type": "network", "error": "Either to_region or to_internet must be specified"}
        
        # Get Network pricing
        pricing_response = json.loads(get_network_pricing(
            from_region, to_region, to_internet, data_transfer_gb
        ))
        
        if "error" in pricing_response:
            return {"resource_type": "network", "error": pricing_response["error"]}
        
        monthly_cost = pricing_response.get("estimated_cost", 0)
        
        return {
            "resource_type": "network",
            "from_region": from_region,
            "to_region": to_region,
            "to_internet": to_internet,
            "data_transfer_gb": data_transfer_gb,
            "monthly_cost": monthly_cost,
            "currency": "USD"
        }
    
    except Exception as e:
        return {"resource_type": "network", "error": str(e)}