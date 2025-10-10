# Web Console Implementation Backlog

> 目标：依据 `web/v2` 目录下的静态原型页面，逐步在 Next.js 应用中还原界面与交互。各任务按模块归类，推荐依次推进（全局基础 → 核心流程 → 管理面 → 运维面 → 诊断工具）。

## ✅ 全局基础
- [ ] 搭建统一布局（导航、主题、栅格）以承载所有页面；对照 `00.homepage_overview.html` 的顶栏/侧栏结构。
- [ ] 建立设计系统（色板、排版、按钮/标签等 UI 原子件），确保后续页面可复用。
- [ ] 引入全局状态管理（React Query/Context），预留 API 数据接入点。
- [ ] 定义路由映射表（原型页面 → Next.js 路由路径），并整理导航菜单。

## 🧭 首页与概览
- [ ] `00.homepage_overview.html`：实现总览仪表盘（构建状态卡片、部署摘要、活跃项目列表、底部日志切片）。
- [ ] `change-preview.html`：新增模块用于展示版本变更摘要，与首页或发布流程联动。

## 🛠 Agent 构建流程
- [ ] `01.AgentBuild.html`：实现多阶段可视化的 Agent 构建向导（需求收集 → 架构 → 工具 → 代码 → 测试 → 部署）。
- [ ] `01.AgentBuildModule.html`：细化子组件（步骤横向导航、右侧预览面板、上下分栏卡片）。
- [ ] `agent-dialog.html`：实现构建确认弹窗（输入参数、风险提示、行动按钮）。
- [ ] `agent-graph-dialog.html` & `agent-graph-view.html`：接入 Agent 工作流拓扑图，支持节点信息 hover、关键路径高亮。
- [ ] `agent-detail.html`：构建单个 Agent 的详情视图，包含基础信息、版本切换、执行统计。

## 📈 项目与演进
- [ ] `02.AgentManagement.html`：实现项目/Agent 列表页（筛选、排序、批量操作、快速入口）。
- [ ] `evolution.html`：搭建项目演进总览（甘特图/泳道、状态摘要、右侧事件流）。
- [ ] `evolution-submit.html`：完善演进提交流程（需求变更表单、负责人/标签选择）。
- [ ] `evolution-progress.html`：实现阶段进度追踪（里程碑、燃尽图、依赖关系）。
- [ ] `evolution-history.html`：呈现历史版本/里程碑时间轴，支持对比与回滚入口。
- [ ] `evolution-analytics.html`：构建分析面板（成功率、耗时箱线图、Top 失败原因）。
- [ ] `evolution-agents.html`：列出演进期间的关联 Agent 及其状态、版本脉络。

## 🧩 工具与 MCP
- [ ] `03.Tools&MCP.html`：实现工具总览页，展示内置工具、MCP 集成状态、启用指标。
- [ ] `tool-create.html`：工具创建向导（表单验证、代码模板、依赖检查）。
- [ ] `tool-config.html`：配置详情页（环境变量、权限、回调/超时设置）。
- [ ] `tool-detail.html`：工具执行历史、告警、关联 Agent 视图。
- [ ] `tool-logs.html`：集成实时日志流与分页查询。
- [ ] `tool-build-progress.html`：还原工具构建与发布流水线可视化。
- [ ] `mcp-create.html`：MCP 连接配置页面（认证、能力声明、连接测试）。

## 📚 PFR（Prompt Feedback Review）
- [ ] `04.PFR.html`：搭建 Prompt 审核与反馈主界面（评审队列、上下文预览、操作栏）。
- [ ] `pfr-history.html`：审查历史列表，支持过滤、导出。
- [ ] `pfr-iteration-detail.html`：单次迭代详情（修改对比、评分、批注）。

## 🚀 运维与 AgentOps
- [ ] `06.AgentOps.html`：运维总览面板（运行状况、告警、部署节奏、SLA）。
- [ ] `evolution-analytics.html`（与 Ops 复用图表）& `evolution-progress.html` 中涉及的 Ops 视角需共用组件。
- [ ] `项目总结报告.md`：生成发布后总结报告的展示模板（markdown → 组件）。

## 🧪 演示与测试工具
- [ ] `对话测试.html`：实现对话测试接口（多模型切换、上下文注入、工具调用回显）。

## 🔍 故障诊断与 Troubleshoot
- [ ] `troubleshoot.html`：创建诊断流程入口（问题分类、快速导航、统计概览）。
- [ ] `troubleshoot-analysis.html`：问题分析页面（日志、指标、根因建议）。
- [ ] `troubleshoot-reproduction.html`：复现流程（环境选择、输入记录、重放控制）。
- [ ] `troubleshoot-code-review.html`：代码诊断视图（静态分析结果、风险提示）。
- [ ] `troubleshoot-fix.html`：修复执行跟踪（任务状态、回滚入口）。
- [ ] `troubleshoot-tracking.html`：后续跟踪与验证面板（告警清零、业务指标回归）。

## 🔄 变更与对比
- [ ] `change-preview.html`（与首页引用）和 `agent-dialog.html` 等弹窗需抽象成复用的模态框组件。

## 📊 其他页面
- [ ] `pfr-history.html`、`pfr-iteration-detail.html`、`evolution-history.html` 等时间轴页面共用“事件线”组件。
- [ ] `evolution-submit.html`、`tool-create.html`、`mcp-create.html` 等表单需统一校验体验与成功反馈。
- [ ] `evolution-progress.html` 与 `tool-build-progress.html` 的流水线组件应共享基础实现。

---

> 提示：每完成一组页面（如 Agent 构建、工具管理）后，更新此文档的勾选状态，并在对应 PR / 任务单中关联该条目。

扩展后端，新增项目构建总览接口，统一返回需求描述、阶段快照、最新任务信息与基础指标。
补充后端解析/聚合逻辑（如 workflow summary 指标提取、stage snapshot 合并）。
在前端定义新的类型与 API 封装，提供构建总览的 React Query hook。
重构 /build 主页面，让进度、需求、指标等都基于真实数据渲染。
继续改造 /build/modules 与 /build/graph，复用同一数据源并展示动态状态。