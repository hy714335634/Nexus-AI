#!/usr/bin/env python3
"""
S3 storage tools using boto3 for file upload and management.
Supports direct upload, batch upload, and public URL generation.
"""

import json
import os
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import quote

from strands import tool

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


@tool
def upload_file_to_s3(
    file_path: str,
    bucket_name: str,
    s3_key: Optional[str] = None,
    public_read: bool = True,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> str:
    """
    上传文件到S3存储桶
    
    Args:
        file_path (str): 本地文件路径
        bucket_name (str): S3存储桶名称
        s3_key (str, optional): S3对象键（不指定则使用文件名）
        public_read (bool): 是否设置为公开可读
        content_type (str, optional): 文件MIME类型（自动检测）
        metadata (Dict, optional): 自定义元数据
        
    Returns:
        str: JSON格式的上传结果
    """
    try:
        if not BOTO3_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "boto3库未安装。请安装: pip install boto3"
            }, ensure_ascii=False)
        
        # 验证文件存在
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return json.dumps({
                "status": "error",
                "message": f"文件不存在: {file_path}"
            }, ensure_ascii=False)
        
        # 生成S3键
        if not s3_key:
            s3_key = file_path_obj.name
        
        # 自动检测Content-Type
        if not content_type:
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = "application/octet-stream"
        
        # 创建S3客户端
        s3_client = boto3.client('s3')
        
        # 准备上传参数
        extra_args = {
            'ContentType': content_type
        }
        
        if public_read:
            extra_args['ACL'] = 'public-read'
        
        if metadata:
            extra_args['Metadata'] = metadata
        
        # 上传文件
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=s3_key,
            ExtraArgs=extra_args
        )
        
        # 生成公开URL
        if public_read:
            region = s3_client.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
            if region is None:
                region = 'us-east-1'
            
            public_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{quote(s3_key)}"
        else:
            public_url = None
        
        return json.dumps({
            "status": "success",
            "message": "文件上传成功",
            "file_path": file_path,
            "bucket_name": bucket_name,
            "s3_key": s3_key,
            "public_url": public_url,
            "file_size": file_path_obj.stat().st_size,
            "content_type": content_type,
            "upload_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except NoCredentialsError:
        return json.dumps({
            "status": "error",
            "message": "AWS凭证未配置。请配置AWS_ACCESS_KEY_ID和AWS_SECRET_ACCESS_KEY"
        }, ensure_ascii=False)
    except ClientError as e:
        return json.dumps({
            "status": "error",
            "message": f"S3操作失败: {e.response['Error']['Message']}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"上传失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def batch_upload_to_s3(
    file_paths: List[str],
    bucket_name: str,
    s3_prefix: Optional[str] = None,
    public_read: bool = True
) -> str:
    """
    批量上传文件到S3
    
    Args:
        file_paths (List[str]): 本地文件路径列表
        bucket_name (str): S3存储桶名称
        s3_prefix (str, optional): S3键前缀（目录）
        public_read (bool): 是否设置为公开可读
        
    Returns:
        str: JSON格式的批量上传结果
    """
    try:
        results = {
            "status": "success",
            "bucket_name": bucket_name,
            "s3_prefix": s3_prefix or "",
            "total_files": len(file_paths),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "upload_results": [],
            "upload_time": datetime.now().isoformat()
        }
        
        for file_path in file_paths:
            try:
                # 生成S3键
                file_name = Path(file_path).name
                s3_key = f"{s3_prefix}/{file_name}" if s3_prefix else file_name
                
                # 上传文件
                upload_result_json = upload_file_to_s3(
                    file_path=file_path,
                    bucket_name=bucket_name,
                    s3_key=s3_key,
                    public_read=public_read
                )
                upload_result = json.loads(upload_result_json)
                
                if upload_result["status"] == "success":
                    results["successful_uploads"] += 1
                else:
                    results["failed_uploads"] += 1
                
                results["upload_results"].append({
                    "file_path": file_path,
                    "status": upload_result["status"],
                    "s3_key": upload_result.get("s3_key"),
                    "public_url": upload_result.get("public_url"),
                    "message": upload_result.get("message")
                })
                
            except Exception as e:
                results["failed_uploads"] += 1
                results["upload_results"].append({
                    "file_path": file_path,
                    "status": "error",
                    "message": str(e)
                })
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量上传失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def upload_directory_to_s3(
    directory_path: str,
    bucket_name: str,
    s3_prefix: Optional[str] = None,
    public_read: bool = True,
    recursive: bool = True,
    file_patterns: Optional[List[str]] = None
) -> str:
    """
    上传目录到S3
    
    Args:
        directory_path (str): 本地目录路径
        bucket_name (str): S3存储桶名称
        s3_prefix (str, optional): S3键前缀
        public_read (bool): 是否设置为公开可读
        recursive (bool): 是否递归上传子目录
        file_patterns (List[str], optional): 文件匹配模式（如["*.html", "*.json"]）
        
    Returns:
        str: JSON格式的上传结果
    """
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            return json.dumps({
                "status": "error",
                "message": f"目录不存在: {directory_path}"
            }, ensure_ascii=False)
        
        # 收集要上传的文件
        files_to_upload = []
        
        if recursive:
            if file_patterns:
                for pattern in file_patterns:
                    files_to_upload.extend(dir_path.rglob(pattern))
            else:
                files_to_upload.extend(dir_path.rglob("*"))
        else:
            if file_patterns:
                for pattern in file_patterns:
                    files_to_upload.extend(dir_path.glob(pattern))
            else:
                files_to_upload.extend(dir_path.glob("*"))
        
        # 过滤出文件（排除目录）
        files_to_upload = [f for f in files_to_upload if f.is_file()]
        
        # 批量上传
        file_paths = [str(f) for f in files_to_upload]
        
        results = {
            "status": "success",
            "directory_path": directory_path,
            "bucket_name": bucket_name,
            "s3_prefix": s3_prefix or "",
            "total_files": len(file_paths),
            "successful_uploads": 0,
            "failed_uploads": 0,
            "upload_results": [],
            "upload_time": datetime.now().isoformat()
        }
        
        for file_path in file_paths:
            try:
                # 保持目录结构
                relative_path = Path(file_path).relative_to(dir_path)
                s3_key = f"{s3_prefix}/{relative_path}" if s3_prefix else str(relative_path)
                s3_key = s3_key.replace("\\", "/")  # Windows路径转换
                
                # 上传文件
                upload_result_json = upload_file_to_s3(
                    file_path=file_path,
                    bucket_name=bucket_name,
                    s3_key=s3_key,
                    public_read=public_read
                )
                upload_result = json.loads(upload_result_json)
                
                if upload_result["status"] == "success":
                    results["successful_uploads"] += 1
                else:
                    results["failed_uploads"] += 1
                
                results["upload_results"].append({
                    "file_path": file_path,
                    "status": upload_result["status"],
                    "s3_key": upload_result.get("s3_key"),
                    "public_url": upload_result.get("public_url")
                })
                
            except Exception as e:
                results["failed_uploads"] += 1
                results["upload_results"].append({
                    "file_path": file_path,
                    "status": "error",
                    "message": str(e)
                })
        
        return json.dumps(results, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"目录上传失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def list_s3_objects(
    bucket_name: str,
    prefix: Optional[str] = None,
    max_keys: int = 1000
) -> str:
    """
    列出S3存储桶中的对象
    
    Args:
        bucket_name (str): S3存储桶名称
        prefix (str, optional): 对象键前缀
        max_keys (int): 最大返回数量
        
    Returns:
        str: JSON格式的对象列表
    """
    try:
        if not BOTO3_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "boto3库未安装。请安装: pip install boto3"
            }, ensure_ascii=False)
        
        s3_client = boto3.client('s3')
        
        # 列出对象
        params = {
            'Bucket': bucket_name,
            'MaxKeys': max_keys
        }
        
        if prefix:
            params['Prefix'] = prefix
        
        response = s3_client.list_objects_v2(**params)
        
        objects = []
        for obj in response.get('Contents', []):
            objects.append({
                "key": obj['Key'],
                "size": obj['Size'],
                "last_modified": obj['LastModified'].isoformat(),
                "etag": obj['ETag'].strip('"')
            })
        
        return json.dumps({
            "status": "success",
            "bucket_name": bucket_name,
            "prefix": prefix or "",
            "total_objects": len(objects),
            "objects": objects,
            "query_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "status": "error",
            "message": f"S3操作失败: {e.response['Error']['Message']}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"列出对象失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def delete_s3_object(
    bucket_name: str,
    s3_key: str
) -> str:
    """
    删除S3对象
    
    Args:
        bucket_name (str): S3存储桶名称
        s3_key (str): S3对象键
        
    Returns:
        str: JSON格式的删除结果
    """
    try:
        if not BOTO3_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "boto3库未安装。请安装: pip install boto3"
            }, ensure_ascii=False)
        
        s3_client = boto3.client('s3')
        
        # 删除对象
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=s3_key
        )
        
        return json.dumps({
            "status": "success",
            "message": "对象删除成功",
            "bucket_name": bucket_name,
            "s3_key": s3_key,
            "deletion_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "status": "error",
            "message": f"S3操作失败: {e.response['Error']['Message']}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"删除失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def generate_presigned_url(
    bucket_name: str,
    s3_key: str,
    expiration: int = 3600
) -> str:
    """
    生成S3对象的预签名URL
    
    Args:
        bucket_name (str): S3存储桶名称
        s3_key (str): S3对象键
        expiration (int): URL有效期（秒）
        
    Returns:
        str: JSON格式的预签名URL
    """
    try:
        if not BOTO3_AVAILABLE:
            return json.dumps({
                "status": "error",
                "message": "boto3库未安装。请安装: pip install boto3"
            }, ensure_ascii=False)
        
        s3_client = boto3.client('s3')
        
        # 生成预签名URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        return json.dumps({
            "status": "success",
            "bucket_name": bucket_name,
            "s3_key": s3_key,
            "presigned_url": presigned_url,
            "expiration_seconds": expiration,
            "generation_time": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except ClientError as e:
        return json.dumps({
            "status": "error",
            "message": f"S3操作失败: {e.response['Error']['Message']}"
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"生成预签名URL失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def upload_report_to_s3(
    report_path: str,
    bucket_name: str,
    report_category: str = "energy_reports",
    public_read: bool = True
) -> str:
    """
    上传分析报告到S3（带自动分类和命名）
    
    Args:
        report_path (str): 报告文件路径
        bucket_name (str): S3存储桶名称
        report_category (str): 报告分类（用作S3前缀）
        public_read (bool): 是否设置为公开可读
        
    Returns:
        str: JSON格式的上传结果
    """
    try:
        report_file = Path(report_path)
        if not report_file.exists():
            return json.dumps({
                "status": "error",
                "message": f"报告文件不存在: {report_path}"
            }, ensure_ascii=False)
        
        # 生成S3键（包含日期分类）
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"{report_category}/{date_prefix}/{report_file.name}"
        
        # 添加元数据
        metadata = {
            "upload_time": datetime.now().isoformat(),
            "report_category": report_category,
            "file_type": report_file.suffix.lstrip('.')
        }
        
        # 上传文件
        upload_result_json = upload_file_to_s3(
            file_path=report_path,
            bucket_name=bucket_name,
            s3_key=s3_key,
            public_read=public_read,
            metadata=metadata
        )
        upload_result = json.loads(upload_result_json)
        
        if upload_result["status"] == "success":
            upload_result["report_category"] = report_category
            upload_result["date_prefix"] = date_prefix
        
        return json.dumps(upload_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"报告上传失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def batch_upload_reports_to_s3(
    report_directory: str,
    bucket_name: str,
    report_category: str = "energy_reports",
    file_patterns: Optional[List[str]] = None,
    public_read: bool = True
) -> str:
    """
    批量上传报告目录到S3
    
    Args:
        report_directory (str): 报告目录路径
        bucket_name (str): S3存储桶名称
        report_category (str): 报告分类
        file_patterns (List[str], optional): 文件匹配模式（如["*.html", "*.json"]）
        public_read (bool): 是否设置为公开可读
        
    Returns:
        str: JSON格式的批量上传结果
    """
    try:
        # 默认上传所有报告格式
        if not file_patterns:
            file_patterns = ["*.html", "*.md", "*.json", "*.pdf"]
        
        # 使用目录上传功能
        result_json = upload_directory_to_s3(
            directory_path=report_directory,
            bucket_name=bucket_name,
            s3_prefix=report_category,
            public_read=public_read,
            recursive=True,
            file_patterns=file_patterns
        )
        
        return result_json
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量上传报告失败: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试工具
    print("🧪 测试S3存储工具...")
    
    # 注意：实际测试需要配置AWS凭证和S3存储桶
    print("⚠️  S3工具需要配置AWS凭证才能测试")
    print("✅ 工具定义完成！")
