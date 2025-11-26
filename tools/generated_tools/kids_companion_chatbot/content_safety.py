"""
儿童内容安全检查工具模块

本模块提供内容安全检查功能，确保对话内容适合儿童。
包括敏感词过滤、不当内容检测和年龄适配性评估。

作者: Nexus-AI平台
日期: 2025-11-26
版本: 1.0.0
"""

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from strands import tool


# 敏感词库定义
SENSITIVE_WORDS = {
    "violence": ["暴力", "打人", "杀", "血", "死亡", "伤害", "武器"],
    "horror": ["恐怖", "鬼", "吓人", "可怕", "尸体", "僵尸"],
    "inappropriate": ["色情", "裸", "性", "黄色"],
    "negative": ["自杀", "抑郁", "绝望", "痛苦不堪"],
    "adult_topics": ["赌博", "酒", "烟", "毒品", "犯罪"]
}

# 年龄段词汇复杂度配置
AGE_VOCABULARY_LEVELS = {
    "3-6": {
        "max_word_length": 3,
        "max_sentence_length": 15,
        "preferred_patterns": ["简单", "有趣", "好玩", "开心", "喜欢"],
        "avoid_patterns": ["复杂", "困难", "抽象"]
    },
    "7-9": {
        "max_word_length": 5,
        "max_sentence_length": 25,
        "preferred_patterns": ["探索", "发现", "学习", "理解", "思考"],
        "avoid_patterns": ["深奥", "哲学", "复杂理论"]
    },
    "10-12": {
        "max_word_length": 8,
        "max_sentence_length": 40,
        "preferred_patterns": ["分析", "推理", "创造", "想象", "挑战"],
        "avoid_patterns": ["成人话题", "政治", "宗教争议"]
    }
}


