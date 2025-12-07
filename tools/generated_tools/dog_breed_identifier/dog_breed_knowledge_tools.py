"""
犬种识别知识工具集
提供犬种特征匹配、知识查询和信息提取功能
"""

from strands import tool
from typing import Dict, List, Any, Optional
import json
import re


@tool
def extract_dog_features(description: str) -> str:
    """
    从用户描述中提取犬只特征
    
    Args:
        description: 用户对小狗的描述文本
        
    Returns:
        str: JSON格式的特征提取结果
    """
    try:
        features = {
            "size": None,
            "colors": [],
            "coat_type": None,
            "coat_length": None,
            "ear_type": None,
            "tail_type": None,
            "weight": None,
            "temperament": [],
            "extracted_keywords": []
        }
        
        description_lower = description.lower()
        
        # 体型识别
        size_patterns = {
            "toy": ["玩具型", "超小型", "迷你", "袖珍", "toy", "tiny"],
            "small": ["小型", "小狗", "小犬", "small"],
            "medium": ["中型", "中等", "medium"],
            "large": ["大型", "大狗", "大犬", "large"],
            "giant": ["巨型", "超大型", "giant", "extra large"]
        }
        
        for size_key, patterns in size_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["size"] = size_key
                break
        
        # 毛色识别
        color_patterns = {
            "black": ["黑色", "黑", "black"],
            "white": ["白色", "白", "white"],
            "brown": ["棕色", "褐色", "咖啡色", "brown", "chocolate"],
            "golden": ["金色", "黄色", "金黄", "golden", "yellow"],
            "gray": ["灰色", "银色", "gray", "silver"],
            "red": ["红色", "红棕", "red", "rust"],
            "cream": ["奶油色", "米色", "cream", "beige"],
            "spotted": ["斑点", "花色", "spotted", "patched"],
            "brindle": ["虎斑", "条纹", "brindle", "striped"]
        }
        
        for color_key, patterns in color_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["colors"].append(color_key)
        
        # 毛质识别
        coat_type_patterns = {
            "smooth": ["光滑", "短毛", "smooth", "short"],
            "rough": ["粗糙", "硬毛", "rough", "wiry"],
            "curly": ["卷毛", "卷曲", "curly", "wavy"],
            "straight": ["直毛", "直", "straight"],
            "double": ["双层毛", "厚毛", "double coat"]
        }
        
        for coat_key, patterns in coat_type_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["coat_type"] = coat_key
                break
        
        # 毛长识别
        coat_length_patterns = {
            "short": ["短毛", "短", "short"],
            "medium": ["中长", "中等", "medium"],
            "long": ["长毛", "长", "long"]
        }
        
        for length_key, patterns in coat_length_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["coat_length"] = length_key
                break
        
        # 耳型识别
        ear_patterns = {
            "erect": ["立耳", "竖耳", "直立", "erect", "pricked"],
            "drop": ["垂耳", "下垂", "drop", "hanging"],
            "folded": ["折耳", "折叠", "folded"],
            "rose": ["玫瑰耳", "rose"]
        }
        
        for ear_key, patterns in ear_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["ear_type"] = ear_key
                break
        
        # 尾型识别
        tail_patterns = {
            "curled": ["卷尾", "卷曲", "curled"],
            "straight": ["直尾", "直", "straight"],
            "docked": ["断尾", "短尾", "docked", "bobbed"],
            "plumed": ["羽状尾", "毛茸茸", "plumed", "feathered"]
        }
        
        for tail_key, patterns in tail_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["tail_type"] = tail_key
                break
        
        # 体重提取（使用正则表达式）
        weight_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:kg|公斤|千克)',
            r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|磅)',
            r'体重.*?(\d+(?:\.\d+)?)',
            r'重.*?(\d+(?:\.\d+)?)'
        ]
        
        for pattern in weight_patterns:
            match = re.search(pattern, description_lower)
            if match:
                weight_value = float(match.group(1))
                # 转换为kg
                if 'lb' in pattern or '磅' in pattern:
                    weight_value = weight_value * 0.453592
                features["weight"] = round(weight_value, 1)
                break
        
        # 性格特征识别
        temperament_patterns = {
            "friendly": ["友好", "友善", "亲切", "friendly", "affectionate"],
            "energetic": ["活泼", "精力充沛", "energetic", "active"],
            "calm": ["冷静", "平静", "calm", "gentle"],
            "intelligent": ["聪明", "智慧", "intelligent", "smart"],
            "loyal": ["忠诚", "忠实", "loyal", "devoted"],
            "protective": ["保护", "警惕", "protective", "guard"],
            "playful": ["爱玩", "顽皮", "playful"],
            "independent": ["独立", "自主", "independent"]
        }
        
        for temp_key, patterns in temperament_patterns.items():
            if any(pattern in description_lower for pattern in patterns):
                features["temperament"].append(temp_key)
        
        # 提取所有关键词
        words = re.findall(r'\w+', description_lower)
        features["extracted_keywords"] = list(set(words))[:20]  # 限制20个关键词
        
        return json.dumps({
            "success": True,
            "features": features,
            "original_description": description
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "feature_extraction_error"
        }, ensure_ascii=False, indent=2)


