"""
布局优化工具，用于优化PPT页面布局。

此模块提供了一组工具函数，用于分析内容、计算最佳布局、
自动排列元素并优化幻灯片的整体视觉效果。
"""

import json
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from strands import tool


@tool
def optimize_slide_layout(
    content_elements: List[Dict[str, Any]],
    slide_size: Dict[str, float],
    layout_type: str = "auto",
    title_height: float = 1.0
) -> str:
    """
    优化幻灯片布局，计算内容元素的最佳位置和大小。

    Args:
        content_elements (List[Dict[str, Any]]): 内容元素列表，每个元素包含类型、内容和可选的原始大小
        slide_size (Dict[str, float]): 幻灯片大小，包含宽度和高度（英寸）
        layout_type (str): 布局类型，可选值: "auto", "balanced", "grid", "column", "row"
        title_height (float): 标题区域高度（英寸）
        
    Returns:
        str: JSON格式的优化布局，包含每个元素的位置和大小
    """
    try:
        # 验证输入
        if not content_elements:
            raise ValueError("内容元素列表不能为空")
        
        if "width" not in slide_size or "height" not in slide_size:
            raise ValueError("幻灯片大小必须包含宽度和高度")
        
        # 提取幻灯片尺寸
        slide_width = slide_size["width"]
        slide_height = slide_size["height"]
        
        # 计算内容区域（排除标题区域）
        content_area = {
            "left": 0.5,  # 左边距0.5英寸
            "top": title_height + 0.5,  # 标题下方0.5英寸
            "width": slide_width - 1.0,  # 左右各减去0.5英寸边距
            "height": slide_height - title_height - 1.0  # 上下各减去0.5英寸边距
        }
        
        # 根据布局类型选择布局策略
        if layout_type == "grid":
            layout = _create_grid_layout(content_elements, content_area)
        elif layout_type == "column":
            layout = _create_column_layout(content_elements, content_area)
        elif layout_type == "row":
            layout = _create_row_layout(content_elements, content_area)
        elif layout_type == "balanced":
            layout = _create_balanced_layout(content_elements, content_area)
        else:  # auto
            # 根据内容元素类型和数量自动选择最佳布局
            layout = _create_auto_layout(content_elements, content_area)
        
        # 构建响应
        response = {
            "status": "success",
            "layout_type": layout_type,
            "slide_size": slide_size,
            "content_area": content_area,
            "optimized_layout": layout
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "布局优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def calculate_text_box_size(
    text: str,
    font_size: float = 14.0,
    font_name: str = "Arial",
    width_constraint: float = None,
    include_margins: bool = True
) -> str:
    """
    计算文本框所需的大小。

    Args:
        text (str): 要显示的文本
        font_size (float): 字体大小（磅）
        font_name (str): 字体名称
        width_constraint (float, optional): 宽度约束（英寸），如果提供则计算所需高度
        include_margins (bool): 是否包含内边距
        
    Returns:
        str: JSON格式的文本框大小（英寸）
    """
    try:
        # 验证输入
        if not text:
            raise ValueError("文本不能为空")
        
        # 估算每个字符的平均宽度（英寸）
        # 这是一个近似值，不同字体和字符会有差异
        char_width_inches = font_size * 0.01  # 1磅约等于0.01英寸宽度
        
        # 估算行高（英寸）
        line_height_inches = font_size * 1.2 / 72  # 1磅 = 1/72英寸，行高为字体大小的1.2倍
        
        # 计算边距（如果需要）
        margin_inches = 0.1 if include_margins else 0.0
        
        # 如果提供了宽度约束，计算所需的高度
        if width_constraint:
            # 可用宽度（减去边距）
            available_width = width_constraint - (2 * margin_inches)
            
            # 估算每行可容纳的字符数
            chars_per_line = int(available_width / char_width_inches)
            
            if chars_per_line <= 0:
                raise ValueError("宽度约束太小，无法容纳文本")
            
            # 分割文本为行
            lines = []
            words = text.split()
            current_line = []
            current_length = 0
            
            for word in words:
                word_length = len(word)
                
                # 检查是否需要换行
                if current_length + word_length + len(current_line) <= chars_per_line:
                    current_line.append(word)
                    current_length += word_length
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = word_length
            
            # 添加最后一行
            if current_line:
                lines.append(" ".join(current_line))
            
            # 计算高度
            height = (len(lines) * line_height_inches) + (2 * margin_inches)
            width = width_constraint
        
        else:
            # 如果没有宽度约束，估算所需的宽度和高度
            # 找出最长的行
            lines = text.split('\n')
            max_line_length = max(len(line) for line in lines)
            
            # 计算宽度和高度
            width = (max_line_length * char_width_inches) + (2 * margin_inches)
            height = (len(lines) * line_height_inches) + (2 * margin_inches)
        
        # 构建响应
        response = {
            "status": "success",
            "text_box_size": {
                "width": round(width, 2),
                "height": round(height, 2)
            },
            "text_metrics": {
                "character_count": len(text),
                "line_count": len(lines) if 'lines' in locals() else text.count('\n') + 1,
                "font_size": font_size,
                "font_name": font_name
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "文本框大小计算失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def optimize_image_placement(
    images: List[Dict[str, Any]],
    content_area: Dict[str, float],
    layout_style: str = "grid"
) -> str:
    """
    优化图片放置位置。

    Args:
        images (List[Dict[str, Any]]): 图片列表，每个图片包含宽度、高度和可选的重要性
        content_area (Dict[str, float]): 可用内容区域，包含left、top、width和height（英寸）
        layout_style (str): 布局样式，可选值: "grid", "cascade", "focal", "gallery"
        
    Returns:
        str: JSON格式的图片布局，包含每个图片的位置和大小
    """
    try:
        # 验证输入
        if not images:
            raise ValueError("图片列表不能为空")
        
        required_keys = ["left", "top", "width", "height"]
        if not all(key in content_area for key in required_keys):
            raise ValueError("内容区域必须包含left、top、width和height")
        
        # 根据布局样式选择布局策略
        if layout_style == "cascade":
            layout = _create_cascade_image_layout(images, content_area)
        elif layout_style == "focal":
            layout = _create_focal_image_layout(images, content_area)
        elif layout_style == "gallery":
            layout = _create_gallery_image_layout(images, content_area)
        else:  # grid
            layout = _create_grid_image_layout(images, content_area)
        
        # 构建响应
        response = {
            "status": "success",
            "layout_style": layout_style,
            "content_area": content_area,
            "image_count": len(images),
            "optimized_layout": layout
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片布局优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def create_balanced_composition(
    elements: List[Dict[str, Any]],
    slide_size: Dict[str, float],
    composition_type: str = "balanced",
    title_height: float = 1.0
) -> str:
    """
    创建平衡的幻灯片构图。

    Args:
        elements (List[Dict[str, Any]]): 元素列表，每个元素包含类型、内容和重要性
        slide_size (Dict[str, float]): 幻灯片大小，包含宽度和高度（英寸）
        composition_type (str): 构图类型，可选值: "balanced", "focal", "rule_of_thirds", "golden_ratio", "symmetrical"
        title_height (float): 标题区域高度（英寸）
        
    Returns:
        str: JSON格式的构图布局，包含每个元素的位置和大小
    """
    try:
        # 验证输入
        if not elements:
            raise ValueError("元素列表不能为空")
        
        if "width" not in slide_size or "height" not in slide_size:
            raise ValueError("幻灯片大小必须包含宽度和高度")
        
        # 提取幻灯片尺寸
        slide_width = slide_size["width"]
        slide_height = slide_size["height"]
        
        # 计算内容区域（排除标题区域）
        content_area = {
            "left": 0.5,  # 左边距0.5英寸
            "top": title_height + 0.5,  # 标题下方0.5英寸
            "width": slide_width - 1.0,  # 左右各减去0.5英寸边距
            "height": slide_height - title_height - 1.0  # 上下各减去0.5英寸边距
        }
        
        # 根据构图类型选择布局策略
        if composition_type == "focal":
            layout = _create_focal_composition(elements, content_area)
        elif composition_type == "rule_of_thirds":
            layout = _create_rule_of_thirds_composition(elements, content_area)
        elif composition_type == "golden_ratio":
            layout = _create_golden_ratio_composition(elements, content_area)
        elif composition_type == "symmetrical":
            layout = _create_symmetrical_composition(elements, content_area)
        else:  # balanced
            layout = _create_balanced_composition_layout(elements, content_area)
        
        # 构建响应
        response = {
            "status": "success",
            "composition_type": composition_type,
            "slide_size": slide_size,
            "content_area": content_area,
            "optimized_layout": layout
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "构图优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def optimize_table_layout(
    table_data: Dict[str, Any],
    content_area: Dict[str, float],
    auto_size: bool = True
) -> str:
    """
    优化表格布局。

    Args:
        table_data (Dict[str, Any]): 表格数据，包含标题、列数、行数和单元格内容
        content_area (Dict[str, float]): 可用内容区域，包含left、top、width和height（英寸）
        auto_size (bool): 是否自动调整列宽和行高
        
    Returns:
        str: JSON格式的表格布局，包含表格位置、大小和单元格布局
    """
    try:
        # 验证输入
        required_keys = ["left", "top", "width", "height"]
        if not all(key in content_area for key in required_keys):
            raise ValueError("内容区域必须包含left、top、width和height")
        
        if "headers" not in table_data and "data" not in table_data:
            raise ValueError("表格数据必须包含headers或data")
        
        # 提取表格数据
        headers = table_data.get("headers", [])
        data = table_data.get("data", [])
        
        # 确定行数和列数
        row_count = len(data)
        col_count = len(headers) if headers else (len(data[0]) if data else 0)
        
        if row_count == 0 or col_count == 0:
            raise ValueError("表格必须至少包含一行一列")
        
        # 计算表格位置和大小
        table_left = content_area["left"]
        table_top = content_area["top"]
        table_width = min(content_area["width"], 10.0)  # 限制最大宽度为10英寸
        table_height = min(content_area["height"], row_count * 0.5 + 0.5)  # 每行约0.5英寸，标题行稍高
        
        # 如果自动调整大小，计算最佳列宽
        column_widths = []
        if auto_size:
            # 计算每列的最大内容长度
            max_lengths = [0] * col_count
            
            # 检查标题
            if headers:
                for i, header in enumerate(headers):
                    if i < col_count:
                        max_lengths[i] = max(max_lengths[i], len(str(header)))
            
            # 检查数据
            for row in data:
                for i, cell in enumerate(row):
                    if i < col_count:
                        max_lengths[i] = max(max_lengths[i], len(str(cell)))
            
            # 计算列宽（英寸）
            total_chars = sum(max_lengths)
            for length in max_lengths:
                if total_chars > 0:
                    # 按比例分配宽度，最小宽度为0.5英寸
                    width = max(0.5, (length / total_chars) * table_width)
                else:
                    width = table_width / col_count
                column_widths.append(round(width, 2))
            
            # 确保列宽总和等于表格宽度
            total_width = sum(column_widths)
            if total_width != table_width:
                # 调整最后一列
                column_widths[-1] += (table_width - total_width)
        else:
            # 均匀分配列宽
            column_width = table_width / col_count
            column_widths = [round(column_width, 2)] * col_count
        
        # 计算行高
        header_height = 0.4 if headers else 0.0  # 标题行高度
        if row_count > 0:
            row_height = (table_height - header_height) / row_count
        else:
            row_height = 0.3  # 默认行高
        
        # 构建单元格布局
        cells = []
        
        # 添加标题行
        if headers:
            y = table_top
            x = table_left
            for i, header in enumerate(headers):
                if i < col_count:
                    width = column_widths[i]
                    cells.append({
                        "row": 0,
                        "column": i,
                        "left": round(x, 2),
                        "top": round(y, 2),
                        "width": width,
                        "height": round(header_height, 2),
                        "is_header": True,
                        "content": str(header)
                    })
                    x += width
        
        # 添加数据行
        for row_idx, row in enumerate(data):
            y = table_top + header_height + (row_idx * row_height)
            x = table_left
            for col_idx, cell in enumerate(row):
                if col_idx < col_count:
                    width = column_widths[col_idx]
                    cells.append({
                        "row": row_idx + 1,
                        "column": col_idx,
                        "left": round(x, 2),
                        "top": round(y, 2),
                        "width": width,
                        "height": round(row_height, 2),
                        "is_header": False,
                        "content": str(cell)
                    })
                    x += width
        
        # 构建响应
        response = {
            "status": "success",
            "table_layout": {
                "left": table_left,
                "top": table_top,
                "width": table_width,
                "height": table_height,
                "row_count": row_count + (1 if headers else 0),
                "column_count": col_count,
                "column_widths": column_widths,
                "cells": cells
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "表格布局优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def suggest_content_distribution(
    content_elements: List[Dict[str, Any]],
    max_slides: int = 10,
    content_density: str = "medium"
) -> str:
    """
    建议内容分布到多个幻灯片。

    Args:
        content_elements (List[Dict[str, Any]]): 内容元素列表
        max_slides (int): 最大幻灯片数量
        content_density (str): 内容密度，可选值: "low", "medium", "high"
        
    Returns:
        str: JSON格式的内容分布建议，包含每个幻灯片的内容元素
    """
    try:
        # 验证输入
        if not content_elements:
            raise ValueError("内容元素列表不能为空")
        
        # 根据内容密度确定每张幻灯片的最大元素数量
        if content_density == "low":
            max_elements_per_slide = 3
        elif content_density == "high":
            max_elements_per_slide = 8
        else:  # medium
            max_elements_per_slide = 5
        
        # 初始化幻灯片列表
        slides = []
        current_slide = []
        current_element_count = 0
        
        # 特殊处理：标题幻灯片
        title_element = None
        for element in content_elements:
            if element.get("type") == "title":
                title_element = element
                break
        
        if title_element:
            slides.append([title_element])
            content_elements = [e for e in content_elements if e != title_element]
        
        # 分配内容元素到幻灯片
        for element in content_elements:
            # 检查元素类型和复杂度
            element_type = element.get("type", "")
            element_complexity = _get_element_complexity(element)
            
            # 复杂元素（如表格、图表）可能需要单独一张幻灯片
            if element_complexity == "high":
                # 如果当前幻灯片已有内容，完成当前幻灯片
                if current_slide:
                    slides.append(current_slide)
                    current_slide = []
                    current_element_count = 0
                
                # 将复杂元素放在新幻灯片上
                slides.append([element])
            else:
                # 检查当前幻灯片是否已满
                if current_element_count >= max_elements_per_slide:
                    slides.append(current_slide)
                    current_slide = []
                    current_element_count = 0
                
                # 添加元素到当前幻灯片
                current_slide.append(element)
                current_element_count += 1
        
        # 添加最后一张幻灯片（如果有内容）
        if current_slide:
            slides.append(current_slide)
        
        # 限制幻灯片数量
        if len(slides) > max_slides:
            # 尝试合并一些幻灯片
            slides = _merge_slides(slides, max_slides)
        
        # 构建响应
        response = {
            "status": "success",
            "content_distribution": {
                "slide_count": len(slides),
                "content_density": content_density,
                "max_elements_per_slide": max_elements_per_slide,
                "slides": []
            }
        }
        
        # 添加每张幻灯片的信息
        for i, slide_elements in enumerate(slides):
            slide_info = {
                "slide_number": i + 1,
                "element_count": len(slide_elements),
                "elements": slide_elements
            }
            response["content_distribution"]["slides"].append(slide_info)
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "内容分布建议失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def optimize_visual_hierarchy(
    slide_elements: List[Dict[str, Any]],
    slide_size: Dict[str, float]
) -> str:
    """
    优化幻灯片的视觉层次结构。

    Args:
        slide_elements (List[Dict[str, Any]]): 幻灯片元素列表，包含类型、内容和重要性
        slide_size (Dict[str, float]): 幻灯片大小，包含宽度和高度（英寸）
        
    Returns:
        str: JSON格式的视觉层次优化结果，包含元素大小、位置和样式建议
    """
    try:
        # 验证输入
        if not slide_elements:
            raise ValueError("幻灯片元素列表不能为空")
        
        if "width" not in slide_size or "height" not in slide_size:
            raise ValueError("幻灯片大小必须包含宽度和高度")
        
        # 提取幻灯片尺寸
        slide_width = slide_size["width"]
        slide_height = slide_size["height"]
        
        # 分析元素重要性
        elements_with_importance = []
        for element in slide_elements:
            # 如果没有指定重要性，根据元素类型和位置估算
            importance = element.get("importance", 0)
            if importance == 0:
                importance = _estimate_element_importance(element)
            
            elements_with_importance.append({
                **element,
                "calculated_importance": importance
            })
        
        # 按重要性排序
        elements_with_importance.sort(key=lambda x: x["calculated_importance"], reverse=True)
        
        # 优化视觉层次
        optimized_elements = []
        for i, element in enumerate(elements_with_importance):
            element_type = element.get("type", "")
            importance = element["calculated_importance"]
            
            # 基于重要性计算元素大小和样式
            size_factor = min(1.0, 0.5 + (importance / 10))  # 0.5 到 1.0 之间
            
            # 计算元素样式
            style = _calculate_element_style(element_type, importance)
            
            # 计算元素位置（基于重要性和元素类型）
            position = _calculate_element_position(element_type, importance, i, len(elements_with_importance), slide_width, slide_height)
            
            optimized_elements.append({
                **element,
                "optimized_position": position,
                "optimized_size_factor": size_factor,
                "optimized_style": style
            })
        
        # 构建响应
        response = {
            "status": "success",
            "slide_size": slide_size,
            "optimized_elements": optimized_elements
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "视觉层次优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _create_grid_layout(elements, content_area):
    """创建网格布局"""
    layout = []
    
    # 计算网格尺寸
    element_count = len(elements)
    if element_count <= 1:
        cols = 1
    elif element_count <= 4:
        cols = 2
    else:
        cols = 3
    
    rows = math.ceil(element_count / cols)
    
    # 计算单元格大小
    cell_width = content_area["width"] / cols
    cell_height = content_area["height"] / rows
    
    # 放置元素
    for i, element in enumerate(elements):
        row = i // cols
        col = i % cols
        
        # 计算位置
        left = content_area["left"] + (col * cell_width)
        top = content_area["top"] + (row * cell_height)
        
        # 添加元素布局
        layout.append({
            "element_index": i,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(cell_width * 0.9, 2),  # 留出一些间距
                "height": round(cell_height * 0.9, 2)  # 留出一些间距
            }
        })
    
    return layout


def _create_column_layout(elements, content_area):
    """创建列布局"""
    layout = []
    
    # 计算列数
    element_count = len(elements)
    cols = min(element_count, 3)  # 最多3列
    
    # 计算列宽
    col_width = content_area["width"] / cols
    
    # 为每列分配元素
    elements_per_col = math.ceil(element_count / cols)
    
    for i, element in enumerate(elements):
        col = i // elements_per_col
        pos_in_col = i % elements_per_col
        
        # 计算位置
        left = content_area["left"] + (col * col_width)
        top = content_area["top"] + (pos_in_col * (content_area["height"] / elements_per_col))
        height = content_area["height"] / elements_per_col
        
        # 添加元素布局
        layout.append({
            "element_index": i,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(col_width * 0.9, 2),  # 留出一些间距
                "height": round(height * 0.9, 2)  # 留出一些间距
            }
        })
    
    return layout


def _create_row_layout(elements, content_area):
    """创建行布局"""
    layout = []
    
    # 计算行数
    element_count = len(elements)
    rows = min(element_count, 5)  # 最多5行
    
    # 计算行高
    row_height = content_area["height"] / rows
    
    # 为每行分配元素
    elements_per_row = math.ceil(element_count / rows)
    
    for i, element in enumerate(elements):
        row = i // elements_per_row
        pos_in_row = i % elements_per_row
        
        # 计算位置
        left = content_area["left"] + (pos_in_row * (content_area["width"] / elements_per_row))
        top = content_area["top"] + (row * row_height)
        width = content_area["width"] / elements_per_row
        
        # 添加元素布局
        layout.append({
            "element_index": i,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(width * 0.9, 2),  # 留出一些间距
                "height": round(row_height * 0.9, 2)  # 留出一些间距
            }
        })
    
    return layout


