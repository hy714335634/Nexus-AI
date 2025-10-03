#!/usr/bin/env python3
"""
智能健身顾问 (Fitness Advisor Agent)

一个专业的智能健身顾问，能够根据用户个人情况和健身目标，提供科学、个性化的健身建议，
包括锻炼计划、饮食指导和进度跟踪方法。

功能包括：
- 用户个人信息收集和分析
- 基于目标的健身计划生成
- 个性化饮食建议
- 运动强度和频率建议
- 健身进度跟踪指导
- 安全提醒和注意事项
- 健身知识科普
- 计划调整建议

使用工具：
- user_profile_analyzer - 分析用户个人信息和健身目标，生成用户健身画像
- workout_plan_generator - 基于用户画像生成个性化锻炼计划
- nutrition_plan_generator - 基于用户画像和健身目标生成饮食建议
- progress_tracker - 提供健身进度跟踪方法和指标
- fitness_knowledge_base - 提供健身知识和问题解答
- safety_checker - 检查生成的健身计划是否安全合理
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fitness_advisor_agent")

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用 agent_factory 创建 agent
fitness_advisor = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/fitness_advisor/fitness_advisor_agent", 
    **agent_params
)

def process_fitness_request(user_query: str) -> str:
    """
    处理用户的健身咨询请求
    
    Args:
        user_query: 用户的健身咨询内容
        
    Returns:
        str: Agent的回复内容
    """
    try:
        logger.info(f"处理健身咨询请求: {user_query[:50]}...")
        response = fitness_advisor(user_query)
        logger.info("健身咨询请求处理完成")
        return response
    except Exception as e:
        logger.error(f"处理健身咨询请求时出错: {str(e)}")
        return f"抱歉，处理您的请求时遇到了问题: {str(e)}。请稍后再试或重新描述您的需求。"

def analyze_user_profile(user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析用户信息并生成健身画像
    
    Args:
        user_info: 包含用户基本信息的字典
        
    Returns:
        Dict: 用户健身画像
    """
    try:
        # 构建分析请求
        analysis_request = (
            f"请分析以下用户信息并生成健身画像:\n"
            f"年龄: {user_info.get('age', '未提供')}\n"
            f"性别: {user_info.get('gender', '未提供')}\n"
            f"身高: {user_info.get('height', '未提供')}cm\n"
            f"体重: {user_info.get('weight', '未提供')}kg\n"
            f"活动水平: {user_info.get('activity_level', '未提供')}\n"
            f"健身经验: {user_info.get('experience', '未提供')}\n"
            f"健身目标: {user_info.get('goal', '未提供')}\n"
            f"健康状况: {user_info.get('health_condition', '未提供')}\n"
            f"时间限制: {user_info.get('time_constraint', '未提供')}\n"
            f"可用设备: {user_info.get('available_equipment', '未提供')}\n"
        )
        
        # 调用Agent进行分析
        response = fitness_advisor(analysis_request)
        
        # 提取并返回健身画像
        # 注意：这里假设返回的是结构化文本，实际应用中可能需要进一步处理
        return {"profile_analysis": response}
    except Exception as e:
        logger.error(f"分析用户健身画像时出错: {str(e)}")
        return {"error": str(e)}

