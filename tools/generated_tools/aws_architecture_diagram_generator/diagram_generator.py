from typing import List, Dict, Any, Optional, Tuple, Union
import json
import os
import base64
import re
import logging
from io import BytesIO
import xml.etree.ElementTree as ET
import xml.dom.minidom
import math
import hashlib
from datetime import datetime

from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for AWS service icons and styles
AWS_ICON_MAP = {
    "EC2": "Compute/Amazon-EC2",
    "S3": "Storage/Amazon-S3",
    "RDS": "Database/Amazon-RDS",
    "Lambda": "Compute/AWS-Lambda",
    "DynamoDB": "Database/Amazon-DynamoDB",
    "ELB": "Networking-Content-Delivery/Elastic-Load-Balancing",
    "CloudFront": "Networking-Content-Delivery/Amazon-CloudFront",
    "Route53": "Networking-Content-Delivery/Amazon-Route-53",
    "VPC": "Networking-Content-Delivery/Amazon-VPC",
    "IAM": "Security-Identity-Compliance/AWS-Identity-and-Access-Management",
    "CloudWatch": "Management-Governance/Amazon-CloudWatch",
    "SNS": "Application-Integration/Amazon-SNS",
    "SQS": "Application-Integration/Amazon-SQS",
    "API Gateway": "Networking-Content-Delivery/Amazon-API-Gateway",
    "Cognito": "Security-Identity-Compliance/Amazon-Cognito",
    "ElastiCache": "Database/Amazon-ElastiCache",
    "CloudFormation": "Management-Governance/AWS-CloudFormation",
    "ECS": "Compute/Amazon-ECS",
    "EKS": "Compute/Amazon-EKS",
    "Fargate": "Compute/AWS-Fargate",
    "Aurora": "Database/Amazon-Aurora",
    "Redshift": "Database/Amazon-Redshift",
    "Elasticsearch": "Analytics/Amazon-Elasticsearch-Service",
    "Kinesis": "Analytics/Amazon-Kinesis",
    "Glue": "Analytics/AWS-Glue",
    "Athena": "Analytics/Amazon-Athena",
    "Step Functions": "Application-Integration/AWS-Step-Functions",
    "EventBridge": "Application-Integration/Amazon-EventBridge",
    "CodePipeline": "Developer-Tools/AWS-CodePipeline",
    "CodeBuild": "Developer-Tools/AWS-CodeBuild",
    "CodeDeploy": "Developer-Tools/AWS-CodeDeploy",
    "WAF": "Security-Identity-Compliance/AWS-WAF",
    "Shield": "Security-Identity-Compliance/AWS-Shield",
    "Secrets Manager": "Security-Identity-Compliance/AWS-Secrets-Manager",
    "KMS": "Security-Identity-Compliance/AWS-Key-Management-Service",
    "CloudTrail": "Management-Governance/AWS-CloudTrail",
    "Config": "Management-Governance/AWS-Config",
    "Systems Manager": "Management-Governance/AWS-Systems-Manager",
    "Organizations": "Management-Governance/AWS-Organizations",
    "Trusted Advisor": "Management-Governance/AWS-Trusted-Advisor",
    "GuardDuty": "Security-Identity-Compliance/Amazon-GuardDuty",
    "Inspector": "Security-Identity-Compliance/Amazon-Inspector",
    "Macie": "Security-Identity-Compliance/Amazon-Macie",
    "Certificate Manager": "Security-Identity-Compliance/AWS-Certificate-Manager",
    "CloudHSM": "Security-Identity-Compliance/AWS-CloudHSM",
    "Directory Service": "Security-Identity-Compliance/AWS-Directory-Service",
    "Single Sign-On": "Security-Identity-Compliance/AWS-Single-Sign-On",
    "AppSync": "Application-Integration/AWS-AppSync",
    "MQ": "Application-Integration/Amazon-MQ",
    "SWF": "Application-Integration/Amazon-SWF",
    "Batch": "Compute/AWS-Batch",
    "Elastic Beanstalk": "Compute/AWS-Elastic-Beanstalk",
    "Lightsail": "Compute/Amazon-Lightsail",
    "Outposts": "Compute/AWS-Outposts",
    "Serverless Application Repository": "Compute/AWS-Serverless-Application-Repository",
    "DocumentDB": "Database/Amazon-DocumentDB",
    "Neptune": "Database/Amazon-Neptune",
    "QLDB": "Database/Amazon-QLDB",
    "Timestream": "Database/Amazon-Timestream",
    "AppFlow": "Application-Integration/Amazon-AppFlow",
    "EMR": "Analytics/Amazon-EMR",
    "MSK": "Analytics/Amazon-MSK",
    "QuickSight": "Analytics/Amazon-QuickSight",
    "Data Pipeline": "Analytics/AWS-Data-Pipeline",
    "Lake Formation": "Analytics/AWS-Lake-Formation",
    "Amplify": "Mobile/AWS-Amplify",
    "AppStream 2.0": "End-User-Computing/Amazon-AppStream-2",
    "WorkSpaces": "End-User-Computing/Amazon-WorkSpaces",
    "IoT Core": "Internet-of-Things/AWS-IoT-Core",
    "IoT Analytics": "Internet-of-Things/AWS-IoT-Analytics",
    "IoT Events": "Internet-of-Things/AWS-IoT-Events",
    "IoT Greengrass": "Internet-of-Things/AWS-IoT-Greengrass",
    "IoT SiteWise": "Internet-of-Things/AWS-IoT-SiteWise",
    "IoT Things Graph": "Internet-of-Things/AWS-IoT-Things-Graph",
    "Storage Gateway": "Storage/AWS-Storage-Gateway",
    "EFS": "Storage/Amazon-EFS",
    "FSx": "Storage/Amazon-FSx",
    "Backup": "Storage/AWS-Backup",
    "Snowball": "Storage/AWS-Snowball",
    "Transfer Family": "Storage/AWS-Transfer-Family",
    "Global Accelerator": "Networking-Content-Delivery/AWS-Global-Accelerator",
    "Transit Gateway": "Networking-Content-Delivery/AWS-Transit-Gateway",
    "Direct Connect": "Networking-Content-Delivery/AWS-Direct-Connect",
    "App Mesh": "Networking-Content-Delivery/AWS-App-Mesh",
    "Cloud9": "Developer-Tools/AWS-Cloud9",
    "CodeStar": "Developer-Tools/AWS-CodeStar",
    "X-Ray": "Developer-Tools/AWS-X-Ray",
    "Cost Explorer": "Cloud-Financial-Management/AWS-Cost-Explorer",
    "Budgets": "Cloud-Financial-Management/AWS-Budgets",
    "Comprehend": "Machine-Learning/Amazon-Comprehend",
    "Forecast": "Machine-Learning/Amazon-Forecast",
    "Fraud Detector": "Machine-Learning/Amazon-Fraud-Detector",
    "Kendra": "Machine-Learning/Amazon-Kendra",
    "Lex": "Machine-Learning/Amazon-Lex",
    "Personalize": "Machine-Learning/Amazon-Personalize",
    "Polly": "Machine-Learning/Amazon-Polly",
    "Rekognition": "Machine-Learning/Amazon-Rekognition",
    "SageMaker": "Machine-Learning/Amazon-SageMaker",
    "Textract": "Machine-Learning/Amazon-Textract",
    "Transcribe": "Machine-Learning/Amazon-Transcribe",
    "Translate": "Machine-Learning/Amazon-Translate",
    "Connect": "Customer-Engagement/Amazon-Connect",
    "Pinpoint": "Customer-Engagement/Amazon-Pinpoint",
    "Simple Email Service": "Customer-Engagement/Amazon-Simple-Email-Service",
    "WorkDocs": "Business-Applications/Amazon-WorkDocs",
    "WorkMail": "Business-Applications/Amazon-WorkMail",
    "Chime": "Business-Applications/Amazon-Chime",
    "Managed Blockchain": "Blockchain/Amazon-Managed-Blockchain",
    "Ground Station": "Satellite/AWS-Ground-Station",
    "Outposts": "Hybrid/AWS-Outposts",
    "Wavelength": "Hybrid/AWS-Wavelength",
    "Snow Family": "Hybrid/AWS-Snow-Family",
    "Local Zones": "Hybrid/AWS-Local-Zones",
    "RoboMaker": "Robotics/AWS-RoboMaker",
    "Braket": "Quantum-Technologies/Amazon-Braket",
    "GameLift": "Game-Development/Amazon-GameLift",
    "OpenSearch": "Analytics/Amazon-OpenSearch-Service",
    "CloudFront": "Networking-Content-Delivery/Amazon-CloudFront",
    "Internet Gateway": "Networking-Content-Delivery/Amazon-VPC_Internet-Gateway",
    "NAT Gateway": "Networking-Content-Delivery/Amazon-VPC_NAT-Gateway",
    "Subnet": "Networking-Content-Delivery/Amazon-VPC_Subnet",
    "Security Group": "Networking-Content-Delivery/Amazon-VPC_Security-Group",
    "Route Table": "Networking-Content-Delivery/Amazon-VPC_Route-Table",
    "Elastic IP": "Networking-Content-Delivery/Amazon-VPC_Elastic-Network-Interface",
    "ALB": "Networking-Content-Delivery/Elastic-Load-Balancing_Application-Load-Balancer",
    "NLB": "Networking-Content-Delivery/Elastic-Load-Balancing_Network-Load-Balancer",
    "Gateway Load Balancer": "Networking-Content-Delivery/Elastic-Load-Balancing_Gateway-Load-Balancer",
    "Classic Load Balancer": "Networking-Content-Delivery/Elastic-Load-Balancing_Classic-Load-Balancer",
    "Auto Scaling": "Management-Governance/AWS-Auto-Scaling",
    "EC2 Auto Scaling": "Management-Governance/Amazon-EC2-Auto-Scaling"
}

