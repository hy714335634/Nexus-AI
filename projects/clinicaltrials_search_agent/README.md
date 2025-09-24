# clinicaltrials_search_agent

## 项目描述
一个专为临床开发人员设计的智能检索Agent，能够自动检索clinicaltrials.gov的数据，支持多次深度检索并整合分析结果，确保检索内容全面、完整且正确。

## 项目结构
```
clinicaltrials_search_agent/
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

#### clinicaltrials_search_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/clinicaltrials_search_agent/agents/clinicaltrials_search_agent/agent_developer_manager.json)

## 附加信息
# ClinicalTrials Search Agent

## 项目概述
ClinicalTrials Search Agent 是一个专为临床开发人员设计的智能检索Agent，能够自动检索clinicaltrials.gov的数据，支持多次深度检索并整合分析结果，确保检索内容全面、完整且正确。

## 功能特点
- **智能查询理解**：理解用户的自然语言查询和临床术语
- **检索策略规划**：根据用户问题先思考如何进行检索，再搜索相关内容信息
- **多次深度检索**：执行多次深度检索以获取全面信息
- **结果分析与整合**：分析和整合检索结果，消除重复和冲突
- **临床视角呈现**：以临床开发视角组织和呈现信息
- **会话上下文管理**：维护会话上下文以支持连续查询

## 项目结构
```
clinicaltrials_search_agent/
├── agents/
│   └── clinicaltrials_search_agent.py  # 主Agent实现
├── config/
│   └── agent_config.py                 # Agent配置文件
├── prompts/
│   └── clinicaltrials_search_agent_prompt.txt  # Agent提示词模板
├── tools/
│   ├── clinical_trials_api_client.py   # API客户端工具
│   ├── query_builder.py                # 查询构建工具
│   ├── results_parser.py               # 结果解析工具
│   ├── results_analyzer.py             # 结果分析工具
│   ├── results_integrator.py           # 结果整合工具
│   └── clinical_report_generator.py    # 报告生成工具
├── utils/
│   ├── session_manager.py              # 会话管理
│   ├── error_handler.py                # 错误处理
│   └── logger.py                       # 日志记录
└── requirements.txt                    # 项目依赖
```

## 使用方法
### 基本使用
```bash
python agents/clinicaltrials_search_agent.py -q "查找针对2型糖尿病的III期临床试验"
```

### 高级参数
```bash
python agents/clinicaltrials_search_agent.py -q "查找针对2型糖尿病的III期临床试验" \
  -n 30 \
  -d 3 \
  --study_types "Interventional" \
  --phases "Phase 3" \
  --status "Recruiting,Active, not recruiting" \
  --start_date "2020-01-01" \
  --report_type "detailed"
```

### 交互式会话
```bash
python agents/clinicaltrials_search_agent.py --session
```

## 参数说明
- `-q`: 研究问题或临床查询（必需）
- `-n`: 每次搜索返回的最大结果数（默认：20）
- `-d`: 执行深度搜索的次数（默认：2）
- `--study_types`: 按研究类型过滤的逗号分隔列表
- `--phases`: 按试验阶段过滤的逗号分隔列表
- `--status`: 按试验状态过滤的逗号分隔列表
- `--start_date`: 结果过滤的开始日期（YYYY-MM-DD）
- `--end_date`: 结果过滤的结束日期（YYYY-MM-DD）
- `--report_type`: 生成报告的类型（默认：summary）
- `--session`: 启动多查询交互式会话

## 依赖项
项目依赖项列在requirements.txt文件中。使用以下命令安装：
```bash
pip install -r requirements.txt
```

## 开发状态
- ✅ 需求分析
- ✅ 系统架构设计
- ✅ Agent设计
- ✅ 工具开发
- ✅ 提示词工程
- ✅ Agent代码开发
- ✅ Agent开发管理

## 注意事项
- 本Agent遵守ClinicalTrials.gov的使用条款和API限制
- 不存储或缓存大量ClinicalTrials.gov数据
- 不提供医疗建议或诊断
- 不替代专业临床判断
- 不修改或提交临床试验数据

## 示例查询
1. "查找针对晚期乳腺癌的免疫疗法临床试验"
2. "比较COVID-19 mRNA疫苗的III期临床试验结果"
3. "找出过去5年内针对阿尔茨海默病的新药临床试验"
4. "查询正在招募的儿童哮喘治疗临床试验"
5. "分析罕见病临床试验的成功率趋势"

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-23 18:05:03 UTC*
