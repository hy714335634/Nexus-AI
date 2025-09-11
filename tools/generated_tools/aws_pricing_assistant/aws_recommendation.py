"""
AWS Recommendation Tools - Intelligent Configuration Recommendation Module

This module provides intelligent recommendation functionality for AWS resources
based on user requirements and best practices.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Union, Any, Tuple
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# Import pricing tools
from tools.generated_tools.aws_pricing_assistant.aws_pricing_api import (
    get_ec2_instance_types,
    get_ec2_pricing,
    get_ebs_pricing,
    get_s3_pricing,
    get_rds_pricing,
    get_elasticache_pricing,
    get_opensearch_pricing,
    get_loadbalancer_pricing,
    get_network_pricing,
    calculate_aws_cost
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# EC2 instance family characteristics
EC2_INSTANCE_FAMILIES = {
    "t": {
        "description": "Burstable performance instances",
        "use_case": "Development, testing, low-traffic websites",
        "suitable_for_production": False,
        "cpu_performance": "Burstable",
        "memory_ratio": "Moderate",
        "network_performance": "Low to Moderate"
    },
    "m": {
        "description": "General purpose instances",
        "use_case": "Web servers, small databases, development environments",
        "suitable_for_production": True,
        "cpu_performance": "Balanced",
        "memory_ratio": "Balanced",
        "network_performance": "Moderate to High"
    },
    "c": {
        "description": "Compute optimized instances",
        "use_case": "High-performance web servers, scientific modeling, batch processing",
        "suitable_for_production": True,
        "cpu_performance": "High",
        "memory_ratio": "Low",
        "network_performance": "High"
    },
    "r": {
        "description": "Memory optimized instances",
        "use_case": "Memory-intensive applications, in-memory databases, real-time big data analytics",
        "suitable_for_production": True,
        "cpu_performance": "Moderate",
        "memory_ratio": "High",
        "network_performance": "High"
    },
    "x": {
        "description": "Memory optimized instances with highest memory ratio",
        "use_case": "High-performance databases, in-memory databases, big data processing engines",
        "suitable_for_production": True,
        "cpu_performance": "High",
        "memory_ratio": "Very High",
        "network_performance": "Very High"
    },
    "i": {
        "description": "Storage optimized instances",
        "use_case": "Data warehousing, Hadoop, distributed file systems",
        "suitable_for_production": True,
        "cpu_performance": "High",
        "memory_ratio": "Moderate",
        "network_performance": "Very High",
        "storage_performance": "Very High"
    },
    "g": {
        "description": "GPU instances",
        "use_case": "Machine learning, high-performance computing, graphics rendering",
        "suitable_for_production": True,
        "cpu_performance": "High",
        "memory_ratio": "High",
        "network_performance": "Very High",
        "gpu": "Yes"
    },
    "p": {
        "description": "GPU instances optimized for machine learning",
        "use_case": "Deep learning, high-performance databases, computational fluid dynamics",
        "suitable_for_production": True,
        "cpu_performance": "High",
        "memory_ratio": "High",
        "network_performance": "Very High",
        "gpu": "Yes"
    }
}

# EBS volume type characteristics
EBS_VOLUME_TYPES = {
    "gp3": {
        "description": "General Purpose SSD (gp3)",
        "use_case": "Boot volumes, development and test environments, low-latency interactive applications",
        "baseline_iops": 3000,
        "max_iops": 16000,
        "baseline_throughput": "125 MB/s",
        "max_throughput": "1000 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "High"
    },
    "gp2": {
        "description": "General Purpose SSD (gp2)",
        "use_case": "Boot volumes, development and test environments, low-latency interactive applications",
        "baseline_iops": "3 IOPS/GB (minimum 100)",
        "max_iops": 16000,
        "baseline_throughput": "Dependent on IOPS",
        "max_throughput": "250 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "Moderate"
    },
    "io1": {
        "description": "Provisioned IOPS SSD (io1)",
        "use_case": "Critical business applications that require sustained IOPS performance",
        "baseline_iops": "User provisioned (up to 50 IOPS/GB)",
        "max_iops": 64000,
        "baseline_throughput": "Dependent on IOPS",
        "max_throughput": "1000 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "Low"
    },
    "io2": {
        "description": "Provisioned IOPS SSD (io2)",
        "use_case": "Critical business applications that require sustained IOPS performance with higher durability",
        "baseline_iops": "User provisioned (up to 500 IOPS/GB)",
        "max_iops": 64000,
        "baseline_throughput": "Dependent on IOPS",
        "max_throughput": "1000 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "Low"
    },
    "st1": {
        "description": "Throughput Optimized HDD (st1)",
        "use_case": "Big data, data warehouses, log processing",
        "baseline_iops": "Not applicable for HDD",
        "max_iops": 500,
        "baseline_throughput": "40 MB/s per TB",
        "max_throughput": "500 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "High"
    },
    "sc1": {
        "description": "Cold HDD (sc1)",
        "use_case": "Infrequently accessed data, lowest cost storage",
        "baseline_iops": "Not applicable for HDD",
        "max_iops": 250,
        "baseline_throughput": "12 MB/s per TB",
        "max_throughput": "250 MB/s",
        "suitable_for_production": True,
        "cost_effectiveness": "Very High"
    },
    "standard": {
        "description": "Magnetic (standard)",
        "use_case": "Legacy applications, infrequently accessed data",
        "baseline_iops": "Variable",
        "max_iops": "40-200",
        "baseline_throughput": "Variable",
        "max_throughput": "40-90 MB/s",
        "suitable_for_production": False,
        "cost_effectiveness": "Moderate"
    }
}

# S3 storage class characteristics
S3_STORAGE_CLASSES = {
    "standard": {
        "description": "Amazon S3 Standard",
        "use_case": "Frequently accessed data, low-latency access",
        "availability": "99.99%",
        "durability": "99.999999999%",
        "min_storage_duration": "None",
        "retrieval_fee": "No",
        "cost_effectiveness": "Moderate"
    },
    "intelligent_tiering": {
        "description": "Amazon S3 Intelligent-Tiering",
        "use_case": "Data with unknown or changing access patterns",
        "availability": "99.9%",
        "durability": "99.999999999%",
        "min_storage_duration": "30 days",
        "retrieval_fee": "No",
        "cost_effectiveness": "High"
    },
    "standard_ia": {
        "description": "Amazon S3 Standard-IA (Infrequent Access)",
        "use_case": "Long-lived, infrequently accessed data",
        "availability": "99.9%",
        "durability": "99.999999999%",
        "min_storage_duration": "30 days",
        "retrieval_fee": "Yes",
        "cost_effectiveness": "High"
    },
    "onezone_ia": {
        "description": "Amazon S3 One Zone-IA",
        "use_case": "Infrequently accessed data that can be recreated",
        "availability": "99.5%",
        "durability": "99.999999999% (single AZ)",
        "min_storage_duration": "30 days",
        "retrieval_fee": "Yes",
        "cost_effectiveness": "Very High"
    },
    "glacier": {
        "description": "Amazon S3 Glacier",
        "use_case": "Archive data with retrieval times of minutes to hours",
        "availability": "99.99%",
        "durability": "99.999999999%",
        "min_storage_duration": "90 days",
        "retrieval_fee": "Yes",
        "cost_effectiveness": "Very High"
    },
    "deep_archive": {
        "description": "Amazon S3 Glacier Deep Archive",
        "use_case": "Long-term data archiving accessed once or twice a year",
        "availability": "99.99%",
        "durability": "99.999999999%",
        "min_storage_duration": "180 days",
        "retrieval_fee": "Yes",
        "cost_effectiveness": "Extremely High"
    }
}

# Database engine characteristics
DB_ENGINE_CHARACTERISTICS = {
    "mysql": {
        "description": "MySQL Community Edition",
        "use_case": "Web applications, e-commerce, content management systems",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "No",
        "performance": "Good",
        "ease_of_use": "High"
    },
    "postgresql": {
        "description": "PostgreSQL",
        "use_case": "Complex queries, data warehousing, GIS applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "No",
        "performance": "Excellent",
        "ease_of_use": "Moderate"
    },
    "mariadb": {
        "description": "MariaDB",
        "use_case": "Similar to MySQL, drop-in replacement with additional features",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "No",
        "performance": "Good",
        "ease_of_use": "High"
    },
    "aurora": {
        "description": "Amazon Aurora MySQL",
        "use_case": "Enterprise applications requiring high throughput",
        "max_db_size": "128 TB",
        "suitable_for_production": True,
        "license_cost": "No",
        "performance": "Very High",
        "ease_of_use": "High"
    },
    "aurora-postgresql": {
        "description": "Amazon Aurora PostgreSQL",
        "use_case": "Enterprise applications requiring high throughput and PostgreSQL compatibility",
        "max_db_size": "128 TB",
        "suitable_for_production": True,
        "license_cost": "No",
        "performance": "Very High",
        "ease_of_use": "Moderate"
    },
    "oracle-se": {
        "description": "Oracle Standard Edition",
        "use_case": "Small to medium-sized business applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes",
        "performance": "High",
        "ease_of_use": "Moderate"
    },
    "oracle-se1": {
        "description": "Oracle Standard Edition One",
        "use_case": "Small to medium-sized business applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes",
        "performance": "High",
        "ease_of_use": "Moderate"
    },
    "oracle-se2": {
        "description": "Oracle Standard Edition Two",
        "use_case": "Small to medium-sized business applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes",
        "performance": "High",
        "ease_of_use": "Moderate"
    },
    "oracle-ee": {
        "description": "Oracle Enterprise Edition",
        "use_case": "Mission-critical enterprise applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes (High)",
        "performance": "Very High",
        "ease_of_use": "Moderate"
    },
    "sqlserver-ex": {
        "description": "Microsoft SQL Server Express",
        "use_case": "Small applications, development and testing",
        "max_db_size": "10 GB",
        "suitable_for_production": False,
        "license_cost": "No",
        "performance": "Moderate",
        "ease_of_use": "High"
    },
    "sqlserver-web": {
        "description": "Microsoft SQL Server Web",
        "use_case": "Web applications and websites",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes (Low)",
        "performance": "Good",
        "ease_of_use": "High"
    },
    "sqlserver-se": {
        "description": "Microsoft SQL Server Standard",
        "use_case": "Departmental applications, medium-sized businesses",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes",
        "performance": "High",
        "ease_of_use": "High"
    },
    "sqlserver-ee": {
        "description": "Microsoft SQL Server Enterprise",
        "use_case": "Mission-critical enterprise applications",
        "max_db_size": "64 TB",
        "suitable_for_production": True,
        "license_cost": "Yes (High)",
        "performance": "Very High",
        "ease_of_use": "High"
    }
}

# Helper functions for parsing user requirements
def _extract_cpu_memory_requirements(description: str) -> Tuple[Optional[int], Optional[float]]:
    """Extract CPU cores and memory requirements from description."""
    cpu_cores = None
    memory_gb = None
    
    # Extract CPU cores
    cpu_patterns = [
        r'(\d+)\s*(?:cpu|core|vcpu|processor)s?',
        r'(\d+)\s*核(?:cpu|处理器)?',
        r'cpu\s*(?:core|processor)?s?\s*:\s*(\d+)',
        r'处理器\s*(?:核心)?数\s*[为是:：]\s*(\d+)'
    ]
    
    for pattern in cpu_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            cpu_cores = int(match.group(1))
            break
    
    # Extract memory
    memory_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g)\s*(?:ram|memory|内存)',
        r'(\d+(?:\.\d+)?)\s*(?:ram|memory|内存)\s*(?:gb|gib|g)',
        r'(?:ram|memory|内存)\s*:\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g)',
        r'内存\s*[为是:：]\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g)'
    ]
    
    for pattern in memory_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            memory_gb = float(match.group(1))
            break
    
    return cpu_cores, memory_gb

def _extract_storage_requirements(description: str) -> Tuple[Optional[int], Optional[str]]:
    """Extract storage size and type requirements from description."""
    storage_size = None
    storage_type = None
    
    # Extract storage size
    size_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:storage|disk|volume|存储|磁盘)',
        r'(?:storage|disk|volume|存储|磁盘)\s*(?:size|capacity|容量)?\s*[为是:：]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)',
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)'
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            size_value = float(match.group(1))
            size_unit = re.search(r'(tb|tib|t)', match.group(0), re.IGNORECASE)
            
            if size_unit:  # Convert TB to GB
                storage_size = int(size_value * 1024)
            else:
                storage_size = int(size_value)
            break
    
    # Extract storage type
    type_patterns = [
        r'(ssd|hdd|gp2|gp3|io1|io2|st1|sc1|standard)\s*(?:storage|disk|volume|存储|磁盘)',
        r'(?:storage|disk|volume|存储|磁盘)\s*(?:type|类型)?\s*[为是:：]?\s*(ssd|hdd|gp2|gp3|io1|io2|st1|sc1|standard)',
        r'(ssd|hdd|gp2|gp3|io1|io2|st1|sc1|standard)'
    ]
    
    for pattern in type_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            storage_type = match.group(1).lower()
            break
    
    # Map general types to specific EBS types
    if storage_type == "ssd":
        storage_type = "gp3"  # Default to gp3 for SSD
    elif storage_type == "hdd":
        storage_type = "st1"  # Default to st1 for HDD
    
    return storage_size, storage_type

def _extract_database_requirements(description: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract database engine and deployment option from description."""
    db_engine = None
    deployment_option = None
    
    # Extract database engine
    engine_patterns = [
        r'(mysql|postgresql|postgres|oracle|sqlserver|mariadb|aurora)\s*(?:database|db|数据库)',
        r'(?:database|db|数据库)\s*(?:engine|type|类型)?\s*[为是:：]?\s*(mysql|postgresql|postgres|oracle|sqlserver|mariadb|aurora)',
        r'(mysql|postgresql|postgres|oracle|sqlserver|mariadb|aurora)'
    ]
    
    for pattern in engine_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            db_engine = match.group(1).lower()
            if db_engine == "postgres":
                db_engine = "postgresql"
            break
    
    # Extract deployment option
    deployment_patterns = [
        r'(single[\s-]az|multi[\s-]az|高可用|高可靠性|多可用区)',
        r'(ha|high[\s-]availability)'
    ]
    
    for pattern in deployment_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            matched_text = match.group(1).lower()
            if any(term in matched_text for term in ["multi", "ha", "high", "高可用", "高可靠性", "多可用区"]):
                deployment_option = "multi-az"
            else:
                deployment_option = "single-az"
            break
    
    return db_engine, deployment_option

