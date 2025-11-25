"""
日志分析工具集 - 提供CloudWatch日志分析功能，包括解析、过滤、提取关键信息和错误模式识别

该模块提供了一系列工具，用于分析CloudWatch日志，提取关键错误信息，识别常见错误模式，
执行时间序列关联分析，并集成LLM进行复杂日志理解。
"""

import os
import re
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from strands import tool

# 设置日志分析缓存目录
LOG_ANALYSIS_CACHE_DIR = Path(".cache/aws_monitoring_agent/log_analysis")
LOG_ANALYSIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 常见错误模式定义
ERROR_PATTERNS = {
    "exception": r"(?i)exception|error|failure|failed|traceback",
    "timeout": r"(?i)timeout|timed?\s*out|connection.*?timed?\s*out",
    "memory": r"(?i)(out\s*of\s*memory)|(memory\s*limit)|(insufficient\s*memory)",
    "permission": r"(?i)(access\s*denied)|(permission\s*denied)|(not\s*authorized)|(forbidden)",
    "throttling": r"(?i)(throttl(ed|ing))|(rate\s*exceed(ed)?)|(too\s*many\s*requests)",
    "connection": r"(?i)(connection\s*(refused|reset|closed|abort))|(unable\s*to\s*connect)",
    "resource": r"(?i)(resource\s*not\s*found)|(does\s*not\s*exist)|(404\s*not\s*found)",
    "configuration": r"(?i)(invalid\s*configuration)|(config.*?error)|(parameter.*?invalid)",
    "dependency": r"(?i)(dependency.*?(missing|failed))|(module.*?not\s*found)",
    "disk": r"(?i)(disk\s*full)|(no\s*space\s*left)|(i/o\s*error)"
}

# 服务特定错误模式
SERVICE_ERROR_PATTERNS = {
    "EC2": {
        "instance_termination": r"(?i)(instance.*?terminat(ed|ing))|(shutting\s*down)",
        "capacity": r"(?i)(insufficient\s*capacity)|(no\s*capacity\s*available)",
        "ami": r"(?i)(ami.*?not\s*found)|(image.*?not\s*available)",
        "network": r"(?i)(network.*?error)|(vpc.*?not\s*found)|(subnet.*?invalid)"
    },
    "Lambda": {
        "timeout": r"(?i)(task\s*timed\s*out)|(execution\s*timed\s*out)",
        "memory": r"(?i)(memory\s*size\s*exceeded)|(out\s*of\s*memory)",
        "cold_start": r"(?i)(cold\s*start)|(init\s*duration)",
        "permission": r"(?i)(role.*?not.*?assume)|(policy.*?not.*?allow)"
    },
    "RDS": {
        "connection_limit": r"(?i)(too\s*many\s*connections)|(max_connections)",
        "storage": r"(?i)(storage\s*full)|(out\s*of\s*storage\s*space)",
        "backup": r"(?i)(backup.*?failed)|(snapshot.*?error)",
        "replication": r"(?i)(replication.*?broken)|(replica.*?lag)"
    },
    "S3": {
        "access": r"(?i)(access\s*denied)|(403\s*forbidden)",
        "throttling": r"(?i)(slow\s*down)|(request\s*rate)",
        "consistency": r"(?i)(eventual\s*consistency)|(propagation\s*delay)"
    },
    "DynamoDB": {
        "throughput": r"(?i)(provisioned\s*throughput\s*exceeded)|(throttling)",
        "hot_key": r"(?i)(hot\s*key)|(hot\s*partition)",
        "item_size": r"(?i)(item\s*size.*?exceeded)|(too\s*large)"
    }
}

