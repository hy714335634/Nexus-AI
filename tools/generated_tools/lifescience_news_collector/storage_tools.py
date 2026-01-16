"""
生命科学新闻存储工具模块

该模块提供：
- AWS S3对象存储
- AWS DynamoDB数据库存储
- 本地文件存储
- 缓存管理
- 数据导出功能
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from strands import tool


# ============================================================================
# AWS S3 存储工具
# ============================================================================

@tool
def upload_file_to_s3(
    file_path: str,
    bucket_name: str,
    object_key: str,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    region: str = "us-west-2"
) -> str:
    """
    从本地文件路径上传文件到AWS S3（推荐使用，确保本地与云端内容一致）
    
    Args:
        file_path: 本地文件路径（支持相对路径和绝对路径）
        bucket_name: S3存储桶名称
        object_key: S3对象键（文件在S3中的路径）
        content_type: 内容类型（可选，自动根据文件扩展名推断）
        metadata: 对象元数据（可选）
        region: AWS区域（默认us-west-2）
    
    Returns:
        str: JSON格式的上传结果，包含：
            - success: 是否成功
            - bucket: S3桶名称
            - key: 对象键
            - url: S3 URI
            - file_path: 本地文件路径
            - file_size: 文件大小（字节）
            - content_type: 内容类型
            - timestamp: 上传时间
    
    Example:
        upload_file_to_s3(
            file_path="./reports/2026/01/07/newsletter_20260107_150230.html",
            bucket_name="hcls-newsletter",
            object_key="reports/2026/01/07/newsletter_20260107_150230.html",
            region="us-west-2"
        )
    """
    try:
        from pathlib import Path
        import mimetypes
        
        # 解析文件路径
        local_file = Path(file_path)
        
        if not local_file.exists():
            return json.dumps({
                "success": False,
                "error": f"本地文件不存在: {file_path}",
                "hint": "请确保文件路径正确，可以使用 generate_newsletter_from_json 工具生成报告后获取文件路径"
            }, ensure_ascii=False, indent=2)
        
        if not local_file.is_file():
            return json.dumps({
                "success": False,
                "error": f"路径不是文件: {file_path}"
            }, ensure_ascii=False, indent=2)
        
        # 自动推断内容类型
        if content_type is None:
            mime_type, _ = mimetypes.guess_type(str(local_file))
            content_type = mime_type or "application/octet-stream"
            
            # 特殊处理常见类型
            if local_file.suffix.lower() == '.html':
                content_type = "text/html; charset=utf-8"
            elif local_file.suffix.lower() == '.json':
                content_type = "application/json; charset=utf-8"
            elif local_file.suffix.lower() == '.css':
                content_type = "text/css; charset=utf-8"
            elif local_file.suffix.lower() == '.js':
                content_type = "application/javascript; charset=utf-8"
        
        # 获取文件大小
        file_size = local_file.stat().st_size
        
        # 创建S3客户端
        s3_client = boto3.client('s3', region_name=region)
        
        # 准备上传参数
        extra_args = {
            'ContentType': content_type
        }
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        # 使用 upload_file 方法上传本地文件（更高效，支持大文件分片上传）
        s3_client.upload_file(
            Filename=str(local_file.absolute()),
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs=extra_args
        )
        
        # 生成对象URL
        object_url = f"s3://{bucket_name}/{object_key}"
        
        return json.dumps({
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "url": object_url,
            "file_path": str(local_file.absolute()),
            "file_size": file_size,
            "content_type": content_type,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"S3上传失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code'],
            "file_path": file_path
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"S3上传异常: {str(e)}",
            "file_path": file_path
        }, ensure_ascii=False, indent=2)


@tool
def upload_to_s3(
    content: str,
    bucket_name: str,
    object_key: str,
    content_type: str = "application/json",
    metadata: Optional[Dict[str, str]] = None,
    region: str = "us-east-1"
) -> str:
    """
    上传字符串内容到AWS S3（注意：推荐使用 upload_file_to_s3 上传本地文件，确保内容一致性）
    
    Args:
        content: 要上传的字符串内容
        bucket_name: S3存储桶名称
        object_key: 对象键（文件路径）
        content_type: 内容类型（默认application/json）
        metadata: 对象元数据（可选）
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的上传结果
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # 准备上传参数
        put_params = {
            'Bucket': bucket_name,
            'Key': object_key,
            'Body': content.encode('utf-8'),
            'ContentType': content_type
        }
        
        if metadata:
            put_params['Metadata'] = metadata
        
        # 上传到S3
        s3_client.put_object(**put_params)
        
        # 生成对象URL
        object_url = f"s3://{bucket_name}/{object_key}"
        
        return json.dumps({
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "url": object_url,
            "content_length": len(content),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"S3上传失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"S3上传异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def generate_presigned_url(
    bucket_name: str,
    object_key: str,
    expiration: int = 604800,
    region: str = "us-west-2"
) -> str:
    """
    生成S3对象的预签名URL
    
    Args:
        bucket_name: S3存储桶名称
        object_key: 对象键（文件路径）
        expiration: URL有效期（秒），默认7天（604800秒）
        region: AWS区域（默认us-west-2）
    
    Returns:
        str: JSON格式的预签名URL结果
    """
    try:
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
        from datetime import timedelta
        expiry_time = datetime.now() + timedelta(seconds=expiration)
        
        return json.dumps({
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "presigned_url": presigned_url,
            "s3_uri": f"s3://{bucket_name}/{object_key}",
            "expiration_seconds": expiration,
            "expiration_days": round(expiration / 86400, 1),
            "expires_at": expiry_time.isoformat(),
            "region": region,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"生成预签名URL失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"生成预签名URL异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def download_from_s3(
    bucket_name: str,
    object_key: str,
    region: str = "us-east-1"
) -> str:
    """
    从AWS S3下载内容
    
    Args:
        bucket_name: S3存储桶名称
        object_key: 对象键（文件路径）
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的下载结果
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # 从S3下载
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content = response['Body'].read().decode('utf-8')
        
        return json.dumps({
            "success": True,
            "bucket": bucket_name,
            "key": object_key,
            "content": content,
            "content_length": len(content),
            "last_modified": response['LastModified'].isoformat(),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"S3下载失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"S3下载异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def list_s3_objects(
    bucket_name: str,
    prefix: str = "",
    max_keys: int = 1000,
    region: str = "us-east-1"
) -> str:
    """
    列出S3存储桶中的对象
    
    Args:
        bucket_name: S3存储桶名称
        prefix: 对象键前缀（过滤）
        max_keys: 最大返回对象数
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的对象列表
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        
        # 列出对象
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        if 'Contents' in response:
            for obj in response['Contents']:
                objects.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "etag": obj['ETag']
                })
        
        return json.dumps({
            "success": True,
            "bucket": bucket_name,
            "prefix": prefix,
            "total_objects": len(objects),
            "objects": objects,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"S3列表失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"S3列表异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# AWS DynamoDB 存储工具
# ============================================================================

@tool
def put_item_to_dynamodb(
    table_name: str,
    item: Dict[str, Any],
    region: str = "us-east-1"
) -> str:
    """
    向DynamoDB表插入项目
    
    Args:
        table_name: DynamoDB表名
        item: 要插入的项目数据
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的插入结果
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # 添加时间戳
        if 'created_at' not in item:
            item['created_at'] = datetime.now().isoformat()
        
        # 插入项目
        table.put_item(Item=item)
        
        return json.dumps({
            "success": True,
            "table_name": table_name,
            "item_id": item.get("id", "unknown"),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB插入失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB插入异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def get_item_from_dynamodb(
    table_name: str,
    key: Dict[str, Any],
    region: str = "us-east-1"
) -> str:
    """
    从DynamoDB表获取项目
    
    Args:
        table_name: DynamoDB表名
        key: 主键字典，例如 {"id": "article-123"}
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的获取结果
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # 获取项目
        response = table.get_item(Key=key)
        
        if 'Item' in response:
            return json.dumps({
                "success": True,
                "table_name": table_name,
                "item": response['Item'],
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "项目不存在",
                "table_name": table_name,
                "key": key
            }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB获取失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB获取异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def query_dynamodb(
    table_name: str,
    key_condition_expression: str,
    expression_attribute_values: Dict[str, Any],
    index_name: Optional[str] = None,
    limit: int = 100,
    region: str = "us-east-1"
) -> str:
    """
    查询DynamoDB表
    
    Args:
        table_name: DynamoDB表名
        key_condition_expression: 键条件表达式，例如 "id = :id"
        expression_attribute_values: 表达式属性值，例如 {":id": "article-123"}
        index_name: 全局二级索引名称（可选）
        limit: 返回结果数量限制
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的查询结果
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # 构建查询参数
        query_params = {
            'KeyConditionExpression': key_condition_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'Limit': limit
        }
        
        if index_name:
            query_params['IndexName'] = index_name
        
        # 执行查询
        response = table.query(**query_params)
        
        items = response.get('Items', [])
        
        return json.dumps({
            "success": True,
            "table_name": table_name,
            "index_name": index_name,
            "count": len(items),
            "items": items,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB查询失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB查询异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def batch_write_to_dynamodb(
    table_name: str,
    items: List[Dict[str, Any]],
    region: str = "us-east-1"
) -> str:
    """
    批量写入DynamoDB表
    
    Args:
        table_name: DynamoDB表名
        items: 要写入的项目列表
        region: AWS区域（默认us-east-1）
    
    Returns:
        str: JSON格式的批量写入结果
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table(table_name)
        
        # DynamoDB批量写入限制为25项
        batch_size = 25
        total_written = 0
        failed_items = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            with table.batch_writer() as writer:
                for item in batch:
                    try:
                        # 添加时间戳
                        if 'created_at' not in item:
                            item['created_at'] = datetime.now().isoformat()
                        
                        writer.put_item(Item=item)
                        total_written += 1
                    except Exception as e:
                        failed_items.append({
                            "item": item,
                            "error": str(e)
                        })
        
        return json.dumps({
            "success": True,
            "table_name": table_name,
            "total_items": len(items),
            "written_count": total_written,
            "failed_count": len(failed_items),
            "failed_items": failed_items,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB批量写入失败: {e.response['Error']['Message']}",
            "error_code": e.response['Error']['Code']
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"DynamoDB批量写入异常: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 本地文件存储工具
# ============================================================================

@tool
def save_to_local_file(
    content: str,
    file_path: str,
    mode: str = "w",
    encoding: str = "utf-8",
    create_dirs: bool = True
) -> str:
    """
    保存内容到本地文件
    
    Args:
        content: 要保存的内容
        file_path: 文件路径
        mode: 文件打开模式（w=覆盖, a=追加）
        encoding: 文件编码（默认utf-8）
        create_dirs: 是否自动创建目录（默认True）
    
    Returns:
        str: JSON格式的保存结果
    """
    try:
        path = Path(file_path)
        
        # 创建目录
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(path, mode, encoding=encoding) as f:
            f.write(content)
        
        # 获取文件信息
        file_size = path.stat().st_size
        
        return json.dumps({
            "success": True,
            "file_path": str(path.absolute()),
            "file_size": file_size,
            "mode": mode,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文件保存失败: {str(e)}",
            "file_path": file_path
        }, ensure_ascii=False, indent=2)


@tool
def read_from_local_file(
    file_path: str,
    encoding: str = "utf-8"
) -> str:
    """
    从本地文件读取内容
    
    Args:
        file_path: 文件路径
        encoding: 文件编码（默认utf-8）
    
    Returns:
        str: JSON格式的读取结果
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return json.dumps({
                "success": False,
                "error": "文件不存在",
                "file_path": file_path
            }, ensure_ascii=False, indent=2)
        
        # 读取文件
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # 获取文件信息
        file_size = path.stat().st_size
        modified_time = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        
        return json.dumps({
            "success": True,
            "file_path": str(path.absolute()),
            "content": content,
            "file_size": file_size,
            "modified_time": modified_time,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文件读取失败: {str(e)}",
            "file_path": file_path
        }, ensure_ascii=False, indent=2)


@tool
def list_local_files(
    directory: str,
    pattern: str = "*",
    recursive: bool = False
) -> str:
    """
    列出本地目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件名模式（支持通配符）
        recursive: 是否递归搜索子目录
    
    Returns:
        str: JSON格式的文件列表
    """
    try:
        path = Path(directory)
        
        if not path.exists():
            return json.dumps({
                "success": False,
                "error": "目录不存在",
                "directory": directory
            }, ensure_ascii=False, indent=2)
        
        # 列出文件
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))
        
        file_list = []
        for file in files:
            if file.is_file():
                file_list.append({
                    "path": str(file.absolute()),
                    "name": file.name,
                    "size": file.stat().st_size,
                    "modified_time": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })
        
        return json.dumps({
            "success": True,
            "directory": directory,
            "pattern": pattern,
            "recursive": recursive,
            "total_files": len(file_list),
            "files": file_list,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文件列表获取失败: {str(e)}",
            "directory": directory
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 缓存管理工具
# ============================================================================

@tool
def save_to_cache(
    cache_key: str,
    data: Any,
    cache_dir: str = ".cache/lifescience_news_collector",
    ttl_hours: Optional[int] = None
) -> str:
    """
    保存数据到本地缓存
    
    Args:
        cache_key: 缓存键
        data: 要缓存的数据
        cache_dir: 缓存目录
        ttl_hours: 缓存有效期（小时），None表示永久
    
    Returns:
        str: JSON格式的缓存结果
    """
    try:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # 生成缓存文件名
        import hashlib
        cache_file_name = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
        cache_file_path = cache_path / cache_file_name
        
        # 准备缓存数据
        cache_data = {
            "key": cache_key,
            "data": data,
            "created_at": datetime.now().isoformat(),
            "ttl_hours": ttl_hours
        }
        
        # 写入缓存
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "cache_key": cache_key,
            "cache_file": str(cache_file_path),
            "ttl_hours": ttl_hours,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"缓存保存失败: {str(e)}",
            "cache_key": cache_key
        }, ensure_ascii=False, indent=2)


@tool
def get_from_cache(
    cache_key: str,
    cache_dir: str = ".cache/lifescience_news_collector"
) -> str:
    """
    从本地缓存获取数据
    
    Args:
        cache_key: 缓存键
        cache_dir: 缓存目录
    
    Returns:
        str: JSON格式的缓存数据
    """
    try:
        cache_path = Path(cache_dir)
        
        # 生成缓存文件名
        import hashlib
        cache_file_name = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
        cache_file_path = cache_path / cache_file_name
        
        if not cache_file_path.exists():
            return json.dumps({
                "success": False,
                "error": "缓存不存在",
                "cache_key": cache_key
            }, ensure_ascii=False, indent=2)
        
        # 读取缓存
        with open(cache_file_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查TTL
        if cache_data.get("ttl_hours"):
            created_at = datetime.fromisoformat(cache_data["created_at"])
            age_hours = (datetime.now() - created_at).total_seconds() / 3600
            
            if age_hours > cache_data["ttl_hours"]:
                return json.dumps({
                    "success": False,
                    "error": "缓存已过期",
                    "cache_key": cache_key,
                    "age_hours": age_hours,
                    "ttl_hours": cache_data["ttl_hours"]
                }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "success": True,
            "cache_key": cache_key,
            "data": cache_data["data"],
            "created_at": cache_data["created_at"],
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"缓存读取失败: {str(e)}",
            "cache_key": cache_key
        }, ensure_ascii=False, indent=2)


@tool
def clear_cache(
    cache_dir: str = ".cache/lifescience_news_collector",
    older_than_hours: Optional[int] = None
) -> str:
    """
    清理本地缓存
    
    Args:
        cache_dir: 缓存目录
        older_than_hours: 只清理超过指定小时数的缓存，None表示清理全部
    
    Returns:
        str: JSON格式的清理结果
    """
    try:
        cache_path = Path(cache_dir)
        
        if not cache_path.exists():
            return json.dumps({
                "success": True,
                "message": "缓存目录不存在，无需清理",
                "cache_dir": cache_dir
            }, ensure_ascii=False, indent=2)
        
        deleted_count = 0
        total_count = 0
        
        # 遍历缓存文件
        for cache_file in cache_path.glob("*.json"):
            total_count += 1
            
            if older_than_hours is not None:
                # 检查文件年龄
                modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age_hours = (datetime.now() - modified_time).total_seconds() / 3600
                
                if age_hours > older_than_hours:
                    cache_file.unlink()
                    deleted_count += 1
            else:
                # 删除所有缓存
                cache_file.unlink()
                deleted_count += 1
        
        return json.dumps({
            "success": True,
            "cache_dir": cache_dir,
            "total_files": total_count,
            "deleted_files": deleted_count,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"缓存清理失败: {str(e)}",
            "cache_dir": cache_dir
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 数据导出工具
# ============================================================================

@tool
def export_to_json(
    data: Any,
    output_path: str,
    pretty: bool = True
) -> str:
    """
    导出数据为JSON文件
    
    Args:
        data: 要导出的数据
        output_path: 输出文件路径
        pretty: 是否格式化输出
    
    Returns:
        str: JSON格式的导出结果
    """
    try:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)
        
        file_size = path.stat().st_size
        
        return json.dumps({
            "success": True,
            "output_path": str(path.absolute()),
            "file_size": file_size,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"JSON导出失败: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False, indent=2)


@tool
def export_to_csv(
    data: List[Dict[str, Any]],
    output_path: str,
    columns: Optional[List[str]] = None
) -> str:
    """
    导出数据为CSV文件
    
    Args:
        data: 要导出的数据列表（字典列表）
        output_path: 输出文件路径
        columns: 要导出的列名列表（None表示所有列）
    
    Returns:
        str: JSON格式的导出结果
    """
    try:
        import csv
        
        if not data:
            return json.dumps({
                "success": False,
                "error": "数据为空",
                "output_path": output_path
            }, ensure_ascii=False, indent=2)
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 确定列名
        if columns is None:
            columns = list(data[0].keys())
        
        # 写入CSV
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for row in data:
                # 只写入指定列
                filtered_row = {k: v for k, v in row.items() if k in columns}
                writer.writerow(filtered_row)
        
        file_size = path.stat().st_size
        
        return json.dumps({
            "success": True,
            "output_path": str(path.absolute()),
            "file_size": file_size,
            "row_count": len(data),
            "column_count": len(columns),
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"CSV导出失败: {str(e)}",
            "output_path": output_path
        }, ensure_ascii=False, indent=2)
