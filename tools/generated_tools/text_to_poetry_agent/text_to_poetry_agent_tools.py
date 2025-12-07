"""
Text to Poetry Agent Tools

本模块为text_to_poetry_agent提供工具函数支持。
根据设计规格，本Agent通过提示词工程实现所有功能，无需额外工具。

本文件作为占位符存在，以符合项目结构规范。
如果未来需要扩展功能（如诗歌评分、历史记录等），可在此添加工具函数。

Author: Nexus-AI Platform
Date: 2025-12-02
Version: 1.0
"""

from strands import tool
from typing import Dict, Any, Optional


# 本Agent通过提示词工程实现所有功能，无需额外工具
# 以下为预留的扩展工具示例（当前未使用）


@tool
def validate_input_text(text: str, max_length: int = 2000) -> Dict[str, Any]:
    """
    验证输入文本的有效性
    
    Args:
        text: 待验证的文本内容
        max_length: 最大允许长度，默认2000字
        
    Returns:
        Dict[str, Any]: 验证结果，包含以下字段：
            - valid: bool - 是否有效
            - message: str - 验证信息
            - processed_text: str - 处理后的文本（如截断）
            - warning: Optional[str] - 警告信息
    """
    result = {
        "valid": False,
        "message": "",
        "processed_text": "",
        "warning": None
    }
    
    try:
        # 检查文本是否为空
        if not text or not text.strip():
            result["message"] = "请提供有效的文字内容，以便我为您创作诗歌。"
            return result
        
        # 去除首尾空白
        processed_text = text.strip()
        
        # 检查长度
        if len(processed_text) > max_length:
            result["warning"] = f"您提供的文字内容超过{max_length}字，我将提取核心部分进行创作。建议简化内容以获得更精准的诗歌。"
            processed_text = processed_text[:max_length]
        
        # 验证通过
        result["valid"] = True
        result["message"] = "验证通过"
        result["processed_text"] = processed_text
        
    except Exception as e:
        result["message"] = f"文本验证失败: {str(e)}"
    
    return result


@tool
def format_poetry_output(title: str, content: str, style: str = "modern") -> str:
    """
    格式化诗歌输出
    
    Args:
        title: 诗歌标题
        content: 诗歌正文内容
        style: 诗歌风格，可选值：modern（现代诗）、classical（古体诗）、free（自由诗）
        
    Returns:
        str: 格式化后的诗歌文本
    """
    try:
        # 清理标题和内容
        title = title.strip()
        content = content.strip()
        
        # 确保标题不为空
        if not title:
            title = "无题"
        
        # 根据风格调整格式
        if style == "classical":
            # 古体诗：每句一行，无空行
            formatted_content = content.replace('\n\n', '\n')
        else:
            # 现代诗和自由诗：保持原格式
            formatted_content = content
        
        # 组装最终输出
        output = f"《{title}》\n\n{formatted_content}"
        
        return output
        
    except Exception as e:
        return f"格式化失败: {str(e)}\n\n原始内容：\n{title}\n{content}"


@tool
def extract_emotion_keywords(text: str) -> Dict[str, Any]:
    """
    提取文本中的情感关键词（预留功能）
    
    本函数当前未使用，因为情感分析通过提示词工程实现。
    预留用于未来可能的情感分析增强功能。
    
    Args:
        text: 待分析的文本
        
    Returns:
        Dict[str, Any]: 情感关键词分析结果
    """
    # 情感关键词词典（简化版示例）
    emotion_keywords = {
        "joy": ["开心", "快乐", "欢乐", "喜悦", "高兴", "愉快", "兴奋"],
        "sadness": ["悲伤", "难过", "伤心", "忧伤", "痛苦", "失落", "哀愁"],
        "longing": ["思念", "想念", "怀念", "回忆", "留恋", "牵挂"],
        "passion": ["激动", "热情", "澎湃", "激昂", "热血", "奋进"],
        "peace": ["平静", "宁静", "安详", "淡然", "从容", "平和"],
        "hope": ["希望", "期待", "憧憬", "向往", "梦想", "未来"],
        "anger": ["愤怒", "生气", "不满", "气愤", "恼怒"],
        "love": ["爱", "喜欢", "深情", "温柔", "亲密", "浪漫"],
        "loneliness": ["孤独", "寂寞", "孤单", "寂寥", "独自"],
        "gratitude": ["感谢", "感激", "感恩", "敬佩", "尊敬"]
    }
    
    result = {
        "detected_emotions": [],
        "keywords_found": {},
        "dominant_emotion": None
    }
    
    try:
        text_lower = text.lower()
        emotion_counts = {}
        
        # 统计各类情感关键词出现次数
        for emotion, keywords in emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text)
            if count > 0:
                emotion_counts[emotion] = count
                result["keywords_found"][emotion] = [kw for kw in keywords if kw in text]
        
        # 确定主导情感
        if emotion_counts:
            result["detected_emotions"] = list(emotion_counts.keys())
            result["dominant_emotion"] = max(emotion_counts, key=emotion_counts.get)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


# 注意：本文件中的工具函数当前未被Agent使用
# Agent通过提示词工程实现所有功能
# 这些工具函数预留用于未来可能的功能扩展
