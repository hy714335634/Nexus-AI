"""
儿童陪伴聊天Agent - 用户画像管理工具

本模块提供用户画像的加载和保存功能，支持从本地文件系统读取和写入JSON格式的用户画像数据。

Author: Nexus-AI Platform
Created: 2025-12-23
Version: 1.0.0
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from strands import tool


# 默认缓存目录
DEFAULT_CACHE_DIR = ".cache/children_chat_companion"


@tool
def load_user_profile(
    user_id: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    从本地文件系统加载用户画像
    
    Args:
        user_id: 用户唯一标识
        cache_dir: 缓存目录路径（可选，默认为.cache/children_chat_companion）
        
    Returns:
        str: JSON格式的用户画像数据，如果画像不存在则返回None标识
    """
    try:
        # 确定缓存目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        profile_path = user_dir / "profile.json"
        
        # 检查文件是否存在
        if not profile_path.exists():
            return json.dumps({
                "status": "not_found",
                "message": f"用户画像不存在: {user_id}",
                "user_id": user_id,
                "profile": None
            }, ensure_ascii=False, indent=2)
        
        # 读取画像文件
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        # 验证必需字段
        if "user_id" not in profile_data:
            profile_data["user_id"] = user_id
        
        return json.dumps({
            "status": "success",
            "message": "用户画像加载成功",
            "user_id": user_id,
            "profile": profile_data,
            "file_path": str(profile_path)
        }, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "json_decode_error",
            "message": f"JSON解析失败: {str(e)}",
            "user_id": user_id,
            "profile": None
        }, ensure_ascii=False, indent=2)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error_type": "permission_error",
            "message": f"文件权限不足: {str(e)}",
            "user_id": user_id,
            "profile": None
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"加载用户画像失败: {str(e)}",
            "user_id": user_id,
            "profile": None
        }, ensure_ascii=False, indent=2)


