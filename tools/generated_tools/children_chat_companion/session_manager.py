"""
儿童陪伴聊天Agent - 会话历史管理工具

本模块提供会话历史的加载和保存功能，支持从本地文件系统读取和写入JSON格式的会话历史数据。

Author: Nexus-AI Platform
Created: 2025-12-23
Version: 1.0.0
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool


# 默认缓存目录
DEFAULT_CACHE_DIR = ".cache/children_chat_companion"

# 最大会话轮数限制
MAX_SESSION_TURNS = 50


@tool
def load_session_history(
    user_id: str,
    session_id: str,
    cache_dir: Optional[str] = None,
    max_turns: Optional[int] = None
) -> str:
    """
    从本地文件系统加载会话历史
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        cache_dir: 缓存目录路径（可选，默认为.cache/children_chat_companion）
        max_turns: 最多加载的轮数（可选，默认加载所有，建议3-5轮）
        
    Returns:
        str: JSON格式的会话历史数据，如果会话不存在则返回空历史
    """
    try:
        # 确定缓存目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        session_path = user_dir / f"session_{session_id}.json"
        
        # 检查文件是否存在
        if not session_path.exists():
            return json.dumps({
                "status": "not_found",
                "message": f"会话历史不存在: {session_id}",
                "user_id": user_id,
                "session_id": session_id,
                "history": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "conversation_turns": [],
                    "session_metadata": {
                        "start_time": datetime.utcnow().isoformat() + "Z",
                        "total_turns": 0,
                        "topics_discussed": []
                    }
                }
            }, ensure_ascii=False, indent=2)
        
        # 读取会话历史文件
        with open(session_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # 验证必需字段
        if "session_id" not in history_data:
            history_data["session_id"] = session_id
        if "user_id" not in history_data:
            history_data["user_id"] = user_id
        
        # 限制返回的轮数（如果指定）
        if max_turns and max_turns > 0:
            conversation_turns = history_data.get("conversation_turns", [])
            if len(conversation_turns) > max_turns:
                # 返回最近的max_turns轮对话
                history_data["conversation_turns"] = conversation_turns[-max_turns:]
                history_data["_note"] = f"仅返回最近{max_turns}轮对话"
        
        return json.dumps({
            "status": "success",
            "message": "会话历史加载成功",
            "user_id": user_id,
            "session_id": session_id,
            "history": history_data,
            "file_path": str(session_path),
            "turns_loaded": len(history_data.get("conversation_turns", []))
        }, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "json_decode_error",
            "message": f"JSON解析失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id,
            "history": None
        }, ensure_ascii=False, indent=2)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error_type": "permission_error",
            "message": f"文件权限不足: {str(e)}",
            "user_id": user_id,
            "session_id": session_id,
            "history": None
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"加载会话历史失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id,
            "history": None
        }, ensure_ascii=False, indent=2)


@tool
def save_session_history(
    user_id: str,
    session_id: str,
    history_data: Dict[str, Any],
    cache_dir: Optional[str] = None,
    create_if_missing: bool = True
) -> str:
    """
    将会话历史保存到本地文件系统
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        history_data: 会话历史数据字典
        cache_dir: 缓存目录路径（可选，默认为.cache/children_chat_companion）
        create_if_missing: 如果目录不存在是否创建（默认True）
        
    Returns:
        str: JSON格式的保存结果
    """
    try:
        # 确定缓存目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        session_path = user_dir / f"session_{session_id}.json"
        
        # 创建用户目录（如果不存在）
        if create_if_missing:
            user_dir.mkdir(parents=True, exist_ok=True)
        elif not user_dir.exists():
            return json.dumps({
                "status": "error",
                "error_type": "directory_not_found",
                "message": f"用户目录不存在且不允许创建: {user_dir}",
                "user_id": user_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 验证和补充必需字段
        if "session_id" not in history_data:
            history_data["session_id"] = session_id
        if "user_id" not in history_data:
            history_data["user_id"] = user_id
        
        now = datetime.utcnow().isoformat() + "Z"
        if "created_at" not in history_data:
            history_data["created_at"] = now
        history_data["last_updated"] = now
        
        # 验证会话轮数限制
        conversation_turns = history_data.get("conversation_turns", [])
        if len(conversation_turns) > MAX_SESSION_TURNS:
            return json.dumps({
                "status": "error",
                "error_type": "validation_error",
                "message": f"会话轮数超过限制（最多{MAX_SESSION_TURNS}轮）: {len(conversation_turns)}",
                "user_id": user_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 更新会话元数据
        if "session_metadata" not in history_data:
            history_data["session_metadata"] = {}
        
        metadata = history_data["session_metadata"]
        metadata["total_turns"] = len(conversation_turns)
        if "start_time" not in metadata:
            metadata["start_time"] = now
        
        # 写入会话历史文件
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        # 获取文件大小
        file_size = session_path.stat().st_size
        
        return json.dumps({
            "status": "success",
            "message": "会话历史保存成功",
            "user_id": user_id,
            "session_id": session_id,
            "file_path": str(session_path),
            "file_size_bytes": file_size,
            "total_turns": len(conversation_turns),
            "last_updated": history_data["last_updated"]
        }, ensure_ascii=False, indent=2)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error_type": "permission_error",
            "message": f"文件写入权限不足: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)
        
    except OSError as e:
        return json.dumps({
            "status": "error",
            "error_type": "os_error",
            "message": f"文件系统错误（可能磁盘空间不足）: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"保存会话历史失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def append_conversation_turn(
    user_id: str,
    session_id: str,
    user_input: str,
    agent_response: str,
    cache_dir: Optional[str] = None,
    context_summary: Optional[str] = None
) -> str:
    """
    向会话历史追加一轮对话
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        user_input: 用户输入内容
        agent_response: Agent回复内容
        cache_dir: 缓存目录路径（可选）
        context_summary: 本轮上下文摘要（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 加载现有会话历史
        load_result_str = load_session_history(user_id, session_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] in ["success", "not_found"]:
            history_data = load_result["history"]
        else:
            return load_result_str
        
        # 获取对话轮次列表
        conversation_turns = history_data.get("conversation_turns", [])
        
        # 检查是否超过最大轮数限制
        if len(conversation_turns) >= MAX_SESSION_TURNS:
            return json.dumps({
                "status": "error",
                "error_type": "limit_exceeded",
                "message": f"会话已达到最大轮数限制（{MAX_SESSION_TURNS}轮），请创建新会话",
                "user_id": user_id,
                "session_id": session_id,
                "current_turns": len(conversation_turns)
            }, ensure_ascii=False, indent=2)
        
        # 创建新的对话轮次
        turn_number = len(conversation_turns) + 1
        now = datetime.utcnow().isoformat() + "Z"
        
        new_turn = {
            "turn_number": turn_number,
            "timestamp": now,
            "user_input": user_input,
            "agent_response": agent_response
        }
        
        if context_summary:
            new_turn["context_summary"] = context_summary
        
        # 追加到对话列表
        conversation_turns.append(new_turn)
        history_data["conversation_turns"] = conversation_turns
        
        # 更新会话元数据
        if "session_metadata" not in history_data:
            history_data["session_metadata"] = {
                "start_time": now,
                "total_turns": 0,
                "topics_discussed": []
            }
        
        history_data["session_metadata"]["total_turns"] = len(conversation_turns)
        
        # 保存更新后的会话历史
        save_result_str = save_session_history(
            user_id=user_id,
            session_id=session_id,
            history_data=history_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "对话轮次追加成功",
                "user_id": user_id,
                "session_id": session_id,
                "turn_number": turn_number,
                "total_turns": len(conversation_turns)
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"追加对话轮次失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def get_recent_context(
    user_id: str,
    session_id: str,
    window_size: int = 5,
    cache_dir: Optional[str] = None
) -> str:
    """
    获取最近N轮对话作为上下文
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        window_size: 上下文窗口大小（最近N轮，默认5轮）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的上下文数据
    """
    try:
        # 加载会话历史（已经限制了返回轮数）
        load_result_str = load_session_history(
            user_id=user_id,
            session_id=session_id,
            cache_dir=cache_dir,
            max_turns=window_size
        )
        load_result = json.loads(load_result_str)
        
        if load_result["status"] in ["success", "not_found"]:
            history = load_result["history"]
            conversation_turns = history.get("conversation_turns", [])
            
            # 格式化为上下文字符串列表
            context_messages = []
            for turn in conversation_turns:
                context_messages.append({
                    "role": "user",
                    "content": turn["user_input"],
                    "turn": turn["turn_number"],
                    "timestamp": turn["timestamp"]
                })
                context_messages.append({
                    "role": "assistant",
                    "content": turn["agent_response"],
                    "turn": turn["turn_number"],
                    "timestamp": turn["timestamp"]
                })
            
            return json.dumps({
                "status": "success",
                "message": f"成功获取最近{len(conversation_turns)}轮对话上下文",
                "user_id": user_id,
                "session_id": session_id,
                "window_size": window_size,
                "actual_turns": len(conversation_turns),
                "context_messages": context_messages
            }, ensure_ascii=False, indent=2)
        else:
            return load_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"获取上下文失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def create_new_session(
    user_id: str,
    session_id: Optional[str] = None,
    user_age: Optional[int] = None,
    cache_dir: Optional[str] = None
) -> str:
    """
    创建新的会话
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识（可选，未提供则自动生成UUID）
        user_age: 用户年龄（可选，用于记录会话时的年龄）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的创建结果，包含新的session_id
    """
    try:
        # 生成session_id（如果未提供）
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 创建初始会话历史结构
        now = datetime.utcnow().isoformat() + "Z"
        
        history_data = {
            "session_id": session_id,
            "user_id": user_id,
            "conversation_turns": [],
            "session_metadata": {
                "start_time": now,
                "end_time": None,
                "total_turns": 0,
                "topics_discussed": []
            },
            "created_at": now,
            "last_updated": now
        }
        
        if user_age is not None:
            history_data["session_metadata"]["user_age_at_session"] = user_age
        
        # 保存新会话
        save_result_str = save_session_history(
            user_id=user_id,
            session_id=session_id,
            history_data=history_data,
            cache_dir=cache_dir,
            create_if_missing=True
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "新会话创建成功",
                "user_id": user_id,
                "session_id": session_id,
                "file_path": save_result["file_path"]
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"创建新会话失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def list_user_sessions(
    user_id: str,
    cache_dir: Optional[str] = None,
    max_sessions: Optional[int] = None
) -> str:
    """
    列出用户的所有会话
    
    Args:
        user_id: 用户唯一标识
        cache_dir: 缓存目录路径（可选）
        max_sessions: 最多返回的会话数（可选，按时间倒序）
        
    Returns:
        str: JSON格式的会话列表
    """
    try:
        # 确定缓存目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        
        # 检查用户目录是否存在
        if not user_dir.exists():
            return json.dumps({
                "status": "success",
                "message": "用户没有任何会话记录",
                "user_id": user_id,
                "sessions": []
            }, ensure_ascii=False, indent=2)
        
        # 查找所有会话文件
        session_files = list(user_dir.glob("session_*.json"))
        
        # 读取会话元数据
        sessions_info = []
        for session_file in session_files:
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                session_id = session_data.get("session_id")
                metadata = session_data.get("session_metadata", {})
                
                sessions_info.append({
                    "session_id": session_id,
                    "start_time": metadata.get("start_time"),
                    "end_time": metadata.get("end_time"),
                    "total_turns": metadata.get("total_turns", 0),
                    "topics_discussed": metadata.get("topics_discussed", []),
                    "file_path": str(session_file)
                })
            except Exception as e:
                # 跳过损坏的会话文件
                continue
        
        # 按开始时间倒序排序
        sessions_info.sort(
            key=lambda x: x.get("start_time", ""),
            reverse=True
        )
        
        # 限制返回数量
        if max_sessions and max_sessions > 0:
            sessions_info = sessions_info[:max_sessions]
        
        return json.dumps({
            "status": "success",
            "message": f"找到{len(sessions_info)}个会话",
            "user_id": user_id,
            "total_sessions": len(session_files),
            "returned_sessions": len(sessions_info),
            "sessions": sessions_info
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"列出会话失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def get_session_summary(
    user_id: str,
    session_id: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    获取会话的摘要信息
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的会话摘要
    """
    try:
        # 加载会话历史
        load_result_str = load_session_history(user_id, session_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] == "not_found":
            return json.dumps({
                "status": "not_found",
                "message": f"会话不存在: {session_id}",
                "user_id": user_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        elif load_result["status"] != "success":
            return load_result_str
        
        history = load_result["history"]
        metadata = history.get("session_metadata", {})
        conversation_turns = history.get("conversation_turns", [])
        
        # 提取关键信息
        summary = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            "total_turns": len(conversation_turns),
            "topics_discussed": metadata.get("topics_discussed", []),
            "user_age_at_session": metadata.get("user_age_at_session"),
            "first_message": conversation_turns[0]["user_input"] if conversation_turns else None,
            "last_message": conversation_turns[-1]["agent_response"] if conversation_turns else None
        }
        
        return json.dumps({
            "status": "success",
            "message": "会话摘要生成成功",
            "user_id": user_id,
            "session_id": session_id,
            "summary": summary
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"获取会话摘要失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def archive_old_sessions(
    user_id: str,
    keep_recent: int = 10,
    cache_dir: Optional[str] = None
) -> str:
    """
    归档旧的会话历史，保留最近的N个会话
    
    Args:
        user_id: 用户唯一标识
        keep_recent: 保留最近的会话数量（默认10）
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的归档结果
    """
    try:
        # 获取所有会话
        list_result_str = list_user_sessions(user_id, cache_dir)
        list_result = json.loads(list_result_str)
        
        if list_result["status"] != "success":
            return list_result_str
        
        sessions = list_result["sessions"]
        total_sessions = len(sessions)
        
        # 如果会话数量不超过保留数量，不需要归档
        if total_sessions <= keep_recent:
            return json.dumps({
                "status": "success",
                "message": f"会话数量（{total_sessions}）不超过保留数量（{keep_recent}），无需归档",
                "user_id": user_id,
                "total_sessions": total_sessions,
                "archived_count": 0
            }, ensure_ascii=False, indent=2)
        
        # 确定需要归档的会话
        sessions_to_archive = sessions[keep_recent:]
        
        # 创建归档目录
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        archive_dir = user_dir / "archived_sessions"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 移动旧会话到归档目录
        archived_count = 0
        for session in sessions_to_archive:
            try:
                session_file = Path(session["file_path"])
                if session_file.exists():
                    archive_path = archive_dir / session_file.name
                    session_file.rename(archive_path)
                    archived_count += 1
            except Exception as e:
                # 跳过无法归档的文件
                continue
        
        return json.dumps({
            "status": "success",
            "message": f"成功归档{archived_count}个会话",
            "user_id": user_id,
            "total_sessions": total_sessions,
            "kept_sessions": keep_recent,
            "archived_count": archived_count,
            "archive_directory": str(archive_dir)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"归档会话失败: {str(e)}",
            "user_id": user_id
        }, ensure_ascii=False, indent=2)


@tool
def delete_session(
    user_id: str,
    session_id: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    删除指定的会话历史
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的删除结果
    """
    try:
        # 确定文件路径
        base_dir = cache_dir if cache_dir else DEFAULT_CACHE_DIR
        user_dir = Path(base_dir) / user_id
        session_path = user_dir / f"session_{session_id}.json"
        
        # 检查文件是否存在
        if not session_path.exists():
            return json.dumps({
                "status": "not_found",
                "message": f"会话不存在: {session_id}",
                "user_id": user_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        
        # 删除文件
        session_path.unlink()
        
        return json.dumps({
            "status": "success",
            "message": "会话删除成功",
            "user_id": user_id,
            "session_id": session_id,
            "deleted_file": str(session_path)
        }, ensure_ascii=False, indent=2)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error_type": "permission_error",
            "message": f"文件删除权限不足: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"删除会话失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def update_session_topics(
    user_id: str,
    session_id: str,
    topics: List[str],
    cache_dir: Optional[str] = None,
    append_mode: bool = True
) -> str:
    """
    更新会话讨论的主题列表
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        topics: 主题列表
        cache_dir: 缓存目录路径（可选）
        append_mode: 是否追加模式（True=追加，False=覆盖，默认True）
        
    Returns:
        str: JSON格式的更新结果
    """
    try:
        # 加载会话历史
        load_result_str = load_session_history(user_id, session_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] in ["success", "not_found"]:
            history_data = load_result["history"]
        else:
            return load_result_str
        
        # 更新主题列表
        if "session_metadata" not in history_data:
            history_data["session_metadata"] = {}
        
        metadata = history_data["session_metadata"]
        
        if append_mode:
            # 追加模式：合并新旧主题并去重
            existing_topics = metadata.get("topics_discussed", [])
            combined_topics = list(set(existing_topics + topics))
            metadata["topics_discussed"] = combined_topics
        else:
            # 覆盖模式：直接替换
            metadata["topics_discussed"] = topics
        
        # 保存更新后的会话历史
        save_result_str = save_session_history(
            user_id=user_id,
            session_id=session_id,
            history_data=history_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "会话主题更新成功",
                "user_id": user_id,
                "session_id": session_id,
                "topics": metadata["topics_discussed"],
                "total_topics": len(metadata["topics_discussed"])
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"更新会话主题失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)


@tool
def close_session(
    user_id: str,
    session_id: str,
    cache_dir: Optional[str] = None
) -> str:
    """
    关闭会话，标记会话结束时间
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话唯一标识
        cache_dir: 缓存目录路径（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 加载会话历史
        load_result_str = load_session_history(user_id, session_id, cache_dir)
        load_result = json.loads(load_result_str)
        
        if load_result["status"] == "not_found":
            return json.dumps({
                "status": "not_found",
                "message": f"会话不存在: {session_id}",
                "user_id": user_id,
                "session_id": session_id
            }, ensure_ascii=False, indent=2)
        elif load_result["status"] != "success":
            return load_result_str
        
        history_data = load_result["history"]
        
        # 更新结束时间
        if "session_metadata" not in history_data:
            history_data["session_metadata"] = {}
        
        now = datetime.utcnow().isoformat() + "Z"
        history_data["session_metadata"]["end_time"] = now
        
        # 保存更新后的会话历史
        save_result_str = save_session_history(
            user_id=user_id,
            session_id=session_id,
            history_data=history_data,
            cache_dir=cache_dir
        )
        
        save_result = json.loads(save_result_str)
        if save_result["status"] == "success":
            return json.dumps({
                "status": "success",
                "message": "会话已关闭",
                "user_id": user_id,
                "session_id": session_id,
                "end_time": now,
                "total_turns": len(history_data.get("conversation_turns", []))
            }, ensure_ascii=False, indent=2)
        else:
            return save_result_str
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": "unknown_error",
            "message": f"关闭会话失败: {str(e)}",
            "user_id": user_id,
            "session_id": session_id
        }, ensure_ascii=False, indent=2)
