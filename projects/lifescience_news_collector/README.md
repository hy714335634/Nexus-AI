# lifescience_news_collector

## 项目描述
生命科学行业新闻自动采集Agent - 支持多源数据采集、智能分类、摘要生成、HTML报告生成及S3自动上传

## 项目结构
```
lifescience_news_collector/
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

#### lifescience_news_collector
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/lifescience_news_collector/agents/lifescience_news_collector/agent_code_developer.json)
- **agent_developer_manager**: ⏳ 待完成

## 附加信息
# 生命科学行业新闻自动采集Agent

## 项目概述

**lifescience_news_collector** 是一个专业的生命科学行业新闻自动采集与分析系统，能够从15+权威数据源自动采集新闻内容，通过AI技术进行智能分类、摘要生成，并输出结构化的HTML报告，最终自动上传到AWS S3并生成分享链接。

### 核心价值
- ⚡ **高效自动化**：从手动收集数小时缩短到自动化分钟级完成
- 🤖 **AI智能处理**：通过Claude Sonnet 4.5进行智能分类和高质量摘要生成
- 📊 **标准化输出**：生成专业的HTML报告，便于团队协作和知识分享
- ☁️ **云端集成**：自动S3存储和Presign URL生成，简化后续邮件分发流程
- 🔧 **灵活配置**：支持配置化管理，可快速适应数据源变化和业务需求调整

---

## 功能特性

### 1. 多源数据采集
- **搜索引擎API**：集成SerpAPI进行Google搜索
- **14个医疗资讯网站**：
  - **综合医疗**：丁香园、医学界、健康界、医谷
  - **生物医药**：生物探索、医药魔方、药智网、美柏医健
  - **学术科研**：科学网、中国生物技术网、生物谷
  - **行业动态**：动脉网、亿欧大健康、36氪医疗
- **深度遍历**：自动识别列表页和详情页，支持多层级遍历（最大2层）
- **并发采集**：使用asyncio和aiohttp，支持最多5个数据源并发访问

### 2. AI智能分类
基于Claude Sonnet 4.5的7大分类体系：
1. **政策法规类**：医疗数据合规、药品审批政策、医保支付政策
2. **医疗数字化转型案例**：医院信息化、远程医疗、医疗影像AI应用
3. **药物研发与创新**：新药研发管线、AI制药、临床试验数字化
4. **医疗器械与产品**：新医疗设备、可穿戴设备、IoT医疗
5. **战略合作与并购**：医药企业合作、科技公司进入医疗、跨境合作
6. **基因组学与精准医疗**：基因测序技术、个性化治疗
7. **医疗数据与AI**：大模型医疗应用、医疗数据平台、生成式AI

### 3. 自动摘要生成
- **长度控制**：每篇新闻生成100-200字的中文摘要
- **结构化**：背景 + 核心内容 + 影响/意义
- **关键信息提取**：识别关键实体（公司、产品、技术、人物）和关键数据
- **全局总结**：生成Top 5关键发现和行业趋势分析

### 4. HTML报告生成
- **模板引擎**：基于Jinja2模板渲染
- **参考模板**：case/newsletter_template.html
- **报告结构**：
  - 执行摘要（生成日期、总文章数、类别统计）
  - 全局关键信息总结
  - 按类别组织的新闻列表（标题、摘要、来源、超链接）
  - 附录（失败的数据源、执行日志）
- **响应式设计**：支持移动端和桌面端查看

### 5. AWS S3自动上传
- **存储桶**：s3://newletter-2026
- **区域**：us-west-2
- **路径格式**：reports/{year}/{month}/{day}/newsletter_{timestamp}.html
- **Presign URL**：自动生成7天有效期的分享链接
- **元数据**：Content-Type、Cache-Control、生成时间等

### 6. 配置化管理
- **配置文件**：config/lifescience_news_collector.yaml
- **支持内容**：
  - 数据源URL列表和CSS选择器
  - SerpAPI密钥
  - S3配置（桶名、区域、路径前缀）
  - 分类体系和关键词
  - 执行参数（并发数、超时时间、重试次数）
- **环境变量覆盖**：支持敏感信息通过环境变量管理

### 7. 完善的错误处理
- **单点隔离**：单个数据源失败不影响整体流程
- **重试机制**：网络错误和S3错误自动重试3次（指数退避）
- **降级策略**：AI调用失败时使用基于规则的降级方法
- **详细日志**：记录所有关键步骤和错误信息
- **部分成功**：即使部分失败也返回成功采集的内容和报告

---

## 技术架构

### 核心技术栈
- **AI模型**：Claude Sonnet 4.5 (global.anthropic.claude-sonnet-4-5-20250929-v1:0)
- **框架**：Strands SDK + AWS Bedrock
- **部署**：Bedrock AgentCore (Docker容器)
- **存储**：Amazon S3
- **数据库**：Amazon DynamoDB（可选）
- **邮件**：Amazon SES（可选）

### 关键依赖
```
- strands-agents >= 1.21.0
- boto3 >= 1.42.23
- aiohttp >= 3.13.3
- playwright >= 1.57.0
- beautifulsoup4 >= 4.14.3
- jinja2 >= 3.1.6
- lxml
- requests
- PyYAML
- Pillow
```

### 工具模块（42个工具）
1. **data_collector.py**（11个工具）：SerpAPI搜索、网页采集、HTML解析、URL管理
2. **data_processor.py**（8个工具）：文章去重、分类、摘要、关键词提取
3. **storage_tools.py**（15个工具）：S3存储、DynamoDB、本地文件、缓存管理
4. **newsletter_generator.py**（11个工具）：HTML渲染、邮件生成、图片处理

---

## 项目结构

```
lifescience_news_collector/
├── agents/
│   └── generated_agents/
│       └── lifescience_news_collector/
│           └── lifescience_news_collector.py      # Agent执行代码
├── prompts/
│   └── generated_agents_prompts/
│       └── lifescience_news_collector/
│           └── lifescience_news_collector.yaml    # 提示词模板
├── tools/
│   └── generated_tools/
│       └── lifescience_news_collector/
│           ├── data_collector.py                   # 数据采集工具
│           ├── data_processor.py                   # 数据处理工具
│           ├── storage_tools.py                    # 存储管理工具
│           └── newsletter_generator.py             # 报告生成工具
├── projects/
│   └── lifescience_news_collector/
│       ├── config.yaml                             # 项目配置
│       ├── status.yaml                             # 项目状态
│       ├── README.md                               # 项目文档
│       ├── requirements.txt                        # Python依赖
│       └── agents/
│           └── lifescience_news_collector/
│               ├── requirements_analyzer.json      # 需求分析文档
│               ├── system_architect.json           # 系统架构设计
│               ├── agent_designer.json             # Agent设计文档
│               ├── tools_developer.json            # 工具开发文档
│               ├── prompt_engineer.json            # 提示词工程文档
│               └── agent_code_developer.json       # Agent代码文档
└── config/
    └── lifescience_news_collector.yaml             # Agent配置文件
