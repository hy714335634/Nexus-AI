"""
多 Agent 迭代开发支持

提供多 Agent 项目的迭代开发逻辑，支持对每个 Agent 进行独立的设计、工具开发、
提示词工程和代码开发。

Requirements:
    - 6.1: 多 Agent 架构记录
    - 6.2: agent_design 阶段迭代处理
    - 6.3: tools_developer 阶段迭代处理
    - 6.4: prompt_engineer 阶段迭代处理
    - 6.5: agent_code_developer 阶段迭代处理
    - 6.7: 多 Agent 进度跟踪
"""

import logging
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable

from .models import (
    WorkflowContext,
    StageOutput,
    StageStatus,
    AgentDefinition,
    MultiAgentArchitecture,
    AgentStageProgress,
)

# 从统一配置模块导入
from api.v2.core.stage_config import ITERATIVE_STAGES as _ITERATIVE_STAGES

logger = logging.getLogger(__name__)


class MultiAgentIterator:
    """
    多 Agent 迭代器
    
    负责管理多 Agent 项目中各 Agent 的迭代开发过程。
    
    Validates:
        - Requirement 6.2: agent_design 阶段迭代处理
        - Requirement 6.3: tools_developer 阶段迭代处理
        - Requirement 6.4: prompt_engineer 阶段迭代处理
        - Requirement 6.5: agent_code_developer 阶段迭代处理
    """
    
    # 需要迭代处理的阶段 - 从统一配置模块获取
    ITERATIVE_STAGES = _ITERATIVE_STAGES
    
    # 阶段到 Agent 进度阶段的映射
    STAGE_TO_PROGRESS_STAGE = {
        "agent_design": "agent_design",
        "tools_developer": "tool_development",
        "prompt_engineer": "prompt_engineering",
        "agent_code_developer": "code_development",
    }
    
    def __init__(self, context: WorkflowContext):
        """
        初始化多 Agent 迭代器
        
        参数:
            context: 工作流上下文
        """
        self.context = context
        self._architecture: Optional[MultiAgentArchitecture] = None
        self._progress_tracker: Dict[str, AgentStageProgress] = {}
    
    @property
    def architecture(self) -> Optional[MultiAgentArchitecture]:
        """获取多 Agent 架构（延迟解析）"""
        if self._architecture is None:
            self._architecture = self._parse_architecture()
        return self._architecture
    
    @property
    def is_multi_agent(self) -> bool:
        """检查是否为多 Agent 项目"""
        arch = self.architecture
        return arch is not None and arch.agent_count > 1
    
    @property
    def agent_count(self) -> int:
        """获取 Agent 数量"""
        arch = self.architecture
        return arch.agent_count if arch else 1
    
    def _parse_architecture(self) -> Optional[MultiAgentArchitecture]:
        """
        从 system_architecture 阶段输出解析多 Agent 架构
        
        返回:
            MultiAgentArchitecture: 解析的架构，如果不是多 Agent 则返回 None
            
        Validates: Requirement 6.1 - 多 Agent 架构记录
        """
        # 获取 system_architecture 阶段输出
        architect_output = self.context.get_stage_output("system_architecture")
        if not architect_output or not architect_output.is_completed:
            return None
        
        content = architect_output.content
        if not content:
            return None
        
        # 尝试解析 JSON 格式的架构
        architecture = self._parse_json_architecture(content)
        if architecture:
            return architecture
        
        # 尝试从 Markdown 格式解析
        architecture = self._parse_markdown_architecture(content)
        return architecture
    
    def _parse_json_architecture(self, content: str) -> Optional[MultiAgentArchitecture]:
        """
        从 JSON 格式解析架构
        
        参数:
            content: 输出内容
            
        返回:
            MultiAgentArchitecture: 解析的架构
        """
        try:
            # 查找 JSON 块
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if not json_match:
                return None
            
            json_content = json_match.group(1)
            data = json.loads(json_content)
            
            # 检查是否包含多 Agent 信息
            agents_data = data.get('agents', [])
            if not agents_data or len(agents_data) <= 1:
                return None
            
            # 解析 Agent 定义
            agents = []
            for agent_data in agents_data:
                agent = AgentDefinition(
                    name=agent_data.get('name', ''),
                    agent_type=agent_data.get('type', 'main'),
                    description=agent_data.get('description', ''),
                    orchestration_pattern=agent_data.get('orchestration_pattern', 'agent_as_tool'),
                    dependencies=agent_data.get('dependencies', []),
                    tools=agent_data.get('tools', []),
                )
                agents.append(agent)
            
            # 创建架构
            architecture = MultiAgentArchitecture(
                agents=agents,
                orchestration_pattern=data.get('orchestration_pattern', 'agent_as_tool'),
                main_agent=data.get('main_agent', agents[0].name if agents else ''),
            )
            
            logger.info(f"Parsed multi-agent architecture: {architecture.agent_count} agents")
            return architecture
            
        except Exception as e:
            logger.debug(f"Failed to parse JSON architecture: {e}")
            return None
    
    def _parse_markdown_architecture(self, content: str) -> Optional[MultiAgentArchitecture]:
        """
        从 Markdown 格式解析架构
        
        参数:
            content: 输出内容
            
        返回:
            MultiAgentArchitecture: 解析的架构
        """
        try:
            agents = []
            
            # 查找 Agent 定义模式
            # 模式1: ## Agent: agent_name
            agent_pattern1 = re.findall(
                r'##\s*Agent[:\s]+([a-zA-Z0-9_]+)\s*\n([\s\S]*?)(?=##|$)', 
                content
            )
            
            # 模式2: - **Agent Name**: description
            agent_pattern2 = re.findall(
                r'-\s*\*\*([a-zA-Z0-9_]+)\*\*[:\s]*(.*?)(?=\n-|\n\n|$)',
                content
            )
            
            # 模式3: | agent_name | type | description |
            agent_pattern3 = re.findall(
                r'\|\s*([a-zA-Z0-9_]+)\s*\|\s*(\w+)\s*\|\s*(.*?)\s*\|',
                content
            )
            
            # 处理模式1
            for name, desc in agent_pattern1:
                agent = AgentDefinition(
                    name=name.strip(),
                    description=desc.strip()[:200],
                )
                agents.append(agent)
            
            # 处理模式2（如果模式1没有找到）
            if not agents:
                for name, desc in agent_pattern2:
                    agent = AgentDefinition(
                        name=name.strip(),
                        description=desc.strip()[:200],
                    )
                    agents.append(agent)
            
            # 处理模式3（如果前两个模式都没有找到）
            if not agents:
                for name, agent_type, desc in agent_pattern3:
                    if name.lower() not in ['name', 'agent', '---']:
                        agent = AgentDefinition(
                            name=name.strip(),
                            agent_type=agent_type.strip().lower(),
                            description=desc.strip()[:200],
                        )
                        agents.append(agent)
            
            if len(agents) <= 1:
                return None
            
            # 确定编排模式
            orchestration_pattern = "agent_as_tool"
            if 'swarm' in content.lower():
                orchestration_pattern = "swarm"
            elif 'graph' in content.lower():
                orchestration_pattern = "graph"
            
            # 确定主 Agent
            main_agent = ""
            for agent in agents:
                if agent.agent_type == "main" or "main" in agent.name.lower():
                    main_agent = agent.name
                    agent.agent_type = "main"
                    break
            
            if not main_agent and agents:
                main_agent = agents[0].name
                agents[0].agent_type = "main"
            
            architecture = MultiAgentArchitecture(
                agents=agents,
                orchestration_pattern=orchestration_pattern,
                main_agent=main_agent,
            )
            
            logger.info(f"Parsed multi-agent architecture from markdown: {architecture.agent_count} agents")
            return architecture
            
        except Exception as e:
            logger.debug(f"Failed to parse markdown architecture: {e}")
            return None
    
    def get_agents_for_stage(self, stage_name: str) -> List[AgentDefinition]:
        """
        获取指定阶段需要处理的 Agent 列表
        
        参数:
            stage_name: 阶段名称
            
        返回:
            List[AgentDefinition]: 需要处理的 Agent 列表
        """
        if not self.is_multi_agent:
            return []
        
        if stage_name not in self.ITERATIVE_STAGES:
            return []
        
        # 返回所有 Agent（按依赖顺序排序）
        return self._sort_agents_by_dependency()
    
    def _sort_agents_by_dependency(self) -> List[AgentDefinition]:
        """
        按依赖关系排序 Agent
        
        返回:
            List[AgentDefinition]: 排序后的 Agent 列表
        """
        if not self.architecture:
            return []
        
        agents = list(self.architecture.agents)
        sorted_agents = []
        processed = set()
        
        # 简单的拓扑排序
        while len(sorted_agents) < len(agents):
            for agent in agents:
                if agent.name in processed:
                    continue
                
                # 检查所有依赖是否已处理
                deps_satisfied = all(
                    dep in processed for dep in agent.dependencies
                )
                
                if deps_satisfied:
                    sorted_agents.append(agent)
                    processed.add(agent.name)
            
            # 防止无限循环（循环依赖）
            if len(sorted_agents) == len(processed):
                # 添加剩余的 Agent
                for agent in agents:
                    if agent.name not in processed:
                        sorted_agents.append(agent)
                        processed.add(agent.name)
                break
        
        return sorted_agents
    
    def format_agent_context(
        self, 
        agent: AgentDefinition, 
        stage_name: str,
        base_context: str,
    ) -> str:
        """
        为特定 Agent 格式化执行上下文
        
        参数:
            agent: Agent 定义
            stage_name: 阶段名称
            base_context: 基础上下文
            
        返回:
            str: 格式化的上下文
        """
        agent_context = f"""
## 当前处理的 Agent

- **Agent 名称**: {agent.name}
- **Agent 类型**: {agent.agent_type}
- **描述**: {agent.description}
- **编排模式**: {agent.orchestration_pattern}
"""
        
        if agent.dependencies:
            agent_context += f"- **依赖**: {', '.join(agent.dependencies)}\n"
        
        if agent.tools:
            agent_context += f"- **工具**: {', '.join(agent.tools)}\n"
        
        # 添加其他 Agent 的信息（用于协调）
        if self.architecture and self.architecture.agent_count > 1:
            other_agents = [a for a in self.architecture.agents if a.name != agent.name]
            if other_agents:
                agent_context += "\n## 其他 Agent\n"
                for other in other_agents:
                    agent_context += f"- **{other.name}** ({other.agent_type}): {other.description[:100]}\n"
        
        return f"{base_context}\n{agent_context}"
    
    def get_progress(self, agent_name: str) -> AgentStageProgress:
        """
        获取指定 Agent 的进度
        
        参数:
            agent_name: Agent 名称
            
        返回:
            AgentStageProgress: Agent 进度
            
        Validates: Requirement 6.7 - 多 Agent 进度跟踪
        """
        if agent_name not in self._progress_tracker:
            self._progress_tracker[agent_name] = AgentStageProgress(
                agent_name=agent_name
            )
        return self._progress_tracker[agent_name]
    
    def update_progress(
        self, 
        agent_name: str, 
        stage_name: str, 
        status: StageStatus
    ) -> None:
        """
        更新 Agent 进度
        
        参数:
            agent_name: Agent 名称
            stage_name: 阶段名称
            status: 状态
            
        Validates: Requirement 6.7 - 多 Agent 进度跟踪
        """
        progress = self.get_progress(agent_name)
        
        # 映射到进度阶段名称
        progress_stage = self.STAGE_TO_PROGRESS_STAGE.get(stage_name, stage_name)
        progress.update_stage_status(progress_stage, status)
        
        logger.info(
            f"Agent {agent_name} progress updated: {progress_stage} -> {status.value} "
            f"({progress.progress_percentage:.1f}%)"
        )
    
    def get_all_progress(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有 Agent 的进度
        
        返回:
            Dict: Agent 名称到进度信息的映射
        """
        result = {}
        
        if self.architecture:
            for agent in self.architecture.agents:
                progress = self.get_progress(agent.name)
                result[agent.name] = progress.to_dict()
        
        return result
    
    def is_stage_complete_for_all_agents(self, stage_name: str) -> bool:
        """
        检查指定阶段是否对所有 Agent 都已完成
        
        参数:
            stage_name: 阶段名称
            
        返回:
            bool: 是否所有 Agent 都已完成该阶段
        """
        if not self.is_multi_agent:
            return True
        
        progress_stage = self.STAGE_TO_PROGRESS_STAGE.get(stage_name, stage_name)
        
        for agent in self.architecture.agents:
            progress = self.get_progress(agent.name)
            status = progress.stage_statuses.get(progress_stage)
            if status != StageStatus.COMPLETED:
                return False
        
        return True
    
    def get_next_agent_for_stage(self, stage_name: str) -> Optional[AgentDefinition]:
        """
        获取指定阶段下一个需要处理的 Agent
        
        参数:
            stage_name: 阶段名称
            
        返回:
            AgentDefinition: 下一个需要处理的 Agent，如果都已完成则返回 None
        """
        if not self.is_multi_agent:
            return None
        
        progress_stage = self.STAGE_TO_PROGRESS_STAGE.get(stage_name, stage_name)
        
        for agent in self._sort_agents_by_dependency():
            progress = self.get_progress(agent.name)
            status = progress.stage_statuses.get(progress_stage)
            if status != StageStatus.COMPLETED:
                return agent
        
        return None


class MultiAgentStageExecutor:
    """
    多 Agent 阶段执行器
    
    负责执行多 Agent 项目中的迭代阶段。
    
    Validates:
        - Requirement 6.2: agent_designer 阶段迭代处理
        - Requirement 6.3: tool_developer 阶段迭代处理
        - Requirement 6.4: prompt_engineer 阶段迭代处理
        - Requirement 6.5: agent_code_developer 阶段迭代处理
    """
    
    def __init__(
        self, 
        context: WorkflowContext,
        iterator: Optional[MultiAgentIterator] = None,
        on_agent_start: Optional[Callable[[str, str], None]] = None,
        on_agent_complete: Optional[Callable[[str, str, StageOutput], None]] = None,
    ):
        """
        初始化多 Agent 阶段执行器
        
        参数:
            context: 工作流上下文
            iterator: 多 Agent 迭代器（可选）
            on_agent_start: Agent 开始处理回调 (agent_name, stage_name)
            on_agent_complete: Agent 完成处理回调 (agent_name, stage_name, output)
        """
        self.context = context
        self.iterator = iterator or MultiAgentIterator(context)
        self.on_agent_start = on_agent_start
        self.on_agent_complete = on_agent_complete
    
    def should_iterate(self, stage_name: str) -> bool:
        """
        检查指定阶段是否需要迭代处理
        
        参数:
            stage_name: 阶段名称
            
        返回:
            bool: 是否需要迭代处理
        """
        return (
            self.iterator.is_multi_agent and 
            stage_name in MultiAgentIterator.ITERATIVE_STAGES
        )
    
    def execute_for_agent(
        self,
        stage_name: str,
        agent: AgentDefinition,
        base_executor,  # StageExecutor
        base_context: str,
        state: Optional[Dict[str, Any]] = None,
    ) -> StageOutput:
        """
        为特定 Agent 执行阶段
        
        参数:
            stage_name: 阶段名称
            agent: Agent 定义
            base_executor: 基础阶段执行器
            base_context: 基础上下文
            state: Agent 状态
            
        返回:
            StageOutput: 阶段输出
        """
        logger.info(f"Executing stage {stage_name} for agent: {agent.name}")
        
        # 触发开始回调
        if self.on_agent_start:
            self.on_agent_start(agent.name, stage_name)
        
        # 更新进度
        self.iterator.update_progress(agent.name, stage_name, StageStatus.RUNNING)
        
        try:
            # 格式化 Agent 特定的上下文
            agent_context = self.iterator.format_agent_context(
                agent, stage_name, base_context
            )
            
            # 准备状态
            agent_state = state or {}
            agent_state['current_agent'] = agent.name
            agent_state['agent_type'] = agent.agent_type
            agent_state['is_multi_agent'] = True
            agent_state['total_agents'] = self.iterator.agent_count
            
            # 执行阶段
            output = base_executor.execute_stage(
                stage_name, 
                input_message=agent_context,
                state=agent_state,
            )
            
            # 更新进度
            self.iterator.update_progress(agent.name, stage_name, StageStatus.COMPLETED)
            
            # 触发完成回调
            if self.on_agent_complete:
                self.on_agent_complete(agent.name, stage_name, output)
            
            return output
            
        except Exception as e:
            # 更新进度为失败
            self.iterator.update_progress(agent.name, stage_name, StageStatus.FAILED)
            raise
    
    def execute_iterative_stage(
        self,
        stage_name: str,
        base_executor,  # StageExecutor
        base_context: str,
        state: Optional[Dict[str, Any]] = None,
    ) -> StageOutput:
        """
        执行迭代阶段（处理所有 Agent）
        
        参数:
            stage_name: 阶段名称
            base_executor: 基础阶段执行器
            base_context: 基础上下文
            state: Agent 状态
            
        返回:
            StageOutput: 合并的阶段输出
        """
        if not self.should_iterate(stage_name):
            # 非迭代阶段，直接执行
            return base_executor.execute_stage(stage_name, base_context, state)
        
        logger.info(f"Starting iterative execution of stage {stage_name}")
        
        agents = self.iterator.get_agents_for_stage(stage_name)
        all_outputs: List[StageOutput] = []
        
        for agent in agents:
            output = self.execute_for_agent(
                stage_name, agent, base_executor, base_context, state
            )
            all_outputs.append(output)
        
        # 合并所有输出
        merged_output = self._merge_outputs(stage_name, all_outputs)
        
        logger.info(
            f"Iterative stage {stage_name} completed for {len(agents)} agents"
        )
        
        return merged_output
    
    def _merge_outputs(
        self, 
        stage_name: str, 
        outputs: List[StageOutput]
    ) -> StageOutput:
        """
        合并多个 Agent 的输出
        
        参数:
            stage_name: 阶段名称
            outputs: 输出列表
            
        返回:
            StageOutput: 合并的输出
        """
        if not outputs:
            return StageOutput(stage_name=stage_name, status=StageStatus.COMPLETED)
        
        if len(outputs) == 1:
            return outputs[0]
        
        # 合并内容
        merged_content_parts = []
        for i, output in enumerate(outputs):
            agent_name = self.iterator.architecture.agents[i].name if self.iterator.architecture else f"Agent_{i}"
            merged_content_parts.append(f"## {agent_name}\n\n{output.content}")
        
        merged_content = "\n\n---\n\n".join(merged_content_parts)
        
        # 合并指标
        from .models import StageMetrics
        merged_metrics = StageMetrics()
        for output in outputs:
            merged_metrics.input_tokens += output.metrics.input_tokens
            merged_metrics.output_tokens += output.metrics.output_tokens
            merged_metrics.execution_time_seconds += output.metrics.execution_time_seconds
            merged_metrics.tool_calls_count += output.metrics.tool_calls_count
        
        # 合并生成的文件
        merged_files = []
        for output in outputs:
            merged_files.extend(output.generated_files)
        
        # 确定最终状态
        final_status = StageStatus.COMPLETED
        error_messages = []
        for output in outputs:
            if output.status == StageStatus.FAILED:
                final_status = StageStatus.FAILED
                if output.error_message:
                    error_messages.append(output.error_message)
        
        return StageOutput(
            stage_name=stage_name,
            content=merged_content,
            metrics=merged_metrics,
            generated_files=merged_files,
            completed_at=datetime.now(timezone.utc),
            status=final_status,
            error_message="; ".join(error_messages) if error_messages else None,
        )


def create_multi_agent_iterator(context: WorkflowContext) -> MultiAgentIterator:
    """
    创建多 Agent 迭代器
    
    参数:
        context: 工作流上下文
        
    返回:
        MultiAgentIterator: 迭代器实例
    """
    return MultiAgentIterator(context)


def is_multi_agent_project(context: WorkflowContext) -> bool:
    """
    检查是否为多 Agent 项目
    
    参数:
        context: 工作流上下文
        
    返回:
        bool: 是否为多 Agent 项目
    """
    iterator = MultiAgentIterator(context)
    return iterator.is_multi_agent


def get_multi_agent_progress(context: WorkflowContext) -> Dict[str, Dict[str, Any]]:
    """
    获取多 Agent 项目的进度
    
    参数:
        context: 工作流上下文
        
    返回:
        Dict: 进度信息
    """
    iterator = MultiAgentIterator(context)
    return iterator.get_all_progress()
