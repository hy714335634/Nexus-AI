"""AWS Service Knowledge Base Tool.

This tool provides access to information about AWS services, their capabilities,
use cases, and relationships.
"""

from typing import Dict, List, Optional, Any, Union
import json
import boto3
from strands import tool


@tool
def aws_service_info(
    service_name: str,
    info_type: str = "general"
) -> str:
    """Get information about a specific AWS service.

    Args:
        service_name (str): The name of the AWS service (e.g., "EC2", "S3", "RDS")
        info_type (str): Type of information to retrieve. Options:
            - "general": General information about the service
            - "features": Key features and capabilities
            - "use_cases": Common use cases
            - "limits": Service limits and quotas
            - "pricing": Pricing information
            - "related": Related AWS services
            - "best_practices": Best practices for using the service

    Returns:
        str: JSON formatted information about the requested AWS service
    """
    try:
        # Normalize service name to handle different formats
        service_name = service_name.lower().strip()
        
        # Use AWS Service Catalog API to get service information
        client = boto3.client('servicecatalog', region_name='us-east-1')
        
        # First try to find the product by name
        response = {}
        
        try:
            # Try to get detailed information based on the service name
            if info_type == "general":
                response = client.describe_product_as_admin(
                    Name=service_name
                )
            elif info_type == "features" or info_type == "use_cases":
                # Get product details which include features and use cases
                products = client.search_products(
                    Filters={
                        'FullTextSearch': [service_name]
                    }
                )
                
                if products.get('ProductViewSummaries'):
                    product_id = products['ProductViewSummaries'][0]['ProductId']
                    response = client.describe_product_view(
                        Id=product_id
                    )
            elif info_type == "limits":
                # For service limits, we need to use the Service Quotas API
                quotas_client = boto3.client('service-quotas', region_name='us-east-1')
                service_code = _get_service_code(service_name)
                if service_code:
                    quotas = quotas_client.list_service_quotas(
                        ServiceCode=service_code
                    )
                    response = {"quotas": quotas.get('Quotas', [])}
                else:
                    response = {"error": f"Could not find service code for {service_name}"}
            elif info_type == "pricing":
                # For pricing, we need to use the Pricing API
                pricing_client = boto3.client('pricing', region_name='us-east-1')
                pricing = pricing_client.get_products(
                    ServiceCode=_get_service_code(service_name) or service_name,
                    MaxResults=5
                )
                response = {"pricing": pricing.get('PriceList', [])}
            elif info_type == "related":
                # For related services, we'll use a custom implementation
                response = {"related_services": _get_related_services(service_name)}
            elif info_type == "best_practices":
                # For best practices, we'll use a custom implementation
                response = {"best_practices": _get_best_practices(service_name)}
            else:
                response = {"error": f"Invalid info_type: {info_type}"}
                
        except client.exceptions.ResourceNotFoundException:
            # If service not found in Service Catalog, fall back to our knowledge base
            response = _get_service_info_from_knowledge_base(service_name, info_type)
        
        if not response or (isinstance(response, dict) and not response.keys()):
            # If we still don't have data, fall back to our knowledge base
            response = _get_service_info_from_knowledge_base(service_name, info_type)
            
        return json.dumps(response, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to retrieve information for {service_name}: {str(e)}",
            "fallback_info": _get_service_info_from_knowledge_base(service_name, info_type)
        }, indent=2)


@tool
def aws_service_search(
    keyword: str,
    category: Optional[str] = None,
    max_results: int = 10
) -> str:
    """Search for AWS services based on keywords or categories.

    Args:
        keyword (str): Keyword to search for in service descriptions
        category (str, optional): Filter by service category (e.g., "Compute", "Storage", "Database")
        max_results (int): Maximum number of results to return (default: 10)

    Returns:
        str: JSON formatted list of matching AWS services
    """
    try:
        # Use AWS Service Catalog API to search for services
        client = boto3.client('servicecatalog', region_name='us-east-1')
        
        filters = {
            'FullTextSearch': [keyword]
        }
        
        # Add category filter if provided
        if category:
            # Map common category names to AWS category names
            category_mapping = {
                "compute": "Compute",
                "storage": "Storage",
                "database": "Database",
                "networking": "Networking & Content Delivery",
                "security": "Security, Identity, & Compliance",
                "analytics": "Analytics",
                "machine learning": "Machine Learning",
                "integration": "Application Integration",
                "iot": "Internet of Things",
                "containers": "Containers",
                "serverless": "Serverless"
            }
            
            aws_category = category_mapping.get(category.lower(), category)
            
            # Add category filter
            filters['Category'] = [aws_category]
        
        try:
            # Search for products in the Service Catalog
            response = client.search_products(
                Filters=filters
            )
            
            # Extract relevant information
            services = []
            for product in response.get('ProductViewSummaries', [])[:max_results]:
                services.append({
                    "name": product.get('Name'),
                    "description": product.get('ShortDescription'),
                    "id": product.get('ProductId'),
                    "owner": product.get('Owner'),
                    "product_type": product.get('Type'),
                    "distributor": product.get('Distributor')
                })
                
            result = {
                "keyword": keyword,
                "category": category,
                "total_results": len(response.get('ProductViewSummaries', [])),
                "returned_results": len(services),
                "services": services
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            # Fall back to our knowledge base
            return json.dumps({
                "error": f"Service Catalog search failed: {str(e)}",
                "fallback_results": _search_service_knowledge_base(keyword, category, max_results)
            }, indent=2)
    
    except Exception as e:
        # Fall back to our knowledge base for any errors
        return json.dumps({
            "error": f"Failed to search AWS services: {str(e)}",
            "fallback_results": _search_service_knowledge_base(keyword, category, max_results)
        }, indent=2)


@tool
def aws_service_mapping(
    technology: str,
    use_case: Optional[str] = None,
    alternatives: bool = False
) -> str:
    """Map a technology or concept to equivalent AWS services.

    Args:
        technology (str): The technology or concept to map (e.g., "MySQL", "load balancer", "message queue")
        use_case (str, optional): Specific use case to refine the mapping
        alternatives (bool): Whether to include alternative AWS services (default: False)

    Returns:
        str: JSON formatted mapping of the technology to AWS services
    """
    try:
        # Normalize inputs
        technology = technology.lower().strip()
        if use_case:
            use_case = use_case.lower().strip()
        
        # Get mapping from our knowledge base
        mapping = _get_technology_mapping(technology, use_case, alternatives)
        
        return json.dumps(mapping, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to map technology {technology} to AWS services: {str(e)}"
        }, indent=2)


