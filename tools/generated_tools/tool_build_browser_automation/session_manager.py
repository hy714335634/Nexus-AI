#!/usr/bin/env python3
"""
浏览器会话存储和管理模块

提供线程安全的会话存储和管理功能，支持会话添加、获取和移除操作。
"""

import threading
import uuid
from typing import Dict, Optional
from bedrock_agentcore.tools.browser_client import BrowserClient
import logging

logger = logging.getLogger(__name__)


class SessionStore:
    """线程安全的浏览器会话存储器"""
    
    def __init__(self, max_sessions: int = 10):
        """
        初始化会话存储器
        
        Args:
            max_sessions: 最大会话数量限制，默认10个
        """
        self._sessions: Dict[str, BrowserClient] = {}
        self._lock = threading.Lock()
        self._max_sessions = max_sessions
        logger.info(f"SessionStore initialized with max_sessions={max_sessions}")
    
    def add_session(self, client: BrowserClient) -> str:
        """
        添加新会话到存储
        
        Args:
            client: BrowserClient实例
            
        Returns:
            str: 生成的唯一会话ID
            
        Raises:
            ValueError: 当达到最大会话数限制时
        """
        with self._lock:
            if len(self._sessions) >= self._max_sessions:
                raise ValueError(f"Maximum sessions ({self._max_sessions}) reached")
            
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = client
            logger.info(f"Session added: {session_id} (total: {len(self._sessions)})")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[BrowserClient]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[BrowserClient]: BrowserClient实例或None（如果不存在）
        """
        with self._lock:
            client = self._sessions.get(session_id)
            if client:
                logger.debug(f"Session retrieved: {session_id}")
            else:
                logger.warning(f"Session not found: {session_id}")
            return client
    
    def remove_session(self, session_id: str) -> bool:
        """
        移除会话并停止客户端
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            client = self._sessions.get(session_id)
            if not client:
                logger.warning(f"Cannot remove: session not found: {session_id}")
                return False
            
            try:
                client.stop()
                logger.info(f"Session client stopped: {session_id}")
            except Exception as e:
                logger.error(f"Error stopping client for session {session_id}: {e}")
            
            del self._sessions[session_id]
            logger.info(f"Session removed: {session_id} (remaining: {len(self._sessions)})")
            return True
    
    def get_all_sessions(self) -> Dict[str, str]:
        """
        获取所有会话的状态信息
        
        Returns:
            Dict[str, str]: 会话ID到状态的映射
        """
        with self._lock:
            return {sid: "active" for sid in self._sessions.keys()}
    
    def clear_all(self) -> int:
        """
        清除所有会话（用于清理）
        
        Returns:
            int: 清除的会话数量
        """
        with self._lock:
            count = len(self._sessions)
            for session_id, client in list(self._sessions.items()):
                try:
                    client.stop()
                except Exception as e:
                    logger.error(f"Error stopping client for session {session_id}: {e}")
            
            self._sessions.clear()
            logger.info(f"All sessions cleared: {count} sessions")
            return count


# 全局会话存储实例
_global_session_store = SessionStore()


def get_session_store() -> SessionStore:
    """
    获取全局会话存储实例
    
    Returns:
        SessionStore: 全局会话存储器
    """
    return _global_session_store
