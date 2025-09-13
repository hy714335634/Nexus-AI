#!/usr/bin/env python3
"""
Config Matcher Tool

将解析后的配置数据映射到匹配的AWS产品，支持计算、存储、网络、数据库四个核心产品类别。
能够处理不完整的配置信息，并根据已有信息推断合理的配置参数。
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
import strands
from strands import tool


@tool
def match_config(
    config_data: str,
    product_type: str,
    region: str = 'us-east-1'
) -> str:
    """
    将解析后的配置数据映射到匹配的AWS产品

    Args:
        config_data (str): 解析后的配置数据（JSON格式）
        product_type (str): 产品类型（compute, storage, network, database）
        region (str, optional): AWS区域代码，默认为us-east-1

    Returns:
        str: 匹配的AWS产品详情的JSON字符串，包含产品信息、配置参数和置信度评分

    Raises:
        ValueError: 当产品类型无效或配置数据格式错误时
    """
    try:
        # 验证产品类型
        valid_product_types = ["compute", "storage", "network", "database"]
        if product_type not in valid_product_types:
            raise ValueError(f"无效的产品类型: {product_type}，有效类型为: {', '.join(valid_product_types)}")
        
        # 解析配置数据
        config_dict = json.loads(config_data)
        
        # 根据产品类型选择匹配函数
        if product_type == "compute":
            result = match_compute_product(config_dict, region)
        elif product_type == "storage":
            result = match_storage_product(config_dict, region)
        elif product_type == "network":
            result = match_network_product(config_dict, region)
        elif product_type == "database":
            result = match_database_product(config_dict, region)
        
        # 将结果转换为JSON字符串
        return json.dumps(result, ensure_ascii=False)
        
    except json.JSONDecodeError:
        raise ValueError("配置数据格式错误，无法解析JSON")
    except Exception as e:
        raise ValueError(f"配置匹配失败: {str(e)}")


def match_compute_product(config_dict: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    匹配计算产品（EC2实例）

    Args:
        config_dict: 配置数据字典
        region: AWS区域代码

    Returns:
        Dict: 匹配的AWS计算产品详情
    """
    # 提取配置参数
    parsed_data = config_dict.get("parsed_data", [])
    if not parsed_data:
        raise ValueError("配置数据中未找到有效的解析结果")
    
    matched_products = []
    
    for item in parsed_data:
        # 检查是否为计算产品
        if "product_type" in item and item["product_type"] != "compute":
            continue
        
        config_params = item.get("config_parameters", {})
        quantity = item.get("quantity", 1)
        
        # 提取CPU和内存信息
        cpu = None
        memory = None
        
        if "cpu" in config_params:
            cpu = config_params["cpu"]
        
        if "memory" in config_params:
            memory = config_params["memory"]
            memory_unit = config_params.get("memory_unit", "GB")
            
            # 转换内存单位为GB
            if memory_unit == "MB":
                memory = memory / 1024
            elif memory_unit == "TB":
                memory = memory * 1024
        
        # 如果CPU或内存信息缺失，尝试推断
        if cpu is None or memory is None:
            cpu, memory = infer_compute_config(config_params)
        
        # 匹配EC2实例类型
        instance_type, confidence = match_ec2_instance(cpu, memory)
        
        # 构建匹配结果
        matched_product = {
            "aws_service": "Amazon EC2",
            "product_family": "Compute Instance",
            "instance_type": instance_type,
            "region": region,
            "quantity": quantity,
            "original_config": item,
            "matched_config": {
                "vcpu": cpu,
                "memory_gb": memory,
                "architecture": "x86_64",  # 默认架构
                "operating_system": "Linux"  # 默认操作系统
            },
            "confidence_score": confidence,
            "is_inferred": cpu is None or memory is None
        }
        
        # 添加操作系统信息（如果有）
        if "os" in config_params or "operating_system" in config_params:
            os_info = config_params.get("os") or config_params.get("operating_system")
            matched_product["matched_config"]["operating_system"] = map_os_name(os_info)
        
        matched_products.append(matched_product)
    
    return {
        "product_type": "compute",
        "matched_products": matched_products,
        "region": region,
        "service_code": "AmazonEC2"
    }


