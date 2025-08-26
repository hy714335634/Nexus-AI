"""
Match IT product specifications to equivalent AWS services.

This tool takes structured IT product data and determines the most appropriate AWS 
services based on product specifications. It provides configuration details and 
pricing options for the matched services according to AWS best practices.

Examples:
    Input: Structured server data with CPU, RAM, and storage specifications
    Output: Matching EC2 instance types, EBS volumes, and configuration recommendations
"""
from strands import tool
import json
from typing import Dict, Any, List, Optional, Union

# AWS Service Catalog - EC2 Instance Types with approximate specs for matching
EC2_INSTANCES = {
    # General Purpose
    "t3.micro": {"vcpu": 2, "memory": 1, "description": "Burstable general purpose"},
    "t3.small": {"vcpu": 2, "memory": 2, "description": "Burstable general purpose"},
    "t3.medium": {"vcpu": 2, "memory": 4, "description": "Burstable general purpose"},
    "t3.large": {"vcpu": 2, "memory": 8, "description": "Burstable general purpose"},
    "t3.xlarge": {"vcpu": 4, "memory": 16, "description": "Burstable general purpose"},
    "t3.2xlarge": {"vcpu": 8, "memory": 32, "description": "Burstable general purpose"},
    
    "m5.large": {"vcpu": 2, "memory": 8, "description": "General purpose"},
    "m5.xlarge": {"vcpu": 4, "memory": 16, "description": "General purpose"},
    "m5.2xlarge": {"vcpu": 8, "memory": 32, "description": "General purpose"},
    "m5.4xlarge": {"vcpu": 16, "memory": 64, "description": "General purpose"},
    "m5.8xlarge": {"vcpu": 32, "memory": 128, "description": "General purpose"},
    "m5.12xlarge": {"vcpu": 48, "memory": 192, "description": "General purpose"},
    "m5.16xlarge": {"vcpu": 64, "memory": 256, "description": "General purpose"},
    "m5.24xlarge": {"vcpu": 96, "memory": 384, "description": "General purpose"},
    
    # Compute Optimized
    "c5.large": {"vcpu": 2, "memory": 4, "description": "Compute optimized"},
    "c5.xlarge": {"vcpu": 4, "memory": 8, "description": "Compute optimized"},
    "c5.2xlarge": {"vcpu": 8, "memory": 16, "description": "Compute optimized"},
    "c5.4xlarge": {"vcpu": 16, "memory": 32, "description": "Compute optimized"},
    "c5.9xlarge": {"vcpu": 36, "memory": 72, "description": "Compute optimized"},
    "c5.12xlarge": {"vcpu": 48, "memory": 96, "description": "Compute optimized"},
    "c5.18xlarge": {"vcpu": 72, "memory": 144, "description": "Compute optimized"},
    "c5.24xlarge": {"vcpu": 96, "memory": 192, "description": "Compute optimized"},
    
    # Memory Optimized
    "r5.large": {"vcpu": 2, "memory": 16, "description": "Memory optimized"},
    "r5.xlarge": {"vcpu": 4, "memory": 32, "description": "Memory optimized"},
    "r5.2xlarge": {"vcpu": 8, "memory": 64, "description": "Memory optimized"},
    "r5.4xlarge": {"vcpu": 16, "memory": 128, "description": "Memory optimized"},
    "r5.8xlarge": {"vcpu": 32, "memory": 256, "description": "Memory optimized"},
    "r5.12xlarge": {"vcpu": 48, "memory": 384, "description": "Memory optimized"},
    "r5.16xlarge": {"vcpu": 64, "memory": 512, "description": "Memory optimized"},
    "r5.24xlarge": {"vcpu": 96, "memory": 768, "description": "Memory optimized"},
    
    # Storage Optimized
    "i3.large": {"vcpu": 2, "memory": 16, "description": "Storage optimized with NVMe SSD"},
    "i3.xlarge": {"vcpu": 4, "memory": 32, "description": "Storage optimized with NVMe SSD"},
    "i3.2xlarge": {"vcpu": 8, "memory": 64, "description": "Storage optimized with NVMe SSD"},
    "i3.4xlarge": {"vcpu": 16, "memory": 128, "description": "Storage optimized with NVMe SSD"},
    "i3.8xlarge": {"vcpu": 32, "memory": 256, "description": "Storage optimized with NVMe SSD"},
    "i3.16xlarge": {"vcpu": 64, "memory": 512, "description": "Storage optimized with NVMe SSD"},
}

