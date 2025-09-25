# aws_architecture_diagram_generator

## 项目描述
AWS架构图生成智能体，能够理解IT技术栈并映射到AWS服务，基于自然语言描述生成多种格式的架构图（mermaid、markdown、drawio和PPT），确保架构合理、产品选择正确、概念准确且图形美观。

## 项目结构
```
aws_architecture_diagram_generator/
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

#### aws_architect
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_architecture_diagram_generator/agents/aws_architect/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_architecture_diagram_generator/agents/aws_architect/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_architecture_diagram_generator/agents/aws_architect/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# AWS Architecture Diagram Generator

## 项目概述
AWS架构图生成智能体，能够理解IT技术栈并映射到AWS服务，基于自然语言描述生成多种格式的架构图（mermaid、markdown、drawio和PPT），确保架构合理、产品选择正确、概念准确且图形美观。

## 开发状态
项目已完成全部开发阶段：
- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 工具开发
- ✅ 提示词工程
- ✅ Agent代码开发
- ✅ 开发管理

## 功能特性
- 自然语言架构需求理解和澄清
- IT技术栈到AWS服务的智能映射
- 架构合理性验证和最佳实践检查
- 多格式架构图生成（mermaid、markdown、drawio、PPT）
- 架构图美化和AWS风格适配
- AWS服务实时查询和信息获取
- VPC内外服务的正确分类和布局
- 复杂连接关系的优化布局
- AWS图标和样式的专业应用

## 目录结构
```
aws_architecture_diagram_generator/
├── agents/
│   └── aws_architect/
│       └── aws_architect_agent.py
├── prompts/
│   └── aws_architect_prompt.yaml
├── tools/
│   ├── aws_service_tools.py
│   ├── diagram_generator.py
│   └── ppt_generator_and_validator.py
├── requirements.txt
└── README.md
```

## 使用方式
### 安装依赖
```bash
pip install -r requirements.txt
```

### 基本使用
```bash
python agents/aws_architect/aws_architect_agent.py -r "需要一个三层Web应用架构，包含前端、API和数据库，需要高可用性"
```

### 命令行参数
- `-r`: 自然语言描述的架构需求
- `-f`: 包含架构需求的文件路径
- `-o`: 输出格式，逗号分隔（mermaid,markdown,drawio,ppt）或"all"
- `-t`: 架构图标题
- `--template`: PPT输出的PowerPoint模板文件路径
- `--interactive`: 启用交互模式进行多轮对话

### 示例
```bash
# 生成所有格式的架构图
python agents/aws_architect/aws_architect_agent.py -r "电商网站架构，包含Web前端、商品目录API、用户认证、购物车、支付处理和订单管理，需要高可用和可扩展" -t "电商网站AWS架构"

# 仅生成mermaid和markdown格式
python agents/aws_architect/aws_architect_agent.py -r "简单的WordPress博客架构" -o "mermaid,markdown"

# 使用自定义PPT模板
python agents/aws_architect/aws_architect_agent.py -r "数据分析平台架构" --template "templates/company_template.pptx"

# 交互式模式
python agents/aws_architect/aws_architect_agent.py --interactive
```

## 工具说明
1. **aws_service_tools.py**
   - `map_tech_stack_to_aws`: 将传统IT技术栈映射到对应的AWS服务
   - `query_aws_service_info`: 查询AWS服务信息，包括服务描述、功能、限制等
   - `validate_architecture`: 验证架构设计的合理性和AWS最佳实践符合性

2. **diagram_generator.py**
   - `generate_mermaid_diagram`: 生成mermaid格式的架构图
   - `generate_markdown_diagram`: 生成markdown格式的架构文档
   - `generate_drawio_diagram`: 生成drawio格式的XML文件

3. **ppt_generator_and_validator.py**
   - `generate_ppt_architecture`: 基于模板生成PPT格式的架构图
   - `validate_aws_architecture`: 验证架构设计，包括VPC内外服务的正确分类

## 注意事项
- 需要网络连接以使用strands_tools/use_aws工具进行实时AWS服务查询
- PPT生成功能需要用户提供模板，否则将使用内置的默认模板
- 复杂架构可能需要更长的处理时间
- 仅支持AWS云服务，不支持其他云平台

## 依赖库
- strands>=0.5.0
- python-pptx>=0.6.21
- diagrams>=0.23.3
- markdown>=3.4.3
- boto3>=1.26.0
- drawio-exporter>=0.1.0
- 其他依赖详见requirements.txt

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-24 10:31:17 UTC*
