"""Architecture Validator Tool.

This tool validates AWS architectures against best practices, service compatibility,
and design principles.
"""

from typing import Dict, List, Optional, Any, Union, Set, Tuple
import json
import boto3
from datetime import datetime
from strands import tool


@tool
def validate_architecture(
    architecture_description: Dict[str, Any],
    validation_level: str = "standard",
    check_categories: Optional[List[str]] = None
) -> str:
    """Validate an AWS architecture against best practices and design principles.

    Args:
        architecture_description (Dict[str, Any]): A structured description of the architecture.
            Must include:
            - "components": List of AWS services/components
            - "connections": List of connections between components
        validation_level (str): Level of validation to perform. Options:
            - "basic": Check only critical issues
            - "standard": Check common best practices (default)
            - "strict": Check all best practices and recommendations
        check_categories (List[str], optional): Specific categories of checks to perform. Options:
            - "security": Security best practices
            - "reliability": High availability and fault tolerance
            - "performance": Performance optimization
            - "cost": Cost optimization
            - "operational": Operational excellence
            If not specified, all categories will be checked.

    Returns:
        str: JSON formatted validation results including issues, warnings, and recommendations
    """
    try:
        # Validate input
        _validate_architecture_description(architecture_description)
        
        # Set default check categories if not specified
        if not check_categories:
            check_categories = ["security", "reliability", "performance", "cost", "operational"]
        else:
            # Normalize categories
            check_categories = [category.lower() for category in check_categories]
        
        # Perform validation
        validation_results = {
            "valid": True,  # Will be set to False if critical issues are found
            "timestamp": datetime.utcnow().isoformat(),
            "validation_level": validation_level,
            "check_categories": check_categories,
            "summary": {
                "critical_issues": 0,
                "warnings": 0,
                "recommendations": 0
            },
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Run different validation checks based on categories
        if "security" in check_categories:
            _validate_security(architecture_description, validation_level, validation_results)
        
        if "reliability" in check_categories:
            _validate_reliability(architecture_description, validation_level, validation_results)
        
        if "performance" in check_categories:
            _validate_performance(architecture_description, validation_level, validation_results)
        
        if "cost" in check_categories:
            _validate_cost(architecture_description, validation_level, validation_results)
        
        if "operational" in check_categories:
            _validate_operational(architecture_description, validation_level, validation_results)
        
        # Update summary counts
        validation_results["summary"]["critical_issues"] = len(validation_results["issues"])
        validation_results["summary"]["warnings"] = len(validation_results["warnings"])
        validation_results["summary"]["recommendations"] = len(validation_results["recommendations"])
        
        # Update overall validity
        validation_results["valid"] = validation_results["summary"]["critical_issues"] == 0
        
        return json.dumps(validation_results, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to validate architecture: {str(e)}",
            "valid": False
        }, indent=2)


@tool
def check_service_compatibility(
    service1: str,
    service2: str,
    connection_type: Optional[str] = None
) -> str:
    """Check compatibility between two AWS services.

    Args:
        service1 (str): First AWS service name
        service2 (str): Second AWS service name
        connection_type (str, optional): Type of connection to check (e.g., "network", "data", "api")

    Returns:
        str: JSON formatted compatibility information including:
            - Whether the services are compatible
            - Integration methods
            - Best practices
            - Limitations
    """
    try:
        # Normalize service names
        service1 = service1.lower().strip()
        service2 = service2.lower().strip()
        
        # Get compatibility information
        compatibility_info = _get_service_compatibility(service1, service2, connection_type)
        
        # Add timestamp
        compatibility_info["timestamp"] = datetime.utcnow().isoformat()
        
        return json.dumps(compatibility_info, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to check compatibility between {service1} and {service2}: {str(e)}",
            "compatible": False
        }, indent=2)


@tool
def validate_against_well_architected(
    architecture_description: Dict[str, Any],
    pillars: Optional[List[str]] = None
) -> str:
    """Validate an architecture against the AWS Well-Architected Framework.

    Args:
        architecture_description (Dict[str, Any]): A structured description of the architecture
        pillars (List[str], optional): Specific Well-Architected pillars to check. Options:
            - "operational_excellence"
            - "security"
            - "reliability"
            - "performance_efficiency"
            - "cost_optimization"
            - "sustainability"
            If not specified, all pillars will be checked.

    Returns:
        str: JSON formatted validation results against the Well-Architected Framework
    """
    try:
        # Validate input
        _validate_architecture_description(architecture_description)
        
        # Set default pillars if not specified
        if not pillars:
            pillars = [
                "operational_excellence",
                "security",
                "reliability",
                "performance_efficiency",
                "cost_optimization",
                "sustainability"
            ]
        else:
            # Normalize pillars
            pillars = [pillar.lower() for pillar in pillars]
        
        # Perform validation against each pillar
        validation_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "pillars": pillars,
            "overall_score": 0,
            "pillar_scores": {},
            "findings": {}
        }
        
        total_score = 0
        for pillar in pillars:
            pillar_score, pillar_findings = _validate_pillar(architecture_description, pillar)
            validation_results["pillar_scores"][pillar] = pillar_score
            validation_results["findings"][pillar] = pillar_findings
            total_score += pillar_score
        
        # Calculate overall score (average of pillar scores)
        validation_results["overall_score"] = round(total_score / len(pillars), 1)
        
        # Add recommendations based on findings
        validation_results["recommendations"] = _generate_well_architected_recommendations(validation_results["findings"])
        
        return json.dumps(validation_results, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to validate against Well-Architected Framework: {str(e)}"
        }, indent=2)


@tool
def validate_service_configuration(
    service_type: str,
    configuration: Dict[str, Any]
) -> str:
    """Validate the configuration of a specific AWS service against best practices.

    Args:
        service_type (str): The AWS service type (e.g., "EC2", "S3", "RDS")
        configuration (Dict[str, Any]): Configuration parameters for the service

    Returns:
        str: JSON formatted validation results for the service configuration
    """
    try:
        # Normalize service type
        service_type = service_type.lower().strip()
        
        # Validate the service configuration
        validation_results = _validate_service_config(service_type, configuration)
        
        # Add timestamp
        validation_results["timestamp"] = datetime.utcnow().isoformat()
        
        return json.dumps(validation_results, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to validate {service_type} configuration: {str(e)}",
            "valid": False
        }, indent=2)


@tool
def check_architecture_pattern_compliance(
    architecture_description: Dict[str, Any],
    pattern_name: str
) -> str:
    """Check if an architecture follows a specific AWS architecture pattern.

    Args:
        architecture_description (Dict[str, Any]): A structured description of the architecture
        pattern_name (str): Name of the architecture pattern to check (e.g., "three-tier", "microservices", "serverless")

    Returns:
        str: JSON formatted compliance results including:
            - Whether the architecture follows the pattern
            - Missing components or connections
            - Recommendations to better align with the pattern
    """
    try:
        # Validate input
        _validate_architecture_description(architecture_description)
        
        # Normalize pattern name
        pattern_name = pattern_name.lower().strip()
        
        # Check compliance with the pattern
        compliance_results = _check_pattern_compliance(architecture_description, pattern_name)
        
        # Add timestamp
        compliance_results["timestamp"] = datetime.utcnow().isoformat()
        
        return json.dumps(compliance_results, indent=2)
    
    except Exception as e:
        return json.dumps({
            "error": f"Failed to check compliance with {pattern_name} pattern: {str(e)}",
            "compliant": False
        }, indent=2)