# Default colors for Mermaid diagrams
MERMAID_COLORS = {
    "vpc": "#E8F4FA",
    "subnet": "#F7F7F7",
    "edge": "#666666",
    "node": "#FF9900",
    "text": "#333333",
    "title": "#000000"
}

# Cache directory for storing service information
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "aws_architect")
os.makedirs(CACHE_DIR, exist_ok=True)

def get_service_cache_path(service_name: str) -> str:
    """Get the cache file path for a service."""
    sanitized_name = re.sub(r'[^\w\-]', '_', service_name.lower())
    return os.path.join(CACHE_DIR, f"{sanitized_name}_info.json")

def cache_service_info(service_name: str, info: Dict[str, Any]) -> None:
    """Cache service information to a file."""
    cache_path = get_service_cache_path(service_name)
    with open(cache_path, 'w') as f:
        json.dump(info, f)

def get_cached_service_info(service_name: str) -> Optional[Dict[str, Any]]:
    """Get cached service information if available."""
    cache_path = get_service_cache_path(service_name)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached service info for {service_name}: {e}")
    return None

@tool
def query_aws_service_info(service_name: str, region: str = "us-east-1") -> str:
    """Query AWS service information including description, features, and limitations.

    Args:
        service_name (str): AWS service name (e.g., EC2, S3, RDS)
        region (str): AWS region name (default: us-east-1)
        
    Returns:
        str: JSON string containing service information
    """
    # Normalize service name
    service_name = service_name.strip()
    
    # Check cache first
    cached_info = get_cached_service_info(service_name)
    if cached_info:
        logger.info(f"Using cached information for {service_name}")
        return json.dumps(cached_info)
    
    # Service information dictionary
    # This is a comprehensive database of AWS services with descriptions, features, and use cases
    # In a real implementation, this would be fetched from AWS Service Catalog API
    aws_services = {
        "EC2": {
            "name": "Amazon Elastic Compute Cloud (EC2)",
            "description": "Amazon EC2 is a web service that provides secure, resizable compute capacity in the cloud. It is designed to make web-scale cloud computing easier for developers.",
            "features": [
                "Elastic computing with various instance types",
                "Multiple purchasing options (On-Demand, Reserved, Spot)",
                "Amazon Machine Images (AMIs) for quick deployment",
                "Integration with VPC for secure networking",
                "Auto Scaling capabilities",
                "Load balancing support"
            ],
            "use_cases": [
                "Web and application hosting",
                "Development and test environments",
                "High-performance computing",
                "Batch processing",
                "Gaming servers",
                "Machine learning applications"
            ],
            "limitations": [
                "Instance quotas per region",
                "Some instance types not available in all regions",
                "Requires management of OS patches and updates"
            ],
            "service_type": "Compute",
            "pricing_model": "Pay-as-you-go based on instance type, region, and usage time"
        },
        "S3": {
            "name": "Amazon Simple Storage Service (S3)",
            "description": "Amazon S3 is an object storage service offering industry-leading scalability, data availability, security, and performance.",
            "features": [
                "Virtually unlimited storage capacity",
                "Multiple storage classes (Standard, Intelligent-Tiering, Glacier, etc.)",
                "Versioning and lifecycle policies",
                "Fine-grained access controls",
                "Server-side encryption options",
                "Event notifications"
            ],
            "use_cases": [
                "Data backup and archiving",
                "Content distribution",
                "Data lakes for analytics",
                "Static website hosting",
                "Application data storage",
                "Disaster recovery"
            ],
            "limitations": [
                "Individual objects limited to 5TB",
                "Request rate limits (can be increased)",
                "Eventual consistency for overwrite PUTS and DELETES"
            ],
            "service_type": "Storage",
            "pricing_model": "Pay for storage used, requests made, and data transferred"
        },
        "RDS": {
            "name": "Amazon Relational Database Service (RDS)",
            "description": "Amazon RDS makes it easy to set up, operate, and scale a relational database in the cloud. It provides cost-efficient and resizable capacity while automating time-consuming administration tasks.",
            "features": [
                "Supports multiple database engines (MySQL, PostgreSQL, Oracle, SQL Server, MariaDB, Aurora)",
                "Automated backups and patching",
                "Multi-AZ deployments for high availability",
                "Read replicas for improved read performance",
                "Encryption at rest and in transit",
                "Monitoring and metrics via CloudWatch"
            ],
            "use_cases": [
                "Web and mobile applications",
                "E-commerce platforms",
                "Enterprise applications",
                "SaaS applications",
                "Gaming applications",
                "Content management systems"
            ],
            "limitations": [
                "Maximum database size varies by engine",
                "Some advanced database features may not be supported",
                "Limited direct access to underlying OS"
            ],
            "service_type": "Database",
            "pricing_model": "Pay for instance hours, storage, I/O, and backup storage"
        },
        "Lambda": {
            "name": "AWS Lambda",
            "description": "AWS Lambda is a serverless compute service that runs your code in response to events and automatically manages the underlying compute resources.",
            "features": [
                "Serverless architecture (no server management)",
                "Automatic scaling",
                "Support for multiple programming languages",
                "Event-driven execution model",
                "Integration with other AWS services",
                "Pay-per-use pricing"
            ],
            "use_cases": [
                "Real-time file processing",
                "Data transformation",
                "Backend APIs",
                "IoT backends",
                "Stream processing",
                "Scheduled tasks"
            ],
            "limitations": [
                "Maximum execution duration of 15 minutes",
                "Memory allocation from 128MB to 10GB",
                "Temporary disk space limited to 512MB",
                "Cold start latency for infrequently used functions"
            ],
            "service_type": "Compute",
            "pricing_model": "Pay for number of requests and compute time"
        },
        "DynamoDB": {
            "name": "Amazon DynamoDB",
            "description": "Amazon DynamoDB is a fully managed NoSQL database service that provides fast and predictable performance with seamless scalability.",
            "features": [
                "Fully managed NoSQL database",
                "Single-digit millisecond latency",
                "Automatic scaling of throughput capacity",
                "Built-in security and backup",
                "Global tables for multi-region deployment",
                "Transactions support"
            ],
            "use_cases": [
                "Web and mobile applications",
                "Gaming applications",
                "IoT device data management",
                "Ad tech and marketing tech",
                "Real-time big data",
                "Microservices data store"
            ],
            "limitations": [
                "Item size limit of 400KB",
                "Limited query flexibility compared to SQL",
                "Read/write capacity planning required for provisioned mode"
            ],
            "service_type": "Database",
            "pricing_model": "Pay for read/write throughput and storage"
        },
        "VPC": {
            "name": "Amazon Virtual Private Cloud (VPC)",
            "description": "Amazon VPC lets you provision a logically isolated section of the AWS Cloud where you can launch AWS resources in a virtual network that you define.",
            "features": [
                "Custom IP address ranges",
                "Subnets and route tables",
                "Security groups and network ACLs",
                "Internet and NAT gateways",
                "VPN and Direct Connect integration",
                "Flow logs for network monitoring"
            ],
            "use_cases": [
                "Secure hosting of multi-tier applications",
                "Extending corporate networks to the cloud",
                "Disaster recovery environments",
                "Isolated development and testing environments",
                "Regulated workloads with specific networking requirements",
                "Hybrid cloud architectures"
            ],
            "limitations": [
                "Maximum of 5 VPCs per region by default (can be increased)",
                "Maximum of 200 subnets per VPC",
                "CIDR block size between /16 and /28"
            ],
            "service_type": "Networking",
            "pricing_model": "No additional charge for VPC itself; pay for resources used within VPC and data transfer"
        },
        "CloudFront": {
            "name": "Amazon CloudFront",
            "description": "Amazon CloudFront is a fast content delivery network (CDN) service that securely delivers data, videos, applications, and APIs to customers globally with low latency and high transfer speeds.",
            "features": [
                "Global network of edge locations",
                "Integration with AWS Shield for DDoS protection",
                "HTTPS support with custom SSL certificates",
                "Real-time metrics and logging",
                "Field-level encryption",
                "Origin failover capabilities"
            ],
            "use_cases": [
                "Static and dynamic content delivery",
                "Video streaming",
                "Software distribution",
                "API acceleration",
                "Website security",
                "Game distribution"
            ],
            "limitations": [
                "Cache invalidation can take time to propagate",
                "Some advanced features require specific request routing",
                "Regional edge caches have different behaviors than edge locations"
            ],
            "service_type": "Content Delivery",
            "pricing_model": "Pay for data transfer and requests"
        },
        "Route53": {
            "name": "Amazon Route 53",
            "description": "Amazon Route 53 is a highly available and scalable cloud Domain Name System (DNS) web service.",
            "features": [
                "Domain registration",
                "DNS routing with various routing policies",
                "Health checking of resources",
                "Traffic flow visual editor",
                "Private DNS for VPCs",
                "DNSSEC support"
            ],
            "use_cases": [
                "Domain management",
                "Global DNS resolution",
                "Traffic management and failover",
                "Latency-based routing",
                "Geolocation routing",
                "Weighted round-robin"
            ],
            "limitations": [
                "Maximum of 10,000 hosted zones per account (can be increased)",
                "Maximum of 100 domains per domain registration (can be increased)",
                "DNS propagation delays due to TTL"
            ],
            "service_type": "Networking",
            "pricing_model": "Pay for hosted zones, queries, health checks, and domain registrations"
        }
    }
    
    # Try to get service information
    service_info = {}
    service_key = service_name
    
    # Handle common aliases and case variations
    service_name_upper = service_name.upper()
    if service_name_upper == "EC2":
        service_key = "EC2"
    elif service_name_upper in ["S3", "SIMPLE STORAGE SERVICE"]:
        service_key = "S3"
    elif service_name_upper in ["RDS", "RELATIONAL DATABASE SERVICE"]:
        service_key = "RDS"
    elif service_name_upper == "DYNAMODB":
        service_key = "DynamoDB"
    elif service_name_upper in ["VPC", "VIRTUAL PRIVATE CLOUD"]:
        service_key = "VPC"
    elif service_name_upper in ["CLOUDFRONT", "CLOUD FRONT"]:
        service_key = "CloudFront"
    elif service_name_upper in ["ROUTE53", "ROUTE 53"]:
        service_key = "Route53"
    elif service_name_upper == "LAMBDA":
        service_key = "Lambda"
    
    # Get service info from our database
    if service_key in aws_services:
        service_info = aws_services[service_key]
    else:
        # If not in our database, provide a generic response
        service_info = {
            "name": f"AWS {service_name}",
            "description": f"Information for {service_name} is not available in the local database.",
            "features": ["Please refer to AWS documentation for details."],
            "use_cases": ["Please refer to AWS documentation for details."],
            "limitations": ["Information not available."],
            "service_type": "Unknown",
            "pricing_model": "Please refer to AWS pricing documentation."
        }
    
    # Add region information
    service_info["region"] = region
    
    # Cache the result
    cache_service_info(service_name, service_info)
    
    return json.dumps(service_info)