@tool
def aws_architecture_pattern(
    pattern_name: str,
    details: bool = False
) -> str:
    """Get information about common AWS architecture patterns.

    Args:
        pattern_name (str): Name of the architecture pattern (e.g., "three-tier", "microservices", "serverless")
        details (bool): Whether to include detailed implementation information (default: False)

    Returns:
        str: JSON formatted information about the architecture pattern
    """
    try:
        # Normalize pattern name
        pattern_name = pattern_name.lower().strip()
        
        # Get pattern information from our knowledge base
        pattern_info = _get_architecture_pattern(pattern_name, details)
        
        return json.dumps(pattern_info, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to retrieve architecture pattern {pattern_name}: {str(e)}"
        }, indent=2)


@tool
def aws_service_compatibility(
    service1: str,
    service2: str
) -> str:
    """Check compatibility between two AWS services.

    Args:
        service1 (str): First AWS service name
        service2 (str): Second AWS service name

    Returns:
        str: JSON formatted compatibility information between the services
    """
    try:
        # Normalize service names
        service1 = service1.lower().strip()
        service2 = service2.lower().strip()
        
        # Get compatibility information from our knowledge base
        compatibility_info = _get_service_compatibility(service1, service2)
        
        return json.dumps(compatibility_info, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to check compatibility between {service1} and {service2}: {str(e)}"
        }, indent=2)


# Helper functions

def _get_service_code(service_name: str) -> Optional[str]:
    """Convert a service name to its service code for AWS APIs."""
    # Map of common service names to their service codes
    service_code_map = {
        "ec2": "ec2",
        "s3": "s3",
        "rds": "rds",
        "dynamodb": "dynamodb",
        "lambda": "lambda",
        "apigateway": "apigateway",
        "api gateway": "apigateway",
        "cloudfront": "cloudfront",
        "elasticache": "elasticache",
        "elastic cache": "elasticache",
        "vpc": "vpc",
        "iam": "iam",
        "sns": "sns",
        "sqs": "sqs",
        "cloudwatch": "cloudwatch",
        "cloud watch": "cloudwatch",
        "route53": "route53",
        "route 53": "route53",
        "elb": "elb",
        "elastic load balancing": "elb",
        "elastic load balancer": "elb",
        "ecs": "ecs",
        "eks": "eks",
        "fargate": "fargate",
        "aurora": "aurora",
        "redshift": "redshift",
        "cloudformation": "cloudformation",
        "cloud formation": "cloudformation",
        "kms": "kms",
        "waf": "waf",
        "cognito": "cognito",
        "step functions": "stepfunctions",
        "stepfunctions": "stepfunctions",
        "eventbridge": "eventbridge",
        "event bridge": "eventbridge",
        "kinesis": "kinesis",
        "glue": "glue",
        "athena": "athena",
        "quicksight": "quicksight",
        "quick sight": "quicksight",
        "secrets manager": "secretsmanager",
        "secretsmanager": "secretsmanager",
        "systems manager": "ssm",
        "ssm": "ssm",
        "elastic beanstalk": "elasticbeanstalk",
        "elasticbeanstalk": "elasticbeanstalk",
        "codecommit": "codecommit",
        "codebuild": "codebuild",
        "codepipeline": "codepipeline",
        "codedeploy": "codedeploy",
        "cloudtrail": "cloudtrail",
        "cloud trail": "cloudtrail",
        "config": "config",
        "guardduty": "guardduty",
        "guard duty": "guardduty",
        "direct connect": "directconnect",
        "directconnect": "directconnect",
        "storage gateway": "storagegateway",
        "storagegateway": "storagegateway",
        "backup": "backup",
        "cloudfront": "cloudfront",
        "cloud front": "cloudfront"
    }
    
    return service_code_map.get(service_name.lower())


