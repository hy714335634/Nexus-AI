#!/usr/bin/env python3
"""
健身顾问智能体 - 提供个性化健身建议、锻炼计划、饮食指导和健身相关问题解答

该智能体整合了多种健身计算工具、用户资料管理工具和健身时间管理工具，
能够根据用户的个人情况、健身目标和偏好，提供科学、安全、个性化的健身建议。
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 设置遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建Agent的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 创建健身顾问智能体
fitness_advisor_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/fitness_advisor/fitness_advisor_agent", 
    **agent_params
)

def generate_user_id(name: str, email: Optional[str] = None) -> str:
    """
    根据用户名和可选的邮箱生成唯一用户ID
    
    Args:
        name: 用户名
        email: 用户邮箱(可选)
        
    Returns:
        str: 生成的用户ID
    """
    import hashlib
    
    # 如果提供了邮箱，使用邮箱作为主要标识符
    if email:
        identifier = email.lower()
    else:
        # 否则使用名字和当前时间戳
        identifier = f"{name.lower()}_{datetime.now().timestamp()}"
    
    # 创建哈希
    hash_obj = hashlib.md5(identifier.encode())
    user_id = hash_obj.hexdigest()[:12]  # 取前12位作为ID
    
    return user_id

def parse_bmi_result(bmi_json: str) -> Dict[str, Any]:
    """
    解析BMI计算结果JSON字符串
    
    Args:
        bmi_json: BMI计算工具返回的JSON字符串
        
    Returns:
        Dict[str, Any]: 解析后的BMI数据
    """
    try:
        bmi_data = json.loads(bmi_json)
        return bmi_data
    except json.JSONDecodeError:
        return {"status": "error", "message": "无法解析BMI数据"}

def parse_bmr_result(bmr_json: str) -> Dict[str, Any]:
    """
    解析BMR计算结果JSON字符串
    
    Args:
        bmr_json: BMR计算工具返回的JSON字符串
        
    Returns:
        Dict[str, Any]: 解析后的BMR数据
    """
    try:
        bmr_data = json.loads(bmr_json)
        return bmr_data
    except json.JSONDecodeError:
        return {"status": "error", "message": "无法解析BMR数据"}

def parse_tdee_result(tdee_json: str) -> Dict[str, Any]:
    """
    解析TDEE计算结果JSON字符串
    
    Args:
        tdee_json: TDEE计算工具返回的JSON字符串
        
    Returns:
        Dict[str, Any]: 解析后的TDEE数据
    """
    try:
        tdee_data = json.loads(tdee_json)
        return tdee_data
    except json.JSONDecodeError:
        return {"status": "error", "message": "无法解析TDEE数据"}

def create_workout_plan_for_user(
    user_id: str,
    goal: str,
    experience_level: str,
    available_days: List[str],
    available_equipment: List[str],
    health_conditions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    为用户创建健身计划
    
    Args:
        user_id: 用户ID
        goal: 健身目标(减脂、增肌、提高耐力等)
        experience_level: 经验水平(初学者、中级、高级)
        available_days: 可用于锻炼的日期列表
        available_equipment: 可用设备列表
        health_conditions: 健康状况列表(可选)
        
    Returns:
        Dict[str, Any]: 创建的健身计划
    """
    # 构建健身计划请求
    workout_request = (
        f"请为用户创建一个健身计划，具有以下特点:\n"
        f"- 健身目标: {goal}\n"
        f"- 经验水平: {experience_level}\n"
        f"- 每周可锻炼天数: {', '.join(available_days)}\n"
        f"- 可用设备: {', '.join(available_equipment)}\n"
    )
    
    if health_conditions:
        workout_request += f"- 健康状况/限制: {', '.join(health_conditions)}\n"
    
    workout_request += (
        "请提供详细的健身计划，包括每天的锻炼内容、每个动作的组数和次数，"
        "以及适当的休息时间建议。"
    )
    
    # 使用智能体生成健身计划
    response = fitness_advisor_agent(workout_request)
    
    # 返回健身计划
    return {
        "user_id": user_id,
        "goal": goal,
        "experience_level": experience_level,
        "available_days": available_days,
        "plan": response,
        "created_at": datetime.now().isoformat()
    }

