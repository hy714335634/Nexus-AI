# greeting_agent

## 项目描述
AI智能体项目：greeting_agent

## 项目结构
```
greeting_agent/
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

#### requirements_analyzer
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/greeting_agent/agents/requirements_analyzer/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/greeting_agent/agents/requirements_analyzer/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/greeting_agent/agents/requirements_analyzer/agent_designer.json)
- **prompt_engineer**: ⏳ 待完成
- **tools_developer**: ⏳ 待完成
- **agent_code_developer**: ✅ 已完成
- **agent_developer_manager**: ⏳ 待完成

## 附加信息


## 项目完成情况

### 开发阶段进度

| 阶段 | 状态 | 完成时间 | 说明 |
|------|------|---------|------|
| requirements_analyzer | ✅ 完成 | 03:26:36 | 需求分析和功能规格定义 |
| system_architect | ✅ 完成 | 03:28:34 | 系统架构设计和技术方案 |
| agent_designer | ✅ 完成 | 03:29:56 | Agent结构和交互模式设计 |
| prompt_engineer | ✅ 完成 | 03:30:44 | 业务规则和模板定义 |
| tools_developer | ✅ 完成 | 03:31:17 | 工具集开发规范和接口设计 |
| agent_code_developer | ✅ 完成 | 03:31:57 | Agent代码架构和实现指南 |
| agent_developer_manager | ✅ 完成 | 03:32:09 | 项目协调管理和交付 |

**总体进度: 7/7 (100%)**

## 功能概述

### 核心功能
- **基础问候功能**：根据用户名称生成个性化问候消息
- **时间感知问候**：根据当前时间段自动选择合适的问候语（早安、午安、晚安、通用）
- **多语言支持**：支持中文（zh）和英文（en）问候
- **RESTful API接口**：标准的HTTP API端点，支持GET和POST方法
- **健康检查端点**：监控服务可用性和性能指标
- **标准化响应**：统一的JSON响应格式
- **完善的错误处理**：清晰的错误提示和状态码
- **详细的日志记录**：结构化日志便于问题排查

### API端点

#### 问候端点
```
POST /api/greet
GET /api/greet?name=用户名&language=zh&timezone=Asia/Shanghai

请求示例：
{
  "name": "张三",
  "language": "zh",
  "timezone": "Asia/Shanghai"
}

响应示例（成功）：
{
  "status": "success",
  "message": "早上好，张三！",
  "data": {
    "greeting_type": "morning",
    "language": "zh",
    "timestamp": "2025-11-23T11:30:00+08:00",
    "processing_time_ms": 5.2
  }
}

响应示例（错误）：
{
  "status": "error",
  "error": "用户名称无效或超出长度限制",
  "error_code": "INVALID_NAME",
  "details": {
    "field": "name",
    "reason": "length exceeds maximum",
    "max_length": 50
  },
  "timestamp": "2025-11-23T11:30:00+08:00"
}
```

#### 健康检查端点
```
GET /health

响应示例：
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": "3h 25m 15s",
  "timestamp": "2025-11-23T11:30:00+08:00",
  "metrics": {
    "total_requests": 1024,
    "avg_response_time": 45.3
  }
}
```

## 技术架构

### 系统架构
```
客户端 HTTP 请求
  ↓
FastAPI 应用层
  ↓
路由分发 (routes.py)
  ↓
参数验证 (input_validator)
  ↓
业务逻辑层 (services.py)
  ├─ 时间处理 (time_processor)
  ├─ 问候生成 (greeting_generator)
  └─ 性能指标 (metrics_collector)
  ↓
响应格式化 (response_formatter)
  ↓
HTTP JSON 响应
```

### 核心组件

#### 1. 主应用 (main.py)
- FastAPI应用初始化
- 路由配置
- 中间件设置
- 全局异常处理
- 启动/关闭事件

#### 2. 数据模型 (models.py)
- GreetingRequest：问候请求模型
- GreetingResponse：成功响应模型
- ErrorResponse：错误响应模型
- HealthResponse：健康检查响应模型

#### 3. API路由 (routes.py)
- POST /api/greet：POST方法问候端点
- GET /api/greet：GET方法问候端点
- GET /health：健康检查端点

#### 4. 业务逻辑 (services.py)
- GreetingService：问候生成服务
- MetricsService：性能指标收集服务

#### 5. 工具层
- input_validator.py：参数验证
- time_processor.py：时间处理
- greeting_generator.py：问候生成
- response_formatter.py：响应格式化
- logger.py：日志记录
- metrics_collector.py：性能指标

## 配置和部署

### 环境要求
- Python 3.9+
- FastAPI 0.100+
- Uvicorn 0.23+
- 必要的Python包（见requirements.txt）

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境变量配置
```bash
export LOG_LEVEL=INFO
export SERVICE_VERSION=1.0.0
export TIMEZONE=UTC
export WORKERS=4
export PORT=8000
```

### 本地运行
```bash
# 开发模式（自动重载）
python -m uvicorn main:app --reload

# 生产模式
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker运行
```bash
# 构建镜像
docker build -t greeting-agent .

# 运行容器
docker run -p 8000:8000 greeting-agent

# 访问API文档
浏览器访问：http://localhost:8000/docs
```

## 性能指标