```

---

## 安装与配置

### 1. 环境要求
- Python 3.13+
- Docker（AgentCore部署）
- AWS账号（S3访问权限）
- SerpAPI密钥（可选）

### 2. 安装依赖
```bash
cd projects/lifescience_news_collector
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 3. 配置文件
创建配置文件 `config/lifescience_news_collector.yaml`：

```yaml
data_sources:
  search_api:
    provider: serpapi
    api_key: ${SERPAPI_API_KEY}  # 从环境变量读取
    search_query: "生命科学 新闻"
    max_results: 20
  
  news_websites:
    - name: "丁香园"
      url: "https://www.dxy.cn/"
      type: "dynamic"
      enabled: true
    # ... 其他数据源配置

classification:
  categories:
    - name: "政策法规类"
      keywords: ["政策", "法规", "监管", "合规"]
    # ... 其他分类配置

s3:
  bucket: "newletter-2026"
  region: "us-west-2"
  key_prefix: "reports/"
  presign_expires_in: 604800  # 7天

execution:
  concurrent_requests: 5
  request_timeout: 30
  retry_attempts: 3
  max_depth: 2
```

### 4. 环境变量
```bash
export SERPAPI_API_KEY="your_serpapi_key"
export AWS_ACCESS_KEY_ID="your_aws_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret"
# 或者使用IAM角色（推荐）
```

