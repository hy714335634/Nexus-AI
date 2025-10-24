# Literature Analyzer Agent

## 概述

文献相关性分析专家Agent，专门用于评估文献与研究主题的相关性，为文献筛选Agent提供深度分析和判断建议。

## 核心功能

1. **文献获取**：通过research_id和PMC ID获取文献全文
2. **相关性评估**：深度分析文献与研究主题的相关性
3. **判断建议**：明确建议是否应该标记该文献
4. **理由说明**：提供详细、具体的判断理由
5. **关键信息提取**：提取支持判断的关键内容

## 使用场景

### 场景1：辅助文献筛选Agent

文献筛选Agent在遇到难以判断的文献时，可以调用此Agent进行深度分析：

```python
# 文献筛选Agent的工作流程
for pmc_id in pmc_ids:
    # 读取元数据
    metadata = read_metadata(pmc_id)
    
    # 基于标题和摘要初步判断
    if is_obviously_relevant(metadata):
        mark_literature([pmc_id], research_id, reasoning={...})
    elif is_obviously_irrelevant(metadata):
        continue
    else:
        # 边界情况，调用分析Agent
        result = call_literature_analyzer(
            research_id=research_id,
            pmcid=pmc_id,
            research_topic=topic
        )
        
        if result['should_mark']:
            mark_literature([pmc_id], research_id, 
                          reasoning={pmc_id: result['reasoning']})
```

### 场景2：独立深度分析

用户可以直接调用此Agent对特定文献进行深度分析：

```python
result = literature_analyzer.analyze(
    research_id="ml_cancer_20251024",
    pmcid="PMC8391798",
    research_topic="机器学习在癌症预测中的应用",
    research_requirements="关注深度学习方法和临床应用"
)
```

## 输入参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| research_id | string | 是 | 研究项目ID，用于定位缓存目录 |
| pmcid | string | 是 | 文献的PMC ID |
| research_topic | string | 是 | 用户的研究主题和问题 |
| research_requirements | string | 否 | 额外的筛选要求 |

## 输出格式

```json
{
  "pmcid": "PMC123456",
  "should_mark": true,
  "relevance_score": 0.85,
  "reasoning": "详细的判断理由...",
  "key_findings": [
    "关键发现1",
    "关键发现2"
  ],
  "relevance_aspects": {
    "topic_match": "高",
    "methodology": "相关",
    "conclusions": "有价值",
    "innovation": "创新"
  },
  "recommendation": "强烈推荐标记",
  "confidence": "高"
}
```

## 判断标准

### 相关性评分（relevance_score）

- **0.9-1.0**：高度相关，核心文献
- **0.7-0.9**：相关，重要参考文献
- **0.5-0.7**：中度相关，可选参考
- **0.3-0.5**：低度相关，边缘文献
- **0.0-0.3**：不相关

### 标记建议（should_mark）

- **true**：relevance_score >= 0.5
- **false**：relevance_score < 0.5

### 推荐级别（recommendation）

- **强烈推荐标记**：relevance_score >= 0.7
- **推荐标记**：0.5 <= relevance_score < 0.7
- **不推荐标记**：relevance_score < 0.5

## 评估维度

### 1. 主题匹配度（topic_match）
- **高**：标题或摘要直接讨论研究主题
- **中**：部分内容与主题相关
- **低**：仅提及相关术语

### 2. 方法相关性（methodology）
- **相关**：研究方法与主题高度相关
- **部分相关**：方法有一定参考价值
- **不相关**：方法与主题无关

### 3. 结论价值（conclusions）
- **有价值**：结论对研究有重要贡献
- **部分有价值**：结论有一定参考意义
- **无价值**：结论对研究无帮助

### 4. 创新性（innovation）
- **创新**：提供新的视角或发现
- **常规**：常规研究，无特别创新
- **重复**：重复已有研究

## reasoning字段结构

必须包含以下5个部分：

```
1. 标题分析：标题是否体现主题相关性
2. 摘要分析：摘要中的关键信息和相关性
3. 方法相关性：研究方法是否适用于主题
4. 结论价值：研究结论对主题的贡献
5. 综合判断：基于以上分析的最终判断
```

## 使用示例

### 示例1：高度相关文献

**输入**：
```json
{
  "research_id": "ml_cancer_20251024",
  "pmcid": "PMC8391798",
  "research_topic": "机器学习在癌症预测中的应用"
}
```

**输出**：
```json
{
  "pmcid": "PMC8391798",
  "should_mark": true,
  "relevance_score": 0.92,
  "reasoning": "1. 标题分析：标题'Combining Machine Learning and Computational Chemistry'明确涉及机器学习主题\n2. 摘要分析：摘要详细讨论了ML在化学系统预测中的应用\n3. 方法相关性：研究系统性回顾了ML方法，方法论完整\n4. 结论价值：提供了ML模型选择和应用的最佳实践\n5. 综合判断：该文献是ML应用领域的重要综述，强烈推荐标记",
  "key_findings": [
    "系统性回顾了ML在计算化学中的应用",
    "对比了深度学习和传统ML方法",
    "提供了模型选择的最佳实践指南"
  ],
  "relevance_aspects": {
    "topic_match": "高",
    "methodology": "相关",
    "conclusions": "有价值",
    "innovation": "创新"
  },
  "recommendation": "强烈推荐标记",
  "confidence": "高"
}
```

### 示例2：不相关文献

**输入**：
```json
{
  "research_id": "ml_cancer_20251024",
  "pmcid": "PMC1234567",
  "research_topic": "机器学习在癌症预测中的应用"
}
```

**输出**：
```json
{
  "pmcid": "PMC1234567",
  "should_mark": false,
  "relevance_score": 0.25,
  "reasoning": "1. 标题分析：标题讨论的是传统统计方法在流行病学中的应用，与ML无关\n2. 摘要分析：摘要未提及机器学习或AI技术\n3. 方法相关性：使用传统回归分析，与ML方法不相关\n4. 结论价值：结论对ML研究无参考价值\n5. 综合判断：该文献与研究主题不相关，不推荐标记",
  "key_findings": [],
  "relevance_aspects": {
    "topic_match": "低",
    "methodology": "不相关",
    "conclusions": "无价值",
    "innovation": "常规"
  },
  "recommendation": "不推荐标记",
  "confidence": "高"
}
```

## 工具依赖

- `get_fulltext_content`：获取文献全文内容
- `current_time`：记录分析时间

## 配置文件

配置文件位置：`prompts/generated_agents_prompts/literature_analysis_agent/literature_analyzer.yaml`

## 最佳实践

1. **批量调用**：对于大量文献，建议批量调用以提高效率
2. **缓存结果**：保存分析结果，避免重复分析
3. **阈值调整**：根据实际需求调整relevance_score阈值
4. **人工复核**：对于边界情况（0.4-0.6），建议人工复核
5. **持续优化**：根据反馈不断优化判断标准

## 注意事项

1. 分析依赖文献全文，确保文献已缓存
2. reasoning字段必须具体，避免泛泛而谈
3. relevance_score必须准确反映相关程度
4. 所有判断必须基于文献实际内容
5. 保持客观中立，避免主观偏见
