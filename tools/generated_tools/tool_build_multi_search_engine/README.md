# Multi Search Engine Tool

## 概述

**Multi Search Engine Tool** 是一个通用的多搜索引擎访问工具，为Agent提供统一的搜索接口，支持国内外主流搜索引擎。工具能够自动适配网络环境，智能选择最佳搜索引擎，并对搜索结果进行标准化处理，确保Agent在中国境内和海外都能获得高质量的搜索服务。

**版本**: 1.0.0  
**状态**: 生产就绪（建议补充单元测试）

---

## 功能特性

### ✨ 核心功能

- **🌐 多搜索引擎支持**
  - 国内：百度、搜狗、360搜索
  - 海外：Google、Bing、DuckDuckGo
  - 统一的搜索接口，屏蔽底层差异

- **🎯 智能环境适配**
  - 自动检测网络环境
  - 根据地区和语言偏好选择最佳引擎
  - 并发测试引擎可用性和响应时间
  - 搜索失败自动切换备用引擎（最多3次）

- **📊 结果标准化**
  - 统一不同搜索引擎的返回格式
  - 标准字段：标题、链接、摘要、排名、来源
  - 支持3种输出格式：JSON、Markdown、纯文本

- **🔍 高级过滤和排序**
  - 关键词过滤（包含/排除）
  - URL自动去重
  - 多种排序方式（相关性/日期/随机）
  - 详细的过滤统计信息

- **🏥 健康检查**
  - 批量检查搜索引擎可用性
  - 返回响应时间和错误信息
  - 用于系统监控和问题诊断

- **🔄 高可用性设计**
  - User-Agent轮换机制
  - 指数退避重试策略
  - 完善的错误处理和日志记录
  - 可配置的超时时间

---

## 安装

### 依赖要求

```bash
pip install requests>=2.31.0 beautifulsoup4>=4.12.0 lxml>=4.9.0 urllib3>=2.0.0 fake-useragent>=1.4.0
```

### 完整安装

```bash
cd tools/generated_tools/tool_build_multi_search_engine
pip install -r requirements.txt
```

### 依赖说明

| 包名 | 版本 | 用途 |
|-----|------|------|
| requests | ≥2.31.0 | HTTP请求库 |
| beautifulsoup4 | ≥4.12.0 | HTML解析 |
| lxml | ≥4.9.0 | 高性能解析器 |
| urllib3 | ≥2.0.0 | 连接池和重试 |
| fake-useragent | ≥1.4.0 | User-Agent轮换 |
| python-dotenv | ≥1.0.0 | 环境变量管理（可选） |
| httpx | ≥0.24.0 | 异步HTTP支持（可选） |

---

## 使用方法

### 快速开始

```python
from tools.generated_tools.tool_build_multi_search_engine.multi_search_engine import search

# 基本搜索（自动选择最佳引擎）
result = search(query="人工智能", num_results=5)
print(result)
```

---

## API 文档

### 1. search - 统一搜索接口

**描述**: 统一的搜索接口，支持多个搜索引擎，自动适配网络环境。

#### 参数

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| query | str | ✅ | - | 搜索关键词或查询语句 |
| engine | str | ❌ | "auto" | 指定搜索引擎（baidu/sogou/so360/google/bing/duckduckgo/auto） |
| num_results | int | ❌ | 10 | 返回的搜索结果数量，范围1-20 |
| language | str | ❌ | "auto" | 搜索结果语言偏好（zh-CN/en-US/auto） |
| region | str | ❌ | "auto" | 地区提示（china/overseas/auto） |
| timeout | int | ❌ | 15 | 搜索超时时间（秒），范围5-30 |
| format | str | ❌ | "json" | 输出格式（json/markdown/text） |
| include_metadata | bool | ❌ | true | 是否包含元数据 |

#### 返回值

**JSON格式** (format="json"):
```json
{
  "status": "success",
  "engine_used": "baidu",
  "query": "人工智能",
  "results": [
    {
      "title": "人工智能_百度百科",
      "url": "https://baike.baidu.com/item/人工智能",
      "snippet": "人工智能是计算机科学的一个分支...",
      "rank": 1,
      "source": "baidu"
    }
  ],
  "total_results": 10,
  "metadata": {
    "search_time_ms": 235,
    "timestamp": "2026-01-31T16:00:00Z"
  }
}
```

