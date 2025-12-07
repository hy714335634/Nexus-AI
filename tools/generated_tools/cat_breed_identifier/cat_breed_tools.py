"""
猫咪品种识别工具集

本模块为cat_breed_identifier Agent提供核心工具支持。
由于Agent设计采用"提示词工程为核心"的策略，充分利用LLM内置知识，
因此本模块主要提供辅助功能，而非核心识别逻辑。

核心功能由LLM通过提示词引导完成：
- 特征提取
- 品种匹配
- 置信度评估
- 习性信息生成

工具提供的辅助功能：
- 输入验证和清理
- 特征结构化
- 响应格式化
- 会话状态管理（如需要）

设计原则：
1. 最小化工具复杂度，避免重复LLM能力
2. 工具只做数据处理和验证，不做业务判断
3. 保持工具的通用性和可复用性
4. 遵循Strands框架规范

技术栈：
- Python 3.13+
- Strands框架（@tool装饰器）
- 标准库（re, json等）
"""

from strands import tool
from typing import Dict, Any, List, Optional
import re
import json


@tool
def validate_user_input(
    user_input: str,
    max_length: int = 500,
    min_length: int = 5
) -> str:
    """
    验证和清理用户输入
    
    功能：
    - 检查输入长度是否在合理范围
    - 移除多余空白字符
    - 检测并标记潜在的恶意输入
    - 提供清理后的文本和验证状态
    
    Args:
        user_input: 用户输入的原始文本
        max_length: 最大长度限制（默认500字符）
        min_length: 最小长度限制（默认5字符）
        
    Returns:
        str: JSON格式的验证结果
        {
            "is_valid": bool,
            "cleaned_input": str,
            "validation_errors": List[str],
            "warnings": List[str],
            "metadata": {
                "original_length": int,
                "cleaned_length": int,
                "removed_chars": int
            }
        }
    """
    try:
        result = {
            "is_valid": True,
            "cleaned_input": "",
            "validation_errors": [],
            "warnings": [],
            "metadata": {
                "original_length": 0,
                "cleaned_length": 0,
                "removed_chars": 0
            }
        }
        
        # 检查输入是否为空
        if not user_input or not isinstance(user_input, str):
            result["is_valid"] = False
            result["validation_errors"].append("输入为空或类型无效")
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        original_length = len(user_input)
        result["metadata"]["original_length"] = original_length
        
        # 长度验证
        if original_length < min_length:
            result["is_valid"] = False
            result["validation_errors"].append(f"输入过短（少于{min_length}个字符），请提供更详细的描述")
        
        if original_length > max_length:
            result["is_valid"] = False
            result["validation_errors"].append(f"输入过长（超过{max_length}个字符），请精简描述")
        
        # 清理输入
        cleaned = user_input.strip()
        # 移除多余的空白字符（连续多个空格/换行替换为单个空格）
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # 移除控制字符
        cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', cleaned)
        
        result["cleaned_input"] = cleaned
        result["metadata"]["cleaned_length"] = len(cleaned)
        result["metadata"]["removed_chars"] = original_length - len(cleaned)
        
        # 检测可能的问题模式
        # 检测是否包含过多重复字符（可能是垃圾输入）
        if re.search(r'(.)\1{10,}', cleaned):
            result["warnings"].append("检测到大量重复字符，可能影响识别准确性")
        
        # 检测是否只包含特殊字符和数字（缺少有意义的文本）
        if re.match(r'^[^a-zA-Z\u4e00-\u9fff]+$', cleaned):
            result["warnings"].append("输入缺少有意义的文字描述")
        
        # 检测是否包含URL（可能是恶意输入）
        if re.search(r'https?://', cleaned, re.IGNORECASE):
            result["warnings"].append("检测到URL链接，已保留但请注意这不会影响识别")
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "is_valid": False,
            "cleaned_input": "",
            "validation_errors": [f"输入验证失败: {str(e)}"],
            "warnings": [],
            "metadata": {
                "original_length": 0,
                "cleaned_length": 0,
                "removed_chars": 0
            }
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def extract_feature_keywords(
    text: str,
    feature_categories: Optional[List[str]] = None
) -> str:
    """
    从文本中提取特征关键词
    
    功能：
    - 识别毛色、体型、脸型、耳朵、眼睛、尾巴等特征关键词
    - 对关键词进行分类和结构化
    - 识别特征的修饰词（如"很长"、"特别圆"）
    - 标记可能的矛盾特征
    
    注意：这个工具只做关键词提取，不做品种推理。
    品种推理由LLM通过提示词完成。
    
    Args:
        text: 包含特征描述的文本
        feature_categories: 要提取的特征类别列表（可选）
                          默认: ["coat_color", "coat_length", "body_type", 
                                "face_shape", "ear_type", "eye_color", "tail_type"]
        
    Returns:
        str: JSON格式的提取结果
        {
            "extracted_features": {
                "coat_color": List[str],
                "coat_length": List[str],
                "body_type": List[str],
                "face_shape": List[str],
                "ear_type": List[str],
                "eye_color": List[str],
                "tail_type": List[str],
                "other": List[str]
            },
            "feature_modifiers": Dict[str, List[str]],
            "potential_conflicts": List[str],
            "completeness_score": float,
            "missing_categories": List[str]
        }
    """
    try:
        if feature_categories is None:
            feature_categories = [
                "coat_color", "coat_length", "body_type", 
                "face_shape", "ear_type", "eye_color", "tail_type"
            ]
        
        # 特征关键词库
        feature_patterns = {
            "coat_color": [
                "白色", "黑色", "灰色", "橙色", "棕色", "奶油色", "蓝色", "银色",
                "三花", "玳瑁", "虎斑", "重点色", "双色", "纯色", "渐层",
                "白", "黑", "灰", "橙", "棕", "蓝", "银", "金色", "黄色"
            ],
            "coat_length": [
                "长毛", "短毛", "中长毛", "无毛", "卷毛",
                "毛很长", "毛很短", "毛茸茸", "光滑"
            ],
            "body_type": [
                "大型", "中型", "小型", "壮实", "纤细", "苗条", "肌肉发达",
                "圆滚滚", "胖", "瘦", "粗壮", "优雅", "紧凑"
            ],
            "face_shape": [
                "圆脸", "扁脸", "尖脸", "三角形脸", "楔形脸",
                "脸很圆", "脸很扁", "鼻子扁", "鼻子长", "鼻子短"
            ],
            "ear_type": [
                "立耳", "折耳", "大耳朵", "小耳朵", "耳朵尖", "耳朵圆",
                "耳朵向前折", "耳朵向下折", "耳朵很大", "耳朵很小"
            ],
            "eye_color": [
                "蓝眼", "绿眼", "黄眼", "金眼", "琥珀色眼", "鸳鸯眼", "异色瞳",
                "眼睛蓝色", "眼睛绿色", "眼睛黄色", "眼睛是蓝色的"
            ],
            "tail_type": [
                "长尾", "短尾", "无尾", "尾巴蓬松", "尾巴细长",
                "尾巴很长", "尾巴很短", "尾巴粗", "尾巴细"
            ]
        }
        
        # 修饰词模式
        modifier_patterns = [
            "很", "非常", "特别", "极其", "超级", "比较", "稍微", "有点",
            "明显", "显著", "略微", "相当"
        ]
        
        result = {
            "extracted_features": {cat: [] for cat in feature_categories},
            "feature_modifiers": {},
            "potential_conflicts": [],
            "completeness_score": 0.0,
            "missing_categories": []
        }
        
        # 添加"other"类别用于未分类的关键词
        if "other" not in result["extracted_features"]:
            result["extracted_features"]["other"] = []
        
        text_lower = text.lower()
        
        # 提取特征关键词
        for category, keywords in feature_patterns.items():
            if category not in feature_categories:
                continue
                
            for keyword in keywords:
                if keyword in text_lower:
                    # 查找修饰词
                    modifiers = []
                    for modifier in modifier_patterns:
                        pattern = f"{modifier}[^，。！？]*{keyword}"
                        if re.search(pattern, text_lower):
                            modifiers.append(modifier)
                    
                    result["extracted_features"][category].append(keyword)
                    if modifiers:
                        result["feature_modifiers"][keyword] = modifiers
        
        # 检测潜在冲突
        conflicts = []
        
        # 毛长冲突
        coat_length = result["extracted_features"].get("coat_length", [])
        if "长毛" in coat_length and "短毛" in coat_length:
            conflicts.append("毛长描述冲突：同时提到'长毛'和'短毛'")
        
        # 体型冲突
        body_type = result["extracted_features"].get("body_type", [])
        if ("大型" in body_type or "壮实" in body_type) and ("小型" in body_type or "纤细" in body_type):
            conflicts.append("体型描述冲突：同时提到大型和小型特征")
        
        # 耳朵冲突
        ear_type = result["extracted_features"].get("ear_type", [])
        if "立耳" in ear_type and "折耳" in ear_type:
            conflicts.append("耳朵描述冲突：同时提到'立耳'和'折耳'")
        
        result["potential_conflicts"] = conflicts
        
        # 计算完整性评分
        extracted_count = sum(1 for cat in feature_categories 
                            if result["extracted_features"].get(cat, []))
        result["completeness_score"] = extracted_count / len(feature_categories)
        
        # 识别缺失的类别
        result["missing_categories"] = [
            cat for cat in feature_categories 
            if not result["extracted_features"].get(cat, [])
        ]
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "extracted_features": {},
            "feature_modifiers": {},
            "potential_conflicts": [],
            "completeness_score": 0.0,
            "missing_categories": feature_categories or [],
            "error": f"特征提取失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def format_breed_response(
    breed_name: str,
    confidence: str,
    characteristics: Dict[str, Any],
    alternative_breeds: Optional[List[str]] = None,
    follow_up_questions: Optional[List[str]] = None
) -> str:
    """
    格式化品种识别响应
    
    功能：
    - 将识别结果格式化为结构化、易读的输出
    - 添加适当的emoji和格式化标记
    - 组织习性信息的层次结构
    - 生成友好的文本描述
    
    Args:
        breed_name: 识别出的品种名称
        confidence: 置信度等级 ("高" / "中" / "低")
        characteristics: 品种特性字典，包含：
            - personality: 性格特点
            - care_level: 饲养难度
            - health_notes: 健康注意事项
            - living_environment: 环境要求
            - diet: 饮食特点
            - sociability: 社交能力
        alternative_breeds: 其他可能的品种列表（可选）
        follow_up_questions: 追问问题列表（可选）
        
    Returns:
        str: 格式化的响应文本
    """
    try:
        # 置信度emoji映射
        confidence_emoji = {
            "高": "✅",
            "中": "🤔",
            "低": "❓"
        }
        
        # 构建响应
        lines = []
        
        # 标题和置信度
        emoji = confidence_emoji.get(confidence, "🔍")
        lines.append(f"{emoji} **品种识别结果**")
        lines.append("")
        lines.append(f"**品种名称**: {breed_name}")
        lines.append(f"**识别置信度**: {confidence}")
        lines.append("")
        
        # 置信度说明
        if confidence == "高":
            lines.append("根据您的描述，这只猫咪的特征非常符合该品种的典型特征。")
        elif confidence == "中":
            lines.append("根据您的描述，这只猫咪的部分特征符合该品种，但可能需要更多信息来确认。")
        else:
            lines.append("根据您的描述，这只猫咪可能是该品种，但特征描述较少，建议提供更多信息。")
        lines.append("")
        
        # 习性信息
        lines.append("---")
        lines.append("## 🐱 品种特性")
        lines.append("")
        
        if "personality" in characteristics:
            lines.append(f"**性格特点**: {characteristics['personality']}")
            lines.append("")
        
        if "care_level" in characteristics:
            lines.append(f"**饲养难度**: {characteristics['care_level']}")
            lines.append("")
        
        if "health_notes" in characteristics:
            lines.append(f"**健康注意**: {characteristics['health_notes']}")
            lines.append("")
        
        if "living_environment" in characteristics:
            lines.append(f"**环境要求**: {characteristics['living_environment']}")
            lines.append("")
        
        if "diet" in characteristics:
            lines.append(f"**饮食特点**: {characteristics['diet']}")
            lines.append("")
        
        if "sociability" in characteristics:
            lines.append(f"**社交能力**: {characteristics['sociability']}")
            lines.append("")
        
        # 其他可能的品种
        if alternative_breeds:
            lines.append("---")
            lines.append("## 🔄 其他可能的品种")
            lines.append("")
            lines.append("根据描述，以下品种也有相似特征：")
            for alt_breed in alternative_breeds:
                lines.append(f"- {alt_breed}")
            lines.append("")
        
        # 追问问题
        if follow_up_questions:
            lines.append("---")
            lines.append("## ❓ 需要更多信息")
            lines.append("")
            lines.append("为了提高识别准确度，能否补充以下信息？")
            for i, question in enumerate(follow_up_questions, 1):
                lines.append(f"{i}. {question}")
            lines.append("")
        
        # 免责声明
        lines.append("---")
        lines.append("**注意**: 以上信息是该品种的一般特性，个体猫咪可能会有差异。如需专业建议，请咨询兽医或专业饲养员。")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error: 格式化响应失败: {str(e)}"