def _create_balanced_layout(elements, content_area):
    """创建平衡布局"""
    layout = []
    
    # 分析元素类型
    text_elements = []
    image_elements = []
    table_elements = []
    other_elements = []
    
    for i, element in enumerate(elements):
        element_type = element.get("type", "").lower()
        if element_type in ["text", "paragraph", "bullet"]:
            text_elements.append((i, element))
        elif element_type in ["image", "picture", "photo"]:
            image_elements.append((i, element))
        elif element_type in ["table", "grid"]:
            table_elements.append((i, element))
        else:
            other_elements.append((i, element))
    
    # 确定布局策略
    if len(image_elements) > 0 and len(text_elements) > 0:
        # 图文混合布局
        return _create_text_image_layout(text_elements, image_elements, table_elements, other_elements, content_area)
    elif len(image_elements) > 1:
        # 多图布局
        return _create_multi_image_layout(image_elements, text_elements, table_elements, other_elements, content_area)
    else:
        # 默认网格布局
        return _create_grid_layout(elements, content_area)


def _create_auto_layout(elements, content_area):
    """根据内容自动选择最佳布局"""
    # 分析元素类型和数量
    element_count = len(elements)
    element_types = [element.get("type", "").lower() for element in elements]
    
    # 计算各类型元素的数量
    text_count = sum(1 for t in element_types if t in ["text", "paragraph", "bullet"])
    image_count = sum(1 for t in element_types if t in ["image", "picture", "photo"])
    table_count = sum(1 for t in element_types if t in ["table", "grid"])
    
    # 根据元素组成选择布局
    if element_count == 1:
        # 单元素居中布局
        return _create_single_element_layout(elements[0], content_area)
    elif image_count > 0 and text_count > 0:
        # 图文混合布局
        if image_count == 1 and text_count >= 1:
            # 单图多文本
            return _create_image_text_layout(elements, content_area)
        else:
            # 多图多文本
            return _create_balanced_layout(elements, content_area)
    elif image_count > 1:
        # 多图布局
        return _create_grid_image_layout([e for e in elements if e.get("type", "").lower() in ["image", "picture", "photo"]], content_area)
    elif table_count >= 1:
        # 表格为主的布局
        return _create_table_centered_layout(elements, content_area)
    elif text_count >= 3:
        # 多文本列布局
        return _create_column_layout(elements, content_area)
    else:
        # 默认网格布局
        return _create_grid_layout(elements, content_area)


