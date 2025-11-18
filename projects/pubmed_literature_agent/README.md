# pubmed_literature_agent

## 项目描述
PubMed文献检索和分析智能体，能够基于用户问题检索相关文献，提取关键内容，生成总结和要点，并按相关度排序输出结果。

## 项目结构
```
pubmed_literature_agent/
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

#### pubmed_search_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/pubmed_search_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/pubmed_search_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/pubmed_search_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](prompts/generated_agents_prompts/pubmed_literature_agent/pubmed_search_agent.yaml)
- **tools_developer**: ✅ 已完成 - [文档](tools/generated_tools/pubmed_search_agent/pubmed_api_tool.py)
- **agent_code_developer**: ✅ 已完成 - [文档](agents/generated_agents/pubmed_literature_agent/pubmed_search_agent.py)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# PubMed Literature Agent

## Project Overview
The PubMed Literature Agent is an intelligent system designed to search, retrieve, analyze, and present relevant medical literature from PubMed based on user queries. This agent streamlines the process of finding and understanding scientific medical publications by providing concise summaries, key points, and relevance-ranked results.

## Key Features
- **Natural Language Query Processing**: Convert user questions into optimized PubMed search terms
- **Comprehensive Literature Retrieval**: Search PubMed's extensive database of medical publications
- **Content Extraction & Analysis**: Extract key information from research papers
- **Summary Generation**: Create concise summaries and key points for each article
- **Relevance Ranking**: Present results ranked by multiple relevance factors
- **Structured Output**: Clear, well-organized presentation of search results

## Components

### 1. PubMed Search Agent
The main agent responsible for processing queries, retrieving literature, and presenting results.

- **Location**: `agents/generated_agents/pubmed_literature_agent/pubmed_search_agent.py`
- **Prompt Template**: `prompts/generated_agents_prompts/pubmed_literature_agent/pubmed_search_agent.yaml`
- **Model**: Claude Opus (optimized for advanced medical comprehension)

### 2. PubMed API Tool
Custom tool for interacting with the PubMed/NCBI E-utilities API.

- **Location**: `tools/generated_tools/pubmed_search_agent/pubmed_api_tool.py`
- **Functions**:
  - `pubmed_search`: Search PubMed for articles matching a query
  - `pubmed_fetch_abstract`: Fetch the abstract for a specific article
  - `pubmed_advanced_search`: Perform structured searches with field-specific terms
  - `pubmed_fetch_citations`: Get articles that cite a specific article
  - `pubmed_fetch_related`: Find articles related to a specific article
  - `pubmed_get_trending_articles`: Find recent articles on a topic
  - `pubmed_rank_articles`: Rank articles by multiple factors
  - `pubmed_get_author_publications`: Find publications by a specific author

## Usage

### Basic Usage
```python
from agents.generated_agents.pubmed_literature_agent.pubmed_search_agent import search_pubmed_literature

# Simple search
result = search_pubmed_literature("Effects of vitamin D supplementation on immune function")

# Search with parameters
result = search_pubmed_literature(
    query="Effects of vitamin D supplementation on immune function",
    max_results=10,
    sort_by="pub_date",
    date_range={"min_date": "2020", "max_date": "2023"},
    article_types=["Clinical Trial", "Review"]
)

print(result)
```

### Command Line Usage
```bash
python -m agents.generated_agents.pubmed_literature_agent.pubmed_search_agent \
  --query "Effects of vitamin D supplementation on immune function" \
  --max_results 10 \
  --sort_by pub_date \
  --min_date 2020 \
  --max_date 2023 \
  --article_types "Clinical Trial,Review"
```

## Output Format
The agent provides a structured output that includes:

1. **Search Summary**:
   - Original query and optimized search terms
   - Number of results found
   - Date range of publications
   - Overview of search strategy

2. **Ranked Results**:
   - For each article:
     - Title, authors, journal, and publication date
     - DOI link when available
     - Relevance score and factors
     - Concise summary (3-5 sentences)
     - 3-5 key points or findings
     - Study design and methods (when applicable)
     - Limitations (when applicable)

3. **Analysis Overview**:
   - Common themes across articles
   - Conflicting findings (if any)
   - Strength of evidence assessment
   - Research gaps identified

4. **Search Refinement Suggestions**:
   - Alternative search terms
   - Related topics
   - Filtering suggestions

## Requirements
- Python 3.13+
- Strands SDK
- AWS Bedrock access (for Claude Opus model)
- Internet access for PubMed API calls

## Configuration
The agent uses the following environment variables:
- `PUBMED_API_KEY`: Optional API key for higher rate limits with PubMed API

## Limitations
- Cannot access full-text content for paywalled articles
- Limited to information available in PubMed abstracts and metadata
- Cannot perform real-time citation analysis beyond what the API provides
- Must comply with PubMed/NCBI E-utilities API usage terms and rate limits

## Project Status
- [x] Requirements Analysis
- [x] System Architecture Design
- [x] Agent Design
- [x] Tool Development
- [x] Prompt Engineering
- [x] Agent Code Development
- [x] Development Management

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-18 06:00:17 UTC*
