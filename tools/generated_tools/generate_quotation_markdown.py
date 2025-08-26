"""
Generate Markdown formatted quotation document.

This tool formats all gathered information into a professional Markdown quotation table,
following the standard template structure for AWS service quotations. It organizes the 
information into compute resources, storage resources, networking resources (if applicable),
TCO comparison, additional value propositions, and notes.

Examples:
    Input: Product data, AWS matches, pricing data, cost comparison
    Output: Complete Markdown formatted quotation document
"""
from strands import tool
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Constants for additional value propositions and notes
ADDITIONAL_VALUES = [
    "弹性扩展能力：根据业务需求灵活调整资源规模，按需付费",
    "降低运维负担：AWS管理基础设施，减少硬件维护成本和人力投入",
    "提高可靠性：利用AWS全球基础设施和多可用区架构提升系统可用性",
    "加速创新：快速部署新服务和功能，缩短上市时间",
    "全球覆盖：根据需要在全球范围内快速部署应用和服务"
]

STANDARD_NOTES = [
    "价格基于最新公开的AWS定价信息，实际费用可能因地区、使用量和特殊优惠而异",
    "未包含数据传输费用，实际部署时需考虑此因素",
    "本地部署成本包含硬件、维护、电力冷却、数据中心和人员费用估算",
    "建议咨询AWS销售代表获取适合您企业的精确定价和折扣方案"
]

# Currency conversion rates (approximate)
CURRENCY_CONVERSION = {
    "USD": {"CNY": 7.15, "EUR": 0.92, "GBP": 0.79},
    "CNY": {"USD": 0.14, "EUR": 0.13, "GBP": 0.11},
    "EUR": {"USD": 1.09, "CNY": 7.8, "GBP": 0.86},
    "GBP": {"USD": 1.27, "CNY": 9.05, "EUR": 1.16}
}

@tool
def generate_quotation_markdown(product_data: str, aws_matches: str, pricing_data: str, cost_comparison: str) -> str:
    """
    Generate Markdown formatted quotation document.
    
    Args:
        product_data (str): JSON string containing original product specifications
        aws_matches (str): JSON string containing matched AWS services
        pricing_data (str): JSON string containing AWS pricing information
        cost_comparison (str): JSON string containing cost comparison data
        
    Returns:
        str: Markdown formatted quotation document
        
    Raises:
        ValueError: If input data cannot be parsed or markdown generation fails
    """
    try:
        # Parse input JSON data
        products = json.loads(product_data)
        matches = json.loads(aws_matches)
        pricing = json.loads(pricing_data)
        comparison = json.loads(cost_comparison)
        
        # Ensure products is a list
        if not isinstance(products, list):
            products = [products]
        
        # Generate the markdown document
        markdown = _generate_markdown_document(products, matches, pricing, comparison)
        
        return markdown
    
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON input data: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error generating markdown quotation: {str(e)}")

def _generate_markdown_document(products: List[Dict[str, Any]], 
                              matches: List[Dict[str, Any]], 
                              pricing: Dict[str, Any],
                              comparison: Dict[str, Any]) -> str:
    """Generate the complete markdown document."""
    # Get pricing service results
    pricing_results = pricing.get("service_pricing", [])
    
    # Determine currency to use
    currency = _determine_currency(products, pricing, comparison)
    currency_symbol = _get_currency_symbol(currency)
    
    # Begin building the markdown document
    markdown = "# AWS云服务报价单\n\n"
    
    # Group products by type
    compute_products = []
    storage_products = []
    network_products = []
    database_products = []
    
    for i, product in enumerate(products):
        product_type = product.get("type", "").lower()
        
        # Skip products with errors
        if "error" in product:
            continue
        
        # Create product entry with all relevant data
        product_entry = {
            "product": product,
            "match": matches[i] if i < len(matches) else {},
            "pricing": pricing_results[i] if i < len(pricing_results) else {}
        }
        
        # Group by type
        if product_type == "server":
            compute_products.append(product_entry)
        elif product_type == "storage":
            storage_products.append(product_entry)
        elif product_type == "network":
            network_products.append(product_entry)
        elif product_type == "database":
            database_products.append(product_entry)
        else:
            # Default to compute if type is unknown
            compute_products.append(product_entry)
    
    # Generate tables for each product type
    if compute_products:
        markdown += _generate_resource_table("计算资源对照表", compute_products, currency, currency_symbol)
    
    if storage_products:
        markdown += _generate_resource_table("存储资源对照表", storage_products, currency, currency_symbol)
    
    if network_products:
        markdown += _generate_resource_table("网络资源对照表", network_products, currency, currency_symbol)
    
    if database_products:
        markdown += _generate_resource_table("数据库资源对照表", database_products, currency, currency_symbol)
    
    # Generate TCO comparison table
    markdown += _generate_tco_table(comparison, currency, currency_symbol)
    
    # Add additional values
    markdown += "## 4. 附加价值\n"
    for value in ADDITIONAL_VALUES:
        markdown += f"- {value}\n"
    markdown += "\n"
    
    # Add notes
    markdown += "## 5. 备注\n"
    for note in STANDARD_NOTES:
        markdown += f"- {note}\n"
    
    # Add generation timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown += f"\n*报价生成时间: {current_time}*\n"
    
    return markdown