def create_diet_plan_for_user(
    user_id: str,
    goal: str,
    tdee: int,
    dietary_preferences: List[str],
    allergies: Optional[List[str]] = None,
    meal_count: int = 3
) -> Dict[str, Any]:
    """
    为用户创建饮食计划
    
    Args:
        user_id: 用户ID
        goal: 健身目标(减脂、增肌、维持)
        tdee: 每日总能量消耗(卡路里)
        dietary_preferences: 饮食偏好列表
        allergies: 过敏源列表(可选)
        meal_count: 每日餐数(默认为3)
        
    Returns:
        Dict[str, Any]: 创建的饮食计划
    """
    # 构建饮食计划请求
    diet_request = (
        f"请为用户创建一个饮食计划，具有以下特点:\n"
        f"- 健身目标: {goal}\n"
        f"- 每日总能量需求: {tdee}卡路里\n"
        f"- 饮食偏好: {', '.join(dietary_preferences)}\n"
        f"- 每日餐数: {meal_count}\n"
    )
    
    if allergies:
        diet_request += f"- 食物过敏源: {', '.join(allergies)}\n"
    
    diet_request += (
        "请提供详细的饮食计划，包括每餐的食物选择、大致份量，"
        "以及宏量营养素(蛋白质、碳水化合物、脂肪)的分配建议。"
    )
    
    # 使用智能体生成饮食计划
    response = fitness_advisor_agent(diet_request)
    
    # 返回饮食计划
    return {
        "user_id": user_id,
        "goal": goal,
        "tdee": tdee,
        "meal_count": meal_count,
        "dietary_preferences": dietary_preferences,
        "plan": response,
        "created_at": datetime.now().isoformat()
    }

def answer_fitness_question(question: str) -> str:
    """
    回答用户关于健身的问题
    
    Args:
        question: 用户的健身相关问题
        
    Returns:
        str: 问题的回答
    """
    # 构建问题请求
    question_request = f"健身问题: {question}\n请提供专业、准确的回答。"
    
    # 使用智能体回答问题
    response = fitness_advisor_agent(question_request)
    
    return response

def main():
    """主函数，用于命令行测试"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='健身顾问智能体测试')
    parser.add_argument('-m', '--mode', type=str, 
                       choices=['workout', 'diet', 'question'],
                       default="question",
                       help='运行模式: workout(健身计划), diet(饮食计划), question(回答问题)')
    parser.add_argument('-q', '--question', type=str, 
                       default="如何正确做俯卧撑?",
                       help='健身相关问题')
    args = parser.parse_args()
    
    print(f"✅ 健身顾问智能体创建成功: {fitness_advisor_agent.name}")
    
    # 根据模式执行不同功能
    if args.mode == 'workout':
        # 测试创建健身计划
        plan = create_workout_plan_for_user(
            user_id="test_user",
            goal="增肌",
            experience_level="中级",
            available_days=["周一", "周三", "周五"],
            available_equipment=["哑铃", "杠铃", "引体向上器械"]
        )
        print("\n📋 生成的健身计划:")
        print(plan["plan"])
        
    elif args.mode == 'diet':
        # 测试创建饮食计划
        plan = create_diet_plan_for_user(
            user_id="test_user",
            goal="减脂",
            tdee=2200,
            dietary_preferences=["高蛋白", "低碳水"],
            meal_count=4
        )
        print("\n📋 生成的饮食计划:")
        print(plan["plan"])
        
    else:  # question模式
        # 测试回答健身问题
        question = args.question
        print(f"\n❓ 问题: {question}")
        answer = answer_fitness_question(question)
        print(f"\n📋 回答:\n{answer}")

if __name__ == "__main__":
    main()