# AWS Storage Services
STORAGE_SERVICES = {
    "ebs_gp3": {
        "name": "Amazon EBS gp3",
        "description": "General purpose SSD volume that balances price and performance",
        "use_case": "Boot volumes, dev/test environments, medium-sized databases",
        "performance": "3,000-16,000 IOPS, 125-1,000 MB/s throughput"
    },
    "ebs_io1": {
        "name": "Amazon EBS io1/io2",
        "description": "Highest-performance SSD volume for mission-critical workloads",
        "use_case": "Critical business applications, large databases with high I/O needs",
        "performance": "Up to 64,000 IOPS, 1,000 MB/s throughput"
    },
    "ebs_st1": {
        "name": "Amazon EBS st1",
        "description": "Low-cost HDD volume for frequently accessed throughput-intensive workloads",
        "use_case": "Big data, data warehouses, log processing",
        "performance": "Up to 500 IOPS, 500 MB/s throughput"
    },
    "ebs_sc1": {
        "name": "Amazon EBS sc1",
        "description": "Lowest cost HDD volume for less frequently accessed data",
        "use_case": "Archive data, infrequently accessed workloads",
        "performance": "Up to 250 IOPS, 250 MB/s throughput"
    },
    "s3_standard": {
        "name": "Amazon S3 Standard",
        "description": "General purpose object storage for frequently accessed data",
        "use_case": "Content distribution, websites, mobile applications",
        "performance": "Low-latency, high-throughput performance"
    },
    "s3_ia": {
        "name": "Amazon S3 Standard-IA",
        "description": "For less frequently accessed data but with rapid access when needed",
        "use_case": "Long-term storage, backups, disaster recovery",
        "performance": "Same performance as S3 Standard"
    },
    "s3_glacier": {
        "name": "Amazon S3 Glacier",
        "description": "Low-cost archive storage with retrieval times from minutes to hours",
        "use_case": "Long-term archives, compliance data retention",
        "performance": "Retrieval within minutes to hours"
    }
}

# AWS Database Services
DATABASE_SERVICES = {
    "rds_mysql": {
        "name": "Amazon RDS for MySQL",
        "description": "Managed MySQL database service",
        "use_case": "Web applications, content management systems",
        "features": "Automated backups, patching, scaling"
    },
    "rds_postgresql": {
        "name": "Amazon RDS for PostgreSQL",
        "description": "Managed PostgreSQL database service",
        "use_case": "Geographic applications, complex workloads",
        "features": "Automated backups, patching, scaling"
    },
    "rds_sqlserver": {
        "name": "Amazon RDS for SQL Server",
        "description": "Managed SQL Server database service",
        "use_case": "Enterprise applications, Microsoft workloads",
        "features": "Automated backups, patching, multi-AZ"
    },
    "rds_oracle": {
        "name": "Amazon RDS for Oracle",
        "description": "Managed Oracle database service",
        "use_case": "Enterprise applications, Oracle workloads",
        "features": "Automated backups, patching, multi-AZ"
    },
    "aurora": {
        "name": "Amazon Aurora",
        "description": "MySQL and PostgreSQL-compatible relational database with 5x performance",
        "use_case": "Enterprise applications requiring high performance and availability",
        "features": "Distributed, fault-tolerant, self-healing storage"
    },
    "dynamodb": {
        "name": "Amazon DynamoDB",
        "description": "Fully managed NoSQL database service",
        "use_case": "Mobile, web, gaming, IoT applications",
        "features": "Single-digit millisecond latency, auto scaling, serverless"
    },
    "redshift": {
        "name": "Amazon Redshift",
        "description": "Fast, simple, cost-effective data warehousing service",
        "use_case": "Data warehousing, big data analytics",
        "features": "Parallel processing, columnar storage, ML integration"
    }
}

