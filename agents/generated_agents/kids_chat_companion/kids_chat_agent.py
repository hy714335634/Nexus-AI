#!/usr/bin/env python3
"""
儿童智能陪伴对话Agent

专业的儿童对话陪伴系统，提供年龄适配的对话交互、用户画像管理、
情感识别、内容安全过滤等功能。支持多轮对话，维护用户上下文。

功能特性：
- 年龄适配的对话交互
- 用户画像创建与管理
- 对话历史管理
- 情感识别与回应
- 内容安全过滤
- 话题推荐
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kids_chat_agent")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Agent参数配置
agent_params = {
    "env": "production",
    "version": "latest",
    "model_id": "default"
}

# 创建儿童对话Agent
kids_chat_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/kids_chat_companion/kids_chat_agent",
    **agent_params
)


def initialize_session(user_id: str, user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    初始化用户会话
    
    Args:
        user_id: 用户唯一标识
        user_info: 用户基本信息（昵称、年龄等）
        
    Returns:
        会话初始化结果
    """
    try:
        logger.info(f"初始化用户会话: user_id={user_id}")
        
        # 构建初始化请求
        if user_info:
            request = f"""
新用户初始化:
用户ID: {user_id}
用户信息: {json.dumps(user_info, ensure_ascii=False)}

请创建用户画像并开始友好的对话。
"""
        else:
            request = f"""
返回用户识别:
用户ID: {user_id}

请加载用户画像和对话历史，欢迎用户回来。
"""
        
        # 调用Agent处理
        response = kids_chat_agent(request)
        
        # 解析响应
        if hasattr(response, 'content') and response.content:
            result_text = response.content
        elif isinstance(response, str):
            result_text = response
        else:
            result_text = str(response)
        
        logger.info(f"会话初始化成功: user_id={user_id}")
        return {
            "status": "success",
            "user_id": user_id,
            "response": result_text
        }
        
    except Exception as e:
        logger.error(f"会话初始化失败: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "message": f"初始化失败: {str(e)}"
        }