def _get_service_info_from_knowledge_base(service_name: str, info_type: str) -> Dict[str, Any]:
    """Get service information from our built-in knowledge base."""
    # This is our fallback knowledge base for AWS services
    knowledge_base = {
        "ec2": {
            "general": {
                "name": "Amazon EC2",
                "full_name": "Amazon Elastic Compute Cloud",
                "description": "Secure and resizable compute capacity in the cloud. Launch virtual servers, configure security and networking, and manage storage.",
                "category": "Compute",
                "url": "https://aws.amazon.com/ec2/"
            },
            "features": [
                "Multiple instance types optimized for different workloads",
                "Auto Scaling to adjust capacity based on demand",
                "Elastic Load Balancing for distributing traffic",
                "Integration with VPC for secure networking",
                "Spot Instances for cost savings",
                "Reserved Instances for predictable workloads",
                "Dedicated Hosts for compliance requirements"
            ],
            "use_cases": [
                "Web and application hosting",
                "Development and test environments",
                "High-performance computing (HPC)",
                "Batch processing",
                "Gaming servers",
                "Machine learning and AI workloads",
                "Enterprise applications"
            ],
            "limits": {
                "max_instances_per_region": "Varies by account",
                "max_spot_instance_requests": "Varies by account",
                "max_elastic_ips": "5 per region (default)",
                "max_security_groups_per_instance": "5",
                "max_rules_per_security_group": "60 inbound, 60 outbound"
            },
            "best_practices": [
                "Use security groups to control inbound and outbound traffic",
                "Use IAM roles for EC2 instances instead of storing credentials",
                "Enable detailed monitoring for better visibility",
                "Use instance metadata service for secure access to instance information",
                "Implement proper backup strategies for EC2 instances",
                "Use Auto Scaling groups for high availability and elasticity",
                "Choose the right instance type for your workload"
            ],
            "related_services": ["EBS", "ELB", "Auto Scaling", "VPC", "CloudWatch", "IAM"]
        },
        "s3": {
            "general": {
                "name": "Amazon S3",
                "full_name": "Amazon Simple Storage Service",
                "description": "Object storage built to store and retrieve any amount of data from anywhere. Offers industry-leading scalability, data availability, security, and performance.",
                "category": "Storage",
                "url": "https://aws.amazon.com/s3/"
            },
            "features": [
                "Virtually unlimited scalability",
                "99.999999999% (11 9's) of durability",
                "Multiple storage classes for cost optimization",
                "Lifecycle management",
                "Versioning",
                "Encryption",
                "Access control and permissions",
                "Event notifications",
                "Query-in-place functionality"
            ],
            "use_cases": [
                "Backup and restore",
                "Disaster recovery",
                "Data lakes and big data analytics",
                "Content distribution",
                "Static website hosting",
                "Mobile applications",
                "IoT device data",
                "Software delivery"
            ],
            "limits": {
                "max_buckets_per_account": "100 (default)",
                "max_object_size": "5 TB",
                "max_parts_in_multipart_upload": "10,000"
            },
            "best_practices": [
                "Use bucket policies and IAM policies for access control",
                "Enable versioning for critical data",
                "Use appropriate storage classes based on access patterns",
                "Implement lifecycle policies to manage costs",
                "Use server-side encryption for sensitive data",
                "Enable access logging for audit purposes",
                "Use S3 Transfer Acceleration for faster uploads",
                "Implement proper error handling for S3 operations"
            ],
            "related_services": ["CloudFront", "Glacier", "EBS", "Storage Gateway", "Athena", "Lambda"]
        },
        "rds": {
            "general": {
                "name": "Amazon RDS",
                "full_name": "Amazon Relational Database Service",
                "description": "Set up, operate, and scale a relational database in the cloud with just a few clicks. Automates time-consuming administration tasks like hardware provisioning, database setup, patching, and backups.",
                "category": "Database",
                "url": "https://aws.amazon.com/rds/"
            },
            "features": [
                "Supports multiple database engines (MySQL, PostgreSQL, MariaDB, Oracle, SQL Server, Aurora)",
                "Automated backups and point-in-time recovery",
                "Multi-AZ deployments for high availability",
                "Read replicas for read scaling",
                "Automated patching and maintenance",
                "Monitoring and metrics via CloudWatch",
                "Encryption at rest and in transit"
            ],
            "use_cases": [
                "Web and mobile applications",
                "E-commerce platforms",
                "Enterprise applications",
                "SaaS applications",
                "Gaming applications",
                "Content management systems"
            ],
            "limits": {
                "max_databases_per_instance": "Varies by engine",
                "max_storage": "64 TB for most engines",
                "max_read_replicas": "5 per primary instance"
            },
            "best_practices": [
                "Use Multi-AZ deployments for production workloads",
                "Create read replicas to offload read traffic",
                "Enable automated backups and set appropriate retention periods",
                "Use parameter groups to optimize database settings",
                "Monitor performance with Enhanced Monitoring and Performance Insights",
                "Use IAM database authentication where supported",
                "Implement proper security groups to control access"
            ],
            "related_services": ["Aurora", "DynamoDB", "ElastiCache", "Database Migration Service", "CloudWatch"]
        }
        # More services would be added to the knowledge base
    }
    
    # Normalize service name to handle different formats
    service_name_lower = service_name.lower()
    
    # Try to find the service in our knowledge base
    for key, data in knowledge_base.items():
        if service_name_lower == key or service_name_lower in key or key in service_name_lower:
            # If we found a match, return the requested information
            if info_type == "general":
                return data.get("general", {})
            elif info_type == "features":
                return {"features": data.get("features", [])}
            elif info_type == "use_cases":
                return {"use_cases": data.get("use_cases", [])}
            elif info_type == "limits":
                return {"limits": data.get("limits", {})}
            elif info_type == "best_practices":
                return {"best_practices": data.get("best_practices", [])}
            elif info_type == "related":
                return {"related_services": data.get("related_services", [])}
            else:
                return data
    
    # If service not found, return a message
    return {
        "error": f"Service '{service_name}' not found in knowledge base",
        "available_services": list(knowledge_base.keys())
    }