def _generate_resource_table(title: str, products: List[Dict[str, Any]], 
                            currency: str, currency_symbol: str) -> str:
    """Generate a resource comparison table for a specific type of resources."""
    section_number = "1"
    if "计算" in title:
        section_number = "1"
    elif "存储" in title:
        section_number = "2"
    elif "网络" in title:
        section_number = "3"
    elif "数据库" in title:
        section_number = "4"
    
    markdown = f"## {section_number}. {title}\n\n"
    markdown += "| 本地设备 | AWS替代服务 | 规格对照 | 本地价格 | AWS价格(按需) | AWS价格(预留1年) | 潜在节约 |\n"
    markdown += "|---------|------------|---------|--------|-------------|---------------|--------|\n"
    
    for product_entry in products:
        product = product_entry["product"]
        match = product_entry["match"]
        pricing_info = product_entry["pricing"]
        
        # Get product name and price
        product_name = product.get("product_name", "未知产品")
        product_price = 0
        price_info = product.get("price", {})
        
        if isinstance(price_info, dict) and "amount" in price_info:
            product_price = price_info["amount"]
            product_currency = price_info.get("currency", "CNY")
            
            # Convert to target currency if different
            if product_currency != currency:
                product_price = _convert_currency(product_price, product_currency, currency)
        
        # Get AWS service name and configuration
        aws_service = "未匹配服务"
        config = {}
        
        if "aws_service" in match:
            aws_service = match["aws_service"]
            config = match.get("configuration", {})
        
        # Get pricing information
        on_demand_price = 0
        reserved_price = 0
        savings_percent = 0
        
        if "pricing" in pricing_info:
            if "on_demand" in pricing_info["pricing"] and "yearly" in pricing_info["pricing"]["on_demand"]:
                on_demand_price = pricing_info["pricing"]["on_demand"]["yearly"]
            
            if "reserved_1yr" in pricing_info["pricing"] and "yearly" in pricing_info["pricing"]["reserved_1yr"]:
                reserved_price = pricing_info["pricing"]["reserved_1yr"]["yearly"]
            
            if "savings" in pricing_info and "reserved_1yr_vs_on_demand" in pricing_info["savings"]:
                savings_percent = pricing_info["savings"]["reserved_1yr_vs_on_demand"]
        
        # Format prices
        product_price_str = f"{currency_symbol}{_format_price(product_price)}"
        on_demand_price_str = f"{currency_symbol}{_format_price(on_demand_price)}/年"
        reserved_price_str = f"{currency_symbol}{_format_price(reserved_price)}/年"
        
        # Generate specifications comparison text
        specs_comparison = _generate_specs_comparison(product, config)
        
        # Calculate savings percentage compared to on-premises
        if product_price > 0:
            savings_vs_onprem = (product_price - reserved_price) / product_price * 100
            savings_str = f"{int(savings_vs_onprem)}% (预留)"
        else:
            savings_str = f"{int(savings_percent)}% (比按需)"
        
        # Add table row
        markdown += f"| {product_name} | {aws_service} | {specs_comparison} | {product_price_str} | {on_demand_price_str} | {reserved_price_str} | {savings_str} |\n"
    
    markdown += "\n"
    return markdown

def _generate_specs_comparison(product: Dict[str, Any], aws_config: Dict[str, Any]) -> str:
    """Generate a formatted string comparing on-premises specs with AWS specs."""
    # Get product specs
    product_specs = product.get("specs", {})
    product_type = product.get("type", "").lower()
    
    # Generate comparison based on product type
    if product_type == "server":
        # Get AWS instance details
        instance_type = aws_config.get("instance_type", "")
        vcpu = aws_config.get("vcpu", "")
        memory = aws_config.get("memory_gb", "")
        
        # Get storage details
        storage_info = ""
        if "storage" in aws_config:
            storage_type = aws_config["storage"].get("type", "")
            storage_size = aws_config["storage"].get("size_gb", "")
            storage_info = f"<br>+ {storage_size}GB {storage_type}"
        
        return f"{instance_type} ({vcpu} vCPU, {memory}GB RAM){storage_info}"
    
    elif product_type == "storage":
        service_type = aws_config.get("service_type", "")
        capacity = aws_config.get("capacity_gb", "")
        
        if capacity >= 1024:
            capacity_str = f"{capacity/1024:.1f}TB"
        else:
            capacity_str = f"{capacity}GB"
        
        return f"{service_type}<br>{capacity_str}"
    
    elif product_type == "network":
        service_type = aws_config.get("service_type", "")
        features = aws_config.get("features", [])
        
        feature_str = ""
        if features and len(features) > 0:
            feature_str = f"<br>{features[0]}"
            if len(features) > 1:
                feature_str += f" + {len(features)-1}项功能"
        
        return f"{service_type}{feature_str}"
    
    elif product_type == "database":
        service_type = aws_config.get("service_type", "")
        storage = aws_config.get("storage_gb", "")
        
        storage_str = ""
        if storage:
            if storage >= 1024:
                storage_str = f"<br>{storage/1024:.1f}TB 存储"
            else:
                storage_str = f"<br>{storage}GB 存储"
        
        return f"{service_type}{storage_str}"
    
    else:
        # Generic specs comparison
        return "AWS等效配置"

