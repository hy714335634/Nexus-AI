"""
Calculate AWS service pricing based on configurations.

This tool estimates the cost of AWS services based on provided configurations and pricing models.
It supports multiple pricing models including on-demand, reserved instances, and savings plans,
providing comprehensive cost analysis for AWS service recommendations.

Examples:
    Input: AWS EC2 instance configurations with instance types and EBS volumes
    Output: Price estimates for on-demand and reserved instances with 1-year and 3-year terms
"""
from strands import tool
import json
from typing import Dict, Any, List, Optional, Union
import math

# AWS Pricing Data - Simplified for demonstration
# In a production environment, this would be fetched from AWS Price List API or a regularly updated database

# EC2 On-Demand Instance Pricing (hourly) - Beijing Region (cn-north-1) - USD
EC2_PRICING = {
    # General Purpose
    "t3.micro": {"on_demand": 0.0104, "reserved_1yr": 0.0066, "reserved_3yr": 0.0044},
    "t3.small": {"on_demand": 0.0208, "reserved_1yr": 0.0133, "reserved_3yr": 0.0089},
    "t3.medium": {"on_demand": 0.0416, "reserved_1yr": 0.0265, "reserved_3yr": 0.0177},
    "t3.large": {"on_demand": 0.0832, "reserved_1yr": 0.0530, "reserved_3yr": 0.0354},
    "t3.xlarge": {"on_demand": 0.1664, "reserved_1yr": 0.1060, "reserved_3yr": 0.0708},
    "t3.2xlarge": {"on_demand": 0.3328, "reserved_1yr": 0.2120, "reserved_3yr": 0.1416},
    
    "m5.large": {"on_demand": 0.113, "reserved_1yr": 0.0685, "reserved_3yr": 0.0456},
    "m5.xlarge": {"on_demand": 0.226, "reserved_1yr": 0.1370, "reserved_3yr": 0.0912},
    "m5.2xlarge": {"on_demand": 0.452, "reserved_1yr": 0.2740, "reserved_3yr": 0.1824},
    "m5.4xlarge": {"on_demand": 0.904, "reserved_1yr": 0.5480, "reserved_3yr": 0.3648},
    "m5.8xlarge": {"on_demand": 1.808, "reserved_1yr": 1.0960, "reserved_3yr": 0.7296},
    "m5.12xlarge": {"on_demand": 2.712, "reserved_1yr": 1.6440, "reserved_3yr": 1.0944},
    "m5.16xlarge": {"on_demand": 3.616, "reserved_1yr": 2.1920, "reserved_3yr": 1.4592},
    "m5.24xlarge": {"on_demand": 5.424, "reserved_1yr": 3.2880, "reserved_3yr": 2.1888},
    
    # Compute Optimized
    "c5.large": {"on_demand": 0.097, "reserved_1yr": 0.0588, "reserved_3yr": 0.0394},
    "c5.xlarge": {"on_demand": 0.194, "reserved_1yr": 0.1176, "reserved_3yr": 0.0788},
    "c5.2xlarge": {"on_demand": 0.388, "reserved_1yr": 0.2352, "reserved_3yr": 0.1576},
    "c5.4xlarge": {"on_demand": 0.776, "reserved_1yr": 0.4704, "reserved_3yr": 0.3152},
    "c5.9xlarge": {"on_demand": 1.746, "reserved_1yr": 1.0584, "reserved_3yr": 0.7092},
    "c5.12xlarge": {"on_demand": 2.328, "reserved_1yr": 1.4112, "reserved_3yr": 0.9456},
    "c5.18xlarge": {"on_demand": 3.492, "reserved_1yr": 2.1168, "reserved_3yr": 1.4184},
    "c5.24xlarge": {"on_demand": 4.656, "reserved_1yr": 2.8224, "reserved_3yr": 1.8912},
    
    # Memory Optimized
    "r5.large": {"on_demand": 0.149, "reserved_1yr": 0.0903, "reserved_3yr": 0.0605},
    "r5.xlarge": {"on_demand": 0.298, "reserved_1yr": 0.1807, "reserved_3yr": 0.1209},
    "r5.2xlarge": {"on_demand": 0.596, "reserved_1yr": 0.3613, "reserved_3yr": 0.2419},
    "r5.4xlarge": {"on_demand": 1.192, "reserved_1yr": 0.7226, "reserved_3yr": 0.4838},
    "r5.8xlarge": {"on_demand": 2.384, "reserved_1yr": 1.4451, "reserved_3yr": 0.9676},
    "r5.12xlarge": {"on_demand": 3.576, "reserved_1yr": 2.1677, "reserved_3yr": 1.4514},
    "r5.16xlarge": {"on_demand": 4.768, "reserved_1yr": 2.8903, "reserved_3yr": 1.9352},
    "r5.24xlarge": {"on_demand": 7.152, "reserved_1yr": 4.3354, "reserved_3yr": 2.9028},
    
    # Storage Optimized
    "i3.large": {"on_demand": 0.187, "reserved_1yr": 0.1134, "reserved_3yr": 0.0759},
    "i3.xlarge": {"on_demand": 0.374, "reserved_1yr": 0.2267, "reserved_3yr": 0.1519},
    "i3.2xlarge": {"on_demand": 0.748, "reserved_1yr": 0.4535, "reserved_3yr": 0.3037},
    "i3.4xlarge": {"on_demand": 1.496, "reserved_1yr": 0.9070, "reserved_3yr": 0.6075},
    "i3.8xlarge": {"on_demand": 2.992, "reserved_1yr": 1.8139, "reserved_3yr": 1.2149},
    "i3.16xlarge": {"on_demand": 5.984, "reserved_1yr": 3.6278, "reserved_3yr": 2.4299}
}

