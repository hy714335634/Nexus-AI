# TXT格式处理说明

## 格式变更

从XML格式改为TXT格式处理，原因：
- XML结构不统一，解析复杂
- TXT格式统一，易于处理
- TXT文件更小，下载更快

## PMC TXT文件结构

PMC开放数据集的TXT文件采用统一的分段格式：

```
==== Front
[期刊信息、标题、作者、摘要等]

==== Body
[正文内容]

==== Refs
[参考文献]

==== Back
[附录等]
```

## 摘要提取逻辑

提取 `==== Front` 和 `==== Body` 之间的所有内容作为摘要：

```python
# 1. 去除所有空行
lines = [line for line in content.split('\n') if line.strip()]
content = '\n'.join(lines)

# 2. 提取Front和Body之间的内容
if '==== Front' in content and '==== Body' in content:
    start = content.find('==== Front') + len('==== Front')
    end = content.find('==== Body')
    abstract = content[start:end].strip()
```

## 示例文件：PMC10003322.txt

### Front部分内容

```
==== Front
J Clin Med
J Clin Med
jcm
Journal of Clinical Medicine
2077-0383
MDPI

10.3390/jcm12051726
jcm-12-01726
Opinion
Aggressive Angiomyxoma of the Vulva: Which Is the Best Management Strategy?
...
Background: Aggressive angiomyxoma is a rare mesenchymal tumour...
Conclusion: Wide surgical excision is the gold-standard treatment...

aggressive angiomyxoma
mesenchymal tumour
genital tumour
vulvar lesion
```

### 提取的摘要

包含：
- 期刊信息
- 文章标题
- 作者信息
- 摘要正文
- 关键词

## 文件路径

TXT文件在S3中的路径：

```
s3://pmc-oa-opendata/
├── oa_comm/txt/all/PMC{id}.txt      # 商业使用许可
└── oa_noncomm/txt/all/PMC{id}.txt   # 非商业使用许可
```

## 工具更新

### search_by_keywords.py
- 只下载TXT格式
- 提取Front和Body之间内容作为摘要
- 去除空行后存储

### search_by_filters.py
- 同上

### download_fulltext.py
- 只下载TXT格式
- 移除XML结构化处理逻辑
- 简化下载流程

### get_fulltext_content.py
- 只读取TXT文件
- 移除XML和结构化JSON处理

### mark_literature.py
- 检查TXT文件是否存在
- 移除XML和结构化JSON检查

## 性能优势

| 指标 | XML | TXT |
|------|-----|-----|
| 文件大小 | ~800KB | ~350KB |
| 解析复杂度 | 高（需要XML解析） | 低（文本处理） |
| 结构统一性 | 低（各文章结构不同） | 高（统一分段格式） |
| 处理速度 | 慢 | 快 |

## 测试结果

```
测试文献: PMC8391798
格式: TXT
文件大小: 351,812 字符
摘要长度: 4,364 字符
下载状态: ✅ 成功
解析状态: ✅ 成功
```

## 注意事项

1. **摘要内容丰富**：Front部分包含期刊信息、作者、关键词等，比纯摘要更完整
2. **空行处理**：必须先去除空行，否则会影响分段识别
3. **编码处理**：使用UTF-8编码读取文件
4. **容错处理**：如果找不到分段标记，返回空字符串

## 未来优化

可以进一步细化Front部分的解析，提取：
- 纯摘要文本（去除期刊信息）
- 关键词列表
- 作者列表
- DOI等元数据

但当前实现已满足Agent筛选文献的需求。
