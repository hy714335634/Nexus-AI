"""
信息提取工具模块

本模块提供从对话中提取儿童信息的功能。
包括兴趣识别、性格特征分析、话题偏好提取等。

作者: Nexus-AI平台
日期: 2025-11-26
版本: 1.0.0
"""

import json
import re
from typing import Any, Dict, List, Optional, Set
from strands import tool


# 兴趣关键词库
INTEREST_KEYWORDS = {
    "sports": ["足球", "篮球", "游泳", "跑步", "运动", "体育", "打球"],
    "arts": ["画画", "绘画", "音乐", "唱歌", "跳舞", "舞蹈", "乐器"],
    "reading": ["看书", "读书", "故事", "阅读", "书籍", "小说"],
    "science": ["科学", "实验", "发明", "探索", "研究", "恐龙", "太空", "星球"],
    "games": ["游戏", "玩具", "积木", "拼图", "电子游戏", "桌游"],
    "animals": ["动物", "宠物", "狗", "猫", "兔子", "小鸟", "鱼"],
    "nature": ["自然", "植物", "花", "树", "公园", "户外"],
    "technology": ["电脑", "平板", "机器人", "编程", "科技"],
    "cooking": ["做饭", "烹饪", "美食", "食物", "吃"],
    "crafts": ["手工", "制作", "折纸", "剪纸", "DIY"]
}

# 性格特征关键词库
PERSONALITY_KEYWORDS = {
    "outgoing": ["活泼", "开朗", "外向", "喜欢交朋友", "爱说话"],
    "shy": ["害羞", "内向", "安静", "不爱说话"],
    "curious": ["好奇", "爱问问题", "想知道", "为什么"],
    "creative": ["创造", "想象", "创意", "发明"],
    "patient": ["耐心", "细心", "认真"],
    "energetic": ["精力充沛", "活力", "好动"],
    "kind": ["善良", "友好", "温柔", "关心别人"],
    "brave": ["勇敢", "不怕", "敢于尝试"],
    "funny": ["幽默", "搞笑", "有趣", "爱笑"]
}

# 情绪关键词库
EMOTION_KEYWORDS = {
    "happy": ["开心", "高兴", "快乐", "兴奋", "愉快"],
    "sad": ["难过", "伤心", "不开心", "失落"],
    "angry": ["生气", "愤怒", "不高兴"],
    "scared": ["害怕", "恐惧", "担心", "紧张"],
    "surprised": ["惊讶", "意外", "没想到"],
    "proud": ["骄傲", "自豪", "得意"]
}


