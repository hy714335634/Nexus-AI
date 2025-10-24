# pubmed_literature_assistant

## 项目描述
生命科学文献助手Agent，能根据用户给定的主题，进行文献检索和汇总工作，为客户编写综述提供重要依据

## 项目结构
```
pubmed_literature_assistant/
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

#### literature_assistant
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/pubmed_literature_assistant/agents/literature_assistant/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/pubmed_literature_assistant/agents/literature_assistant/system_architect.json)
- **agent_designer**: ✅ 已完成
- **prompt_engineer**: ✅ 已完成 - [文档](projects/pubmed_literature_assistant/agents/literature_assistant/prompt_engineer.json)
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/pubmed_literature_assistant/agents/literature_assistant/agent_developer_manager.json)

## 附加信息
# 生命科学文献助手 (PubMed Literature Assistant)

## 项目概述

生命科学文献助手是一个专门为科研工作者设计的智能代理系统，能够根据用户提供的研究主题，自动执行文献检索、下载、分析和汇总工作。该系统旨在为编写综述论文提供全面的文献支持，通过智能化的文献管理和分析功能，帮助研究人员高效获取和整理相关研究成果。

### 版本信息
- 版本：1.0.0
- 更新日期：2025-10-23

## 功能特点

- **主题分析与检索策略制定**：理解和分析用户给定的主题，自动制定合适的检索策略
- **PMC文献检索与筛选**：在PMC中搜索相关文献，根据影响因子、摘要和元数据信息进行排序和筛选
- **文献全文下载与本地缓存**：下载文献全文到本地磁盘进行缓存，便于后续分析
- **缓存清单生成与管理**：生成和维护结构化的缓存清单，记录文献元数据和处理状态
- **文献全文阅读与相关性分析**：阅读文献全文，评估与研究主题的相关性和质量
- **文献引用评估与筛选**：评估文献是否应被引用，确保引用文献数量不少于20篇
- **文献内容摘要与关键信息提取**：提取文献的主要发现、研究方法和关键结论
- **结构化JSON结果输出**：生成符合规范的JSON输出，包含完整的分析结果和统计信息

## 项目结构

```
pubmed_literature_assistant/
├── agents/
│   └── generated_agents/
│       └── pubmed_literature_assistant/
│           └── literature_assistant.py       # Agent主代码
├── generated_agents_prompts/
│   └── pubmed_literature_assistant/
│       └── literature_assistant.yaml         # Agent提示词模板
├── generated_tools/
│   └── pubmed_literature_assistant/
│       ├── literature_analyzer.py            # 文献分析工具
│       ├── literature_cache_manager.py       # 缓存管理工具
│       └── literature_output_formatter.py    # 输出格式化工具
├── requirements.txt                          # 项目依赖
└── README.md                                 # 项目说明
```

## 开发状态

| 阶段 | 状态 | 描述 |
|------|------|------|
| 需求分析 | ✅ 完成 | 明确功能需求、非功能需求、约束条件和成功标准 |
| 系统架构 | ✅ 完成 | 定义数据模型、交互流程、错误处理和性能考虑 |
| Agent设计 | ✅ 完成 | 明确Agent角色、能力、知识领域和交互模式 |
| 工具开发 | ✅ 完成 | 开发文献分析、缓存管理和输出格式化工具 |
| 提示词工程 | ✅ 完成 | 设计专业、细致、系统性的提示词模板 |
| Agent代码开发 | ✅ 完成 | 实现Agent代码，包括主类定义、工具集成等功能 |
| Agent开发管理 | ✅ 完成 | 协调完成所有开发阶段，验证项目配置 |

## 安装与配置

### 环境要求
- Python 3.9+
- 足够的本地磁盘空间用于缓存文献

### 安装步骤
1. 克隆项目代码
2. 安装依赖：`pip install -r requirements.txt`
3. 确保有PMC API访问权限

## 使用方法

### 基本用法

```python
from agents.generated_agents.pubmed_literature_assistant.literature_assistant import LiteratureAssistant

# 初始化Agent
assistant = LiteratureAssistant()

# 处理研究主题
result = assistant.process("癌症免疫治疗的最新进展")

# 输出结果
print(result)
```

### 输出格式

Agent输出两种JSON格式文件：

1. **缓存清单 (cache_manifest.json)**：记录文献元数据和处理状态
2. **最终输出结果 (final_output.json)**：包含分析结果和统计信息

## 工具模块说明

### literature_analyzer
提供文献分析功能，包括：
- 相关性分析
- 引用价值评估
- 内容摘要提取
- 统计信息生成

### literature_cache_manager
管理文献缓存，包括：
- 缓存清单创建
- 文献下载
- 内容获取
- 状态更新

### literature_output_formatter
格式化输出结果，包括：
- 缓存清单格式化
- 最终输出格式化
- JSON输出生成
- 推荐信息添加

## 注意事项

- 系统仅支持PMC数据库的文献检索
- 文献缓存需要足够的本地磁盘空间
- 系统必须遵循PMC的使用条款和API限制
- JSON输出结构必须严格遵循指定格式

## 未来计划

- 添加更多数据库支持，如Scopus、Web of Science等
- 增强文献分析能力，支持图表数据提取和可视化
- 添加多语言支持，处理非英文文献
- 实现用户界面，提供更友好的交互体验
- 添加增量更新功能，支持定期检索新发表的相关文献

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-23 09:12:13 UTC*
