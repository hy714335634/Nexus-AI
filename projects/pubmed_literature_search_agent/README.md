# pubmed_literature_search_agent

## 项目描述
基于PubMed Central的学术文献智能检索、筛选和汇总智能体，支持通过AWS S3访问PMC开放数据

## 项目结构
```
pubmed_literature_search_agent/
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

#### pubmed_literature_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/pubmed_literature_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/pubmed_literature_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/pubmed_literature_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](agents/pubmed_literature_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# PubMed文献检索和汇总智能体

## 项目概述

PubMed文献检索和汇总智能体是一个专门负责学术文献的智能检索、筛选和初步汇总工作的AI助手。该智能体基于PubMed Central (PMC)开放获取文章，通过AWS S3访问PMC数据，支持多种筛选标准，提供智能文献排序和相关性评分，并能生成结构化的文献综述报告和引用信息。

## 核心功能

- **PMC数据访问与检索**：通过AWS S3访问PubMed Central开放获取文章
- **关键词与主题检索**：基于用户输入的关键词和主题进行精准文献检索
- **多维度文献筛选**：按时间范围、期刊类型、影响因子等条件筛选文献
- **相关性评分与排序**：使用多维度算法对文献进行相关性评分和排序
- **文献摘要提取**：从文章中提取关键信息和摘要
- **引用信息生成**：生成多种格式(APA、MLA、Chicago等)的引用信息
- **结构化报告生成**：生成包含关键发现的结构化文献综述报告
- **撤稿状态检查**：识别并标记已撤回的文章
- **多语言支持**：处理英文和中文文献

## 技术架构

该智能体基于单一Agent架构设计，集成了多个功能模块：

1. **PMC S3连接模块**：连接AWS S3并访问PMC开放数据
2. **元数据解析模块**：解析PMC文章元数据和内容
3. **文献检索模块**：执行关键词和主题检索
4. **文献筛选模块**：按各种条件筛选文献
5. **相关性排序模块**：计算和排序文献相关性
6. **引用生成模块**：生成标准格式引用
7. **报告生成模块**：生成结构化报告

## 项目结构

```
pubmed_literature_search_agent/
├── agents/
│   └── generated_agents/
│       └── pubmed_literature_search_agent/
│           └── pubmed_literature_agent.py  # 主智能体代码
├── prompts/
│   └── generated_agents_prompts/
│       └── pubmed_literature_search_agent/
│           └── pubmed_literature_agent.yaml  # 提示词模板
├── tools/
│   └── generated_tools/
│       └── pubmed_literature_search_agent/
│           ├── pmc_s3_connector.py  # PMC S3连接工具
│           ├── pmc_metadata_parser.py  # PMC元数据解析工具
│           ├── literature_searcher.py  # 文献检索工具
│           ├── literature_filter.py  # 文献筛选工具
│           ├── relevance_ranker.py  # 相关性排序工具
│           ├── citation_generator.py  # 引用生成工具
│           └── report_generator.py  # 报告生成工具
└── requirements.txt  # 项目依赖
```

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from pubmed_literature_agent import create_pubmed_literature_agent

# 创建智能体实例
agent = create_pubmed_literature_agent()

# 执行文献检索
result = agent("请检索关于COVID-19疫苗有效性的最新研究")
print(result)
```

### 命令行使用

```bash
# 基本文献检索
python pubmed_literature_agent.py -q "COVID-19疫苗有效性" -m search

# 生成文献综述
python pubmed_literature_agent.py -q "COVID-19疫苗有效性" -t "past 2 years" -m review

# 生成引用信息
python pubmed_literature_agent.py -p "PMC7745045,PMC8233962" -m citation

# 提取关键信息
python pubmed_literature_agent.py -p "PMC7745045" -m extract
```

## 参数说明

- `-q, --query`: 检索查询
- `-t, --time`: 时间范围 (默认: "past 2 years")
- `-j, --journal`: 期刊类型过滤
- `-i, --impact`: 最小影响因子
- `-m, --mode`: 操作模式 (search, review, citation, extract)
- `-p, --pmcid`: PMC ID (用于citation和extract模式)

## 注意事项

1. 该智能体仅限于PubMed Central开放获取文章
2. 使用no-sign-request方式访问AWS S3，无需AWS凭证
3. 尊重PMC数据使用政策和版权限制
4. 默认排除已撤回的文章
5. 处理大量文献时可能需要较长时间

## 开发状态

| 阶段 | 状态 |
|------|------|
| 需求分析 | ✅ 已完成 |
| 系统架构设计 | ✅ 已完成 |
| Agent设计 | ✅ 已完成 |
| 提示词工程 | ✅ 已完成 |
| 工具开发 | ✅ 已完成 |
| Agent代码开发 | ✅ 已完成 |
| Agent开发管理 | ✅ 已完成 |

## 依赖库

- boto3: AWS SDK for Python
- strands: AI Agent框架
- nexus-utils: Nexus工具库
- lxml: XML处理库
- beautifulsoup4: HTML/XML解析库
- pandas: 数据分析库
- opentelemetry: 遥测库

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-20 03:45:56 UTC*
