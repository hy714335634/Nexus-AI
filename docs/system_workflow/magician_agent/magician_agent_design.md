# Magician Agent 设计文档

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [编排类型](#编排类型)
- [工作流程](#工作流程)
- [工具系统](#工具系统)
- [使用指南](#使用指南)
- [示例](#示例)
- [最佳实践](#最佳实践)
- [故障排查](#故障排查)

---

## 概述

### 什么是 Magician Agent

Magician Agent 是 Nexus-AI 平台中的智能 Agent 编排系统。它能够根据用户自然语言需求，自动搜索可用的 Agent，智能选择最适合的编排方式（单 Agent、Graph 或 Swarm），并动态构建对应的 Agent 系统。

### 核心特性

- **智能编排**：根据需求复杂度自动选择编排类型
- **Agent 搜索**：自动搜索系统中所有可用的 Agent（包括 generated 和 template）
- **动态构建**：支持三种编排类型的动态构建
- **Agent 缓存**：智能缓存 Agent 实例，提高性能
- **交互式模式**：支持交互式对话和命令行使用

### 适用场景

- 需要快速找到合适的 Agent 完成任务
- 需要多个 Agent 协作处理复杂任务
- 不确定应该使用哪个 Agent
- 需要动态构建 Agent 工作流
- 需要测试和调试 Agent

---

## 架构设计

### 整体架构

```
用户输入（自然语言需求）
    ↓
Magician Orchestrator Agent
    ↓
┌─────────────────────────────────────┐
│  需求分析 + Agent 搜索 + 编排决策      │
└─────────────────────────────────────┘
    ↓
结构化输出（AgentOrchestrationResult）
    ↓
┌─────────────────────────────────────┐
│  动态构建编排对象                     │
│  - build_single_magician_agent()    │
│  - build_magician_graph()           │
│  - build_magician_swarm()           │
└─────────────────────────────────────┘
    ↓
Agent/Graph/Swarm 对象
```

### 技术栈

- **编排框架**：Strands Multi-Agent (Graph, Swarm)
- **Agent 创建**：nexus_utils.agent_factory
- **结构化输出**：Pydantic BaseModel
- **模板管理**：prompt_template_provider
- **缓存机制**：类级别 Agent 缓存

### 组件说明

#### 1. Magician 类 (`nexus_utils/magician.py`)

**核心类**，提供 Magician 的完整功能：

**关键方法**：
- `__init__(user_input)`: 初始化 Magician，执行需求分析
- `build_magician_agent()`: 构建编排对象（Agent/Graph/Swarm）
- `get_magician_agent(template_path)`: 获取 Agent 实例（带缓存）
- `get_magician_description()`: 获取编排描述信息
- `build_single_magician_agent()`: 构建单 Agent
- `build_magician_graph()`: 构建 Graph 编排
- `build_magician_swarm()`: 构建 Swarm 编排

**缓存机制**：
- 类级别缓存 `_agent_cache`
- 缓存键：`template_path + nocallback + custom_params`
- 支持缓存清空和信息查询

#### 2. Magician Orchestrator Agent

**Agent**: `magician_orchestrator.yaml`

**职责**：
1. **需求分析**：深度理解用户需求，提取核心功能
2. **Agent 搜索**：搜索系统中所有可用的 Agent
3. **编排决策**：智能选择编排类型
4. **结构化输出**：生成 `AgentOrchestrationResult`

**工具依赖**：
- `get_all_templates`: 获取所有可用 Agent 模板
- `search_templates_by_tags`: 根据标签搜索
- `search_templates_by_description`: 根据描述搜索
- `get_template_content`: 获取模板详细内容
- `get_available_tags`: 获取所有可用标签

#### 3. 结构化输出模型

**模型**: `AgentOrchestrationResult`

**字段**：
- `user_input`: 用户原始输入
- `orchestration_type`: 编排类型（"agent" | "graph" | "swarm"）
- `requirement_analysis`: 需求分析结果
- `available_agents`: 搜索到的可用 Agent 列表
- `orchestration_result`: 编排结果（根据类型不同）
- `creation_params`: 创建参数
- `usage_instructions`: 使用说明
- `alternative_solutions`: 替代方案

---

## 编排类型

### 1. 单 Agent 编排（agent）

**适用场景**：
- 功能需求单一且明确
- 处理流程简单，无需多步骤协作
- 单个专业 Agent 能够完全胜任
- 对执行效率要求高
- 结果可预测且标准化

**典型示例**：
- 文档格式转换（PDF→PPT、HTML→PDF）
- 数据查询和分析（AWS价格查询、数据库查询）
- 内容生成（文本摘要、翻译、改写）
- API调用（天气查询、股票信息）
- 文件处理（压缩、解压、格式转换）

**特点**：
- Agent 数量：1个
- 处理模式：直接处理
- 执行效率：高
- 结果确定性：高

### 2. Graph 编排（graph）

**适用场景**：
- 需要多个 Agent 按特定顺序处理
- 存在明确的数据流转和依赖关系
- 需要中间结果和状态管理
- 流程可标准化和自动化
- 需要错误隔离和断点续传

**典型示例**：
- 文档处理流水线：PDF解析→内容提取→格式转换→PPT生成
- 数据分析流水线：数据清洗→特征工程→模型训练→结果输出
- 内容创作流水线：素材收集→内容生成→格式优化→发布
- 审核流程：内容检查→合规判断→自动通过/人工审核
- 多媒体处理：图片处理+音频处理+文本处理→合成视频

**特点**：
- Agent 数量：2-5个
- 处理模式：顺序/并行工作流
- 数据流转：复杂但有规律
- 执行效率：中等
- 结果确定性：高

**Graph 结构**：
```json
{
  "graph_config": {
    "nodes": [
      {
        "id": "node1",
        "agent": {
          "agent_name": "agent1",
          "template_path": "prompts/...",
          "description": "..."
        }
      }
    ],
    "edges": [
      {
        "from": "node1",
        "to": "node2",
        "condition": ""
      }
    ]
  }
}
```

### 3. Swarm 编排（swarm）

**适用场景**：
- 需要多个 Agent 协作处理复杂任务
- 任务具有不确定性和创造性
- 需要多角度分析和集体智慧
- 问题复杂度高，需要专家级知识
- 结果质量比执行效率更重要

**典型示例**：
- 复杂问题解决：科研分析、技术架构设计、投资决策
- 创意协作：产品设计、广告创意、内容策划
- 多角度分析：风险评估、市场分析、用户研究
- 迭代优化：代码审查、方案优化、策略制定
- 知识整合：多领域专家协作解决跨学科问题

**特点**：
- Agent 数量：3-8个
- 处理模式：协作讨论
- 数据流转：动态和交互式
- 执行效率：较低
- 结果确定性：中等
- 创新性：高

**Swarm 结构**：
```json
{
  "swarm_structure": {
    "agents": [
      {
        "agent_id": "coordinator",
        "agent_info": {...},
        "role": "coordinator",
        "priority": 1,
        "capabilities": [...],
        "communication_pattern": "hierarchical"
      }
    ],
    "communication_pattern": "hierarchical",
    "config": {
      "max_handoffs": 20,
      "max_iterations": 30
    }
  }
}
```

### 编排类型对比

| 维度 | 单Agent | Graph | Swarm |
|------|---------|-------|-------|
| **复杂度** | 低-中等 | 中等-高 | 高-极高 |
| **Agent数量** | 1个 | 2-5个 | 3-8个 |
| **处理模式** | 直接处理 | 顺序/并行工作流 | 协作讨论 |
| **数据流转** | 无或简单 | 复杂但有规律 | 动态和交互式 |
| **执行效率** | 高 | 中等 | 较低 |
| **结果确定性** | 高 | 高 | 中等 |
| **创新性** | 低 | 中等 | 高 |
| **调试难度** | 低 | 中等 | 高 |
| **资源消耗** | 低 | 中等 | 高 |

---

## 工作流程

### 完整流程

```
1. 用户输入
   ↓
2. Magician 初始化
   - 创建 magician_orchestrator Agent
   - 执行需求分析
   ↓
3. 编排决策（magician_orchestrator）
   - 需求分析
   - Agent 搜索
   - 编排类型选择
   - 生成结构化输出
   ↓
4. 动态构建（Magician.build_magician_agent）
   - 解析 orchestration_result
   - 根据类型调用对应构建方法
   ↓
5. 返回编排对象
   - Agent 实例
   - Graph 对象
   - Swarm 对象
```

### 详细步骤

#### 步骤 1: 需求分析

Magician Orchestrator 分析用户输入：
1. **功能需求提取**：明确用户需要什么功能
2. **复杂度评估**：判断需求复杂度（简单/中等/复杂）
3. **约束识别**：识别技术约束、性能要求、业务场景
4. **编排类型预判**：基于复杂度初步判断编排方式

#### 步骤 2: Agent 搜索

使用工具搜索可用 Agent：
1. **全量搜索**：`get_all_templates` 获取所有可用 Agent
2. **关键词匹配**：根据需求关键词搜索相关 Agent
3. **标签筛选**：`search_templates_by_tags` 进行标签匹配
4. **描述匹配**：`search_templates_by_description` 进行描述匹配
5. **Agent 信息提取**：提取每个 Agent 的详细信息

#### 步骤 3: 编排决策

基于以下标准选择编排方式：

**单 Agent 编排**：
- 功能需求单一且明确
- 单个 Agent 能够完全胜任
- 处理流程简单，无需多步骤协作

**Graph 编排**：
- 需要多个 Agent 按特定顺序处理
- 存在明确的数据流转和依赖关系
- 需要中间结果和状态管理

**Swarm 编排**：
- 需要多个 Agent 协作处理复杂任务
- 任务具有不确定性和创造性
- 需要多角度分析和集体智慧

#### 步骤 4: 动态构建

根据编排类型构建对应对象：

**单 Agent**：
```python
agent = magician.get_magician_agent(template_path)
```

**Graph**：
```python
builder = GraphBuilder()
for node in nodes:
    agent = magician.get_magician_agent(node.template_path)
    builder.add_node(agent, node.node_id)
for edge in edges:
    builder.add_edge(edge.source, edge.target)
graph = builder.build()
```

**Swarm**：
```python
agents = []
for swarm_agent in swarm_agents:
    agent = magician.get_magician_agent(swarm_agent.template_path)
    agents.append(agent)
swarm = Swarm(agents, **swarm_params)
```

---

## 工具系统

### Agent 模板提供工具

#### 1. `get_all_templates()`

获取所有可用的 Agent 模板。

**返回**：JSON 字符串，包含所有模板的基本信息

**模板来源**：
- `prompts/template_prompts/`: 模板 Agent
- `prompts/generated_agents_prompts/`: 生成的 Agent

#### 2. `search_templates_by_tags(tags)`

根据标签搜索 Agent。

**参数**：
- `tags` (List[str]): 标签列表

**返回**：JSON 字符串，包含匹配的模板列表

#### 3. `search_templates_by_description(keywords)`

根据描述搜索 Agent。

**参数**：
- `keywords` (str): 关键词

**返回**：JSON 字符串，包含匹配的模板列表

#### 4. `get_template_content(template_path)`

获取指定模板的完整内容。

**参数**：
- `template_path` (str): 模板路径

**返回**：JSON 字符串，包含模板的完整 YAML 内容

#### 5. `get_available_tags()`

获取所有可用的标签。

**返回**：JSON 字符串，包含所有标签列表

---

## 使用指南

### 基本使用

#### 1. Python 代码调用

```python
from nexus_utils.magician import Magician

# 创建 Magician 实例
magician = Magician("我需要一个AWS价格查询工具")

# 构建编排对象
agent = magician.build_magician_agent()

# 获取编排描述
magician.get_magician_description()

# 使用编排对象
result = agent("查询EC2实例价格")
```

#### 2. 命令行使用

```bash
# 交互式模式（默认）
python agents/system_agents/magician.py

# 指定 Agent 路径进行交互
python agents/system_agents/magician.py \
  -a "prompts/generated_agents_prompts/news_retrieval_agent/news_agent_prompt.yaml" \
  --interactive

# 使用 Magician 编排（自动选择 Agent）
python agents/system_agents/magician.py \
  -i "我需要一个AWS价格查询工具"

# 使用 Magician 编排并进入交互模式
python agents/system_agents/magician.py \
  -i "我需要一个AWS价格查询工具" \
  --interactive
```

### 使用场景

#### 场景 1: 快速查找 Agent

```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个新闻检索工具")
agent = magician.build_magician_agent()
result = agent("给我看看人工智能的最新新闻")
```

#### 场景 2: 构建 Graph 工作流

```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个文档处理流水线：PDF解析→内容提取→格式转换→PPT生成")
graph = magician.build_magician_agent()
result = graph("处理这个PDF文件：/path/to/file.pdf")
```

#### 场景 3: 构建 Swarm 协作系统

```python
from nexus_utils.magician import Magician

magician = Magician("我需要多个专家协作分析一个复杂的技术问题")
swarm = magician.build_magician_agent()
result = swarm("分析这个技术架构设计的优缺点")
```

### 缓存管理

```python
from nexus_utils.magician import Magician

# 获取缓存信息
cache_info = Magician.get_cache_info()
print(f"缓存的Agent数量: {cache_info['cached_agents']}")

# 清空缓存
Magician.clear_agent_cache()
```

### 交互式模式

```bash
python agents/system_agents/magician.py --interactive
```

交互式模式支持：
- 持续对话
- 输入 `quit` 或 `exit` 退出
- 自动使用缓存的 Agent

---

## 示例

### 示例 1: 单 Agent 编排

**用户需求**：
```
我需要一个AWS价格查询工具
```

**Magician 处理**：
1. 分析需求：AWS价格查询，单一功能
2. 搜索 Agent：找到 `aws_pricing_agent`
3. 选择编排：单 Agent 编排
4. 构建 Agent：创建 `aws_pricing_agent` 实例

**代码**：
```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个AWS价格查询工具")
agent = magician.build_magician_agent()
magician.get_magician_description()

# 使用 Agent
result = agent("查询EC2 t3.medium实例在us-east-1的价格")
```

### 示例 2: Graph 编排

**用户需求**：
```
我需要一个文档处理流水线：PDF解析→内容提取→格式转换→PPT生成
```

**Magician 处理**：
1. 分析需求：多步骤处理，有明确顺序
2. 搜索 Agent：找到 PDF 解析、内容提取、格式转换、PPT 生成等 Agent
3. 选择编排：Graph 编排
4. 构建 Graph：创建包含 4 个节点的 Graph

**代码**：
```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个文档处理流水线：PDF解析→内容提取→格式转换→PPT生成")
graph = magician.build_magician_agent()
magician.get_magician_description()

# 使用 Graph
result = graph("处理这个PDF文件：/path/to/document.pdf")
```

### 示例 3: Swarm 编排

**用户需求**：
```
我需要多个专家协作分析一个复杂的技术架构设计
```

**Magician 处理**：
1. 分析需求：复杂问题，需要多角度分析
2. 搜索 Agent：找到架构师、安全专家、性能专家等 Agent
3. 选择编排：Swarm 编排
4. 构建 Swarm：创建包含多个专家的 Swarm

**代码**：
```python
from nexus_utils.magician import Magician

magician = Magician("我需要多个专家协作分析一个复杂的技术架构设计")
swarm = magician.build_magician_agent()
magician.get_magician_description()

# 使用 Swarm
result = swarm("分析这个微服务架构设计的优缺点")
```

---

## 最佳实践

### 1. 需求描述

- ✅ **清晰具体**：明确说明需要什么功能
- ✅ **包含场景**：说明使用场景和约束
- ✅ **避免模糊**：不要使用过于抽象的描述

### 2. 编排类型选择

- ✅ **简单任务**：使用单 Agent 编排
- ✅ **流程化任务**：使用 Graph 编排
- ✅ **复杂协作**：使用 Swarm 编排
- ❌ **避免过度设计**：不要为简单任务使用复杂编排

### 3. Agent 搜索

- ✅ **使用工具**：必须使用工具搜索，不能假设
- ✅ **多维度搜索**：结合标签、描述、关键词搜索
- ✅ **验证匹配度**：检查 Agent 是否真正匹配需求

### 4. 缓存管理

- ✅ **利用缓存**：Agent 实例会自动缓存
- ✅ **适时清空**：长时间运行后可以清空缓存
- ✅ **监控缓存**：定期查看缓存信息

### 5. 错误处理

- ✅ **验证结果**：检查编排对象是否成功创建
- ✅ **查看描述**：使用 `get_magician_description()` 验证编排
- ✅ **处理异常**：捕获并处理构建失败的情况

---

## 故障排查

### 常见问题

#### 1. Agent 未找到

**错误信息**：
```
编排结果中未找到Agent信息
```

**解决方案**：
- 检查 Agent 模板路径是否正确
- 确认 Agent 存在于 `prompts/template_prompts/` 或 `prompts/generated_agents_prompts/`
- 使用 `get_all_templates` 查看可用 Agent

#### 2. 模板路径错误

**错误信息**：
```
Agent信息中未找到template_path
```

**解决方案**：
- 检查 `template_path` 字段是否存在
- 确认路径格式正确（以 `prompts/` 开头）
- 验证路径对应的文件是否存在

#### 3. Graph 构建失败

**错误信息**：
```
节点缺少node_id或id
```

**解决方案**：
- 检查 Graph 配置中的节点数据结构
- 确认每个节点都有 `node_id` 或 `id` 字段
- 验证 `template_path` 字段存在

#### 4. Swarm 构建失败

**错误信息**：
```
没有成功创建任何Agent实例
```

**解决方案**：
- 检查 Swarm 配置中的 Agent 列表
- 确认每个 Agent 的 `template_path` 正确
- 验证 Agent 模板文件存在且格式正确

#### 5. 缓存问题

**现象**：Agent 创建失败，但模板路径正确

**解决方案**：
- 清空缓存：`Magician.clear_agent_cache()`
- 检查缓存信息：`Magician.get_cache_info()`
- 重新创建 Magician 实例

### 调试技巧

#### 1. 查看编排结果

```python
from nexus_utils.magician import Magician

magician = Magician("用户需求")
orchestration_result = magician.magician_agent.structured_output(
    AgentOrchestrationResult,
    "生成编排配置"
)

# 查看编排结果
print(f"编排类型: {orchestration_result.orchestration_type}")
print(f"可用Agent: {len(orchestration_result.available_agents)}")
print(f"编排结果: {orchestration_result.orchestration_result}")
```

#### 2. 查看编排描述

```python
magician = Magician("用户需求")
agent = magician.build_magician_agent()
magician.get_magician_description()  # 输出详细的编排信息
```

#### 3. 单独测试 Agent

```python
# 直接使用模板路径创建 Agent
from nexus_utils.agent_factory import create_agent_from_prompt_template

agent = create_agent_from_prompt_template(
    agent_name="prompts/generated_agents_prompts/news_retrieval_agent/news_agent_prompt",
    env="production",
    version="latest",
    model_id="default"
)

result = agent("测试输入")
```

#### 4. 查看可用 Agent

```python
from tools.system_tools.agent_build_workflow.agent_template_provider import get_all_templates

templates = json.loads(get_all_templates())
print(f"可用Agent数量: {len(templates['templates'])}")
for template in templates['templates']:
    print(f"- {template['name']}: {template['relative_path']}")
```

---

## 总结

Magician Agent 是 Nexus-AI 平台中强大的智能 Agent 编排系统。它能够根据用户需求自动搜索、选择和编排 Agent，支持单 Agent、Graph 和 Swarm 三种编排方式，大大简化了 Agent 的使用和组合。

### 核心优势

1. **智能化**：自动分析需求并选择最佳编排方式
2. **自动化**：自动搜索和匹配可用 Agent
3. **灵活性**：支持三种不同的编排类型
4. **高效性**：Agent 缓存机制提高性能
5. **易用性**：简单的 API 和交互式模式

### 适用场景

- 快速查找和使用 Agent
- 构建复杂的工作流
- 多 Agent 协作系统
- Agent 测试和调试

### 未来改进

- 支持自定义编排规则
- 支持编排性能优化
- 支持编排可视化
- 支持编排版本管理

---

**文档版本**: 1.0  
**最后更新**: 2025-11-11  
**作者**: Nexus-AI Team

