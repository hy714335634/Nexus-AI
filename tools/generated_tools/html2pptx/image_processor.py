"""
图片处理工具，用于处理和嵌入图片资源。

此模块提供了一组工具函数，用于处理HTML中的图片、下载远程图片、
调整大小、优化质量和格式转换等操作，以便在PPT中使用。
"""

import os
import io
import json
import base64
import hashlib
import tempfile
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

import requests
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
from strands import tool


@tool
def download_image(
    image_url: str,
    output_path: str = None,
    timeout: int = 10,
    headers: Dict[str, str] = None,
    cache_dir: str = None
) -> str:
    """
    从URL下载图片到本地文件。

    Args:
        image_url (str): 图片URL
        output_path (str, optional): 输出文件路径，如果不提供则使用临时文件
        timeout (int): 下载超时时间（秒）
        headers (Dict[str, str], optional): 请求头
        cache_dir (str, optional): 缓存目录，如果提供则使用缓存
        
    Returns:
        str: JSON格式的下载结果，包含文件路径和元数据
    """
    try:
        # 检查URL格式
        parsed_url = urllib.parse.urlparse(image_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"无效的URL: {image_url}")
        
        # 设置请求头
        if not headers:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        
        # 检查缓存
        cache_path = None
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_path = os.path.join(cache_dir, f"{url_hash}.img")
            
            if os.path.exists(cache_path):
                # 使用缓存
                if output_path:
                    # 复制缓存文件到输出路径
                    with open(cache_path, 'rb') as src, open(output_path, 'wb') as dst:
                        dst.write(src.read())
                    file_path = output_path
                else:
                    file_path = cache_path
                
                # 获取文件信息
                file_size = os.path.getsize(file_path)
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_name = img.format
                
                response = {
                    "status": "success",
                    "message": "从缓存加载图片",
                    "file_path": file_path,
                    "file_size": file_size,
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "from_cache": True,
                    "original_url": image_url
                }
                
                return json.dumps(response, ensure_ascii=False)
        
        # 下载图片
        response = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        
        # 检查内容类型
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"URL不是图片: {content_type}")
        
        # 确定输出路径
        if not output_path:
            if cache_path:
                file_path = cache_path
            else:
                # 创建临时文件
                suffix = _get_extension_from_content_type(content_type)
                fd, file_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            file_path = output_path
        
        # 保存图片
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        
        # 获取图片信息
        file_size = os.path.getsize(file_path)
        with Image.open(file_path) as img:
            width, height = img.size
            format_name = img.format
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片下载成功",
            "file_path": file_path,
            "file_size": file_size,
            "width": width,
            "height": height,
            "format": format_name,
            "from_cache": False,
            "original_url": image_url
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片下载失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def resize_image(
    image_path: str,
    output_path: str = None,
    width: int = None,
    height: int = None,
    maintain_aspect_ratio: bool = True,
    resize_method: str = "lanczos",
    quality: int = 90
) -> str:
    """
    调整图片大小。

    Args:
        image_path (str): 输入图片路径
        output_path (str, optional): 输出图片路径，如果不提供则覆盖原图片
        width (int, optional): 目标宽度（像素）
        height (int, optional): 目标高度（像素）
        maintain_aspect_ratio (bool): 是否保持纵横比
        resize_method (str): 调整方法，可选值: "nearest", "box", "bilinear", "hamming", "bicubic", "lanczos"
        quality (int): JPEG压缩质量（1-100）
        
    Returns:
        str: JSON格式的处理结果
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 确定输出路径
        if not output_path:
            output_path = image_path
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # 打开图片
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            original_format = img.format
            
            # 如果没有指定宽度或高度，使用原始尺寸
            if width is None and height is None:
                width, height = original_width, original_height
            elif width is None:
                # 只指定了高度，按比例计算宽度
                width = int(original_width * (height / original_height)) if maintain_aspect_ratio else original_width
            elif height is None:
                # 只指定了宽度，按比例计算高度
                height = int(original_height * (width / original_width)) if maintain_aspect_ratio else original_height
            elif maintain_aspect_ratio:
                # 同时指定了宽度和高度，但需要保持纵横比
                width_ratio = width / original_width
                height_ratio = height / original_height
                
                # 使用较小的比例以确保图片完全适应目标尺寸
                if width_ratio < height_ratio:
                    height = int(original_height * width_ratio)
                else:
                    width = int(original_width * height_ratio)
            
            # 调整大小
            resize_methods = {
                "nearest": Image.NEAREST,
                "box": Image.BOX,
                "bilinear": Image.BILINEAR,
                "hamming": Image.HAMMING,
                "bicubic": Image.BICUBIC,
                "lanczos": Image.LANCZOS
            }
            
            resampling = resize_methods.get(resize_method.lower(), Image.LANCZOS)
            resized_img = img.resize((width, height), resampling)
            
            # 保存图片
            save_kwargs = {}
            if resized_img.format == 'JPEG' or output_path.lower().endswith(('.jpg', '.jpeg')):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif resized_img.format == 'PNG' or output_path.lower().endswith('.png'):
                save_kwargs['optimize'] = True
            
            resized_img.save(output_path, **save_kwargs)
        
        # 获取输出文件信息
        file_size = os.path.getsize(output_path)
        with Image.open(output_path) as img:
            final_width, final_height = img.size
            final_format = img.format
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片大小调整成功",
            "file_path": output_path,
            "file_size": file_size,
            "original_dimensions": {
                "width": original_width,
                "height": original_height,
                "format": original_format
            },
            "new_dimensions": {
                "width": final_width,
                "height": final_height,
                "format": final_format
            },
            "resize_method": resize_method
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片大小调整失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def optimize_image(
    image_path: str,
    output_path: str = None,
    quality: int = 85,
    format_conversion: str = None,
    max_size_kb: int = None
) -> str:
    """
    优化图片大小和质量。

    Args:
        image_path (str): 输入图片路径
        output_path (str, optional): 输出图片路径，如果不提供则覆盖原图片
        quality (int): 压缩质量（1-100）
        format_conversion (str, optional): 转换格式，可选值: "jpeg", "png", "webp"
        max_size_kb (int, optional): 最大文件大小（KB），如果指定则自动调整质量以达到目标大小
        
    Returns:
        str: JSON格式的处理结果
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 确定输出路径
        if not output_path:
            output_path = image_path
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # 打开图片
        with Image.open(image_path) as img:
            original_format = img.format
            original_size = os.path.getsize(image_path)
            
            # 确定输出格式
            if format_conversion:
                output_format = format_conversion.upper()
            else:
                output_format = original_format
            
            # 如果需要转换为JPEG，确保图片有RGB模式
            if output_format == 'JPEG' and img.mode in ('RGBA', 'LA'):
                # 将透明背景转换为白色
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                else:
                    background.paste(img, mask=img.split()[1])  # 1 is the alpha channel
                img = background
            
            # 优化图片
            if max_size_kb:
                # 自动调整质量以达到目标大小
                max_bytes = max_size_kb * 1024
                
                # 使用二分查找找到合适的质量
                min_quality = 5
                max_quality = 95
                current_quality = quality
                best_quality = current_quality
                best_size = float('inf')
                
                # 最多尝试8次
                for _ in range(8):
                    # 保存到内存中以检查大小
                    buffer = io.BytesIO()
                    save_kwargs = {'format': output_format}
                    
                    if output_format in ('JPEG', 'WEBP'):
                        save_kwargs['quality'] = current_quality
                        save_kwargs['optimize'] = True
                    elif output_format == 'PNG':
                        save_kwargs['optimize'] = True
                    
                    img.save(buffer, **save_kwargs)
                    current_size = buffer.tell()
                    
                    # 更新最佳质量
                    if current_size <= max_bytes and current_quality > best_quality:
                        best_quality = current_quality
                        best_size = current_size
                    
                    # 调整质量
                    if current_size > max_bytes:
                        max_quality = current_quality - 1
                    else:
                        min_quality = current_quality + 1
                    
                    # 计算新的质量值
                    current_quality = (min_quality + max_quality) // 2
                    
                    # 如果范围收敛，退出循环
                    if min_quality > max_quality:
                        break
                
                # 使用找到的最佳质量保存图片
                quality = best_quality
            
            # 保存优化后的图片
            save_kwargs = {'format': output_format}
            
            if output_format in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif output_format == 'PNG':
                save_kwargs['optimize'] = True
            
            img.save(output_path, **save_kwargs)
        
        # 获取输出文件信息
        optimized_size = os.path.getsize(output_path)
        size_reduction = original_size - optimized_size
        size_reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片优化成功",
            "file_path": output_path,
            "original_size": original_size,
            "optimized_size": optimized_size,
            "size_reduction": size_reduction,
            "size_reduction_percent": round(size_reduction_percent, 2),
            "original_format": original_format,
            "output_format": output_format,
            "quality": quality
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片优化失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def crop_image(
    image_path: str,
    output_path: str = None,
    left: int = None,
    top: int = None,
    right: int = None,
    bottom: int = None,
    width: int = None,
    height: int = None,
    center_crop: bool = False
) -> str:
    """
    裁剪图片。

    Args:
        image_path (str): 输入图片路径
        output_path (str, optional): 输出图片路径，如果不提供则覆盖原图片
        left (int, optional): 左边界坐标
        top (int, optional): 上边界坐标
        right (int, optional): 右边界坐标
        bottom (int, optional): 下边界坐标
        width (int, optional): 裁剪宽度，与right互斥
        height (int, optional): 裁剪高度，与bottom互斥
        center_crop (bool): 是否从中心裁剪
        
    Returns:
        str: JSON格式的处理结果
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 确定输出路径
        if not output_path:
            output_path = image_path
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # 打开图片
        with Image.open(image_path) as img:
            original_width, original_height = img.size
            
            # 确定裁剪区域
            if center_crop:
                # 从中心裁剪
                if width is None or height is None:
                    raise ValueError("使用center_crop时必须指定width和height")
                
                center_x = original_width // 2
                center_y = original_height // 2
                
                left = center_x - (width // 2)
                top = center_y - (height // 2)
                right = left + width
                bottom = top + height
            else:
                # 使用指定的坐标
                if left is None:
                    left = 0
                if top is None:
                    top = 0
                
                # 处理width/height和right/bottom的关系
                if width is not None:
                    right = left + width
                elif right is None:
                    right = original_width
                
                if height is not None:
                    bottom = top + height
                elif bottom is None:
                    bottom = original_height
            
            # 确保坐标在图片范围内
            left = max(0, left)
            top = max(0, top)
            right = min(original_width, right)
            bottom = min(original_height, bottom)
            
            # 裁剪图片
            cropped_img = img.crop((left, top, right, bottom))
            
            # 保存裁剪后的图片
            cropped_img.save(output_path)
        
        # 获取输出文件信息
        file_size = os.path.getsize(output_path)
        with Image.open(output_path) as img:
            cropped_width, cropped_height = img.size
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片裁剪成功",
            "file_path": output_path,
            "file_size": file_size,
            "original_dimensions": {
                "width": original_width,
                "height": original_height
            },
            "cropped_dimensions": {
                "width": cropped_width,
                "height": cropped_height
            },
            "crop_coordinates": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom
            }
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片裁剪失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def convert_image_format(
    image_path: str,
    output_format: str,
    output_path: str = None,
    quality: int = 90
) -> str:
    """
    转换图片格式。

    Args:
        image_path (str): 输入图片路径
        output_format (str): 输出格式，可选值: "jpeg", "png", "webp", "gif", "bmp", "tiff"
        output_path (str, optional): 输出图片路径，如果不提供则自动生成
        quality (int): 压缩质量（1-100），仅对JPEG和WebP有效
        
    Returns:
        str: JSON格式的处理结果
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 检查输出格式
        output_format = output_format.lower()
        supported_formats = {
            "jpeg": "JPEG",
            "jpg": "JPEG",
            "png": "PNG",
            "webp": "WEBP",
            "gif": "GIF",
            "bmp": "BMP",
            "tiff": "TIFF"
        }
        
        if output_format not in supported_formats:
            raise ValueError(f"不支持的输出格式: {output_format}，支持的格式: {', '.join(supported_formats.keys())}")
        
        pil_format = supported_formats[output_format]
        
        # 确定输出路径
        if not output_path:
            # 自动生成输出路径
            base_name = os.path.splitext(image_path)[0]
            output_path = f"{base_name}.{output_format}"
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # 打开图片
        with Image.open(image_path) as img:
            original_format = img.format
            original_size = os.path.getsize(image_path)
            
            # 如果需要转换为JPEG，确保图片有RGB模式
            if pil_format == 'JPEG' and img.mode in ('RGBA', 'LA'):
                # 将透明背景转换为白色
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                else:
                    background.paste(img, mask=img.split()[1])  # 1 is the alpha channel
                img = background
            
            # 保存转换后的图片
            save_kwargs = {'format': pil_format}
            
            if pil_format in ('JPEG', 'WEBP'):
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif pil_format == 'PNG':
                save_kwargs['optimize'] = True
            
            img.save(output_path, **save_kwargs)
        
        # 获取输出文件信息
        converted_size = os.path.getsize(output_path)
        with Image.open(output_path) as img:
            width, height = img.size
            final_format = img.format
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片格式转换成功",
            "file_path": output_path,
            "file_size": converted_size,
            "original_format": original_format,
            "original_size": original_size,
            "converted_format": final_format,
            "converted_size": converted_size,
            "dimensions": {
                "width": width,
                "height": height
            }
        }
        
        return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片格式转换失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def get_image_info(
    image_path: str,
    include_exif: bool = False,
    include_base64: bool = False,
    base64_max_size_kb: int = 1024
) -> str:
    """
    获取图片的详细信息。

    Args:
        image_path (str): 图片文件路径
        include_exif (bool): 是否包含EXIF元数据
        include_base64 (bool): 是否包含Base64编码的图片数据
        base64_max_size_kb (int): 如果包含Base64数据，文件大小上限（KB）
        
    Returns:
        str: JSON格式的图片信息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 获取文件基本信息
        file_size = os.path.getsize(image_path)
        file_name = os.path.basename(image_path)
        file_extension = os.path.splitext(file_name)[1].lower()
        
        # 打开图片
        with Image.open(image_path) as img:
            # 基本信息
            info = {
                "file_name": file_name,
                "file_path": os.path.abspath(image_path),
                "file_size": file_size,
                "file_size_kb": round(file_size / 1024, 2),
                "dimensions": {
                    "width": img.width,
                    "height": img.height,
                    "aspect_ratio": round(img.width / img.height, 4) if img.height > 0 else 0
                },
                "format": img.format,
                "mode": img.mode,
                "animation": hasattr(img, 'is_animated') and img.is_animated,
                "frames": getattr(img, 'n_frames', 1)
            }
            
            # EXIF数据
            if include_exif and hasattr(img, '_getexif') and img._getexif():
                exif_data = {}
                for tag_id, value in img._getexif().items():
                    tag_name = _get_exif_tag_name(tag_id)
                    if isinstance(value, bytes):
                        # 跳过二进制数据
                        continue
                    exif_data[tag_name] = str(value)
                
                info["exif"] = exif_data
            
            # Base64编码
            if include_base64 and file_size <= base64_max_size_kb * 1024:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    mime_type = _get_mime_type(file_extension)
                    info["base64"] = f"data:{mime_type};base64,{base64_data}"
            elif include_base64:
                info["base64_skipped"] = f"图片大小 ({round(file_size / 1024, 2)} KB) 超过了限制 ({base64_max_size_kb} KB)"
        
        return json.dumps(info, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "获取图片信息失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


@tool
def enhance_image(
    image_path: str,
    output_path: str = None,
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0,
    color: float = 1.0,
    apply_filter: str = None
) -> str:
    """
    增强图片质量。

    Args:
        image_path (str): 输入图片路径
        output_path (str, optional): 输出图片路径，如果不提供则覆盖原图片
        brightness (float): 亮度调整因子，1.0为原始亮度，大于1增加亮度，小于1降低亮度
        contrast (float): 对比度调整因子，1.0为原始对比度
        sharpness (float): 锐度调整因子，1.0为原始锐度
        color (float): 色彩饱和度调整因子，1.0为原始饱和度
        apply_filter (str, optional): 应用滤镜，可选值: "blur", "contour", "edge_enhance", "emboss", "sharpen", "smooth"
        
    Returns:
        str: JSON格式的处理结果
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        
        # 确定输出路径
        if not output_path:
            output_path = image_path
        else:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
        
        # 打开图片
        with Image.open(image_path) as img:
            original_format = img.format
            enhanced_img = img.copy()
            
            # 应用增强
            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(enhanced_img)
                enhanced_img = enhancer.enhance(brightness)
            
            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(enhanced_img)
                enhanced_img = enhancer.enhance(contrast)
            
            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(enhanced_img)
                enhanced_img = enhancer.enhance(sharpness)
            
            if color != 1.0:
                enhancer = ImageEnhance.Color(enhanced_img)
                enhanced_img = enhancer.enhance(color)
            
            # 应用滤镜
            if apply_filter:
                filters = {
                    "blur": ImageFilter.BLUR,
                    "contour": ImageFilter.CONTOUR,
                    "edge_enhance": ImageFilter.EDGE_ENHANCE,
                    "emboss": ImageFilter.EMBOSS,
                    "sharpen": ImageFilter.SHARPEN,
                    "smooth": ImageFilter.SMOOTH
                }
                
                if apply_filter.lower() in filters:
                    enhanced_img = enhanced_img.filter(filters[apply_filter.lower()])
                else:
                    raise ValueError(f"不支持的滤镜: {apply_filter}，支持的滤镜: {', '.join(filters.keys())}")
            
            # 保存增强后的图片
            save_kwargs = {}
            if enhanced_img.format == 'JPEG' or output_path.lower().endswith(('.jpg', '.jpeg')):
                save_kwargs['quality'] = 95
                save_kwargs['optimize'] = True
            elif enhanced_img.format == 'PNG' or output_path.lower().endswith('.png'):
                save_kwargs['optimize'] = True
            
            enhanced_img.save(output_path, format=original_format, **save_kwargs)
        
        # 获取输出文件信息
        file_size = os.path.getsize(output_path)
        
        # 构建响应
        result = {
            "status": "success",
            "message": "图片增强成功",
            "file_path": output_path,
            "file_size": file_size,
            "enhancements": {
                "brightness": brightness,
                "contrast": contrast,
                "sharpness": sharpness,
                "color": color,
                "filter": apply_filter
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "failed",
            "error": str(e),
            "message": "图片增强失败"
        }
        return json.dumps(error_response, ensure_ascii=False)


# 辅助函数

def _get_extension_from_content_type(content_type: str) -> str:
    """根据Content-Type获取文件扩展名"""
    content_type = content_type.lower()
    if content_type == 'image/jpeg':
        return '.jpg'
    elif content_type == 'image/png':
        return '.png'
    elif content_type == 'image/gif':
        return '.gif'
    elif content_type == 'image/webp':
        return '.webp'
    elif content_type == 'image/svg+xml':
        return '.svg'
    elif content_type == 'image/bmp':
        return '.bmp'
    elif content_type == 'image/tiff':
        return '.tiff'
    else:
        return '.img'


def _get_mime_type(extension: str) -> str:
    """根据文件扩展名获取MIME类型"""
    extension = extension.lower()
    if extension in ('.jpg', '.jpeg'):
        return 'image/jpeg'
    elif extension == '.png':
        return 'image/png'
    elif extension == '.gif':
        return 'image/gif'
    elif extension == '.webp':
        return 'image/webp'
    elif extension == '.svg':
        return 'image/svg+xml'
    elif extension == '.bmp':
        return 'image/bmp'
    elif extension in ('.tiff', '.tif'):
        return 'image/tiff'
    else:
        return 'application/octet-stream'


def _get_exif_tag_name(tag: int) -> str:
    """获取EXIF标签名称"""
    exif_tags = {
        0x010E: "ImageDescription",
        0x010F: "Make",
        0x0110: "Model",
        0x0112: "Orientation",
        0x0131: "Software",
        0x0132: "DateTime",
        0x013B: "Artist",
        0x8298: "Copyright",
        0x8769: "ExifOffset",
        0x8825: "GPSInfo",
        0x9000: "ExifVersion",
        0x9003: "DateTimeOriginal",
        0x9004: "DateTimeDigitized",
        0x9201: "ShutterSpeedValue",
        0x9202: "ApertureValue",
        0x9203: "BrightnessValue",
        0x9204: "ExposureBiasValue",
        0x9205: "MaxApertureValue",
        0x9206: "SubjectDistance",
        0x9207: "MeteringMode",
        0x9208: "LightSource",
        0x9209: "Flash",
        0x920A: "FocalLength",
        0x927C: "MakerNote",
        0x9286: "UserComment",
        0xA000: "FlashPixVersion",
        0xA001: "ColorSpace",
        0xA002: "ExifImageWidth",
        0xA003: "ExifImageHeight",
        0xA004: "RelatedSoundFile",
        0xA005: "ExifInteroperabilityOffset",
        0xA20E: "FocalPlaneXResolution",
        0xA20F: "FocalPlaneYResolution",
        0xA210: "FocalPlaneResolutionUnit",
        0xA217: "SensingMethod",
        0xA300: "FileSource",
        0xA301: "SceneType",
        0xA302: "CFAPattern"
    }
    
    return exif_tags.get(tag, f"Tag_{tag:04X}")