def _create_single_element_layout(element, content_area):
    """创建单元素居中布局"""
    element_type = element.get("type", "").lower()
    
    # 根据元素类型调整大小
    if element_type in ["table", "grid"]:
        # 表格占据大部分空间
        width = content_area["width"] * 0.9
        height = content_area["height"] * 0.9
    elif element_type in ["image", "picture", "photo"]:
        # 图片保持适当比例
        width = content_area["width"] * 0.7
        height = content_area["height"] * 0.7
    else:
        # 文本和其他元素
        width = content_area["width"] * 0.8
        height = content_area["height"] * 0.6
    
    # 居中放置
    left = content_area["left"] + (content_area["width"] - width) / 2
    top = content_area["top"] + (content_area["height"] - height) / 2
    
    return [{
        "element_index": 0,
        "element_type": element_type,
        "position": {
            "left": round(left, 2),
            "top": round(top, 2),
            "width": round(width, 2),
            "height": round(height, 2)
        }
    }]


def _create_image_text_layout(elements, content_area):
    """创建单图多文本布局"""
    layout = []
    
    # 找出图片和文本元素
    image_element = None
    text_elements = []
    
    for i, element in enumerate(elements):
        element_type = element.get("type", "").lower()
        if element_type in ["image", "picture", "photo"] and image_element is None:
            image_element = (i, element)
        elif element_type in ["text", "paragraph", "bullet"]:
            text_elements.append((i, element))
        else:
            text_elements.append((i, element))  # 其他元素也当作文本处理
    
    # 如果没有找到图片，使用网格布局
    if image_element is None:
        return _create_grid_layout(elements, content_area)
    
    # 确定布局方向（图片在左或在右）
    image_on_left = True  # 默认图片在左
    
    # 计算图片和文本区域
    if image_on_left:
        # 图片在左，文本在右
        image_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": content_area["width"] * 0.4,
            "height": content_area["height"]
        }
        
        text_area = {
            "left": content_area["left"] + image_area["width"],
            "top": content_area["top"],
            "width": content_area["width"] * 0.6,
            "height": content_area["height"]
        }
    else:
        # 文本在左，图片在右
        text_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": content_area["width"] * 0.6,
            "height": content_area["height"]
        }
        
        image_area = {
            "left": content_area["left"] + text_area["width"],
            "top": content_area["top"],
            "width": content_area["width"] * 0.4,
            "height": content_area["height"]
        }
    
    # 放置图片
    i, element = image_element
    layout.append({
        "element_index": i,
        "element_type": element.get("type", "unknown"),
        "position": {
            "left": round(image_area["left"] + image_area["width"] * 0.1, 2),
            "top": round(image_area["top"] + image_area["height"] * 0.1, 2),
            "width": round(image_area["width"] * 0.8, 2),
            "height": round(image_area["height"] * 0.8, 2)
        }
    })
    
    # 放置文本
    if text_elements:
        text_count = len(text_elements)
        text_height = text_area["height"] / text_count
        
        for j, (i, element) in enumerate(text_elements):
            layout.append({
                "element_index": i,
                "element_type": element.get("type", "unknown"),
                "position": {
                    "left": round(text_area["left"] + text_area["width"] * 0.05, 2),
                    "top": round(text_area["top"] + j * text_height, 2),
                    "width": round(text_area["width"] * 0.9, 2),
                    "height": round(text_height * 0.9, 2)
                }
            })
    
    return layout


