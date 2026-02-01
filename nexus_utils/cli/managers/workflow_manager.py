"""
工作流管理器 - 处理 Agent 更新和工具构建工作流

支持通过 CLI 触发各种工作流类型：
- agent_update: Agent 更新工作流
- tool_build: 工具构建工作流
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .base import ResourceManager

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """
    工作流操作结果
    
    属性:
        success: 是否成功
        project_id: 项目 ID
        task_id: 任务 ID
        workflow_type: 工作流类型
        message: 结果消息
        data: 额外数据
    """
    success: bool
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    workflow_type: Optional[str] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class WorkflowManager(ResourceManager):
    """
    工作流管理器
    
    通过 API 触发和管理各种工作流
    """
    
    def __init__(self, fs, config, api_base_url: str = "http://localhost:8000"):
        """
        初始化工作流管理器
        
        参数:
            fs: 文件系统适配器
            config: 配置加载器
            api_base_url: API 基础 URL
        """
        super().__init__(fs, config)
        self.api_base_url = api_base_url.rstrip('/')
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送 API 请求
        
        参数:
            method: HTTP 方法
            endpoint: API 端点
            data: 请求数据
            params: 查询参数
            
        返回:
            API 响应数据
        """
        url = f"{self.api_base_url}/api/v1{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to API server at {self.api_base_url}. "
                "Please ensure the API service is running."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError("API request timed out")
        except requests.exceptions.HTTPError as e:
            # 尝试解析错误响应
            try:
                error_data = e.response.json()
                error_msg = error_data.get('detail', str(e))
            except:
                error_msg = str(e)
            raise RuntimeError(f"API error: {error_msg}")
    
    def trigger_agent_update(
        self,
        agent_id: str,
        update_requirement: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        priority: int = 3
    ) -> WorkflowResult:
        """
        触发 Agent 更新工作流
        
        参数:
            agent_id: 要更新的 Agent ID
            update_requirement: 更新需求描述
            user_id: 用户 ID
            user_name: 用户名
            priority: 优先级 (1-5)
            
        返回:
            WorkflowResult: 工作流触发结果
        """
        data = {
            'agent_id': agent_id,
            'update_requirement': update_requirement,
            'priority': priority
        }
        
        if user_id:
            data['user_id'] = user_id
        if user_name:
            data['user_name'] = user_name
        
        try:
            response = self._make_request('POST', '/workflows/agent-update', data)
            
            result_data = response.get('data', {})
            return WorkflowResult(
                success=response.get('success', False),
                project_id=result_data.get('project_id'),
                task_id=result_data.get('task_id'),
                workflow_type='agent_update',
                message=response.get('message'),
                data=result_data
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_type='agent_update',
                message=str(e)
            )
    
    def trigger_tool_build(
        self,
        requirement: str,
        tool_name: Optional[str] = None,
        category: Optional[str] = None,
        target_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        priority: int = 3,
        tags: Optional[List[str]] = None
    ) -> WorkflowResult:
        """
        触发工具构建工作流
        
        参数:
            requirement: 工具需求描述
            tool_name: 工具名称（可选）
            category: 工具类别
            target_agent: 目标 Agent
            user_id: 用户 ID
            user_name: 用户名
            priority: 优先级 (1-5)
            tags: 标签列表
            
        返回:
            WorkflowResult: 工作流触发结果
        """
        data = {
            'requirement': requirement,
            'priority': priority
        }
        
        if tool_name:
            data['tool_name'] = tool_name
        if category:
            data['category'] = category
        if target_agent:
            data['target_agent'] = target_agent
        if user_id:
            data['user_id'] = user_id
        if user_name:
            data['user_name'] = user_name
        if tags:
            data['tags'] = tags
        
        try:
            response = self._make_request('POST', '/workflows/tool-build', data)
            
            result_data = response.get('data', {})
            return WorkflowResult(
                success=response.get('success', False),
                project_id=result_data.get('project_id'),
                task_id=result_data.get('task_id'),
                workflow_type='tool_build',
                message=response.get('message'),
                data=result_data
            )
            
        except Exception as e:
            return WorkflowResult(
                success=False,
                workflow_type='tool_build',
                message=str(e)
            )
    
    def get_workflow_status(self, project_id: str) -> Dict[str, Any]:
        """
        获取工作流状态
        
        参数:
            project_id: 项目 ID
            
        返回:
            工作流状态信息
        """
        try:
            response = self._make_request('GET', f'/workflows/{project_id}/status')
            return response.get('data', {})
        except Exception as e:
            return {'error': str(e)}
    
    def list_workflow_types(self) -> List[Dict[str, Any]]:
        """
        获取支持的工作流类型列表
        
        返回:
            工作流类型列表
        """
        try:
            response = self._make_request('GET', '/workflows/types')
            return response.get('data', [])
        except Exception as e:
            logger.error(f"Failed to list workflow types: {e}")
            return []
    
    def get_local_agents(self) -> List[Dict[str, str]]:
        """
        获取本地 Agent 列表（用于选择要更新的 Agent）
        
        返回:
            Agent 信息列表
        """
        agents = []
        
        # 扫描 generated_agents 目录
        agents_dir = "agents/generated_agents"
        if self.fs.exists(agents_dir) and self.fs.is_directory(agents_dir):
            for project_dir in self.fs.list_directory(agents_dir):
                if project_dir.is_dir() and not project_dir.name.startswith('.'):
                    project_name = project_dir.name
                    # 扫描项目下的 Agent 文件
                    for agent_file in self.fs.list_directory(
                        f"{agents_dir}/{project_name}", "*.py"
                    ):
                        if agent_file.name != "__init__.py":
                            agents.append({
                                'name': agent_file.stem,
                                'project': project_name,
                                'path': str(agent_file)
                            })
        
        return agents
