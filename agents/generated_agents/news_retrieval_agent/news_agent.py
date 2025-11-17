#!/usr/bin/env python3
"""
新闻检索Agent

专业的新闻检索与聚合专家，根据用户关注话题从多个主流媒体平台检索热门新闻，
进行热度排序和摘要生成，为用户提供最新、最热门的新闻信息。

支持功能：
- 关注话题管理（添加、查看、删除话题）
- 多平台新闻检索（百度、新浪、澎湃等）
- 新闻热度计算与排序
- 新闻内容摘要生成
- 用户友好的交互界面
"""

import os
import json
from typing import List, Dict, Any, Optional
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default",
    "enable_logging": True
}

# 使用 agent_factory 创建 agent
news_agent = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/news_retrieval_agent/news_agent_prompt", 
    **agent_params
)

def format_news_output(news_data: Dict[str, Any]) -> str:
    """
    格式化新闻输出
    
    Args:
        news_data: 包含新闻信息的字典
        
    Returns:
        str: 格式化的新闻输出字符串
    """
    try:
        topic = news_data.get("topic", "未知话题")
        news_items = news_data.get("news_items", [])
        
        if not news_items:
            return f"# 热门新闻：{topic}\n\n没有找到相关新闻。"
        
        output = [f"# 热门新闻：{topic}\n"]
        
        for i, item in enumerate(news_items, 1):
            title = item.get("title", "无标题")
            source = item.get("source", item.get("platform", "未知来源"))
            heat = item.get("estimated_heat", 0)
            publish_time = item.get("publish_time", "未知时间")
            summary = item.get("short_summary", item.get("summary", "无摘要"))
            url = item.get("url", "")
            
            news_entry = [
                f"## {i}. {title}",
                f"- 来源：{source}",
                f"- 热度：{heat}/100",
                f"- 发布时间：{publish_time}",
                f"- 摘要：{summary}",
                f"- 链接：{url}",
                ""
            ]
            
            output.append("\n".join(news_entry))
        
        return "\n".join(output)
    except Exception as e:
        return f"格式化新闻数据时出错: {str(e)}"

def format_topics_output(topics_data: Dict[str, Any]) -> str:
    """
    格式化话题列表输出
    
    Args:
        topics_data: 包含话题信息的字典
        
    Returns:
        str: 格式化的话题列表输出字符串
    """
    try:
        topics = topics_data.get("topics", [])
        
        if not topics:
            return "# 关注话题列表\n\n您还没有添加任何关注话题。"
        
        output = ["# 关注话题列表\n"]
        
        for i, topic in enumerate(topics, 1):
            keyword = topic.get("keyword", "未知话题")
            topic_id = topic.get("topic_id", "无ID")
            created_at = topic.get("created_at", "未知时间")
            
            output.append(f"{i}. {keyword} (ID: {topic_id}, 创建时间: {created_at})")
        
        return "\n".join(output)
    except Exception as e:
        return f"格式化话题数据时出错: {str(e)}"

def process_news_request(topic: str, platforms: List[str] = None, max_results: int = 10) -> str:
    """
    处理新闻请求
    
    Args:
        topic: 搜索的新闻话题
        platforms: 新闻平台列表
        max_results: 每个平台最大返回结果数
        
    Returns:
        str: 格式化的新闻输出
    """
    try:
        # 构建请求
        request = f"""
请帮我检索关于"{topic}"的热门新闻，并按热度排序展示。

要求：
1. 使用fetch_news工具从多个平台获取新闻
2. 使用calculate_news_heat工具计算热度并排序
3. 使用generate_news_summary工具生成摘要
4. 以标准格式展示结果
"""
        
        # 调用Agent处理请求
        response = news_agent(request)
        return response
    except Exception as e:
        return f"处理新闻请求时出错: {str(e)}"

