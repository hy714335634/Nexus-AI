#!/usr/bin/env python3
"""
话题管理工具模块

提供用户关注话题的添加、查看、删除等管理功能
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from strands import tool


# 定义话题存储目录
TOPICS_DIR = os.path.expanduser("~/.news_retrieval_agent/topics")


@tool
def add_topic(keyword: str, user_id: str = "default") -> str:
    """
    添加用户关注话题
    
    Args:
        keyword (str): 话题关键词
        user_id (str, optional): 用户ID，默认为"default"
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证输入
        if not keyword or len(keyword.strip()) == 0:
            return json.dumps({
                "status": "error",
                "message": "话题关键词不能为空",
                "user_id": user_id
            }, ensure_ascii=False, indent=2)
        
        # 规范化关键词
        keyword = keyword.strip()
        
        # 确保目录存在
        user_topics_dir = _get_user_topics_dir(user_id)
        os.makedirs(user_topics_dir, exist_ok=True)
        
        # 获取现有话题
        existing_topics = _get_user_topics(user_id)
        
        # 检查是否已存在相同话题
        for topic in existing_topics:
            if topic["keyword"].lower() == keyword.lower():
                return json.dumps({
                    "status": "error",
                    "message": f"话题 '{keyword}' 已存在",
                    "user_id": user_id,
                    "topic_id": topic["topic_id"]
                }, ensure_ascii=False, indent=2)
        
        # 创建新话题
        now = datetime.now().isoformat()
        new_topic = {
            "topic_id": str(uuid.uuid4()),
            "keyword": keyword,
            "created_at": now,
            "last_used": now
        }
        
        # 添加到话题列表
        existing_topics.append(new_topic)
        
        # 保存话题列表
        _save_user_topics(user_id, existing_topics)
        
        return json.dumps({
            "status": "success",
            "message": f"成功添加话题 '{keyword}'",
            "user_id": user_id,
            "topic": new_topic
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"添加话题失败: {str(e)}",
            "user_id": user_id,
            "keyword": keyword
        }, ensure_ascii=False, indent=2)