@tool
def match_dog_breeds(features: str) -> str:
    """
    根据提取的特征匹配可能的犬种
    
    Args:
        features: JSON格式的特征数据（由extract_dog_features生成）
        
    Returns:
        str: JSON格式的匹配结果，包含可能的犬种列表
    """
    try:
        feature_data = json.loads(features)
        
        if not feature_data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Invalid features data"
            }, ensure_ascii=False, indent=2)
        
        extracted_features = feature_data.get("features", {})
        
        # 犬种特征数据库（精简版，实际应用中应包含200-300个品种）
        breed_database = {
            "golden_retriever": {
                "name_zh": "金毛寻回犬",
                "name_en": "Golden Retriever",
                "size": "large",
                "colors": ["golden", "cream"],
                "coat_type": "straight",
                "coat_length": "medium",
                "ear_type": "drop",
                "tail_type": "plumed",
                "weight_range": [25, 34],
                "temperament": ["friendly", "intelligent", "loyal"],
                "origin": "苏格兰",
                "group": "运动犬组"
            },
            "labrador_retriever": {
                "name_zh": "拉布拉多寻回犬",
                "name_en": "Labrador Retriever",
                "size": "large",
                "colors": ["black", "golden", "brown"],
                "coat_type": "smooth",
                "coat_length": "short",
                "ear_type": "drop",
                "tail_type": "straight",
                "weight_range": [25, 36],
                "temperament": ["friendly", "energetic", "intelligent"],
                "origin": "加拿大",
                "group": "运动犬组"
            },
            "german_shepherd": {
                "name_zh": "德国牧羊犬",
                "name_en": "German Shepherd",
                "size": "large",
                "colors": ["black", "brown"],
                "coat_type": "double",
                "coat_length": "medium",
                "ear_type": "erect",
                "tail_type": "straight",
                "weight_range": [22, 40],
                "temperament": ["intelligent", "loyal", "protective"],
                "origin": "德国",
                "group": "牧羊犬组"
            },
            "poodle": {
                "name_zh": "贵宾犬",
                "name_en": "Poodle",
                "size": "medium",
                "colors": ["white", "black", "brown", "gray"],
                "coat_type": "curly",
                "coat_length": "long",
                "ear_type": "drop",
                "tail_type": "docked",
                "weight_range": [20, 32],
                "temperament": ["intelligent", "playful", "friendly"],
                "origin": "法国",
                "group": "非运动犬组"
            },
            "chihuahua": {
                "name_zh": "吉娃娃",
                "name_en": "Chihuahua",
                "size": "toy",
                "colors": ["brown", "black", "white", "cream"],
                "coat_type": "smooth",
                "coat_length": "short",
                "ear_type": "erect",
                "tail_type": "curled",
                "weight_range": [1, 3],
                "temperament": ["loyal", "energetic", "independent"],
                "origin": "墨西哥",
                "group": "玩具犬组"
            },
            "husky": {
                "name_zh": "西伯利亚雪橇犬",
                "name_en": "Siberian Husky",
                "size": "medium",
                "colors": ["gray", "black", "white"],
                "coat_type": "double",
                "coat_length": "medium",
                "ear_type": "erect",
                "tail_type": "curled",
                "weight_range": [16, 27],
                "temperament": ["energetic", "friendly", "independent"],
                "origin": "西伯利亚",
                "group": "工作犬组"
            },
            "bulldog": {
                "name_zh": "斗牛犬",
                "name_en": "Bulldog",
                "size": "medium",
                "colors": ["white", "brown", "brindle"],
                "coat_type": "smooth",
                "coat_length": "short",
                "ear_type": "rose",
                "tail_type": "straight",
                "weight_range": [18, 25],
                "temperament": ["calm", "friendly", "loyal"],
                "origin": "英国",
                "group": "非运动犬组"
            },
            "beagle": {
                "name_zh": "比格犬",
                "name_en": "Beagle",
                "size": "small",
                "colors": ["brown", "white", "black"],
                "coat_type": "smooth",
                "coat_length": "short",
                "ear_type": "drop",
                "tail_type": "straight",
                "weight_range": [9, 11],
                "temperament": ["friendly", "energetic", "playful"],
                "origin": "英国",
                "group": "猎犬组"
            },
            "shiba_inu": {
                "name_zh": "柴犬",
                "name_en": "Shiba Inu",
                "size": "small",
                "colors": ["red", "black", "cream"],
                "coat_type": "double",
                "coat_length": "short",
                "ear_type": "erect",
                "tail_type": "curled",
                "weight_range": [8, 11],
                "temperament": ["independent", "loyal", "alert"],
                "origin": "日本",
                "group": "非运动犬组"
            },
            "corgi": {
                "name_zh": "柯基犬",
                "name_en": "Welsh Corgi",
                "size": "small",
                "colors": ["red", "brown", "black", "white"],
                "coat_type": "double",
                "coat_length": "medium",
                "ear_type": "erect",
                "tail_type": "docked",
                "weight_range": [10, 14],
                "temperament": ["friendly", "intelligent", "playful"],
                "origin": "威尔士",
                "group": "牧羊犬组"
            }
        }
        
        # 计算匹配分数
        matches = []
        
        for breed_id, breed_data in breed_database.items():
            score = 0
            max_score = 0
            match_details = []
            
            # 体型匹配（权重：20）
            max_score += 20
            if extracted_features.get("size") == breed_data.get("size"):
                score += 20
                match_details.append("体型匹配")
            elif extracted_features.get("size"):
                match_details.append(f"体型不匹配（描述：{extracted_features.get('size')}，标准：{breed_data.get('size')}）")
            
            # 毛色匹配（权重：15）
            if extracted_features.get("colors"):
                max_score += 15
                color_match = any(c in breed_data.get("colors", []) for c in extracted_features.get("colors", []))
                if color_match:
                    score += 15
                    match_details.append("毛色匹配")
                else:
                    match_details.append(f"毛色不匹配")
            
            # 毛质匹配（权重：10）
            if extracted_features.get("coat_type"):
                max_score += 10
                if extracted_features.get("coat_type") == breed_data.get("coat_type"):
                    score += 10
                    match_details.append("毛质匹配")
                else:
                    match_details.append(f"毛质不匹配")
            
            # 毛长匹配（权重：10）
            if extracted_features.get("coat_length"):
                max_score += 10
                if extracted_features.get("coat_length") == breed_data.get("coat_length"):
                    score += 10
                    match_details.append("毛长匹配")
                else:
                    match_details.append(f"毛长不匹配")
            
            # 耳型匹配（权重：10）
            if extracted_features.get("ear_type"):
                max_score += 10
                if extracted_features.get("ear_type") == breed_data.get("ear_type"):
                    score += 10
                    match_details.append("耳型匹配")
                else:
                    match_details.append(f"耳型不匹配")
            
            # 尾型匹配（权重：10）
            if extracted_features.get("tail_type"):
                max_score += 10
                if extracted_features.get("tail_type") == breed_data.get("tail_type"):
                    score += 10
                    match_details.append("尾型匹配")
                else:
                    match_details.append(f"尾型不匹配")
            
            # 体重匹配（权重：15）
            if extracted_features.get("weight"):
                max_score += 15
                weight = extracted_features.get("weight")
                weight_range = breed_data.get("weight_range", [0, 999])
                if weight_range[0] <= weight <= weight_range[1]:
                    score += 15
                    match_details.append("体重匹配")
                else:
                    match_details.append(f"体重不匹配（描述：{weight}kg，标准：{weight_range[0]}-{weight_range[1]}kg）")
            
            # 性格匹配（权重：10）
            if extracted_features.get("temperament"):
                max_score += 10
                temp_match = any(t in breed_data.get("temperament", []) for t in extracted_features.get("temperament", []))
                if temp_match:
                    score += 10
                    match_details.append("性格匹配")
                else:
                    match_details.append(f"性格不完全匹配")
            
            # 计算置信度（0-100）
            confidence = round((score / max_score * 100) if max_score > 0 else 0, 1)
            
            if confidence > 20:  # 只保留置信度大于20的匹配
                matches.append({
                    "breed_id": breed_id,
                    "name_zh": breed_data["name_zh"],
                    "name_en": breed_data["name_en"],
                    "confidence": confidence,
                    "match_score": score,
                    "max_score": max_score,
                    "match_details": match_details,
                    "breed_info": {
                        "origin": breed_data.get("origin"),
                        "group": breed_data.get("group"),
                        "size": breed_data.get("size"),
                        "weight_range": breed_data.get("weight_range")
                    }
                })
        
        # 按置信度排序
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        # 只返回前3个匹配
        top_matches = matches[:3]
        
        return json.dumps({
            "success": True,
            "total_matches": len(matches),
            "top_matches": top_matches,
            "match_quality": "high" if (top_matches and top_matches[0]["confidence"] >= 70) else "medium" if (top_matches and top_matches[0]["confidence"] >= 50) else "low"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "breed_matching_error"
        }, ensure_ascii=False, indent=2)