def _generate_tco_table(comparison: Dict[str, Any], currency: str, currency_symbol: str) -> str:
    """Generate the TCO comparison table."""
    markdown = "## 3. 总体拥有成本(TCO)对比\n\n"
    markdown += "| 时间范围 | 本地部署总成本 | AWS云服务总成本 | 潜在节约 |\n"
    markdown += "|---------|-------------|--------------|--------|\n"
    
    # Get TCO comparison data
    tco_comparison = comparison.get("tco_comparison", {})
    savings_summary = comparison.get("savings_summary", {})
    
    # Sort time periods
    time_periods = sorted([int(period.split("_")[0]) for period in tco_comparison.keys()])
    
    for period in time_periods:
        period_key = f"{period}_year"
        
        if period_key in tco_comparison:
            period_data = tco_comparison[period_key]
            summary_data = savings_summary.get(period_key, {})
            
            # Get on-premises and AWS costs
            on_prem_cost = period_data["on_premises"]["total_tco"]
            
            # Get AWS cost from best option
            aws_cost = period_data["aws"]["best_option"]["cost"]
            aws_option = period_data["aws"]["best_option"]["option"]
            
            # Get savings
            savings_amount = on_prem_cost - aws_cost
            savings_percent = 0
            
            if on_prem_cost > 0:
                savings_percent = (savings_amount / on_prem_cost) * 100
            
            # Format values
            on_prem_cost_str = f"{currency_symbol}{_format_price(on_prem_cost)}"
            aws_cost_str = f"{currency_symbol}{_format_price(aws_cost)}"
            savings_str = f"{currency_symbol}{_format_price(savings_amount)} ({int(savings_percent)}%)"
            
            # Add pricing model indicator to AWS cost
            aws_option_label = ""
            if aws_option == "on_demand":
                aws_option_label = " (按需)"
            elif aws_option == "reserved_1yr":
                aws_option_label = " (预留1年)"
            elif aws_option == "reserved_3yr":
                aws_option_label = " (预留3年)"
            
            # Add row
            markdown += f"| {period}年 | {on_prem_cost_str} | {aws_cost_str}{aws_option_label} | {savings_str} |\n"
    
    markdown += "\n"
    return markdown

def _determine_currency(products: List[Dict[str, Any]], 
                      pricing: Dict[str, Any],
                      comparison: Dict[str, Any]) -> str:
    """Determine which currency to use for output."""
    # Default to CNY
    output_currency = "CNY"
    
    # Check pricing data
    if "service_pricing" in pricing and pricing["service_pricing"]:
        for service in pricing["service_pricing"]:
            if "currency" in service:
                # If we find USD, prefer it
                if service["currency"] == "USD":
                    return "USD"
                output_currency = service["currency"]
    
    # Check products data
    for product in products:
        price_info = product.get("price", {})
        if isinstance(price_info, dict) and "currency" in price_info:
            # If we find CNY, prefer it since output is in Chinese
            if price_info["currency"] == "CNY":
                return "CNY"
            output_currency = price_info["currency"]
    
    return output_currency

def _get_currency_symbol(currency: str) -> str:
    """Get currency symbol for a given currency code."""
    currency_symbols = {
        "USD": "$",
        "CNY": "¥",
        "EUR": "€",
        "GBP": "£"
    }
    
    return currency_symbols.get(currency, "¥")

def _format_price(price: float) -> str:
    """Format price with thousands separator and fixed decimal places."""
    if price >= 1000000:
        # Format as millions
        return f"{price/1000000:.2f}M"
    elif price >= 1000:
        # Format with thousands separator
        return f"{price:,.2f}".rstrip('0').rstrip('.')
    else:
        # Format with 2 decimal places
        return f"{price:.2f}".rstrip('0').rstrip('.')

def _convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """Convert amount from one currency to another."""
    # Return original amount if currencies are the same
    if from_currency == to_currency:
        return amount
    
    # Return original amount if conversion rate not found
    if from_currency not in CURRENCY_CONVERSION or to_currency not in CURRENCY_CONVERSION[from_currency]:
        return amount
    
    # Convert using approximate rates
    return amount * CURRENCY_CONVERSION[from_currency][to_currency]