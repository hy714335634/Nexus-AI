#!/usr/bin/env python3
"""
Excel文件读取工具

提供Excel文件读取和解析功能，支持处理公司信息数据
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from strands import tool


@tool
def excel_reader(file_path: str, sheet_name: Optional[str] = None, 
                required_columns: Optional[List[str]] = None, 
                max_rows: Optional[int] = None) -> str:
    """
    读取Excel文件中的公司信息
    
    Args:
        file_path (str): Excel文件路径
        sheet_name (str, optional): 要读取的工作表名称，如果不提供则读取第一个工作表
        required_columns (List[str], optional): 必需的列名列表，如果不提供则不检查
        max_rows (int, optional): 最大读取行数，如果不提供则读取所有行
    
    Returns:
        str: JSON格式的读取结果，包含公司信息数据和元数据
    """
    try:
        # 验证文件存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 验证文件是否为Excel文件
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return json.dumps({
                "status": "error",
                "message": f"不支持的文件格式，请提供.xlsx或.xls文件",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 读取Excel文件
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取Excel文件失败: {str(e)}",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 验证必需的列
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return json.dumps({
                    "status": "error",
                    "message": f"Excel文件缺少必需的列: {', '.join(missing_columns)}",
                    "data": None
                }, ensure_ascii=False, indent=2)
        
        # 限制行数
        if max_rows and max_rows > 0:
            df = df.head(max_rows)
        
        # 处理NaN值
        df = df.fillna("")
        
        # 转换为字典列表
        data = df.to_dict(orient='records')
        
        # 构建结果
        result = {
            "status": "success",
            "message": "Excel文件读取成功",
            "metadata": {
                "file_path": file_path,
                "sheet_name": sheet_name or "默认工作表",
                "total_rows": len(data),
                "total_columns": len(df.columns),
                "columns": list(df.columns)
            },
            "data": data
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"处理Excel文件时发生错误: {str(e)}",
            "data": None
        }, ensure_ascii=False, indent=2)


@tool
def excel_reader_batch(file_path: str, sheet_name: Optional[str] = None, 
                      required_columns: Optional[List[str]] = None,
                      batch_size: int = 10, batch_number: int = 1) -> str:
    """
    分批读取Excel文件中的公司信息
    
    Args:
        file_path (str): Excel文件路径
        sheet_name (str, optional): 要读取的工作表名称，如果不提供则读取第一个工作表
        required_columns (List[str], optional): 必需的列名列表，如果不提供则不检查
        batch_size (int): 每批读取的行数，默认为10
        batch_number (int): 要读取的批次编号，从1开始，默认为1
    
    Returns:
        str: JSON格式的读取结果，包含当前批次的公司信息数据和元数据
    """
    try:
        # 验证文件存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 验证文件是否为Excel文件
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return json.dumps({
                "status": "error",
                "message": f"不支持的文件格式，请提供.xlsx或.xls文件",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 验证批次参数
        if batch_size <= 0:
            return json.dumps({
                "status": "error",
                "message": "batch_size必须大于0",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        if batch_number <= 0:
            return json.dumps({
                "status": "error",
                "message": "batch_number必须大于0",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 读取Excel文件
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取Excel文件失败: {str(e)}",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 验证必需的列
        if required_columns:
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return json.dumps({
                    "status": "error",
                    "message": f"Excel文件缺少必需的列: {', '.join(missing_columns)}",
                    "data": None
                }, ensure_ascii=False, indent=2)
        
        # 计算总批次数
        total_rows = len(df)
        total_batches = (total_rows + batch_size - 1) // batch_size  # 向上取整
        
        # 验证批次编号
        if batch_number > total_batches:
            return json.dumps({
                "status": "error",
                "message": f"批次编号超出范围，总批次数为 {total_batches}",
                "data": None
            }, ensure_ascii=False, indent=2)
        
        # 计算当前批次的起始和结束索引
        start_idx = (batch_number - 1) * batch_size
        end_idx = min(start_idx + batch_size, total_rows)
        
        # 获取当前批次的数据
        batch_df = df.iloc[start_idx:end_idx]
        
        # 处理NaN值
        batch_df = batch_df.fillna("")
        
        # 转换为字典列表
        batch_data = batch_df.to_dict(orient='records')
        
        # 构建结果
        result = {
            "status": "success",
            "message": f"成功读取第 {batch_number}/{total_batches} 批数据",
            "metadata": {
                "file_path": file_path,
                "sheet_name": sheet_name or "默认工作表",
                "total_rows": total_rows,
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "batch_size": batch_size,
                "current_batch": batch_number,
                "total_batches": total_batches,
                "batch_start_index": start_idx,
                "batch_end_index": end_idx - 1,
                "batch_row_count": len(batch_data)
            },
            "data": batch_data
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"处理Excel文件时发生错误: {str(e)}",
            "data": None
        }, ensure_ascii=False, indent=2)


@tool
def excel_get_structure(file_path: str) -> str:
    """
    获取Excel文件的结构信息，包括所有工作表和列名
    
    Args:
        file_path (str): Excel文件路径
    
    Returns:
        str: JSON格式的Excel文件结构信息
    """
    try:
        # 验证文件存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}",
                "structure": None
            }, ensure_ascii=False, indent=2)
        
        # 验证文件是否为Excel文件
        if not file_path.lower().endswith(('.xlsx', '.xls')):
            return json.dumps({
                "status": "error",
                "message": f"不支持的文件格式，请提供.xlsx或.xls文件",
                "structure": None
            }, ensure_ascii=False, indent=2)
        
        # 读取Excel文件的所有工作表
        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # 获取每个工作表的结构
            sheets_structure = []
            for sheet in sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)  # 只读取第一行来获取列名
                sheets_structure.append({
                    "sheet_name": sheet,
                    "columns": list(df.columns),
                    "column_count": len(df.columns)
                })
            
            # 构建结果
            result = {
                "status": "success",
                "message": "成功获取Excel文件结构",
                "file_info": {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path),
                    "file_size_formatted": _format_file_size(os.path.getsize(file_path)),
                    "last_modified": os.path.getmtime(file_path)
                },
                "structure": {
                    "sheet_count": len(sheet_names),
                    "sheets": sheets_structure
                }
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取Excel文件结构失败: {str(e)}",
                "structure": None
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"处理Excel文件时发生错误: {str(e)}",
            "structure": None
        }, ensure_ascii=False, indent=2)


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读形式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"