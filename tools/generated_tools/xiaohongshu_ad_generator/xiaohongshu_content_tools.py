"""
小红书广告文案生成工具集

本模块提供用于小红书广告文案生成的工具函数，包括：
- 产品信息验证
- emoji智能选择
- 话题标签推荐
- 内容质量评估

所有工具使用@tool装饰器定义，符合Strands框架规范
"""

from strands import tool
from typing import Dict, List, Any, Optional
import json
import re


@tool
def validate_product_info(product_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证产品信息的完整性和有效性
    
    检查必填字段、字段类型、内容长度等，确保输入符合要求
    
    Args:
        product_info: 产品信息字典，支持以下字段：
            - product_name (str, 必填): 产品名称
            - product_type (str, 可选): 产品类型
            - features (list, 可选): 产品特点列表
            - target_audience (str, 可选): 目标用户
            - price (str/float, 可选): 价格信息
            - style (str, 可选): 内容风格
            - additional_info (str, 可选): 其他信息
    
    Returns:
        Dict[str, Any]: 验证结果，包含：
            - valid (bool): 是否有效
            - errors (List[str]): 错误列表
            - warnings (List[str]): 警告列表
            - normalized_info (Dict): 标准化后的产品信息
    
    Examples:
        >>> result = validate_product_info({
        ...     "product_name": "维生素C精华液",
        ...     "product_type": "护肤品",
        ...     "features": ["美白", "抗氧化"]
        ... })
        >>> print(result["valid"])
        True
    """
    errors = []
    warnings = []
    normalized_info = {}
    
    # 检查必填字段
    if not product_info:
        return {
            "valid": False,
            "errors": ["产品信息不能为空"],
            "warnings": [],
            "normalized_info": {}
        }
    
    # 验证产品名称（必填）
    product_name = product_info.get("product_name", "").strip()
    if not product_name:
        errors.append("缺少必填字段：product_name（产品名称）")
    elif len(product_name) > 50:
        errors.append("产品名称过长（最多50字）")
    else:
        normalized_info["product_name"] = product_name
    
    # 验证产品类型（可选）
    product_type = product_info.get("product_type", "").strip()
    if product_type:
        if len(product_type) > 30:
            warnings.append("产品类型过长（建议30字以内）")
        normalized_info["product_type"] = product_type
    else:
        warnings.append("未提供产品类型，可能影响标签推荐准确性")
    
    # 验证产品特点（可选）
    features = product_info.get("features", [])
    if features:
        if not isinstance(features, list):
            errors.append("features字段必须是列表类型")
        elif len(features) > 10:
            warnings.append("产品特点过多（建议10个以内），可能影响文案聚焦度")
        else:
            # 过滤空字符串和过长的特点
            valid_features = []
            for feature in features:
                if isinstance(feature, str):
                    feature = feature.strip()
                    if feature:
                        if len(feature) > 30:
                            warnings.append(f"产品特点过长（建议30字以内）：{feature[:20]}...")
                        else:
                            valid_features.append(feature)
            normalized_info["features"] = valid_features
    else:
        warnings.append("未提供产品特点，可能影响文案说服力")
    
    # 验证目标用户（可选）
    target_audience = product_info.get("target_audience", "").strip()
    if target_audience:
        if len(target_audience) > 50:
            warnings.append("目标用户描述过长（建议50字以内）")
        normalized_info["target_audience"] = target_audience
    else:
        warnings.append("未提供目标用户，将使用默认受众定位")
    
    # 验证价格（可选）
    price = product_info.get("price")
    if price is not None:
        if isinstance(price, (int, float)):
            if price < 0:
                errors.append("价格不能为负数")
            else:
                normalized_info["price"] = str(price)
        elif isinstance(price, str):
            price = price.strip()
            if price:
                normalized_info["price"] = price
        else:
            errors.append("价格格式不正确（应为数字或字符串）")
    
    # 验证内容风格（可选）
    style = product_info.get("style", "").strip()
    valid_styles = ["测评", "种草", "教程", "分享", "对比"]
    if style:
        if style not in valid_styles:
            warnings.append(f"内容风格'{style}'不在推荐列表中（推荐：{', '.join(valid_styles)}），将使用默认风格")
        else:
            normalized_info["style"] = style
    
    # 验证其他信息（可选）
    additional_info = product_info.get("additional_info", "").strip()
    if additional_info:
        if len(additional_info) > 500:
            warnings.append("其他信息过长（建议500字以内），可能影响生成速度")
        normalized_info["additional_info"] = additional_info
    
    # 汇总验证结果
    is_valid = len(errors) == 0
    
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "normalized_info": normalized_info
    }


@tool
def select_emojis(
    context: str,
    category: str = "general",
    max_count: int = 3
) -> List[str]:
    """
    根据上下文智能选择合适的emoji表情
    
    基于内容主题、情感色彩和使用场景推荐emoji，增强文案的视觉吸引力和情感表达
    
    Args:
        context: 上下文内容（产品名称、特点、场景等）
        category: emoji类别，可选值：
            - "general": 通用表情
            - "beauty": 美妆护肤
            - "food": 美食饮品
            - "fashion": 服饰配饰
            - "travel": 旅行出行
            - "tech": 数码科技
            - "lifestyle": 生活方式
        max_count: 最多返回的emoji数量（1-5）
    
    Returns:
        List[str]: 推荐的emoji列表
    
    Examples:
        >>> emojis = select_emojis("维生素C精华液 美白", "beauty", 3)
        >>> print(emojis)
        ['✨', '💫', '🌟']
    """
    # 限制max_count范围
    max_count = max(1, min(max_count, 5))
    
    # emoji分类库
    emoji_library = {
        "beauty": {
            "skincare": ["✨", "💫", "🌟", "💎", "🌸", "🌺", "💐", "🌹", "🦋", "🧚"],
            "makeup": ["💄", "💅", "👄", "💋", "🎀", "🌈", "✨", "💖", "🦢", "👑"],
            "positive": ["😍", "🥰", "😘", "💕", "💗", "💓", "💝", "❤️", "🤩", "😊"],
            "effect": ["✨", "💫", "⭐", "🌟", "💎", "🔆", "☀️", "🌞", "💥", "🎉"]
        },
        "food": {
            "delicious": ["😋", "🤤", "😍", "🥰", "👍", "💯", "🔥", "❤️", "💕", "✨"],
            "fruit": ["🍓", "🍊", "🍋", "🍌", "🍉", "🍇", "🍑", "🍒", "🥭", "🍍"],
            "drink": ["☕", "🍵", "🧋", "🥤", "🍹", "🧃", "🥛", "🍶", "🧉", "🫖"],
            "dessert": ["🍰", "🎂", "🧁", "🍪", "🍩", "🍮", "🍨", "🍦", "🍡", "🥮"]
        },
        "fashion": {
            "clothing": ["👗", "👚", "👕", "🧥", "👔", "👘", "🥻", "👖", "👙", "🩱"],
            "accessories": ["👜", "👝", "🎒", "👛", "💼", "🕶️", "👒", "🧢", "👑", "💍"],
            "shoes": ["👠", "👡", "👢", "👞", "👟", "🥿", "🩰", "🥾", "👢", "👡"],
            "style": ["✨", "💫", "🌟", "💎", "🎀", "🌸", "💖", "👑", "🦋", "🌈"]
        },
        "travel": {
            "destination": ["🏝️", "🏖️", "🗾", "🏔️", "🗻", "🏕️", "🏞️", "🌅", "🌄", "🌠"],
            "transport": ["✈️", "🚄", "🚗", "🚙", "🚕", "🚌", "🚎", "🏎️", "🛫", "🛬"],
            "activity": ["📸", "🎒", "🗺️", "🧳", "🎫", "🎟️", "🎭", "🎨", "🎪", "🎡"],
            "emotion": ["😍", "🥰", "😘", "💕", "✨", "🌟", "💫", "🎉", "🎊", "🥳"]
        },
        "tech": {
            "devices": ["📱", "💻", "⌚", "🎧", "🎮", "📷", "📹", "🖥️", "⌨️", "🖱️"],
            "features": ["⚡", "🔋", "💡", "🔌", "📡", "🛰️", "💾", "💿", "📀", "🔊"],
            "quality": ["✨", "💫", "🌟", "💎", "👍", "💯", "🔥", "❤️", "😍", "🤩"],
            "innovation": ["🚀", "🎯", "💡", "⚡", "🔥", "💥", "🌈", "🎨", "🧩", "🔮"]
        },
        "lifestyle": {
            "home": ["🏠", "🛋️", "🛏️", "🪴", "🕯️", "💐", "🌸", "🌺", "🌻", "🌷"],
            "wellness": ["🧘", "💆", "💅", "🛀", "🧖", "💤", "😴", "🌙", "⭐", "✨"],
            "hobby": ["📚", "🎨", "🎭", "🎪", "🎸", "🎹", "🎼", "🎵", "🎶", "🎤"],
            "positive": ["😊", "😌", "🥰", "💕", "💗", "❤️", "✨", "🌟", "💫", "🌈"]
        },
        "general": {
            "positive": ["😊", "😍", "🥰", "😘", "💕", "❤️", "✨", "🌟", "💫", "👍"],
            "excited": ["🎉", "🎊", "🥳", "🤩", "😍", "💖", "🔥", "💥", "⚡", "🚀"],
            "quality": ["💯", "👍", "💎", "🌟", "✨", "💫", "⭐", "🔥", "❤️", "💖"],
            "attention": ["⚠️", "📢", "🔔", "💡", "🎯", "👀", "💥", "🔥", "✨", "⚡"]
        }
    }
    
    # 获取指定类别的emoji库
    category_emojis = emoji_library.get(category, emoji_library["general"])
    
    # 根据上下文关键词匹配子类别
    context_lower = context.lower()
    selected_emojis = []
    
    # 关键词匹配规则
    keyword_rules = {
        "beauty": {
            "护肤|精华|面膜|乳液|水|霜": "skincare",
            "口红|眼影|腮红|粉底|睫毛膏": "makeup",
            "美白|亮肤|提亮|光泽|透亮": "effect"
        },
        "food": {
            "水果|果汁|鲜果": "fruit",
            "咖啡|奶茶|茶|饮料": "drink",
            "蛋糕|甜品|点心|零食": "dessert"
        },
        "fashion": {
            "衣服|裙子|上衣|外套|裤子": "clothing",
            "包|帽子|围巾|配饰|首饰": "accessories",
            "鞋|靴|凉鞋|运动鞋": "shoes"
        },
        "travel": {
            "海边|山|景点|风景": "destination",
            "飞机|火车|自驾|交通": "transport",
            "拍照|打卡|游玩|体验": "activity"
        },
        "tech": {
            "手机|电脑|平板|耳机|相机": "devices",
            "快充|续航|性能|配置": "features",
            "创新|科技|智能|未来": "innovation"
        },
        "lifestyle": {
            "家居|装饰|摆件": "home",
            "放松|休息|睡眠|护理": "wellness",
            "阅读|画画|音乐|兴趣": "hobby"
        }
    }
    
    # 匹配子类别
    matched_subcategories = []
    if category in keyword_rules:
        for pattern, subcategory in keyword_rules[category].items():
            if re.search(pattern, context):
                matched_subcategories.append(subcategory)
    
    # 如果没有匹配到子类别，使用positive作为默认
    if not matched_subcategories:
        matched_subcategories = ["positive"]
    
    # 从匹配的子类别中选择emoji
    for subcategory in matched_subcategories:
        if subcategory in category_emojis:
            subcategory_emojis = category_emojis[subcategory]
            # 避免重复
            for emoji in subcategory_emojis:
                if emoji not in selected_emojis:
                    selected_emojis.append(emoji)
                    if len(selected_emojis) >= max_count:
                        break
        if len(selected_emojis) >= max_count:
            break
    
    # 如果还不够，从其他子类别补充
    if len(selected_emojis) < max_count:
        for subcategory, emojis in category_emojis.items():
            for emoji in emojis:
                if emoji not in selected_emojis:
                    selected_emojis.append(emoji)
                    if len(selected_emojis) >= max_count:
                        break
            if len(selected_emojis) >= max_count:
                break
    
    return selected_emojis[:max_count]


@tool
def recommend_hashtags(
    product_info: Dict[str, Any],
    max_count: int = 6
) -> List[str]:
    """
    根据产品信息推荐相关的小红书话题标签
    
    综合考虑产品类型、特点、目标用户等维度，推荐热度高、相关性强的话题标签
    
    Args:
        product_info: 产品信息字典，包含：
            - product_name (str): 产品名称
            - product_type (str): 产品类型
            - features (list): 产品特点
            - target_audience (str): 目标用户
            - style (str): 内容风格
        max_count: 最多返回的标签数量（3-8）
    
    Returns:
        List[str]: 推荐的话题标签列表（带#前缀）
    
    Examples:
        >>> tags = recommend_hashtags({
        ...     "product_name": "维生素C精华液",
        ...     "product_type": "护肤品",
        ...     "features": ["美白", "抗氧化"],
        ...     "target_audience": "25-35岁女性"
        ... }, max_count=6)
        >>> print(tags)
        ['#护肤', '#美白', '#精华液', '#抗氧化', '#护肤品推荐', '#美妆']
    """
    # 限制max_count范围
    max_count = max(3, min(max_count, 8))
    
    # 话题标签库
    hashtag_library = {
        "product_type": {
            "护肤品": ["#护肤", "#护肤品推荐", "#美妆", "#skincare", "#护肤日常"],
            "彩妆": ["#彩妆", "#美妆", "#化妆", "#makeup", "#彩妆分享"],
            "服饰": ["#穿搭", "#服饰", "#时尚", "#fashion", "#穿搭分享"],
            "鞋子": ["#鞋子", "#穿搭", "#时尚", "#鞋履", "#鞋子推荐"],
            "包包": ["#包包", "#配饰", "#时尚", "#包包推荐", "#包包分享"],
            "美食": ["#美食", "#美食分享", "#美食推荐", "#foodie", "#吃货"],
            "饮品": ["#饮品", "#美食", "#饮品推荐", "#喝什么", "#饮品分享"],
            "数码": ["#数码", "#科技", "#数码产品", "#tech", "#数码测评"],
            "家居": ["#家居", "#家居好物", "#生活", "#家居分享", "#家居装饰"],
            "图书": ["#读书", "#阅读", "#书籍推荐", "#读书分享", "#好书推荐"]
        },
        "features": {
            "美白": ["#美白", "#美白产品", "#美白精华", "#白皙肌肤"],
            "保湿": ["#保湿", "#补水", "#保湿护肤", "#水润肌肤"],
            "抗氧化": ["#抗氧化", "#抗老", "#抗衰老", "#年轻肌肤"],
            "防晒": ["#防晒", "#防晒霜", "#防晒产品", "#夏日防晒"],
            "修复": ["#修复", "#肌肤修复", "#舒缓", "#敏感肌"],
            "舒适": ["#舒适", "#舒适穿搭", "#舒服", "#comfort"],
            "时尚": ["#时尚", "#潮流", "#时尚穿搭", "#fashion"],
            "百搭": ["#百搭", "#百搭单品", "#实用", "#日常穿搭"],
            "健康": ["#健康", "#健康生活", "#养生", "#健康饮食"],
            "美味": ["#美味", "#好吃", "#美食", "#delicious"]
        },
        "target_audience": {
            "女性": ["#女生", "#女生必备", "#女性", "#女生好物"],
            "男性": ["#男生", "#男士", "#男性", "#男生好物"],
            "学生": ["#学生党", "#学生", "#学生必备", "#校园"],
            "上班族": ["#上班族", "#职场", "#打工人", "#通勤"],
            "宝妈": ["#宝妈", "#妈妈", "#母婴", "#育儿"],
            "年轻人": ["#年轻人", "#青春", "#Z世代", "#95后"]
        },
        "style": {
            "测评": ["#测评", "#产品测评", "#真实测评", "#使用感受"],
            "种草": ["#种草", "#好物推荐", "#好物分享", "#种草清单"],
            "教程": ["#教程", "#攻略", "#新手教程", "#使用方法"],
            "分享": ["#分享", "#日常分享", "#生活分享", "#真实分享"],
            "对比": ["#对比", "#产品对比", "#选购指南", "#怎么选"]
        },
        "general": [
            "#好物推荐", "#种草", "#分享", "#日常", "#生活",
            "#推荐", "#必买", "#值得", "#实用", "#好用",
            "#小红书", "#笔记", "#干货", "#真实", "#亲测"
        ]
    }
    
    recommended_tags = []
    
    # 1. 从产品类型提取标签
    product_type = product_info.get("product_type", "")
    if product_type:
        for key, tags in hashtag_library["product_type"].items():
            if key in product_type:
                for tag in tags[:2]:  # 每个类别最多取2个
                    if tag not in recommended_tags:
                        recommended_tags.append(tag)
    
    # 2. 从产品特点提取标签
    features = product_info.get("features", [])
    if features:
        for feature in features[:3]:  # 最多处理3个特点
            for key, tags in hashtag_library["features"].items():
                if key in str(feature):
                    for tag in tags[:2]:
                        if tag not in recommended_tags:
                            recommended_tags.append(tag)
    
    # 3. 从目标用户提取标签
    target_audience = product_info.get("target_audience", "")
    if target_audience:
        for key, tags in hashtag_library["target_audience"].items():
            if key in target_audience:
                for tag in tags[:1]:  # 每个用户群体取1个
                    if tag not in recommended_tags:
                        recommended_tags.append(tag)
    
    # 4. 从内容风格提取标签
    style = product_info.get("style", "")
    if style:
        for key, tags in hashtag_library["style"].items():
            if key in style:
                for tag in tags[:1]:
                    if tag not in recommended_tags:
                        recommended_tags.append(tag)
    
    # 5. 补充通用标签
    if len(recommended_tags) < max_count:
        for tag in hashtag_library["general"]:
            if tag not in recommended_tags:
                recommended_tags.append(tag)
                if len(recommended_tags) >= max_count:
                    break
    
    return recommended_tags[:max_count]


@tool
def evaluate_content_quality(
    title: str,
    content: str,
    tags: List[str],
    cta: str
) -> Dict[str, Any]:
    """
    评估生成内容的质量
    
    从多个维度评估广告文案的质量，包括长度、结构、emoji使用、标签相关性等
    
    Args:
        title: 标题文本
        content: 正文内容
        tags: 话题标签列表
        cta: 行动号召文案
    
    Returns:
        Dict[str, Any]: 质量评估结果，包含：
            - overall_score (float): 综合评分（0-100）
            - dimension_scores (Dict): 各维度评分
            - issues (List[str]): 发现的问题
            - suggestions (List[str]): 改进建议
            - passed (bool): 是否通过质量检查
    
    Examples:
        >>> result = evaluate_content_quality(
        ...     title="✨维C精华真的绝了！美白效果太惊艳💫",
        ...     content="姐妹们！今天必须跟你们分享这款...",
        ...     tags=["#护肤", "#美白", "#精华液"],
        ...     cta="评论区告诉我你的美白秘诀！"
        ... )
        >>> print(result["overall_score"])
        85.5
    """
    dimension_scores = {}
    issues = []
    suggestions = []
    
    # 1. 标题质量评估（满分20分）
    title_score = 0
    title_length = len(title)
    
    if 15 <= title_length <= 30:
        title_score += 10
    elif title_length < 15:
        issues.append("标题过短（少于15字）")
        suggestions.append("建议增加标题长度，突出更多卖点")
        title_score += 5
    else:
        issues.append("标题过长（超过30字）")
        suggestions.append("建议精简标题，保持简洁有力")
        title_score += 7
    
    # 检查emoji数量
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    title_emojis = emoji_pattern.findall(title)
    emoji_count = len(title_emojis)
    
    if 1 <= emoji_count <= 3:
        title_score += 10
    elif emoji_count == 0:
        issues.append("标题缺少emoji表情")
        suggestions.append("建议添加1-3个相关emoji，增强吸引力")
        title_score += 5
    else:
        issues.append("标题emoji过多（超过3个）")
        suggestions.append("建议减少emoji数量，避免视觉混乱")
        title_score += 7
    
    dimension_scores["title"] = title_score
    
    # 2. 正文质量评估（满分30分）
    content_score = 0
    content_length = len(content)
    
    if 200 <= content_length <= 800:
        content_score += 15
    elif content_length < 200:
        issues.append("正文过短（少于200字）")
        suggestions.append("建议增加内容，提供更多细节和使用体验")
        content_score += 8
    else:
        issues.append("正文过长（超过800字）")
        suggestions.append("建议精简内容，保持用户阅读兴趣")
        content_score += 12
    
    # 检查正文结构
    structure_keywords = ["使用", "效果", "推荐", "体验", "感受"]
    structure_count = sum(1 for keyword in structure_keywords if keyword in content)
    
    if structure_count >= 3:
        content_score += 10
    elif structure_count >= 2:
        content_score += 7
        suggestions.append("建议增加使用体验和效果描述")
    else:
        content_score += 4
        issues.append("正文结构不够完整")
        suggestions.append("建议按照：开场-介绍-体验-推荐的结构组织内容")
    
    # 检查正文emoji使用
    content_emojis = emoji_pattern.findall(content)
    content_emoji_count = len(content_emojis)
    
    if 3 <= content_emoji_count <= 10:
        content_score += 5
    elif content_emoji_count < 3:
        suggestions.append("建议在正文中适当增加emoji表情")
        content_score += 3
    else:
        suggestions.append("正文emoji可能过多，注意适度使用")
        content_score += 4
    
    dimension_scores["content"] = content_score
    
    # 3. 标签质量评估（满分25分）
    tags_score = 0
    tags_count = len(tags)
    
    if 3 <= tags_count <= 8:
        tags_score += 15
    elif tags_count < 3:
        issues.append("标签数量过少（少于3个）")
        suggestions.append("建议增加标签数量，提高内容曝光")
        tags_score += 8
    else:
        issues.append("标签数量过多（超过8个）")
        suggestions.append("建议精简标签，保持相关性")
        tags_score += 12
    
    # 检查标签格式
    invalid_tags = [tag for tag in tags if not tag.startswith("#")]
    if invalid_tags:
        issues.append(f"部分标签缺少#前缀：{', '.join(invalid_tags)}")
        suggestions.append("确保所有标签都以#开头")
        tags_score += 5
    else:
        tags_score += 10
    
    dimension_scores["tags"] = tags_score
    
    # 4. CTA质量评估（满分15分）
    cta_score = 0
    cta_length = len(cta)
    
    if 10 <= cta_length <= 50:
        cta_score += 10
    elif cta_length < 10:
        issues.append("CTA过短")
        suggestions.append("建议增加互动引导内容")
        cta_score += 5
    else:
        suggestions.append("CTA可以更简洁")
        cta_score += 8
    
    # 检查CTA关键词
    cta_keywords = ["评论", "告诉我", "分享", "收藏", "点赞", "关注", "双击"]
    has_cta_keyword = any(keyword in cta for keyword in cta_keywords)
    
    if has_cta_keyword:
        cta_score += 5
    else:
        issues.append("CTA缺少明确的行动号召")
        suggestions.append("建议使用'评论''收藏''分享'等引导词")
        cta_score += 2
    
    dimension_scores["cta"] = cta_score
    
    # 5. 整体协调性评估（满分10分）
    coherence_score = 10
    
    # 检查标题和正文的一致性
    title_keywords = set(re.findall(r'[\u4e00-\u9fa5]+', title))
    content_keywords = set(re.findall(r'[\u4e00-\u9fa5]+', content))
    common_keywords = title_keywords & content_keywords
    
    if len(common_keywords) < 2:
        issues.append("标题和正文关联度较低")
        suggestions.append("建议在正文中呼应标题的关键词")
        coherence_score -= 3
    
    dimension_scores["coherence"] = coherence_score
    
    # 计算综合评分
    overall_score = sum(dimension_scores.values())
    
    # 判断是否通过质量检查
    passed = overall_score >= 70 and len(issues) <= 3
    
    return {
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "issues": issues,
        "suggestions": suggestions,
        "passed": passed,
        "quality_level": (
            "优秀" if overall_score >= 85 else
            "良好" if overall_score >= 70 else
            "及格" if overall_score >= 60 else
            "待改进"
        )
    }


@tool
def format_output_json(
    title: str,
    content: str,
    tags: List[str],
    cta: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    将生成的内容格式化为标准JSON输出
    
    组装所有内容元素为结构化的JSON字符串，便于用户使用和系统集成
    
    Args:
        title: 标题文本
        content: 正文内容
        tags: 话题标签列表
        cta: 行动号召文案
        metadata: 元数据（可选），包含生成时间、风格、字数等信息
    
    Returns:
        str: 格式化的JSON字符串
    
    Examples:
        >>> json_output = format_output_json(
        ...     title="✨维C精华真的绝了！",
        ...     content="姐妹们！今天必须跟你们分享...",
        ...     tags=["#护肤", "#美白"],
        ...     cta="评论区告诉我你的美白秘诀！",
        ...     metadata={"style": "种草", "word_count": 350}
        ... )
        >>> print(json_output)
        {"title": "✨维C精华真的绝了！", ...}
    """
    # 构建输出字典
    output = {
        "title": title,
        "content": content,
        "tags": tags,
        "cta": cta
    }
    
    # 添加元数据
    if metadata:
        output["metadata"] = metadata
    else:
        output["metadata"] = {
            "title_length": len(title),
            "content_length": len(content),
            "tags_count": len(tags)
        }
    
    # 转换为JSON字符串
    try:
        json_output = json.dumps(output, ensure_ascii=False, indent=2)
        return json_output
    except Exception as e:
        # 如果JSON序列化失败，返回错误信息
        error_output = {
            "error": "JSON格式化失败",
            "message": str(e),
            "raw_data": {
                "title": str(title),
                "content": str(content),
                "tags": [str(tag) for tag in tags],
                "cta": str(cta)
            }
        }
        return json.dumps(error_output, ensure_ascii=False, indent=2)