def _search_service_knowledge_base(keyword: str, category: Optional[str], max_results: int) -> Dict[str, Any]:
    """Search for AWS services in our knowledge base."""
    # This is our fallback search function
    # In a real implementation, this would search a comprehensive database of AWS services
    
    # Sample knowledge base (would be much more comprehensive in production)
    services = [
        {
            "name": "Amazon EC2",
            "description": "Secure and resizable compute capacity in the cloud",
            "category": "Compute",
            "keywords": ["virtual machine", "vm", "server", "compute", "instance"]
        },
        {
            "name": "Amazon S3",
            "description": "Object storage built to store and retrieve any amount of data",
            "category": "Storage",
            "keywords": ["storage", "object", "bucket", "file", "backup"]
        },
        {
            "name": "Amazon RDS",
            "description": "Set up, operate, and scale a relational database in the cloud",
            "category": "Database",
            "keywords": ["database", "sql", "mysql", "postgresql", "oracle", "relational"]
        },
        {
            "name": "Amazon DynamoDB",
            "description": "Fast and flexible NoSQL database service",
            "category": "Database",
            "keywords": ["nosql", "database", "key-value", "document", "serverless"]
        },
        {
            "name": "AWS Lambda",
            "description": "Run code without provisioning or managing servers",
            "category": "Compute",
            "keywords": ["serverless", "function", "event-driven", "code", "faas"]
        },
        {
            "name": "Amazon VPC",
            "description": "Provision a logically isolated section of the AWS Cloud",
            "category": "Networking & Content Delivery",
            "keywords": ["network", "vpc", "subnet", "routing", "security"]
        },
        {
            "name": "Amazon CloudFront",
            "description": "Fast content delivery network (CDN) service",
            "category": "Networking & Content Delivery",
            "keywords": ["cdn", "content delivery", "edge", "caching", "global"]
        },
        {
            "name": "Amazon ECS",
            "description": "Highly secure, reliable, and scalable way to run containers",
            "category": "Containers",
            "keywords": ["container", "docker", "orchestration", "microservice"]
        },
        {
            "name": "Amazon EKS",
            "description": "Managed Kubernetes service",
            "category": "Containers",
            "keywords": ["kubernetes", "k8s", "container", "orchestration"]
        },
        {
            "name": "AWS IAM",
            "description": "Securely manage access to AWS services and resources",
            "category": "Security, Identity, & Compliance",
            "keywords": ["security", "identity", "authentication", "authorization", "permission"]
        }
    ]
    
    # Filter by keyword
    keyword_lower = keyword.lower()
    results = []
    
    for service in services:
        # Check if keyword matches name, description, or keywords
        if (keyword_lower in service["name"].lower() or 
            keyword_lower in service["description"].lower() or 
            any(keyword_lower in kw for kw in service["keywords"])):
            
            # If category is specified, filter by category
            if category and category.lower() != service["category"].lower():
                continue
                
            results.append({
                "name": service["name"],
                "description": service["description"],
                "category": service["category"]
            })
    
    # Limit results
    results = results[:max_results]
    
    return {
        "keyword": keyword,
        "category": category,
        "total_results": len(results),
        "services": results
    }


