"""
样式映射工具，用于将HTML样式映射到PPT样式。

此模块提供了一组工具函数，用于分析HTML元素的样式属性，并将其映射到
PowerPoint演示文稿中的对应样式，确保转换后的PPT保持原始HTML的视觉效果。
"""

import re
import json
import colorsys
from typing import Dict, List, Any, Optional, Tuple, Union
from strands import tool


@tool
def map_html_styles_to_ppt(
    html_styles: Dict[str, Any],
    element_type: str,
    target_format: str = "pptx"
) -> str:
    """
    将HTML样式映射到PPT样式。

    Args:
        html_styles (Dict[str, Any]): HTML元素的样式属性字典
        element_type (str): HTML元素类型，如"p", "h1", "img", "table"等
        target_format (str): 目标格式，默认为"pptx"
        
    Returns:
        str: JSON格式的PPT样式属性
    """
    try:
        # 初始化PPT样式字典
        ppt_styles = {}
        
        # 处理文本相关样式
        if element_type in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "div", "li", "a", "td", "th"]:
            # 字体
            if "font-family" in html_styles:
                ppt_styles["font_name"] = _extract_font_family(html_styles["font-family"])
            
            # 字体大小
            if "font-size" in html_styles:
                font_size = _convert_font_size(html_styles["font-size"], element_type)
                if font_size:
                    ppt_styles["font_size"] = font_size
            
            # 字体粗细
            if "font-weight" in html_styles:
                ppt_styles["bold"] = _is_bold(html_styles["font-weight"])
            
            # 字体样式
            if "font-style" in html_styles:
                ppt_styles["italic"] = html_styles["font-style"].lower() == "italic"
            
            # 文本装饰
            if "text-decoration" in html_styles:
                text_decoration = html_styles["text-decoration"].lower()
                ppt_styles["underline"] = "underline" in text_decoration
                ppt_styles["strike"] = "line-through" in text_decoration
            
            # 文本对齐
            if "text-align" in html_styles:
                ppt_styles["alignment"] = _map_text_alignment(html_styles["text-align"])
            
            # 文本颜色
            if "color" in html_styles:
                color = _parse_color(html_styles["color"])
                if color:
                    ppt_styles["color"] = color
            
            # 背景颜色
            if "background-color" in html_styles:
                bg_color = _parse_color(html_styles["background-color"])
                if bg_color:
                    ppt_styles["fill_color"] = bg_color
            
            # 行高
            if "line-height" in html_styles:
                line_height = _convert_line_height(html_styles["line-height"])
                if line_height:
                    ppt_styles["line_spacing"] = line_height
            
            # 段落间距
            if "margin-bottom" in html_styles:
                margin_bottom = _convert_spacing(html_styles["margin-bottom"])
                if margin_bottom:
                    ppt_styles["space_after"] = margin_bottom
            
            if "margin-top" in html_styles:
                margin_top = _convert_spacing(html_styles["margin-top"])
                if margin_top:
                    ppt_styles["space_before"] = margin_top
        
        # 处理图片相关样式
        elif element_type == "img":
            # 宽度和高度
            if "width" in html_styles:
                width = _convert_dimension(html_styles["width"])
                if width:
                    ppt_styles["width"] = width
            
            if "height" in html_styles:
                height = _convert_dimension(html_styles["height"])
                if height:
                    ppt_styles["height"] = height
            
            # 边框
            if "border" in html_styles:
                border_props = _parse_border(html_styles["border"])
                if border_props:
                    ppt_styles.update(border_props)
            
            # 边距
            if "margin" in html_styles:
                margin = _parse_margin(html_styles["margin"])
                if margin:
                    ppt_styles.update(margin)
        
        # 处理表格相关样式
        elif element_type in ["table", "tr", "td", "th"]:
            # 边框
            if "border" in html_styles:
                border_props = _parse_border(html_styles["border"])
                if border_props:
                    ppt_styles.update(border_props)
            
            # 背景颜色
            if "background-color" in html_styles:
                bg_color = _parse_color(html_styles["background-color"])
                if bg_color:
                    ppt_styles["fill_color"] = bg_color
            
            # 宽度
            if "width" in html_styles and element_type in ["table", "td", "th"]:
                width = _convert_dimension(html_styles["width"])
                if width:
                    ppt_styles["width"] = width
            
            # 高度
            if "height" in html_styles and element_type in ["table", "tr"]:
                height = _convert_dimension(html_styles["height"])
                if height:
                    ppt_styles["height"] = height
            
            # 单元格内边距
            if "padding" in html_styles and element_type in ["td", "th"]:
                padding = _parse_padding(html_styles["padding"])
                if padding:
                    ppt_styles.update(padding)
        
        # 处理列表相关样式
        elif element_type in ["ul", "ol"]:
            # 列表类型
            if element_type == "ul":
                ppt_styles["bullet_type"] = "bullet"
            else:
                ppt_styles["bullet_type"] = "number"
            
            # 缩进
            if "margin-left" in html_styles:
                indent = _convert_spacing(html_styles["margin-left"])
                if indent:
                    ppt_styles["indent"] = indent
        
        # 添加元素类型信息
        ppt_styles["element_type"] = element_type
        
        # 构建响应
        response = {
            "status": "success",
            "html_element": element_type,
            "ppt_styles": ppt_styles
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "样式映射失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def extract_html_styles(
    html_element: Dict[str, Any],
    include_computed: bool = True,
    include_inherited: bool = True
) -> str:
    """
    从HTML元素中提取样式信息。

    Args:
        html_element (Dict[str, Any]): HTML元素的字典表示，包含标签、属性和内联样式
        include_computed (bool): 是否包含计算样式
        include_inherited (bool): 是否包含继承样式
        
    Returns:
        str: JSON格式的样式信息
    """
    try:
        # 初始化样式字典
        styles = {}
        
        # 提取元素类型
        element_type = html_element.get("tag", "").lower()
        if not element_type:
            raise ValueError("HTML元素缺少标签信息")
        
        # 提取内联样式
        inline_styles = {}
        if "attributes" in html_element and "style" in html_element["attributes"]:
            inline_style_str = html_element["attributes"]["style"]
            inline_styles = _parse_inline_styles(inline_style_str)
        
        # 提取class和id
        classes = []
        element_id = None
        if "attributes" in html_element:
            if "class" in html_element["attributes"]:
                classes = html_element["attributes"]["class"].split()
            if "id" in html_element["attributes"]:
                element_id = html_element["attributes"]["id"]
        
        # 根据元素类型设置默认样式
        default_styles = _get_default_styles(element_type)
        
        # 合并样式（默认样式 < 继承样式 < 计算样式 < 内联样式）
        styles.update(default_styles)
        
        # 添加继承样式（在实际应用中，这些将从父元素继承）
        if include_inherited and "inherited_styles" in html_element:
            styles.update(html_element["inherited_styles"])
        
        # 添加计算样式（在实际应用中，这些将从CSS规则计算）
        if include_computed and "computed_styles" in html_element:
            styles.update(html_element["computed_styles"])
        
        # 内联样式优先级最高
        styles.update(inline_styles)
        
        # 构建响应
        response = {
            "status": "success",
            "element_type": element_type,
            "styles": styles,
            "classes": classes,
            "id": element_id,
            "has_inline_styles": bool(inline_styles)
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "样式提取失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def map_color_scheme(
    html_colors: List[Dict[str, Any]],
    target_format: str = "pptx"
) -> str:
    """
    将HTML颜色方案映射到PPT颜色方案。

    Args:
        html_colors (List[Dict[str, Any]]): HTML颜色列表，每个颜色包含名称、值和用途
        target_format (str): 目标格式，默认为"pptx"
        
    Returns:
        str: JSON格式的PPT颜色方案
    """
    try:
        # 初始化PPT颜色方案
        ppt_colors = {
            "background": None,
            "text": None,
            "accent1": None,
            "accent2": None,
            "accent3": None,
            "accent4": None,
            "accent5": None,
            "accent6": None
        }
        
        # 分析颜色用途
        background_colors = []
        text_colors = []
        accent_colors = []
        
        for color_info in html_colors:
            color_value = color_info.get("value")
            color_usage = color_info.get("usage", "").lower()
            
            if not color_value:
                continue
            
            # 解析颜色值
            rgb = _parse_color(color_value)
            if not rgb:
                continue
            
            # 根据用途分类
            if "background" in color_usage:
                background_colors.append((rgb, color_info))
            elif any(term in color_usage for term in ["text", "font", "foreground"]):
                text_colors.append((rgb, color_info))
            else:
                accent_colors.append((rgb, color_info))
        
        # 设置背景色
        if background_colors:
            # 使用出现频率最高的背景色
            ppt_colors["background"] = background_colors[0][0]
        
        # 设置文本色
        if text_colors:
            # 使用出现频率最高的文本色
            ppt_colors["text"] = text_colors[0][0]
        
        # 设置强调色
        for i, (rgb, _) in enumerate(accent_colors[:6]):
            ppt_colors[f"accent{i+1}"] = rgb
        
        # 如果强调色不足6个，生成互补色
        if accent_colors:
            base_color = accent_colors[0][0]
            for i in range(len(accent_colors), 6):
                # 生成互补色
                h, s, v = colorsys.rgb_to_hsv(base_color[0]/255, base_color[1]/255, base_color[2]/255)
                h = (h + (i+1)/6) % 1.0  # 在色环上均匀分布
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                ppt_colors[f"accent{i+1}"] = [int(r*255), int(g*255), int(b*255)]
        
        # 如果没有足够的颜色，使用默认颜色方案
        if not ppt_colors["background"]:
            ppt_colors["background"] = [255, 255, 255]  # 白色背景
        if not ppt_colors["text"]:
            ppt_colors["text"] = [0, 0, 0]  # 黑色文本
        
        for i in range(1, 7):
            if not ppt_colors[f"accent{i}"]:
                # 使用Office默认强调色
                default_accents = [
                    [91, 155, 213],   # 蓝色
                    [237, 125, 49],   # 橙色
                    [165, 165, 165],  # 灰色
                    [255, 192, 0],    # 金色
                    [68, 114, 196],   # 深蓝色
                    [112, 173, 71]    # 绿色
                ]
                ppt_colors[f"accent{i}"] = default_accents[i-1]
        
        # 构建响应
        response = {
            "status": "success",
            "color_scheme": ppt_colors,
            "analysis": {
                "background_colors_count": len(background_colors),
                "text_colors_count": len(text_colors),
                "accent_colors_count": len(accent_colors),
                "total_colors_analyzed": len(html_colors)
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "颜色方案映射失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def map_font_scheme(
    html_fonts: List[Dict[str, Any]],
    target_format: str = "pptx"
) -> str:
    """
    将HTML字体方案映射到PPT字体方案。

    Args:
        html_fonts (List[Dict[str, Any]]): HTML字体列表，每个字体包含名称、类型和用途
        target_format (str): 目标格式，默认为"pptx"
        
    Returns:
        str: JSON格式的PPT字体方案
    """
    try:
        # 初始化PPT字体方案
        ppt_fonts = {
            "title": None,
            "body": None,
            "fallback_title": "Arial",
            "fallback_body": "Arial"
        }
        
        # 分析字体用途
        title_fonts = []
        body_fonts = []
        
        for font_info in html_fonts:
            font_name = font_info.get("name")
            font_usage = font_info.get("usage", "").lower()
            
            if not font_name:
                continue
            
            # 清理字体名称（移除引号和多余空格）
            font_name = re.sub(r'^["\']\s*|\s*["\']$', '', font_name.strip())
            
            # 根据用途分类
            if any(term in font_usage for term in ["heading", "title", "h1", "h2", "h3"]):
                title_fonts.append(font_name)
            else:
                body_fonts.append(font_name)
        
        # 设置标题字体
        if title_fonts:
            # 使用出现频率最高的标题字体
            ppt_fonts["title"] = title_fonts[0]
        
        # 设置正文字体
        if body_fonts:
            # 使用出现频率最高的正文字体
            ppt_fonts["body"] = body_fonts[0]
        
        # 如果没有找到标题字体，使用正文字体
        if not ppt_fonts["title"] and ppt_fonts["body"]:
            ppt_fonts["title"] = ppt_fonts["body"]
        
        # 如果没有找到正文字体，使用标题字体
        if not ppt_fonts["body"] and ppt_fonts["title"]:
            ppt_fonts["body"] = ppt_fonts["title"]
        
        # 构建响应
        response = {
            "status": "success",
            "font_scheme": ppt_fonts,
            "analysis": {
                "title_fonts_count": len(title_fonts),
                "body_fonts_count": len(body_fonts),
                "title_fonts": title_fonts[:5],  # 限制返回的字体数量
                "body_fonts": body_fonts[:5]
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "字体方案映射失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def get_element_box_model(
    html_styles: Dict[str, Any],
    element_type: str
) -> str:
    """
    获取HTML元素的盒模型信息。

    Args:
        html_styles (Dict[str, Any]): HTML元素的样式属性字典
        element_type (str): HTML元素类型
        
    Returns:
        str: JSON格式的盒模型信息
    """
    try:
        # 初始化盒模型
        box_model = {
            "content": {"width": None, "height": None},
            "padding": {"top": 0, "right": 0, "bottom": 0, "left": 0},
            "border": {"top": 0, "right": 0, "bottom": 0, "left": 0},
            "margin": {"top": 0, "right": 0, "bottom": 0, "left": 0},
            "box_sizing": "content-box"
        }
        
        # 设置box-sizing
        if "box-sizing" in html_styles:
            box_model["box_sizing"] = html_styles["box-sizing"]
        
        # 提取宽度和高度
        if "width" in html_styles:
            box_model["content"]["width"] = _convert_dimension(html_styles["width"])
        
        if "height" in html_styles:
            box_model["content"]["height"] = _convert_dimension(html_styles["height"])
        
        # 提取内边距
        if "padding" in html_styles:
            padding = _parse_padding(html_styles["padding"])
            if padding:
                for side in ["top", "right", "bottom", "left"]:
                    key = f"padding_{side}"
                    if key in padding:
                        box_model["padding"][side] = padding[key]
        else:
            # 单独的内边距属性
            for side in ["top", "right", "bottom", "left"]:
                key = f"padding-{side}"
                if key in html_styles:
                    value = _convert_spacing(html_styles[key])
                    if value is not None:
                        box_model["padding"][side] = value
        
        # 提取边框
        if "border" in html_styles:
            border = _parse_border(html_styles["border"])
            if border:
                for side in ["top", "right", "bottom", "left"]:
                    key = f"border_{side}_width"
                    if key in border:
                        box_model["border"][side] = border[key]
        else:
            # 单独的边框属性
            for side in ["top", "right", "bottom", "left"]:
                key = f"border-{side}-width"
                if key in html_styles:
                    value = _convert_spacing(html_styles[key])
                    if value is not None:
                        box_model["border"][side] = value
        
        # 提取外边距
        if "margin" in html_styles:
            margin = _parse_margin(html_styles["margin"])
            if margin:
                for side in ["top", "right", "bottom", "left"]:
                    key = f"margin_{side}"
                    if key in margin:
                        box_model["margin"][side] = margin[key]
        else:
            # 单独的外边距属性
            for side in ["top", "right", "bottom", "left"]:
                key = f"margin-{side}"
                if key in html_styles:
                    value = _convert_spacing(html_styles[key])
                    if value is not None:
                        box_model["margin"][side] = value
        
        # 计算总宽度和高度
        total_width = box_model["content"]["width"]
        total_height = box_model["content"]["height"]
        
        if total_width is not None:
            if box_model["box_sizing"] == "content-box":
                total_width += box_model["padding"]["left"] + box_model["padding"]["right"]
                total_width += box_model["border"]["left"] + box_model["border"]["right"]
        
        if total_height is not None:
            if box_model["box_sizing"] == "content-box":
                total_height += box_model["padding"]["top"] + box_model["padding"]["bottom"]
                total_height += box_model["border"]["top"] + box_model["border"]["bottom"]
        
        # 构建响应
        response = {
            "status": "success",
            "element_type": element_type,
            "box_model": box_model,
            "computed": {
                "total_width": total_width,
                "total_height": total_height
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "获取盒模型信息失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def map_text_style_to_ppt(
    html_text_style: Dict[str, Any],
    ppt_defaults: Dict[str, Any] = None
) -> str:
    """
    将HTML文本样式映射到PPT文本样式。

    Args:
        html_text_style (Dict[str, Any]): HTML文本样式属性
        ppt_defaults (Dict[str, Any], optional): PPT默认样式属性
        
    Returns:
        str: JSON格式的PPT文本样式
    """
    try:
        # 初始化PPT文本样式
        ppt_text_style = {}
        
        # 如果提供了默认值，使用它们
        if ppt_defaults:
            ppt_text_style.update(ppt_defaults)
        
        # 字体
        if "font-family" in html_text_style:
            ppt_text_style["font_name"] = _extract_font_family(html_text_style["font-family"])
        
        # 字体大小
        if "font-size" in html_text_style:
            font_size = _convert_font_size(html_text_style["font-size"])
            if font_size:
                ppt_text_style["font_size"] = font_size
        
        # 字体粗细
        if "font-weight" in html_text_style:
            ppt_text_style["bold"] = _is_bold(html_text_style["font-weight"])
        
        # 字体样式
        if "font-style" in html_text_style:
            ppt_text_style["italic"] = html_text_style["font-style"].lower() == "italic"
        
        # 文本装饰
        if "text-decoration" in html_text_style:
            text_decoration = html_text_style["text-decoration"].lower()
            ppt_text_style["underline"] = "underline" in text_decoration
            ppt_text_style["strike"] = "line-through" in text_decoration
        
        # 文本对齐
        if "text-align" in html_text_style:
            ppt_text_style["alignment"] = _map_text_alignment(html_text_style["text-align"])
        
        # 文本颜色
        if "color" in html_text_style:
            color = _parse_color(html_text_style["color"])
            if color:
                ppt_text_style["color"] = color
        
        # 行高
        if "line-height" in html_text_style:
            line_height = _convert_line_height(html_text_style["line-height"])
            if line_height:
                ppt_text_style["line_spacing"] = line_height
        
        # 段落间距
        if "margin-bottom" in html_text_style:
            margin_bottom = _convert_spacing(html_text_style["margin-bottom"])
            if margin_bottom:
                ppt_text_style["space_after"] = margin_bottom
        
        if "margin-top" in html_text_style:
            margin_top = _convert_spacing(html_text_style["margin-top"])
            if margin_top:
                ppt_text_style["space_before"] = margin_top
        
        # 文本缩进
        if "text-indent" in html_text_style:
            indent = _convert_spacing(html_text_style["text-indent"])
            if indent:
                ppt_text_style["indent"] = indent
        
        # 文本转换
        if "text-transform" in html_text_style:
            text_transform = html_text_style["text-transform"].lower()
            if text_transform == "uppercase":
                ppt_text_style["all_caps"] = True
            elif text_transform == "lowercase":
                ppt_text_style["all_caps"] = False
        
        # 字母间距
        if "letter-spacing" in html_text_style:
            letter_spacing = _convert_spacing(html_text_style["letter-spacing"])
            if letter_spacing:
                ppt_text_style["character_spacing"] = letter_spacing
        
        # 构建响应
        response = {
            "status": "success",
            "ppt_text_style": ppt_text_style
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "文本样式映射失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def analyze_document_theme(
    html_styles: List[Dict[str, Any]]
) -> str:
    """
    分析HTML文档的主题样式，提取配色方案和字体方案。

    Args:
        html_styles (List[Dict[str, Any]]): HTML元素样式列表
        
    Returns:
        str: JSON格式的文档主题分析结果
    """
    try:
        # 初始化分析结果
        colors = []
        fonts = []
        
        # 提取颜色和字体
        for style in html_styles:
            element_type = style.get("element_type", "")
            styles = style.get("styles", {})
            
            # 提取颜色
            if "color" in styles:
                color = _parse_color(styles["color"])
                if color:
                    usage = "text"
                    if element_type in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                        usage = "heading"
                    
                    colors.append({
                        "value": color,
                        "usage": usage,
                        "element": element_type
                    })
            
            if "background-color" in styles:
                color = _parse_color(styles["background-color"])
                if color:
                    colors.append({
                        "value": color,
                        "usage": "background",
                        "element": element_type
                    })
            
            # 提取字体
            if "font-family" in styles:
                font_family = styles["font-family"]
                font_name = _extract_font_family(font_family)
                
                usage = "body"
                if element_type in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    usage = "heading"
                
                fonts.append({
                    "name": font_name,
                    "usage": usage,
                    "element": element_type
                })
        
        # 分析颜色方案
        color_scheme_result = json.loads(map_color_scheme(colors))
        
        # 分析字体方案
        font_scheme_result = json.loads(map_font_scheme(fonts))
        
        # 构建响应
        response = {
            "status": "success",
            "theme": {
                "colors": color_scheme_result.get("color_scheme", {}),
                "fonts": font_scheme_result.get("font_scheme", {})
            },
            "analysis": {
                "colors_found": len(colors),
                "fonts_found": len(fonts),
                "color_analysis": color_scheme_result.get("analysis", {}),
                "font_analysis": font_scheme_result.get("analysis", {})
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "文档主题分析失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _parse_inline_styles(style_str: str) -> Dict[str, str]:
    """解析内联样式字符串为样式字典"""
    styles = {}
    if not style_str:
        return styles
    
    # 分割样式声明
    declarations = style_str.split(';')
    for declaration in declarations:
        if ':' in declaration:
            property_name, value = declaration.split(':', 1)
            property_name = property_name.strip().lower()
            value = value.strip()
            if property_name and value:
                styles[property_name] = value
    
    return styles


def _get_default_styles(element_type: str) -> Dict[str, str]:
    """获取元素的默认样式"""
    default_styles = {}
    
    # 标题元素的默认样式
    if element_type == "h1":
        default_styles["font-size"] = "2em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "0.67em"
        default_styles["margin-bottom"] = "0.67em"
    elif element_type == "h2":
        default_styles["font-size"] = "1.5em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "0.83em"
        default_styles["margin-bottom"] = "0.83em"
    elif element_type == "h3":
        default_styles["font-size"] = "1.17em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "1em"
        default_styles["margin-bottom"] = "1em"
    elif element_type == "h4":
        default_styles["font-size"] = "1em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "1.33em"
        default_styles["margin-bottom"] = "1.33em"
    elif element_type == "h5":
        default_styles["font-size"] = "0.83em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "1.67em"
        default_styles["margin-bottom"] = "1.67em"
    elif element_type == "h6":
        default_styles["font-size"] = "0.67em"
        default_styles["font-weight"] = "bold"
        default_styles["margin-top"] = "2.33em"
        default_styles["margin-bottom"] = "2.33em"
    
    # 段落元素的默认样式
    elif element_type == "p":
        default_styles["margin-top"] = "1em"
        default_styles["margin-bottom"] = "1em"
    
    # 列表元素的默认样式
    elif element_type in ["ul", "ol"]:
        default_styles["margin-top"] = "1em"
        default_styles["margin-bottom"] = "1em"
        default_styles["padding-left"] = "40px"
    
    # 表格元素的默认样式
    elif element_type == "table":
        default_styles["border-collapse"] = "separate"
        default_styles["border-spacing"] = "2px"
    elif element_type == "th":
        default_styles["font-weight"] = "bold"
        default_styles["text-align"] = "center"
    
    # 链接元素的默认样式
    elif element_type == "a":
        default_styles["color"] = "#0000EE"
        default_styles["text-decoration"] = "underline"
    
    return default_styles


def _extract_font_family(font_family: str) -> str:
    """从font-family属性中提取第一个字体名称"""
    if not font_family:
        return "Arial"
    
    # 分割字体名称列表
    fonts = re.split(r',\s*', font_family)
    if not fonts:
        return "Arial"
    
    # 获取第一个字体名称
    first_font = fonts[0].strip()
    
    # 移除引号
    first_font = re.sub(r'^["\']\s*|\s*["\']$', '', first_font)
    
    return first_font or "Arial"


def _convert_font_size(font_size: str, element_type: str = None) -> Optional[float]:
    """将HTML字体大小转换为PPT字体大小（磅）"""
    if not font_size:
        return None
    
    # 默认字体大小（磅）
    default_sizes = {
        "p": 12,
        "h1": 24,
        "h2": 18,
        "h3": 14,
        "h4": 12,
        "h5": 10,
        "h6": 8
    }
    
    # 移除单位并转换为浮点数
    size_match = re.match(r'^([\d.]+)(\w+|%)$', font_size)
    if not size_match:
        # 使用元素类型的默认大小
        if element_type in default_sizes:
            return default_sizes[element_type]
        return 12  # 默认12磅
    
    value = float(size_match.group(1))
    unit = size_match.group(2)
    
    # 根据单位转换为磅
    if unit == 'pt':
        return value
    elif unit == 'px':
        return value * 0.75  # 1px ≈ 0.75pt
    elif unit == 'em':
        base_size = default_sizes.get(element_type, 12)
        return value * base_size
    elif unit == 'rem':
        return value * 12  # 假设1rem = 12pt
    elif unit == '%':
        base_size = default_sizes.get(element_type, 12)
        return (value / 100) * base_size
    else:
        # 其他单位（如vw, vh等）难以精确转换，使用默认值
        if element_type in default_sizes:
            return default_sizes[element_type]
        return 12


def _is_bold(font_weight: str) -> bool:
    """判断字体粗细是否为粗体"""
    if not font_weight:
        return False
    
    # 数值型粗细
    if font_weight.isdigit():
        return int(font_weight) >= 700
    
    # 关键字粗细
    return font_weight.lower() in ["bold", "bolder"]


def _map_text_alignment(text_align: str) -> str:
    """将HTML文本对齐方式映射到PPT对齐方式"""
    if not text_align:
        return "left"
    
    text_align = text_align.lower()
    
    if text_align == "left":
        return "left"
    elif text_align == "center":
        return "center"
    elif text_align == "right":
        return "right"
    elif text_align == "justify":
        return "justify"
    else:
        return "left"


def _parse_color(color_str: str) -> Optional[List[int]]:
    """解析颜色字符串为RGB值列表"""
    if not color_str:
        return None
    
    # 移除空白
    color_str = color_str.strip().lower()
    
    # 处理关键字颜色
    keyword_colors = {
        "black": [0, 0, 0],
        "white": [255, 255, 255],
        "red": [255, 0, 0],
        "green": [0, 128, 0],
        "blue": [0, 0, 255],
        "yellow": [255, 255, 0],
        "purple": [128, 0, 128],
        "gray": [128, 128, 128],
        "silver": [192, 192, 192],
        "maroon": [128, 0, 0],
        "olive": [128, 128, 0],
        "lime": [0, 255, 0],
        "aqua": [0, 255, 255],
        "teal": [0, 128, 128],
        "navy": [0, 0, 128],
        "fuchsia": [255, 0, 255]
    }
    
    if color_str in keyword_colors:
        return keyword_colors[color_str]
    
    # 处理十六进制颜色
    hex_match = re.match(r'^#?([0-9a-f]{3,8})$', color_str)
    if hex_match:
        hex_value = hex_match.group(1)
        
        if len(hex_value) == 3:
            # 简写形式 #RGB
            r = int(hex_value[0] + hex_value[0], 16)
            g = int(hex_value[1] + hex_value[1], 16)
            b = int(hex_value[2] + hex_value[2], 16)
            return [r, g, b]
        
        elif len(hex_value) == 6:
            # 标准形式 #RRGGBB
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
            return [r, g, b]
        
        elif len(hex_value) == 8:
            # 带透明度形式 #RRGGBBAA
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
            return [r, g, b]
    
    # 处理rgb()和rgba()颜色
    rgb_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*[\d.]+)?\s*\)$', color_str)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        return [r, g, b]
    
    # 处理rgb()百分比形式
    rgb_percent_match = re.match(r'rgba?\(\s*(\d+)%\s*,\s*(\d+)%\s*,\s*(\d+)%(?:\s*,\s*[\d.]+)?\s*\)$', color_str)
    if rgb_percent_match:
        r = int(float(rgb_percent_match.group(1)) * 2.55)
        g = int(float(rgb_percent_match.group(2)) * 2.55)
        b = int(float(rgb_percent_match.group(3)) * 2.55)
        return [r, g, b]
    
    return None


def _convert_dimension(dimension: str) -> Optional[float]:
    """将HTML尺寸转换为PPT尺寸（英寸）"""
    if not dimension:
        return None
    
    # 如果是auto或百分比，返回None
    if dimension == "auto" or "%" in dimension:
        return None
    
    # 移除单位并转换为浮点数
    size_match = re.match(r'^([\d.]+)(\w+)?$', dimension)
    if not size_match:
        return None
    
    value = float(size_match.group(1))
    unit = size_match.group(2) if size_match.group(2) else "px"
    
    # 根据单位转换为英寸
    if unit == 'in':
        return value
    elif unit == 'cm':
        return value / 2.54  # 1cm = 0.3937in
    elif unit == 'mm':
        return value / 25.4  # 1mm = 0.03937in
    elif unit == 'pt':
        return value / 72  # 1pt = 1/72in
    elif unit == 'pc':
        return value / 6  # 1pc = 1/6in
    elif unit == 'px':
        return value / 96  # 1px = 1/96in
    else:
        return value / 96  # 默认假设为像素


def _convert_spacing(spacing: str) -> Optional[float]:
    """将HTML间距转换为PPT间距（磅）"""
    if not spacing:
        return None
    
    # 如果是auto，返回None
    if spacing == "auto":
        return None
    
    # 移除单位并转换为浮点数
    size_match = re.match(r'^([\d.]+)(\w+|%)$', spacing)
    if not size_match:
        return None
    
    value = float(size_match.group(1))
    unit = size_match.group(2)
    
    # 根据单位转换为磅
    if unit == 'pt':
        return value
    elif unit == 'px':
        return value * 0.75  # 1px ≈ 0.75pt
    elif unit == 'in':
        return value * 72  # 1in = 72pt
    elif unit == 'cm':
        return value * 28.35  # 1cm ≈ 28.35pt
    elif unit == 'mm':
        return value * 2.835  # 1mm ≈ 2.835pt
    elif unit == 'em':
        return value * 12  # 假设1em = 12pt
    elif unit == 'rem':
        return value * 12  # 假设1rem = 12pt
    elif unit == '%':
        return None  # 百分比无法直接转换为磅
    else:
        return None


def _convert_line_height(line_height: str) -> Optional[float]:
    """将HTML行高转换为PPT行间距"""
    if not line_height:
        return None
    
    # 如果是normal，返回默认值
    if line_height == "normal":
        return 1.0
    
    # 无单位数值表示倍数
    if re.match(r'^[\d.]+$', line_height):
        return float(line_height)
    
    # 带单位的值
    size_match = re.match(r'^([\d.]+)(\w+|%)$', line_height)
    if size_match:
        value = float(size_match.group(1))
        unit = size_match.group(2)
        
        if unit == '%':
            return value / 100
        
        # 其他单位（如px、pt等）难以精确转换为行间距倍数
        return 1.0
    
    return 1.0


def _parse_border(border: str) -> Dict[str, Any]:
    """解析边框属性"""
    if not border:
        return {}
    
    result = {}
    
    # 简单边框解析（宽度 样式 颜色）
    parts = border.split()
    
    # 提取宽度
    width = None
    for part in parts:
        width_match = re.match(r'^([\d.]+)(\w+)$', part)
        if width_match:
            width = _convert_spacing(part)
            break
    
    if width is not None:
        result["border_width"] = width
        
        # 对四个边设置相同的宽度
        for side in ["top", "right", "bottom", "left"]:
            result[f"border_{side}_width"] = width
    
    # 提取颜色
    color = None
    for part in parts:
        if part.startswith('#') or part in ["black", "white", "red", "green", "blue", "yellow", "purple", "gray"]:
            color = _parse_color(part)
            break
        elif part.startswith("rgb"):
            color = _parse_color(part)
            break
    
    if color:
        result["border_color"] = color
    
    return result


def _parse_margin(margin: str) -> Dict[str, float]:
    """解析外边距属性"""
    if not margin:
        return {}
    
    result = {}
    parts = margin.split()
    
    if len(parts) == 1:
        # 四个边相同
        value = _convert_spacing(parts[0])
        if value is not None:
            for side in ["top", "right", "bottom", "left"]:
                result[f"margin_{side}"] = value
    
    elif len(parts) == 2:
        # 上下相同，左右相同
        vertical = _convert_spacing(parts[0])
        horizontal = _convert_spacing(parts[1])
        
        if vertical is not None:
            result["margin_top"] = vertical
            result["margin_bottom"] = vertical
        
        if horizontal is not None:
            result["margin_left"] = horizontal
            result["margin_right"] = horizontal
    
    elif len(parts) == 3:
        # 上、左右相同、下
        top = _convert_spacing(parts[0])
        horizontal = _convert_spacing(parts[1])
        bottom = _convert_spacing(parts[2])
        
        if top is not None:
            result["margin_top"] = top
        
        if horizontal is not None:
            result["margin_left"] = horizontal
            result["margin_right"] = horizontal
        
        if bottom is not None:
            result["margin_bottom"] = bottom
    
    elif len(parts) == 4:
        # 上、右、下、左
        top = _convert_spacing(parts[0])
        right = _convert_spacing(parts[1])
        bottom = _convert_spacing(parts[2])
        left = _convert_spacing(parts[3])
        
        if top is not None:
            result["margin_top"] = top
        
        if right is not None:
            result["margin_right"] = right
        
        if bottom is not None:
            result["margin_bottom"] = bottom
        
        if left is not None:
            result["margin_left"] = left
    
    return result


def _parse_padding(padding: str) -> Dict[str, float]:
    """解析内边距属性"""
    if not padding:
        return {}
    
    result = {}
    parts = padding.split()
    
    if len(parts) == 1:
        # 四个边相同
        value = _convert_spacing(parts[0])
        if value is not None:
            for side in ["top", "right", "bottom", "left"]:
                result[f"padding_{side}"] = value
    
    elif len(parts) == 2:
        # 上下相同，左右相同
        vertical = _convert_spacing(parts[0])
        horizontal = _convert_spacing(parts[1])
        
        if vertical is not None:
            result["padding_top"] = vertical
            result["padding_bottom"] = vertical
        
        if horizontal is not None:
            result["padding_left"] = horizontal
            result["padding_right"] = horizontal
    
    elif len(parts) == 3:
        # 上、左右相同、下
        top = _convert_spacing(parts[0])
        horizontal = _convert_spacing(parts[1])
        bottom = _convert_spacing(parts[2])
        
        if top is not None:
            result["padding_top"] = top
        
        if horizontal is not None:
            result["padding_left"] = horizontal
            result["padding_right"] = horizontal
        
        if bottom is not None:
            result["padding_bottom"] = bottom
    
    elif len(parts) == 4:
        # 上、右、下、左
        top = _convert_spacing(parts[0])
        right = _convert_spacing(parts[1])
        bottom = _convert_spacing(parts[2])
        left = _convert_spacing(parts[3])
        
        if top is not None:
            result["padding_top"] = top
        
        if right is not None:
            result["padding_right"] = right
        
        if bottom is not None:
            result["padding_bottom"] = bottom
        
        if left is not None:
            result["padding_left"] = left
    
    return result