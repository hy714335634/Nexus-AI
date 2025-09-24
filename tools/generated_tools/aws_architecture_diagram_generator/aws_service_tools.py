from typing import Dict, List, Any, Optional, Union, Literal
import json
import boto3
import logging
import re
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AWS Service information cache
AWS_SERVICE_CACHE = {}

# Technology stack mapping cache
TECH_STACK_MAPPING_CACHE = {}

# AWS Service categories
AWS_SERVICE_CATEGORIES = {
    "compute": ["EC2", "Lambda", "ECS", "EKS", "Batch", "Fargate", "Lightsail", "Elastic Beanstalk"],
    "storage": ["S3", "EBS", "EFS", "FSx", "Storage Gateway", "Snow Family"],
    "database": ["RDS", "DynamoDB", "ElastiCache", "Neptune", "Timestream", "QLDB", "DocumentDB", "Keyspaces"],
    "networking": ["VPC", "CloudFront", "Route 53", "API Gateway", "Direct Connect", "Transit Gateway", "PrivateLink"],
    "security": ["IAM", "Cognito", "KMS", "WAF", "Shield", "GuardDuty", "Security Hub", "Detective"],
    "analytics": ["Athena", "EMR", "Kinesis", "Redshift", "QuickSight", "DataZone", "Glue", "OpenSearch Service"],
    "integration": ["SNS", "SQS", "EventBridge", "Step Functions", "AppFlow", "MQ"],
    "management": ["CloudWatch", "CloudTrail", "Config", "Systems Manager", "Control Tower", "Organizations"],
    "developer_tools": ["CodeCommit", "CodeBuild", "CodeDeploy", "CodePipeline", "Cloud9", "CodeStar"],
    "ai_ml": ["SageMaker", "Rekognition", "Comprehend", "Lex", "Polly", "Textract", "Bedrock", "Kendra"]
}