# EBS Storage Pricing (per GB-month) - Beijing Region
EBS_PRICING = {
    "gp3": {"price": 0.0114, "iops_price": 0.0068, "throughput_price": 0.0684},  # Base: 3000 IOPS, 125 MB/s
    "io1": {"price": 0.0138, "iops_price": 0.0072},  # Per provisioned IOPS
    "st1": {"price": 0.0054},
    "sc1": {"price": 0.0028}
}

# S3 Storage Pricing (per GB-month) - Beijing Region
S3_PRICING = {
    "standard": {"price": 0.0230, "request_price": 0.0000054},  # PUT/COPY/POST requests
    "standard_ia": {"price": 0.0138, "request_price": 0.0000108},
    "glacier": {"price": 0.0050, "retrieval_price": 0.0300}
}

# RDS Instance Pricing (hourly) - Beijing Region
RDS_PRICING = {
    "mysql_small": {"on_demand": 0.034, "reserved_1yr": 0.0218, "reserved_3yr": 0.0150},
    "mysql_medium": {"on_demand": 0.068, "reserved_1yr": 0.0435, "reserved_3yr": 0.0299},
    "mysql_large": {"on_demand": 0.136, "reserved_1yr": 0.0870, "reserved_3yr": 0.0598},
    "mysql_xlarge": {"on_demand": 0.272, "reserved_1yr": 0.1741, "reserved_3yr": 0.1197},
    
    "postgresql_small": {"on_demand": 0.042, "reserved_1yr": 0.0269, "reserved_3yr": 0.0185},
    "postgresql_medium": {"on_demand": 0.084, "reserved_1yr": 0.0537, "reserved_3yr": 0.0369},
    "postgresql_large": {"on_demand": 0.168, "reserved_1yr": 0.1075, "reserved_3yr": 0.0739},
    "postgresql_xlarge": {"on_demand": 0.336, "reserved_1yr": 0.2150, "reserved_3yr": 0.1478},
    
    "sqlserver_small": {"on_demand": 0.096, "reserved_1yr": 0.0614, "reserved_3yr": 0.0422},
    "sqlserver_medium": {"on_demand": 0.192, "reserved_1yr": 0.1229, "reserved_3yr": 0.0845},
    "sqlserver_large": {"on_demand": 0.384, "reserved_1yr": 0.2458, "reserved_3yr": 0.1690},
    "sqlserver_xlarge": {"on_demand": 0.768, "reserved_1yr": 0.4915, "reserved_3yr": 0.3379},
    
    "oracle_small": {"on_demand": 0.204, "reserved_1yr": 0.1306, "reserved_3yr": 0.0898},
    "oracle_medium": {"on_demand": 0.408, "reserved_1yr": 0.2611, "reserved_3yr": 0.1795},
    "oracle_large": {"on_demand": 0.816, "reserved_1yr": 0.5222, "reserved_3yr": 0.3590},
    "oracle_xlarge": {"on_demand": 1.632, "reserved_1yr": 1.0445, "reserved_3yr": 0.7181}
}