# AWS Networking Services
NETWORK_SERVICES = {
    "elb": {
        "name": "Elastic Load Balancing",
        "description": "Automatically distributes incoming application traffic",
        "types": ["Application Load Balancer", "Network Load Balancer", "Gateway Load Balancer"]
    },
    "vpc": {
        "name": "Amazon Virtual Private Cloud",
        "description": "Isolated cloud resources with custom networking",
        "features": ["Security Groups", "Network ACLs", "Route Tables"]
    },
    "direct_connect": {
        "name": "AWS Direct Connect",
        "description": "Dedicated network connection from premises to AWS",
        "options": ["1Gbps", "10Gbps", "100Gbps"]
    },
    "route53": {
        "name": "Amazon Route 53",
        "description": "Scalable domain name system (DNS) web service",
        "features": ["Health checks", "Failover", "Geolocation routing"]
    },
    "cloudfront": {
        "name": "Amazon CloudFront",
        "description": "Global content delivery network service",
        "features": ["Low latency", "High transfer speeds", "Edge locations worldwide"]
    }
}

@tool
def match_aws_service(product_data: str) -> str:
    """
    Match IT product specifications to equivalent AWS services.
    
    Args:
        product_data (str): JSON string containing structured product data with specifications
        
    Returns:
        str: JSON string with AWS service matches and configuration details
    
    Raises:
        ValueError: If input data cannot be parsed or is invalid
    """
    try:
        # Parse input JSON data
        products = json.loads(product_data)
        
        # Ensure products is a list
        if not isinstance(products, list):
            products = [products]
        
        matched_services = []
        
        for product in products:
            # Skip products with errors
            if "error" in product:
                matched_services.append({
                    "original_product": product,
                    "match_error": "Could not match due to parsing error in product data",
                    "partial_matches": []
                })
                continue
            
            # Determine product type and call appropriate matcher
            product_type = product.get("type", "").lower()
            
            if product_type == "server":
                matched_service = _match_server(product)
            elif product_type == "storage":
                matched_service = _match_storage(product)
            elif product_type == "network":
                matched_service = _match_network(product)
            elif product_type == "database":
                matched_service = _match_database(product)
            else:
                # Default to server if type is unknown
                matched_service = _match_server(product)
            
            matched_services.append(matched_service)
        
        return json.dumps(matched_services, ensure_ascii=False, indent=2)
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input data")
    except Exception as e:
        raise ValueError(f"Error matching AWS services: {str(e)}")