# Helper functions

def _validate_architecture_description(architecture_description: Dict[str, Any]) -> None:
    """Validate the architecture description."""
    if not isinstance(architecture_description, dict):
        raise ValueError("Architecture description must be a dictionary")
    
    if "components" not in architecture_description:
        raise ValueError("Architecture description must include 'components'")
    
    if not isinstance(architecture_description["components"], list):
        raise ValueError("Components must be a list")
    
    if len(architecture_description["components"]) == 0:
        raise ValueError("Components list cannot be empty")
    
    # Check that each component has the required fields
    for component in architecture_description["components"]:
        if not isinstance(component, dict):
            raise ValueError("Each component must be a dictionary")
        
        if "id" not in component:
            raise ValueError("Each component must have an 'id'")
        
        if "type" not in component:
            raise ValueError("Each component must have a 'type'")


def _validate_security(
    architecture_description: Dict[str, Any],
    validation_level: str,
    validation_results: Dict[str, Any]
) -> None:
    """Validate security aspects of the architecture."""
    components = architecture_description["components"]
    connections = architecture_description.get("connections", [])
    
    # Check for public-facing resources
    public_facing = []
    for component in components:
        component_type = component["type"].lower()
        properties = component.get("properties", {})
        
        if component_type in ["ec2", "rds", "elasticache", "redshift"]:
            if properties.get("publicly_accessible", False):
                public_facing.append(component["id"])
    
    # Check for direct database access from public internet
    for component in components:
        if component["type"].lower() in ["rds", "dynamodb", "elasticache", "redshift"]:
            for connection in connections:
                if connection["target"] == component["id"]:
                    source_component = next((c for c in components if c["id"] == connection["source"]), None)
                    if source_component and source_component.get("properties", {}).get("publicly_accessible", False):
                        validation_results["issues"].append({
                            "category": "security",
                            "severity": "critical",
                            "title": "Direct database access from public internet",
                            "description": f"Component {component['id']} ({component.get('name', component['id'])}) is directly accessible from a public-facing resource.",
                            "affected_components": [component["id"], connection["source"]],
                            "recommendation": "Use a private subnet for databases and access through application tier only."
                        })
    
    # Check for encryption
    for component in components:
        component_type = component["type"].lower()
        properties = component.get("properties", {})
        
        if component_type in ["s3", "rds", "dynamodb", "ebs"]:
            if not properties.get("encryption_enabled", False):
                if validation_level in ["standard", "strict"]:
                    validation_results["warnings"].append({
                        "category": "security",
                        "severity": "medium",
                        "title": f"Encryption not enabled for {component_type.upper()}",
                        "description": f"Component {component['id']} ({component.get('name', component['id'])}) does not have encryption enabled.",
                        "affected_components": [component["id"]],
                        "recommendation": f"Enable encryption for {component_type.upper()} to protect sensitive data."
                    })
    
    # Check for VPC usage
    has_vpc = any(component["type"].lower() == "vpc" for component in components)
    if not has_vpc:
        validation_results["warnings"].append({
            "category": "security",
            "severity": "medium",
            "title": "No VPC defined",
            "description": "The architecture does not include a VPC, which is recommended for network isolation.",
            "affected_components": [],
            "recommendation": "Define a VPC to isolate your resources and control network traffic."
        })
    
    # Check for IAM usage
    has_iam = any(component["type"].lower() == "iam" for component in components)
    if not has_iam and validation_level == "strict":
        validation_results["recommendations"].append({
            "category": "security",
            "severity": "low",
            "title": "No IAM components defined",
            "description": "The architecture does not explicitly include IAM roles or policies.",
            "affected_components": [],
            "recommendation": "Define IAM roles and policies to follow the principle of least privilege."
        })
    
    # Check for WAF usage for public-facing applications
    has_public_alb = any(
        component["type"].lower() == "alb" and component.get("properties", {}).get("scheme") == "internet-facing"
        for component in components
    )
    has_api_gateway = any(component["type"].lower() == "api gateway" for component in components)
    has_cloudfront = any(component["type"].lower() == "cloudfront" for component in components)
    
    has_waf = any(component["type"].lower() == "waf" for component in components)
    
    if (has_public_alb or has_api_gateway or has_cloudfront) and not has_waf and validation_level in ["standard", "strict"]:
        validation_results["warnings"].append({
            "category": "security",
            "severity": "medium",
            "title": "WAF not used for public-facing applications",
            "description": "The architecture includes public-facing web applications but does not use AWS WAF.",
            "affected_components": [],
            "recommendation": "Use AWS WAF to protect your web applications from common web exploits."
        })


def _validate_reliability(
    architecture_description: Dict[str, Any],
    validation_level: str,
    validation_results: Dict[str, Any]
) -> None:
    """Validate reliability aspects of the architecture."""
    components = architecture_description["components"]
    
    # Check for single points of failure
    for component in components:
        component_type = component["type"].lower()
        properties = component.get("properties", {})
        
        if component_type in ["ec2", "rds"]:
            # Check for EC2 in Auto Scaling Group
            if component_type == "ec2" and not properties.get("in_asg", False):
                validation_results["warnings"].append({
                    "category": "reliability",
                    "severity": "medium",
                    "title": "EC2 instance not in Auto Scaling Group",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) is not part of an Auto Scaling Group.",
                    "affected_components": [component["id"]],
                    "recommendation": "Use Auto Scaling Groups for EC2 instances to improve availability and fault tolerance."
                })
            
            # Check for RDS Multi-AZ
            if component_type == "rds" and not properties.get("multi_az", False):
                validation_results["warnings"].append({
                    "category": "reliability",
                    "severity": "medium",
                    "title": "RDS instance not Multi-AZ",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) is not configured for Multi-AZ deployment.",
                    "affected_components": [component["id"]],
                    "recommendation": "Enable Multi-AZ for RDS instances to improve availability and durability."
                })
    
    # Check for multi-AZ deployment
    az_count = set()
    for component in components:
        if "availability_zone" in component.get("properties", {}):
            az_count.add(component["properties"]["availability_zone"])
    
    if len(az_count) < 2:
        validation_results["warnings"].append({
            "category": "reliability",
            "severity": "medium",
            "title": "Resources not deployed across multiple AZs",
            "description": "The architecture does not deploy resources across multiple Availability Zones.",
            "affected_components": [],
            "recommendation": "Deploy resources across at least two Availability Zones to improve availability."
        })
    
    # Check for backup configurations
    for component in components:
        component_type = component["type"].lower()
        properties = component.get("properties", {})
        
        if component_type in ["rds", "dynamodb", "ebs", "efs"]:
            if not properties.get("backup_enabled", False) and validation_level in ["standard", "strict"]:
                validation_results["warnings"].append({
                    "category": "reliability",
                    "severity": "medium",
                    "title": f"Backups not enabled for {component_type.upper()}",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) does not have backups enabled.",
                    "affected_components": [component["id"]],
                    "recommendation": f"Enable automated backups for {component_type.upper()} to protect against data loss."
                })
    
    # Check for load balancing
    has_web_servers = any(component["type"].lower() == "ec2" for component in components)
    has_load_balancer = any(component["type"].lower() in ["elb", "alb", "nlb"] for component in components)
    
    if has_web_servers and not has_load_balancer and validation_level in ["standard", "strict"]:
        validation_results["recommendations"].append({
            "category": "reliability",
            "severity": "low",
            "title": "No load balancer for web servers",
            "description": "The architecture includes web servers but no load balancer.",
            "affected_components": [],
            "recommendation": "Use Elastic Load Balancing to distribute traffic across multiple instances for improved availability."
        })


