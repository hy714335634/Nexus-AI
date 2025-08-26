"""
Generate cost comparison between on-premises and AWS services.

This tool compares the total cost of ownership (TCO) between on-premises IT infrastructure and 
AWS cloud services. It considers multiple time periods, factors in additional costs for 
on-premises infrastructure, and calculates potential savings over time.

Examples:
    Input: On-premises costs and AWS costs for multiple services
    Output: Comprehensive cost comparison with TCO analysis for different time periods
"""
from strands import tool
import json
from typing import Dict, Any, List, Optional, Union
import math

# Default additional cost factors for on-premises infrastructure
DEFAULT_ON_PREM_FACTORS = {
    "maintenance_percentage": 0.15,  # Annual maintenance cost as percentage of hardware cost
    "power_cooling_percentage": 0.10,  # Annual power and cooling cost as percentage of hardware cost
    "datacenter_percentage": 0.08,  # Annual datacenter space cost as percentage of hardware cost
    "staff_percentage": 0.20,  # Annual staff cost as percentage of hardware cost
    "hardware_lifespan_years": 3,  # Typical hardware replacement cycle
    "hardware_residual_value_percentage": 0.10,  # Residual value of hardware after lifespan
}

@tool
def compare_costs(on_prem_costs: str, aws_costs: str, time_periods: List[int] = [1, 3]) -> str:
    """
    Generate cost comparison between on-premises and AWS services.
    
    Args:
        on_prem_costs (str): JSON string containing on-premises cost data
        aws_costs (str): JSON string containing AWS services cost data
        time_periods (list, optional): Time periods in years for comparison
                                       Default is [1, 3]
        
    Returns:
        str: JSON string with cost comparison data including potential savings
        
    Raises:
        ValueError: If input data cannot be parsed or comparison calculation fails
    """
    try:
        # Parse input JSON data
        on_prem_data = json.loads(on_prem_costs)
        aws_data = json.loads(aws_costs)
        
        # Make sure time_periods has at least one value
        if not time_periods:
            time_periods = [1, 3]
        
        # Calculate comprehensive comparison
        comparison_data = _generate_comprehensive_comparison(on_prem_data, aws_data, time_periods)
        
        # Return JSON string
        return json.dumps(comparison_data, ensure_ascii=False, indent=2)
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input data")
    except Exception as e:
        raise ValueError(f"Error generating cost comparison: {str(e)}")

def _generate_comprehensive_comparison(on_prem_data: Dict[str, Any], aws_data: Dict[str, Any], 
                                      time_periods: List[int]) -> Dict[str, Any]:
    """Generate comprehensive cost comparison data."""
    # Extract original products from on_prem_data
    original_products = []
    
    # Check if on_prem_data contains service_pricing list
    if "service_pricing" in on_prem_data:
        for service in on_prem_data["service_pricing"]:
            if "original_product" in service:
                original_products.append(service["original_product"])
    # If direct list of products
    elif isinstance(on_prem_data, list):
        for item in on_prem_data:
            if isinstance(item, dict):
                original_products.append(item)
    # If single product
    elif isinstance(on_prem_data, dict):
        original_products.append(on_prem_data)
    
    # Initialize comparison result
    comparison_result = {
        "time_periods": time_periods,
        "currency": "USD",  # Default, will be updated if specified in input
        "product_comparisons": [],
        "tco_comparison": {}
    }
    
    # Get AWS pricing data
    aws_pricing_data = {}
    aws_total_costs = None
    
    if "service_pricing" in aws_data:
        aws_pricing_data = {idx: service for idx, service in enumerate(aws_data["service_pricing"])}
        aws_total_costs = aws_data.get("total_costs", {})
    
    # Generate comparison for each original product
    for idx, product in enumerate(original_products):
        # Create product comparison
        product_comparison = _generate_product_comparison(product, aws_pricing_data.get(idx, {}), time_periods)
        comparison_result["product_comparisons"].append(product_comparison)
    
    # Generate overall TCO comparison
    comparison_result["tco_comparison"] = _generate_tco_comparison(original_products, aws_total_costs, time_periods)
    
    # Add savings summary
    comparison_result["savings_summary"] = _generate_savings_summary(comparison_result["tco_comparison"])
    
    return comparison_result