@tool
def get_breed_habits(breed_id: str) -> str:
    """
    获取指定犬种的生活习惯信息
    
    Args:
        breed_id: 犬种ID（如 golden_retriever）
        
    Returns:
        str: JSON格式的生活习惯信息
    """
    try:
        # 犬种生活习惯数据库
        habits_database = {
            "golden_retriever": {
                "breed_name_zh": "金毛寻回犬",
                "breed_name_en": "Golden Retriever",
                "diet": {
                    "daily_calories": "1500-1800卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，富含蛋白质和脂肪",
                    "special_needs": "需要控制食量避免肥胖，可适量添加鱼油补充Omega-3",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "木糖醇"]
                },
                "exercise": {
                    "daily_duration": "60-90分钟",
                    "activity_level": "高",
                    "recommended_activities": ["游泳", "捡球", "慢跑", "飞盘"],
                    "exercise_notes": "精力旺盛，需要充足运动，游泳是最佳选择"
                },
                "temperament": {
                    "personality_traits": ["友好", "温和", "聪明", "忠诚", "耐心"],
                    "social_behavior": "对人友好，对其他动物友善，适合家庭饲养",
                    "trainability": "极高，学习能力强，容易训练",
                    "child_friendly": "非常适合，耐心温和",
                    "stranger_tolerance": "友好，不具攻击性"
                },
                "grooming": {
                    "brushing_frequency": "每周2-3次",
                    "bathing_frequency": "每月1-2次",
                    "shedding_level": "中等到高，春秋换毛期大量掉毛",
                    "grooming_needs": ["定期刷毛", "修剪指甲", "清洁耳朵", "刷牙"],
                    "professional_grooming": "每2-3个月一次专业美容"
                },
                "health": {
                    "common_issues": ["髋关节发育不良", "肘关节发育不良", "眼部疾病", "心脏病", "癌症"],
                    "lifespan": "10-12年",
                    "health_screening": ["髋关节X光", "眼科检查", "心脏检查"],
                    "preventive_care": "定期体检、疫苗接种、驱虫",
                    "special_attention": "注意体重控制，定期检查关节和眼睛"
                }
            },
            "labrador_retriever": {
                "breed_name_zh": "拉布拉多寻回犬",
                "breed_name_en": "Labrador Retriever",
                "diet": {
                    "daily_calories": "1500-1900卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，蛋白质含量25-30%",
                    "special_needs": "容易肥胖，需严格控制食量",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "高脂肪食物"]
                },
                "exercise": {
                    "daily_duration": "60-90分钟",
                    "activity_level": "非常高",
                    "recommended_activities": ["游泳", "捡球", "慢跑", "敏捷训练"],
                    "exercise_notes": "精力极其旺盛，需要大量运动"
                },
                "temperament": {
                    "personality_traits": ["友好", "外向", "活泼", "温和", "聪明"],
                    "social_behavior": "极度友好，对所有人和动物都友善",
                    "trainability": "极高，是最易训练的犬种之一",
                    "child_friendly": "非常适合，耐心温和",
                    "stranger_tolerance": "非常友好，不适合做看门犬"
                },
                "grooming": {
                    "brushing_frequency": "每周1-2次",
                    "bathing_frequency": "每月1次",
                    "shedding_level": "中等，换毛期较多",
                    "grooming_needs": ["定期刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["髋关节发育不良", "肘关节发育不良", "肥胖", "眼部疾病"],
                    "lifespan": "10-12年",
                    "health_screening": ["髋关节X光", "眼科检查", "体重监控"],
                    "preventive_care": "定期体检、疫苗接种、体重控制",
                    "special_attention": "极易肥胖，需严格饮食管理"
                }
            },
            "german_shepherd": {
                "breed_name_zh": "德国牧羊犬",
                "breed_name_en": "German Shepherd",
                "diet": {
                    "daily_calories": "1700-2100卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高蛋白狗粮，适合大型工作犬",
                    "special_needs": "需要充足蛋白质支持肌肉发育",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "过量脂肪"]
                },
                "exercise": {
                    "daily_duration": "60-120分钟",
                    "activity_level": "非常高",
                    "recommended_activities": ["跑步", "敏捷训练", "追踪训练", "服从训练"],
                    "exercise_notes": "需要大量运动和心智刺激"
                },
                "temperament": {
                    "personality_traits": ["聪明", "忠诚", "勇敢", "警惕", "自信"],
                    "social_behavior": "对家人忠诚，对陌生人警惕，需要社会化训练",
                    "trainability": "极高，工作能力强",
                    "child_friendly": "适合，但需要监督",
                    "stranger_tolerance": "警惕，有保护意识"
                },
                "grooming": {
                    "brushing_frequency": "每周3-4次",
                    "bathing_frequency": "每月1-2次",
                    "shedding_level": "高，常年掉毛",
                    "grooming_needs": ["频繁刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "每3-4个月一次"
                },
                "health": {
                    "common_issues": ["髋关节发育不良", "肘关节发育不良", "脊椎问题", "胃扭转"],
                    "lifespan": "9-13年",
                    "health_screening": ["髋关节X光", "肘关节X光", "脊椎检查"],
                    "preventive_care": "定期体检、关节保健、避免剧烈跳跃",
                    "special_attention": "注意关节健康，避免过早剧烈运动"
                }
            },
            "poodle": {
                "breed_name_zh": "贵宾犬",
                "breed_name_en": "Poodle",
                "diet": {
                    "daily_calories": "900-1200卡路里（标准型成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，适合敏感肠胃",
                    "special_needs": "可能有食物过敏，需注意食材选择",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "过敏原食物"]
                },
                "exercise": {
                    "daily_duration": "40-60分钟",
                    "activity_level": "中等到高",
                    "recommended_activities": ["散步", "游泳", "敏捷训练", "智力游戏"],
                    "exercise_notes": "聪明活泼，需要心智刺激"
                },
                "temperament": {
                    "personality_traits": ["聪明", "活泼", "优雅", "友好", "敏感"],
                    "social_behavior": "友好但有时保留，需要社会化",
                    "trainability": "极高，学习能力强",
                    "child_friendly": "适合，但需要温和对待",
                    "stranger_tolerance": "友好但可能保留"
                },
                "grooming": {
                    "brushing_frequency": "每天",
                    "bathing_frequency": "每3-6周",
                    "shedding_level": "极低，适合过敏人群",
                    "grooming_needs": ["每天刷毛防打结", "定期修剪", "清洁耳朵", "修剪指甲"],
                    "professional_grooming": "每6-8周必须专业美容"
                },
                "health": {
                    "common_issues": ["髋关节发育不良", "眼部疾病", "耳部感染", "皮肤问题"],
                    "lifespan": "12-15年",
                    "health_screening": ["眼科检查", "髋关节检查", "耳部检查"],
                    "preventive_care": "定期体检、耳部清洁、牙齿护理",
                    "special_attention": "注意耳部清洁，防止感染"
                }
            },
            "chihuahua": {
                "breed_name_zh": "吉娃娃",
                "breed_name_en": "Chihuahua",
                "diet": {
                    "daily_calories": "200-400卡路里（成年犬）",
                    "feeding_frequency": "每天2-3次（小份量）",
                    "food_type": "小型犬专用狗粮，颗粒要小",
                    "special_needs": "容易低血糖，需要少食多餐",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "大块食物"]
                },
                "exercise": {
                    "daily_duration": "20-30分钟",
                    "activity_level": "中等",
                    "recommended_activities": ["室内玩耍", "短距离散步", "玩具互动"],
                    "exercise_notes": "体型小，运动需求不大，注意保暖"
                },
                "temperament": {
                    "personality_traits": ["忠诚", "警惕", "勇敢", "活泼", "占有欲强"],
                    "social_behavior": "对主人极度忠诚，对陌生人警惕",
                    "trainability": "中等，可能固执",
                    "child_friendly": "不太适合，容易受伤",
                    "stranger_tolerance": "警惕，爱叫"
                },
                "grooming": {
                    "brushing_frequency": "每周1-2次",
                    "bathing_frequency": "每月1次",
                    "shedding_level": "低到中等",
                    "grooming_needs": ["刷毛", "修剪指甲", "清洁耳朵", "牙齿护理"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["心脏病", "牙齿问题", "髌骨脱位", "气管塌陷", "低血糖"],
                    "lifespan": "12-20年",
                    "health_screening": ["心脏检查", "牙科检查", "膝盖检查"],
                    "preventive_care": "定期牙科护理、心脏检查、保暖",
                    "special_attention": "容易受寒，需要保暖；牙齿易出问题，需定期护理"
                }
            },
            "husky": {
                "breed_name_zh": "西伯利亚雪橇犬",
                "breed_name_en": "Siberian Husky",
                "diet": {
                    "daily_calories": "1200-1600卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高蛋白狗粮，适合活跃犬种",
                    "special_needs": "代谢效率高，食量相对较小",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "高脂肪食物"]
                },
                "exercise": {
                    "daily_duration": "90-120分钟",
                    "activity_level": "极高",
                    "recommended_activities": ["跑步", "拉雪橇", "徒步", "玩雪"],
                    "exercise_notes": "精力极其旺盛，需要大量运动，喜欢寒冷天气"
                },
                "temperament": {
                    "personality_traits": ["友好", "外向", "独立", "顽皮", "爱自由"],
                    "social_behavior": "友好但独立，喜欢群体生活",
                    "trainability": "中等，独立性强，可能固执",
                    "child_friendly": "友好，但精力太旺盛",
                    "stranger_tolerance": "友好，不适合看家"
                },
                "grooming": {
                    "brushing_frequency": "每周2-3次（换毛期每天）",
                    "bathing_frequency": "每2-3个月",
                    "shedding_level": "极高，一年两次大量掉毛",
                    "grooming_needs": ["频繁刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["髋关节发育不良", "眼部疾病", "皮肤问题"],
                    "lifespan": "12-14年",
                    "health_screening": ["眼科检查", "髋关节检查"],
                    "preventive_care": "定期体检、眼部检查、充足运动",
                    "special_attention": "怕热，夏天需要降温；容易逃跑，需要安全围栏"
                }
            },
            "bulldog": {
                "breed_name_zh": "斗牛犬",
                "breed_name_en": "Bulldog",
                "diet": {
                    "daily_calories": "1000-1400卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，易消化",
                    "special_needs": "容易肥胖和食物过敏",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "高脂肪食物"]
                },
                "exercise": {
                    "daily_duration": "20-40分钟",
                    "activity_level": "低",
                    "recommended_activities": ["短距离散步", "室内玩耍"],
                    "exercise_notes": "不耐热，不适合剧烈运动，容易呼吸困难"
                },
                "temperament": {
                    "personality_traits": ["温和", "友好", "勇敢", "固执", "忠诚"],
                    "social_behavior": "友好温和，对人友善",
                    "trainability": "中等，可能固执",
                    "child_friendly": "非常适合，温和耐心",
                    "stranger_tolerance": "友好"
                },
                "grooming": {
                    "brushing_frequency": "每周1-2次",
                    "bathing_frequency": "每月1次",
                    "shedding_level": "中等",
                    "grooming_needs": ["刷毛", "清洁皱褶", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["呼吸问题", "皮肤褶皱感染", "髋关节发育不良", "心脏病", "眼部问题"],
                    "lifespan": "8-10年",
                    "health_screening": ["呼吸道检查", "心脏检查", "髋关节检查"],
                    "preventive_care": "定期清洁皱褶、控制体重、避免过热",
                    "special_attention": "怕热，需要空调；呼吸道问题常见，避免剧烈运动"
                }
            },
            "beagle": {
                "breed_name_zh": "比格犬",
                "breed_name_en": "Beagle",
                "diet": {
                    "daily_calories": "600-900卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，控制份量",
                    "special_needs": "食欲旺盛，容易肥胖",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "高脂肪食物"]
                },
                "exercise": {
                    "daily_duration": "60-90分钟",
                    "activity_level": "高",
                    "recommended_activities": ["散步", "追踪游戏", "嗅觉训练"],
                    "exercise_notes": "精力旺盛，喜欢追踪气味"
                },
                "temperament": {
                    "personality_traits": ["友好", "好奇", "快乐", "固执", "精力充沛"],
                    "social_behavior": "非常友好，喜欢群体",
                    "trainability": "中等，容易分心",
                    "child_friendly": "非常适合，温和友好",
                    "stranger_tolerance": "友好，不适合看家"
                },
                "grooming": {
                    "brushing_frequency": "每周1-2次",
                    "bathing_frequency": "每月1次",
                    "shedding_level": "中等",
                    "grooming_needs": ["刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["肥胖", "耳部感染", "髋关节发育不良", "癫痫"],
                    "lifespan": "12-15年",
                    "health_screening": ["髋关节检查", "眼科检查", "耳部检查"],
                    "preventive_care": "控制体重、定期清洁耳朵、充足运动",
                    "special_attention": "极易肥胖，需严格控制饮食；耳朵长，易感染"
                }
            },
            "shiba_inu": {
                "breed_name_zh": "柴犬",
                "breed_name_en": "Shiba Inu",
                "diet": {
                    "daily_calories": "600-900卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，适合中小型犬",
                    "special_needs": "可能有食物过敏",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "过敏原食物"]
                },
                "exercise": {
                    "daily_duration": "40-60分钟",
                    "activity_level": "中等到高",
                    "recommended_activities": ["散步", "徒步", "玩耍"],
                    "exercise_notes": "活泼好动，需要适量运动"
                },
                "temperament": {
                    "personality_traits": ["独立", "忠诚", "警惕", "自信", "固执"],
                    "social_behavior": "对主人忠诚，对陌生人保留",
                    "trainability": "中等，独立性强",
                    "child_friendly": "适合，但需要监督",
                    "stranger_tolerance": "保留，有警惕性"
                },
                "grooming": {
                    "brushing_frequency": "每周2-3次（换毛期每天）",
                    "bathing_frequency": "每2-3个月",
                    "shedding_level": "高，一年两次大量掉毛",
                    "grooming_needs": ["刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["髌骨脱位", "髋关节发育不良", "眼部疾病", "过敏"],
                    "lifespan": "12-15年",
                    "health_screening": ["髋关节检查", "眼科检查", "膝盖检查"],
                    "preventive_care": "定期体检、控制体重、适量运动",
                    "special_attention": "独立性强，训练需要耐心"
                }
            },
            "corgi": {
                "breed_name_zh": "柯基犬",
                "breed_name_en": "Welsh Corgi",
                "diet": {
                    "daily_calories": "700-1000卡路里（成年犬）",
                    "feeding_frequency": "每天2次",
                    "food_type": "高质量狗粮，控制份量",
                    "special_needs": "容易肥胖，需控制饮食",
                    "avoid_foods": ["巧克力", "洋葱", "葡萄", "高脂肪食物"]
                },
                "exercise": {
                    "daily_duration": "40-60分钟",
                    "activity_level": "中等到高",
                    "recommended_activities": ["散步", "敏捷训练", "放牧游戏"],
                    "exercise_notes": "活泼好动，喜欢工作"
                },
                "temperament": {
                    "personality_traits": ["聪明", "友好", "活泼", "勇敢", "固执"],
                    "social_behavior": "友好外向，喜欢社交",
                    "trainability": "高，学习能力强",
                    "child_friendly": "适合，但可能追赶",
                    "stranger_tolerance": "友好但警惕"
                },
                "grooming": {
                    "brushing_frequency": "每周2-3次",
                    "bathing_frequency": "每月1次",
                    "shedding_level": "高，常年掉毛",
                    "grooming_needs": ["频繁刷毛", "修剪指甲", "清洁耳朵"],
                    "professional_grooming": "不需要频繁专业美容"
                },
                "health": {
                    "common_issues": ["椎间盘疾病", "髋关节发育不良", "眼部疾病", "肥胖"],
                    "lifespan": "12-15年",
                    "health_screening": ["脊椎检查", "髋关节检查", "眼科检查"],
                    "preventive_care": "控制体重、避免跳跃、定期体检",
                    "special_attention": "腿短身长，易患脊椎疾病，避免频繁上下楼梯"
                }
            }
        }
        
        if breed_id not in habits_database:
            return json.dumps({
                "success": False,
                "error": f"Breed ID '{breed_id}' not found in database",
                "error_type": "breed_not_found"
            }, ensure_ascii=False, indent=2)
        
        habits = habits_database[breed_id]
        
        return json.dumps({
            "success": True,
            "breed_id": breed_id,
            "habits": habits
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "habits_query_error"
        }, ensure_ascii=False, indent=2)