class InfoExtractor:
    """信息提取器"""
    
    def __init__(self):
        self.interest_keywords = INTEREST_KEYWORDS
        self.personality_keywords = PERSONALITY_KEYWORDS
        self.emotion_keywords = EMOTION_KEYWORDS
    
    def extract_interests(self, text: str) -> List[str]:
        """
        从文本中提取兴趣
        
        Args:
            text: 输入文本
        
        Returns:
            识别到的兴趣列表
        """
        interests = []
        text_lower = text.lower()
        
        for interest_type, keywords in self.interest_keywords.items():
            for keyword in keywords:
                if keyword in text or keyword.lower() in text_lower:
                    interests.append(interest_type)
                    break
        
        return list(set(interests))
    
    def extract_personality_traits(self, text: str) -> List[str]:
        """
        从文本中提取性格特征
        
        Args:
            text: 输入文本
        
        Returns:
            识别到的性格特征列表
        """
        traits = []
        text_lower = text.lower()
        
        for trait_type, keywords in self.personality_keywords.items():
            for keyword in keywords:
                if keyword in text or keyword.lower() in text_lower:
                    traits.append(trait_type)
                    break
        
        return list(set(traits))
    
    def extract_emotions(self, text: str) -> List[str]:
        """
        从文本中提取情绪
        
        Args:
            text: 输入文本
        
        Returns:
            识别到的情绪列表
        """
        emotions = []
        text_lower = text.lower()
        
        for emotion_type, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in text or keyword.lower() in text_lower:
                    emotions.append(emotion_type)
                    break
        
        return list(set(emotions))
    
    def extract_topics(self, text: str) -> List[str]:
        """
        提取对话话题
        
        Args:
            text: 输入文本
        
        Returns:
            话题列表
        """
        topics = []
        
        # 简单的话题提取：提取名词性短语
        # 这里使用简单的规则匹配，实际应用中可以使用NLP工具
        common_topics = [
            "学校", "家庭", "朋友", "老师", "爸爸", "妈妈",
            "周末", "假期", "生日", "节日", "作业", "考试",
            "梦想", "愿望", "未来", "长大"
        ]
        
        for topic in common_topics:
            if topic in text:
                topics.append(topic)
        
        return topics
    
    def extract_preferences(self, text: str) -> Dict[str, List[str]]:
        """
        提取喜好和厌恶
        
        Args:
            text: 输入文本
        
        Returns:
            包含喜欢和不喜欢的字典
        """
        likes = []
        dislikes = []
        
        # 匹配"喜欢"模式
        like_patterns = [
            r"喜欢(.{1,10})",
            r"爱(.{1,10})",
            r"最爱(.{1,10})",
            r"很喜欢(.{1,10})"
        ]
        
        for pattern in like_patterns:
            matches = re.findall(pattern, text)
            likes.extend([m.strip() for m in matches])
        
        # 匹配"不喜欢"模式
        dislike_patterns = [
            r"不喜欢(.{1,10})",
            r"讨厌(.{1,10})",
            r"不爱(.{1,10})"
        ]
        
        for pattern in dislike_patterns:
            matches = re.findall(pattern, text)
            dislikes.extend([m.strip() for m in matches])
        
        return {
            "likes": list(set(likes)),
            "dislikes": list(set(dislikes))
        }


