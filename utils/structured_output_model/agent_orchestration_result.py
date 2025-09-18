from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field


class AgentInfo(BaseModel):
    """单个Agent信息"""
    agent_name: str = Field(description="Agent名称")
    template_path: str = Field(description="Agent对应的YAML模板路径，用于create_agent_from_prompt_template,应该以'prompts/'或'generated_agents_prompts/'开头")
    description: str = Field(description="Agent功能描述")
    category: str = Field(description="Agent分类")
    capabilities: List[str] = Field(description="Agent能力列表")
    tools_dependencies: List[str] = Field(description="工具依赖列表")
    tags: List[str] = Field(description="标签列表")


class GraphNode(BaseModel):
    """Graph编排中的节点信息"""
    node_id: str = Field(description="节点ID")
    agent_info: AgentInfo = Field(description="节点对应的Agent信息")
    position: Optional[Dict[str, int]] = Field(default=None, description="节点位置信息")


class GraphEdge(BaseModel):
    """Graph编排中的边信息"""
    source: str = Field(description="源节点ID")
    target: str = Field(description="目标节点ID")
    edge_type: str = Field(default="sequential", description="边类型：sequential, parallel, conditional")
    condition: Optional[str] = Field(default=None, description="条件边时的条件描述")


class SwarmAgent(BaseModel):
    """Swarm编排中的Agent信息"""
    agent_id: str = Field(description="Swarm中Agent的唯一ID")
    agent_info: AgentInfo = Field(description="Agent信息")
    role: str = Field(description="在Swarm中的角色")
    priority: int = Field(default=1, description="优先级，数字越小优先级越高")
    communication_pattern: str = Field(default="broadcast", description="通信模式：broadcast, peer_to_peer, hierarchical")


class AgentOrchestrationResult(BaseModel):
    """
    Agent编排结果 - 支持agent、graph、swarm三种编排类型
    """
    
    # 用户原始输入
    user_input: str = Field(description="用户原始输入内容")
    
    # 编排类型
    orchestration_type: Literal["agent", "graph", "swarm"] = Field(
        description="编排类型：agent(单个Agent), graph(图编排), swarm(群组编排)"
    )
    
    # 需求分析结果
    requirement_analysis: Dict[str, Any] = Field(
        description="需求分析结果，包含功能需求、技术约束、业务场景等"
    )
    
    # 搜索到的可用Agent列表
    available_agents: List[AgentInfo] = Field(
        description="搜索到的所有可用Agent列表"
    )
    
    # 编排结果
    orchestration_result: Dict[str, Any] = Field(
        description="编排结果，根据orchestration_type包含不同的结构"
    )
    
    # 创建参数
    creation_params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "env": "production",
            "version": "latest",
            "model_id": "default"
        },
        description="用于create_agent_from_prompt_template的创建参数"
    )
    
    # 使用说明
    usage_instructions: str = Field(
        description="如何使用编排结果的说明"
    )
    
    # 替代方案
    alternative_solutions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="替代的编排方案"
    )


# 使用示例
"""
使用示例：

# 单个Agent编排
result = AgentOrchestrationResult(
    user_input="我需要一个AWS价格查询工具",
    orchestration_type="agent",
    requirement_analysis={
        "core_function": "AWS价格查询",
        "technical_constraints": ["AWS API集成", "实时价格查询"],
        "business_scenario": "销售报价支持"
    },
    available_agents=[
        AgentInfo(
            agent_name="aws_pricing_agent",
            template_path="generated_agents_prompts/aws_pricing_agent/aws_pricing_agent",
            description="AWS产品报价智能体",
            category="aws_integration",
            capabilities=["价格查询", "配置推荐", "报价生成"],
            tools_dependencies=["aws_pricing_tool"],
            tags=["aws", "pricing", "sales"]
        )
    ],
    orchestration_result={
        "selected_agent": {
            "agent_name": "aws_pricing_agent",
            "template_path": "generated_agents_prompts/aws_pricing_agent/aws_pricing_agent",
            "match_score": 95,
            "reason": "完全匹配AWS价格查询需求"
        }
    },
    usage_instructions="使用create_agent_from_prompt_template创建aws_pricing_agent实例",
    alternative_solutions=[]
)

# Graph编排
result = AgentOrchestrationResult(
    user_input="我需要一个完整的数据分析工作流",
    orchestration_type="graph",
    requirement_analysis={
        "core_function": "数据分析工作流",
        "workflow_steps": ["数据读取", "数据清洗", "统计分析", "结果输出"],
        "technical_constraints": ["多步骤处理", "数据流转"]
    },
    available_agents=[
        AgentInfo(agent_name="data_reader", template_path="...", ...),
        AgentInfo(agent_name="data_cleaner", template_path="...", ...),
        AgentInfo(agent_name="data_analyzer", template_path="...", ...)
    ],
    orchestration_result={
        "graph_structure": {
            "nodes": [
                GraphNode(node_id="reader", agent_info=..., position={"x": 0, "y": 0}),
                GraphNode(node_id="cleaner", agent_info=..., position={"x": 1, "y": 0}),
                GraphNode(node_id="analyzer", agent_info=..., position={"x": 2, "y": 0})
            ],
            "edges": [
                GraphEdge(source="reader", target="cleaner", edge_type="sequential"),
                GraphEdge(source="cleaner", target="analyzer", edge_type="sequential")
            ]
        }
    },
    usage_instructions="使用GraphBuilder创建图编排工作流"
)

# Swarm编排
result = AgentOrchestrationResult(
    user_input="我需要多个Agent协作处理复杂任务",
    orchestration_type="swarm",
    requirement_analysis={
        "core_function": "多Agent协作",
        "collaboration_pattern": "并行处理+结果汇总",
        "complexity": "高"
    },
    available_agents=[
        AgentInfo(agent_name="task_splitter", template_path="...", ...),
        AgentInfo(agent_name="worker_1", template_path="...", ...),
        AgentInfo(agent_name="worker_2", template_path="...", ...),
        AgentInfo(agent_name="result_merger", template_path="...", ...)
    ],
    orchestration_result={
        "swarm_structure": {
            "agents": [
                SwarmAgent(agent_id="splitter", agent_info=..., role="coordinator", priority=1),
                SwarmAgent(agent_id="worker1", agent_info=..., role="worker", priority=2),
                SwarmAgent(agent_id="worker2", agent_info=..., role="worker", priority=2),
                SwarmAgent(agent_id="merger", agent_info=..., role="collector", priority=1)
            ],
            "communication_pattern": "hierarchical"
        }
    },
    usage_instructions="使用Swarm创建多Agent协作系统"
)
"""
