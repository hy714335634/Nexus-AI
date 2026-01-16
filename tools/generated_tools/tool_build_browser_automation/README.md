# 浏览器自动化工具集

> 集成Amazon Bedrock AgentCore、Nova Act和Browser Use的AI驱动浏览器自动化工具集

## 📋 概述

本工具集提供5个强大的浏览器自动化工具，支持：
- ✅ 自然语言指令驱动的网页交互
- ✅ AI智能决策和任务执行
- ✅ 实时浏览器视图监控
- ✅ 批量网页数据采集
- ✅ 完善的会话管理

## 🚀 核心功能

### 1. browser_with_nova_act
**基础Nova Act浏览器自动化**

使用Nova Act API通过CDP WebSocket连接执行自然语言指令，支持网页搜索、表单填写、数据提取等自动化任务。

**参数：**
- `prompt` (str, 必需): 自然语言浏览器操作指令
- `starting_page` (str, 必需): 起始URL地址
- `nova_act_key` (str, 必需): Nova Act API密钥
- `region` (str, 可选): AWS区域，默认'us-west-2'

**返回：**
```json
{
  "status": "success",
  "response": "操作完成",
  "data": {
    "response": "...",
    "status_code": 200,
    "screenshots": [...],
    "metadata": {...}
  }
}
```

**示例：**
```python
from browser_automation_tools import browser_with_nova_act

result = browser_with_nova_act(
    prompt="搜索'机器学习'并提取前5个结果的标题",
    starting_page="https://www.google.com",
    nova_act_key="your-api-key"
)
```

---

### 2. browser_with_live_view_nova
**Nova Act + 实时视图浏览器自动化**

在基础自动化功能基础上增加DCV实时浏览器查看功能，支持多种显示尺寸和手动控制。

**参数：**
- `prompt` (str, 必需): 自然语言浏览器操作指令
- `starting_page` (str, 必需): 起始URL地址
- `nova_act_key` (str, 必需): Nova Act API密钥
- `region` (str, 可选): AWS区域，默认'us-west-2'
- `viewer_port` (int, 可选): DCV viewer服务器端口，默认8000
- `display_size` (str, 可选): 显示尺寸（720p/900p/1080p/1440p），默认'900p'
- `open_browser` (bool, 可选): 是否自动打开浏览器查看，默认True

**返回：**
```json
{
  "status": "success",
  "response": "操作完成",
  "viewer_url": "http://localhost:8000",
  "data": {...}
}
```

**示例：**
```python
result = browser_with_live_view_nova(
    prompt="访问亚马逊首页并截图",
    starting_page="https://www.amazon.com",
    nova_act_key="your-api-key",
    display_size="1080p"
)
```

---

### 3. browser_with_live_view_use
**Browser Use AI驱动浏览器自动化**

使用browser-use库和Claude 3.5 Sonnet模型进行AI驱动的浏览器任务执行，支持复杂的多步骤任务。

**参数：**
- `task` (str, 必需): 自然语言任务描述
- `region` (str, 可选): AWS区域，默认'us-west-2'
- `viewer_port` (int, 可选): DCV viewer服务器端口，默认8000
- `open_browser` (bool, 可选): 是否自动打开浏览器查看，默认True
- `model_id` (str, 可选): Bedrock模型ID，默认'anthropic.claude-3-5-sonnet-20240620-v1:0'
- `timeout` (int, 可选): 浏览器超时时间（秒），默认1500

**返回：**
```json
{
  "status": "success",
  "task": "...",
  "viewer_url": "http://localhost:8000",
  "message": "任务执行成功"
}
```

**示例：**
```python
result = browser_with_live_view_use(
    task="在维基百科搜索'人工智能'并提取定义"
)
```

---

### 4. manage_browser_session
**浏览器会话管理器**

提供统一的浏览器会话创建、查询、销毁等操作。

**参数：**
- `action` (str, 必需): 操作类型
  - `create`: 创建新会话
  - `stop`: 停止会话
  - `get_ws_headers`: 获取WebSocket连接信息
  - `get_status`: 查询会话状态
  - `list_all`: 列出所有会话
- `region` (str, 可选): AWS区域，默认'us-west-2'
- `session_id` (str, 可选): 会话ID（create操作会自动生成）

**返回：**
```json
{
  "status": "success",
  "action": "create",
  "session_id": "xxx-xxx-xxx",
  "ws_url": "wss://...",
  "headers": {...}
}
```

**示例：**
```python
# 创建会话
result = manage_browser_session(action="create", region="us-west-2")

# 停止会话
result = manage_browser_session(action="stop", session_id="xxx-xxx-xxx")
```

---

### 5. batch_extract_from_urls
**批量网页数据采集**

批量从多个URL采集数据，支持并发控制和两种采集方法（Nova Act和Browser Use）。