def _create_text_image_layout(text_elements, image_elements, table_elements, other_elements, content_area):
    """创建图文混合布局"""
    layout = []
    
    # 计算各部分元素数量
    text_count = len(text_elements)
    image_count = len(image_elements)
    table_count = len(table_elements)
    other_count = len(other_elements)
    
    # 确定布局策略
    if image_count == 1 and text_count >= 1:
        # 单图多文本
        image_width = content_area["width"] * 0.4
        image_height = content_area["height"] * 0.6
        image_left = content_area["left"] + (content_area["width"] - image_width) / 2
        image_top = content_area["top"]
        
        # 放置图片
        i, element = image_elements[0]
        layout.append({
            "element_index": i,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(image_left, 2),
                "top": round(image_top, 2),
                "width": round(image_width, 2),
                "height": round(image_height, 2)
            }
        })
        
        # 放置文本（在图片下方）
        text_area = {
            "left": content_area["left"],
            "top": image_top + image_height,
            "width": content_area["width"],
            "height": content_area["height"] - image_height
        }
        
        # 使用列布局放置文本
        text_layout = _create_column_layout([e for _, e in text_elements], text_area)
        
        # 调整索引
        for j, item in enumerate(text_layout):
            item["element_index"] = text_elements[j][0]
            layout.append(item)
    
    elif image_count > 1 and text_count >= 1:
        # 多图多文本
        # 图片在上，文本在下
        image_area_height = content_area["height"] * 0.6
        image_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": content_area["width"],
            "height": image_area_height
        }
        
        text_area = {
            "left": content_area["left"],
            "top": content_area["top"] + image_area_height,
            "width": content_area["width"],
            "height": content_area["height"] - image_area_height
        }
        
        # 放置图片
        image_layout = _create_grid_image_layout([e for _, e in image_elements], image_area)
        
        # 调整索引
        for j, item in enumerate(image_layout):
            item["element_index"] = image_elements[j][0]
            layout.append(item)
        
        # 放置文本
        text_layout = _create_column_layout([e for _, e in text_elements], text_area)
        
        # 调整索引
        for j, item in enumerate(text_layout):
            item["element_index"] = text_elements[j][0]
            layout.append(item)
    
    # 添加表格和其他元素
    if table_count > 0 or other_count > 0:
        remaining_elements = table_elements + other_elements
        
        # 找出剩余空间
        used_areas = [item["position"] for item in layout]
        remaining_area = _calculate_remaining_area(content_area, used_areas)
        
        # 在剩余空间中放置元素
        if remaining_area:
            remaining_layout = _create_grid_layout([e for _, e in remaining_elements], remaining_area)
            
            # 调整索引
            for j, item in enumerate(remaining_layout):
                item["element_index"] = remaining_elements[j][0]
                layout.append(item)
    
    return layout


