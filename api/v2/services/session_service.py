"""
Session Service - 会话管理服务

职责:
- 创建和管理 Agent 对话会话
- 消息管理
"""
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from api.v2.database import db_client

logger = logging.getLogger(__name__)


def generate_ulid() -> str:
    """生成 ULID 格式的消息 ID（时间有序）"""
    import time
    import random
    import string
    
    # 时间戳部分 (10 字符)
    timestamp = int(time.time() * 1000)
    chars = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
    time_part = ''
    for _ in range(10):
        time_part = chars[timestamp % 32] + time_part
        timestamp //= 32
    
    # 随机部分 (16 字符)
    random_part = ''.join(random.choices(chars, k=16))
    
    return time_part + random_part


class SessionService:
    """会话管理服务"""
    
    def __init__(self):
        self.db = db_client
    
    def create_session(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建会话"""
        # AgentCore 要求 runtimeSessionId 至少 33 个字符
        # 使用完整的 UUID (36 字符) 确保兼容性
        session_id = f"sess-{uuid.uuid4()}"  # 格式: sess-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (41 字符)
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        session_data = {
            'session_id': session_id,
            'agent_id': agent_id,
            'user_id': user_id or 'anonymous',
            'display_name': display_name or f"会话 {session_id[-8:]}",
            'status': 'active',
            'message_count': 0,
            'last_active_at': now,
            'metadata': metadata or {}
        }
        
        self.db.create_session(session_data)
        logger.info(f"Created session {session_id} for agent {agent_id}")
        
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详情"""
        return self.db.get_session(session_id)
    
    def list_sessions(self, agent_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """列表 Agent 的会话"""
        return self.db.list_sessions(agent_id, limit=limit)
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """添加消息到会话"""
        message_id = generate_ulid()
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        message_data = {
            'session_id': session_id,
            'message_id': message_id,
            'role': role,
            'content': content,
            'created_at': now,
            'metadata': metadata or {}
        }
        
        self.db.create_message(message_data)
        
        # 更新会话的消息计数和最后活跃时间
        session = self.db.get_session(session_id)
        if session:
            # 简化更新，实际应该使用原子操作
            pass
        
        return message_data
    
    def list_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """列表会话消息"""
        return self.db.list_messages(session_id, limit=limit)
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """关闭会话"""
        session = self.db.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # 这里需要实现会话更新
        # return self.db.update_session(session_id, {'status': 'closed'})
        return {'session_id': session_id, 'status': 'closed'}


# 全局单例
session_service = SessionService()
