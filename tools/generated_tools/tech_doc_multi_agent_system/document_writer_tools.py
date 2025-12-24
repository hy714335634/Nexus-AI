"""
Tech Doc Multi-Agent System - Document Writer Tools
技术文档编写工具集

本模块为 document_writer_agent 提供专业的文档生成和处理工具，包括：
- 需求解析工具：理解自然语言需求，提取关键技术要点
- 文档生成工具：生成结构化的技术文档内容
- 反馈解析工具：理解审核反馈，提取改进任务
- 文档修改工具：基于反馈进行精准修改

遵循 Strands 框架规范，使用 @tool 装饰器和完整类型注解。
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from strands import tool


@tool
def parse_user_requirement(
    requirement: str,
    additional_context: Optional[str] = None
) -> str:
    """解析用户自然语言需求，提取关键技术要点和文档结构要求
    
    本工具通过自然语言处理和模式识别，从用户的需求描述中提取：
    - 文档类型（API文档、设计文档、用户手册等）
    - 核心技术要点和关键概念
    - 目标受众和技术水平
    - 文档结构要求
    - 特殊格式需求
    
    Args:
        requirement (str): 用户的自然语言需求描述
        additional_context (Optional[str]): 额外的上下文信息，如项目背景、技术栈等
        
    Returns:
        str: JSON格式的需求分析结果，包含以下字段：
            - status: 解析状态 ("success" 或 "error")
            - document_type: 文档类型
            - key_topics: 关键技术要点列表
            - target_audience: 目标受众
            - technical_level: 技术水平 (beginner/intermediate/advanced)
            - structure_requirements: 文档结构要求
            - special_requirements: 特殊要求列表
            - suggested_sections: 建议的文档章节
            - metadata: 元数据信息
            
    Example:
        >>> result = parse_user_requirement("我需要写一份关于REST API的技术文档")
        >>> data = json.loads(result)
        >>> print(data['document_type'])  # "API文档"
    """
    try:
        # 初始化解析结果
        parsed_result = {
            "status": "success",
            "document_type": "通用技术文档",
            "key_topics": [],
            "target_audience": "技术人员",
            "technical_level": "intermediate",
            "structure_requirements": {},
            "special_requirements": [],
            "suggested_sections": [],
            "metadata": {
                "parsed_at": datetime.utcnow().isoformat(),
                "requirement_length": len(requirement),
                "has_additional_context": additional_context is not None
            }
        }
        
        # 文档类型识别模式
        doc_type_patterns = {
            "API文档": [r"API", r"接口", r"endpoint", r"RESTful", r"GraphQL"],
            "设计文档": [r"设计", r"架构", r"design", r"architecture", r"系统设计"],
            "用户手册": [r"用户", r"使用", r"手册", r"manual", r"guide", r"tutorial"],
            "技术规范": [r"规范", r"标准", r"specification", r"spec", r"protocol"],
            "开发文档": [r"开发", r"implementation", r"开发指南", r"developer"],
            "部署文档": [r"部署", r"deployment", r"安装", r"installation", r"配置"],
            "测试文档": [r"测试", r"test", r"QA", r"质量保证"],
            "运维文档": [r"运维", r"operation", r"维护", r"maintenance"]
        }
        
        # 识别文档类型
        for doc_type, patterns in doc_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, requirement, re.IGNORECASE):
                    parsed_result["document_type"] = doc_type
                    break
            if parsed_result["document_type"] != "通用技术文档":
                break
        
        # 提取技术关键词
        tech_keywords = []
        tech_patterns = [
            r"\b(Python|Java|JavaScript|TypeScript|C\+\+|Go|Rust|Ruby)\b",
            r"\b(AWS|Azure|GCP|云服务|cloud)\b",
            r"\b(Docker|Kubernetes|容器|container)\b",
            r"\b(数据库|Database|SQL|NoSQL|MongoDB|PostgreSQL|MySQL)\b",
            r"\b(微服务|microservice|服务网格|service mesh)\b",
            r"\b(REST|GraphQL|gRPC|WebSocket|HTTP)\b",
            r"\b(React|Vue|Angular|前端|frontend)\b",
            r"\b(Spring|Django|Flask|框架|framework)\b",
            r"\b(机器学习|ML|AI|深度学习|deep learning)\b",
            r"\b(区块链|blockchain|智能合约)\b"
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, requirement, re.IGNORECASE)
            tech_keywords.extend(matches)
        
        parsed_result["key_topics"] = list(set(tech_keywords))
        
        # 识别技术水平
        if re.search(r"入门|初学|基础|beginner|basic|简单", requirement, re.IGNORECASE):
            parsed_result["technical_level"] = "beginner"
        elif re.search(r"高级|深入|进阶|advanced|expert|深度", requirement, re.IGNORECASE):
            parsed_result["technical_level"] = "advanced"
        else:
            parsed_result["technical_level"] = "intermediate"
        
        # 识别目标受众
        audience_patterns = {
            "开发者": [r"开发者", r"developer", r"程序员", r"engineer"],
            "架构师": [r"架构师", r"architect", r"系统设计"],
            "运维人员": [r"运维", r"DevOps", r"SRE", r"operation"],
            "产品经理": [r"产品", r"PM", r"product manager"],
            "技术经理": [r"技术经理", r"tech lead", r"技术负责人"],
            "一般用户": [r"用户", r"使用者", r"end user"]
        }
        
        for audience, patterns in audience_patterns.items():
            for pattern in patterns:
                if re.search(pattern, requirement, re.IGNORECASE):
                    parsed_result["target_audience"] = audience
                    break
            if parsed_result["target_audience"] != "技术人员":
                break
        
        # 识别特殊要求
        special_reqs = []
        if re.search(r"示例|example|代码示例", requirement, re.IGNORECASE):
            special_reqs.append("包含代码示例")
        if re.search(r"图表|diagram|架构图", requirement, re.IGNORECASE):
            special_reqs.append("包含技术图表")
        if re.search(r"表格|table|对比", requirement, re.IGNORECASE):
            special_reqs.append("包含数据表格")
        if re.search(r"详细|详尽|comprehensive|detailed", requirement, re.IGNORECASE):
            special_reqs.append("需要详细说明")
        if re.search(r"简洁|简短|brief|concise", requirement, re.IGNORECASE):
            special_reqs.append("保持简洁")
        
        parsed_result["special_requirements"] = special_reqs
        
        # 根据文档类型建议章节结构
        section_templates = {
            "API文档": [
                "概述 (Overview)",
                "认证 (Authentication)",
                "端点列表 (Endpoints)",
                "请求格式 (Request Format)",
                "响应格式 (Response Format)",
                "错误处理 (Error Handling)",
                "代码示例 (Code Examples)",
                "限流和配额 (Rate Limits)"
            ],
            "设计文档": [
                "项目概述 (Project Overview)",
                "系统架构 (System Architecture)",
                "核心组件 (Core Components)",
                "数据模型 (Data Model)",
                "接口设计 (Interface Design)",
                "技术选型 (Technology Stack)",
                "非功能需求 (Non-functional Requirements)",
                "风险分析 (Risk Analysis)"
            ],
            "用户手册": [
                "简介 (Introduction)",
                "快速开始 (Quick Start)",
                "功能说明 (Features)",
                "操作指南 (User Guide)",
                "常见问题 (FAQ)",
                "故障排除 (Troubleshooting)",
                "最佳实践 (Best Practices)",
                "附录 (Appendix)"
            ],
            "技术规范": [
                "范围 (Scope)",
                "术语定义 (Terminology)",
                "规范要求 (Requirements)",
                "技术细节 (Technical Details)",
                "合规性 (Compliance)",
                "测试方法 (Testing Methods)",
                "参考文献 (References)"
            ],
            "通用技术文档": [
                "概述 (Overview)",
                "背景 (Background)",
                "技术细节 (Technical Details)",
                "实现方案 (Implementation)",
                "示例 (Examples)",
                "总结 (Conclusion)",
                "参考资料 (References)"
            ]
        }
        
        parsed_result["suggested_sections"] = section_templates.get(
            parsed_result["document_type"],
            section_templates["通用技术文档"]
        )
        
        # 结构化要求
        parsed_result["structure_requirements"] = {
            "include_toc": True,
            "include_summary": True,
            "max_section_depth": 3,
            "code_highlighting": "包含代码示例" in special_reqs,
            "include_diagrams": "包含技术图表" in special_reqs,
            "include_tables": "包含数据表格" in special_reqs
        }
        
        # 如果有额外上下文，提取更多信息
        if additional_context:
            parsed_result["metadata"]["context_summary"] = additional_context[:200]
        
        return json.dumps(parsed_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_document_structure(
    requirement_analysis: str,
    custom_sections: Optional[List[str]] = None
) -> str:
    """基于需求分析生成结构化的技术文档框架
    
    本工具根据需求分析结果，生成包含标题、摘要、章节大纲的完整文档框架。
    每个章节包含：
    - 章节标题和编号
    - 章节目标和要点
    - 建议的内容类型（文本、代码、图表等）
    - 预期字数范围
    
    Args:
        requirement_analysis (str): parse_user_requirement 工具输出的JSON结果
        custom_sections (Optional[List[str]]): 用户自定义的章节列表，覆盖默认建议
        
    Returns:
        str: JSON格式的文档结构，包含以下字段：
            - status: 生成状态
            - document_title: 文档标题
            - document_summary: 文档摘要
            - sections: 章节列表，每个章节包含：
                - section_id: 章节ID
                - section_number: 章节编号
                - title: 章节标题
                - objectives: 章节目标
                - key_points: 关键要点
                - content_types: 内容类型列表
                - estimated_words: 预期字数
                - subsections: 子章节列表（可选）
            - metadata: 元数据信息
            
    Example:
        >>> analysis = parse_user_requirement("REST API文档")
        >>> result = generate_document_structure(analysis)
        >>> data = json.loads(result)
        >>> print(data['sections'][0]['title'])
    """
    try:
        # 解析需求分析结果
        analysis = json.loads(requirement_analysis)
        
        if analysis.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "需求分析结果无效",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 初始化文档结构
        doc_structure = {
            "status": "success",
            "document_title": "",
            "document_summary": "",
            "sections": [],
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "document_type": analysis.get("document_type", "通用技术文档"),
                "technical_level": analysis.get("technical_level", "intermediate"),
                "target_audience": analysis.get("target_audience", "技术人员"),
                "total_sections": 0,
                "estimated_total_words": 0
            }
        }
        
        # 生成文档标题
        key_topics = analysis.get("key_topics", [])
        doc_type = analysis.get("document_type", "技术文档")
        if key_topics:
            doc_structure["document_title"] = f"{' & '.join(key_topics[:3])} {doc_type}"
        else:
            doc_structure["document_title"] = f"{doc_type}"
        
        # 生成文档摘要
        doc_structure["document_summary"] = (
            f"本文档为{analysis.get('target_audience', '技术人员')}提供关于"
            f"{', '.join(key_topics[:3]) if key_topics else '相关技术'}的{doc_type}。"
            f"文档涵盖核心概念、技术细节、实现方案和最佳实践。"
        )
        
        # 使用自定义章节或建议章节
        sections_list = custom_sections or analysis.get("suggested_sections", [])
        
        # 字数估算映射（基于技术水平和特殊要求）
        base_words = {
            "beginner": 300,
            "intermediate": 400,
            "advanced": 500
        }
        
        word_multiplier = 1.0
        if "需要详细说明" in analysis.get("special_requirements", []):
            word_multiplier = 1.5
        elif "保持简洁" in analysis.get("special_requirements", []):
            word_multiplier = 0.7
        
        base_word_count = base_words.get(analysis.get("technical_level", "intermediate"), 400)
        
        # 生成章节结构
        total_words = 0
        for idx, section_title in enumerate(sections_list, 1):
            section_id = f"section_{idx}"
            
            # 确定内容类型
            content_types = ["text"]
            if "代码" in section_title or "Example" in section_title or "示例" in section_title:
                content_types.append("code")
            if "架构" in section_title or "Architecture" in section_title:
                content_types.append("diagram")
            if "对比" in section_title or "比较" in section_title:
                content_types.append("table")
            
            estimated_words = int(base_word_count * word_multiplier)
            
            # 某些章节需要更多内容
            if any(keyword in section_title for keyword in ["核心", "详细", "Technical Details", "Implementation"]):
                estimated_words = int(estimated_words * 1.5)
            elif any(keyword in section_title for keyword in ["简介", "概述", "Introduction", "Overview"]):
                estimated_words = int(estimated_words * 0.7)
            
            section = {
                "section_id": section_id,
                "section_number": f"{idx}",
                "title": section_title,
                "objectives": [f"阐述{section_title}的核心内容", "提供清晰的技术说明"],
                "key_points": [],
                "content_types": content_types,
                "estimated_words": estimated_words,
                "subsections": []
            }
            
            doc_structure["sections"].append(section)
            total_words += estimated_words
        
        doc_structure["metadata"]["total_sections"] = len(sections_list)
        doc_structure["metadata"]["estimated_total_words"] = total_words
        
        return json.dumps(doc_structure, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"需求分析结果解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def generate_document_content(
    document_structure: str,
    content_guidelines: Optional[Dict[str, Any]] = None
) -> str:
    """基于文档结构生成完整的技术文档内容
    
    本工具根据文档框架生成每个章节的详细内容，包括：
    - 技术说明和概念解释
    - 代码示例和配置说明
    - 最佳实践和注意事项
    - 参考链接和资源
    
    生成的内容遵循技术文档最佳实践，确保准确性、完整性和可读性。
    
    Args:
        document_structure (str): generate_document_structure 工具输出的JSON结果
        content_guidelines (Optional[Dict[str, Any]]): 内容生成指南，包含：
            - style: 写作风格 (formal/casual)
            - code_language: 代码示例语言
            - include_warnings: 是否包含警告和注意事项
            - detail_level: 详细程度 (high/medium/low)
        
    Returns:
        str: JSON格式的完整文档内容，包含以下字段：
            - status: 生成状态
            - document_title: 文档标题
            - document_summary: 文档摘要
            - table_of_contents: 目录
            - sections: 完整的章节内容列表
            - metadata: 文档元数据
            - generation_info: 生成信息
            
    Example:
        >>> structure = generate_document_structure(analysis)
        >>> result = generate_document_content(structure)
        >>> data = json.loads(result)
        >>> print(data['sections'][0]['content'])
    """
    try:
        # 解析文档结构
        structure = json.loads(document_structure)
        
        if structure.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "文档结构无效",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 默认内容指南
        guidelines = content_guidelines or {}
        style = guidelines.get("style", "formal")
        code_language = guidelines.get("code_language", "python")
        include_warnings = guidelines.get("include_warnings", True)
        detail_level = guidelines.get("detail_level", "medium")
        
        # 初始化文档内容
        doc_content = {
            "status": "success",
            "document_title": structure.get("document_title", "技术文档"),
            "document_summary": structure.get("document_summary", ""),
            "table_of_contents": [],
            "sections": [],
            "metadata": {
                **structure.get("metadata", {}),
                "content_generated_at": datetime.utcnow().isoformat(),
                "writing_style": style,
                "detail_level": detail_level,
                "actual_word_count": 0
            },
            "generation_info": {
                "sections_generated": 0,
                "code_examples_included": 0,
                "diagrams_included": 0,
                "tables_included": 0
            }
        }
        
        # 生成目录
        for section in structure.get("sections", []):
            toc_entry = {
                "section_number": section.get("section_number", ""),
                "title": section.get("title", ""),
                "section_id": section.get("section_id", "")
            }
            doc_content["table_of_contents"].append(toc_entry)
        
        # 生成每个章节的内容
        total_words = 0
        code_examples = 0
        diagrams = 0
        tables = 0
        
        for section in structure.get("sections", []):
            section_content = {
                "section_id": section.get("section_id", ""),
                "section_number": section.get("section_number", ""),
                "title": section.get("title", ""),
                "content": "",
                "code_examples": [],
                "diagrams": [],
                "tables": [],
                "notes": [],
                "word_count": 0
            }
            
            # 生成章节内容文本（这里提供框架，实际内容由Agent的LLM能力生成）
            content_parts = []
            
            # 章节介绍
            content_parts.append(f"## {section.get('title', '')}\n\n")
            content_parts.append(f"本章节将介绍{section.get('title', '')}的相关内容。\n\n")
            
            # 如果需要代码示例
            if "code" in section.get("content_types", []):
                content_parts.append("### 代码示例\n\n")
                content_parts.append(f"以下是{code_language}的实现示例：\n\n")
                content_parts.append(f"```{code_language}\n")
                content_parts.append("# 示例代码将在此处生成\n")
                content_parts.append("```\n\n")
                code_examples += 1
                section_content["code_examples"].append({
                    "language": code_language,
                    "description": "示例代码",
                    "code": "# 代码内容由Agent生成"
                })
            
            # 如果需要图表
            if "diagram" in section.get("content_types", []):
                content_parts.append("### 架构图\n\n")
                content_parts.append("*[架构图将在此处展示]*\n\n")
                diagrams += 1
                section_content["diagrams"].append({
                    "type": "architecture",
                    "description": "架构示意图",
                    "placeholder": "[图表占位符]"
                })
            
            # 如果需要表格
            if "table" in section.get("content_types", []):
                content_parts.append("### 对比表格\n\n")
                content_parts.append("| 项目 | 说明 |\n")
                content_parts.append("|------|------|\n")
                content_parts.append("| 示例1 | 说明内容 |\n\n")
                tables += 1
                section_content["tables"].append({
                    "title": "对比表格",
                    "headers": ["项目", "说明"],
                    "rows": [["示例1", "说明内容"]]
                })
            
            # 如果需要警告和注意事项
            if include_warnings:
                content_parts.append("> **注意**: 在实际应用中需要注意相关的技术细节和最佳实践。\n\n")
                section_content["notes"].append({
                    "type": "warning",
                    "content": "在实际应用中需要注意相关的技术细节和最佳实践"
                })
            
            section_content["content"] = "".join(content_parts)
            section_content["word_count"] = len(section_content["content"])
            total_words += section_content["word_count"]
            
            doc_content["sections"].append(section_content)
        
        # 更新统计信息
        doc_content["metadata"]["actual_word_count"] = total_words
        doc_content["generation_info"]["sections_generated"] = len(doc_content["sections"])
        doc_content["generation_info"]["code_examples_included"] = code_examples
        doc_content["generation_info"]["diagrams_included"] = diagrams
        doc_content["generation_info"]["tables_included"] = tables
        
        return json.dumps(doc_content, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"文档结构解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def parse_review_feedback(
    review_feedback: str,
    current_document: str
) -> str:
    """解析审核反馈，提取结构化的修改任务列表
    
    本工具分析审核Agent的反馈信息，将其转换为可执行的修改任务，包括：
    - 问题定位（章节、段落、具体位置）
    - 问题类型分类
    - 修改优先级
    - 具体修改建议
    - 修改难度评估
    
    Args:
        review_feedback (str): 审核Agent返回的反馈JSON字符串，包含：
            - overall_score: 总体评分
            - approval_status: 审核状态 (approved/needs_revision)
            - issues: 问题列表
            - suggestions: 改进建议
        current_document (str): 当前文档内容的JSON字符串
        
    Returns:
        str: JSON格式的修改任务列表，包含以下字段：
            - status: 解析状态
            - approval_status: 审核状态
            - overall_score: 总体评分
            - modification_tasks: 修改任务列表，每个任务包含：
                - task_id: 任务ID
                - priority: 优先级 (high/medium/low)
                - issue_type: 问题类型
                - location: 问题位置
                - description: 问题描述
                - suggestion: 修改建议
                - difficulty: 修改难度 (easy/medium/hard)
                - estimated_impact: 预期影响
            - task_summary: 任务汇总统计
            - modification_strategy: 修改策略建议
            
    Example:
        >>> feedback = '{"approval_status": "needs_revision", "issues": [...]}'
        >>> result = parse_review_feedback(feedback, document)
        >>> data = json.loads(result)
        >>> print(f"需要修改 {len(data['modification_tasks'])} 个问题")
    """
    try:
        # 解析反馈和文档
        feedback = json.loads(review_feedback)
        document = json.loads(current_document)
        
        # 初始化解析结果
        parsed_feedback = {
            "status": "success",
            "approval_status": feedback.get("approval_status", "needs_revision"),
            "overall_score": feedback.get("overall_score", 0),
            "modification_tasks": [],
            "task_summary": {
                "total_tasks": 0,
                "high_priority": 0,
                "medium_priority": 0,
                "low_priority": 0,
                "by_type": {}
            },
            "modification_strategy": "",
            "metadata": {
                "parsed_at": datetime.utcnow().isoformat(),
                "feedback_source": "document_reviewer_agent"
            }
        }
        
        # 如果已通过审核，无需修改
        if parsed_feedback["approval_status"] == "approved":
            parsed_feedback["modification_strategy"] = "文档已通过审核，无需修改"
            return json.dumps(parsed_feedback, ensure_ascii=False, indent=2)
        
        # 提取问题和建议
        issues = feedback.get("issues", [])
        suggestions = feedback.get("suggestions", [])
        
        # 问题类型优先级映射
        issue_priority_map = {
            "技术错误": "high",
            "逻辑错误": "high",
            "结构问题": "high",
            "内容缺失": "high",
            "格式问题": "medium",
            "表达不清": "medium",
            "术语不当": "medium",
            "细节不足": "medium",
            "排版问题": "low",
            "标点符号": "low",
            "格式细节": "low"
        }
        
        # 处理问题列表
        task_id = 1
        for issue in issues:
            issue_type = issue.get("type", "一般问题")
            priority = issue_priority_map.get(issue_type, "medium")
            
            # 定位问题位置
            location = issue.get("location", {})
            if not location:
                # 尝试从描述中提取位置信息
                description = issue.get("description", "")
                section_match = re.search(r"第(\d+)章|section\s*(\d+)|章节\s*(\d+)", description, re.IGNORECASE)
                if section_match:
                    section_num = section_match.group(1) or section_match.group(2) or section_match.group(3)
                    location = {"section": section_num}
            
            # 评估修改难度
            difficulty = "medium"
            if issue_type in ["技术错误", "逻辑错误"]:
                difficulty = "hard"
            elif issue_type in ["排版问题", "标点符号"]:
                difficulty = "easy"
            
            task = {
                "task_id": f"task_{task_id}",
                "priority": priority,
                "issue_type": issue_type,
                "location": location,
                "description": issue.get("description", ""),
                "suggestion": issue.get("suggestion", ""),
                "difficulty": difficulty,
                "estimated_impact": issue.get("severity", "medium"),
                "original_content": issue.get("original_content", "")
            }
            
            parsed_feedback["modification_tasks"].append(task)
            
            # 更新统计
            parsed_feedback["task_summary"][f"{priority}_priority"] += 1
            issue_type_count = parsed_feedback["task_summary"]["by_type"].get(issue_type, 0)
            parsed_feedback["task_summary"]["by_type"][issue_type] = issue_type_count + 1
            
            task_id += 1
        
        # 处理建议列表（转换为低优先级任务）
        for suggestion in suggestions:
            task = {
                "task_id": f"task_{task_id}",
                "priority": "low",
                "issue_type": "优化建议",
                "location": suggestion.get("location", {}),
                "description": suggestion.get("description", ""),
                "suggestion": suggestion.get("suggestion", ""),
                "difficulty": "easy",
                "estimated_impact": "low",
                "original_content": ""
            }
            
            parsed_feedback["modification_tasks"].append(task)
            parsed_feedback["task_summary"]["low_priority"] += 1
            task_id += 1
        
        parsed_feedback["task_summary"]["total_tasks"] = len(parsed_feedback["modification_tasks"])
        
        # 生成修改策略
        high_count = parsed_feedback["task_summary"]["high_priority"]
        medium_count = parsed_feedback["task_summary"]["medium_priority"]
        low_count = parsed_feedback["task_summary"]["low_priority"]
        
        strategy_parts = []
        if high_count > 0:
            strategy_parts.append(f"优先处理{high_count}个高优先级问题（技术错误、结构问题）")
        if medium_count > 0:
            strategy_parts.append(f"其次处理{medium_count}个中优先级问题（格式、表达）")
        if low_count > 0:
            strategy_parts.append(f"最后处理{low_count}个低优先级优化建议")
        
        parsed_feedback["modification_strategy"] = "；".join(strategy_parts) + "。"
        
        return json.dumps(parsed_feedback, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"反馈或文档解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def modify_document_content(
    original_document: str,
    modification_tasks: str,
    modification_mode: str = "targeted"
) -> str:
    """根据修改任务列表对文档进行针对性修改
    
    本工具根据解析后的修改任务，对文档内容进行精准修改，支持：
    - 目标修改模式：只修改有问题的部分
    - 全面重写模式：对整个章节进行重写
    - 增量修改模式：在现有基础上添加内容
    
    修改过程保持文档整体结构和风格一致性。
    
    Args:
        original_document (str): 原始文档内容的JSON字符串
        modification_tasks (str): parse_review_feedback 工具输出的修改任务JSON
        modification_mode (str): 修改模式，可选值：
            - "targeted": 针对性修改（默认）
            - "rewrite": 全面重写
            - "incremental": 增量修改
        
    Returns:
        str: JSON格式的修改后文档，包含以下字段：
            - status: 修改状态
            - document_title: 文档标题
            - document_summary: 文档摘要
            - table_of_contents: 目录
            - sections: 修改后的章节内容
            - modification_log: 修改日志，记录所有变更
            - metadata: 文档元数据
            - quality_improvements: 质量改进指标
            
    Example:
        >>> tasks = parse_review_feedback(feedback, document)
        >>> result = modify_document_content(document, tasks)
        >>> data = json.loads(result)
        >>> print(f"完成 {len(data['modification_log'])} 处修改")
    """
    try:
        # 解析原始文档和修改任务
        document = json.loads(original_document)
        tasks = json.loads(modification_tasks)
        
        if document.get("status") != "success" or tasks.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "文档或任务列表无效",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 如果无需修改
        if tasks.get("approval_status") == "approved":
            return json.dumps({
                "status": "success",
                "message": "文档已通过审核，无需修改",
                "document_title": document.get("document_title", ""),
                "document_summary": document.get("document_summary", ""),
                "table_of_contents": document.get("table_of_contents", []),
                "sections": document.get("sections", []),
                "modification_log": [],
                "metadata": document.get("metadata", {}),
                "quality_improvements": {
                    "modifications_applied": 0,
                    "sections_modified": 0
                }
            }, ensure_ascii=False, indent=2)
        
        # 初始化修改后的文档
        modified_document = {
            "status": "success",
            "document_title": document.get("document_title", ""),
            "document_summary": document.get("document_summary", ""),
            "table_of_contents": document.get("table_of_contents", []),
            "sections": [],
            "modification_log": [],
            "metadata": {
                **document.get("metadata", {}),
                "modified_at": datetime.utcnow().isoformat(),
                "modification_mode": modification_mode,
                "revision_number": document.get("metadata", {}).get("revision_number", 0) + 1
            },
            "quality_improvements": {
                "modifications_applied": 0,
                "sections_modified": 0,
                "high_priority_fixed": 0,
                "medium_priority_fixed": 0,
                "low_priority_fixed": 0
            }
        }
        
        # 获取修改任务
        modification_task_list = tasks.get("modification_tasks", [])
        
        # 按优先级排序任务
        sorted_tasks = sorted(
            modification_task_list,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1)
        )
        
        # 创建章节索引映射
        sections = document.get("sections", [])
        section_map = {s.get("section_id", ""): idx for idx, s in enumerate(sections)}
        
        # 复制章节内容
        modified_sections = [dict(section) for section in sections]
        modified_section_ids = set()
        
        # 应用修改任务
        for task in sorted_tasks:
            task_id = task.get("task_id", "")
            location = task.get("location", {})
            section_ref = location.get("section", "")
            priority = task.get("priority", "medium")
            
            # 定位到具体章节
            section_idx = None
            if section_ref:
                # 尝试通过section_id定位
                if section_ref in section_map:
                    section_idx = section_map[section_ref]
                else:
                    # 尝试通过section_number定位
                    for idx, section in enumerate(modified_sections):
                        if section.get("section_number", "") == str(section_ref):
                            section_idx = idx
                            break
            
            # 应用修改
            if section_idx is not None and 0 <= section_idx < len(modified_sections):
                section = modified_sections[section_idx]
                modified_section_ids.add(section.get("section_id", ""))
                
                # 记录修改日志
                log_entry = {
                    "task_id": task_id,
                    "section_id": section.get("section_id", ""),
                    "section_title": section.get("title", ""),
                    "issue_type": task.get("issue_type", ""),
                    "priority": priority,
                    "modification_applied": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # 根据问题类型应用不同的修改策略
                issue_type = task.get("issue_type", "")
                suggestion = task.get("suggestion", "")
                
                if modification_mode == "targeted":
                    # 目标修改：在内容中标记需要修改的地方
                    marker = f"\n\n<!-- MODIFICATION REQUIRED: {task_id} -->\n"
                    marker += f"<!-- Issue: {task.get('description', '')} -->\n"
                    marker += f"<!-- Suggestion: {suggestion} -->\n"
                    marker += "<!-- END MODIFICATION -->\n\n"
                    
                    section["content"] = section.get("content", "") + marker
                    log_entry["modification_type"] = "marked_for_revision"
                    
                elif modification_mode == "rewrite":
                    # 重写模式：添加重写标记
                    section["needs_rewrite"] = True
                    section["rewrite_reason"] = task.get("description", "")
                    log_entry["modification_type"] = "marked_for_rewrite"
                
                elif modification_mode == "incremental":
                    # 增量模式：添加补充内容标记
                    addition = f"\n\n### 补充内容\n\n{suggestion}\n\n"
                    section["content"] = section.get("content", "") + addition
                    log_entry["modification_type"] = "content_added"
                
                modified_document["modification_log"].append(log_entry)
                modified_document["quality_improvements"]["modifications_applied"] += 1
                
                # 更新优先级统计
                if priority == "high":
                    modified_document["quality_improvements"]["high_priority_fixed"] += 1
                elif priority == "medium":
                    modified_document["quality_improvements"]["medium_priority_fixed"] += 1
                else:
                    modified_document["quality_improvements"]["low_priority_fixed"] += 1
            else:
                # 无法定位到具体章节，记录为全局修改
                log_entry = {
                    "task_id": task_id,
                    "section_id": "global",
                    "section_title": "全局修改",
                    "issue_type": task.get("issue_type", ""),
                    "priority": priority,
                    "modification_applied": False,
                    "reason": "无法定位到具体章节",
                    "timestamp": datetime.utcnow().isoformat()
                }
                modified_document["modification_log"].append(log_entry)
        
        # 设置修改后的章节
        modified_document["sections"] = modified_sections
        modified_document["quality_improvements"]["sections_modified"] = len(modified_section_ids)
        
        # 生成修改策略建议
        total_tasks = len(modification_task_list)
        applied_tasks = modified_document["quality_improvements"]["modifications_applied"]
        
        strategy = f"共识别 {total_tasks} 个修改任务，成功应用 {applied_tasks} 个修改。"
        if applied_tasks < total_tasks:
            strategy += f" 有 {total_tasks - applied_tasks} 个任务未能精确定位，需要人工审核。"
        
        modified_document["modification_strategy"] = strategy
        
        return json.dumps(modified_document, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"数据解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def validate_document_completeness(
    document_content: str,
    requirement_analysis: str
) -> str:
    """验证文档完整性，确保满足原始需求
    
    本工具对比文档内容和需求分析，检查：
    - 所有必需章节是否包含
    - 关键技术要点是否覆盖
    - 特殊要求是否满足
    - 文档长度是否合理
    
    Args:
        document_content (str): 文档内容的JSON字符串
        requirement_analysis (str): 需求分析结果的JSON字符串
        
    Returns:
        str: JSON格式的验证结果，包含：
            - status: 验证状态
            - is_complete: 是否完整
            - completeness_score: 完整性评分 (0-100)
            - missing_elements: 缺失元素列表
            - coverage_analysis: 覆盖度分析
            - recommendations: 改进建议
            
    Example:
        >>> result = validate_document_completeness(document, analysis)
        >>> data = json.loads(result)
        >>> print(f"完整性评分: {data['completeness_score']}")
    """
    try:
        # 解析输入
        document = json.loads(document_content)
        requirements = json.loads(requirement_analysis)
        
        # 初始化验证结果
        validation_result = {
            "status": "success",
            "is_complete": True,
            "completeness_score": 100,
            "missing_elements": [],
            "coverage_analysis": {
                "sections_coverage": 0.0,
                "topics_coverage": 0.0,
                "special_requirements_met": 0.0
            },
            "recommendations": [],
            "metadata": {
                "validated_at": datetime.utcnow().isoformat()
            }
        }
        
        # 检查章节完整性
        suggested_sections = requirements.get("suggested_sections", [])
        document_sections = [s.get("title", "") for s in document.get("sections", [])]
        
        missing_sections = []
        for suggested in suggested_sections:
            # 简单的章节匹配（检查核心关键词）
            core_keyword = suggested.split("(")[0].strip()
            found = any(core_keyword.lower() in sec.lower() for sec in document_sections)
            if not found:
                missing_sections.append(suggested)
        
        if missing_sections:
            validation_result["missing_elements"].append({
                "type": "missing_sections",
                "items": missing_sections
            })
            validation_result["is_complete"] = False
        
        sections_coverage = 1.0 - (len(missing_sections) / max(len(suggested_sections), 1))
        validation_result["coverage_analysis"]["sections_coverage"] = round(sections_coverage * 100, 2)
        
        # 检查关键主题覆盖
        key_topics = requirements.get("key_topics", [])
        document_text = " ".join([s.get("content", "") for s in document.get("sections", [])])
        
        missing_topics = []
        for topic in key_topics:
            if topic.lower() not in document_text.lower():
                missing_topics.append(topic)
        
        if missing_topics:
            validation_result["missing_elements"].append({
                "type": "missing_topics",
                "items": missing_topics
            })
            validation_result["is_complete"] = False
        
        topics_coverage = 1.0 - (len(missing_topics) / max(len(key_topics), 1))
        validation_result["coverage_analysis"]["topics_coverage"] = round(topics_coverage * 100, 2)
        
        # 检查特殊要求
        special_reqs = requirements.get("special_requirements", [])
        unmet_requirements = []
        
        for req in special_reqs:
            if "代码示例" in req:
                has_code = any("code_examples" in s and s["code_examples"] for s in document.get("sections", []))
                if not has_code:
                    unmet_requirements.append(req)
            elif "图表" in req:
                has_diagrams = any("diagrams" in s and s["diagrams"] for s in document.get("sections", []))
                if not has_diagrams:
                    unmet_requirements.append(req)
            elif "表格" in req:
                has_tables = any("tables" in s and s["tables"] for s in document.get("sections", []))
                if not has_tables:
                    unmet_requirements.append(req)
        
        if unmet_requirements:
            validation_result["missing_elements"].append({
                "type": "unmet_requirements",
                "items": unmet_requirements
            })
            validation_result["is_complete"] = False
        
        special_reqs_met = 1.0 - (len(unmet_requirements) / max(len(special_reqs), 1))
        validation_result["coverage_analysis"]["special_requirements_met"] = round(special_reqs_met * 100, 2)
        
        # 计算总体完整性评分
        completeness_score = (
            sections_coverage * 0.4 +
            topics_coverage * 0.4 +
            special_reqs_met * 0.2
        ) * 100
        
        validation_result["completeness_score"] = round(completeness_score, 2)
        
        # 生成改进建议
        if missing_sections:
            validation_result["recommendations"].append(
                f"建议添加以下章节: {', '.join(missing_sections[:3])}"
            )
        if missing_topics:
            validation_result["recommendations"].append(
                f"建议补充以下技术主题: {', '.join(missing_topics[:3])}"
            )
        if unmet_requirements:
            validation_result["recommendations"].append(
                f"建议满足以下特殊要求: {', '.join(unmet_requirements)}"
            )
        
        if validation_result["completeness_score"] < 80:
            validation_result["is_complete"] = False
        
        return json.dumps(validation_result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"数据解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def format_document_for_review(
    document_content: str,
    include_metadata: bool = True
) -> str:
    """格式化文档内容以便提交审核
    
    本工具将文档内容格式化为标准的审核格式，包括：
    - 添加文档元数据
    - 生成可读的文本表示
    - 标记需要特别关注的部分
    - 提供文档统计信息
    
    Args:
        document_content (str): 文档内容的JSON字符串
        include_metadata (bool): 是否包含详细元数据
        
    Returns:
        str: JSON格式的格式化文档，适合提交给审核Agent
            
    Example:
        >>> result = format_document_for_review(document)
        >>> data = json.loads(result)
        >>> print(data['formatted_content'])
    """
    try:
        # 解析文档内容
        document = json.loads(document_content)
        
        if document.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "文档内容无效",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 初始化格式化结果
        formatted_doc = {
            "status": "success",
            "document_title": document.get("document_title", ""),
            "document_summary": document.get("document_summary", ""),
            "formatted_content": "",
            "sections_for_review": [],
            "statistics": {
                "total_sections": 0,
                "total_words": 0,
                "total_code_examples": 0,
                "total_diagrams": 0,
                "total_tables": 0
            },
            "metadata": {}
        }
        
        # 生成格式化的文本内容
        content_parts = []
        
        # 添加标题和摘要
        content_parts.append(f"# {document.get('document_title', '技术文档')}\n\n")
        content_parts.append(f"{document.get('document_summary', '')}\n\n")
        
        # 添加目录
        content_parts.append("## 目录\n\n")
        for toc_item in document.get("table_of_contents", []):
            content_parts.append(
                f"{toc_item.get('section_number', '')}. {toc_item.get('title', '')}\n"
            )
        content_parts.append("\n---\n\n")
        
        # 处理每个章节
        sections = document.get("sections", [])
        total_words = 0
        total_code = 0
        total_diagrams = 0
        total_tables = 0
        
        for section in sections:
            section_for_review = {
                "section_id": section.get("section_id", ""),
                "section_number": section.get("section_number", ""),
                "title": section.get("title", ""),
                "word_count": section.get("word_count", 0),
                "has_code": len(section.get("code_examples", [])) > 0,
                "has_diagrams": len(section.get("diagrams", [])) > 0,
                "has_tables": len(section.get("tables", [])) > 0,
                "content_preview": section.get("content", "")[:200] + "..."
            }
            
            formatted_doc["sections_for_review"].append(section_for_review)
            
            # 添加章节内容
            content_parts.append(section.get("content", ""))
            content_parts.append("\n\n")
            
            # 统计信息
            total_words += section.get("word_count", 0)
            total_code += len(section.get("code_examples", []))
            total_diagrams += len(section.get("diagrams", []))
            total_tables += len(section.get("tables", []))
        
        # 更新统计信息
        formatted_doc["statistics"]["total_sections"] = len(sections)
        formatted_doc["statistics"]["total_words"] = total_words
        formatted_doc["statistics"]["total_code_examples"] = total_code
        formatted_doc["statistics"]["total_diagrams"] = total_diagrams
        formatted_doc["statistics"]["total_tables"] = total_tables
        
        # 设置格式化内容
        formatted_doc["formatted_content"] = "".join(content_parts)
        
        # 添加元数据
        if include_metadata:
            formatted_doc["metadata"] = {
                **document.get("metadata", {}),
                "formatted_at": datetime.utcnow().isoformat(),
                "ready_for_review": True
            }
        
        return json.dumps(formatted_doc, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"文档解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)


@tool
def extract_modification_priorities(
    modification_tasks: str,
    max_priority_items: int = 5
) -> str:
    """提取最高优先级的修改任务
    
    从完整的修改任务列表中提取最需要立即处理的任务，帮助Agent
    聚焦于最重要的改进点。
    
    Args:
        modification_tasks (str): 修改任务列表的JSON字符串
        max_priority_items (int): 最多返回的高优先级任务数量
        
    Returns:
        str: JSON格式的优先任务列表
            
    Example:
        >>> result = extract_modification_priorities(tasks, max_priority_items=3)
        >>> data = json.loads(result)
        >>> for task in data['priority_tasks']:
        ...     print(task['description'])
    """
    try:
        # 解析任务列表
        tasks = json.loads(modification_tasks)
        
        if tasks.get("status") != "success":
            return json.dumps({
                "status": "error",
                "error_message": "任务列表无效",
                "timestamp": datetime.utcnow().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 获取所有任务
        all_tasks = tasks.get("modification_tasks", [])
        
        # 按优先级和影响排序
        def task_score(task):
            priority_scores = {"high": 3, "medium": 2, "low": 1}
            impact_scores = {"high": 3, "medium": 2, "low": 1}
            
            priority = priority_scores.get(task.get("priority", "medium"), 2)
            impact = impact_scores.get(task.get("estimated_impact", "medium"), 2)
            
            return priority * 2 + impact  # 优先级权重更高
        
        sorted_tasks = sorted(all_tasks, key=task_score, reverse=True)
        
        # 提取优先任务
        priority_tasks = sorted_tasks[:max_priority_items]
        
        result = {
            "status": "success",
            "priority_tasks": priority_tasks,
            "total_tasks": len(all_tasks),
            "priority_tasks_count": len(priority_tasks),
            "priority_distribution": {
                "high": sum(1 for t in priority_tasks if t.get("priority") == "high"),
                "medium": sum(1 for t in priority_tasks if t.get("priority") == "medium"),
                "low": sum(1 for t in priority_tasks if t.get("priority") == "low")
            },
            "metadata": {
                "extracted_at": datetime.utcnow().isoformat()
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"任务列表解析失败: {str(e)}",
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, ensure_ascii=False, indent=2)
