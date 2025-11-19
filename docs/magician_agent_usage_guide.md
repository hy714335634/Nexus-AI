# Magician Agent - 智能Agent编排师

## 概述

Magician Agent是一个专业的智能Agent编排师，能够根据用户需求搜索可用的Agent，并智能选择最适合的编排方式来满足用户需求。它支持单Agent、Graph和Swarm三种编排类型。

## 核心功能

### 1. 需求分析
- 深度理解用户的自然语言需求
- 提取核心功能、技术约束、业务场景等关键信息
- 评估需求复杂程度（简单/中等/复杂）

### 2. Agent搜索
- 搜索系统中所有可用的Agent（包括generated agents和template agents）
- 支持关键词匹配、标签筛选、描述匹配等多种搜索方式
- 提取Agent的详细信息（名称、描述、能力、工具依赖等）

### 3. 智能编排
- **单Agent编排（agent）**：当单个Agent能够完全满足需求时选择
- **Graph编排（graph）**：当需要多个Agent按顺序或并行处理时选择
- **Swarm编排（swarm）**：当需要多个Agent协作处理复杂任务时选择

## 编排类型选择标准

### 单Agent编排
- 需求功能单一，一个Agent能够完全满足
- 处理流程简单，无需多步骤协作
- 示例：价格查询、文档转换、数据分析等

### Graph编排
- 需要多个Agent按特定顺序处理
- 存在数据流转和依赖关系
- 示例：数据清洗→分析→报告生成的工作流

### Swarm编排
- 需要多个Agent并行协作处理
- 任务复杂度高，需要智能分工
- 示例：多Agent协作的复杂项目开发

## 结构化输出

Magician Agent使用`AgentOrchestrationResult`结构化输出模型，包含以下信息：

- `user_input`：用户原始输入
- `orchestration_type`：编排类型（agent/graph/swarm）
- `requirement_analysis`：需求分析结果
- `available_agents`：搜索到的可用Agent列表
- `orchestration_result`：编排结果（根据类型包含不同结构）
- `creation_params`：创建参数
- `usage_instructions`：使用说明
- `alternative_solutions`：替代方案

## 使用方法

### 1. 创建Magician Agent

```python
from utils.agent_factory import create_agent_from_prompt_template

# 创建agent的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 创建magician agent
magician_agent = create_agent_from_prompt_template(
    agent_name="system_agents_prompts/magician", 
    **agent_params
)
```

### 2. 使用Magician Agent

```python
# 用户需求
user_input = "我需要一个AWS价格查询工具"

# 获取编排结果
result = magician_agent(user_input)

# 根据编排结果创建相应的Agent或工作流
if result.orchestration_type == "agent":
    # 创建单个Agent
    agent = create_agent_from_prompt_template(
        agent_name=result.orchestration_result["selected_agent"]["template_path"],
        **result.creation_params
    )
elif result.orchestration_type == "graph":
    # 创建Graph工作流
    # 使用GraphBuilder创建图编排
    pass
elif result.orchestration_type == "swarm":
    # 创建Swarm协作
    # 使用Swarm创建多Agent协作系统
    pass
```

## 工具依赖

Magician Agent依赖以下工具：

- `strands_tools/current_time`：获取当前时间
- `system_tools/agent_build_workflow/agent_template_provider/get_all_templates`：获取所有可用Agent模板
- `system_tools/agent_build_workflow/agent_template_provider/search_templates_by_tags`：根据标签搜索Agent
- `system_tools/agent_build_workflow/agent_template_provider/search_templates_by_description`：根据描述搜索Agent
- `system_tools/agent_build_workflow/agent_template_provider/get_template_content`：获取特定模板的详细内容
- `system_tools/agent_build_workflow/agent_template_provider/get_available_tags`：获取所有可用标签

## 测试

使用提供的测试脚本验证Magician Agent功能：

```bash
# 标准测试
python test_magician_agent.py

# 自定义测试
python test_magician_agent.py -i "你的需求描述"
```

## 文件结构

- `prompts/system_agents_prompts/magician.yaml`：Magician Agent的提示词模板
- `utils/structured_output_model/agent_orchestration_result.py`：结构化输出模型
- `test_magician_agent.py`：测试脚本

## 注意事项

1. **必须使用工具搜索**：Magician Agent不能基于假设直接回复，必须通过工具获取实际Agent数据
2. **一次性完成**：无需多轮对话，一次性完成搜索、分析和编排
3. **结构化输出**：严格按照AgentOrchestrationResult模型输出结果
4. **提供完整信息**：包含Agent名称、模板路径、创建参数等完整信息
5. **考虑替代方案**：提供备选的编排方案供用户选择

## 示例场景

### 场景1：单Agent需求
**用户输入**：我需要一个AWS价格查询工具
**编排结果**：选择aws_pricing_agent作为单Agent解决方案

### 场景2：Graph工作流需求
**用户输入**：我需要一个完整的数据分析工作流
**编排结果**：创建Graph编排，包含数据读取→清洗→分析→报告生成的流程

### 场景3：Swarm协作需求
**用户输入**：我需要多个Agent协作处理复杂项目
**编排结果**：创建Swarm编排，包含任务分解、并行处理、结果汇总的协作模式