# 日志级别模式
LOG_LEVEL_PATTERNS = {
    "error": r"(?i)(^|\s)ERROR(\s|:|\]|\[|$)",
    "warn": r"(?i)(^|\s)WARN(ING)?(\s|:|\]|\[|$)",
    "info": r"(?i)(^|\s)INFO(\s|:|\]|\[|$)",
    "debug": r"(?i)(^|\s)DEBUG(\s|:|\]|\[|$)",
    "trace": r"(?i)(^|\s)TRACE(\s|:|\]|\[|$)",
    "fatal": r"(?i)(^|\s)FATAL(\s|:|\]|\[|$)",
    "critical": r"(?i)(^|\s)CRITICAL(\s|:|\]|\[|$)"
}

# 堆栈跟踪模式
STACK_TRACE_PATTERNS = {
    "java": r"(?s)(\w+\.)+\w+Exception.*?at\s+(\w+\.)+\w+\(.*?\.java:\d+\)(\s+at\s+(\w+\.)+\w+\(.*?\.java:\d+\))*",
    "python": r"(?s)Traceback \(most recent call last\):.*?(?:^\w+Error|^\w+Exception).*?$",
    "node": r"(?s)Error:.*?at\s+.*?\(.*?:\d+:\d+\)(\s+at\s+.*?\(.*?:\d+:\d+\))*",
    "dotnet": r"(?s)System\.\w+Exception:.*?at\s+[\w\.]+\(.*?\)(\s+at\s+[\w\.]+\(.*?\))*"
}

