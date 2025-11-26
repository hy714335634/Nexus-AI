"""
儿童用户画像管理工具模块

本模块提供儿童用户画像的创建、更新、加载和持久化功能。
支持记录儿童的基本信息、兴趣爱好、性格特征、对话历史等。

作者: Nexus-AI平台
日期: 2025-11-26
版本: 1.0.0
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from strands import tool


# 数据模型定义
class ChildProfile:
    """儿童用户画像数据模型"""
    
    def __init__(
        self,
        child_id: str,
        name: str = "",
        age: Optional[int] = None,
        age_group: str = "unknown",
        interests: Optional[List[str]] = None,
        personality_traits: Optional[List[str]] = None,
        favorite_topics: Optional[List[str]] = None,
        conversation_preferences: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        last_updated: Optional[str] = None,
        total_conversations: int = 0,
        total_messages: int = 0,
        notes: Optional[List[str]] = None
    ):
        self.child_id = child_id
        self.name = name
        self.age = age
        self.age_group = age_group
        self.interests = interests or []
        self.personality_traits = personality_traits or []
        self.favorite_topics = favorite_topics or []
        self.conversation_preferences = conversation_preferences or {}
        self.created_at = created_at or datetime.now().isoformat()
        self.last_updated = last_updated or datetime.now().isoformat()
        self.total_conversations = total_conversations
        self.total_messages = total_messages
        self.notes = notes or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "child_id": self.child_id,
            "name": self.name,
            "age": self.age,
            "age_group": self.age_group,
            "interests": self.interests,
            "personality_traits": self.personality_traits,
            "favorite_topics": self.favorite_topics,
            "conversation_preferences": self.conversation_preferences,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "total_conversations": self.total_conversations,
            "total_messages": self.total_messages,
            "notes": self.notes
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ChildProfile':
        """从字典创建对象"""
        return ChildProfile(**data)


class ConversationTurn:
    """对话轮次数据模型"""
    
    def __init__(
        self,
        turn_id: int,
        timestamp: str,
        user_message: str,
        assistant_response: str,
        extracted_info: Optional[Dict[str, Any]] = None
    ):
        self.turn_id = turn_id
        self.timestamp = timestamp
        self.user_message = user_message
        self.assistant_response = assistant_response
        self.extracted_info = extracted_info or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "extracted_info": self.extracted_info
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ConversationTurn':
        """从字典创建对象"""
        return ConversationTurn(**data)


class SessionHistory:
    """会话历史数据模型"""
    
    def __init__(
        self,
        session_id: str,
        child_id: str,
        start_time: str,
        end_time: Optional[str] = None,
        turns: Optional[List[ConversationTurn]] = None,
        session_summary: str = ""
    ):
        self.session_id = session_id
        self.child_id = child_id
        self.start_time = start_time
        self.end_time = end_time
        self.turns = turns or []
        self.session_summary = session_summary
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "child_id": self.child_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "turns": [turn.to_dict() for turn in self.turns],
            "session_summary": self.session_summary
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SessionHistory':
        """从字典创建对象"""
        turns = [ConversationTurn.from_dict(t) for t in data.get("turns", [])]
        return SessionHistory(
            session_id=data["session_id"],
            child_id=data["child_id"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            turns=turns,
            session_summary=data.get("session_summary", "")
        )


# 工具函数定义
@tool
def create_child_profile(
    child_id: str,
    name: str = "",
    age: Optional[int] = None,
    initial_interests: Optional[List[str]] = None
) -> str:
    """
    创建新的儿童用户画像
    
    Args:
        child_id: 儿童的唯一标识符
        name: 儿童姓名（可选）
        age: 儿童年龄（可选）
        initial_interests: 初始兴趣列表（可选）
    
    Returns:
        JSON格式的操作结果，包含创建的用户画像信息或错误信息
    """
    try:
        # 确定年龄组
        age_group = "unknown"
        if age is not None:
            if 3 <= age <= 6:
                age_group = "3-6"
            elif 7 <= age <= 9:
                age_group = "7-9"
            elif 10 <= age <= 12:
                age_group = "10-12"
        
        # 创建用户画像对象
        profile = ChildProfile(
            child_id=child_id,
            name=name,
            age=age,
            age_group=age_group,
            interests=initial_interests or []
        )
        
        # 确保缓存目录存在
        cache_dir = Path(".cache/kids_companion_chatbot/profiles")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        profile_path = cache_dir / f"{child_id}.json"
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功创建用户画像：{child_id}",
            "profile": profile.to_dict(),
            "file_path": str(profile_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"创建用户画像失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def load_child_profile(child_id: str) -> str:
    """
    加载儿童用户画像
    
    Args:
        child_id: 儿童的唯一标识符
    
    Returns:
        JSON格式的用户画像数据或错误信息
    """
    try:
        profile_path = Path(f".cache/kids_companion_chatbot/profiles/{child_id}.json")
        
        if not profile_path.exists():
            return json.dumps({
                "status": "not_found",
                "message": f"未找到用户画像：{child_id}",
                "child_id": child_id
            }, ensure_ascii=False, indent=2)
        
        # 读取用户画像
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        profile = ChildProfile.from_dict(profile_data)
        
        return json.dumps({
            "status": "success",
            "message": f"成功加载用户画像：{child_id}",
            "profile": profile.to_dict(),
            "file_path": str(profile_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"加载用户画像失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def update_child_profile(
    child_id: str,
    name: Optional[str] = None,
    age: Optional[int] = None,
    new_interests: Optional[List[str]] = None,
    new_personality_traits: Optional[List[str]] = None,
    new_favorite_topics: Optional[List[str]] = None,
    conversation_preferences: Optional[Dict[str, Any]] = None,
    notes: Optional[List[str]] = None,
    increment_conversations: bool = False,
    increment_messages: int = 0
) -> str:
    """
    更新儿童用户画像
    
    Args:
        child_id: 儿童的唯一标识符
        name: 更新姓名（可选）
        age: 更新年龄（可选）
        new_interests: 新增兴趣列表（可选）
        new_personality_traits: 新增性格特征列表（可选）
        new_favorite_topics: 新增喜爱话题列表（可选）
        conversation_preferences: 对话偏好设置（可选）
        notes: 新增备注列表（可选）
        increment_conversations: 是否增加对话计数
        increment_messages: 增加消息计数
    
    Returns:
        JSON格式的操作结果
    """
    try:
        # 加载现有画像
        profile_path = Path(f".cache/kids_companion_chatbot/profiles/{child_id}.json")
        
        if not profile_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"用户画像不存在：{child_id}",
                "child_id": child_id
            }, ensure_ascii=False, indent=2)
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        profile = ChildProfile.from_dict(profile_data)
        
        # 更新基本信息
        if name is not None:
            profile.name = name
        
        if age is not None:
            profile.age = age
            # 更新年龄组
            if 3 <= age <= 6:
                profile.age_group = "3-6"
            elif 7 <= age <= 9:
                profile.age_group = "7-9"
            elif 10 <= age <= 12:
                profile.age_group = "10-12"
        
        # 更新兴趣（去重）
        if new_interests:
            profile.interests = list(set(profile.interests + new_interests))
        
        # 更新性格特征（去重）
        if new_personality_traits:
            profile.personality_traits = list(set(profile.personality_traits + new_personality_traits))
        
        # 更新喜爱话题（去重）
        if new_favorite_topics:
            profile.favorite_topics = list(set(profile.favorite_topics + new_favorite_topics))
        
        # 更新对话偏好
        if conversation_preferences:
            profile.conversation_preferences.update(conversation_preferences)
        
        # 添加备注
        if notes:
            profile.notes.extend(notes)
        
        # 更新计数
        if increment_conversations:
            profile.total_conversations += 1
        
        if increment_messages > 0:
            profile.total_messages += increment_messages
        
        # 更新时间戳
        profile.last_updated = datetime.now().isoformat()
        
        # 保存更新
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功更新用户画像：{child_id}",
            "profile": profile.to_dict(),
            "file_path": str(profile_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"更新用户画像失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def list_all_profiles() -> str:
    """
    列出所有儿童用户画像
    
    Returns:
        JSON格式的所有用户画像列表
    """
    try:
        cache_dir = Path(".cache/kids_companion_chatbot/profiles")
        
        if not cache_dir.exists():
            return json.dumps({
                "status": "success",
                "message": "没有找到任何用户画像",
                "profiles": []
            }, ensure_ascii=False, indent=2)
        
        profiles = []
        for profile_file in cache_dir.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                    profiles.append({
                        "child_id": profile_data.get("child_id"),
                        "name": profile_data.get("name"),
                        "age": profile_data.get("age"),
                        "age_group": profile_data.get("age_group"),
                        "total_conversations": profile_data.get("total_conversations", 0),
                        "last_updated": profile_data.get("last_updated")
                    })
            except Exception as e:
                continue
        
        return json.dumps({
            "status": "success",
            "message": f"找到{len(profiles)}个用户画像",
            "profiles": profiles
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"列出用户画像失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def delete_child_profile(child_id: str) -> str:
    """
    删除儿童用户画像
    
    Args:
        child_id: 儿童的唯一标识符
    
    Returns:
        JSON格式的操作结果
    """
    try:
        profile_path = Path(f".cache/kids_companion_chatbot/profiles/{child_id}.json")
        
        if not profile_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"用户画像不存在：{child_id}",
                "child_id": child_id
            }, ensure_ascii=False, indent=2)
        
        # 删除文件
        profile_path.unlink()
        
        return json.dumps({
            "status": "success",
            "message": f"成功删除用户画像：{child_id}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"删除用户画像失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)