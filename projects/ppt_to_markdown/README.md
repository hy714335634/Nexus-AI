# ppt_to_markdown

## 项目描述
一个能够解析PPT文件、提取每页内容并生成完整Markdown格式总结报告的智能体

## 项目结构
```
ppt_to_markdown/
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

#### requirements_analyzer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/prompt_engineer.json)
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/ppt_to_markdown/agents/requirements_analyzer/agent_developer_manager.json)

## 附加信息
# PPT to Markdown Converter

## 项目概述

PPT to Markdown Converter 是一个专业的智能体系统，能够解析PPT文件、提取每页内容并生成完整的Markdown格式总结报告。该系统允许用户上传PPT文件，自动提取每页内容，并将其转换为结构化的Markdown文档，保持原始PPT的层次结构和格式。

## 项目状态

✅ 需求分析：已完成  
✅ 系统架构设计：已完成  
✅ 智能体设计：已完成  
✅ 工具开发：已完成  
✅ 提示词工程：已完成  
✅ 智能体代码开发：已完成  
✅ 智能体开发管理：已完成  

**当前版本**：1.0.0  
**开发状态**：已完成  
**完成日期**：2025-09-15  

## 功能特性

- **PPT文件处理**：支持上传和验证PPT/PPTX格式文件
- **内容提取**：按页面提取PPT内容，包括标题、段落、列表等
- **结构保持**：保持原始PPT的层次结构和内容组织
- **Markdown转换**：将提取的内容转换为标准Markdown格式
- **格式支持**：支持基本文本格式（标题、列表、段落等）的转换
- **用户交互**：提供清晰的处理状态和错误信息
- **多轮对话**：支持多轮交互和结果调整

## 使用方法

### 基本用法

用户只需提供PPT文件路径，智能体将自动处理并返回Markdown格式的结果。

### 示例命令

```
请将我的presentation.pptx转换为Markdown
解析/path/to/slides.ppt并生成Markdown报告
提取这个PPT文件的内容并转换为Markdown格式
```

### 高级选项

- 用户可以请求调整特定页面的格式
- 用户可以询问特定部分的转换结果
- 用户可以要求优化特定类型的内容（如列表或表格）

## 技术实现

### 架构

- 单Agent架构，基于Strands框架
- 使用Claude 3.7 Sonnet作为底层模型

### 核心技术

- Python-pptx库用于PPT解析
- Markdown生成工具
- Strands SDK
- 文件系统访问工具

### 集成点

- 文件系统接口
- 用户交互接口

## 项目结构

```
ppt_to_markdown/
├── agents/
│   └── requirements_analyzer/
│       ├── requirements_analyzer.json  # 需求分析文档
│       ├── system_architect.json       # 系统架构设计
│       ├── agent_designer.json         # 智能体设计
│       ├── tools_developer.json        # 工具开发
│       ├── prompt_engineer.json        # 提示词工程
│       ├── agent_code_developer.json   # 智能体代码
│       └── agent_developer_manager.json # 开发管理总结
├── tools/
│   └── ppt_to_markdown_converter.py    # PPT转换工具
├── prompts/
│   └── ppt_to_markdown_converter.prompt # 提示词模板
├── src/
│   └── ppt_to_markdown_agent.py        # 智能体实现
├── config.yaml                         # 项目配置
└── README.md                           # 项目文档
```

## 局限性

- 不支持复杂图表和图片的详细转换
- 不处理PPT动画效果
- 不保留高级样式和主题
- 不进行内容翻译或修改
- 不支持实时协作编辑

## 未来增强

- 增强图片和图表的处理能力
- 支持更多PPT格式和特殊元素
- 添加批量处理功能
- 提供更多自定义选项
- 改进处理速度和效率

## 技术依赖

- Python 3.13+
- python-pptx
- Strands Framework
- AWS Bedrock (Claude 3.7 Sonnet)

## 使用注意事项

1. 确保提供的PPT文件路径正确且文件可访问
2. 大型PPT文件可能需要更长的处理时间
3. 复杂格式的PPT可能无法完全保留原始样式
4. 处理结果以Markdown文本形式返回，可能需要进一步编辑以满足特定需求
5. 建议处理完成后检查生成的Markdown内容，确保关键信息正确转换

## 开发团队

项目由Nexus-AI平台开发团队完成，采用单Agent架构，通过系统化的开发流程从需求分析到最终实现。

## 许可证

© 2025 Nexus-AI. 保留所有权利。

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-15 08:40:39 UTC*