@tool
def map_tech_stack_to_aws(tech_stack: List[str], include_alternatives: bool = True) -> str:
    """Map traditional IT technology stack components to corresponding AWS services.

    Args:
        tech_stack (List[str]): List of traditional IT components or technologies
        include_alternatives (bool): Whether to include alternative AWS services
        
    Returns:
        str: JSON string containing the mapping results
    """
    if not tech_stack or not isinstance(tech_stack, list):
        return json.dumps({
            "status": "error",
            "message": "Invalid input: tech_stack must be a non-empty list of strings",
            "mappings": []
        })
    
    # Technology stack to AWS service mapping
    tech_to_aws = {
        # Compute
        "virtual machine": {
            "primary": "EC2",
            "description": "Amazon EC2 provides virtual servers in the cloud",
            "alternatives": ["Lightsail", "App Runner", "Elastic Beanstalk"]
        },
        "vm": {
            "primary": "EC2",
            "description": "Amazon EC2 provides virtual servers in the cloud",
            "alternatives": ["Lightsail", "App Runner", "Elastic Beanstalk"]
        },
        "server": {
            "primary": "EC2",
            "description": "Amazon EC2 provides virtual servers in the cloud",
            "alternatives": ["Lightsail", "App Runner", "Elastic Beanstalk"]
        },
        "container": {
            "primary": "ECS",
            "description": "Amazon ECS is a fully managed container orchestration service",
            "alternatives": ["EKS", "Fargate", "App Runner"]
        },
        "docker": {
            "primary": "ECS",
            "description": "Amazon ECS is a fully managed container orchestration service",
            "alternatives": ["EKS", "Fargate", "App Runner"]
        },
        "kubernetes": {
            "primary": "EKS",
            "description": "Amazon EKS is a managed Kubernetes service",
            "alternatives": ["ECS"]
        },
        "serverless": {
            "primary": "Lambda",
            "description": "AWS Lambda lets you run code without provisioning servers",
            "alternatives": ["Fargate", "App Runner"]
        },
        "function": {
            "primary": "Lambda",
            "description": "AWS Lambda lets you run code without provisioning servers",
            "alternatives": ["Fargate", "App Runner"]
        },
        
        # Storage
        "object storage": {
            "primary": "S3",
            "description": "Amazon S3 is an object storage service",
            "alternatives": ["Glacier"]
        },
        "file storage": {
            "primary": "EFS",
            "description": "Amazon EFS provides scalable file storage",
            "alternatives": ["FSx", "S3"]
        },
        "block storage": {
            "primary": "EBS",
            "description": "Amazon EBS provides block-level storage volumes for EC2 instances",
            "alternatives": ["Instance Store"]
        },
        "archive": {
            "primary": "S3 Glacier",
            "description": "Amazon S3 Glacier is a secure, durable, and low-cost storage service for data archiving",
            "alternatives": ["S3 Glacier Deep Archive"]
        },
        
        # Database
        "mysql": {
            "primary": "RDS MySQL",
            "description": "Amazon RDS for MySQL is a managed relational database service",
            "alternatives": ["Aurora MySQL", "MariaDB"]
        },
        "postgresql": {
            "primary": "RDS PostgreSQL",
            "description": "Amazon RDS for PostgreSQL is a managed relational database service",
            "alternatives": ["Aurora PostgreSQL"]
        },
        "postgres": {
            "primary": "RDS PostgreSQL",
            "description": "Amazon RDS for PostgreSQL is a managed relational database service",
            "alternatives": ["Aurora PostgreSQL"]
        },
        "oracle": {
            "primary": "RDS Oracle",
            "description": "Amazon RDS for Oracle is a managed relational database service",
            "alternatives": []
        },
        "sql server": {
            "primary": "RDS SQL Server",
            "description": "Amazon RDS for SQL Server is a managed relational database service",
            "alternatives": []
        },
        "mariadb": {
            "primary": "RDS MariaDB",
            "description": "Amazon RDS for MariaDB is a managed relational database service",
            "alternatives": ["Aurora MySQL"]
        },
        "nosql": {
            "primary": "DynamoDB",
            "description": "Amazon DynamoDB is a managed NoSQL database service",
            "alternatives": ["DocumentDB", "Neptune"]
        },
        "mongodb": {
            "primary": "DocumentDB",
            "description": "Amazon DocumentDB is a MongoDB-compatible document database service",
            "alternatives": ["DynamoDB"]
        },
        "redis": {
            "primary": "ElastiCache for Redis",
            "description": "Amazon ElastiCache for Redis is a managed in-memory data store",
            "alternatives": ["MemoryDB for Redis"]
        },
        "memcached": {
            "primary": "ElastiCache for Memcached",
            "description": "Amazon ElastiCache for Memcached is a managed in-memory data store",
            "alternatives": []
        },
        "graph database": {
            "primary": "Neptune",
            "description": "Amazon Neptune is a fully managed graph database service",
            "alternatives": []
        },
        "time series database": {
            "primary": "Timestream",
            "description": "Amazon Timestream is a fast, scalable, fully managed time series database",
            "alternatives": ["DynamoDB"]
        },
        "cassandra": {
            "primary": "Keyspaces",
            "description": "Amazon Keyspaces is a scalable, highly available, and managed Apache Cassandra-compatible database service",
            "alternatives": ["DynamoDB"]
        },
        
        # Networking
        "load balancer": {
            "primary": "ELB",
            "description": "Elastic Load Balancing automatically distributes incoming application traffic",
            "alternatives": ["ALB", "NLB", "GLB"]
        },
        "cdn": {
            "primary": "CloudFront",
            "description": "Amazon CloudFront is a content delivery network service",
            "alternatives": []
        },
        "dns": {
            "primary": "Route 53",
            "description": "Amazon Route 53 is a scalable domain name system (DNS) web service",
            "alternatives": []
        },
        "vpn": {
            "primary": "Site-to-Site VPN",
            "description": "AWS Site-to-Site VPN creates encrypted connections between your network and your AWS VPCs",
            "alternatives": ["Client VPN"]
        },
        "direct connect": {
            "primary": "Direct Connect",
            "description": "AWS Direct Connect links your internal network to an AWS Direct Connect location over a standard Ethernet fiber-optic cable",
            "alternatives": []
        },
        "api gateway": {
            "primary": "API Gateway",
            "description": "Amazon API Gateway is a fully managed service that makes it easy for developers to create, publish, maintain, monitor, and secure APIs",
            "alternatives": ["AppSync"]
        },
        "firewall": {
            "primary": "Network Firewall",
            "description": "AWS Network Firewall is a managed service that makes it easy to deploy essential network protections for your VPCs",
            "alternatives": ["WAF", "Security Groups"]
        },
        
        # Security
        "identity management": {
            "primary": "IAM",
            "description": "AWS Identity and Access Management enables you to manage access to AWS services and resources securely",
            "alternatives": ["Cognito", "Directory Service"]
        },
        "waf": {
            "primary": "WAF",
            "description": "AWS WAF is a web application firewall that helps protect your web applications from common web exploits",
            "alternatives": ["Shield"]
        },
        "ddos protection": {
            "primary": "Shield",
            "description": "AWS Shield is a managed Distributed Denial of Service (DDoS) protection service",
            "alternatives": ["WAF"]
        },
        "certificate": {
            "primary": "Certificate Manager",
            "description": "AWS Certificate Manager handles the complexity of creating, storing, and renewing public and private SSL/TLS certificates",
            "alternatives": []
        },
        "secrets": {
            "primary": "Secrets Manager",
            "description": "AWS Secrets Manager helps you protect secrets needed to access your applications, services, and IT resources",
            "alternatives": ["Parameter Store"]
        },
        "encryption": {
            "primary": "KMS",
            "description": "AWS Key Management Service makes it easy for you to create and manage cryptographic keys and control their use",
            "alternatives": ["CloudHSM"]
        },
        
        # Messaging
        "message queue": {
            "primary": "SQS",
            "description": "Amazon Simple Queue Service is a fully managed message queuing service",
            "alternatives": ["MQ"]
        },
        "pub/sub": {
            "primary": "SNS",
            "description": "Amazon Simple Notification Service is a fully managed pub/sub messaging service",
            "alternatives": ["EventBridge"]
        },
        "kafka": {
            "primary": "MSK",
            "description": "Amazon Managed Streaming for Apache Kafka is a fully managed service that makes it easy to build and run applications that use Apache Kafka",
            "alternatives": ["Kinesis"]
        },
        "streaming": {
            "primary": "Kinesis",
            "description": "Amazon Kinesis makes it easy to collect, process, and analyze real-time, streaming data",
            "alternatives": ["MSK"]
        },
        "rabbitmq": {
            "primary": "MQ",
            "description": "Amazon MQ is a managed message broker service for Apache ActiveMQ and RabbitMQ",
            "alternatives": ["SQS"]
        },
        
        # Analytics
        "data warehouse": {
            "primary": "Redshift",
            "description": "Amazon Redshift is a fully managed, petabyte-scale data warehouse service",
            "alternatives": ["Athena"]
        },
        "etl": {
            "primary": "Glue",
            "description": "AWS Glue is a fully managed extract, transform, and load (ETL) service",
            "alternatives": ["Data Pipeline"]
        },
        "elasticsearch": {
            "primary": "OpenSearch Service",
            "description": "Amazon OpenSearch Service makes it easy to deploy, secure, and run Elasticsearch and OpenSearch",
            "alternatives": []
        },
        "log analytics": {
            "primary": "CloudWatch Logs",
            "description": "Amazon CloudWatch Logs helps you centralize the logs from all your systems, applications, and AWS services",
            "alternatives": ["OpenSearch Service"]
        },
        "business intelligence": {
            "primary": "QuickSight",
            "description": "Amazon QuickSight is a fast, cloud-powered business intelligence service",
            "alternatives": []
        },
        
        # DevOps
        "ci/cd": {
            "primary": "CodePipeline",
            "description": "AWS CodePipeline is a fully managed continuous delivery service",
            "alternatives": ["CodeBuild", "CodeDeploy"]
        },
        "source control": {
            "primary": "CodeCommit",
            "description": "AWS CodeCommit is a fully-managed source control service",
            "alternatives": []
        },
        "build": {
            "primary": "CodeBuild",
            "description": "AWS CodeBuild is a fully managed build service",
            "alternatives": []
        },
        "deployment": {
            "primary": "CodeDeploy",
            "description": "AWS CodeDeploy is a fully managed deployment service",
            "alternatives": ["Elastic Beanstalk"]
        },
        "monitoring": {
            "primary": "CloudWatch",
            "description": "Amazon CloudWatch is a monitoring and observability service",
            "alternatives": ["X-Ray"]
        },
        "logging": {
            "primary": "CloudWatch Logs",
            "description": "Amazon CloudWatch Logs helps you centralize the logs from all your systems, applications, and AWS services",
            "alternatives": ["OpenSearch Service"]
        },
        
        # Web and Mobile
        "web hosting": {
            "primary": "Amplify",
            "description": "AWS Amplify is a complete solution for building web and mobile applications",
            "alternatives": ["S3", "CloudFront", "Elastic Beanstalk"]
        },
        "static website": {
            "primary": "S3",
            "description": "Amazon S3 can host static websites",
            "alternatives": ["Amplify", "CloudFront"]
        },
        "mobile backend": {
            "primary": "Amplify",
            "description": "AWS Amplify provides a declarative and easy-to-use interface for building mobile backends",
            "alternatives": ["AppSync", "API Gateway"]
        },
        
        # Machine Learning
        "machine learning": {
            "primary": "SageMaker",
            "description": "Amazon SageMaker helps data scientists and developers prepare, build, train, and deploy machine learning models",
            "alternatives": ["Comprehend", "Rekognition", "Forecast"]
        },
        "ai": {
            "primary": "SageMaker",
            "description": "Amazon SageMaker helps data scientists and developers prepare, build, train, and deploy machine learning models",
            "alternatives": ["Comprehend", "Rekognition", "Forecast"]
        },
        "nlp": {
            "primary": "Comprehend",
            "description": "Amazon Comprehend uses natural language processing to extract insights from text",
            "alternatives": ["Lex", "Transcribe"]
        },
        "image recognition": {
            "primary": "Rekognition",
            "description": "Amazon Rekognition makes it easy to add image and video analysis to your applications",
            "alternatives": []
        },
        "chatbot": {
            "primary": "Lex",
            "description": "Amazon Lex is a service for building conversational interfaces into applications using voice and text",
            "alternatives": ["Comprehend"]
        },
        
        # IoT
        "iot": {
            "primary": "IoT Core",
            "description": "AWS IoT Core is a managed cloud service that lets connected devices easily and securely interact with cloud applications and other devices",
            "alternatives": ["IoT Greengrass", "IoT Analytics"]
        },
        "edge computing": {
            "primary": "IoT Greengrass",
            "description": "AWS IoT Greengrass seamlessly extends AWS to edge devices so they can act locally on the data they generate",
            "alternatives": ["Outposts", "Snow Family"]
        }
    }
    
    # Process each technology in the stack
    mappings = []
    for tech in tech_stack:
        tech_lower = tech.lower().strip()
        mapping = {
            "original_tech": tech,
            "aws_service": None,
            "description": None,
            "alternatives": [],
            "confidence": 0.0
        }
        
        # Direct match
        if tech_lower in tech_to_aws:
            match = tech_to_aws[tech_lower]
            mapping["aws_service"] = match["primary"]
            mapping["description"] = match["description"]
            if include_alternatives:
                mapping["alternatives"] = match["alternatives"]
            mapping["confidence"] = 1.0
        else:
            # Partial match
            best_match = None
            best_score = 0
            
            for key, value in tech_to_aws.items():
                # Check if the key is in the tech or vice versa
                if key in tech_lower or tech_lower in key:
                    score = len(key) / max(len(key), len(tech_lower))
                    if score > best_score:
                        best_score = score
                        best_match = (key, value)
            
            if best_match and best_score > 0.5:
                key, match = best_match
                mapping["aws_service"] = match["primary"]
                mapping["description"] = match["description"]
                if include_alternatives:
                    mapping["alternatives"] = match["alternatives"]
                mapping["confidence"] = best_score
            else:
                mapping["aws_service"] = "Unknown"
                mapping["description"] = "No suitable AWS service mapping found"
                mapping["confidence"] = 0.0
        
        mappings.append(mapping)
    
    result = {
        "status": "success",
        "message": f"Mapped {len(mappings)} technologies to AWS services",
        "mappings": mappings
    }
    
    return json.dumps(result)

