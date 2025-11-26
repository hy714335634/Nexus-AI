"""
会话历史管理工具模块

本模块提供对话会话的创建、更新、加载和持久化功能。
支持记录完整的对话历史、会话摘要和信息提取。

作者: Nexus-AI平台
日期: 2025-11-26
版本: 1.0.0
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from strands import tool


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


@tool
def create_session(child_id: str, session_id: Optional[str] = None) -> str:
    """
    创建新的对话会话
    
    Args:
        child_id: 儿童的唯一标识符
        session_id: 会话ID（可选，默认自动生成）
    
    Returns:
        JSON格式的操作结果，包含创建的会话信息
    """
    try:
        # 生成会话ID
        if session_id is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"{child_id}_{timestamp}"
        
        # 创建会话对象
        session = SessionHistory(
            session_id=session_id,
            child_id=child_id,
            start_time=datetime.now().isoformat()
        )
        
        # 确保缓存目录存在
        cache_dir = Path(f".cache/kids_companion_chatbot/sessions/{child_id}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        session_path = cache_dir / f"{session_id}.json"
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功创建会话：{session_id}",
            "session": session.to_dict(),
            "file_path": str(session_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"创建会话失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def load_session(child_id: str, session_id: str) -> str:
    """
    加载对话会话
    
    Args:
        child_id: 儿童的唯一标识符
        session_id: 会话ID
    
    Returns:
        JSON格式的会话数据或错误信息
    """
    try:
        session_path = Path(f".cache/kids_companion_chatbot/sessions/{child_id}/{session_id}.json")
        
        if not session_path.exists():
            return json.dumps({
                "status": "not_found",
                "message": f"未找到会话：{session_id}",
                "child_id": child_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 读取会话
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        session = SessionHistory.from_dict(session_data)
        
        return json.dumps({
            "status": "success",
            "message": f"成功加载会话：{session_id}",
            "session": session.to_dict(),
            "file_path": str(session_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"加载会话失败：{str(e)}",
            "child_id": child_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def add_conversation_turn(
    child_id: str,
    session_id: str,
    user_message: str,
    assistant_response: str,
    extracted_info: Optional[Dict[str, Any]] = None
) -> str:
    """
    向会话添加对话轮次
    
    Args:
        child_id: 儿童的唯一标识符
        session_id: 会话ID
        user_message: 用户消息
        assistant_response: 助手回复
        extracted_info: 提取的信息（可选）
    
    Returns:
        JSON格式的操作结果
    """
    try:
        session_path = Path(f".cache/kids_companion_chatbot/sessions/{child_id}/{session_id}.json")
        
        if not session_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"会话不存在：{session_id}",
                "child_id": child_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 加载现有会话
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        session = SessionHistory.from_dict(session_data)
        
        # 创建新的对话轮次
        turn_id = len(session.turns) + 1
        new_turn = ConversationTurn(
            turn_id=turn_id,
            timestamp=datetime.now().isoformat(),
            user_message=user_message,
            assistant_response=assistant_response,
            extracted_info=extracted_info or {}
        )
        
        # 添加到会话
        session.turns.append(new_turn)
        
        # 保存更新
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功添加对话轮次到会话：{session_id}",
            "turn": new_turn.to_dict(),
            "total_turns": len(session.turns),
            "file_path": str(session_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"添加对话轮次失败：{str(e)}",
            "child_id": child_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def end_session(
    child_id: str,
    session_id: str,
    session_summary: Optional[str] = None
) -> str:
    """
    结束对话会话
    
    Args:
        child_id: 儿童的唯一标识符
        session_id: 会话ID
        session_summary: 会话摘要（可选）
    
    Returns:
        JSON格式的操作结果
    """
    try:
        session_path = Path(f".cache/kids_companion_chatbot/sessions/{child_id}/{session_id}.json")
        
        if not session_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"会话不存在：{session_id}",
                "child_id": child_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 加载现有会话
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        session = SessionHistory.from_dict(session_data)
        
        # 更新结束时间和摘要
        session.end_time = datetime.now().isoformat()
        if session_summary:
            session.session_summary = session_summary
        
        # 保存更新
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "status": "success",
            "message": f"成功结束会话：{session_id}",
            "session": session.to_dict(),
            "file_path": str(session_path)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"结束会话失败：{str(e)}",
            "child_id": child_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def list_child_sessions(
    child_id: str,
    limit: int = 10,
    include_details: bool = False
) -> str:
    """
    列出儿童的所有会话
    
    Args:
        child_id: 儿童的唯一标识符
        limit: 返回的会话数量限制（默认10）
        include_details: 是否包含详细的对话轮次（默认False）
    
    Returns:
        JSON格式的会话列表
    """
    try:
        sessions_dir = Path(f".cache/kids_companion_chatbot/sessions/{child_id}")
        
        if not sessions_dir.exists():
            return json.dumps({
                "status": "success",
                "message": f"未找到{child_id}的会话记录",
                "child_id": child_id,
                "sessions": []
            }, ensure_ascii=False, indent=2)
        
        sessions = []
        session_files = sorted(
            sessions_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        for session_file in session_files[:limit]:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                if include_details:
                    sessions.append(session_data)
                else:
                    # 只返回基本信息
                    sessions.append({
                        "session_id": session_data.get("session_id"),
                        "start_time": session_data.get("start_time"),
                        "end_time": session_data.get("end_time"),
                        "turn_count": len(session_data.get("turns", [])),
                        "session_summary": session_data.get("session_summary", "")
                    })
            except Exception as e:
                continue
        
        return json.dumps({
            "status": "success",
            "message": f"找到{len(sessions)}个会话",
            "child_id": child_id,
            "sessions": sessions,
            "total_found": len(sessions)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"列出会话失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def get_recent_conversations(
    child_id: str,
    max_turns: int = 5
) -> str:
    """
    获取最近的对话历史
    
    Args:
        child_id: 儿童的唯一标识符
        max_turns: 最多返回的对话轮次数（默认5）
    
    Returns:
        JSON格式的最近对话历史
    """
    try:
        sessions_dir = Path(f".cache/kids_companion_chatbot/sessions/{child_id}")
        
        if not sessions_dir.exists():
            return json.dumps({
                "status": "success",
                "message": f"未找到{child_id}的对话记录",
                "child_id": child_id,
                "recent_conversations": []
            }, ensure_ascii=False, indent=2)
        
        # 获取最新的会话文件
        session_files = sorted(
            sessions_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        recent_conversations = []
        turns_collected = 0
        
        for session_file in session_files:
            if turns_collected >= max_turns:
                break
            
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                turns = session_data.get("turns", [])
                # 从最新的轮次开始收集
                for turn in reversed(turns):
                    if turns_collected >= max_turns:
                        break
                    recent_conversations.insert(0, turn)
                    turns_collected += 1
            except Exception as e:
                continue
        
        return json.dumps({
            "status": "success",
            "message": f"找到{len(recent_conversations)}轮最近对话",
            "child_id": child_id,
            "recent_conversations": recent_conversations,
            "total_turns": len(recent_conversations)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"获取最近对话失败：{str(e)}",
            "child_id": child_id
        }, ensure_ascii=False, indent=2)


@tool
def delete_session(child_id: str, session_id: str) -> str:
    """
    删除对话会话
    
    Args:
        child_id: 儿童的唯一标识符
        session_id: 会话ID
    
    Returns:
        JSON格式的操作结果
    """
    try:
        session_path = Path(f".cache/kids_companion_chatbot/sessions/{child_id}/{session_id}.json")
        
        if not session_path.exists():
            return json.dumps({
                "status": "error",
                "message": f"会话不存在：{session_id}",
                "child_id": child_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 删除文件
        session_path.unlink()
        
        return json.dumps({
            "status": "success",
            "message": f"成功删除会话：{session_id}",
            "child_id": child_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"删除会话失败：{str(e)}",
            "child_id": child_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)