def _create_multi_image_layout(image_elements, text_elements, table_elements, other_elements, content_area):
    """创建多图布局"""
    layout = []
    
    # 计算各部分元素数量
    image_count = len(image_elements)
    
    # 为图片分配空间
    image_area = {
        "left": content_area["left"],
        "top": content_area["top"],
        "width": content_area["width"],
        "height": content_area["height"] * 0.7
    }
    
    # 放置图片
    image_layout = _create_grid_image_layout([e for _, e in image_elements], image_area)
    
    # 调整索引
    for j, item in enumerate(image_layout):
        item["element_index"] = image_elements[j][0]
        layout.append(item)
    
    # 为其他元素分配剩余空间
    remaining_elements = text_elements + table_elements + other_elements
    if remaining_elements:
        remaining_area = {
            "left": content_area["left"],
            "top": content_area["top"] + image_area["height"],
            "width": content_area["width"],
            "height": content_area["height"] - image_area["height"]
        }
        
        remaining_layout = _create_grid_layout([e for _, e in remaining_elements], remaining_area)
        
        # 调整索引
        for j, item in enumerate(remaining_layout):
            item["element_index"] = remaining_elements[j][0]
            layout.append(item)
    
    return layout


def _create_table_centered_layout(elements, content_area):
    """创建以表格为中心的布局"""
    layout = []
    
    # 找出表格和非表格元素
    table_elements = []
    other_elements = []
    
    for i, element in enumerate(elements):
        element_type = element.get("type", "").lower()
        if element_type in ["table", "grid"]:
            table_elements.append((i, element))
        else:
            other_elements.append((i, element))
    
    # 表格占据中心位置
    table_area = {
        "left": content_area["left"],
        "top": content_area["top"] + content_area["height"] * 0.2,
        "width": content_area["width"],
        "height": content_area["height"] * 0.6
    }
    
    # 放置表格
    for j, (i, element) in enumerate(table_elements):
        table_width = table_area["width"] / len(table_elements)
        layout.append({
            "element_index": i,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(table_area["left"] + j * table_width, 2),
                "top": round(table_area["top"], 2),
                "width": round(table_width * 0.95, 2),
                "height": round(table_area["height"], 2)
            }
        })
    
    # 放置其他元素
    if other_elements:
        # 上方区域
        top_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": content_area["width"],
            "height": content_area["height"] * 0.2
        }
        
        # 下方区域
        bottom_area = {
            "left": content_area["left"],
            "top": content_area["top"] + content_area["height"] * 0.8,
            "width": content_area["width"],
            "height": content_area["height"] * 0.2
        }
        
        # 将一半元素放在上方，一半放在下方
        mid_point = len(other_elements) // 2
        
        top_elements = other_elements[:mid_point]
        bottom_elements = other_elements[mid_point:]
        
        # 放置上方元素
        if top_elements:
            top_layout = _create_row_layout([e for _, e in top_elements], top_area)
            
            # 调整索引
            for j, item in enumerate(top_layout):
                item["element_index"] = top_elements[j][0]
                layout.append(item)
        
        # 放置下方元素
        if bottom_elements:
            bottom_layout = _create_row_layout([e for _, e in bottom_elements], bottom_area)
            
            # 调整索引
            for j, item in enumerate(bottom_layout):
                item["element_index"] = bottom_elements[j][0]
                layout.append(item)
    
    return layout


def _create_grid_image_layout(images, content_area):
    """创建图片网格布局"""
    layout = []
    
    # 计算网格尺寸
    image_count = len(images)
    if image_count <= 1:
        cols = 1
    elif image_count <= 4:
        cols = 2
    else:
        cols = 3
    
    rows = math.ceil(image_count / cols)
    
    # 计算单元格大小
    cell_width = content_area["width"] / cols
    cell_height = content_area["height"] / rows
    
    # 放置图片
    for i, image in enumerate(images):
        row = i // cols
        col = i % cols
        
        # 计算位置
        left = content_area["left"] + (col * cell_width)
        top = content_area["top"] + (row * cell_height)
        
        # 添加图片布局
        layout.append({
            "element_index": i,
            "element_type": image.get("type", "image"),
            "position": {
                "left": round(left + cell_width * 0.1, 2),  # 留出10%的边距
                "top": round(top + cell_height * 0.1, 2),
                "width": round(cell_width * 0.8, 2),
                "height": round(cell_height * 0.8, 2)
            }
        })
    
    return layout


def _create_cascade_image_layout(images, content_area):
    """创建层叠图片布局"""
    layout = []
    
    # 计算每个图片的偏移量
    offset_x = content_area["width"] * 0.05
    offset_y = content_area["height"] * 0.05
    
    # 计算基础图片大小
    base_width = content_area["width"] * 0.7
    base_height = content_area["height"] * 0.7
    
    # 放置图片
    for i, image in enumerate(images):
        # 计算位置
        left = content_area["left"] + (i * offset_x)
        top = content_area["top"] + (i * offset_y)
        
        # 确保不超出内容区域
        if left + base_width > content_area["left"] + content_area["width"]:
            left = content_area["left"] + content_area["width"] - base_width
        
        if top + base_height > content_area["top"] + content_area["height"]:
            top = content_area["top"] + content_area["height"] - base_height
        
        # 添加图片布局
        layout.append({
            "element_index": i,
            "element_type": image.get("type", "image"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(base_width, 2),
                "height": round(base_height, 2)
            },
            "z_index": i  # 层叠顺序
        })
    
    return layout


def _create_focal_image_layout(images, content_area):
    """创建焦点图片布局（一个主图，其他图片围绕）"""
    layout = []
    
    if not images:
        return layout
    
    # 第一张图片作为焦点
    focal_image = images[0]
    
    # 计算焦点图片大小
    focal_width = content_area["width"] * 0.6
    focal_height = content_area["height"] * 0.6
    
    # 计算焦点图片位置（居中）
    focal_left = content_area["left"] + (content_area["width"] - focal_width) / 2
    focal_top = content_area["top"] + (content_area["height"] - focal_height) / 2
    
    # 添加焦点图片
    layout.append({
        "element_index": 0,
        "element_type": focal_image.get("type", "image"),
        "position": {
            "left": round(focal_left, 2),
            "top": round(focal_top, 2),
            "width": round(focal_width, 2),
            "height": round(focal_height, 2)
        },
        "is_focal": True
    })
    
    # 如果有其他图片，围绕焦点放置
    if len(images) > 1:
        secondary_images = images[1:]
        
        # 计算次要图片大小
        secondary_width = content_area["width"] * 0.25
        secondary_height = content_area["height"] * 0.25
        
        # 计算放置位置
        positions = [
            {"left": focal_left - secondary_width * 0.8, "top": focal_top - secondary_height * 0.8},  # 左上
            {"left": focal_left + focal_width - secondary_width * 0.2, "top": focal_top - secondary_height * 0.8},  # 右上
            {"left": focal_left - secondary_width * 0.8, "top": focal_top + focal_height - secondary_height * 0.2},  # 左下
            {"left": focal_left + focal_width - secondary_width * 0.2, "top": focal_top + focal_height - secondary_height * 0.2}  # 右下
        ]
        
        # 放置次要图片
        for i, image in enumerate(secondary_images):
            if i < len(positions):
                pos = positions[i]
                
                # 添加次要图片
                layout.append({
                    "element_index": i + 1,
                    "element_type": image.get("type", "image"),
                    "position": {
                        "left": round(pos["left"], 2),
                        "top": round(pos["top"], 2),
                        "width": round(secondary_width, 2),
                        "height": round(secondary_height, 2)
                    },
                    "is_focal": False
                })
    
    return layout


