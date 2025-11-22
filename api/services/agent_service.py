"""
Agent Service - Agent实例管理和调用

职责:
- 注册Agent实例（Deployer阶段调用）
- 查询Agent详情和列表
- 调用Agent（仅支持AgentCore部署）
- 更新运行时统计
- 删除Agent（级联删除）
"""
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from api.database.dynamodb_client import db_client
from api.models.schemas import (
    AgentRecord,
    AgentStatus,
    AgentCoreConfig,
    RuntimeStats,
)
from api.core.exceptions import APIException, ResourceNotFoundError

logger = logging.getLogger(__name__)


class AgentService:
    """Agent管理服务"""

    def __init__(self):
        self.db_client = db_client

    def register_agent(
        self,
        agent_id: str,
        project_id: str,
        agent_name: str,
        agentcore_config: AgentCoreConfig,
        capabilities: Optional[List[str]] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        version: str = "v1.0.0",
        **kwargs
    ) -> Dict[str, Any]:
        """
        注册Agent实例（Deployer阶段调用）

        Args:
            agent_id: Agent ID
            project_id: 项目ID
            agent_name: Agent名称
            agentcore_config: AgentCore部署配置
            capabilities: Agent能力列表
            description: Agent描述
            category: Agent类别
            version: Agent版本
            **kwargs: 其他字段

        Returns:
            Dict: 创建的Agent记录

        Requirements: 4.1
        """
        try:
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            # 初始化runtime_stats
            runtime_stats = RuntimeStats(
                total_invocations=0,
                successful_invocations=0,
                failed_invocations=0,
                avg_duration_ms=0.0,
                last_invoked_at=None
            )

            agent_data = AgentRecord(
                agent_id=agent_id,
                project_id=project_id,
                agent_name=agent_name,
                description=description,
                category=category,
                version=version,
                status=AgentStatus.RUNNING,  # 注册后设为running
                agentcore_config=agentcore_config,
                capabilities=capabilities or [],
                runtime_stats=runtime_stats,
                created_at=now,
                updated_at=now,
                deployed_at=now,
                **kwargs
            )

            self.db_client.create_agent_record(agent_data)
            logger.info(f"Registered agent {agent_id} for project {project_id}")

            # 重新获取Agent记录
            agent = self.db_client.get_agent_record(agent_id)
            return agent

        except Exception as e:
            logger.error(f"Failed to register agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to register agent: {str(e)}")

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        查询Agent详情

        Args:
            agent_id: Agent ID

        Returns:
            Dict: Agent详细信息

        Requirements: 4.2
        """
        try:
            agent = self.db_client.get_agent_record(agent_id)
            if not agent:
                raise ResourceNotFoundError("Agent", agent_id)

            return agent

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to get agent: {str(e)}")

    def list_agents(
        self,
        project_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        limit: int = 20,
        last_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询Agent列表

        Args:
            project_id: 项目ID过滤
            status: 状态过滤
            limit: 每页数量
            last_key: 分页游标

        Returns:
            Dict: 包含items和last_evaluated_key的响应

        Requirements: 4.3
        """
        try:
            if project_id:
                agents = self.db_client.list_agents_by_project(project_id)
                # 应用状态过滤
                if status:
                    agents = [a for a in agents if a.get('status') == status.value]

                # 简单分页处理
                start_idx = 0
                if last_key:
                    try:
                        start_idx = int(last_key)
                    except ValueError:
                        start_idx = 0

                end_idx = start_idx + limit
                paginated_agents = agents[start_idx:end_idx]

                next_key = None
                if end_idx < len(agents):
                    next_key = str(end_idx)

                return {
                    "items": paginated_agents,
                    "last_evaluated_key": next_key
                }
            else:
                # 全局查询（scan）
                result = self.db_client.list_agents(limit=limit, last_key=last_key)

                # 应用状态过滤
                if status:
                    result["items"] = [a for a in result["items"] if a.get('status') == status.value]

                return result

        except Exception as e:
            logger.error(f"Failed to list agents: {str(e)}")
            raise APIException(f"Failed to list agents: {str(e)}")

    def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        **kwargs
    ) -> None:
        """
        更新Agent状态

        Args:
            agent_id: Agent ID
            status: 新状态
            **kwargs: 其他字段

        Requirements: 4.4
        """
        try:
            self.db_client.update_agent_status(agent_id, status, **kwargs)
            logger.info(f"Updated agent {agent_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Failed to update agent status: {str(e)}")
            raise APIException(f"Failed to update agent status: {str(e)}")

    def invoke_agent(
        self,
        agent_id: str,
        input_text: str,
        session_id: Optional[str] = None,
        enable_trace: bool = False,
        end_session: bool = False,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        调用Agent（仅支持AgentCore部署）

        Args:
            agent_id: Agent ID
            input_text: 输入文本
            session_id: 会话ID（可选，用于多轮对话）
            enable_trace: 是否启用追踪
            end_session: 是否结束会话
            session_state: 会话状态

        Returns:
            Dict: 调用响应（包含output, session_id, trace等）

        Requirements: 5.1, 5.2, 5.3
        """
        start_time = datetime.now(timezone.utc)
        invocation_id = str(uuid.uuid4())

        try:
            # 1. 验证Agent存在且状态正确
            agent = self.get_agent(agent_id)
            agent_status = AgentStatus(agent.get('status', 'offline'))

            if agent_status not in [AgentStatus.RUNNING, AgentStatus.OFFLINE]:
                raise APIException(
                    f"Agent {agent_id} is not available for invocation. Status: {agent_status.value}"
                )

            # 2. 获取AgentCore配置
            agentcore_config = agent.get('agentcore_config')
            if not agentcore_config:
                raise APIException(f"Agent {agent_id} does not have AgentCore configuration")

            # 3. 调用AWS Bedrock AgentCore
            try:
                # 导入boto3和botocore
                try:
                    import boto3
                    from botocore.exceptions import ClientError
                except ImportError:
                    raise APIException("boto3 is not installed. Cannot invoke AgentCore.")

                bedrock_agent = boto3.client('bedrock-agent-runtime')

                # 生成或使用提供的session_id
                if not session_id:
                    session_id = str(uuid.uuid4())

                # 构建请求参数
                invoke_params = {
                    'agentId': agentcore_config['agent_arn'].split('/')[-1],
                    'agentAliasId': agentcore_config['agent_alias_id'],
                    'sessionId': session_id,
                    'inputText': input_text,
                    'enableTrace': enable_trace,
                    'endSession': end_session
                }

                if session_state:
                    invoke_params['sessionState'] = session_state

                response = bedrock_agent.invoke_agent(**invoke_params)

                # 处理响应（流式响应）
                output_text = ""
                trace_data = []

                for event in response.get('completion', []):
                    if 'chunk' in event:
                        chunk = event['chunk']
                        if 'bytes' in chunk:
                            output_text += chunk['bytes'].decode('utf-8')
                    elif 'trace' in event:
                        trace_data.append(event['trace'])

                # 计算调用时长
                end_time = datetime.now(timezone.utc)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # 4. 记录调用
                invocation_record = {
                    'invocation_id': invocation_id,
                    'agent_id': agent_id,
                    'session_id': session_id,
                    'input_text': input_text,
                    'output_text': output_text,
                    'duration_ms': duration_ms,
                    'status': 'success',
                    'timestamp': end_time.isoformat().replace('+00:00', 'Z'),
                    'trace': trace_data if enable_trace else None
                }

                self.db_client.create_invocation(invocation_record)

                # 5. 更新运行时统计
                self.update_runtime_stats(agent_id, duration_ms, success=True)

                logger.info(f"Agent {agent_id} invoked successfully, duration: {duration_ms}ms")

                return {
                    'invocation_id': invocation_id,
                    'session_id': session_id,
                    'output': output_text,
                    'trace': trace_data if enable_trace else None,
                    'duration_ms': duration_ms,
                    'status': 'success'
                }

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                logger.error(f"AWS Bedrock error: {error_code} - {error_message}")

                # 计算调用时长
                end_time = datetime.now(timezone.utc)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # 记录失败的调用
                invocation_record = {
                    'invocation_id': invocation_id,
                    'agent_id': agent_id,
                    'session_id': session_id or str(uuid.uuid4()),
                    'input_text': input_text,
                    'output_text': None,
                    'duration_ms': duration_ms,
                    'status': 'failed',
                    'error_message': f"{error_code}: {error_message}",
                    'timestamp': end_time.isoformat().replace('+00:00', 'Z')
                }

                self.db_client.create_invocation(invocation_record)

                # 更新运行时统计（失败）
                self.update_runtime_stats(agent_id, duration_ms, success=False)

                raise APIException(f"Failed to invoke agent: {error_code} - {error_message}")

        except (ResourceNotFoundError, APIException):
            raise
        except Exception as e:
            logger.error(f"Failed to invoke agent {agent_id}: {str(e)}")

            # 计算调用时长
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # 记录失败的调用
            invocation_record = {
                'invocation_id': invocation_id,
                'agent_id': agent_id,
                'session_id': session_id or str(uuid.uuid4()),
                'input_text': input_text,
                'output_text': None,
                'duration_ms': duration_ms,
                'status': 'failed',
                'error_message': str(e),
                'timestamp': end_time.isoformat().replace('+00:00', 'Z')
            }

            try:
                self.db_client.create_invocation(invocation_record)
                self.update_runtime_stats(agent_id, duration_ms, success=False)
            except:
                pass  # 忽略记录失败

            raise APIException(f"Failed to invoke agent: {str(e)}")

    def update_runtime_stats(
        self,
        agent_id: str,
        duration_ms: int,
        success: bool = True
    ) -> None:
        """
        更新运行时统计

        Args:
            agent_id: Agent ID
            duration_ms: 调用时长（毫秒）
            success: 是否成功

        Requirements: 5.5
        """
        try:
            agent = self.db_client.get_agent_record(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found, skipping runtime stats update")
                return

            runtime_stats = agent.get('runtime_stats', {})

            # 更新统计
            total_invocations = runtime_stats.get('total_invocations', 0) + 1
            successful_invocations = runtime_stats.get('successful_invocations', 0)
            failed_invocations = runtime_stats.get('failed_invocations', 0)
            avg_duration_ms = runtime_stats.get('avg_duration_ms', 0.0)

            if success:
                successful_invocations += 1
            else:
                failed_invocations += 1

            # 计算新的平均时长（使用增量算法）
            if total_invocations == 1:
                new_avg_duration = float(duration_ms)
            else:
                new_avg_duration = (avg_duration_ms * (total_invocations - 1) + duration_ms) / total_invocations

            # 更新Agent记录
            now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            updated_stats = {
                'total_invocations': total_invocations,
                'successful_invocations': successful_invocations,
                'failed_invocations': failed_invocations,
                'avg_duration_ms': round(new_avg_duration, 2),
                'last_invoked_at': now
            }

            # 使用update_agent_status方法更新runtime_stats
            self.db_client.update_agent_status(agent_id, AgentStatus(agent['status']), runtime_stats=updated_stats)

            logger.info(
                f"Updated runtime stats for agent {agent_id}: "
                f"{total_invocations} total, {successful_invocations} success, "
                f"{failed_invocations} failed, avg {new_avg_duration:.2f}ms"
            )

        except Exception as e:
            logger.error(f"Failed to update runtime stats for agent {agent_id}: {str(e)}")
            # 不抛出异常，避免影响主流程

    def delete_agent(self, agent_id: str) -> None:
        """
        删除Agent（级联删除所有关联数据）

        级联删除顺序:
        1. AgentInstances (Agent本身)

        注意: 其他关联数据（sessions, invocations）的删除方法将在后续添加

        Args:
            agent_id: Agent ID

        Requirements: 4.5, 10.3
        """
        try:
            # 验证Agent存在
            agent = self.db_client.get_agent_record(agent_id)
            if not agent:
                raise ResourceNotFoundError("Agent", agent_id)

            logger.info(f"Deleting agent {agent_id}")

            # 删除Agent记录
            self.db_client.delete_agent_record(agent_id)

            logger.info(f"Successfully deleted agent {agent_id}")

        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
            raise APIException(f"Failed to delete agent: {str(e)}")


# Singleton instance
agent_service = AgentService()
