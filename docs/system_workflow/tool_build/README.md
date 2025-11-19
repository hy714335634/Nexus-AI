# Tool Build Workflow 文档

## 文档索引

本目录包含 Tool Build Workflow 的完整文档。

### 📚 文档列表

1. **[设计文档](./tool_build_workflow_design.md)** - 完整的设计说明文档
   - 概述和架构设计
   - 工作流阶段详解
   - 工具系统说明
   - 规则系统说明
   - 使用指南和示例
   - 最佳实践和故障排查

2. **[快速参考](./quick_reference.md)** - 快速查阅指南
   - 基本命令和用法
   - 工作流阶段速查表
   - 关键工具列表
   - 命名和代码规范
   - 常见问题解答

## 快速开始

### 基本使用

```bash
python agents/system_agents/tool_build_workflow/tool_build_workflow.py \
  -i "你的功能需求描述"
```

### Python 调用

```python
from agents.system_agents.tool_build_workflow.tool_build_workflow import (
    run_tool_build_workflow
)

result = run_tool_build_workflow("你的功能需求描述")
```

## 工作流概览

Tool Build Workflow 通过 6 个专业 Agent 协作，将用户自然语言需求转换为符合 Strands SDK 规范的工具代码：

```
用户需求 → Orchestrator → Requirements → Designer → Developer → Validator → Documenter
```

## 核心特性

- ✅ **自动化工具开发**：从需求到代码全流程自动化
- ✅ **多阶段协作**：6 个专业 Agent 按顺序协作
- ✅ **规则驱动**：严格遵循 Nexus-AI 平台规则
- ✅ **完整生命周期**：覆盖需求、设计、开发、验证、文档
- ✅ **状态跟踪**：实时跟踪各阶段状态和进度

## 目录结构

工具项目生成在：

```
tools/generated_tools/tool_build_<tool_name>/
├── config.yaml              # 项目配置
├── status.yaml              # 项目状态
├── README.md                # 使用文档
├── stages/                  # 阶段文档
│   ├── requirements_analyzer.json
│   ├── tool_designer.json
│   ├── tool_developer.json
│   ├── tool_validator.json
│   └── tool_documenter.json
└── *.py                     # 工具代码文件
```

## 相关资源

- **工作流代码**: `agents/system_agents/tool_build_workflow/`
- **工具管理**: `tools/system_tools/tool_build_workflow/`
- **提示词模板**: `prompts/system_agents_prompts/tool_build_workflow/`
- **规则配置**: `config/nexus_ai_base_rule.yaml`

## 文档版本

- **版本**: 1.0
- **最后更新**: 2025-11-11
- **作者**: Nexus-AI Team

---

**提示**: 首次使用建议先阅读[设计文档](./tool_build_workflow_design.md)，日常使用可参考[快速参考](./quick_reference.md)。