def _match_server(product: Dict[str, Any]) -> Dict[str, Any]:
    """Match server products to EC2 instances."""
    result = {
        "original_product": product,
        "aws_service": "Amazon EC2",
        "configuration": {},
        "alternatives": []
    }
    
    # Extract CPU and memory specifications
    specs = product.get("specs", {})
    
    # Parse CPU info
    cpu_count = 2  # Default value
    cpu_info = specs.get("cpu", "")
    
    # Try to extract CPU count from specification
    if cpu_info:
        cpu_count_match = re.search(r'(\d+)\s*x', cpu_info, re.IGNORECASE)
        if cpu_count_match:
            try:
                cpu_count = int(cpu_count_match.group(1))
            except ValueError:
                cpu_count = 2  # Default if parsing fails
    
    # Parse memory size in GB
    memory_gb = 8  # Default value
    memory_info = specs.get("memory", "")
    
    if memory_info:
        memory_match = re.search(r'(\d+)\s*(GB|TB|MB)', memory_info, re.IGNORECASE)
        if memory_match:
            try:
                memory_size = int(memory_match.group(1))
                memory_unit = memory_match.group(2).upper()
                
                # Convert to GB
                if memory_unit == "TB":
                    memory_gb = memory_size * 1024
                elif memory_unit == "MB":
                    memory_gb = memory_size / 1024
                else:  # GB
                    memory_gb = memory_size
            except ValueError:
                memory_gb = 8  # Default if parsing fails
    
    # Find matching EC2 instance types
    matched_instances = []
    for instance_type, instance_specs in EC2_INSTANCES.items():
        # Calculate a match score based on CPU and memory proximity
        cpu_score = abs(instance_specs["vcpu"] - cpu_count)
        memory_score = abs(instance_specs["memory"] - memory_gb)
        
        # Lower score is better
        total_score = cpu_score * 2 + memory_score
        
        matched_instances.append({
            "instance_type": instance_type,
            "specs": instance_specs,
            "match_score": total_score
        })
    
    # Sort by match score (lower is better)
    matched_instances.sort(key=lambda x: x["match_score"])
    
    # Select the best match
    if matched_instances:
        best_match = matched_instances[0]
        result["configuration"] = {
            "instance_type": best_match["instance_type"],
            "vcpu": best_match["specs"]["vcpu"],
            "memory_gb": best_match["specs"]["memory"],
            "description": best_match["specs"]["description"]
        }
        
        # Add alternatives
        for alt in matched_instances[1:4]:  # Take next 3 best matches
            result["alternatives"].append({
                "instance_type": alt["instance_type"],
                "vcpu": alt["specs"]["vcpu"],
                "memory_gb": alt["specs"]["memory"],
                "description": alt["specs"]["description"]
            })
    
    # Check for storage requirements and add EBS volumes
    storage_info = specs.get("storage", "")
    if storage_info:
        storage_match = re.search(r'(\d+)\s*(GB|TB|PB)', storage_info, re.IGNORECASE)
        if storage_match:
            try:
                storage_size = int(storage_match.group(1))
                storage_unit = storage_match.group(2).upper()
                
                # Convert to GB
                storage_gb = storage_size
                if storage_unit == "TB":
                    storage_gb = storage_size * 1024
                elif storage_unit == "PB":
                    storage_gb = storage_size * 1024 * 1024
                
                # Determine EBS volume type
                ebs_type = "gp3"  # Default to general purpose SSD
                if "SSD" in storage_info or "固态" in storage_info or "高性能" in storage_info:
                    ebs_type = "gp3"
                elif "HDD" in storage_info or "机械" in storage_info:
                    ebs_type = "st1"
                
                # Add EBS configuration
                result["configuration"]["storage"] = {
                    "type": f"Amazon EBS {ebs_type}",
                    "size_gb": storage_gb,
                    "description": STORAGE_SERVICES.get(f"ebs_{ebs_type}", {}).get("description", "")
                }
            except (ValueError, AttributeError):
                pass  # Skip if parsing fails
    
    # Add some typical server deployment resources
    result["additional_services"] = [
        {
            "service": "Amazon VPC",
            "description": "Networking isolation for your EC2 instances"
        },
        {
            "service": "Amazon CloudWatch",
            "description": "Monitoring and management service for your EC2 instances"
        }
    ]
    
    return result