### 目标指标
- **平均响应时间**：<50ms
- **P95响应时间**：<100ms
- **支持的并发**：≥100 QPS
- **内存占用**：<200MB
- **启动时间**：<5秒
- **服务可用性**：99.9%

### 监控指标
- 总请求数
- 平均响应时间
- 最小/最大响应时间
- P95响应时间
- 当前QPS
- 错误率

## 测试

### 单元测试
- 参数验证逻辑测试
- 时间处理逻辑测试
- 问候生成逻辑测试
- 响应格式化测试
- 错误处理测试

### 集成测试
- 完整的API调用流程
- 不同时间段的问候生成
- 多语言问候测试
- 并发请求处理
- 健康检查功能

### 性能测试
- 单个请求响应时间
- P95响应时间验证
- 并发请求处理（100 QPS）
- 内存使用情况

## API文档

### 自动生成的文档
- **Swagger UI**：访问 http://localhost:8000/docs
- **ReDoc**：访问 http://localhost:8000/redoc
- **OpenAPI规范**：访问 http://localhost:8000/openapi.json

### 手动文档
- 详细的API使用指南
- 示例代码和请求样本
- 错误处理说明
- 性能优化建议

## 使用示例

### Python客户端
```python
import requests
import json

# 发送问候请求
url = "http://localhost:8000/api/greet"
data = {
    "name": "张三",
    "language": "zh",
    "timezone": "Asia/Shanghai"
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

### cURL命令
```bash
# POST请求
curl -X POST http://localhost:8000/api/greet \
  -H 'Content-Type: application/json' \
  -d '{"name": "张三", "language": "zh"}'

# GET请求
curl 'http://localhost:8000/api/greet?name=张三&language=zh'

# 健康检查
curl http://localhost:8000/health
```

### JavaScript客户端
```javascript
fetch('http://localhost:8000/api/greet', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: '张三',
    language: 'zh'
  })
})
.then(response => response.json())
.then(data => console.log(JSON.stringify(data, null, 2)))
```

## 文件结构

```
projects/greeting_agent/
├── agents/
│   ├── requirements_analyzer/
│   │   ├── requirements_analyzer.json         # 需求分析文档
│   │   ├── system_architect.json             # 系统架构设计
│   │   ├── agent_designer.json               # Agent设计
│   │   ├── prompt_engineer.json              # 业务规则定义
│   │   ├── tools_developer.json              # 工具开发规范
│   │   └── agent_code_developer.json         # Agent代码实现
│   └── generated_agents/
│       └── greeting_agent/
│           ├── main.py                       # 应用主入口
│           ├── models.py                     # Pydantic数据模型
│           ├── routes.py                     # API路由定义
│           ├── services.py                   # 业务逻辑层
│           ├── config.py                     # 配置管理
│           ├── middleware.py                 # 中间件
│           └── __init__.py                   # 包初始化
├── tools/
│   └── generated_tools/
│       ├── input_validator.py                # 参数验证工具
│       ├── time_processor.py                 # 时间处理工具
│       ├── greeting_generator.py             # 问候生成工具
│       ├── response_formatter.py             # 响应格式化工具
│       ├── logger.py                         # 日志记录工具
│       └── metrics_collector.py              # 性能指标工具
├── prompts/
│   └── generated_agents_prompts/
│       └── greeting_rules_and_templates.yaml # 业务规则和模板
├── config.yaml                               # 项目配置
├── requirements.txt                          # Python依赖
├── README.md                                 # 项目说明（本文档）
└── status.yaml                               # 项目状态追踪
```

## 开发文档

### 设计文档位置
- **需求分析**：`projects/greeting_agent/agents/requirements_analyzer/requirements_analyzer.json`
- **系统架构**：`projects/greeting_agent/agents/requirements_analyzer/system_architect.json`
- **Agent设计**：`projects/greeting_agent/agents/requirements_analyzer/agent_designer.json`
- **业务规则**：`projects/greeting_agent/agents/requirements_analyzer/prompt_engineer.json`
- **工具开发**：`projects/greeting_agent/agents/requirements_analyzer/tools_developer.json`
- **代码开发**：`projects/greeting_agent/agents/requirements_analyzer/agent_code_developer.json`

## 后续开发建议

### 短期优化（Phase 2）
1. 实现实际的Python代码文件
2. 进行单元测试和集成测试
3. 进行性能测试，验证响应时间指标
4. 编写详细的API文档和使用指南

### 中期扩展（Phase 3）
1. 添加更多语言支持
2. 实现自定义问候模板功能
3. 添加用户认证和授权
4. 实现请求限流和防护

### 长期规划（Phase 4）
1. 与监控系统集成（Prometheus/Grafana）
2. 实现分布式追踪（OpenTelemetry）
3. 构建微服务架构中的一部分
4. 提供SDK和客户端库

## 注意事项

1. **时间处理**：默认使用服务器时间，可通过timezone参数指定用户时区
2. **性能要求**：P95响应时间<100ms是严格要求，需要进行性能测试验证
3. **并发处理**：使用FastAPI的异步特性支持高并发
4. **日志记录**：使用结构化日志便于日志聚合和分析
5. **错误处理**：所有错误都返回标准化的错误响应格式

## 联系和支持

如有问题或建议，请参考设计文档或联系项目维护者。

---

**项目状态**: ✅ 设计完成  
**最后更新**: 2025-11-23  
**版本**: 1.0.0

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。


## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-11-23 03:32:47 UTC*
