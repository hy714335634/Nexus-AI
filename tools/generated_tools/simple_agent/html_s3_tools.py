"""
HTML文档生成与S3上传工具集

该模块提供了HTML文档生成、S3上传、预签名URL生成等核心功能。
所有工具函数使用@tool装饰器定义，符合Strands SDK规范。

Author: Nexus-AI Tools Developer
Created: 2026-01-24
Project: simple_agent
"""

import json
import uuid
import re
import boto3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from strands import tool


@tool
def validate_input(
    prompt: str,
    expiration: Optional[int] = None
) -> str:
    """
    验证用户输入的有效性
    
    该工具检查用户提供的文档内容和可选参数是否符合要求，
    包括内容长度、过期时间范围等验证。
    
    Args:
        prompt: 用户的文档需求描述
        expiration: URL过期时间（秒），可选
        
    Returns:
        str: JSON格式的验证结果，包含：
            - is_valid: 是否有效
            - errors: 错误列表
            - warnings: 警告列表
            - sanitized_prompt: 清理后的prompt
            - sanitized_expiration: 标准化的过期时间
            
    Example:
        >>> result = validate_input("生成一个简单的HTML页面", 3600)
        >>> data = json.loads(result)
        >>> print(data['is_valid'])  # True
    """
    try:
        errors = []
        warnings = []
        
        # 验证prompt
        if not prompt or not prompt.strip():
            errors.append("文档内容不能为空")
        
        sanitized_prompt = prompt.strip() if prompt else ""
        
        # 检查prompt长度
        if len(sanitized_prompt) > 50000:
            errors.append("文档内容过长（最大50000字符）")
        elif len(sanitized_prompt) < 10:
            warnings.append("文档内容过短，可能无法生成有意义的HTML")
        
        # 验证expiration
        sanitized_expiration = 3600  # 默认1小时
        if expiration is not None:
            if not isinstance(expiration, int):
                errors.append("过期时间必须是整数")
            elif expiration < 60:
                errors.append("过期时间不能少于60秒（1分钟）")
            elif expiration > 604800:
                errors.append("过期时间不能超过604800秒（7天）")
            else:
                sanitized_expiration = expiration
        
        # 检查是否包含可疑内容
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sanitized_prompt, re.IGNORECASE | re.DOTALL):
                warnings.append("检测到可能的脚本内容，生成的HTML将进行安全处理")
                break
        
        is_valid = len(errors) == 0
        
        return json.dumps({
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "sanitized_prompt": sanitized_prompt,
            "sanitized_expiration": sanitized_expiration,
            "validation_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "is_valid": False,
            "errors": [f"验证过程异常: {str(e)}"],
            "warnings": [],
            "sanitized_prompt": "",
            "sanitized_expiration": 3600
        }, ensure_ascii=False, indent=2)


