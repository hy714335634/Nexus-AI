#!/usr/bin/env python3
"""
Excel文件写入工具

提供Excel文件写入和处理功能，支持生成公司信息报告
"""

import os
import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from strands import tool


@tool
def excel_writer(data: str, output_path: str, sheet_name: Optional[str] = None) -> str:
    """
    将数据写入Excel文件
    
    Args:
        data: 要写入的数据(JSON字符串)，应为对象列表
        output_path: 输出Excel文件路径
        sheet_name: 工作表名称，如果不提供则使用"Sheet1"
    
    Returns:
        JSON格式的写入结果
    """
    try:
        # 解析数据
        try:
            json_data = json.loads(data) if isinstance(data, str) else data
            if not isinstance(json_data, list):
                return json.dumps({
                    "status": "error",
                    "message": "数据必须是对象列表",
                    "output_path": output_path
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析数据失败: {str(e)}",
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建DataFrame
        df = pd.DataFrame(json_data)
        
        # 写入Excel文件
        sheet_name = sheet_name or "Sheet1"
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return json.dumps({
            "status": "success",
            "message": f"成功写入数据到Excel文件",
            "output_path": output_path,
            "rows_written": len(json_data),
            "columns_written": len(df.columns),
            "sheet_name": sheet_name
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"写入Excel文件时发生错误: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False)


@tool
def excel_append_sheet(data: str, file_path: str, sheet_name: str) -> str:
    """
    向现有Excel文件添加新工作表
    
    Args:
        data: 要写入的数据(JSON字符串)，应为对象列表
        file_path: 现有Excel文件路径
        sheet_name: 新工作表名称
    
    Returns:
        JSON格式的写入结果
    """
    try:
        # 解析数据
        try:
            json_data = json.loads(data) if isinstance(data, str) else data
            if not isinstance(json_data, list):
                return json.dumps({
                    "status": "error",
                    "message": "数据必须是对象列表",
                    "file_path": file_path,
                    "sheet_name": sheet_name
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析数据失败: {str(e)}",
                "file_path": file_path,
                "sheet_name": sheet_name
            }, ensure_ascii=False)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}",
                "file_path": file_path,
                "sheet_name": sheet_name
            }, ensure_ascii=False)
        
        # 创建DataFrame
        df = pd.DataFrame(json_data)
        
        # 读取现有Excel文件
        try:
            book = pd.ExcelFile(file_path)
            existing_sheets = book.sheet_names
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"读取现有Excel文件失败: {str(e)}",
                "file_path": file_path,
                "sheet_name": sheet_name
            }, ensure_ascii=False)
        
        # 检查工作表是否已存在
        if sheet_name in existing_sheets:
            return json.dumps({
                "status": "error",
                "message": f"工作表已存在: {sheet_name}",
                "file_path": file_path,
                "sheet_name": sheet_name,
                "existing_sheets": existing_sheets
            }, ensure_ascii=False)
        
        # 读取所有现有工作表
        all_dfs = {}
        for sheet in existing_sheets:
            all_dfs[sheet] = pd.read_excel(file_path, sheet_name=sheet)
        
        # 添加新工作表
        all_dfs[sheet_name] = df
        
        # 写回Excel文件
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for sheet, sheet_df in all_dfs.items():
                sheet_df.to_excel(writer, sheet_name=sheet, index=False)
        
        return json.dumps({
            "status": "success",
            "message": f"成功添加新工作表到Excel文件",
            "file_path": file_path,
            "sheet_name": sheet_name,
            "rows_written": len(json_data),
            "columns_written": len(df.columns),
            "all_sheets": list(all_dfs.keys())
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"添加工作表时发生错误: {str(e)}",
            "file_path": file_path,
            "sheet_name": sheet_name
        }, ensure_ascii=False)


