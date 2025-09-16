#!/usr/bin/env python3
"""
TSV Parser Tool

解析TSV格式的云平台账单或IDC配置清单，提取关键配置信息。
支持多种格式的TSV文件，能够处理不同的分隔符和表头结构。
"""

import json
import csv
import io
from typing import Dict, List, Any, Optional, Union
import strands
from strands import tool


@tool
def parse_tsv(
    file_content: str,
    header_row: int = 0,
    has_header: bool = True
) -> str:
    """
    解析TSV格式的云平台账单或IDC配置清单

    Args:
        file_content (str): TSV文件内容
        header_row (int, optional): 表头行号，默认为0
        has_header (bool, optional): 是否包含表头，默认为True

    Returns:
        str: 解析后的数据的JSON字符串，包含产品类型、配置参数、数量等信息

    Raises:
        ValueError: 当文件格式错误或解析失败时
    """
    try:
        # 检测分隔符（TSV应该是制表符，但也支持其他分隔符）
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(file_content[:1024])
        delimiter = dialect.delimiter
        
        # 如果没有检测到分隔符，默认使用制表符
        if not delimiter or len(delimiter) == 0:
            delimiter = '\t'
        
        # 解析TSV内容
        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        rows = list(reader)
        
        if len(rows) <= header_row:
            raise ValueError(f"文件行数({len(rows)})小于指定的表头行号({header_row})")
        
        # 提取表头和数据
        if has_header:
            headers = rows[header_row]
            data_rows = rows[header_row + 1:]
        else:
            # 如果没有表头，则使用列索引作为键
            headers = [f"column_{i}" for i in range(len(rows[0]))]
            data_rows = rows
        
        # 将数据转换为字典列表
        result = []
        for row in data_rows:
            if len(row) == 0:
                continue  # 跳过空行
                
            # 处理行长度不一致的情况
            row_data = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    key = headers[i]
                    row_data[key] = value
                else:
                    # 对于超出表头长度的数据，使用列索引作为键
                    row_data[f"column_{i}"] = value
            
            # 尝试识别产品类型
            product_type = identify_product_type(row_data, headers)
            if product_type:
                row_data["product_type"] = product_type
            
            # 尝试提取配置参数和数量
            config_params = extract_config_parameters(row_data, headers)
            if config_params:
                row_data["config_parameters"] = config_params
            
            quantity = extract_quantity(row_data, headers)
            if quantity is not None:
                row_data["quantity"] = quantity
                
            result.append(row_data)
        
        # 将结果转换为JSON字符串
        return json.dumps({
            "parsed_data": result,
            "detected_delimiter": delimiter,
            "headers": headers,
            "total_rows": len(data_rows),
            "has_header": has_header
        }, ensure_ascii=False)
        
    except Exception as e:
        raise ValueError(f"解析TSV文件失败: {str(e)}")


def identify_product_type(row_data: Dict[str, str], headers: List[str]) -> Optional[str]:
    """
    尝试识别行数据中的产品类型

    Args:
        row_data: 行数据字典
        headers: 表头列表

    Returns:
        str: 产品类型（compute, storage, network, database）或None
    """
    # 产品类型关键词映射
    type_keywords = {
        "compute": ["compute", "计算", "服务器", "实例", "vm", "cpu", "instance", "ec2", "虚拟机", "云主机"],
        "storage": ["storage", "存储", "磁盘", "disk", "volume", "s3", "oss", "对象存储", "块存储", "文件存储", "ebs"],
        "network": ["network", "网络", "带宽", "bandwidth", "流量", "traffic", "负载均衡", "elb", "slb", "cdn", "vpc"],
        "database": ["database", "数据库", "db", "rds", "redis", "mongodb", "nosql", "sql", "mysql", "postgresql"]
    }
    
    # 检查行数据中是否包含产品类型关键词
    for col, value in row_data.items():
        if not isinstance(value, str):
            continue
            
        value_lower = value.lower()
        col_lower = col.lower()
        
        # 检查值
        for product_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in value_lower:
                    return product_type
                    
        # 检查列名
        for product_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in col_lower:
                    return product_type
    
    return None