@tool
def extract_child_info_from_message(
    message: str,
    extract_interests: bool = True,
    extract_personality: bool = True,
    extract_emotions: bool = True,
    extract_topics: bool = True,
    extract_preferences: bool = True
) -> str:
    """
    从消息中提取儿童信息
    
    Args:
        message: 用户消息文本
        extract_interests: 是否提取兴趣（默认True）
        extract_personality: 是否提取性格特征（默认True）
        extract_emotions: 是否提取情绪（默认True）
        extract_topics: 是否提取话题（默认True）
        extract_preferences: 是否提取喜好（默认True）
    
    Returns:
        JSON格式的提取结果
    """
    try:
        extractor = InfoExtractor()
        extracted_info = {}
        
        if extract_interests:
            extracted_info["interests"] = extractor.extract_interests(message)
        
        if extract_personality:
            extracted_info["personality_traits"] = extractor.extract_personality_traits(message)
        
        if extract_emotions:
            extracted_info["emotions"] = extractor.extract_emotions(message)
        
        if extract_topics:
            extracted_info["topics"] = extractor.extract_topics(message)
        
        if extract_preferences:
            extracted_info["preferences"] = extractor.extract_preferences(message)
        
        # 统计提取到的信息数量
        total_items = sum([
            len(v) if isinstance(v, list) else sum(len(vv) for vv in v.values())
            for v in extracted_info.values()
        ])
        
        return json.dumps({
            "status": "success",
            "message_length": len(message),
            "extracted_info": extracted_info,
            "total_items_extracted": total_items,
            "extraction_summary": {
                "interests_count": len(extracted_info.get("interests", [])),
                "personality_traits_count": len(extracted_info.get("personality_traits", [])),
                "emotions_count": len(extracted_info.get("emotions", [])),
                "topics_count": len(extracted_info.get("topics", [])),
                "preferences_count": sum(
                    len(v) for v in extracted_info.get("preferences", {}).values()
                )
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"信息提取失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def extract_info_from_conversation(
    conversation_turns: List[Dict[str, str]]
) -> str:
    """
    从完整对话中提取信息
    
    Args:
        conversation_turns: 对话轮次列表，每个元素包含user_message字段
    
    Returns:
        JSON格式的聚合提取结果
    """
    try:
        extractor = InfoExtractor()
        
        all_interests = []
        all_personality_traits = []
        all_emotions = []
        all_topics = []
        all_likes = []
        all_dislikes = []
        
        for turn in conversation_turns:
            user_msg = turn.get("user_message", "")
            
            # 提取各类信息
            all_interests.extend(extractor.extract_interests(user_msg))
            all_personality_traits.extend(extractor.extract_personality_traits(user_msg))
            all_emotions.extend(extractor.extract_emotions(user_msg))
            all_topics.extend(extractor.extract_topics(user_msg))
            
            prefs = extractor.extract_preferences(user_msg)
            all_likes.extend(prefs["likes"])
            all_dislikes.extend(prefs["dislikes"])
        
        # 去重
        unique_interests = list(set(all_interests))
        unique_personality_traits = list(set(all_personality_traits))
        unique_emotions = list(set(all_emotions))
        unique_topics = list(set(all_topics))
        unique_likes = list(set(all_likes))
        unique_dislikes = list(set(all_dislikes))
        
        # 统计频率
        interest_freq = {i: all_interests.count(i) for i in unique_interests}
        personality_freq = {p: all_personality_traits.count(p) for p in unique_personality_traits}
        emotion_freq = {e: all_emotions.count(e) for e in unique_emotions}
        topic_freq = {t: all_topics.count(t) for t in unique_topics}
        
        return json.dumps({
            "status": "success",
            "total_turns": len(conversation_turns),
            "aggregated_info": {
                "interests": unique_interests,
                "personality_traits": unique_personality_traits,
                "emotions": unique_emotions,
                "topics": unique_topics,
                "preferences": {
                    "likes": unique_likes,
                    "dislikes": unique_dislikes
                }
            },
            "frequency_analysis": {
                "interests": interest_freq,
                "personality_traits": personality_freq,
                "emotions": emotion_freq,
                "topics": topic_freq
            },
            "summary": {
                "total_interests": len(unique_interests),
                "total_personality_traits": len(unique_personality_traits),
                "total_emotions": len(unique_emotions),
                "total_topics": len(unique_topics),
                "total_likes": len(unique_likes),
                "total_dislikes": len(unique_dislikes)
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"对话信息提取失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def identify_age_from_message(message: str) -> str:
    """
    从消息中识别年龄信息
    
    Args:
        message: 用户消息文本
    
    Returns:
        JSON格式的年龄识别结果
    """
    try:
        # 匹配年龄模式
        age_patterns = [
            r"我(\d{1,2})岁",
            r"(\d{1,2})岁",
            r"今年(\d{1,2})",
            r"age\s*[:=]?\s*(\d{1,2})",
        ]
        
        identified_age = None
        matched_pattern = None
        
        for pattern in age_patterns:
            matches = re.findall(pattern, message)
            if matches:
                try:
                    age = int(matches[0])
                    if 1 <= age <= 18:
                        identified_age = age
                        matched_pattern = pattern
                        break
                except ValueError:
                    continue
        
        # 确定年龄组
        age_group = "unknown"
        if identified_age:
            if 3 <= identified_age <= 6:
                age_group = "3-6"
            elif 7 <= identified_age <= 9:
                age_group = "7-9"
            elif 10 <= identified_age <= 12:
                age_group = "10-12"
            elif identified_age > 12:
                age_group = "above-12"
        
        return json.dumps({
            "status": "success",
            "age_identified": identified_age is not None,
            "identified_age": identified_age,
            "age_group": age_group,
            "matched_pattern": matched_pattern,
            "message_length": len(message)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"年龄识别失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def identify_name_from_message(message: str) -> str:
    """
    从消息中识别姓名信息
    
    Args:
        message: 用户消息文本
    
    Returns:
        JSON格式的姓名识别结果
    """
    try:
        # 匹配姓名模式
        name_patterns = [
            r"我叫(.{2,10})",
            r"我的名字是(.{2,10})",
            r"叫我(.{2,10})",
            r"name\s*[:=]?\s*(.{2,10})",
        ]
        
        identified_name = None
        matched_pattern = None
        
        for pattern in name_patterns:
            matches = re.findall(pattern, message)
            if matches:
                name = matches[0].strip()
                # 过滤掉一些不像名字的内容
                if len(name) >= 2 and len(name) <= 10:
                    identified_name = name
                    matched_pattern = pattern
                    break
        
        return json.dumps({
            "status": "success",
            "name_identified": identified_name is not None,
            "identified_name": identified_name,
            "matched_pattern": matched_pattern,
            "message_length": len(message)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"姓名识别失败：{str(e)}"
        }, ensure_ascii=False, indent=2)


@tool
def suggest_conversation_topics(
    child_interests: List[str],
    child_age_group: str,
    recent_topics: Optional[List[str]] = None
) -> str:
    """
    根据儿童兴趣和年龄推荐对话话题
    
    Args:
        child_interests: 儿童兴趣列表
        child_age_group: 年龄组（3-6, 7-9, 10-12）
        recent_topics: 最近讨论的话题（可选）
    
    Returns:
        JSON格式的话题推荐结果
    """
    try:
        recent_topics = recent_topics or []
        
        # 基于兴趣的话题建议
        interest_based_topics = {
            "sports": ["最喜欢的运动", "运动明星", "运动比赛"],
            "arts": ["喜欢的画作", "音乐类型", "艺术创作"],
            "reading": ["喜欢的故事", "书中的角色", "阅读时间"],
            "science": ["科学实验", "自然现象", "科学家"],
            "games": ["喜欢的游戏", "游戏规则", "游戏朋友"],
            "animals": ["喜欢的动物", "宠物故事", "动物习性"],
            "nature": ["户外活动", "植物观察", "季节变化"],
            "technology": ["科技产品", "编程学习", "未来科技"],
            "cooking": ["喜欢的食物", "烹饪体验", "家庭美食"],
            "crafts": ["手工作品", "制作过程", "创意想法"]
        }
        
        # 年龄段通用话题
        age_based_topics = {
            "3-6": [
                "今天在幼儿园玩了什么",
                "喜欢的动画片",
                "最好的朋友",
                "喜欢的玩具",
                "家里的宠物"
            ],
            "7-9": [
                "学校里的趣事",
                "最喜欢的课程",
                "周末的计划",
                "最近的小发现",
                "想学的新技能"
            ],
            "10-12": [
                "兴趣爱好的发展",
                "未来的梦想",
                "最近读的书",
                "关心的社会话题",
                "科学和技术"
            ]
        }
        
        # 生成推荐话题
        suggested_topics = []
        
        # 基于兴趣的话题
        for interest in child_interests:
            if interest in interest_based_topics:
                suggested_topics.extend(interest_based_topics[interest])
        
        # 基于年龄的话题
        if child_age_group in age_based_topics:
            suggested_topics.extend(age_based_topics[child_age_group])
        
        # 过滤掉最近讨论过的话题
        suggested_topics = [t for t in suggested_topics if t not in recent_topics]
        
        # 去重
        suggested_topics = list(set(suggested_topics))
        
        return json.dumps({
            "status": "success",
            "child_interests": child_interests,
            "child_age_group": child_age_group,
            "suggested_topics": suggested_topics[:10],
            "total_suggestions": len(suggested_topics),
            "filtered_recent_topics": len(recent_topics)
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"话题推荐失败：{str(e)}"
        }, ensure_ascii=False, indent=2)