def process_conversation(user_id: str, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    处理对话输入
    
    Args:
        user_id: 用户唯一标识
        user_input: 用户输入内容
        context: 对话上下文信息
        
    Returns:
        对话处理结果
    """
    try:
        logger.info(f"处理用户输入: user_id={user_id}")
        
        # 构建对话请求
        context_info = ""
        if context:
            context_info = f"\n上下文信息: {json.dumps(context, ensure_ascii=False)}"
        
        request = f"""
用户ID: {user_id}
用户输入: {user_input}{context_info}

请进行内容安全检查、情感识别，并生成个性化回复。
"""
        
        # 调用Agent处理
        response = kids_chat_agent(request)
        
        # 解析响应
        if hasattr(response, 'content') and response.content:
            result_text = response.content
        elif isinstance(response, str):
            result_text = response
        else:
            result_text = str(response)
        
        logger.info(f"对话处理成功: user_id={user_id}")
        return {
            "status": "success",
            "user_id": user_id,
            "response": result_text
        }
        
    except Exception as e:
        logger.error(f"对话处理失败: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "message": f"处理失败: {str(e)}",
            "fallback_response": "抱歉，我现在有点困惑。我们换个话题聊聊吧！"
        }


def end_session(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    结束对话会话
    
    Args:
        user_id: 用户唯一标识
        session_id: 会话ID（可选）
        
    Returns:
        会话结束结果
    """
    try:
        logger.info(f"结束用户会话: user_id={user_id}")
        
        # 构建结束请求
        request = f"""
结束会话:
用户ID: {user_id}
会话ID: {session_id or 'default'}

请生成会话总结，更新用户画像，并友好告别。
"""
        
        # 调用Agent处理
        response = kids_chat_agent(request)
        
        # 解析响应
        if hasattr(response, 'content') and response.content:
            result_text = response.content
        elif isinstance(response, str):
            result_text = response
        else:
            result_text = str(response)
        
        logger.info(f"会话结束成功: user_id={user_id}")
        return {
            "status": "success",
            "user_id": user_id,
            "response": result_text
        }
        
    except Exception as e:
        logger.error(f"会话结束失败: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "message": f"结束失败: {str(e)}"
        }


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    获取用户画像
    
    Args:
        user_id: 用户唯一标识
        
    Returns:
        用户画像信息
    """
    try:
        logger.info(f"获取用户画像: user_id={user_id}")
        
        # 构建查询请求
        request = f"""
查询用户画像:
用户ID: {user_id}

请返回用户的详细画像信息。
"""
        
        # 调用Agent处理
        response = kids_chat_agent(request)
        
        # 解析响应
        if hasattr(response, 'content') and response.content:
            result_text = response.content
        elif isinstance(response, str):
            result_text = response
        else:
            result_text = str(response)
        
        # 尝试解析JSON
        try:
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                profile_data = json.loads(json_str)
                return {
                    "status": "success",
                    "user_id": user_id,
                    "profile": profile_data
                }
        except json.JSONDecodeError:
            pass
        
        logger.info(f"用户画像获取成功: user_id={user_id}")
        return {
            "status": "success",
            "user_id": user_id,
            "profile_text": result_text
        }
        
    except Exception as e:
        logger.error(f"获取用户画像失败: {str(e)}")
        return {
            "status": "error",
            "user_id": user_id,
            "message": f"获取失败: {str(e)}"
        }


def interactive_chat(user_id: str = "test_user"):
    """
    交互式对话模式
    
    Args:
        user_id: 用户唯一标识
    """
    print(f"\n{'='*60}")
    print(f"🎈 儿童智能陪伴对话系统")
    print(f"{'='*60}")
    print(f"用户ID: {user_id}")
    print(f"输入 'exit' 或 'quit' 结束对话")
    print(f"输入 'profile' 查看用户画像")
    print(f"{'='*60}\n")
    
    # 初始化会话
    init_result = initialize_session(user_id)
    if init_result["status"] == "success":
        print(f"🤖 Agent: {init_result['response']}\n")
    else:
        print(f"❌ 初始化失败: {init_result.get('message', '未知错误')}\n")
        return
    
    # 对话循环
    conversation_count = 0
    while True:
        try:
            user_input = input("👦 你: ").strip()
            
            if not user_input:
                continue
            
            # 检查退出命令
            if user_input.lower() in ['exit', 'quit', '退出', '再见']:
                end_result = end_session(user_id)
                if end_result["status"] == "success":
                    print(f"\n🤖 Agent: {end_result['response']}\n")
                print("👋 对话结束，再见！\n")
                break
            
            # 检查查看画像命令
            if user_input.lower() in ['profile', '画像', '我的信息']:
                profile_result = get_user_profile(user_id)
                if profile_result["status"] == "success":
                    print(f"\n📋 用户画像:")
                    print(json.dumps(profile_result.get('profile', profile_result.get('profile_text', {})), 
                                   ensure_ascii=False, indent=2))
                    print()
                else:
                    print(f"❌ 获取画像失败: {profile_result.get('message', '未知错误')}\n")
                continue
            
            # 处理对话
            conversation_count += 1
            context = {"conversation_count": conversation_count}
            
            chat_result = process_conversation(user_id, user_input, context)
            if chat_result["status"] == "success":
                print(f"\n🤖 Agent: {chat_result['response']}\n")
            else:
                print(f"❌ 处理失败: {chat_result.get('message', '未知错误')}")
                if 'fallback_response' in chat_result:
                    print(f"🤖 Agent: {chat_result['fallback_response']}\n")
                else:
                    print()
            
        except KeyboardInterrupt:
            print("\n\n👋 对话被中断，再见！\n")
            break
        except Exception as e:
            logger.error(f"对话循环错误: {str(e)}")
            print(f"❌ 发生错误: {str(e)}\n")


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='儿童智能陪伴对话Agent')
    parser.add_argument('-u', '--user-id', type=str, 
                       default="test_user",
                       help='用户唯一标识')
    parser.add_argument('-i', '--input', type=str,
                       help='单次对话输入（非交互模式）')
    parser.add_argument('-m', '--mode', type=str,
                       choices=['chat', 'init', 'profile', 'end'],
                       default='chat',
                       help='运行模式: chat(交互对话), init(初始化), profile(查看画像), end(结束会话)')
    parser.add_argument('--name', type=str,
                       help='用户昵称（初始化时使用）')
    parser.add_argument('--age', type=int,
                       help='用户年龄（初始化时使用）')
    
    args = parser.parse_args()
    
    print(f"✅ Kids Chat Agent 创建成功: {kids_chat_agent.name}")
    
    # 根据模式执行不同操作
    if args.mode == 'init':
        # 初始化模式
        user_info = {}
        if args.name:
            user_info['name'] = args.name
        if args.age:
            user_info['age'] = args.age
        
        result = initialize_session(args.user_id, user_info if user_info else None)
        print(f"\n📋 初始化结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif args.mode == 'profile':
        # 查看画像模式
        result = get_user_profile(args.user_id)
        print(f"\n📋 用户画像:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif args.mode == 'end':
        # 结束会话模式
        result = end_session(args.user_id)
        print(f"\n📋 结束结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif args.input:
        # 单次对话模式
        result = process_conversation(args.user_id, args.input)
        print(f"\n📋 Agent响应:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    else:
        # 交互对话模式
        interactive_chat(args.user_id)