# Technology stack to AWS service mapping
DEFAULT_TECH_MAPPING = {
    # Compute
    "virtual machine": {"primary": "EC2", "alternatives": ["Lightsail", "App Runner"]},
    "vm": {"primary": "EC2", "alternatives": ["Lightsail", "App Runner"]},
    "container": {"primary": "ECS", "alternatives": ["EKS", "Fargate", "App Runner"]},
    "kubernetes": {"primary": "EKS", "alternatives": ["ECS"]},
    "serverless": {"primary": "Lambda", "alternatives": ["Fargate", "App Runner"]},
    "function": {"primary": "Lambda", "alternatives": ["Step Functions"]},
    "batch processing": {"primary": "Batch", "alternatives": ["Lambda", "Step Functions"]},
    "web hosting": {"primary": "Elastic Beanstalk", "alternatives": ["Amplify", "S3", "EC2"]},
    
    # Storage
    "object storage": {"primary": "S3", "alternatives": ["EFS"]},
    "file storage": {"primary": "EFS", "alternatives": ["FSx", "S3"]},
    "block storage": {"primary": "EBS", "alternatives": ["EC2 Instance Store"]},
    "backup": {"primary": "Backup", "alternatives": ["S3 Glacier", "Storage Gateway"]},
    
    # Databases
    "sql": {"primary": "RDS", "alternatives": ["Aurora", "Redshift"]},
    "mysql": {"primary": "RDS MySQL", "alternatives": ["Aurora MySQL"]},
    "postgresql": {"primary": "RDS PostgreSQL", "alternatives": ["Aurora PostgreSQL"]},
    "oracle": {"primary": "RDS Oracle", "alternatives": []},
    "sql server": {"primary": "RDS SQL Server", "alternatives": []},
    "mariadb": {"primary": "RDS MariaDB", "alternatives": ["Aurora MySQL"]},
    "nosql": {"primary": "DynamoDB", "alternatives": ["DocumentDB", "Keyspaces"]},
    "mongodb": {"primary": "DocumentDB", "alternatives": ["DynamoDB"]},
    "cassandra": {"primary": "Keyspaces", "alternatives": ["DynamoDB"]},
    "redis": {"primary": "ElastiCache for Redis", "alternatives": ["MemoryDB"]},
    "memcached": {"primary": "ElastiCache for Memcached", "alternatives": []},
    "graph database": {"primary": "Neptune", "alternatives": []},
    "time series": {"primary": "Timestream", "alternatives": ["DynamoDB", "RDS"]},
    "ledger": {"primary": "QLDB", "alternatives": []},
    "data warehouse": {"primary": "Redshift", "alternatives": ["Athena", "Lake Formation"]},
    
    # Networking
    "cdn": {"primary": "CloudFront", "alternatives": []},
    "dns": {"primary": "Route 53", "alternatives": []},
    "load balancer": {"primary": "ELB", "alternatives": ["API Gateway"]},
    "api": {"primary": "API Gateway", "alternatives": ["AppSync", "Lambda"]},
    "vpn": {"primary": "VPN", "alternatives": ["Client VPN", "Site-to-Site VPN"]},
    "direct connect": {"primary": "Direct Connect", "alternatives": []},
    "firewall": {"primary": "Network Firewall", "alternatives": ["WAF", "Security Groups"]},
    
    # Security
    "identity management": {"primary": "IAM", "alternatives": ["Cognito", "Directory Service"]},
    "authentication": {"primary": "Cognito", "alternatives": ["IAM", "Directory Service"]},
    "encryption": {"primary": "KMS", "alternatives": ["CloudHSM", "Certificate Manager"]},
    "waf": {"primary": "WAF", "alternatives": ["Shield"]},
    "ddos protection": {"primary": "Shield", "alternatives": ["WAF"]},
    "security monitoring": {"primary": "GuardDuty", "alternatives": ["Security Hub", "Detective"]},
    
    # Integration
    "message queue": {"primary": "SQS", "alternatives": ["MQ", "MSK"]},
    "pub/sub": {"primary": "SNS", "alternatives": ["EventBridge"]},
    "event bus": {"primary": "EventBridge", "alternatives": ["SNS", "SQS"]},
    "workflow": {"primary": "Step Functions", "alternatives": ["SWF"]},
    "kafka": {"primary": "MSK", "alternatives": ["Kinesis"]},
    "rabbitmq": {"primary": "MQ", "alternatives": ["SQS"]},
    "activemq": {"primary": "MQ", "alternatives": ["SQS"]},
    
    # Analytics
    "etl": {"primary": "Glue", "alternatives": ["Data Pipeline", "EMR"]},
    "streaming": {"primary": "Kinesis", "alternatives": ["MSK", "Firehose"]},
    "data lake": {"primary": "Lake Formation", "alternatives": ["S3", "Athena"]},
    "big data": {"primary": "EMR", "alternatives": ["Athena", "Glue"]},
    "search": {"primary": "OpenSearch Service", "alternatives": ["Kendra"]},
    "business intelligence": {"primary": "QuickSight", "alternatives": ["Athena"]},
    "log analytics": {"primary": "CloudWatch Logs", "alternatives": ["OpenSearch Service"]},
    
    # AI/ML
    "machine learning": {"primary": "SageMaker", "alternatives": ["Rekognition", "Comprehend", "Bedrock"]},
    "ai": {"primary": "Bedrock", "alternatives": ["SageMaker"]},
    "chatbot": {"primary": "Lex", "alternatives": ["Bedrock"]},
    "nlp": {"primary": "Comprehend", "alternatives": ["Bedrock"]},
    "image recognition": {"primary": "Rekognition", "alternatives": ["SageMaker"]},
    "document analysis": {"primary": "Textract", "alternatives": ["Comprehend"]},
    "text to speech": {"primary": "Polly", "alternatives": ["Transcribe"]},
    "speech to text": {"primary": "Transcribe", "alternatives": ["Polly"]},
    
    # Web/App Development
    "web application": {"primary": "Amplify", "alternatives": ["Elastic Beanstalk", "App Runner"]},
    "static website": {"primary": "S3", "alternatives": ["Amplify", "CloudFront"]},
    "mobile backend": {"primary": "Amplify", "alternatives": ["AppSync", "API Gateway"]},
    "content management": {"primary": "Amplify", "alternatives": ["S3", "CloudFront"]},
    
    # DevOps
    "ci/cd": {"primary": "CodePipeline", "alternatives": ["CodeBuild", "CodeDeploy"]},
    "source control": {"primary": "CodeCommit", "alternatives": []},
    "build": {"primary": "CodeBuild", "alternatives": []},
    "deployment": {"primary": "CodeDeploy", "alternatives": ["Elastic Beanstalk"]},
    "monitoring": {"primary": "CloudWatch", "alternatives": ["X-Ray", "Managed Grafana"]},
    "logging": {"primary": "CloudWatch Logs", "alternatives": ["OpenSearch Service"]},
    "tracing": {"primary": "X-Ray", "alternatives": ["CloudWatch"]},
    
    # Traditional IT Infrastructure
    "active directory": {"primary": "Directory Service", "alternatives": ["Cognito"]},
    "file server": {"primary": "FSx", "alternatives": ["EFS", "Storage Gateway"]},
    "windows file server": {"primary": "FSx for Windows", "alternatives": ["Storage Gateway"]},
    "nfs": {"primary": "EFS", "alternatives": ["FSx for Lustre"]},
    "vpn server": {"primary": "Client VPN", "alternatives": ["Site-to-Site VPN"]},
    "proxy server": {"primary": "API Gateway", "alternatives": ["App Mesh"]},
    "email server": {"primary": "SES", "alternatives": ["WorkMail"]},
    "directory service": {"primary": "Directory Service", "alternatives": ["Cognito"]},
    
    # Common software
    "nginx": {"primary": "ALB", "alternatives": ["EC2", "ECS"]},
    "apache": {"primary": "ALB", "alternatives": ["EC2", "ECS"]},
    "tomcat": {"primary": "Elastic Beanstalk", "alternatives": ["EC2", "ECS"]},
    "jenkins": {"primary": "CodeBuild", "alternatives": ["EC2", "ECS"]},
    "wordpress": {"primary": "Lightsail", "alternatives": ["EC2", "Elastic Beanstalk"]},
    "drupal": {"primary": "Lightsail", "alternatives": ["EC2", "Elastic Beanstalk"]},
    "joomla": {"primary": "Lightsail", "alternatives": ["EC2", "Elastic Beanstalk"]},
    "elasticsearch": {"primary": "OpenSearch Service", "alternatives": ["EC2"]},
    "hadoop": {"primary": "EMR", "alternatives": ["EC2"]},
    "spark": {"primary": "EMR", "alternatives": ["Glue", "EC2"]},
    
    # Miscellaneous
    "iot": {"primary": "IoT Core", "alternatives": ["Greengrass"]},
    "blockchain": {"primary": "Managed Blockchain", "alternatives": []},
    "game server": {"primary": "GameLift", "alternatives": ["EC2"]},
    "video streaming": {"primary": "Elemental MediaLive", "alternatives": ["Kinesis Video Streams"]},
    "augmented reality": {"primary": "Sumerian", "alternatives": []},
    "quantum computing": {"primary": "Braket", "alternatives": []}
}

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
    service_name = service_name.strip().upper()
    
    # Check cache first
    cache_key = f"{service_name}_{region}"
    if cache_key in AWS_SERVICE_CACHE:
        logger.info(f"Returning cached information for {service_name}")
        return json.dumps(AWS_SERVICE_CACHE[cache_key])
    
    try:
        # Try to get service information from AWS Service Catalog
        # This is a real API call that would work in production with proper permissions
        result = get_service_info_from_aws(service_name, region)
        
        # Cache the result
        AWS_SERVICE_CACHE[cache_key] = result
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error querying AWS service info: {str(e)}")
        
        # Fallback to built-in information if AWS API call fails
        fallback_info = get_fallback_service_info(service_name)
        
        if fallback_info:
            # Cache the fallback result
            AWS_SERVICE_CACHE[cache_key] = fallback_info
            return json.dumps(fallback_info)
        else:
            return json.dumps({
                "status": "error",
                "error": f"Could not retrieve information for service: {service_name}",
                "message": str(e)
            })