def _extract_cache_requirements(description: str) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """Extract cache engine, CPU cores and memory requirements from description."""
    cache_engine = None
    cpu_cores = None
    memory_gb = None
    
    # Extract cache engine
    engine_patterns = [
        r'(redis|memcached)\s*(?:cache|缓存)',
        r'(?:cache|缓存)\s*(?:engine|type|类型)?\s*[为是:：]?\s*(redis|memcached)',
        r'(redis|memcached)'
    ]
    
    for pattern in engine_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            cache_engine = match.group(1).lower()
            break
    
    # Extract CPU and memory using the same function as for EC2
    cpu_cores, memory_gb = _extract_cpu_memory_requirements(description)
    
    return cache_engine, cpu_cores, memory_gb

def _extract_s3_requirements(description: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """Extract S3 storage class, size and data transfer requirements from description."""
    storage_class = None
    storage_size = None
    data_transfer = None
    
    # Extract storage class
    class_patterns = [
        r'(standard|intelligent[\s-]tiering|standard[\s-]ia|onezone[\s-]ia|glacier|deep[\s-]archive)\s*(?:storage|class|存储)',
        r'(?:storage|class|存储)\s*(?:type|class|类型)?\s*[为是:：]?\s*(standard|intelligent[\s-]tiering|standard[\s-]ia|onezone[\s-]ia|glacier|deep[\s-]archive)',
        r'(standard|intelligent[\s-]tiering|standard[\s-]ia|onezone[\s-]ia|glacier|deep[\s-]archive)'
    ]
    
    for pattern in class_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            storage_class = match.group(1).lower().replace("-", "_").replace(" ", "_")
            break
    
    # Extract storage size
    size_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:storage|存储)',
        r'(?:storage|存储)\s*(?:size|capacity|容量)?\s*[为是:：]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)'
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            size_value = float(match.group(1))
            size_unit = re.search(r'(tb|tib|t)', match.group(0), re.IGNORECASE)
            
            if size_unit:  # Convert TB to GB
                storage_size = int(size_value * 1024)
            else:
                storage_size = int(size_value)
            break
    
    # Extract data transfer
    transfer_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:transfer|bandwidth|带宽|传输)',
        r'(?:transfer|bandwidth|带宽|传输)\s*[为是:：]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)'
    ]
    
    for pattern in transfer_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            transfer_value = float(match.group(1))
            transfer_unit = re.search(r'(tb|tib|t)', match.group(0), re.IGNORECASE)
            
            if transfer_unit:  # Convert TB to GB
                data_transfer = int(transfer_value * 1024)
            else:
                data_transfer = int(transfer_value)
            break
    
    return storage_class, storage_size, data_transfer