def _match_storage(product: Dict[str, Any]) -> Dict[str, Any]:
    """Match storage products to AWS storage services."""
    result = {
        "original_product": product,
        "aws_service": "AWS Storage",
        "configuration": {},
        "alternatives": []
    }
    
    specs = product.get("specs", {})
    product_name = product.get("product_name", "").lower()
    
    # Parse storage capacity
    storage_capacity_gb = 100  # Default value
    storage_info = specs.get("storage", "")
    
    if storage_info:
        storage_match = re.search(r'(\d+)\s*(GB|TB|PB)', storage_info, re.IGNORECASE)
        if storage_match:
            try:
                storage_size = int(storage_match.group(1))
                storage_unit = storage_match.group(2).upper()
                
                # Convert to GB
                if storage_unit == "TB":
                    storage_capacity_gb = storage_size * 1024
                elif storage_unit == "PB":
                    storage_capacity_gb = storage_size * 1024 * 1024
                else:  # GB
                    storage_capacity_gb = storage_size
            except ValueError:
                pass  # Use default if parsing fails
    
    # Determine storage type and use case
    is_high_performance = any(keyword in product_name.lower() for keyword in ["ssd", "flash", "高性能", "闪存"])
    is_archive = any(keyword in product_name.lower() for keyword in ["archive", "backup", "备份", "归档"])
    is_object_storage = any(keyword in product_name.lower() for keyword in ["object", "对象存储", "分布式"])
    
    # Determine primary AWS storage service
    if is_object_storage:
        # Object storage matches to S3
        result["aws_service"] = "Amazon S3"
        result["configuration"] = {
            "service_type": "Amazon S3 Standard",
            "capacity_gb": storage_capacity_gb,
            "description": STORAGE_SERVICES["s3_standard"]["description"],
            "use_case": STORAGE_SERVICES["s3_standard"]["use_case"]
        }
        
        # Add alternatives
        result["alternatives"] = [
            {
                "service_type": "Amazon S3 Standard-IA",
                "capacity_gb": storage_capacity_gb,
                "description": STORAGE_SERVICES["s3_ia"]["description"]
            }
        ]
        
        if is_archive:
            result["alternatives"].append({
                "service_type": "Amazon S3 Glacier",
                "capacity_gb": storage_capacity_gb,
                "description": STORAGE_SERVICES["s3_glacier"]["description"]
            })
            
    else:
        # Block storage matches to EBS
        ebs_type = "gp3"
        if is_high_performance:
            ebs_type = "io1"
        elif is_archive:
            ebs_type = "sc1"
        
        result["aws_service"] = "Amazon EBS"
        result["configuration"] = {
            "service_type": f"Amazon EBS {ebs_type}",
            "capacity_gb": storage_capacity_gb,
            "description": STORAGE_SERVICES.get(f"ebs_{ebs_type}", {}).get("description", ""),
            "performance": STORAGE_SERVICES.get(f"ebs_{ebs_type}", {}).get("performance", "")
        }
        
        # Add alternatives
        if ebs_type != "gp3":
            result["alternatives"].append({
                "service_type": "Amazon EBS gp3",
                "capacity_gb": storage_capacity_gb,
                "description": STORAGE_SERVICES["ebs_gp3"]["description"]
            })
        
        # For large storage requirements, suggest S3 as alternative
        if storage_capacity_gb > 10240:  # More than 10TB
            result["alternatives"].append({
                "service_type": "Amazon S3 Standard",
                "capacity_gb": storage_capacity_gb,
                "description": "Object storage, more cost-effective for large datasets"
            })
    
    # Add some typical additional services
    result["additional_services"] = [
        {
            "service": "AWS Backup",
            "description": "Centralized backup service for AWS services"
        }
    ]
    
    return result