@tool
def generate_mermaid_diagram(architecture_components: List[Dict[str, Any]], diagram_title: str) -> str:
    """Generate a Mermaid diagram representation of an AWS architecture.

    Args:
        architecture_components (List[Dict[str, Any]]): List of architecture components with their relationships
            Each component should have:
            - id: Unique identifier
            - type: AWS service type
            - name: Display name
            - connections: List of component IDs this component connects to
            - vpc (optional): VPC identifier if the component is inside a VPC
        diagram_title (str): Title of the diagram
        
    Returns:
        str: JSON string containing the Mermaid diagram code
    """
    if not architecture_components:
        return json.dumps({
            "status": "error",
            "message": "No architecture components provided",
            "diagram_code": ""
        })
    
    # Initialize Mermaid diagram
    mermaid_lines = ["graph TB"]
    mermaid_lines.append(f"    title[\"<b>{diagram_title}</b>\"]")
    mermaid_lines.append("    style title fill:none,stroke:none")
    
    # Track VPCs and their components
    vpcs = {}
    components_by_id = {}
    
    # First pass: identify VPCs and components
    for component in architecture_components:
        component_id = component.get("id", "")
        if not component_id:
            continue
            
        components_by_id[component_id] = component
        
        # If component is in a VPC, track it
        vpc_id = component.get("vpc")
        if vpc_id:
            if vpc_id not in vpcs:
                vpcs[vpc_id] = []
            vpcs[vpc_id].append(component_id)
    
    # Second pass: define VPC subgraphs
    vpc_index = 0
    for vpc_id, component_ids in vpcs.items():
        vpc_component = next((c for c in architecture_components if c.get("id") == vpc_id), None)
        vpc_name = vpc_component.get("name", f"VPC {vpc_index + 1}") if vpc_component else f"VPC {vpc_index + 1}"
        
        mermaid_lines.append(f"    subgraph vpc{vpc_index}[\"{vpc_name}\"]")
        mermaid_lines.append(f"        style vpc{vpc_index} fill:{MERMAID_COLORS['vpc']},stroke:#1E88E5")
        
        # Add components in this VPC
        for component_id in component_ids:
            component = components_by_id.get(component_id)
            if component and component.get("id") != vpc_id:  # Skip the VPC itself
                component_name = component.get("name", component_id)
                component_type = component.get("type", "Generic")
                mermaid_lines.append(f"        {component_id}[\"{component_name}<br><i>{component_type}</i>\"]")
                mermaid_lines.append(f"        style {component_id} fill:{MERMAID_COLORS['node']},stroke:#FF9900,color:{MERMAID_COLORS['text']}")
        
        mermaid_lines.append("    end")
        vpc_index += 1
    
    # Third pass: add components not in any VPC
    non_vpc_components = [c for c in architecture_components if not c.get("vpc") and c.get("id") not in vpcs]
    for component in non_vpc_components:
        component_id = component.get("id", "")
        if not component_id:
            continue
            
        component_name = component.get("name", component_id)
        component_type = component.get("type", "Generic")
        mermaid_lines.append(f"    {component_id}[\"{component_name}<br><i>{component_type}</i>\"]")
        mermaid_lines.append(f"    style {component_id} fill:{MERMAID_COLORS['node']},stroke:#FF9900,color:{MERMAID_COLORS['text']}")
    
    # Fourth pass: add connections
    for component in architecture_components:
        component_id = component.get("id", "")
        connections = component.get("connections", [])
        
        for target_id in connections:
            if target_id in components_by_id:
                mermaid_lines.append(f"    {component_id} --> {target_id}")
    
    # Join all lines
    mermaid_code = "\n".join(mermaid_lines)
    
    return json.dumps({
        "status": "success",
        "message": "Mermaid diagram generated successfully",
        "diagram_code": mermaid_code
    })