def extract_config_parameters(row_data: Dict[str, str], headers: List[str]) -> Optional[Dict[str, Any]]:
    """
    从行数据中提取配置参数

    Args:
        row_data: 行数据字典
        headers: 表头列表

    Returns:
        Dict: 配置参数字典或None
    """
    config_params = {}
    
    # 配置参数关键词映射
    param_keywords = {
        "cpu": ["cpu", "核", "core", "processor", "处理器"],
        "memory": ["memory", "内存", "ram", "mem"],
        "storage_size": ["storage", "disk", "磁盘", "容量", "size", "存储"],
        "storage_type": ["type", "类型", "ssd", "hdd", "nvme", "存储类型"],
        "iops": ["iops", "io", "读写速度"],
        "network_bandwidth": ["bandwidth", "带宽", "network", "网络"],
        "region": ["region", "区域", "地域", "zone", "可用区"],
        "database_engine": ["engine", "引擎", "database", "数据库类型"],
        "database_version": ["version", "版本"]
    }
    
    # 检查行数据中是否包含配置参数关键词
    for col, value in row_data.items():
        if not value or not isinstance(value, str):
            continue
            
        col_lower = col.lower()
        
        # 检查列名是否包含配置参数关键词
        for param, keywords in param_keywords.items():
            for keyword in keywords:
                if keyword in col_lower:
                    # 尝试将值转换为数字（如果可能）
                    try:
                        # 检查是否包含数字和单位
                        if any(char.isdigit() for char in value):
                            # 处理常见的单位后缀
                            if "gb" in value.lower() or "g" in value.lower():
                                # 提取数字部分
                                num_value = ''.join(char for char in value if char.isdigit() or char == '.')
                                config_params[param] = float(num_value)
                                config_params[f"{param}_unit"] = "GB"
                            elif "mb" in value.lower() or "m" in value.lower():
                                num_value = ''.join(char for char in value if char.isdigit() or char == '.')
                                config_params[param] = float(num_value)
                                config_params[f"{param}_unit"] = "MB"
                            elif "tb" in value.lower() or "t" in value.lower():
                                num_value = ''.join(char for char in value if char.isdigit() or char == '.')
                                config_params[param] = float(num_value)
                                config_params[f"{param}_unit"] = "TB"
                            elif "core" in value.lower() or "核" in value:
                                num_value = ''.join(char for char in value if char.isdigit() or char == '.')
                                config_params[param] = float(num_value)
                                config_params[f"{param}_unit"] = "cores"
                            else:
                                # 尝试直接转换为数字
                                config_params[param] = float(value) if '.' in value else int(value)
                        else:
                            # 非数字值直接存储
                            config_params[param] = value
                    except (ValueError, TypeError):
                        # 如果转换失败，则保留原始字符串
                        config_params[param] = value
                    break
    
    return config_params if config_params else None


def extract_quantity(row_data: Dict[str, str], headers: List[str]) -> Optional[int]:
    """
    从行数据中提取数量信息

    Args:
        row_data: 行数据字典
        headers: 表头列表

    Returns:
        int: 数量或None
    """
    # 数量关键词
    quantity_keywords = ["quantity", "数量", "count", "个数", "台数", "套数", "num", "number"]
    
    # 检查行数据中是否包含数量关键词
    for col, value in row_data.items():
        if not value:
            continue
            
        col_lower = col.lower()
        
        # 检查列名是否包含数量关键词
        for keyword in quantity_keywords:
            if keyword in col_lower:
                try:
                    return int(float(value))
                except (ValueError, TypeError):
                    # 如果转换失败，继续检查其他列
                    pass
    
    # 如果没有找到数量信息，默认为1
    return 1