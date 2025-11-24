"""
Session Service - Agent会话管理

职责:
- 创建和管理Agent会话
- 管理会话消息
- 调用Agent生成响应
- 删除会话（级联删除消息）
"""
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from api.database.dynamodb_client import db_client
from api.models.schemas import (
    AgentSessionRecord,
    AgentSessionMessageRecord,
)
from api.core.exceptions import APIException, ResourceNotFoundError
from api.services.agent_service import agent_service

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""

    def __init__(self):
        self.db_client = db_client
        self.agent_service = agent_service

    def create_session(
        self,
        agent_id: str,
        display_name: Optional[str] = None,
        conversation_mode: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建新会话

        Args:
            agent_id: Agent ID
            display_name: 会话显示名称
            conversation_mode: 会话模式（normal/debug/eval）
            metadata: 会话元数据

        Returns:
            Dict: 创建的会话记录

        Requirements: 6.1
        """
        try:
            # 验证agent存在
            agent = self.agent_service.get_agent(agent_id)
            if not agent:
                raise ResourceNotFoundError("Agent", agent_id)

            # 生成session_id
            session_id = f"sess_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            session_data = AgentSessionRecord(
                agent_id=agent_id,
                session_id=session_id,
                display_name=display_name or f"Session {now.strftime('%Y-%m-%d %H:%M')}",
                conversation_mode=conversation_mode,
                metadata=metadata or {},
                created_at=now,
                last_active_at=now
            )

            self.db_client.create_agent_session(session_data)
            logger.info(f"Created session {session_id} for agent {agent_id}")

            # 重新获取会话记录
            session = self.db_client.get_agent_session(agent_id, session_id)
            return session

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to create session for agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to create session: {str(e)}")

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话详情

        Args:
            session_id: 会话ID

        Returns:
            Dict: 会话详细信息

        Requirements: 6.1
        """
        try:
            # 由于DynamoDB需要agent_id和session_id，我们需要从session_id中提取或查询
            # 这里简化处理：扫描AgentSessions表查找session_id
            # 实际生产环境应该使用GSI或在session_id中编码agent_id

            # 暂时使用简化方法：遍历agents的sessions
            # 更好的方法是添加GSI或在调用时提供agent_id
            sessions_table = self.db_client.agent_sessions_table
            response = sessions_table.scan(
                FilterExpression='session_id = :sid',
                ExpressionAttributeValues={':sid': session_id},
                Limit=1
            )

            items = response.get('Items', [])
            if not items:
                raise ResourceNotFoundError("Session", session_id)

            item = self.db_client._deserialize_item(items[0])
            return item

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {str(e)}")
            raise APIException(f"Failed to get session: {str(e)}")

    def list_sessions(
        self,
        agent_id: str,
        limit: int = 20,
        last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        列出Agent的会话

        Args:
            agent_id: Agent ID
            limit: 每页数量
            last_key: 分页游标

        Returns:
            Dict: 包含items和last_evaluated_key的响应

        Requirements: 6.3
        """
        try:
            result = self.db_client.list_agent_sessions(
                agent_id=agent_id,
                limit=limit,
                last_evaluated_key=last_key,
                descending=True  # 按last_active_at降序
            )

            return result

        except Exception as e:
            logger.error(f"Failed to list sessions for agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to list sessions: {str(e)}")

    def send_message(
        self,
        session_id: str,
        content: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送消息并获取Agent响应

        Args:
            session_id: 会话ID
            content: 消息内容
            role: 消息角色（user/system）
            metadata: 消息元数据

        Returns:
            Dict: 包含用户消息和助手响应的字典

        Requirements: 6.2
        """
        try:
            # 获取会话信息
            session = self.get_session(session_id)
            agent_id = session.get('agent_id')

            now = datetime.now(timezone.utc)

            # 保存用户消息
            user_message_id = f"msg_{uuid.uuid4().hex[:16]}"
            user_message = AgentSessionMessageRecord(
                agent_id=agent_id,
                session_id=session_id,
                message_id=user_message_id,
                role=role,
                content=content,
                metadata=metadata or {},
                created_at=now
            )
            self.db_client.append_session_message(user_message)

            # 调用Agent生成响应
            try:
                invocation_result = self.agent_service.invoke_agent(
                    agent_id=agent_id,
                    input_text=content,
                    session_id=session_id,
                    enable_trace=False
                )

                assistant_content = invocation_result.get('output', '')
                assistant_metadata = {
                    'invocation_id': invocation_result.get('invocation_id'),
                    'duration_ms': invocation_result.get('duration_ms')
                }

            except Exception as e:
                logger.error(f"Failed to invoke agent {agent_id}: {str(e)}")
                assistant_content = f"Error: Failed to generate response - {str(e)}"
                assistant_metadata = {'error': str(e)}

            # 保存助手响应
            assistant_message_id = f"msg_{uuid.uuid4().hex[:16]}"
            assistant_message = AgentSessionMessageRecord(
                agent_id=agent_id,
                session_id=session_id,
                message_id=assistant_message_id,
                role="assistant",
                content=assistant_content,
                metadata=assistant_metadata,
                created_at=datetime.now(timezone.utc)
            )
            self.db_client.append_session_message(assistant_message)

            # 更新会话活跃时间
            self.db_client.update_agent_session_activity(
                agent_id=agent_id,
                session_id=session_id,
                last_active_at=datetime.now(timezone.utc)
            )

            logger.info(f"Sent message to session {session_id}, got response")

            return {
                "user_message": {
                    "message_id": user_message_id,
                    "role": role,
                    "content": content,
                    "created_at": now.isoformat().replace('+00:00', 'Z')
                },
                "assistant_message": {
                    "message_id": assistant_message_id,
                    "role": "assistant",
                    "content": assistant_content,
                    "metadata": assistant_metadata,
                    "created_at": assistant_message.created_at.isoformat().replace('+00:00', 'Z')
                }
            }

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {str(e)}")
            raise APIException(f"Failed to send message: {str(e)}")

    def list_messages(
        self,
        session_id: str,
        limit: int = 100,
        last_key: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        列出会话消息

        Args:
            session_id: 会话ID
            limit: 每页数量
            last_key: 分页游标

        Returns:
            Dict: 包含items和last_evaluated_key的响应

        Requirements: 6.4
        """
        try:
            result = self.db_client.list_session_messages(
                session_id=session_id,
                limit=limit,
                last_evaluated_key=last_key,
                ascending=True  # 按created_at升序
            )

            return result

        except Exception as e:
            logger.error(f"Failed to list messages for session {session_id}: {str(e)}")
            raise APIException(f"Failed to list messages: {str(e)}")

    def delete_session(self, session_id: str) -> None:
        """
        删除会话（级联删除所有消息）

        Args:
            session_id: 会话ID

        Requirements: 6.5, 10.3
        """
        try:
            # 获取会话信息
            session = self.get_session(session_id)
            agent_id = session.get('agent_id')

            logger.info(f"Deleting session {session_id} and all messages")

            # 删除所有消息（分批处理）
            last_key = None
            deleted_messages = 0

            while True:
                messages_result = self.db_client.list_session_messages(
                    session_id=session_id,
                    limit=100,
                    last_evaluated_key=last_key
                )

                messages = messages_result.get('items', [])
                if not messages:
                    break

                # 批量删除消息
                for message in messages:
                    try:
                        self.db_client.agent_session_messages_table.delete_item(
                            Key={
                                'session_id': session_id,
                                'message_id': message.get('message_id')
                            }
                        )
                        deleted_messages += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete message {message.get('message_id')}: {str(e)}")

                last_key = messages_result.get('last_evaluated_key')
                if not last_key:
                    break

            # 删除会话记录
            self.db_client.agent_sessions_table.delete_item(
                Key={
                    'agent_id': agent_id,
                    'session_id': session_id
                }
            )

            logger.info(f"Successfully deleted session {session_id} and {deleted_messages} messages")

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            raise APIException(f"Failed to delete session: {str(e)}")


# Singleton instance
session_service = SessionService()
