#!/usr/bin/env python3
"""
会议纪要生成Agent

专业的视频会议纪要生成专家，处理视频会议文件，提取音频，转换为文本，生成标准会议纪要。
支持多种视频格式、高质量音频提取、准确的语音转文本和标准化会议纪要生成。
"""

import os
import json
import argparse
from typing import Dict, List, Optional, Any, Union
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"  # 使用默认模型（Claude 3.7 Sonnet）
}

# 使用 agent_factory 创建 agent
meeting_minutes_generator = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/meeting_minutes_generator/meeting_minutes_generator", 
    **agent_params
)

def process_video(
    video_path: str, 
    meeting_title: Optional[str] = None, 
    meeting_date: Optional[str] = None,
    participants: Optional[List[str]] = None,
    language_code: str = "zh-CN",
    format_type: str = "standard",
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理视频会议文件并生成会议纪要
    
    Args:
        video_path: 视频文件路径
        meeting_title: 会议标题（可选）
        meeting_date: 会议日期（可选）
        participants: 参会人员列表（可选）
        language_code: 语言代码，默认为中文
        format_type: 会议纪要格式类型（standard, detailed, summary）
        output_dir: 输出目录路径（可选）
        
    Returns:
        包含处理结果的字典
    """
    # 构建用户输入
    user_input = f"请处理以下视频会议文件并生成会议纪要：\n视频文件路径: {video_path}"
    
    # 添加可选参数
    if meeting_title:
        user_input += f"\n会议标题: {meeting_title}"
    if meeting_date:
        user_input += f"\n会议日期: {meeting_date}"
    if participants:
        user_input += f"\n参会人员: {', '.join(participants)}"
    
    user_input += f"\n语言: {language_code}"
    user_input += f"\n纪要格式: {format_type}"
    
    if output_dir:
        user_input += f"\n输出目录: {output_dir}"
    
    # 调用Agent处理请求
    try:
        response = meeting_minutes_generator(user_input)
        
        # 尝试从响应中提取JSON结果
        try:
            # 查找JSON内容（可能嵌入在文本中）
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # 尝试将整个响应解析为JSON
                result = json.loads(response)
        except json.JSONDecodeError:
            # 如果无法解析JSON，返回原始响应
            result = {"success": True, "response": response}
            
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "agent_error"
        }

def main():
    """命令行界面入口点"""
    parser = argparse.ArgumentParser(description='会议纪要生成工具')
    parser.add_argument('-v', '--video', type=str, required=True,
                        help='视频文件路径')
    parser.add_argument('-t', '--title', type=str, default=None,
                        help='会议标题')
    parser.add_argument('-d', '--date', type=str, default=None,
                        help='会议日期')
    parser.add_argument('-p', '--participants', type=str, default=None,
                        help='参会人员，用逗号分隔')
    parser.add_argument('-l', '--language', type=str, default="zh-CN",
                        help='语言代码，默认为中文(zh-CN)')
    parser.add_argument('-f', '--format', type=str, default="standard",
                        choices=["standard", "detailed", "summary"],
                        help='纪要格式类型')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='输出目录路径')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='交互模式，直接与Agent对话')
    
    args = parser.parse_args()
    
    # 交互模式
    if args.interactive:
        print("📝 会议纪要生成Agent已启动（交互模式）")
        print("输入'exit'或'quit'退出")
        
        while True:
            user_input = input("\n🔹 请输入您的请求: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            try:
                response = meeting_minutes_generator(user_input)
                print(f"\n🔸 Agent响应:\n{response}")
            except Exception as e:
                print(f"\n❌ 错误: {e}")
        
        print("👋 感谢使用会议纪要生成Agent")
        return
    
    # 处理视频模式
    print(f"📝 正在处理视频: {args.video}")
    
    # 解析参与者列表
    participants = None
    if args.participants:
        participants = [p.strip() for p in args.participants.split(',')]
    
    # 调用处理函数
    result = process_video(
        video_path=args.video,
        meeting_title=args.title,
        meeting_date=args.date,
        participants=participants,
        language_code=args.language,
        format_type=args.format,
        output_dir=args.output
    )
    
    # 输出结果
    print(result)
    if result['success']:
        print("✅ 会议纪要生成成功!")
        
        # 显示纪要路径（如果有）
        if "minutes_path" in result:
            print(f"📄 会议纪要已保存至: {result['minutes_path']}")
        
        # 显示会议纪要内容（如果有）
        if "meeting_minutes" in result:
            print("\n📋 会议纪要内容:")
            print("-" * 80)
            print(result["meeting_minutes"])
            print("-" * 80)
    else:
        print(f"❌ 处理失败: {result.get('error', '未知错误')}")
        if "error_type" in result:
            print(f"错误类型: {result['error_type']}")

if __name__ == "__main__":
    main()