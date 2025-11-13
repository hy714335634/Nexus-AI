# Google Scholar Search Tool

## 概述

Google Scholar Search 是一个功能强大的工具，用于在 Google Scholar 上进行学术文献搜索并获取详细的文献信息。该工具能够根据用户提供的关键字进行搜索，并返回包含标题、作者、摘要、引用次数、发表年份和期刊等关键信息的结构化结果。

## 功能特性

- 根据关键字在 Google Scholar 上进行搜索
- 限制返回结果数量
- 支持按相关度或日期排序
- 支持按年份范围筛选文献
- 提取文献的详细信息：
  - 标题
  - 作者
  - 摘要
  - 引用次数
  - 发表年份
  - 期刊名称
  - 文献链接
- 完善的错误处理机制
- 规避 Google Scholar 反爬机制

## 安装

### 依赖安装

```bash
pip install requests>=2.25.0 beautifulsoup4>=4.9.0 lxml>=4.6.0 fake-useragent>=0.1.11
```

## 使用方法

### 导入工具

```python
from tools.generated_tools.tool_build_scholar_search.scholar_search import search_google_scholar
```

### 基本搜索

```python
# 基本搜索，返回默认10条结果
result = search_google_scholar(keywords="machine learning")
print(result)
```

### 限制结果数量

```python
# 限制返回前5条结果
result = search_google_scholar(keywords="artificial intelligence", top_n=5)
print(result)
```

### 按日期排序

```python
# 按日期排序，获取最新的研究
result = search_google_scholar(keywords="deep learning", top_n=5, sort_by="date")
print(result)
```

### 年份范围筛选

```python
# 获取2020年至2025年之间发表的文献
result = search_google_scholar(
    keywords="quantum computing", 
    top_n=5, 
    start_year=2020, 
    end_year=2025
)
print(result)
```

### 组合使用

```python
# 组合使用多个参数
result = search_google_scholar(
    keywords="climate change adaptation", 
    top_n=8, 
    sort_by="date", 
    start_year=2022
)
print(result)
```

## API 文档

### search_google_scholar

根据关键字在 Google Scholar 上进行搜索并返回学术文献信息。

#### 参数

- **keywords** (str): 搜索关键字或短语，多个关键字可以用空格分隔
- **top_n** (int, 可选): 返回结果的数量限制，默认为10
- **sort_by** (str, 可选): 结果排序方式，可选值：relevance（相关度）或date（日期）
- **start_year** (int, 可选): 筛选文献的起始年份
- **end_year** (int, 可选): 筛选文献的结束年份

#### 返回值

JSON格式字符串，包含以下内容：

```json
{
  "status": "success",
  "results_count": 5,
  "results": [
    {
      "title": "文献标题",
      "authors": ["作者1", "作者2"],
      "publication": "期刊名称",
      "year": 2023,
      "abstract": "文献摘要内容...",
      "citations": 42,
      "url": "https://..."
    },
    ...
  ]
}
```

如果发生错误，返回格式为：

```json
{
  "status": "error",
  "message": "错误信息"
}
```

## 错误处理

工具提供了全面的错误处理机制，包括：

1. **输入参数验证**：检查关键字是否为空，数值参数是否为有效整数
2. **网络错误处理**：处理请求超时、连接失败等网络异常
3. **解析错误处理**：处理HTML解析失败的情况
4. **Google Scholar访问限制**：使用随机User-Agent头规避反爬机制

## 注意事项

1. **使用频率限制**：过于频繁的请求可能导致IP被Google Scholar暂时封禁，建议合理控制请求频率
2. **遵守使用条款**：使用本工具应遵守Google Scholar的使用条款和服务协议
3. **学术研究用途**：工具应主要用于学术研究目的，避免大规模商业数据抓取
4. **结果可用性**：由于Google Scholar页面结构可能会变化，工具的解析功能可能需要定期更新
5. **信息完整性**：部分文献可能缺少某些信息（如摘要、引用次数等），返回结果中对应字段可能为空

## 改进建议

以下是一些可能的改进方向：

1. 添加请求重试机制，应对网络不稳定情况
2. 增加代理IP池功能，规避Google Scholar的IP限制
3. 添加结果缓存机制，减少重复请求
4. 增加更多排序和过滤选项，如按引用次数排序或按作者过滤

## 技术实现

工具主要使用以下技术和库：

- **requests**：发送HTTP请求获取Google Scholar页面
- **BeautifulSoup4**：解析HTML页面内容，提取文献信息
- **lxml**：作为BeautifulSoup的HTML解析器
- **fake-useragent**：生成随机User-Agent头，避免被Google Scholar识别为爬虫

内部实现了以下几个主要功能函数：

1. **get_random_user_agent**：生成随机User-Agent头
2. **build_search_url**：构建Google Scholar搜索URL
3. **extract_article_info**：从单个文献结果元素中提取详细信息
4. **parse_search_results**：从Google Scholar搜索结果页面中解析文献信息
5. **search_google_scholar**：主函数，整合所有功能，提供对外接口