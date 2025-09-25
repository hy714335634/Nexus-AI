# fitness_advisor

## 项目描述
一个能够根据用户情况生成个性化健身建议的智能体

## 项目结构
```
fitness_advisor/
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

#### fitness_advisor_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# Fitness Advisor

## 项目概述
Fitness Advisor 是一个智能健身顾问系统，能够根据用户的个人情况、健身目标和偏好，生成个性化健身建议，提供锻炼计划、饮食建议和健身指导，回答用户关于健身的常见问题。

## 项目状态
✅ 需求分析: 完成  
✅ 系统架构: 完成  
✅ 智能体设计: 完成  
✅ 工具开发: 完成  
✅ 提示词工程: 完成  
✅ 智能体代码开发: 完成  
✅ 智能体开发管理: 完成  

## 功能特点
- 个性化健身计划生成
- 科学的饮食建议和营养指导
- 健康指标计算（BMI、BMR、TDEE等）
- 锻炼进度跟踪和分析
- 健身目标设定和监控
- 健身常见问题解答
- 锻炼提醒和日程安排

## 技术架构
本项目基于Claude 3.5 Sonnet大语言模型，结合专业健身知识和个性化推荐算法，通过自然语言交互为用户提供健身指导。

### 核心组件
1. **健身计算工具** - 提供各种健康指标的计算功能
2. **用户资料管理** - 存储和管理用户个人信息和健身记录
3. **时间跟踪系统** - 管理健身计划和提醒

## 目录结构
```
fitness_advisor/
├── agents/
│   └── fitness_advisor_agent/
│       ├── agent_designer.json      # 智能体设计文档
│       ├── requirements_analyzer.json # 需求分析文档
│       ├── system_architect.json    # 系统架构文档
│       ├── prompt_engineer.json     # 提示词工程文档
│       └── agent_code_developer.json # 智能体代码文档
├── tools/
│   └── generated_tools/
│       └── fitness_advisor/
│           ├── fitness_calculator.py  # 健康指标计算工具
│           ├── user_profile_manager.py # 用户数据管理工具
│           └── fitness_time_tracker.py # 时间管理工具
├── requirements.txt                 # 项目依赖
└── README.md                        # 项目说明文档
```

## 工具说明

### 1. 健康指标计算工具 (fitness_calculator.py)
提供多种健康和健身相关指标的计算功能：
- BMI (身体质量指数) 计算
- BMR (基础代谢率) 计算
- TDEE (每日总能量消耗) 计算
- 体脂率计算
- 理想体重计算
- 宏量营养素需求计算
- 一次性最大重量(1RM)计算
- 运动消耗卡路里计算
- 每日水分需求计算

### 2. 用户数据管理工具 (user_profile_manager.py)
管理用户个人资料和健身相关数据：
- 用户个人资料保存和检索
- 健身目标管理
- 锻炼记录存储和分析
- 身体测量数据跟踪
- 用户进度报告生成

### 3. 时间管理工具 (fitness_time_tracker.py)
管理健身计划和时间相关功能：
- 健身计划创建和管理
- 每日/每周锻炼计划查看
- 锻炼完成记录
- 锻炼提醒设置
- 计划坚持情况分析

## 使用方法
用户可以通过自然语言对话与Fitness Advisor智能体进行交互，例如：
1. 询问健身建议："我想减掉10公斤体重，应该怎么做？"
2. 获取锻炼计划："请给我制定一个每周三天的力量训练计划"
3. 计算健康指标："我身高175厘米，体重70公斤，请计算我的BMI"
4. 设定健身目标："我想在三个月内增加5公斤肌肉"
5. 跟踪健身进度："我上周完成了哪些锻炼？"
6. 获取饮食建议："请给我制定一个减脂期的饮食计划"

## 安全与免责声明
- Fitness Advisor提供的建议基于科学健身原则，但不能替代专业医疗或健身教练的指导
- 用户在开始任何新的健身计划前应咨询医生
- 系统不提供医疗诊断或治疗建议
- 用户数据仅在当前会话中使用，不进行永久存储

## 依赖项
- strands>=0.1.0
- python-dateutil>=2.8.2
- typing_extensions>=4.5.0
- pydantic>=2.0.0

## 未来计划
- 添加更多专业化的训练计划模板
- 增强饮食建议的个性化程度
- 集成可视化进度报告
- 支持可穿戴设备数据导入
- 开发移动应用界面

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-25 07:55:54 UTC*
