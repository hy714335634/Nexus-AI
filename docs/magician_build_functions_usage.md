# Magician Build函数使用指南

本文档介绍如何使用magician.py中的三个build函数来解析Agent编排结果并创建对应的agent、graph、swarm对象。

## 概述

magician.py提供了三个核心build函数：

1. **build_agent()** - 构建单个Agent对象
2. **build_graph()** - 构建Graph编排对象  
3. **build_swarm()** - 构建Swarm编排对象

这些函数能够解析`AgentOrchestrationResult`数据结构，并根据编排类型创建相应的对象。

## 数据结构

### AgentOrchestrationResult

```python
from utils.structured_output_model.agent_orchestration_result import AgentOrchestrationResult

# 基本结构
orchestration_result = AgentOrchestrationResult(
    user_input="用户输入内容",
    orchestration_type="agent",  # "agent", "graph", "swarm"
    requirement_analysis={...},
    available_agents=[...],
    orchestration_result={...},
    creation_params={...},
    usage_instructions="...",
    alternative_solutions=[...]
)
```

## 使用示例

### 1. 构建单个Agent

```python
from agents.system_agents.magician import build_agent

# 假设你已经有了Agent编排结果
agent = build_agent(orchestration_result)

if agent:
    print("Agent创建成功")
    # 使用agent处理任务
    result = agent("你的输入内容")
else:
    print("Agent创建失败")
```

### 2. 构建Graph编排

```python
from agents.system_agents.magician import build_graph

# 假设你已经有了Graph编排结果
graph = build_graph(orchestration_result)

if graph:
    print("Graph创建成功")
    # 执行图工作流
    result = graph("你的输入内容")
else:
    print("Graph创建失败")
```

### 3. 构建Swarm编排

```python
from agents.system_agents.magician import build_swarm

# 假设你已经有了Swarm编排结果
swarm = build_swarm(orchestration_result)

if swarm:
    print("Swarm创建成功")
    # 执行群组协作
    result = swarm("你的输入内容")
else:
    print("Swarm创建失败")
```

## 完整工作流示例

```python
from agents.system_agents.magician import get_magician_agent, build_agent, build_graph, build_swarm
from utils.structured_output_model.agent_orchestration_result import AgentOrchestrationResult

def dynamic_orchestration(user_input: str):
    """
    动态编排工作流
    """
    # 1. 获取编排Agent
    magician_orchestration_agent = get_magician_agent("system_agents_prompts/magician_orchestrator.yaml")
    
    # 2. 获取编排结果
    orchestration_result = magician_orchestration_agent.structured_output(
        AgentOrchestrationResult,
        f"用户输入：{user_input}"
    )
    
    # 3. 根据编排类型构建相应对象
    orchestration_type = orchestration_result.orchestration_type
    
    if orchestration_type == "agent":
        return build_agent(orchestration_result)
    elif orchestration_type == "graph":
        return build_graph(orchestration_result)
    elif orchestration_type == "swarm":
        return build_swarm(orchestration_result)
    else:
        raise ValueError(f"不支持的编排类型: {orchestration_type}")

# 使用示例
user_input = "我希望能够通过PDF生成PPT"
result = dynamic_orchestration(user_input)

if result:
    # 执行编排好的系统
    output = result(user_input)
    print(f"执行结果: {output}")
```

## 数据结构格式

### Agent编排结果格式

```python
orchestration_result = {
    "orchestration_type": "agent",
    "orchestration_result": {
        "agent_info": {
            "agent_name": "PDF to PPT Converter",
            "template_path": "document_conversion/pdf_to_ppt_converter",
            "description": "专门将PDF文档转换为PowerPoint演示文稿的Agent",
            "capabilities": ["PDF文档解析", "内容结构提取", "PPT幻灯片生成"]
        }
    }
}
```

### Graph编排结果格式

```python
orchestration_result = {
    "orchestration_type": "graph",
    "orchestration_result": {
        "graph_structure": {
            "nodes": [
                {
                    "node_id": "document_summarizer",
                    "agent_info": {
                        "agent_name": "Document Summarizer",
                        "template_path": "content_processing/document_summarizer"
                    }
                },
                {
                    "node_id": "presentation_designer", 
                    "agent_info": {
                        "agent_name": "Presentation Designer",
                        "template_path": "content_creation/presentation_designer"
                    }
                }
            ],
            "edges": [
                {
                    "source": "document_summarizer",
                    "target": "presentation_designer",
                    "edge_type": "sequential"
                }
            ]
        }
    }
}
```

### Swarm编排结果格式

```python
orchestration_result = {
    "orchestration_type": "swarm",
    "orchestration_result": {
        "swarm_structure": {
            "agents": [
                {
                    "agent_id": "splitter",
                    "agent_info": {
                        "agent_name": "Task Splitter",
                        "template_path": "task_processing/task_splitter"
                    },
                    "role": "coordinator",
                    "priority": 1
                },
                {
                    "agent_id": "worker1",
                    "agent_info": {
                        "agent_name": "Worker Agent",
                        "template_path": "task_processing/worker"
                    },
                    "role": "worker",
                    "priority": 2
                }
            ],
            "communication_pattern": "hierarchical"
        }
    }
}
```

## 测试

运行测试函数来验证build函数的功能：

```bash
cd /Users/qangz/Downloads/99.Project/Nexus-AI
python agents/system_agents/magician.py --test-build
```

## 错误处理

所有build函数都包含完整的错误处理机制：

- 验证编排类型是否匹配
- 检查必要的数据字段是否存在
- 捕获创建过程中的异常
- 返回None表示创建失败

建议在使用这些函数时始终检查返回值是否为None。

## 注意事项

1. **模板路径**: 确保`template_path`指向有效的Agent模板
2. **依赖关系**: Graph和Swarm中的Agent需要正确处理依赖关系
3. **资源管理**: 创建的Agent对象需要适当的资源管理
4. **错误恢复**: 建议实现重试机制来处理临时的创建失败

## 扩展

如果需要支持新的编排类型，可以：

1. 在`AgentOrchestrationResult`中添加新的`orchestration_type`
2. 创建对应的build函数
3. 更新主工作流逻辑

这些build函数为动态Agent编排提供了强大的基础架构支持。