def _get_technology_mapping(technology: str, use_case: Optional[str], alternatives: bool) -> Dict[str, Any]:
    """Map a technology or concept to equivalent AWS services."""
    # This would be a comprehensive mapping in a real implementation
    # Here's a sample of common mappings
    
    mappings = {
        "mysql": {
            "primary": "Amazon RDS for MySQL",
            "description": "Managed MySQL database service",
            "alternatives": ["Amazon Aurora MySQL", "Amazon RDS MariaDB"],
            "use_cases": {
                "high_performance": "Amazon Aurora MySQL",
                "cost_effective": "Amazon RDS MySQL",
                "migration": "AWS Database Migration Service"
            }
        },
        "postgresql": {
            "primary": "Amazon RDS for PostgreSQL",
            "description": "Managed PostgreSQL database service",
            "alternatives": ["Amazon Aurora PostgreSQL", "Amazon Redshift (for analytics)"],
            "use_cases": {
                "high_performance": "Amazon Aurora PostgreSQL",
                "analytics": "Amazon Redshift",
                "migration": "AWS Database Migration Service"
            }
        },
        "mongodb": {
            "primary": "Amazon DocumentDB",
            "description": "MongoDB-compatible document database service",
            "alternatives": ["Amazon DynamoDB (with document support)"],
            "use_cases": {
                "serverless": "Amazon DynamoDB",
                "migration": "AWS Database Migration Service"
            }
        },
        "redis": {
            "primary": "Amazon ElastiCache for Redis",
            "description": "Managed Redis service for in-memory data store",
            "alternatives": ["Amazon MemoryDB for Redis"],
            "use_cases": {
                "caching": "Amazon ElastiCache for Redis",
                "persistence": "Amazon MemoryDB for Redis"
            }
        },
        "load balancer": {
            "primary": "Elastic Load Balancing",
            "description": "Automatically distributes incoming application traffic",
            "alternatives": ["AWS Global Accelerator"],
            "use_cases": {
                "http": "Application Load Balancer",
                "tcp": "Network Load Balancer",
                "legacy": "Classic Load Balancer",
                "global": "AWS Global Accelerator"
            }
        },
        "message queue": {
            "primary": "Amazon SQS",
            "description": "Fully managed message queuing service",
            "alternatives": ["Amazon MQ", "Amazon MSK (Kafka)"],
            "use_cases": {
                "simple": "Amazon SQS",
                "pub_sub": "Amazon SNS",
                "streaming": "Amazon Kinesis",
                "kafka": "Amazon MSK",
                "rabbitmq": "Amazon MQ"
            }
        },
        "web server": {
            "primary": "Amazon EC2",
            "description": "Virtual servers in the cloud",
            "alternatives": ["AWS Elastic Beanstalk", "Amazon Lightsail", "AWS Amplify"],
            "use_cases": {
                "custom": "Amazon EC2",
                "managed": "AWS Elastic Beanstalk",
                "simple": "Amazon Lightsail",
                "static": "Amazon S3 + CloudFront",
                "serverless": "AWS Lambda + API Gateway"
            }
        },
        "container": {
            "primary": "Amazon ECS",
            "description": "Highly scalable container orchestration service",
            "alternatives": ["Amazon EKS", "AWS Fargate", "AWS App Runner"],
            "use_cases": {
                "docker": "Amazon ECS",
                "kubernetes": "Amazon EKS",
                "serverless": "AWS Fargate",
                "simple": "AWS App Runner"
            }
        },
        "file storage": {
            "primary": "Amazon EFS",
            "description": "Scalable file storage for use with EC2 instances",
            "alternatives": ["Amazon FSx", "Amazon S3"],
            "use_cases": {
                "linux": "Amazon EFS",
                "windows": "Amazon FSx for Windows File Server",
                "lustre": "Amazon FSx for Lustre",
                "object": "Amazon S3"
            }
        },
        "api": {
            "primary": "Amazon API Gateway",
            "description": "Create, publish, maintain, monitor, and secure APIs",
            "alternatives": ["AWS AppSync"],
            "use_cases": {
                "rest": "Amazon API Gateway",
                "graphql": "AWS AppSync",
                "websocket": "Amazon API Gateway WebSocket APIs"
            }
        }
    }
    
    # Try to find the technology in our mappings
    technology_lower = technology.lower()
    
    for key, data in mappings.items():
        if technology_lower == key or technology_lower in key or key in technology_lower:
            result = {
                "technology": technology,
                "primary_service": data["primary"],
                "description": data["description"]
            }
            
            # Add alternatives if requested
            if alternatives:
                result["alternatives"] = data["alternatives"]
            
            # Add use case specific mapping if provided
            if use_case and "use_cases" in data:
                for case_key, case_value in data["use_cases"].items():
                    if use_case in case_key or case_key in use_case:
                        result["recommended_for_use_case"] = case_value
                        break
            
            return result
    
    # If technology not found, return a message
    return {
        "error": f"Technology '{technology}' not found in mapping database",
        "suggestion": "Try a more general term or a specific AWS service name"
    }


