# 工作流总结报告生成功能使用说明

## 功能概述

工作流总结报告生成功能已成功集成到 `agent_build_workflow.py` 中，能够在工作流执行完成后自动生成详细的总结报告。

## 主要特性

### 📊 报告内容
- **总体概览**: 工作流状态、执行时间、成功阶段数、Token使用量、工具调用次数
- **成本估算**: 基于GPT-4定价的输入/输出成本估算
- **阶段执行详情**: 每个阶段的详细执行指标
- **工具使用统计**: 各工具调用次数统计
- **性能分析**: 平均执行时间、Token效率、工具调用频率
- **详细工具调用记录**: 每个阶段的具体工具调用详情

### 🔧 技术实现
- 自动解析 `workflow_result` 中的 `GraphResult` 结构
- 提取 `EventLoopMetrics` 和 `ToolMetrics` 数据
- 基于 `cycle_count` 估算Token使用量
- 计算工具调用时间和成功率
- 生成Markdown格式的详细报告

## 使用方法

### 自动生成（推荐）
工作流执行完成后会自动生成报告，无需额外操作：

```python
# 在 agent_build_workflow.py 中已集成
result = run_workflow(user_input)
# 报告会自动生成到项目目录下的 workflow_summary_report.md
```

### 手动生成
如果需要手动生成报告：

```python
from utils.workflow_report_generator import generate_workflow_summary_report

# 生成报告
report_path = generate_workflow_summary_report(
    workflow_result=result['workflow_result'],
    intent_analysis=result['intent_analysis'],
    default_project_root_path="/projects/aws_pricing_agent"
)

print(f"报告已生成: {report_path}")
```

### 从JSON文件生成
如果工作流结果已保存为JSON文件：

```python
from utils.workflow_report_generator import generate_workflow_summary_report_from_json

# 从JSON文件生成报告
report_path = generate_workflow_summary_report_from_json(
    json_file_path="workflow_result.json",
    default_project_root_path="/projects/website_clone_generator"
)

print(f"报告已生成: {report_path}")
```

## 报告示例

生成的报告包含以下信息：

```markdown
# 工作流执行总结报告

**生成时间**: 2025-09-10 13:55:37
**项目名称**: aws_pricing_agent

## 📊 总体概览
- **工作流状态**: ✅ 成功完成
- **总执行时间**: 25.50 秒
- **成功阶段数**: 5/5
- **总输入Token**: 7,650
- **总输出Token**: 3,825
- **总工具调用次数**: 35

## 💰 成本估算
- **输入成本**: $0.000018 USD
- **输出成本**: $0.000057 USD
- **总成本**: $0.000075 USD
- **定价模型**: Claude 3.7 Sonnet
- **输入费率**: $0.003 USD/1K tokens
- **输出费率**: $0.015 USD/1K tokens

## 🔄 阶段执行详情
| 阶段名称 | 状态 | 执行时间(秒) | 输入Token | 输出Token | 工具调用次数 |
|---------|------|-------------|-----------|-----------|-------------|
| orchestrator | ✅ | 3.00 | 900 | 450 | 7 |
| requirements_analyzer | ✅ | 4.00 | 1,200 | 600 | 7 |
| system_architect | ✅ | 6.00 | 1,800 | 900 | 7 |
| agent_designer | ✅ | 5.00 | 1,500 | 750 | 7 |
| agent_developer_manager | ✅ | 7.50 | 2,250 | 1,125 | 7 |

## 🛠️ 工具使用统计
| 工具名称 | 调用次数 |
|---------|----------|
| current_time | 15 |
| update_project_config | 10 |
| project_init | 5 |
| list_all_projects | 5 |

## 📈 性能分析
- **平均每阶段执行时间**: 5.10 秒
- **Token效率**: 0.50 (输出/输入比)
- **工具调用频率**: 1.37 次/秒
```

## 文件位置

报告文件会生成在项目根目录下：
- 文件名: `workflow_summary_report.md`
- 路径: `{project_root_path}/workflow_summary_report.md`

### 项目路径提取逻辑

系统会自动从工作流结果中提取项目路径：

1. **优先从GraphResult提取**: 从orchestrator阶段的project_init工具调用中提取项目名称
2. **回退到默认路径**: 如果无法提取，使用 `/projects/` 作为默认路径
3. **动态路径构建**: 基于提取的项目名称构建完整路径 `/projects/{project_name}`

```python
def _extract_project_path_from_result(workflow_result: Any) -> str:
    """从工作流结果中提取项目路径"""
    # 从orchestrator的project_init工具调用中提取项目名称
    # 构建路径: /projects/{project_name}
    # 回退到: /projects/
```

## 注意事项

1. **Token估算**: 当前基于 `cycle_count` 进行估算，实际Token使用量可能有所不同
2. **成本计算**: 基于Claude 3.7 Sonnet定价模型（输入$0.003/1K，输出$0.015/1K），实际成本可能因使用的模型而异
3. **执行时间**: 基于工具调用时间和循环次数计算，提供相对准确的估算
4. **错误处理**: 如果解析失败，会生成包含错误信息的报告
5. **定价精度**: 成本显示精度为6位小数，适合小规模Token使用量的精确计算
6. **字符串化数据解析**: 支持解析保存为JSON文件的字符串化Python对象（如GraphResult、NodeResult等）
7. **正则表达式提取**: 使用正则表达式从字符串化数据中提取cycle_count、tool_metrics等信息

## 扩展功能

该功能可以进一步扩展：
- 支持更多定价模型
- 添加更精确的Token计算
- 集成实际执行时间记录
- 支持自定义报告模板