**错误格式**:
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "搜索关键词不能为空"
}
```

#### 使用示例

**示例1: 基本搜索（自动选择引擎）**
```python
result = search(query="机器学习", num_results=5)
```

**示例2: 指定搜索引擎**
```python
result = search(query="deep learning", engine="google", num_results=10)
```

**示例3: 中国地区优先**
```python
result = search(
    query="深度学习教程",
    engine="auto",
    region="china",
    language="zh-CN",
    num_results=10
)
```

**示例4: Markdown格式输出**
```python
result = search(
    query="Python教程",
    engine="baidu",
    format="markdown",
    num_results=5
)
```

**示例5: 海外搜索**
```python
result = search(
    query="artificial intelligence",
    engine="auto",
    region="overseas",
    language="en-US",
    num_results=10
)
```

---

### 2. check_engine_health - 健康检查

**描述**: 检查搜索引擎的可用性和响应时间，支持批量检查或指定引擎检查。

#### 参数

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| engines | str | ❌ | "" | 需要检查的引擎列表（JSON数组字符串），为空时检查所有引擎 |
| check_timeout | int | ❌ | 5 | 每个引擎的检查超时时间（秒） |

#### 返回值

```json
{
  "status": "success",
  "check_time": "2026-01-31T16:00:00Z",
  "total_engines": 6,
  "available_engines": 4,
  "unavailable_engines": 2,
  "engines_status": [
    {
      "engine": "baidu",
      "available": true,
      "response_time_ms": 150,
      "error": null
    },
    {
      "engine": "google",
      "available": false,
      "response_time_ms": -1,
      "error": "Connection timeout"
    }
  ]
}
```

#### 使用示例

**示例1: 检查所有引擎**
```python
from tools.generated_tools.tool_build_multi_search_engine.multi_search_engine import check_engine_health

result = check_engine_health()
```

**示例2: 检查指定引擎**
```python
result = check_engine_health(engines='["baidu", "google", "bing"]', check_timeout=3)
```

**示例3: 快速检查（短超时）**
```python
result = check_engine_health(check_timeout=2)
```

---

### 3. filter_and_sort_results - 过滤和排序

**描述**: 对搜索结果进行过滤和自定义排序。

#### 参数

| 参数名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| results_json | str | ✅ | - | 待处理的搜索结果JSON字符串 |
| filter_keywords | str | ❌ | "" | 过滤关键词列表（JSON数组） |
| exclude_keywords | str | ❌ | "" | 排除关键词列表（JSON数组） |
| sort_by | str | ❌ | "relevance" | 排序方式（relevance/date/random） |
| deduplicate | bool | ❌ | true | 是否去除重复结果 |

#### 返回值

```json
{
  "status": "success",
  "original_count": 50,
  "filtered_count": 10,
  "removed_by_filter": 30,
  "removed_by_exclude": 5,
  "removed_by_dedup": 5,
  "results": [
    {
      "title": "...",
      "url": "...",
      "snippet": "...",
      "rank": 1,
      "source": "baidu"
    }
  ]
}
```

#### 使用示例

**示例1: 关键词过滤**
```python
from tools.generated_tools.tool_build_multi_search_engine.multi_search_engine import search, filter_and_sort_results

# 先搜索
search_result = search(query="机器学习", num_results=20)