def _create_gallery_image_layout(images, content_area):
    """创建画廊式图片布局（等大小，均匀分布）"""
    layout = []
    
    # 计算每行放置的图片数量
    image_count = len(images)
    
    if image_count <= 3:
        images_per_row = image_count
    elif image_count <= 6:
        images_per_row = 3
    else:
        images_per_row = 4
    
    rows = math.ceil(image_count / images_per_row)
    
    # 计算图片大小
    image_width = (content_area["width"] - (images_per_row - 1) * 0.2) / images_per_row
    image_height = (content_area["height"] - (rows - 1) * 0.2) / rows
    
    # 放置图片
    for i, image in enumerate(images):
        row = i // images_per_row
        col = i % images_per_row
        
        # 计算位置
        left = content_area["left"] + col * (image_width + 0.2)
        top = content_area["top"] + row * (image_height + 0.2)
        
        # 添加图片布局
        layout.append({
            "element_index": i,
            "element_type": image.get("type", "image"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(image_width, 2),
                "height": round(image_height, 2)
            }
        })
    
    return layout


def _create_focal_composition(elements, content_area):
    """创建焦点构图（一个主要元素，其他元素围绕）"""
    layout = []
    
    if not elements:
        return layout
    
    # 找出最重要的元素作为焦点
    focal_element = None
    other_elements = []
    
    for i, element in enumerate(elements):
        importance = element.get("importance", 0)
        if focal_element is None or importance > focal_element[1]:
            if focal_element:
                other_elements.append((focal_element[0], focal_element[2]))
            focal_element = (i, importance, element)
        else:
            other_elements.append((i, element))
    
    if not focal_element:
        return _create_balanced_composition_layout(elements, content_area)
    
    # 计算焦点元素大小
    focal_width = content_area["width"] * 0.6
    focal_height = content_area["height"] * 0.6
    
    # 计算焦点元素位置（居中）
    focal_left = content_area["left"] + (content_area["width"] - focal_width) / 2
    focal_top = content_area["top"] + (content_area["height"] - focal_height) / 2
    
    # 添加焦点元素
    layout.append({
        "element_index": focal_element[0],
        "element_type": focal_element[2].get("type", "unknown"),
        "position": {
            "left": round(focal_left, 2),
            "top": round(focal_top, 2),
            "width": round(focal_width, 2),
            "height": round(focal_height, 2)
        },
        "is_focal": True
    })
    
    # 如果有其他元素，围绕焦点放置
    if other_elements:
        # 计算次要元素大小
        secondary_width = content_area["width"] * 0.3
        secondary_height = content_area["height"] * 0.3
        
        # 计算放置位置
        positions = [
            {"left": focal_left - secondary_width * 0.8, "top": focal_top - secondary_height * 0.8},  # 左上
            {"left": focal_left + focal_width - secondary_width * 0.2, "top": focal_top - secondary_height * 0.8},  # 右上
            {"left": focal_left - secondary_width * 0.8, "top": focal_top + focal_height - secondary_height * 0.2},  # 左下
            {"left": focal_left + focal_width - secondary_width * 0.2, "top": focal_top + focal_height - secondary_height * 0.2}  # 右下
        ]
        
        # 放置次要元素
        for i, (idx, element) in enumerate(other_elements):
            if i < len(positions):
                pos = positions[i]
                
                # 添加次要元素
                layout.append({
                    "element_index": idx,
                    "element_type": element.get("type", "unknown"),
                    "position": {
                        "left": round(pos["left"], 2),
                        "top": round(pos["top"], 2),
                        "width": round(secondary_width, 2),
                        "height": round(secondary_height, 2)
                    },
                    "is_focal": False
                })
    
    return layout


def _create_rule_of_thirds_composition(elements, content_area):
    """创建三分法构图"""
    layout = []
    
    if not elements:
        return layout
    
    # 计算三分点
    third_x1 = content_area["left"] + content_area["width"] / 3
    third_x2 = content_area["left"] + content_area["width"] * 2 / 3
    third_y1 = content_area["top"] + content_area["height"] / 3
    third_y2 = content_area["top"] + content_area["height"] * 2 / 3
    
    # 定义交点
    intersections = [
        {"left": third_x1, "top": third_y1},  # 左上
        {"left": third_x2, "top": third_y1},  # 右上
        {"left": third_x1, "top": third_y2},  # 左下
        {"left": third_x2, "top": third_y2}   # 右下
    ]
    
    # 按重要性排序元素
    elements_with_importance = []
    for i, element in enumerate(elements):
        importance = element.get("importance", 0)
        elements_with_importance.append((i, importance, element))
    
    elements_with_importance.sort(key=lambda x: x[1], reverse=True)
    
    # 为最重要的元素分配交点
    for i, (idx, importance, element) in enumerate(elements_with_importance):
        if i < len(intersections):
            # 计算元素大小
            element_width = content_area["width"] * 0.3
            element_height = content_area["height"] * 0.3
            
            # 计算位置（使元素中心位于交点）
            left = intersections[i]["left"] - element_width / 2
            top = intersections[i]["top"] - element_height / 2
            
            # 确保不超出内容区域
            left = max(content_area["left"], min(left, content_area["left"] + content_area["width"] - element_width))
            top = max(content_area["top"], min(top, content_area["top"] + content_area["height"] - element_height))
            
            # 添加元素布局
            layout.append({
                "element_index": idx,
                "element_type": element.get("type", "unknown"),
                "position": {
                    "left": round(left, 2),
                    "top": round(top, 2),
                    "width": round(element_width, 2),
                    "height": round(element_height, 2)
                },
                "intersection_point": i + 1
            })
        else:
            # 剩余元素使用网格布局
            remaining_elements = [e[2] for e in elements_with_importance[len(intersections):]]
            remaining_indices = [e[0] for e in elements_with_importance[len(intersections):]]
            
            # 找出未使用的区域
            used_areas = [item["position"] for item in layout]
            remaining_area = _calculate_remaining_area(content_area, used_areas)
            
            if remaining_area:
                remaining_layout = _create_grid_layout(remaining_elements, remaining_area)
                
                # 调整索引
                for j, item in enumerate(remaining_layout):
                    item["element_index"] = remaining_indices[j]
                    layout.append(item)
            
            break
    
    return layout