def get_service_info_from_aws(service_name: str, region: str) -> Dict[str, Any]:
    """Get service information from AWS Service Catalog API.
    
    This function makes real AWS API calls using boto3.
    """
    try:
        # Create AWS Service Catalog client
        client = boto3.client('servicecatalog', region_name=region)
        
        # Try to find the service in AWS Service Catalog
        # This is a simplified example - in reality, we would need to search through
        # products and portfolios to find the matching service
        response = client.search_products(
            Filters={
                'FullTextSearch': [service_name]
            }
        )
        
        if 'ProductViewSummaries' in response and response['ProductViewSummaries']:
            product = response['ProductViewSummaries'][0]
            product_id = product['ProductId']
            
            # Get detailed product information
            product_detail = client.describe_product(
                Id=product_id
            )
            
            # Format the response
            result = {
                "status": "success",
                "service_name": service_name,
                "description": product.get('ShortDescription', ''),
                "full_description": product_detail.get('ProvisioningArtifactSummaries', [{}])[0].get('Description', ''),
                "features": [],  # Would need to extract from description or other sources
                "limitations": [],  # Would need to extract from description or other sources
                "pricing_model": "See AWS Pricing Calculator",
                "documentation_url": f"https://docs.aws.amazon.com/{service_name.lower()}/latest/userguide/",
                "console_url": f"https://{region}.console.aws.amazon.com/{service_name.lower()}/home?region={region}",
                "category": get_service_category(service_name)
            }
            
            return result
        else:
            # If not found, fall back to built-in information
            return get_fallback_service_info(service_name)
            
    except Exception as e:
        logger.error(f"AWS API call failed: {str(e)}")
        # Fall back to built-in information
        return get_fallback_service_info(service_name)

def get_service_category(service_name: str) -> str:
    """Get the category of an AWS service."""
    service_name_upper = service_name.upper()
    
    for category, services in AWS_SERVICE_CATEGORIES.items():
        for service in services:
            if service.upper() == service_name_upper or service_name_upper in service.upper():
                return category
    
    return "other"

def get_fallback_service_info(service_name: str) -> Dict[str, Any]:
    """Get fallback information for AWS services from a built-in database."""
    service_name_upper = service_name.upper()
    
    # Built-in information for common AWS services
    service_info = {
        "EC2": {
            "description": "Amazon Elastic Compute Cloud (Amazon EC2) is a web service that provides secure, resizable compute capacity in the cloud.",
            "full_description": "Amazon EC2 eliminates your need to invest in hardware up front, so you can develop and deploy applications faster. You can use Amazon EC2 to launch as many or as few virtual servers as you need, configure security and networking, and manage storage.",
            "features": [
                "Elastic computing capacity",
                "Complete control of instances",
                "Flexible instance options (On-Demand, Reserved, Spot)",
                "Integrated with most AWS services",
                "High security through VPC and security groups"
            ],
            "limitations": [
                "Instance quotas per region",
                "Some instance types not available in all regions",
                "Maximum 65,535 IPs per VPC"
            ],
            "pricing_model": "Pay-as-you-go with options for Reserved and Spot Instances",
            "category": "compute"
        },
        "S3": {
            "description": "Amazon Simple Storage Service (Amazon S3) is an object storage service offering industry-leading scalability, data availability, security, and performance.",
            "full_description": "Amazon S3 allows you to store and retrieve any amount of data at any time, from anywhere on the web. It provides comprehensive security and compliance capabilities that meet even the most stringent regulatory requirements.",
            "features": [
                "Unlimited storage capacity",
                "Multiple storage classes (Standard, IA, Glacier, etc.)",
                "Versioning and lifecycle policies",
                "Strong consistency",
                "Event notifications",
                "Fine-grained access controls"
            ],
            "limitations": [
                "Individual objects limited to 5TB",
                "Maximum 5,500 requests per second per prefix",
                "Eventual consistency for overwrite PUTS and DELETES in some regions"
            ],
            "pricing_model": "Pay only for what you use with tiered pricing based on storage amount",
            "category": "storage"
        },
        "RDS": {
            "description": "Amazon Relational Database Service (Amazon RDS) makes it easy to set up, operate, and scale a relational database in the cloud.",
            "full_description": "Amazon RDS provides cost-efficient and resizable capacity while automating time-consuming administration tasks such as hardware provisioning, database setup, patching and backups.",
            "features": [
                "Supports multiple database engines (MySQL, PostgreSQL, Oracle, SQL Server, MariaDB, Aurora)",
                "Automated backups and patching",
                "Multi-AZ deployments for high availability",
                "Read replicas for improved read performance",
                "Encryption at rest and in transit"
            ],
            "limitations": [
                "Maximum database size varies by engine",
                "Some advanced database features may not be available",
                "Limited direct access to underlying OS"
            ],
            "pricing_model": "Pay-as-you-go based on instance type, storage, and I/O operations",
            "category": "database"
        },
        "LAMBDA": {
            "description": "AWS Lambda is a serverless compute service that lets you run code without provisioning or managing servers.",
            "full_description": "AWS Lambda executes your code only when needed and scales automatically, from a few requests per day to thousands per second. You pay only for the compute time you consume - there is no charge when your code is not running.",
            "features": [
                "Automatic scaling",
                "Stateless functions",
                "Event-driven execution",
                "Supports multiple programming languages",
                "Integrated with many AWS services"
            ],
            "limitations": [
                "Maximum execution duration of 15 minutes",
                "Memory allocation from 128MB to 10GB",
                "Deployment package size limit of 250MB unzipped",
                "Temporary disk space (/tmp) limited to 512MB"
            ],
            "pricing_model": "Pay only for the compute time and requests you use",
            "category": "compute"
        },
        "DYNAMODB": {
            "description": "Amazon DynamoDB is a key-value and document database that delivers single-digit millisecond performance at any scale.",
            "full_description": "DynamoDB is a fully managed NoSQL database service that provides fast and predictable performance with seamless scalability. It offloads the administrative burdens of operating and scaling a distributed database.",
            "features": [
                "Fully managed NoSQL database",
                "Seamless scalability",
                "Single-digit millisecond latency",
                "Automatic multi-region replication",
                "Point-in-time recovery",
                "Built-in security and backup"
            ],
            "limitations": [
                "Maximum item size of 400KB",
                "Limited query flexibility compared to SQL",
                "Maximum of 25 local secondary indexes per table"
            ],
            "pricing_model": "Pay for provisioned throughput capacity or on-demand capacity mode",
            "category": "database"
        },
        "VPC": {
            "description": "Amazon Virtual Private Cloud (Amazon VPC) lets you provision a logically isolated section of the AWS Cloud where you can launch AWS resources in a virtual network that you define.",
            "full_description": "Amazon VPC gives you complete control over your virtual networking environment, including selection of your own IP address range, creation of subnets, and configuration of route tables and network gateways.",
            "features": [
                "Logically isolated virtual networks",
                "Complete control over IP addressing",
                "Multiple connectivity options",
                "Security groups and network ACLs",
                "Flow logs for network monitoring"
            ],
            "limitations": [
                "Maximum of 5 VPCs per region by default (can be increased)",
                "Maximum of 200 subnets per VPC",
                "Maximum of 50 customer gateways per region"
            ],
            "pricing_model": "No additional charge for using VPC itself, pay only for resources used within it",
            "category": "networking"
        },
        "IAM": {
            "description": "AWS Identity and Access Management (IAM) enables you to manage access to AWS services and resources securely.",
            "full_description": "IAM gives you the ability to create and manage AWS users and groups, and use permissions to allow and deny their access to AWS resources. IAM is a feature of your AWS account offered at no additional charge.",
            "features": [
                "Fine-grained access control",
                "Multi-factor authentication",
                "Identity federation",
                "Shared access to AWS accounts",
                "Seamless integration with AWS services"
            ],
            "limitations": [
                "Maximum of 5,000 IAM users per account",
                "Maximum of 1,000 IAM roles per account",
                "Maximum of 10 managed policies per IAM user"
            ],
            "pricing_model": "No additional charge for using IAM",
            "category": "security"
        },
        "CLOUDWATCH": {
            "description": "Amazon CloudWatch is a monitoring and observability service built for DevOps engineers, developers, site reliability engineers (SREs), and IT managers.",
            "full_description": "CloudWatch provides data and actionable insights to monitor your applications, respond to system-wide performance changes, optimize resource utilization, and get a unified view of operational health.",
            "features": [
                "Real-time monitoring",
                "Logs collection and analysis",
                "Alarms and automated actions",
                "Dashboards for visualization",
                "Application insights"
            ],
            "limitations": [
                "Standard resolution metrics stored for 15 months",
                "High resolution metrics stored for 3 hours",
                "Maximum of 10 dimensions per metric"
            ],
            "pricing_model": "Pay for metrics, logs, dashboards, and alarms used",
            "category": "management"
        }
    }
    
    # Try to find the service in our built-in database
    for service_key, info in service_info.items():
        if service_key == service_name_upper:
            result = {
                "status": "success",
                "service_name": service_name,
                "description": info["description"],
                "full_description": info["full_description"],
                "features": info["features"],
                "limitations": info["limitations"],
                "pricing_model": info["pricing_model"],
                "documentation_url": f"https://docs.aws.amazon.com/{service_name.lower()}/latest/userguide/",
                "console_url": f"https://console.aws.amazon.com/{service_name.lower()}/home",
                "category": info["category"]
            }
            return result
    
    # If service not found in our database
    return None

