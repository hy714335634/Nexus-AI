# Manifest.json 结构说明

## 完整结构

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
            "title": "Machine Learning for Toxicity Prediction...",
            "impact_factor": 10,
            "reasoning": "Title is highly relevant to ML in cancer",
            "is_fulltext_cached": true
          },
          {
            "pmcid": "PMC12078339",
            "title": "The application of machine learning...",
            "impact_factor": 5.1,
            "reasoning": "Abstract discusses ML applications",
            "is_fulltext_cached": false
          }
        ]
      },
      "2021": {
        "total_count": 1,
        "average_impact_factor": 8.2,
        "literature": [
          {
            "pmcid": "PMC8391798",
            "title": "Combining Machine Learning...",
            "impact_factor": 8.2,
            "reasoning": "Recent publication with high relevance",
            "is_fulltext_cached": true
          }
        ]
      }
    }
  },
  "statistics": {
    "total_count": 3,
    "by_year": {
      "2021": 1,
      "2025": 2
    },
    "average_impact_factor": 7.77
  }
}
```

## 字段说明

### marked_literature
标记的文献主体，按年度组织

#### by_year
按发表年度分组的文献

- **年份键** (如 "2025", "2021"): 发表年度
  - `total_count`: 该年度文献总数
  - `average_impact_factor`: 该年度平均影响因子
  - `literature`: 文献列表数组

#### literature 数组元素
- `pmcid`: PMC ID
- `title`: 文献标题
- `impact_factor`: 影响因子（如果可用）
- `reasoning`: 标记理由（Agent判断为何选择该文献）
- `is_fulltext_cached`: 全文是否已缓存

### statistics
全局统计信息

- `total_count`: 所有标记文献总数
- `by_year`: 各年度文献数量分布
- `average_impact_factor`: 所有文献的平均影响因子

## 设计特点

1. **按年度分组**: 便于分析文献的时间分布
2. **年度降序**: 最新的文献排在前面
3. **无作者信息**: 保持manifest简洁，作者信息在meta_data中
4. **标记理由**: 记录Agent的判断依据
5. **缓存状态**: 标识全文是否可用
6. **双层统计**: 年度级和全局级统计信息

## 使用场景

### Agent总结时
```python
manifest = get_manifest("research_001")
data = json.loads(manifest)

# 获取最新年度的文献
latest_year = max(data["manifest"]["marked_literature"]["by_year"].keys())
latest_papers = data["manifest"]["marked_literature"]["by_year"][latest_year]["literature"]

# 统计信息
stats = data["manifest"]["statistics"]
print(f"共标记 {stats['total_count']} 篇文献")
print(f"平均影响因子: {stats['average_impact_factor']}")
```

### 按年度分析
```python
for year, year_data in data["manifest"]["marked_literature"]["by_year"].items():
    print(f"{year}年: {year_data['total_count']}篇, 平均IF: {year_data['average_impact_factor']}")
    for lit in year_data["literature"]:
        print(f"  - {lit['title']}")
        print(f"    理由: {lit['reasoning']}")
```

## 更新机制

每次调用 `mark_literature()` 时：
1. 读取现有manifest（如果存在）
2. 添加新标记的文献
3. 重新计算年度统计
4. 重新计算全局统计
5. 保存更新后的manifest