# 过滤包含特定关键词的结果
filtered = filter_and_sort_results(
    results_json=search_result,
    filter_keywords='["深度学习", "神经网络"]',
    deduplicate=True
)
```

**示例2: 排除广告**
```python
filtered = filter_and_sort_results(
    results_json=search_result,
    exclude_keywords='["广告", "推广", "赞助"]',
    deduplicate=True
)
```

**示例3: 随机排序**
```python
filtered = filter_and_sort_results(
    results_json=search_result,
    sort_by="random",
    deduplicate=True
)
```

**示例4: 组合过滤**
```python
filtered = filter_and_sort_results(
    results_json=search_result,
    filter_keywords='["Python", "教程"]',
    exclude_keywords='["视频", "付费"]',
    sort_by="relevance",
    deduplicate=True
)
```

---

## 架构设计

### 模块结构

```
tool_build_multi_search_engine/
├── multi_search_engine.py      # 主工具文件（3个@tool函数）
├── engine_adapters.py          # 搜索引擎适配器（6个引擎）
├── environment_detector.py     # 环境检测模块
├── result_formatter.py         # 结果格式化模块
├── utils.py                    # 工具函数模块
├── exceptions.py               # 自定义异常类
├── __init__.py                 # 包初始化文件
├── requirements.txt            # 依赖包列表
├── README.md                   # 使用文档
└── tool_config.json            # 工具配置文件
```

### 设计模式

- **适配器模式**: 统一不同搜索引擎的接口
- **策略模式**: 根据region和language选择最佳引擎
- **装饰器模式**: retry_on_failure重试装饰器

### 核心算法

**智能引擎选择算法**:
1. 如果region为"china"，优先选择国内引擎（baidu/sogou/so360）
2. 如果region为"overseas"，优先选择海外引擎（google/bing/duckduckgo）
3. 如果region为"auto"：
   - 并发测试所有引擎的可达性（超时3秒）
   - 选择响应时间最快且可用的引擎
   - 如果language为"zh-CN"，优先国内引擎
   - 如果language为"en-US"，优先海外引擎

---

## 使用场景

### 场景1: Agent需要搜索最新技术资料

```python
# Agent在中国境内，需要搜索中文技术资料
result = search(
    query="Transformer模型原理",
    engine="auto",
    region="china",
    language="zh-CN",
    num_results=10
)
```

### 场景2: Agent需要查找英文学术论文

```python
# Agent需要搜索海外学术资源
result = search(
    query="transformer architecture paper",
    engine="google",
    region="overseas",
    language="en-US",
    num_results=15
)
```

### 场景3: 系统启动时健康检查

```python
# 检查所有搜索引擎的可用性
health_status = check_engine_health()

# 解析结果，选择可用的引擎
import json
status = json.loads(health_status)
available_engines = [
    e["engine"] for e in status["engines_status"] 
    if e["available"]
]
print(f"可用的搜索引擎: {available_engines}")
```

### 场景4: 搜索结果精细化处理

```python
# 搜索Python相关内容
search_result = search(query="Python编程", num_results=50)

# 过滤出包含"教程"的结果，排除"视频"
filtered = filter_and_sort_results(
    results_json=search_result,
    filter_keywords='["教程", "入门"]',
    exclude_keywords='["视频", "付费"]',
    sort_by="relevance",
    deduplicate=True
)
```

### 场景5: 跨引擎结果聚合

```python
# 从多个引擎搜索并聚合结果
import json

engines = ["baidu", "google", "bing"]
all_results = []

for engine in engines:
    result = search(query="深度学习", engine=engine, num_results=5)
    data = json.loads(result)
    if data.get("status") == "success":
        all_results.extend(data.get("results", []))

# 去重和排序
aggregated = filter_and_sort_results(
    results_json=json.dumps({"results": all_results}),
    deduplicate=True,
    sort_by="relevance"
)
```

---

## 错误处理

工具实现了完善的错误处理机制，所有错误都返回友好的JSON格式错误信息：

### 常见错误类型

| 错误类型 | 触发条件 | 示例 |
|---------|---------|------|
| ValidationError | 参数验证失败 | 空查询、无效引擎、结果数量超出范围 |
| EngineUnavailableError | 搜索引擎不可用 | 网络连接失败、超时 |
| ParseError | 结果解析失败 | HTML结构变化、编码错误 |
| JSONDecodeError | JSON解析失败 | 无效的JSON字符串参数 |

### 错误示例

```python
# 空查询错误
result = search(query="")
# 返回: {"status": "error", "error_type": "ValidationError", "message": "搜索关键词不能为空"}

# 无效引擎错误
result = search(query="test", engine="invalid_engine")
# 返回: {"status": "error", "error_type": "ValidationError", "message": "不支持的搜索引擎: invalid_engine"}

