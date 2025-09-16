# html2pptx

## 项目描述
一个智能Agent，能够将HTML文档转换为PPTX格式的演示文稿，保留原始文档的结构、样式、图片和语义内容，支持自定义模板，并能处理任意复杂度的HTML文档。

## 项目结构
```
html2pptx/
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

#### html2pptx_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/html2pptx_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/html2pptx_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/html2pptx_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

#### HTML2PPTXAgent
- **requirements_analyzer**: ⏳ 待完成
- **system_architect**: ⏳ 待完成
- **agent_designer**: ⏳ 待完成
- **prompt_engineer**: ⏳ 待完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ⏳ 待完成
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# HTML2PPTX Agent

一个智能Agent，能够将HTML文档转换为PPTX格式的演示文稿，保留原始文档的结构、样式、图片和语义内容，支持自定义模板，并能处理任意复杂度的HTML文档。

## 项目概述

HTML2PPTX Agent是一个专业的文档转换工具，旨在解决将网页内容或HTML文档快速转换为高质量PowerPoint演示文稿的需求。该Agent能够智能地分析HTML文档的语义结构，提取关键内容，并生成符合原始样式的PPT页面，大大节省了手动创建演示文稿的时间和精力。

### 主要功能

- **HTML文档解析与语义提取**：解析任意复杂度的HTML文档，提取关键语义信息
- **PPT结构生成**：基于HTML文档结构自动生成合理的PPT页面结构
- **样式映射**：将HTML样式属性映射到PPT样式设置，保持原始视觉效果
- **图片处理**：提取HTML中的图片并合理布局到PPT中
- **自定义模板支持**：支持用户指定PPT模板，满足品牌或风格要求
- **备注信息保留**：将HTML中的重要注释和补充信息保存在PPT的备注部分
- **本地缓存机制**：使用本地缓存存储中间处理结果，解决Token限制问题

## 项目状态

| 阶段 | 状态 |
|------|------|
| 需求分析 | ✅ 已完成 |
| 系统架构设计 | ✅ 已完成 |
| Agent设计 | ✅ 已完成 |
| 工具开发 | ✅ 已完成 |
| 提示词工程 | ✅ 已完成 |
| Agent代码开发 | ✅ 已完成 |
| 开发管理 | ✅ 已完成 |

## 目录结构

```
html2pptx/
├── agents/
│   └── generated_agents/
│       └── html2pptx/
│           └── html2pptx_agent.py  # Agent主代码
├── prompts/
│   └── generated_agents_prompts/
│       └── html2pptx/
│           └── html2pptx_agent.yaml  # Agent提示词模板
├── tools/
│   └── generated_tools/
│       └── html2pptx/
│           ├── html_parser.py       # HTML解析工具
│           ├── pptx_generator.py    # PPT生成工具
│           ├── image_processor.py   # 图片处理工具
│           ├── cache_manager.py     # 缓存管理工具
│           ├── style_mapper.py      # 样式映射工具
│           ├── semantic_analyzer.py # 语义分析工具
│           └── layout_optimizer.py  # 布局优化工具
└── README.md
```

## 使用方法

### 基本用法

```python
from agents.generated_agents.html2pptx.html2pptx_agent import convert_html_to_pptx

# 基本转换
output_path = convert_html_to_pptx(
    html_path="path/to/document.html",
    output_path="path/to/output.pptx"
)

# 使用自定义模板
output_path = convert_html_to_pptx(
    html_path="path/to/document.html",
    output_path="path/to/output.pptx",
    template_path="path/to/template.pptx"
)
```

### 命令行使用

```bash
# 转换HTML到PPTX
python -m agents.generated_agents.html2pptx.html2pptx_agent convert -i path/to/document.html -o path/to/output.pptx

# 使用自定义模板
python -m agents.generated_agents.html2pptx.html2pptx_agent convert -i path/to/document.html -o path/to/output.pptx -t path/to/template.pptx

# 分析HTML文档结构
python -m agents.generated_agents.html2pptx.html2pptx_agent analyze -i path/to/document.html

# 建议PPT幻灯片结构
python -m agents.generated_agents.html2pptx.html2pptx_agent suggest -i path/to/document.html -m 15

# 清理缓存
python -m agents.generated_agents.html2pptx.html2pptx_agent clear-cache
```

## 高级功能

### 分析HTML结构

```python
from agents.generated_agents.html2pptx.html2pptx_agent import analyze_html_structure

# 分析HTML文档结构
analysis = analyze_html_structure("path/to/document.html")
print(analysis)
```

### 建议PPT结构

```python
from agents.generated_agents.html2pptx.html2pptx_agent import suggest_ppt_structure

# 获取PPT结构建议
suggestions = suggest_ppt_structure(
    html_path="path/to/document.html",
    max_slides=15
)
print(suggestions)
```

### 缓存管理

```python
from agents.generated_agents.html2pptx.html2pptx_agent import clear_cache

# 清理缓存
clear_cache()
```

## 技术特点

1. **语义优先**：不仅仅是简单的格式转换，而是深入理解HTML文档的语义结构和内容
2. **样式保留**：尽可能保持原始HTML的视觉样式，确保转换后的PPT美观专业
3. **模块化设计**：将HTML解析、内容提取、PPT生成等功能模块化，便于维护和扩展
4. **缓存机制**：实现本地缓存以解决Token限制问题，提高处理效率
5. **错误容忍**：能够处理不规范的HTML文档，跳过不支持的元素而非中断整个流程

## 限制说明

- 不支持HTML动画效果转换
- 不支持交互式HTML元素的功能复制
- 不支持视频内容的处理和嵌入
- 不提供在线存储和共享功能
- 不支持实时协作编辑

## 依赖库

- BeautifulSoup/lxml：用于HTML解析
- python-pptx：用于PPT生成
- Pillow：用于图片处理
- Strands SDK：用于Agent框架

## 性能考量

- 能够在60秒内完成中等复杂度HTML文档的转换
- 能够处理至少100页的HTML文档
- 能够处理包含至少50张图片的HTML文档

## 未来计划

- 添加更多PPT模板和主题
- 支持更多HTML特性和样式
- 提供图表和数据可视化转换
- 优化大型文档的处理性能
- 添加批量转换功能

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-15 18:16:40 UTC*