def _validate_performance(
    architecture_description: Dict[str, Any],
    validation_level: str,
    validation_results: Dict[str, Any]
) -> None:
    """Validate performance aspects of the architecture."""
    components = architecture_description["components"]
    
    # Check for caching
    has_web_app = any(component["type"].lower() in ["ec2", "ecs", "elastic beanstalk"] for component in components)
    has_database = any(component["type"].lower() in ["rds", "dynamodb"] for component in components)
    has_cache = any(component["type"].lower() in ["elasticache", "cloudfront", "dax"] for component in components)
    
    if (has_web_app and has_database) and not has_cache and validation_level in ["standard", "strict"]:
        validation_results["recommendations"].append({
            "category": "performance",
            "severity": "low",
            "title": "No caching layer",
            "description": "The architecture includes web applications and databases but no caching layer.",
            "affected_components": [],
            "recommendation": "Consider adding ElastiCache or DAX to improve performance and reduce database load."
        })
    
    # Check for content delivery
    has_static_content = any(component["type"].lower() == "s3" for component in components)
    has_cloudfront = any(component["type"].lower() == "cloudfront" for component in components)
    
    if has_static_content and not has_cloudfront and validation_level in ["standard", "strict"]:
        validation_results["recommendations"].append({
            "category": "performance",
            "severity": "low",
            "title": "No CDN for static content",
            "description": "The architecture includes S3 for static content but no CloudFront distribution.",
            "affected_components": [],
            "recommendation": "Use CloudFront to deliver static content with lower latency and higher transfer speeds."
        })
    
    # Check for read replicas for databases
    for component in components:
        if component["type"].lower() == "rds":
            if not component.get("properties", {}).get("read_replica_count", 0) > 0 and validation_level == "strict":
                validation_results["recommendations"].append({
                    "category": "performance",
                    "severity": "low",
                    "title": "No read replicas for RDS",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) does not have read replicas.",
                    "affected_components": [component["id"]],
                    "recommendation": "Consider adding read replicas to offload read traffic from the primary database."
                })


def _validate_cost(
    architecture_description: Dict[str, Any],
    validation_level: str,
    validation_results: Dict[str, Any]
) -> None:
    """Validate cost optimization aspects of the architecture."""
    components = architecture_description["components"]
    
    # Check for reserved instances
    for component in components:
        if component["type"].lower() == "ec2":
            if not component.get("properties", {}).get("reserved_instance", False) and validation_level in ["standard", "strict"]:
                validation_results["recommendations"].append({
                    "category": "cost",
                    "severity": "low",
                    "title": "EC2 instance not using Reserved Instances",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) is not using Reserved Instances.",
                    "affected_components": [component["id"]],
                    "recommendation": "Consider using Reserved Instances for predictable workloads to reduce costs."
                })
    
    # Check for appropriate storage classes
    for component in components:
        if component["type"].lower() == "s3":
            if component.get("properties", {}).get("storage_class", "").lower() == "standard":
                validation_results["recommendations"].append({
                    "category": "cost",
                    "severity": "low",
                    "title": "S3 using Standard storage class",
                    "description": f"Component {component['id']} ({component.get('name', component['id'])}) is using S3 Standard storage class.",
                    "affected_components": [component["id"]],
                    "recommendation": "Consider using S3 Intelligent-Tiering, S3 Standard-IA, or S3 Glacier for data that is accessed less frequently."
                })
    
    # Check for auto scaling
    has_ec2 = any(component["type"].lower() == "ec2" for component in components)
    has_asg = any(component["type"].lower() == "auto scaling group" for component in components)
    
    if has_ec2 and not has_asg and validation_level in ["standard", "strict"]:
        validation_results["recommendations"].append({
            "category": "cost",
            "severity": "low",
            "title": "No Auto Scaling for EC2",
            "description": "The architecture includes EC2 instances but no Auto Scaling Groups.",
            "affected_components": [],
            "recommendation": "Use Auto Scaling to automatically adjust capacity based on demand, which can help optimize costs."
        })


def _validate_operational(
    architecture_description: Dict[str, Any],
    validation_level: str,
    validation_results: Dict[str, Any]
) -> None:
    """Validate operational excellence aspects of the architecture."""
    components = architecture_description["components"]
    
    # Check for monitoring
    has_cloudwatch = any(component["type"].lower() == "cloudwatch" for component in components)
    
    if not has_cloudwatch and validation_level in ["standard", "strict"]:
        validation_results["recommendations"].append({
            "category": "operational",
            "severity": "low",
            "title": "No monitoring solution",
            "description": "The architecture does not include CloudWatch or other monitoring components.",
            "affected_components": [],
            "recommendation": "Use CloudWatch to monitor your resources and applications."
        })
    
    # Check for logging
    has_cloudtrail = any(component["type"].lower() == "cloudtrail" for component in components)
    
    if not has_cloudtrail and validation_level == "strict":
        validation_results["recommendations"].append({
            "category": "operational",
            "severity": "low",
            "title": "No audit logging",
            "description": "The architecture does not include CloudTrail for AWS API activity logging.",
            "affected_components": [],
            "recommendation": "Enable CloudTrail to log, monitor, and retain account activity related to actions across your AWS infrastructure."
        })
    
    # Check for infrastructure as code
    has_cloudformation = any(component["type"].lower() in ["cloudformation", "terraform", "cdk"] for component in components)
    
    if not has_cloudformation and validation_level == "strict":
        validation_results["recommendations"].append({
            "category": "operational",
            "severity": "low",
            "title": "No infrastructure as code",
            "description": "The architecture does not include CloudFormation or other IaC components.",
            "affected_components": [],
            "recommendation": "Use infrastructure as code to automate provisioning and improve consistency and repeatability."
        })


