#!/usr/bin/env python3
"""
Pricing Proposal Generator Tool

生成AWS产品报价方案，包括产品配置、价格明细和优化建议。
支持中文输出，以销售思维组织报价内容。
"""

import json
import datetime
from typing import Dict, List, Any, Optional
import strands
from strands import tool


@tool
def generate_proposal(
    matched_products: str,
    price_data: str,
    customer_info: str = None,
    optimization_suggestions: bool = True
) -> str:
    """
    生成AWS产品报价方案

    Args:
        matched_products (str): 匹配的AWS产品信息（JSON格式）
        price_data (str): 价格数据（JSON格式）
        customer_info (str, optional): 客户信息（JSON格式，可选）
        optimization_suggestions (bool, optional): 是否包含优化建议，默认为True

    Returns:
        str: 格式化的报价方案（中文）

    Raises:
        ValueError: 当产品信息或价格数据格式错误时
    """
    try:
        # 解析匹配的产品信息和价格数据
        matched_products_dict = json.loads(matched_products)
        price_data_dict = json.loads(price_data)
        
        # 解析客户信息（如果有）
        customer_dict = {}
        if customer_info:
            try:
                customer_dict = json.loads(customer_info)
            except json.JSONDecodeError:
                # 如果客户信息格式错误，使用空字典
                customer_dict = {}
        
        # 生成报价方案
        proposal = generate_pricing_proposal(
            matched_products_dict,
            price_data_dict,
            customer_dict,
            optimization_suggestions
        )
        
        return proposal
        
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析错误: {str(e)}")
    except Exception as e:
        raise ValueError(f"生成报价方案失败: {str(e)}")