@tool
def map_tech_stack_to_aws(tech_stack: List[str], include_alternatives: bool = True) -> str:
    """Map traditional IT technology stack components to corresponding AWS services.

    Args:
        tech_stack (List[str]): List of traditional IT components or technologies
        include_alternatives (bool): Whether to include alternative AWS services
        
    Returns:
        str: JSON string containing the mapping results
    """
    if not tech_stack:
        return json.dumps({
            "status": "error",
            "error": "Empty technology stack provided",
            "message": "Please provide a list of technologies to map to AWS services."
        })
    
    try:
        # Normalize tech stack items (lowercase, remove special chars)
        normalized_tech_stack = [normalize_tech_name(item) for item in tech_stack]
        
        # Map each tech to AWS services
        mappings = []
        for tech in normalized_tech_stack:
            # Check cache first
            cache_key = f"{tech}_{include_alternatives}"
            if cache_key in TECH_STACK_MAPPING_CACHE:
                mapping = TECH_STACK_MAPPING_CACHE[cache_key]
            else:
                # Get mapping for this tech
                mapping = map_single_tech_to_aws(tech, include_alternatives)
                # Cache the result
                TECH_STACK_MAPPING_CACHE[cache_key] = mapping
            
            mappings.append(mapping)
        
        result = {
            "status": "success",
            "mappings": mappings,
            "unmapped_technologies": [
                tech for i, tech in enumerate(tech_stack) 
                if mappings[i]["aws_service"] == "Unknown"
            ]
        }
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error mapping tech stack to AWS: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to map technology stack",
            "message": str(e)
        })

def normalize_tech_name(tech_name: str) -> str:
    """Normalize technology name for consistent mapping."""
    # Convert to lowercase and remove special characters
    normalized = tech_name.lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