**参数：**
- `urls` (str, 必需): 待采集的URL列表，JSON数组字符串格式
- `extraction_prompt` (str, 必需): 数据提取指令
- `method` (str, 可选): 采集方法（'nova_act'或'browser_use'），默认'browser_use'
- `nova_act_key` (str, 可选): Nova Act API密钥（method='nova_act'时必需）
- `region` (str, 可选): AWS区域，默认'us-west-2'
- `max_concurrent` (int, 可选): 最大并发数，默认3

**返回：**
```json
{
  "status": "success",
  "total": 10,
  "success": 9,
  "failed": 1,
  "results": [
    {
      "url": "https://example.com",
      "status": "success",
      "data": {...},
      "error": null
    }
  ]
}
```

**示例：**
```python
import json

urls = ["https://example1.com", "https://example2.com"]
result = batch_extract_from_urls(
    urls=json.dumps(urls),
    extraction_prompt="提取页面标题和描述",
    max_concurrent=2
)
```

---

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

**依赖包：**
- bedrock-agentcore >= 1.0.0
- nova-act >= 0.1.0
- browser-use >= 0.1.0
- langchain-aws >= 0.1.0
- boto3 >= 1.26.0
- rich >= 13.0.0
- playwright >= 1.40.0
- strands-core >= 1.0.0

**Playwright安装：**
```bash
playwright install
```

---

## 🔧 配置要求

### 1. AWS凭证配置
确保AWS凭证已配置（用于Bedrock和AgentCore）：

```bash
aws configure
```

或设置环境变量：
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2
```

### 2. Nova Act API密钥
获取Nova Act API密钥并在调用时传入。

### 3. Amazon DCV SDK
实时视图功能需要Amazon DCV SDK支持（可选）。

---

## 📚 使用场景

### 场景1: 自动化搜索和数据提取
```python
# 在Google搜索并提取结果
result = browser_with_nova_act(
    prompt="搜索'Python教程'并提取前10个结果的标题和链接",
    starting_page="https://www.google.com",
    nova_act_key="your-api-key"
)
```

### 场景2: 电商产品信息采集
```python
# 使用AI自动导航和提取产品信息
result = browser_with_live_view_use(
    task="""
    在亚马逊搜索'笔记本电脑'，然后：
    1. 提取前10个产品的名称、价格、评分
    2. 点击第一个产品查看详情
    3. 提取详细规格参数
    """
)
```

### 场景3: 批量网站监控
```python
import json

# 批量检查多个网站的可用性和响应时间
urls = [
    "https://www.example1.com",
    "https://www.example2.com",
    "https://www.example3.com"
]

result = batch_extract_from_urls(
    urls=json.dumps(urls),
    extraction_prompt="提取页面标题、加载时间和HTTP状态码",
    method="browser_use",
    max_concurrent=3
)
```

### 场景4: 表单自动填写和提交
```python
# 自动填写表单
result = browser_with_nova_act(
    prompt="""
    在表单中填写以下信息：
    - 姓名: 张三
    - 邮箱: zhangsan@example.com
    - 电话: 13800138000
    然后点击提交按钮
    """,
    starting_page="https://example.com/contact",
    nova_act_key="your-api-key"
)
```

---

## 🧪 测试

运行测试脚本：

```bash
python test_browser_automation.py
```

运行示例代码：

```bash
python examples.py
```

---

## ⚠️ 注意事项

1. **API密钥安全**
   - 不要在代码中硬编码API密钥
   - 使用环境变量或配置文件管理密钥

2. **并发限制**
   - 批量采集时注意并发数设置（默认3）
   - 过高的并发可能导致目标网站限流

3. **超时设置**
   - 复杂任务建议增加超时时间
   - 单个URL采集默认超时60秒

4. **资源管理**
   - 使用完会话后及时调用stop操作
   - 避免会话泄漏导致资源浪费

5. **实时视图**
   - 端口冲突时更换viewer_port参数
   - 批量操作时建议关闭自动打开浏览器

6. **错误处理**
   - 所有工具都返回JSON字符串格式
   - 检查返回结果的status字段判断成功或失败

---

## 🔄 错误处理

所有工具都返回统一的JSON格式：

**成功：**
```json
{
  "status": "success",
  ...
}
```

**错误：**
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "具体错误信息"
}
```

**错误类型：**
- `ValidationError`: 参数验证错误
- `ConnectionError`: 网络连接错误
- `TimeoutError`: 操作超时
- `APIError`: 外部API调用失败
- `ResourceError`: 资源不可用（如端口占用、会话不存在）

---

## 📖 API参考

详细的API文档请参考各工具函数的docstring：

```python
from browser_automation_tools import browser_with_nova_act
help(browser_with_nova_act)
```

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

本工具集遵循项目许可证。

---

## 🔗 相关链接

- [Amazon Bedrock AgentCore 文档](https://docs.aws.amazon.com/bedrock/)
- [Nova Act API 文档](https://nova-act.com/docs)
- [Browser Use 文档](https://github.com/browser-use/browser-use)
- [Strands SDK 文档](https://strands.dev/)

---

## 📞 支持

如有问题或建议，请联系项目维护者。

---

**最后更新：** 2026-01-12
**版本：** 1.0.0
