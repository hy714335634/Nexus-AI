#!/usr/bin/env python3
"""
JSON文件夹处理工具

该工具能够处理文件夹中的所有JSON文件，读取公司信息数据，合并处理并输出为Excel文件。
参考agent逻辑和excel_writer逻辑，提供完整的数据处理流程。

功能特点:
1. 扫描指定文件夹中的所有JSON文件
2. 读取和解析JSON数据
3. 数据清洗和标准化处理
4. 合并所有公司信息
5. 生成Excel输出文件
6. 提供详细的处理报告

作者: Nexus-AI平台
版本: 1.0.0
日期: 2025-09-30
"""

import os
import json
import time
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from strands import tool


@tool
def process_json_folder(folder_path: str, output_path: str, 
                       include_metadata: bool = False,
                       sheet_name: Optional[str] = None,
                       create_report: bool = True) -> str:
    """
    处理文件夹中的所有JSON文件，合并数据并输出为Excel文件
    
    Args:
        folder_path: 包含JSON文件的文件夹路径,一般为.cache/company_info_search_agent/<task_id>/
        output_path: 输出Excel文件路径
        include_metadata: 是否包含元数据字段，默认为False
        sheet_name: 工作表名称，如果不提供则使用"公司信息"
        create_report: 是否创建处理报告，默认为True
    
    Returns:
        JSON格式的处理结果
    """
    try:
        # 验证文件夹路径
        folder = Path(folder_path)
        if not folder.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件夹不存在: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path
            }, ensure_ascii=False)
        
        if not folder.is_dir():
            return json.dumps({
                "status": "error",
                "message": f"路径不是文件夹: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 扫描JSON文件
        json_files = list(folder.glob("*.json"))
        if not json_files:
            return json.dumps({
                "status": "error",
                "message": f"文件夹中没有找到JSON文件: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 处理统计信息
        processing_stats = {
            "total_files": len(json_files),
            "successful_files": 0,
            "failed_files": 0,
            "failed_file_details": [],
            "start_time": time.time()
        }
        
        # 读取和处理所有JSON文件
        companies_data = []
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 处理元数据
                if not include_metadata and "_metadata" in data:
                    metadata = data.pop("_metadata")
                    # 保留公司名称（如果元数据中有的话）
                    if "company_name" in metadata and "Company-Name-ENG" not in data:
                        data["Company-Name-ENG"] = metadata["company_name"]
                
                # 数据标准化处理
                processed_data = _standardize_company_data(data, json_file.name)
                companies_data.append(processed_data)
                processing_stats["successful_files"] += 1
                
            except Exception as e:
                processing_stats["failed_files"] += 1
                processing_stats["failed_file_details"].append({
                    "file_name": json_file.name,
                    "error": str(e)
                })
        
        if not companies_data:
            return json.dumps({
                "status": "error",
                "message": f"无法处理任何JSON文件: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path,
                "processing_stats": processing_stats
            }, ensure_ascii=False)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建DataFrame
        df = pd.DataFrame(companies_data)
        
        # 写入Excel文件
        sheet_name = sheet_name or "公司信息"
        processing_stats["end_time"] = time.time()
        processing_stats["processing_time"] = processing_stats["end_time"] - processing_stats["start_time"]
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 主数据表
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 如果需要，添加处理报告
            if create_report:
                _add_processing_report_sheet(writer, processing_stats, df)
        
        return json.dumps({
            "status": "success",
            "message": f"成功处理文件夹中的JSON文件",
            "folder_path": folder_path,
            "output_path": output_path,
            "processing_stats": {
                **processing_stats,
                "companies_processed": len(companies_data),
                "fields_count": len(df.columns),
                "sheet_name": sheet_name
            }
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"处理JSON文件夹时发生错误: {str(e)}",
            "folder_path": folder_path,
            "output_path": output_path
        }, ensure_ascii=False)


@tool
def process_json_folder_with_analysis(folder_path: str, output_path: str,
                                    include_metadata: bool = False,
                                    analysis_level: str = "basic") -> str:
    """
    处理文件夹中的JSON文件并生成详细分析报告
    
    Args:
        folder_path: 包含JSON文件的文件夹路径
        output_path: 输出Excel文件路径
        include_metadata: 是否包含元数据字段，默认为False
        analysis_level: 分析级别，可选值: "basic", "detailed", "comprehensive"
    
    Returns:
        JSON格式的处理和分析结果
    """
    try:
        # 验证文件夹路径
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return json.dumps({
                "status": "error",
                "message": f"文件夹不存在或不是有效目录: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 扫描JSON文件
        json_files = list(folder.glob("*.json"))
        if not json_files:
            return json.dumps({
                "status": "error",
                "message": f"文件夹中没有找到JSON文件: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path
            }, ensure_ascii=False)
        
        # 处理统计信息
        processing_stats = {
            "total_files": len(json_files),
            "successful_files": 0,
            "failed_files": 0,
            "failed_file_details": [],
            "start_time": time.time()
        }
        
        # 读取和处理所有JSON文件
        companies_data = []
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 处理元数据
                if not include_metadata and "_metadata" in data:
                    metadata = data.pop("_metadata")
                    if "company_name" in metadata and "Company-Name-ENG" not in data:
                        data["Company-Name-ENG"] = metadata["company_name"]
                
                # 数据标准化处理
                processed_data = _standardize_company_data(data, json_file.name)
                companies_data.append(processed_data)
                processing_stats["successful_files"] += 1
                
            except Exception as e:
                processing_stats["failed_files"] += 1
                processing_stats["failed_file_details"].append({
                    "file_name": json_file.name,
                    "error": str(e)
                })
        
        if not companies_data:
            return json.dumps({
                "status": "error",
                "message": f"无法处理任何JSON文件: {folder_path}",
                "folder_path": folder_path,
                "output_path": output_path,
                "processing_stats": processing_stats
            }, ensure_ascii=False)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 创建DataFrame
        df = pd.DataFrame(companies_data)
        
        # 生成分析数据
        analysis_data = _generate_analysis_data(df, analysis_level)
        
        # 写入Excel文件
        processing_stats["end_time"] = time.time()
        processing_stats["processing_time"] = processing_stats["end_time"] - processing_stats["start_time"]
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 主数据表
            df.to_excel(writer, sheet_name="公司信息", index=False)
            
            # 处理报告
            _add_processing_report_sheet(writer, processing_stats, df)
            
            # 分析报告
            _add_analysis_sheets(writer, analysis_data, analysis_level)
        
        return json.dumps({
            "status": "success",
            "message": f"成功处理文件夹中的JSON文件并生成分析报告",
            "folder_path": folder_path,
            "output_path": output_path,
            "processing_stats": {
                **processing_stats,
                "companies_processed": len(companies_data),
                "fields_count": len(df.columns),
                "analysis_level": analysis_level
            },
            "analysis_summary": {
                "total_companies": len(companies_data),
                "analysis_sheets_created": len(analysis_data) + 2,  # +2 for main data and processing report
                "analysis_types": list(analysis_data.keys())
            }
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"处理JSON文件夹并生成分析时发生错误: {str(e)}",
            "folder_path": folder_path,
            "output_path": output_path
        }, ensure_ascii=False)


@tool
def validate_json_folder(folder_path: str) -> str:
    """
    验证文件夹中的JSON文件格式和内容
    
    Args:
        folder_path: 包含JSON文件的文件夹路径
    
    Returns:
        JSON格式的验证结果
    """
    try:
        # 验证文件夹路径
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return json.dumps({
                "status": "error",
                "message": f"文件夹不存在或不是有效目录: {folder_path}",
                "folder_path": folder_path
            }, ensure_ascii=False)
        
        # 扫描JSON文件
        json_files = list(folder.glob("*.json"))
        if not json_files:
            return json.dumps({
                "status": "error",
                "message": f"文件夹中没有找到JSON文件: {folder_path}",
                "folder_path": folder_path
            }, ensure_ascii=False)
        
        # 验证统计信息
        validation_stats = {
            "total_files": len(json_files),
            "valid_files": 0,
            "invalid_files": 0,
            "validation_details": []
        }
        
        # 验证每个JSON文件
        for json_file in json_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 基本验证
                validation_result = _validate_company_data(data, json_file.name)
                validation_stats["validation_details"].append(validation_result)
                
                if validation_result["is_valid"]:
                    validation_stats["valid_files"] += 1
                else:
                    validation_stats["invalid_files"] += 1
                    
            except Exception as e:
                validation_stats["invalid_files"] += 1
                validation_stats["validation_details"].append({
                    "file_name": json_file.name,
                    "is_valid": False,
                    "errors": [f"JSON解析错误: {str(e)}"],
                    "warnings": []
                })
        
        return json.dumps({
            "status": "success",
            "message": f"完成JSON文件夹验证",
            "folder_path": folder_path,
            "validation_stats": validation_stats
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"验证JSON文件夹时发生错误: {str(e)}",
            "folder_path": folder_path
        }, ensure_ascii=False)


def _standardize_company_data(data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
    """
    标准化公司数据格式
    
    Args:
        data: 原始公司数据
        file_name: 文件名
    
    Returns:
        标准化后的公司数据
    """
    # 定义标准字段
    standard_fields = [
        "Company-Name-ENG",
        "Company-Name-CHN", 
        "Revenue",
        "Company-Profile",
        "Related-Links",
        "Company-Type",
        "Additional-Info",
        "Info-Sources",
        "Last-Updated"
    ]
    
    # 创建标准化数据
    standardized_data = {}
    
    # 复制现有字段
    for field in standard_fields:
        if field in data:
            standardized_data[field] = data[field]
        else:
            standardized_data[field] = ""
    
    # 添加文件名信息
    standardized_data["Source-File"] = file_name
    
    # 处理嵌套数据
    for key, value in data.items():
        if key not in standard_fields and key != "_metadata":
            if isinstance(value, (dict, list)):
                standardized_data[key] = json.dumps(value, ensure_ascii=False)
            else:
                standardized_data[key] = value
    
    return standardized_data


def _validate_company_data(data: Dict[str, Any], file_name: str) -> Dict[str, Any]:
    """
    验证公司数据的完整性和格式
    
    Args:
        data: 公司数据
        file_name: 文件名
    
    Returns:
        验证结果
    """
    errors = []
    warnings = []
    
    # 检查必要字段
    required_fields = ["Company-Name-ENG"]
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"缺少必要字段: {field}")
    
    # 检查字段完整性
    important_fields = [
        "Company-Name-ENG",
        "Company-Name-CHN",
        "Revenue",
        "Company-Profile"
    ]
    
    for field in important_fields:
        if field not in data or not data[field]:
            warnings.append(f"字段为空: {field}")
    
    # 检查数据格式
    if "Revenue" in data and data["Revenue"]:
        revenue = str(data["Revenue"]).lower()
        if not any(keyword in revenue for keyword in ["万", "亿", "million", "billion", "元", "dollar", "¥", "$"]):
            warnings.append("Revenue字段可能格式不正确")
    
    # 检查链接格式
    if "Related-Links" in data and data["Related-Links"]:
        links = str(data["Related-Links"])
        if not any(link.startswith("http") for link in links.split(",")):
            warnings.append("Related-Links字段可能包含无效链接")
    
    return {
        "file_name": file_name,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "field_count": len(data),
        "has_metadata": "_metadata" in data
    }


def _generate_analysis_data(df: pd.DataFrame, analysis_level: str) -> Dict[str, pd.DataFrame]:
    """
    生成分析数据
    
    Args:
        df: 公司数据DataFrame
        analysis_level: 分析级别
    
    Returns:
        分析数据字典
    """
    analysis_data = {}
    
    # 基本统计
    basic_stats = []
    basic_stats.append({"统计项": "总公司数", "数值": len(df)})
    
    # 字段完整性统计
    for column in df.columns:
        if column not in ["Source-File", "_metadata"]:
            non_empty = df[column].astype(str).str.strip().str.len() > 0
            completion_rate = non_empty.mean() * 100
            basic_stats.append({
                "统计项": f"{column} 完整率",
                "数值": f"{completion_rate:.2f}%"
            })
    
    analysis_data["基本统计"] = pd.DataFrame(basic_stats)
    
    if analysis_level in ["detailed", "comprehensive"]:
        # 公司类型分析
        if "Company-Type" in df.columns:
            # 获取公司名称，优先使用英文名称，如果没有则使用中文名称
            company_names = None
            if "Company-Name-ENG" in df.columns:
                company_names = df["Company-Name-ENG"]
            elif "Company-Name-CHN" in df.columns:
                company_names = df["Company-Name-CHN"]
            
            company_types = _analyze_company_types(df["Company-Type"], company_names)
            if company_types is not None:
                analysis_data["公司类型分布"] = company_types
        
        # 收入分析（如果可能）
        if "Revenue" in df.columns:
            revenue_analysis = _analyze_revenue_data(df["Revenue"], company_names)
            if revenue_analysis is not None:
                analysis_data["收入分析"] = revenue_analysis
    
    if analysis_level == "comprehensive":
        # 更详细的分析
        if "Company-Profile" in df.columns:
            profile_analysis = _analyze_profile_data(df["Company-Profile"])
            if profile_analysis is not None:
                analysis_data["公司简介分析"] = profile_analysis
        
        # 链接分析
        if "Related-Links" in df.columns:
            link_analysis = _analyze_links_data(df["Related-Links"])
            if link_analysis is not None:
                analysis_data["链接分析"] = link_analysis
    
    return analysis_data


def _analyze_company_types(company_type_series: pd.Series, company_names: pd.Series = None) -> Optional[pd.DataFrame]:
    """
    分析公司类型数据，按逗号分割后统计，并包含公司列表
    """
    try:
        # 如果没有提供公司名称，使用索引作为公司标识
        if company_names is None:
            company_names = pd.Series([f"公司_{i}" for i in range(len(company_type_series))])
        
        # 构建类型到公司的映射
        type_to_companies = {}
        
        for idx, company_type in enumerate(company_type_series):
            company_name = company_names.iloc[idx] if idx < len(company_names) else f"公司_{idx}"
            
            if pd.isna(company_type) or not company_type:
                type_key = "未分类"
            else:
                # 按','分割公司类型
                types = [t.strip() for t in str(company_type).split(",") if t.strip()]
                if not types:
                    type_key = "未分类"
                else:
                    # 为每个类型添加公司
                    for type_name in types:
                        if type_name not in type_to_companies:
                            type_to_companies[type_name] = []
                        type_to_companies[type_name].append(company_name)
                    continue
            
            # 处理未分类的情况
            if type_key not in type_to_companies:
                type_to_companies[type_key] = []
            type_to_companies[type_key].append(company_name)
        
        # 构建结果DataFrame
        result_data = []
        for type_name, companies in type_to_companies.items():
            result_data.append({
                "公司类型": type_name,
                "数量": len(companies),
                "公司列表": " | ".join(companies)
            })
        
        # 按数量降序排序
        result_df = pd.DataFrame(result_data)
        result_df = result_df.sort_values("数量", ascending=False).reset_index(drop=True)
        
        return result_df
    except Exception:
        return None


def _analyze_revenue_data(revenue_series: pd.Series, company_names: pd.Series = None) -> Optional[pd.DataFrame]:
    """
    分析收入数据，包含公司列表
    """
    try:
        # 如果没有提供公司名称，使用索引作为公司标识
        if company_names is None:
            company_names = pd.Series([f"公司_{i}" for i in range(len(revenue_series))])
        
        # 构建收入级别到公司的映射
        revenue_to_companies = {}
        
        for idx, revenue in enumerate(revenue_series):
            company_name = company_names.iloc[idx] if idx < len(company_names) else f"公司_{idx}"
            
            if pd.isna(revenue) or not revenue:
                revenue_category = "无数据"
            else:
                revenue_str = str(revenue).lower()
                if "亿" in revenue_str or "billion" in revenue_str:
                    revenue_category = "十亿级"
                elif "万" in revenue_str or "million" in revenue_str:
                    revenue_category = "百万级"
                elif "千" in revenue_str or "thousand" in revenue_str:
                    revenue_category = "千级"
                else:
                    revenue_category = "其他"
            
            # 添加公司到对应收入级别
            if revenue_category not in revenue_to_companies:
                revenue_to_companies[revenue_category] = []
            revenue_to_companies[revenue_category].append(company_name)
        
        # 构建结果DataFrame
        result_data = []
        for revenue_level, companies in revenue_to_companies.items():
            result_data.append({
                "收入级别": revenue_level,
                "公司数量": len(companies),
                "公司列表": " | ".join(companies)
            })
        
        # 按数量降序排序
        result_df = pd.DataFrame(result_data)
        result_df = result_df.sort_values("公司数量", ascending=False).reset_index(drop=True)
        
        return result_df
    except Exception:
        return None


def _analyze_profile_data(profile_series: pd.Series) -> Optional[pd.DataFrame]:
    """
    分析公司简介数据
    """
    try:
        profile_lengths = []
        for profile in profile_series:
            if pd.isna(profile) or not profile:
                profile_lengths.append("无简介")
            else:
                length = len(str(profile))
                if length < 50:
                    profile_lengths.append("简短(<50字)")
                elif length < 200:
                    profile_lengths.append("中等(50-200字)")
                else:
                    profile_lengths.append("详细(>200字)")
        
        profile_df = pd.DataFrame({"简介长度": profile_lengths})
        profile_counts = profile_df["简介长度"].value_counts().reset_index()
        profile_counts.columns = ["简介长度", "公司数量"]
        return profile_counts
    except Exception:
        return None


def _analyze_links_data(links_series: pd.Series) -> Optional[pd.DataFrame]:
    """
    分析链接数据
    """
    try:
        link_counts = []
        for links in links_series:
            if pd.isna(links) or not links:
                link_counts.append("无链接")
            else:
                link_list = str(links).split(",")
                link_count = len([link for link in link_list if link.strip()])
                if link_count == 0:
                    link_counts.append("无链接")
                elif link_count == 1:
                    link_counts.append("1个链接")
                elif link_count <= 3:
                    link_counts.append("2-3个链接")
                else:
                    link_counts.append("3个以上链接")
        
        links_df = pd.DataFrame({"链接数量": link_counts})
        links_counts = links_df["链接数量"].value_counts().reset_index()
        links_counts.columns = ["链接数量", "公司数量"]
        return links_counts
    except Exception:
        return None


def _add_processing_report_sheet(writer: pd.ExcelWriter, stats: Dict[str, Any], df: pd.DataFrame) -> None:
    """添加处理报告工作表"""
    report_data = []
    
    # 处理统计
    report_data.append({"项目": "处理文件总数", "值": stats["total_files"]})
    report_data.append({"项目": "成功处理文件数", "值": stats["successful_files"]})
    report_data.append({"项目": "失败文件数", "值": stats["failed_files"]})
    report_data.append({"项目": "处理公司总数", "值": len(df)})
    report_data.append({"项目": "数据字段数", "值": len(df.columns)})
    report_data.append({"项目": "处理时间(秒)", "值": f"{stats['processing_time']:.2f}"})
    
    # 失败文件详情
    if stats["failed_file_details"]:
        report_data.append({"项目": "失败文件详情", "值": "见下方列表"})
        for failed_file in stats["failed_file_details"]:
            report_data.append({
                "项目": f"失败文件: {failed_file['file_name']}",
                "值": failed_file["error"]
            })
    
    report_df = pd.DataFrame(report_data)
    report_df.to_excel(writer, sheet_name="处理报告", index=False)


def _add_analysis_sheets(writer: pd.ExcelWriter, analysis_data: Dict[str, pd.DataFrame], analysis_level: str) -> None:
    """添加分析工作表"""
    for sheet_name, data in analysis_data.items():
        # Excel工作表名称不能超过31个字符
        safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
        data.to_excel(writer, sheet_name=safe_sheet_name, index=False)