def map_single_tech_to_aws(tech: str, include_alternatives: bool) -> Dict[str, Any]:
    """Map a single technology to AWS service(s)."""
    # Try exact match first
    if tech in DEFAULT_TECH_MAPPING:
        mapping = DEFAULT_TECH_MAPPING[tech]
        result = {
            "original_technology": tech,
            "aws_service": mapping["primary"],
            "confidence": "high",
            "description": f"{mapping['primary']} is the recommended AWS service for {tech}."
        }
        
        if include_alternatives and mapping["alternatives"]:
            result["alternatives"] = mapping["alternatives"]
            
        return result
    
    # Try partial match
    for key, mapping in DEFAULT_TECH_MAPPING.items():
        if tech in key or key in tech:
            result = {
                "original_technology": tech,
                "aws_service": mapping["primary"],
                "confidence": "medium",
                "description": f"{mapping['primary']} is likely the appropriate AWS service for {tech}."
            }
            
            if include_alternatives and mapping["alternatives"]:
                result["alternatives"] = mapping["alternatives"]
                
            return result
    
    # If no match found
    return {
        "original_technology": tech,
        "aws_service": "Unknown",
        "confidence": "none",
        "description": f"No direct AWS service mapping found for {tech}."
    }

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
            "error": "Empty architecture components",
            "message": "Please provide a list of architecture components."
        })
    
    try:
        # Start building the Mermaid diagram
        mermaid_code = ["graph TB"]
        mermaid_code.append(f"    %% {diagram_title}")
        mermaid_code.append("")
        
        # Track VPCs for subgraphs
        vpcs = {}
        
        # First pass: Identify all VPCs
        for component in architecture_components:
            if "vpc" in component and component["vpc"]:
                vpc_id = component["vpc"]
                if vpc_id not in vpcs:
                    vpcs[vpc_id] = {
                        "id": vpc_id,
                        "name": next((c["name"] for c in architecture_components if c["id"] == vpc_id), f"VPC-{vpc_id}"),
                        "components": []
                    }
                
                if component["id"] != vpc_id:  # Don't add the VPC itself to its components
                    vpcs[vpc_id]["components"].append(component["id"])
        
        # Add style definitions
        mermaid_code.append("    %% Style definitions")
        mermaid_code.append("    classDef vpc fill:#f9f9f9,stroke:#888,stroke-width:2px;")
        mermaid_code.append("    classDef ec2 fill:#F58536,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef rds fill:#3B48CC,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef s3 fill:#E05243,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef lambda fill:#FF9900,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef dynamodb fill:#3B48CC,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef elb fill:#1A476F,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef cloudfront fill:#5294CF,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef apigateway fill:#D9A843,stroke:#000,color:#fff;")
        mermaid_code.append("    classDef default fill:#fff,stroke:#000;")
        mermaid_code.append("")
        
        # Add component definitions
        mermaid_code.append("    %% Component definitions")
        for component in architecture_components:
            component_id = component["id"]
            component_name = component["name"]
            component_type = component["type"].lower() if "type" in component else "default"
            
            # Add the component node
            mermaid_code.append(f"    {component_id}[\"{component_name}\"]")
            
            # Add class based on component type
            if component_type in ["ec2", "rds", "s3", "lambda", "dynamodb", "elb", "cloudfront", "apigateway"]:
                mermaid_code.append(f"    class {component_id} {component_type};")
            else:
                mermaid_code.append(f"    class {component_id} default;")
        
        mermaid_code.append("")
        
        # Add VPC subgraphs
        if vpcs:
            mermaid_code.append("    %% VPC subgraphs")
            for vpc_id, vpc_info in vpcs.items():
                mermaid_code.append(f"    subgraph {vpc_id}[\"{vpc_info['name']}\"]")
                for component_id in vpc_info["components"]:
                    mermaid_code.append(f"        {component_id}")
                mermaid_code.append("    end")
                mermaid_code.append(f"    class {vpc_id} vpc;")
            mermaid_code.append("")
        
        # Add connections
        mermaid_code.append("    %% Connections")
        for component in architecture_components:
            if "connections" in component and component["connections"]:
                source_id = component["id"]
                for target_id in component["connections"]:
                    # Find if there's a label for this connection
                    label = ""
                    if "connection_labels" in component:
                        for conn in component["connection_labels"]:
                            if conn["target"] == target_id:
                                label = f"|{conn['label']}|"
                                break
                    
                    mermaid_code.append(f"    {source_id} -->>{label} {target_id}")
        
        # Join all lines to create the final Mermaid code
        final_mermaid_code = "\n".join(mermaid_code)
        
        result = {
            "status": "success",
            "diagram_title": diagram_title,
            "mermaid_code": final_mermaid_code,
            "component_count": len(architecture_components),
            "vpc_count": len(vpcs)
        }
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Mermaid diagram: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to generate Mermaid diagram",
            "message": str(e)
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
            "error": "Empty architecture components",
            "message": "Please provide a list of architecture components."
        })
    
    try:
        # Start building the Markdown content
        markdown_lines = []
        
        # Add title and description
        markdown_lines.append(f"# {diagram_title}")
        markdown_lines.append("")
        markdown_lines.append("## Architecture Overview")
        markdown_lines.append("")
        
        # Add Mermaid diagram
        mermaid_result = json.loads(generate_mermaid_diagram(architecture_components, diagram_title))
        if mermaid_result["status"] == "success":
            markdown_lines.append("```mermaid")
            markdown_lines.append(mermaid_result["mermaid_code"])
            markdown_lines.append("```")
            markdown_lines.append("")
        
        # Group components by type
        components_by_type = {}
        for component in architecture_components:
            component_type = component.get("type", "Other")
            if component_type not in components_by_type:
                components_by_type[component_type] = []
            components_by_type[component_type].append(component)
        
        # Add components section
        markdown_lines.append("## Components")
        markdown_lines.append("")
        
        for component_type, components in components_by_type.items():
            markdown_lines.append(f"### {component_type}")
            markdown_lines.append("")
            
            # Create a table for this component type
            markdown_lines.append("| Name | Description | Connections |")
            markdown_lines.append("| ---- | ----------- | ----------- |")
            
            for component in components:
                name = component.get("name", component.get("id", "Unknown"))
                description = component.get("description", "No description provided")
                
                # Format connections
                connections = []
                if "connections" in component and component["connections"]:
                    for target_id in component["connections"]:
                        target_component = next((c for c in architecture_components if c["id"] == target_id), None)
                        if target_component:
                            target_name = target_component.get("name", target_id)
                            connections.append(target_name)
                
                connections_str = ", ".join(connections) if connections else "None"
                
                markdown_lines.append(f"| {name} | {description} | {connections_str} |")
            
            markdown_lines.append("")
        
        # Add VPC section if applicable
        vpcs = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
        if vpcs:
            markdown_lines.append("## Network Architecture")
            markdown_lines.append("")
            
            for vpc in vpcs:
                vpc_id = vpc["id"]
                vpc_name = vpc.get("name", f"VPC-{vpc_id}")
                vpc_description = vpc.get("description", "No description provided")
                
                markdown_lines.append(f"### {vpc_name}")
                markdown_lines.append("")
                markdown_lines.append(vpc_description)
                markdown_lines.append("")
                
                # List components in this VPC
                vpc_components = [c for c in architecture_components if c.get("vpc") == vpc_id and c["id"] != vpc_id]
                if vpc_components:
                    markdown_lines.append("#### Components in this VPC")
                    markdown_lines.append("")
                    markdown_lines.append("| Name | Type | Description |")
                    markdown_lines.append("| ---- | ---- | ----------- |")
                    
                    for component in vpc_components:
                        name = component.get("name", component.get("id", "Unknown"))
                        component_type = component.get("type", "Unknown")
                        description = component.get("description", "No description provided")
                        
                        markdown_lines.append(f"| {name} | {component_type} | {description} |")
                    
                    markdown_lines.append("")
        
        # Join all lines to create the final Markdown content
        final_markdown = "\n".join(markdown_lines)
        
        result = {
            "status": "success",
            "diagram_title": diagram_title,
            "markdown_content": final_markdown,
            "component_count": len(architecture_components),
            "vpc_count": len(vpcs) if vpcs else 0
        }
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating Markdown diagram: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to generate Markdown diagram",
            "message": str(e)
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
            "error": "Empty architecture components",
            "message": "Please provide a list of architecture components."
        })
    
    try:
        # Create a basic draw.io XML structure
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<mxfile host="app.diagrams.net" modified="2023-09-24T12:00:00.000Z" agent="5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36" etag="abc123" version="14.9.0" type="device">',
            '  <diagram id="architecture-diagram" name="' + diagram_title + '">',
            '    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1169" pageHeight="827" math="0" shadow="0">',
            '      <root>',
            '        <mxCell id="0" />',
            '        <mxCell id="1" parent="0" />',
        ]
        
        # Track VPCs for grouping
        vpcs = {}
        
        # First pass: Identify all VPCs
        for component in architecture_components:
            if "vpc" in component and component["vpc"]:
                vpc_id = component["vpc"]
                if vpc_id not in vpcs:
                    vpc_info = next((c for c in architecture_components if c["id"] == vpc_id), None)
                    vpc_name = vpc_info["name"] if vpc_info and "name" in vpc_info else f"VPC-{vpc_id}"
                    vpcs[vpc_id] = {
                        "id": vpc_id,
                        "name": vpc_name,
                        "components": []
                    }
                
                if component["id"] != vpc_id:  # Don't add the VPC itself to its components
                    vpcs[vpc_id]["components"].append(component["id"])
        
        # Define AWS service styles
        aws_service_styles = {
            "ec2": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FCompute%2FAmazon-EC2_instance_container.svg",
                "width": 60,
                "height": 60
            },
            "rds": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FDatabase%2FAmazon-RDS.svg",
                "width": 60,
                "height": 60
            },
            "s3": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FStorage%2FAmazon-S3-Standard.svg",
                "width": 60,
                "height": 60
            },
            "lambda": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FCompute%2FAWS-Lambda.svg",
                "width": 60,
                "height": 60
            },
            "dynamodb": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FDatabase%2FAmazon-DynamoDB.svg",
                "width": 60,
                "height": 60
            },
            "vpc": {
                "shape": "swimlane",
                "startSize": 30,
                "fillColor": "#f5f5f5",
                "strokeColor": "#666666",
                "width": 480,
                "height": 380
            },
            "default": {
                "shape": "image",
                "image": "https://icons.terrastruct.com/aws%2FGeneral%2FAWS-Cloud.svg",
                "width": 60,
                "height": 60
            }
        }
        
        # Calculate positions
        component_positions = calculate_component_positions(architecture_components, vpcs)
        
        # Add VPC containers first
        for vpc_id, vpc_info in vpcs.items():
            vpc_position = component_positions.get(vpc_id, {"x": 100, "y": 100})
            
            # Create VPC container
            vpc_style = aws_service_styles.get("vpc", aws_service_styles["default"])
            vpc_xml = f'        <mxCell id="{vpc_id}" value="{vpc_info["name"]}" style="swimlane;fontStyle=0;childLayout=stackLayout;horizontal=1;startSize=30;horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;fillColor={vpc_style["fillColor"]};strokeColor={vpc_style["strokeColor"]};" vertex="1" parent="1">'
            vpc_xml += f'          <mxGeometry x="{vpc_position["x"]}" y="{vpc_position["y"]}" width="{vpc_style["width"]}" height="{vpc_style["height"]}" as="geometry" />'
            vpc_xml += '        </mxCell>'
            
            xml_lines.append(vpc_xml)
        
        # Add components
        for component in architecture_components:
            component_id = component["id"]
            component_name = component["name"]
            component_type = component["type"].lower() if "type" in component else "default"
            
            # Skip VPCs as they were already added
            if component_type == "vpc":
                continue
            
            # Get position
            position = component_positions.get(component_id, {"x": 100, "y": 100})
            
            # Get style based on component type
            style = aws_service_styles.get(component_type, aws_service_styles["default"])
            
            # Determine parent (VPC or root)
            parent = "1"  # Default to root
            for vpc_id, vpc_info in vpcs.items():
                if component_id in vpc_info["components"]:
                    parent = vpc_id
                    break
            
            # Create component cell
            if style["shape"] == "image":
                component_xml = f'        <mxCell id="{component_id}" value="{component_name}" style="shape=image;verticalLabelPosition=bottom;labelBackgroundColor=#ffffff;verticalAlign=top;aspect=fixed;imageAspect=0;image={style["image"]};" vertex="1" parent="{parent}">'
                component_xml += f'          <mxGeometry x="{position["x"]}" y="{position["y"]}" width="{style["width"]}" height="{style["height"]}" as="geometry" />'
                component_xml += '        </mxCell>'
            else:
                component_xml = f'        <mxCell id="{component_id}" value="{component_name}" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="{parent}">'
                component_xml += f'          <mxGeometry x="{position["x"]}" y="{position["y"]}" width="{style["width"]}" height="{style["height"]}" as="geometry" />'
                component_xml += '        </mxCell>'
            
            xml_lines.append(component_xml)
        
        # Add connections
        for component in architecture_components:
            if "connections" in component and component["connections"]:
                source_id = component["id"]
                for target_id in component["connections"]:
                    # Create connection
                    connection_id = f"{source_id}-{target_id}"
                    connection_xml = f'        <mxCell id="{connection_id}" value="" style="endArrow=classic;html=1;rounded=0;" edge="1" parent="1" source="{source_id}" target="{target_id}">'
                    connection_xml += '          <mxGeometry width="50" height="50" relative="1" as="geometry">'
                    connection_xml += '            <mxPoint as="sourcePoint" />'
                    connection_xml += '            <mxPoint as="targetPoint" />'
                    connection_xml += '          </mxGeometry>'
                    connection_xml += '        </mxCell>'
                    
                    xml_lines.append(connection_xml)
        
        # Close XML structure
        xml_lines.extend([
            '      </root>',
            '    </mxGraphModel>',
            '  </diagram>',
            '</mxfile>'
        ])
        
        # Join all lines to create the final XML
        final_xml = "\n".join(xml_lines)
        
        result = {
            "status": "success",
            "diagram_title": diagram_title,
            "drawio_xml": final_xml,
            "component_count": len(architecture_components),
            "vpc_count": len(vpcs),
            "usage_instructions": "To use this diagram, go to https://app.diagrams.net/, select 'File > Import From > XML', and paste the XML content."
        }
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating draw.io diagram: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to generate draw.io diagram",
            "message": str(e)
        })

