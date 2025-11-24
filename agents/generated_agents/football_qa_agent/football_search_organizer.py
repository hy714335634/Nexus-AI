#!/usr/bin/env python3
"""
足球问答搜索整理Agent

专业的足球问答搜索整理专家，能够理解用户足球问题，执行网络搜索，
提取整理信息，并输出结构化答案。

功能特点：
- 支持多类型足球问题（球员、球队、比赛、战术、历史等）
- 使用ReAct模式进行思考-行动-观察循环
- 集成多个专业工具进行信息收集和分析
- 提供结构化、易读的答案输出
- 包含信息来源引用和可靠性评估

作者: Agent Build Workflow
版本: 1.0
日期: 2025-11-23
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
logger = logging.getLogger("football_search_organizer")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


def create_football_search_organizer_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default"
) -> Any:
    """
    创建足球问答搜索整理Agent
    
    Args:
        env (str): 运行环境 (development, production, testing)
        version (str): Agent版本
        model_id (str): 模型ID
        
    Returns:
        Agent实例
    """
    try:
        agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id,
            "enable_logging": True
        }
        
        agent_config_path = "generated_agents_prompts/football_qa_agent/football_search_organizer"
        
        agent = create_agent_from_prompt_template(
            agent_name=agent_config_path,
            **agent_params
        )
        
        logger.info(f"✅ Football Search Organizer Agent 创建成功: {agent.name}")
        logger.info(f"📋 环境: {env}, 版本: {version}, 模型: {model_id}")
        
        return agent
        
    except Exception as e:
        logger.error(f"❌ Agent创建失败: {str(e)}")
        raise


def process_football_question(
    agent: Any,
    question: str,
    question_type: Optional[str] = None,
    search_scope: Optional[str] = None,
    output_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理足球问题并返回结构化答案
    
    Args:
        agent: Agent实例
        question (str): 用户的足球问题
        question_type (str, optional): 问题类型提示
        search_scope (str, optional): 搜索范围限制
        output_format (str, optional): 输出格式要求
        
    Returns:
        Dict[str, Any]: 结构化的答案结果
    """
    try:
        # 构建输入
        user_input = question
        
        if question_type:
            user_input += f"\n\n问题类型: {question_type}"
        
        if search_scope:
            user_input += f"\n搜索范围: {search_scope}"
        
        if output_format:
            user_input += f"\n输出格式: {output_format}"
        
        logger.info(f"🎯 处理问题: {question}")
        logger.info(f"📝 完整输入: {user_input}")
        
        # 调用Agent处理
        response = agent(user_input)
        
        # 解析响应
        try:
            # 尝试提取响应内容
            if hasattr(response, 'content') and response.content:
                content = response.content
            elif isinstance(response, str):
                content = response
            elif hasattr(response, 'text'):
                content = response.text
            else:
                content = str(response)
            
            logger.info(f"📋 Agent响应长度: {len(content)} 字符")
            
            # 尝试解析JSON格式的答案
            try:
                # 查找JSON内容
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    parsed_result = json.loads(json_str)
                    
                    result = {
                        "status": "success",
                        "question": question,
                        "answer": parsed_result,
                        "raw_response": content,
                        "processing_info": {
                            "agent_name": agent.name,
                            "question_type": question_type,
                            "search_scope": search_scope
                        }
                    }
                else:
                    # 没有JSON格式，返回原始文本
                    result = {
                        "status": "success",
                        "question": question,
                        "answer": {
                            "text_response": content
                        },
                        "raw_response": content,
                        "processing_info": {
                            "agent_name": agent.name,
                            "question_type": question_type,
                            "search_scope": search_scope,
                            "note": "响应为文本格式"
                        }
                    }
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ JSON解析失败: {str(e)}")
                # JSON解析失败，返回文本响应
                result = {
                    "status": "success",
                    "question": question,
                    "answer": {
                        "text_response": content
                    },
                    "raw_response": content,
                    "processing_info": {
                        "agent_name": agent.name,
                        "question_type": question_type,
                        "search_scope": search_scope,
                        "note": "响应为文本格式"
                    }
                }
            
            logger.info("✅ 问题处理成功")
            return result
            
        except Exception as e:
            logger.error(f"❌ 响应解析失败: {str(e)}")
            return {
                "status": "error",
                "question": question,
                "error": f"响应解析失败: {str(e)}",
                "raw_response": str(response)
            }
        
    except Exception as e:
        logger.error(f"❌ 问题处理失败: {str(e)}")
        return {
            "status": "error",
            "question": question,
            "error": f"问题处理失败: {str(e)}"
        }


def validate_question(question: str) -> Dict[str, Any]:
    """
    验证问题的有效性
    
    Args:
        question (str): 用户问题
        
    Returns:
        Dict[str, Any]: 验证结果
    """
    if not question or not question.strip():
        return {
            "valid": False,
            "error": "问题不能为空"
        }
    
    if len(question) < 5:
        return {
            "valid": False,
            "error": "问题过短，请提供更详细的问题描述"
        }
    
    if len(question) > 500:
        return {
            "valid": False,
            "error": "问题过长，请简化问题描述"
        }
    
    return {
        "valid": True,
        "question_length": len(question)
    }


