#!/usr/bin/env python3
"""
translation_engine.py - 医学文档翻译引擎工具

该工具提供了基于词库和AI的医学文档翻译功能，
支持精准术语翻译、上下文感知翻译和多种医学专业领域翻译。
"""

import os
import json
import re
import hashlib
import datetime
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
import time

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    raise ImportError("请安装boto3库: pip install boto3")

from strands import tool


# 默认缓存目录
DEFAULT_CACHE_DIR = os.path.join(".cache", "medical_translator", "translations")

# 支持的语言代码
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "en": "英文",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "it": "意大利语",
    "pt": "葡萄牙语"
}

# 支持的医学领域
MEDICAL_DOMAINS = [
    "general",           # 通用医学
    "clinical",          # 临床医学
    "pharmacology",      # 药理学
    "pathology",         # 病理学
    "diagnosis",         # 诊断学
    "surgery",           # 外科学
    "internal_medicine", # 内科学
    "pediatrics",        # 儿科学
    "oncology",          # 肿瘤学
    "neurology",         # 神经学
    "cardiology",        # 心脏病学
    "dermatology",       # 皮肤病学
    "psychiatry",        # 精神病学
    "radiology",         # 放射学
    "laboratory"         # 实验室医学
]


@tool
def translate_text(text: str, 
                   source_lang: str, 
                   target_lang: str,
                   glossary_name: Optional[str] = None,
                   domain: str = "general",
                   use_ai: bool = True,
                   context: Optional[str] = None,
                   cache_dir: Optional[str] = None) -> str:
    """
    翻译单个文本，支持词库和AI翻译
    
    Args:
        text (str): 要翻译的文本
        source_lang (str): 源语言代码（如'en', 'zh'）
        target_lang (str): 目标语言代码（如'zh', 'en'）
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域（默认为'general'）
        use_ai (bool): 是否使用AI翻译（默认为True）
        context (Optional[str]): 上下文信息（可选）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的翻译结果
    """
    try:
        # 验证语言代码
        if source_lang not in SUPPORTED_LANGUAGES:
            return json.dumps({
                "success": False,
                "error": f"不支持的源语言: {source_lang}，支持的语言有: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            }, ensure_ascii=False)
            
        if target_lang not in SUPPORTED_LANGUAGES:
            return json.dumps({
                "success": False,
                "error": f"不支持的目标语言: {target_lang}，支持的语言有: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            }, ensure_ascii=False)
        
        # 验证医学领域
        if domain not in MEDICAL_DOMAINS:
            return json.dumps({
                "success": False,
                "error": f"不支持的医学领域: {domain}，支持的领域有: {', '.join(MEDICAL_DOMAINS)}"
            }, ensure_ascii=False)
        
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 创建翻译结果
        result = {
            "source_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "translation": "",
            "glossary_matches": [],
            "used_ai": False,
            "confidence": 0.0
        }
        
        # 检查缓存
        cache_key = hashlib.md5(f"{text}:{source_lang}:{target_lang}:{domain}:{glossary_name or ''}".encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_result = json.load(f)
                
                # 检查缓存是否有效（不超过7天）
                cache_time = datetime.datetime.fromisoformat(cached_result.get("timestamp", "1970-01-01T00:00:00"))
                now = datetime.datetime.now()
                
                if (now - cache_time).days < 7:
                    return json.dumps(cached_result, ensure_ascii=False)
            except:
                # 忽略缓存错误
                pass
        
        # 如果提供了词库名称，使用词库进行术语匹配
        if glossary_name:
            glossary_dir = os.path.join(".cache", "medical_translator", "glossaries")
            glossary_file = os.path.join(glossary_dir, f"{glossary_name}.json")
            
            if os.path.exists(glossary_file):
                # 加载词库
                with open(glossary_file, 'r', encoding='utf-8') as f:
                    glossary_data = json.load(f)
                
                if "terms" in glossary_data:
                    # 按长度排序术语，优先匹配长术语
                    source_field = "source_term"
                    target_field = "target_term"
                    
                    sorted_terms = sorted(
                        glossary_data["terms"],
                        key=lambda x: len(x.get(source_field, "")),
                        reverse=True
                    )
                    
                    # 匹配结果
                    matches = []
                    processed_text = text
                    
                    # 对每个术语进行匹配
                    for term in sorted_terms:
                        source = term.get(source_field, "")
                        target = term.get(target_field, "")
                        
                        if not source or not target:
                            continue
                        
                        # 使用正则表达式匹配术语
                        pattern = r'\b' + re.escape(source) + r'\b'
                        matches_found = list(re.finditer(pattern, processed_text))
                        
                        if matches_found:
                            # 记录匹配
                            for match in matches_found:
                                start, end = match.span()
                                matches.append({
                                    "term_id": term.get("term_id"),
                                    "source": source,
                                    "target": target,
                                    "position": {
                                        "start": start,
                                        "end": end
                                    },
                                    "confidence": term.get("confidence", 1.0)
                                })
                            
                            # 更新术语使用计数
                            term["usage_count"] = term.get("usage_count", 0) + len(matches_found)
                            
                            # 替换已匹配的术语为占位符
                            processed_text = re.sub(pattern, f"__TERM_{len(matches) - 1}__", processed_text)
                    
                    # 保存更新后的词库
                    with open(glossary_file, 'w', encoding='utf-8') as f:
                        json.dump(glossary_data, f, ensure_ascii=False, indent=2)
                    
                    # 如果所有文本都被词库覆盖，直接返回结果
                    if not re.search(r'[^\s\W_]', processed_text.replace("__TERM_", "")):
                        # 恢复占位符为目标语言术语
                        translated_text = processed_text
                        for i, match in enumerate(matches):
                            translated_text = translated_text.replace(f"__TERM_{i}__", match["target"])
                        
                        result["translation"] = translated_text
                        result["glossary_matches"] = matches
                        result["confidence"] = 1.0
                        result["used_ai"] = False
                        
                        # 缓存结果
                        result["timestamp"] = datetime.datetime.now().isoformat()
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, ensure_ascii=False, indent=2)
                        
                        return json.dumps(result, ensure_ascii=False)
                    
                    # 如果有部分文本未被词库覆盖，并且允许使用AI翻译
                    if use_ai:
                        # 使用AI翻译未匹配的部分
                        ai_text = processed_text
                        for i, match in enumerate(matches):
                            # 将术语占位符替换为源语言术语，以便AI翻译时保持上下文
                            ai_text = ai_text.replace(f"__TERM_{i}__", match["source"])
                        
                        # 调用AI翻译
                        ai_result = _translate_with_ai(ai_text, source_lang, target_lang, domain, context)
                        
                        if ai_result["success"]:
                            ai_translated = ai_result["translation"]
                            
                            # 将AI翻译结果中的术语替换为词库中的对应术语
                            final_text = ai_translated
                            for match in matches:
                                source = match["source"]
                                target = match["target"]
                                
                                # 使用正则表达式替换术语
                                pattern = r'\b' + re.escape(source) + r'\b'
                                final_text = re.sub(pattern, target, final_text)
                            
                            result["translation"] = final_text
                            result["glossary_matches"] = matches
                            result["used_ai"] = True
                            result["confidence"] = 0.8  # 混合翻译的置信度
                            
                            # 缓存结果
                            result["timestamp"] = datetime.datetime.now().isoformat()
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(result, f, ensure_ascii=False, indent=2)
                            
                            return json.dumps(result, ensure_ascii=False)
        
        # 如果没有词库或词库未覆盖所有文本，且允许使用AI翻译
        if use_ai:
            ai_result = _translate_with_ai(text, source_lang, target_lang, domain, context)
            
            if ai_result["success"]:
                result["translation"] = ai_result["translation"]
                result["used_ai"] = True
                result["confidence"] = 0.7  # 纯AI翻译的置信度
                
                # 缓存结果
                result["timestamp"] = datetime.datetime.now().isoformat()
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                return json.dumps(result, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"AI翻译失败: {ai_result.get('error', '未知错误')}"
                }, ensure_ascii=False)
        
        # 如果不允许使用AI翻译，且词库未覆盖所有文本
        return json.dumps({
            "success": False,
            "error": "文本未被词库完全覆盖，且未启用AI翻译"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"翻译文本时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def translate_batch(texts: List[str], 
                    source_lang: str, 
                    target_lang: str,
                    glossary_name: Optional[str] = None,
                    domain: str = "general",
                    use_ai: bool = True,
                    context: Optional[str] = None,
                    cache_dir: Optional[str] = None) -> str:
    """
    批量翻译多个文本
    
    Args:
        texts (List[str]): 要翻译的文本列表
        source_lang (str): 源语言代码（如'en', 'zh'）
        target_lang (str): 目标语言代码（如'zh', 'en'）
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域（默认为'general'）
        use_ai (bool): 是否使用AI翻译（默认为True）
        context (Optional[str]): 上下文信息（可选）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的批量翻译结果
    """
    try:
        # 验证语言代码
        if source_lang not in SUPPORTED_LANGUAGES:
            return json.dumps({
                "success": False,
                "error": f"不支持的源语言: {source_lang}，支持的语言有: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            }, ensure_ascii=False)
            
        if target_lang not in SUPPORTED_LANGUAGES:
            return json.dumps({
                "success": False,
                "error": f"不支持的目标语言: {target_lang}，支持的语言有: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            }, ensure_ascii=False)
        
        # 验证医学领域
        if domain not in MEDICAL_DOMAINS:
            return json.dumps({
                "success": False,
                "error": f"不支持的医学领域: {domain}，支持的领域有: {', '.join(MEDICAL_DOMAINS)}"
            }, ensure_ascii=False)
        
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 批量翻译结果
        results = []
        success_count = 0
        failed_count = 0
        
        # 逐个翻译文本
        for i, text in enumerate(texts):
            if not text.strip():
                # 跳过空文本
                results.append({
                    "index": i,
                    "source_text": text,
                    "translation": "",
                    "success": True,
                    "empty": True
                })
                success_count += 1
                continue
            
            # 调用单文本翻译
            result_json = translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                glossary_name=glossary_name,
                domain=domain,
                use_ai=use_ai,
                context=context,
                cache_dir=cache_dir
            )
            
            result = json.loads(result_json)
            
            # 添加索引
            result["index"] = i
            
            if "success" in result and result["success"] is False:
                failed_count += 1
            else:
                success_count += 1
            
            results.append(result)
        
        # 构建批量结果
        batch_result = {
            "success": failed_count == 0,
            "total": len(texts),
            "success_count": success_count,
            "failed_count": failed_count,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "results": results,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return json.dumps(batch_result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"批量翻译文本时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def translate_with_context(text: str, 
                           source_lang: str, 
                           target_lang: str,
                           context_before: Optional[str] = None,
                           context_after: Optional[str] = None,
                           glossary_name: Optional[str] = None,
                           domain: str = "general",
                           use_ai: bool = True,
                           cache_dir: Optional[str] = None) -> str:
    """
    使用上下文进行翻译，提高翻译准确性
    
    Args:
        text (str): 要翻译的文本
        source_lang (str): 源语言代码（如'en', 'zh'）
        target_lang (str): 目标语言代码（如'zh', 'en'）
        context_before (Optional[str]): 前置上下文（可选）
        context_after (Optional[str]): 后置上下文（可选）
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域（默认为'general'）
        use_ai (bool): 是否使用AI翻译（默认为True）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的翻译结果
    """
    try:
        # 构建完整上下文
        full_context = ""
        if context_before:
            full_context += context_before + "\n\n"
        
        full_context += text
        
        if context_after:
            full_context += "\n\n" + context_after
        
        # 使用上下文调用翻译
        result_json = translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_name=glossary_name,
            domain=domain,
            use_ai=use_ai,
            context=full_context,
            cache_dir=cache_dir
        )
        
        result = json.loads(result_json)
        
        # 添加上下文信息
        if "success" not in result or result["success"] is not False:
            result["has_context"] = bool(context_before or context_after)
            result["context_before"] = context_before
            result["context_after"] = context_after
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"使用上下文翻译时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def translate_with_domain_adaptation(text: str, 
                                     source_lang: str, 
                                     target_lang: str,
                                     primary_domain: str,
                                     secondary_domain: Optional[str] = None,
                                     glossary_name: Optional[str] = None,
                                     use_ai: bool = True,
                                     cache_dir: Optional[str] = None) -> str:
    """
    使用领域适应进行翻译，适用于跨医学领域的文本
    
    Args:
        text (str): 要翻译的文本
        source_lang (str): 源语言代码（如'en', 'zh'）
        target_lang (str): 目标语言代码（如'zh', 'en'）
        primary_domain (str): 主要医学领域
        secondary_domain (Optional[str]): 次要医学领域（可选）
        glossary_name (Optional[str]): 词库名称（可选）
        use_ai (bool): 是否使用AI翻译（默认为True）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的翻译结果
    """
    try:
        # 验证主要医学领域
        if primary_domain not in MEDICAL_DOMAINS:
            return json.dumps({
                "success": False,
                "error": f"不支持的主要医学领域: {primary_domain}，支持的领域有: {', '.join(MEDICAL_DOMAINS)}"
            }, ensure_ascii=False)
        
        # 验证次要医学领域
        if secondary_domain and secondary_domain not in MEDICAL_DOMAINS:
            return json.dumps({
                "success": False,
                "error": f"不支持的次要医学领域: {secondary_domain}，支持的领域有: {', '.join(MEDICAL_DOMAINS)}"
            }, ensure_ascii=False)
        
        # 构建领域上下文
        domain_context = f"这是一篇{MEDICAL_DOMAINS.get(primary_domain, '医学')}领域的文本"
        if secondary_domain:
            domain_context += f"，同时涉及{MEDICAL_DOMAINS.get(secondary_domain, '医学')}领域"
        
        # 使用主要领域调用翻译
        result_json = translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_name=glossary_name,
            domain=primary_domain,
            use_ai=use_ai,
            context=domain_context,
            cache_dir=cache_dir
        )
        
        result = json.loads(result_json)
        
        # 添加领域信息
        if "success" not in result or result["success"] is not False:
            result["primary_domain"] = primary_domain
            result["secondary_domain"] = secondary_domain
            result["domain_context"] = domain_context
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"使用领域适应翻译时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def translate_abbreviations(text: str, 
                            source_lang: str, 
                            target_lang: str,
                            expand_abbreviations: bool = True,
                            glossary_name: Optional[str] = None,
                            domain: str = "general",
                            use_ai: bool = True,
                            cache_dir: Optional[str] = None) -> str:
    """
    处理医学缩写的翻译
    
    Args:
        text (str): 要翻译的文本
        source_lang (str): 源语言代码（如'en', 'zh'）
        target_lang (str): 目标语言代码（如'zh', 'en'）
        expand_abbreviations (bool): 是否展开缩写（默认为True）
        glossary_name (Optional[str]): 词库名称（可选）
        domain (str): 医学领域（默认为'general'）
        use_ai (bool): 是否使用AI翻译（默认为True）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的翻译结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(cache_dir, exist_ok=True)
        
        # 创建翻译结果
        result = {
            "source_text": text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "domain": domain,
            "translation": "",
            "abbreviations": [],
            "expanded_text": text,
            "used_ai": False,
            "confidence": 0.0
        }
        
        # 查找常见医学缩写
        abbreviations = _find_abbreviations(text, source_lang, domain)
        
        if abbreviations and expand_abbreviations:
            # 展开缩写
            expanded_text = text
            for abbr in abbreviations:
                if abbr["expansion"]:
                    # 替换缩写为全称
                    pattern = r'\b' + re.escape(abbr["abbreviation"]) + r'\b'
                    expanded_text = re.sub(pattern, f"{abbr['abbreviation']} ({abbr['expansion']})", expanded_text)
            
            result["expanded_text"] = expanded_text
            result["abbreviations"] = abbreviations
            
            # 使用展开后的文本进行翻译
            expanded_result_json = translate_text(
                text=expanded_text,
                source_lang=source_lang,
                target_lang=target_lang,
                glossary_name=glossary_name,
                domain=domain,
                use_ai=use_ai,
                cache_dir=cache_dir
            )
            
            expanded_result = json.loads(expanded_result_json)
            
            if "success" not in expanded_result or expanded_result["success"] is not False:
                result["translation"] = expanded_result.get("translation", "")
                result["used_ai"] = expanded_result.get("used_ai", False)
                result["confidence"] = expanded_result.get("confidence", 0.0)
                result["glossary_matches"] = expanded_result.get("glossary_matches", [])
                
                return json.dumps(result, ensure_ascii=False)
        
        # 如果没有找到缩写或不需要展开，直接翻译
        direct_result_json = translate_text(
            text=text,
            source_lang=source_lang,
            target_lang=target_lang,
            glossary_name=glossary_name,
            domain=domain,
            use_ai=use_ai,
            cache_dir=cache_dir
        )
        
        direct_result = json.loads(direct_result_json)
        
        if "success" not in direct_result or direct_result["success"] is not False:
            result["translation"] = direct_result.get("translation", "")
            result["used_ai"] = direct_result.get("used_ai", False)
            result["confidence"] = direct_result.get("confidence", 0.0)
            result["glossary_matches"] = direct_result.get("glossary_matches", [])
            result["abbreviations"] = abbreviations
            
            return json.dumps(result, ensure_ascii=False)
        else:
            return direct_result_json
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"处理缩写翻译时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_supported_languages() -> str:
    """
    获取支持的语言列表
    
    Returns:
        str: JSON格式的支持语言列表
    """
    try:
        languages = []
        for code, name in SUPPORTED_LANGUAGES.items():
            languages.append({
                "code": code,
                "name": name
            })
        
        return json.dumps({
            "success": True,
            "languages": languages,
            "count": len(languages)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取支持语言列表时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def get_supported_domains() -> str:
    """
    获取支持的医学领域列表
    
    Returns:
        str: JSON格式的支持医学领域列表
    """
    try:
        domains = []
        for domain in MEDICAL_DOMAINS:
            domains.append({
                "code": domain,
                "name": domain.replace('_', ' ').title()
            })
        
        return json.dumps({
            "success": True,
            "domains": domains,
            "count": len(domains)
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取支持医学领域列表时出错: {str(e)}"
        }, ensure_ascii=False)


@tool
def clear_translation_cache(cache_key: Optional[str] = None, 
                            older_than_days: Optional[int] = None,
                            cache_dir: Optional[str] = None) -> str:
    """
    清除翻译缓存
    
    Args:
        cache_key (Optional[str]): 特定缓存键（可选）
        older_than_days (Optional[int]): 清除指定天数以前的缓存（可选）
        cache_dir (Optional[str]): 缓存目录（可选）
        
    Returns:
        str: JSON格式的操作结果
    """
    try:
        # 确定缓存目录
        cache_dir = cache_dir or DEFAULT_CACHE_DIR
        
        if not os.path.exists(cache_dir):
            return json.dumps({
                "success": True,
                "message": "缓存目录不存在，无需清理",
                "deleted_count": 0
            }, ensure_ascii=False)
        
        deleted_count = 0
        
        # 清除特定缓存
        if cache_key:
            cache_file = os.path.join(cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                deleted_count += 1
                
            return json.dumps({
                "success": True,
                "message": f"已清除指定的缓存: {cache_key}",
                "deleted_count": deleted_count
            }, ensure_ascii=False)
        
        # 清除指定天数以前的缓存
        if older_than_days is not None:
            cutoff_time = datetime.datetime.now() - datetime.timedelta(days=older_than_days)
            
            for filename in os.listdir(cache_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(cache_dir, filename)
                    
                    try:
                        # 获取文件修改时间
                        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        # 检查文件是否过期
                        if file_time < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                    except:
                        # 忽略文件操作错误
                        pass
            
            return json.dumps({
                "success": True,
                "message": f"已清除 {older_than_days} 天前的缓存",
                "deleted_count": deleted_count
            }, ensure_ascii=False)
        
        # 清除所有缓存
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(cache_dir, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except:
                    # 忽略文件操作错误
                    pass
        
        return json.dumps({
            "success": True,
            "message": "已清除所有翻译缓存",
            "deleted_count": deleted_count
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"清除翻译缓存时出错: {str(e)}"
        }, ensure_ascii=False)


# 辅助函数
def _translate_with_ai(text: str, 
                      source_lang: str, 
                      target_lang: str, 
                      domain: str = "general",
                      context: Optional[str] = None) -> Dict[str, Any]:
    """
    使用AWS Bedrock进行AI翻译
    
    Args:
        text (str): 要翻译的文本
        source_lang (str): 源语言代码
        target_lang (str): 目标语言代码
        domain (str): 医学领域
        context (Optional[str]): 上下文信息
        
    Returns:
        Dict[str, Any]: 翻译结果
    """
    try:
        # 创建Bedrock客户端
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-west-2'  # 使用适当的区域
        )
        
        # 构建提示词
        prompt = f"""请将以下{SUPPORTED_LANGUAGES.get(source_lang, '源语言')}医学文本翻译成{SUPPORTED_LANGUAGES.get(target_lang, '目标语言')}。
这是一篇关于{domain.replace('_', ' ')}领域的医学文本。请确保翻译准确、专业，并保持医学术语的一致性。

源文本:
{text}

"""
        
        if context:
            prompt += f"\n上下文信息:\n{context}\n"
        
        # 调用Claude模型
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # 解析响应
        response_body = json.loads(response['body'].read().decode('utf-8'))
        translation = response_body['content'][0]['text']
        
        # 清理翻译结果
        translation = translation.strip()
        
        # 如果翻译结果以"翻译:"开头，移除这个前缀
        prefixes = ["翻译:", "翻译：", "Translation:", "Translated text:"]
        for prefix in prefixes:
            if translation.startswith(prefix):
                translation = translation[len(prefix):].strip()
        
        return {
            "success": True,
            "translation": translation
        }
    
    except ClientError as e:
        return {
            "success": False,
            "error": f"AWS Bedrock API错误: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"AI翻译错误: {str(e)}"
        }


def _find_abbreviations(text: str, lang: str, domain: str) -> List[Dict[str, Any]]:
    """
    在文本中查找医学缩写
    
    Args:
        text (str): 文本内容
        lang (str): 语言代码
        domain (str): 医学领域
        
    Returns:
        List[Dict[str, Any]]: 找到的缩写列表
    """
    # 常见英文医学缩写正则表达式
    en_abbr_pattern = r'\b([A-Z]{2,})\b'
    
    # 中文医学缩写通常是英文字母缩写
    zh_abbr_pattern = r'\b([A-Z]{2,})\b'
    
    abbreviations = []
    
    if lang == 'en':
        # 查找英文缩写
        matches = re.finditer(en_abbr_pattern, text)
        for match in matches:
            abbr = match.group(1)
            expansion = _get_abbreviation_expansion(abbr, lang, domain)
            
            if expansion:
                abbreviations.append({
                    "abbreviation": abbr,
                    "expansion": expansion,
                    "position": {
                        "start": match.start(),
                        "end": match.end()
                    }
                })
    
    elif lang == 'zh':
        # 查找中文文本中的英文缩写
        matches = re.finditer(zh_abbr_pattern, text)
        for match in matches:
            abbr = match.group(1)
            expansion = _get_abbreviation_expansion(abbr, 'en', domain)  # 中文文本中的缩写通常是英文缩写
            
            if expansion:
                abbreviations.append({
                    "abbreviation": abbr,
                    "expansion": expansion,
                    "position": {
                        "start": match.start(),
                        "end": match.end()
                    }
                })
    
    return abbreviations


def _get_abbreviation_expansion(abbr: str, lang: str, domain: str) -> Optional[str]:
    """
    获取缩写的全称
    
    Args:
        abbr (str): 缩写
        lang (str): 语言代码
        domain (str): 医学领域
        
    Returns:
        Optional[str]: 缩写的全称，如果找不到则返回None
    """
    # 常见医学缩写词典
    common_medical_abbreviations = {
        "BP": "Blood Pressure",
        "HR": "Heart Rate",
        "RR": "Respiratory Rate",
        "T": "Temperature",
        "SpO2": "Oxygen Saturation",
        "CBC": "Complete Blood Count",
        "BMP": "Basic Metabolic Panel",
        "CMP": "Comprehensive Metabolic Panel",
        "BUN": "Blood Urea Nitrogen",
        "Cr": "Creatinine",
        "Na": "Sodium",
        "K": "Potassium",
        "Cl": "Chloride",
        "CO2": "Carbon Dioxide",
        "Ca": "Calcium",
        "Mg": "Magnesium",
        "PO4": "Phosphate",
        "Glu": "Glucose",
        "HbA1c": "Hemoglobin A1c",
        "PT": "Prothrombin Time",
        "PTT": "Partial Thromboplastin Time",
        "INR": "International Normalized Ratio",
        "WBC": "White Blood Cell",
        "RBC": "Red Blood Cell",
        "Hgb": "Hemoglobin",
        "Hct": "Hematocrit",
        "MCV": "Mean Corpuscular Volume",
        "MCH": "Mean Corpuscular Hemoglobin",
        "MCHC": "Mean Corpuscular Hemoglobin Concentration",
        "PLT": "Platelet",
        "ESR": "Erythrocyte Sedimentation Rate",
        "CRP": "C-Reactive Protein",
        "LFT": "Liver Function Test",
        "AST": "Aspartate Aminotransferase",
        "ALT": "Alanine Aminotransferase",
        "ALP": "Alkaline Phosphatase",
        "GGT": "Gamma-Glutamyl Transferase",
        "TB": "Total Bilirubin",
        "DB": "Direct Bilirubin",
        "TP": "Total Protein",
        "Alb": "Albumin",
        "BNP": "Brain Natriuretic Peptide",
        "CK": "Creatine Kinase",
        "CK-MB": "Creatine Kinase-MB",
        "LDH": "Lactate Dehydrogenase",
        "Trop": "Troponin",
        "TSH": "Thyroid Stimulating Hormone",
        "T3": "Triiodothyronine",
        "T4": "Thyroxine",
        "FT3": "Free Triiodothyronine",
        "FT4": "Free Thyroxine",
        "PSA": "Prostate Specific Antigen",
        "CEA": "Carcinoembryonic Antigen",
        "AFP": "Alpha-Fetoprotein",
        "CA-125": "Cancer Antigen 125",
        "CA-19-9": "Cancer Antigen 19-9",
        "EKG": "Electrocardiogram",
        "ECG": "Electrocardiogram",
        "ECHO": "Echocardiogram",
        "CT": "Computed Tomography",
        "MRI": "Magnetic Resonance Imaging",
        "US": "Ultrasound",
        "CXR": "Chest X-Ray",
        "KUB": "Kidneys, Ureters, Bladder X-Ray",
        "IVP": "Intravenous Pyelogram",
        "UGI": "Upper Gastrointestinal Series",
        "BE": "Barium Enema",
        "ERCP": "Endoscopic Retrograde Cholangiopancreatography",
        "EGD": "Esophagogastroduodenoscopy",
        "EUS": "Endoscopic Ultrasound",
        "MRCP": "Magnetic Resonance Cholangiopancreatography",
        "PET": "Positron Emission Tomography",
        "PFT": "Pulmonary Function Test",
        "ABG": "Arterial Blood Gas",
        "COPD": "Chronic Obstructive Pulmonary Disease",
        "CHF": "Congestive Heart Failure",
        "CAD": "Coronary Artery Disease",
        "MI": "Myocardial Infarction",
        "CVA": "Cerebrovascular Accident",
        "TIA": "Transient Ischemic Attack",
        "DVT": "Deep Vein Thrombosis",
        "PE": "Pulmonary Embolism",
        "HTN": "Hypertension",
        "DM": "Diabetes Mellitus",
        "CKD": "Chronic Kidney Disease",
        "ESRD": "End-Stage Renal Disease",
        "HD": "Hemodialysis",
        "PD": "Peritoneal Dialysis",
        "RA": "Rheumatoid Arthritis",
        "SLE": "Systemic Lupus Erythematosus",
        "IBD": "Inflammatory Bowel Disease",
        "UC": "Ulcerative Colitis",
        "CD": "Crohn's Disease",
        "GERD": "Gastroesophageal Reflux Disease",
        "PUD": "Peptic Ulcer Disease",
        "UTI": "Urinary Tract Infection",
        "URI": "Upper Respiratory Infection",
        "LRI": "Lower Respiratory Infection",
        "CAP": "Community-Acquired Pneumonia",
        "HAP": "Hospital-Acquired Pneumonia",
        "VAP": "Ventilator-Associated Pneumonia",
        "TB": "Tuberculosis",
        "HIV": "Human Immunodeficiency Virus",
        "AIDS": "Acquired Immunodeficiency Syndrome",
        "HBV": "Hepatitis B Virus",
        "HCV": "Hepatitis C Virus",
        "HSV": "Herpes Simplex Virus",
        "HPV": "Human Papillomavirus",
        "STI": "Sexually Transmitted Infection",
        "PID": "Pelvic Inflammatory Disease",
        "BPH": "Benign Prostatic Hyperplasia",
        "ED": "Erectile Dysfunction",
        "PCOS": "Polycystic Ovary Syndrome",
        "PMS": "Premenstrual Syndrome",
        "OA": "Osteoarthritis",
        "OP": "Osteoporosis",
        "RA": "Rheumatoid Arthritis",
        "SLE": "Systemic Lupus Erythematosus",
        "MS": "Multiple Sclerosis",
        "ALS": "Amyotrophic Lateral Sclerosis",
        "AD": "Alzheimer's Disease",
        "PD": "Parkinson's Disease",
        "ADHD": "Attention Deficit Hyperactivity Disorder",
        "OCD": "Obsessive-Compulsive Disorder",
        "PTSD": "Post-Traumatic Stress Disorder",
        "MDD": "Major Depressive Disorder",
        "GAD": "Generalized Anxiety Disorder",
        "BD": "Bipolar Disorder",
        "SCZ": "Schizophrenia",
        "BMI": "Body Mass Index",
        "NPO": "Nothing by Mouth",
        "PRN": "As Needed",
        "QD": "Once Daily",
        "BID": "Twice Daily",
        "TID": "Three Times Daily",
        "QID": "Four Times Daily",
        "AC": "Before Meals",
        "PC": "After Meals",
        "HS": "At Bedtime",
        "PO": "By Mouth",
        "IV": "Intravenous",
        "IM": "Intramuscular",
        "SC": "Subcutaneous",
        "SL": "Sublingual",
        "PR": "Per Rectum",
        "PV": "Per Vagina",
        "NGT": "Nasogastric Tube",
        "NJ": "Nasojejunal",
        "PEG": "Percutaneous Endoscopic Gastrostomy",
        "PEJ": "Percutaneous Endoscopic Jejunostomy",
        "ETT": "Endotracheal Tube",
        "LMA": "Laryngeal Mask Airway",
        "NIPPV": "Non-Invasive Positive Pressure Ventilation",
        "CPAP": "Continuous Positive Airway Pressure",
        "BiPAP": "Bilevel Positive Airway Pressure",
        "HFNC": "High-Flow Nasal Cannula",
        "NC": "Nasal Cannula",
        "NRB": "Non-Rebreather Mask",
        "VM": "Venturi Mask",
        "PEEP": "Positive End-Expiratory Pressure",
        "FiO2": "Fraction of Inspired Oxygen",
        "TV": "Tidal Volume",
        "RR": "Respiratory Rate",
        "IE": "Inspiratory to Expiratory Ratio",
        "SIMV": "Synchronized Intermittent Mandatory Ventilation",
        "AC": "Assist Control",
        "PS": "Pressure Support",
        "PC": "Pressure Control",
        "VC": "Volume Control",
        "PRVC": "Pressure-Regulated Volume Control",
        "APRV": "Airway Pressure Release Ventilation",
        "HFOV": "High-Frequency Oscillatory Ventilation",
        "ECMO": "Extracorporeal Membrane Oxygenation",
        "CPR": "Cardiopulmonary Resuscitation",
        "ACLS": "Advanced Cardiac Life Support",
        "BLS": "Basic Life Support",
        "AED": "Automated External Defibrillator",
        "VF": "Ventricular Fibrillation",
        "VT": "Ventricular Tachycardia",
        "SVT": "Supraventricular Tachycardia",
        "AF": "Atrial Fibrillation",
        "AFL": "Atrial Flutter",
        "AV": "Atrioventricular",
        "SA": "Sinoatrial",
        "NSR": "Normal Sinus Rhythm",
        "BBB": "Bundle Branch Block",
        "LBBB": "Left Bundle Branch Block",
        "RBBB": "Right Bundle Branch Block",
        "PVC": "Premature Ventricular Contraction",
        "PAC": "Premature Atrial Contraction",
        "PJC": "Premature Junctional Contraction",
        "AV": "Atrioventricular",
        "WPW": "Wolff-Parkinson-White",
        "STEMI": "ST-Elevation Myocardial Infarction",
        "NSTEMI": "Non-ST-Elevation Myocardial Infarction",
        "UA": "Unstable Angina",
        "ACS": "Acute Coronary Syndrome",
        "HF": "Heart Failure",
        "HFrEF": "Heart Failure with Reduced Ejection Fraction",
        "HFpEF": "Heart Failure with Preserved Ejection Fraction",
        "EF": "Ejection Fraction",
        "AS": "Aortic Stenosis",
        "AR": "Aortic Regurgitation",
        "MS": "Mitral Stenosis",
        "MR": "Mitral Regurgitation",
        "TR": "Tricuspid Regurgitation",
        "PR": "Pulmonic Regurgitation",
        "MVP": "Mitral Valve Prolapse",
        "VSD": "Ventricular Septal Defect",
        "ASD": "Atrial Septal Defect",
        "PDA": "Patent Ductus Arteriosus",
        "TOF": "Tetralogy of Fallot",
        "TGA": "Transposition of the Great Arteries",
        "HLHS": "Hypoplastic Left Heart Syndrome",
        "CABG": "Coronary Artery Bypass Graft",
        "PCI": "Percutaneous Coronary Intervention",
        "PTCA": "Percutaneous Transluminal Coronary Angioplasty",
        "IABP": "Intra-Aortic Balloon Pump",
        "VAD": "Ventricular Assist Device",
        "ICD": "Implantable Cardioverter-Defibrillator",
        "PPM": "Permanent Pacemaker",
        "TPM": "Temporary Pacemaker",
        "CRT": "Cardiac Resynchronization Therapy",
        "EP": "Electrophysiology",
        "EPS": "Electrophysiology Study",
        "TEE": "Transesophageal Echocardiogram",
        "TTE": "Transthoracic Echocardiogram",
        "CTA": "Computed Tomography Angiography",
        "MRA": "Magnetic Resonance Angiography",
        "DSA": "Digital Subtraction Angiography",
        "PVD": "Peripheral Vascular Disease",
        "AAA": "Abdominal Aortic Aneurysm",
        "TAA": "Thoracic Aortic Aneurysm",
        "AVM": "Arteriovenous Malformation",
        "AVF": "Arteriovenous Fistula",
        "AVG": "Arteriovenous Graft"
    }
    
    # 特定领域的缩写词典
    domain_specific_abbreviations = {
        "clinical": {
            "Dx": "Diagnosis",
            "Tx": "Treatment",
            "Hx": "History",
            "PMH": "Past Medical History",
            "FH": "Family History",
            "SH": "Social History",
            "ROS": "Review of Systems",
            "PE": "Physical Examination",
            "VS": "Vital Signs",
            "CC": "Chief Complaint",
            "HPI": "History of Present Illness",
            "A/P": "Assessment and Plan"
        },
        "pharmacology": {
            "PO": "Per Os (by mouth)",
            "IV": "Intravenous",
            "IM": "Intramuscular",
            "SC": "Subcutaneous",
            "SL": "Sublingual",
            "PR": "Per Rectum",
            "PV": "Per Vagina",
            "QD": "Once Daily",
            "BID": "Twice Daily",
            "TID": "Three Times Daily",
            "QID": "Four Times Daily",
            "PRN": "As Needed",
            "STAT": "Immediately",
            "NPO": "Nothing by Mouth",
            "AC": "Before Meals",
            "PC": "After Meals",
            "HS": "At Bedtime"
        }
    }
    
    # 查找缩写全称
    expansion = None
    
    # 先查找特定领域的缩写
    if domain in domain_specific_abbreviations and abbr in domain_specific_abbreviations[domain]:
        expansion = domain_specific_abbreviations[domain][abbr]
    
    # 如果没有找到，查找通用医学缩写
    if not expansion and abbr in common_medical_abbreviations:
        expansion = common_medical_abbreviations[abbr]
    
    return expansion