def _create_golden_ratio_composition(elements, content_area):
    """创建黄金比例构图"""
    layout = []
    
    if not elements:
        return layout
    
    # 黄金比例约为1.618
    golden_ratio = 1.618
    
    # 计算主区域和次区域
    if content_area["width"] >= content_area["height"]:
        # 水平分割
        main_width = content_area["width"] / golden_ratio
        main_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": main_width,
            "height": content_area["height"]
        }
        
        secondary_area = {
            "left": content_area["left"] + main_width,
            "top": content_area["top"],
            "width": content_area["width"] - main_width,
            "height": content_area["height"]
        }
    else:
        # 垂直分割
        main_height = content_area["height"] / golden_ratio
        main_area = {
            "left": content_area["left"],
            "top": content_area["top"],
            "width": content_area["width"],
            "height": main_height
        }
        
        secondary_area = {
            "left": content_area["left"],
            "top": content_area["top"] + main_height,
            "width": content_area["width"],
            "height": content_area["height"] - main_height
        }
    
    # 按重要性排序元素
    elements_with_importance = []
    for i, element in enumerate(elements):
        importance = element.get("importance", 0)
        elements_with_importance.append((i, importance, element))
    
    elements_with_importance.sort(key=lambda x: x[1], reverse=True)
    
    # 将最重要的元素放在主区域
    if elements_with_importance:
        idx, _, element = elements_with_importance[0]
        
        # 计算元素大小
        element_width = main_area["width"] * 0.9
        element_height = main_area["height"] * 0.9
        
        # 计算位置
        left = main_area["left"] + (main_area["width"] - element_width) / 2
        top = main_area["top"] + (main_area["height"] - element_height) / 2
        
        # 添加主元素布局
        layout.append({
            "element_index": idx,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(element_width, 2),
                "height": round(element_height, 2)
            },
            "area": "main"
        })
    
    # 将剩余元素放在次区域
    if len(elements_with_importance) > 1:
        remaining_elements = [e[2] for e in elements_with_importance[1:]]
        remaining_indices = [e[0] for e in elements_with_importance[1:]]
        
        # 在次区域使用网格布局
        secondary_layout = _create_grid_layout(remaining_elements, secondary_area)
        
        # 调整索引
        for j, item in enumerate(secondary_layout):
            item["element_index"] = remaining_indices[j]
            item["area"] = "secondary"
            layout.append(item)
    
    return layout


def _create_symmetrical_composition(elements, content_area):
    """创建对称构图"""
    layout = []
    
    if not elements:
        return layout
    
    # 计算中心点
    center_x = content_area["left"] + content_area["width"] / 2
    center_y = content_area["top"] + content_area["height"] / 2
    
    # 按重要性排序元素
    elements_with_importance = []
    for i, element in enumerate(elements):
        importance = element.get("importance", 0)
        elements_with_importance.append((i, importance, element))
    
    elements_with_importance.sort(key=lambda x: x[1], reverse=True)
    
    # 将最重要的元素放在中心
    if elements_with_importance:
        idx, _, element = elements_with_importance[0]
        
        # 计算元素大小
        element_width = content_area["width"] * 0.4
        element_height = content_area["height"] * 0.4
        
        # 计算位置
        left = center_x - element_width / 2
        top = center_y - element_height / 2
        
        # 添加中心元素布局
        layout.append({
            "element_index": idx,
            "element_type": element.get("type", "unknown"),
            "position": {
                "left": round(left, 2),
                "top": round(top, 2),
                "width": round(element_width, 2),
                "height": round(element_height, 2)
            },
            "position_type": "center"
        })
    
    # 对称放置剩余元素
    if len(elements_with_importance) > 1:
        remaining_elements = elements_with_importance[1:]
        
        # 计算对称位置
        positions = []
        
        # 左右对称位置
        if len(remaining_elements) >= 2:
            left_element = remaining_elements[0]
            right_element = remaining_elements[1]
            
            # 计算元素大小
            element_width = content_area["width"] * 0.25
            element_height = content_area["height"] * 0.3
            
            # 左侧位置
            left_left = content_area["left"] + content_area["width"] * 0.1
            left_top = center_y - element_height / 2
            
            # 右侧位置
            right_left = content_area["left"] + content_area["width"] * 0.65
            right_top = center_y - element_height / 2
            
            # 添加左侧元素布局
            layout.append({
                "element_index": left_element[0],
                "element_type": left_element[2].get("type", "unknown"),
                "position": {
                    "left": round(left_left, 2),
                    "top": round(left_top, 2),
                    "width": round(element_width, 2),
                    "height": round(element_height, 2)
                },
                "position_type": "left"
            })
            
            # 添加右侧元素布局
            layout.append({
                "element_index": right_element[0],
                "element_type": right_element[2].get("type", "unknown"),
                "position": {
                    "left": round(right_left, 2),
                    "top": round(right_top, 2),
                    "width": round(element_width, 2),
                    "height": round(element_height, 2)
                },
                "position_type": "right"
            })
        
        # 如果还有更多元素，上下对称放置
        if len(remaining_elements) > 2:
            # 在剩余空间中使用网格布局
            remaining = remaining_elements[2:]
            remaining_indices = [e[0] for e in remaining]
            remaining_elements_list = [e[2] for e in remaining]
            
            # 找出未使用的区域
            used_areas = [item["position"] for item in layout]
            remaining_area = _calculate_remaining_area(content_area, used_areas)
            
            if remaining_area:
                remaining_layout = _create_grid_layout(remaining_elements_list, remaining_area)
                
                # 调整索引
                for j, item in enumerate(remaining_layout):
                    item["element_index"] = remaining_indices[j]
                    layout.append(item)
    
    return layout


def _create_balanced_composition_layout(elements, content_area):
    """创建平衡构图"""
    layout = []
    
    if not elements:
        return layout
    
    # 按重要性排序元素
    elements_with_importance = []
    for i, element in enumerate(elements):
        importance = element.get("importance", 0)
        elements_with_importance.append((i, importance, element))
    
    elements_with_importance.sort(key=lambda x: x[1], reverse=True)
    
    # 计算中心点
    center_x = content_area["left"] + content_area["width"] / 2
    center_y = content_area["top"] + content_area["height"] / 2
    
    # 将元素分为左右两组
    left_elements = []
    right_elements = []
    
    total_importance = sum(e[1] for e in elements_with_importance)
    left_importance = 0
    right_importance = 0
    
    for i, (idx, importance, element) in enumerate(elements_with_importance):
        # 尝试平衡左右两侧的重要性
        if left_importance <= right_importance:
            left_elements.append((idx, importance, element))
            left_importance += importance
        else:
            right_elements.append((idx, importance, element))
            right_importance += importance
    
    # 计算左右区域
    left_area = {
        "left": content_area["left"],
        "top": content_area["top"],
        "width": content_area["width"] / 2,
        "height": content_area["height"]
    }
    
    right_area = {
        "left": content_area["left"] + content_area["width"] / 2,
        "top": content_area["top"],
        "width": content_area["width"] / 2,
        "height": content_area["height"]
    }
    
    # 在左侧区域放置元素
    if left_elements:
        left_layout = _create_grid_layout([e[2] for e in left_elements], left_area)
        
        # 调整索引
        for j, item in enumerate(left_layout):
            item["element_index"] = left_elements[j][0]
            item["side"] = "left"
            layout.append(item)
    
    # 在右侧区域放置元素
    if right_elements:
        right_layout = _create_grid_layout([e[2] for e in right_elements], right_area)
        
        # 调整索引
        for j, item in enumerate(right_layout):
            item["element_index"] = right_elements[j][0]
            item["side"] = "right"
            layout.append(item)
    
    return layout


