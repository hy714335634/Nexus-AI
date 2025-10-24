# PubMed Literature Screen Assistant Tools

文献检索助手工具集，用于PubMed/PMC文献的检索、筛选和管理。

## 工具列表

### 1. search_by_keywords
基于关键词查询PubMed/PMC文献库

**功能**：
- 按相关度排序查询文献
- 获取文献元数据（PMC ID、标题、作者、期刊、发表日期）
- **自动下载全文并提取摘要**
- 自动缓存元数据到 `.cache/pmc_literature/{research_id}/meta_data/`
- 自动缓存全文到 `.cache/pmc_literature/{research_id}/paper/`

**参数**：
- `keywords` (str): 查询关键词
- `research_id` (str): 研究项目ID
- `max_results` (int): 最大返回结果数，默认100

**返回**：
```json
{
  "status": "success",
  "count": 50,
  "ids": ["PMC123456", "PMC789012", ...],
  "cached": ["PMC123456", "PMC789012", ...]
}
```

**元数据结构**（包含摘要）：
```json
{
  "pmcid": "PMC123456",
  "title": "Machine Learning in Healthcare",
  "authors": [{"name": "John Doe"}],
  "journal": "Nature Medicine",
  "publication_date": "2023",
  "abstract": "This study explores..."
}
```

### 2. search_by_filters
基于NCBI查询筛选条件查询文献

**功能**：
- 支持NCBI高级查询语法
- 按指定方式排序（默认相关度）
- **自动下载全文并提取摘要**
- 自动缓存元数据和全文

**参数**：
- `query_filter` (str): NCBI查询语法，如 `"cancer[Title] AND 2023[PDAT]"`
- `research_id` (str): 研究项目ID
- `max_results` (int): 最大返回结果数，默认100
- `sort_by` (str): 排序方式，默认"relevance"

**示例查询**：
- 按标题: `"machine learning[Title]"`
- 按时间: `"2020:2023[PDAT]"`
- 组合查询: `"COVID-19[Title] AND 2023[PDAT]"`

### 3. mark_literature
标记文献并维护manifest.json

**功能**：
- 标记选中的文献
- 按发表年度分组
- 按相关度排序
- 统计数据（总数、年度分布、平均影响因子）
- 自动下载全文

**参数**：
- `pmc_ids` (list): PMC ID列表
- `research_id` (str): 研究项目ID
- `reasoning` (dict): 标记理由字典，格式 `{pmcid: reasoning_text}`
- `auto_download` (bool): 是否自动下载全文，默认True

**返回**：
```json
{
  "status": "success",
  "marked_count": 25,
  "statistics": {
    "total_count": 25,
    "by_year": {"2023": 10, "2022": 15},
    "average_impact_factor": 5.2
  }
}
```

**manifest.json结构**：
```json
{
  "marked_literature": {
    "by_year": {
      "2025": {
        "total_count": 2,
        "average_impact_factor": 7.5,
        "literature": [
          {
            "pmcid": "PMC12093382",
            "title": "Machine Learning for...",
            "impact_factor": 10,
            "reasoning": "Title is highly relevant",
            "is_fulltext_cached": true
          }
        ]
      }
    }
  },
  "statistics": {
    "total_count": 3,
    "by_year": {"2021": 1, "2025": 2},
    "average_impact_factor": 5.2
  }
}
```

### 4. download_fulltext
下载并缓存文献全文

**功能**：
- 从PMC S3开放数据集下载全文
- 优先保存为结构化XML
- 解析失败时保存原始文件
- 缓存到 `.cache/pmc_literature/{research_id}/paper/`

**参数**：
- `pmc_ids` (list): PMC ID列表
- `research_id` (str): 研究项目ID

**返回**：
```json
{
  "status": "success",
  "results": [
    {"pmcid": "PMC123456", "status": "cached", "format": "xml_structured"},
    {"pmcid": "PMC789012", "status": "cached", "format": "txt"}
  ]
}
```

### 5. get_fulltext_content
获取文献全文内容

**功能**：
- 以字符串形式返回全文内容
- 优先返回结构化内容
- 支持XML和TXT格式

**参数**：
- `pmc_ids` (list): PMC ID列表
- `research_id` (str): 研究项目ID

**返回**：
```json
{
  "status": "success",
  "results": [
    {
      "pmcid": "PMC123456",
      "content": "Title: ...\nAbstract: ...\n...",
      "format": "structured"
    }
  ]
}
```

### 6. get_manifest
获取manifest.json文件内容

**功能**：
- 返回当前标记的文献清单
- 包含统计信息

**参数**：
- `research_id` (str): 研究项目ID

**返回**：
```json
{
  "status": "success",
  "manifest": {
    "marked_literature": [...],
    "statistics": {...}
  }
}
```

## 使用流程

典型的文献检索工作流程：

```python
# 1. 根据关键词检索文献
search_by_keywords("machine learning in healthcare", "research_001", max_results=200)

# 2. 或使用高级筛选
search_by_filters("machine learning[Title] AND 2023[PDAT]", "research_001")

# 3. 根据元数据判断并标记相关文献（带理由）
reasoning = {
    "PMC123456": "Title highly relevant to ML in cancer research",
    "PMC789012": "Abstract discusses novel ML applications"
}
mark_literature(["PMC123456", "PMC789012"], "research_001", reasoning=reasoning)

# 4. 获取全文内容进行深度分析
get_fulltext_content(["PMC123456"], "research_001")

# 5. 获取最终清单进行总结
get_manifest("research_001")
```

## 环境变量

需要设置以下环境变量：

- `NCBI_API_KEY`: NCBI API密钥（可选，但强烈推荐以提高请求限制）

获取API Key: https://www.ncbi.nlm.nih.gov/account/settings/

## 缓存目录结构

```
.cache/pmc_literature/{research_id}/
├── meta_data/              # 元数据缓存
│   ├── PMC123456.json
│   └── PMC789012.json
├── paper/                  # 全文缓存
│   ├── PMC123456.xml
│   ├── PMC123456_structured.json
│   └── PMC789012.txt
└── manifest.json           # 标记清单
```

## 注意事项

1. 所有工具自动从环境变量获取 `NCBI_API_KEY`
2. **搜索时自动下载全文并提取摘要**，无需单独调用下载工具
3. 摘要信息已包含在meta_data中，可直接用于文献筛选判断
4. 全文下载依赖PMC开放数据集，部分文献可能不可用
5. 建议设置NCBI API Key以避免请求限制
6. 工具会自动处理PMC ID格式（带或不带"PMC"前缀）