def _extract_loadbalancer_requirements(description: str) -> Tuple[Optional[str], Optional[int]]:
    """Extract load balancer type and data processed requirements from description."""
    lb_type = None
    data_processed = None
    
    # Extract load balancer type
    type_patterns = [
        r'(application|network|classic|alb|nlb|clb)\s*(?:load[\s-]balancer|负载均衡器)',
        r'(?:load[\s-]balancer|负载均衡器)\s*(?:type|类型)?\s*[为是:：]?\s*(application|network|classic|alb|nlb|clb)',
        r'(application|network|classic|alb|nlb|clb)'
    ]
    
    for pattern in type_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            lb_type_match = match.group(1).lower()
            if lb_type_match in ["application", "alb"]:
                lb_type = "alb"
            elif lb_type_match in ["network", "nlb"]:
                lb_type = "nlb"
            elif lb_type_match in ["classic", "clb"]:
                lb_type = "clb"
            break
    
    # Extract data processed
    processed_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)\s*(?:data[\s-]processed|processed|处理数据)',
        r'(?:data[\s-]processed|processed|处理数据)\s*[为是:：]?\s*(\d+(?:\.\d+)?)\s*(?:gb|gib|g|tb|tib|t)'
    ]
    
    for pattern in processed_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            processed_value = float(match.group(1))
            processed_unit = re.search(r'(tb|tib|t)', match.group(0), re.IGNORECASE)
            
            if processed_unit:  # Convert TB to GB
                data_processed = int(processed_value * 1024)
            else:
                data_processed = int(processed_value)
            break
    
    return lb_type, data_processed

def _extract_region_and_environment(description: str) -> Tuple[Optional[str], bool]:
    """Extract AWS region and environment type from description."""
    region = None
    is_production = True  # Default to production environment
    
    # Extract region
    region_patterns = [
        r'(?:region|地区|区域)\s*[为是:：]?\s*(us-east-1|us-east-2|us-west-1|us-west-2|eu-west-1|eu-west-2|eu-west-3|eu-central-1|ap-northeast-1|ap-northeast-2|ap-northeast-3|ap-southeast-1|ap-southeast-2|ap-south-1|sa-east-1|ca-central-1|cn-north-1|cn-northwest-1)',
        r'(us-east-1|us-east-2|us-west-1|us-west-2|eu-west-1|eu-west-2|eu-west-3|eu-central-1|ap-northeast-1|ap-northeast-2|ap-northeast-3|ap-southeast-1|ap-southeast-2|ap-south-1|sa-east-1|ca-central-1|cn-north-1|cn-northwest-1)',
        r'(北京|宁夏|弗吉尼亚|俄亥俄|加利福尼亚|俄勒冈|爱尔兰|伦敦|巴黎|法兰克福|东京|首尔|大阪|新加坡|悉尼|孟买|圣保罗|加拿大|中国)'
    ]
    
    for pattern in region_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            region_match = match.group(1).lower()
            
            # Map region names to region codes
            region_mapping = {
                "北京": "cn-north-1",
                "宁夏": "cn-northwest-1",
                "弗吉尼亚": "us-east-1",
                "俄亥俄": "us-east-2",
                "加利福尼亚": "us-west-1",
                "俄勒冈": "us-west-2",
                "爱尔兰": "eu-west-1",
                "伦敦": "eu-west-2",
                "巴黎": "eu-west-3",
                "法兰克福": "eu-central-1",
                "东京": "ap-northeast-1",
                "首尔": "ap-northeast-2",
                "大阪": "ap-northeast-3",
                "新加坡": "ap-southeast-1",
                "悉尼": "ap-southeast-2",
                "孟买": "ap-south-1",
                "圣保罗": "sa-east-1",
                "加拿大": "ca-central-1",
                "中国": "cn-north-1"
            }
            
            region = region_mapping.get(region_match, region_match)
            break
    
    # Extract environment type
    env_patterns = [
        r'(production|prod|生产环境|正式环境)',
        r'(development|dev|测试环境|开发环境|非生产环境)'
    ]
    
    for pattern in env_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            matched_text = match.group(1).lower()
            if any(term in matched_text for term in ["development", "dev", "测试", "开发", "非生产"]):
                is_production = False
            break
    
    return region, is_production

