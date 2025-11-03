from strands import tool
import boto3
from typing import Dict, Any, Optional, List, Union
import json
import os
from botocore.exceptions import ClientError, NoCredentialsError

@tool
def boto3_client(
    service_name: str,
    region_name: str,
    operation_name: str,
    parameters: Dict[str, Any] = None,
    profile_name: Optional[str] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    创建并使用boto3客户端执行AWS API操作。
    
    Args:
        service_name: AWS服务名称，如's3', 'ec2', 'vpc'等
        region_name: AWS区域名称，如'us-east-1', 'eu-west-1'等
        operation_name: 要执行的API操作名称，使用蛇形命名法，如'list_buckets', 'describe_instances'
        parameters: 操作的参数字典，默认为空字典
        profile_name: AWS凭证配置文件名称，默认为None，使用默认凭证
        max_retries: 最大重试次数，默认为3
    
    Returns:
        Dict[str, Any]: 包含操作结果或错误信息的字典
    """
    if parameters is None:
        parameters = {}
    
    try:
        # 创建会话
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        # 创建客户端
        client = session.client(service_name, region_name=region_name)
        
        # 获取操作方法
        operation = getattr(client, operation_name)
        
        # 执行操作，带重试逻辑
        retry_count = 0
        last_exception = None
        
        while retry_count < max_retries:
            try:
                response = operation(**parameters)
                
                # 处理响应，确保可序列化为JSON
                serializable_response = json.loads(json.dumps(response, default=str))
                return {
                    "status": "success",
                    "service": service_name,
                    "operation": operation_name,
                    "region": region_name,
                    "response": serializable_response
                }
            except ClientError as e:
                last_exception = e
                error_code = e.response.get('Error', {}).get('Code', '')
                # 对某些错误类型进行重试
                if error_code in ['RequestLimitExceeded', 'Throttling', 'ThrottlingException']:
                    retry_count += 1
                    if retry_count < max_retries:
                        # 指数退避重试
                        import time
                        time.sleep(2 ** retry_count)
                        continue
                # 其他错误直接返回
                return {
                    "status": "error",
                    "service": service_name,
                    "operation": operation_name,
                    "region": region_name,
                    "error_type": "ClientError",
                    "error_code": error_code,
                    "error_message": str(e),
                    "request_id": e.response.get('ResponseMetadata', {}).get('RequestId', '')
                }
            except Exception as e:
                last_exception = e
                retry_count += 1
                if retry_count < max_retries:
                    import time
                    time.sleep(2 ** retry_count)
                    continue
        
        # 如果达到最大重试次数仍然失败
        return {
            "status": "error",
            "service": service_name,
            "operation": operation_name,
            "region": region_name,
            "error_type": type(last_exception).__name__,
            "error_message": str(last_exception)
        }
        
    except NoCredentialsError:
        return {
            "status": "error",
            "service": service_name,
            "operation": operation_name,
            "region": region_name,
            "error_type": "NoCredentialsError",
            "error_message": "AWS凭证未找到。请确保已配置AWS凭证。"
        }
    except AttributeError:
        return {
            "status": "error",
            "service": service_name,
            "operation": operation_name,
            "region": region_name,
            "error_type": "AttributeError",
            "error_message": f"操作'{operation_name}'在服务'{service_name}'中不存在。"
        }
    except Exception as e:
        return {
            "status": "error",
            "service": service_name,
            "operation": operation_name,
            "region": region_name,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def boto3_resource(
    service_name: str,
    region_name: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    action: Optional[str] = None,
    parameters: Dict[str, Any] = None,
    profile_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    创建并使用boto3资源对象执行AWS资源操作。
    
    Args:
        service_name: AWS服务名称，如's3', 'ec2', 'dynamodb'等
        region_name: AWS区域名称，如'us-east-1', 'eu-west-1'等
        resource_type: 资源类型，如'bucket', 'instance', 'table'等
        resource_id: 资源ID，如存储桶名称、实例ID等，如果不提供则返回资源列表
        action: 要执行的资源操作，如'download_file', 'start', 'scan'等，默认为None
        parameters: 操作的参数字典，默认为空字典
        profile_name: AWS凭证配置文件名称，默认为None，使用默认凭证
    
    Returns:
        Dict[str, Any]: 包含操作结果或错误信息的字典
    """
    if parameters is None:
        parameters = {}
    
    try:
        # 创建会话
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        
        # 创建资源
        resource = session.resource(service_name, region_name=region_name)
        
        # 处理不同的资源类型
        if resource_type == 'bucket' and service_name == 's3':
            if not resource_id:
                # 列出所有存储桶
                buckets = list(resource.buckets.all())
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "region": region_name,
                    "resources": [{"name": bucket.name} for bucket in buckets]
                }
            
            # 获取特定存储桶
            bucket = resource.Bucket(resource_id)
            
            # 执行存储桶操作
            if action == 'list_objects':
                objects = list(bucket.objects.all())
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "objects": [{"key": obj.key, "size": obj.size, "last_modified": str(obj.last_modified)} for obj in objects]
                }
            elif action == 'download_file':
                bucket.download_file(
                    parameters.get('Key'),
                    parameters.get('Filename')
                )
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "message": f"文件已下载到 {parameters.get('Filename')}"
                }
            elif action == 'upload_file':
                bucket.upload_file(
                    parameters.get('Filename'),
                    parameters.get('Key')
                )
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "message": f"文件已上传到 {resource_id}/{parameters.get('Key')}"
                }
            else:
                return {
                    "status": "error",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "error_type": "InvalidAction",
                    "error_message": f"不支持的存储桶操作: {action}"
                }
                
        elif resource_type == 'instance' and service_name == 'ec2':
            if not resource_id:
                # 列出所有EC2实例
                instances = list(resource.instances.all())
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "region": region_name,
                    "resources": [{"id": instance.id, "state": instance.state['Name'], "type": instance.instance_type} for instance in instances]
                }
            
            # 获取特定EC2实例
            instance = resource.Instance(resource_id)
            
            # 执行实例操作
            if action == 'start':
                instance.start()
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "message": f"实例 {resource_id} 已启动"
                }
            elif action == 'stop':
                instance.stop()
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "message": f"实例 {resource_id} 已停止"
                }
            elif action == 'describe':
                # 获取实例详细信息
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "instance": {
                        "id": instance.id,
                        "state": instance.state['Name'],
                        "type": instance.instance_type,
                        "public_ip": instance.public_ip_address,
                        "private_ip": instance.private_ip_address,
                        "vpc_id": instance.vpc_id,
                        "subnet_id": instance.subnet_id,
                        "security_groups": [sg['GroupId'] for sg in instance.security_groups],
                        "tags": [{tag['Key']: tag['Value']} for tag in instance.tags] if instance.tags else []
                    }
                }
            else:
                return {
                    "status": "error",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "error_type": "InvalidAction",
                    "error_message": f"不支持的实例操作: {action}"
                }
                
        elif resource_type == 'table' and service_name == 'dynamodb':
            if not resource_id:
                # 列出所有DynamoDB表
                tables = list(resource.tables.all())
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "region": region_name,
                    "resources": [{"name": table.name} for table in tables]
                }
            
            # 获取特定DynamoDB表
            table = resource.Table(resource_id)
            
            # 执行表操作
            if action == 'scan':
                response = table.scan(**parameters)
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "items": response.get('Items', []),
                    "count": response.get('Count', 0),
                    "scanned_count": response.get('ScannedCount', 0)
                }
            elif action == 'get_item':
                response = table.get_item(**parameters)
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "item": response.get('Item')
                }
            elif action == 'put_item':
                table.put_item(**parameters)
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "message": "项目已添加到表中"
                }
            elif action == 'describe':
                return {
                    "status": "success",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "table": {
                        "name": table.name,
                        "status": table.table_status,
                        "creation_date": str(table.creation_date_time),
                        "item_count": table.item_count,
                        "table_size_bytes": table.table_size_bytes,
                        "key_schema": table.key_schema
                    }
                }
            else:
                return {
                    "status": "error",
                    "service": service_name,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "action": action,
                    "region": region_name,
                    "error_type": "InvalidAction",
                    "error_message": f"不支持的表操作: {action}"
                }
        
        # 对于其他资源类型，返回不支持的错误
        return {
            "status": "error",
            "service": service_name,
            "resource_type": resource_type,
            "region": region_name,
            "error_type": "UnsupportedResource",
            "error_message": f"不支持的资源类型: {resource_type} for {service_name}"
        }
        
    except ClientError as e:
        return {
            "status": "error",
            "service": service_name,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "region": region_name,
            "error_type": "ClientError",
            "error_code": e.response.get('Error', {}).get('Code', ''),
            "error_message": str(e),
            "request_id": e.response.get('ResponseMetadata', {}).get('RequestId', '')
        }
    except NoCredentialsError:
        return {
            "status": "error",
            "service": service_name,
            "resource_type": resource_type,
            "region": region_name,
            "error_type": "NoCredentialsError",
            "error_message": "AWS凭证未找到。请确保已配置AWS凭证。"
        }
    except Exception as e:
        return {
            "status": "error",
            "service": service_name,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "region": region_name,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }