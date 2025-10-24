# 摘要提取功能说明

## 功能概述

在查询文献元数据时，工具会自动：
1. 从PMC S3开放数据集下载全文XML
2. 解析XML提取摘要信息
3. 将摘要存储在meta_data文件中

## 实现细节

### 触发时机
- `search_by_keywords()` - 查询时自动提取
- `search_by_filters()` - 查询时自动提取

### 提取流程

```
查询PMC → 获取元数据 → 下载全文XML → 解析摘要 → 存储到meta_data
```

### S3路径结构

PMC开放数据集路径：
```
s3://pmc-oa-opendata/
├── oa_comm/xml/all/PMC{id}.xml      # 商业使用许可
├── oa_noncomm/xml/all/PMC{id}.xml   # 非商业使用许可
├── oa_comm/txt/all/PMC{id}.txt      # 文本格式
└── oa_noncomm/txt/all/PMC{id}.txt
```

### XML解析

使用 `xml.etree.ElementTree` 解析：
```python
tree = ET.parse(xml_file)
root = tree.getroot()
abstract_elem = root.find(".//abstract")
abstract_text = ''.join(abstract_elem.itertext()).strip()
```

## 元数据结构

```json
{
  "pmcid": "PMC8391798",
  "title": "Combining Machine Learning and Computational Chemistry...",
  "authors": [{"name": "Author Name"}],
  "journal": "Chemical Reviews",
  "publication_date": "2021",
  "abstract": "Machine learning models are poised to make a transformative impact..."
}
```

## 使用示例

### Agent筛选文献

```python
# 1. 搜索文献（自动提取摘要）
result = search_by_keywords("machine learning cancer", "research_001", max_results=100)
data = json.loads(result)

# 2. 读取元数据（包含摘要）
for pmc_id in data['ids']:
    meta_file = Path(f".cache/pmc_literature/research_001/meta_data/{pmc_id}.json")
    with open(meta_file) as f:
        meta = json.load(f)
    
    # 3. 基于标题和摘要判断相关性
    title = meta['title']
    abstract = meta['abstract']
    
    if is_relevant(title, abstract):
        # 标记相关文献
        mark_literature([pmc_id], "research_001", 
                       reasoning={"pmcid": "Title and abstract highly relevant"})
```

## 性能考虑

### 优点
- **一次性获取**：搜索时同时获取元数据和摘要
- **无需额外API调用**：直接从S3下载，不占用NCBI API配额
- **完整信息**：Agent可基于标题+摘要做出更准确的筛选判断

### 注意事项
- **下载时间**：每篇文献需要下载XML文件（通常几百KB）
- **可用性**：部分文献可能不在开放数据集中
- **网络依赖**：需要稳定的网络连接访问S3

## 测试结果

```
测试文献: PMC8391798
标题: Combining Machine Learning and Computational Chemistry...
摘要长度: 851 字符
摘要预览: Machine learning models are poised to make a transformative 
          impact on chemical sciences by dramatically accelerating 
          computational algorithms...
```

## 错误处理

如果全文不可用或解析失败：
- 摘要字段为空字符串 `""`
- 不影响其他元数据的获取
- Agent可基于标题进行初步筛选

## 与原有工具的关系

- `download_fulltext()` - 仍可用于重新下载或下载其他格式
- `get_fulltext_content()` - 用于获取完整正文内容
- `mark_literature()` - 标记时会再次尝试下载（如果之前失败）

## 总结

通过在搜索阶段前置全文下载和摘要提取，Agent可以：
1. 基于更完整的信息（标题+摘要）进行文献筛选
2. 减少后续的API调用和处理步骤
3. 提高筛选的准确性和效率