@tool
def generate_markdown_diagram(architecture_components: List[Dict[str, Any]], diagram_title: str) -> str:
    """Generate a Markdown representation of an AWS architecture.

    Args:
        architecture_components (List[Dict[str, Any]]): List of architecture components with their relationships
        diagram_title (str): Title of the diagram
        
    Returns:
        str: JSON string containing the Markdown representation
    """
    if not architecture_components:
        return json.dumps({
            "status": "error",
            "message": "No architecture components provided",
            "markdown_content": ""
        })
    
    # Generate Mermaid diagram first
    mermaid_result = json.loads(generate_mermaid_diagram(architecture_components, diagram_title))
    mermaid_code = mermaid_result.get("diagram_code", "")
    
    # Start building Markdown content
    markdown_lines = []
    
    # Add title
    markdown_lines.append(f"# {diagram_title}")
    markdown_lines.append("")
    
    # Add Mermaid diagram
    markdown_lines.append("## Architecture Diagram")
    markdown_lines.append("")
    markdown_lines.append("```mermaid")
    markdown_lines.append(mermaid_code)
    markdown_lines.append("```")
    markdown_lines.append("")
    
    # Group components by type
    components_by_type = {}
    for component in architecture_components:
        component_type = component.get("type", "Other")
        if component_type not in components_by_type:
            components_by_type[component_type] = []
        components_by_type[component_type].append(component)
    
    # Add component details
    markdown_lines.append("## Component Details")
    markdown_lines.append("")
    
    for component_type, components in components_by_type.items():
        markdown_lines.append(f"### {component_type}")
        markdown_lines.append("")
        
        # Create table header
        markdown_lines.append("| Name | Description | Connections |")
        markdown_lines.append("| ---- | ----------- | ----------- |")
        
        # Add components to table
        for component in components:
            component_name = component.get("name", component.get("id", "Unknown"))
            component_description = component.get("description", "No description provided")
            
            # Get connections
            connection_names = []
            for conn_id in component.get("connections", []):
                conn_component = next((c for c in architecture_components if c.get("id") == conn_id), None)
                if conn_component:
                    connection_names.append(conn_component.get("name", conn_id))
            
            connections_text = ", ".join(connection_names) if connection_names else "None"
            
            markdown_lines.append(f"| {component_name} | {component_description} | {connections_text} |")
        
        markdown_lines.append("")
    
    # Add VPC details if applicable
    vpcs = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
    if vpcs:
        markdown_lines.append("## Network Details")
        markdown_lines.append("")
        
        for vpc in vpcs:
            vpc_name = vpc.get("name", vpc.get("id", "Unknown VPC"))
            markdown_lines.append(f"### {vpc_name}")
            markdown_lines.append("")
            
            # List components in this VPC
            vpc_id = vpc.get("id")
            vpc_components = [c for c in architecture_components if c.get("vpc") == vpc_id]
            
            if vpc_components:
                markdown_lines.append("Components in this VPC:")
                markdown_lines.append("")
                
                for component in vpc_components:
                    component_name = component.get("name", component.get("id", "Unknown"))
                    component_type = component.get("type", "Unknown")
                    markdown_lines.append(f"- **{component_name}** ({component_type})")
                
                markdown_lines.append("")
    
    # Join all lines
    markdown_content = "\n".join(markdown_lines)
    
    return json.dumps({
        "status": "success",
        "message": "Markdown representation generated successfully",
        "markdown_content": markdown_content
    })