@tool
def generate_follow_up_questions(
    missing_features: List[str],
    current_confidence: str,
    candidate_breeds: Optional[List[str]] = None
) -> str:
    """
    生成追问问题
    
    功能：
    - 根据缺失的特征生成针对性的追问问题
    - 根据候选品种生成区分性问题
    - 优先询问关键特征
    - 提供选项式问题降低回答难度
    
    Args:
        missing_features: 缺失的特征类别列表
        current_confidence: 当前识别的置信度 ("高" / "中" / "低")
        candidate_breeds: 候选品种列表（可选，用于生成区分性问题）
        
    Returns:
        str: JSON格式的追问问题列表
        {
            "should_ask": bool,
            "questions": List[Dict[str, Any]],
            "rationale": str
        }
    """
    try:
        result = {
            "should_ask": False,
            "questions": [],
            "rationale": ""
        }
        
        # 决定是否需要追问
        # 高置信度且缺失特征少于3个：不追问
        if current_confidence == "高" and len(missing_features) < 3:
            result["rationale"] = "识别置信度高且特征信息较完整，无需追问"
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        # 低置信度或缺失关键特征：需要追问
        if current_confidence in ["低", "中"] or len(missing_features) >= 3:
            result["should_ask"] = True
        
        # 特征类别到问题的映射
        feature_questions = {
            "coat_color": {
                "question": "这只猫咪的毛色是什么？",
                "options": ["纯色（单一颜色）", "双色", "三花", "虎斑", "重点色", "其他"],
                "priority": 1
            },
            "coat_length": {
                "question": "这只猫咪的毛长如何？",
                "options": ["短毛", "中长毛", "长毛", "卷毛", "几乎无毛"],
                "priority": 1
            },
            "ear_type": {
                "question": "这只猫咪的耳朵是什么样的？",
                "options": ["正常立耳", "向前折叠", "向下折叠", "耳朵特别大", "耳朵特别小"],
                "priority": 2
            },
            "face_shape": {
                "question": "这只猫咪的脸型如何？",
                "options": ["圆脸扁鼻", "普通脸型", "尖脸长鼻", "三角形脸"],
                "priority": 2
            },
            "body_type": {
                "question": "这只猫咪的体型如何？",
                "options": ["小型纤细", "中型", "大型壮实", "肌肉发达"],
                "priority": 3
            },
            "eye_color": {
                "question": "这只猫咪的眼睛是什么颜色？",
                "options": ["蓝色", "绿色", "黄色/金色", "异色瞳", "不确定"],
                "priority": 3
            },
            "tail_type": {
                "question": "这只猫咪的尾巴如何？",
                "options": ["长尾", "短尾", "几乎无尾", "尾巴特别蓬松"],
                "priority": 4
            }
        }
        
        # 按优先级排序缺失特征
        prioritized_features = sorted(
            [f for f in missing_features if f in feature_questions],
            key=lambda f: feature_questions[f]["priority"]
        )
        
        # 生成问题（最多3个）
        for feature in prioritized_features[:3]:
            question_info = feature_questions[feature]
            result["questions"].append({
                "feature_category": feature,
                "question": question_info["question"],
                "options": question_info["options"],
                "priority": question_info["priority"]
            })
        
        # 如果有多个候选品种，生成区分性问题
        if candidate_breeds and len(candidate_breeds) > 1:
            # 这里可以根据候选品种生成更具针对性的问题
            # 简化版本：询问是否有特定品种的标志性特征
            result["questions"].append({
                "feature_category": "breed_specific",
                "question": "这只猫咪有没有什么特别明显的特征？比如折耳、扁脸、无尾、蓝眼等？",
                "options": ["有，请描述", "没有特别明显的特征"],
                "priority": 1
            })
        
        if result["questions"]:
            result["rationale"] = f"当前置信度为{current_confidence}，缺失{len(missing_features)}个特征类别，建议追问以提高准确度"
        else:
            result["should_ask"] = False
            result["rationale"] = "无需追问或无法生成有效问题"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "should_ask": False,
            "questions": [],
            "rationale": f"生成追问问题失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@tool