@tool
def validate_input(user_input: str) -> str:
    """
    验证用户输入的有效性
    
    Args:
        user_input: 用户输入的文本
        
    Returns:
        str: JSON格式的验证结果
    """
    try:
        # 基本验证
        if not user_input or not user_input.strip():
            return json.dumps({
                "valid": False,
                "error": "输入为空",
                "suggestion": "请提供小狗的特征描述，如体型、毛色、耳朵形状等。"
            }, ensure_ascii=False, indent=2)
        
        # 长度验证
        if len(user_input) > 2000:
            return json.dumps({
                "valid": False,
                "error": "输入过长",
                "suggestion": "请将描述控制在2000字符以内。"
            }, ensure_ascii=False, indent=2)
        
        if len(user_input) < 5:
            return json.dumps({
                "valid": False,
                "error": "输入过短",
                "suggestion": "请提供更详细的特征描述，至少包含5个字符。"
            }, ensure_ascii=False, indent=2)
        
        # 内容相关性检查（简单关键词检测）
        dog_related_keywords = [
            "狗", "犬", "小狗", "狗狗", "宠物", "dog", "puppy", "pet",
            "毛", "耳朵", "尾巴", "体型", "大小", "颜色", "性格",
            "fur", "ear", "tail", "size", "color", "temperament"
        ]
        
        input_lower = user_input.lower()
        has_related_keyword = any(keyword in input_lower for keyword in dog_related_keywords)
        
        if not has_related_keyword:
            return json.dumps({
                "valid": True,
                "warning": "输入可能与犬只特征描述无关",
                "suggestion": "建议提供小狗的外观特征，如体型、毛色、耳朵形状、尾巴特征等。"
            }, ensure_ascii=False, indent=2)
        
        return json.dumps({
            "valid": True,
            "message": "输入有效"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "valid": False,
            "error": str(e),
            "error_type": "validation_error"
        }, ensure_ascii=False, indent=2)


