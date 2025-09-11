"""
AWS Utilities - Common Functions and Helpers Module

This module provides utility functions and helpers for AWS pricing and recommendation tools.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# AWS Service Mapping
AWS_SERVICES = {
    "AmazonEC2": "Amazon Elastic Compute Cloud (EC2)",
    "AmazonS3": "Amazon Simple Storage Service (S3)",
    "AmazonRDS": "Amazon Relational Database Service (RDS)",
    "AmazonElastiCache": "Amazon ElastiCache",
    "AmazonES": "Amazon OpenSearch Service",
    "AmazonEBS": "Amazon Elastic Block Store (EBS)",
    "AmazonRoute53": "Amazon Route 53",
    "AmazonCloudFront": "Amazon CloudFront",
    "AmazonVPC": "Amazon Virtual Private Cloud (VPC)",
    "AmazonCloudWatch": "Amazon CloudWatch",
    "AmazonSNS": "Amazon Simple Notification Service (SNS)",
    "AmazonSQS": "Amazon Simple Queue Service (SQS)",
    "AmazonDynamoDB": "Amazon DynamoDB",
    "AWSLambda": "AWS Lambda",
    "AmazonECR": "Amazon Elastic Container Registry (ECR)",
    "AmazonECS": "Amazon Elastic Container Service (ECS)",
    "AmazonEKS": "Amazon Elastic Kubernetes Service (EKS)"
}

@tool
def get_aws_regions() -> str:
    """
    Get a list of all AWS regions with their display names.
    
    Returns:
        JSON string with AWS regions and their display names
    """
    try:
        result = {
            "regions": []
        }
        
        for region_code, region_name in AWS_REGIONS.items():
            result["regions"].append({
                "region_code": region_code,
                "region_name": region_name
            })
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error getting AWS regions: {str(e)}")
        return json.dumps({"error": f"Error getting AWS regions: {str(e)}"})

@tool
def get_aws_services() -> str:
    """
    Get a list of AWS services supported by the pricing API.
    
    Returns:
        JSON string with AWS services and their display names
    """
    try:
        result = {
            "services": []
        }
        
        for service_code, service_name in AWS_SERVICES.items():
            result["services"].append({
                "service_code": service_code,
                "service_name": service_name
            })
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error getting AWS services: {str(e)}")
        return json.dumps({"error": f"Error getting AWS services: {str(e)}"})

@tool
def validate_aws_region(region: str) -> str:
    """
    Validate if a given string is a valid AWS region code.
    
    Args:
        region: AWS region code to validate
    
    Returns:
        JSON string with validation result
    """
    try:
        result = {
            "input": region,
            "is_valid": False,
            "normalized_region": None,
            "region_name": None,
            "alternatives": []
        }
        
        # Check for exact match (case-insensitive)
        for r in AWS_REGIONS:
            if r.lower() == region.lower():
                result["is_valid"] = True
                result["normalized_region"] = r
                result["region_name"] = AWS_REGIONS[r]
                return json.dumps(result, ensure_ascii=False)
        
        # If not exact match, find alternatives
        for r, name in AWS_REGIONS.items():
            # Check for partial match in code or name
            if region.lower() in r.lower() or region.lower() in name.lower():
                result["alternatives"].append({
                    "region_code": r,
                    "region_name": name
                })
        
        # Sort alternatives by similarity
        result["alternatives"] = sorted(
            result["alternatives"], 
            key=lambda x: _similarity_score(region, x["region_code"])
        )
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error validating AWS region: {str(e)}")
        return json.dumps({"error": f"Error validating AWS region: {str(e)}"})

def _similarity_score(input_str: str, target: str) -> float:
    """Calculate a simple similarity score between two strings."""
    input_lower = input_str.lower()
    target_lower = target.lower()
    
    # Exact match gets highest score
    if input_lower == target_lower:
        return 1.0
    
    # Prefix match gets high score
    if target_lower.startswith(input_lower):
        return 0.9
    
    # Contains match gets medium score
    if input_lower in target_lower:
        return 0.7
    
    # Partial character match gets low score
    common_chars = set(input_lower) & set(target_lower)
    return len(common_chars) / max(len(input_lower), len(target_lower))

@tool
def get_available_instance_families() -> str:
    """
    Get a list of available EC2 instance families with their descriptions.
    
    Returns:
        JSON string with EC2 instance families and their descriptions
    """
    try:
        # EC2 instance family characteristics
        instance_families = {
            "t": {
                "name": "T-series",
                "description": "Burstable performance instances",
                "use_case": "Development, testing, low-traffic websites",
                "suitable_for_production": False,
                "cpu_performance": "Burstable",
                "memory_ratio": "Moderate",
                "network_performance": "Low to Moderate",
                "examples": ["t3.micro", "t3.small", "t3.medium", "t3.large"]
            },
            "m": {
                "name": "M-series",
                "description": "General purpose instances",
                "use_case": "Web servers, small databases, development environments",
                "suitable_for_production": True,
                "cpu_performance": "Balanced",
                "memory_ratio": "Balanced",
                "network_performance": "Moderate to High",
                "examples": ["m5.large", "m5.xlarge", "m5.2xlarge", "m5.4xlarge"]
            },
            "c": {
                "name": "C-series",
                "description": "Compute optimized instances",
                "use_case": "High-performance web servers, scientific modeling, batch processing",
                "suitable_for_production": True,
                "cpu_performance": "High",
                "memory_ratio": "Low",
                "network_performance": "High",
                "examples": ["c5.large", "c5.xlarge", "c5.2xlarge", "c5.4xlarge"]
            },
            "r": {
                "name": "R-series",
                "description": "Memory optimized instances",
                "use_case": "Memory-intensive applications, in-memory databases, real-time big data analytics",
                "suitable_for_production": True,
                "cpu_performance": "Moderate",
                "memory_ratio": "High",
                "network_performance": "High",
                "examples": ["r5.large", "r5.xlarge", "r5.2xlarge", "r5.4xlarge"]
            },
            "x": {
                "name": "X-series",
                "description": "Memory optimized instances with highest memory ratio",
                "use_case": "High-performance databases, in-memory databases, big data processing engines",
                "suitable_for_production": True,
                "cpu_performance": "High",
                "memory_ratio": "Very High",
                "network_performance": "Very High",
                "examples": ["x1.16xlarge", "x1.32xlarge", "x1e.xlarge", "x1e.2xlarge"]
            },
            "i": {
                "name": "I-series",
                "description": "Storage optimized instances",
                "use_case": "Data warehousing, Hadoop, distributed file systems",
                "suitable_for_production": True,
                "cpu_performance": "High",
                "memory_ratio": "Moderate",
                "network_performance": "Very High",
                "storage_performance": "Very High",
                "examples": ["i3.large", "i3.xlarge", "i3.2xlarge", "i3.4xlarge"]
            },
            "g": {
                "name": "G-series",
                "description": "GPU instances",
                "use_case": "Machine learning, high-performance computing, graphics rendering",
                "suitable_for_production": True,
                "cpu_performance": "High",
                "memory_ratio": "High",
                "network_performance": "Very High",
                "gpu": "Yes",
                "examples": ["g4dn.xlarge", "g4dn.2xlarge", "g4dn.4xlarge", "g4dn.8xlarge"]
            },
            "p": {
                "name": "P-series",
                "description": "GPU instances optimized for machine learning",
                "use_case": "Deep learning, high-performance databases, computational fluid dynamics",
                "suitable_for_production": True,
                "cpu_performance": "High",
                "memory_ratio": "High",
                "network_performance": "Very High",
                "gpu": "Yes",
                "examples": ["p3.2xlarge", "p3.8xlarge", "p3.16xlarge", "p3dn.24xlarge"]
            }
        }
        
        result = {
            "instance_families": []
        }
        
        for family_code, family_info in instance_families.items():
            result["instance_families"].append({
                "family_code": family_code,
                "name": family_info.get("name"),
                "description": family_info.get("description"),
                "use_case": family_info.get("use_case"),
                "suitable_for_production": family_info.get("suitable_for_production"),
                "examples": family_info.get("examples")
            })
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error getting EC2 instance families: {str(e)}")
        return json.dumps({"error": f"Error getting EC2 instance families: {str(e)}"})

@tool
def get_available_storage_types() -> str:
    """
    Get a list of available EBS volume types with their descriptions.
    
    Returns:
        JSON string with EBS volume types and their descriptions
    """
    try:
        # EBS volume type characteristics
        volume_types = {
            "gp3": {
                "name": "General Purpose SSD (gp3)",
                "description": "Latest generation of General Purpose SSD volumes",
                "use_case": "Boot volumes, development and test environments, low-latency interactive applications",
                "baseline_iops": 3000,
                "max_iops": 16000,
                "baseline_throughput": "125 MB/s",
                "max_throughput": "1000 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "High"
            },
            "gp2": {
                "name": "General Purpose SSD (gp2)",
                "description": "Previous generation of General Purpose SSD volumes",
                "use_case": "Boot volumes, development and test environments, low-latency interactive applications",
                "baseline_iops": "3 IOPS/GB (minimum 100)",
                "max_iops": 16000,
                "baseline_throughput": "Dependent on IOPS",
                "max_throughput": "250 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "Moderate"
            },
            "io1": {
                "name": "Provisioned IOPS SSD (io1)",
                "description": "Previous generation of high-performance SSD volumes",
                "use_case": "Critical business applications that require sustained IOPS performance",
                "baseline_iops": "User provisioned (up to 50 IOPS/GB)",
                "max_iops": 64000,
                "baseline_throughput": "Dependent on IOPS",
                "max_throughput": "1000 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "Low"
            },
            "io2": {
                "name": "Provisioned IOPS SSD (io2)",
                "description": "Latest generation of high-performance SSD volumes",
                "use_case": "Critical business applications that require sustained IOPS performance with higher durability",
                "baseline_iops": "User provisioned (up to 500 IOPS/GB)",
                "max_iops": 64000,
                "baseline_throughput": "Dependent on IOPS",
                "max_throughput": "1000 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "Low"
            },
            "st1": {
                "name": "Throughput Optimized HDD (st1)",
                "description": "Low-cost HDD volume designed for frequently accessed, throughput-intensive workloads",
                "use_case": "Big data, data warehouses, log processing",
                "baseline_iops": "Not applicable for HDD",
                "max_iops": 500,
                "baseline_throughput": "40 MB/s per TB",
                "max_throughput": "500 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "High"
            },
            "sc1": {
                "name": "Cold HDD (sc1)",
                "description": "Lowest cost HDD volume designed for less frequently accessed workloads",
                "use_case": "Infrequently accessed data, lowest cost storage",
                "baseline_iops": "Not applicable for HDD",
                "max_iops": 250,
                "baseline_throughput": "12 MB/s per TB",
                "max_throughput": "250 MB/s",
                "suitable_for_production": True,
                "cost_effectiveness": "Very High"
            },
            "standard": {
                "name": "Magnetic (standard)",
                "description": "Previous generation magnetic volumes",
                "use_case": "Legacy applications, infrequently accessed data",
                "baseline_iops": "Variable",
                "max_iops": "40-200",
                "baseline_throughput": "Variable",
                "max_throughput": "40-90 MB/s",
                "suitable_for_production": False,
                "cost_effectiveness": "Moderate"
            }
        }
        
        result = {
            "volume_types": []
        }
        
        for type_code, type_info in volume_types.items():
            result["volume_types"].append({
                "type_code": type_code,
                "name": type_info.get("name"),
                "description": type_info.get("description"),
                "use_case": type_info.get("use_case"),
                "baseline_iops": type_info.get("baseline_iops"),
                "max_iops": type_info.get("max_iops"),
                "baseline_throughput": type_info.get("baseline_throughput"),
                "max_throughput": type_info.get("max_throughput"),
                "suitable_for_production": type_info.get("suitable_for_production"),
                "cost_effectiveness": type_info.get("cost_effectiveness")
            })
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error getting EBS volume types: {str(e)}")
        return json.dumps({"error": f"Error getting EBS volume types: {str(e)}"})

@tool
def get_available_database_engines() -> str:
    """
    Get a list of available RDS database engines with their descriptions.
    
    Returns:
        JSON string with RDS database engines and their descriptions
    """
    try:
        # Database engine characteristics
        db_engines = {
            "mysql": {
                "name": "MySQL Community Edition",
                "description": "Open-source relational database",
                "use_case": "Web applications, e-commerce, content management systems",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "No",
                "performance": "Good",
                "ease_of_use": "High",
                "versions": ["5.7", "8.0"]
            },
            "postgresql": {
                "name": "PostgreSQL",
                "description": "Advanced open-source relational database",
                "use_case": "Complex queries, data warehousing, GIS applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "No",
                "performance": "Excellent",
                "ease_of_use": "Moderate",
                "versions": ["11", "12", "13", "14"]
            },
            "mariadb": {
                "name": "MariaDB",
                "description": "Community-developed fork of MySQL",
                "use_case": "Similar to MySQL, drop-in replacement with additional features",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "No",
                "performance": "Good",
                "ease_of_use": "High",
                "versions": ["10.3", "10.4", "10.5", "10.6"]
            },
            "aurora": {
                "name": "Amazon Aurora MySQL",
                "description": "MySQL-compatible database with up to 5x performance",
                "use_case": "Enterprise applications requiring high throughput",
                "max_db_size": "128 TB",
                "suitable_for_production": True,
                "license_cost": "No",
                "performance": "Very High",
                "ease_of_use": "High",
                "versions": ["2.x (MySQL 5.7 compatible)", "3.x (MySQL 8.0 compatible)"]
            },
            "aurora-postgresql": {
                "name": "Amazon Aurora PostgreSQL",
                "description": "PostgreSQL-compatible database with up to 3x performance",
                "use_case": "Enterprise applications requiring high throughput and PostgreSQL compatibility",
                "max_db_size": "128 TB",
                "suitable_for_production": True,
                "license_cost": "No",
                "performance": "Very High",
                "ease_of_use": "Moderate",
                "versions": ["11", "12", "13", "14"]
            },
            "oracle-se": {
                "name": "Oracle Standard Edition",
                "description": "Commercial relational database",
                "use_case": "Small to medium-sized business applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes",
                "performance": "High",
                "ease_of_use": "Moderate",
                "versions": ["12.1", "12.2", "19"]
            },
            "oracle-se1": {
                "name": "Oracle Standard Edition One",
                "description": "Entry-level commercial relational database",
                "use_case": "Small to medium-sized business applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes",
                "performance": "High",
                "ease_of_use": "Moderate",
                "versions": ["12.1"]
            },
            "oracle-se2": {
                "name": "Oracle Standard Edition Two",
                "description": "Replacement for Standard Edition and Standard Edition One",
                "use_case": "Small to medium-sized business applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes",
                "performance": "High",
                "ease_of_use": "Moderate",
                "versions": ["12.1", "12.2", "19"]
            },
            "oracle-ee": {
                "name": "Oracle Enterprise Edition",
                "description": "Full-featured commercial relational database",
                "use_case": "Mission-critical enterprise applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes (High)",
                "performance": "Very High",
                "ease_of_use": "Moderate",
                "versions": ["12.1", "12.2", "19"]
            },
            "sqlserver-ex": {
                "name": "Microsoft SQL Server Express",
                "description": "Entry-level version of SQL Server",
                "use_case": "Small applications, development and testing",
                "max_db_size": "10 GB",
                "suitable_for_production": False,
                "license_cost": "No",
                "performance": "Moderate",
                "ease_of_use": "High",
                "versions": ["2014", "2016", "2017", "2019"]
            },
            "sqlserver-web": {
                "name": "Microsoft SQL Server Web",
                "description": "Version of SQL Server for web workloads",
                "use_case": "Web applications and websites",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes (Low)",
                "performance": "Good",
                "ease_of_use": "High",
                "versions": ["2014", "2016", "2017", "2019"]
            },
            "sqlserver-se": {
                "name": "Microsoft SQL Server Standard",
                "description": "Standard version of SQL Server",
                "use_case": "Departmental applications, medium-sized businesses",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes",
                "performance": "High",
                "ease_of_use": "High",
                "versions": ["2014", "2016", "2017", "2019"]
            },
            "sqlserver-ee": {
                "name": "Microsoft SQL Server Enterprise",
                "description": "Full-featured version of SQL Server",
                "use_case": "Mission-critical enterprise applications",
                "max_db_size": "64 TB",
                "suitable_for_production": True,
                "license_cost": "Yes (High)",
                "performance": "Very High",
                "ease_of_use": "High",
                "versions": ["2014", "2016", "2017", "2019"]
            }
        }
        
        result = {
            "database_engines": []
        }
        
        for engine_code, engine_info in db_engines.items():
            result["database_engines"].append({
                "engine_code": engine_code,
                "name": engine_info.get("name"),
                "description": engine_info.get("description"),
                "use_case": engine_info.get("use_case"),
                "max_db_size": engine_info.get("max_db_size"),
                "suitable_for_production": engine_info.get("suitable_for_production"),
                "license_cost": engine_info.get("license_cost"),
                "performance": engine_info.get("performance"),
                "ease_of_use": engine_info.get("ease_of_use"),
                "versions": engine_info.get("versions")
            })
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error getting RDS database engines: {str(e)}")
        return json.dumps({"error": f"Error getting RDS database engines: {str(e)}"})

@tool
def get_aws_pricing_api_status() -> str:
    """
    Check the status of AWS Pricing API and available endpoints.
    
    Returns:
        JSON string with AWS Pricing API status and available endpoints
    """
    try:
        # Create a boto3 pricing client
        pricing_client = boto3.client('pricing', region_name='us-east-1')
        
        # Get service codes
        response = pricing_client.describe_services()
        
        services = []
        for service in response.get('Services', []):
            service_code = service.get('ServiceCode')
            service_name = AWS_SERVICES.get(service_code, service_code)
            
            # Get attribute names for the service
            attr_response = pricing_client.describe_services(ServiceCode=service_code)
            attribute_names = []
            if attr_response.get('Services') and len(attr_response.get('Services')) > 0:
                for attr in attr_response['Services'][0].get('AttributeNames', []):
                    attribute_names.append(attr)
            
            services.append({
                "service_code": service_code,
                "service_name": service_name,
                "attribute_names": attribute_names
            })
        
        # Check China region status
        china_status = "Unknown"
        try:
            # Try to create a pricing client for China region
            cn_pricing_client = boto3.client('pricing', region_name='cn-northwest-1')
            cn_response = cn_pricing_client.describe_services()
            china_status = "Available" if cn_response.get('Services') else "No services available"
        except Exception as e:
            china_status = f"Unavailable: {str(e)}"
        
        result = {
            "status": "Available",
            "api_endpoints": [
                {
                    "region": "us-east-1",
                    "status": "Available",
                    "service_count": len(services)
                },
                {
                    "region": "ap-south-1",
                    "status": "Available",
                    "service_count": len(services)
                },
                {
                    "region": "cn-northwest-1",
                    "status": china_status
                }
            ],
            "available_services": services[:10],  # Limit to first 10 services for brevity
            "total_services": len(services)
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error checking AWS Pricing API status: {str(e)}")
        return json.dumps({
            "status": "Error",
            "error": f"Error checking AWS Pricing API status: {str(e)}"
        })

@tool
def parse_requirements(description: str) -> str:
    """
    Parse natural language requirements into structured AWS resource requirements.
    
    Args:
        description: Natural language description of requirements
    
    Returns:
        JSON string with structured AWS resource requirements
    """
    try:
        # Initialize result structure
        result = {
            "parsed_requirements": {
                "compute": {},
                "storage": {},
                "database": {},
                "cache": {},
                "network": {},
                "region": None,
                "is_production": True
            },
            "detected_services": [],
            "confidence": "medium"
        }
        
        # Extract CPU and memory requirements
        cpu_pattern = r'(\d+)\s*(?:cpu|core|vcpu|processor)s?'
        memory_pattern = r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g)\s*(?:ram|memory|内存)'
        
        cpu_match = re.search(cpu_pattern, description, re.IGNORECASE)
        if cpu_match:
            result["parsed_requirements"]["compute"]["cpu_cores"] = int(cpu_match.group(1))
            result["detected_services"].append("EC2")
        
        memory_match = re.search(memory_pattern, description, re.IGNORECASE)
        if memory_match:
            result["parsed_requirements"]["compute"]["memory_gb"] = float(memory_match.group(1))
            if "EC2" not in result["detected_services"]:
                result["detected_services"].append("EC2")
        
        # Extract storage requirements
        storage_pattern = r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:storage|disk|volume|存储|磁盘)'
        storage_type_pattern = r'(ssd|hdd|gp2|gp3|io1|io2|st1|sc1|standard)\s*(?:storage|disk|volume|存储|磁盘)'
        
        storage_match = re.search(storage_pattern, description, re.IGNORECASE)
        if storage_match:
            size_value = float(storage_match.group(1))
            size_unit = re.search(r'(tb|tib|t)', storage_match.group(0), re.IGNORECASE)
            
            if size_unit:  # Convert TB to GB
                result["parsed_requirements"]["storage"]["size_gb"] = int(size_value * 1024)
            else:
                result["parsed_requirements"]["storage"]["size_gb"] = int(size_value)
            
            result["detected_services"].append("EBS")
        
        storage_type_match = re.search(storage_type_pattern, description, re.IGNORECASE)
        if storage_type_match:
            storage_type = storage_type_match.group(1).lower()
            
            # Map general types to specific EBS types
            if storage_type == "ssd":
                storage_type = "gp3"  # Default to gp3 for SSD
            elif storage_type == "hdd":
                storage_type = "st1"  # Default to st1 for HDD
            
            result["parsed_requirements"]["storage"]["volume_type"] = storage_type
            if "EBS" not in result["detected_services"]:
                result["detected_services"].append("EBS")
        
        # Extract database requirements
        db_pattern = r'(mysql|postgresql|postgres|oracle|sqlserver|mariadb|aurora)\s*(?:database|db|数据库)'
        db_match = re.search(db_pattern, description, re.IGNORECASE)
        if db_match:
            db_engine = db_match.group(1).lower()
            if db_engine == "postgres":
                db_engine = "postgresql"
            
            result["parsed_requirements"]["database"]["engine"] = db_engine
            result["detected_services"].append("RDS")
        
        # Extract cache requirements
        cache_pattern = r'(redis|memcached)\s*(?:cache|缓存)'
        cache_match = re.search(cache_pattern, description, re.IGNORECASE)
        if cache_match:
            result["parsed_requirements"]["cache"]["engine"] = cache_match.group(1).lower()
            result["detected_services"].append("ElastiCache")
        
        # Extract S3 requirements
        s3_pattern = r'(s3|object storage|对象存储)'
        s3_match = re.search(s3_pattern, description, re.IGNORECASE)
        if s3_match:
            result["detected_services"].append("S3")
        
        # Extract load balancer requirements
        lb_pattern = r'(load balancer|loadbalancer|alb|nlb|elb|负载均衡)'
        lb_match = re.search(lb_pattern, description, re.IGNORECASE)
        if lb_match:
            result["detected_services"].append("ELB")
        
        # Extract region requirements
        region_pattern = r'(?:region|地区|区域)\s*[为是:：]?\s*(us-east-1|us-east-2|us-west-1|us-west-2|eu-west-1|eu-west-2|eu-west-3|eu-central-1|ap-northeast-1|ap-northeast-2|ap-northeast-3|ap-southeast-1|ap-southeast-2|ap-south-1|sa-east-1|ca-central-1|cn-north-1|cn-northwest-1)'
        region_match = re.search(region_pattern, description, re.IGNORECASE)
        if region_match:
            result["parsed_requirements"]["region"] = region_match.group(1)
        
        # Extract environment type
        env_pattern = r'(production|prod|生产环境|正式环境|development|dev|测试环境|开发环境|非生产环境)'
        env_match = re.search(env_pattern, description, re.IGNORECASE)
        if env_match:
            matched_text = env_match.group(1).lower()
            if any(term in matched_text for term in ["development", "dev", "测试", "开发", "非生产"]):
                result["parsed_requirements"]["is_production"] = False
        
        # Set confidence level based on the number of detected requirements
        detected_count = sum(1 for section in result["parsed_requirements"].values() if section)
        if detected_count >= 4:
            result["confidence"] = "high"
        elif detected_count <= 1:
            result["confidence"] = "low"
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"Error parsing requirements: {str(e)}")
        return json.dumps({"error": f"Error parsing requirements: {str(e)}"})