def generate_workout_plan(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据用户画像生成个性化锻炼计划
    
    Args:
        user_profile: 用户健身画像
        
    Returns:
        Dict: 包含锻炼计划的字典
    """
    try:
        # 构建锻炼计划请求
        plan_request = (
            f"请根据以下用户健身画像生成一个个性化的锻炼计划:\n\n"
            f"{user_profile.get('profile_analysis', '')}\n\n"
            f"请包括以下内容:\n"
            f"1. 每周训练频率和时长\n"
            f"2. 具体的训练日安排\n"
            f"3. 每个训练日的具体动作、组数、次数\n"
            f"4. 热身和拉伸建议\n"
            f"5. 训练强度和进阶方案\n"
            f"6. 安全注意事项\n"
        )
        
        # 调用Agent生成锻炼计划
        response = fitness_advisor(plan_request)
        
        return {"workout_plan": response}
    except Exception as e:
        logger.error(f"生成锻炼计划时出错: {str(e)}")
        return {"error": str(e)}

def generate_nutrition_plan(user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据用户画像生成个性化饮食建议
    
    Args:
        user_profile: 用户健身画像
        
    Returns:
        Dict: 包含饮食建议的字典
    """
    try:
        # 构建饮食建议请求
        nutrition_request = (
            f"请根据以下用户健身画像生成一个个性化的饮食建议:\n\n"
            f"{user_profile.get('profile_analysis', '')}\n\n"
            f"请包括以下内容:\n"
            f"1. 每日卡路里需求\n"
            f"2. 宏量营养素比例(蛋白质、碳水化合物、脂肪)\n"
            f"3. 餐次安排和用餐时间\n"
            f"4. 食物选择建议和示例\n"
            f"5. 训练日和非训练日的饮食调整\n"
            f"6. 水分摄入建议\n"
            f"7. 注意事项和禁忌\n"
        )
        
        # 调用Agent生成饮食建议
        response = fitness_advisor(nutrition_request)
        
        return {"nutrition_plan": response}
    except Exception as e:
        logger.error(f"生成饮食建议时出错: {str(e)}")
        return {"error": str(e)}

def provide_progress_tracking(fitness_goal: str) -> Dict[str, Any]:
    """
    根据健身目标提供进度跟踪方法
    
    Args:
        fitness_goal: 用户的健身目标
        
    Returns:
        Dict: 包含进度跟踪方法的字典
    """
    try:
        # 构建进度跟踪请求
        tracking_request = (
            f"请针对以下健身目标，提供科学的进度跟踪方法和指标:\n\n"
            f"健身目标: {fitness_goal}\n\n"
            f"请包括以下内容:\n"
            f"1. 适合的跟踪指标\n"
            f"2. 测量频率建议\n"
            f"3. 记录方法\n"
            f"4. 进度评估标准\n"
            f"5. 调整计划的触发条件\n"
            f"6. 实用的跟踪工具或应用推荐\n"
        )
        
        # 调用Agent提供进度跟踪方法
        response = fitness_advisor(tracking_request)
        
        return {"progress_tracking": response}
    except Exception as e:
        logger.error(f"提供进度跟踪方法时出错: {str(e)}")
        return {"error": str(e)}

def provide_fitness_knowledge(question: str) -> str:
    """
    提供健身知识和问题解答
    
    Args:
        question: 用户的健身知识问题
        
    Returns:
        str: 健身知识解答
    """
    try:
        # 构建知识查询请求
        knowledge_request = (
            f"请回答以下健身相关问题，提供科学、准确的知识:\n\n"
            f"问题: {question}\n\n"
            f"请确保回答基于科学证据，并在适当时引用相关研究或权威观点。"
        )
        
        # 调用Agent提供健身知识
        response = fitness_advisor(knowledge_request)
        
        return response
    except Exception as e:
        logger.error(f"提供健身知识时出错: {str(e)}")
        return f"抱歉，解答您的问题时遇到了问题: {str(e)}。请稍后再试或重新描述您的问题。"

def check_plan_safety(plan: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    检查健身计划是否安全合理
    
    Args:
        plan: 健身计划内容
        user_info: 用户基本信息
        
    Returns:
        Dict: 安全检查结果
    """
    try:
        # 构建安全检查请求
        safety_request = (
            f"请检查以下健身计划是否安全合理，考虑用户的个人情况:\n\n"
            f"用户信息:\n"
            f"年龄: {user_info.get('age', '未提供')}\n"
            f"性别: {user_info.get('gender', '未提供')}\n"
            f"身高: {user_info.get('height', '未提供')}cm\n"
            f"体重: {user_info.get('weight', '未提供')}kg\n"
            f"健身经验: {user_info.get('experience', '未提供')}\n"
            f"健康状况: {user_info.get('health_condition', '未提供')}\n\n"
            f"健身计划:\n{plan}\n\n"
            f"请评估以下方面:\n"
            f"1. 运动强度是否适合用户水平\n"
            f"2. 是否有潜在的伤害风险\n"
            f"3. 动作选择是否合理\n"
            f"4. 训练量是否适当\n"
            f"5. 是否考虑了用户的健康状况\n"
            f"6. 改进建议\n"
        )
        
        # 调用Agent进行安全检查
        response = fitness_advisor(safety_request)
        
        return {"safety_assessment": response}
    except Exception as e:
        logger.error(f"检查健身计划安全性时出错: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='智能健身顾问Agent')
    parser.add_argument('-q', '--query', type=str, 
                       default="我是一个30岁的男性，身高175cm，体重80kg，想要减脂增肌，每周能锻炼3-4次，每次1小时左右，请给我一个合适的健身计划和饮食建议。",
                       help='健身咨询问题')
    parser.add_argument('-m', '--mode', type=str, 
                       default="general",
                       choices=["general", "workout", "nutrition", "tracking", "knowledge", "safety"],
                       help='咨询模式 (general, workout, nutrition, tracking, knowledge, safety)')
    args = parser.parse_args()
    
    print(f"✅ 智能健身顾问Agent创建成功: {fitness_advisor.name}")
    
    # 根据模式处理请求
    if args.mode == "general":
        print(f"🏋️ 处理一般健身咨询...")
        result = process_fitness_request(args.query)
    elif args.mode == "workout":
        print(f"🏋️ 生成锻炼计划...")
        # 简化示例，实际应用中应解析用户信息
        user_info = {
            "age": "30",
            "gender": "男",
            "height": "175",
            "weight": "80",
            "activity_level": "中等",
            "experience": "初学者",
            "goal": "减脂增肌",
            "time_constraint": "每周3-4次，每次1小时",
            "available_equipment": "健身房设备"
        }
        profile = analyze_user_profile(user_info)
        result = generate_workout_plan(profile)
    elif args.mode == "nutrition":
        print(f"🍎 生成饮食建议...")
        # 简化示例，实际应用中应解析用户信息
        user_info = {
            "age": "30",
            "gender": "男",
            "height": "175",
            "weight": "80",
            "activity_level": "中等",
            "experience": "初学者",
            "goal": "减脂增肌",
            "health_condition": "健康",
            "dietary_restrictions": "无"
        }
        profile = analyze_user_profile(user_info)
        result = generate_nutrition_plan(profile)
    elif args.mode == "tracking":
        print(f"📊 提供进度跟踪方法...")
        result = provide_progress_tracking(args.query)
    elif args.mode == "knowledge":
        print(f"📚 提供健身知识...")
        result = provide_fitness_knowledge(args.query)
    elif args.mode == "safety":
        print(f"🛡️ 检查计划安全性...")
        # 简化示例，实际应用中应解析用户信息和计划
        user_info = {
            "age": "30",
            "gender": "男",
            "height": "175",
            "weight": "80",
            "experience": "初学者",
            "health_condition": "健康"
        }
        result = check_plan_safety(args.query, user_info)
    
    # 输出结果
    if isinstance(result, dict):
        for key, value in result.items():
            print(f"\n--- {key} ---\n")
            print(value)
    else:
        print(f"\n📋 Agent响应:\n{result}")