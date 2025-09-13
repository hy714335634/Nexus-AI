"""
Pricing Proposal Tools

This module provides tools for generating AWS product pricing proposals.
It supports creating detailed pricing proposals with product configurations,
price breakdowns, and optimization suggestions in Chinese.
"""

import json
import datetime
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from strands import tool

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
EXCHANGE_RATES = {
    "USD": 7.10,  # Approximate USD to CNY exchange rate
}

# Chinese translations for AWS services and terms
CN_TRANSLATIONS = {
    # Services
    "EC2": "EC2 云服务器",
    "EBS": "EBS 块存储",
    "S3": "S3 对象存储",
    "RDS": "RDS 关系型数据库",
    "VPC": "VPC 私有网络",
    "ELB": "ELB 负载均衡",
    
    # Instance types
    "compute": "计算资源",
    "storage": "存储资源",
    "database": "数据库资源",
    "network": "网络资源",
    
    # EC2 specific
    "instance_type": "实例类型",
    "vcpu": "vCPU 数量",
    "memory": "内存",
    "os": "操作系统",
    "Linux": "Linux",
    "Windows": "Windows",
    
    # Storage specific
    "volume_type": "卷类型",
    "size_gb": "容量(GB)",
    "iops": "预置IOPS",
    "storage_class": "存储类型",
    "Standard": "标准存储",
    "Standard-IA": "标准-不频繁访问",
    "One-Zone-IA": "单区-不频繁访问",
    "Glacier": "Glacier 归档存储",
    "Deep-Archive": "深度归档存储",
    
    # Database specific
    "db_instance_class": "数据库实例类型",
    "engine": "数据库引擎",
    "MySQL": "MySQL",
    "PostgreSQL": "PostgreSQL",
    "Oracle": "Oracle",
    "SQL Server": "SQL Server",
    "MariaDB": "MariaDB",
    "Aurora MySQL": "Aurora MySQL",
    "deployment_option": "部署选项",
    "Single-AZ": "单可用区",
    "Multi-AZ": "多可用区",
    
    # Network specific
    "service_type": "服务类型",
    "lb_type": "负载均衡器类型",
    "ALB": "应用负载均衡器",
    "NLB": "网络负载均衡器",
    "bandwidth_gbps": "带宽(Gbps)",
    "LoadBalancer": "负载均衡器",
    "NatGateway": "NAT网关",
    "VpnConnection": "VPN连接",
    "VpcEndpoint": "VPC终端节点",
    
    # General terms
    "price_per_unit": "单价",
    "quantity": "数量",
    "unit": "计费单位",
    "total": "总计",
    "monthly": "月度",
    "hourly": "小时",
    "upfront": "预付",
    "On-Demand": "按需付费",
    "Reserved": "预留实例",
    "Savings Plan": "Savings Plan",
    "region": "区域",
    "confidence": "匹配置信度",
    
    # Regions
    "us-east-1": "美国东部(弗吉尼亚)",
    "us-east-2": "美国东部(俄亥俄)",
    "us-west-1": "美国西部(加利福尼亚)",
    "us-west-2": "美国西部(俄勒冈)",
    "ap-east-1": "亚太地区(香港)",
    "ap-south-1": "亚太地区(孟买)",
    "ap-northeast-1": "亚太地区(东京)",
    "ap-northeast-2": "亚太地区(首尔)",
    "ap-northeast-3": "亚太地区(大阪)",
    "ap-southeast-1": "亚太地区(新加坡)",
    "ap-southeast-2": "亚太地区(悉尼)",
    "ca-central-1": "加拿大(中部)",
    "eu-central-1": "欧洲(法兰克福)",
    "eu-west-1": "欧洲(爱尔兰)",
    "eu-west-2": "欧洲(伦敦)",
    "eu-west-3": "欧洲(巴黎)",
    "eu-north-1": "欧洲(斯德哥尔摩)",
    "sa-east-1": "南美洲(圣保罗)"
}

@tool
def pricing_proposal_generator(matched_products: str, price_data: str, customer_info: str = None, 
                              optimization_suggestions: bool = True) -> str:
    """Generate AWS product pricing proposal.
    
    This tool generates a detailed AWS product pricing proposal based on matched products
    and price data. The proposal includes product configurations, price breakdowns, and
    optional optimization suggestions in Chinese.
    
    Args:
        matched_products: Matched AWS product information as a JSON string
        price_data: Price data as a JSON string
        customer_info: Customer information as a JSON string (optional)
        optimization_suggestions: Whether to include optimization suggestions (default: True)
        
    Returns:
        Formatted pricing proposal in Chinese
        
    Example:
        >>> pricing_proposal_generator(matched_products, price_data, customer_info)
    """
    try:
        # Parse input data
        matched_data = json.loads(matched_products)
        price_info = json.loads(price_data)
        customer = json.loads(customer_info) if customer_info else {}
        
        # Generate the proposal
        proposal = generate_proposal(matched_data, price_info, customer, optimization_suggestions)
        
        return proposal
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        return f"错误：无法解析输入的JSON数据 - {str(e)}"
        
    except Exception as e:
        logger.error(f"Error generating proposal: {str(e)}")
        return f"错误：生成报价方案时出错 - {str(e)}"

