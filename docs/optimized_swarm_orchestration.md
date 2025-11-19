# 优化的Swarm编排和Agent创建系统

本文档介绍经过优化的Swarm编排和Agent创建过程，提供了更强大的功能和更好的性能。

## 🚀 主要优化点

### 1. **增强的数据结构解析**
- 支持多种数据源格式
- 自动处理Pydantic模型转换
- 兼容alternative_solutions中的swarm方案

### 2. **智能Agent角色分配**
- 按优先级自动排序Agent
- 智能选择入口点Agent
- 支持多种角色类型（coordinator、leader、manager、worker）

### 3. **动态Swarm配置**
- 根据Agent数量自动调整参数
- 支持自定义配置覆盖
- 优化的默认参数设置

### 4. **Agent缓存机制**
- 避免重复创建相同Agent
- 提高系统性能
- 支持缓存管理和清理

### 5. **详细的日志和错误处理**
- 树状结构的Agent信息显示
- 完整的错误追踪
- 优雅的失败处理

## 📋 数据结构支持

### Swarm编排数据结构

```json
{
  "orchestration_type": "swarm",
  "orchestration_result": {
    "swarm_structure": {
      "agents": [
        {
          "agent_id": "coordinator",
          "agent_info": {
            "agent_name": "项目协调员",
            "template_path": "prompts/template_prompts/project_coordinator_agent",
            "description": "负责协调整个项目的Agent"
          },
          "role": "coordinator",
          "priority": 1,
          "capabilities": ["项目管理", "任务分配", "进度跟踪"],
          "communication_pattern": "hierarchical"
        },
        {
          "agent_id": "developer",
          "agent_info": {
            "agent_name": "开发工程师",
            "template_path": "prompts/template_prompts/developer_agent",
            "description": "负责代码开发的Agent"
          },
          "role": "worker",
          "priority": 2,
          "capabilities": ["代码开发", "调试", "测试"],
          "communication_pattern": "peer_to_peer"
        }
      ],
      "config": {
        "max_handoffs": 15,
        "max_iterations": 25,
        "execution_timeout": 1200.0,
        "node_timeout": 400.0
      }
    }
  }
}
```

### 支持的配置参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `max_handoffs` | `agent_count * 3` | 最大传递次数 |
| `max_iterations` | `agent_count * 5` | 最大迭代次数 |
| `execution_timeout` | `900.0` | 总执行超时时间（秒） |
| `node_timeout` | `300.0` | 单节点超时时间（秒） |
| `repetitive_handoff_detection_window` | `min(agent_count, 8)` | 重复传递检测窗口 |
| `repetitive_handoff_min_unique_agents` | `min(max(agent_count // 2, 2), 5)` | 最少唯一Agent数 |

## 🎯 入口点Agent选择策略

### 策略1：Coordinator角色优先
```python
# 如果有coordinator、leader、manager角色，选择优先级最高的
if coordinator_candidates:
    sorted_candidates = sorted(coordinator_candidates, key=lambda x: x["priority"])
    return sorted_candidates[0]["agent"]
```

### 策略2：最高优先级Agent
```python
# 选择所有Agent中优先级最高的
highest_priority_agent = min(agent_roles.values(), key=lambda x: x["priority"])
return highest_priority_agent["agent"]
```

### 策略3：默认选择
```python
# 默认选择第一个Agent
return agent_instances[0]
```

## 💾 Agent缓存机制

### 缓存键生成
```python
cache_key = f"{template_path}_{nocallback}_{hash(str(custom_params)) if custom_params else 'default'}"
```

### 缓存管理
```python
# 清空缓存
Magician.clear_agent_cache()

# 获取缓存信息
cache_info = Magician.get_cache_info()
print(f"缓存Agent数量: {cache_info['cached_agents']}")
```

## 🔧 使用示例

### 基本Swarm编排
```python
from utils.magician import Magician

# 创建Magician实例
magician = Magician("我需要一个多Agent协作的软件开发团队")

# 构建Swarm
swarm = magician.build_magician_swarm(magician.orchestration_result)

# 执行Swarm
result = swarm("开发一个Web应用程序")
```

### 自定义Agent参数
```python
# 创建带自定义参数的Agent
custom_params = {
    "env": "development",
    "temperature": 0.7,
    "max_tokens": 4000
}

agent = magician.get_magician_agent(
    template_path="prompts/template_prompts/developer_agent",
    custom_params=custom_params
)
```

### 缓存管理
```python
# 查看缓存状态
cache_info = Magician.get_cache_info()
print(f"当前缓存了 {cache_info['cached_agents']} 个Agent")

# 清空缓存
Magician.clear_agent_cache()
```

## 📊 性能优化

### 1. **Agent缓存**
- 避免重复创建相同Agent
- 减少初始化时间
- 降低内存使用

### 2. **智能参数调整**
- 根据Agent数量自动调整Swarm参数
- 避免过度配置或配置不足
- 提高执行效率

### 3. **错误恢复**
- 单个Agent创建失败不影响整体
- 继续处理其他Agent
- 提供详细的错误信息

## 🎨 日志输出示例

```
🐝 正在构建Swarm编排，包含 3 个Agent
📋 添加Swarm Agent: coordinator
   ├─ 角色: coordinator
   ├─ 优先级: 1
   ├─ 模板: prompts/template_prompts/project_coordinator_agent
   ├─ 能力: 项目管理, 任务分配, 进度跟踪
   └─ 通信模式: hierarchical
📦 使用缓存的Agent: prompts/template_prompts/project_coordinator_agent

📋 添加Swarm Agent: developer
   ├─ 角色: worker
   ├─ 优先级: 2
   ├─ 模板: prompts/template_prompts/developer_agent
   ├─ 能力: 代码开发, 调试, 测试
   └─ 通信模式: peer_to_peer
🏗️ 创建新Agent: prompts/template_prompts/developer_agent
💾 Agent已缓存: prompts/template_prompts/developer_agent

🎯 选择coordinator角色作为入口点: coordinator
✅ Swarm构建完成
🎯 入口点Agent: Project Coordinator Agent
📊 Swarm配置: {'max_handoffs': 9, 'max_iterations': 15, 'execution_timeout': 900.0, 'node_timeout': 300.0, 'repetitive_handoff_detection_window': 3, 'repetitive_handoff_min_unique_agents': 2}
```

## 🚨 错误处理

### 常见错误类型
1. **Agent创建失败**：单个Agent创建失败时跳过，继续处理其他Agent
2. **模板路径错误**：提供详细的错误信息和建议
3. **配置参数错误**：自动使用默认配置并警告
4. **数据结构不匹配**：尝试多种解析方式

### 错误恢复策略
- 继续处理其他Agent
- 提供降级方案
- 记录详细错误日志
- 返回部分可用的Swarm

## 🔮 未来扩展

### 计划中的功能
1. **动态Agent添加/移除**
2. **实时性能监控**
3. **自动负载均衡**
4. **智能故障转移**
5. **分布式Swarm支持**

### 配置选项扩展
- 支持更多Swarm参数
- 自定义通信模式
- 动态角色分配
- 性能优化建议

通过这些优化，Swarm编排系统现在更加健壮、高效和易于使用，能够处理更复杂的多Agent协作场景。