@tool
def parse_filter_logs(
    logs_data: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    解析和过滤CloudWatch日志
    
    Args:
        logs_data: CloudWatch日志数据，通常是query_cloudwatch_logs的结果
        filters: 过滤条件，可包含以下字段：
                 - log_levels: 日志级别列表，如["error", "warn"]
                 - keywords: 关键词列表
                 - time_range: 时间范围，格式为{"start": "ISO时间", "end": "ISO时间"}
                 - exclude_patterns: 要排除的模式列表
        max_results: 返回结果的最大数量，默认100
        
    Returns:
        过滤后的日志数据，包含统计信息
    """
    # 验证输入
    if not isinstance(logs_data, dict):
        return {
            "status": "error",
            "message": "logs_data必须是字典类型",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取日志结果
    log_results = logs_data.get("results", [])
    if not log_results:
        return {
            "status": "success",
            "message": "没有找到日志数据",
            "filtered_logs": [],
            "total_logs": 0,
            "filtered_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 初始化过滤器
    filters = filters or {}
    log_levels = filters.get("log_levels", [])
    keywords = filters.get("keywords", [])
    time_range = filters.get("time_range", {})
    exclude_patterns = filters.get("exclude_patterns", [])
    
    # 处理时间范围
    start_time = None
    end_time = None
    if time_range:
        if "start" in time_range:
            try:
                start_time = datetime.fromisoformat(time_range["start"].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        if "end" in time_range:
            try:
                end_time = datetime.fromisoformat(time_range["end"].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
    
    # 编译排除模式
    exclude_regex = None
    if exclude_patterns:
        try:
            exclude_regex = re.compile("|".join(exclude_patterns), re.IGNORECASE)
        except re.error:
            pass
    
    # 过滤日志
    filtered_logs = []
    for log in log_results:
        # 检查是否有消息字段
        message = log.get("@message", log.get("message", ""))
        if not message:
            continue
        
        # 检查时间戳
        timestamp_str = log.get("@timestamp", log.get("timestamp", ""))
        if timestamp_str and (start_time or end_time):
            try:
                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
            except (ValueError, TypeError):
                pass
        
        # 检查日志级别
        if log_levels:
            level_match = False
            for level in log_levels:
                if level.lower() in LOG_LEVEL_PATTERNS:
                    if re.search(LOG_LEVEL_PATTERNS[level.lower()], message):
                        level_match = True
                        break
            if not level_match:
                continue
        
        # 检查关键词
        if keywords:
            keyword_match = False
            for keyword in keywords:
                if keyword.lower() in message.lower():
                    keyword_match = True
                    break
            if not keyword_match:
                continue
        
        # 检查排除模式
        if exclude_regex and exclude_regex.search(message):
            continue
        
        # 添加到过滤结果
        filtered_logs.append(log)
        
        # 检查是否达到最大结果数
        if len(filtered_logs) >= max_results:
            break
    
    # 构建结果
    result = {
        "status": "success",
        "filtered_logs": filtered_logs,
        "total_logs": len(log_results),
        "filtered_count": len(filtered_logs),
        "filters_applied": {
            "log_levels": log_levels,
            "keywords": keywords,
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None
            },
            "exclude_patterns": exclude_patterns
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result

@tool
def extract_error_info(
    logs_data: Dict[str, Any],
    extract_stack_trace: bool = True,
    group_similar_errors: bool = True,
    service_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    从日志中提取关键错误信息和堆栈跟踪
    
    Args:
        logs_data: CloudWatch日志数据，通常是parse_filter_logs的结果
        extract_stack_trace: 是否提取堆栈跟踪，默认为True
        group_similar_errors: 是否对相似错误进行分组，默认为True
        service_type: AWS服务类型，用于应用特定的错误模式（可选）：EC2, Lambda, RDS, S3, DynamoDB
        
    Returns:
        提取的错误信息，包含错误类型、消息和堆栈跟踪
    """
    # 验证输入
    if not isinstance(logs_data, dict):
        return {
            "status": "error",
            "message": "logs_data必须是字典类型",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取日志结果
    log_entries = logs_data.get("filtered_logs", logs_data.get("results", []))
    if not log_entries:
        return {
            "status": "success",
            "message": "没有找到日志数据",
            "errors": [],
            "error_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 初始化错误列表和错误指纹映射
    errors = []
    error_fingerprints = {}
    
    # 选择错误模式
    patterns = ERROR_PATTERNS.copy()
    if service_type and service_type in SERVICE_ERROR_PATTERNS:
        patterns.update(SERVICE_ERROR_PATTERNS[service_type])
    
    # 处理每个日志条目
    for log in log_entries:
        # 获取消息和时间戳
        message = log.get("@message", log.get("message", ""))
        timestamp_str = log.get("@timestamp", log.get("timestamp", ""))
        
        if not message:
            continue
        
        # 初始化错误信息
        error_info = {
            "timestamp": timestamp_str,
            "error_type": None,
            "error_message": None,
            "stack_trace": None,
            "log_entry": log
        }
        
        # 检查错误模式
        for error_type, pattern in patterns.items():
            match = re.search(pattern, message)
            if match:
                error_info["error_type"] = error_type
                # 提取错误消息（匹配行或附近内容）
                error_line = message.split("\n")[match.start() // len(message.split("\n")[0])] if "\n" in message else message
                error_info["error_message"] = error_line.strip()
                break
        
        # 如果没有找到错误类型，继续下一个日志
        if not error_info["error_type"]:
            continue
        
        # 提取堆栈跟踪
        if extract_stack_trace:
            for lang, pattern in STACK_TRACE_PATTERNS.items():
                stack_match = re.search(pattern, message)
                if stack_match:
                    error_info["stack_trace"] = stack_match.group(0)
                    break
        
        # 生成错误指纹（用于分组相似错误）
        if group_similar_errors:
            # 使用错误类型和消息的前50个字符作为指纹
            error_msg = error_info["error_message"] or ""
            fingerprint = f"{error_info['error_type']}:{error_msg[:50]}"
            
            if fingerprint in error_fingerprints:
                # 更新现有错误组
                error_fingerprints[fingerprint]["occurrences"].append({
                    "timestamp": timestamp_str,
                    "log_entry_id": log.get("@id", log.get("id", ""))
                })
                error_fingerprints[fingerprint]["count"] += 1
            else:
                # 创建新的错误组
                error_fingerprints[fingerprint] = {
                    "error_type": error_info["error_type"],
                    "error_message": error_info["error_message"],
                    "stack_trace": error_info["stack_trace"],
                    "first_occurrence": timestamp_str,
                    "occurrences": [{
                        "timestamp": timestamp_str,
                        "log_entry_id": log.get("@id", log.get("id", ""))
                    }],
                    "count": 1,
                    "sample_log": log
                }
        else:
            # 不分组，直接添加到错误列表
            errors.append(error_info)
    
    # 构建结果
    if group_similar_errors:
        # 将错误组转换为列表
        grouped_errors = list(error_fingerprints.values())
        # 按出现次数排序
        grouped_errors.sort(key=lambda x: x["count"], reverse=True)
        
        result = {
            "status": "success",
            "errors": grouped_errors,
            "error_count": len(grouped_errors),
            "total_occurrences": sum(e["count"] for e in grouped_errors),
            "grouping": "similar_errors",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    else:
        # 按时间戳排序
        errors.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
        
        result = {
            "status": "success",
            "errors": errors,
            "error_count": len(errors),
            "grouping": "none",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return result

@tool
def identify_error_patterns(
    logs_data: Dict[str, Any],
    time_window_minutes: int = 60,
    min_occurrence: int = 2,
    service_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    识别日志中的常见错误模式
    
    Args:
        logs_data: CloudWatch日志数据，通常是parse_filter_logs的结果
        time_window_minutes: 时间窗口（分钟），用于识别时间相关模式，默认60分钟
        min_occurrence: 最小出现次数，用于识别重复模式，默认2次
        service_type: AWS服务类型，用于应用特定的错误模式（可选）：EC2, Lambda, RDS, S3, DynamoDB
        
    Returns:
        识别的错误模式，包含模式类型、频率和示例
    """
    # 验证输入
    if not isinstance(logs_data, dict):
        return {
            "status": "error",
            "message": "logs_data必须是字典类型",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取日志结果
    log_entries = logs_data.get("filtered_logs", logs_data.get("results", []))
    if not log_entries:
        return {
            "status": "success",
            "message": "没有找到日志数据",
            "patterns": [],
            "pattern_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 提取错误信息
    error_info = extract_error_info(logs_data, extract_stack_trace=True, group_similar_errors=True, service_type=service_type)
    
    if error_info.get("status") != "success" or not error_info.get("errors"):
        return {
            "status": "success",
            "message": "没有找到错误信息",
            "patterns": [],
            "pattern_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取分组的错误
    grouped_errors = error_info.get("errors", [])
    
    # 初始化模式列表
    patterns = []
    
    # 处理每个错误组
    for error_group in grouped_errors:
        # 跳过低于最小出现次数的错误
        if error_group.get("count", 0) < min_occurrence:
            continue
        
        # 获取错误类型和消息
        error_type = error_group.get("error_type")
        error_message = error_group.get("error_message")
        
        if not error_type or not error_message:
            continue
        
        # 分析时间模式
        occurrences = error_group.get("occurrences", [])
        if len(occurrences) >= min_occurrence:
            # 转换时间戳为datetime对象
            timestamps = []
            for occurrence in occurrences:
                ts_str = occurrence.get("timestamp")
                if ts_str:
                    try:
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        timestamps.append(ts)
                    except (ValueError, TypeError):
                        pass
            
            # 排序时间戳
            timestamps.sort()
            
            # 检查是否在时间窗口内有多次出现
            if len(timestamps) >= 2:
                time_clusters = []
                current_cluster = [timestamps[0]]
                
                for i in range(1, len(timestamps)):
                    if (timestamps[i] - current_cluster[-1]).total_seconds() <= time_window_minutes * 60:
                        current_cluster.append(timestamps[i])
                    else:
                        if len(current_cluster) >= min_occurrence:
                            time_clusters.append(current_cluster)
                        current_cluster = [timestamps[i]]
                
                if len(current_cluster) >= min_occurrence:
                    time_clusters.append(current_cluster)
                
                # 添加时间模式
                for cluster in time_clusters:
                    duration = (cluster[-1] - cluster[0]).total_seconds() / 60
                    frequency = len(cluster) / duration if duration > 0 else 0
                    
                    patterns.append({
                        "pattern_type": "time_cluster",
                        "error_type": error_type,
                        "error_message": error_message,
                        "occurrences": len(cluster),
                        "start_time": cluster[0].isoformat(),
                        "end_time": cluster[-1].isoformat(),
                        "duration_minutes": round(duration, 2),
                        "frequency_per_minute": round(frequency, 4),
                        "sample_log": error_group.get("sample_log")
                    })
        
        # 添加频率模式
        if error_group.get("count", 0) >= min_occurrence:
            patterns.append({
                "pattern_type": "frequency",
                "error_type": error_type,
                "error_message": error_message,
                "occurrences": error_group.get("count", 0),
                "first_occurrence": error_group.get("first_occurrence"),
                "stack_trace": error_group.get("stack_trace"),
                "sample_log": error_group.get("sample_log")
            })
    
    # 按出现次数排序
    patterns.sort(key=lambda x: x["occurrences"], reverse=True)
    
    # 构建结果
    result = {
        "status": "success",
        "patterns": patterns,
        "pattern_count": len(patterns),
        "analysis_parameters": {
            "time_window_minutes": time_window_minutes,
            "min_occurrence": min_occurrence,
            "service_type": service_type
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result

@tool
def time_series_correlation(
    metrics_data: Dict[str, Any],
    logs_data: Dict[str, Any],
    time_window_minutes: int = 10
) -> Dict[str, Any]:
    """
    执行时间序列关联分析，关联指标异常和日志事件
    
    Args:
        metrics_data: CloudWatch指标数据，通常是get_cloudwatch_metrics的结果
        logs_data: CloudWatch日志数据，通常是parse_filter_logs的结果
        time_window_minutes: 关联的时间窗口（分钟），默认10分钟
        
    Returns:
        时间序列关联分析结果，包含关联事件和时间线
    """
    # 验证输入
    if not isinstance(metrics_data, dict) or not isinstance(logs_data, dict):
        return {
            "status": "error",
            "message": "metrics_data和logs_data必须是字典类型",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取指标数据点
    datapoints = metrics_data.get("datapoints", [])
    if not datapoints:
        return {
            "status": "error",
            "message": "没有找到指标数据点",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取日志条目
    log_entries = logs_data.get("filtered_logs", logs_data.get("results", []))
    if not log_entries:
        return {
            "status": "error",
            "message": "没有找到日志数据",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 提取指标信息
    metric_info = metrics_data.get("metric", {})
    metric_name = metric_info.get("name", "未知指标")
    metric_namespace = metric_info.get("namespace", "未知命名空间")
    metric_dimensions = metric_info.get("dimensions", [])
    metric_statistic = metric_info.get("statistic", "Average")
    
    # 转换指标数据点为时间序列
    metric_series = []
    for dp in datapoints:
        timestamp_str = dp.get("timestamp")
        value = dp.get("value")
        
        if timestamp_str and value is not None:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                metric_series.append({
                    "timestamp": timestamp,
                    "value": value,
                    "type": "metric"
                })
            except (ValueError, TypeError):
                pass
    
    # 排序指标时间序列
    metric_series.sort(key=lambda x: x["timestamp"])
    
    # 转换日志条目为时间序列
    log_series = []
    for log in log_entries:
        timestamp_str = log.get("@timestamp", log.get("timestamp"))
        message = log.get("@message", log.get("message", ""))
        
        if timestamp_str and message:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # 检查是否为错误日志
                is_error = False
                for pattern in ERROR_PATTERNS.values():
                    if re.search(pattern, message):
                        is_error = True
                        break
                
                log_series.append({
                    "timestamp": timestamp,
                    "message": message[:200] + ("..." if len(message) > 200 else ""),
                    "is_error": is_error,
                    "log_entry_id": log.get("@id", log.get("id", "")),
                    "type": "log"
                })
            except (ValueError, TypeError):
                pass
    
    # 排序日志时间序列
    log_series.sort(key=lambda x: x["timestamp"])
    
    # 合并时间序列并排序
    combined_series = metric_series + log_series
    combined_series.sort(key=lambda x: x["timestamp"])
    
    # 查找指标异常
    anomalies = []
    if len(metric_series) >= 2:
        # 计算简单的移动平均和标准差
        window_size = min(5, len(metric_series))
        values = [dp["value"] for dp in metric_series]
        
        for i in range(window_size, len(metric_series)):
            window = values[i-window_size:i]
            avg = sum(window) / len(window)
            std_dev = (sum((x - avg) ** 2 for x in window) / len(window)) ** 0.5
            
            # 如果值超出3个标准差，认为是异常
            if abs(values[i] - avg) > 3 * std_dev and std_dev > 0:
                anomalies.append({
                    "timestamp": metric_series[i]["timestamp"],
                    "value": values[i],
                    "avg": avg,
                    "std_dev": std_dev,
                    "deviation": abs(values[i] - avg) / std_dev if std_dev > 0 else 0
                })
    
    # 查找关联事件
    correlations = []
    for anomaly in anomalies:
        anomaly_time = anomaly["timestamp"]
        
        # 查找时间窗口内的日志事件
        window_start = anomaly_time - timedelta(minutes=time_window_minutes)
        window_end = anomaly_time + timedelta(minutes=time_window_minutes)
        
        related_logs = []
        for log in log_series:
            if window_start <= log["timestamp"] <= window_end:
                related_logs.append(log)
        
        # 如果有关联日志，添加到关联列表
        if related_logs:
            correlations.append({
                "anomaly": {
                    "timestamp": anomaly_time.isoformat(),
                    "value": anomaly["value"],
                    "deviation": anomaly["deviation"]
                },
                "related_logs": related_logs,
                "log_count": len(related_logs),
                "error_log_count": sum(1 for log in related_logs if log.get("is_error", False)),
                "time_window": {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat()
                }
            })
    
    # 构建时间线
    timeline = []
    for event in combined_series:
        event_type = event["type"]
        timestamp = event["timestamp"]
        
        timeline_event = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type
        }
        
        if event_type == "metric":
            # 检查是否为异常
            is_anomaly = any(abs((timestamp - a["timestamp"]).total_seconds()) < 1 for a in anomalies)
            
            timeline_event.update({
                "value": event["value"],
                "is_anomaly": is_anomaly
            })
        else:  # log
            timeline_event.update({
                "message": event["message"],
                "is_error": event.get("is_error", False),
                "log_entry_id": event.get("log_entry_id", "")
            })
        
        timeline.append(timeline_event)
    
    # 构建结果
    result = {
        "status": "success",
        "metric": {
            "name": metric_name,
            "namespace": metric_namespace,
            "dimensions": metric_dimensions,
            "statistic": metric_statistic
        },
        "anomalies": [
            {
                "timestamp": a["timestamp"].isoformat(),
                "value": a["value"],
                "deviation": a["deviation"]
            } for a in anomalies
        ],
        "correlations": correlations,
        "timeline": timeline,
        "analysis_parameters": {
            "time_window_minutes": time_window_minutes
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result

@tool
def analyze_logs_with_llm(
    logs_data: Dict[str, Any],
    query: str,
    max_logs: int = 10,
    region: str = "us-east-1",
    profile_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    使用AWS Bedrock LLM分析复杂日志内容
    
    Args:
        logs_data: CloudWatch日志数据，通常是parse_filter_logs的结果
        query: 分析查询，描述需要LLM分析的内容
        max_logs: 发送给LLM的最大日志条数，默认10
        region: AWS Bedrock区域，默认us-east-1
        profile_name: AWS配置文件名称（可选）
        
    Returns:
        LLM分析结果，包含问题描述、根因分析和建议操作
    """
    # 验证输入
    if not isinstance(logs_data, dict):
        return {
            "status": "error",
            "message": "logs_data必须是字典类型",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 获取日志条目
    log_entries = logs_data.get("filtered_logs", logs_data.get("results", []))
    if not log_entries:
        return {
            "status": "error",
            "message": "没有找到日志数据",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # 限制日志条数
    selected_logs = log_entries[:max_logs]
    
    try:
        # 创建Bedrock客户端
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        bedrock_runtime = session.client(
            service_name='bedrock-runtime',
            region_name=region
        )
        
        # 准备日志文本
        logs_text = ""
        for i, log in enumerate(selected_logs):
            message = log.get("@message", log.get("message", ""))
            timestamp = log.get("@timestamp", log.get("timestamp", ""))
            logs_text += f"[{i+1}] {timestamp}: {message}\n\n"
        
        # 构建提示
        prompt = f"""
        请分析以下AWS服务日志，并回答问题："{query}"
        
        日志内容：
        {logs_text}
        
        请提供：
        1. 问题描述：简要描述日志中显示的问题
        2. 根因分析：分析可能的根本原因
        3. 建议操作：提供解决问题的具体步骤
        
        以JSON格式返回，包含problem_description, root_cause_analysis, recommended_actions字段。
        """
        
        # 调用Claude模型
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # 解析响应
        response_body = json.loads(response['body'].read().decode('utf-8'))
        llm_response = response_body['content'][0]['text']
        
        # 尝试解析JSON响应
        try:
            # 查找JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                analysis_json = json.loads(json_match.group(1))
            else:
                # 尝试直接解析整个响应
                analysis_json = json.loads(llm_response)
        except json.JSONDecodeError:
            # 如果无法解析JSON，使用原始响应
            analysis_json = {
                "problem_description": "无法解析LLM响应为JSON格式",
                "root_cause_analysis": llm_response[:500] + ("..." if len(llm_response) > 500 else ""),
                "recommended_actions": "请检查原始LLM响应"
            }
        
        # 构建结果
        result = {
            "status": "success",
            "analysis": {
                "problem_description": analysis_json.get("problem_description", "未提供"),
                "root_cause_analysis": analysis_json.get("root_cause_analysis", "未提供"),
                "recommended_actions": analysis_json.get("recommended_actions", "未提供")
            },
            "query": query,
            "logs_analyzed": len(selected_logs),
            "model_used": "anthropic.claude-3-sonnet-20240229-v1:0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '未知错误码')
        error_message = e.response.get('Error', {}).get('Message', '未知错误')
        
        result = {
            "status": "error",
            "message": f"调用Bedrock LLM失败: {error_message}",
            "error_code": error_code,
            "error_type": "ClientError",
            "query": query,
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if error_code == "AccessDeniedException":
            result["resolution"] = "请检查IAM权限是否包含Bedrock访问权限"
        elif error_code == "ValidationException":
            result["resolution"] = "请检查请求参数是否有效"
        elif error_code == "ThrottlingException":
            result["resolution"] = "请求被限流，请稍后重试"
        
        return result
    
    except Exception as e:
        result = {
            "status": "error",
            "message": f"分析日志时发生错误: {str(e)}",
            "error_type": type(e).__name__,
            "query": query,
            "region": region,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return result

@tool
def generate_log_insights_query(
    service_type: str,
    problem_type: str,
    resource_id: Optional[str] = None,
    time_range_minutes: int = 60
) -> Dict[str, Any]:
    """
    生成CloudWatch Logs Insights查询语句
    
    Args:
        service_type: AWS服务类型，如EC2, Lambda, RDS, S3, DynamoDB
        problem_type: 问题类型，如error, timeout, memory, permission, throttling
        resource_id: 资源ID（可选），如实例ID、函数名称等
        time_range_minutes: 查询时间范围（分钟），默认60分钟
        
    Returns:
        生成的查询语句和相关信息
    """
    # 服务类型和日志组映射
    service_log_groups = {
        "EC2": ["/var/log/cloud-init-output.log", "/var/log/syslog", "/var/log/messages"],
        "Lambda": ["/aws/lambda/{function_name}"],
        "RDS": ["/aws/rds/instance/{instance_id}/error", "/aws/rds/instance/{instance_id}/slowquery"],
        "ECS": ["/aws/ecs/containerinsights/{cluster_name}/application", "/aws/ecs/containerinsights/{cluster_name}/performance"],
        "API_Gateway": ["/aws/apigateway/{api_id}"],
        "ELB": ["/aws/elasticloadbalancing/access"],
        "CloudTrail": ["/aws/cloudtrail"],
        "S3": ["不直接支持日志组，需要启用访问日志"],
        "DynamoDB": ["不直接支持日志组，需要启用CloudTrail"]
    }
    
    # 问题类型和查询模式映射
    problem_query_patterns = {
        "error": {
            "base": "filter @message like /(?i)error|exception|fail|fatal/",
            "EC2": "filter @message like /(?i)error|exception|fail|fatal|terminated|shutdown/",
            "Lambda": "filter @message like /(?i)error|exception|fail|fatal|timeout|memory|Task timed out/",
            "RDS": "filter @message like /(?i)error|exception|fail|fatal|timeout|connection|denied/",
            "S3": "filter eventName like /(?i)error|exception|AccessDenied|NoSuchKey/",
            "DynamoDB": "filter errorCode like /(?i)ProvisionedThroughputExceededException|ResourceNotFoundException/"
        },
        "timeout": {
            "base": "filter @message like /(?i)timeout|timed out|connection timed out/",
            "Lambda": "filter @message like /(?i)Task timed out|execution timed out|duration|timeout/",
            "RDS": "filter @message like /(?i)timeout|connection timeout|query timeout|lock timeout/",
            "API_Gateway": "filter @message like /(?i)timeout|integration timeout|endpoint timeout/"
        },
        "memory": {
            "base": "filter @message like /(?i)out of memory|memory limit|insufficient memory/",
            "Lambda": "filter @message like /(?i)out of memory|memory size exceeded|memory usage/",
            "EC2": "filter @message like /(?i)out of memory|memory exhausted|cannot allocate memory/"
        },
        "permission": {
            "base": "filter @message like /(?i)access denied|permission denied|not authorized|forbidden/",
            "Lambda": "filter @message like /(?i)access denied|permission denied|not authorized|role cannot|policy does not/",
            "S3": "filter eventName = 'AccessDenied'",
            "DynamoDB": "filter errorCode = 'AccessDeniedException'"
        },
        "throttling": {
            "base": "filter @message like /(?i)throttl|rate exceed|too many requests/",
            "Lambda": "filter @message like /(?i)throttl|rate exceed|too many requests|concurrency/",
            "API_Gateway": "filter @message like /(?i)throttl|rate exceed|too many requests|quota/",
            "DynamoDB": "filter errorCode = 'ProvisionedThroughputExceededException'"
        }
    }
    
    # 获取服务的日志组
    log_groups = service_log_groups.get(service_type, ["未知服务类型"])
    if resource_id and "{" in str(log_groups):
        # 替换占位符
        log_groups = [lg.replace("{function_name}", resource_id).replace("{instance_id}", resource_id).replace("{cluster_name}", resource_id).replace("{api_id}", resource_id) for lg in log_groups]
    
    # 获取查询模式
    query_pattern = problem_query_patterns.get(problem_type, {}).get(service_type)
    if not query_pattern:
        query_pattern = problem_query_patterns.get(problem_type, {}).get("base", f"filter @message like /(?i){problem_type}/")
    
    # 构建资源过滤条件
    resource_filter = ""
    if resource_id:
        resource_filter = f" and @message like /{resource_id}/"
    
    # 构建完整查询
    query = f"""
    {query_pattern}{resource_filter}
    | sort @timestamp desc
    | limit 100
    """
    
    # 构建结果
    result = {
        "status": "success",
        "query": query.strip(),
        "log_groups": log_groups,
        "parameters": {
            "service_type": service_type,
            "problem_type": problem_type,
            "resource_id": resource_id,
            "time_range_minutes": time_range_minutes
        },
        "usage_instructions": f"使用此查询在过去{time_range_minutes}分钟的日志中搜索{service_type}服务的{problem_type}问题",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return result