@tool
def generate_drawio_diagram(architecture_components: List[Dict[str, Any]], diagram_title: str) -> str:
    """Generate a draw.io diagram XML representation of an AWS architecture.

    Args:
        architecture_components (List[Dict[str, Any]]): List of architecture components with their relationships
        diagram_title (str): Title of the diagram
        
    Returns:
        str: JSON string containing the draw.io XML representation
    """
    if not architecture_components:
        return json.dumps({
            "status": "error",
            "message": "No architecture components provided",
            "drawio_xml": ""
        })
    
    # Define Draw.io XML template
    drawio_template = """
    <mxfile host="app.diagrams.net" modified="{timestamp}" agent="AWS Architecture Diagram Generator" etag="{etag}" version="21.1.8">
      <diagram id="{diagram_id}" name="{diagram_title}">
        <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="850" math="0" shadow="0">
          <root>
            <mxCell id="0"/>
            <mxCell id="1" parent="0"/>
            {cells}
          </root>
        </mxGraphModel>
      </diagram>
    </mxfile>
    """
    
    # Generate a unique diagram ID
    diagram_id = hashlib.md5(diagram_title.encode()).hexdigest()
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Generate etag
    etag = hashlib.md5((diagram_title + timestamp).encode()).hexdigest()
    
    # Track components by ID for easier reference
    components_by_id = {c.get("id"): c for c in architecture_components if c.get("id")}
    
    # Track VPCs
    vpcs = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
    
    # Calculate layout
    # This is a simplified layout algorithm - in a real implementation, you would use a more sophisticated approach
    grid_size = math.ceil(math.sqrt(len(architecture_components)))
    cell_width = 160
    cell_height = 80
    margin = 40
    
    # Start building cells
    cells = []
    cell_id = 2  # Start from 2 as 0 and 1 are reserved
    component_cells = {}  # Map component IDs to cell IDs
    
    # Add title
    title_cell = f"""
    <mxCell id="{cell_id}" value="&lt;font style=&quot;font-size: 24px;&quot;&gt;&lt;b&gt;{diagram_title}&lt;/b&gt;&lt;/font&gt;" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;" vertex="1" parent="1">
      <mxGeometry x="400" y="20" width="300" height="40" as="geometry"/>
    </mxCell>
    """
    cells.append(title_cell)
    cell_id += 1
    
    # First, add VPC containers
    vpc_cells = {}
    vpc_y_position = 100
    for i, vpc in enumerate(vpcs):
        vpc_id = vpc.get("id")
        vpc_name = vpc.get("name", f"VPC {i+1}")
        
        # Calculate VPC size based on components inside it
        vpc_components = [c for c in architecture_components if c.get("vpc") == vpc_id]
        vpc_width = max(400, (len(vpc_components) // 2 + 1) * (cell_width + margin))
        vpc_height = max(200, (len(vpc_components) // 2 + 1) * (cell_height + margin))
        
        vpc_x = 100 + (i % 2) * (vpc_width + margin)
        
        # Create VPC cell
        vpc_cell = f"""
        <mxCell id="{cell_id}" value="{vpc_name}" style="points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc;strokeColor=#248814;fillColor=none;verticalAlign=top;align=left;spacingLeft=30;fontColor=#AAB7B8;dashed=0;" vertex="1" parent="1">
          <mxGeometry x="{vpc_x}" y="{vpc_y_position}" width="{vpc_width}" height="{vpc_height}" as="geometry"/>
        </mxCell>
        """
        cells.append(vpc_cell)
        vpc_cells[vpc_id] = cell_id
        component_cells[vpc_id] = cell_id
        cell_id += 1
        
        if i % 2 == 1:
            vpc_y_position += vpc_height + margin
    
    # Next, add components
    component_positions = {}
    
    # Add components inside VPCs
    for vpc_id, vpc_cell_id in vpc_cells.items():
        vpc_components = [c for c in architecture_components if c.get("vpc") == vpc_id]
        vpc = components_by_id.get(vpc_id)
        
        # Calculate grid layout inside VPC
        vpc_grid_size = math.ceil(math.sqrt(len(vpc_components)))
        
        for i, component in enumerate(vpc_components):
            component_id = component.get("id")
            component_name = component.get("name", component_id)
            component_type = component.get("type", "Generic")
            
            # Calculate position within VPC
            row = i // vpc_grid_size
            col = i % vpc_grid_size
            
            x = 100 + (vpc_cells.index(vpc_cell_id) % 2) * (400 + margin) + col * (cell_width + margin/2) + margin
            y = vpc_y_position - (vpc_height + margin) + row * (cell_height + margin/2) + margin*2
            
            # Store position for connection drawing
            component_positions[component_id] = (x + cell_width/2, y + cell_height/2)
            
            # Create component cell with AWS icon
            aws_icon = get_aws_icon_for_type(component_type)
            component_cell = f"""
            <mxCell id="{cell_id}" value="{component_name}" style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.{aws_icon};fillColor=#FF9900;strokeColor=none;" vertex="1" parent="{vpc_cell_id}">
              <mxGeometry x="{col * (cell_width + margin/2) + margin}" y="{row * (cell_height + margin/2) + margin}" width="{cell_width}" height="{cell_height}" as="geometry"/>
            </mxCell>
            """
            cells.append(component_cell)
            component_cells[component_id] = cell_id
            cell_id += 1
    
    # Add components not in VPCs
    non_vpc_components = [c for c in architecture_components if not c.get("vpc") and c.get("type", "").lower() != "vpc"]
    non_vpc_y_position = vpc_y_position + 100
    
    for i, component in enumerate(non_vpc_components):
        component_id = component.get("id")
        component_name = component.get("name", component_id)
        component_type = component.get("type", "Generic")
        
        # Calculate position
        row = i // grid_size
        col = i % grid_size
        
        x = 100 + col * (cell_width + margin)
        y = non_vpc_y_position + row * (cell_height + margin)
        
        # Store position for connection drawing
        component_positions[component_id] = (x + cell_width/2, y + cell_height/2)
        
        # Create component cell with AWS icon
        aws_icon = get_aws_icon_for_type(component_type)
        component_cell = f"""
        <mxCell id="{cell_id}" value="{component_name}" style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.{aws_icon};fillColor=#FF9900;strokeColor=none;" vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" as="geometry"/>
        </mxCell>
        """
        cells.append(component_cell)
        component_cells[component_id] = cell_id
        cell_id += 1
    
    # Finally, add connections
    for component in architecture_components:
        source_id = component.get("id")
        if not source_id or source_id not in component_cells:
            continue
            
        source_cell_id = component_cells[source_id]
        connections = component.get("connections", [])
        
        for target_id in connections:
            if target_id in component_cells:
                target_cell_id = component_cells[target_id]
                
                connection_cell = f"""
                <mxCell id="{cell_id}" value="" style="endArrow=classic;html=1;rounded=0;" edge="1" parent="1" source="{source_cell_id}" target="{target_cell_id}">
                  <mxGeometry width="50" height="50" relative="1" as="geometry">
                    <mxPoint x="550" y="420" as="sourcePoint"/>
                    <mxPoint x="600" y="370" as="targetPoint"/>
                  </mxGeometry>
                </mxCell>
                """
                cells.append(connection_cell)
                cell_id += 1
    
    # Combine all cells
    all_cells = "\n".join(cells)
    
    # Generate the final XML
    drawio_xml = drawio_template.format(
        timestamp=timestamp,
        etag=etag,
        diagram_id=diagram_id,
        diagram_title=diagram_title,
        cells=all_cells
    )
    
    # Clean up the XML formatting
    drawio_xml = re.sub(r'\n\s*', '', drawio_xml)
    
    return json.dumps({
        "status": "success",
        "message": "Draw.io diagram generated successfully",
        "drawio_xml": drawio_xml
    })

def get_aws_icon_for_type(component_type: str) -> str:
    """Get the appropriate AWS icon for a component type."""
    # Normalize component type
    component_type_lower = component_type.lower()
    
    # Map component types to AWS icons
    icon_mapping = {
        "ec2": "resourceIcon/Compute/Amazon-EC2",
        "s3": "resourceIcon/Storage/Amazon-S3",
        "rds": "resourceIcon/Database/Amazon-RDS",
        "lambda": "resourceIcon/Compute/AWS-Lambda",
        "dynamodb": "resourceIcon/Database/Amazon-DynamoDB",
        "elb": "resourceIcon/Networking-Content-Delivery/Elastic-Load-Balancing",
        "alb": "resourceIcon/Networking-Content-Delivery/Elastic-Load-Balancing_Application-Load-Balancer",
        "nlb": "resourceIcon/Networking-Content-Delivery/Elastic-Load-Balancing_Network-Load-Balancer",
        "cloudfront": "resourceIcon/Networking-Content-Delivery/Amazon-CloudFront",
        "route53": "resourceIcon/Networking-Content-Delivery/Amazon-Route-53",
        "vpc": "resourceIcon/Networking-Content-Delivery/Amazon-VPC",
        "subnet": "resourceIcon/Networking-Content-Delivery/Amazon-VPC_Subnet",
        "internet gateway": "resourceIcon/Networking-Content-Delivery/Amazon-VPC_Internet-Gateway",
        "nat gateway": "resourceIcon/Networking-Content-Delivery/Amazon-VPC_NAT-Gateway",
        "security group": "resourceIcon/Networking-Content-Delivery/Amazon-VPC_Security-Group",
        "iam": "resourceIcon/Security-Identity-Compliance/AWS-Identity-and-Access-Management",
        "cloudwatch": "resourceIcon/Management-Governance/Amazon-CloudWatch",
        "sns": "resourceIcon/Application-Integration/Amazon-SNS",
        "sqs": "resourceIcon/Application-Integration/Amazon-SQS",
        "api gateway": "resourceIcon/Networking-Content-Delivery/Amazon-API-Gateway",
        "cognito": "resourceIcon/Security-Identity-Compliance/Amazon-Cognito",
        "elasticache": "resourceIcon/Database/Amazon-ElastiCache",
        "redis": "resourceIcon/Database/Amazon-ElastiCache_Redis",
        "memcached": "resourceIcon/Database/Amazon-ElastiCache_Memcached",
        "cloudformation": "resourceIcon/Management-Governance/AWS-CloudFormation",
        "ecs": "resourceIcon/Compute/Amazon-ECS",
        "eks": "resourceIcon/Compute/Amazon-EKS",
        "fargate": "resourceIcon/Compute/AWS-Fargate",
        "aurora": "resourceIcon/Database/Amazon-Aurora",
        "redshift": "resourceIcon/Database/Amazon-Redshift",
        "elasticsearch": "resourceIcon/Analytics/Amazon-OpenSearch-Service",
        "opensearch": "resourceIcon/Analytics/Amazon-OpenSearch-Service",
        "kinesis": "resourceIcon/Analytics/Amazon-Kinesis",
        "glue": "resourceIcon/Analytics/AWS-Glue",
        "athena": "resourceIcon/Analytics/Amazon-Athena",
        "step functions": "resourceIcon/Application-Integration/AWS-Step-Functions",
        "eventbridge": "resourceIcon/Application-Integration/Amazon-EventBridge",
        "codepipeline": "resourceIcon/Developer-Tools/AWS-CodePipeline",
        "codebuild": "resourceIcon/Developer-Tools/AWS-CodeBuild",
        "codedeploy": "resourceIcon/Developer-Tools/AWS-CodeDeploy",
        "waf": "resourceIcon/Security-Identity-Compliance/AWS-WAF",
        "shield": "resourceIcon/Security-Identity-Compliance/AWS-Shield",
        "secrets manager": "resourceIcon/Security-Identity-Compliance/AWS-Secrets-Manager",
        "kms": "resourceIcon/Security-Identity-Compliance/AWS-Key-Management-Service",
        "cloudtrail": "resourceIcon/Management-Governance/AWS-CloudTrail",
        "config": "resourceIcon/Management-Governance/AWS-Config",
        "systems manager": "resourceIcon/Management-Governance/AWS-Systems-Manager",
        "organizations": "resourceIcon/Management-Governance/AWS-Organizations",
        "trusted advisor": "resourceIcon/Management-Governance/AWS-Trusted-Advisor"
    }
    
    # Try to find a direct match
    if component_type_lower in icon_mapping:
        return icon_mapping[component_type_lower]
    
    # Try to find a partial match
    for key, value in icon_mapping.items():
        if key in component_type_lower or component_type_lower in key:
            return value
    
    # Default to a generic AWS icon
    return "resourceIcon/General/AWS-Cloud"

@tool
def generate_ppt_diagram(architecture_components: List[Dict[str, Any]], template_path: Optional[str] = None, diagram_title: str = "AWS Architecture Diagram") -> str:
    """Generate PowerPoint presentation diagram based on architecture components.

    Args:
        architecture_components (List[Dict[str, Any]]): List of architecture components with their relationships
        template_path (Optional[str]): Path to PowerPoint template file (.pptx)
        diagram_title (str): Title of the diagram
        
    Returns:
        str: JSON string containing information about the generated PowerPoint file
    """
    if not architecture_components:
        return json.dumps({
            "status": "error",
            "message": "No architecture components provided",
            "file_path": None
        })
    
    # In a real implementation, this would use a library like python-pptx to generate a PowerPoint file
    # Since we can't actually create a PowerPoint file in this environment, we'll return a mock response
    
    # Count components by type
    component_types = {}
    for component in architecture_components:
        component_type = component.get("type", "Unknown")
        if component_type in component_types:
            component_types[component_type] += 1
        else:
            component_types[component_type] = 1
    
    # Count VPCs and their contents
    vpcs = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
    vpc_contents = {}
    for vpc in vpcs:
        vpc_id = vpc.get("id")
        vpc_name = vpc.get("name", vpc_id)
        vpc_components = [c for c in architecture_components if c.get("vpc") == vpc_id]
        vpc_contents[vpc_name] = len(vpc_components)
    
    # Generate a mock file path
    output_filename = f"{diagram_title.replace(' ', '_')}.pptx"
    output_path = f"/tmp/{output_filename}"
    
    # Describe what would be in the PowerPoint
    slides_description = [
        {
            "slide_number": 1,
            "title": diagram_title,
            "content": "Title slide with AWS logo and diagram title"
        },
        {
            "slide_number": 2,
            "title": "Architecture Overview",
            "content": f"Main architecture diagram showing {len(architecture_components)} components and their relationships"
        }
    ]
    
    # Add VPC detail slides
    slide_number = 3
    for vpc_name, component_count in vpc_contents.items():
        slides_description.append({
            "slide_number": slide_number,
            "title": f"{vpc_name} Details",
            "content": f"Detailed view of {vpc_name} with {component_count} components"
        })
        slide_number += 1
    
    # Add component summary slide
    slides_description.append({
        "slide_number": slide_number,
        "title": "Component Summary",
        "content": f"Summary table of all {len(architecture_components)} components grouped by type"
    })
    
    return json.dumps({
        "status": "success",
        "message": "PowerPoint presentation diagram would be generated (mock implementation)",
        "file_path": output_path,
        "slides": slides_description,
        "component_count": len(architecture_components),
        "component_types": component_types,
        "vpc_count": len(vpcs),
        "template_used": template_path if template_path else "Default template"
    })

@tool
def validate_architecture(architecture_components: List[Dict[str, Any]]) -> str:
    """Validate AWS architecture design for best practices and common issues.

    Args:
        architecture_components (List[Dict[str, Any]]): List of architecture components with their relationships
        
    Returns:
        str: JSON string containing validation results, recommendations and issues found
    """
    if not architecture_components:
        return json.dumps({
            "status": "error",
            "message": "No architecture components provided",
            "validation_results": {}
        })
    
    # Initialize validation results
    validation_results = {
        "status": "success",
        "component_count": len(architecture_components),
        "issues": {
            "critical": [],
            "warning": [],
            "info": []
        },
        "recommendations": [],
        "best_practices_met": [],
        "validation_summary": ""
    }
    
    # Helper function to add issues
    def add_issue(severity, title, description, affected_components=None, recommendation=None):
        issue = {
            "title": title,
            "description": description
        }
        
        if affected_components:
            issue["affected_components"] = affected_components
            
        if recommendation:
            issue["recommendation"] = recommendation
            
        validation_results["issues"][severity].append(issue)
    
    # Helper function to add recommendations
    def add_recommendation(title, description, benefit):
        validation_results["recommendations"].append({
            "title": title,
            "description": description,
            "benefit": benefit
        })
    
    # Helper function to add best practices met
    def add_best_practice(title, description):
        validation_results["best_practices_met"].append({
            "title": title,
            "description": description
        })
    
    # Track components by ID for easier reference
    components_by_id = {c.get("id"): c for c in architecture_components if c.get("id")}
    
    # Track VPCs and their components
    vpcs = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
    vpc_components = {}
    
    for vpc in vpcs:
        vpc_id = vpc.get("id")
        vpc_components[vpc_id] = [c for c in architecture_components if c.get("vpc") == vpc_id]
    
    # Check 1: Ensure there's at least one VPC
    if not vpcs:
        add_issue(
            "warning", 
            "No VPC defined", 
            "The architecture does not include any Virtual Private Cloud (VPC) components.",
            recommendation="Consider adding a VPC to isolate your resources in a virtual network."
        )
    else:
        add_best_practice(
            "VPC isolation", 
            "The architecture uses VPC for network isolation."
        )
    
    # Check 2: Check for public-facing components
    public_facing_components = []
    for component in architecture_components:
        # Components not in a VPC are considered public-facing
        if not component.get("vpc") and component.get("type", "").lower() not in ["vpc", "cloudfront", "route53", "waf", "shield"]:
            public_facing_components.append(component)
    
    if public_facing_components:
        component_names = [c.get("name", c.get("id", "Unknown")) for c in public_facing_components]
        add_issue(
            "warning",
            "Public-facing components detected",
            f"The following components are not placed within a VPC: {', '.join(component_names)}",
            affected_components=component_names,
            recommendation="Consider placing these components within a VPC for better security."
        )
    
    # Check 3: Check for load balancing
    load_balancers = [c for c in architecture_components if c.get("type", "").lower() in ["elb", "alb", "nlb", "load balancer"]]
    
    if not load_balancers:
        ec2_instances = [c for c in architecture_components if c.get("type", "").lower() == "ec2"]
        if len(ec2_instances) > 1:
            add_issue(
                "info",
                "Multiple EC2 instances without load balancer",
                f"There are {len(ec2_instances)} EC2 instances but no load balancer.",
                affected_components=[c.get("name", c.get("id", "Unknown")) for c in ec2_instances],
                recommendation="Consider adding a load balancer for high availability and better traffic distribution."
            )
    else:
        add_best_practice(
            "Load balancing", 
            "The architecture includes load balancing for high availability."
        )
    
    # Check 4: Check for database backup/redundancy
    databases = [c for c in architecture_components if c.get("type", "").lower() in ["rds", "aurora", "dynamodb", "redshift", "database"]]
    
    if databases:
        # Check if there's any mention of multi-AZ or read replicas in the component descriptions
        has_redundancy = any("multi-az" in c.get("description", "").lower() or "replica" in c.get("description", "").lower() for c in databases)
        
        if not has_redundancy:
            add_issue(
                "info",
                "Database redundancy not specified",
                "The architecture includes databases but doesn't explicitly mention Multi-AZ or read replicas.",
                affected_components=[c.get("name", c.get("id", "Unknown")) for c in databases],
                recommendation="Consider using Multi-AZ deployments or read replicas for database redundancy."
            )
    
    # Check 5: Check for security components
    security_components = [c for c in architecture_components if c.get("type", "").lower() in ["waf", "shield", "security group", "nacl", "iam"]]
    
    if not security_components:
        add_issue(
            "warning",
            "Limited security components",
            "The architecture doesn't include explicit security components like WAF, Shield, or IAM.",
            recommendation="Consider adding security components to protect your application."
        )
    else:
        add_best_practice(
            "Security components", 
            "The architecture includes dedicated security components."
        )
    
    # Check 6: Check for monitoring
    monitoring_components = [c for c in architecture_components if c.get("type", "").lower() in ["cloudwatch", "monitoring", "logs"]]
    
    if not monitoring_components:
        add_issue(
            "info",
            "No monitoring components",
            "The architecture doesn't include explicit monitoring components.",
            recommendation="Consider adding CloudWatch for monitoring and alerting."
        )
    else:
        add_best_practice(
            "Monitoring", 
            "The architecture includes monitoring components."
        )
    
    # Check 7: Check for auto scaling
    autoscaling_components = [c for c in architecture_components if "auto scaling" in c.get("type", "").lower() or "autoscaling" in c.get("type", "").lower()]
    
    if not autoscaling_components and any(c.get("type", "").lower() == "ec2" for c in architecture_components):
        add_issue(
            "info",
            "No Auto Scaling",
            "The architecture includes EC2 instances but no Auto Scaling components.",
            recommendation="Consider adding Auto Scaling for better elasticity and fault tolerance."
        )
    elif autoscaling_components:
        add_best_practice(
            "Auto Scaling", 
            "The architecture includes Auto Scaling for elasticity."
        )
    
    # Check 8: Check for CDN for static content
    has_s3 = any(c.get("type", "").lower() == "s3" for c in architecture_components)
    has_cloudfront = any(c.get("type", "").lower() == "cloudfront" for c in architecture_components)
    
    if has_s3 and not has_cloudfront:
        add_recommendation(
            "Add CloudFront CDN",
            "Consider using CloudFront CDN with your S3 buckets for better performance and reduced latency.",
            "Improved global performance and reduced origin load."
        )
    elif has_s3 and has_cloudfront:
        add_best_practice(
            "CDN for static content", 
            "The architecture uses CloudFront CDN with S3 for static content delivery."
        )
    
    # Check 9: Check for multi-region components
    multi_region_components = [c for c in architecture_components if "region" in c.get("description", "").lower() and "multi" in c.get("description", "").lower()]
    
    if not multi_region_components:
        add_recommendation(
            "Consider multi-region deployment",
            "For critical applications, consider a multi-region deployment for disaster recovery and high availability.",
            "Improved disaster recovery capabilities and global performance."
        )
    else:
        add_best_practice(
            "Multi-region deployment", 
            "The architecture includes multi-region components for high availability."
        )
    
    # Generate validation summary
    critical_count = len(validation_results["issues"]["critical"])
    warning_count = len(validation_results["issues"]["warning"])
    info_count = len(validation_results["issues"]["info"])
    recommendation_count = len(validation_results["recommendations"])
    best_practice_count = len(validation_results["best_practices_met"])
    
    if critical_count > 0:
        validation_summary = f"Architecture validation found {critical_count} critical issues that should be addressed."
    elif warning_count > 0:
        validation_summary = f"Architecture validation found {warning_count} warnings that should be reviewed."
    elif info_count > 0:
        validation_summary = f"Architecture validation found {info_count} suggestions for improvement."
    else:
        validation_summary = "Architecture validation completed successfully with no issues found."
    
    validation_summary += f" {recommendation_count} recommendations and {best_practice_count} best practices identified."
    validation_results["validation_summary"] = validation_summary
    
    return json.dumps(validation_results)