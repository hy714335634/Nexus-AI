from strands import tool
from typing import Dict, List, Optional, Any, Union
import boto3
import json
import os
import logging
from botocore.exceptions import ClientError, ProfileNotFound

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@tool
def aws_profile_manager(
    action: str,
    profile_name: str,
    region: Optional[str] = None,
    create_session: bool = False
) -> str:
    """
    管理AWS配置文件和认证
    
    Args:
        action: 执行的操作，可选值: validate, list, get_credentials, test_connection
        profile_name: AWS配置文件名称
        region: AWS区域（可选，默认使用配置文件中的区域）
        create_session: 是否创建并返回会话对象（可选，默认False）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        result = {}
        
        if action == "list":
            # 列出所有可用的配置文件
            session = boto3.Session()
            profiles = session.available_profiles
            result = {
                "status": "success",
                "profiles": profiles,
                "count": len(profiles)
            }
            
        elif action == "validate":
            # 验证配置文件是否存在
            session = boto3.Session()
            profiles = session.available_profiles
            
            if profile_name in profiles:
                try:
                    # 尝试使用配置文件创建会话
                    profile_session = boto3.Session(profile_name=profile_name)
                    
                    # 获取配置文件中的默认区域
                    default_region = profile_session.region_name
                    
                    # 使用指定区域或默认区域
                    actual_region = region if region else default_region
                    
                    if not actual_region:
                        result = {
                            "status": "error",
                            "message": f"Profile '{profile_name}' exists but has no region configured",
                            "exists": True,
                            "valid": False
                        }
                    else:
                        # 创建STS客户端进行凭证验证
                        sts_client = profile_session.client('sts', region_name=actual_region)
                        identity = sts_client.get_caller_identity()
                        
                        result = {
                            "status": "success",
                            "message": f"Profile '{profile_name}' is valid",
                            "exists": True,
                            "valid": True,
                            "account_id": identity['Account'],
                            "user_id": identity['UserId'],
                            "arn": identity['Arn'],
                            "region": actual_region
                        }
                        
                        if create_session:
                            result["session_created"] = True
                            
                except ClientError as e:
                    result = {
                        "status": "error",
                        "message": f"Profile '{profile_name}' exists but credentials are invalid: {str(e)}",
                        "exists": True,
                        "valid": False,
                        "error_code": e.response['Error']['Code'],
                        "error_message": e.response['Error']['Message']
                    }
            else:
                result = {
                    "status": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "exists": False,
                    "valid": False
                }
                
        elif action == "get_credentials":
            # 获取配置文件的凭证信息（不包括敏感信息）
            try:
                session = boto3.Session(profile_name=profile_name)
                credentials = session.get_credentials()
                
                if credentials:
                    # 不返回实际密钥，只返回元数据
                    result = {
                        "status": "success",
                        "message": f"Retrieved credentials metadata for profile '{profile_name}'",
                        "has_credentials": True,
                        "credential_type": credentials.method,
                        "region": session.region_name
                    }
                    
                    # 如果是临时凭证，添加过期信息
                    if hasattr(credentials, 'expiry_time'):
                        result["expiry_time"] = credentials.expiry_time.isoformat() if credentials.expiry_time else None
                else:
                    result = {
                        "status": "error",
                        "message": f"No credentials found for profile '{profile_name}'",
                        "has_credentials": False
                    }
            except ProfileNotFound:
                result = {
                    "status": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "exists": False
                }
                
        elif action == "test_connection":
            # 测试与AWS的连接
            try:
                # 使用指定配置文件创建会话
                session = boto3.Session(profile_name=profile_name)
                
                # 获取配置文件中的默认区域或使用指定区域
                actual_region = region if region else session.region_name
                
                if not actual_region:
                    result = {
                        "status": "error",
                        "message": "No region specified and no default region in profile",
                        "connected": False
                    }
                else:
                    # 创建STS客户端进行连接测试
                    sts_client = session.client('sts', region_name=actual_region)
                    identity = sts_client.get_caller_identity()
                    
                    # 获取可用区域列表
                    ec2_client = session.client('ec2', region_name=actual_region)
                    regions_response = ec2_client.describe_regions()
                    available_regions = [region['RegionName'] for region in regions_response['Regions']]
                    
                    result = {
                        "status": "success",
                        "message": "Successfully connected to AWS",
                        "connected": True,
                        "account_id": identity['Account'],
                        "user_id": identity['UserId'],
                        "arn": identity['Arn'],
                        "region": actual_region,
                        "available_regions": available_regions
                    }
                    
                    if create_session:
                        result["session_created"] = True
                        
            except ClientError as e:
                result = {
                    "status": "error",
                    "message": f"Failed to connect to AWS: {str(e)}",
                    "connected": False,
                    "error_code": e.response['Error']['Code'],
                    "error_message": e.response['Error']['Message']
                }
            except ProfileNotFound:
                result = {
                    "status": "error",
                    "message": f"Profile '{profile_name}' does not exist",
                    "connected": False
                }
        else:
            result = {
                "status": "error",
                "message": f"Invalid action: {action}. Supported actions: validate, list, get_credentials, test_connection"
            }
            
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}",
            "error_type": type(e).__name__
        }
        return json.dumps(error_result, indent=2)