def generate_pricing_proposal(
    matched_products: Dict[str, Any],
    price_data: Dict[str, Any],
    customer_info: Dict[str, Any],
    include_optimization: bool
) -> str:
    """
    生成详细的AWS产品报价方案

    Args:
        matched_products: 匹配的AWS产品信息
        price_data: 价格数据
        customer_info: 客户信息
        include_optimization: 是否包含优化建议

    Returns:
        str: 格式化的报价方案（中文）
    """
    # 获取当前日期和时间
    now = datetime.datetime.now()
    current_date = now.strftime("%Y年%m月%d日")
    
    # 获取产品类型和区域
    product_type = matched_products.get("product_type", "未知")
    region = matched_products.get("region", "us-east-1")
    region_name = get_region_name(region)
    
    # 获取匹配的产品列表
    products = matched_products.get("matched_products", [])
    
    # 准备报价方案
    proposal = []
    
    # 1. 报价标题
    proposal.append(f"# AWS产品报价方案")
    proposal.append(f"**生成日期**: {current_date}")
    proposal.append(f"**有效期**: {current_date} 至 {(now + datetime.timedelta(days=30)).strftime('%Y年%m月%d日')}")
    proposal.append(f"**区域**: {region_name} ({region})")
    
    # 添加客户信息（如果有）
    if customer_info:
        customer_name = customer_info.get("name", "尊敬的客户")
        proposal.append(f"**客户**: {customer_name}")
        if "company" in customer_info:
            proposal.append(f"**公司**: {customer_info['company']}")
    
    proposal.append("\n## 报价摘要")
    
    # 2. 计算总价
    total_price = 0.0
    monthly_total = 0.0
    
    for product in products:
        product_price = get_product_price(product, price_data)
        quantity = product.get("quantity", 1)
        total_price += product_price * quantity
        monthly_total += product_price * quantity * 730  # 730小时/月
    
    # 添加报价摘要
    proposal.append(f"* **产品类型**: {translate_product_type(product_type)}")
    proposal.append(f"* **产品数量**: {len(products)}个")
    proposal.append(f"* **小时总价**: ¥{total_price:.2f}")
    proposal.append(f"* **月度总价**: ¥{monthly_total:.2f}")
    proposal.append(f"* **年度总价**: ¥{monthly_total * 12:.2f}")
    
    # 3. 产品配置详情
    proposal.append("\n## 产品配置详情")
    
    for i, product in enumerate(products):
        service = product.get("aws_service", "未知服务")
        proposal.append(f"\n### {i+1}. {translate_service_name(service)}")
        
        # 根据产品类型显示不同的配置详情
        if product_type == "compute":
            instance_type = product.get("instance_type", "未知实例类型")
            vcpu = product.get("matched_config", {}).get("vcpu", "未知")
            memory = product.get("matched_config", {}).get("memory_gb", "未知")
            os = product.get("matched_config", {}).get("operating_system", "Linux")
            
            proposal.append(f"* **实例类型**: {instance_type}")
            proposal.append(f"* **vCPU**: {vcpu} 核")
            proposal.append(f"* **内存**: {memory} GB")
            proposal.append(f"* **操作系统**: {os}")
            
        elif product_type == "storage":
            storage_class = product.get("storage_class", "未知存储类型")
            storage_size = product.get("matched_config", {}).get("storage_size_gb", "未知")
            storage_type = product.get("matched_config", {}).get("storage_type", "未知")
            
            proposal.append(f"* **存储类型**: {storage_class}")
            proposal.append(f"* **存储容量**: {storage_size} GB")
            proposal.append(f"* **存储特性**: {storage_type}")
            
            if "iops" in product.get("matched_config", {}):
                proposal.append(f"* **IOPS**: {product['matched_config']['iops']}")
            
        elif product_type == "network":
            service_type = product.get("service_type", "未知服务类型")
            bandwidth = product.get("matched_config", {}).get("bandwidth_mbps", "未知")
            
            proposal.append(f"* **服务类型**: {service_type}")
            proposal.append(f"* **带宽**: {bandwidth} Mbps")
            
        elif product_type == "database":
            instance_type = product.get("instance_type", "未知实例类型")
            engine = product.get("engine", "未知引擎")
            engine_version = product.get("engine_version", "未知版本")
            vcpu = product.get("matched_config", {}).get("vcpu", "未知")
            memory = product.get("matched_config", {}).get("memory_gb", "未知")
            storage = product.get("matched_config", {}).get("storage_gb", "未知")
            storage_type = product.get("matched_config", {}).get("storage_type", "未知")
            
            proposal.append(f"* **实例类型**: {instance_type}")
            proposal.append(f"* **数据库引擎**: {engine} {engine_version}")
            proposal.append(f"* **vCPU**: {vcpu} 核")
            proposal.append(f"* **内存**: {memory} GB")
            proposal.append(f"* **存储容量**: {storage} GB")
            proposal.append(f"* **存储类型**: {storage_type}")
        
        # 显示推断信息（如果有）
        if product.get("is_inferred", False):
            proposal.append(f"* **注**: 部分配置参数是根据已有信息推断得出")
        
        # 显示置信度评分
        confidence = product.get("confidence_score", 0.0)
        if confidence > 0:
            confidence_level = "高" if confidence > 0.8 else "中" if confidence > 0.6 else "低"
            proposal.append(f"* **匹配置信度**: {confidence_level}")
    
    # 4. 价格明细
    proposal.append("\n## 价格明细")
    
    for i, product in enumerate(products):
        service = product.get("aws_service", "未知服务")
        product_price = get_product_price(product, price_data)
        quantity = product.get("quantity", 1)
        
        # 根据产品类型显示不同的价格信息
        if product_type == "compute":
            instance_type = product.get("instance_type", "未知实例类型")
            proposal.append(f"\n### {i+1}. {translate_service_name(service)} - {instance_type}")
        elif product_type == "storage":
            storage_class = product.get("storage_class", "未知存储类型")
            storage_size = product.get("matched_config", {}).get("storage_size_gb", "未知")
            proposal.append(f"\n### {i+1}. {translate_service_name(service)} - {storage_class} ({storage_size} GB)")
        elif product_type == "network":
            service_type = product.get("service_type", "未知服务类型")
            proposal.append(f"\n### {i+1}. {translate_service_name(service)} - {service_type}")
        elif product_type == "database":
            instance_type = product.get("instance_type", "未知实例类型")
            engine = product.get("engine", "未知引擎")
            proposal.append(f"\n### {i+1}. {translate_service_name(service)} - {engine} {instance_type}")
        
        proposal.append(f"* **单价**: ¥{product_price:.4f} /小时")
        proposal.append(f"* **数量**: {quantity}")
        proposal.append(f"* **小时总价**: ¥{product_price * quantity:.4f}")
        proposal.append(f"* **月度总价**: ¥{product_price * quantity * 730:.2f}")
        proposal.append(f"* **年度总价**: ¥{product_price * quantity * 730 * 12:.2f}")
    
    # 5. 总价汇总
    proposal.append("\n## 总价汇总")
    proposal.append(f"* **小时总价**: ¥{total_price:.4f}")
    proposal.append(f"* **月度总价**: ¥{monthly_total:.2f}")
    proposal.append(f"* **年度总价**: ¥{monthly_total * 12:.2f}")
    
    # 6. 优化建议（如果需要）
    if include_optimization:
        proposal.append("\n## 优化建议")
        
        # 根据产品类型提供不同的优化建议
        if product_type == "compute":
            proposal.append("1. **预留实例**: 如果您的工作负载稳定，建议使用预留实例，可节省高达75%的成本。")
            proposal.append("2. **Spot实例**: 对于可中断的工作负载，使用Spot实例可节省高达90%的成本。")
            proposal.append("3. **自动扩缩容**: 配置Auto Scaling根据实际需求自动调整实例数量，优化成本。")
            proposal.append("4. **实例类型优化**: 定期评估实例类型，确保CPU和内存利用率在最佳范围内。")
            
        elif product_type == "storage":
            proposal.append("1. **存储分层**: 根据数据访问频率选择不同的存储类别，如S3 Standard、S3 IA、S3 Glacier等。")
            proposal.append("2. **生命周期策略**: 配置生命周期策略自动将不常访问的数据迁移到更低成本的存储类别。")
            proposal.append("3. **EBS卷类型选择**: 根据性能需求选择适合的EBS卷类型，如gp3、io2、st1等。")
            proposal.append("4. **数据压缩**: 在可能的情况下压缩数据，减少存储空间需求。")
            
        elif product_type == "network":
            proposal.append("1. **数据传输优化**: 使用CloudFront或Global Accelerator优化数据传输路径。")
            proposal.append("2. **VPC端点**: 使用VPC端点减少NAT网关流量和相关费用。")
            proposal.append("3. **带宽优化**: 根据实际需求选择合适的带宽，避免过度配置。")
            proposal.append("4. **流量监控**: 定期监控网络流量，识别异常模式和优化机会。")
            
        elif product_type == "database":
            proposal.append("1. **多可用区部署**: 对于关键业务，建议使用多可用区部署提高可用性。")
            proposal.append("2. **读取副本**: 使用读取副本分担读取负载，提高性能。")
            proposal.append("3. **实例类型选择**: 根据工作负载特性选择适合的实例类型，如内存优化型或计算优化型。")
            proposal.append("4. **自动扩展存储**: 启用自动扩展存储功能，根据需求自动调整存储容量。")
        
        # 通用优化建议
        proposal.append("\n### 通用优化建议")
        proposal.append("1. **成本监控**: 使用AWS Cost Explorer和预算功能定期监控和分析成本。")
        proposal.append("2. **标签策略**: 实施全面的标签策略，便于成本分配和优化。")
        proposal.append("3. **Savings Plans**: 考虑购买Savings Plans，可为EC2、Fargate和Lambda提供灵活的定价模式。")
        proposal.append("4. **资源清理**: 定期检查并删除未使用的资源，如未附加的EBS卷、未使用的弹性IP等。")
    
    # 7. 附加说明
    proposal.append("\n## 附加说明")
    proposal.append("1. 本报价基于当前AWS官方价格，实际价格可能因促销活动、折扣计划或价格调整而变化。")
    proposal.append("2. 报价不包含可能适用的税费。")
    proposal.append("3. 实际费用将根据实际使用量计算，本报价仅供参考。")
    proposal.append("4. 如需更精确的报价或有任何疑问，请联系AWS销售团队。")
    
    # 8. 联系信息
    proposal.append("\n## 联系信息")
    proposal.append("如需进一步了解AWS产品和服务，或获取更详细的报价信息，请联系：")
    proposal.append("* **AWS官方网站**: https://aws.amazon.com/cn/")
    proposal.append("* **AWS中国区联系电话**: 400-021-2098")
    proposal.append("* **AWS全球联系电话**: +1-206-266-7010")
    
    # 9. 免责声明
    proposal.append("\n## 免责声明")
    proposal.append("本报价方案仅供参考，不构成合同要约。AWS保留在不事先通知的情况下更改价格的权利。最终价格以AWS官方报价为准。")
    
    return "\n".join(proposal)


def get_product_price(product: Dict[str, Any], price_data: Dict[str, Any]) -> float:
    """
    从价格数据中获取产品价格

    Args:
        product: 产品信息
        price_data: 价格数据

    Returns:
        float: 产品价格（小时）
    """
    # 尝试从价格数据中获取产品价格
    service = product.get("aws_service")
    
    # 如果价格数据中包含该产品的价格信息
    if service in price_data:
        # 根据产品类型获取价格
        product_type = product.get("product_type", "")
        
        if product_type == "compute":
            instance_type = product.get("instance_type")
            if instance_type in price_data[service]:
                return float(price_data[service][instance_type])
        
        elif product_type == "storage":
            storage_class = product.get("storage_class")
            if storage_class in price_data[service]:
                return float(price_data[service][storage_class])
        
        elif product_type == "network":
            service_type = product.get("service_type")
            if service_type in price_data[service]:
                return float(price_data[service][service_type])
        
        elif product_type == "database":
            instance_type = product.get("instance_type")
            engine = product.get("engine")
            key = f"{engine}_{instance_type}"
            if key in price_data[service]:
                return float(price_data[service][key])
    
    # 如果无法获取实际价格，使用估算价格
    return estimate_product_price(product)


def estimate_product_price(product: Dict[str, Any]) -> float:
    """
    估算产品价格

    Args:
        product: 产品信息

    Returns:
        float: 估算的产品价格（小时）
    """
    # 根据产品类型估算价格
    product_type = product.get("product_type", "")
    
    if product_type == "compute":
        # 根据实例类型估算EC2价格
        instance_type = product.get("instance_type", "")
        
        # 基础价格
        base_price = 0.5  # 默认价格
        
        # 根据实例系列调整价格
        if "t3" in instance_type:
            base_price = 0.1
        elif "m5" in instance_type:
            base_price = 0.2
        elif "c5" in instance_type:
            base_price = 0.25
        elif "r5" in instance_type:
            base_price = 0.3
        
        # 根据实例大小调整价格
        if "micro" in instance_type:
            return base_price * 0.1
        elif "small" in instance_type:
            return base_price * 0.2
        elif "medium" in instance_type:
            return base_price * 0.4
        elif "large" in instance_type:
            return base_price * 0.8
        elif "xlarge" in instance_type:
            return base_price * 1.6
        elif "2xlarge" in instance_type:
            return base_price * 3.2
        elif "4xlarge" in instance_type:
            return base_price * 6.4
        
        return base_price
    
    elif product_type == "storage":
        # 根据存储类型和大小估算存储价格
        storage_class = product.get("storage_class", "")
        storage_size = product.get("matched_config", {}).get("storage_size_gb", 100)
        
        # 基础价格（每GB每小时）
        if "Standard" in storage_class:
            base_price = 0.0002  # S3 Standard
        elif "IA" in storage_class:
            base_price = 0.0001  # S3 IA
        elif "Glacier" in storage_class:
            base_price = 0.00005  # S3 Glacier
        elif "gp2" in storage_class or "gp3" in storage_class:
            base_price = 0.0001  # EBS gp2/gp3
        elif "io1" in storage_class or "io2" in storage_class:
            base_price = 0.0005  # EBS io1/io2
        elif "st1" in storage_class:
            base_price = 0.00008  # EBS st1
        else:
            base_price = 0.0001  # 默认价格
        
        return base_price * storage_size
    
    elif product_type == "network":
        # 根据服务类型和带宽估算网络价格
        service_type = product.get("service_type", "")
        bandwidth = product.get("matched_config", {}).get("bandwidth_mbps", 100)
        
        # 基础价格
        if "Load Balancer" in service_type:
            return 0.03  # ELB 每小时
        elif "CloudFront" in service_type:
            return 0.02 * (bandwidth / 100)  # CloudFront 根据带宽
        elif "Direct Connect" in service_type:
            return 0.05 * (bandwidth / 100)  # Direct Connect 根据带宽
        elif "VPC" in service_type:
            return 0.01  # VPC 每小时
        else:
            return 0.02  # 默认价格
    
    elif product_type == "database":
        # 根据实例类型和引擎估算数据库价格
        instance_type = product.get("instance_type", "")
        engine = product.get("engine", "")
        
        # 基础价格
        base_price = 0.2  # 默认价格
        
        # 根据引擎调整价格
        if "mysql" in engine.lower() or "mariadb" in engine.lower():
            base_price = 0.2
        elif "postgresql" in engine.lower():
            base_price = 0.25
        elif "oracle" in engine.lower():
            base_price = 0.4
        elif "sqlserver" in engine.lower():
            base_price = 0.35
        elif "aurora" in engine.lower():
            base_price = 0.3
        elif "dynamodb" in engine.lower():
            return 0.01  # DynamoDB 使用按需定价
        elif "redis" in engine.lower() or "memcached" in engine.lower():
            base_price = 0.15
        
        # 根据实例大小调整价格
        if "micro" in instance_type:
            return base_price * 0.1
        elif "small" in instance_type:
            return base_price * 0.2
        elif "medium" in instance_type:
            return base_price * 0.4
        elif "large" in instance_type:
            return base_price * 0.8
        elif "xlarge" in instance_type:
            return base_price * 1.6
        elif "2xlarge" in instance_type:
            return base_price * 3.2
        elif "4xlarge" in instance_type:
            return base_price * 6.4
        
        return base_price
    
    # 默认价格
    return 0.1


