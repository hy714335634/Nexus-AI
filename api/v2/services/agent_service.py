"""
Agent Service - Agent 管理服务

职责:
- 注册 Agent 实例
- 查询 Agent 详情和列表
- 调用 Agent
- 更新 Agent 状态和统计
- 扫描本地项目目录中的 Agents
"""
import uuid
import logging
import os
import yaml
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from api.v2.database import db_client
from api.v2.models.schemas import AgentStatus

logger = logging.getLogger(__name__)


def _get_project_root() -> Path:
    """获取项目根目录"""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent.parent


class AgentService:
    """Agent 管理服务"""
    
    def __init__(self):
        self.db = db_client
        self._local_agents_cache = None
        self._cache_time = None
    
    def _scan_local_agents(self) -> List[Dict[str, Any]]:
        """扫描本地 projects 目录中的 Agents，优先读取 project_config.json"""
        agents = []
        project_root = _get_project_root()
        
        # 只扫描 projects 目录
        projects_dir = project_root / "projects"
        if not projects_dir.exists():
            return agents
            
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir() or project_dir.name.startswith('.'):
                continue
            
            project_config_file = project_dir / "project_config.json"
            status_file = project_dir / "status.yaml"
            
            # 优先使用 project_config.json
            if project_config_file.exists():
                agent_info = self._parse_project_config(project_dir, project_config_file)
                if agent_info:
                    agents.append(agent_info)
            # 回退到 status.yaml
            elif status_file.exists():
                agent_info = self._parse_status_yaml(project_dir, status_file)
                if agent_info:
                    agents.append(agent_info)
        
        return agents
    
    def _parse_project_config(self, project_dir: Path, config_file: Path) -> Optional[Dict[str, Any]]:
        """从 project_config.json 解析 Agent 信息"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            project_name = config.get('project_name', project_dir.name)
            
            # 从 agent_scripts 获取脚本信息
            agent_scripts = config.get('agent_scripts', [])
            script_info = agent_scripts[0] if agent_scripts else {}
            script_path = script_info.get('script_path')
            argparse_params = script_info.get('argparse_params', [])
            dependencies = script_info.get('dependencies', [])
            
            # 从 prompt_files 获取 agent 信息
            prompt_files = config.get('prompt_files', [])
            prompt_info = prompt_files[0] if prompt_files else {}
            prompt_path = prompt_info.get('prompt_path')
            agent_info = prompt_info.get('agent_info', {})
            metadata = prompt_info.get('metadata', {})
            
            agent_name = agent_info.get('name', project_name)
            description = agent_info.get('description', '')
            category = agent_info.get('category', 'project')
            tags = metadata.get('tags', [])
            supported_models = metadata.get('supported_models', [])
            tools_dependencies = metadata.get('tools_dependencies', [])
            
            # 获取工具信息
            generated_tools = config.get('generated_tools', [])
            total_tools = config.get('total_tools', len(generated_tools))
            
            # 检查是否有 agentcore 配置
            agentcore_config = config.get('agentcore')
            
            # 检查构建状态
            summary = config.get('summary', {})
            all_valid = (
                summary.get('all_scripts_valid', False) and 
                summary.get('all_prompts_valid', False)
            )
            
            # 确定部署类型
            deployment_type = 'agentcore' if agentcore_config else 'local'
            
            # 确定状态
            if agentcore_config and agentcore_config.get('agent_arn'):
                status = AgentStatus.RUNNING.value
            elif all_valid and script_path:
                status = AgentStatus.RUNNING.value
            else:
                status = AgentStatus.OFFLINE.value
            
            return {
                'agent_id': f"local_{project_dir.name}",
                'project_id': project_dir.name,
                'agent_name': agent_name,
                'description': description,
                'category': category,
                'version': '1.0.0',
                'status': status,
                'deployment_type': deployment_type,
                'agentcore_config': agentcore_config,
                'agent_path': script_path,
                'prompt_path': prompt_path,
                'code_path': script_path,
                'tags': tags,
                'supported_models': supported_models,
                'tools_dependencies': tools_dependencies,
                'argparse_params': argparse_params,
                'dependencies': dependencies,
                'total_tools': total_tools,
                'created_at': config.get('validation_timestamp'),
                'updated_at': config.get('validation_timestamp'),
                'total_invocations': 0,
                'successful_invocations': 0,
                'failed_invocations': 0,
                'avg_duration_ms': 0,
                'source': 'local_project'
            }
        except Exception as e:
            logger.warning(f"Failed to parse project_config.json for {project_dir.name}: {e}")
            return None
    
    def _parse_status_yaml(self, project_dir: Path, status_file: Path) -> Optional[Dict[str, Any]]:
        """从 status.yaml 解析 Agent 信息（回退方案）"""
        project_root = _get_project_root()
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status_data = yaml.safe_load(f)
            
            project_info = status_data.get('project_info', [])
            if not project_info:
                return None
            
            info = project_info[0]
            agent_list = info.get('agents', [])
            if not agent_list:
                return None
            
            agent_data = agent_list[0]
            agent_name = agent_data.get('name', project_dir.name)
            
            # 查找 agent 代码路径
            agent_code_path = None
            prompt_path = None
            for pipeline_stage in agent_data.get('pipeline', []):
                stage_name = pipeline_stage.get('stage')
                artifact_paths = pipeline_stage.get('agent_artifact_path', [])
                
                if stage_name == 'agent_code_developer' and artifact_paths:
                    raw_path = artifact_paths[0]
                    for p in [project_root / raw_path, project_dir / raw_path]:
                        if p.exists():
                            agent_code_path = str(p.relative_to(project_root))
                            break
                    if not agent_code_path:
                        agent_code_path = raw_path
                
                elif stage_name == 'prompt_engineer' and artifact_paths:
                    raw_path = artifact_paths[0]
                    for p in [project_root / raw_path, project_dir / raw_path]:
                        if p.exists():
                            prompt_path = str(p.relative_to(project_root))
                            break
                    if not prompt_path:
                        prompt_path = raw_path
            
            # 计算进度
            progress_info = info.get('progress', [])
            is_completed = False
            if progress_info:
                completed = progress_info[0].get('completed', 0)
                total = progress_info[0].get('total', 1)
                is_completed = completed >= total
            
            return {
                'agent_id': f"local_{project_dir.name}",
                'project_id': project_dir.name,
                'agent_name': agent_name,
                'description': info.get('description', ''),
                'category': 'project',
                'version': info.get('version', '1.0.0'),
                'status': AgentStatus.RUNNING.value if (agent_code_path and is_completed) else AgentStatus.OFFLINE.value,
                'deployment_type': 'local',
                'agentcore_config': None,
                'agent_path': agent_code_path,
                'prompt_path': prompt_path,
                'code_path': agent_code_path,
                'created_at': agent_data.get('created_date'),
                'updated_at': agent_data.get('last_updated'),
                'total_invocations': 0,
                'successful_invocations': 0,
                'failed_invocations': 0,
                'avg_duration_ms': 0,
                'source': 'local_project'
            }
        except Exception as e:
            logger.warning(f"Failed to parse status.yaml for {project_dir.name}: {e}")
            return None
    
    def _get_local_agents(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """获取本地 agents（带缓存）"""
        now = datetime.now(timezone.utc)
        
        # 缓存 60 秒
        if not force_refresh and self._local_agents_cache is not None and self._cache_time is not None:
            if (now - self._cache_time).total_seconds() < 60:
                return self._local_agents_cache
        
        self._local_agents_cache = self._scan_local_agents()
        self._cache_time = now
        return self._local_agents_cache
    
    def register_agent(
        self,
        project_id: str,
        agent_name: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        prompt_path: Optional[str] = None,
        code_path: Optional[str] = None,
        deployment_type: str = "local",
        agentcore_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        注册 Agent 实例
        
        通常在构建工作流的 Deployer 阶段调用
        """
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        agent_data = {
            'agent_id': agent_id,
            'project_id': project_id,
            'agent_name': agent_name,
            'description': description,
            'category': category or 'general',
            'version': '1.0.0',
            'status': AgentStatus.RUNNING.value,
            'deployment_type': deployment_type,
            'agentcore_config': agentcore_config,
            'capabilities': capabilities or [],
            'tools': tools or [],
            'prompt_path': prompt_path,
            'code_path': code_path,
            'deployed_at': now,
            'total_invocations': 0,
            'successful_invocations': 0,
            'failed_invocations': 0,
            'avg_duration_ms': 0.0,
            'last_invoked_at': None
        }
        
        self.db.create_agent(agent_data)
        logger.info(f"Registered agent {agent_id} for project {project_id}")
        
        return agent_data
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 详情"""
        # 先从数据库查找
        agent = self.db.get_agent(agent_id)
        if agent:
            return agent
        
        # 从本地 agents 查找
        local_agents = self._get_local_agents()
        for agent in local_agents:
            if agent['agent_id'] == agent_id:
                return agent
        
        return None
    
    def list_agents(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """列表 Agent - 合并数据库和本地 agents"""
        # 从数据库获取
        db_result = self.db.list_agents(
            status=status,
            category=category,
            limit=limit
        )
        
        db_agents = db_result.get('items', [])
        db_agent_ids = {a.get('agent_id') for a in db_agents}
        
        # 获取本地 agents
        local_agents = self._get_local_agents()
        
        # 合并，避免重复
        all_agents = list(db_agents)
        for local_agent in local_agents:
            if local_agent['agent_id'] not in db_agent_ids:
                # 应用筛选条件
                if status and local_agent.get('status') != status:
                    continue
                if category and local_agent.get('category') != category:
                    continue
                all_agents.append(local_agent)
        
        total = len(all_agents)
        pages = (total + limit - 1) // limit if total > 0 else 0
        
        # 分页
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_agents = all_agents[start_idx:end_idx]
        
        return {
            'items': paginated_agents,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': pages,
                'has_next': end_idx < total,
                'has_prev': page > 1
            }
        }
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新 Agent"""
        return self.db.update_agent(agent_id, updates)
    
    def update_agent_status(self, agent_id: str, status: AgentStatus, error_message: Optional[str] = None) -> Dict[str, Any]:
        """更新 Agent 状态"""
        updates = {'status': status.value}
        if error_message:
            updates['error_message'] = error_message
        return self.db.update_agent(agent_id, updates)
    
    def record_invocation(
        self,
        agent_id: str,
        session_id: Optional[str],
        input_text: str,
        output_text: str,
        status: str,
        duration_ms: int,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录 Agent 调用
        
        同时更新 Agent 的运行时统计
        """
        invocation_id = f"inv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # 创建调用记录
        invocation_data = {
            'invocation_id': invocation_id,
            'agent_id': agent_id,
            'session_id': session_id,
            'input_text': input_text,
            'output_text': output_text,
            'status': status,
            'duration_ms': duration_ms,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'error_message': error_message,
            'created_at': now,
            'metadata': metadata or {}
        }
        
        # 这里需要添加 invocations 表的操作
        # self.db.create_invocation(invocation_data)
        
        # 更新 Agent 统计
        agent = self.db.get_agent(agent_id)
        if agent:
            total = agent.get('total_invocations', 0) + 1
            successful = agent.get('successful_invocations', 0)
            failed = agent.get('failed_invocations', 0)
            
            if status == 'success':
                successful += 1
            else:
                failed += 1
            
            # 计算新的平均耗时
            old_avg = agent.get('avg_duration_ms', 0.0)
            new_avg = ((old_avg * (total - 1)) + duration_ms) / total
            
            self.db.update_agent(agent_id, {
                'total_invocations': total,
                'successful_invocations': successful,
                'failed_invocations': failed,
                'avg_duration_ms': new_avg,
                'last_invoked_at': now
            })
        
        return invocation_data
    
    def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent"""
        return self.db.delete_agent(agent_id)


# 全局单例
agent_service = AgentService()
