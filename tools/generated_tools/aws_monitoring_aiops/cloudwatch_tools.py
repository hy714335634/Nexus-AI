"""
AWS CloudWatch 工具集 - 提供与AWS CloudWatch API交互的功能，包括获取指标、告警和日志查询

该模块提供了一系列工具，用于与AWS CloudWatch API交互，获取指标数据、告警状态和查询日志。
工具集支持多区域监控，实现缓存机制减少API调用，并支持分批处理大量资源。
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(".cache/aws_monitoring_agent/cloudwatch")
# 缓存过期时间(秒)
METRICS_CACHE_TTL = 300  # 5分钟
ALARMS_CACHE_TTL = 180   # 3分钟
LOGS_CACHE_TTL = 600     # 10分钟

# 确保缓存目录存在
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_key(params: Dict[str, Any]) -> str:
    """生成缓存键"""
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.md5(params_str.encode()).hexdigest()

def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """获取缓存数据"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    
    try:
        data = json.loads(cache_file.read_text())
        if time.time() > data.get("expiry", 0):
            return None
        return data.get("result")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"缓存文件损坏: {e}")
        return None

def save_to_cache(cache_key: str, data: Dict[str, Any], ttl: int) -> None:
    """保存数据到缓存"""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    cache_data = {
        "result": data,
        "expiry": time.time() + ttl,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        cache_file.write_text(json.dumps(cache_data, default=str))
    except Exception as e:
        logger.warning(f"保存缓存失败: {e}")

def create_cloudwatch_client(region: str, profile_name: Optional[str] = None) -> Any:
    """创建CloudWatch客户端"""
    session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
    return session.client('cloudwatch', region_name=region)

def create_logs_client(region: str, profile_name: Optional[str] = None) -> Any:
    """创建CloudWatch Logs客户端"""
    session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
    return session.client('logs', region_name=region)

@tool
def verify_aws_credentials(region: str, profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    验证AWS凭证并测试CloudWatch API连接
    
    Args:
        region: AWS区域
        profile_name: AWS配置文件名称（可选）
        
    Returns:
        验证结果，包含状态和凭证信息
    """
    try:
        # 创建CloudWatch客户端
        cloudwatch = create_cloudwatch_client(region, profile_name)
        
        # 测试API连接 - 获取命名空间列表
        response = cloudwatch.list_metrics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            MaxItems=1
        )
        
        # 创建CloudWatch Logs客户端
        logs = create_logs_client(region, profile_name)
        
        # 测试Logs API连接 - 获取日志组列表
        logs_response = logs.describe_log_groups(
            limit=1
        )
        
        # 获取当前凭证信息
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        credentials = session.get_credentials()
        
        # 构建返回结果
        result = {
            "status": "success",
            "message": "AWS凭证验证成功，CloudWatch API连接正常",
            "region": region,
            "credential_type": "profile" if profile_name else "default",
            "profile_name": profile_name if profile_name else "default",
            "access_key_id": credentials.access_key[-4:] if credentials and credentials.access_key else "未知",
            "cloudwatch_api_status": "正常",
            "logs_api_status": "正常",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"AWS凭证验证失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "region": region,
            "profile_name": profile_name if profile_name else "default",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error_code == "InvalidClientTokenId":
            result["resolution"] = "请检查AWS Access Key是否有效"
        elif error_code == "AccessDenied":
            result["resolution"] = "请检查IAM权限是否包含CloudWatch和CloudWatch Logs访问权限"
        
        return result
    
    except BotoCoreError as e:
        result = {
            "status": "error",
            "message": f"AWS服务连接失败: {str(e)}",
            "error_type": "BotoCoreError",
            "region": region,
            "profile_name": profile_name if profile_name else "default",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolution": "请检查网络连接和区域设置"
        }
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"验证过程发生未知错误: {str(e)}",
            "error_type": type(e).__name__,
            "region": region,
            "profile_name": profile_name if profile_name else "default",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def get_cloudwatch_metrics(
    region: str,
    namespace: str,
    metric_name: str,
    dimensions: Optional[List[Dict[str, str]]] = None,
    period: int = 300,
    statistic: str = "Average",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    profile_name: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    获取CloudWatch指标数据
    
    Args:
        region: AWS区域
        namespace: CloudWatch命名空间（如'AWS/EC2', 'AWS/Lambda'等）
        metric_name: 指标名称（如'CPUUtilization', 'Invocations'等）
        dimensions: 指标维度列表，如[{"Name": "InstanceId", "Value": "i-1234abcd"}]
        period: 数据点之间的时间间隔（秒），默认300秒（5分钟）
        statistic: 统计类型（Average, Sum, Minimum, Maximum, SampleCount），默认Average
        start_time: 开始时间（ISO 8601格式），默认为当前时间前1小时
        end_time: 结束时间（ISO 8601格式），默认为当前时间
        profile_name: AWS配置文件名称（可选）
        use_cache: 是否使用缓存，默认为True
        
    Returns:
        指标数据，包含时间戳和对应的值
    """
    # 处理默认时间范围
    if not end_time:
        end_time_dt = datetime.now(timezone.utc)
    else:
        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    if not start_time:
        start_time_dt = end_time_dt - timedelta(hours=1)
    else:
        start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # 构建缓存参数
    cache_params = {
        "region": region,
        "namespace": namespace,
        "metric_name": metric_name,
        "dimensions": dimensions,
        "period": period,
        "statistic": statistic,
        "start_time": start_time_dt.isoformat(),
        "end_time": end_time_dt.isoformat()
    }
    
    cache_key = get_cache_key(cache_params)
    
    # 检查缓存
    if use_cache:
        cached_result = get_cached_data(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
    
    try:
        # 创建CloudWatch客户端
        cloudwatch = create_cloudwatch_client(region, profile_name)
        
        # 构建查询参数
        query_params = {
            'Namespace': namespace,
            'MetricName': metric_name,
            'StartTime': start_time_dt,
            'EndTime': end_time_dt,
            'Period': period,
            'Statistics': [statistic]
        }
        
        if dimensions:
            query_params['Dimensions'] = dimensions
        
        # 获取指标数据
        response = cloudwatch.get_metric_statistics(**query_params)
        
        # 处理结果
        datapoints = response.get('Datapoints', [])
        sorted_datapoints = sorted(datapoints, key=lambda x: x['Timestamp'])
        
        # 格式化数据点
        formatted_datapoints = []
        for dp in sorted_datapoints:
            formatted_datapoints.append({
                "timestamp": dp['Timestamp'].isoformat(),
                "value": dp.get(statistic),
                "unit": dp.get('Unit', 'None')
            })
        
        # 构建结果
        result = {
            "status": "success",
            "metric": {
                "namespace": namespace,
                "name": metric_name,
                "dimensions": dimensions or [],
                "statistic": statistic,
                "period": period
            },
            "datapoints": formatted_datapoints,
            "datapoints_count": len(formatted_datapoints),
            "time_range": {
                "start_time": start_time_dt.isoformat(),
                "end_time": end_time_dt.isoformat()
            },
            "region": region,
            "from_cache": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # 保存到缓存
        if use_cache:
            save_to_cache(cache_key, result, METRICS_CACHE_TTL)
        
        return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"获取指标数据失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "metric": {
                "namespace": namespace,
                "name": metric_name,
                "dimensions": dimensions or []
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"获取指标数据时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "metric": {
                "namespace": namespace,
                "name": metric_name,
                "dimensions": dimensions or []
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def get_cloudwatch_alarms(
    region: str,
    alarm_names: Optional[List[str]] = None,
    state_value: Optional[str] = None,
    alarm_types: Optional[List[str]] = None,
    profile_name: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    获取CloudWatch告警状态
    
    Args:
        region: AWS区域
        alarm_names: 告警名称列表（可选），如不提供则获取所有告警
        state_value: 告警状态过滤（可选）：OK, ALARM, INSUFFICIENT_DATA
        alarm_types: 告警类型过滤（可选）：CompositeAlarm, MetricAlarm
        profile_name: AWS配置文件名称（可选）
        use_cache: 是否使用缓存，默认为True
        
    Returns:
        告警状态信息，包含告警名称、状态、最后更新时间等
    """
    # 构建缓存参数
    cache_params = {
        "region": region,
        "alarm_names": alarm_names,
        "state_value": state_value,
        "alarm_types": alarm_types
    }
    
    cache_key = get_cache_key(cache_params)
    
    # 检查缓存
    if use_cache:
        cached_result = get_cached_data(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
    
    try:
        # 创建CloudWatch客户端
        cloudwatch = create_cloudwatch_client(region, profile_name)
        
        # 构建查询参数
        query_params = {}
        if alarm_names:
            query_params['AlarmNames'] = alarm_names
        if state_value:
            query_params['StateValue'] = state_value
        if alarm_types:
            query_params['AlarmTypes'] = alarm_types
        
        # 获取告警信息
        response = cloudwatch.describe_alarms(**query_params)
        
        # 处理结果
        composite_alarms = response.get('CompositeAlarms', [])
        metric_alarms = response.get('MetricAlarms', [])
        
        # 格式化复合告警
        formatted_composite_alarms = []
        for alarm in composite_alarms:
            formatted_composite_alarms.append({
                "name": alarm.get('AlarmName'),
                "description": alarm.get('AlarmDescription'),
                "state": alarm.get('StateValue'),
                "state_reason": alarm.get('StateReason'),
                "state_updated_timestamp": alarm.get('StateUpdatedTimestamp').isoformat() if alarm.get('StateUpdatedTimestamp') else None,
                "alarm_rule": alarm.get('AlarmRule'),
                "type": "CompositeAlarm",
                "actions_enabled": alarm.get('ActionsEnabled', False)
            })
        
        # 格式化指标告警
        formatted_metric_alarms = []
        for alarm in metric_alarms:
            formatted_metric_alarms.append({
                "name": alarm.get('AlarmName'),
                "description": alarm.get('AlarmDescription'),
                "state": alarm.get('StateValue'),
                "state_reason": alarm.get('StateReason'),
                "state_updated_timestamp": alarm.get('StateUpdatedTimestamp').isoformat() if alarm.get('StateUpdatedTimestamp') else None,
                "namespace": alarm.get('Namespace'),
                "metric_name": alarm.get('MetricName'),
                "dimensions": alarm.get('Dimensions', []),
                "period": alarm.get('Period'),
                "statistic": alarm.get('Statistic'),
                "comparison_operator": alarm.get('ComparisonOperator'),
                "threshold": alarm.get('Threshold'),
                "evaluation_periods": alarm.get('EvaluationPeriods'),
                "type": "MetricAlarm",
                "actions_enabled": alarm.get('ActionsEnabled', False)
            })
        
        # 构建结果
        result = {
            "status": "success",
            "alarms": {
                "composite_alarms": formatted_composite_alarms,
                "metric_alarms": formatted_metric_alarms,
                "total_count": len(formatted_composite_alarms) + len(formatted_metric_alarms)
            },
            "filters": {
                "alarm_names": alarm_names,
                "state_value": state_value,
                "alarm_types": alarm_types
            },
            "region": region,
            "from_cache": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # 保存到缓存
        if use_cache:
            save_to_cache(cache_key, result, ALARMS_CACHE_TTL)
        
        return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"获取告警状态失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "filters": {
                "alarm_names": alarm_names,
                "state_value": state_value,
                "alarm_types": alarm_types
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"获取告警状态时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "filters": {
                "alarm_names": alarm_names,
                "state_value": state_value,
                "alarm_types": alarm_types
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def query_cloudwatch_logs(
    region: str,
    log_group_name: str,
    query_string: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    wait_for_results: bool = True,
    profile_name: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    查询CloudWatch Logs并获取日志数据
    
    Args:
        region: AWS区域
        log_group_name: 日志组名称
        query_string: CloudWatch Logs Insights查询语句
        start_time: 开始时间（ISO 8601格式），默认为当前时间前1小时
        end_time: 结束时间（ISO 8601格式），默认为当前时间
        limit: 返回结果的最大数量，默认100
        wait_for_results: 是否等待查询完成，默认True
        profile_name: AWS配置文件名称（可选）
        use_cache: 是否使用缓存，默认为True
        
    Returns:
        查询结果，包含日志数据和查询统计信息
    """
    # 处理默认时间范围
    if not end_time:
        end_time_dt = datetime.now(timezone.utc)
    else:
        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    if not start_time:
        start_time_dt = end_time_dt - timedelta(hours=1)
    else:
        start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # 转换为毫秒时间戳
    start_time_ms = int(start_time_dt.timestamp() * 1000)
    end_time_ms = int(end_time_dt.timestamp() * 1000)
    
    # 构建缓存参数
    cache_params = {
        "region": region,
        "log_group_name": log_group_name,
        "query_string": query_string,
        "start_time": start_time_dt.isoformat(),
        "end_time": end_time_dt.isoformat(),
        "limit": limit
    }
    
    cache_key = get_cache_key(cache_params)
    
    # 检查缓存
    if use_cache:
        cached_result = get_cached_data(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
    
    try:
        # 创建CloudWatch Logs客户端
        logs = create_logs_client(region, profile_name)
        
        # 开始查询
        start_query_response = logs.start_query(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            queryString=query_string,
            limit=limit
        )
        
        query_id = start_query_response['queryId']
        
        # 如果不等待结果，直接返回查询ID
        if not wait_for_results:
            result = {
                "status": "pending",
                "message": "查询已启动，但未等待结果",
                "query_id": query_id,
                "log_group": log_group_name,
                "query_string": query_string,
                "time_range": {
                    "start_time": start_time_dt.isoformat(),
                    "end_time": end_time_dt.isoformat()
                },
                "region": region,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return result
        
        # 等待查询完成
        query_status = "Running"
        max_attempts = 60  # 最多等待60次
        attempt = 0
        
        while query_status == "Running" and attempt < max_attempts:
            time.sleep(1)  # 等待1秒
            attempt += 1
            
            query_results = logs.get_query_results(
                queryId=query_id
            )
            
            query_status = query_results['status']
        
        # 处理查询结果
        if query_status == "Complete":
            # 格式化结果
            formatted_results = []
            for result in query_results.get('results', []):
                result_item = {}
                for field in result:
                    result_item[field['field']] = field['value']
                formatted_results.append(result_item)
            
            # 构建结果
            result = {
                "status": "success",
                "query_status": query_status,
                "query_id": query_id,
                "log_group": log_group_name,
                "query_string": query_string,
                "time_range": {
                    "start_time": start_time_dt.isoformat(),
                    "end_time": end_time_dt.isoformat()
                },
                "results": formatted_results,
                "result_count": len(formatted_results),
                "statistics": {
                    "records_matched": query_results.get('statistics', {}).get('recordsMatched', 0),
                    "records_scanned": query_results.get('statistics', {}).get('recordsScanned', 0),
                    "bytes_scanned": query_results.get('statistics', {}).get('bytesScanned', 0)
                },
                "region": region,
                "from_cache": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # 保存到缓存
            if use_cache:
                save_to_cache(cache_key, result, LOGS_CACHE_TTL)
            
            return result
        else:
            # 查询未完成
            result = {
                "status": "error",
                "message": f"查询未在预期时间内完成，当前状态: {query_status}",
                "query_id": query_id,
                "query_status": query_status,
                "log_group": log_group_name,
                "time_range": {
                    "start_time": start_time_dt.isoformat(),
                    "end_time": end_time_dt.isoformat()
                },
                "region": region,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"查询日志失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "log_group": log_group_name,
            "query_string": query_string,
            "time_range": {
                "start_time": start_time_dt.isoformat(),
                "end_time": end_time_dt.isoformat()
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error_code == "ResourceNotFoundException":
            result["resolution"] = f"日志组 '{log_group_name}' 不存在，请检查名称"
        elif error_code == "InvalidParameterException":
            result["resolution"] = "查询语句格式错误，请检查语法"
        
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"查询日志时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "log_group": log_group_name,
            "query_string": query_string,
            "time_range": {
                "start_time": start_time_dt.isoformat(),
                "end_time": end_time_dt.isoformat()
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def get_cloudwatch_log_groups(
    region: str,
    name_prefix: Optional[str] = None,
    limit: int = 50,
    profile_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取CloudWatch日志组列表
    
    Args:
        region: AWS区域
        name_prefix: 日志组名称前缀过滤（可选）
        limit: 返回结果的最大数量，默认50
        profile_name: AWS配置文件名称（可选）
        
    Returns:
        日志组列表，包含名称、创建时间等信息
    """
    try:
        # 创建CloudWatch Logs客户端
        logs = create_logs_client(region, profile_name)
        
        # 构建查询参数
        query_params = {
            'limit': limit
        }
        
        if name_prefix:
            query_params['logGroupNamePrefix'] = name_prefix
        
        # 获取日志组列表
        response = logs.describe_log_groups(**query_params)
        
        # 处理结果
        log_groups = response.get('logGroups', [])
        
        # 格式化日志组
        formatted_log_groups = []
        for log_group in log_groups:
            formatted_log_groups.append({
                "name": log_group.get('logGroupName'),
                "arn": log_group.get('arn'),
                "creation_time": datetime.fromtimestamp(log_group.get('creationTime', 0) / 1000, timezone.utc).isoformat(),
                "retention_days": log_group.get('retentionInDays'),
                "stored_bytes": log_group.get('storedBytes', 0),
                "metric_filter_count": log_group.get('metricFilterCount', 0)
            })
        
        # 构建结果
        result = {
            "status": "success",
            "log_groups": formatted_log_groups,
            "count": len(formatted_log_groups),
            "filters": {
                "name_prefix": name_prefix
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"获取日志组列表失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "filters": {
                "name_prefix": name_prefix
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"获取日志组列表时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "filters": {
                "name_prefix": name_prefix
            },
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def batch_get_metrics(
    region: str,
    resources: List[Dict[str, Any]],
    period: int = 300,
    statistic: str = "Average",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    batch_size: int = 5,
    profile_name: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    批量获取多个资源的CloudWatch指标数据
    
    Args:
        region: AWS区域
        resources: 资源列表，每个资源包含namespace、metric_name和dimensions
                  格式: [{"namespace": "AWS/EC2", "metric_name": "CPUUtilization", 
                         "dimensions": [{"Name": "InstanceId", "Value": "i-1234abcd"}]}]
        period: 数据点之间的时间间隔（秒），默认300秒（5分钟）
        statistic: 统计类型（Average, Sum, Minimum, Maximum, SampleCount），默认Average
        start_time: 开始时间（ISO 8601格式），默认为当前时间前1小时
        end_time: 结束时间（ISO 8601格式），默认为当前时间
        batch_size: 每批处理的资源数量，默认5
        profile_name: AWS配置文件名称（可选）
        use_cache: 是否使用缓存，默认为True
        
    Returns:
        多个资源的指标数据
    """
    # 处理默认时间范围
    if not end_time:
        end_time_dt = datetime.now(timezone.utc)
    else:
        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    
    if not start_time:
        start_time_dt = end_time_dt - timedelta(hours=1)
    else:
        start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    
    # 结果集
    results = []
    errors = []
    
    # 分批处理资源
    for i in range(0, len(resources), batch_size):
        batch = resources[i:i+batch_size]
        
        for resource in batch:
            try:
                # 获取单个资源的指标数据
                metric_result = get_cloudwatch_metrics(
                    region=region,
                    namespace=resource.get('namespace'),
                    metric_name=resource.get('metric_name'),
                    dimensions=resource.get('dimensions'),
                    period=period,
                    statistic=statistic,
                    start_time=start_time_dt.isoformat(),
                    end_time=end_time_dt.isoformat(),
                    profile_name=profile_name,
                    use_cache=use_cache
                )
                
                # 添加资源标识信息
                if "resource_id" in resource:
                    metric_result["resource_id"] = resource["resource_id"]
                if "resource_type" in resource:
                    metric_result["resource_type"] = resource["resource_type"]
                
                # 添加到结果集
                if metric_result.get("status") == "success":
                    results.append(metric_result)
                else:
                    errors.append(metric_result)
            
            except Exception as e:
                error_result = {
                    "status": "error",
                    "message": f"处理资源指标时发生错误: {str(e)}",
                    "error_type": type(e).__name__,
                    "resource": resource,
                    "region": region,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                errors.append(error_result)
    
    # 构建结果
    result = {
        "status": "success" if not errors else "partial_success" if results else "error",
        "metrics_results": results,
        "success_count": len(results),
        "error_count": len(errors),
        "errors": errors if errors else None,
        "time_range": {
            "start_time": start_time_dt.isoformat(),
            "end_time": end_time_dt.isoformat()
        },
        "region": region,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result

@tool
def multi_region_get_alarms(
    regions: List[str],
    state_value: Optional[str] = "ALARM",
    alarm_types: Optional[List[str]] = None,
    profile_name: Optional[str] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    从多个AWS区域获取告警状态
    
    Args:
        regions: AWS区域列表
        state_value: 告警状态过滤（可选）：OK, ALARM, INSUFFICIENT_DATA，默认ALARM
        alarm_types: 告警类型过滤（可选）：CompositeAlarm, MetricAlarm
        profile_name: AWS配置文件名称（可选）
        use_cache: 是否使用缓存，默认为True
        
    Returns:
        多个区域的告警状态信息
    """
    # 结果集
    results = {}
    errors = []
    total_alarms = 0
    
    # 处理每个区域
    for region in regions:
        try:
            # 获取区域的告警
            region_result = get_cloudwatch_alarms(
                region=region,
                state_value=state_value,
                alarm_types=alarm_types,
                profile_name=profile_name,
                use_cache=use_cache
            )
            
            # 添加到结果集
            if region_result.get("status") == "success":
                results[region] = region_result
                
                # 累计告警数量
                if "alarms" in region_result:
                    total_alarms += region_result["alarms"].get("total_count", 0)
            else:
                errors.append({
                    "region": region,
                    "error": region_result
                })
        
        except Exception as e:
            error_result = {
                "region": region,
                "error": {
                    "status": "error",
                    "message": f"处理区域告警时发生错误: {str(e)}",
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            errors.append(error_result)
    
    # 构建结果
    result = {
        "status": "success" if not errors else "partial_success" if results else "error",
        "regions_processed": len(regions),
        "regions_succeeded": len(results),
        "regions_failed": len(errors),
        "total_alarms": total_alarms,
        "region_results": results,
        "errors": errors if errors else None,
        "filters": {
            "state_value": state_value,
            "alarm_types": alarm_types
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result

@tool
def clear_cloudwatch_cache() -> Dict[str, Any]:
    """
    清除CloudWatch工具集的缓存数据
    
    Returns:
        清除结果信息
    """
    try:
        # 获取缓存文件列表
        cache_files = list(CACHE_DIR.glob("*.json"))
        file_count = len(cache_files)
        
        # 删除所有缓存文件
        for cache_file in cache_files:
            cache_file.unlink()
        
        # 构建结果
        result = {
            "status": "success",
            "message": f"成功清除 {file_count} 个缓存文件",
            "cache_directory": str(CACHE_DIR),
            "files_cleared": file_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"清除缓存时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "cache_directory": str(CACHE_DIR),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result