def get_region_name(region_code: str) -> str:
    """
    获取AWS区域的中文名称

    Args:
        region_code: AWS区域代码

    Returns:
        str: 区域中文名称
    """
    region_names = {
        "us-east-1": "美国东部（弗吉尼亚北部）",
        "us-east-2": "美国东部（俄亥俄州）",
        "us-west-1": "美国西部（加利福尼亚北部）",
        "us-west-2": "美国西部（俄勒冈）",
        "af-south-1": "非洲（开普敦）",
        "ap-east-1": "亚太地区（香港）",
        "ap-south-1": "亚太地区（孟买）",
        "ap-northeast-1": "亚太地区（东京）",
        "ap-northeast-2": "亚太地区（首尔）",
        "ap-northeast-3": "亚太地区（大阪）",
        "ap-southeast-1": "亚太地区（新加坡）",
        "ap-southeast-2": "亚太地区（悉尼）",
        "ca-central-1": "加拿大（中部）",
        "eu-central-1": "欧洲（法兰克福）",
        "eu-west-1": "欧洲（爱尔兰）",
        "eu-west-2": "欧洲（伦敦）",
        "eu-west-3": "欧洲（巴黎）",
        "eu-north-1": "欧洲（斯德哥尔摩）",
        "eu-south-1": "欧洲（米兰）",
        "me-south-1": "中东（巴林）",
        "sa-east-1": "南美洲（圣保罗）",
        "cn-north-1": "中国（北京）",
        "cn-northwest-1": "中国（宁夏）"
    }
    
    return region_names.get(region_code, f"未知区域({region_code})")