@tool
def recommend_ec2_instance(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Recommend EC2 instance types based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with recommended EC2 instance types and rationale
    """
    try:
        # Extract CPU and memory requirements from description
        cpu_cores, memory_gb = _extract_cpu_memory_requirements(description)
        
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Get available instance types in the region
        instance_types_response = json.loads(get_ec2_instance_types(region))
        
        if "error" in instance_types_response:
            return json.dumps({"error": instance_types_response["error"]})
        
        available_instances = instance_types_response.get("instance_types", [])
        
        # Filter instances based on requirements
        filtered_instances = []
        for instance in available_instances:
            # Skip t-series instances for production unless explicitly mentioned in description
            instance_family = instance.get("instance_type", "")[0]
            if is_production and instance_family == "t" and "t series" not in description.lower():
                continue
            
            # Filter by CPU if specified
            if cpu_cores is not None and instance.get("vcpu") < cpu_cores:
                continue
            
            # Filter by memory if specified
            if memory_gb is not None and instance.get("memory_gib") < memory_gb:
                continue
            
            filtered_instances.append(instance)
        
        # Sort instances by price (if available) or by size
        sorted_instances = sorted(
            filtered_instances,
            key=lambda x: (x.get("vcpu", 0), x.get("memory_gib", 0))
        )
        
        # Select top recommendations
        recommendations = []
        families_included = set()
        
        # First, add instances that closely match the requirements
        close_matches = []
        if cpu_cores is not None and memory_gb is not None:
            for instance in sorted_instances:
                # Look for instances with CPU and memory close to requirements
                cpu_ratio = instance.get("vcpu", 0) / cpu_cores
                memory_ratio = instance.get("memory_gib", 0) / memory_gb
                
                # Instance is a close match if CPU and memory are within 50% of requirements
                if 0.9 <= cpu_ratio <= 1.5 and 0.9 <= memory_ratio <= 1.5:
                    close_matches.append(instance)
        
        # Add close matches first
        for instance in close_matches[:3]:
            instance_family = instance.get("instance_type", "")[0]
            recommendations.append({
                "instance_type": instance.get("instance_type"),
                "vcpu": instance.get("vcpu"),
                "memory_gib": instance.get("memory_gib"),
                "family_description": EC2_INSTANCE_FAMILIES.get(instance_family, {}).get("description", ""),
                "use_case": EC2_INSTANCE_FAMILIES.get(instance_family, {}).get("use_case", ""),
                "rationale": "Closely matches CPU and memory requirements"
            })
            families_included.add(instance_family)
        
        # Add instances from different families for variety
        for instance in sorted_instances:
            instance_family = instance.get("instance_type", "")[0]
            
            # Skip if we already have enough recommendations or this family is already included
            if len(recommendations) >= 5 or instance_family in families_included:
                continue
            
            recommendations.append({
                "instance_type": instance.get("instance_type"),
                "vcpu": instance.get("vcpu"),
                "memory_gib": instance.get("memory_gib"),
                "family_description": EC2_INSTANCE_FAMILIES.get(instance_family, {}).get("description", ""),
                "use_case": EC2_INSTANCE_FAMILIES.get(instance_family, {}).get("use_case", ""),
                "rationale": "Alternative instance family that meets requirements"
            })
            families_included.add(instance_family)
        
        # Create the result
        result = {
            "requirements": {
                "cpu_cores": cpu_cores,
                "memory_gb": memory_gb,
                "region": region,
                "is_production": is_production
            },
            "recommendations": recommendations[:5],  # Limit to top 5 recommendations
            "note": "Prices shown are approximate and may vary based on specific terms and conditions."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_ec2_pricing(rec["instance_type"], region))
                if "on_demand_pricing" in pricing_response and pricing_response["on_demand_pricing"]:
                    rec["price_per_hour"] = pricing_response["on_demand_pricing"][0].get("price_per_hour")
                    rec["estimated_monthly_cost"] = rec["price_per_hour"] * 24 * 30  # Approximate month as 30 days
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['instance_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending EC2 instance: {str(e)}")
        return json.dumps({"error": f"Error recommending EC2 instance: {str(e)}"})

@tool
def recommend_ebs_volume(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Recommend EBS volume types based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with recommended EBS volume types and rationale
    """
    try:
        # Extract storage requirements from description
        storage_size, storage_type = _extract_storage_requirements(description)
        
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Set default storage size if not specified
        if storage_size is None:
            storage_size = 100  # Default to 100 GB
        
        # Create recommendations
        recommendations = []
        
        # If storage type is explicitly specified, make it the primary recommendation
        if storage_type and storage_type in EBS_VOLUME_TYPES:
            recommendations.append({
                "volume_type": storage_type,
                "size_gb": storage_size,
                "description": EBS_VOLUME_TYPES[storage_type]["description"],
                "use_case": EBS_VOLUME_TYPES[storage_type]["use_case"],
                "baseline_iops": EBS_VOLUME_TYPES[storage_type]["baseline_iops"],
                "max_iops": EBS_VOLUME_TYPES[storage_type]["max_iops"],
                "rationale": "Matches explicitly requested volume type"
            })
        
        # Add gp3 as primary or secondary recommendation (it's the most versatile and cost-effective)
        if not storage_type or storage_type != "gp3":
            recommendations.append({
                "volume_type": "gp3",
                "size_gb": storage_size,
                "description": EBS_VOLUME_TYPES["gp3"]["description"],
                "use_case": EBS_VOLUME_TYPES["gp3"]["use_case"],
                "baseline_iops": EBS_VOLUME_TYPES["gp3"]["baseline_iops"],
                "max_iops": EBS_VOLUME_TYPES["gp3"]["max_iops"],
                "rationale": "Best balance of performance and cost for most workloads"
            })
        
        # For production environments with large storage requirements, suggest io2
        if is_production and storage_size >= 500 and (not storage_type or storage_type != "io2"):
            recommendations.append({
                "volume_type": "io2",
                "size_gb": storage_size,
                "description": EBS_VOLUME_TYPES["io2"]["description"],
                "use_case": EBS_VOLUME_TYPES["io2"]["use_case"],
                "baseline_iops": EBS_VOLUME_TYPES["io2"]["baseline_iops"],
                "max_iops": EBS_VOLUME_TYPES["io2"]["max_iops"],
                "rationale": "High performance option for production workloads with large storage requirements"
            })
        
        # For large storage with lower performance requirements, suggest st1
        if storage_size >= 1000 and (not storage_type or storage_type != "st1"):
            recommendations.append({
                "volume_type": "st1",
                "size_gb": storage_size,
                "description": EBS_VOLUME_TYPES["st1"]["description"],
                "use_case": EBS_VOLUME_TYPES["st1"]["use_case"],
                "baseline_iops": EBS_VOLUME_TYPES["st1"]["baseline_iops"],
                "max_iops": EBS_VOLUME_TYPES["st1"]["max_iops"],
                "rationale": "Cost-effective option for large storage with throughput-intensive workloads"
            })
        
        # For non-production or cost-sensitive scenarios, suggest sc1
        if (not is_production or "cost" in description.lower()) and storage_size >= 500 and (not storage_type or storage_type != "sc1"):
            recommendations.append({
                "volume_type": "sc1",
                "size_gb": storage_size,
                "description": EBS_VOLUME_TYPES["sc1"]["description"],
                "use_case": EBS_VOLUME_TYPES["sc1"]["use_case"],
                "baseline_iops": EBS_VOLUME_TYPES["sc1"]["baseline_iops"],
                "max_iops": EBS_VOLUME_TYPES["sc1"]["max_iops"],
                "rationale": "Lowest cost option for infrequently accessed data"
            })
        
        # Create the result
        result = {
            "requirements": {
                "storage_size_gb": storage_size,
                "requested_volume_type": storage_type,
                "region": region,
                "is_production": is_production
            },
            "recommendations": recommendations[:3],  # Limit to top 3 recommendations
            "note": "IOPS and throughput can be customized for gp3, io1, and io2 volumes."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_ebs_pricing(rec["volume_type"], region, rec["size_gb"]))
                if "estimated_monthly_cost" in pricing_response:
                    rec["estimated_monthly_cost"] = pricing_response["estimated_monthly_cost"]
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['volume_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending EBS volume: {str(e)}")
        return json.dumps({"error": f"Error recommending EBS volume: {str(e)}"})

@tool
def recommend_s3_storage(
    description: str,
    region: str = "us-east-1"
) -> str:
    """
    Recommend S3 storage class based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
    
    Returns:
        JSON string with recommended S3 storage classes and rationale
    """
    try:
        # Extract S3 requirements from description
        storage_class, storage_size, data_transfer = _extract_s3_requirements(description)
        
        # Extract region information if not explicitly provided
        extracted_region, _ = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        
        # Set default storage size if not specified
        if storage_size is None:
            storage_size = 100  # Default to 100 GB
        
        # Set default data transfer if not specified
        if data_transfer is None:
            data_transfer = 50  # Default to 50 GB
        
        # Create recommendations
        recommendations = []
        
        # If storage class is explicitly specified, make it the primary recommendation
        if storage_class and storage_class in S3_STORAGE_CLASSES:
            recommendations.append({
                "storage_class": storage_class,
                "description": S3_STORAGE_CLASSES[storage_class]["description"],
                "use_case": S3_STORAGE_CLASSES[storage_class]["use_case"],
                "availability": S3_STORAGE_CLASSES[storage_class]["availability"],
                "min_storage_duration": S3_STORAGE_CLASSES[storage_class]["min_storage_duration"],
                "rationale": "Matches explicitly requested storage class"
            })
        
        # Add Standard as primary or secondary recommendation for frequently accessed data
        if not storage_class or storage_class != "standard":
            if "frequent" in description.lower() or "high access" in description.lower():
                recommendations.append({
                    "storage_class": "standard",
                    "description": S3_STORAGE_CLASSES["standard"]["description"],
                    "use_case": S3_STORAGE_CLASSES["standard"]["use_case"],
                    "availability": S3_STORAGE_CLASSES["standard"]["availability"],
                    "min_storage_duration": S3_STORAGE_CLASSES["standard"]["min_storage_duration"],
                    "rationale": "Best for frequently accessed data with highest availability"
                })
        
        # Add Intelligent-Tiering for unknown access patterns
        if not storage_class or storage_class != "intelligent_tiering":
            if "unknown" in description.lower() or "varying" in description.lower() or "changing" in description.lower():
                recommendations.append({
                    "storage_class": "intelligent_tiering",
                    "description": S3_STORAGE_CLASSES["intelligent_tiering"]["description"],
                    "use_case": S3_STORAGE_CLASSES["intelligent_tiering"]["use_case"],
                    "availability": S3_STORAGE_CLASSES["intelligent_tiering"]["availability"],
                    "min_storage_duration": S3_STORAGE_CLASSES["intelligent_tiering"]["min_storage_duration"],
                    "rationale": "Automatically optimizes costs for data with unknown or changing access patterns"
                })
            else:
                # Add as a general recommendation if not specifically mentioned
                recommendations.append({
                    "storage_class": "intelligent_tiering",
                    "description": S3_STORAGE_CLASSES["intelligent_tiering"]["description"],
                    "use_case": S3_STORAGE_CLASSES["intelligent_tiering"]["use_case"],
                    "availability": S3_STORAGE_CLASSES["intelligent_tiering"]["availability"],
                    "min_storage_duration": S3_STORAGE_CLASSES["intelligent_tiering"]["min_storage_duration"],
                    "rationale": "Good general-purpose option that automatically optimizes costs"
                })
        
        # Add Standard-IA for infrequently accessed data
        if not storage_class or storage_class != "standard_ia":
            if "infrequent" in description.lower() or "backup" in description.lower():
                recommendations.append({
                    "storage_class": "standard_ia",
                    "description": S3_STORAGE_CLASSES["standard_ia"]["description"],
                    "use_case": S3_STORAGE_CLASSES["standard_ia"]["use_case"],
                    "availability": S3_STORAGE_CLASSES["standard_ia"]["availability"],
                    "min_storage_duration": S3_STORAGE_CLASSES["standard_ia"]["min_storage_duration"],
                    "rationale": "Cost-effective for infrequently accessed data with high durability"
                })
        
        # Add Glacier for archival
        if not storage_class or storage_class != "glacier":
            if "archive" in description.lower() or "backup" in description.lower() or "long-term" in description.lower():
                recommendations.append({
                    "storage_class": "glacier",
                    "description": S3_STORAGE_CLASSES["glacier"]["description"],
                    "use_case": S3_STORAGE_CLASSES["glacier"]["use_case"],
                    "availability": S3_STORAGE_CLASSES["glacier"]["availability"],
                    "min_storage_duration": S3_STORAGE_CLASSES["glacier"]["min_storage_duration"],
                    "rationale": "Low-cost archival storage with retrieval times of minutes to hours"
                })
        
        # Create the result
        result = {
            "requirements": {
                "storage_size_gb": storage_size,
                "data_transfer_gb": data_transfer,
                "requested_storage_class": storage_class,
                "region": region
            },
            "recommendations": recommendations[:3],  # Limit to top 3 recommendations
            "note": "S3 pricing varies based on storage amount, data transfer, and request patterns."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_s3_pricing(
                    rec["storage_class"], region, storage_size, data_transfer
                ))
                if "estimated_monthly_storage_cost" in pricing_response:
                    rec["estimated_monthly_storage_cost"] = pricing_response["estimated_monthly_storage_cost"]
                if "estimated_data_transfer_cost" in pricing_response:
                    rec["estimated_data_transfer_cost"] = pricing_response["estimated_data_transfer_cost"]
                    rec["estimated_total_cost"] = (
                        pricing_response["estimated_monthly_storage_cost"] + 
                        pricing_response["estimated_data_transfer_cost"]
                    )
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['storage_class']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending S3 storage: {str(e)}")
        return json.dumps({"error": f"Error recommending S3 storage: {str(e)}"})

@tool
def recommend_rds_instance(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Recommend RDS instance types based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with recommended RDS instance types and rationale
    """
    try:
        # Extract CPU and memory requirements from description
        cpu_cores, memory_gb = _extract_cpu_memory_requirements(description)
        
        # Extract database requirements from description
        db_engine, deployment_option = _extract_database_requirements(description)
        
        # Extract storage requirements from description
        storage_size, _ = _extract_storage_requirements(description)
        
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Set default values if not specified
        if db_engine is None:
            db_engine = "mysql"  # Default to MySQL
        
        if deployment_option is None:
            deployment_option = "multi-az" if is_production else "single-az"
        
        if storage_size is None:
            storage_size = 100  # Default to 100 GB
        
        # Map DB engine to specific version if needed
        if db_engine == "oracle":
            db_engine = "oracle-se2"  # Default to Standard Edition 2
        elif db_engine == "sqlserver":
            db_engine = "sqlserver-se"  # Default to Standard Edition
        
        # Define common RDS instance types to recommend
        instance_types = [
            # General purpose
            "db.t3.micro", "db.t3.small", "db.t3.medium", "db.t3.large",
            "db.m5.large", "db.m5.xlarge", "db.m5.2xlarge", "db.m5.4xlarge",
            # Memory optimized
            "db.r5.large", "db.r5.xlarge", "db.r5.2xlarge", "db.r5.4xlarge"
        ]
        
        # Filter instance types based on production requirement
        if is_production:
            # Remove t-series instances for production unless explicitly mentioned
            if "t series" not in description.lower():
                instance_types = [it for it in instance_types if not it.startswith("db.t")]
        
        # Create recommendations
        recommendations = []
        
        # Map CPU/memory requirements to instance types
        if cpu_cores is not None and memory_gb is not None:
            # Define instance type characteristics (approximate values)
            instance_specs = {
                "db.t3.micro": {"vcpu": 2, "memory_gb": 1},
                "db.t3.small": {"vcpu": 2, "memory_gb": 2},
                "db.t3.medium": {"vcpu": 2, "memory_gb": 4},
                "db.t3.large": {"vcpu": 2, "memory_gb": 8},
                "db.m5.large": {"vcpu": 2, "memory_gb": 8},
                "db.m5.xlarge": {"vcpu": 4, "memory_gb": 16},
                "db.m5.2xlarge": {"vcpu": 8, "memory_gb": 32},
                "db.m5.4xlarge": {"vcpu": 16, "memory_gb": 64},
                "db.r5.large": {"vcpu": 2, "memory_gb": 16},
                "db.r5.xlarge": {"vcpu": 4, "memory_gb": 32},
                "db.r5.2xlarge": {"vcpu": 8, "memory_gb": 64},
                "db.r5.4xlarge": {"vcpu": 16, "memory_gb": 128}
            }
            
            # Find instances that meet or exceed requirements
            suitable_instances = []
            for instance_type, specs in instance_specs.items():
                if specs["vcpu"] >= cpu_cores and specs["memory_gb"] >= memory_gb:
                    suitable_instances.append((instance_type, specs))
            
            # Sort by capacity (smallest that meets requirements first)
            suitable_instances.sort(key=lambda x: (x[1]["vcpu"], x[1]["memory_gb"]))
            
            # Add top matches to recommendations
            for instance_type, specs in suitable_instances[:3]:
                instance_family = instance_type.split(".")[1][0]
                family_type = "General Purpose" if instance_family == "m" else "Memory Optimized" if instance_family == "r" else "Burstable"
                
                recommendations.append({
                    "instance_type": instance_type,
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": specs["vcpu"],
                    "memory_gb": specs["memory_gb"],
                    "family_type": family_type,
                    "rationale": f"Meets CPU ({cpu_cores} cores) and memory ({memory_gb} GB) requirements"
                })
        else:
            # If no specific CPU/memory requirements, provide general recommendations
            if is_production:
                # For production, recommend m5.large, r5.large, and m5.xlarge
                recommendations.append({
                    "instance_type": "db.m5.large",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 2,
                    "memory_gb": 8,
                    "family_type": "General Purpose",
                    "rationale": "Good starting point for production workloads with balanced CPU and memory"
                })
                
                recommendations.append({
                    "instance_type": "db.r5.large",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 2,
                    "memory_gb": 16,
                    "family_type": "Memory Optimized",
                    "rationale": "Good for production workloads with higher memory requirements"
                })
                
                recommendations.append({
                    "instance_type": "db.m5.xlarge",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 4,
                    "memory_gb": 16,
                    "family_type": "General Purpose",
                    "rationale": "Higher capacity option for demanding production workloads"
                })
            else:
                # For non-production, recommend t3.small, t3.medium, and m5.large
                recommendations.append({
                    "instance_type": "db.t3.small",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 2,
                    "memory_gb": 2,
                    "family_type": "Burstable",
                    "rationale": "Cost-effective option for development and testing"
                })
                
                recommendations.append({
                    "instance_type": "db.t3.medium",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 2,
                    "memory_gb": 4,
                    "family_type": "Burstable",
                    "rationale": "Balanced option for development and testing with moderate workloads"
                })
                
                recommendations.append({
                    "instance_type": "db.m5.large",
                    "engine": db_engine,
                    "deployment_option": deployment_option,
                    "storage_gb": storage_size,
                    "vcpu": 2,
                    "memory_gb": 8,
                    "family_type": "General Purpose",
                    "rationale": "Higher capacity option for demanding non-production workloads"
                })
        
        # Create the result
        result = {
            "requirements": {
                "cpu_cores": cpu_cores,
                "memory_gb": memory_gb,
                "engine": db_engine,
                "deployment_option": deployment_option,
                "storage_gb": storage_size,
                "region": region,
                "is_production": is_production
            },
            "engine_info": {
                "name": DB_ENGINE_CHARACTERISTICS.get(db_engine, {}).get("description", db_engine),
                "use_case": DB_ENGINE_CHARACTERISTICS.get(db_engine, {}).get("use_case", ""),
                "license_cost": DB_ENGINE_CHARACTERISTICS.get(db_engine, {}).get("license_cost", "")
            },
            "recommendations": recommendations,
            "note": "RDS pricing includes instance hours, storage, I/O operations, and backup storage."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_rds_pricing(
                    rec["instance_type"], rec["engine"], region, rec["deployment_option"]
                ))
                if "on_demand_pricing" in pricing_response and pricing_response["on_demand_pricing"]:
                    rec["price_per_hour"] = pricing_response["on_demand_pricing"][0].get("price_per_hour")
                    rec["estimated_monthly_instance_cost"] = rec["price_per_hour"] * 24 * 30  # Approximate month as 30 days
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['instance_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending RDS instance: {str(e)}")
        return json.dumps({"error": f"Error recommending RDS instance: {str(e)}"})

@tool
def recommend_elasticache_node(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Recommend ElastiCache node types based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with recommended ElastiCache node types and rationale
    """
    try:
        # Extract cache requirements from description
        cache_engine, cpu_cores, memory_gb = _extract_cache_requirements(description)
        
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Set default values if not specified
        if cache_engine is None:
            cache_engine = "redis"  # Default to Redis
        
        # Define common ElastiCache node types to recommend
        node_types = [
            # T-series (burstable)
            "cache.t3.micro", "cache.t3.small", "cache.t3.medium",
            # M-series (general purpose)
            "cache.m5.large", "cache.m5.xlarge", "cache.m5.2xlarge",
            # R-series (memory optimized)
            "cache.r5.large", "cache.r5.xlarge", "cache.r5.2xlarge"
        ]
        
        # Filter node types based on production requirement
        if is_production:
            # Remove t-series nodes for production unless explicitly mentioned
            if "t series" not in description.lower():
                node_types = [nt for nt in node_types if not nt.startswith("cache.t")]
        
        # Create recommendations
        recommendations = []
        
        # Map CPU/memory requirements to node types
        if memory_gb is not None:
            # Define node type characteristics (approximate values)
            node_specs = {
                "cache.t3.micro": {"vcpu": 2, "memory_gb": 0.5},
                "cache.t3.small": {"vcpu": 2, "memory_gb": 1.5},
                "cache.t3.medium": {"vcpu": 2, "memory_gb": 3.2},
                "cache.m5.large": {"vcpu": 2, "memory_gb": 6.4},
                "cache.m5.xlarge": {"vcpu": 4, "memory_gb": 12.9},
                "cache.m5.2xlarge": {"vcpu": 8, "memory_gb": 25.9},
                "cache.r5.large": {"vcpu": 2, "memory_gb": 13.1},
                "cache.r5.xlarge": {"vcpu": 4, "memory_gb": 26.3},
                "cache.r5.2xlarge": {"vcpu": 8, "memory_gb": 52.8}
            }
            
            # Find nodes that meet or exceed memory requirements
            suitable_nodes = []
            for node_type, specs in node_specs.items():
                if specs["memory_gb"] >= memory_gb:
                    suitable_nodes.append((node_type, specs))
            
            # Sort by memory (smallest that meets requirements first)
            suitable_nodes.sort(key=lambda x: x[1]["memory_gb"])
            
            # Add top matches to recommendations
            for node_type, specs in suitable_nodes[:3]:
                node_family = node_type.split(".")[1][0]
                family_type = "General Purpose" if node_family == "m" else "Memory Optimized" if node_family == "r" else "Burstable"
                
                recommendations.append({
                    "node_type": node_type,
                    "engine": cache_engine,
                    "vcpu": specs["vcpu"],
                    "memory_gb": specs["memory_gb"],
                    "family_type": family_type,
                    "rationale": f"Meets memory requirements ({memory_gb} GB)"
                })
        else:
            # If no specific memory requirements, provide general recommendations
            if is_production:
                # For production, recommend m5.large, r5.large, and m5.xlarge
                recommendations.append({
                    "node_type": "cache.m5.large",
                    "engine": cache_engine,
                    "vcpu": 2,
                    "memory_gb": 6.4,
                    "family_type": "General Purpose",
                    "rationale": "Good starting point for production workloads with balanced performance"
                })
                
                recommendations.append({
                    "node_type": "cache.r5.large",
                    "engine": cache_engine,
                    "vcpu": 2,
                    "memory_gb": 13.1,
                    "family_type": "Memory Optimized",
                    "rationale": "Good for production workloads with higher memory requirements"
                })
                
                recommendations.append({
                    "node_type": "cache.m5.xlarge",
                    "engine": cache_engine,
                    "vcpu": 4,
                    "memory_gb": 12.9,
                    "family_type": "General Purpose",
                    "rationale": "Higher capacity option for demanding production workloads"
                })
            else:
                # For non-production, recommend t3.small, t3.medium, and m5.large
                recommendations.append({
                    "node_type": "cache.t3.small",
                    "engine": cache_engine,
                    "vcpu": 2,
                    "memory_gb": 1.5,
                    "family_type": "Burstable",
                    "rationale": "Cost-effective option for development and testing"
                })
                
                recommendations.append({
                    "node_type": "cache.t3.medium",
                    "engine": cache_engine,
                    "vcpu": 2,
                    "memory_gb": 3.2,
                    "family_type": "Burstable",
                    "rationale": "Balanced option for development and testing with moderate workloads"
                })
                
                recommendations.append({
                    "node_type": "cache.m5.large",
                    "engine": cache_engine,
                    "vcpu": 2,
                    "memory_gb": 6.4,
                    "family_type": "General Purpose",
                    "rationale": "Higher capacity option for demanding non-production workloads"
                })
        
        # Create the result
        result = {
            "requirements": {
                "memory_gb": memory_gb,
                "engine": cache_engine,
                "region": region,
                "is_production": is_production
            },
            "engine_info": {
                "name": cache_engine.capitalize(),
                "use_case": "In-memory data store and cache" if cache_engine == "redis" else "Distributed memory caching system"
            },
            "recommendations": recommendations,
            "note": "ElastiCache pricing is based on node hours, and varies by node type and region."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_elasticache_pricing(
                    rec["node_type"], rec["engine"], region
                ))
                if "on_demand_pricing" in pricing_response and pricing_response["on_demand_pricing"]:
                    rec["price_per_hour"] = pricing_response["on_demand_pricing"][0].get("price_per_hour")
                    rec["estimated_monthly_cost"] = rec["price_per_hour"] * 24 * 30  # Approximate month as 30 days
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['node_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending ElastiCache node: {str(e)}")
        return json.dumps({"error": f"Error recommending ElastiCache node: {str(e)}"})

@tool
def recommend_opensearch_domain(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Recommend OpenSearch domain configuration based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with recommended OpenSearch domain configuration and rationale
    """
    try:
        # Extract CPU and memory requirements from description
        cpu_cores, memory_gb = _extract_cpu_memory_requirements(description)
        
        # Extract storage requirements from description
        storage_size, _ = _extract_storage_requirements(description)
        
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Set default values if not specified
        if storage_size is None:
            storage_size = 100  # Default to 100 GB
        
        # Define common OpenSearch instance types to recommend
        instance_types = [
            # T-series (burstable)
            "t3.small.search", "t3.medium.search",
            # M-series (general purpose)
            "m5.large.search", "m5.xlarge.search", "m5.2xlarge.search",
            # R-series (memory optimized)
            "r5.large.search", "r5.xlarge.search", "r5.2xlarge.search",
            # C-series (compute optimized)
            "c5.large.search", "c5.xlarge.search", "c5.2xlarge.search"
        ]
        
        # Filter instance types based on production requirement
        if is_production:
            # Remove t-series instances for production unless explicitly mentioned
            if "t series" not in description.lower():
                instance_types = [it for it in instance_types if not it.startswith("t")]
        
        # Create recommendations
        recommendations = []
        
        # Define instance type characteristics (approximate values)
        instance_specs = {
            "t3.small.search": {"vcpu": 2, "memory_gb": 2, "family": "Burstable"},
            "t3.medium.search": {"vcpu": 2, "memory_gb": 4, "family": "Burstable"},
            "m5.large.search": {"vcpu": 2, "memory_gb": 8, "family": "General Purpose"},
            "m5.xlarge.search": {"vcpu": 4, "memory_gb": 16, "family": "General Purpose"},
            "m5.2xlarge.search": {"vcpu": 8, "memory_gb": 32, "family": "General Purpose"},
            "r5.large.search": {"vcpu": 2, "memory_gb": 16, "family": "Memory Optimized"},
            "r5.xlarge.search": {"vcpu": 4, "memory_gb": 32, "family": "Memory Optimized"},
            "r5.2xlarge.search": {"vcpu": 8, "memory_gb": 64, "family": "Memory Optimized"},
            "c5.large.search": {"vcpu": 2, "memory_gb": 4, "family": "Compute Optimized"},
            "c5.xlarge.search": {"vcpu": 4, "memory_gb": 8, "family": "Compute Optimized"},
            "c5.2xlarge.search": {"vcpu": 8, "memory_gb": 16, "family": "Compute Optimized"}
        }
        
        # Determine use case based on description
        use_case = "general"
        if any(term in description.lower() for term in ["log", "logs", "logging", "日志"]):
            use_case = "logging"
        elif any(term in description.lower() for term in ["search", "searching", "搜索"]):
            use_case = "search"
        elif any(term in description.lower() for term in ["analytic", "analytics", "分析"]):
            use_case = "analytics"
        
        # Select appropriate instance types based on use case and requirements
        suitable_instances = []
        
        if cpu_cores is not None and memory_gb is not None:
            # Filter by CPU and memory requirements
            for instance_type, specs in instance_specs.items():
                if specs["vcpu"] >= cpu_cores and specs["memory_gb"] >= memory_gb:
                    suitable_instances.append((instance_type, specs))
            
            # Sort by capacity (smallest that meets requirements first)
            suitable_instances.sort(key=lambda x: (x[1]["vcpu"], x[1]["memory_gb"]))
        else:
            # If no specific requirements, select based on use case
            if use_case == "logging":
                # Logging typically benefits from compute-optimized instances
                suitable_instances = [(it, instance_specs[it]) for it in instance_types if it.startswith("c5")]
            elif use_case == "search":
                # Search typically benefits from memory-optimized instances
                suitable_instances = [(it, instance_specs[it]) for it in instance_types if it.startswith("r5")]
            elif use_case == "analytics":
                # Analytics can benefit from both compute and memory
                suitable_instances = [(it, instance_specs[it]) for it in instance_types if it.startswith("m5")]
            else:
                # General purpose use case
                suitable_instances = [(it, instance_specs[it]) for it in instance_types if it.startswith("m5")]
            
            # If in development, add t-series instances
            if not is_production:
                suitable_instances.extend([(it, instance_specs[it]) for it in instance_types if it.startswith("t3")])
            
            # Sort by size
            suitable_instances.sort(key=lambda x: (x[1]["vcpu"], x[1]["memory_gb"]))
        
        # Generate node count recommendation based on storage size and production status
        if is_production:
            # For production, recommend at least 3 nodes for high availability
            node_count = max(3, (storage_size // 100) + 1)  # 1 node per 100GB, minimum 3
        else:
            # For development, can use fewer nodes
            node_count = max(1, (storage_size // 200) + 1)  # 1 node per 200GB, minimum 1
        
        # Add top matches to recommendations
        for instance_type, specs in suitable_instances[:3]:
            recommendations.append({
                "instance_type": instance_type,
                "node_count": node_count,
                "storage_gb": storage_size,
                "vcpu_per_node": specs["vcpu"],
                "memory_gb_per_node": specs["memory_gb"],
                "family_type": specs["family"],
                "rationale": f"Optimized for {use_case} workloads"
            })
        
        # Create the result
        result = {
            "requirements": {
                "cpu_cores": cpu_cores,
                "memory_gb": memory_gb,
                "storage_gb": storage_size,
                "region": region,
                "is_production": is_production,
                "detected_use_case": use_case
            },
            "recommendations": recommendations,
            "note": "OpenSearch pricing includes instance hours, storage, and data transfer. For production environments, at least 3 nodes are recommended for high availability."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_opensearch_pricing(
                    rec["instance_type"], region, rec["storage_gb"]
                ))
                
                if "instance_pricing" in pricing_response and pricing_response["instance_pricing"]:
                    # Find hourly price
                    instance_price = next(
                        (p["price"] for p in pricing_response["instance_pricing"] if "Hrs" in p["unit"]),
                        0
                    )
                    
                    rec["price_per_hour_per_node"] = instance_price
                    rec["estimated_monthly_instance_cost"] = instance_price * 24 * 30 * rec["node_count"]
                
                if "estimated_monthly_storage_cost" in pricing_response:
                    rec["estimated_monthly_storage_cost"] = pricing_response["estimated_monthly_storage_cost"] * rec["node_count"]
                    rec["estimated_total_monthly_cost"] = (
                        rec["estimated_monthly_instance_cost"] + rec["estimated_monthly_storage_cost"]
                    )
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['instance_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending OpenSearch domain: {str(e)}")
        return json.dumps({"error": f"Error recommending OpenSearch domain: {str(e)}"})

@tool
def recommend_loadbalancer(
    description: str,
    region: str = "us-east-1"
) -> str:
    """
    Recommend load balancer type based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
    
    Returns:
        JSON string with recommended load balancer types and rationale
    """
    try:
        # Extract load balancer requirements from description
        lb_type, data_processed = _extract_loadbalancer_requirements(description)
        
        # Extract region information if not explicitly provided
        extracted_region, _ = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        
        # Set default data processed if not specified
        if data_processed is None:
            data_processed = 500  # Default to 500 GB
        
        # Create recommendations
        recommendations = []
        
        # If load balancer type is explicitly specified, make it the primary recommendation
        if lb_type:
            lb_info = {
                "alb": {
                    "name": "Application Load Balancer (ALB)",
                    "description": "Layer 7 load balancer for HTTP/HTTPS applications",
                    "use_case": "Web applications, microservices, container-based applications",
                    "features": ["Path-based routing", "Host-based routing", "HTTP header-based routing", "Support for WebSockets", "HTTP/2 support"],
                    "limitations": ["Does not support TCP/UDP protocols directly"]
                },
                "nlb": {
                    "name": "Network Load Balancer (NLB)",
                    "description": "Layer 4 load balancer for TCP/UDP applications",
                    "use_case": "TCP/UDP applications, extreme performance requirements, static IP addresses",
                    "features": ["Ultra-low latency", "Millions of requests per second", "Static IP addresses", "Preserve source IP address"],
                    "limitations": ["No application layer (HTTP) features"]
                },
                "clb": {
                    "name": "Classic Load Balancer (CLB)",
                    "description": "Legacy load balancer for basic HTTP/TCP applications",
                    "use_case": "Legacy applications, simple load balancing needs",
                    "features": ["Basic load balancing", "EC2-Classic support"],
                    "limitations": ["Limited features compared to ALB/NLB", "Not recommended for new applications"]
                }
            }
            
            lb_details = lb_info.get(lb_type, {})
            recommendations.append({
                "lb_type": lb_type,
                "name": lb_details.get("name", f"{lb_type.upper()} Load Balancer"),
                "description": lb_details.get("description", ""),
                "use_case": lb_details.get("use_case", ""),
                "features": lb_details.get("features", []),
                "limitations": lb_details.get("limitations", []),
                "rationale": "Matches explicitly requested load balancer type"
            })
        
        # Determine application type based on description
        app_type = "web"  # Default to web application
        if any(term in description.lower() for term in ["tcp", "udp", "network", "高性能", "静态ip", "static ip"]):
            app_type = "network"
        elif any(term in description.lower() for term in ["http", "https", "web", "网站", "应用"]):
            app_type = "web"
        
        # Add recommendations based on application type
        if app_type == "web" and (not lb_type or lb_type != "alb"):
            recommendations.append({
                "lb_type": "alb",
                "name": "Application Load Balancer (ALB)",
                "description": "Layer 7 load balancer for HTTP/HTTPS applications",
                "use_case": "Web applications, microservices, container-based applications",
                "features": ["Path-based routing", "Host-based routing", "HTTP header-based routing", "Support for WebSockets", "HTTP/2 support"],
                "limitations": ["Does not support TCP/UDP protocols directly"],
                "rationale": "Best choice for HTTP/HTTPS applications with advanced routing capabilities"
            })
        
        if app_type == "network" and (not lb_type or lb_type != "nlb"):
            recommendations.append({
                "lb_type": "nlb",
                "name": "Network Load Balancer (NLB)",
                "description": "Layer 4 load balancer for TCP/UDP applications",
                "use_case": "TCP/UDP applications, extreme performance requirements, static IP addresses",
                "features": ["Ultra-low latency", "Millions of requests per second", "Static IP addresses", "Preserve source IP address"],
                "limitations": ["No application layer (HTTP) features"],
                "rationale": "Best choice for TCP/UDP applications requiring high performance"
            })
        
        # Always include ALB as a recommendation if not already included
        if not any(rec["lb_type"] == "alb" for rec in recommendations):
            recommendations.append({
                "lb_type": "alb",
                "name": "Application Load Balancer (ALB)",
                "description": "Layer 7 load balancer for HTTP/HTTPS applications",
                "use_case": "Web applications, microservices, container-based applications",
                "features": ["Path-based routing", "Host-based routing", "HTTP header-based routing", "Support for WebSockets", "HTTP/2 support"],
                "limitations": ["Does not support TCP/UDP protocols directly"],
                "rationale": "Most versatile option for modern applications"
            })
        
        # Create the result
        result = {
            "requirements": {
                "requested_lb_type": lb_type,
                "data_processed_gb": data_processed,
                "detected_app_type": app_type,
                "region": region
            },
            "recommendations": recommendations[:2],  # Limit to top 2 recommendations
            "note": "Load balancer pricing includes hourly charges and data processing charges."
        }
        
        # Add pricing information to recommendations
        for rec in result["recommendations"]:
            try:
                pricing_response = json.loads(get_loadbalancer_pricing(
                    rec["lb_type"], region, data_processed
                ))
                
                if "hourly_pricing" in pricing_response and pricing_response["hourly_pricing"]:
                    rec["price_per_hour"] = pricing_response["hourly_pricing"][0].get("price")
                    rec["estimated_monthly_lb_cost"] = rec["price_per_hour"] * 24 * 30  # Approximate month as 30 days
                
                if "estimated_data_processing_cost" in pricing_response:
                    rec["estimated_data_processing_cost"] = pricing_response["estimated_data_processing_cost"]
                    rec["estimated_total_monthly_cost"] = (
                        rec["estimated_monthly_lb_cost"] + rec["estimated_data_processing_cost"]
                    )
            except Exception as e:
                logger.warning(f"Failed to get pricing for {rec['lb_type']}: {str(e)}")
        
        return json.dumps(result, default=str)
    
    except Exception as e:
        logger.error(f"Error recommending load balancer: {str(e)}")
        return json.dumps({"error": f"Error recommending load balancer: {str(e)}"})

@tool
def generate_aws_solution(
    description: str,
    region: str = "us-east-1",
    is_production: bool = True
) -> str:
    """
    Generate a complete AWS solution based on user requirements.
    
    Args:
        description: User requirements in natural language
        region: AWS region code (default: us-east-1)
        is_production: Whether this is for a production environment (default: True)
    
    Returns:
        JSON string with a complete AWS solution including all recommended resources and pricing
    """
    try:
        # Extract region and environment information if not explicitly provided
        extracted_region, extracted_is_production = _extract_region_and_environment(description)
        if extracted_region:
            region = extracted_region
        if extracted_is_production is not None:
            is_production = extracted_is_production
        
        # Initialize solution components
        solution = {
            "requirements": {
                "description": description,
                "region": region,
                "is_production": is_production
            },
            "components": {}
        }
        
        # Check for EC2 requirements
        if any(term in description.lower() for term in ["ec2", "instance", "server", "virtual machine", "vm", "服务器", "实例"]):
            try:
                ec2_recommendation = json.loads(recommend_ec2_instance(description, region, is_production))
                if "error" not in ec2_recommendation:
                    solution["components"]["ec2"] = {
                        "type": "EC2 Instances",
                        "recommendations": ec2_recommendation.get("recommendations", []),
                        "selected": ec2_recommendation.get("recommendations", [])[0] if ec2_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting EC2 recommendations: {str(e)}")
        
        # Check for EBS requirements
        if any(term in description.lower() for term in ["ebs", "storage", "volume", "disk", "存储", "磁盘"]):
            try:
                ebs_recommendation = json.loads(recommend_ebs_volume(description, region, is_production))
                if "error" not in ebs_recommendation:
                    solution["components"]["ebs"] = {
                        "type": "EBS Volumes",
                        "recommendations": ebs_recommendation.get("recommendations", []),
                        "selected": ebs_recommendation.get("recommendations", [])[0] if ebs_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting EBS recommendations: {str(e)}")
        
        # Check for S3 requirements
        if any(term in description.lower() for term in ["s3", "object storage", "对象存储"]):
            try:
                s3_recommendation = json.loads(recommend_s3_storage(description, region))
                if "error" not in s3_recommendation:
                    solution["components"]["s3"] = {
                        "type": "S3 Storage",
                        "recommendations": s3_recommendation.get("recommendations", []),
                        "selected": s3_recommendation.get("recommendations", [])[0] if s3_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting S3 recommendations: {str(e)}")
        
        # Check for RDS requirements
        if any(term in description.lower() for term in ["rds", "database", "db", "数据库", "mysql", "postgresql", "oracle", "sqlserver"]):
            try:
                rds_recommendation = json.loads(recommend_rds_instance(description, region, is_production))
                if "error" not in rds_recommendation:
                    solution["components"]["rds"] = {
                        "type": "RDS Database",
                        "recommendations": rds_recommendation.get("recommendations", []),
                        "selected": rds_recommendation.get("recommendations", [])[0] if rds_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting RDS recommendations: {str(e)}")
        
        # Check for ElastiCache requirements
        if any(term in description.lower() for term in ["elasticache", "cache", "redis", "memcached", "缓存"]):
            try:
                cache_recommendation = json.loads(recommend_elasticache_node(description, region, is_production))
                if "error" not in cache_recommendation:
                    solution["components"]["elasticache"] = {
                        "type": "ElastiCache",
                        "recommendations": cache_recommendation.get("recommendations", []),
                        "selected": cache_recommendation.get("recommendations", [])[0] if cache_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting ElastiCache recommendations: {str(e)}")
        
        # Check for OpenSearch requirements
        if any(term in description.lower() for term in ["opensearch", "elasticsearch", "search", "logs", "logging", "analytics", "搜索", "日志", "分析"]):
            try:
                search_recommendation = json.loads(recommend_opensearch_domain(description, region, is_production))
                if "error" not in search_recommendation:
                    solution["components"]["opensearch"] = {
                        "type": "OpenSearch Service",
                        "recommendations": search_recommendation.get("recommendations", []),
                        "selected": search_recommendation.get("recommendations", [])[0] if search_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting OpenSearch recommendations: {str(e)}")
        
        # Check for Load Balancer requirements
        if any(term in description.lower() for term in ["load balancer", "alb", "nlb", "elb", "负载均衡"]):
            try:
                lb_recommendation = json.loads(recommend_loadbalancer(description, region))
                if "error" not in lb_recommendation:
                    solution["components"]["loadbalancer"] = {
                        "type": "Load Balancer",
                        "recommendations": lb_recommendation.get("recommendations", []),
                        "selected": lb_recommendation.get("recommendations", [])[0] if lb_recommendation.get("recommendations") else None
                    }
            except Exception as e:
                logger.warning(f"Error getting Load Balancer recommendations: {str(e)}")
        
        # Calculate total cost
        resources = []
        
        # Add EC2 instances
        if "ec2" in solution["components"] and solution["components"]["ec2"]["selected"]:
            selected_ec2 = solution["components"]["ec2"]["selected"]
            resources.append({
                "type": "ec2",
                "instance_type": selected_ec2.get("instance_type"),
                "os": "linux",  # Default to Linux
                "count": 2 if is_production else 1  # Use 2 instances for production
            })
        
        # Add EBS volumes
        if "ebs" in solution["components"] and solution["components"]["ebs"]["selected"]:
            selected_ebs = solution["components"]["ebs"]["selected"]
            resources.append({
                "type": "ebs",
                "volume_type": selected_ebs.get("volume_type"),
                "size_gb": selected_ebs.get("size_gb")
            })
        
        # Add S3 storage
        if "s3" in solution["components"] and solution["components"]["s3"]["selected"]:
            selected_s3 = solution["components"]["s3"]["selected"]
            s3_size = solution["components"]["s3"].get("requirements", {}).get("storage_size_gb", 100)
            s3_transfer = solution["components"]["s3"].get("requirements", {}).get("data_transfer_gb", 50)
            resources.append({
                "type": "s3",
                "storage_class": selected_s3.get("storage_class"),
                "storage_gb": s3_size,
                "data_transfer_gb": s3_transfer
            })
        
        # Add RDS database
        if "rds" in solution["components"] and solution["components"]["rds"]["selected"]:
            selected_rds = solution["components"]["rds"]["selected"]
            resources.append({
                "type": "rds",
                "instance_type": selected_rds.get("instance_type"),
                "engine": selected_rds.get("engine"),
                "deployment_option": selected_rds.get("deployment_option"),
                "storage_gb": selected_rds.get("storage_gb")
            })
        
        # Add ElastiCache
        if "elasticache" in solution["components"] and solution["components"]["elasticache"]["selected"]:
            selected_cache = solution["components"]["elasticache"]["selected"]
            resources.append({
                "type": "elasticache",
                "node_type": selected_cache.get("node_type"),
                "engine": selected_cache.get("engine"),
                "count": 2 if is_production else 1  # Use 2 nodes for production
            })
        
        # Add OpenSearch
        if "opensearch" in solution["components"] and solution["components"]["opensearch"]["selected"]:
            selected_search = solution["components"]["opensearch"]["selected"]
            resources.append({
                "type": "opensearch",
                "instance_type": selected_search.get("instance_type"),
                "storage_gb": selected_search.get("storage_gb"),
                "node_count": selected_search.get("node_count")
            })
        
        # Add Load Balancer
        if "loadbalancer" in solution["components"] and solution["components"]["loadbalancer"]["selected"]:
            selected_lb = solution["components"]["loadbalancer"]["selected"]
            lb_data = solution["components"]["loadbalancer"].get("requirements", {}).get("data_processed_gb", 500)
            resources.append({
                "type": "loadbalancer",
                "lb_type": selected_lb.get("lb_type"),
                "data_processed_gb": lb_data
            })
        
        # Calculate total cost if we have resources
        if resources:
            try:
                cost_calculation = json.loads(calculate_aws_cost(resources, region))
                solution["cost_summary"] = {
                    "resources": cost_calculation.get("cost_items", []),
                    "total_monthly_cost": cost_calculation.get("total_monthly_cost"),
                    "currency": "USD"
                }
            except Exception as e:
                logger.warning(f"Error calculating total cost: {str(e)}")
                solution["cost_summary"] = {
                    "error": f"Failed to calculate total cost: {str(e)}"
                }
        
        # Add architecture recommendations
        solution["architecture_recommendations"] = []
        
        # High availability for production
        if is_production:
            solution["architecture_recommendations"].append(
                "Deploy resources across multiple Availability Zones for high availability"
            )
        
        # Auto Scaling for EC2
        if "ec2" in solution["components"]:
            solution["architecture_recommendations"].append(
                "Use Auto Scaling Groups for EC2 instances to handle variable load"
            )
        
        # Security recommendations
        solution["architecture_recommendations"].append(
            "Implement security groups and network ACLs to control traffic"
        )
        solution["architecture_recommendations"].append(
            "Use IAM roles and policies to manage access to resources"
        )
        
        # Backup recommendations
        if "rds" in solution["components"] or "ebs" in solution["components"]:
            solution["architecture_recommendations"].append(
                "Configure automated backups for databases and critical data"
            )
        
        # Monitoring recommendations
        solution["architecture_recommendations"].append(
            "Set up CloudWatch monitoring and alarms for all resources"
        )
        
        return json.dumps(solution, default=str)
    
    except Exception as e:
        logger.error(f"Error generating AWS solution: {str(e)}")
        return json.dumps({"error": f"Error generating AWS solution: {str(e)}"})