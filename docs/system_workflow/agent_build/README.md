# Agent Build Workflow 文档

## 文档索引

本目录包含 Agent Build Workflow 的完整文档。

### 📚 文档列表

1. **[设计文档](./agent_build_workflow_design.md)** - 完整的设计说明文档
   - 概述和架构设计
   - 工作流阶段详解（包含意图识别）
   - 工具系统说明
   - 规则系统说明
   - 目录结构
   - 使用指南和示例
   - 最佳实践和故障排查

2. **[快速参考](./quick_reference.md)** - 快速查阅指南
   - 基本命令和用法
   - 工作流阶段速查表
   - 关键工具列表
   - 意图类型说明
   - 常见问题解答

## 快速开始

### 基本使用

```bash
python agents/system_agents/agent_build_workflow/agent_build_workflow.py \
  -i "你的功能需求描述"
```

### Python 调用

```python
from agents.system_agents.agent_build_workflow.agent_build_workflow import (
    run_workflow
)

result = run_workflow("你的功能需求描述")
```

## 工作流概览

Agent Build Workflow 通过意图识别和 7 个专业 Agent 协作，将用户自然语言需求转换为符合 Strands SDK 规范的 Agent 代码：

```
用户需求 → 意图识别 → Orchestrator → Requirements → System Architect → 
Agent Designer → Developer Manager (Tool → Prompt → Code) → Deployer
```

## 核心特性

- ✅ **自动化 Agent 构建**：从需求到代码全流程自动化
- ✅ **意图识别机制**：自动识别用户意图，区分新项目/已存在项目
- ✅ **多阶段协作**：7 个专业 Agent 按顺序协作完成 Agent 构建
- ✅ **单/多 Agent 支持**：自动识别需求复杂度，选择合适架构
- ✅ **模板驱动**：基于现有模板快速构建，确保代码质量
- ✅ **完整生命周期**：覆盖需求、设计、开发、验证、部署全流程
- ✅ **工作流报告**：自动生成详细的工作流执行报告

## 目录结构

项目生成在以下位置：

**项目目录**：
```
projects/<project_name>/
├── config.yaml                      # 项目配置
├── status.yaml                      # 项目状态
├── README.md                        # 项目说明
├── requirements.txt                 # Python 依赖
└── agents/<agent_name>/             # 阶段文档
```

**生成的代码**：
```
agents/generated_agents/<project_name>/<agent_name>.py
prompts/generated_agents_prompts/<project_name>/<agent_name>_prompt.yaml
tools/generated_tools/<project_name>/<module>/<tool_name>.py
```

## 工作流阶段

1. **Intent Analyzer** - 意图识别（工作流开始前）
2. **Orchestrator** - 项目初始化
3. **Requirements Analyzer** - 需求分析
4. **System Architect** - 系统架构设计
5. **Agent Designer** - Agent 详细设计
6. **Developer Manager** - 开发协调管理
   - Tool Developer - 工具开发
   - Prompt Engineer - 提示词工程
   - Code Developer - Agent 代码开发
7. **Agent Deployer** - Agent 部署

## 相关资源

- **工作流代码**: `agents/system_agents/agent_build_workflow/`
- **工具管理**: `tools/system_tools/agent_build_workflow/`
- **提示词模板**: `prompts/system_agents_prompts/agent_build_workflow/`
- **规则配置**: `config/nexus_ai_base_rule.yaml`
- **报告生成**: `nexus_utils/workflow_report_generator.py`

## 文档版本

- **版本**: 1.0
- **最后更新**: 2025-11-11
- **作者**: Nexus-AI Team

---

**提示**: 首次使用建议先阅读[设计文档](./agent_build_workflow_design.md)，日常使用可参考[快速参考](./quick_reference.md)。