@tool
def view_topics(user_id: str = "default") -> str:
    """
    查看用户关注的话题列表
    
    Args:
        user_id (str, optional): 用户ID，默认为"default"
        
    Returns:
        str: JSON格式的话题列表
    """
    try:
        # 获取用户话题
        topics = _get_user_topics(user_id)
        
        # 构建结果
        result = {
            "status": "success",
            "user_id": user_id,
            "topics_count": len(topics),
            "topics": topics
        }
        
        # 如果没有话题，添加提示信息
        if len(topics) == 0:
            result["message"] = "您还没有添加任何关注话题"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取话题列表失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def delete_topic(topic_id: str = None, keyword: str = None, user_id: str = "default") -> str:
    """
    删除用户关注话题
    
    Args:
        topic_id (str, optional): 话题ID，与keyword二选一
        keyword (str, optional): 话题关键词，与topic_id二选一
        user_id (str, optional): 用户ID，默认为"default"
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证输入
        if not topic_id and not keyword:
            return json.dumps({
                "status": "error",
                "message": "必须提供topic_id或keyword",
                "user_id": user_id
            }, ensure_ascii=False, indent=2)
        
        # 获取用户话题
        topics = _get_user_topics(user_id)
        
        # 查找要删除的话题
        found = False
        new_topics = []
        deleted_topic = None
        
        for topic in topics:
            if (topic_id and topic["topic_id"] == topic_id) or \
               (keyword and topic["keyword"].lower() == keyword.lower()):
                found = True
                deleted_topic = topic
            else:
                new_topics.append(topic)
        
        if not found:
            return json.dumps({
                "status": "error",
                "message": f"未找到指定话题",
                "user_id": user_id,
                "topic_id": topic_id,
                "keyword": keyword
            }, ensure_ascii=False, indent=2)
        
        # 保存更新后的话题列表
        _save_user_topics(user_id, new_topics)
        
        return json.dumps({
            "status": "success",
            "message": f"成功删除话题 '{deleted_topic['keyword']}'",
            "user_id": user_id,
            "deleted_topic": deleted_topic
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"删除话题失败: {str(e)}",
            "user_id": user_id,
            "topic_id": topic_id,
            "keyword": keyword
        }, ensure_ascii=False, indent=2)


@tool
def update_topic_usage(topic_id: str = None, keyword: str = None, user_id: str = "default") -> str:
    """
    更新话题使用时间
    
    Args:
        topic_id (str, optional): 话题ID，与keyword二选一
        keyword (str, optional): 话题关键词，与topic_id二选一
        user_id (str, optional): 用户ID，默认为"default"
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 验证输入
        if not topic_id and not keyword:
            return json.dumps({
                "status": "error",
                "message": "必须提供topic_id或keyword",
                "user_id": user_id
            }, ensure_ascii=False, indent=2)
        
        # 获取用户话题
        topics = _get_user_topics(user_id)
        
        # 查找要更新的话题
        found = False
        updated_topic = None
        
        for topic in topics:
            if (topic_id and topic["topic_id"] == topic_id) or \
               (keyword and topic["keyword"].lower() == keyword.lower()):
                topic["last_used"] = datetime.now().isoformat()
                found = True
                updated_topic = topic
                break
        
        if not found:
            return json.dumps({
                "status": "error",
                "message": f"未找到指定话题",
                "user_id": user_id,
                "topic_id": topic_id,
                "keyword": keyword
            }, ensure_ascii=False, indent=2)
        
        # 保存更新后的话题列表
        _save_user_topics(user_id, topics)
        
        return json.dumps({
            "status": "success",
            "message": f"成功更新话题 '{updated_topic['keyword']}' 的使用时间",
            "user_id": user_id,
            "updated_topic": updated_topic
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"更新话题使用时间失败: {str(e)}",
            "user_id": user_id,
            "topic_id": topic_id,
            "keyword": keyword
        }, ensure_ascii=False, indent=2)


@tool
def get_recent_topics(limit: int = 5, user_id: str = "default") -> str:
    """
    获取最近使用的话题
    
    Args:
        limit (int, optional): 返回的话题数量，默认为5
        user_id (str, optional): 用户ID，默认为"default"
        
    Returns:
        str: JSON格式的最近使用的话题列表
    """
    try:
        # 获取用户话题
        topics = _get_user_topics(user_id)
        
        # 按最近使用时间排序
        sorted_topics = sorted(topics, key=lambda x: x.get("last_used", x.get("created_at", "")), reverse=True)
        
        # 限制返回数量
        recent_topics = sorted_topics[:limit]
        
        # 构建结果
        result = {
            "status": "success",
            "user_id": user_id,
            "topics_count": len(recent_topics),
            "topics": recent_topics
        }
        
        # 如果没有话题，添加提示信息
        if len(recent_topics) == 0:
            result["message"] = "您还没有添加任何关注话题"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取最近话题失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


def _get_user_topics_dir(user_id: str) -> str:
    """获取用户话题存储目录"""
    return os.path.join(TOPICS_DIR, user_id)


def _get_user_topics_file(user_id: str) -> str:
    """获取用户话题文件路径"""
    return os.path.join(_get_user_topics_dir(user_id), "topics.json")


def _get_user_topics(user_id: str) -> List[Dict[str, Any]]:
    """获取用户话题列表"""
    topics_file = _get_user_topics_file(user_id)
    
    # 如果文件不存在，返回空列表
    if not os.path.exists(topics_file):
        return []
    
    # 读取话题文件
    try:
        with open(topics_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # 如果文件读取失败，返回空列表
        return []


def _save_user_topics(user_id: str, topics: List[Dict[str, Any]]) -> None:
    """保存用户话题列表"""
    # 确保目录存在
    user_topics_dir = _get_user_topics_dir(user_id)
    os.makedirs(user_topics_dir, exist_ok=True)
    
    # 保存话题文件
    topics_file = _get_user_topics_file(user_id)
    with open(topics_file, 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)