def translate_product_type(product_type: str) -> str:
    """
    将产品类型翻译为中文

    Args:
        product_type: 产品类型

    Returns:
        str: 中文产品类型
    """
    translations = {
        "compute": "计算",
        "storage": "存储",
        "network": "网络",
        "database": "数据库"
    }
    
    return translations.get(product_type, product_type)


def translate_service_name(service_name: str) -> str:
    """
    将AWS服务名称翻译为中文

    Args:
        service_name: AWS服务名称

    Returns:
        str: 中文服务名称
    """
    translations = {
        "Amazon EC2": "亚马逊弹性计算云 (EC2)",
        "Amazon S3": "亚马逊简单存储服务 (S3)",
        "Amazon EBS": "亚马逊弹性块存储 (EBS)",
        "Amazon EFS": "亚马逊弹性文件系统 (EFS)",
        "Amazon S3 Glacier": "亚马逊S3 Glacier",
        "Amazon VPC": "亚马逊虚拟私有云 (VPC)",
        "Elastic Load Balancing": "弹性负载均衡 (ELB)",
        "Amazon CloudFront": "亚马逊CloudFront",
        "Amazon Route 53": "亚马逊Route 53",
        "AWS Direct Connect": "AWS Direct Connect",
        "Amazon RDS": "亚马逊关系数据库服务 (RDS)",
        "Amazon DynamoDB": "亚马逊DynamoDB",
        "Amazon ElastiCache": "亚马逊ElastiCache",
        "Amazon Redshift": "亚马逊Redshift",
        "Amazon Aurora": "亚马逊Aurora"
    }
    
    return translations.get(service_name, service_name)