def format_answer_output(result: Dict[str, Any], format_type: str = "text") -> str:
    """
    格式化答案输出
    
    Args:
        result (Dict[str, Any]): 处理结果
        format_type (str): 输出格式 (text, json, markdown)
        
    Returns:
        str: 格式化的输出
    """
    if format_type == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif format_type == "markdown":
        output = f"# 足球问答结果\n\n"
        output += f"**问题**: {result.get('question', 'N/A')}\n\n"
        output += f"**状态**: {result.get('status', 'N/A')}\n\n"
        
        if result.get('status') == 'success':
            answer = result.get('answer', {})
            if isinstance(answer, dict):
                output += "## 答案\n\n"
                for key, value in answer.items():
                    output += f"### {key}\n\n{value}\n\n"
            else:
                output += f"## 答案\n\n{answer}\n\n"
        else:
            output += f"**错误**: {result.get('error', 'N/A')}\n\n"
        
        return output
    
    else:  # text
        output = "=" * 60 + "\n"
        output += "足球问答结果\n"
        output += "=" * 60 + "\n\n"
        output += f"问题: {result.get('question', 'N/A')}\n"
        output += f"状态: {result.get('status', 'N/A')}\n\n"
        
        if result.get('status') == 'success':
            output += "答案:\n"
            output += "-" * 60 + "\n"
            
            answer = result.get('answer', {})
            if isinstance(answer, dict):
                if 'text_response' in answer:
                    output += answer['text_response']
                else:
                    output += json.dumps(answer, ensure_ascii=False, indent=2)
            else:
                output += str(answer)
            
            output += "\n" + "-" * 60 + "\n"
        else:
            output += f"错误: {result.get('error', 'N/A')}\n"
        
        return output


# 创建默认Agent实例
football_search_organizer = create_football_search_organizer_agent()


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='足球问答搜索整理Agent测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本问题
  python football_search_organizer.py -i "梅西目前在哪个球队？"
  
  # 指定问题类型
  python football_search_organizer.py -i "梅西的职业生涯成就" -t player
  
  # 指定搜索范围
  python football_search_organizer.py -i "昨天巴萨vs皇马的比赛" -s matches
  
  # JSON输出格式
  python football_search_organizer.py -i "C罗转会历史" -f json
  
  # 指定运行环境
  python football_search_organizer.py -i "梅西数据" -e development
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="梅西目前在哪个球队？他的职业生涯成就是什么？",
        help='足球问题（默认: 梅西相关问题）'
    )
    
    parser.add_argument(
        '-t', '--type',
        type=str,
        choices=['player', 'team', 'match', 'tactics', 'history', 'general'],
        help='问题类型（可选）'
    )
    
    parser.add_argument(
        '-s', '--scope',
        type=str,
        choices=['general', 'news', 'statistics', 'matches', 'transfers', 'historical'],
        help='搜索范围（可选）'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['text', 'json', 'markdown'],
        default='text',
        help='输出格式（默认: text）'
    )
    
    parser.add_argument(
        '-e', '--env',
        type=str,
        choices=['development', 'production', 'testing'],
        default='production',
        help='运行环境（默认: production）'
    )
    
    parser.add_argument(
        '-v', '--version',
        type=str,
        default='latest',
        help='Agent版本（默认: latest）'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    print("\n" + "=" * 60)
    print("足球问答搜索整理Agent - 测试运行")
    print("=" * 60 + "\n")
    
    # 验证问题
    validation = validate_question(args.input)
    if not validation['valid']:
        print(f"❌ 问题验证失败: {validation['error']}")
        exit(1)
    
    print(f"✅ 问题验证通过")
    print(f"📝 问题: {args.input}")
    
    if args.type:
        print(f"🏷️  问题类型: {args.type}")
    
    if args.scope:
        print(f"🔍 搜索范围: {args.scope}")
    
    print(f"📄 输出格式: {args.format}")
    print(f"🌍 运行环境: {args.env}")
    print(f"📌 版本: {args.version}")
    print()
    
    try:
        # 创建Agent
        agent = create_football_search_organizer_agent(
            env=args.env,
            version=args.version
        )
        
        print("🚀 开始处理问题...\n")
        
        # 处理问题
        result = process_football_question(
            agent=agent,
            question=args.input,
            question_type=args.type,
            search_scope=args.scope
        )
        
        # 格式化输出
        output = format_answer_output(result, args.format)
        
        print(output)
        
        # 如果是详细模式，显示处理信息
        if args.verbose and result.get('processing_info'):
            print("\n" + "=" * 60)
            print("处理信息")
            print("=" * 60)
            print(json.dumps(result['processing_info'], ensure_ascii=False, indent=2))
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        print(f"\n❌ 测试失败: {str(e)}")
        exit(1)