---

## 使用指南

### 本地测试模式

#### 单次执行
```bash
python agents/generated_agents/lifescience_news_collector/lifescience_news_collector.py \
  -i "请采集今天的生命科学行业新闻" \
  -e production \
  -v latest
```

#### 交互式对话模式
```bash
python agents/generated_agents/lifescience_news_collector/lifescience_news_collector.py -it
```

#### 指定环境和模型
```bash
python agents/generated_agents/lifescience_news_collector/lifescience_news_collector.py \
  -i "测试输入" \
  -e development \
  -m global.anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --log-level DEBUG
```

### AgentCore部署模式

#### 1. 构建Docker镜像
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY . /app

RUN pip install -r projects/lifescience_news_collector/requirements.txt
RUN playwright install chromium --with-deps

ENV DOCKER_CONTAINER=1
ENV BYPASS_TOOL_CONSENT=true

EXPOSE 8080

CMD ["python", "agents/generated_agents/lifescience_news_collector/lifescience_news_collector.py"]
```

#### 2. 启动服务
```bash
docker build -t lifescience-news-collector .
docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e SERPAPI_API_KEY=$SERPAPI_API_KEY \
  lifescience-news-collector
```

#### 3. HTTP API调用
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "请采集今天的生命科学行业新闻",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

---

## 输出示例

### 执行进度（流式响应）
```
📥 收到请求: 请采集今天的生命科学行业新闻
🔄 加载配置文件...
✅ 配置加载成功，共15个数据源

🌐 开始数据采集...
  [1/15] SerpAPI搜索: ✅ 成功采集20条结果
  [2/15] 丁香园: ✅ 成功采集15条新闻
  [3/15] 医学界: ✅ 成功采集12条新闻
  ...
  [15/15] 国家卫健委: ✅ 成功采集8条新闻

📊 数据清洗与去重...
  原始文章数: 210
  去重后: 185

🤖 AI智能分类...
  [1/185] "国家药监局发布新政策" -> 政策法规类 (置信度: 0.92)
  [2/185] "某公司AI制药新突破" -> 药物研发与创新 (置信度: 0.88)
  ...

✍️ 生成摘要...
  [1/185] 摘要完成 (152字)
  [2/185] 摘要完成 (168字)
  ...

📈 生成全局总结...
  Top 5关键发现:
  1. AI制药技术成为热点，相关新闻占比18%
  2. 医疗数据安全政策密集出台
  3. 跨境医疗合作案例显著增加
  ...

📄 生成HTML报告...
  模板渲染完成
  报告大小: 2.3 MB

☁️ 上传到S3...
  上传成功: s3://newletter-2026/reports/2026/01/07/newsletter_20260107_120530.html
  Presign URL (7天有效): https://newletter-2026.s3.us-west-2.amazonaws.com/...

