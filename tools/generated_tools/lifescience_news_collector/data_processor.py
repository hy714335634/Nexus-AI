"""
生命科学新闻数据处理工具模块

该模块提供：
- 文章去重和相似度检测
- 内容摘要生成
- 关键词提取
- 分类和标签
- 数据验证和规范化
"""

import json
import hashlib
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import Counter
from strands import tool


# ============================================================================
# 文章去重工具
# ============================================================================

@tool
def deduplicate_articles(
    articles: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
    method: str = "title_hash"  # title_hash, content_hash, fuzzy
) -> str:
    """
    文章去重工具
    
    Args:
        articles: 文章列表，每篇文章包含title和content字段
        similarity_threshold: 相似度阈值（0-1），用于fuzzy方法
        method: 去重方法（title_hash=标题哈希, content_hash=内容哈希, fuzzy=模糊匹配）
    
    Returns:
        str: JSON格式的去重结果
    """
    try:
        unique_articles = []
        duplicate_articles = []
        seen_hashes = set()
        
        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")
            
            # 根据方法计算哈希或相似度
            if method == "title_hash":
                # 基于标题哈希去重
                article_hash = hashlib.md5(title.strip().lower().encode()).hexdigest()
                
            elif method == "content_hash":
                # 基于内容哈希去重（前500字符）
                content_sample = content[:500].strip().lower()
                article_hash = hashlib.md5(content_sample.encode()).hexdigest()
                
            elif method == "fuzzy":
                # 模糊匹配（简化版：基于标题关键词）
                title_words = set(re.findall(r'\w+', title.lower()))
                
                is_duplicate = False
                for unique_article in unique_articles:
                    unique_title = unique_article.get("title", "")
                    unique_words = set(re.findall(r'\w+', unique_title.lower()))
                    
                    # 计算Jaccard相似度
                    if len(title_words) > 0 and len(unique_words) > 0:
                        intersection = len(title_words & unique_words)
                        union = len(title_words | unique_words)
                        similarity = intersection / union if union > 0 else 0
                        
                        if similarity >= similarity_threshold:
                            is_duplicate = True
                            duplicate_articles.append(article)
                            break
                
                if not is_duplicate:
                    unique_articles.append(article)
                
                continue
            else:
                return json.dumps({
                    "success": False,
                    "error": f"不支持的去重方法: {method}"
                }, ensure_ascii=False, indent=2)
            
            # 哈希方法的去重逻辑
            if method in ["title_hash", "content_hash"]:
                if article_hash not in seen_hashes:
                    seen_hashes.add(article_hash)
                    unique_articles.append(article)
                else:
                    duplicate_articles.append(article)
        
        return json.dumps({
            "success": True,
            "method": method,
            "original_count": len(articles),
            "unique_count": len(unique_articles),
            "duplicate_count": len(duplicate_articles),
            "unique_articles": unique_articles,
            "duplicate_articles": duplicate_articles,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文章去重失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 内容摘要生成工具
# ============================================================================

@tool
def generate_article_summary(
    content: str,
    max_sentences: int = 3,
    max_length: int = 300
) -> str:
    """
    生成文章摘要（基于规则的简化版）
    
    Args:
        content: 文章内容
        max_sentences: 最大句子数
        max_length: 最大字符数
    
    Returns:
        str: JSON格式的摘要结果
    """
    try:
        # 分句（简化版：按句号、问号、感叹号分割）
        sentences = re.split(r'[。！？\.\!\?]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            return json.dumps({
                "success": False,
                "error": "无法从内容中提取有效句子"
            }, ensure_ascii=False, indent=2)
        
        # 选择前N个句子作为摘要（可优化为基于重要性）
        summary_sentences = sentences[:max_sentences]
        summary = "。".join(summary_sentences) + "。"
        
        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return json.dumps({
            "success": True,
            "original_length": len(content),
            "summary_length": len(summary),
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"摘要生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 关键词提取工具
# ============================================================================

@tool
def extract_keywords(
    text: str,
    top_k: int = 10,
    min_word_length: int = 2,
    stopwords: Optional[List[str]] = None
) -> str:
    """
    提取关键词（基于词频的简化版）
    
    Args:
        text: 文本内容
        top_k: 返回前K个关键词
        min_word_length: 最小词长
        stopwords: 停用词列表
    
    Returns:
        str: JSON格式的关键词结果
    """
    try:
        # 默认停用词（简化版）
        default_stopwords = {
            "的", "了", "和", "是", "在", "我", "有", "个", "人", "这", "中", "大", "为", "上",
            "来", "到", "时", "地", "们", "出", "就", "会", "可", "也", "你", "对", "生", "能",
            "而", "子", "那", "得", "于", "着", "下", "自", "之", "年", "过", "发", "后", "作",
            "里", "用", "家", "方", "开", "天", "种", "去", "他", "说", "看", "主", "无", "又"
        }
        
        if stopwords:
            default_stopwords.update(stopwords)
        
        # 中文分词（简化版：提取连续中文字符）
        words = re.findall(r'[\u4e00-\u9fa5]+', text)
        
        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if len(word) >= min_word_length and word not in default_stopwords
        ]
        
        # 统计词频
        word_counts = Counter(filtered_words)
        
        # 获取Top K关键词
        top_keywords = word_counts.most_common(top_k)
        
        keywords = [
            {"keyword": word, "frequency": count}
            for word, count in top_keywords
        ]
        
        return json.dumps({
            "success": True,
            "total_words": len(filtered_words),
            "unique_words": len(word_counts),
            "top_k": top_k,
            "keywords": keywords,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"关键词提取失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 文章分类工具
# ============================================================================

@tool
def classify_article(
    title: str,
    content: str,
    categories: Dict[str, List[str]]
) -> str:
    """
    基于关键词的文章分类
    
    Args:
        title: 文章标题
        content: 文章内容
        categories: 分类关键词字典，格式: {"类别名": ["关键词1", "关键词2"]}
    
    Returns:
        str: JSON格式的分类结果
    """
    try:
        text = f"{title} {content}".lower()
        
        category_scores = {}
        
        # 计算每个类别的匹配分数
        for category, keywords in categories.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # 统计关键词出现次数
                count = text.count(keyword_lower)
                if count > 0:
                    score += count
                    matched_keywords.append({
                        "keyword": keyword,
                        "count": count
                    })
            
            if score > 0:
                category_scores[category] = {
                    "score": score,
                    "matched_keywords": matched_keywords
                }
        
        # 排序并获取最佳匹配类别
        sorted_categories = sorted(
            category_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )
        
        primary_category = sorted_categories[0][0] if sorted_categories else "未分类"
        
        return json.dumps({
            "success": True,
            "primary_category": primary_category,
            "all_matches": {
                cat: info for cat, info in sorted_categories
            },
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"文章分类失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 标签生成工具
# ============================================================================

@tool
def generate_article_tags(
    title: str,
    content: str,
    keywords: Optional[List[str]] = None,
    max_tags: int = 5,
    predefined_tags: Optional[List[str]] = None
) -> str:
    """
    生成文章标签
    
    Args:
        title: 文章标题
        content: 文章内容
        keywords: 已提取的关键词列表（可选）
        max_tags: 最大标签数
        predefined_tags: 预定义标签列表（可选）
    
    Returns:
        str: JSON格式的标签结果
    """
    try:
        tags = []
        
        # 方法1: 使用已提取的关键词
        if keywords:
            tags.extend(keywords[:max_tags])
        
        # 方法2: 从预定义标签中匹配
        if predefined_tags:
            text = f"{title} {content}".lower()
            for tag in predefined_tags:
                if tag.lower() in text:
                    if tag not in tags:
                        tags.append(tag)
                    if len(tags) >= max_tags:
                        break
        
        # 方法3: 如果标签不足，从内容中提取高频词
        if len(tags) < max_tags:
            # 提取关键词
            extract_result = extract_keywords(
                text=content,
                top_k=max_tags - len(tags),
                min_word_length=2
            )
            extract_data = json.loads(extract_result)
            
            if extract_data.get("success"):
                for kw in extract_data.get("keywords", []):
                    keyword = kw.get("keyword", "")
                    if keyword not in tags:
                        tags.append(keyword)
                    if len(tags) >= max_tags:
                        break
        
        return json.dumps({
            "success": True,
            "tags_count": len(tags),
            "tags": tags[:max_tags],
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"标签生成失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 数据验证工具
# ============================================================================

@tool
def validate_article_data(
    article: Dict[str, Any],
    required_fields: Optional[List[str]] = None,
    min_content_length: int = 100,
    max_title_length: int = 200
) -> str:
    """
    验证文章数据完整性和有效性
    
    Args:
        article: 文章数据字典
        required_fields: 必需字段列表（默认: ["title", "content", "url"]）
        min_content_length: 最小内容长度
        max_title_length: 最大标题长度
    
    Returns:
        str: JSON格式的验证结果
    """
    try:
        if required_fields is None:
            required_fields = ["title", "content", "url"]
        
        validation_errors = []
        validation_warnings = []
        
        # 检查必需字段
        for field in required_fields:
            if field not in article or not article[field]:
                validation_errors.append(f"缺少必需字段: {field}")
        
        # 检查标题长度
        title = article.get("title", "")
        if len(title) == 0:
            validation_errors.append("标题为空")
        elif len(title) > max_title_length:
            validation_warnings.append(f"标题过长 ({len(title)} > {max_title_length})")
        
        # 检查内容长度
        content = article.get("content", "")
        if len(content) == 0:
            validation_errors.append("内容为空")
        elif len(content) < min_content_length:
            validation_warnings.append(f"内容过短 ({len(content)} < {min_content_length})")
        
        # 检查URL格式
        url = article.get("url", "")
        if url and not url.startswith(("http://", "https://")):
            validation_errors.append(f"URL格式无效: {url}")
        
        is_valid = len(validation_errors) == 0
        
        return json.dumps({
            "success": True,
            "is_valid": is_valid,
            "errors": validation_errors,
            "warnings": validation_warnings,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"数据验证失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 数据规范化工具
# ============================================================================

@tool
def normalize_article_data(
    article: Dict[str, Any],
    add_id: bool = True,
    add_timestamp: bool = True,
    clean_content: bool = True
) -> str:
    """
    规范化文章数据格式
    
    Args:
        article: 原始文章数据
        add_id: 是否添加唯一ID
        add_timestamp: 是否添加时间戳
        clean_content: 是否清洗内容
    
    Returns:
        str: JSON格式的规范化结果
    """
    try:
        normalized_article = article.copy()
        
        # 添加唯一ID
        if add_id and "id" not in normalized_article:
            # 基于URL和标题生成ID
            url = normalized_article.get("url", "")
            title = normalized_article.get("title", "")
            id_string = f"{url}{title}"
            article_id = hashlib.md5(id_string.encode()).hexdigest()
            normalized_article["id"] = article_id
        
        # 添加时间戳
        if add_timestamp:
            normalized_article["processed_at"] = datetime.now().isoformat()
        
        # 清洗内容
        if clean_content:
            content = normalized_article.get("content", "")
            if content:
                clean_result = clean_article_text(
                    text=content,
                    remove_extra_whitespace=True,
                    remove_html_entities=True,
                    remove_special_chars=False
                )
                clean_data = json.loads(clean_result)
                if clean_data.get("success"):
                    normalized_article["content"] = clean_data.get("cleaned_text", content)
        
        # 规范化字段名
        field_mapping = {
            "link": "url",
            "snippet": "summary",
            "date": "published_date"
        }
        
        for old_field, new_field in field_mapping.items():
            if old_field in normalized_article and new_field not in normalized_article:
                normalized_article[new_field] = normalized_article.pop(old_field)
        
        return json.dumps({
            "success": True,
            "normalized_article": normalized_article,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"数据规范化失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 批量数据处理工具
# ============================================================================

@tool
def batch_process_articles(
    articles: List[Dict[str, Any]],
    operations: List[str],
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    批量处理文章数据
    
    Args:
        articles: 文章列表
        operations: 操作列表，支持: deduplicate, summarize, extract_keywords, classify, generate_tags, validate, normalize
        config: 操作配置参数
    
    Returns:
        str: JSON格式的批量处理结果
    """
    try:
        if config is None:
            config = {}
        
        processed_articles = articles.copy()
        operation_results = {}
        
        # 去重
        if "deduplicate" in operations:
            dedup_method = config.get("deduplicate_method", "title_hash")
            dedup_result = deduplicate_articles(
                articles=processed_articles,
                method=dedup_method
            )
            dedup_data = json.loads(dedup_result)
            if dedup_data.get("success"):
                processed_articles = dedup_data.get("unique_articles", [])
                operation_results["deduplicate"] = {
                    "original_count": dedup_data.get("original_count"),
                    "unique_count": dedup_data.get("unique_count")
                }
        
        # 为每篇文章执行操作
        for article in processed_articles:
            # 生成摘要
            if "summarize" in operations:
                content = article.get("content", "")
                if content:
                    summary_result = generate_article_summary(
                        content=content,
                        max_sentences=config.get("max_summary_sentences", 3)
                    )
                    summary_data = json.loads(summary_result)
                    if summary_data.get("success"):
                        article["summary"] = summary_data.get("summary", "")
            
            # 提取关键词
            if "extract_keywords" in operations:
                content = article.get("content", "")
                if content:
                    kw_result = extract_keywords(
                        text=content,
                        top_k=config.get("top_k_keywords", 10)
                    )
                    kw_data = json.loads(kw_result)
                    if kw_data.get("success"):
                        article["keywords"] = [
                            kw["keyword"] for kw in kw_data.get("keywords", [])
                        ]
            
            # 分类
            if "classify" in operations:
                categories = config.get("categories", {})
                if categories:
                    classify_result = classify_article(
                        title=article.get("title", ""),
                        content=article.get("content", ""),
                        categories=categories
                    )
                    classify_data = json.loads(classify_result)
                    if classify_data.get("success"):
                        article["category"] = classify_data.get("primary_category", "")
            
            # 生成标签
            if "generate_tags" in operations:
                tags_result = generate_article_tags(
                    title=article.get("title", ""),
                    content=article.get("content", ""),
                    keywords=article.get("keywords"),
                    max_tags=config.get("max_tags", 5),
                    predefined_tags=config.get("predefined_tags")
                )
                tags_data = json.loads(tags_result)
                if tags_data.get("success"):
                    article["tags"] = tags_data.get("tags", [])
            
            # 验证
            if "validate" in operations:
                validate_result = validate_article_data(
                    article=article,
                    required_fields=config.get("required_fields"),
                    min_content_length=config.get("min_content_length", 100)
                )
                validate_data = json.loads(validate_result)
                article["validation"] = {
                    "is_valid": validate_data.get("is_valid", False),
                    "errors": validate_data.get("errors", []),
                    "warnings": validate_data.get("warnings", [])
                }
            
            # 规范化
            if "normalize" in operations:
                normalize_result = normalize_article_data(
                    article=article,
                    add_id=config.get("add_id", True),
                    add_timestamp=config.get("add_timestamp", True),
                    clean_content=config.get("clean_content", True)
                )
                normalize_data = json.loads(normalize_result)
                if normalize_data.get("success"):
                    article.update(normalize_data.get("normalized_article", {}))
        
        return json.dumps({
            "success": True,
            "total_articles": len(processed_articles),
            "operations_performed": operations,
            "operation_results": operation_results,
            "processed_articles": processed_articles,
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"批量处理失败: {str(e)}"
        }, ensure_ascii=False, indent=2)


# ============================================================================
# 辅助函数：文本清洗
# ============================================================================

def clean_article_text(
    text: str,
    remove_extra_whitespace: bool = True,
    remove_html_entities: bool = True,
    remove_special_chars: bool = False
) -> str:
    """
    清洗文章文本（内部辅助函数）
    """
    try:
        import html as html_lib
        
        cleaned_text = text
        
        if remove_html_entities:
            cleaned_text = html_lib.unescape(cleaned_text)
        
        if remove_extra_whitespace:
            cleaned_text = re.sub(r' +', ' ', cleaned_text)
            cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
            cleaned_text = '\n'.join(line.strip() for line in cleaned_text.split('\n'))
        
        if remove_special_chars:
            cleaned_text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,!?;:，。！？；：、\-\(\)\[\]（）【】]', '', cleaned_text)
        
        return json.dumps({
            "success": True,
            "cleaned_text": cleaned_text
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)
