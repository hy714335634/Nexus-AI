#!/usr/bin/env python3
"""
新闻处理工具模块

提供新闻热度计算、排序和摘要生成功能
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import boto3
from strands import tool


@tool
def calculate_news_heat(news_data: str) -> str:
    """
    计算新闻热度并按热度排序
    
    Args:
        news_data (str): JSON格式的新闻数据，通常是fetch_news的输出
        
    Returns:
        str: JSON格式的排序后的新闻数据，包含热度分数
    """
    try:
        # 解析输入数据
        try:
            data = json.loads(news_data)
        except:
            return json.dumps({
                "error": "输入数据格式错误，无法解析JSON",
                "status": "error"
            }, ensure_ascii=False, indent=2)
        
        # 检查数据结构
        if "news_items" not in data:
            return json.dumps({
                "error": "输入数据缺少news_items字段",
                "status": "error"
            }, ensure_ascii=False, indent=2)
        
        news_items = data["news_items"]
        if not news_items:
            return json.dumps({
                "error": "没有找到新闻数据",
                "status": "error",
                "topic": data.get("topic", "未知话题")
            }, ensure_ascii=False, indent=2)
        
        # 计算或更新热度分数
        for item in news_items:
            # 如果已有热度分数，则使用现有分数
            if "estimated_heat" in item and item["estimated_heat"] is not None:
                continue
            
            # 否则计算热度分数
            read_count = item.get("read_count")
            comment_count = item.get("comment_count")
            
            # 解析发布日期
            publish_date = None
            if "publish_date" in item and item["publish_date"]:
                try:
                    publish_date = datetime.fromisoformat(item["publish_date"])
                except:
                    publish_date = None
            
            # 计算热度分数
            heat_score = _calculate_heat_score(
                read_count=read_count,
                comment_count=comment_count,
                publish_date=publish_date
            )
            
            item["estimated_heat"] = heat_score
        
        # 按热度排序（降序）
        sorted_news = sorted(news_items, key=lambda x: x.get("estimated_heat", 0), reverse=True)
        
        # 构建结果
        result = {
            "topic": data.get("topic", "未知话题"),
            "process_time": datetime.now().isoformat(),
            "total_count": len(sorted_news),
            "news_items": sorted_news,
            "status": "success",
            "heat_calculation_method": "综合阅读量、评论数和时间新鲜度的加权算法"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"热度计算失败: {str(e)}",
            "status": "error"
        }, ensure_ascii=False, indent=2)


@tool
def generate_news_summary(news_data: str, summary_length: str = "short") -> str:
    """
    为新闻生成摘要
    
    Args:
        news_data (str): JSON格式的新闻数据，通常是fetch_news或calculate_news_heat的输出
        summary_length (str): 摘要长度，可选值：short（短摘要，约50字）, medium（中等长度，约100字）, long（长摘要，约200字）
        
    Returns:
        str: JSON格式的带摘要的新闻数据
    """
    try:
        # 解析输入数据
        try:
            data = json.loads(news_data)
        except:
            return json.dumps({
                "error": "输入数据格式错误，无法解析JSON",
                "status": "error"
            }, ensure_ascii=False, indent=2)
        
        # 检查数据结构
        if "news_items" not in data:
            return json.dumps({
                "error": "输入数据缺少news_items字段",
                "status": "error"
            }, ensure_ascii=False, indent=2)
        
        news_items = data["news_items"]
        if not news_items:
            return json.dumps({
                "error": "没有找到新闻数据",
                "status": "error",
                "topic": data.get("topic", "未知话题")
            }, ensure_ascii=False, indent=2)
        
        # 确定摘要长度限制
        if summary_length == "short":
            max_length = 50
        elif summary_length == "medium":
            max_length = 100
        elif summary_length == "long":
            max_length = 200
        else:
            max_length = 100  # 默认中等长度
        
        # 生成摘要
        for item in news_items:
            # 如果已有摘要，检查是否需要调整长度
            if "summary" in item and item["summary"]:
                current_summary = item["summary"]
                
                # 如果现有摘要太长，截断它
                if len(current_summary) > max_length:
                    item["short_summary"] = current_summary[:max_length] + "..."
                    item["full_summary"] = current_summary
                else:
                    item["short_summary"] = current_summary
                    item["full_summary"] = current_summary
            else:
                # 没有摘要，使用标题作为摘要
                item["short_summary"] = item.get("title", "无标题")
                item["full_summary"] = item.get("title", "无标题")
            
            # 尝试使用Amazon Bedrock生成更好的摘要
            try:
                if "title" in item and item.get("title"):
                    # 使用标题和现有摘要作为输入
                    title = item.get("title", "")
                    existing_summary = item.get("summary", "")
                    
                    # 调用Amazon Bedrock生成摘要
                    generated_summary = _generate_bedrock_summary(
                        title=title,
                        content=existing_summary,
                        max_length=max_length
                    )
                    
                    if generated_summary:
                        item["short_summary"] = generated_summary
                        if "full_summary" not in item or not item["full_summary"]:
                            item["full_summary"] = generated_summary
            except Exception as e:
                # 摘要生成失败时使用默认摘要
                pass
        
        # 构建结果
        result = {
            "topic": data.get("topic", "未知话题"),
            "process_time": datetime.now().isoformat(),
            "total_count": len(news_items),
            "news_items": news_items,
            "status": "success",
            "summary_length": summary_length,
            "summary_method": "使用Amazon Bedrock生成摘要，结合原始内容"
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"摘要生成失败: {str(e)}",
            "status": "error"
        }, ensure_ascii=False, indent=2)


def _calculate_heat_score(read_count: Optional[int] = None, 
                         comment_count: Optional[int] = None,
                         publish_date: Optional[datetime] = None) -> float:
    """计算新闻热度分数"""
    score = 0.0
    
    # 基于阅读量的分数
    if read_count is not None:
        # 阅读量对数变换，避免极值影响
        score += min(50, max(0, 10 * (read_count / 1000)))
    
    # 基于评论数的分数（评论互动更有价值）
    if comment_count is not None:
        score += min(30, max(0, 15 * (comment_count / 100)))
    
    # 基于时间新鲜度的分数
    time_score = _calculate_freshness(publish_date)
    score += time_score
    
    # 如果没有任何数据，给一个默认分数
    if score == 0:
        score = 10.0
    
    return round(score, 2)


def _calculate_freshness(publish_date: Optional[datetime]) -> float:
    """计算基于发布时间的新鲜度分数"""
    if not publish_date:
        return 10.0  # 默认分数
    
    now = datetime.now()
    hours_diff = (now - publish_date).total_seconds() / 3600
    
    # 24小时内的新闻获得较高分数
    if hours_diff <= 24:
        return 20.0 * (1 - hours_diff / 24)
    # 一周内的新闻获得中等分数
    elif hours_diff <= 168:  # 7*24
        return 10.0 * (1 - (hours_diff - 24) / 144)
    # 更旧的新闻获得较低分数
    else:
        return max(0, 5.0 * (1 - (hours_diff - 168) / 672))  # 最多考虑一个月


def _generate_bedrock_summary(title: str, content: str, max_length: int) -> str:
    """使用Amazon Bedrock生成新闻摘要"""
    try:
        # 创建Bedrock客户端
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
        
        # 准备提示词
        prompt = f"""请为以下新闻生成一个简洁的摘要，不超过{max_length}个字符：
        
标题：{title}
        
内容：{content}
        
摘要："""
        
        # 调用Claude模型
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-v2',
            body=json.dumps({
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": 300,
                "temperature": 0.1,
                "top_p": 0.9,
            })
        )
        
        # 解析响应
        response_body = json.loads(response['body'].read())
        summary = response_body.get('completion', '').strip()
        
        # 确保摘要不超过最大长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        
        return summary
    
    except Exception as e:
        # 如果Bedrock调用失败，使用简单的提取方法
        if content and len(content) > 0:
            if len(content) > max_length:
                return content[:max_length] + "..."
            return content
        return title