def process_topic_management(action: str, keyword: str = None, topic_id: str = None) -> str:
    """
    处理话题管理请求
    
    Args:
        action: 操作类型（add, view, delete）
        keyword: 话题关键词
        topic_id: 话题ID
        
    Returns:
        str: Agent响应
    """
    try:
        # 构建请求
        if action == "add" and keyword:
            request = f'请将"{keyword}"添加到我的关注话题列表中。'
        elif action == "view":
            request = "请显示我的所有关注话题。"
        elif action == "delete" and (keyword or topic_id):
            if keyword:
                request = f'请将"{keyword}"从我的关注话题列表中删除。'
            else:
                request = f'请删除ID为"{topic_id}"的关注话题。'
        else:
            return "无效的话题管理请求。"
        
        # 调用Agent处理请求
        response = news_agent(request)
        return response
    except Exception as e:
        return f"处理话题管理请求时出错: {str(e)}"

def process_recent_topics_news() -> str:
    """
    获取最近话题的新闻
    
    Returns:
        str: Agent响应
    """
    try:
        # 构建请求
        request = "请获取我最近关注话题的热门新闻。"
        
        # 调用Agent处理请求
        response = news_agent(request)
        return response
    except Exception as e:
        return f"获取最近话题新闻时出错: {str(e)}"

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='新闻检索Agent')
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 新闻检索命令
    news_parser = subparsers.add_parser('news', help='检索新闻')
    news_parser.add_argument('-t', '--topic', type=str, required=True, help='新闻话题')
    news_parser.add_argument('-p', '--platforms', type=str, help='新闻平台列表，用逗号分隔')
    news_parser.add_argument('-m', '--max', type=int, default=10, help='每个平台最大返回结果数')
    
    # 话题管理命令
    topic_parser = subparsers.add_parser('topic', help='管理关注话题')
    topic_parser.add_argument('action', choices=['add', 'view', 'delete'], help='操作类型')
    topic_parser.add_argument('-k', '--keyword', type=str, help='话题关键词')
    topic_parser.add_argument('-i', '--id', type=str, help='话题ID')
    
    # 最近话题新闻命令
    recent_parser = subparsers.add_parser('recent', help='获取最近话题的新闻')
    
    # 交互模式命令
    interactive_parser = subparsers.add_parser('interactive', help='交互模式')
    
    args = parser.parse_args()
    
    print(f"✅ 新闻检索Agent创建成功: {news_agent.name}")
    
    if args.command == 'news':
        platforms = args.platforms.split(',') if args.platforms else None
        result = process_news_request(args.topic, platforms, args.max)
        print(result)
    
    elif args.command == 'topic':
        result = process_topic_management(args.action, args.keyword, args.id)
        print(result)
    
    elif args.command == 'recent':
        result = process_recent_topics_news()
        print(result)
    
    elif args.command == 'interactive':
        print("欢迎使用新闻检索Agent！")
        print("您可以：")
        print("- 输入话题关键词直接检索新闻")
        print("- 输入'add 话题'添加关注话题")
        print("- 输入'view'查看所有关注话题")
        print("- 输入'delete 话题'或'delete id:话题ID'删除关注话题")
        print("- 输入'recent'获取最近关注话题的新闻")
        print("- 输入'exit'或'quit'退出")
        print()
        
        while True:
            print("---"*10)
            user_input = input("🌏请输入您的请求: ")
            print(">>>:")
            
            if user_input.lower() in ['exit', 'quit']:
                print("感谢使用，再见！")
                break
            
            if user_input.lower() == 'view':
                result = process_topic_management('view')
            elif user_input.lower().startswith('add '):
                keyword = user_input[4:].strip()
                result = process_topic_management('add', keyword)
            elif user_input.lower().startswith('delete '):
                target = user_input[7:].strip()
                if target.startswith('id:'):
                    topic_id = target[3:].strip()
                    result = process_topic_management('delete', topic_id=topic_id)
                else:
                    result = process_topic_management('delete', keyword=target)
            elif user_input.lower() == 'recent':
                result = process_recent_topics_news()
            else:
                # 默认作为话题关键词处理
                result = process_news_request(user_input)
            
            # print(result)
            print()
    
    else:
        parser.print_help()