@tool
def save_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
    cache_dir: Optional[str] = None,
    create_if_missing: bool = True
) -> str:
    """
    将更新后的用户画像保存到本地文件系统
    
    Args:
        user_id: 用户唯一标识
        profile_data: 用户画像数据字典
        cache_dir: 缓存目录路径（可选，默认为.cache/children_chat_companion）
        create_if_missing: 如果目录不存在是否创建（默认True）
        
    Returns:
        str: JSON格式的保存结果
    """
    try:
        # 确定缓存目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        profile_path = user_dir / "profile.json"
        
        # 创建用户目录（如果不存在）
        if create_if_missing:
            user_dir.mkdir(parents=True, exist_ok=True)
        elif not user_dir.exists():
            return json.dumps({
                "status": "error",
                "error_type": "directory_not_found",
                "message": f"用户目录不存在且不允许创建: {user_dir}",
                "user_id": user_id
            }, ensure_ascii=False, indent=2)
        
        # 验证和补充必需字段
        if "user_id" not in profile_data:
            profile_data["user_id"] = user_id
        
        if "last_updated" not in profile_data:
            profile_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        else:
            profile_data["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        if "version" not in profile_data:
            profile_data["version"] = "1.0"
        
        # 验证年龄范围
        if "basic_info" in profile_data and "age" in profile_data["basic_info"]:
            age = profile_data["basic_info"]["age"]
            if not isinstance(age, int) or age < 3 or age > 12:
                return json.dumps({
                    "status": "error",
                    "error_type": "validation_error",
                    "message": f"年龄必须在3-12岁范围内: {age}",
                    "user_id": user_id
                }, ensure_ascii=False, indent=2)
        
        # 写入画像文件
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
        
        # 获取文件大小
        file_size = profile_path.stat().st_size
        
        return json.dumps({
            "status": "success",
            "message": "用户画像保存成功",
            "user_id": user_id,
            "file_path": str(profile_path),
            "file_size_bytes": file_size,
            "last_updated": profile_data["last_updated"]
        }, ensure_ascii=False, indent=2)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error_type": "permission_error",
            "message": f"文件写入权限不足: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)
        
    except OSError as e:
        return json.dumps({
            "status": "error",
            "error_type": "os_error",
            "message": f"文件系统错误（可能磁盘空间不足）: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"保存用户画像失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def create_default_profile(
    user_id: str,
    age: Optional[int] = None,
    cache_dir: Optional[str] = None
) -> str:
    """
    创建默认的用户画像
    
    Args:
        user_id: 用户唯一标识
        age: 用户年龄（可选，默认为7岁）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的创建结果
    """
    try:
        # 设置默认年龄
        default_age = age if age and 3 <= age <= 12 else 7
        
        # 创建默认画像结构
        now = datetime.utcnow().isoformat() + "Z"
        default_profile = {
            "user_id": user_id,
            "basic_info": {
                "nickname": None,
                "age": default_age,
                "gender": "unknown",
                "grade": None
            },
            "interests": [],
            "personality_traits": [],
            "behavior_patterns": [],
            "key_memories": [],
            "conversation_stats": {
                "total_conversations": 0,
                "total_turns": 0,
                "first_conversation": now,
                "last_conversation": now,
                "average_turns_per_session": 0.0
            },
            "created_at": now,
            "last_updated": now,
            "version": "1.0"
        }
        
        # 保存默认画像
        result_str = save_user_profile(
            user_id=user_id,
            profile_data=default_profile,
            cache_dir=cache_dir,
            create_if_missing=True
        )
        
        result = json.loads(result_str)
        if result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "默认用户画像创建成功",
                "user_id": user_id,
                "profile": default_profile
            }, ensure_ascii=False, indent=2)
        else:
            return result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"创建默认画像失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def update_profile_field(
    user_id: str,
    field_path: str,
    value: Any,
    cache_dir: Optional[str] = None
) -> str:
    """
    更新用户画像的特定字段
    
    Args:
        user_id: 用户唯一标识
        field_path: 字段路径，使用点号分隔（如"basic_info.age"或"interests"）
        value: 新的字段值
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的更新结果
    """
    try:
        # 加载现有画像
        load_result_str = load_user_profile(user_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] == "not_found":
            # 如果画像不存在，创建默认画像
            create_result_str = create_default_profile(user_id, cache_dir=cache_dir)
            create_result = json.loads(create_result_str)
            if create_result["status"] != "success":
                return create_result_str
            profile_data = create_result["profile"]
        elif load_result["status"] == "success":
            profile_data = load_result["profile"]
        else:
            return load_result_str
        
        # 解析字段路径并更新值
        path_parts = field_path.split('.')
        current = profile_data
        
        # 遍历路径到倒数第二级
        for i, part in enumerate(path_parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # 更新最后一级字段
        last_key = path_parts[-1]
        current[last_key] = value
        
        # 保存更新后的画像
        save_result_str = save_user_profile(
            user_id=user_id,
            profile_data=profile_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": f"字段 {field_path} 更新成功",
                "user_id": user_id,
                "field_path": field_path,
                "new_value": value,
                "last_updated": save_result["last_updated"]
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"更新字段失败: {str(e)}",
            "user_id": user_id,
            "field_path": field_path
        }, ensure_ascii=False, indent=2)