# Additional Services Pricing
NETWORK_PRICING = {
    "data_transfer_out": 0.123,  # per GB
    "elb_hourly": 0.025,
    "nat_gateway_hourly": 0.052,
    "vpn_connection_hourly": 0.05,
    "direct_connect_1gbps": 0.30  # per hour
}

@tool
def calculate_aws_pricing(aws_services: str, pricing_model: str = "on_demand") -> str:
    """
    Calculate AWS service pricing based on specifications.
    
    Args:
        aws_services (str): JSON string containing AWS service configurations
        pricing_model (str, optional): Pricing model to use 
                                      (on_demand, reserved_1yr, reserved_3yr, all)
                                      Default is on_demand
        
    Returns:
        str: JSON string with pricing information for each service and total costs
        
    Raises:
        ValueError: If input data cannot be parsed or pricing calculation fails
    """
    try:
        # Parse input JSON data
        matched_services = json.loads(aws_services)
        
        # Ensure matched_services is a list
        if not isinstance(matched_services, list):
            matched_services = [matched_services]
        
        pricing_results = []
        
        for service_match in matched_services:
            # Skip services with errors
            if "match_error" in service_match:
                pricing_results.append({
                    "original_product": service_match.get("original_product", {}),
                    "pricing_error": "Could not calculate pricing due to match error",
                    "partial_pricing": {}
                })
                continue
            
            # Calculate pricing based on service type
            aws_service_type = service_match.get("aws_service", "")
            
            if "EC2" in aws_service_type:
                service_pricing = _calculate_ec2_pricing(service_match, pricing_model)
            elif "EBS" in aws_service_type or "S3" in aws_service_type:
                service_pricing = _calculate_storage_pricing(service_match, pricing_model)
            elif "RDS" in aws_service_type or "Database" in aws_service_type:
                service_pricing = _calculate_database_pricing(service_match, pricing_model)
            elif "Network" in aws_service_type or "VPC" in aws_service_type or "Load" in aws_service_type:
                service_pricing = _calculate_network_pricing(service_match, pricing_model)
            else:
                # Generic pricing calculation
                service_pricing = _calculate_generic_pricing(service_match, pricing_model)
            
            pricing_results.append(service_pricing)
        
        # Calculate total costs across all services
        total_costs = _calculate_total_costs(pricing_results)
        
        # Add total costs to the response
        response = {
            "service_pricing": pricing_results,
            "total_costs": total_costs
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input data")
    except Exception as e:
        raise ValueError(f"Error calculating AWS pricing: {str(e)}")

def _calculate_ec2_pricing(service_match: Dict[str, Any], pricing_model: str) -> Dict[str, Any]:
    """Calculate pricing for EC2 instances and attached storage."""
    pricing_result = {
        "service_name": service_match.get("aws_service", "Amazon EC2"),
        "original_product": service_match.get("original_product", {}),
        "pricing": {}
    }
    
    # Get EC2 instance configuration
    config = service_match.get("configuration", {})
    instance_type = config.get("instance_type", "")
    
    # Initialize pricing with zeros in case instance type is not found
    on_demand_hourly = 0
    reserved_1yr_hourly = 0
    reserved_3yr_hourly = 0
    
    # Calculate EC2 instance pricing
    if instance_type and instance_type in EC2_PRICING:
        instance_pricing = EC2_PRICING[instance_type]
        on_demand_hourly = instance_pricing.get("on_demand", 0)
        reserved_1yr_hourly = instance_pricing.get("reserved_1yr", 0)
        reserved_3yr_hourly = instance_pricing.get("reserved_3yr", 0)
    
    # Calculate monthly and yearly costs
    hours_per_month = 730  # Average hours per month (365 days / 12 months * 24 hours)
    
    on_demand_monthly = on_demand_hourly * hours_per_month
    on_demand_yearly = on_demand_monthly * 12
    
    reserved_1yr_monthly = reserved_1yr_hourly * hours_per_month
    reserved_1yr_yearly = reserved_1yr_monthly * 12
    
    reserved_3yr_monthly = reserved_3yr_hourly * hours_per_month
    reserved_3yr_yearly = reserved_3yr_monthly * 12
    
    # Calculate storage pricing
    storage_pricing = {"on_demand": 0, "reserved_1yr": 0, "reserved_3yr": 0}
    storage_config = config.get("storage", {})
    
    if storage_config:
        storage_type = storage_config.get("type", "").lower()
        storage_size_gb = storage_config.get("size_gb", 0)
        
        # Extract EBS type from the storage type string
        ebs_type = "gp3"  # Default
        if "io1" in storage_type or "io2" in storage_type:
            ebs_type = "io1"
        elif "st1" in storage_type:
            ebs_type = "st1"
        elif "sc1" in storage_type:
            ebs_type = "sc1"
        
        # Calculate monthly storage cost
        if ebs_type in EBS_PRICING:
            storage_monthly_cost = storage_size_gb * EBS_PRICING[ebs_type]["price"]
            storage_yearly_cost = storage_monthly_cost * 12
            
            # Add to pricing
            storage_pricing["on_demand"] = storage_yearly_cost
            storage_pricing["reserved_1yr"] = storage_yearly_cost  # EBS has no reserved pricing
            storage_pricing["reserved_3yr"] = storage_yearly_cost
    
    # Compile pricing information
    pricing_result["pricing"] = {
        "on_demand": {
            "hourly": round(on_demand_hourly, 4),
            "monthly": round(on_demand_monthly, 2),
            "yearly": round(on_demand_yearly, 2),
            "storage_yearly": round(storage_pricing["on_demand"], 2),
            "total_yearly": round(on_demand_yearly + storage_pricing["on_demand"], 2)
        },
        "reserved_1yr": {
            "hourly": round(reserved_1yr_hourly, 4),
            "monthly": round(reserved_1yr_monthly, 2),
            "yearly": round(reserved_1yr_yearly, 2),
            "storage_yearly": round(storage_pricing["reserved_1yr"], 2),
            "total_yearly": round(reserved_1yr_yearly + storage_pricing["reserved_1yr"], 2)
        },
        "reserved_3yr": {
            "hourly": round(reserved_3yr_hourly, 4),
            "monthly": round(reserved_3yr_monthly, 2),
            "yearly": round(reserved_3yr_yearly, 2),
            "storage_yearly": round(storage_pricing["reserved_3yr"], 2),
            "total_yearly": round(reserved_3yr_yearly + storage_pricing["reserved_3yr"], 2)
        }
    }
    
    # Add saving percentages compared to on-demand
    if pricing_result["pricing"]["on_demand"]["total_yearly"] > 0:
        pricing_result["savings"] = {
            "reserved_1yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_1yr"]["total_yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["total_yearly"]) * 100, 1),
            "reserved_3yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_3yr"]["total_yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["total_yearly"]) * 100, 1)
        }
    
    # Add currency information
    pricing_result["currency"] = "USD"
    
    return pricing_result

def _calculate_storage_pricing(service_match: Dict[str, Any], pricing_model: str) -> Dict[str, Any]:
    """Calculate pricing for storage services (EBS, S3)."""
    pricing_result = {
        "service_name": service_match.get("aws_service", "AWS Storage"),
        "original_product": service_match.get("original_product", {}),
        "pricing": {}
    }
    
    # Get storage configuration
    config = service_match.get("configuration", {})
    service_type = config.get("service_type", "").lower()
    capacity_gb = config.get("capacity_gb", 0)
    
    # Initialize pricing
    monthly_cost = 0
    
    # Calculate based on storage type
    if "ebs" in service_type:
        # Determine EBS type
        ebs_type = "gp3"  # Default
        if "io1" in service_type or "io2" in service_type:
            ebs_type = "io1"
        elif "st1" in service_type:
            ebs_type = "st1"
        elif "sc1" in service_type:
            ebs_type = "sc1"
        
        # Calculate EBS cost
        if ebs_type in EBS_PRICING:
            monthly_cost = capacity_gb * EBS_PRICING[ebs_type]["price"]
    
    elif "s3" in service_type:
        # Determine S3 storage class
        s3_class = "standard"  # Default
        if "ia" in service_type or "infrequent" in service_type:
            s3_class = "standard_ia"
        elif "glacier" in service_type or "archive" in service_type:
            s3_class = "glacier"
        
        # Calculate S3 cost
        if s3_class in S3_PRICING:
            monthly_cost = capacity_gb * S3_PRICING[s3_class]["price"]
    
    # Calculate yearly cost
    yearly_cost = monthly_cost * 12
    
    # Compile pricing information (storage services don't have reserved pricing)
    pricing_result["pricing"] = {
        "on_demand": {
            "monthly": round(monthly_cost, 2),
            "yearly": round(yearly_cost, 2)
        },
        "reserved_1yr": {
            "monthly": round(monthly_cost, 2),  # Same as on-demand for storage
            "yearly": round(yearly_cost, 2)
        },
        "reserved_3yr": {
            "monthly": round(monthly_cost, 2),  # Same as on-demand for storage
            "yearly": round(yearly_cost, 2)
        }
    }
    
    # Add currency information
    pricing_result["currency"] = "USD"
    
    return pricing_result

def _calculate_database_pricing(service_match: Dict[str, Any], pricing_model: str) -> Dict[str, Any]:
    """Calculate pricing for database services (RDS, DynamoDB, etc.)."""
    pricing_result = {
        "service_name": service_match.get("aws_service", "AWS Database"),
        "original_product": service_match.get("original_product", {}),
        "pricing": {}
    }
    
    # Get database configuration
    config = service_match.get("configuration", {})
    service_type = config.get("service_type", "").lower()
    storage_gb = config.get("storage_gb", 100)  # Default to 100GB if not specified
    
    # Initialize pricing with zeros
    on_demand_hourly = 0
    reserved_1yr_hourly = 0
    reserved_3yr_hourly = 0
    
    # Determine database size based on storage
    db_size = "medium"  # Default
    if storage_gb < 50:
        db_size = "small"
    elif storage_gb > 500:
        db_size = "large"
    elif storage_gb > 1000:
        db_size = "xlarge"
    
    # Determine database engine
    db_engine = "mysql"  # Default
    if "oracle" in service_type:
        db_engine = "oracle"
    elif "sql server" in service_type or "sqlserver" in service_type:
        db_engine = "sqlserver"
    elif "postgres" in service_type:
        db_engine = "postgresql"
    
    # Create key for RDS pricing lookup
    rds_key = f"{db_engine}_{db_size}"
    
    # Calculate RDS instance pricing
    if rds_key in RDS_PRICING:
        instance_pricing = RDS_PRICING[rds_key]
        on_demand_hourly = instance_pricing.get("on_demand", 0)
        reserved_1yr_hourly = instance_pricing.get("reserved_1yr", 0)
        reserved_3yr_hourly = instance_pricing.get("reserved_3yr", 0)
    
    # Calculate monthly and yearly costs
    hours_per_month = 730  # Average hours per month
    
    on_demand_monthly = on_demand_hourly * hours_per_month
    on_demand_yearly = on_demand_monthly * 12
    
    reserved_1yr_monthly = reserved_1yr_hourly * hours_per_month
    reserved_1yr_yearly = reserved_1yr_monthly * 12
    
    reserved_3yr_monthly = reserved_3yr_hourly * hours_per_month
    reserved_3yr_yearly = reserved_3yr_monthly * 12
    
    # Calculate storage cost (simplified)
    storage_monthly_cost = storage_gb * 0.115  # General EBS cost for RDS
    storage_yearly_cost = storage_monthly_cost * 12
    
    # Compile pricing information
    pricing_result["pricing"] = {
        "on_demand": {
            "hourly": round(on_demand_hourly, 4),
            "monthly": round(on_demand_monthly, 2),
            "yearly": round(on_demand_yearly, 2),
            "storage_yearly": round(storage_yearly_cost, 2),
            "total_yearly": round(on_demand_yearly + storage_yearly_cost, 2)
        },
        "reserved_1yr": {
            "hourly": round(reserved_1yr_hourly, 4),
            "monthly": round(reserved_1yr_monthly, 2),
            "yearly": round(reserved_1yr_yearly, 2),
            "storage_yearly": round(storage_yearly_cost, 2),
            "total_yearly": round(reserved_1yr_yearly + storage_yearly_cost, 2)
        },
        "reserved_3yr": {
            "hourly": round(reserved_3yr_hourly, 4),
            "monthly": round(reserved_3yr_monthly, 2),
            "yearly": round(reserved_3yr_yearly, 2),
            "storage_yearly": round(storage_yearly_cost, 2),
            "total_yearly": round(reserved_3yr_yearly + storage_yearly_cost, 2)
        }
    }
    
    # Add saving percentages
    if pricing_result["pricing"]["on_demand"]["total_yearly"] > 0:
        pricing_result["savings"] = {
            "reserved_1yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_1yr"]["total_yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["total_yearly"]) * 100, 1),
            "reserved_3yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_3yr"]["total_yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["total_yearly"]) * 100, 1)
        }
    
    # Add currency information
    pricing_result["currency"] = "USD"
    
    return pricing_result

def _calculate_network_pricing(service_match: Dict[str, Any], pricing_model: str) -> Dict[str, Any]:
    """Calculate pricing for networking services."""
    pricing_result = {
        "service_name": service_match.get("aws_service", "AWS Networking"),
        "original_product": service_match.get("original_product", {}),
        "pricing": {}
    }
    
    # Get network configuration
    config = service_match.get("configuration", {})
    service_type = config.get("service_type", "").lower()
    
    # Initialize pricing
    monthly_cost = 0
    
    # Calculate based on network service type
    if "load balancer" in service_type or "elb" in service_type:
        # Elastic Load Balancer pricing
        elb_hourly = NETWORK_PRICING["elb_hourly"]
        monthly_cost = elb_hourly * 730  # 730 hours per month
    
    elif "vpn" in service_type:
        # VPN Connection pricing
        vpn_hourly = NETWORK_PRICING["vpn_connection_hourly"]
        monthly_cost = vpn_hourly * 730
    
    elif "direct connect" in service_type:
        # Direct Connect pricing
        dc_hourly = NETWORK_PRICING["direct_connect_1gbps"]
        monthly_cost = dc_hourly * 730
    
    elif "nat" in service_type:
        # NAT Gateway pricing
        nat_hourly = NETWORK_PRICING["nat_gateway_hourly"]
        monthly_cost = nat_hourly * 730
    
    else:
        # Generic VPC pricing - mostly free but add minimal cost for associated resources
        monthly_cost = 20  # Approximate cost for typical VPC resources
    
    # Calculate yearly cost
    yearly_cost = monthly_cost * 12
    
    # Compile pricing information (networking services typically don't have reserved pricing)
    pricing_result["pricing"] = {
        "on_demand": {
            "monthly": round(monthly_cost, 2),
            "yearly": round(yearly_cost, 2)
        },
        "reserved_1yr": {
            "monthly": round(monthly_cost, 2),  # Same as on-demand for networking
            "yearly": round(yearly_cost, 2)
        },
        "reserved_3yr": {
            "monthly": round(monthly_cost, 2),  # Same as on-demand for networking
            "yearly": round(yearly_cost, 2)
        }
    }
    
    # Add currency information
    pricing_result["currency"] = "USD"
    
    return pricing_result

def _calculate_generic_pricing(service_match: Dict[str, Any], pricing_model: str) -> Dict[str, Any]:
    """Calculate generic pricing for services not specifically handled."""
    pricing_result = {
        "service_name": service_match.get("aws_service", "AWS Service"),
        "original_product": service_match.get("original_product", {}),
        "pricing_note": "Estimated pricing for general service usage",
        "pricing": {}
    }
    
    # Get original product price as reference
    original_product = service_match.get("original_product", {})
    original_price = 0
    
    if "price" in original_product:
        price_info = original_product["price"]
        if isinstance(price_info, dict) and "amount" in price_info:
            original_price = price_info["amount"]
    
    # Estimate AWS cost as percentage of original price
    # Simplified assumption: AWS is typically 60-70% of on-premises cost
    estimated_yearly = original_price * 0.65
    estimated_monthly = estimated_yearly / 12
    
    # Further discount for reserved instances
    reserved_1yr_yearly = estimated_yearly * 0.75
    reserved_1yr_monthly = reserved_1yr_yearly / 12
    
    reserved_3yr_yearly = estimated_yearly * 0.60
    reserved_3yr_monthly = reserved_3yr_yearly / 12
    
    # Compile pricing information
    pricing_result["pricing"] = {
        "on_demand": {
            "monthly": round(estimated_monthly, 2),
            "yearly": round(estimated_yearly, 2)
        },
        "reserved_1yr": {
            "monthly": round(reserved_1yr_monthly, 2),
            "yearly": round(reserved_1yr_yearly, 2)
        },
        "reserved_3yr": {
            "monthly": round(reserved_3yr_monthly, 2),
            "yearly": round(reserved_3yr_yearly, 2)
        }
    }
    
    # Add saving percentages
    if pricing_result["pricing"]["on_demand"]["yearly"] > 0:
        pricing_result["savings"] = {
            "reserved_1yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_1yr"]["yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["yearly"]) * 100, 1),
            "reserved_3yr_vs_on_demand": round((1 - pricing_result["pricing"]["reserved_3yr"]["yearly"] / 
                                            pricing_result["pricing"]["on_demand"]["yearly"]) * 100, 1)
        }
    
    # Add currency information
    pricing_result["currency"] = "USD"
    
    # Add note about estimation
    pricing_result["estimation_note"] = "This is an approximate estimate based on typical cost savings patterns."
    
    return pricing_result

def _calculate_total_costs(pricing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate total costs across all services."""
    # Initialize totals
    total_on_demand_yearly = 0
    total_reserved_1yr_yearly = 0
    total_reserved_3yr_yearly = 0
    
    # Sum up costs from all services
    for result in pricing_results:
        pricing = result.get("pricing", {})
        
        # On-demand
        if "on_demand" in pricing:
            if "total_yearly" in pricing["on_demand"]:
                total_on_demand_yearly += pricing["on_demand"]["total_yearly"]
            elif "yearly" in pricing["on_demand"]:
                total_on_demand_yearly += pricing["on_demand"]["yearly"]
        
        # Reserved 1 year
        if "reserved_1yr" in pricing:
            if "total_yearly" in pricing["reserved_1yr"]:
                total_reserved_1yr_yearly += pricing["reserved_1yr"]["total_yearly"]
            elif "yearly" in pricing["reserved_1yr"]:
                total_reserved_1yr_yearly += pricing["reserved_1yr"]["yearly"]
        
        # Reserved 3 year
        if "reserved_3yr" in pricing:
            if "total_yearly" in pricing["reserved_3yr"]:
                total_reserved_3yr_yearly += pricing["reserved_3yr"]["total_yearly"]
            elif "yearly" in pricing["reserved_3yr"]:
                total_reserved_3yr_yearly += pricing["reserved_3yr"]["yearly"]
    
    # Calculate monthly costs
    total_on_demand_monthly = total_on_demand_yearly / 12
    total_reserved_1yr_monthly = total_reserved_1yr_yearly / 12
    total_reserved_3yr_monthly = total_reserved_3yr_yearly / 12
    
    # Calculate savings percentages
    savings_1yr = 0
    savings_3yr = 0
    
    if total_on_demand_yearly > 0:
        savings_1yr = (1 - total_reserved_1yr_yearly / total_on_demand_yearly) * 100
        savings_3yr = (1 - total_reserved_3yr_yearly / total_on_demand_yearly) * 100
    
    # Return total costs
    return {
        "on_demand": {
            "monthly": round(total_on_demand_monthly, 2),
            "yearly": round(total_on_demand_yearly, 2)
        },
        "reserved_1yr": {
            "monthly": round(total_reserved_1yr_monthly, 2),
            "yearly": round(total_reserved_1yr_yearly, 2),
            "savings_percentage": round(savings_1yr, 1)
        },
        "reserved_3yr": {
            "monthly": round(total_reserved_3yr_monthly, 2),
            "yearly": round(total_reserved_3yr_yearly, 2),
            "savings_percentage": round(savings_3yr, 1)
        },
        "currency": "USD"
    }