def _calculate_remaining_area(content_area, used_areas):
    """计算内容区域中未使用的空间"""
    # 简单实现：如果内容区域底部有足够空间，返回底部区域
    bottom_y = content_area["top"]
    
    for area in used_areas:
        bottom = area["top"] + area["height"]
        if bottom > bottom_y:
            bottom_y = bottom
    
    if bottom_y < content_area["top"] + content_area["height"] - 1:  # 至少1英寸高度
        return {
            "left": content_area["left"],
            "top": bottom_y,
            "width": content_area["width"],
            "height": content_area["top"] + content_area["height"] - bottom_y
        }
    
    # 如果底部没有足够空间，尝试右侧
    right_x = content_area["left"]
    
    for area in used_areas:
        right = area["left"] + area["width"]
        if right > right_x:
            right_x = right
    
    if right_x < content_area["left"] + content_area["width"] - 1:  # 至少1英寸宽度
        return {
            "left": right_x,
            "top": content_area["top"],
            "width": content_area["left"] + content_area["width"] - right_x,
            "height": content_area["height"]
        }
    
    return None


def _get_element_complexity(element):
    """评估元素的复杂度"""
    element_type = element.get("type", "").lower()
    
    if element_type in ["table", "grid", "chart", "diagram"]:
        return "high"
    elif element_type in ["image", "picture", "photo"]:
        return "medium"
    else:
        return "low"


def _merge_slides(slides, max_slides):
    """尝试合并幻灯片以减少数量"""
    if len(slides) <= max_slides:
        return slides
    
    # 计算需要合并的幻灯片数量
    slides_to_merge = len(slides) - max_slides
    
    # 找出元素最少的幻灯片进行合并
    slide_sizes = [(i, len(slide)) for i, slide in enumerate(slides)]
    slide_sizes.sort(key=lambda x: x[1])  # 按元素数量排序
    
    # 跳过第一张幻灯片（通常是标题幻灯片）
    merge_candidates = slide_sizes[1:]
    
    # 合并幻灯片
    merged_slides = slides.copy()
    merged_indices = set()
    
    for i in range(slides_to_merge):
        if i < len(merge_candidates) - 1:
            # 获取要合并的两张幻灯片
            idx1 = merge_candidates[i][0]
            idx2 = merge_candidates[i + 1][0]
            
            # 确保索引有效且未被合并
            if idx1 not in merged_indices and idx2 not in merged_indices and idx1 < len(merged_slides) and idx2 < len(merged_slides):
                # 合并幻灯片内容
                merged_slides[idx1].extend(merged_slides[idx2])
                merged_indices.add(idx2)
    
    # 移除已合并的幻灯片
    result = [slide for i, slide in enumerate(merged_slides) if i not in merged_indices]
    
    return result


def _estimate_element_importance(element):
    """估算元素的重要性"""
    element_type = element.get("type", "").lower()
    
    # 基础重要性
    base_importance = 5
    
    # 根据元素类型调整重要性
    if element_type in ["title", "heading", "h1"]:
        base_importance += 5
    elif element_type in ["subtitle", "h2"]:
        base_importance += 4
    elif element_type in ["h3", "h4"]:
        base_importance += 3
    elif element_type in ["table", "chart", "diagram"]:
        base_importance += 3
    elif element_type in ["image", "picture", "photo"]:
        base_importance += 2
    elif element_type in ["list", "bullet"]:
        base_importance += 1
    
    # 根据位置调整重要性
    position = element.get("position", {})
    if position:
        # 靠近中心的元素更重要
        if "left" in position and "top" in position:
            center_x = 0.5  # 假设幻灯片宽度为1
            center_y = 0.5  # 假设幻灯片高度为1
            
            distance_from_center = math.sqrt((position["left"] - center_x) ** 2 + (position["top"] - center_y) ** 2)
            
            # 距离中心越近，加分越多
            if distance_from_center < 0.2:
                base_importance += 2
            elif distance_from_center < 0.4:
                base_importance += 1
    
    return base_importance


def _calculate_element_style(element_type, importance):
    """根据元素类型和重要性计算样式"""
    style = {}
    
    # 基础字体大小（磅）
    base_font_size = 14
    
    if element_type in ["title", "heading", "h1"]:
        style["font_size"] = base_font_size + 10
        style["bold"] = True
        style["alignment"] = "center"
    elif element_type in ["subtitle", "h2"]:
        style["font_size"] = base_font_size + 6
        style["bold"] = True
        style["alignment"] = "center"
    elif element_type in ["h3", "h4"]:
        style["font_size"] = base_font_size + 2
        style["bold"] = True
    elif element_type in ["text", "paragraph"]:
        style["font_size"] = base_font_size
    elif element_type in ["list", "bullet"]:
        style["font_size"] = base_font_size
        style["bullet"] = True
    
    # 根据重要性调整样式
    if importance >= 8:
        if "font_size" in style:
            style["font_size"] += 2
        style["emphasis"] = True
    
    return style


def _calculate_element_position(element_type, importance, index, total_elements, slide_width, slide_height):
    """根据元素类型和重要性计算位置"""
    position = {}
    
    # 标题元素居中
    if element_type in ["title", "heading", "h1"]:
        position["left"] = slide_width * 0.1
        position["top"] = slide_height * 0.1
        position["width"] = slide_width * 0.8
        position["height"] = slide_height * 0.15
    
    # 副标题在标题下方
    elif element_type in ["subtitle", "h2"]:
        position["left"] = slide_width * 0.15
        position["top"] = slide_height * 0.25
        position["width"] = slide_width * 0.7
        position["height"] = slide_height * 0.1
    
    # 重要内容在中心区域
    elif importance >= 8:
        position["left"] = slide_width * 0.25
        position["top"] = slide_height * 0.35
        position["width"] = slide_width * 0.5
        position["height"] = slide_height * 0.3
    
    # 其他元素根据索引分布
    else:
        # 计算网格位置
        cols = min(3, total_elements)
        rows = math.ceil(total_elements / cols)
        
        row = index // cols
        col = index % cols
        
        cell_width = slide_width / cols
        cell_height = slide_height / (rows + 1)  # 留出顶部空间
        
        position["left"] = col * cell_width + (cell_width * 0.1)
        position["top"] = slide_height * 0.4 + row * cell_height
        position["width"] = cell_width * 0.8
        position["height"] = cell_height * 0.8
    
    # 确保位置值为浮点数
    for key in position:
        position[key] = float(position[key])
    
    return position