@tool
def format_price_for_display(price: float, currency: str = "USD", convert_to_cny: bool = True) -> str:
    """Format price for display in the proposal.
    
    Args:
        price: Price value
        currency: Currency code (default: USD)
        convert_to_cny: Whether to convert and show CNY price (default: True)
        
    Returns:
        Formatted price string
    """
    try:
        if not isinstance(price, (int, float)):
            price = float(price)
            
        formatted_price = f"{price:.4f} {currency}"
        
        if convert_to_cny and currency.upper() == "USD":
            cny_price = price * EXCHANGE_RATES.get("USD", 7.10)
            formatted_price += f" (约 ¥{cny_price:.2f} CNY)"
            
        return formatted_price
        
    except (ValueError, TypeError) as e:
        logger.error(f"Price formatting error: {str(e)}")
        return f"{price} {currency}"

def generate_proposal(matched_data: Dict[str, Any], price_info: Dict[str, Any], 
                     customer: Dict[str, Any], include_suggestions: bool) -> str:
    """Generate the complete pricing proposal.
    
    Args:
        matched_data: Matched AWS product information
        price_info: Price data
        customer: Customer information
        include_suggestions: Whether to include optimization suggestions
        
    Returns:
        Complete pricing proposal as a formatted string
    """
    # Get current date for the proposal
    current_date = datetime.datetime.now().strftime("%Y年%m月%d日")
    
    # Extract customer information
    customer_name = customer.get("name", "尊敬的客户")
    company_name = customer.get("company", "")
    
    # Build the proposal
    proposal = []
    
    # Add header
    proposal.append(f"# AWS 产品报价方案\n")
    proposal.append(f"**生成日期：** {current_date}\n")
    
    if company_name:
        proposal.append(f"**客户：** {customer_name}，{company_name}\n")
    else:
        proposal.append(f"**客户：** {customer_name}\n")
    
    # Add introduction
    proposal.append("## 方案概述\n")
    proposal.append("根据您提供的需求，我们为您定制了以下 AWS 云服务解决方案。"
                   "此方案基于 AWS 全球领先的云计算平台，提供高可用性、可扩展性和安全性。\n")
    
    # Process matched products
    matches = matched_data.get("data", {}).get("matches", [])
    if not matches and "matches" in matched_data:
        matches = matched_data.get("matches", [])
    
    if not matches:
        proposal.append("**注意：** 未找到匹配的产品配置信息。请提供更详细的配置需求。\n")
        return "\n".join(proposal)
    
    # Group products by type
    compute_products = []
    storage_products = []
    database_products = []
    network_products = []
    
    for match in matches:
        product_type = match.get("product_type", "").lower()
        if product_type == "compute":
            compute_products.append(match)
        elif product_type == "storage":
            storage_products.append(match)
        elif product_type == "database":
            database_products.append(match)
        elif product_type == "network":
            network_products.append(match)
    
    # Add product sections
    total_monthly_cost = 0
    
    # Add compute section
    if compute_products:
        monthly_cost = add_compute_section(proposal, compute_products, price_info)
        total_monthly_cost += monthly_cost
    
    # Add storage section
    if storage_products:
        monthly_cost = add_storage_section(proposal, storage_products, price_info)
        total_monthly_cost += monthly_cost
    
    # Add database section
    if database_products:
        monthly_cost = add_database_section(proposal, database_products, price_info)
        total_monthly_cost += monthly_cost
    
    # Add network section
    if network_products:
        monthly_cost = add_network_section(proposal, network_products, price_info)
        total_monthly_cost += monthly_cost
    
    # Add cost summary
    proposal.append("## 费用总结\n")
    proposal.append("以下是所有服务的月度费用总结：\n")
    proposal.append("| 服务类别 | 月度费用 |\n")
    proposal.append("| --- | ---: |\n")
    
    if compute_products:
        compute_cost = sum(get_product_monthly_cost(p, price_info) for p in compute_products)
        proposal.append(f"| {translate('compute')} | {format_price_for_display(compute_cost)} |\n")
    
    if storage_products:
        storage_cost = sum(get_product_monthly_cost(p, price_info) for p in storage_products)
        proposal.append(f"| {translate('storage')} | {format_price_for_display(storage_cost)} |\n")
    
    if database_products:
        database_cost = sum(get_product_monthly_cost(p, price_info) for p in database_products)
        proposal.append(f"| {translate('database')} | {format_price_for_display(database_cost)} |\n")
    
    if network_products:
        network_cost = sum(get_product_monthly_cost(p, price_info) for p in network_products)
        proposal.append(f"| {translate('network')} | {format_price_for_display(network_cost)} |\n")
    
    proposal.append(f"| **总计** | **{format_price_for_display(total_monthly_cost)}** |\n")
    
    # Add optimization suggestions if requested
    if include_suggestions:
        add_optimization_suggestions(proposal, matches, total_monthly_cost)
    
    # Add closing
    proposal.append("## 后续步骤\n")
    proposal.append("1. 审阅此报价方案\n")
    proposal.append("2. 与我们的解决方案架构师讨论您的具体需求和任何定制要求\n")
    proposal.append("3. 确认方案后，我们将协助您完成AWS账户设置和资源部署\n")
    proposal.append("4. 提供上线支持和技术培训\n\n")
    
    proposal.append("## 备注\n")
    proposal.append("- 此报价基于当前AWS官方价格，实际费用可能因使用量、促销活动或企业折扣而有所不同\n")
    proposal.append("- 所有价格均不含税\n")
    proposal.append("- 报价有效期为30天\n")
    proposal.append("- 如有任何问题，请随时联系您的AWS客户经理\n\n")
    
    proposal.append("感谢您考虑使用AWS云服务！\n")
    
    return "\n".join(proposal)