def _get_architecture_pattern(pattern_name: str, details: bool) -> Dict[str, Any]:
    """Get information about common AWS architecture patterns."""
    # This would be a comprehensive database of architecture patterns in a real implementation
    
    patterns = {
        "three-tier": {
            "name": "Three-Tier Architecture",
            "description": "A traditional architecture pattern that separates an application into three logical tiers: presentation, application, and data.",
            "components": ["Web tier", "Application tier", "Database tier"],
            "aws_services": {
                "web_tier": ["Elastic Load Balancing", "Amazon EC2", "Auto Scaling", "Amazon CloudFront"],
                "application_tier": ["Amazon EC2", "Auto Scaling", "AWS Elastic Beanstalk", "AWS Lambda"],
                "database_tier": ["Amazon RDS", "Amazon ElastiCache", "Amazon DynamoDB"]
            },
            "benefits": [
                "Separation of concerns",
                "Independent scaling of tiers",
                "Improved security through isolation",
                "Easier maintenance and updates"
            ],
            "use_cases": [
                "Traditional web applications",
                "Enterprise applications",
                "E-commerce platforms"
            ],
            "implementation_details": {
                "networking": "Use Amazon VPC with public and private subnets. Place web tier in public subnets, application and database tiers in private subnets.",
                "security": "Use security groups to control traffic between tiers. Only allow necessary communication paths.",
                "high_availability": "Deploy resources across multiple Availability Zones. Use Auto Scaling for web and application tiers. Use Multi-AZ deployments for databases.",
                "scaling": "Configure Auto Scaling based on CPU utilization, request count, or custom metrics."
            },
            "diagram_description": "Web tier with ELB and EC2 instances in public subnets, application tier with EC2 instances in private subnets, and database tier with RDS in isolated private subnets."
        },
        "microservices": {
            "name": "Microservices Architecture",
            "description": "An architectural style that structures an application as a collection of small, loosely coupled services that can be developed, deployed, and scaled independently.",
            "components": ["API Gateway", "Microservices", "Service Discovery", "Data Stores", "Event Bus"],
            "aws_services": {
                "api_layer": ["Amazon API Gateway", "AWS AppSync"],
                "compute": ["Amazon ECS", "Amazon EKS", "AWS Fargate", "AWS Lambda"],
                "service_discovery": ["AWS Cloud Map", "Amazon Route 53", "AWS App Mesh"],
                "data_stores": ["Amazon DynamoDB", "Amazon RDS", "Amazon ElastiCache", "Amazon S3"],
                "messaging": ["Amazon SNS", "Amazon SQS", "Amazon EventBridge", "Amazon MSK"]
            },
            "benefits": [
                "Independent development and deployment",
                "Technology diversity",
                "Resilience",
                "Scalability",
                "Organizational alignment"
            ],
            "use_cases": [
                "Complex applications with multiple teams",
                "Applications requiring frequent updates",
                "Systems with varying scalability requirements"
            ],
            "implementation_details": {
                "service_boundaries": "Define service boundaries based on business capabilities. Each service should own its data and expose APIs.",
                "communication": "Use synchronous (API) and asynchronous (events) communication patterns as appropriate.",
                "deployment": "Use containers with ECS/EKS or serverless with Lambda. Implement CI/CD pipelines for each service.",
                "monitoring": "Implement distributed tracing with AWS X-Ray. Use CloudWatch for metrics and logs.",
                "data_management": "Each service should own its data. Use appropriate database technology for each service's needs."
            },
            "diagram_description": "API Gateway routing to multiple containerized microservices running on ECS/EKS, each with its own database, communicating through SQS/SNS message queues."
        },
        "serverless": {
            "name": "Serverless Architecture",
            "description": "An architecture pattern where applications are built without managing servers, focusing on functions that respond to events and using managed services for all infrastructure needs.",
            "components": ["API Gateway", "Functions", "Event Sources", "Managed Services"],
            "aws_services": {
                "compute": ["AWS Lambda"],
                "api_layer": ["Amazon API Gateway", "AWS AppSync"],
                "data_stores": ["Amazon DynamoDB", "Amazon S3", "Amazon Aurora Serverless"],
                "event_sources": ["Amazon EventBridge", "Amazon SNS", "Amazon SQS", "Amazon Kinesis"],
                "orchestration": ["AWS Step Functions"],
                "monitoring": ["AWS CloudWatch", "AWS X-Ray"]
            },
            "benefits": [
                "No server management",
                "Pay-per-use pricing",
                "Built-in high availability and fault tolerance",
                "Automatic scaling",
                "Faster time to market"
            ],
            "use_cases": [
                "Web and mobile backends",
                "Data processing",
                "IoT backends",
                "Chatbots and virtual assistants",
                "Scheduled tasks"
            ],
            "implementation_details": {
                "function_design": "Design functions to be stateless and idempotent. Keep functions focused on a single responsibility.",
                "cold_starts": "Optimize for cold starts by minimizing dependencies and function size. Use provisioned concurrency for latency-sensitive applications.",
                "state_management": "Store state in managed services like DynamoDB or S3. Use Step Functions for complex workflows.",
                "security": "Use IAM roles with least privilege. Implement fine-grained access control.",
                "monitoring": "Set up CloudWatch alarms for errors and performance issues. Use X-Ray for tracing."
            },
            "diagram_description": "API Gateway connected to Lambda functions that process events and interact with DynamoDB tables and S3 buckets, with EventBridge coordinating event-driven processes."
        }
        # More patterns would be added in a real implementation
    }
    
    # Try to find the pattern in our database
    pattern_lower = pattern_name.lower()
    
    for key, data in patterns.items():
        if pattern_lower == key or pattern_lower in key or key in pattern_lower:
            result = {
                "name": data["name"],
                "description": data["description"],
                "components": data["components"],
                "aws_services": data["aws_services"],
                "benefits": data["benefits"],
                "use_cases": data["use_cases"],
                "diagram_description": data["diagram_description"]
            }
            
            # Add implementation details if requested
            if details:
                result["implementation_details"] = data["implementation_details"]
            
            return result
    
    # If pattern not found, return a message
    return {
        "error": f"Architecture pattern '{pattern_name}' not found",
        "available_patterns": list(patterns.keys()),
        "suggestion": "Try one of the common patterns: three-tier, microservices, serverless"
    }


