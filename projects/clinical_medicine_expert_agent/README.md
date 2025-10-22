# clinical_medicine_expert_agent

## 项目描述
临床医学专家智能体，能够回答用户专业的生命科学和临床医学问题，尤其是药物研发领域相关问题。基于给定工具和数据库收集证据，提供严谨的回答和完整的思考过程。

## 项目结构
```
clinical_medicine_expert_agent/
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

#### clinical_medicine_expert
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](agents/clinical_medicine_expert/agent_developer_manager.json)

## 附加信息
# 临床医学专家智能体 (Clinical Medicine Expert Agent)

## 项目概述

临床医学专家智能体是一个专业的AI助手，专门用于回答用户在生命科学和临床医学领域的专业问题，尤其是药物研发相关问题。该智能体基于给定的工具和数据库收集证据，提供严谨的回答和完整的思考过程，确保回答的专业性和可靠性。

### 核心特点

- **证据驱动**：所有回答基于可靠的证据和数据
- **思考透明**：提供完整的思考过程和证据来源
- **专业严谨**：确保医学和药物研发领域的专业准确性
- **谨慎审慎**：在证据不足时明确告知用户
- **工具集成**：有效整合和利用多种工具收集证据

## 项目状态

| 开发阶段 | 状态 | 完成日期 |
|---------|------|---------|
| 需求分析 | ✅ 已完成 | 2025-10-10 |
| 系统架构设计 | ✅ 已完成 | 2025-10-10 |
| Agent设计 | ✅ 已完成 | 2025-10-10 |
| 工具开发 | ✅ 已完成 | 2025-10-10 |
| 提示词工程 | ✅ 已完成 | 2025-10-10 |
| Agent代码开发 | ✅ 已完成 | 2025-10-10 |
| 开发管理 | ✅ 已完成 | 2025-10-10 |

## 目录结构

```
clinical_medicine_expert_agent/
├── agents/
│   └── clinical_medicine_expert_agent.py  # 主Agent代码
├── tools/
│   └── clinical_medicine_expert_tools.py  # 工具集成模块
├── prompts/
│   └── clinical_medicine_expert_prompt.txt  # 提示词模板
├── docs/
│   ├── requirements_analyzer.json  # 需求分析文档
│   ├── system_architect.json  # 系统架构文档
│   ├── agent_designer.json  # Agent设计文档
│   ├── tools_developer.json  # 工具开发文档
│   ├── prompt_engineer.json  # 提示词工程文档
│   └── agent_code_developer.json  # Agent代码开发文档
├── tests/
│   └── test_clinical_medicine_expert.py  # 测试用例
├── README.md  # 项目说明文档
└── requirements.txt  # 依赖包列表
```

## 功能说明

### 1. 问题分析

智能体能够分析用户问题，确定问题类型、领域和关键概念，为后续的证据收集提供指导。支持的问题类型包括：

- 机制类问题（药物作用机制、疾病机理等）
- 比较类问题（不同药物或治疗方法的对比）
- 研究进展类问题（最新研究成果和临床试验）
- 安全性问题（药物副作用和风险）
- 给药类问题（剂量、用法等）
- 疗效类问题（治疗效果和临床结果）
- 一般信息类问题

### 2. 证据收集

智能体集成了多种工具收集证据，包括：

- **embedding搜索**：查找相关医学文献和研究数据
- **知识图谱查询**：探索医学概念关系和药物作用路径
- **动态工具调用**：执行专门的医学数据分析任务

根据问题类型，智能体会选择最合适的工具和方法收集证据，并评估证据的充分性。

### 3. 回答生成

基于收集到的证据，智能体生成专业、严谨的回答，包括：

- 问题分析：对问题的理解和需要收集的证据类型
- 证据收集过程：使用的工具和获取到的证据
- 思考与分析：基于证据的推理和分析
- 专业回答：对用户问题的直接回答
- 局限性说明：如果证据不足，明确说明限制
- 参考来源：列出主要证据来源

## 使用方法

### 安装依赖

```bash
pip install -r requirements.txt
```

### 命令行使用

```bash
python agents/clinical_medicine_expert_agent.py -q "阿司匹林如何发挥抗血小板作用？"
```

参数说明：
- `-q` 或 `--query`：医学或药物研发问题（必需）
- `-e` 或 `--evidence_count`：最大证据收集数量（可选，默认为5）
- `-t` 或 `--threshold`：证据相关性阈值（可选，默认为0.7）

### 作为Web服务

```bash
# 启动Flask服务
python web_service.py
```

然后可以通过API调用：

```bash
curl -X POST http://localhost:5000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "二甲双胍在治疗2型糖尿病中的作用机制是什么？"}'
```

### 作为Python模块导入

```python
from agents.clinical_medicine_expert_agent import ClinicalMedicineExpertAgent

agent = ClinicalMedicineExpertAgent()
response = agent.process_query("mRNA疫苗技术在癌症治疗中有哪些最新进展？")
print(response)
```

## 示例问题

1. **药物机制类问题**：
   - "阿司匹林如何发挥抗血小板作用？"
   - "二甲双胍在治疗2型糖尿病中的作用机制是什么？"

2. **研究进展类问题**：
   - "mRNA疫苗技术在癌症治疗中有哪些最新进展？"
   - "CAR-T细胞疗法在血液肿瘤治疗中的最新研究成果有哪些？"

3. **比较分析类问题**：
   - "比较SGLT-2抑制剂和GLP-1受体激动剂在2型糖尿病治疗中的作用机制和疗效"
   - "PD-1和CTLA-4抑制剂在肿瘤免疫治疗中的异同是什么？"

## 注意事项

- 该智能体不提供医疗诊断或治疗建议，不应替代专业医生的判断
- 不处理个人健康信息
- 在证据不足的情况下，智能体会明确告知用户，不进行推测
- 回答基于现有医学文献和研究数据，可能不包含最新发布的研究成果

## 技术架构

该项目采用单Agent架构，基于三阶段思考框架（问题分析→证据收集→回答生成）实现。主要组件包括：

1. **ClinicalMedicineExpertAgent**：主Agent类，管理整个问答流程
2. **ClinicalMedicineTools**：工具集成类，提供证据收集和分析功能
3. **提示词模板**：定义Agent的角色、工作流程和回答格式

## 依赖技术

- Python 3.8+
- Strands SDK
- 大语言模型：Claude 3.5 Sonnet（推荐）
- 工具集成：embedding搜索、知识图谱查询、动态工具调用

## 维护与更新

- 定期更新工具和知识库，确保医学信息的时效性
- 监控和记录用户查询模式，优化常见问题的回答质量
- 实现证据缓存机制，提高频繁查询的响应速度
- 添加用户反馈机制，持续改进回答质量

## 贡献指南

欢迎对项目进行贡献，包括但不限于：

- 改进工具集成和证据收集方法
- 优化提示词模板和回答格式
- 添加新的医学数据源和专业分析工具
- 完善文档和示例

## 许可证

[MIT License](LICENSE)

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-10 10:08:02 UTC*