def calculate_component_positions(components: List[Dict[str, Any]], vpcs: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Calculate positions for components in the diagram."""
    positions = {}
    
    # Set initial positions for VPCs
    vpc_x = 40
    vpc_y = 40
    for vpc_id in vpcs:
        positions[vpc_id] = {"x": vpc_x, "y": vpc_y}
        vpc_x += 600  # Space between VPCs
    
    # Set positions for components inside VPCs
    for vpc_id, vpc_info in vpcs.items():
        vpc_position = positions[vpc_id]
        component_x = vpc_position["x"] + 40
        component_y = vpc_position["y"] + 60
        
        for component_id in vpc_info["components"]:
            positions[component_id] = {"x": component_x, "y": component_y}
            component_x += 100
            
            # Wrap to next row if needed
            if component_x > vpc_position["x"] + 400:
                component_x = vpc_position["x"] + 40
                component_y += 100
    
    # Set positions for components not in VPCs
    non_vpc_components = [c for c in components if "vpc" not in c or not c["vpc"]]
    non_vpc_x = 40
    non_vpc_y = max([pos["y"] for pos in positions.values()], default=40) + 400
    
    for component in non_vpc_components:
        if component["id"] not in positions:
            positions[component["id"]] = {"x": non_vpc_x, "y": non_vpc_y}
            non_vpc_x += 150
            
            # Wrap to next row if needed
            if non_vpc_x > 1000:
                non_vpc_x = 40
                non_vpc_y += 150
    
    return positions

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
            "error": "Empty architecture components",
            "message": "Please provide a list of architecture components."
        })
    
    try:
        # This would be the actual implementation using python-pptx library
        # For now, we'll return a structured response with the diagram information
        
        # Group components by type
        components_by_type = {}
        for component in architecture_components:
            component_type = component.get("type", "Other")
            if component_type not in components_by_type:
                components_by_type[component_type] = []
            components_by_type[component_type].append(component)
        
        # Track VPCs for grouping
        vpcs = {}
        for component in architecture_components:
            if "vpc" in component and component["vpc"]:
                vpc_id = component["vpc"]
                if vpc_id not in vpcs:
                    vpc_info = next((c for c in architecture_components if c["id"] == vpc_id), None)
                    vpc_name = vpc_info["name"] if vpc_info and "name" in vpc_info else f"VPC-{vpc_id}"
                    vpcs[vpc_id] = {
                        "id": vpc_id,
                        "name": vpc_name,
                        "components": []
                    }
                
                if component["id"] != vpc_id:  # Don't add the VPC itself to its components
                    vpcs[vpc_id]["components"].append(component["id"])
        
        # Create a description of the slides that would be generated
        slides = [
            {
                "slide_type": "Title",
                "title": diagram_title,
                "subtitle": "AWS Architecture Diagram"
            },
            {
                "slide_type": "Overview",
                "title": "Architecture Overview",
                "content": "High-level overview of the AWS architecture"
            }
        ]
        
        # Add VPC slides
        for vpc_id, vpc_info in vpcs.items():
            vpc_components = [c for c in architecture_components if c["id"] in vpc_info["components"]]
            slides.append({
                "slide_type": "VPC",
                "title": f"{vpc_info['name']} Components",
                "vpc_name": vpc_info["name"],
                "component_count": len(vpc_components),
                "components": [c["name"] for c in vpc_components]
            })
        
        # Add component type slides
        for component_type, components in components_by_type.items():
            if component_type.lower() != "vpc":  # Skip VPC type as we already have VPC slides
                slides.append({
                    "slide_type": "ComponentType",
                    "title": f"{component_type} Services",
                    "component_type": component_type,
                    "component_count": len(components),
                    "components": [c["name"] for c in components]
                })
        
        # Add details slide
        slides.append({
            "slide_type": "Details",
            "title": "Architecture Details",
            "content": "Detailed information about the architecture components and their relationships"
        })
        
        result = {
            "status": "success",
            "diagram_title": diagram_title,
            "template_used": template_path if template_path else "Default template",
            "component_count": len(architecture_components),
            "vpc_count": len(vpcs),
            "slides": slides,
            "note": "In a real implementation, this would generate an actual PowerPoint file using python-pptx library.",
            "usage_instructions": "This response contains a description of the PowerPoint slides that would be generated."
        }
        
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error generating PowerPoint diagram: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to generate PowerPoint diagram",
            "message": str(e)
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
            "error": "Empty architecture components",
            "message": "Please provide a list of architecture components."
        })
    
    try:
        # Initialize validation results
        validation_results = {
            "status": "success",
            "validation_summary": {
                "total_issues": 0,
                "critical_issues": 0,
                "warning_issues": 0,
                "info_issues": 0
            },
            "issues": [],
            "recommendations": [],
            "best_practices_followed": []
        }
        
        # Check for VPC usage
        vpc_components = [c for c in architecture_components if c.get("type", "").lower() == "vpc"]
        if not vpc_components:
            validation_results["issues"].append({
                "severity": "warning",
                "issue": "No VPC defined",
                "description": "Architecture does not include a Virtual Private Cloud (VPC), which is recommended for network isolation and security.",
                "recommendation": "Add a VPC to isolate your resources and control network traffic."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["warning_issues"] += 1
        else:
            validation_results["best_practices_followed"].append({
                "practice": "VPC Usage",
                "description": "Architecture includes VPC for network isolation and security."
            })
        
        # Check for public-facing components
        public_facing_components = []
        for component in architecture_components:
            if "public" in component and component["public"] == True:
                public_facing_components.append(component)
        
        # Check for security groups or NACLs
        security_components = [c for c in architecture_components if c.get("type", "").lower() in ["security group", "nacl", "network acl"]]
        if not security_components and public_facing_components:
            validation_results["issues"].append({
                "severity": "critical",
                "issue": "Missing security groups or NACLs",
                "description": "Architecture has public-facing components but no security groups or NACLs defined.",
                "recommendation": "Add security groups to control inbound and outbound traffic to your instances."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["critical_issues"] += 1
        elif security_components:
            validation_results["best_practices_followed"].append({
                "practice": "Security Groups/NACLs",
                "description": "Architecture includes security groups or NACLs for network traffic control."
            })
        
        # Check for multi-AZ deployment
        has_multi_az = False
        for component in architecture_components:
            if "multi_az" in component and component["multi_az"] == True:
                has_multi_az = True
                break
        
        if not has_multi_az:
            validation_results["issues"].append({
                "severity": "warning",
                "issue": "No multi-AZ deployment",
                "description": "Architecture does not appear to use multi-AZ deployment for high availability.",
                "recommendation": "Consider deploying critical components across multiple Availability Zones for high availability."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["warning_issues"] += 1
        else:
            validation_results["best_practices_followed"].append({
                "practice": "Multi-AZ Deployment",
                "description": "Architecture uses multi-AZ deployment for high availability."
            })
        
        # Check for database backup
        database_components = [c for c in architecture_components if c.get("type", "").lower() in ["rds", "dynamodb", "aurora", "documentdb", "neptune"]]
        has_backup = False
        for component in architecture_components:
            if "backup" in component.get("type", "").lower() or "backup" in component.get("name", "").lower():
                has_backup = True
                break
        
        if database_components and not has_backup:
            validation_results["issues"].append({
                "severity": "warning",
                "issue": "No database backup strategy",
                "description": "Architecture includes databases but no clear backup strategy.",
                "recommendation": "Implement automated backups for your databases using AWS Backup or database-specific backup features."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["warning_issues"] += 1
        elif database_components and has_backup:
            validation_results["best_practices_followed"].append({
                "practice": "Database Backup",
                "description": "Architecture includes backup strategy for databases."
            })
        
        # Check for monitoring
        monitoring_components = [c for c in architecture_components if c.get("type", "").lower() in ["cloudwatch", "cloudtrail", "config"]]
        if not monitoring_components:
            validation_results["issues"].append({
                "severity": "info",
                "issue": "No monitoring services",
                "description": "Architecture does not include monitoring services like CloudWatch, CloudTrail, or Config.",
                "recommendation": "Add CloudWatch for monitoring and alerting, CloudTrail for API activity logging, and AWS Config for configuration tracking."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["info_issues"] += 1
        else:
            validation_results["best_practices_followed"].append({
                "practice": "Monitoring Services",
                "description": "Architecture includes monitoring services for observability and compliance."
            })
        
        # Check for load balancing
        compute_components = [c for c in architecture_components if c.get("type", "").lower() in ["ec2", "ecs", "eks"]]
        load_balancers = [c for c in architecture_components if c.get("type", "").lower() in ["elb", "alb", "nlb"]]
        if len(compute_components) > 1 and not load_balancers:
            validation_results["issues"].append({
                "severity": "warning",
                "issue": "Multiple compute instances without load balancer",
                "description": "Architecture has multiple compute instances but no load balancer.",
                "recommendation": "Add an Elastic Load Balancer (ALB, NLB, or CLB) to distribute traffic across your compute instances."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["warning_issues"] += 1
        elif compute_components and load_balancers:
            validation_results["best_practices_followed"].append({
                "practice": "Load Balancing",
                "description": "Architecture uses load balancers for traffic distribution and high availability."
            })
        
        # Check for auto scaling
        has_auto_scaling = False
        for component in architecture_components:
            if "auto scaling" in component.get("type", "").lower() or "autoscaling" in component.get("type", "").lower():
                has_auto_scaling = True
                break
        
        if compute_components and not has_auto_scaling:
            validation_results["issues"].append({
                "severity": "info",
                "issue": "No auto scaling",
                "description": "Architecture has compute instances but no auto scaling configuration.",
                "recommendation": "Add Auto Scaling Groups to automatically adjust capacity based on demand."
            })
            validation_results["validation_summary"]["total_issues"] += 1
            validation_results["validation_summary"]["info_issues"] += 1
        elif compute_components and has_auto_scaling:
            validation_results["best_practices_followed"].append({
                "practice": "Auto Scaling",
                "description": "Architecture uses auto scaling for elasticity and cost optimization."
            })
        
        # Add general recommendations
        validation_results["recommendations"].extend([
            {
                "category": "Security",
                "recommendation": "Implement AWS WAF for web applications to protect against common web exploits.",
                "importance": "high"
            },
            {
                "category": "Cost Optimization",
                "recommendation": "Use AWS Cost Explorer and Budgets to monitor and control your AWS spending.",
                "importance": "medium"
            },
            {
                "category": "Operational Excellence",
                "recommendation": "Implement Infrastructure as Code using AWS CloudFormation or AWS CDK.",
                "importance": "high"
            },
            {
                "category": "Reliability",
                "recommendation": "Design for failure by implementing retry logic, circuit breakers, and graceful degradation.",
                "importance": "high"
            },
            {
                "category": "Performance Efficiency",
                "recommendation": "Use Amazon CloudFront to cache content and reduce latency for global users.",
                "importance": "medium"
            }
        ])
        
        return json.dumps(validation_results)
    except Exception as e:
        logger.error(f"Error validating architecture: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": "Failed to validate architecture",
            "message": str(e)
        })