# sleep_reminder

## 项目描述
一个能够帮助用户生成睡觉提醒的智能体，提供个性化的睡眠时间建议和提醒功能。

## 项目结构
```
sleep_reminder/
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

#### sleep_reminder_agent
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/sleep_reminder/agents/sleep_reminder_agent/agent_developer_manager.json)

## 附加信息
# 睡眠提醒助手 (Sleep Reminder)

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![状态](https://img.shields.io/badge/状态-稳定-success)

## 项目概述

睡眠提醒助手是一个智能化的个人睡眠管理工具，能够根据用户的睡眠习惯、作息规律和健康目标，生成个性化的睡觉提醒。系统通过分析用户的日常活动模式，提供最佳的睡眠时间建议，并在合适的时机发送温馨的睡眠提醒，帮助用户建立健康的睡眠习惯。

### 核心功能

- **个性化睡眠时间计算**：根据用户的起床时间和睡眠需求，自动计算最佳睡觉时间
- **智能睡眠提醒**：在合适的时间发送个性化的睡眠提醒消息
- **睡眠习惯追踪**：记录和分析用户的睡眠模式，提供改善建议
- **睡眠健康知识**：提供科学的睡眠健康知识和建议
- **高度可定制**：支持自定义提醒方式、风格和内容

## 项目结构

```
sleep_reminder/
├── src/                          # 源代码目录
│   ├── sleep_reminder_agent.py   # 主Agent类
│   ├── tools/                    # 功能模块工具
│   │   ├── user_profile_manager.py
│   │   ├── sleep_calculator.py
│   │   ├── reminder_generator.py
│   │   ├── sleep_tracker.py
│   │   ├── knowledge_base.py
│   │   ├── schedule_manager.py
│   │   └── notification_service.py
│   ├── utils/                    # 工具类
│   │   ├── database_manager.py
│   │   ├── config_manager.py
│   │   ├── log_manager.py
│   │   └── validation_utils.py
│   ├── interfaces/               # 接口层
│   │   ├── agent_tools_api.py
│   │   └── data_access_layer.py
│   └── ui/                       # 用户界面
│       ├── sleep_reminder_gui.py
│       └── sleep_reminder_cli.py
├── config/                       # 配置文件
│   ├── default_settings.json
│   ├── reminder_templates.json
│   ├── knowledge_base.json
│   └── database_schema.sql
├── prompts/                      # 提示词模板
│   ├── system_prompt.txt
│   ├── prompt_templates.json
│   ├── response_examples.json
│   └── validation_rules.py
├── tests/                        # 测试代码
│   ├── unit/
│   ├── integration/
│   └── performance/
├── docs/                         # 文档
├── main.py                       # 主程序入口
├── setup.py                      # 安装脚本
├── service.py                    # 服务模式入口
├── requirements.txt              # 依赖项列表
└── README.md                     # 项目说明
```

## 安装指南

### 系统要求

- Python 3.8+
- SQLite 3.x
- 系统通知支持
- 100MB存储空间

### 安装步骤

1. 克隆或下载项目代码
   ```bash
   git clone https://github.com/yourusername/sleep_reminder.git
   cd sleep_reminder
   ```

2. 安装依赖项
   ```bash
   pip install -r requirements.txt
   ```

3. 运行初始化设置
   ```bash
   python setup.py
   ```

## 使用方法

### 图形界面模式

启动图形用户界面：
```bash
python main.py --gui
```

### 命令行模式

启动命令行界面：
```bash
python main.py --cli
```

### 服务模式

以后台服务方式运行：
```bash
python service.py start
```

### 基本操作流程

1. **初始设置**：首次运行时，系统会引导您完成个人睡眠偏好设置
2. **查看睡眠建议**：系统会根据您的设置计算最佳睡觉时间
3. **接收提醒**：在设定的时间，系统会发送睡眠提醒
4. **追踪分析**：使用一段时间后，可以查看睡眠习惯分析报告
5. **调整设置**：随时可以调整您的睡眠偏好和提醒设置

## 功能详解

### 用户睡眠偏好设置

- 设置理想睡眠时长（6-10小时）
- 设置固定起床时间
- 设置睡前准备时间（15-60分钟）
- 选择提醒风格（温和/活泼/专业/简洁）
- 设置提醒频率

### 智能睡眠时间计算

- 基于起床时间和睡眠需求计算最佳睡觉时间
- 考虑睡眠周期（90分钟）优化睡眠质量
- 根据实际情况动态调整建议

### 个性化睡眠提醒

- 支持多种提醒风格
- 根据距离睡觉时间调整提醒内容
- 考虑用户历史表现个性化提醒
- 多渠道提醒（桌面通知、声音、弹窗）

### 睡眠习惯分析

- 记录实际睡眠时间
- 分析睡眠规律性
- 计算睡眠债务
- 生成改善建议
- 提供周/月度报告

### 睡眠健康知识库

- 提供科学的睡眠知识
- 针对性的改善建议
- 根据年龄段的差异化建议
- 常见睡眠问题解决方案

## 隐私说明

- 所有数据本地存储，不上传到云端
- 敏感信息加密存储
- 最小化数据收集
- 用户完全控制数据，可随时导出或删除

## 开发状态

| 开发阶段 | 状态 |
|---------|------|
| 需求分析 | ✅ 完成 |
| 系统架构 | ✅ 完成 |
| Agent设计 | ✅ 完成 |
| 提示词工程 | ✅ 完成 |
| 工具开发 | ✅ 完成 |
| Agent代码开发 | ✅ 完成 |
| 开发管理 | ✅ 完成 |

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 联系方式

如有问题或建议，请提交 Issue 或联系开发团队。

---

*睡眠提醒助手 - 帮助您建立健康的睡眠习惯*

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-08 14:28:31 UTC*