@tool
def generate_html_document(
    content_description: str,
    style_requirements: Optional[str] = None,
    include_responsive: bool = True
) -> str:
    """
    使用AI模型生成HTML文档
    
    该工具接收用户的文档内容描述和样式要求，生成符合HTML5标准的
    完整HTML文档。生成的HTML包含完整的文档结构、样式和内容。
    
    Args:
        content_description: 文档内容描述
        style_requirements: 样式要求（可选），如颜色、字体、布局等
        include_responsive: 是否包含响应式设计，默认True
        
    Returns:
        str: JSON格式的生成结果，包含：
            - success: 是否成功
            - html_content: 生成的HTML内容
            - html_size: HTML大小（字节）
            - generation_time: 生成耗时（秒）
            - metadata: 生成元数据
            
    Example:
        >>> result = generate_html_document(
        ...     content_description="创建一个产品介绍页面",
        ...     style_requirements="使用蓝色主题，现代化设计"
        ... )
        >>> data = json.loads(result)
        >>> print(data['success'])  # True
    """
    try:
        start_time = datetime.now()
        
        # 构建HTML生成提示词
        system_prompt = """你是一个专业的HTML文档生成专家。请根据用户的需求生成高质量的HTML5文档。

要求：
1. 生成完整的HTML5文档，包含<!DOCTYPE html>、<html>、<head>和<body>标签
2. 在<head>中包含必要的meta标签（charset、viewport等）
3. 使用语义化HTML标签（header、section、article、footer等）
4. 使用内联CSS或<style>标签实现样式
5. 确保HTML结构清晰、格式规范
6. 如果需要响应式设计，包含适当的媒体查询
7. 不要包含外部依赖（外部CSS、JS文件等）
8. 确保生成的HTML可以直接在浏览器中打开使用

请直接返回完整的HTML代码，不要添加任何解释或markdown格式。"""

        user_message = f"内容要求：{content_description}"
        if style_requirements:
            user_message += f"\n\n样式要求：{style_requirements}"
        if include_responsive:
            user_message += "\n\n请确保HTML支持响应式设计，能够在不同设备上正常显示。"
        
        # 使用boto3调用Bedrock生成HTML
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100000,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "system": system_prompt,
            "temperature": 0.7
        }
        
        response = bedrock_runtime.invoke_model(
            modelId="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        html_content = response_body['content'][0]['text']
        
        # 验证生成的HTML
        if not html_content or len(html_content) < 100:
            return json.dumps({
                "success": False,
                "error": "生成的HTML内容过短或为空",
                "hint": "请提供更详细的内容描述"
            }, ensure_ascii=False, indent=2)
        
        # 检查是否包含基本HTML结构
        if '<!DOCTYPE' not in html_content and '<html' not in html_content:
            return json.dumps({
                "success": False,
                "error": "生成的内容不是有效的HTML文档",
                "hint": "请重新生成或检查内容描述"
            }, ensure_ascii=False, indent=2)
        
        end_time = datetime.now()
        generation_time = (end_time - start_time).total_seconds()
        
        return json.dumps({
            "success": True,
            "html_content": html_content,
            "html_size": len(html_content.encode('utf-8')),
            "generation_time": round(generation_time, 2),
            "metadata": {
                "model": "claude-sonnet-4.5",
                "include_responsive": include_responsive,
                "has_style_requirements": bool(style_requirements),
                "generated_at": end_time.isoformat()
            }
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"Bedrock API调用失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code'],
            "hint": "请检查AWS凭证和Bedrock服务配置"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"HTML生成异常: {str(e)}",
            "hint": "请检查输入内容或稍后重试"
        }, ensure_ascii=False, indent=2)


@tool
def upload_to_s3(
    html_content: str,
    bucket_name: str = "awesome-nexus-ai-file-storage",
    object_key: Optional[str] = None,
    content_type: str = "text/html; charset=utf-8",
    region: str = "us-west-2",
    max_retries: int = 3
) -> str:
    """
    上传HTML内容至AWS S3存储桶
    
    该工具将HTML字符串内容上传至指定的S3存储桶，支持自动重试和
    详细的错误处理。如果未指定对象键，将自动生成UUID文件名。
    
    Args:
        html_content: HTML文档内容
        bucket_name: S3存储桶名称，默认为awesome-nexus-ai-file-storage
        object_key: S3对象键（文件路径），如果不提供则自动生成UUID
        content_type: 内容类型，默认为text/html; charset=utf-8
        region: AWS区域，默认为us-west-2
        max_retries: 最大重试次数，默认为3
        
    Returns:
        str: JSON格式的上传结果，包含：
            - success: 是否成功
            - bucket: S3存储桶名称
            - key: 对象键
            - s3_uri: S3 URI
            - file_size: 文件大小（字节）
            - content_type: 内容类型
            - retry_count: 重试次数
            - upload_time: 上传耗时（秒）
            - timestamp: 上传时间
            
    Example:
        >>> result = upload_to_s3(
        ...     html_content="<html>...</html>",
        ...     bucket_name="awesome-nexus-ai-file-storage"
        ... )
        >>> data = json.loads(result)
        >>> print(data['key'])  # "abc-123-def.html"
    """
    try:
        # 生成对象键（如果未提供）
        if not object_key:
            unique_id = str(uuid.uuid4())
            object_key = f"{unique_id}.html"
        
        # 验证HTML内容
        if not html_content:
            return json.dumps({
                "success": False,
                "error": "HTML内容不能为空"
            }, ensure_ascii=False, indent=2)
        
        # 检查文件大小
        html_bytes = html_content.encode('utf-8')
        file_size = len(html_bytes)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return json.dumps({
                "success": False,
                "error": f"HTML文件过大（{file_size / 1024 / 1024:.2f}MB），最大支持10MB"
            }, ensure_ascii=False, indent=2)
        
        start_time = datetime.now()
        
        # 创建S3客户端
        s3_client = boto3.client('s3', region_name=region)
        
        # 重试上传
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # 上传文件
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=object_key,
                    Body=html_bytes,
                    ContentType=content_type,
                    Metadata={
                        'generated_by': 'simple_agent',
                        'created_at': datetime.now().isoformat()
                    }
                )
                
                # 上传成功
                end_time = datetime.now()
                upload_time = (end_time - start_time).total_seconds()
                
                return json.dumps({
                    "success": True,
                    "bucket": bucket_name,
                    "key": object_key,
                    "s3_uri": f"s3://{bucket_name}/{object_key}",
                    "file_size": file_size,
                    "content_type": content_type,
                    "retry_count": retry_count,
                    "upload_time": round(upload_time, 2),
                    "timestamp": end_time.isoformat()
                }, ensure_ascii=False, indent=2)
                
            except ClientError as e:
                last_error = e
                retry_count += 1
                
                # 如果是权限错误或存储桶不存在，不重试
                error_code = e.response['Error']['Code']
                if error_code in ['AccessDenied', 'NoSuchBucket', 'InvalidAccessKeyId']:
                    break
                
                # 其他错误继续重试
                if retry_count < max_retries:
                    continue
        
        # 重试失败
        if last_error:
            error_code = last_error.response['Error']['Code']
            error_message = last_error.response['Error']['Message']
            
            # 根据错误类型提供具体建议
            if error_code == 'NoSuchBucket':
                hint = f"S3存储桶'{bucket_name}'不存在，请检查存储桶名称或联系管理员"
            elif error_code == 'AccessDenied':
                hint = "AWS凭证无权限访问S3存储桶，请检查IAM权限配置"
            elif error_code == 'InvalidAccessKeyId':
                hint = "AWS凭证无效，请检查环境变量或IAM角色配置"
            else:
                hint = "请检查网络连接和S3配置，或稍后重试"
            
            return json.dumps({
                "success": False,
                "error": f"S3上传失败（重试{retry_count}次）: {error_message}",
                "error_code": error_code,
                "hint": hint,
                "retry_count": retry_count
            }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": False,
            "error": "S3上传失败：未知错误",
            "retry_count": retry_count
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"S3上传异常: {str(e)}",
            "hint": "请检查系统配置或联系管理员"
        }, ensure_ascii=False, indent=2)


