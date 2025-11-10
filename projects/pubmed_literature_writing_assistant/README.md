# pubmed_literature_writing_assistant

## 项目描述
一个科研文献编写智能体，能根据用户提供材料和思路进行文献综述的编写工作，支持处理大量PubMed文献并生成高质量文献综述

## 项目结构
```
pubmed_literature_writing_assistant/
├── agents/          # Agent实现文件
├── config.yaml      # 项目配置文件
├── README.md        # 项目说明文档
└── status.yaml      # 项目状态跟踪文件
```

## Agent开发阶段

### 阶段说明
1. **requirements_analyzer**: 需求分析阶段
2. **system_architect**: 系统架构设计阶段
3. **agent_designer**: Agent设计阶段
4. **prompt_engineer**: 提示词工程阶段
5. **tools_developer**: 工具开发阶段
6. **agent_code_developer**: Agent代码开发阶段
7. **agent_developer_manager**: Agent开发管理阶段

### 各Agent阶段结果

#### pubmed_literature_writing_assistant
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/tools_developer.json)
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/pubmed_literature_writing_assistant/agents/pubmed_literature_writing_assistant/agent_developer_manager.json)

## 附加信息
# PubMed Literature Writing Assistant

## 项目概述

PubMed Literature Writing Assistant是一个专业的科研文献编写智能体，能够根据用户提供的研究ID和需求，自动处理PubMed文献并生成高质量的文献综述。该智能体支持大量文献处理、断点续传、多语言输出和会话缓存功能，为科研工作者提供高效的文献综述编写工具。

## 项目状态

- **版本**: 1.0.0
- **状态**: 完成
- **完成日期**: 2025-10-26

### 开发阶段状态

| 阶段 | 状态 | 描述 |
|------|------|------|
| 需求分析 | ✅ 完成 | 明确了智能体的功能需求、业务价值和工作流程 |
| 系统架构 | ✅ 完成 | 设计了系统架构、数据模型和交互流程 |
| Agent设计 | ✅ 完成 | 定义了智能体的角色、能力和交互模式 |
| 工具开发 | ✅ 完成 | 开发了文献元数据加载、文献综述版本管理和处理状态跟踪工具 |
| 提示词工程 | ✅ 完成 | 设计了专业的提示词模板，确保高质量文献综述生成 |
| Agent代码开发 | ✅ 完成 | 实现了智能体代码，支持文献综述生成、断点续传等功能 |
| Agent开发管理 | ✅ 完成 | 协调和管理整个开发过程，确保各阶段成果的质量和一致性 |

## 功能特点

- **文献元数据处理**: 读取和解析文献元数据，基于元数据生成初始文献综述
- **文献内容分析**: 逐篇处理文献内容，提取关键信息并更新综述
- **断点续传支持**: 维护处理进度，支持在处理大量文献时中断后继续
- **多语言输出**: 支持将文献综述输出为不同语言
- **会话缓存**: 通过会话ID管理缓存数据，避免重复处理
- **进度管理**: 实时跟踪处理进度，提供清晰的状态信息

## 目录结构

```
pubmed_literature_writing_assistant/
├── agents/
│   └── generated_agents/
│       └── pubmed_literature_writing_assistant/
│           └── pubmed_literature_writing_assistant.py  # 智能体主代码
├── prompts/
│   └── generated_agents_prompts/
│       └── pubmed_literature_writing_assistant/
│           └── pubmed_literature_writing_assistant.yaml  # 提示词模板
├── tools/
│   └── generated_tools/
│       └── pubmed_literature_writing_assistant/
│           └── literature_processing_tools.py  # 文献处理工具
└── requirements.txt  # 项目依赖库
```

## 安装与配置

1. 确保.cache/pmc_literature目录存在并有读写权限
2. 安装所有依赖库:
   ```
   pip install -r requirements.txt
   ```
3. 配置Strands环境变量

## 使用方法

### 生成文献综述

```bash
python pubmed_literature_writing_assistant.py -r research_123 -l english
```

### 继续处理之前中断的文献综述

```bash
python pubmed_literature_writing_assistant.py -r research_123 -s session_456 -m continue
```

### 查询处理状态

```bash
python pubmed_literature_writing_assistant.py -r research_123 -s session_456 -m status
```

### 翻译文献综述

```bash
python pubmed_literature_writing_assistant.py -r research_123 -m translate -t chinese -v final
```

## 参数说明

- `-r, --research_id`: 研究ID，对应.cache/pmc_literature下的目录名（必需）
- `-q, --requirement`: 用户额外研究需求（可选）
- `-l, --language`: 输出语言，默认为english（可选）
- `-s, --session_id`: 会话ID，用于缓存会话数据（可选）
- `-m, --mode`: 操作模式，可选值：generate, continue, status, translate（可选，默认为generate）
- `-v, --version`: 翻译模式下的综述版本（可选，默认为final）
- `-t, --target_language`: 翻译模式下的目标语言（翻译模式下必需）

## 工作流程

1. **初始化阶段**:
   - 读取research_id对应的manifest.json文件，获取所有推荐文献的元数据
   - 基于元数据生成初始版本的文献综述，保存为initial_review-initial.md

2. **迭代处理阶段**:
   - 读取初始版本文献综述
   - 获取当前处理状态，确定已处理和未处理的文献
   - 逐篇处理未读文献，更新文献综述
   - 每处理完一篇文献，保存更新版本的综述，并更新处理状态

3. **完成阶段**:
   - 所有文献处理完成后，生成最终版本的文献综述
   - 根据用户指定的语言输出最终综述

## 文献综述结构

生成的文献综述包含以下部分：

1. **标题**: 简明扼要地反映研究主题
2. **摘要**: 概述文献综述的主要内容和发现
3. **引言**: 介绍研究背景、目的和意义
4. **方法**: 说明文献筛选和分析方法
5. **结果**: 按主题或时间顺序组织文献发现
6. **讨论**: 分析研究趋势、争议点和研究差距
7. **结论**: 总结主要发现和建议
8. **参考文献**: 列出所有引用的文献

## 已知限制

- 目前仅支持PubMed文献
- 不进行文献质量评估
- 不提供文献推荐功能
- 不下载文献原文
- 不自动转换参考文献格式

## 未来增强计划

- 添加文献质量评估功能
- 实现文献推荐功能
- 开发Web界面，提供更友好的用户交互
- 支持更多文献格式和来源
- 添加参考文献格式自动转换功能

## 依赖库

- nexus-utils>=0.1.0
- strands>=0.1.0
- uuid>=1.30
- pathlib>=1.0.1
- typing>=3.7.4
- datetime>=4.3
- logging>=0.5.1.2
- argparse>=1.4.0
- json>=2.0.9

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-26 02:29:05 UTC*