def add_compute_section(proposal: List[str], products: List[Dict[str, Any]], 
                       price_info: Dict[str, Any]) -> float:
    """Add compute products section to the proposal.
    
    Args:
        proposal: List to append proposal content
        products: List of compute products
        price_info: Price data
        
    Returns:
        Total monthly cost for compute products
    """
    proposal.append(f"## {translate('compute')}\n")
    
    if not products:
        proposal.append("无计算资源需求。\n")
        return 0
    
    total_monthly_cost = 0
    
    for i, product in enumerate(products):
        matched_product = product.get("matched_product", {})
        instance_type = matched_product.get("instance_type", "")
        os = matched_product.get("os", "Linux")
        quantity = matched_product.get("quantity", 1)
        confidence = product.get("confidence", 0) * 100
        
        # Get price information
        hourly_price = get_ec2_price(instance_type, os, price_info)
        monthly_price = hourly_price * 730  # Average hours per month
        total_price = monthly_price * quantity
        total_monthly_cost += total_price
        
        proposal.append(f"### 计算资源 {i+1}\n")
        proposal.append(f"**实例类型：** {instance_type}\n")
        proposal.append(f"**操作系统：** {translate(os)}\n")
        proposal.append(f"**数量：** {quantity}\n")
        
        if "region" in product:
            proposal.append(f"**区域：** {translate(product.get('region', 'us-east-1'))}\n")
        
        proposal.append(f"**匹配置信度：** {confidence:.1f}%\n")
        
        # Add pricing table
        proposal.append("\n**价格明细：**\n")
        proposal.append("| 项目 | 单价(每小时) | 月度费用(730小时) | 数量 | 总费用(月) |\n")
        proposal.append("| --- | ---: | ---: | ---: | ---: |\n")
        proposal.append(f"| {instance_type} | {format_price_for_display(hourly_price)} | "
                       f"{format_price_for_display(monthly_price)} | {quantity} | "
                       f"{format_price_for_display(total_price)} |\n\n")
        
        # Add instance details
        proposal.append("**实例详情：**\n")
        instance_details = get_ec2_instance_details(instance_type)
        for key, value in instance_details.items():
            proposal.append(f"- {translate(key)}: {value}\n")
        proposal.append("\n")
    
    return total_monthly_cost

def add_storage_section(proposal: List[str], products: List[Dict[str, Any]], 
                       price_info: Dict[str, Any]) -> float:
    """Add storage products section to the proposal.
    
    Args:
        proposal: List to append proposal content
        products: List of storage products
        price_info: Price data
        
    Returns:
        Total monthly cost for storage products
    """
    proposal.append(f"## {translate('storage')}\n")
    
    if not products:
        proposal.append("无存储资源需求。\n")
        return 0
    
    total_monthly_cost = 0
    
    for i, product in enumerate(products):
        service = product.get("service", "")
        matched_product = product.get("matched_product", {})
        confidence = product.get("confidence", 0) * 100
        
        proposal.append(f"### {translate(service)} 存储 {i+1}\n")
        
        if service == "EBS":
            volume_type = matched_product.get("volume_type", "gp3")
            size_gb = matched_product.get("size_gb", 100)
            iops = matched_product.get("iops", 3000) if volume_type in ["io1", "io2"] else None
            quantity = matched_product.get("quantity", 1)
            
            # Get price information
            monthly_price = get_ebs_price(volume_type, size_gb, iops, price_info)
            total_price = monthly_price * quantity
            total_monthly_cost += total_price
            
            proposal.append(f"**卷类型：** {volume_type}\n")
            proposal.append(f"**容量：** {size_gb} GB\n")
            if iops:
                proposal.append(f"**预置IOPS：** {iops}\n")
            proposal.append(f"**数量：** {quantity}\n")
            
            if "region" in product:
                proposal.append(f"**区域：** {translate(product.get('region', 'us-east-1'))}\n")
            
            proposal.append(f"**匹配置信度：** {confidence:.1f}%\n")
            
            # Add pricing table
            proposal.append("\n**价格明细：**\n")
            proposal.append("| 项目 | 单价(每GB每月) | 容量(GB) | 月度费用 | 数量 | 总费用(月) |\n")
            proposal.append("| --- | ---: | ---: | ---: | ---: | ---: |\n")
            
            gb_price = monthly_price / size_gb if size_gb > 0 else 0
            proposal.append(f"| {volume_type} | {format_price_for_display(gb_price)} | "
                           f"{size_gb} | {format_price_for_display(monthly_price)} | "
                           f"{quantity} | {format_price_for_display(total_price)} |\n")
            
            if iops and volume_type in ["io1", "io2"]:
                iops_price = get_ebs_iops_price(volume_type, iops, price_info)
                total_iops_price = iops_price * quantity
                total_monthly_cost += total_iops_price
                
                proposal.append(f"| IOPS | {format_price_for_display(iops_price / iops)} (每IOPS) | "
                               f"{iops} | {format_price_for_display(iops_price)} | "
                               f"{quantity} | {format_price_for_display(total_iops_price)} |\n")
            
            proposal.append("\n")
            
        elif service == "S3":
            storage_class = matched_product.get("storage_class", "Standard")
            size_gb = matched_product.get("size_gb", 1000)
            quantity = matched_product.get("quantity", 1)
            
            # Get price information
            monthly_price = get_s3_price(storage_class, size_gb, price_info)
            total_price = monthly_price * quantity
            total_monthly_cost += total_price
            
            proposal.append(f"**存储类型：** {translate(storage_class)}\n")
            proposal.append(f"**容量：** {size_gb} GB\n")
            proposal.append(f"**数量：** {quantity}\n")
            
            if "region" in product:
                proposal.append(f"**区域：** {translate(product.get('region', 'us-east-1'))}\n")
            
            proposal.append(f"**匹配置信度：** {confidence:.1f}%\n")
            
            # Add pricing table
            proposal.append("\n**价格明细：**\n")
            proposal.append("| 项目 | 单价(每GB每月) | 容量(GB) | 月度费用 | 数量 | 总费用(月) |\n")
            proposal.append("| --- | ---: | ---: | ---: | ---: | ---: |\n")
            
            gb_price = monthly_price / size_gb if size_gb > 0 else 0
            proposal.append(f"| {translate(storage_class)} | {format_price_for_display(gb_price)} | "
                           f"{size_gb} | {format_price_for_display(monthly_price)} | "
                           f"{quantity} | {format_price_for_display(total_price)} |\n\n")
    
    return total_monthly_cost