def _generate_product_comparison(on_prem_product: Dict[str, Any], aws_service: Dict[str, Any], 
                                time_periods: List[int]) -> Dict[str, Any]:
    """Generate comparison between on-premises product and AWS service."""
    product_comparison = {
        "on_premises_product": {
            "name": on_prem_product.get("product_name", "Unknown Product"),
            "type": on_prem_product.get("type", "Unknown"),
            "specs": on_prem_product.get("specs", {})
        },
        "aws_service": {
            "name": aws_service.get("service_name", "AWS Service"),
            "configuration": aws_service.get("configuration", {})
        },
        "cost_comparison": {}
    }
    
    # Extract on-premises price
    on_prem_price = 0
    price_info = on_prem_product.get("price", {})
    if isinstance(price_info, dict) and "amount" in price_info:
        on_prem_price = price_info["amount"]
        product_comparison["on_premises_product"]["price"] = {
            "amount": on_prem_price,
            "currency": price_info.get("currency", "CNY")
        }
    
    # Extract AWS pricing
    aws_pricing = {}
    if "pricing" in aws_service:
        aws_pricing = aws_service["pricing"]
        product_comparison["aws_service"]["pricing"] = aws_pricing
    
    # Calculate costs for each time period
    for period in time_periods:
        # Calculate on-premises TCO for this product
        on_prem_tco = _calculate_onprem_tco(on_prem_price, period)
        
        # Get AWS costs for this period
        aws_costs = {
            "on_demand": 0,
            "reserved_1yr": 0,
            "reserved_3yr": 0
        }
        
        if aws_pricing:
            # On-demand
            if "on_demand" in aws_pricing:
                if "total_yearly" in aws_pricing["on_demand"]:
                    aws_costs["on_demand"] = aws_pricing["on_demand"]["total_yearly"] * period
                elif "yearly" in aws_pricing["on_demand"]:
                    aws_costs["on_demand"] = aws_pricing["on_demand"]["yearly"] * period
            
            # Reserved 1-year
            if "reserved_1yr" in aws_pricing:
                # For multi-year periods, calculate correctly with renewals
                if period <= 1:
                    if "total_yearly" in aws_pricing["reserved_1yr"]:
                        aws_costs["reserved_1yr"] = aws_pricing["reserved_1yr"]["total_yearly"]
                    elif "yearly" in aws_pricing["reserved_1yr"]:
                        aws_costs["reserved_1yr"] = aws_pricing["reserved_1yr"]["yearly"]
                else:
                    if "total_yearly" in aws_pricing["reserved_1yr"]:
                        aws_costs["reserved_1yr"] = aws_pricing["reserved_1yr"]["total_yearly"] * period
                    elif "yearly" in aws_pricing["reserved_1yr"]:
                        aws_costs["reserved_1yr"] = aws_pricing["reserved_1yr"]["yearly"] * period
            
            # Reserved 3-year
            if "reserved_3yr" in aws_pricing:
                # For multi-year periods, calculate correctly with renewals
                if period <= 3:
                    if "total_yearly" in aws_pricing["reserved_3yr"]:
                        aws_costs["reserved_3yr"] = aws_pricing["reserved_3yr"]["total_yearly"] * period
                    elif "yearly" in aws_pricing["reserved_3yr"]:
                        aws_costs["reserved_3yr"] = aws_pricing["reserved_3yr"]["yearly"] * period
                else:
                    # Calculate full 3-year terms plus remainder
                    full_terms = period // 3
                    remainder = period % 3
                    
                    if "total_yearly" in aws_pricing["reserved_3yr"]:
                        aws_costs["reserved_3yr"] = (aws_pricing["reserved_3yr"]["total_yearly"] * 3 * full_terms + 
                                                  aws_pricing["reserved_3yr"]["total_yearly"] * remainder)
                    elif "yearly" in aws_pricing["reserved_3yr"]:
                        aws_costs["reserved_3yr"] = (aws_pricing["reserved_3yr"]["yearly"] * 3 * full_terms + 
                                                  aws_pricing["reserved_3yr"]["yearly"] * remainder)
        
        # Calculate savings for each pricing model
        savings = {
            "on_demand": {
                "amount": on_prem_tco - aws_costs["on_demand"],
                "percentage": 0
            },
            "reserved_1yr": {
                "amount": on_prem_tco - aws_costs["reserved_1yr"],
                "percentage": 0
            },
            "reserved_3yr": {
                "amount": on_prem_tco - aws_costs["reserved_3yr"],
                "percentage": 0
            }
        }
        
        # Calculate savings percentages
        if on_prem_tco > 0:
            savings["on_demand"]["percentage"] = (savings["on_demand"]["amount"] / on_prem_tco) * 100
            savings["reserved_1yr"]["percentage"] = (savings["reserved_1yr"]["amount"] / on_prem_tco) * 100
            savings["reserved_3yr"]["percentage"] = (savings["reserved_3yr"]["amount"] / on_prem_tco) * 100
        
        # Add to comparison
        product_comparison["cost_comparison"][f"{period}_year"] = {
            "on_premises_tco": on_prem_tco,
            "aws_costs": aws_costs,
            "savings": savings
        }
    
    return product_comparison