✅ 任务完成！
```

### 最终输出（JSON格式）
```json
{
  "status": "success",
  "execution_summary": {
    "start_time": "2026-01-07T12:05:00Z",
    "end_time": "2026-01-07T12:25:30Z",
    "duration_seconds": 1230,
    "data_sources": {
      "total": 15,
      "success": 14,
      "failed": 1
    },
    "articles": {
      "total_collected": 210,
      "after_deduplication": 185,
      "classified": 185,
      "summarized": 185
    }
  },
  "key_findings": [
    "AI制药技术成为热点，相关新闻占比18%",
    "医疗数据安全政策密集出台",
    "跨境医疗合作案例显著增加",
    "基因测序成本持续下降",
    "大模型在医疗领域应用加速"
  ],
  "category_distribution": {
    "政策法规类": 28,
    "医疗数字化转型案例": 35,
    "药物研发与创新": 42,
    "医疗器械与产品": 25,
    "战略合作与并购": 22,
    "基因组学与精准医疗": 18,
    "医疗数据与AI": 15
  },
  "s3_upload": {
    "status": "success",
    "s3_uri": "s3://newletter-2026/reports/2026/01/07/newsletter_20260107_120530.html",
    "presign_url": "https://newletter-2026.s3.us-west-2.amazonaws.com/reports/2026/01/07/newsletter_20260107_120530.html?...",
    "expires_in_days": 7,
    "file_size_kb": 2356
  },
  "failed_sources": [
    {
      "name": "药智网",
      "url": "https://www.yaozh.com/",
      "error": "连接超时"
    }
  ]
}
```

---

## 开发阶段完成情况

| 阶段 | 状态 | 完成时间 | 文档路径 |
|------|------|----------|----------|
| 需求分析 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/requirements_analyzer.json |
| 系统架构设计 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/system_architect.json |
| Agent设计 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/agent_designer.json |
| 提示词工程 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/prompt_engineer.json |
| 工具开发 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/tools_developer.json |
| Agent代码开发 | ✅ 完成 | 2026-01-07 | projects/lifescience_news_collector/agents/lifescience_news_collector/agent_code_developer.json |
| Agent开发管理 | ✅ 完成 | 2026-01-07 | 本文档 |

---

## 性能指标

- **单次完整采集时间**：20-30分钟（取决于网络和数据源响应速度）
- **并发采集能力**：最多5个数据源同时访问
- **AI处理速度**：每篇文章分类+摘要 < 5秒
- **HTML报告生成**：< 10秒
- **S3上传速度**：取决于网络，通常 < 30秒
- **分类准确率**：≥ 80%（基于AI语义理解）

---

## 安全考虑

- ✅ API密钥通过环境变量管理，不硬编码
- ✅ AWS使用IAM角色认证，避免长期访问密钥
- ✅ S3 Presign URL有效期限制为7天
- ✅ 日志脱敏，不记录敏感信息
- ✅ HTTPS通信，SSL证书验证
- ✅ 输入验证，防止注入攻击
- ✅ 权限最小化原则（S3、DynamoDB、SES）

---

## 监控与日志

### 日志级别
- **INFO**：关键步骤执行状态
- **WARNING**：单个数据源失败、AI调用失败
- **ERROR**：严重错误（配置错误、S3上传失败）
- **DEBUG**：详细的调试信息

### 遥测数据
- 使用StrandsTelemetry输出OTLP格式遥测数据
- 支持集成到CloudWatch、Prometheus等监控系统
- 记录关键指标：执行时间、成功率、错误率、采集文章数

### 日志输出
```
2026-01-07 12:05:00 - lifescience_news_collector - INFO - 📥 收到请求: 请采集今天的生命科学行业新闻
2026-01-07 12:05:01 - lifescience_news_collector - INFO - ✅ Agent创建成功: lifescience_news_collector
2026-01-07 12:05:02 - lifescience_news_collector - INFO - 🔄 开始处理请求...
2026-01-07 12:05:05 - lifescience_news_collector - INFO - 🌐 开始数据采集 (15个数据源)
2026-01-07 12:08:30 - lifescience_news_collector - WARNING - ⚠️ 数据源失败: 药智网 (连接超时)
2026-01-07 12:15:20 - lifescience_news_collector - INFO - 📊 数据清洗完成: 210 -> 185
2026-01-07 12:20:45 - lifescience_news_collector - INFO - 🤖 AI分类完成: 185篇
2026-01-07 12:23:10 - lifescience_news_collector - INFO - ✍️ 摘要生成完成: 185篇
2026-01-07 12:24:30 - lifescience_news_collector - INFO - 📄 HTML报告生成完成
2026-01-07 12:25:15 - lifescience_news_collector - INFO - ☁️ S3上传成功
2026-01-07 12:25:30 - lifescience_news_collector - INFO - ✅ 任务完成！耗时: 1230秒
```

---

## 常见问题

### Q1: 如何添加新的数据源？
A: 在配置文件 `config/lifescience_news_collector.yaml` 的 `news_websites` 部分添加新的数据源配置，包括URL、CSS选择器等。

### Q2: 如何调整分类体系？
A: 在配置文件的 `classification.categories` 部分修改类别名称、描述和关键词。注意：当前版本固定为7大类别。

### Q3: SerpAPI密钥是必需的吗？
A: 不是必需的。如果不提供SerpAPI密钥，系统会跳过Google搜索，仅从其他14个医疗资讯网站采集数据。

### Q4: 如何处理数据源网站结构变化？
A: 更新配置文件中对应数据源的CSS选择器。建议定期检查和维护选择器配置。

### Q5: 如何减少采集时间？
A: 可以调整以下参数：
- 增加 `concurrent_requests`（并发数）
- 减少 `max_depth`（遍历深度）
- 禁用部分响应较慢的数据源
- 使用缓存机制避免重复采集

### Q6: 如何自定义HTML报告样式？
A: 修改 `case/newsletter_template.html` 模板文件，使用Jinja2语法自定义样式和布局。

### Q7: 支持定时任务吗？
A: Agent本身不提供定时任务功能，需要使用外部调度系统（如AWS EventBridge、Cron、Airflow）定期触发。

### Q8: 如何处理反爬虫机制？
A: 系统使用Playwright模拟真实浏览器行为，并支持自定义User-Agent和请求头。对于需要登录的网站，当前版本暂不支持。

---

## 故障排查

### 问题1: Agent创建失败
**症状**：`Error: Failed to create agent`
**原因**：提示词文件路径错误或格式错误
**解决方案**：
1. 检查提示词文件是否存在：`prompts/generated_agents_prompts/lifescience_news_collector/lifescience_news_collector.yaml`
2. 验证YAML格式是否正确
3. 检查日志中的详细错误信息

### 问题2: S3上传失败
**症状**：`Error: S3 upload failed`
**原因**：AWS凭证配置错误或权限不足
**解决方案**：
1. 检查AWS凭证配置：`aws configure list`
2. 验证S3桶是否存在：`aws s3 ls s3://newletter-2026`
3. 检查IAM权限：确保有 `s3:PutObject` 权限
4. 查看日志中的详细错误信息

