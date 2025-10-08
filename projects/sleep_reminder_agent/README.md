# sleep_reminder_agent

## 项目描述
一个能够帮助用户生成睡觉提醒的智能体，可以根据用户设定的时间和偏好发送提醒

## 项目结构
```
sleep_reminder_agent/
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
- **requirements_analyzer**: ✅ 已完成 - [文档](agents/sleep_reminder_agent/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](agents/sleep_reminder_agent/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](agents/sleep_reminder_agent/agent_designer.json)
- **prompt_engineer**: ✅ 已完成
- **tools_developer**: ✅ 已完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# 睡眠提醒Agent

## 项目概述

睡眠提醒Agent是一个智能化的睡眠提醒系统，能够根据用户的作息习惯和偏好，提供个性化的睡眠提醒服务，帮助用户建立健康的睡眠规律。

## 项目状态

| 阶段 | 状态 |
|------|------|
| 需求分析 | ✅ 已完成 |
| 系统架构 | ✅ 已完成 |
| Agent设计 | ✅ 已完成 |
| 工具开发 | ✅ 已完成 |
| 提示词工程 | ✅ 已完成 |
| Agent代码开发 | ✅ 已完成 |
| 项目总结与交付 | ✅ 已完成 |

## 功能特性

- **睡眠时间设置和管理**：用户可以设置理想的睡眠时间，系统会在适当时间提醒
- **个性化提醒消息**：根据用户偏好生成定制化的提醒内容
- **多种提醒方式**：支持文本、声音、弹窗等多种提醒方式
- **重复提醒规则**：可设置在用户未响应时的重复提醒策略
- **用户偏好学习**：系统会学习用户的使用习惯，优化提醒策略
- **提醒历史管理**：记录和查询历史提醒数据，分析睡眠习惯

## 目录结构

```
sleep_reminder_agent/
├── agent/
│   ├── sleep_reminder_agent.py   # 主Agent代码
│   └── app.py                    # Web API接口
├── tools/
│   └── sleep_reminder_tools.py   # 工具代码
├── prompts/
│   └── sleep_reminder_prompt.md  # 提示词模板
├── agents/
│   └── sleep_reminder_agent/     # Agent开发阶段文档
├── requirements.txt              # 项目依赖
└── README.md                     # 项目说明
```

## 安装与使用

### 安装依赖

```bash
pip install -r requirements.txt
```

### 命令行模式

```bash
python agent/sleep_reminder_agent.py
```

### API服务模式

```bash
python agent/sleep_reminder_agent.py --api [端口号]
```

或者使用Flask应用：

```bash
python agent/app.py
```

## 使用示例

### 设置睡眠时间

```
用户: 设置睡眠时间为晚上10点半
助手: 好的，我已将您的睡眠提醒时间设置为22:30。下次提醒将在明天晚上10:30发送，距离现在还有XX小时XX分钟。您希望使用什么方式接收提醒呢？（目前支持文本、声音和弹窗通知）
```

### 配置提醒方式

```
用户: 我想用声音方式提醒我
助手: 已将您的提醒方式设置为声音通知。在睡眠提醒时间到达时，系统将发送声音提醒。您还可以随时添加其他提醒方式，如文本或弹窗通知。
```

### 设置重复提醒

```
用户: 如果我没回应，请每10分钟提醒我一次，最多提醒3次
助手: 已设置重复提醒规则。如果您没有响应第一次提醒，系统将每10分钟再次提醒您，最多重复3次。这有助于确保您不会错过睡眠时间。
```

### 查询下次提醒

```
用户: 我的下一次睡眠提醒是什么时候？
助手: 根据您的设置，下一次睡眠提醒将在今晚22:00（晚上10点）发送，距离现在还有5小时23分钟。您设置的提醒方式是文本通知，是否需要我调整这些设置？
```

## 技术实现

### 工具模块

- **TimeManager**：时间管理工具，用于验证时间格式、计算下次提醒时间等
- **NotificationManager**：通知工具，支持多种提醒方式（文本、声音、弹窗）
- **DataManager**：数据存储工具，管理用户配置和历史记录
- **MessageTemplateManager**：消息模板工具，生成个性化提醒消息
- **UserPreferenceManager**：用户偏好工具，学习和优化用户偏好
- **ReminderScheduler**：定时调度器，管理提醒的定时执行

### Agent实现

- 基于正则表达式的意图识别系统
- 全面的错误处理机制
- 支持命令行交互和API服务两种模式
- 个性化响应生成

## 注意事项

- 本系统提供的睡眠建议仅为一般性建议，不构成医疗建议
- 用户数据存储在本地，不会上传到云端
- 系统依赖于设备的时钟准确性
- 需要授权通知权限才能正常发送提醒

## 未来扩展计划

1. 添加更高级的自然语言处理能力
2. 集成机器学习模型进行更精准的用户偏好学习
3. 支持多用户和账户系统
4. 添加更丰富的睡眠统计和分析功能
5. 开发移动应用和桌面客户端

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-10-08 14:30:36 UTC*