def calculate_feature_completeness(
    extracted_features: Dict[str, List[str]],
    required_features: Optional[List[str]] = None
) -> str:
    """
    计算特征完整性评分
    
    功能：
    - 评估已提供特征的完整程度
    - 识别关键缺失特征
    - 为置信度评估提供依据
    
    Args:
        extracted_features: 已提取的特征字典
        required_features: 必需特征列表（可选）
        
    Returns:
        str: JSON格式的完整性评估结果
        {
            "completeness_score": float,  # 0.0-1.0
            "completeness_level": str,    # "高" / "中" / "低"
            "provided_features": List[str],
            "missing_features": List[str],
            "critical_missing": List[str],
            "recommendation": str
        }
    """
    try:
        if required_features is None:
            required_features = [
                "coat_color", "coat_length", "body_type",
                "face_shape", "ear_type"
            ]
        
        # 识别关键特征（权重更高）
        critical_features = ["coat_color", "coat_length", "ear_type"]
        
        result = {
            "completeness_score": 0.0,
            "completeness_level": "低",
            "provided_features": [],
            "missing_features": [],
            "critical_missing": [],
            "recommendation": ""
        }
        
        # 统计已提供的特征
        provided = []
        for feature, values in extracted_features.items():
            if values and feature in required_features:
                provided.append(feature)
        
        result["provided_features"] = provided
        
        # 识别缺失特征
        missing = [f for f in required_features if f not in provided]
        result["missing_features"] = missing
        
        # 识别关键缺失特征
        critical_missing = [f for f in critical_features if f in missing]
        result["critical_missing"] = critical_missing
        
        # 计算完整性评分
        # 基础分：已提供特征 / 必需特征
        base_score = len(provided) / len(required_features) if required_features else 0
        
        # 关键特征惩罚：每缺失一个关键特征扣10%
        critical_penalty = len(critical_missing) * 0.1
        
        final_score = max(0.0, base_score - critical_penalty)
        result["completeness_score"] = round(final_score, 2)
        
        # 评定完整性等级
        if final_score >= 0.7:
            result["completeness_level"] = "高"
            result["recommendation"] = "特征信息较完整，可以进行准确识别"
        elif final_score >= 0.4:
            result["completeness_level"] = "中"
            result["recommendation"] = "特征信息部分完整，建议补充关键特征以提高准确度"
        else:
            result["completeness_level"] = "低"
            result["recommendation"] = "特征信息不足，强烈建议补充更多特征描述"
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "completeness_score": 0.0,
            "completeness_level": "低",
            "provided_features": [],
            "missing_features": required_features or [],
            "critical_missing": [],
            "recommendation": f"评估失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
