# stock_analysis_agent

## 项目描述
AI智能体项目：stock_analysis_agent

## 平台目录结构
```
nexus-ai/
├── agents/                    # 智能体实现
│   ├── system_agents/         # 核心平台智能体
│   ├── template_agents/       # 可复用智能体模板 —— 后续Agent代码开发需要参考模版文件
│   └── generated_agents/      # 动态创建的智能体 —— 后续开发的Agent代码应存储在此目录
├── prompts/                   # YAML提示词模板
│   ├── system_agents_prompts/ # 系统智能体提示词
│   ├── template_prompts/      # 模板提示词 —— 后续Agent提示词开发需要参考模版文件
│   └── generated_agents_prompts/ # 生成的提示词 —— 后续开发的Agent提示词应存储在此目录
├── tools/                     # 工具实现
│   ├── system_tools/          # 核心平台工具
│   ├── template_tools/        # 工具模板  —— 后续Agent工具开发需要参考模版文件
│   └── generated_tools/       # 生成的工具 —— 后续开发的Agent工具应存储在此目录
├── projects/                  # 用户项目目录  —— Agent开发过程文件及项目管理文件存储在对应项目目录中
│   └── <project_name>/
│       ├── agents/
│       │   └── <agent_name>/
        │       ├── requirements_analyzer.json       #需求分析师输出文档
        │       ├── system_architect.json            #Agent系统架构师输出文档
        │       ├── agent_designer.json              #agent设计师输出文档
        │       ├── prompt_engineer.json             #提示词工程师输出文档
        │       ├── tools_developer.json             #工具开发者输出文档
        │       ├── agent_code_developer.json        #agent代码开发工程师输出文档
        │       └── agent_developer_manager.json     #项目开发审核结果
│       ├── config.yaml          # 项目基本配置
│       ├── README.md            # 项目说明
│       └── status.yaml          # 项目需求文档和进度追踪
└── utils/                     # 共享工具

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
项目状态和各阶段结果将在开发过程中更新到此文档。

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。
