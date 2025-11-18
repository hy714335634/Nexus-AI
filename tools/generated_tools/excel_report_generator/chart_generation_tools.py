#!/usr/bin/env python3
"""
图表生成工具模块

提供多种类型图表的生成功能，包括饼图、折线图、热图、柱状图和散点图。
所有图表生成工具保证幂等性（使用固定随机种子、确定性算法）。
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

from strands import tool

# 配置中文字体
_CHINESE_FONT = None

def setup_chinese_font():
    """配置matplotlib使用中文字体"""
    global _CHINESE_FONT
    
    # macOS常见中文字体列表（按优先级排序）
    chinese_fonts = [
        'PingFang SC',           # macOS系统字体
        'STHeiti',               # 华文黑体
        'STSong',                # 华文宋体
        'Arial Unicode MS',      # Arial Unicode MS
        'SimHei',                # 黑体（Windows）
        'Microsoft YaHei',       # 微软雅黑（Windows）
        'WenQuanYi Micro Hei',   # 文泉驿微米黑（Linux）
    ]
    
    # 查找可用的中文字体
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    chinese_font = None
    
    for font_name in chinese_fonts:
        if font_name in available_fonts:
            chinese_font = font_name
            break
    
    # 如果找到中文字体，则配置使用
    if chinese_font:
        _CHINESE_FONT = chinese_font
        # 强制设置字体，移除Arial等不支持中文的字体
        plt.rcParams['font.sans-serif'] = [chinese_font, 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        # 同时配置seaborn的字体
        sns.set(font=chinese_font)
    else:
        # 如果没有找到，尝试使用系统默认字体
        _CHINESE_FONT = 'Arial Unicode MS'
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    return _CHINESE_FONT

def ensure_chinese_font():
    """确保使用中文字体（在每个绘图函数中调用）"""
    if _CHINESE_FONT:
        plt.rcParams['font.sans-serif'] = [_CHINESE_FONT, 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        # 同时更新seaborn的字体设置
        sns.set(font=_CHINESE_FONT)
    else:
        setup_chinese_font()

# 初始化中文字体配置
setup_chinese_font()

# 设置确定性配置
np.random.seed(42)  # 固定随机种子
plt.rcParams['figure.dpi'] = 100  # 固定DPI
plt.rcParams['savefig.dpi'] = 100  # 固定保存DPI
sns.set_theme(style="whitegrid")  # 固定样式

# 在seaborn主题设置后重新确认字体（防止被覆盖）
if _CHINESE_FONT:
    sns.set(font=_CHINESE_FONT)


@tool
def generate_pie_chart(
    data_json: str,
    category_column: str,
    value_column: str,
    title: str,
    save_path: str,
    colors: Optional[List[str]] = None,
    explode_max: bool = False
) -> str:
    """
    饼图生成工具
    
    功能：基于数据生成饼图，确定性输出，幂等性保证
    
    Args:
        data_json (str): JSON格式的DataFrame数据
        category_column (str): 分类列名
        value_column (str): 数值列名
        title (str): 图表标题
        save_path (str): 保存路径（PNG格式）
        colors (Optional[List[str]]): 自定义颜色列表，如果不提供则使用默认配色
        explode_max (bool): 是否突出显示最大值，默认False
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 确保使用中文字体
        ensure_chinese_font()
        
        # 解析数据
        input_data = json.loads(data_json)
        if "data" in input_data:
            df = pd.DataFrame(input_data["data"])
        else:
            df = pd.DataFrame(input_data)
        
        # 验证列是否存在
        if category_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"分类列'{category_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if value_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"数值列'{value_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 准备数据
        pie_data = df.groupby(category_column)[value_column].sum().sort_values(ascending=False)
        
        if len(pie_data) == 0:
            return json.dumps({
                "status": "error",
                "message": "没有可用数据生成饼图",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建图表（确定性配置）
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 设置确定性颜色
        if colors is None:
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                     '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#AAB7B8']
        
        # 设置explode
        explode = None
        if explode_max:
            explode = [0.1 if i == 0 else 0 for i in range(len(pie_data))]
        
        # 绘制饼图
        wedges, texts, autotexts = ax.pie(
            pie_data.values,
            labels=pie_data.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(pie_data)],
            explode=explode,
            shadow=False,  # 确定性输出
            textprops={'fontsize': 10}
        )
        
        # 设置标题
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 确保圆形
        ax.axis('equal')
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        
        # 计算文件哈希
        with open(save_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return json.dumps({
            "status": "success",
            "chart_type": "pie_chart",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "file_hash": file_hash,
            "chart_info": {
                "title": title,
                "category_column": category_column,
                "value_column": value_column,
                "categories_count": len(pie_data),
                "total_value": float(pie_data.sum())
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"饼图生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_line_chart(
    data_json: str,
    x_column: str,
    y_columns: Union[str, List[str]],
    title: str,
    save_path: str,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    show_markers: bool = True,
    show_grid: bool = True
) -> str:
    """
    折线图生成工具
    
    功能：基于数据生成折线图，支持多条线，确定性输出，幂等性保证
    
    Args:
        data_json (str): JSON格式的DataFrame数据
        x_column (str): X轴列名
        y_columns (Union[str, List[str]]): Y轴列名或列名列表（支持多条线）
        title (str): 图表标题
        save_path (str): 保存路径（PNG格式）
        x_label (Optional[str]): X轴标签，如果不提供则使用列名
        y_label (Optional[str]): Y轴标签，如果不提供则使用列名
        show_markers (bool): 是否显示数据点标记，默认True
        show_grid (bool): 是否显示网格，默认True
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 确保使用中文字体
        ensure_chinese_font()
        
        # 解析数据
        input_data = json.loads(data_json)
        if "data" in input_data:
            df = pd.DataFrame(input_data["data"])
        else:
            df = pd.DataFrame(input_data)
        
        # 标准化y_columns为列表
        if isinstance(y_columns, str):
            y_columns = [y_columns]
        
        # 验证列是否存在
        if x_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"X轴列'{x_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        for y_col in y_columns:
            if y_col not in df.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"Y轴列'{y_col}'不存在",
                    "available_columns": df.columns.tolist(),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建图表（确定性配置）
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 确定性颜色
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 确定性线型
        linestyles = ['-', '--', '-.', ':']
        markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
        
        # 绘制多条线
        for idx, y_col in enumerate(y_columns):
            ax.plot(
                df[x_column],
                df[y_col],
                label=y_col,
                color=colors[idx % len(colors)],
                linestyle=linestyles[idx % len(linestyles)],
                marker=markers[idx % len(markers)] if show_markers else None,
                markersize=6 if show_markers else 0,
                linewidth=2
            )
        
        # 设置标签
        ax.set_xlabel(x_label if x_label else x_column, fontsize=12)
        ax.set_ylabel(y_label if y_label else ', '.join(y_columns), fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 设置网格
        if show_grid:
            ax.grid(True, alpha=0.3)
        
        # 设置图例
        if len(y_columns) > 1:
            ax.legend(loc='best', fontsize=10)
        
        # 旋转X轴标签（如果是日期或长文本）
        plt.xticks(rotation=45, ha='right')
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        
        # 计算文件哈希
        with open(save_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return json.dumps({
            "status": "success",
            "chart_type": "line_chart",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "file_hash": file_hash,
            "chart_info": {
                "title": title,
                "x_column": x_column,
                "y_columns": y_columns,
                "data_points": len(df),
                "lines_count": len(y_columns)
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"折线图生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_heatmap(
    data_json: str,
    title: str,
    save_path: str,
    columns: Optional[List[str]] = None,
    colormap: str = "coolwarm",
    show_values: bool = True
) -> str:
    """
    热图生成工具
    
    功能：基于数据生成热图，支持相关系数矩阵可视化，确定性配色，幂等性保证
    
    Args:
        data_json (str): JSON格式的DataFrame数据或相关系数矩阵
        title (str): 图表标题
        save_path (str): 保存路径（PNG格式）
        columns (Optional[List[str]]): 要包含的列名列表，如果不提供则使用所有数值列
        colormap (str): 颜色映射，默认'coolwarm'，可选'viridis', 'plasma', 'RdYlGn'等
        show_values (bool): 是否在热图上显示数值，默认True
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 确保使用中文字体
        ensure_chinese_font()
        
        # 解析数据
        input_data = json.loads(data_json)
        
        # 判断是否为相关性矩阵
        if "correlation_analysis" in input_data and "matrix" in input_data["correlation_analysis"]:
            # 使用相关性矩阵
            corr_matrix = pd.DataFrame(input_data["correlation_analysis"]["matrix"])
        else:
            # 从原始数据计算相关性矩阵
            if "data" in input_data:
                df = pd.DataFrame(input_data["data"])
            else:
                df = pd.DataFrame(input_data)
            
            # 选择数值列
            numeric_df = df.select_dtypes(include=[np.number])
            
            if columns:
                numeric_df = numeric_df[[col for col in columns if col in numeric_df.columns]]
            
            if numeric_df.empty:
                return json.dumps({
                    "status": "error",
                    "message": "没有可用的数值列生成热图",
                    "available_columns": df.columns.tolist(),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            
            # 计算相关性矩阵
            corr_matrix = numeric_df.corr()
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建图表（确定性配置）
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 绘制热图
        sns.heatmap(
            corr_matrix,
            annot=show_values,
            fmt='.2f',
            cmap=colormap,
            center=0,
            square=True,
            linewidths=0.5,
            cbar_kws={"shrink": 0.8},
            ax=ax,
            vmin=-1,
            vmax=1
        )
        
        # 设置标题
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 旋转标签
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        
        # 计算文件哈希
        with open(save_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return json.dumps({
            "status": "success",
            "chart_type": "heatmap",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "file_hash": file_hash,
            "chart_info": {
                "title": title,
                "matrix_size": f"{len(corr_matrix)}x{len(corr_matrix.columns)}",
                "columns": corr_matrix.columns.tolist(),
                "colormap": colormap
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"热图生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_bar_chart(
    data_json: str,
    category_column: str,
    value_column: str,
    title: str,
    save_path: str,
    orientation: str = "vertical",
    sort_values: bool = True,
    show_values: bool = True
) -> str:
    """
    柱状图生成工具
    
    功能：基于数据生成柱状图，确定性输出，幂等性保证
    
    Args:
        data_json (str): JSON格式的DataFrame数据
        category_column (str): 分类列名
        value_column (str): 数值列名
        title (str): 图表标题
        save_path (str): 保存路径（PNG格式）
        orientation (str): 方向，'vertical'或'horizontal'，默认'vertical'
        sort_values (bool): 是否按值排序，默认True
        show_values (bool): 是否在柱子上显示数值，默认True
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 确保使用中文字体
        ensure_chinese_font()
        
        # 解析数据
        input_data = json.loads(data_json)
        if "data" in input_data:
            df = pd.DataFrame(input_data["data"])
        else:
            df = pd.DataFrame(input_data)
        
        # 验证列是否存在
        if category_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"分类列'{category_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if value_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"数值列'{value_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 准备数据
        bar_data = df.groupby(category_column)[value_column].sum()
        
        if sort_values:
            bar_data = bar_data.sort_values(ascending=False)
        
        if len(bar_data) == 0:
            return json.dumps({
                "status": "error",
                "message": "没有可用数据生成柱状图",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建图表（确定性配置）
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 确定性颜色
        color = '#4ECDC4'
        
        # 绘制柱状图
        if orientation == "vertical":
            bars = ax.bar(
                range(len(bar_data)),
                bar_data.values,
                color=color,
                alpha=0.8,
                edgecolor='black',
                linewidth=0.5
            )
            ax.set_xticks(range(len(bar_data)))
            ax.set_xticklabels(bar_data.index, rotation=45, ha='right')
            ax.set_ylabel(value_column, fontsize=12)
            
            # 在柱子上显示数值
            if show_values:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width()/2.,
                        height,
                        f'{height:.1f}',
                        ha='center',
                        va='bottom',
                        fontsize=9
                    )
        else:  # horizontal
            bars = ax.barh(
                range(len(bar_data)),
                bar_data.values,
                color=color,
                alpha=0.8,
                edgecolor='black',
                linewidth=0.5
            )
            ax.set_yticks(range(len(bar_data)))
            ax.set_yticklabels(bar_data.index)
            ax.set_xlabel(value_column, fontsize=12)
            
            # 在柱子上显示数值
            if show_values:
                for bar in bars:
                    width = bar.get_width()
                    ax.text(
                        width,
                        bar.get_y() + bar.get_height()/2.,
                        f'{width:.1f}',
                        ha='left',
                        va='center',
                        fontsize=9
                    )
        
        # 设置标题
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 设置网格
        ax.grid(True, alpha=0.3, axis='y' if orientation == "vertical" else 'x')
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        
        # 计算文件哈希
        with open(save_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return json.dumps({
            "status": "success",
            "chart_type": "bar_chart",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "file_hash": file_hash,
            "chart_info": {
                "title": title,
                "category_column": category_column,
                "value_column": value_column,
                "categories_count": len(bar_data),
                "orientation": orientation,
                "total_value": float(bar_data.sum())
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"柱状图生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_scatter_plot(
    data_json: str,
    x_column: str,
    y_column: str,
    title: str,
    save_path: str,
    color_column: Optional[str] = None,
    size_column: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    show_regression: bool = False
) -> str:
    """
    散点图生成工具
    
    功能：基于数据生成散点图，支持颜色和大小映射，确定性输出，幂等性保证
    
    Args:
        data_json (str): JSON格式的DataFrame数据
        x_column (str): X轴列名
        y_column (str): Y轴列名
        title (str): 图表标题
        save_path (str): 保存路径（PNG格式）
        color_column (Optional[str]): 用于颜色映射的列名
        size_column (Optional[str]): 用于大小映射的列名
        x_label (Optional[str]): X轴标签
        y_label (Optional[str]): Y轴标签
        show_regression (bool): 是否显示回归线，默认False
        
    Returns:
        str: JSON格式的生成结果
    """
    try:
        # 确保使用中文字体
        ensure_chinese_font()
        
        # 解析数据
        input_data = json.loads(data_json)
        if "data" in input_data:
            df = pd.DataFrame(input_data["data"])
        else:
            df = pd.DataFrame(input_data)
        
        # 验证列是否存在
        required_columns = [x_column, y_column]
        for col in required_columns:
            if col not in df.columns:
                return json.dumps({
                    "status": "error",
                    "message": f"列'{col}'不存在",
                    "available_columns": df.columns.tolist(),
                    "timestamp": datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
        
        if color_column and color_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"颜色列'{color_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if size_column and size_column not in df.columns:
            return json.dumps({
                "status": "error",
                "message": f"大小列'{size_column}'不存在",
                "available_columns": df.columns.tolist(),
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 确保保存目录存在
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 创建图表（确定性配置）
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 准备颜色和大小
        colors = None
        sizes = None
        
        if color_column:
            if df[color_column].dtype in [np.number]:
                colors = df[color_column]
            else:
                # 分类变量转换为数值
                unique_categories = df[color_column].unique()
                color_map = {cat: idx for idx, cat in enumerate(unique_categories)}
                colors = df[color_column].map(color_map)
        
        if size_column:
            sizes = df[size_column]
            # 标准化大小到合理范围
            sizes = (sizes - sizes.min()) / (sizes.max() - sizes.min()) * 200 + 50
        else:
            sizes = 50  # 默认大小
        
        # 绘制散点图
        scatter = ax.scatter(
            df[x_column],
            df[y_column],
            c=colors if colors is not None else '#4ECDC4',
            s=sizes,
            alpha=0.6,
            edgecolors='black',
            linewidth=0.5,
            cmap='viridis' if color_column else None
        )
        
        # 添加颜色条
        if color_column and colors is not None:
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label(color_column, fontsize=10)
        
        # 添加回归线
        if show_regression:
            # 计算线性回归
            x_vals = df[x_column].dropna()
            y_vals = df[y_column].dropna()
            
            if len(x_vals) > 1 and len(y_vals) > 1:
                z = np.polyfit(x_vals, y_vals, 1)
                p = np.poly1d(z)
                ax.plot(x_vals, p(x_vals), "r--", alpha=0.8, linewidth=2, label=f'y={z[0]:.2f}x+{z[1]:.2f}')
                ax.legend(loc='best')
        
        # 设置标签
        ax.set_xlabel(x_label if x_label else x_column, fontsize=12)
        ax.set_ylabel(y_label if y_label else y_column, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        # 设置网格
        ax.grid(True, alpha=0.3)
        
        # 保存图表
        plt.tight_layout()
        plt.savefig(save_path, format='png', bbox_inches='tight')
        plt.close()
        
        # 计算文件哈希
        with open(save_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        
        return json.dumps({
            "status": "success",
            "chart_type": "scatter_plot",
            "file_path": save_path,
            "file_name": os.path.basename(save_path),
            "file_size_bytes": os.path.getsize(save_path),
            "file_hash": file_hash,
            "chart_info": {
                "title": title,
                "x_column": x_column,
                "y_column": y_column,
                "color_column": color_column,
                "size_column": size_column,
                "data_points": len(df)
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"散点图生成失败: {str(e)}",
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("🧪 测试图表生成工具...")
    print("✅ 图表生成工具模块加载成功！")
