# Agent Update Workflow 文档

## 文档索引

本目录包含 Agent Update Workflow 的完整文档。

### 📚 文档列表

1. **[设计文档](./agent_update_workflow_design.md)** - 完整的设计说明文档
   - 概述和架构设计
   - 工作流阶段详解
   - 工具系统说明
   - 规则系统说明
   - 版本管理机制
   - 使用指南和示例
   - 最佳实践和故障排查

2. **[快速参考](./quick_reference.md)** - 快速查阅指南
   - 基本命令和用法
   - 工作流阶段速查表
   - 关键工具列表
   - 重要规则速查
   - 常见问题解答

## 快速开始

### 基本使用

```bash
python agents/system_agents/agent_update_workflow/agent_update_workflow.py \
  -i "更新需求描述" \
  -j "project_name"
```

### Python 调用

```python
from agents.system_agents.agent_update_workflow.agent_update_workflow import (
    run_update_workflow
)

result = run_update_workflow("更新需求描述", "project_name")
```

## 工作流概览

Agent Update Workflow 通过 5 个专业 Agent 协作，在保持历史版本完整的前提下，安全、有序地更新 Agent：

```
用户需求 + 项目ID → Orchestrator → Requirements → Tool Update → Prompt Update → Code Update
```

## 核心特性

- ✅ **版本化管理**：自动生成版本ID，创建版本目录，保持历史版本完整
- ✅ **非破坏性更新**：不允许修改和删除源文件，仅在新版本目录创建新文件
- ✅ **多阶段协作**：5 个专业 Agent 按顺序协作完成更新流程
- ✅ **规则驱动**：严格遵循 Nexus-AI 平台规则和目录规范
- ✅ **完整追踪**：记录每个阶段的文档、状态和变更日志

## 目录结构

更新后的内容分布在以下位置：

**版本目录**：
```
projects/<project_name>/<version_id>/
├── stages/                      # 阶段文档
├── summary.yaml                 # 版本总结
└── change_log.yaml             # 变更日志
```

**新版本工具**：
```
tools/generated_tools/<project_name>/<version_id>/...
```

**更新的提示词**：
```
prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
# 包含多个版本条目
```

**新版本代码**：
```
agents/generated_agents/<project_name>/<version_id>/<agent_name>.py
```

## 重要规则

### 目录规则

仅允许在以下目录创建和更新：
- `projects/<project_name>/<version_id>/`
- `prompts/generated_agents_prompts/<project_name>/<agent_name>.yaml`
- `tools/generated_tools/<project_name>/<version_id>/`
- `agents/generated_agents/<project_name>/<version_id>/`

### 生成规则

- ❌ **不允许修改和删除源文件**
- ✅ **仅允许在当前工作版本的目录中创建新文件**
- ✅ **提示词更新时，必须在现有文件中追加新版本**

## 相关资源

- **工作流代码**: `agents/system_agents/agent_update_workflow/`
- **工具管理**: `tools/system_tools/agent_update_workflow/`
- **提示词模板**: `prompts/system_agents_prompts/agent_update_workflow/`
- **规则配置**: `config/nexus_ai_base_rule.yaml`

## 文档版本

- **版本**: 1.0
- **最后更新**: 2025-11-11
- **作者**: Nexus-AI Team

---

**提示**: 首次使用建议先阅读[设计文档](./agent_update_workflow_design.md)，日常使用可参考[快速参考](./quick_reference.md)。