def add_database_section(proposal: List[str], products: List[Dict[str, Any]], 
                        price_info: Dict[str, Any]) -> float:
    """Add database products section to the proposal.
    
    Args:
        proposal: List to append proposal content
        products: List of database products
        price_info: Price data
        
    Returns:
        Total monthly cost for database products
    """
    proposal.append(f"## {translate('database')}\n")
    
    if not products:
        proposal.append("无数据库资源需求。\n")
        return 0
    
    total_monthly_cost = 0
    
    for i, product in enumerate(products):
        matched_product = product.get("matched_product", {})
        db_instance_class = matched_product.get("db_instance_class", "db.t3.medium")
        engine = matched_product.get("engine", "MySQL")
        deployment_option = matched_product.get("deployment_option", "Single-AZ")
        quantity = matched_product.get("quantity", 1)
        confidence = product.get("confidence", 0) * 100
        
        # Get price information
        hourly_price = get_rds_price(db_instance_class, engine, deployment_option, price_info)
        monthly_price = hourly_price * 730  # Average hours per month
        total_price = monthly_price * quantity
        total_monthly_cost += total_price
        
        proposal.append(f"### 数据库资源 {i+1}\n")
        proposal.append(f"**实例类型：** {db_instance_class}\n")
        proposal.append(f"**数据库引擎：** {translate(engine)}\n")
        proposal.append(f"**部署选项：** {translate(deployment_option)}\n")
        proposal.append(f"**数量：** {quantity}\n")
        
        if "region" in product:
            proposal.append(f"**区域：** {translate(product.get('region', 'us-east-1'))}\n")
        
        proposal.append(f"**匹配置信度：** {confidence:.1f}%\n")
        
        # Add pricing table
        proposal.append("\n**价格明细：**\n")
        proposal.append("| 项目 | 单价(每小时) | 月度费用(730小时) | 数量 | 总费用(月) |\n")
        proposal.append("| --- | ---: | ---: | ---: | ---: |\n")
        proposal.append(f"| {db_instance_class} | {format_price_for_display(hourly_price)} | "
                       f"{format_price_for_display(monthly_price)} | {quantity} | "
                       f"{format_price_for_display(total_price)} |\n\n")
        
        # Add instance details
        proposal.append("**实例详情：**\n")
        instance_details = get_rds_instance_details(db_instance_class)
        for key, value in instance_details.items():
            proposal.append(f"- {translate(key)}: {value}\n")
        
        # Add deployment note
        if deployment_option == "Multi-AZ":
            proposal.append("- 多可用区部署提供了增强的可用性和数据持久性\n")
        
        proposal.append("\n")
    
    return total_monthly_cost

def add_network_section(proposal: List[str], products: List[Dict[str, Any]], 
                       price_info: Dict[str, Any]) -> float:
    """Add network products section to the proposal.
    
    Args:
        proposal: List to append proposal content
        products: List of network products
        price_info: Price data
        
    Returns:
        Total monthly cost for network products
    """
    proposal.append(f"## {translate('network')}\n")
    
    if not products:
        proposal.append("无网络资源需求。\n")
        return 0
    
    total_monthly_cost = 0
    
    for i, product in enumerate(products):
        service = product.get("service", "")
        matched_product = product.get("matched_product", {})
        service_type = matched_product.get("service_type", "")
        quantity = matched_product.get("quantity", 1)
        confidence = product.get("confidence", 0) * 100
        
        proposal.append(f"### {translate(service)} 网络服务 {i+1}\n")
        proposal.append(f"**服务类型：** {translate(service_type)}\n")
        
        if service == "ELB":
            lb_type = matched_product.get("lb_type", "ALB")
            proposal.append(f"**负载均衡器类型：** {translate(lb_type)}\n")
            
            # Get price information
            monthly_price = get_elb_price(lb_type, price_info)
            total_price = monthly_price * quantity
            total_monthly_cost += total_price
            
        elif service == "VPC":
            if service_type == "NatGateway":
                # Get price information for NAT Gateway
                monthly_price = get_nat_gateway_price(price_info)
                total_price = monthly_price * quantity
                total_monthly_cost += total_price
                
                # Add bandwidth if specified
                bandwidth_gbps = matched_product.get("bandwidth_gbps")
                if bandwidth_gbps:
                    proposal.append(f"**带宽：** {bandwidth_gbps} Gbps\n")
                    
                    # Add data processing cost estimate
                    data_gb = bandwidth_gbps * 730 * 3600 / 8  # Convert Gbps to GB per month (rough estimate)
                    data_price = get_nat_data_processing_price(data_gb, price_info)
                    total_monthly_cost += data_price
                    
            elif service_type == "VpnConnection":
                # Get price information for VPN Connection
                monthly_price = get_vpn_connection_price(price_info)
                total_price = monthly_price * quantity
                total_monthly_cost += total_price
                
            else:  # VpcEndpoint or other
                # Get price information for VPC Endpoint
                monthly_price = get_vpc_endpoint_price(price_info)
                total_price = monthly_price * quantity
                total_monthly_cost += total_price
        
        proposal.append(f"**数量：** {quantity}\n")
        
        if "region" in product:
            proposal.append(f"**区域：** {translate(product.get('region', 'us-east-1'))}\n")
        
        proposal.append(f"**匹配置信度：** {confidence:.1f}%\n")
        
        # Add pricing table
        proposal.append("\n**价格明细：**\n")
        proposal.append("| 项目 | 单价(每月) | 数量 | 总费用(月) |\n")
        proposal.append("| --- | ---: | ---: | ---: |\n")
        proposal.append(f"| {translate(service_type)} | {format_price_for_display(monthly_price)} | "
                       f"{quantity} | {format_price_for_display(total_price)} |\n")
        
        # Add data processing costs if applicable
        if service == "VPC" and service_type == "NatGateway" and "bandwidth_gbps" in matched_product:
            bandwidth_gbps = matched_product.get("bandwidth_gbps")
            data_gb = bandwidth_gbps * 730 * 3600 / 8  # Convert Gbps to GB per month
            data_price = get_nat_data_processing_price(data_gb, price_info)
            
            proposal.append(f"| 数据处理 ({data_gb:.0f} GB) | {format_price_for_display(data_price)} | "
                           f"1 | {format_price_for_display(data_price)} |\n")
        
        proposal.append("\n")
    
    return total_monthly_cost

