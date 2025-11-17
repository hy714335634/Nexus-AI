"""
文档生成工具

此模块为document_writer_agent提供文档生成和修改功能，
包括需求解析、文档结构生成、内容优化和反馈处理。
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from strands import tool


@tool
def parse_user_requirement(
    user_input: str,
    requirement_type: str = "auto"
) -> str:
    """
    解析用户需求，识别文档类型和关键信息
    
    此工具分析用户的自然语言输入，提取关键需求信息，
    为文档生成提供结构化的需求描述。
    
    Args:
        user_input (str): 用户的自然语言需求描述
        requirement_type (str): 需求类型提示，可选值：
            - "auto": 自动检测
            - "api_doc": API文档
            - "user_manual": 用户手册
            - "design_doc": 设计文档
            - "tutorial": 教程
            - "technical_spec": 技术规格说明
            
    Returns:
        str: JSON格式的需求分析结果，包含：
            {
                "status": "success",
                "requirement_analysis": {
                    "document_type": "文档类型",
                    "main_topic": "主题",
                    "key_requirements": [...],  # 关键需求列表
                    "target_audience": "目标读者",
                    "technical_level": "技术水平",
                    "suggested_sections": [...]  # 建议章节
                },
                "extracted_keywords": [...],  # 提取的关键词
                "complexity_level": "simple" | "moderate" | "complex"
            }
    """
    try:
        # 清理输入
        user_input = user_input.strip()
        
        if not user_input:
            raise ValueError("用户输入不能为空")
        
        # 检测文档类型
        detected_type = _detect_document_type(user_input, requirement_type)
        
        # 提取关键词
        keywords = _extract_keywords(user_input)
        
        # 识别主题
        main_topic = _identify_main_topic(user_input, keywords)
        
        # 分析技术水平
        technical_level = _analyze_technical_level(user_input)
        
        # 识别目标读者
        target_audience = _identify_target_audience(user_input, technical_level)
        
        # 提取关键需求
        key_requirements = _extract_key_requirements(user_input)
        
        # 建议章节结构
        suggested_sections = _suggest_sections(detected_type, key_requirements)
        
        # 评估复杂度
        complexity_level = _assess_complexity(user_input, key_requirements)
        
        # 构建响应
        response = {
            "status": "success",
            "requirement_analysis": {
                "document_type": detected_type,
                "main_topic": main_topic,
                "key_requirements": key_requirements,
                "target_audience": target_audience,
                "technical_level": technical_level,
                "suggested_sections": suggested_sections,
                "original_input": user_input
            },
            "extracted_keywords": keywords,
            "complexity_level": complexity_level
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _detect_document_type(user_input: str, hint: str) -> str:
    """检测文档类型"""
    if hint != "auto":
        return hint
    
    input_lower = user_input.lower()
    
    type_patterns = {
        "api_doc": ["api", "endpoint", "rest", "graphql", "接口", "api文档"],
        "user_manual": ["使用", "操作", "手册", "指南", "manual", "guide"],
        "design_doc": ["设计", "架构", "design", "architecture"],
        "tutorial": ["教程", "入门", "学习", "tutorial", "learn"],
        "technical_spec": ["规格", "规范", "specification", "标准"]
    }
    
    for doc_type, patterns in type_patterns.items():
        if any(pattern in input_lower for pattern in patterns):
            return doc_type
    
    return "technical_doc"


def _extract_keywords(text: str) -> List[str]:
    """提取关键词"""
    # 移除标点和特殊字符
    cleaned = re.sub(r'[^\w\s]', ' ', text)
    words = cleaned.split()
    
    # 简单的关键词提取（可以使用更复杂的NLP方法）
    keywords = [w for w in words if len(w) > 3]
    
    # 去重并保持顺序
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)
    
    return unique_keywords[:10]  # 返回前10个关键词


def _identify_main_topic(text: str, keywords: List[str]) -> str:
    """识别主题"""
    # 使用第一个句子和关键词推断主题
    first_sentence = text.split('.')[0].strip()
    
    if keywords:
        return f"{first_sentence} (关键词: {', '.join(keywords[:3])})"
    
    return first_sentence


def _analyze_technical_level(text: str) -> str:
    """分析技术水平"""
    technical_indicators = {
        "beginner": ["入门", "基础", "简单", "初学者", "beginner", "basic"],
        "intermediate": ["中级", "进阶", "intermediate", "advanced beginner"],
        "advanced": ["高级", "专家", "深入", "advanced", "expert", "架构"]
    }
    
    text_lower = text.lower()
    
    for level, indicators in technical_indicators.items():
        if any(indicator in text_lower for indicator in indicators):
            return level
    
    return "intermediate"  # 默认中级


def _identify_target_audience(text: str, technical_level: str) -> str:
    """识别目标读者"""
    audience_map = {
        "beginner": "初学者和新手开发者",
        "intermediate": "有一定经验的开发者",
        "advanced": "资深开发者和架构师"
    }
    
    # 检查文本中是否明确提到读者
    if "开发者" in text or "developer" in text.lower():
        return audience_map.get(technical_level, "开发者")
    elif "用户" in text or "user" in text.lower():
        return "最终用户"
    elif "管理员" in text or "admin" in text.lower():
        return "系统管理员"
    
    return audience_map.get(technical_level, "技术人员")


def _extract_key_requirements(text: str) -> List[str]:
    """提取关键需求"""
    requirements = []
    
    # 查找明确的需求标记
    requirement_patterns = [
        r'需要\s*(.+?)(?:[。，,\.]|$)',
        r'应该\s*(.+?)(?:[。，,\.]|$)',
        r'必须\s*(.+?)(?:[。，,\.]|$)',
        r'包括\s*(.+?)(?:[。，,\.]|$)',
        r'要求\s*(.+?)(?:[。，,\.]|$)'
    ]
    
    for pattern in requirement_patterns:
        matches = re.findall(pattern, text)
        requirements.extend([m.strip() for m in matches])
    
    # 如果没有找到明确的需求，将整个文本作为需求
    if not requirements:
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        requirements = sentences[:3]  # 取前3句
    
    return requirements[:5]  # 最多返回5个需求


def _suggest_sections(doc_type: str, requirements: List[str]) -> List[Dict[str, str]]:
    """建议章节结构"""
    section_templates = {
        "api_doc": [
            {"title": "概述", "description": "API整体介绍和用途"},
            {"title": "认证", "description": "认证方式和授权说明"},
            {"title": "端点说明", "description": "API端点详细说明"},
            {"title": "请求示例", "description": "请求格式和示例"},
            {"title": "响应格式", "description": "响应结构和状态码"},
            {"title": "错误处理", "description": "错误码和处理方法"}
        ],
        "user_manual": [
            {"title": "简介", "description": "产品介绍和功能概述"},
            {"title": "快速开始", "description": "快速上手指南"},
            {"title": "功能说明", "description": "详细功能介绍"},
            {"title": "常见问题", "description": "FAQ和问题解答"},
            {"title": "故障排除", "description": "常见问题的解决方法"}
        ],
        "design_doc": [
            {"title": "背景", "description": "项目背景和目标"},
            {"title": "系统架构", "description": "整体架构设计"},
            {"title": "技术选型", "description": "技术栈和工具选择"},
            {"title": "详细设计", "description": "模块和组件设计"},
            {"title": "数据模型", "description": "数据结构设计"},
            {"title": "安全考虑", "description": "安全设计和措施"}
        ],
        "tutorial": [
            {"title": "简介", "description": "教程目标和学习内容"},
            {"title": "环境准备", "description": "环境配置和工具安装"},
            {"title": "基础概念", "description": "核心概念讲解"},
            {"title": "实践示例", "description": "动手实践"},
            {"title": "进阶内容", "description": "深入学习"},
            {"title": "总结", "description": "知识点回顾"}
        ],
        "technical_spec": [
            {"title": "概述", "description": "规格说明概述"},
            {"title": "技术要求", "description": "技术标准和要求"},
            {"title": "接口规范", "description": "接口定义和规范"},
            {"title": "性能指标", "description": "性能要求和指标"},
            {"title": "测试标准", "description": "测试方法和标准"}
        ]
    }
    
    return section_templates.get(doc_type, [
        {"title": "概述", "description": "文档概述"},
        {"title": "详细说明", "description": "详细内容"},
        {"title": "总结", "description": "总结和展望"}
    ])


def _assess_complexity(text: str, requirements: List[str]) -> str:
    """评估复杂度"""
    # 基于文本长度和需求数量评估
    text_length = len(text)
    requirement_count = len(requirements)
    
    if text_length < 100 and requirement_count <= 2:
        return "simple"
    elif text_length < 500 and requirement_count <= 5:
        return "moderate"
    else:
        return "complex"


@tool
def generate_document_outline(
    requirement_analysis: Dict[str, Any],
    custom_sections: List[Dict[str, str]] = None
) -> str:
    """
    生成文档大纲
    
    根据需求分析结果生成详细的文档大纲，包括章节标题、
    描述和内容要点。
    
    Args:
        requirement_analysis (Dict[str, Any]): 需求分析结果
        custom_sections (List[Dict[str, str]]): 自定义章节列表，
            每个章节包含title和description字段
            
    Returns:
        str: JSON格式的文档大纲，包含：
            {
                "status": "success",
                "document_outline": {
                    "title": "文档标题",
                    "sections": [...],  # 章节列表
                    "metadata": {...}
                }
            }
    """
    try:
        # 验证输入
        if not isinstance(requirement_analysis, dict):
            raise ValueError("requirement_analysis必须是字典类型")
        
        # 提取信息
        doc_type = requirement_analysis.get("document_type", "technical_doc")
        main_topic = requirement_analysis.get("main_topic", "Technical Document")
        suggested_sections = requirement_analysis.get("suggested_sections", [])
        
        # 使用自定义章节或建议章节
        sections = custom_sections if custom_sections else suggested_sections
        
        # 生成文档标题
        title = _generate_title(main_topic, doc_type)
        
        # 增强章节信息
        enhanced_sections = []
        for i, section in enumerate(sections):
            enhanced_section = {
                "id": f"section_{i+1}",
                "title": section.get("title", f"Section {i+1}"),
                "description": section.get("description", ""),
                "key_points": _generate_key_points(
                    section.get("title", ""),
                    requirement_analysis.get("key_requirements", [])
                ),
                "estimated_length": _estimate_section_length(section.get("title", ""))
            }
            enhanced_sections.append(enhanced_section)
        
        # 构建大纲
        outline = {
            "title": title,
            "sections": enhanced_sections,
            "metadata": {
                "document_type": doc_type,
                "target_audience": requirement_analysis.get("target_audience", "技术人员"),
                "technical_level": requirement_analysis.get("technical_level", "intermediate"),
                "estimated_total_length": sum(s["estimated_length"] for s in enhanced_sections),
                "created_at": datetime.now().isoformat()
            }
        }
        
        # 构建响应
        response = {
            "status": "success",
            "document_outline": outline
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _generate_title(topic: str, doc_type: str) -> str:
    """生成文档标题"""
    type_suffixes = {
        "api_doc": "API Documentation",
        "user_manual": "User Manual",
        "design_doc": "Design Document",
        "tutorial": "Tutorial",
        "technical_spec": "Technical Specification"
    }
    
    suffix = type_suffixes.get(doc_type, "Technical Document")
    
    # 清理主题
    clean_topic = topic.split('(')[0].strip()
    
    return f"{clean_topic} - {suffix}"


def _generate_key_points(section_title: str, requirements: List[str]) -> List[str]:
    """为章节生成关键要点"""
    # 基于章节标题和需求生成要点
    key_points = []
    
    title_lower = section_title.lower()
    
    # 根据章节类型生成通用要点
    if "概述" in section_title or "introduction" in title_lower:
        key_points = ["背景介绍", "目标和范围", "主要特性"]
    elif "安装" in section_title or "setup" in title_lower:
        key_points = ["系统要求", "安装步骤", "配置说明"]
    elif "使用" in section_title or "usage" in title_lower:
        key_points = ["基本操作", "高级功能", "最佳实践"]
    elif "api" in title_lower or "接口" in section_title:
        key_points = ["端点说明", "参数描述", "示例代码"]
    else:
        key_points = ["详细说明", "示例", "注意事项"]
    
    # 结合需求
    for req in requirements[:2]:
        if len(req) < 50:
            key_points.append(req)
    
    return key_points[:5]


def _estimate_section_length(section_title: str) -> int:
    """估算章节长度（字数）"""
    # 基于章节类型估算
    title_lower = section_title.lower()
    
    if "概述" in section_title or "introduction" in title_lower:
        return 300
    elif "详细" in section_title or "detail" in title_lower:
        return 800
    elif "示例" in section_title or "example" in title_lower:
        return 500
    else:
        return 400


@tool
def apply_feedback_to_document(
    document_content: Dict[str, Any],
    review_feedback: Dict[str, Any]
) -> str:
    """
    根据审核反馈修改文档
    
    此工具分析审核反馈，生成针对性的修改建议，
    用于指导文档的迭代改进。
    
    Args:
        document_content (Dict[str, Any]): 当前文档内容
        review_feedback (Dict[str, Any]): 审核反馈，包含：
            - overall_status: "pass" | "fail"
            - quality_score: 质量评分(0-100)
            - feedback_items: 反馈项列表
            - suggestions: 改进建议
            
    Returns:
        str: JSON格式的修改指导，包含：
            {
                "status": "success",
                "modification_guide": {
                    "priority_changes": [...],  # 优先修改项
                    "section_modifications": {...},  # 按章节的修改建议
                    "content_enhancements": [...],  # 内容增强建议
                    "style_improvements": [...]  # 风格改进建议
                },
                "estimated_effort": "修改工作量评估"
            }
    """
    try:
        # 验证输入
        if not isinstance(document_content, dict):
            raise ValueError("document_content必须是字典类型")
        
        if not isinstance(review_feedback, dict):
            raise ValueError("review_feedback必须是字典类型")
        
        # 提取反馈信息
        feedback_items = review_feedback.get("feedback_items", [])
        suggestions = review_feedback.get("suggestions", [])
        quality_score = review_feedback.get("quality_score", 0)
        
        # 分析反馈项
        priority_changes = []
        section_modifications = {}
        content_enhancements = []
        style_improvements = []
        
        # 处理反馈项
        for item in feedback_items:
            category = item.get("category", "general")
            severity = item.get("severity", "medium")
            description = item.get("description", "")
            suggestion = item.get("suggestion", "")
            section_ref = item.get("section_reference", "")
            
            modification = {
                "category": category,
                "severity": severity,
                "description": description,
                "suggestion": suggestion,
                "section": section_ref
            }
            
            # 高优先级问题
            if severity == "high":
                priority_changes.append(modification)
            
            # 按章节组织
            if section_ref:
                if section_ref not in section_modifications:
                    section_modifications[section_ref] = []
                section_modifications[section_ref].append(modification)
            
            # 按类别分类
            if category in ["content", "completeness", "accuracy"]:
                content_enhancements.append(modification)
            elif category in ["style", "clarity", "formatting"]:
                style_improvements.append(modification)
        
        # 处理建议
        for suggestion in suggestions:
            enhancement = {
                "type": "general_suggestion",
                "suggestion": suggestion,
                "priority": "medium"
            }
            content_enhancements.append(enhancement)
        
        # 评估修改工作量
        effort = _estimate_modification_effort(
            len(priority_changes),
            len(feedback_items),
            quality_score
        )
        
        # 构建修改指导
        modification_guide = {
            "priority_changes": priority_changes,
            "section_modifications": section_modifications,
            "content_enhancements": content_enhancements,
            "style_improvements": style_improvements,
            "modification_summary": {
                "total_issues": len(feedback_items),
                "high_priority": len(priority_changes),
                "sections_affected": len(section_modifications),
                "current_quality_score": quality_score
            }
        }
        
        # 构建响应
        response = {
            "status": "success",
            "modification_guide": modification_guide,
            "estimated_effort": effort
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _estimate_modification_effort(
    high_priority_count: int,
    total_issues: int,
    quality_score: float
) -> str:
    """评估修改工作量"""
    if quality_score >= 80 and total_issues <= 3:
        return "minimal"
    elif quality_score >= 60 and total_issues <= 8:
        return "moderate"
    elif high_priority_count > 5 or quality_score < 40:
        return "significant"
    else:
        return "moderate"


@tool
def track_document_history(
    document_content: Dict[str, Any],
    modification_type: str,
    modification_details: str
) -> str:
    """
    跟踪文档修改历史
    
    此工具记录文档的每次修改，维护完整的修改历史。
    
    Args:
        document_content (Dict[str, Any]): 文档内容
        modification_type (str): 修改类型，如"initial_creation", "feedback_revision", "content_enhancement"
        modification_details (str): 修改详情描述
            
    Returns:
        str: JSON格式的历史记录，包含：
            {
                "status": "success",
                "history_entry": {
                    "timestamp": "时间戳",
                    "version": "版本号",
                    "modification_type": "修改类型",
                    "details": "修改详情",
                    "document_snapshot": {...}  # 文档快照
                }
            }
    """
    try:
        # 生成版本号
        current_version = document_content.get("version", "1.0")
        new_version = _increment_version(current_version, modification_type)
        
        # 创建历史记录
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "version": new_version,
            "modification_type": modification_type,
            "details": modification_details,
            "document_snapshot": {
                "title": document_content.get("title", ""),
                "section_count": len(document_content.get("sections", [])),
                "metadata": document_content.get("metadata", {})
            }
        }
        
        # 构建响应
        response = {
            "status": "success",
            "history_entry": history_entry
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)


def _increment_version(current_version: str, modification_type: str) -> str:
    """递增版本号"""
    try:
        parts = current_version.split('.')
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
        
        if modification_type == "initial_creation":
            return "1.0.0"
        elif modification_type == "feedback_revision":
            patch += 1
        elif modification_type == "content_enhancement":
            minor += 1
        else:
            patch += 1
        
        return f"{major}.{minor}.{patch}"
    except:
        return "1.0.1"


@tool
def validate_document_quality(
    document_content: Dict[str, Any],
    quality_criteria: Dict[str, Any] = None
) -> str:
    """
    验证文档质量
    
    在提交审核前进行自我质量检查。
    
    Args:
        document_content (Dict[str, Any]): 文档内容
        quality_criteria (Dict[str, Any]): 质量标准，包括：
            - min_section_count: 最少章节数
            - min_content_length: 最少内容长度
            - require_examples: 是否要求示例
            - check_completeness: 是否检查完整性
            
    Returns:
        str: JSON格式的质量检查结果
    """
    try:
        # 默认质量标准
        default_criteria = {
            "min_section_count": 3,
            "min_content_length": 500,
            "require_examples": True,
            "check_completeness": True
        }
        
        criteria = {**default_criteria, **(quality_criteria or {})}
        
        issues = []
        warnings = []
        score = 100
        
        # 检查章节数量
        sections = document_content.get("sections", [])
        if len(sections) < criteria["min_section_count"]:
            issues.append({
                "type": "structure",
                "message": f"章节数量({len(sections)})少于最小要求({criteria['min_section_count']})"
            })
            score -= 20
        
        # 检查内容长度
        total_length = sum(len(s.get("content", "")) for s in sections)
        if total_length < criteria["min_content_length"]:
            issues.append({
                "type": "content",
                "message": f"内容总长度({total_length})少于最小要求({criteria['min_content_length']})"
            })
            score -= 15
        
        # 检查是否有空章节
        empty_sections = [i for i, s in enumerate(sections) if not s.get("content", "").strip()]
        if empty_sections:
            warnings.append({
                "type": "completeness",
                "message": f"发现{len(empty_sections)}个空章节"
            })
            score -= 5 * len(empty_sections)
        
        # 检查示例
        if criteria["require_examples"]:
            has_code_example = any("```" in s.get("content", "") for s in sections)
            if not has_code_example:
                warnings.append({
                    "type": "content",
                    "message": "建议添加代码示例"
                })
                score -= 10
        
        # 最终评分
        final_score = max(0, min(100, score))
        
        # 判断质量等级
        if final_score >= 80:
            quality_level = "excellent"
        elif final_score >= 60:
            quality_level = "good"
        elif final_score >= 40:
            quality_level = "fair"
        else:
            quality_level = "poor"
        
        # 构建响应
        response = {
            "status": "success",
            "quality_check": {
                "quality_score": final_score,
                "quality_level": quality_level,
                "issues": issues,
                "warnings": warnings,
                "passed": len(issues) == 0,
                "summary": f"发现{len(issues)}个问题和{len(warnings)}个警告"
            }
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)
    
    except Exception as e:
        error_response = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(error_response, ensure_ascii=False)