def _get_service_compatibility(
    service1: str,
    service2: str,
    connection_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get compatibility information between two AWS services."""
    # Normalize service names
    service1 = service1.lower()
    service2 = service2.lower()
    
    # Sort services alphabetically to ensure consistent lookups
    if service1 > service2:
        service1, service2 = service2, service1
    
    # Create a key for the service pair
    service_pair = f"{service1}-{service2}"
    
    # Comprehensive compatibility database
    compatibility_db = {
        "ec2-rds": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "Direct network connection",
                    "description": "EC2 instances can connect to RDS databases over the network within a VPC",
                    "connection_types": ["network", "data"]
                }
            ],
            "best_practices": [
                "Place RDS in a private subnet",
                "Use security groups to restrict access to RDS",
                "Use IAM database authentication where supported",
                "Use connection pooling for efficient database connections"
            ],
            "limitations": [
                "EC2 and RDS must be in the same region to avoid cross-region data transfer costs",
                "EC2 must be in the same VPC as RDS or use VPC peering/Transit Gateway"
            ]
        },
        "ec2-s3": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "AWS SDK",
                    "description": "EC2 instances can access S3 using the AWS SDK",
                    "connection_types": ["api", "data"]
                },
                {
                    "method": "VPC Endpoint",
                    "description": "Use VPC Endpoints to access S3 without going through the public internet",
                    "connection_types": ["network", "data"]
                }
            ],
            "best_practices": [
                "Use IAM roles for EC2 to access S3",
                "Use VPC Endpoints for S3 to improve security and reduce data transfer costs",
                "Use S3 Transfer Acceleration for faster uploads from distant locations"
            ],
            "limitations": [
                "S3 bucket policies may restrict access from specific VPCs or IP ranges"
            ]
        },
        "lambda-dynamodb": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "AWS SDK",
                    "description": "Lambda functions can access DynamoDB using the AWS SDK",
                    "connection_types": ["api", "data"]
                }
            ],
            "best_practices": [
                "Use IAM roles to grant Lambda access to DynamoDB",
                "Consider DynamoDB Streams for event-driven architectures",
                "Use DynamoDB DAX for caching frequently accessed items",
                "Optimize Lambda functions to reuse connections"
            ],
            "limitations": [
                "Lambda has a default timeout of 15 minutes which may impact long-running operations",
                "Lambda concurrent executions can be limited which may impact DynamoDB throughput"
            ]
        },
        "lambda-rds": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "Direct connection",
                    "description": "Lambda functions can connect to RDS databases",
                    "connection_types": ["network", "data"]
                }
            ],
            "best_practices": [
                "Place Lambda in the same VPC as RDS",
                "Use connection pooling to manage database connections",
                "Consider RDS Proxy to handle connection management",
                "Be aware of Lambda cold start impact on database connections"
            ],
            "limitations": [
                "Lambda functions in a VPC incur additional cold start latency",
                "Lambda has limited execution time which may impact database operations"
            ]
        },
        "api gateway-lambda": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "Direct integration",
                    "description": "API Gateway can directly invoke Lambda functions",
                    "connection_types": ["api"]
                }
            ],
            "best_practices": [
                "Use API Gateway stage variables for environment-specific configurations",
                "Configure appropriate timeouts for Lambda integration",
                "Use API Gateway caching to reduce Lambda invocations",
                "Implement request validation in API Gateway"
            ],
            "limitations": [
                "API Gateway has a timeout limit of 29 seconds",
                "Payload size limits apply (10MB for REST APIs, 128KB for HTTP APIs)"
            ]
        },
        "cloudfront-s3": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "Origin configuration",
                    "description": "CloudFront can use S3 buckets as origins for content delivery",
                    "connection_types": ["network", "data"]
                }
            ],
            "best_practices": [
                "Use Origin Access Identity (OAI) to restrict S3 access to CloudFront",
                "Enable CloudFront compression for text-based content",
                "Configure appropriate cache behaviors based on content type",
                "Use S3 Transfer Acceleration for faster uploads to origin"
            ],
            "limitations": [
                "S3 website endpoints don't support OAI",
                "Dynamic content may not benefit from caching"
            ]
        },
        "elb-ec2": {
            "compatible": True,
            "integration_methods": [
                {
                    "method": "Target group",
                    "description": "ELB distributes traffic to EC2 instances in target groups",
                    "connection_types": ["network"]
                }
            ],
            "best_practices": [
                "Use Auto Scaling with ELB for dynamic capacity",
                "Configure health checks to ensure traffic goes to healthy instances",
                "Use connection draining to complete in-flight requests during scale-in",
                "Distribute instances across multiple Availability Zones"
            ],
            "limitations": [
                "Classic Load Balancers have fewer features than Application or Network Load Balancers",
                "EC2 instances must be in the same region as the ELB"
            ]
        }
        # More compatibility information would be added in a real implementation
    }
    
    # Check if we have compatibility information for these services
    if service_pair in compatibility_db:
        compatibility_info = compatibility_db[service_pair].copy()
        
        # Filter by connection type if specified
        if connection_type:
            connection_type = connection_type.lower()
            
            # Filter integration methods
            filtered_methods = []
            for method in compatibility_info["integration_methods"]:
                if connection_type in method.get("connection_types", []):
                    filtered_methods.append(method)
            
            compatibility_info["integration_methods"] = filtered_methods
        
        # Add service names to the result
        compatibility_info["service1"] = service1
        compatibility_info["service2"] = service2
        
        return compatibility_info
    
    # If no specific compatibility information, return a generic response
    return {
        "service1": service1,
        "service2": service2,
        "compatible": "Unknown",
        "integration_methods": [],
        "best_practices": [],
        "limitations": [],
        "notes": "No specific compatibility information available for these services. Most AWS services can work together through various integration patterns.",
        "suggestion": "Check AWS documentation for integration options between these services."
    }


def _validate_pillar(
    architecture_description: Dict[str, Any],
    pillar: str
) -> Tuple[float, List[Dict[str, Any]]]:
    """Validate architecture against a specific Well-Architected pillar."""
    # This is a simplified implementation
    # A real implementation would use the AWS Well-Architected Tool API
    
    components = architecture_description["components"]
    connections = architecture_description.get("connections", [])
    
    findings = []
    score = 0.0
    
    if pillar == "operational_excellence":
        # Check for monitoring and observability
        has_cloudwatch = any(component["type"].lower() == "cloudwatch" for component in components)
        has_cloudtrail = any(component["type"].lower() == "cloudtrail" for component in components)
        has_config = any(component["type"].lower() == "config" for component in components)
        
        if has_cloudwatch:
            score += 2.0
        else:
            findings.append({
                "question": "How do you monitor your resources?",
                "risk": "high",
                "description": "No monitoring solution detected. CloudWatch is recommended for monitoring AWS resources."
            })
        
        if has_cloudtrail:
            score += 1.5
        else:
            findings.append({
                "question": "How do you audit your resources?",
                "risk": "medium",
                "description": "No audit logging solution detected. CloudTrail is recommended for AWS API activity logging."
            })
        
        if has_config:
            score += 1.5
        else:
            findings.append({
                "question": "How do you track configuration changes?",
                "risk": "medium",
                "description": "No configuration tracking solution detected. AWS Config is recommended for tracking resource configurations."
            })
        
        # Check for infrastructure as code
        has_iac = any(component["type"].lower() in ["cloudformation", "terraform", "cdk"] for component in components)
        
        if has_iac:
            score += 2.0
        else:
            findings.append({
                "question": "How do you implement change?",
                "risk": "medium",
                "description": "No infrastructure as code solution detected. CloudFormation, Terraform, or CDK is recommended for managing infrastructure."
            })
        
        # Check for CI/CD
        has_cicd = any(component["type"].lower() in ["codepipeline", "codebuild", "codedeploy"] for component in components)
        
        if has_cicd:
            score += 1.0
        else:
            findings.append({
                "question": "How do you deploy your workloads?",
                "risk": "low",
                "description": "No CI/CD solution detected. AWS CodePipeline, CodeBuild, and CodeDeploy are recommended for automated deployments."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    elif pillar == "security":
        # Check for encryption
        encryption_count = 0
        encryption_eligible_count = 0
        
        for component in components:
            component_type = component["type"].lower()
            properties = component.get("properties", {})
            
            if component_type in ["s3", "rds", "dynamodb", "ebs", "efs"]:
                encryption_eligible_count += 1
                if properties.get("encryption_enabled", False):
                    encryption_count += 1
        
        if encryption_eligible_count > 0:
            encryption_score = (encryption_count / encryption_eligible_count) * 1.5
            score += encryption_score
            
            if encryption_count < encryption_eligible_count:
                findings.append({
                    "question": "How do you protect data at rest?",
                    "risk": "high",
                    "description": f"{encryption_eligible_count - encryption_count} out of {encryption_eligible_count} eligible resources do not have encryption enabled."
                })
        
        # Check for network security
        has_vpc = any(component["type"].lower() == "vpc" for component in components)
        has_security_groups = any(component["type"].lower() == "security group" for component in components)
        has_nacl = any(component["type"].lower() == "network acl" for component in components)
        
        if has_vpc:
            score += 1.0
        else:
            findings.append({
                "question": "How do you protect your networks?",
                "risk": "high",
                "description": "No VPC detected. VPCs are recommended for network isolation."
            })
        
        if has_security_groups:
            score += 1.0
        else:
            findings.append({
                "question": "How do you control traffic at the host level?",
                "risk": "high",
                "description": "No security groups detected. Security groups are recommended for controlling traffic to resources."
            })
        
        if has_nacl:
            score += 0.5
        
        # Check for IAM
        has_iam = any(component["type"].lower() == "iam" for component in components)
        
        if has_iam:
            score += 1.0
        else:
            findings.append({
                "question": "How do you manage identities?",
                "risk": "high",
                "description": "No IAM components detected. IAM is recommended for managing access to AWS resources."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    elif pillar == "reliability":
        # Check for multi-AZ
        az_count = set()
        for component in components:
            if "availability_zone" in component.get("properties", {}):
                az_count.add(component["properties"]["availability_zone"])
        
        if len(az_count) >= 2:
            score += 1.5
        else:
            findings.append({
                "question": "How do you design your workload to withstand component failures?",
                "risk": "high",
                "description": "Resources not deployed across multiple Availability Zones. Deploy resources across at least two AZs for high availability."
            })
        
        # Check for auto scaling
        has_asg = any(component["type"].lower() == "auto scaling group" for component in components)
        
        if has_asg:
            score += 1.0
        else:
            findings.append({
                "question": "How do you implement change?",
                "risk": "medium",
                "description": "No Auto Scaling Groups detected. Auto Scaling is recommended for handling changes in demand."
            })
        
        # Check for backups
        backup_count = 0
        backup_eligible_count = 0
        
        for component in components:
            component_type = component["type"].lower()
            properties = component.get("properties", {})
            
            if component_type in ["rds", "dynamodb", "ebs", "efs"]:
                backup_eligible_count += 1
                if properties.get("backup_enabled", False):
                    backup_count += 1
        
        if backup_eligible_count > 0:
            backup_score = (backup_count / backup_eligible_count) * 1.5
            score += backup_score
            
            if backup_count < backup_eligible_count:
                findings.append({
                    "question": "How do you back up your data?",
                    "risk": "high",
                    "description": f"{backup_eligible_count - backup_count} out of {backup_eligible_count} eligible resources do not have backups enabled."
                })
        
        # Check for disaster recovery
        has_dr = any(component.get("properties", {}).get("dr_enabled", False) for component in components)
        
        if has_dr:
            score += 1.0
        else:
            findings.append({
                "question": "How do you plan for disaster recovery?",
                "risk": "medium",
                "description": "No disaster recovery solution detected. Consider implementing a disaster recovery strategy."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    elif pillar == "performance_efficiency":
        # Check for appropriate instance types
        has_instance_types = all(
            "instance_type" in component.get("properties", {})
            for component in components
            if component["type"].lower() == "ec2"
        )
        
        if has_instance_types:
            score += 1.0
        else:
            findings.append({
                "question": "How do you select the best performing architecture?",
                "risk": "medium",
                "description": "Instance types not specified for all EC2 instances. Select appropriate instance types based on workload requirements."
            })
        
        # Check for caching
        has_cache = any(component["type"].lower() in ["elasticache", "cloudfront", "dax"] for component in components)
        
        if has_cache:
            score += 1.0
        else:
            findings.append({
                "question": "How do you use caching to improve performance?",
                "risk": "medium",
                "description": "No caching solution detected. Consider using ElastiCache, CloudFront, or DAX to improve performance."
            })
        
        # Check for content delivery
        has_cloudfront = any(component["type"].lower() == "cloudfront" for component in components)
        
        if has_cloudfront:
            score += 1.0
        else:
            findings.append({
                "question": "How do you deliver content efficiently?",
                "risk": "low",
                "description": "No content delivery solution detected. Consider using CloudFront to deliver content with lower latency."
            })
        
        # Check for database read replicas
        has_read_replicas = any(
            component.get("properties", {}).get("read_replica_count", 0) > 0
            for component in components
            if component["type"].lower() == "rds"
        )
        
        if has_read_replicas:
            score += 1.0
        else:
            findings.append({
                "question": "How do you design your database architecture?",
                "risk": "medium",
                "description": "No read replicas detected for databases. Consider adding read replicas to offload read traffic."
            })
        
        # Check for monitoring
        has_cloudwatch = any(component["type"].lower() == "cloudwatch" for component in components)
        
        if has_cloudwatch:
            score += 1.0
        else:
            findings.append({
                "question": "How do you monitor your resources?",
                "risk": "medium",
                "description": "No monitoring solution detected. CloudWatch is recommended for monitoring performance."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    elif pillar == "cost_optimization":
        # Check for right sizing
        has_right_sizing = all(
            "instance_type" in component.get("properties", {})
            for component in components
            if component["type"].lower() == "ec2"
        )
        
        if has_right_sizing:
            score += 1.0
        else:
            findings.append({
                "question": "How do you right size your resources?",
                "risk": "medium",
                "description": "Instance types not specified for all EC2 instances. Select appropriate instance types to avoid over-provisioning."
            })
        
        # Check for reserved instances
        has_reserved_instances = any(
            component.get("properties", {}).get("reserved_instance", False)
            for component in components
            if component["type"].lower() == "ec2"
        )
        
        if has_reserved_instances:
            score += 1.0
        else:
            findings.append({
                "question": "How do you use pricing models to reduce costs?",
                "risk": "medium",
                "description": "No Reserved Instances detected. Consider using Reserved Instances for predictable workloads."
            })
        
        # Check for auto scaling
        has_asg = any(component["type"].lower() == "auto scaling group" for component in components)
        
        if has_asg:
            score += 1.0
        else:
            findings.append({
                "question": "How do you match supply of resources with demand?",
                "risk": "medium",
                "description": "No Auto Scaling Groups detected. Auto Scaling can help optimize costs by adjusting capacity based on demand."
            })
        
        # Check for appropriate storage classes
        has_appropriate_storage = all(
            component.get("properties", {}).get("storage_class", "").lower() != "standard"
            for component in components
            if component["type"].lower() == "s3"
        )
        
        if has_appropriate_storage:
            score += 1.0
        else:
            findings.append({
                "question": "How do you select the most cost-effective storage solution?",
                "risk": "low",
                "description": "S3 Standard storage class detected. Consider using S3 Intelligent-Tiering, S3 Standard-IA, or S3 Glacier for data that is accessed less frequently."
            })
        
        # Check for cost monitoring
        has_cost_explorer = any(component["type"].lower() == "cost explorer" for component in components)
        has_budgets = any(component["type"].lower() == "budgets" for component in components)
        
        if has_cost_explorer or has_budgets:
            score += 1.0
        else:
            findings.append({
                "question": "How do you monitor usage and cost?",
                "risk": "medium",
                "description": "No cost monitoring solution detected. Consider using AWS Cost Explorer and AWS Budgets to monitor and control costs."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    elif pillar == "sustainability":
        # Check for right sizing
        has_right_sizing = all(
            "instance_type" in component.get("properties", {})
            for component in components
            if component["type"].lower() == "ec2"
        )
        
        if has_right_sizing:
            score += 1.0
        else:
            findings.append({
                "question": "How do you right size your resources?",
                "risk": "medium",
                "description": "Instance types not specified for all EC2 instances. Select appropriate instance types to avoid over-provisioning and reduce environmental impact."
            })
        
        # Check for auto scaling
        has_asg = any(component["type"].lower() == "auto scaling group" for component in components)
        
        if has_asg:
            score += 1.0
        else:
            findings.append({
                "question": "How do you match supply of resources with demand?",
                "risk": "medium",
                "description": "No Auto Scaling Groups detected. Auto Scaling can help reduce environmental impact by adjusting capacity based on demand."
            })
        
        # Check for appropriate storage classes
        has_appropriate_storage = all(
            component.get("properties", {}).get("storage_class", "").lower() != "standard"
            for component in components
            if component["type"].lower() == "s3"
        )
        
        if has_appropriate_storage:
            score += 1.0
        else:
            findings.append({
                "question": "How do you select the most sustainable storage solution?",
                "risk": "low",
                "description": "S3 Standard storage class detected. Consider using S3 Intelligent-Tiering or lifecycle policies to move data to more sustainable storage classes."
            })
        
        # Check for serverless
        has_serverless = any(component["type"].lower() in ["lambda", "fargate"] for component in components)
        
        if has_serverless:
            score += 1.0
        else:
            findings.append({
                "question": "How do you use managed services to reduce environmental impact?",
                "risk": "low",
                "description": "No serverless components detected. Consider using serverless services like Lambda and Fargate to reduce environmental impact."
            })
        
        # Check for regions with renewable energy
        green_regions = ["eu-west-1", "us-west-2", "us-east-2", "eu-central-1"]
        has_green_region = any(
            component.get("properties", {}).get("region", "") in green_regions
            for component in components
        )
        
        if has_green_region:
            score += 1.0
        else:
            findings.append({
                "question": "How do you select regions with renewable energy?",
                "risk": "low",
                "description": "No components in regions with high renewable energy usage. Consider deploying in regions like eu-west-1, us-west-2, us-east-2, or eu-central-1."
            })
        
        # Normalize score to 0-5 range
        score = min(score, 5.0)
    
    else:
        # Unknown pillar
        score = 0.0
        findings.append({
            "question": "Unknown pillar",
            "risk": "high",
            "description": f"Unknown Well-Architected pillar: {pillar}"
        })
    
    return score, findings


def _generate_well_architected_recommendations(findings: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Generate recommendations based on Well-Architected findings."""
    recommendations = []
    
    for pillar, pillar_findings in findings.items():
        for finding in pillar_findings:
            if finding.get("risk") in ["high", "medium"]:
                recommendations.append({
                    "pillar": pillar,
                    "priority": "high" if finding.get("risk") == "high" else "medium",
                    "title": finding.get("question", ""),
                    "description": finding.get("description", ""),
                    "impact": "Addressing this finding will improve your architecture's alignment with the AWS Well-Architected Framework."
                })
    
    # Sort recommendations by priority
    recommendations.sort(key=lambda x: 0 if x["priority"] == "high" else 1)
    
    return recommendations


def _validate_service_config(service_type: str, configuration: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the configuration of a specific AWS service."""
    # This is a simplified implementation
    # A real implementation would use AWS service-specific validation rules
    
    validation_results = {
        "service_type": service_type,
        "valid": True,
        "issues": [],
        "warnings": [],
        "recommendations": []
    }
    
    if service_type == "ec2":
        # Validate EC2 configuration
        if "instance_type" not in configuration:
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "Instance type not specified",
                "description": "Specify an instance type based on your workload requirements."
            })
        
        if "ami_id" not in configuration:
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "AMI ID not specified",
                "description": "Specify an AMI ID for the EC2 instance."
            })
        
        if not configuration.get("ebs_optimized", False):
            validation_results["recommendations"].append({
                "severity": "low",
                "title": "EBS optimization not enabled",
                "description": "Enable EBS optimization for better storage performance."
            })
        
        if not configuration.get("detailed_monitoring", False):
            validation_results["recommendations"].append({
                "severity": "low",
                "title": "Detailed monitoring not enabled",
                "description": "Enable detailed monitoring for better visibility into instance performance."
            })
    
    elif service_type == "s3":
        # Validate S3 configuration
        if not configuration.get("versioning", False):
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "Versioning not enabled",
                "description": "Enable versioning to protect against accidental deletion and provide data recovery."
            })
        
        if not configuration.get("encryption", False):
            validation_results["warnings"].append({
                "severity": "high",
                "title": "Encryption not enabled",
                "description": "Enable encryption to protect data at rest."
            })
        
        if configuration.get("public_access", False):
            validation_results["issues"].append({
                "severity": "high",
                "title": "Public access enabled",
                "description": "Disable public access unless specifically required for your use case."
            })
            validation_results["valid"] = False
        
        if configuration.get("storage_class", "").lower() == "standard":
            validation_results["recommendations"].append({
                "severity": "low",
                "title": "Standard storage class",
                "description": "Consider using S3 Intelligent-Tiering, S3 Standard-IA, or S3 Glacier for data that is accessed less frequently."
            })
    
    elif service_type == "rds":
        # Validate RDS configuration
        if not configuration.get("multi_az", False):
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "Multi-AZ not enabled",
                "description": "Enable Multi-AZ deployment for high availability."
            })
        
        if not configuration.get("backup_retention_period", 0) >= 7:
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "Backup retention period too short",
                "description": "Set backup retention period to at least 7 days."
            })
        
        if not configuration.get("encryption", False):
            validation_results["warnings"].append({
                "severity": "high",
                "title": "Encryption not enabled",
                "description": "Enable encryption to protect data at rest."
            })
        
        if configuration.get("publicly_accessible", False):
            validation_results["issues"].append({
                "severity": "high",
                "title": "Publicly accessible",
                "description": "Disable public accessibility unless specifically required for your use case."
            })
            validation_results["valid"] = False
        
        if not configuration.get("monitoring_interval", 0) > 0:
            validation_results["recommendations"].append({
                "severity": "low",
                "title": "Enhanced monitoring not enabled",
                "description": "Enable enhanced monitoring for better visibility into database performance."
            })
    
    elif service_type == "dynamodb":
        # Validate DynamoDB configuration
        if not configuration.get("point_in_time_recovery", False):
            validation_results["warnings"].append({
                "severity": "medium",
                "title": "Point-in-time recovery not enabled",
                "description": "Enable point-in-time recovery for data protection."
            })
        
        if not configuration.get("encryption", False):
            validation_results["warnings"].append({
                "severity": "high",
                "title": "Encryption not enabled",
                "description": "Enable encryption to protect data at rest."
            })
        
        if "read_capacity_units" in configuration and "write_capacity_units" in configuration:
            validation_results["recommendations"].append({
                "severity": "low",
                "title": "Provisioned capacity mode",
                "description": "Consider using on-demand capacity mode for unpredictable workloads."
            })
    
    else:
        # Unknown service type
        validation_results["warnings"].append({
            "severity": "medium",
            "title": "Unknown service type",
            "description": f"No validation rules available for service type: {service_type}"
        })
    
    # Update valid flag based on issues
    if validation_results["issues"]:
        validation_results["valid"] = False
    
    return validation_results


def _check_pattern_compliance(
    architecture_description: Dict[str, Any],
    pattern_name: str
) -> Dict[str, Any]:
    """Check if an architecture follows a specific AWS architecture pattern."""
    components = architecture_description["components"]
    connections = architecture_description.get("connections", [])
    
    # Get component types
    component_types = [component["type"].lower() for component in components]
    
    # Initialize compliance results
    compliance_results = {
        "pattern_name": pattern_name,
        "compliant": False,
        "missing_components": [],
        "missing_connections": [],
        "recommendations": []
    }
    
    if pattern_name == "three-tier":
        # Check for web tier components
        has_web_tier = any(ct in ["ec2", "elastic beanstalk", "ecs", "eks"] for ct in component_types)
        has_load_balancer = any(ct in ["elb", "alb", "nlb"] for ct in component_types)
        
        # Check for app tier components
        has_app_tier = any(ct in ["ec2", "elastic beanstalk", "ecs", "eks", "lambda"] for ct in component_types)
        
        # Check for data tier components
        has_data_tier = any(ct in ["rds", "dynamodb", "elasticache"] for ct in component_types)
        
        # Check for required components
        if not has_web_tier:
            compliance_results["missing_components"].append({
                "tier": "web",
                "description": "Web tier components (e.g., EC2, Elastic Beanstalk, ECS, EKS)",
                "recommendation": "Add web servers to handle user requests."
            })
        
        if not has_load_balancer:
            compliance_results["missing_components"].append({
                "tier": "web",
                "description": "Load balancer (e.g., ELB, ALB, NLB)",
                "recommendation": "Add a load balancer to distribute traffic to web servers."
            })
        
        if not has_app_tier:
            compliance_results["missing_components"].append({
                "tier": "app",
                "description": "Application tier components (e.g., EC2, Elastic Beanstalk, ECS, EKS, Lambda)",
                "recommendation": "Add application servers to process business logic."
            })
        
        if not has_data_tier:
            compliance_results["missing_components"].append({
                "tier": "data",
                "description": "Data tier components (e.g., RDS, DynamoDB, ElastiCache)",
                "recommendation": "Add databases to store application data."
            })
        
        # Check for connections between tiers
        has_web_to_app_connection = False
        has_app_to_data_connection = False
        
        for connection in connections:
            source_component = next((c for c in components if c["id"] == connection["source"]), None)
            target_component = next((c for c in components if c["id"] == connection["target"]), None)
            
            if not source_component or not target_component:
                continue
            
            source_type = source_component["type"].lower()
            target_type = target_component["type"].lower()
            
            # Check for web to app connection
            if source_type in ["elb", "alb", "nlb", "ec2"] and target_type in ["ec2", "elastic beanstalk", "ecs", "eks", "lambda"]:
                has_web_to_app_connection = True
            
            # Check for app to data connection
            if source_type in ["ec2", "elastic beanstalk", "ecs", "eks", "lambda"] and target_type in ["rds", "dynamodb", "elasticache"]:
                has_app_to_data_connection = True
        
        if has_web_tier and has_app_tier and not has_web_to_app_connection:
            compliance_results["missing_connections"].append({
                "source_tier": "web",
                "target_tier": "app",
                "description": "Connection from web tier to application tier",
                "recommendation": "Add connections from load balancer to application servers."
            })
        
        if has_app_tier and has_data_tier and not has_app_to_data_connection:
            compliance_results["missing_connections"].append({
                "source_tier": "app",
                "target_tier": "data",
                "description": "Connection from application tier to data tier",
                "recommendation": "Add connections from application servers to databases."
            })
        
        # Add recommendations
        if not has_web_tier or not has_app_tier or not has_data_tier:
            compliance_results["recommendations"].append({
                "title": "Implement all three tiers",
                "description": "A three-tier architecture should have separate web, application, and data tiers.",
                "priority": "high"
            })
        
        # Check for VPC and subnets
        has_vpc = any(ct == "vpc" for ct in component_types)
        has_subnets = any(ct == "subnet" for ct in component_types)
        
        if not has_vpc:
            compliance_results["recommendations"].append({
                "title": "Use VPC for network isolation",
                "description": "Define a VPC to isolate your three-tier architecture.",
                "priority": "medium"
            })
        
        if not has_subnets:
            compliance_results["recommendations"].append({
                "title": "Use separate subnets for each tier",
                "description": "Place web tier in public subnets, and application and data tiers in private subnets.",
                "priority": "medium"
            })
        
        # Check for security groups
        has_security_groups = any(ct == "security group" for ct in component_types)
        
        if not has_security_groups:
            compliance_results["recommendations"].append({
                "title": "Use security groups to control traffic between tiers",
                "description": "Define security groups to restrict traffic flow between tiers.",
                "priority": "medium"
            })
        
        # Determine compliance based on missing components and connections
        compliance_results["compliant"] = (
            has_web_tier and has_load_balancer and has_app_tier and has_data_tier and
            has_web_to_app_connection and has_app_to_data_connection
        )
    
    elif pattern_name == "microservices":
        # Check for API Gateway
        has_api_gateway = any(ct in ["api gateway", "appsync"] for ct in component_types)
        
        # Check for microservices
        has_container_services = any(ct in ["ecs", "eks", "fargate"] for ct in component_types)
        has_lambda = any(ct == "lambda" for ct in component_types)
        has_microservices = has_container_services or has_lambda
        
        # Check for service discovery
        has_service_discovery = any(ct in ["cloud map", "app mesh", "route 53"] for ct in component_types)
        
        # Check for messaging
        has_messaging = any(ct in ["sns", "sqs", "eventbridge", "kinesis", "msk"] for ct in component_types)
        
        # Check for data stores
        has_data_stores = any(ct in ["dynamodb", "rds", "elasticache", "s3"] for ct in component_types)
        
        # Check for required components
        if not has_api_gateway:
            compliance_results["missing_components"].append({
                "component": "api_gateway",
                "description": "API Gateway or AppSync",
                "recommendation": "Add an API Gateway to provide a unified entry point for clients."
            })
        
        if not has_microservices:
            compliance_results["missing_components"].append({
                "component": "microservices",
                "description": "Microservices (e.g., ECS, EKS, Fargate, Lambda)",
                "recommendation": "Add containerized services or Lambda functions to implement microservices."
            })
        
        if not has_service_discovery:
            compliance_results["missing_components"].append({
                "component": "service_discovery",
                "description": "Service discovery (e.g., Cloud Map, App Mesh, Route 53)",
                "recommendation": "Add service discovery to enable microservices to find and communicate with each other."
            })
        
        if not has_messaging:
            compliance_results["missing_components"].append({
                "component": "messaging",
                "description": "Messaging services (e.g., SNS, SQS, EventBridge, Kinesis, MSK)",
                "recommendation": "Add messaging services to enable asynchronous communication between microservices."
            })
        
        if not has_data_stores:
            compliance_results["missing_components"].append({
                "component": "data_stores",
                "description": "Data stores (e.g., DynamoDB, RDS, ElastiCache, S3)",
                "recommendation": "Add data stores for microservices to persist data."
            })
        
        # Add recommendations
        if not has_api_gateway:
            compliance_results["recommendations"].append({
                "title": "Add API Gateway",
                "description": "Use API Gateway to provide a unified entry point for clients to access microservices.",
                "priority": "high"
            })
        
        if not has_microservices:
            compliance_results["recommendations"].append({
                "title": "Implement microservices",
                "description": "Use containers (ECS/EKS) or Lambda functions to implement microservices.",
                "priority": "high"
            })
        
        if not has_messaging:
            compliance_results["recommendations"].append({
                "title": "Add messaging services",
                "description": "Use SNS, SQS, or EventBridge for asynchronous communication between microservices.",
                "priority": "medium"
            })
        
        # Check for monitoring
        has_monitoring = any(ct in ["cloudwatch", "x-ray"] for ct in component_types)
        
        if not has_monitoring:
            compliance_results["recommendations"].append({
                "title": "Add monitoring and tracing",
                "description": "Use CloudWatch and X-Ray to monitor and trace requests across microservices.",
                "priority": "medium"
            })
        
        # Determine compliance based on missing components
        compliance_results["compliant"] = (
            has_api_gateway and has_microservices and has_data_stores and
            (has_service_discovery or has_messaging)
        )
    
    elif pattern_name == "serverless":
        # Check for API Gateway
        has_api_gateway = any(ct in ["api gateway", "appsync"] for ct in component_types)
        
        # Check for Lambda
        has_lambda = any(ct == "lambda" for ct in component_types)
        
        # Check for event sources
        has_event_sources = any(ct in ["eventbridge", "sns", "sqs", "kinesis", "dynamodb streams"] for ct in component_types)
        
        # Check for data stores
        has_dynamodb = any(ct == "dynamodb" for ct in component_types)
        has_s3 = any(ct == "s3" for ct in component_types)
        has_aurora_serverless = any(ct == "aurora serverless" for ct in component_types)
        has_data_stores = has_dynamodb or has_s3 or has_aurora_serverless
        
        # Check for required components
        if not has_api_gateway:
            compliance_results["missing_components"].append({
                "component": "api_gateway",
                "description": "API Gateway or AppSync",
                "recommendation": "Add an API Gateway to provide a unified entry point for clients."
            })
        
        if not has_lambda:
            compliance_results["missing_components"].append({
                "component": "lambda",
                "description": "Lambda functions",
                "recommendation": "Add Lambda functions to implement serverless compute."
            })
        
        if not has_event_sources:
            compliance_results["missing_components"].append({
                "component": "event_sources",
                "description": "Event sources (e.g., EventBridge, SNS, SQS, Kinesis, DynamoDB Streams)",
                "recommendation": "Add event sources to trigger Lambda functions."
            })
        
        if not has_data_stores:
            compliance_results["missing_components"].append({
                "component": "data_stores",
                "description": "Serverless data stores (e.g., DynamoDB, S3, Aurora Serverless)",
                "recommendation": "Add serverless data stores to persist data."
            })
        
        # Add recommendations
        if not has_lambda:
            compliance_results["recommendations"].append({
                "title": "Use Lambda for compute",
                "description": "Replace traditional compute with Lambda functions for a serverless architecture.",
                "priority": "high"
            })
        
        if not has_dynamodb and not has_aurora_serverless:
            compliance_results["recommendations"].append({
                "title": "Use serverless databases",
                "description": "Use DynamoDB or Aurora Serverless for serverless database capabilities.",
                "priority": "medium"
            })
        
        # Check for Step Functions
        has_step_functions = any(ct == "step functions" for ct in component_types)
        
        if not has_step_functions:
            compliance_results["recommendations"].append({
                "title": "Consider Step Functions for orchestration",
                "description": "Use Step Functions to orchestrate complex workflows across multiple Lambda functions.",
                "priority": "low"
            })
        
        # Check for CloudWatch
        has_cloudwatch = any(ct == "cloudwatch" for ct in component_types)
        
        if not has_cloudwatch:
            compliance_results["recommendations"].append({
                "title": "Add monitoring with CloudWatch",
                "description": "Use CloudWatch to monitor Lambda functions and other serverless resources.",
                "priority": "medium"
            })
        
        # Determine compliance based on missing components
        compliance_results["compliant"] = (
            has_lambda and has_data_stores and (has_api_gateway or has_event_sources)
        )
    
    else:
        # Unknown pattern
        compliance_results["recommendations"].append({
            "title": "Unknown architecture pattern",
            "description": f"Pattern '{pattern_name}' is not recognized. Supported patterns include: three-tier, microservices, serverless.",
            "priority": "high"
        })
    
    return compliance_results