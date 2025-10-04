# fitness_advisor

## 项目描述
一个能够根据用户个人情况生成定制化健身建议的智能体，包括锻炼计划、饮食建议和健身目标追踪。

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
- **tools_developer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# Fitness Advisor

一个能够根据用户个人情况生成定制化健身建议的智能体，包括锻炼计划、饮食建议和健身目标追踪。

## 项目概述

Fitness Advisor是一个智能健身顾问系统，能够基于用户的个人信息（如年龄、性别、身高、体重、健身经验等）和健身目标（如减肥、增肌、塑形、提高体能等），提供个性化的健身建议，包括锻炼计划、饮食指导和进度跟踪方法。

## 功能特点

- **个性化健身计划**：根据用户的身体状况、健身经验和目标生成定制化的锻炼计划
- **饮食建议**：提供与健身目标匹配的营养指导和饮食建议
- **进度跟踪**：建议适合的健身进度跟踪方法和指标
- **安全保障**：提供运动安全提醒和注意事项，确保健身过程安全有效
- **健身知识**：解答用户关于健身的问题，提供科学的健身知识
- **动态调整**：根据用户反馈和进度调整训练计划

## 项目结构

```
fitness_advisor/
├── agents/
│   └── generated_agents/
│       └── fitness_advisor/
│           └── fitness_advisor_agent.py  # 主Agent代码
├── generated_agents_prompts/
│   └── fitness_advisor/
│       └── fitness_advisor_agent.yaml    # Agent提示词模板
├── requirements.txt                      # 项目依赖
└── README.md                             # 项目说明文档
```

## 开发状态

- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 提示词工程
- ✅ 工具开发
- ✅ Agent代码开发
- ✅ 开发管理与协调

## 使用方法

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 运行Agent：
   ```
   python agents/generated_agents/fitness_advisor/fitness_advisor_agent.py -q "我是一个30岁的男性，身高175cm，体重80kg，想要减脂增肌，每周能锻炼3-4次，每次1小时左右，请给我一个合适的健身计划和饮食建议。"
   ```

3. 可选参数：
   - `-q`：健身咨询问题
   - `-m`：咨询模式 (general, workout, nutrition, tracking, knowledge, safety)

## 注意事项

- 本系统提供的建议仅供参考，不替代专业健身教练或医疗专业人士的指导
- 用户在开始任何新的健身计划前，应咨询医生，特别是有既往健康问题的用户
- 系统不提供医疗诊断或治疗建议
- 用户应根据自身实际情况调整系统提供的建议

## 技术栈

- Python 3.13+
- Strands SDK
- AWS Bedrock AI推理引擎
- Anthropic Claude 3.5 Sonnet模型

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-03 12:30:49 UTC*