def match_storage_product(config_dict: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    匹配存储产品（S3、EBS等）

    Args:
        config_dict: 配置数据字典
        region: AWS区域代码

    Returns:
        Dict: 匹配的AWS存储产品详情
    """
    # 提取配置参数
    parsed_data = config_dict.get("parsed_data", [])
    if not parsed_data:
        raise ValueError("配置数据中未找到有效的解析结果")
    
    matched_products = []
    
    for item in parsed_data:
        # 检查是否为存储产品
        if "product_type" in item and item["product_type"] != "storage":
            continue
        
        config_params = item.get("config_parameters", {})
        quantity = item.get("quantity", 1)
        
        # 提取存储大小和类型信息
        storage_size = None
        storage_type = None
        
        if "storage_size" in config_params:
            storage_size = config_params["storage_size"]
            size_unit = config_params.get("storage_size_unit", "GB")
            
            # 转换存储单位为GB
            if size_unit == "MB":
                storage_size = storage_size / 1024
            elif size_unit == "TB":
                storage_size = storage_size * 1024
        
        if "storage_type" in config_params:
            storage_type = config_params["storage_type"]
        
        # 如果存储大小或类型信息缺失，尝试推断
        if storage_size is None:
            storage_size = 100  # 默认100GB
        
        # 根据配置特征确定存储服务类型
        storage_service, storage_class = determine_storage_service(config_params, storage_type)
        
        # 构建匹配结果
        matched_product = {
            "aws_service": storage_service,
            "storage_class": storage_class,
            "region": region,
            "quantity": quantity,
            "original_config": item,
            "matched_config": {
                "storage_size_gb": storage_size,
                "storage_type": storage_type or "General Purpose"
            },
            "confidence_score": 0.8 if storage_type else 0.6,
            "is_inferred": storage_size is None or storage_type is None
        }
        
        # 添加IOPS信息（如果有）
        if "iops" in config_params:
            matched_product["matched_config"]["iops"] = config_params["iops"]
        
        matched_products.append(matched_product)
    
    return {
        "product_type": "storage",
        "matched_products": matched_products,
        "region": region,
        "service_code": get_service_code_for_storage(matched_products[0]["aws_service"] if matched_products else "Amazon EBS")
    }


def match_network_product(config_dict: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    匹配网络产品（VPC、ELB等）

    Args:
        config_dict: 配置数据字典
        region: AWS区域代码

    Returns:
        Dict: 匹配的AWS网络产品详情
    """
    # 提取配置参数
    parsed_data = config_dict.get("parsed_data", [])
    if not parsed_data:
        raise ValueError("配置数据中未找到有效的解析结果")
    
    matched_products = []
    
    for item in parsed_data:
        # 检查是否为网络产品
        if "product_type" in item and item["product_type"] != "network":
            continue
        
        config_params = item.get("config_parameters", {})
        quantity = item.get("quantity", 1)
        
        # 提取网络带宽信息
        bandwidth = None
        
        if "network_bandwidth" in config_params:
            bandwidth = config_params["network_bandwidth"]
            bandwidth_unit = config_params.get("network_bandwidth_unit", "Mbps")
            
            # 转换带宽单位为Mbps
            if bandwidth_unit == "Gbps":
                bandwidth = bandwidth * 1000
            elif bandwidth_unit == "Kbps":
                bandwidth = bandwidth / 1000
        
        # 根据配置特征确定网络服务类型
        network_service, service_type = determine_network_service(config_params)
        
        # 构建匹配结果
        matched_product = {
            "aws_service": network_service,
            "service_type": service_type,
            "region": region,
            "quantity": quantity,
            "original_config": item,
            "matched_config": {
                "bandwidth_mbps": bandwidth or 100  # 默认100Mbps
            },
            "confidence_score": 0.7,
            "is_inferred": bandwidth is None
        }
        
        matched_products.append(matched_product)
    
    return {
        "product_type": "network",
        "matched_products": matched_products,
        "region": region,
        "service_code": get_service_code_for_network(matched_products[0]["aws_service"] if matched_products else "Amazon VPC")
    }


def match_database_product(config_dict: Dict[str, Any], region: str) -> Dict[str, Any]:
    """
    匹配数据库产品（RDS、DynamoDB等）

    Args:
        config_dict: 配置数据字典
        region: AWS区域代码

    Returns:
        Dict: 匹配的AWS数据库产品详情
    """
    # 提取配置参数
    parsed_data = config_dict.get("parsed_data", [])
    if not parsed_data:
        raise ValueError("配置数据中未找到有效的解析结果")
    
    matched_products = []
    
    for item in parsed_data:
        # 检查是否为数据库产品
        if "product_type" in item and item["product_type"] != "database":
            continue
        
        config_params = item.get("config_parameters", {})
        quantity = item.get("quantity", 1)
        
        # 提取数据库引擎和版本信息
        db_engine = None
        db_version = None
        
        if "database_engine" in config_params:
            db_engine = config_params["database_engine"]
        
        if "database_version" in config_params:
            db_version = config_params["database_version"]
        
        # 提取CPU和内存信息（用于确定数据库实例类型）
        cpu = None
        memory = None
        
        if "cpu" in config_params:
            cpu = config_params["cpu"]
        
        if "memory" in config_params:
            memory = config_params["memory"]
            memory_unit = config_params.get("memory_unit", "GB")
            
            # 转换内存单位为GB
            if memory_unit == "MB":
                memory = memory / 1024
            elif memory_unit == "TB":
                memory = memory * 1024
        
        # 如果CPU或内存信息缺失，尝试推断
        if cpu is None or memory is None:
            cpu, memory = infer_compute_config(config_params)
        
        # 确定数据库服务和引擎
        db_service, db_engine = determine_database_service(config_params, db_engine)
        
        # 匹配数据库实例类型
        instance_type, confidence = match_db_instance(cpu, memory, db_engine)
        
        # 构建匹配结果
        matched_product = {
            "aws_service": db_service,
            "engine": db_engine or "mysql",  # 默认MySQL
            "engine_version": db_version or "8.0",  # 默认版本
            "instance_type": instance_type,
            "region": region,
            "quantity": quantity,
            "original_config": item,
            "matched_config": {
                "vcpu": cpu,
                "memory_gb": memory,
                "storage_gb": config_params.get("storage_size", 100)  # 默认100GB
            },
            "confidence_score": confidence,
            "is_inferred": cpu is None or memory is None or db_engine is None
        }
        
        # 添加存储类型信息（如果有）
        if "storage_type" in config_params:
            matched_product["matched_config"]["storage_type"] = config_params["storage_type"]
        else:
            matched_product["matched_config"]["storage_type"] = "gp2"  # 默认通用型SSD
        
        matched_products.append(matched_product)
    
    return {
        "product_type": "database",
        "matched_products": matched_products,
        "region": region,
        "service_code": get_service_code_for_database(matched_products[0]["aws_service"] if matched_products else "AmazonRDS")
    }


def infer_compute_config(config_params: Dict[str, Any]) -> Tuple[float, float]:
    """
    根据已有信息推断计算配置

    Args:
        config_params: 配置参数字典

    Returns:
        Tuple[float, float]: 推断的CPU核数和内存大小(GB)
    """
    cpu = config_params.get("cpu")
    memory = config_params.get("memory")
    
    # 如果两者都有，直接返回
    if cpu is not None and memory is not None:
        return cpu, memory
    
    # 如果只有CPU，推断内存
    if cpu is not None and memory is None:
        # 一般内存是CPU核数的2-4倍（GB）
        memory = cpu * 4
        return cpu, memory
    
    # 如果只有内存，推断CPU
    if cpu is None and memory is not None:
        # 一般CPU核数是内存的1/4到1/2
        cpu = max(1, memory / 4)
        return cpu, memory
    
    # 如果都没有，返回默认值
    return 2.0, 8.0  # 默认2核8GB


def match_ec2_instance(cpu: float, memory: float) -> Tuple[str, float]:
    """
    根据CPU和内存匹配EC2实例类型

    Args:
        cpu: CPU核数
        memory: 内存大小(GB)

    Returns:
        Tuple[str, float]: 实例类型和置信度评分
    """
    # 常见EC2实例类型配置
    instance_types = [
        {"type": "t3.micro", "cpu": 2, "memory": 1, "family": "general_purpose"},
        {"type": "t3.small", "cpu": 2, "memory": 2, "family": "general_purpose"},
        {"type": "t3.medium", "cpu": 2, "memory": 4, "family": "general_purpose"},
        {"type": "t3.large", "cpu": 2, "memory": 8, "family": "general_purpose"},
        {"type": "t3.xlarge", "cpu": 4, "memory": 16, "family": "general_purpose"},
        {"type": "t3.2xlarge", "cpu": 8, "memory": 32, "family": "general_purpose"},
        {"type": "m5.large", "cpu": 2, "memory": 8, "family": "general_purpose"},
        {"type": "m5.xlarge", "cpu": 4, "memory": 16, "family": "general_purpose"},
        {"type": "m5.2xlarge", "cpu": 8, "memory": 32, "family": "general_purpose"},
        {"type": "m5.4xlarge", "cpu": 16, "memory": 64, "family": "general_purpose"},
        {"type": "c5.large", "cpu": 2, "memory": 4, "family": "compute_optimized"},
        {"type": "c5.xlarge", "cpu": 4, "memory": 8, "family": "compute_optimized"},
        {"type": "c5.2xlarge", "cpu": 8, "memory": 16, "family": "compute_optimized"},
        {"type": "c5.4xlarge", "cpu": 16, "memory": 32, "family": "compute_optimized"},
        {"type": "r5.large", "cpu": 2, "memory": 16, "family": "memory_optimized"},
        {"type": "r5.xlarge", "cpu": 4, "memory": 32, "family": "memory_optimized"},
        {"type": "r5.2xlarge", "cpu": 8, "memory": 64, "family": "memory_optimized"},
        {"type": "r5.4xlarge", "cpu": 16, "memory": 128, "family": "memory_optimized"}
    ]
    
    best_match = None
    min_diff = float('inf')
    
    for instance in instance_types:
        # 计算CPU和内存的差异
        cpu_diff = abs(instance["cpu"] - cpu)
        mem_diff = abs(instance["memory"] - memory)
        
        # 归一化差异（考虑CPU和内存的不同量级）
        normalized_diff = (cpu_diff / max(cpu, instance["cpu"])) + (mem_diff / max(memory, instance["memory"]))
        
        if normalized_diff < min_diff:
            min_diff = normalized_diff
            best_match = instance
    
    # 计算置信度评分（差异越小，置信度越高）
    confidence = max(0.5, 1.0 - min_diff)
    
    return best_match["type"], confidence


def map_os_name(os_info: str) -> str:
    """
    映射操作系统名称到标准AWS操作系统名称

    Args:
        os_info: 操作系统信息

    Returns:
        str: 标准化的操作系统名称
    """
    os_info = os_info.lower()
    
    if any(keyword in os_info for keyword in ["windows", "win"]):
        return "Windows"
    elif any(keyword in os_info for keyword in ["rhel", "red hat"]):
        return "RHEL"
    elif any(keyword in os_info for keyword in ["suse", "sles"]):
        return "SUSE"
    elif any(keyword in os_info for keyword in ["ubuntu"]):
        return "Ubuntu"
    elif any(keyword in os_info for keyword in ["centos"]):
        return "CentOS"
    elif any(keyword in os_info for keyword in ["debian"]):
        return "Debian"
    elif any(keyword in os_info for keyword in ["amazon", "amzn"]):
        return "Amazon Linux"
    else:
        return "Linux"  # 默认Linux


def determine_storage_service(config_params: Dict[str, Any], storage_type: Optional[str]) -> Tuple[str, str]:
    """
    根据配置参数确定存储服务类型

    Args:
        config_params: 配置参数字典
        storage_type: 存储类型

    Returns:
        Tuple[str, str]: 存储服务名称和存储类别
    """
    # 检查配置参数中的关键词
    param_str = json.dumps(config_params, ensure_ascii=False).lower()
    
    # 对象存储关键词
    if any(keyword in param_str for keyword in ["object", "对象", "s3", "oss", "bucket"]):
        return "Amazon S3", "Standard"
    
    # 文件存储关键词
    if any(keyword in param_str for keyword in ["file", "文件", "efs", "nfs", "smb"]):
        return "Amazon EFS", "Standard"
    
    # 归档存储关键词
    if any(keyword in param_str for keyword in ["archive", "归档", "glacier", "备份", "backup"]):
        return "Amazon S3 Glacier", "Deep Archive"
    
    # 根据存储类型判断
    if storage_type:
        storage_type_lower = storage_type.lower()
        if "ssd" in storage_type_lower or "固态" in storage_type_lower:
            return "Amazon EBS", "gp3"
        elif "hdd" in storage_type_lower or "机械" in storage_type_lower:
            return "Amazon EBS", "st1"
        elif "nvme" in storage_type_lower or "高性能" in storage_type_lower:
            return "Amazon EBS", "io2"
    
    # 默认返回EBS通用型SSD
    return "Amazon EBS", "gp2"


def determine_network_service(config_params: Dict[str, Any]) -> Tuple[str, str]:
    """
    根据配置参数确定网络服务类型

    Args:
        config_params: 配置参数字典

    Returns:
        Tuple[str, str]: 网络服务名称和服务类型
    """
    # 检查配置参数中的关键词
    param_str = json.dumps(config_params, ensure_ascii=False).lower()
    
    # 负载均衡关键词
    if any(keyword in param_str for keyword in ["load balancer", "负载均衡", "elb", "slb", "alb", "nlb"]):
        if "application" in param_str or "应用" in param_str:
            return "Elastic Load Balancing", "Application Load Balancer"
        elif "network" in param_str or "网络" in param_str:
            return "Elastic Load Balancing", "Network Load Balancer"
        else:
            return "Elastic Load Balancing", "Application Load Balancer"
    
    # CDN关键词
    if any(keyword in param_str for keyword in ["cdn", "内容分发", "content delivery"]):
        return "Amazon CloudFront", "Standard"
    
    # DNS关键词
    if any(keyword in param_str for keyword in ["dns", "域名", "domain", "route53"]):
        return "Amazon Route 53", "DNS"
    
    # VPN关键词
    if any(keyword in param_str for keyword in ["vpn", "专线", "direct connect"]):
        return "AWS Direct Connect", "Standard"
    
    # 默认返回VPC
    return "Amazon VPC", "Standard"


def determine_database_service(config_params: Dict[str, Any], db_engine: Optional[str]) -> Tuple[str, str]:
    """
    根据配置参数确定数据库服务类型

    Args:
        config_params: 配置参数字典
        db_engine: 数据库引擎

    Returns:
        Tuple[str, str]: 数据库服务名称和引擎类型
    """
    # 检查配置参数中的关键词
    param_str = json.dumps(config_params, ensure_ascii=False).lower()
    
    # 根据引擎类型判断
    if db_engine:
        db_engine_lower = db_engine.lower()
        
        # NoSQL数据库
        if any(keyword in db_engine_lower for keyword in ["dynamodb", "dynamo", "nosql"]):
            return "Amazon DynamoDB", "DynamoDB"
        
        # 缓存数据库
        if any(keyword in db_engine_lower for keyword in ["redis", "memcached", "缓存", "cache"]):
            return "Amazon ElastiCache", "Redis" if "redis" in db_engine_lower else "Memcached"
        
        # 数据仓库
        if any(keyword in db_engine_lower for keyword in ["redshift", "数据仓库", "warehouse"]):
            return "Amazon Redshift", "Redshift"
        
        # 关系型数据库
        if any(keyword in db_engine_lower for keyword in ["mysql", "mariadb"]):
            return "Amazon RDS", "MySQL"
        if any(keyword in db_engine_lower for keyword in ["postgresql", "postgres"]):
            return "Amazon RDS", "PostgreSQL"
        if any(keyword in db_engine_lower for keyword in ["oracle"]):
            return "Amazon RDS", "Oracle"
        if any(keyword in db_engine_lower for keyword in ["sqlserver", "sql server"]):
            return "Amazon RDS", "SQL Server"
        if any(keyword in db_engine_lower for keyword in ["aurora"]):
            return "Amazon Aurora", "MySQL"
    
    # 检查配置参数中的关键词
    if any(keyword in param_str for keyword in ["dynamodb", "dynamo", "nosql"]):
        return "Amazon DynamoDB", "DynamoDB"
    if any(keyword in param_str for keyword in ["redis", "memcached", "缓存", "cache"]):
        return "Amazon ElastiCache", "Redis"
    if any(keyword in param_str for keyword in ["redshift", "数据仓库", "warehouse"]):
        return "Amazon Redshift", "Redshift"
    if any(keyword in param_str for keyword in ["mysql", "mariadb"]):
        return "Amazon RDS", "MySQL"
    if any(keyword in param_str for keyword in ["postgresql", "postgres"]):
        return "Amazon RDS", "PostgreSQL"
    if any(keyword in param_str for keyword in ["oracle"]):
        return "Amazon RDS", "Oracle"
    if any(keyword in param_str for keyword in ["sqlserver", "sql server"]):
        return "Amazon RDS", "SQL Server"
    if any(keyword in param_str for keyword in ["aurora"]):
        return "Amazon Aurora", "MySQL"
    
    # 默认返回RDS MySQL
    return "Amazon RDS", "MySQL"


def match_db_instance(cpu: float, memory: float, db_engine: Optional[str]) -> Tuple[str, float]:
    """
    根据CPU和内存匹配数据库实例类型

    Args:
        cpu: CPU核数
        memory: 内存大小(GB)
        db_engine: 数据库引擎

    Returns:
        Tuple[str, float]: 实例类型和置信度评分
    """
    # 常见RDS实例类型配置
    instance_types = [
        {"type": "db.t3.micro", "cpu": 2, "memory": 1, "family": "general_purpose"},
        {"type": "db.t3.small", "cpu": 2, "memory": 2, "family": "general_purpose"},
        {"type": "db.t3.medium", "cpu": 2, "memory": 4, "family": "general_purpose"},
        {"type": "db.t3.large", "cpu": 2, "memory": 8, "family": "general_purpose"},
        {"type": "db.t3.xlarge", "cpu": 4, "memory": 16, "family": "general_purpose"},
        {"type": "db.t3.2xlarge", "cpu": 8, "memory": 32, "family": "general_purpose"},
        {"type": "db.m5.large", "cpu": 2, "memory": 8, "family": "general_purpose"},
        {"type": "db.m5.xlarge", "cpu": 4, "memory": 16, "family": "general_purpose"},
        {"type": "db.m5.2xlarge", "cpu": 8, "memory": 32, "family": "general_purpose"},
        {"type": "db.m5.4xlarge", "cpu": 16, "memory": 64, "family": "general_purpose"},
        {"type": "db.r5.large", "cpu": 2, "memory": 16, "family": "memory_optimized"},
        {"type": "db.r5.xlarge", "cpu": 4, "memory": 32, "family": "memory_optimized"},
        {"type": "db.r5.2xlarge", "cpu": 8, "memory": 64, "family": "memory_optimized"},
        {"type": "db.r5.4xlarge", "cpu": 16, "memory": 128, "family": "memory_optimized"}
    ]
    
    best_match = None
    min_diff = float('inf')
    
    for instance in instance_types:
        # 计算CPU和内存的差异
        cpu_diff = abs(instance["cpu"] - cpu)
        mem_diff = abs(instance["memory"] - memory)
        
        # 归一化差异（考虑CPU和内存的不同量级）
        normalized_diff = (cpu_diff / max(cpu, instance["cpu"])) + (mem_diff / max(memory, instance["memory"]))
        
        if normalized_diff < min_diff:
            min_diff = normalized_diff
            best_match = instance
    
    # 计算置信度评分（差异越小，置信度越高）
    confidence = max(0.5, 1.0 - min_diff)
    
    return best_match["type"], confidence


def get_service_code_for_storage(service_name: str) -> str:
    """
    获取存储服务的服务代码

    Args:
        service_name: 存储服务名称

    Returns:
        str: 服务代码
    """
    service_codes = {
        "Amazon S3": "AmazonS3",
        "Amazon EBS": "AmazonEBS",
        "Amazon EFS": "AmazonEFS",
        "Amazon S3 Glacier": "AmazonGlacier"
    }
    
    return service_codes.get(service_name, "AmazonEBS")


def get_service_code_for_network(service_name: str) -> str:
    """
    获取网络服务的服务代码

    Args:
        service_name: 网络服务名称

    Returns:
        str: 服务代码
    """
    service_codes = {
        "Amazon VPC": "AmazonVPC",
        "Elastic Load Balancing": "AmazonELB",
        "Amazon CloudFront": "AmazonCloudFront",
        "Amazon Route 53": "AmazonRoute53",
        "AWS Direct Connect": "AWSDirectConnect"
    }
    
    return service_codes.get(service_name, "AmazonVPC")


def get_service_code_for_database(service_name: str) -> str:
    """
    获取数据库服务的服务代码

    Args:
        service_name: 数据库服务名称

    Returns:
        str: 服务代码
    """
    service_codes = {
        "Amazon RDS": "AmazonRDS",
        "Amazon DynamoDB": "AmazonDynamoDB",
        "Amazon ElastiCache": "AmazonElastiCache",
        "Amazon Redshift": "AmazonRedshift",
        "Amazon Aurora": "AmazonRDS"
    }
    
    return service_codes.get(service_name, "AmazonRDS")