@tool
def merge_csv_to_excel(csv_files: List[str], output_path: str, 
                      sheet_names: Optional[List[str]] = None) -> str:
    """
    合并多个CSV文件到一个Excel文件的不同工作表
    
    Args:
        csv_files: CSV文件路径列表
        output_path: 输出Excel文件路径
        sheet_names: 工作表名称列表，如果不提供则使用CSV文件名
    
    Returns:
        JSON格式的合并结果
    """
    try:
        if not csv_files:
            return json.dumps({
                "status": "error",
                "message": "CSV文件列表不能为空",
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 验证所有CSV文件是否存在
        missing_files = [file for file in csv_files if not os.path.exists(file)]
        if missing_files:
            return json.dumps({
                "status": "error",
                "message": f"以下CSV文件不存在: {', '.join(missing_files)}",
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 生成工作表名称
        if not sheet_names:
            sheet_names = []
            for file in csv_files:
                sheet_name = os.path.splitext(os.path.basename(file))[0]
                # Excel工作表名称不能超过31个字符
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]
                sheet_names.append(sheet_name)
        elif len(sheet_names) != len(csv_files):
            return json.dumps({
                "status": "error",
                "message": f"工作表名称数量({len(sheet_names)})与CSV文件数量({len(csv_files)})不匹配",
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 确保工作表名称唯一
        if len(set(sheet_names)) != len(sheet_names):
            # 为重复的工作表名称添加序号
            unique_names = set()
            for i in range(len(sheet_names)):
                original_name = sheet_names[i]
                if original_name in unique_names:
                    counter = 1
                    while f"{original_name}_{counter}" in unique_names:
                        counter += 1
                    sheet_names[i] = f"{original_name}_{counter}"
                unique_names.add(sheet_names[i])
        
        # 读取所有CSV文件并写入Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for i, file in enumerate(csv_files):
                try:
                    df = pd.read_csv(file)
                    df.to_excel(writer, sheet_name=sheet_names[i], index=False)
                except Exception as e:
                    return json.dumps({
                        "status": "error",
                        "message": f"处理CSV文件时出错 {file}: {str(e)}",
                        "output_path": output_path
                    }, ensure_ascii=False)
        
        return json.dumps({
            "status": "success",
            "message": f"成功合并{len(csv_files)}个CSV文件到Excel文件",
            "output_path": output_path,
            "csv_files": csv_files,
            "sheet_names": sheet_names
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"合并CSV文件时发生错误: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False)


@tool
def create_company_report(company_data: str, output_path: str, 
                         include_charts: bool = True) -> str:
    """
    创建格式化的公司信息报告Excel文件
    
    Args:
        company_data: 公司信息数据(JSON字符串)，应为对象列表
        output_path: 输出Excel文件路径
        include_charts: 是否包含图表，默认为True
    
    Returns:
        JSON格式的报告创建结果
    """
    try:
        # 解析数据
        try:
            companies = json.loads(company_data) if isinstance(company_data, str) else company_data
            if not isinstance(companies, list):
                return json.dumps({
                    "status": "error",
                    "message": "数据必须是对象列表",
                    "output_path": output_path
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"解析数据失败: {str(e)}",
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建主数据DataFrame
        main_df = pd.DataFrame(companies)
        
        # 处理嵌套数据
        for company in companies:
            for key, value in company.items():
                if isinstance(value, (dict, list)):
                    company[key] = json.dumps(value, ensure_ascii=False)
        
        # 创建处理后的DataFrame
        df = pd.DataFrame(companies)
        
        # 写入Excel文件
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 主数据表
            df.to_excel(writer, sheet_name="公司信息", index=False)
            
            # 添加统计表
            _add_statistics_sheet(writer, df)
            
            # 如果需要图表，添加图表数据
            if include_charts:
                _add_chart_data(writer, df)
        
        return json.dumps({
            "status": "success",
            "message": f"成功创建公司信息报告",
            "output_path": output_path,
            "companies_count": len(companies),
            "fields_count": len(df.columns),
            "sheets_created": ["公司信息", "统计信息"] + (["图表数据"] if include_charts else [])
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"创建公司报告时发生错误: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False)


def _add_statistics_sheet(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
    """添加统计信息工作表"""
    # 计算统计信息
    stats = []
    
    # 总公司数
    stats.append({
        "统计项": "总公司数",
        "数值": len(df)
    })
    
    # 字段完整性统计
    for column in df.columns:
        non_empty = df[column].astype(str).str.strip().str.len() > 0
        completion_rate = non_empty.mean() * 100
        stats.append({
            "统计项": f"{column} 字段完整率",
            "数值": f"{completion_rate:.2f}%"
        })
    
    # 创建统计表
    stats_df = pd.DataFrame(stats)
    stats_df.to_excel(writer, sheet_name="统计信息", index=False)


def _add_chart_data(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
    """添加图表数据工作表"""
    chart_data = []
    
    # 添加一些示例图表数据
    # 这里只是准备数据，实际图表需要在Excel中手动创建
    
    # 按行业分组
    if "industry" in df.columns:
        industry_counts = df["industry"].value_counts().reset_index()
        industry_counts.columns = ["行业", "公司数量"]
        industry_counts.to_excel(writer, sheet_name="图表数据", startrow=0, index=False)
    
    # 按地区分组
    if "headquarters" in df.columns:
        # 提取国家/地区
        df["region"] = df["headquarters"].astype(str).str.split(",").str[-1].str.strip()
        region_counts = df["region"].value_counts().reset_index()
        region_counts.columns = ["地区", "公司数量"]
        region_counts.to_excel(writer, sheet_name="图表数据", startrow=len(industry_counts) + 3 if "industry" in df.columns else 0, index=False)