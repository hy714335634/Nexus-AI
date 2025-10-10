# fitness_advisor

## 项目描述
一个能够根据用户需求生成个性化健身建议的智能体，包括锻炼计划、饮食建议和健身进度跟踪。

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
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/fitness_advisor/agents/fitness_advisor_agent/agent_developer_manager.json)

## 附加信息
# 🏋️‍♂️ Fitness Advisor - 智能健身顾问

## 📋 项目概述

Fitness Advisor是一个智能健身顾问Agent，能够为用户提供个性化的健身建议、锻炼计划、饮食指导和进度跟踪。基于先进的AI技术和专业的健身知识，这个智能体旨在成为用户的私人健身教练，帮助他们实现健康目标。

### 🎯 核心功能

- **用户健身水平评估**：分析用户当前健身状态和能力
- **个性化锻炼计划生成**：根据用户目标和条件创建定制训练方案
- **饮食建议和营养指导**：提供符合健身目标的饮食计划
- **健身目标设定和调整**：帮助用户设定科学合理的目标
- **进度跟踪和反馈**：监测训练效果并提供调整建议
- **健身知识问答**：回答用户关于健身和营养的问题
- **运动安全提醒**：确保训练安全，避免受伤风险
- **健身计划优化建议**：根据进度和反馈优化训练计划

## 🛠️ 技术架构

### 核心组件

1. **Agent核心模块**
   - `fitness_advisor_agent.py` - 主Agent实现
   - `conversation_manager.py` - 对话管理
   - `tool_orchestrator.py` - 工具协调
   - `safety_guardian.py` - 安全检查
   - `response_generator.py` - 响应生成

2. **专业工具集**
   - `text_analyzer.py` - 文本分析工具
   - `data_analyzer.py` - 数据分析工具
   - `json_converter.py` - JSON转换工具
   - `web_search_enhanced.py` - 增强型网络搜索
   - `information_collector.py` - 信息收集工具
   - `calculator.py` - 健身计算工具
   - `tool_registry.py` - 工具注册管理
   - `fitness_database.py` - 健身知识库

3. **提示词模板**
   - `fitness_advisor_agent_system_prompt.yaml` - 系统提示词
   - `fitness_advisor_agent_conversation_flows.yaml` - 对话流程模板

## 🚀 安装与使用

### 环境要求

- Python 3.10+
- Strands SDK
- AWS Bedrock访问权限

### 安装步骤

1. 克隆项目仓库
   ```bash
   git clone https://github.com/yourusername/fitness_advisor.git
   cd fitness_advisor
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件，填入必要的API密钥和配置
   ```

4. 启动Agent
   ```bash
   python run_agent.py
   ```

### 使用示例

```python
from fitness_advisor.agents.fitness_advisor_agent import FitnessAdvisorAgent

# 初始化Agent
agent = FitnessAdvisorAgent()

# 用户交互
response = agent.process_message("我想开始健身，但不知道从哪里开始。我的目标是减掉10公斤体重。")
print(response)

# 生成健身计划
user_profile = {
    "age": 30,
    "gender": "female",
    "height": 165,
    "weight": 70,
    "fitness_level": "beginner",
    "goals": ["weight_loss"],
    "available_time": "3 days per week, 1 hour each",
    "equipment": "minimal home equipment"
}
workout_plan = agent.generate_workout_plan(user_profile)
print(workout_plan)
```

## 📊 项目状态

- **开发状态**: ✅ 已完成
- **版本**: 1.0.0
- **最后更新**: 2025-10-08

### 开发阶段完成情况

| 阶段 | 状态 | 完成日期 |
|------|------|---------|
| 需求分析 | ✅ 已完成 | 2025-10-08 |
| 系统架构设计 | ✅ 已完成 | 2025-10-08 |
| Agent设计 | ✅ 已完成 | 2025-10-08 |
| 提示词工程 | ✅ 已完成 | 2025-10-08 |
| 工具开发 | ✅ 已完成 | 2025-10-08 |
| Agent代码开发 | ✅ 已完成 | 2025-10-08 |
| Agent开发管理 | ✅ 已完成 | 2025-10-08 |

## 📁 目录结构

```
fitness_advisor/
├── agents/                      # Agent核心代码
│   ├── __init__.py
│   ├── fitness_advisor_agent.py # 主Agent实现
│   ├── conversation_manager.py  # 对话管理
│   ├── tool_orchestrator.py     # 工具协调
│   ├── safety_guardian.py       # 安全检查
│   ├── response_generator.py    # 响应生成
│   └── config.py                # 配置文件
├── tools/                       # 工具集
│   ├── text_analyzer.py         # 文本分析
│   ├── data_analyzer.py         # 数据分析
│   ├── json_converter.py        # JSON转换
│   ├── web_search_enhanced.py   # 网络搜索
│   ├── information_collector.py # 信息收集
│   ├── calculator.py            # 计算工具
│   ├── tool_registry.py         # 工具注册
│   └── fitness_database.py      # 健身数据库
├── prompts/                     # 提示词模板
│   ├── fitness_advisor_agent_system_prompt.yaml
│   └── fitness_advisor_agent_conversation_flows.yaml
├── tests/                       # 测试代码
│   ├── test_agent_integration.py
│   ├── test_conversation_flows.py
│   └── test_safety_mechanisms.py
├── docs/                        # 文档
│   ├── agent_api_documentation.md
│   └── deployment_guide.md
├── examples/                    # 使用示例
│   └── usage_examples.py
├── requirements.txt             # 项目依赖
└── README.md                    # 项目说明
```

## 🔒 安全与限制

- Agent不提供医疗诊断或治疗建议
- 对于医疗相关问题，会建议用户咨询专业医疗人员
- 所有健身建议都包含安全提示和注意事项
- 根据用户的健康状况和限制提供适当的修改建议

## 📝 注意事项

- 用户应在开始任何新的健身计划前咨询医生
- Agent提供的建议基于用户提供的信息，准确性取决于信息的准确性
- Agent不能替代专业健身教练或营养师的个人指导
- 用户应根据自身感受调整训练强度，避免过度训练

## 🤝 贡献指南

欢迎对项目进行贡献！请遵循以下步骤：

1. Fork项目仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

如有问题或建议，请联系项目维护者：

- 邮箱: example@example.com
- GitHub: [yourusername](https://github.com/yourusername)

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-08 06:36:41 UTC*