def _match_network(product: Dict[str, Any]) -> Dict[str, Any]:
    """Match networking products to AWS networking services."""
    result = {
        "original_product": product,
        "aws_service": "AWS Networking",
        "configuration": {},
        "alternatives": []
    }
    
    product_name = product.get("product_name", "").lower()
    
    # Determine network device type
    if any(keyword in product_name for keyword in ["负载均衡", "load balancer", "均衡器"]):
        # Load Balancer
        result["aws_service"] = "Elastic Load Balancing"
        result["configuration"] = {
            "service_type": "Application Load Balancer",
            "description": "Layer 7 load balancing for HTTP/HTTPS applications",
            "features": ["Content-based routing", "Host-based routing", "Path-based routing"]
        }
        
        result["alternatives"] = [
            {
                "service_type": "Network Load Balancer",
                "description": "Layer 4 load balancing for TCP/UDP applications"
            }
        ]
        
    elif any(keyword in product_name for keyword in ["防火墙", "firewall", "安全"]):
        # Firewall
        result["aws_service"] = "AWS Network Security"
        result["configuration"] = {
            "service_type": "AWS Network Firewall",
            "description": "Managed firewall service for VPC protection",
            "features": ["Stateful inspection", "Intrusion prevention", "Web filtering"]
        }
        
        result["alternatives"] = [
            {
                "service_type": "Security Groups",
                "description": "Virtual firewall for EC2 instances"
            },
            {
                "service_type": "AWS WAF",
                "description": "Web Application Firewall for protecting web applications"
            }
        ]
        
    elif any(keyword in product_name for keyword in ["路由器", "router"]):
        # Router
        result["aws_service"] = "Amazon VPC"
        result["configuration"] = {
            "service_type": "VPC with Transit Gateway",
            "description": "Network transit hub to connect VPCs and on-premises networks",
            "features": ["Centralized routing", "Network segmentation", "Scalable architecture"]
        }
        
        result["alternatives"] = [
            {
                "service_type": "VPN Connection",
                "description": "Secure connection between VPC and on-premises network"
            }
        ]
        
    elif any(keyword in product_name for keyword in ["交换机", "switch"]):
        # Switch
        result["aws_service"] = "Amazon VPC"
        result["configuration"] = {
            "service_type": "VPC with Multiple Subnets",
            "description": "Network isolation with subnet configuration",
            "features": ["Network ACLs", "Route Tables", "Security Groups"]
        }
        
        result["alternatives"] = [
            {
                "service_type": "AWS Transit Gateway",
                "description": "Network transit hub to simplify network architecture"
            }
        ]
        
    else:
        # Generic networking device
        result["aws_service"] = "Amazon VPC"
        result["configuration"] = {
            "service_type": "Amazon VPC",
            "description": "Isolated cloud resources with custom networking",
            "features": ["Security Groups", "Network ACLs", "Route Tables"]
        }
    
    # Add some typical additional services
    result["additional_services"] = [
        {
            "service": "AWS Shield",
            "description": "Managed DDoS protection service"
        },
        {
            "service": "Amazon CloudFront",
            "description": "Global content delivery network"
        }
    ]
    
    return result

