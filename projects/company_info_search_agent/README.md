# company_info_search_agent

## 项目描述
一个能够读取Excel表格中的公司信息，通过多种搜索引擎查询公司详细信息，并将结果输出为Excel表格的智能体。支持多搜索引擎集成、深度检索、缓存机制和分批处理输出。

## 项目结构
```
company_info_search_agent/
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

#### company_info_search_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/company_info_search_agent/agents/company_info_search_agent/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# 公司信息检索与分析系统

## 项目概述

公司信息检索与分析系统是一个能够读取Excel表格中的公司信息，通过多种搜索引擎查询公司详细信息，并将结果输出为Excel表格的智能体系统。系统支持深度检索、多搜索引擎集成、缓存机制和分批处理输出。

## 功能特点

- **Excel文件读取与解析**：支持读取包含公司信息的Excel表格，提取公司名称信息
- **多搜索引擎集成**：集成Google, Bing, Baidu, DuckDuckGo等多种搜索引擎，提高查询可靠性
- **深度网页内容检索**：不仅获取搜索结果摘要，还能访问搜索结果中的链接获取更详细信息
- **公司信息提取与汇总**：从搜索结果中提取公司营业额、公司简介、相关链接等关键信息
- **缓存机制与任务进度跟踪**：支持断点续传，可以中断后继续处理未完成的公司信息
- **分批处理与输出管理**：分批处理大量公司信息，避免token限制和内存问题

## 系统架构

系统采用单Agent架构，由一个核心智能体负责整个工作流程，包括输入处理、信息查询、结果整理和输出生成。主要组件包括：

1. **Excel读取器**：负责读取和解析Excel文件
2. **搜索引擎客户端**：集成多种搜索引擎，支持自动切换
3. **内容提取器**：从网页内容中提取公司信息
4. **缓存管理器**：管理任务进度和结果缓存
5. **Excel生成器**：生成CSV和Excel输出文件

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

```bash
python company_info_search_agent.py --excel <excel_file_path>
```

### 高级选项

```bash
python company_info_search_agent.py \
  --excel <excel_file_path> \
  --task-id <task_id> \
  --search-engines "google bing baidu duckduckgo" \
  --api-key <your_api_key> \
  --batch-size 10 \
  --output <output_file_path>
```

### 参数说明

- `--excel`: Excel文件路径（必需）
- `--task-id`: 任务ID，用于断点续传，如果不提供则自动生成
- `--search-engines`: 搜索引擎列表，例如: google bing baidu duckduckgo
- `--api-key`: 搜索API密钥，如果不提供则尝试从环境变量获取
- `--batch-size`: 批处理大小，默认为5
- `--output`: 输出文件路径，如果不提供则自动生成

### 恢复任务

```bash
python company_info_search_agent.py --task-id <task_id> --output <output_file_path>
```

## 输入输出格式

### 输入格式

输入Excel文件必须包含以下字段：
- `Company-Name-ENG`: 公司英文名称
- `Company-Name-CHN`: 公司中文名称（可选）

### 输出格式

输出Excel文件包含以下字段：
- `Company-Name-ENG`: 公司英文名称
- `Company-Name-CHN`: 公司中文名称
- `Revenue`: 公司营业额
- `Company-Profile`: 公司简介
- `Related-Links`: 相关链接
- `Company-Type`: 公司类型（全球/中国）
- `Additional-Info`: 其他信息
- `Info-Sources`: 信息来源
- `Last-Updated`: 信息最后更新时间

## 项目结构

```
company_info_search_agent/
├── agents/
│   └── generated_agents/
│       └── company_info_search_agent/
│           └── company_info_search_agent.py
├── generated_agents_prompts/
│   └── company_info_search_agent/
│       └── company_info_search_agent.yaml
├── generated_tools/
│   └── company_info_search_agent/
│       ├── excel_reader.py
│       ├── search_engine_client.py
│       ├── company_search.py
│       ├── cache_manager.py
│       └── excel_writer.py
├── requirements.txt
└── README.md
```

## 开发状态

- [x] 需求分析
- [x] 系统架构设计
- [x] Agent设计
- [x] 工具开发
- [x] 提示词工程
- [x] Agent代码开发
- [ ] Agent开发管理

## 注意事项

1. **API密钥安全**：如使用商业搜索引擎，请妥善保管API密钥，不要在代码中硬编码
2. **搜索引擎使用政策**：请遵循各搜索引擎的使用政策和速率限制
3. **大量数据处理**：处理大量公司信息时，建议使用批处理功能，避免token限制和内存问题
4. **网站访问限制**：深度检索可能受到网站反爬虫措施的限制，请合理设置访问间隔

## 限制与约束

- 只能获取公开可访问的信息
- 受搜索引擎API使用限制和速率限制
- 处理大量数据时受token限制
- 深度检索受网站反爬虫措施限制

## 未来改进

- 支持更多搜索引擎和数据源
- 增强信息提取的准确性和全面性
- 添加数据可视化功能
- 实现更高级的缓存和任务管理机制
- 优化网页内容提取算法

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-30 08:43:55 UTC*
