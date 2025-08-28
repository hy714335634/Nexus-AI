#!/usr/bin/env python3
"""
深度研究分析师 - 使用 agent_factory 动态创建具备多源搜索能力的研究agent
"""

import os
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 定义 agent 创建的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# 使用agent_factory创建深度研究agent
deep_research_agent = create_agent_from_prompt_template(
    agent_name="template_prompts/deep_research_agent", **agent_params
)


def conduct_research(research_topic: str) -> str:
    """
    执行深度研究分析
    
    Args:
        research_topic: 研究主题
        
    Returns:
        研究报告结果
    """
    print(f"🔍 开始深度研究: {research_topic}")
    
    try:
        result = deep_research_agent(research_topic)
        print("✅ 研究完成")
        return result
    except Exception as e:
        error_msg = f"❌ 研究过程中出现错误: {str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="深度研究分析师")
    parser.add_argument('-t', '--topic', type=str, 
                       default="人工智能在医疗领域的最新应用和发展趋势",
                       help='研究主题')
    parser.add_argument('--interactive', action='store_true',
                       help='交互式模式')
    args = parser.parse_args()
    
    print(f"✅ 深度研究Agent创建成功: {deep_research_agent.name}")
    print(f"🎯 Agent描述: 专业的深度研究分析师，能够进行全面的信息收集、分析和综合报告生成")
    
    if args.interactive:
        print("\n🔄 进入交互式研究模式 (输入 'quit' 退出)")
        while True:
            topic = input("\n请输入研究主题: ").strip()
            if topic.lower() in ['quit', 'exit', '退出']:
                print("👋 退出研究模式")
                break
            if topic:
                conduct_research(topic)
    else:
        # 运行单次研究
        conduct_research(args.topic)