def _calculate_onprem_tco(hardware_cost: float, years: int) -> float:
    """Calculate on-premises total cost of ownership."""
    # If hardware cost is zero, return zero TCO
    if hardware_cost <= 0:
        return 0
    
    # Get hardware lifespan
    lifespan = DEFAULT_ON_PREM_FACTORS["hardware_lifespan_years"]
    
    # Calculate number of hardware refresh cycles needed
    refresh_cycles = math.ceil(years / lifespan)
    
    # Calculate residual value at the end of the period
    remaining_life_fraction = (refresh_cycles * lifespan - years) / lifespan
    residual_value = 0
    
    if remaining_life_fraction > 0:
        residual_value = hardware_cost * DEFAULT_ON_PREM_FACTORS["hardware_residual_value_percentage"] * remaining_life_fraction
    
    # Calculate total hardware cost including refreshes, minus residual value
    total_hardware_cost = hardware_cost * refresh_cycles - residual_value
    
    # Calculate annual operational costs
    annual_maintenance = hardware_cost * DEFAULT_ON_PREM_FACTORS["maintenance_percentage"]
    annual_power_cooling = hardware_cost * DEFAULT_ON_PREM_FACTORS["power_cooling_percentage"]
    annual_datacenter = hardware_cost * DEFAULT_ON_PREM_FACTORS["datacenter_percentage"]
    annual_staff = hardware_cost * DEFAULT_ON_PREM_FACTORS["staff_percentage"]
    
    annual_operational_cost = annual_maintenance + annual_power_cooling + annual_datacenter + annual_staff
    
    # Calculate total TCO
    total_tco = total_hardware_cost + (annual_operational_cost * years)
    
    return total_tco