def add_optimization_suggestions(proposal: List[str], products: List[Dict[str, Any]], 
                               total_cost: float) -> None:
    """Add optimization suggestions to the proposal.
    
    Args:
        proposal: List to append proposal content
        products: List of all products
        total_cost: Total monthly cost
    """
    proposal.append("## 优化建议\n")
    proposal.append("根据您的需求，我们提供以下优化建议，帮助您降低成本并提高性能：\n\n")
    
    # Check for compute optimizations
    compute_products = [p for p in products if p.get("product_type") == "compute"]
    if compute_products:
        proposal.append("### 计算资源优化\n")
        
        # Reserved Instance suggestion
        ri_savings = total_cost * 0.40  # Approximate 40% savings with RIs
        proposal.append("1. **预留实例 (Reserved Instances)**\n")
        proposal.append("   - 对于稳定的工作负载，使用预留实例可以节省高达72%的成本\n")
        proposal.append(f"   - 估计每月节省: {format_price_for_display(ri_savings)}\n")
        proposal.append("   - 建议承诺期: 1年或3年，根据您的业务需求灵活选择\n\n")
        
        # Savings Plan suggestion
        sp_savings = total_cost * 0.35  # Approximate 35% savings with SPs
        proposal.append("2. **Savings Plans**\n")
        proposal.append("   - 比预留实例更灵活，可以跨实例系列、大小和区域使用\n")
        proposal.append(f"   - 估计每月节省: {format_price_for_display(sp_savings)}\n")
        proposal.append("   - 建议承诺期: 1年，以保持灵活性\n\n")
        
        # Right-sizing suggestion
        proposal.append("3. **实例优化**\n")
        proposal.append("   - 根据实际使用情况调整实例类型和大小\n")
        proposal.append("   - 使用AWS Compute Optimizer分析资源利用率并获取建议\n")
        proposal.append("   - 考虑使用竞价型实例(Spot Instances)处理非关键任务，可节省高达90%的成本\n\n")
    
    # Check for storage optimizations
    storage_products = [p for p in products if p.get("product_type") == "storage"]
    if storage_products:
        proposal.append("### 存储资源优化\n")
        
        # S3 lifecycle policies
        proposal.append("1. **S3存储生命周期管理**\n")
        proposal.append("   - 实施生命周期策略，自动将不常访问的数据转移到更低成本的存储类别\n")
        proposal.append("   - 例如: 标准存储 → 标准-不频繁访问 → Glacier，可节省高达90%的存储成本\n\n")
        
        # EBS optimizations
        proposal.append("2. **EBS卷优化**\n")
        proposal.append("   - 使用gp3代替gp2，性能相同但成本更低\n")
        proposal.append("   - 定期审核并删除未使用的EBS卷和快照\n")
        proposal.append("   - 考虑使用EBS快照生命周期管理自动化备份流程\n\n")
    
    # Check for database optimizations
    database_products = [p for p in products if p.get("product_type") == "database"]
    if database_products:
        proposal.append("### 数据库资源优化\n")
        
        # RDS optimizations
        proposal.append("1. **RDS优化**\n")
        proposal.append("   - 使用预留实例降低RDS成本\n")
        proposal.append("   - 考虑使用Aurora Serverless针对变化的工作负载自动扩展\n")
        proposal.append("   - 实施多区域读取副本以提高性能和可用性\n\n")
        
        # Performance optimizations
        proposal.append("2. **性能优化**\n")
        proposal.append("   - 优化查询和索引以提高数据库性能\n")
        proposal.append("   - 使用Amazon RDS Performance Insights监控和优化数据库性能\n")
        proposal.append("   - 考虑使用缓存服务(如ElastiCache)减轻数据库负载\n\n")
    
    # General optimizations
    proposal.append("### 一般优化建议\n")
    proposal.append("1. **成本监控与管理**\n")
    proposal.append("   - 使用AWS Cost Explorer和AWS Budgets监控和控制支出\n")
    proposal.append("   - 设置成本警报，及时发现异常支出\n")
    proposal.append("   - 使用资源标签跟踪不同项目和部门的成本\n\n")
    
    proposal.append("2. **架构优化**\n")
    proposal.append("   - 采用无服务器架构(如Lambda、DynamoDB)减少闲置资源\n")
    proposal.append("   - 实施自动扩展以根据实际需求调整资源\n")
    proposal.append("   - 使用AWS Trusted Advisor获取最佳实践建议\n\n")
    
    proposal.append("我们的解决方案架构师可以与您一起详细评估这些优化建议，并制定具体的实施计划。\n")

