# 性能优化说明

## download_fulltext.py 优化

### 优化前

使用 `list_objects_v2` 遍历目录查找文件：

```python
def _find_pmc_file(s3_client, pmc_id: str):
    directories = ["oa_comm/xml", "oa_noncomm/xml", "oa_comm/txt", "oa_noncomm/txt"]
    
    for directory in directories:
        response = s3_client.list_objects_v2(
            Bucket=PMC_BUCKET,
            Prefix=directory,
            MaxKeys=1000
        )
        for obj in response.get('Contents', []):
            if pmc_id in obj['Key']:
                return obj['Key']
```

**问题**：
- 需要列出整个目录（最多1000个对象）
- 每个目录都要发起一次list请求
- 效率低，延迟高

### 优化后

使用 `head_object` 直接检查文件是否存在：

```python
def _find_and_download_pmc_file(s3_client, pmc_id: str, cache_dir: Path):
    possible_paths = [
        f"oa_comm/xml/all/{pmc_id}.xml",
        f"oa_noncomm/xml/all/{pmc_id}.xml",
        f"oa_comm/txt/all/{pmc_id}.txt",
        f"oa_noncomm/txt/all/{pmc_id}.txt"
    ]
    
    for s3_key in possible_paths:
        try:
            # 使用head_object检查文件是否存在
            s3_client.head_object(Bucket=PMC_BUCKET, Key=s3_key)
            
            # 文件存在，下载
            cache_file = cache_dir / f"{pmc_id}.{file_ext}"
            s3_client.download_file(PMC_BUCKET, s3_key, str(cache_file))
            return cache_file, file_ext
        except:
            continue
```

**优势**：
- 直接构造文件路径，无需列出目录
- 使用 `head_object` 快速检查文件存在性
- 只需要4次HEAD请求（最坏情况）
- 找到文件后立即下载，无需额外请求

## 性能对比

### 理论分析

| 方法 | API调用次数 | 数据传输量 | 延迟 |
|------|------------|-----------|------|
| list_objects_v2 | 4次LIST | ~数百KB元数据 | 高 |
| head_object | 1-4次HEAD | ~几KB | 低 |

### 实际测试

```
测试文献: PMC8391798
优化后耗时: 3.42s
状态: 成功下载并结构化
```

## 适用场景

### search_by_keywords.py 和 search_by_filters.py

这两个工具也使用了相同的优化策略：

```python
def _find_and_download_fulltext(s3_client, pmc_id: str, paper_dir: Path):
    possible_paths = [
        f"oa_comm/xml/all/{pmc_id}.xml",
        f"oa_noncomm/xml/all/{pmc_id}.xml",
        f"oa_comm/txt/all/{pmc_id}.txt",
        f"oa_noncomm/txt/all/{pmc_id}.txt"
    ]
    
    for s3_key in possible_paths:
        try:
            cache_file = paper_dir / f"{pmc_id}{'.xml' if 'xml' in s3_key else '.txt'}"
            s3_client.download_file(PMC_BUCKET, s3_key, str(cache_file))
            # ... 解析摘要
            return abstract
        except:
            continue
```

**注意**：这里直接尝试下载，如果文件不存在会抛出异常，通过异常处理来判断文件是否存在。这比先HEAD再下载更高效（减少一次请求）。

## 优化原理

### PMC文件路径规律

PMC开放数据集的文件路径是可预测的：

```
{license_type}/{format}/all/{PMCID}.{ext}

其中：
- license_type: oa_comm (商业) 或 oa_noncomm (非商业)
- format: xml 或 txt
- PMCID: 如 PMC8391798
- ext: xml 或 txt
```

### 优化策略

1. **直接构造路径**：根据规律直接生成可能的4个路径
2. **快速验证**：使用HEAD请求或直接下载尝试
3. **优先级排序**：优先尝试XML格式（包含更多结构化信息）
4. **失败快速切换**：一个路径失败立即尝试下一个

## 进一步优化建议

### 1. 缓存文件路径映射

```python
# 维护一个PMCID到S3路径的映射缓存
path_cache = {}

def get_pmc_path(pmc_id):
    if pmc_id in path_cache:
        return path_cache[pmc_id]
    
    # 查找并缓存
    path = _find_and_download_pmc_file(...)
    path_cache[pmc_id] = path
    return path
```

### 2. 并行下载

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(download_single, pmc_id) for pmc_id in pmc_ids]
    results = [f.result() for f in futures]
```

### 3. 使用filelist.csv

PMC提供了文件列表CSV，可以预先下载并建立索引：

```python
# 下载filelist.csv
s3_client.download_file(PMC_BUCKET, 'oa_comm/xml/metadata/filelist.csv', 'filelist.csv')

# 建立索引
pmc_index = {}
with open('filelist.csv') as f:
    for row in csv.reader(f):
        pmc_index[row[1]] = row[0]  # PMCID -> 文件路径
```

## 总结

通过直接构造路径和使用HEAD请求，我们将文件查找效率提升了数倍：

- ✅ 减少API调用次数
- ✅ 降低数据传输量
- ✅ 减少延迟
- ✅ 代码更简洁

这种优化特别适合批量下载场景，能显著提升整体性能。
