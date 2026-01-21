"""
Cloud Resource Manager - handles AgentCore runtime, ECR and DynamoDB resources

Provides functionality for:
- Detecting AgentCore runtime resources
- Detecting ECR repositories
- Detecting DynamoDB agent records
- Deleting cloud resources
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentCoreRuntime:
    """AgentCore runtime information"""
    arn: str
    name: str
    status: str
    region: str


@dataclass
class ECRRepository:
    """ECR repository information"""
    repository_name: str
    repository_uri: str
    repository_arn: str
    image_count: int
    region: str


@dataclass
class DynamoDBAgent:
    """DynamoDB Agent record information"""
    agent_id: str
    agent_name: str
    project_id: Optional[str]
    status: str
    deployment_type: str
    created_at: Optional[str]
    # 关联的会话和调用记录数量
    session_count: int = 0
    invocation_count: int = 0


@dataclass
class CloudResources:
    """Container for cloud resources"""
    agentcore_runtime: Optional[AgentCoreRuntime] = None
    ecr_repository: Optional[ECRRepository] = None
    dynamodb_agents: List[DynamoDBAgent] = field(default_factory=list)
    
    def has_resources(self) -> bool:
        """Check if any cloud resources exist"""
        return (
            self.agentcore_runtime is not None or 
            self.ecr_repository is not None or
            len(self.dynamodb_agents) > 0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        if self.agentcore_runtime:
            result['agentcore_runtime'] = {
                'arn': self.agentcore_runtime.arn,
                'name': self.agentcore_runtime.name,
                'status': self.agentcore_runtime.status,
                'region': self.agentcore_runtime.region,
            }
        if self.ecr_repository:
            result['ecr_repository'] = {
                'repository_name': self.ecr_repository.repository_name,
                'repository_uri': self.ecr_repository.repository_uri,
                'repository_arn': self.ecr_repository.repository_arn,
                'image_count': self.ecr_repository.image_count,
                'region': self.ecr_repository.region,
            }
        if self.dynamodb_agents:
            result['dynamodb_agents'] = [
                {
                    'agent_id': agent.agent_id,
                    'agent_name': agent.agent_name,
                    'project_id': agent.project_id,
                    'status': agent.status,
                    'deployment_type': agent.deployment_type,
                    'created_at': agent.created_at,
                    'session_count': agent.session_count,
                    'invocation_count': agent.invocation_count,
                }
                for agent in self.dynamodb_agents
            ]
        return result


@dataclass
class DeleteResult:
    """Result of delete operation"""
    success: bool
    resource_type: str
    resource_name: str
    error: Optional[str] = None


class CloudResourceManager:
    """Manages cloud resources for Nexus-AI agents"""
    
    def __init__(self, region: str = None):
        """
        初始化云资源管理器
        
        Args:
            region: AWS 区域（默认从配置或 us-west-2）
        """
        self.region = region or self._get_default_region()
        self._agentcore_control_client = None  # 用于管理 runtime（创建、删除、列出）
        self._ecr_client = None
        self._dynamodb_client = None
        # 存储检测过程中的错误信息
        self._detection_errors: Dict[str, str] = {}
    
    @staticmethod
    def _get_default_region() -> str:
        """获取默认区域"""
        try:
            from api.v2.config import settings
            return settings.AWS_REGION
        except ImportError:
            return 'us-west-2'
    
    def _get_agentcore_control_client(self):
        """
        获取或创建 AgentCore Control 客户端
        
        注意：bedrock-agentcore-control 用于管理 runtime（创建、删除、列出）
              bedrock-agentcore 用于调用 runtime（invoke）
        """
        if self._agentcore_control_client is None:
            import boto3
            self._agentcore_control_client = boto3.client(
                'bedrock-agentcore-control',
                region_name=self.region
            )
        return self._agentcore_control_client
    
    def get_detection_errors(self) -> Dict[str, str]:
        """获取检测过程中的错误信息"""
        return self._detection_errors.copy()
    
    def _get_ecr_client(self):
        """获取或创建 ECR 客户端"""
        if self._ecr_client is None:
            import boto3
            self._ecr_client = boto3.client('ecr', region_name=self.region)
        return self._ecr_client
    
    def _get_dynamodb_client(self):
        """获取或创建 DynamoDB 客户端"""
        if self._dynamodb_client is None:
            try:
                from api.v2.database import db_client
                self._dynamodb_client = db_client
            except ImportError:
                logger.debug("Failed to import db_client, DynamoDB operations will be skipped")
                self._dynamodb_client = None
        return self._dynamodb_client
    
    def detect_resources(self, agent_name: str) -> CloudResources:
        """
        检测 Agent 的云资源
        
        Args:
            agent_name: Agent 名称
        
        Returns:
            CloudResources 对象，包含检测到的资源
        """
        # 清空之前的检测错误
        self._detection_errors = {}
        
        resources = CloudResources()
        
        # 检测 AgentCore runtime
        runtime = self._detect_agentcore_runtime(agent_name)
        if runtime:
            resources.agentcore_runtime = runtime
        
        # 检测 ECR 仓库
        ecr = self._detect_ecr_repository(agent_name)
        if ecr:
            resources.ecr_repository = ecr
        
        # 检测 DynamoDB 记录
        dynamodb_agents = self._detect_dynamodb_agents(agent_name)
        if dynamodb_agents:
            resources.dynamodb_agents = dynamodb_agents
        
        return resources
    
    def _detect_agentcore_runtime(self, agent_name: str) -> Optional[AgentCoreRuntime]:
        """
        检测 Agent 的 AgentCore runtime
        
        使用 bedrock-agentcore-control 客户端列出和管理 runtime
        """
        try:
            from botocore.exceptions import ClientError, NoCredentialsError
            
            client = self._get_agentcore_control_client()
            
            # 列出 agent runtimes 并查找匹配项
            paginator = client.get_paginator('list_agent_runtimes')
            for page in paginator.paginate():
                for runtime in page.get('agentRuntimeSummaries', []):
                    runtime_name = runtime.get('agentRuntimeName', '')
                    # 通过名称匹配（agent 名称可能有后缀）
                    if agent_name in runtime_name or runtime_name.startswith(agent_name):
                        return AgentCoreRuntime(
                            arn=runtime.get('agentRuntimeArn', ''),
                            name=runtime_name,
                            status=runtime.get('status', 'UNKNOWN'),
                            region=self.region
                        )
            
            return None
            
        except NoCredentialsError as e:
            error_msg = f"AWS credentials not found: {e}"
            logger.warning(error_msg)
            self._detection_errors['agentcore_runtime'] = error_msg
            return None
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"AWS API error ({error_code}): {e}"
            logger.warning(error_msg)
            self._detection_errors['agentcore_runtime'] = error_msg
            return None
        except Exception as e:
            error_msg = f"Failed to detect AgentCore runtime: {e}"
            logger.warning(error_msg)
            self._detection_errors['agentcore_runtime'] = error_msg
            return None
    
    def _detect_ecr_repository(self, agent_name: str) -> Optional[ECRRepository]:
        """检测 Agent 的 ECR 仓库"""
        try:
            from botocore.exceptions import ClientError, NoCredentialsError
            
            client = self._get_ecr_client()
            
            # 常见的 ECR 仓库命名模式
            repo_patterns = [
                f"nexus-ai/{agent_name}",
                f"nexus-ai-{agent_name}",
                agent_name
            ]
            
            for repo_name in repo_patterns:
                try:
                    response = client.describe_repositories(repositoryNames=[repo_name])
                    if response.get('repositories'):
                        repo = response['repositories'][0]
                        
                        # 获取镜像数量
                        images_response = client.list_images(repositoryName=repo_name)
                        image_count = len(images_response.get('imageIds', []))
                        
                        return ECRRepository(
                            repository_name=repo.get('repositoryName', ''),
                            repository_uri=repo.get('repositoryUri', ''),
                            repository_arn=repo.get('repositoryArn', ''),
                            image_count=image_count,
                            region=self.region
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] != 'RepositoryNotFoundException':
                        raise
            
            return None
            
        except (ImportError, Exception) as e:
            logger.debug(f"Failed to detect ECR repository: {e}")
            return None
    
    def _detect_dynamodb_agents(self, agent_name: str) -> List[DynamoDBAgent]:
        """
        检测 DynamoDB 中的 Agent 记录
        
        通过 agent_name 和 project_id 匹配查找相关记录
        """
        agents = []
        
        try:
            db_client = self._get_dynamodb_client()
            if db_client is None:
                return agents
            
            # 扫描 agents 表查找匹配的记录
            # 匹配条件：agent_name 匹配 或 project_id 匹配
            result = db_client.list_agents(limit=100)
            
            for agent in result.get('items', []):
                agent_id = agent.get('agent_id', '')
                db_agent_name = agent.get('agent_name', '')
                project_id = agent.get('project_id', '')
                
                # 匹配逻辑：
                # 1. agent_name 完全匹配
                # 2. project_id 完全匹配
                # 3. agent_id 包含 agent_name（如 local_xxx 格式）
                if (db_agent_name == agent_name or 
                    project_id == agent_name or
                    agent_name in agent_id):
                    
                    # 获取关联的会话数量
                    session_count = self._count_agent_sessions(db_client, agent_id)
                    
                    # 获取关联的调用记录数量
                    invocation_count = agent.get('total_invocations', 0)
                    
                    agents.append(DynamoDBAgent(
                        agent_id=agent_id,
                        agent_name=db_agent_name,
                        project_id=project_id,
                        status=agent.get('status', 'unknown'),
                        deployment_type=agent.get('deployment_type', 'local'),
                        created_at=agent.get('created_at'),
                        session_count=session_count,
                        invocation_count=invocation_count
                    ))
            
            return agents
            
        except Exception as e:
            logger.debug(f"Failed to detect DynamoDB agents: {e}")
            return agents
    
    def _count_agent_sessions(self, db_client, agent_id: str) -> int:
        """统计 Agent 的会话数量"""
        try:
            sessions = db_client.list_sessions(agent_id, limit=100)
            return len(sessions)
        except Exception:
            return 0
    
    def delete_agentcore_runtime(self, runtime: AgentCoreRuntime) -> DeleteResult:
        """
        删除 AgentCore runtime
        
        使用 bedrock-agentcore-control 客户端删除 runtime
        
        Args:
            runtime: 要删除的 AgentCoreRuntime
        
        Returns:
            DeleteResult 操作结果
        """
        try:
            from botocore.exceptions import ClientError
            
            client = self._get_agentcore_control_client()
            client.delete_agent_runtime(agentRuntimeArn=runtime.arn)
            
            return DeleteResult(
                success=True,
                resource_type='agentcore_runtime',
                resource_name=runtime.name
            )
            
        except Exception as e:
            logger.error(f"Failed to delete AgentCore runtime: {e}")
            return DeleteResult(
                success=False,
                resource_type='agentcore_runtime',
                resource_name=runtime.name,
                error=str(e)
            )
    
    def delete_ecr_repository(self, repository: ECRRepository, force: bool = True) -> DeleteResult:
        """
        删除 ECR 仓库
        
        Args:
            repository: 要删除的 ECRRepository
            force: 如果为 True，即使仓库包含镜像也删除
        
        Returns:
            DeleteResult 操作结果
        """
        try:
            from botocore.exceptions import ClientError
            
            client = self._get_ecr_client()
            client.delete_repository(
                repositoryName=repository.repository_name,
                force=force
            )
            
            return DeleteResult(
                success=True,
                resource_type='ecr_repository',
                resource_name=repository.repository_name
            )
            
        except Exception as e:
            logger.error(f"Failed to delete ECR repository: {e}")
            return DeleteResult(
                success=False,
                resource_type='ecr_repository',
                resource_name=repository.repository_name,
                error=str(e)
            )
    
    def delete_dynamodb_agent(self, agent: DynamoDBAgent, delete_related: bool = True) -> DeleteResult:
        """
        删除 DynamoDB 中的 Agent 记录
        
        Args:
            agent: 要删除的 DynamoDBAgent
            delete_related: 如果为 True，同时删除关联的会话和消息
        
        Returns:
            DeleteResult 操作结果
        """
        try:
            db_client = self._get_dynamodb_client()
            if db_client is None:
                return DeleteResult(
                    success=False,
                    resource_type='dynamodb_agent',
                    resource_name=agent.agent_id,
                    error="DynamoDB client not available"
                )
            
            # 删除关联的会话和消息
            if delete_related:
                self._delete_agent_sessions(db_client, agent.agent_id)
            
            # 删除 Agent 记录
            db_client.delete_agent(agent.agent_id)
            
            return DeleteResult(
                success=True,
                resource_type='dynamodb_agent',
                resource_name=agent.agent_id
            )
            
        except Exception as e:
            logger.error(f"Failed to delete DynamoDB agent: {e}")
            return DeleteResult(
                success=False,
                resource_type='dynamodb_agent',
                resource_name=agent.agent_id,
                error=str(e)
            )
    
    def _delete_agent_sessions(self, db_client, agent_id: str) -> int:
        """
        删除 Agent 的所有会话和消息
        
        Returns:
            删除的会话数量
        """
        deleted_count = 0
        try:
            # 获取 Agent 的所有会话
            sessions = db_client.list_sessions(agent_id, limit=100)
            
            for session in sessions:
                session_id = session.get('session_id')
                if session_id:
                    # 删除会话的消息（通过 session_id 查询并删除）
                    try:
                        messages = db_client.list_messages(session_id, limit=1000)
                        # 消息表使用复合主键 (session_id, created_at)
                        # 需要逐条删除
                        for msg in messages:
                            try:
                                db_client.messages_table.delete_item(
                                    Key={
                                        'session_id': session_id,
                                        'created_at': msg.get('created_at')
                                    }
                                )
                            except Exception as e:
                                logger.debug(f"Failed to delete message: {e}")
                    except Exception as e:
                        logger.debug(f"Failed to delete messages for session {session_id}: {e}")
                    
                    # 删除会话
                    try:
                        db_client.sessions_table.delete_item(
                            Key={'session_id': session_id}
                        )
                        deleted_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to delete session {session_id}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.debug(f"Failed to delete agent sessions: {e}")
            return deleted_count
    
    def delete_all_resources(self, resources: CloudResources) -> List[DeleteResult]:
        """
        删除所有云资源
        
        Args:
            resources: 要删除的 CloudResources
        
        Returns:
            每个资源的 DeleteResult 列表
        """
        results = []
        
        # 删除 AgentCore runtime
        if resources.agentcore_runtime:
            result = self.delete_agentcore_runtime(resources.agentcore_runtime)
            results.append(result)
        
        # 删除 ECR 仓库
        if resources.ecr_repository:
            result = self.delete_ecr_repository(resources.ecr_repository)
            results.append(result)
        
        # 删除 DynamoDB 记录
        for agent in resources.dynamodb_agents:
            result = self.delete_dynamodb_agent(agent)
            results.append(result)
        
        return results