# Helper functions for pricing

def get_product_monthly_cost(product: Dict[str, Any], price_info: Dict[str, Any]) -> float:
    """Get the monthly cost for a product.
    
    Args:
        product: Product information
        price_info: Price data
        
    Returns:
        Monthly cost for the product
    """
    product_type = product.get("product_type", "")
    service = product.get("service", "")
    matched_product = product.get("matched_product", {})
    quantity = matched_product.get("quantity", 1)
    
    if product_type == "compute":
        instance_type = matched_product.get("instance_type", "")
        os = matched_product.get("os", "Linux")
        hourly_price = get_ec2_price(instance_type, os, price_info)
        return hourly_price * 730 * quantity  # 730 hours per month
    
    elif product_type == "storage":
        if service == "EBS":
            volume_type = matched_product.get("volume_type", "gp3")
            size_gb = matched_product.get("size_gb", 100)
            iops = matched_product.get("iops", 3000) if volume_type in ["io1", "io2"] else None
            
            monthly_price = get_ebs_price(volume_type, size_gb, iops, price_info)
            
            if iops and volume_type in ["io1", "io2"]:
                monthly_price += get_ebs_iops_price(volume_type, iops, price_info)
                
            return monthly_price * quantity
            
        elif service == "S3":
            storage_class = matched_product.get("storage_class", "Standard")
            size_gb = matched_product.get("size_gb", 1000)
            return get_s3_price(storage_class, size_gb, price_info) * quantity
    
    elif product_type == "database":
        db_instance_class = matched_product.get("db_instance_class", "db.t3.medium")
        engine = matched_product.get("engine", "MySQL")
        deployment_option = matched_product.get("deployment_option", "Single-AZ")
        
        hourly_price = get_rds_price(db_instance_class, engine, deployment_option, price_info)
        return hourly_price * 730 * quantity  # 730 hours per month
    
    elif product_type == "network":
        service_type = matched_product.get("service_type", "")
        
        if service == "ELB":
            lb_type = matched_product.get("lb_type", "ALB")
            return get_elb_price(lb_type, price_info) * quantity
            
        elif service == "VPC":
            if service_type == "NatGateway":
                monthly_price = get_nat_gateway_price(price_info) * quantity
                
                # Add data processing cost if bandwidth is specified
                bandwidth_gbps = matched_product.get("bandwidth_gbps")
                if bandwidth_gbps:
                    data_gb = bandwidth_gbps * 730 * 3600 / 8  # Convert Gbps to GB per month
                    monthly_price += get_nat_data_processing_price(data_gb, price_info)
                    
                return monthly_price
                
            elif service_type == "VpnConnection":
                return get_vpn_connection_price(price_info) * quantity
                
            else:  # VpcEndpoint or other
                return get_vpc_endpoint_price(price_info) * quantity
    
    # Default fallback
    return 0

def get_ec2_price(instance_type: str, os: str, price_info: Dict[str, Any]) -> float:
    """Get EC2 instance price.
    
    Args:
        instance_type: EC2 instance type
        os: Operating system
        price_info: Price data
        
    Returns:
        Hourly price for the EC2 instance
    """
    # Default prices if not found in price_info
    default_prices = {
        't3.nano': 0.0052,
        't3.micro': 0.0104,
        't3.small': 0.0208,
        't3.medium': 0.0416,
        't3.large': 0.0832,
        't3.xlarge': 0.1664,
        't3.2xlarge': 0.3328,
        'c5.large': 0.085,
        'c5.xlarge': 0.17,
        'c5.2xlarge': 0.34,
        'c5.4xlarge': 0.68,
        'c5.9xlarge': 1.53,
        'c5.18xlarge': 3.06,
        'm5.large': 0.096,
        'm5.xlarge': 0.192,
        'm5.2xlarge': 0.384,
        'm5.4xlarge': 0.768,
        'm5.12xlarge': 2.304,
        'm5.24xlarge': 4.608
    }
    
    # Windows costs approximately 2x Linux
    os_multiplier = 2.0 if os.lower() == 'windows' else 1.0
    
    # Try to get price from price_info
    try:
        if price_info and "data" in price_info:
            pricing_data = price_info.get("data", {}).get("pricing", [])
            for item in pricing_data:
                if item.get("instance_type") == instance_type:
                    return float(item.get("price_per_unit", 0))
    except (KeyError, ValueError, TypeError):
        pass
    
    # Fallback to default price
    base_price = default_prices.get(instance_type, 0.05)  # Default to $0.05/hour if not found
    return base_price * os_multiplier