@tool
def generate_presigned_url(
    bucket_name: str,
    object_key: str,
    expiration: int = 3600,
    region: str = "us-west-2"
) -> str:
    """
    生成S3对象的预签名URL
    
    该工具为已上传的S3对象生成临时访问URL，允许用户在指定时间内
    无需AWS凭证即可访问文件。
    
    Args:
        bucket_name: S3存储桶名称
        object_key: S3对象键（文件路径）
        expiration: URL有效期（秒），默认3600秒（1小时）
        region: AWS区域，默认为us-west-2
        
    Returns:
        str: JSON格式的预签名URL结果，包含：
            - success: 是否成功
            - presigned_url: 预签名URL
            - s3_uri: S3 URI
            - bucket: 存储桶名称
            - key: 对象键
            - expiration_seconds: 过期时间（秒）
            - expiration_hours: 过期时间（小时）
            - expires_at: 过期时间戳
            - region: AWS区域
            - timestamp: 生成时间
            
    Example:
        >>> result = generate_presigned_url(
        ...     bucket_name="awesome-nexus-ai-file-storage",
        ...     object_key="abc-123.html",
        ...     expiration=3600
        ... )
        >>> data = json.loads(result)
        >>> print(data['presigned_url'])
    """
    try:
        # 验证参数
        if not bucket_name:
            return json.dumps({
                "success": False,
                "error": "存储桶名称不能为空"
            }, ensure_ascii=False, indent=2)
        
        if not object_key:
            return json.dumps({
                "success": False,
                "error": "对象键不能为空"
            }, ensure_ascii=False, indent=2)
        
        if expiration < 60 or expiration > 604800:
            return json.dumps({
                "success": False,
                "error": "过期时间必须在60秒到604800秒（7天）之间"
            }, ensure_ascii=False, indent=2)
        
        # 创建S3客户端
        s3_client = boto3.client('s3', region_name=region)
        
        # 生成预签名URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        
        # 计算过期时间
        expires_at = datetime.now() + timedelta(seconds=expiration)
        
        return json.dumps({
            "success": True,
            "presigned_url": presigned_url,
            "s3_uri": f"s3://{bucket_name}/{object_key}",
            "bucket": bucket_name,
            "key": object_key,
            "expiration_seconds": expiration,
            "expiration_hours": round(expiration / 3600, 2),
            "expires_at": expires_at.isoformat(),
            "region": region,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        # 根据错误类型提供具体建议
        if error_code == 'NoSuchBucket':
            hint = f"S3存储桶'{bucket_name}'不存在"
        elif error_code == 'NoSuchKey':
            hint = f"对象'{object_key}'不存在于存储桶中，请先上传文件"
        elif error_code == 'AccessDenied':
            hint = "无权限生成预签名URL，请检查IAM权限配置"
        else:
            hint = "请检查S3配置或联系管理员"
        
        return json.dumps({
            "success": False,
            "error": f"预签名URL生成失败: {error_message}",
            "error_code": error_code,
            "hint": hint,
            "bucket": bucket_name,
            "key": object_key
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"预签名URL生成异常: {str(e)}",
            "hint": "请检查系统配置或联系管理员"
        }, ensure_ascii=False, indent=2)


@tool
def format_error_message(
    error_type: str,
    error_details: str,
    include_hint: bool = True
) -> str:
    """
    格式化友好的错误信息
    
    该工具将技术性错误信息转换为用户友好的错误提示，并提供
    可能的解决建议。
    
    Args:
        error_type: 错误类型，可选值：
            - validation: 输入验证错误
            - generation: HTML生成错误
            - upload: S3上传错误
            - url_generation: URL生成错误
            - network: 网络错误
            - permission: 权限错误
            - unknown: 未知错误
        error_details: 错误详细信息
        include_hint: 是否包含解决建议，默认True
        
    Returns:
        str: 格式化的错误信息字符串
            
    Example:
        >>> message = format_error_message(
        ...     error_type="upload",
        ...     error_details="NoSuchBucket: The specified bucket does not exist"
        ... )
        >>> print(message)  # "Error: 文件上传失败 - S3存储桶不存在，请联系管理员"
    """
    try:
        # 错误类型映射
        error_type_map = {
            "validation": "输入验证失败",
            "generation": "HTML文档生成失败",
            "upload": "文件上传失败",
            "url_generation": "预签名URL生成失败",
            "network": "网络连接失败",
            "permission": "权限验证失败",
            "unknown": "系统错误"
        }
        
        # 获取错误描述
        error_description = error_type_map.get(error_type, "系统错误")
        
        # 生成解决建议
        hints = {
            "validation": "请检查输入内容是否完整且符合要求",
            "generation": "请检查内容描述是否清晰，或稍后重试",
            "upload": "请检查网络连接和S3配置，或稍后重试",
            "url_generation": "请检查S3对象是否存在，或联系管理员",
            "network": "请检查网络连接后重试",
            "permission": "请检查IAM权限配置，或联系管理员",
            "unknown": "请稍后重试，如果问题持续请联系管理员"
        }
        
        hint = hints.get(error_type, "请联系管理员")
        
        # 构建错误信息
        if include_hint:
            formatted_message = f"Error: {error_description} - {hint}"
        else:
            formatted_message = f"Error: {error_description}"
        
        # 如果有详细错误信息，添加到结果中
        if error_details:
            formatted_message += f"\n详细信息: {error_details}"
        
        return formatted_message
        
    except Exception as e:
        return f"Error: 系统错误 - {str(e)}"


@tool
def validate_html_content(
    html_content: str,
    check_structure: bool = True,
    check_size: bool = True,
    max_size_mb: float = 10.0
) -> str:
    """
    验证HTML内容的完整性和有效性
    
    该工具检查生成的HTML内容是否符合基本要求，包括结构完整性、
    文件大小等。
    
    Args:
        html_content: HTML文档内容
        check_structure: 是否检查HTML结构，默认True
        check_size: 是否检查文件大小，默认True
        max_size_mb: 最大文件大小（MB），默认10MB
        
    Returns:
        str: JSON格式的验证结果，包含：
            - is_valid: 是否有效
            - errors: 错误列表
            - warnings: 警告列表
            - html_size: HTML大小（字节）
            - has_doctype: 是否包含DOCTYPE
            - has_html_tag: 是否包含html标签
            - has_head_tag: 是否包含head标签
            - has_body_tag: 是否包含body标签
            
    Example:
        >>> result = validate_html_content("<html><head></head><body>test</body></html>")
        >>> data = json.loads(result)
        >>> print(data['is_valid'])  # True
    """
    try:
        errors = []
        warnings = []
        
        # 检查内容是否为空
        if not html_content:
            errors.append("HTML内容为空")
            return json.dumps({
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "html_size": 0
            }, ensure_ascii=False, indent=2)
        
        # 计算文件大小
        html_bytes = html_content.encode('utf-8')
        html_size = len(html_bytes)
        
        # 检查文件大小
        if check_size:
            max_size_bytes = max_size_mb * 1024 * 1024
            if html_size > max_size_bytes:
                errors.append(f"HTML文件过大（{html_size / 1024 / 1024:.2f}MB），最大支持{max_size_mb}MB")
            elif html_size < 50:
                warnings.append("HTML文件过小，可能内容不完整")
        
        # 检查HTML结构
        has_doctype = False
        has_html_tag = False
        has_head_tag = False
        has_body_tag = False
        
        if check_structure:
            html_lower = html_content.lower()
            
            has_doctype = '<!doctype' in html_lower
            has_html_tag = '<html' in html_lower
            has_head_tag = '<head' in html_lower
            has_body_tag = '<body' in html_lower
            
            if not has_doctype:
                warnings.append("缺少DOCTYPE声明")
            if not has_html_tag:
                errors.append("缺少<html>标签")
            if not has_head_tag:
                warnings.append("缺少<head>标签")
            if not has_body_tag:
                errors.append("缺少<body>标签")
        
        is_valid = len(errors) == 0
        
        return json.dumps({
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "html_size": html_size,
            "html_size_mb": round(html_size / 1024 / 1024, 2),
            "has_doctype": has_doctype,
            "has_html_tag": has_html_tag,
            "has_head_tag": has_head_tag,
            "has_body_tag": has_body_tag,
            "validation_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "is_valid": False,
            "errors": [f"验证过程异常: {str(e)}"],
            "warnings": [],
            "html_size": 0
        }, ensure_ascii=False, indent=2)


@tool
def check_s3_bucket_access(
    bucket_name: str = "awesome-nexus-ai-file-storage",
    region: str = "us-west-2"
) -> str:
    """
    检查S3存储桶访问权限
    
    该工具验证Agent是否有权限访问指定的S3存储桶，包括读取和写入权限。
    
    Args:
        bucket_name: S3存储桶名称，默认为awesome-nexus-ai-file-storage
        region: AWS区域，默认为us-west-2
        
    Returns:
        str: JSON格式的检查结果，包含：
            - accessible: 是否可访问
            - bucket_exists: 存储桶是否存在
            - can_upload: 是否有上传权限
            - can_read: 是否有读取权限
            - bucket_region: 存储桶所在区域
            - error: 错误信息（如果有）
            
    Example:
        >>> result = check_s3_bucket_access("awesome-nexus-ai-file-storage")
        >>> data = json.loads(result)
        >>> print(data['accessible'])  # True or False
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # 检查存储桶是否存在
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            bucket_exists = True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return json.dumps({
                    "accessible": False,
                    "bucket_exists": False,
                    "can_upload": False,
                    "can_read": False,
                    "error": f"S3存储桶'{bucket_name}'不存在"
                }, ensure_ascii=False, indent=2)
            elif error_code == '403':
                return json.dumps({
                    "accessible": False,
                    "bucket_exists": True,
                    "can_upload": False,
                    "can_read": False,
                    "error": f"无权限访问S3存储桶'{bucket_name}'"
                }, ensure_ascii=False, indent=2)
            else:
                raise
        
        # 获取存储桶位置
        try:
            location_response = s3_client.get_bucket_location(Bucket=bucket_name)
            bucket_region = location_response.get('LocationConstraint') or 'us-east-1'
        except:
            bucket_region = "unknown"
        
        # 测试上传权限（使用临时测试文件）
        test_key = f"_test_access_{uuid.uuid4()}.txt"
        can_upload = False
        
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=b"test",
                ContentType="text/plain"
            )
            can_upload = True
            
            # 清理测试文件
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            except:
                pass
        except ClientError:
            can_upload = False
        
        # 测试读取权限
        can_read = False
        try:
            s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            can_read = True
        except ClientError:
            can_read = False
        
        accessible = bucket_exists and can_upload and can_read
        
        return json.dumps({
            "accessible": accessible,
            "bucket_exists": bucket_exists,
            "can_upload": can_upload,
            "can_read": can_read,
            "bucket_name": bucket_name,
            "bucket_region": bucket_region,
            "check_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "accessible": False,
            "bucket_exists": False,
            "can_upload": False,
            "can_read": False,
            "error": f"检查S3访问权限异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def get_s3_object_info(
    bucket_name: str,
    object_key: str,
    region: str = "us-west-2"
) -> str:
    """
    获取S3对象的详细信息
    
    该工具查询已上传的S3对象的元数据和属性信息。
    
    Args:
        bucket_name: S3存储桶名称
        object_key: S3对象键
        region: AWS区域，默认为us-west-2
        
    Returns:
        str: JSON格式的对象信息，包含：
            - success: 是否成功
            - object_exists: 对象是否存在
            - size: 文件大小（字节）
            - content_type: 内容类型
            - last_modified: 最后修改时间
            - metadata: 自定义元数据
            - storage_class: 存储类别
            - etag: ETag
            
    Example:
        >>> result = get_s3_object_info(
        ...     bucket_name="awesome-nexus-ai-file-storage",
        ...     object_key="abc-123.html"
        ... )
        >>> data = json.loads(result)
        >>> print(data['size'])
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # 获取对象元数据
        response = s3_client.head_object(
            Bucket=bucket_name,
            Key=object_key
        )
        
        return json.dumps({
            "success": True,
            "object_exists": True,
            "bucket": bucket_name,
            "key": object_key,
            "size": response['ContentLength'],
            "size_mb": round(response['ContentLength'] / 1024 / 1024, 2),
            "content_type": response.get('ContentType', 'unknown'),
            "last_modified": response['LastModified'].isoformat(),
            "metadata": response.get('Metadata', {}),
            "storage_class": response.get('StorageClass', 'STANDARD'),
            "etag": response.get('ETag', '').strip('"'),
            "query_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        
        if error_code == '404' or error_code == 'NoSuchKey':
            return json.dumps({
                "success": False,
                "object_exists": False,
                "error": f"对象不存在: {object_key}",
                "bucket": bucket_name,
                "key": object_key
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "object_exists": False,
                "error": f"查询对象信息失败: {e.response['Error']['Message']}",
                "error_code": error_code
            }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "object_exists": False,
            "error": f"查询对象信息异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def sanitize_html_content(
    html_content: str,
    remove_scripts: bool = True,
    remove_iframes: bool = True,
    allow_inline_styles: bool = True
) -> str:
    """
    清理HTML内容，移除潜在的安全风险
    
    该工具对HTML内容进行安全处理，移除可能的XSS攻击向量，
    同时保留合法的内容和样式。
    
    Args:
        html_content: 原始HTML内容
        remove_scripts: 是否移除<script>标签，默认True
        remove_iframes: 是否移除<iframe>标签，默认True
        allow_inline_styles: 是否允许内联样式，默认True
        
    Returns:
        str: JSON格式的清理结果，包含：
            - success: 是否成功
            - sanitized_content: 清理后的HTML内容
            - removed_elements: 移除的元素统计
            - size_before: 清理前大小（字节）
            - size_after: 清理后大小（字节）
            
    Example:
        >>> result = sanitize_html_content("<html><script>alert('xss')</script><body>test</body></html>")
        >>> data = json.loads(result)
        >>> print(data['removed_elements']['scripts'])  # 1
    """
    try:
        if not html_content:
            return json.dumps({
                "success": False,
                "error": "HTML内容为空"
            }, ensure_ascii=False, indent=2)
        
        size_before = len(html_content.encode('utf-8'))
        sanitized = html_content
        removed_count = {
            "scripts": 0,
            "iframes": 0,
            "on_events": 0
        }
        
        # 移除<script>标签
        if remove_scripts:
            script_pattern = r'<script[^>]*>.*?</script>'
            scripts_found = len(re.findall(script_pattern, sanitized, re.IGNORECASE | re.DOTALL))
            sanitized = re.sub(script_pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            removed_count["scripts"] = scripts_found
        
        # 移除<iframe>标签
        if remove_iframes:
            iframe_pattern = r'<iframe[^>]*>.*?</iframe>'
            iframes_found = len(re.findall(iframe_pattern, sanitized, re.IGNORECASE | re.DOTALL))
            sanitized = re.sub(iframe_pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            removed_count["iframes"] = iframes_found
        
        # 移除事件处理器属性（如onclick、onload等）
        event_pattern = r'\s+on\w+\s*=\s*["\'][^"\']*["\']'
        events_found = len(re.findall(event_pattern, sanitized, re.IGNORECASE))
        sanitized = re.sub(event_pattern, '', sanitized, flags=re.IGNORECASE)
        removed_count["on_events"] = events_found
        
        # 移除javascript:伪协议
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # 如果不允许内联样式，移除style属性
        if not allow_inline_styles:
            sanitized = re.sub(r'\s+style\s*=\s*["\'][^"\']*["\']', '', sanitized, flags=re.IGNORECASE)
        
        size_after = len(sanitized.encode('utf-8'))
        
        return json.dumps({
            "success": True,
            "sanitized_content": sanitized,
            "removed_elements": removed_count,
            "size_before": size_before,
            "size_after": size_after,
            "size_reduced": size_before - size_after,
            "sanitization_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"HTML清理异常: {str(e)}",
            "sanitized_content": html_content  # 返回原始内容
        }, ensure_ascii=False, indent=2)


@tool
def generate_html_metadata(
    title: str,
    description: Optional[str] = None,
    author: Optional[str] = None,
    keywords: Optional[str] = None
) -> str:
    """
    生成HTML文档的meta标签
    
    该工具生成标准的HTML meta标签，用于SEO和文档描述。
    
    Args:
        title: 文档标题
        description: 文档描述（可选）
        author: 文档作者（可选）
        keywords: 关键词（可选）
        
    Returns:
        str: JSON格式的结果，包含：
            - success: 是否成功
            - meta_tags: 生成的meta标签HTML
            
    Example:
        >>> result = generate_html_metadata(
        ...     title="我的文档",
        ...     description="这是一个示例文档"
        ... )
        >>> data = json.loads(result)
        >>> print(data['meta_tags'])
    """
    try:
        meta_tags = []
        
        # 基本meta标签
        meta_tags.append('<meta charset="UTF-8">')
        meta_tags.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        
        # 标题
        if title:
            meta_tags.append(f'<title>{title}</title>')
        
        # 描述
        if description:
            escaped_desc = description.replace('"', '&quot;')
            meta_tags.append(f'<meta name="description" content="{escaped_desc}">')
        
        # 作者
        if author:
            escaped_author = author.replace('"', '&quot;')
            meta_tags.append(f'<meta name="author" content="{escaped_author}">')
        
        # 关键词
        if keywords:
            escaped_keywords = keywords.replace('"', '&quot;')
            meta_tags.append(f'<meta name="keywords" content="{escaped_keywords}">')
        
        # 生成时间
        meta_tags.append(f'<meta name="generator" content="Nexus-AI simple_agent">')
        meta_tags.append(f'<meta name="created" content="{datetime.now().isoformat()}">')
        
        meta_html = '\n    '.join(meta_tags)
        
        return json.dumps({
            "success": True,
            "meta_tags": meta_html,
            "tag_count": len(meta_tags),
            "generation_timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"生成meta标签异常: {str(e)}",
            "meta_tags": ""
        }, ensure_ascii=False, indent=2)