def _match_database(product: Dict[str, Any]) -> Dict[str, Any]:
    """Match database products to AWS database services."""
    result = {
        "original_product": product,
        "aws_service": "AWS Database",
        "configuration": {},
        "alternatives": []
    }
    
    product_name = product.get("product_name", "").lower()
    specs = product.get("specs", {})
    
    # Determine database type
    is_oracle = any(keyword in product_name for keyword in ["oracle", "甲骨文"])
    is_sqlserver = any(keyword in product_name for keyword in ["sql server", "sqlserver", "微软"])
    is_mysql = any(keyword in product_name for keyword in ["mysql", "我的sql"])
    is_postgresql = any(keyword in product_name for keyword in ["postgresql", "postgres"])
    is_nosql = any(keyword in product_name for keyword in ["nosql", "mongodb", "dynamodb", "非关系"])
    is_warehouse = any(keyword in product_name for keyword in ["warehouse", "数据仓库", "redshift"])
    
    # Match to appropriate database service
    if is_oracle:
        result["aws_service"] = "Amazon RDS"
        result["configuration"] = {
            "service_type": "Amazon RDS for Oracle",
            "description": DATABASE_SERVICES["rds_oracle"]["description"],
            "features": DATABASE_SERVICES["rds_oracle"]["features"].split(", ")
        }
        
        result["alternatives"] = [
            {
                "service_type": "Amazon Aurora",
                "description": "MySQL and PostgreSQL-compatible with better performance"
            }
        ]
        
    elif is_sqlserver:
        result["aws_service"] = "Amazon RDS"
        result["configuration"] = {
            "service_type": "Amazon RDS for SQL Server",
            "description": DATABASE_SERVICES["rds_sqlserver"]["description"],
            "features": DATABASE_SERVICES["rds_sqlserver"]["features"].split(", ")
        }
        
    elif is_mysql:
        result["aws_service"] = "Amazon RDS"
        result["configuration"] = {
            "service_type": "Amazon RDS for MySQL",
            "description": DATABASE_SERVICES["rds_mysql"]["description"],
            "features": DATABASE_SERVICES["rds_mysql"]["features"].split(", ")
        }
        
        result["alternatives"] = [
            {
                "service_type": "Amazon Aurora MySQL-Compatible",
                "description": "MySQL-compatible with 5x performance and higher availability"
            }
        ]
        
    elif is_postgresql:
        result["aws_service"] = "Amazon RDS"
        result["configuration"] = {
            "service_type": "Amazon RDS for PostgreSQL",
            "description": DATABASE_SERVICES["rds_postgresql"]["description"],
            "features": DATABASE_SERVICES["rds_postgresql"]["features"].split(", ")
        }
        
        result["alternatives"] = [
            {
                "service_type": "Amazon Aurora PostgreSQL-Compatible",
                "description": "PostgreSQL-compatible with higher performance and availability"
            }
        ]
        
    elif is_nosql:
        result["aws_service"] = "Amazon DynamoDB"
        result["configuration"] = {
            "service_type": "Amazon DynamoDB",
            "description": DATABASE_SERVICES["dynamodb"]["description"],
            "features": DATABASE_SERVICES["dynamodb"]["features"].split(", ")
        }
        
    elif is_warehouse:
        result["aws_service"] = "Amazon Redshift"
        result["configuration"] = {
            "service_type": "Amazon Redshift",
            "description": DATABASE_SERVICES["redshift"]["description"],
            "features": DATABASE_SERVICES["redshift"]["features"].split(", ")
        }
        
    else:
        # Default to RDS MySQL as a generic database solution
        result["aws_service"] = "Amazon RDS"
        result["configuration"] = {
            "service_type": "Amazon RDS for MySQL",
            "description": DATABASE_SERVICES["rds_mysql"]["description"],
            "features": DATABASE_SERVICES["rds_mysql"]["features"].split(", ")
        }
        
        # Add more alternatives
        result["alternatives"] = [
            {
                "service_type": "Amazon Aurora",
                "description": "MySQL and PostgreSQL-compatible with better performance"
            },
            {
                "service_type": "Amazon DynamoDB",
                "description": "NoSQL database for applications requiring low-latency"
            }
        ]
    
    # Extract storage requirements if available
    storage_info = specs.get("storage", "")
    if storage_info:
        storage_match = re.search(r'(\d+)\s*(GB|TB|PB)', storage_info, re.IGNORECASE)
        if storage_match:
            try:
                storage_size = int(storage_match.group(1))
                storage_unit = storage_match.group(2).upper()
                
                # Convert to GB
                storage_gb = storage_size
                if storage_unit == "TB":
                    storage_gb = storage_size * 1024
                elif storage_unit == "PB":
                    storage_gb = storage_size * 1024 * 1024
                
                # Add storage configuration
                result["configuration"]["storage_gb"] = storage_gb
            except (ValueError, AttributeError):
                pass
    
    # Add typical additional services
    result["additional_services"] = [
        {
            "service": "Amazon RDS Proxy",
            "description": "Database proxy for connection pooling"
        },
        {
            "service": "AWS Database Migration Service",
            "description": "Migrate databases to AWS with minimal downtime"
        }
    ]
    
    return result

# Import needed for regex searches
import re