def _get_service_compatibility(service1: str, service2: str) -> Dict[str, Any]:
    """Check compatibility between two AWS services."""
    # This would be a comprehensive compatibility database in a real implementation
    
    # Normalize service names
    service1 = service1.lower()
    service2 = service2.lower()
    
    # Sort services alphabetically to ensure consistent lookups
    if service1 > service2:
        service1, service2 = service2, service1
    
    # Sample compatibility database
    compatibility_db = {
        ("ec2", "rds"): {
            "compatible": True,
            "integration_method": "Network connection via security groups",
            "notes": "EC2 instances can connect to RDS databases using security groups to control access",
            "best_practices": [
                "Place RDS in private subnet",
                "Use security groups to restrict access",
                "Use IAM database authentication where supported"
            ]
        },
        ("ec2", "s3"): {
            "compatible": True,
            "integration_method": "S3 API, VPC Endpoints",
            "notes": "EC2 instances can access S3 via the public API or through VPC Endpoints for improved security and performance",
            "best_practices": [
                "Use IAM roles for EC2 to access S3",
                "Consider S3 VPC Endpoints to keep traffic within AWS network",
                "Use S3 Transfer Acceleration for faster uploads from distant locations"
            ]
        },
        ("lambda", "rds"): {
            "compatible": True,
            "integration_method": "Direct connection",
            "notes": "Lambda can connect to RDS but requires additional configuration due to Lambda's stateless nature",
            "best_practices": [
                "Place Lambda in the same VPC as RDS",
                "Use connection pooling to manage database connections",
                "Consider RDS Proxy to handle connection management",
                "Be aware of Lambda cold start impact on database connections"
            ]
        },
        ("lambda", "dynamodb"): {
            "compatible": True,
            "integration_method": "AWS SDK, Direct API calls",
            "notes": "Lambda integrates natively with DynamoDB for serverless applications",
            "best_practices": [
                "Use IAM roles to grant Lambda access to DynamoDB",
                "Consider DynamoDB Streams for event-driven architectures",
                "Use DynamoDB DAX for caching frequently accessed items"
            ]
        },
        ("s3", "cloudfront"): {
            "compatible": True,
            "integration_method": "Origin configuration",
            "notes": "CloudFront can use S3 buckets as origins for content delivery",
            "best_practices": [
                "Use Origin Access Identity (OAI) to restrict S3 access to CloudFront",
                "Enable CloudFront compression for text-based content",
                "Configure appropriate cache behaviors based on content type"
            ]
        }
        # More compatibility information would be added in a real implementation
    }
    
    # Check if we have compatibility information for these services
    for (s1, s2), data in compatibility_db.items():
        if (service1 in s1 and service2 in s2) or (service1 in s2 and service2 in s1):
            return {
                "service1": service1,
                "service2": service2,
                "compatible": data["compatible"],
                "integration_method": data["integration_method"],
                "notes": data["notes"],
                "best_practices": data["best_practices"]
            }
    
    # If no specific compatibility information, return a generic response
    return {
        "service1": service1,
        "service2": service2,
        "compatible": "Unknown",
        "notes": "No specific compatibility information available for these services. Most AWS services can work together through various integration patterns.",
        "suggestion": "Check AWS documentation for integration options between these services."
    }


