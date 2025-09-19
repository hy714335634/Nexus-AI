#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logo Design Agent

专业的Logo设计智能体，能够分析用户需求，设计并生成高质量的logo图片，
并提供设计说明报告。集成图像生成、HTML报告生成和专业知识检索功能，
实现完整的logo设计流程，从需求分析到最终交付。

功能包括：
1. 需求收集与分析：收集和分析用户的品牌需求，形成设计基础
2. 设计概念生成：基于需求分析生成logo设计概念
3. Logo图像生成：基于设计概念生成高质量logo图像
4. 设计报告生成：生成HTML格式的设计报告，解释设计过程和理念

使用工具：
- image_generator: 生成高质量logo图像
- html_report_generator: 生成HTML格式的设计报告
- web_search: 检索相关专业知识
- file_write: 保存生成的文件
- file_read: 读取文件
- current_time: 获取当前时间
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 设置遥测
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class LogoDesignAgent:
    """Logo设计智能体类，封装所有功能和交互逻辑"""
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化Logo设计智能体
        
        Args:
            env: 环境配置（development, production, testing）
            version: 使用的模板版本
            model_id: 使用的模型ID
        """
        self.agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id
        }
        
        # 创建智能体
        self.agent = create_agent_from_prompt_template(
            agent_name="generated_agents_prompts/logo_design_agent/logo_designer",
            **self.agent_params
        )
        
        logger.info(f"Logo Design Agent initialized with {env} environment")
    
    def design_logo(self, user_input: str) -> str:
        """
        处理用户的logo设计请求
        
        Args:
            user_input: 用户的品牌和设计需求描述
            
        Returns:
            str: 智能体的响应
        """
        try:
            # 调用智能体处理用户输入
            response = self.agent(user_input)
            return response
        except Exception as e:
            error_msg = f"Error processing logo design request: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，处理您的logo设计请求时出现错误: {str(e)}"
    
    def process_feedback(self, feedback: str, conversation_id: Optional[str] = None) -> str:
        """
        处理用户对设计的反馈
        
        Args:
            feedback: 用户的反馈内容
            conversation_id: 对话ID，用于关联之前的设计
            
        Returns:
            str: 智能体的响应
        """
        try:
            # 构建反馈请求
            feedback_request = f"针对之前的logo设计，我有以下反馈：\n{feedback}"
            
            # 调用智能体处理反馈
            response = self.agent(feedback_request, conversation_id=conversation_id)
            return response
        except Exception as e:
            error_msg = f"Error processing design feedback: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，处理您的设计反馈时出现错误: {str(e)}"
    
    def generate_report(self, design_info: Dict[str, Any], logo_paths: List[str]) -> str:
        """
        生成设计报告（直接调用工具，绕过智能体对话）
        
        Args:
            design_info: 设计相关信息
            logo_paths: Logo图像文件路径列表
            
        Returns:
            str: 报告生成结果
        """
        try:
            # 构建报告生成请求
            report_request = (
                f"请为以下logo设计生成HTML报告：\n"
                f"品牌名称：{design_info.get('brand_name', '品牌')}\n"
                f"设计理念：{design_info.get('design_rationale', '现代简约设计')}\n"
                f"请包含所有设计元素和色彩方案的详细解释。"
            )
            
            # 调用智能体生成报告
            response = self.agent(report_request)
            return response
        except Exception as e:
            error_msg = f"Error generating design report: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，生成设计报告时出现错误: {str(e)}"

def get_logo_designer(env: str = "production", version: str = "latest", model_id: str = "default") -> LogoDesignAgent:
    """
    获取Logo设计智能体实例
    
    Args:
        env: 环境配置（development, production, testing）
        version: 使用的模板版本
        model_id: 使用的模型ID
        
    Returns:
        LogoDesignAgent: Logo设计智能体实例
    """
    return LogoDesignAgent(env, version, model_id)

# 创建默认智能体实例
logo_designer = get_logo_designer()

if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Logo设计智能体')
    parser.add_argument('-i', '--input', type=str, 
                       default="我需要为一家名为'TechNova'的科技初创公司设计logo，主要从事人工智能和云计算业务。希望logo能体现科技感和创新精神，色调偏好蓝色和紫色。",
                       help='用户需求描述')
    parser.add_argument('-e', '--env', type=str, 
                       default="production",
                       help='运行环境 (development, production, testing)')
    parser.add_argument('-m', '--model', type=str, 
                       default="default",
                       help='使用的模型ID')
    args = parser.parse_args()
    
    # 创建智能体
    agent = get_logo_designer(env=args.env, model_id=args.model)
    
    print(f"✅ Logo Design Agent 创建成功")
    print(f"🎯 测试输入: {args.input}")
    
    try:
        # 调用智能体处理用户输入
        result = agent.design_logo(args.input)
        print(f"📋 Agent 响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")