@tool
def add_interest(
    user_id: str,
    interest_name: str,
    weight: float = 0.5,
    cache_dir: Optional[str] = None
) -> str:
    """
    向用户画像添加新的兴趣
    
    Args:
        user_id: 用户唯一标识
        interest_name: 兴趣名称
        weight: 兴趣权重（0.0-1.0，默认0.5）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证权重范围
        if not 0.0 <= weight <= 1.0:
            return json.dumps({
                "status": "error",
                "error_type": "validation_error",
                "message": f"兴趣权重必须在0.0-1.0范围内: {weight}",
                "user_id": user_id
            }, ensure_ascii=False, indent=2)
        
        # 加载现有画像
        load_result_str = load_user_profile(user_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] == "not_found":
            # 创建默认画像
            create_result_str = create_default_profile(user_id, cache_dir=cache_dir)
            create_result = json.loads(create_result_str)
            if create_result["status"] != "success":
                return create_result_str
            profile_data = create_result["profile"]
        elif load_result["status"] == "success":
            profile_data = load_result["profile"]
        else:
            return load_result_str
        
        # 检查兴趣是否已存在
        interests = profile_data.get("interests", [])
        now = datetime.utcnow().isoformat() + "Z"
        
        existing_interest = None
        for interest in interests:
            if interest["name"] == interest_name:
                existing_interest = interest
                break
        
        if existing_interest:
            # 更新现有兴趣
            existing_interest["weight"] = weight
            existing_interest["last_mentioned"] = now
            existing_interest["mention_count"] = existing_interest.get("mention_count", 0) + 1
            message = f"兴趣 '{interest_name}' 已更新"
        else:
            # 添加新兴趣
            new_interest = {
                "name": interest_name,
                "weight": weight,
                "first_mentioned": now,
                "last_mentioned": now,
                "mention_count": 1
            }
            interests.append(new_interest)
            message = f"新兴趣 '{interest_name}' 已添加"
        
        profile_data["interests"] = interests
        
        # 保存更新后的画像
        save_result_str = save_user_profile(
            user_id=user_id,
            profile_data=profile_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": message,
                "user_id": user_id,
                "interest_name": interest_name,
                "weight": weight,
                "total_interests": len(interests)
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"添加兴趣失败: {str(e)}",
            "user_id": user_id,
            "interest_name": interest_name
        }, ensure_ascii=False, indent=2)


@tool
def update_conversation_stats(
    user_id: str,
    turns_increment: int = 1,
    cache_dir: Optional[str] = None
) -> str:
    """
    更新用户的对话统计信息
    
    Args:
        user_id: 用户唯一标识
        turns_increment: 本次对话增加的轮数（默认1）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的更新结果
    """
    try:
        # 加载现有画像
        load_result_str = load_user_profile(user_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] == "not_found":
            # 创建默认画像
            create_result_str = create_default_profile(user_id, cache_dir=cache_dir)
            create_result = json.loads(create_result_str)
            if create_result["status"] != "success":
                return create_result_str
            profile_data = create_result["profile"]
        elif load_result["status"] == "success":
            profile_data = load_result["profile"]
        else:
            return load_result_str
        
        # 获取统计信息
        stats = profile_data.get("conversation_stats", {})
        
        # 更新统计数据
        total_conversations = stats.get("total_conversations", 0) + 1
        total_turns = stats.get("total_turns", 0) + turns_increment
        average_turns = total_turns / total_conversations if total_conversations > 0 else 0.0
        
        now = datetime.utcnow().isoformat() + "Z"
        
        updated_stats = {
            "total_conversations": total_conversations,
            "total_turns": total_turns,
            "first_conversation": stats.get("first_conversation", now),
            "last_conversation": now,
            "average_turns_per_session": round(average_turns, 2)
        }
        
        profile_data["conversation_stats"] = updated_stats
        
        # 保存更新后的画像
        save_result_str = save_user_profile(
            user_id=user_id,
            profile_data=profile_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "对话统计更新成功",
                "user_id": user_id,
                "stats": updated_stats
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"更新对话统计失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def get_profile_summary(
    user_id: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    获取用户画像的简要摘要
    
    Args:
        user_id: 用户唯一标识
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的画像摘要
    """
    try:
        # 加载画像
        load_result_str = load_user_profile(user_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] != "success":
            return load_result_str
        
        profile = load_result["profile"]
        
        # 提取关键信息
        basic_info = profile.get("basic_info", {})
        interests = profile.get("interests", [])
        stats = profile.get("conversation_stats", {})
        
        # 按权重排序兴趣
        sorted_interests = sorted(
            interests,
            key=lambda x: x.get("weight", 0),
            reverse=True
        )
        top_interests = [i["name"] for i in sorted_interests[:5]]
        
        summary = {
            "user_id": user_id,
            "age": basic_info.get("age"),
            "gender": basic_info.get("gender"),
            "grade": basic_info.get("grade"),
            "top_interests": top_interests,
            "total_conversations": stats.get("total_conversations", 0),
            "total_turns": stats.get("total_turns", 0),
            "average_turns_per_session": stats.get("average_turns_per_session", 0.0),
            "personality_traits": profile.get("personality_traits", []),
            "last_conversation": stats.get("last_conversation")
        }
        
        return json.dumps({
            "status": "success",
            "message": "画像摘要生成成功",
            "user_id": user_id,
            "summary": summary
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"获取画像摘要失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)