def _get_related_services(service_name: str) -> List[Dict[str, str]]:
    """Get related AWS services for a given service."""
    # This would be a comprehensive database of service relationships in a real implementation
    
    # Sample related services database
    related_services_db = {
        "ec2": [
            {"name": "Amazon EBS", "relationship": "Storage for EC2 instances"},
            {"name": "Elastic Load Balancing", "relationship": "Distributes traffic to EC2 instances"},
            {"name": "Auto Scaling", "relationship": "Automatically adjusts EC2 capacity"},
            {"name": "Amazon VPC", "relationship": "Networking environment for EC2 instances"},
            {"name": "AWS Systems Manager", "relationship": "Manages EC2 instances"}
        ],
        "s3": [
            {"name": "Amazon CloudFront", "relationship": "Content delivery network for S3 content"},
            {"name": "AWS Lambda", "relationship": "Process S3 events"},
            {"name": "Amazon Athena", "relationship": "Query data in S3 using SQL"},
            {"name": "AWS Glue", "relationship": "ETL service for data in S3"},
            {"name": "Amazon Glacier", "relationship": "Long-term archival storage for S3 objects"}
        ],
        "rds": [
            {"name": "Amazon Aurora", "relationship": "MySQL and PostgreSQL compatible database built for the cloud"},
            {"name": "AWS Database Migration Service", "relationship": "Migrate databases to RDS"},
            {"name": "Amazon ElastiCache", "relationship": "In-memory cache to improve database performance"},
            {"name": "AWS Backup", "relationship": "Centralized backup service for RDS"},
            {"name": "Amazon CloudWatch", "relationship": "Monitoring and observability for RDS"}
        ],
        "lambda": [
            {"name": "Amazon API Gateway", "relationship": "Create APIs that trigger Lambda functions"},
            {"name": "Amazon EventBridge", "relationship": "Invoke Lambda functions based on events"},
            {"name": "AWS Step Functions", "relationship": "Orchestrate Lambda functions"},
            {"name": "Amazon DynamoDB", "relationship": "Serverless database commonly used with Lambda"},
            {"name": "Amazon S3", "relationship": "Trigger Lambda functions on S3 events"}
        ]
        # More services would be added in a real implementation
    }
    
    # Normalize service name
    service_name_lower = service_name.lower()
    
    # Try to find related services
    for key, related in related_services_db.items():
        if service_name_lower == key or service_name_lower in key or key in service_name_lower:
            return related
    
    # If no related services found, return empty list
    return []


def _get_best_practices(service_name: str) -> List[str]:
    """Get best practices for a given AWS service."""
    # This would be a comprehensive database of best practices in a real implementation
    
    # Sample best practices database
    best_practices_db = {
        "ec2": [
            "Use security groups to control inbound and outbound traffic",
            "Use IAM roles for EC2 instances instead of storing credentials",
            "Enable detailed monitoring for better visibility",
            "Use instance metadata service for secure access to instance information",
            "Implement proper backup strategies for EC2 instances",
            "Use Auto Scaling groups for high availability and elasticity",
            "Choose the right instance type for your workload",
            "Use Spot Instances for fault-tolerant, flexible workloads to save costs",
            "Use Reserved Instances for predictable workloads to save costs",
            "Implement a tagging strategy for better resource management"
        ],
        "s3": [
            "Use bucket policies and IAM policies for access control",
            "Enable versioning for critical data",
            "Use appropriate storage classes based on access patterns",
            "Implement lifecycle policies to manage costs",
            "Use server-side encryption for sensitive data",
            "Enable access logging for audit purposes",
            "Use S3 Transfer Acceleration for faster uploads",
            "Implement proper error handling for S3 operations",
            "Use presigned URLs for temporary access to private objects",
            "Configure CORS when using S3 with web applications"
        ],
        "rds": [
            "Use Multi-AZ deployments for production workloads",
            "Create read replicas to offload read traffic",
            "Enable automated backups and set appropriate retention periods",
            "Use parameter groups to optimize database settings",
            "Monitor performance with Enhanced Monitoring and Performance Insights",
            "Use IAM database authentication where supported",
            "Implement proper security groups to control access",
            "Use encryption at rest for sensitive data",
            "Schedule maintenance windows during low-traffic periods",
            "Use RDS Proxy for connection pooling"
        ],
        "lambda": [
            "Keep functions focused on a single responsibility",
            "Minimize the deployment package size",
            "Reuse execution context to improve performance",
            "Set appropriate memory allocation",
            "Use environment variables for configuration",
            "Implement proper error handling and retries",
            "Use AWS X-Ray for tracing and debugging",
            "Set function timeout based on expected execution time",
            "Use provisioned concurrency for latency-sensitive applications",
            "Implement dead-letter queues for failed executions"
        ]
        # More services would be added in a real implementation
    }
    
    # Normalize service name
    service_name_lower = service_name.lower()
    
    # Try to find best practices
    for key, practices in best_practices_db.items():
        if service_name_lower == key or service_name_lower in key or key in service_name_lower:
            return practices
    
    # If no best practices found, return generic best practices
    return [
        "Follow the principle of least privilege for IAM permissions",
        "Enable AWS CloudTrail for auditing API calls",
        "Use AWS Config for resource configuration monitoring",
        "Implement tagging for resource organization and cost tracking",
        "Enable encryption for data at rest and in transit",
        "Set up CloudWatch alarms for monitoring",
        "Follow AWS Well-Architected Framework principles",
        "Regularly review and update security policies",
        "Implement automated backups and disaster recovery",
        "Use Infrastructure as Code for consistent deployments"
    ]