def get_ec2_instance_details(instance_type: str) -> Dict[str, str]:
    """Get EC2 instance details.
    
    Args:
        instance_type: EC2 instance type
        
    Returns:
        Dictionary with instance details
    """
    # Default instance details
    instance_details = {
        't3.nano': {'vcpu': '2', 'memory': '0.5 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.micro': {'vcpu': '2', 'memory': '1 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.small': {'vcpu': '2', 'memory': '2 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.medium': {'vcpu': '2', 'memory': '4 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.large': {'vcpu': '2', 'memory': '8 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.xlarge': {'vcpu': '4', 'memory': '16 GB', 'network_performance': 'Up to 5 Gigabit'},
        't3.2xlarge': {'vcpu': '8', 'memory': '32 GB', 'network_performance': 'Up to 5 Gigabit'},
        'c5.large': {'vcpu': '2', 'memory': '4 GB', 'network_performance': 'Up to 10 Gigabit'},
        'c5.xlarge': {'vcpu': '4', 'memory': '8 GB', 'network_performance': 'Up to 10 Gigabit'},
        'c5.2xlarge': {'vcpu': '8', 'memory': '16 GB', 'network_performance': 'Up to 10 Gigabit'},
        'c5.4xlarge': {'vcpu': '16', 'memory': '32 GB', 'network_performance': 'Up to 10 Gigabit'},
        'c5.9xlarge': {'vcpu': '36', 'memory': '72 GB', 'network_performance': '10 Gigabit'},
        'c5.18xlarge': {'vcpu': '72', 'memory': '144 GB', 'network_performance': '25 Gigabit'},
        'm5.large': {'vcpu': '2', 'memory': '8 GB', 'network_performance': 'Up to 10 Gigabit'},
        'm5.xlarge': {'vcpu': '4', 'memory': '16 GB', 'network_performance': 'Up to 10 Gigabit'},
        'm5.2xlarge': {'vcpu': '8', 'memory': '32 GB', 'network_performance': 'Up to 10 Gigabit'},
        'm5.4xlarge': {'vcpu': '16', 'memory': '64 GB', 'network_performance': 'Up to 10 Gigabit'},
        'm5.12xlarge': {'vcpu': '48', 'memory': '192 GB', 'network_performance': '10 Gigabit'},
        'm5.24xlarge': {'vcpu': '96', 'memory': '384 GB', 'network_performance': '25 Gigabit'}
    }
    
    return instance_details.get(instance_type, {'vcpu': 'N/A', 'memory': 'N/A', 'network_performance': 'N/A'})

def get_ebs_price(volume_type: str, size_gb: float, iops: int = None, 
                 price_info: Dict[str, Any] = None) -> float:
    """Get EBS volume price.
    
    Args:
        volume_type: EBS volume type
        size_gb: Volume size in GB
        iops: Provisioned IOPS (for io1/io2)
        price_info: Price data
        
    Returns:
        Monthly price for the EBS volume
    """
    # Default prices per GB-month if not found in price_info
    default_prices = {
        'gp2': 0.10,
        'gp3': 0.08,
        'io1': 0.125,
        'io2': 0.125,
        'st1': 0.045,
        'sc1': 0.025,
        'standard': 0.05
    }
    
    # Try to get price from price_info
    try:
        if price_info and "data" in price_info:
            pricing_data = price_info.get("data", {}).get("pricing", [])
            for item in pricing_data:
                if item.get("volume_type") == volume_type:
                    return float(item.get("price_per_unit", 0)) * size_gb
    except (KeyError, ValueError, TypeError):
        pass
    
    # Fallback to default price
    gb_price = default_prices.get(volume_type, 0.10)  # Default to $0.10/GB-month if not found
    return gb_price * size_gb

def get_ebs_iops_price(volume_type: str, iops: int, price_info: Dict[str, Any] = None) -> float:
    """Get EBS IOPS price.
    
    Args:
        volume_type: EBS volume type
        iops: Provisioned IOPS
        price_info: Price data
        
    Returns:
        Monthly price for the provisioned IOPS
    """
    # Default prices per IOPS-month
    default_iops_prices = {
        'io1': 0.065 / 1000,  # $0.065 per IOPS-month
        'io2': 0.065 / 1000   # $0.065 per IOPS-month
    }
    
    # Try to get price from price_info
    try:
        if price_info and "data" in price_info:
            pricing_data = price_info.get("data", {}).get("pricing", [])
            for item in pricing_data:
                if item.get("volume_type") == volume_type and "iops" in item:
                    return float(item.get("price_per_unit", 0)) * iops
    except (KeyError, ValueError, TypeError):
        pass
    
    # Fallback to default price
    iops_price = default_iops_prices.get(volume_type, 0)
    return iops_price * iops

def get_s3_price(storage_class: str, size_gb: float, price_info: Dict[str, Any] = None) -> float:
    """Get S3 storage price.
    
    Args:
        storage_class: S3 storage class
        size_gb: Storage size in GB
        price_info: Price data
        
    Returns:
        Monthly price for the S3 storage
    """
    # Default prices per GB-month if not found in price_info
    default_prices = {
        'Standard': 0.023,
        'Standard-IA': 0.0125,
        'One-Zone-IA': 0.01,
        'Glacier': 0.004,
        'Deep-Archive': 0.00099
    }
    
    # Try to get price from price_info
    try:
        if price_info and "data" in price_info:
            pricing_data = price_info.get("data", {}).get("pricing", [])
            for item in pricing_data:
                if item.get("storage_class") == storage_class:
                    return float(item.get("price_per_unit", 0)) * size_gb
    except (KeyError, ValueError, TypeError):
        pass
    
    # Fallback to default price
    gb_price = default_prices.get(storage_class, 0.023)  # Default to Standard if not found
    return gb_price * size_gb

def get_rds_price(db_instance_class: str, engine: str, deployment_option: str, 
                 price_info: Dict[str, Any] = None) -> float:
    """Get RDS instance price.
    
    Args:
        db_instance_class: RDS instance class
        engine: Database engine
        deployment_option: Deployment option
        price_info: Price data
        
    Returns:
        Hourly price for the RDS instance
    """
    # Default prices if not found in price_info
    default_prices = {
        'db.t3.micro': 0.017,
        'db.t3.small': 0.034,
        'db.t3.medium': 0.068,
        'db.t3.large': 0.136,
        'db.t3.xlarge': 0.272,
        'db.t3.2xlarge': 0.544,
        'db.m5.large': 0.171,
        'db.m5.xlarge': 0.342,
        'db.m5.2xlarge': 0.684,
        'db.m5.4xlarge': 1.368,
        'db.r5.large': 0.226,
        'db.r5.xlarge': 0.452,
        'db.r5.2xlarge': 0.904,
        'db.r5.4xlarge': 1.808
    }
    
    # Engine multipliers (relative to MySQL)
    engine_multipliers = {
        'MySQL': 1.0,
        'MariaDB': 1.0,
        'PostgreSQL': 1.0,
        'Aurora MySQL': 1.2,
        'Oracle': 1.5,
        'SQL Server': 1.7
    }
    
    # Multi-AZ costs 2x Single-AZ
    deployment_multiplier = 2.0 if deployment_option == 'Multi-AZ' else 1.0
    
    # Try to get price from price_info
    try:
        if price_info and "data" in price_info:
            pricing_data = price_info.get("data", {}).get("pricing", [])
            for item in pricing_data:
                if (item.get("db_instance_class") == db_instance_class and
                    item.get("engine") == engine and
                    item.get("deployment_option") == deployment_option):
                    return float(item.get("price_per_unit", 0))
    except (KeyError, ValueError, TypeError):
        pass
    
    # Fallback to default price
    base_price = default_prices.get(db_instance_class, 0.10)  # Default to $0.10/hour if not found
    engine_multiplier = engine_multipliers.get(engine, 1.0)
    
    return base_price * engine_multiplier * deployment_multiplier

def get_rds_instance_details(db_instance_class: str) -> Dict[str, str]:
    """Get RDS instance details.
    
    Args:
        db_instance_class: RDS instance class
        
    Returns:
        Dictionary with instance details
    """
    # Default instance details
    instance_details = {
        'db.t3.micro': {'vcpu': '2', 'memory': '1 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.t3.small': {'vcpu': '2', 'memory': '2 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.t3.medium': {'vcpu': '2', 'memory': '4 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.t3.large': {'vcpu': '2', 'memory': '8 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.t3.xlarge': {'vcpu': '4', 'memory': '16 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.t3.2xlarge': {'vcpu': '8', 'memory': '32 GB', 'network_performance': 'Up to 5 Gigabit'},
        'db.m5.large': {'vcpu': '2', 'memory': '8 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.m5.xlarge': {'vcpu': '4', 'memory': '16 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.m5.2xlarge': {'vcpu': '8', 'memory': '32 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.m5.4xlarge': {'vcpu': '16', 'memory': '64 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.r5.large': {'vcpu': '2', 'memory': '16 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.r5.xlarge': {'vcpu': '4', 'memory': '32 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.r5.2xlarge': {'vcpu': '8', 'memory': '64 GB', 'network_performance': 'Up to 10 Gigabit'},
        'db.r5.4xlarge': {'vcpu': '16', 'memory': '128 GB', 'network_performance': 'Up to 10 Gigabit'}
    }
    
    return instance_details.get(db_instance_class, {'vcpu': 'N/A', 'memory': 'N/A', 'network_performance': 'N/A'})

def get_elb_price(lb_type: str, price_info: Dict[str, Any] = None) -> float:
    """Get ELB price.
    
    Args:
        lb_type: Load balancer type
        price_info: Price data
        
    Returns:
        Monthly price for the load balancer
    """
    # Default prices per hour
    default_prices = {
        'ALB': 0.0225,  # $0.0225 per hour
        'NLB': 0.0225,  # $0.0225 per hour
        'CLB': 0.025    # $0.025 per hour
    }
    
    # Convert to monthly price (730 hours per month)
    hourly_price = default_prices.get(lb_type, 0.0225)
    return hourly_price * 730

def get_nat_gateway_price(price_info: Dict[str, Any] = None) -> float:
    """Get NAT Gateway price.
    
    Args:
        price_info: Price data
        
    Returns:
        Monthly price for the NAT Gateway
    """
    # Default price per hour
    hourly_price = 0.045  # $0.045 per hour
    
    # Convert to monthly price (730 hours per month)
    return hourly_price * 730

def get_nat_data_processing_price(data_gb: float, price_info: Dict[str, Any] = None) -> float:
    """Get NAT Gateway data processing price.
    
    Args:
        data_gb: Data processed in GB
        price_info: Price data
        
    Returns:
        Monthly price for data processing
    """
    # Default price per GB
    gb_price = 0.045  # $0.045 per GB
    
    return gb_price * data_gb

def get_vpn_connection_price(price_info: Dict[str, Any] = None) -> float:
    """Get VPN Connection price.
    
    Args:
        price_info: Price data
        
    Returns:
        Monthly price for the VPN Connection
    """
    # Default price per hour
    hourly_price = 0.05  # $0.05 per hour
    
    # Convert to monthly price (730 hours per month)
    return hourly_price * 730

def get_vpc_endpoint_price(price_info: Dict[str, Any] = None) -> float:
    """Get VPC Endpoint price.
    
    Args:
        price_info: Price data
        
    Returns:
        Monthly price for the VPC Endpoint
    """
    # Default price per hour
    hourly_price = 0.01  # $0.01 per hour
    
    # Convert to monthly price (730 hours per month)
    return hourly_price * 730

def translate(key: str) -> str:
    """Translate a key to Chinese.
    
    Args:
        key: Key to translate
        
    Returns:
        Translated text or original key if not found
    """
    return CN_TRANSLATIONS.get(key, key)