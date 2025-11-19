# Magician Agent 快速参考

## 快速开始

### Python 代码调用

```python
from nexus_utils.magician import Magician

# 创建 Magician 实例
magician = Magician("用户需求描述")

# 构建编排对象
agent = magician.build_magician_agent()

# 获取编排描述
magician.get_magician_description()

# 使用编排对象
result = agent("具体任务输入")
```

### 命令行使用

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

## 编排类型

### 单 Agent 编排（agent）

**适用场景**：
- 功能需求单一且明确
- 单个 Agent 能够完全胜任
- 处理流程简单

**特点**：
- Agent 数量：1个
- 执行效率：高
- 结果确定性：高

### Graph 编排（graph）

**适用场景**：
- 需要多个 Agent 按特定顺序处理
- 存在明确的数据流转和依赖关系
- 需要中间结果和状态管理

**特点**：
- Agent 数量：2-5个
- 处理模式：顺序/并行工作流
- 执行效率：中等

### Swarm 编排（swarm）

**适用场景**：
- 需要多个 Agent 协作处理复杂任务
- 任务具有不确定性和创造性
- 需要多角度分析和集体智慧

**特点**：
- Agent 数量：3-8个
- 处理模式：协作讨论
- 执行效率：较低
- 创新性：高

## 编排类型对比

| 维度 | 单Agent | Graph | Swarm |
|------|---------|-------|-------|
| **复杂度** | 低-中等 | 中等-高 | 高-极高 |
| **Agent数量** | 1个 | 2-5个 | 3-8个 |
| **处理模式** | 直接处理 | 工作流 | 协作讨论 |
| **执行效率** | 高 | 中等 | 较低 |
| **结果确定性** | 高 | 高 | 中等 |

## 关键方法

### Magician 类

- `Magician(user_input)` - 创建 Magician 实例
- `build_magician_agent()` - 构建编排对象
- `get_magician_description()` - 获取编排描述
- `get_magician_agent(template_path)` - 获取 Agent（带缓存）

### 缓存管理

- `Magician.get_cache_info()` - 获取缓存信息
- `Magician.clear_agent_cache()` - 清空缓存

## Agent 搜索工具

- `get_all_templates()` - 获取所有可用 Agent 模板
- `search_templates_by_tags(tags)` - 根据标签搜索
- `search_templates_by_description(keywords)` - 根据描述搜索
- `get_template_content(template_path)` - 获取模板内容
- `get_available_tags()` - 获取所有可用标签

## 使用示例

### 单 Agent 编排

```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个AWS价格查询工具")
agent = magician.build_magician_agent()
result = agent("查询EC2实例价格")
```

### Graph 编排

```python
from nexus_utils.magician import Magician

magician = Magician("我需要一个文档处理流水线：PDF解析→内容提取→格式转换→PPT生成")
graph = magician.build_magician_agent()
result = graph("处理这个PDF文件：/path/to/file.pdf")
```

### Swarm 编排

```python
from nexus_utils.magician import Magician

magician = Magician("我需要多个专家协作分析一个复杂的技术架构设计")
swarm = magician.build_magician_agent()
result = swarm("分析这个微服务架构设计的优缺点")
```

## 需求描述模板

### 好的需求

```
我需要一个<功能描述>工具，要求：
1. [功能点1]
2. [功能点2]

使用场景：
- [场景1]
- [场景2]
```

### 示例

```
我需要一个AWS价格查询工具，要求：
1. 支持EC2、S3、RDS等主要服务
2. 能够获取实时价格
3. 支持多个AWS区域

使用场景：
- 销售报价支持
- 成本估算
```

## 故障排查

### Agent 未找到

→ 检查 Agent 模板路径，使用 `get_all_templates` 查看可用 Agent

### 模板路径错误

→ 确认路径格式正确（以 `prompts/` 开头），验证文件存在

### Graph 构建失败

→ 检查节点数据结构，确认 `node_id` 和 `template_path` 字段

### Swarm 构建失败

→ 检查 Swarm 配置，确认 Agent 列表和 `template_path` 正确

### 缓存问题

→ 清空缓存：`Magician.clear_agent_cache()`

## 相关文件

- **Magician 类**: `nexus_utils/magician.py`
- **命令行接口**: `agents/system_agents/magician.py`
- **编排器提示词**: `prompts/system_agents_prompts/magician_workflow/magician_orchestrator.yaml`
- **结构化模型**: `nexus_utils/structured_output_model/agent_orchestration_result.py`
- **模板提供工具**: `tools/system_tools/agent_build_workflow/agent_template_provider.py`

## 更多信息

详细文档请参考：[magician_agent_design.md](./magician_agent_design.md)