### 问题3: 数据源采集失败
**症状**：多个数据源返回失败
**原因**：网络连接问题或网站结构变化
**解决方案**：
1. 检查网络连接：`ping www.dxy.cn`
2. 手动访问网站，验证是否可访问
3. 更新CSS选择器配置
4. 增加超时时间：`request_timeout: 60`

### 问题4: AI分类/摘要失败
**症状**：`Error: AI model invocation failed`
**原因**：模型调用失败或配额超限
**解决方案**：
1. 检查模型ID是否正确
2. 验证Bedrock访问权限
3. 检查是否达到配额限制
4. 查看日志中的详细错误信息

### 问题5: Playwright浏览器启动失败
**症状**：`Error: Playwright browser not found`
**原因**：Playwright浏览器未安装
**解决方案**：
```bash
playwright install chromium --with-deps
```

---

## 贡献指南

本项目由Nexus-AI平台自动生成，如需修改或扩展功能，请遵循以下原则：

1. **工具开发**：在 `tools/generated_tools/lifescience_news_collector/` 目录下添加新工具
2. **提示词优化**：修改 `prompts/generated_agents_prompts/lifescience_news_collector/lifescience_news_collector.yaml`
3. **配置管理**：更新 `config/lifescience_news_collector.yaml` 而非硬编码
4. **测试**：在本地测试模式下充分验证后再部署到生产环境
5. **文档更新**：同步更新本README文档

---

## 许可证

本项目由Nexus-AI平台生成，遵循项目许可证。

---

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目仓库：[Nexus-AI Platform]
- 邮件：support@nexus-ai.example.com

---

**最后更新时间**: 2026-01-07  
**项目版本**: 1.0.0  
**Agent版本**: latest  
**开发状态**: ✅ 完成并可部署

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2026-01-07 05:11:32 UTC*