def _generate_tco_comparison(original_products: List[Dict[str, Any]], 
                            aws_total_costs: Optional[Dict[str, Any]], 
                            time_periods: List[int]) -> Dict[str, Any]:
    """Generate overall TCO comparison."""
    # Initialize TCO comparison
    tco_comparison = {}
    
    # Calculate total on-premises hardware cost
    total_hardware_cost = 0
    for product in original_products:
        price_info = product.get("price", {})
        if isinstance(price_info, dict) and "amount" in price_info:
            total_hardware_cost += price_info["amount"]
    
    # Calculate TCO for each time period
    for period in time_periods:
        on_prem_tco = _calculate_onprem_tco(total_hardware_cost, period)
        
        # Initialize AWS costs
        aws_costs = {
            "on_demand": 0,
            "reserved_1yr": 0,
            "reserved_3yr": 0
        }
        
        # Use provided AWS total costs if available
        if aws_total_costs:
            if "on_demand" in aws_total_costs and "yearly" in aws_total_costs["on_demand"]:
                aws_costs["on_demand"] = aws_total_costs["on_demand"]["yearly"] * period
            
            if "reserved_1yr" in aws_total_costs and "yearly" in aws_total_costs["reserved_1yr"]:
                # For multi-year periods, calculate correctly with renewals
                aws_costs["reserved_1yr"] = aws_total_costs["reserved_1yr"]["yearly"] * period
            
            if "reserved_3yr" in aws_total_costs and "yearly" in aws_total_costs["reserved_3yr"]:
                # For multi-year periods, calculate correctly with renewals
                if period <= 3:
                    aws_costs["reserved_3yr"] = aws_total_costs["reserved_3yr"]["yearly"] * period
                else:
                    # Calculate full 3-year terms plus remainder
                    full_terms = period // 3
                    remainder = period % 3
                    yearly_cost = aws_total_costs["reserved_3yr"]["yearly"]
                    
                    aws_costs["reserved_3yr"] = yearly_cost * 3 * full_terms + yearly_cost * remainder
        
        # Calculate savings
        savings = {
            "on_demand": {
                "amount": on_prem_tco - aws_costs["on_demand"],
                "percentage": 0
            },
            "reserved_1yr": {
                "amount": on_prem_tco - aws_costs["reserved_1yr"],
                "percentage": 0
            },
            "reserved_3yr": {
                "amount": on_prem_tco - aws_costs["reserved_3yr"],
                "percentage": 0
            }
        }
        
        # Calculate savings percentages
        if on_prem_tco > 0:
            savings["on_demand"]["percentage"] = (savings["on_demand"]["amount"] / on_prem_tco) * 100
            savings["reserved_1yr"]["percentage"] = (savings["reserved_1yr"]["amount"] / on_prem_tco) * 100
            savings["reserved_3yr"]["percentage"] = (savings["reserved_3yr"]["amount"] / on_prem_tco) * 100
        
        # Add to TCO comparison
        tco_comparison[f"{period}_year"] = {
            "on_premises": {
                "hardware_cost": total_hardware_cost,
                "operational_costs": on_prem_tco - total_hardware_cost,
                "total_tco": on_prem_tco
            },
            "aws": {
                "on_demand_cost": aws_costs["on_demand"],
                "reserved_1yr_cost": aws_costs["reserved_1yr"],
                "reserved_3yr_cost": aws_costs["reserved_3yr"],
                "best_option": _get_best_aws_option(aws_costs)
            },
            "savings": {
                "best_savings": _get_best_savings(savings),
                "details": savings
            }
        }
    
    return tco_comparison

def _get_best_aws_option(aws_costs: Dict[str, float]) -> Dict[str, Any]:
    """Determine the best AWS pricing option."""
    best_option_name = "on_demand"
    best_option_cost = aws_costs["on_demand"]
    
    if aws_costs["reserved_1yr"] < best_option_cost:
        best_option_name = "reserved_1yr"
        best_option_cost = aws_costs["reserved_1yr"]
    
    if aws_costs["reserved_3yr"] < best_option_cost:
        best_option_name = "reserved_3yr"
        best_option_cost = aws_costs["reserved_3yr"]
    
    return {
        "option": best_option_name,
        "cost": best_option_cost
    }

def _get_best_savings(savings: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Determine the best savings option."""
    best_option_name = "on_demand"
    best_option_amount = savings["on_demand"]["amount"]
    best_option_percentage = savings["on_demand"]["percentage"]
    
    if savings["reserved_1yr"]["amount"] > best_option_amount:
        best_option_name = "reserved_1yr"
        best_option_amount = savings["reserved_1yr"]["amount"]
        best_option_percentage = savings["reserved_1yr"]["percentage"]
    
    if savings["reserved_3yr"]["amount"] > best_option_amount:
        best_option_name = "reserved_3yr"
        best_option_amount = savings["reserved_3yr"]["amount"]
        best_option_percentage = savings["reserved_3yr"]["percentage"]
    
    return {
        "option": best_option_name,
        "amount": best_option_amount,
        "percentage": best_option_percentage
    }

def _generate_savings_summary(tco_comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a summary of potential savings across all time periods."""
    savings_summary = {}
    
    for period_key, period_data in tco_comparison.items():
        best_savings = period_data["savings"]["best_savings"]
        
        savings_summary[period_key] = {
            "best_option": period_data["aws"]["best_option"]["option"],
            "on_premises_cost": period_data["on_premises"]["total_tco"],
            "aws_cost": period_data["aws"]["best_option"]["cost"],
            "savings_amount": best_savings["amount"],
            "savings_percentage": best_savings["percentage"]
        }
    
    return savings_summary