# 结果数量超出范围
result = search(query="test", num_results=100)
# 返回: {"status": "error", "error_type": "ValidationError", "message": "num_results必须在1-20之间"}
```

---

## 注意事项

### ⚠️ 重要提示

1. **遵守服务条款**: 必须遵守各搜索引擎的服务条款和robots.txt规则
2. **访问频率限制**: 建议实现请求频率限制，避免被搜索引擎封禁
3. **代理配置**: 如需访问海外搜索引擎，可能需要配置代理
4. **HTML结构变化**: 搜索引擎的HTML结构可能会变化，需要定期更新选择器
5. **反爬虫机制**: 某些搜索引擎有反爬虫机制，工具已实现User-Agent轮换

### 🔧 配置建议

1. **生产环境超时**: 建议设置timeout为10-20秒
2. **日志级别**: 可以通过环境变量配置日志级别
3. **定期健康检查**: 建议定期运行health check，监控搜索引擎可用性
4. **缓存机制**: 可以考虑实现搜索结果缓存，提高重复查询的响应速度

### 📝 已知限制

1. 搜索引擎的HTML结构可能会变化，需要定期更新选择器
2. 免费搜索方式受限于搜索引擎的访问限制
3. 日期排序功能当前为简化实现（保持原序）
4. 不支持高级搜索语法（如site:、filetype:等）

---

## 性能优化

### 并发性能

- 健康检查使用线程池并发（最大并发6）
- 搜索失败自动切换备用引擎
- 指数退避重试策略

### 响应时间

- 可配置的超时时间（5-30秒）
- 记录搜索耗时，便于性能监控
- 建议实现搜索结果缓存（未来增强）

### 资源使用

- 线程池限制最大并发数，避免资源耗尽
- User-Agent轮换，避免被封禁
- 完善的日志记录，便于调试和监控

---

## 测试建议

### 单元测试用例（建议编写）

1. **基本功能测试**
   - test_basic_search_baidu: 测试百度基本搜索
   - test_basic_search_google: 测试Google基本搜索
   - test_auto_engine_selection: 测试自动引擎选择

2. **环境适配测试**
   - test_region_china: 测试中国地区优先
   - test_region_overseas: 测试海外地区优先
   - test_language_preference: 测试语言偏好

3. **健康检查测试**
   - test_health_check_all: 测试所有引擎健康检查
   - test_health_check_specific: 测试指定引擎健康检查

4. **过滤和排序测试**
   - test_filter_with_keywords: 测试关键词过滤
   - test_exclude_keywords: 测试排除关键词
   - test_deduplicate: 测试去重功能

5. **格式化测试**
   - test_markdown_format: 测试Markdown输出
   - test_text_format: 测试纯文本输出

6. **错误处理测试**
   - test_empty_query_error: 测试空查询错误
   - test_invalid_engine_error: 测试无效引擎错误
   - test_timeout_handling: 测试超时处理

---

## 未来增强

### 计划中的功能

1. **更多搜索引擎**: Yandex、Yahoo等
2. **搜索结果缓存**: 使用Redis或本地缓存
3. **异步搜索**: 使用httpx或aiohttp提高并发性能
4. **高级搜索语法**: 支持site:、filetype:等语法
5. **智能结果聚合**: 从多个引擎聚合结果
6. **多媒体搜索**: 支持图片、视频搜索
7. **更智能的日期排序**: 从snippet中提取日期

---

## 贡献和反馈

如有问题或建议，请通过以下方式反馈：
- 提交Issue
- 提交Pull Request
- 联系开发团队

---

## 许可证

本工具遵循项目许可证。

---

## 版本历史

### v1.0.0 (2026-01-31)
- ✅ 初始版本发布
- ✅ 支持6个搜索引擎（百度、搜狗、360、Google、Bing、DuckDuckGo）
- ✅ 实现智能环境适配和自动引擎选择
- ✅ 实现结果标准化和多格式输出
- ✅ 实现健康检查功能
- ✅ 实现结果过滤和排序功能
- ✅ 完善的错误处理和日志记录

---

## 联系方式

**开发团队**: Nexus-AI Tool Build Workflow  
**项目地址**: `tools/generated_tools/tool_build_multi_search_engine/`  
**文档版本**: 1.0.0  
**最后更新**: 2026-01-31
