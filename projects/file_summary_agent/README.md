# file_summary_agent

## 项目描述
一个能够自动对文件内容进行摘要的智能体，支持多种文件格式，提取关键信息并生成简洁摘要。

## 项目结构
```
file_summary_agent/
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

#### file_summarizer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/file_summary_agent/agents/file_summarizer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/file_summary_agent/agents/file_summarizer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/file_summary_agent/agents/file_summarizer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# File Summary Agent

## 项目概述

File Summary Agent 是一个智能文件摘要生成系统，能够自动读取和分析各种格式的文件内容，并生成简洁、准确的摘要。该系统支持多种文件格式，能够提取关键信息、识别主要观点，并生成结构化的摘要内容。

## 功能特点

- **多格式文件支持**：支持PDF、Word文档、纯文本和Markdown等多种文件格式
- **智能摘要生成**：自动分析文档内容，生成高质量摘要
- **摘要长度控制**：支持简短、标准和详细三种摘要长度
- **多种输出格式**：支持JSON、Markdown和纯文本输出格式
- **关键信息提取**：自动识别和提取文档中的关键信息和关键词
- **批量文件处理**：支持同时处理多个文件，提高工作效率
- **错误处理机制**：完善的错误处理和异常管理

## 项目结构

```
file_summary_agent/
├── agents/
│   └── generated_agents/
│       └── file_summary_agent/
│           └── file_summarizer.py      # 智能体主代码
├── generated_agents_prompts/
│   └── file_summary_agent/
│       └── file_summarizer.yaml        # 智能体提示词模板
├── generated_tools/
│   └── file_summary_agent/
│       └── file_summarizer_tool/
│           └── file_summarizer_tool.py # 文件摘要工具
└── requirements.txt                    # 项目依赖
```

## 技术架构

- **基于Strands框架**：使用Strands SDK构建智能体
- **AWS Bedrock集成**：使用Claude 3 Sonnet模型生成高质量摘要
- **模块化设计**：文件解析、内容分析、摘要生成分离
- **工厂模式**：灵活处理不同文件类型
- **流式处理**：支持大文件处理

## 使用方法

### 基本用法

```python
# 导入智能体
from file_summarizer import FileSummarizerAgent
from strands.models import Message, Role

# 创建智能体实例
agent = FileSummarizerAgent()

# 单文件摘要
response = agent.process_message(
    Message(role=Role.USER, content="请为文件 report.pdf 生成摘要")
)
print(response.message.content)
```

### 命令行使用

```bash
# 单文件摘要
python file_summarizer.py -f /path/to/document.pdf

# 批量处理
python file_summarizer.py -b "/path/to/doc1.pdf,/path/to/doc2.docx"

# 指定摘要长度和输出格式
python file_summarizer.py -f document.pdf -l short -o markdown

# 不提取关键词
python file_summarizer.py -f document.pdf -k false
```

## 参数说明

- **file_path**: 文件路径或文件路径列表
- **summary_length**: 摘要长度选项 - 'short', 'standard', 'detailed'
- **output_format**: 输出格式 - 'json', 'markdown', 'plain'
- **extract_keywords**: 是否提取关键词
- **batch_process**: 是否启用批量处理

## 依赖项

- PyPDF2 和 pdfplumber: 用于PDF文件解析
- python-docx: 用于Word文档解析
- markdown: 用于Markdown文件处理
- chardet: 用于文件编码检测
- boto3: 用于AWS Bedrock服务调用
- strands: 智能体框架

## 安装方法

1. 克隆项目仓库
2. 安装依赖：`pip install -r requirements.txt`
3. 配置AWS凭证（用于Bedrock服务）
4. 运行智能体

## 项目状态

- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 提示词工程
- ✅ 工具开发
- ✅ Agent代码开发
- ✅ 开发管理

## 注意事项

- 文件大小限制为10MB
- 需要有效的AWS凭证配置
- 不支持加密或受保护的文档
- 不处理图像、视频或音频内容

## 未来计划

- 添加更多文件格式支持
- 实现自定义摘要模板
- 添加多语言支持
- 开发Web界面
- 添加文档比较功能

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-09 03:58:14 UTC*
