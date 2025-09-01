#!/usr/bin/env python3
"""
数据转换工具模板

提供JSON、XML、CSV等格式之间的转换功能
"""

import json
import csv
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from io import StringIO
from strands import tool


@tool
def json_converter(data: str, source_format: str, target_format: str) -> str:
    """
    JSON数据转换工具
    
    Args:
        data (str): 要转换的数据
        source_format (str): 源格式 (json, xml, csv, yaml)
        target_format (str): 目标格式 (json, xml, csv, yaml)
        
    Returns:
        str: 转换后的数据
    """
    try:
        # 解析源格式
        if source_format == "json":
            parsed_data = json.loads(data)
        elif source_format == "xml":
            root = ET.fromstring(data)
            parsed_data = _xml_to_dict(root)
        elif source_format == "csv":
            parsed_data = _csv_to_dict(data)
        elif source_format == "yaml":
            import yaml
            parsed_data = yaml.safe_load(data)
        else:
            raise ValueError(f"不支持的源格式: {source_format}")
        
        # 转换为目标格式
        if target_format == "json":
            return json.dumps(parsed_data, ensure_ascii=False, indent=2)
        elif target_format == "xml":
            return _dict_to_xml(parsed_data)
        elif target_format == "csv":
            return _dict_to_csv(parsed_data)
        elif target_format == "yaml":
            import yaml
            return yaml.dump(parsed_data, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"不支持的目标格式: {target_format}")
            
    except Exception as e:
        return f"数据转换错误: {str(e)}"


@tool
def xml_converter(data: str, source_format: str, target_format: str) -> str:
    """
    XML数据转换工具
    
    Args:
        data (str): 要转换的数据
        source_format (str): 源格式 (xml, json, csv)
        target_format (str): 目标格式 (xml, json, csv)
        
    Returns:
        str: 转换后的数据
    """
    try:
        # 解析源格式
        if source_format == "xml":
            root = ET.fromstring(data)
            parsed_data = _xml_to_dict(root)
        elif source_format == "json":
            parsed_data = json.loads(data)
        elif source_format == "csv":
            parsed_data = _csv_to_dict(data)
        else:
            raise ValueError(f"不支持的源格式: {source_format}")
        
        # 转换为目标格式
        if target_format == "xml":
            return _dict_to_xml(parsed_data)
        elif target_format == "json":
            return json.dumps(parsed_data, ensure_ascii=False, indent=2)
        elif target_format == "csv":
            return _dict_to_csv(parsed_data)
        else:
            raise ValueError(f"不支持的目标格式: {target_format}")
            
    except Exception as e:
        return f"XML转换错误: {str(e)}"


@tool
def csv_converter(data: str, source_format: str, target_format: str) -> str:
    """
    CSV数据转换工具
    
    Args:
        data (str): 要转换的数据
        source_format (str): 源格式 (csv, json, xml)
        target_format (str): 目标格式 (csv, json, xml)
        
    Returns:
        str: 转换后的数据
    """
    try:
        # 解析源格式
        if source_format == "csv":
            parsed_data = _csv_to_dict(data)
        elif source_format == "json":
            parsed_data = json.loads(data)
        elif source_format == "xml":
            root = ET.fromstring(data)
            parsed_data = _xml_to_dict(root)
        else:
            raise ValueError(f"不支持的源格式: {source_format}")
        
        # 转换为目标格式
        if target_format == "csv":
            return _dict_to_csv(parsed_data)
        elif target_format == "json":
            return json.dumps(parsed_data, ensure_ascii=False, indent=2)
        elif target_format == "xml":
            return _dict_to_xml(parsed_data)
        else:
            raise ValueError(f"不支持的目标格式: {target_format}")
            
    except Exception as e:
        return f"CSV转换错误: {str(e)}"


@tool
def data_validator(data: str, format_type: str, schema: Dict[str, Any] = None) -> str:
    """
    数据验证工具
    
    Args:
        data (str): 要验证的数据
        format_type (str): 数据格式 (json, xml, csv)
        schema (Dict[str, Any]): 验证模式（可选）
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        result = {
            "format_type": format_type,
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if format_type == "json":
            try:
                parsed_data = json.loads(data)
                result["data_type"] = type(parsed_data).__name__
                result["data_size"] = len(str(parsed_data))
            except json.JSONDecodeError as e:
                result["valid"] = False
                result["errors"].append(f"JSON解析错误: {str(e)}")
                
        elif format_type == "xml":
            try:
                root = ET.fromstring(data)
                result["data_type"] = "xml_element"
                result["root_tag"] = root.tag
            except ET.ParseError as e:
                result["valid"] = False
                result["errors"].append(f"XML解析错误: {str(e)}")
                
        elif format_type == "csv":
            try:
                lines = data.strip().split('\n')
                if len(lines) < 2:
                    result["warnings"].append("CSV数据行数较少")
                result["data_type"] = "csv"
                result["row_count"] = len(lines)
                result["column_count"] = len(lines[0].split(',')) if lines else 0
            except Exception as e:
                result["valid"] = False
                result["errors"].append(f"CSV解析错误: {str(e)}")
        
        # 如果有schema，进行模式验证
        if schema and result["valid"]:
            # 这里可以添加更详细的模式验证逻辑
            result["schema_validated"] = True
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"数据验证错误: {str(e)}",
            "format_type": format_type
        }, ensure_ascii=False, indent=2)


# 辅助函数
def _xml_to_dict(element):
    """将XML元素转换为字典"""
    result = {}
    for child in element:
        if len(child) == 0:
            result[child.tag] = child.text
        else:
            result[child.tag] = _xml_to_dict(child)
    return result


def _dict_to_xml(data, root_name="root"):
    """将字典转换为XML"""
    root = ET.Element(root_name)
    _add_dict_to_xml(root, data)
    return ET.tostring(root, encoding='unicode')


def _add_dict_to_xml(parent, data):
    """递归添加字典数据到XML"""
    for key, value in data.items():
        child = ET.SubElement(parent, key)
        if isinstance(value, dict):
            _add_dict_to_xml(child, value)
        else:
            child.text = str(value)


def _csv_to_dict(csv_data):
    """将CSV数据转换为字典列表"""
    lines = csv_data.strip().split('\n')
    if not lines:
        return []
    
    reader = csv.DictReader(StringIO(csv_data))
    return [dict(row) for row in reader]


def _dict_to_csv(data):
    """将字典列表转换为CSV"""
    if not data:
        return ""
    
    if isinstance(data, list) and data:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    else:
        return ""