class ContentSafetyChecker:
    """内容安全检查器"""
    
    def __init__(self):
        self.sensitive_words = SENSITIVE_WORDS
        self.age_levels = AGE_VOCABULARY_LEVELS
    
    def check_sensitive_words(self, text: str) -> Tuple[bool, List[str]]:
        """
        检查敏感词
        
        Args:
            text: 要检查的文本
        
        Returns:
            (是否安全, 发现的敏感词列表)
        """
        found_words = []
        text_lower = text.lower()
        
        for category, words in self.sensitive_words.items():
            for word in words:
                if word in text or word.lower() in text_lower:
                    found_words.append(f"{category}:{word}")
        
        is_safe = len(found_words) == 0
        return is_safe, found_words
    
    def check_age_appropriate(
        self,
        text: str,
        age_group: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        检查内容是否适合年龄段
        
        Args:
            text: 要检查的文本
            age_group: 年龄组（3-6, 7-9, 10-12）
        
        Returns:
            (是否适合, 详细分析)
        """
        if age_group not in self.age_levels:
            return True, {"message": "未知年龄组，跳过检查"}
        
        config = self.age_levels[age_group]
        issues = []
        
        # 检查句子长度
        sentences = re.split(r'[。！？]', text)
        long_sentences = [s for s in sentences if len(s) > config["max_sentence_length"]]
        if long_sentences:
            issues.append(f"句子过长：{len(long_sentences)}个句子超过{config['max_sentence_length']}字")
        
        # 检查避免模式
        for pattern in config["avoid_patterns"]:
            if pattern in text:
                issues.append(f"包含不适合年龄段的内容：{pattern}")
        
        is_appropriate = len(issues) == 0
        
        return is_appropriate, {
            "is_appropriate": is_appropriate,
            "issues": issues,
            "age_group": age_group,
            "sentence_count": len([s for s in sentences if s.strip()]),
            "long_sentences": len(long_sentences)
        }
    
    def suggest_improvements(
        self,
        text: str,
        age_group: str
    ) -> List[str]:
        """
        建议内容改进
        
        Args:
            text: 原始文本
            age_group: 年龄组
        
        Returns:
            改进建议列表
        """
        suggestions = []
        
        if age_group not in self.age_levels:
            return suggestions
        
        config = self.age_levels[age_group]
        
        # 句子长度建议
        sentences = re.split(r'[。！？]', text)
        long_sentences = [s for s in sentences if len(s) > config["max_sentence_length"]]
        if long_sentences:
            suggestions.append(f"将长句子拆分成更短的句子（建议不超过{config['max_sentence_length']}字）")
        
        # 词汇建议
        if age_group == "3-6":
            suggestions.append("使用更简单的词汇，多用叠词和拟声词")
            suggestions.append("增加互动性问题，如'你觉得呢？'")
        elif age_group == "7-9":
            suggestions.append("可以适当引入新词汇，但要解释含义")
            suggestions.append("鼓励思考和探索")
        elif age_group == "10-12":
            suggestions.append("可以讨论更深入的话题")
            suggestions.append("鼓励批判性思维")
        
        return suggestions


@tool
def check_content_safety(
    text: str,
    age_group: Optional[str] = None,
    strict_mode: bool = True
) -> str:
    """
    检查内容安全性
    
    Args:
        text: 要检查的文本内容
        age_group: 年龄组（3-6, 7-9, 10-12），可选
        strict_mode: 是否使用严格模式（默认True）
    
    Returns:
        JSON格式的安全检查结果
    """
    try:
        checker = ContentSafetyChecker()
        
        # 检查敏感词
        is_safe, sensitive_words = checker.check_sensitive_words(text)
        
        # 检查年龄适配性
        age_check_result = {"checked": False}
        if age_group:
            is_age_appropriate, age_details = checker.check_age_appropriate(text, age_group)
            age_check_result = {
                "checked": True,
                "is_appropriate": is_age_appropriate,
                "details": age_details
            }
        else:
            is_age_appropriate = True
        
        # 综合判断
        overall_safe = is_safe and is_age_appropriate
        
        # 生成建议
        suggestions = []
        if not is_safe:
            suggestions.append("内容包含敏感词，建议修改或移除")
        if age_group and not is_age_appropriate:
            suggestions.extend(checker.suggest_improvements(text, age_group))
        
        return json.dumps({
            "status": "success",
            "overall_safe": overall_safe,
            "checks": {
                "sensitive_words": {
                    "is_safe": is_safe,
                    "found_words": sensitive_words,
                    "count": len(sensitive_words)
                },
                "age_appropriate": age_check_result
            },
            "suggestions": suggestions,
            "text_length": len(text),
            "strict_mode": strict_mode
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"内容安全检查失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def filter_sensitive_content(
    text: str,
    replacement: str = "***"
) -> str:
    """
    过滤敏感内容
    
    Args:
        text: 原始文本
        replacement: 替换字符串（默认为"***"）
    
    Returns:
        JSON格式的过滤结果
    """
    try:
        checker = ContentSafetyChecker()
        filtered_text = text
        replacements = []
        
        # 替换敏感词
        for category, words in checker.sensitive_words.items():
            for word in words:
                if word in filtered_text:
                    filtered_text = filtered_text.replace(word, replacement)
                    replacements.append({
                        "category": category,
                        "word": word,
                        "replacement": replacement
                    })
        
        return json.dumps({
            "status": "success",
            "original_text": text,
            "filtered_text": filtered_text,
            "replacements": replacements,
            "replacement_count": len(replacements)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"内容过滤失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def assess_age_appropriateness(
    text: str,
    target_age_group: str
) -> str:
    """
    评估内容的年龄适配性
    
    Args:
        text: 要评估的文本
        target_age_group: 目标年龄组（3-6, 7-9, 10-12）
    
    Returns:
        JSON格式的评估结果
    """
    try:
        checker = ContentSafetyChecker()
        
        if target_age_group not in checker.age_levels:
            return json.dumps({
                "status": "error",
                "message": f"不支持的年龄组：{target_age_group}",
                "supported_age_groups": list(checker.age_levels.keys())
            }, ensure_ascii=False, indent=2)
        
        is_appropriate, details = checker.check_age_appropriate(text, target_age_group)
        suggestions = checker.suggest_improvements(text, target_age_group)
        
        # 计算适配性评分（0-100）
        score = 100
        if not is_appropriate:
            score -= len(details.get("issues", [])) * 20
        
        score = max(0, score)
        
        return json.dumps({
            "status": "success",
            "is_appropriate": is_appropriate,
            "appropriateness_score": score,
            "target_age_group": target_age_group,
            "details": details,
            "suggestions": suggestions
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"年龄适配性评估失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def generate_safe_alternative(
    text: str,
    age_group: str,
    reason: str = "内容不适合儿童"
) -> str:
    """
    生成安全的替代内容建议
    
    Args:
        text: 原始文本
        age_group: 年龄组（3-6, 7-9, 10-12）
        reason: 需要替代的原因
    
    Returns:
        JSON格式的替代建议
    """
    try:
        checker = ContentSafetyChecker()
        
        # 检查当前内容的问题
        is_safe, sensitive_words = checker.check_sensitive_words(text)
        is_appropriate, age_details = checker.check_age_appropriate(text, age_group)
        
        # 生成替代建议
        alternatives = []
        
        if not is_safe:
            alternatives.append({
                "type": "sensitive_content",
                "suggestion": "移除或替换敏感词汇，使用积极正面的表达",
                "found_issues": sensitive_words
            })
        
        if not is_appropriate:
            alternatives.append({
                "type": "age_inappropriate",
                "suggestion": "简化语言，使用更符合年龄段的表达方式",
                "found_issues": age_details.get("issues", [])
            })
        
        # 根据年龄组提供具体建议
        config = checker.age_levels.get(age_group, {})
        age_specific_suggestions = []
        
        if age_group == "3-6":
            age_specific_suggestions = [
                "使用简单的词汇和短句",
                "加入有趣的比喻和拟声词",
                "多用鼓励性语言"
            ]
        elif age_group == "7-9":
            age_specific_suggestions = [
                "使用适度复杂的词汇，但要解释新词",
                "引导思考和探索",
                "保持积极和鼓励的语气"
            ]
        elif age_group == "10-12":
            age_specific_suggestions = [
                "可以使用更丰富的词汇",
                "鼓励批判性思维",
                "引导深入讨论"
            ]
        
        return json.dumps({
            "status": "success",
            "original_text": text,
            "reason": reason,
            "age_group": age_group,
            "safety_check": {
                "is_safe": is_safe,
                "is_appropriate": is_appropriate
            },
            "alternatives": alternatives,
            "age_specific_suggestions": age_specific_suggestions,
            "general_guidelines": [
                "确保内容积极正面",
                "避免恐惧和焦虑",
                "鼓励好奇心和学习",
                "保持友好和耐心的语气"
            ]
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"生成替代建议失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def batch_check_conversation(
    conversation_turns: List[Dict[str, str]],
    age_group: str
) -> str:
    """
    批量检查对话内容的安全性
    
    Args:
        conversation_turns: 对话轮次列表，每个元素包含user_message和assistant_response
        age_group: 年龄组（3-6, 7-9, 10-12）
    
    Returns:
        JSON格式的批量检查结果
    """
    try:
        checker = ContentSafetyChecker()
        results = []
        
        total_safe = 0
        total_unsafe = 0
        
        for idx, turn in enumerate(conversation_turns):
            turn_id = idx + 1
            user_msg = turn.get("user_message", "")
            assistant_msg = turn.get("assistant_response", "")
            
            # 检查用户消息
            user_safe, user_sensitive = checker.check_sensitive_words(user_msg)
            
            # 检查助手回复
            assistant_safe, assistant_sensitive = checker.check_sensitive_words(assistant_msg)
            assistant_appropriate, assistant_age_details = checker.check_age_appropriate(
                assistant_msg, age_group
            )
            
            turn_safe = user_safe and assistant_safe and assistant_appropriate
            
            if turn_safe:
                total_safe += 1
            else:
                total_unsafe += 1
            
            results.append({
                "turn_id": turn_id,
                "is_safe": turn_safe,
                "user_message_check": {
                    "is_safe": user_safe,
                    "sensitive_words": user_sensitive
                },
                "assistant_response_check": {
                    "is_safe": assistant_safe,
                    "is_appropriate": assistant_appropriate,
                    "sensitive_words": assistant_sensitive,
                    "age_details": assistant_age_details
                }
            })
        
        overall_safety_rate = (total_safe / len(conversation_turns) * 100) if conversation_turns else 0
        
        return json.dumps({
            "status": "success",
            "total_turns": len(conversation_turns),
            "safe_turns": total_safe,
            "unsafe_turns": total_unsafe,
            "safety_rate": round(overall_safety_rate, 2),
            "age_group": age_group,
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"批量检查失败：{str(e)}"
        }, ensure_ascii=False, indent=2)