@tool
def format_response(match_results: str, habits_data: str) -> str:
    """
    格式化最终响应结果
    
    Args:
        match_results: JSON格式的匹配结果（由match_dog_breeds生成）
        habits_data: JSON格式的生活习惯数据（由get_breed_habits生成）
        
    Returns:
        str: JSON格式的完整响应结果
    """
    try:
        matches = json.loads(match_results)
        habits = json.loads(habits_data)
        
        if not matches.get("success"):
            return json.dumps({
                "success": False,
                "error": "匹配失败",
                "details": matches.get("error")
            }, ensure_ascii=False, indent=2)
        
        if not habits.get("success"):
            return json.dumps({
                "success": False,
                "error": "生活习惯查询失败",
                "details": habits.get("error")
            }, ensure_ascii=False, indent=2)
        
        top_matches = matches.get("top_matches", [])
        
        if not top_matches:
            return json.dumps({
                "success": False,
                "error": "无法识别犬种",
                "message": "根据您提供的特征，未能找到匹配的犬种。",
                "suggestion": "请补充更多特征信息，如：体型大小、毛色、耳朵形状、尾巴特征、大致体重等。"
            }, ensure_ascii=False, indent=2)
        
        # 构建响应
        response = {
            "success": True,
            "identification_result": {
                "match_quality": matches.get("match_quality"),
                "primary_breed": {
                    "breed_id": top_matches[0]["breed_id"],
                    "name_zh": top_matches[0]["name_zh"],
                    "name_en": top_matches[0]["name_en"],
                    "confidence": top_matches[0]["confidence"],
                    "match_details": top_matches[0]["match_details"],
                    "breed_info": top_matches[0]["breed_info"]
                },
                "alternative_breeds": []
            },
            "life_habits": habits.get("habits", {})
        }
        
        # 添加备选犬种
        if len(top_matches) > 1:
            for match in top_matches[1:]:
                response["identification_result"]["alternative_breeds"].append({
                    "breed_id": match["breed_id"],
                    "name_zh": match["name_zh"],
                    "name_en": match["name_en"],
                    "confidence": match["confidence"],
                    "match_details": match["match_details"]
                })
        
        # 添加建议
        if matches.get("match_quality") == "low":
            response["suggestion"] = "识别置信度较低，建议补充更多特征信息以提高准确度。"
        elif len(top_matches) > 1 and top_matches[0]["confidence"] - top_matches[1]["confidence"] < 20:
            response["suggestion"] = "存在多个相似的可能品种，建议补充更多特征信息以区分。"
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": "response_formatting_error"
        }, ensure_ascii=False, indent=2)
