# Nexus AI Console v2.0

现代化的 Nexus AI 平台前端控制台，使用 Next.js 14 + React 18 + Tailwind CSS 构建。

## 技术栈

- **框架**: Next.js 14 (App Router)
- **UI**: React 18 + Tailwind CSS
- **状态管理**: TanStack Query v5
- **图标**: Lucide React
- **图表**: Recharts
- **通知**: Sonner

## 项目结构

```
web/
├── app/                    # Next.js App Router 页面
│   ├── page.tsx           # 仪表盘首页
│   ├── layout.tsx         # 根布局
│   ├── globals.css        # 全局样式
│   ├── providers.tsx      # React Query Provider
│   ├── agents/            # Agent 相关页面
│   │   ├── page.tsx       # Agent 列表
│   │   ├── new/           # 创建 Agent
│   │   └── [id]/          # Agent 详情和对话
│   ├── projects/          # 项目相关页面
│   │   ├── page.tsx       # 项目列表
│   │   └── [id]/          # 项目详情
│   ├── tools/             # 工具库
│   ├── analytics/         # 数据分析
│   └── settings/          # 设置
├── src/
│   ├── components/        # React 组件
│   │   ├── ui/           # 基础 UI 组件
│   │   └── layout/       # 布局组件
│   ├── hooks/            # React Query Hooks
│   ├── lib/              # 工具函数和 API 客户端
│   └── types/            # TypeScript 类型定义
├── tailwind.config.ts    # Tailwind 配置
├── tsconfig.json         # TypeScript 配置
└── package.json          # 依赖配置
```

## 页面说明

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘 - 平台概览、统计数据、快速操作 |
| `/agents` | Agent 列表 - 搜索、筛选、查看所有 Agent |
| `/agents/new` | 创建 Agent - 使用自然语言描述需求 |
| `/agents/[id]` | Agent 详情 - 配置、统计、会话历史 |
| `/agents/[id]/chat` | Agent 对话 - 与 Agent 进行对话 |
| `/projects` | 项目列表 - 查看所有构建项目 |
| `/projects/[id]` | 项目详情 - 构建进度、阶段时间线 |
| `/tools` | 工具库 - 浏览和管理可用工具 |
| `/analytics` | 数据分析 - 使用统计和趋势 |
| `/settings` | 设置 - 用户偏好和 API 配置 |

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 启动生产服务器
npm start
```

## 环境变量

```env
# API 基础 URL (可选，默认 http://localhost:8000)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## API 集成

前端通过 `/api/v1/*` 路径与后端 API 通信，主要端点包括：

- `GET /api/v1/agents` - 获取 Agent 列表
- `GET /api/v1/agents/:id` - 获取 Agent 详情
- `POST /api/v1/agents/:id/invoke` - 调用 Agent
- `GET /api/v1/projects` - 获取项目列表
- `GET /api/v1/projects/:id/build` - 获取构建仪表盘
- `POST /api/v1/projects` - 创建新项目
- `GET /api/v1/statistics/overview` - 获取统计概览

## 组件库

### UI 组件 (`src/components/ui/`)

- `Button` - 按钮组件，支持多种变体和尺寸
- `Card` - 卡片容器组件
- `Badge` - 标签/徽章组件
- `Input` - 输入框组件
- `Textarea` - 多行文本输入
- `Progress` - 进度条组件
- `Empty` - 空状态组件
- `Skeleton` - 加载骨架屏

### 布局组件 (`src/components/layout/`)

- `MainLayout` - 主布局容器
- `Sidebar` - 侧边导航栏
- `Header` - 页面头部

## 设计规范

- 主色调: Primary Blue (#3b82f6)
- 圆角: 使用 rounded-lg/xl 保持一致性
- 间距: 使用 Tailwind 的 4px 基准间距系统
- 动画: 使用 transition-all duration-200 保持流畅
