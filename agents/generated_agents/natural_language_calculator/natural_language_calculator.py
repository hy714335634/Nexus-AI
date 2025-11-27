#!/usr/bin/env python3
"""
Natural Language Calculator Agent

专业的自然语言数学计算器智能体，能够理解中文自然语言数学表达式，执行基本四则运算，
并返回准确的计算结果。

功能:
1. 理解中文自然语言数学表达式（如"一加一等于几"、"10乘以5"）
2. 识别和转换中文数字到阿拉伯数字
3. 识别多种表达方式的四则运算符（加、减、乘、除）
4. 执行基本四则运算并返回准确结果
5. 处理输入错误和异常情况，提供友好的错误提示

工具:
- natural_language_calculator: 一站式自然语言数学表达式解析和计算
- parse_natural_language_math: 解析自然语言数学表达式
- calculate_math_expression: 执行数学运算
- convert_chinese_number: 中文数字转换
- validate_math_expression: 验证表达式有效性
- get_supported_operators: 获取支持的运算符列表
- batch_calculate: 批量计算多个表达式
- get_calculator_help: 获取计算器帮助信息
- calculator: Strands基础计算工具
- current_time: 获取当前时间
"""

import os
import json
import argparse
import logging
from typing import Dict, Any, Optional
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("natural_language_calculator")

# 配置遥测
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
natural_language_calculator = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/natural_language_calculator/natural_language_calculator",
    **agent_params
)


# ==================== AgentCore 入口点（必须包含）====================
def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """
    AgentCore 标准入口点

    当部署到 Amazon Bedrock AgentCore 时，AgentCore 会调用此函数处理请求。

    Args:
        event: AgentCore 传入的事件，包含:
            - prompt: 用户消息
            - user_id: 用户ID（可选）
            - session_id: 会话ID（可选）
            - 其他业务参数
        context: AgentCore 上下文

    Returns:
        Dict: 响应结果，必须包含 success 和 response 或 error
    """
    # 从event中提取prompt
    prompt = event.get("prompt") or event.get("message") or event.get("input", "")

    if not prompt:
        logger.error("Missing 'prompt' in request")
        return {"success": False, "error": "Missing 'prompt' in request"}

    try:
        logger.info(f"Processing calculation request: {prompt}")
        result = natural_language_calculator(prompt)
        
        # 解析Agent响应
        if hasattr(result, 'content') and result.content:
            response_text = result.content
        elif isinstance(result, str):
            response_text = result
        elif hasattr(result, 'text'):
            response_text = result.text
        else:
            response_text = str(result)
        
        logger.info(f"Calculation completed successfully")
        return {"success": True, "response": response_text}
    except Exception as e:
        logger.error(f"Calculation failed: {str(e)}")
        return {"success": False, "error": str(e)}


# 为 AgentCore 提供别名入口点
invoke = handler
main = handler


class CalculatorCLI:
    """Natural Language Calculator 命令行接口类"""

    def __init__(self, agent):
        """初始化Calculator CLI

        Args:
            agent: 已初始化的Natural Language Calculator Agent
        """
        self.agent = agent
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器

        Returns:
            argparse.ArgumentParser: 参数解析器对象
        """
        parser = argparse.ArgumentParser(
            description='Natural Language Calculator - 理解中文自然语言数学表达式并执行计算'
        )
        parser.add_argument(
            '-i', '--input',
            type=str,
            help='自然语言数学表达式（如："一加一等于几"、"10乘以5"）'
        )
        parser.add_argument(
            '-f', '--file',
            type=str,
            help='包含数学表达式的文件路径（每行一个表达式）'
        )
        parser.add_argument(
            '--batch',
            action='store_true',
            help='批量计算模式（从文件读取多个表达式）'
        )
        parser.add_argument(
            '--interactive',
            action='store_true',
            help='启用交互模式，允许连续输入多个表达式'
        )
        parser.add_argument(
            '--help-info',
            action='store_true',
            help='显示计算器帮助信息'
        )
        return parser

    def run(self) -> None:
        """运行Calculator CLI"""
        args = self.parser.parse_args()

        # 显示帮助信息
        if args.help_info:
            self._show_help()
            return

        # 交互模式
        if args.interactive:
            self._run_interactive_mode()
            return

        # 批量计算模式
        if args.batch and args.file:
            self._run_batch_mode(args.file)
            return

        # 单次计算模式
        expression = self._get_expression(args)
        if not expression:
            print("❌ 错误: 请提供数学表达式 (使用 -i 或 --file 参数)")
            return

        print(f"🔍 正在计算: {expression}\n")

        try:
            response = self.agent(expression)
            # 解析响应
            if hasattr(response, 'content') and response.content:
                result_text = response.content
            elif isinstance(response, str):
                result_text = response
            elif hasattr(response, 'text'):
                result_text = response.text
            else:
                result_text = str(response)

            print(f"📋 计算结果:\n{result_text}")
        except Exception as e:
            logger.error(f"Calculation error: {str(e)}")
            print(f"❌ 计算失败: {str(e)}")

    def _get_expression(self, args) -> Optional[str]:
        """从命令行参数或文件中获取数学表达式

        Args:
            args: 解析后的命令行参数

        Returns:
            Optional[str]: 数学表达式文本，如果未提供则返回None
        """
        if args.input:
            return args.input
        elif args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Failed to read file: {str(e)}")
                print(f"❌ 读取文件失败: {str(e)}")
                return None
        else:
            return None

    def _run_interactive_mode(self) -> None:
        """运行交互模式，支持连续输入多个表达式"""
        print("🔄 进入交互模式 (输入'exit'或'quit'退出)\n")
        print("💡 提示: 您可以使用中文或阿拉伯数字，例如：")
        print("   - 一加一等于几")
        print("   - 10乘以5")
        print("   - 二十除以四\n")

        while True:
            try:
                user_input = input("请输入数学表达式: ")
                if user_input.lower() in ['exit', 'quit', '退出']:
                    print("👋 感谢使用自然语言计算器!")
                    break

                if not user_input.strip():
                    continue

                response = self.agent(user_input)
                # 解析响应
                if hasattr(response, 'content') and response.content:
                    result_text = response.content
                elif isinstance(response, str):
                    result_text = response
                elif hasattr(response, 'text'):
                    result_text = response.text
                else:
                    result_text = str(response)

                print(f"\n📋 {result_text}\n")
            except KeyboardInterrupt:
                print("\n👋 感谢使用自然语言计算器!")
                break
            except Exception as e:
                logger.error(f"Calculation error: {str(e)}")
                print(f"❌ 计算失败: {str(e)}\n")

    def _run_batch_mode(self, file_path: str) -> None:
        """运行批量计算模式

        Args:
            file_path (str): 包含多个表达式的文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                expressions = [line.strip() for line in f if line.strip()]

            if not expressions:
                print("❌ 文件中没有找到有效的表达式")
                return

            print(f"🔍 正在批量计算 {len(expressions)} 个表达式...\n")

            # 构建批量计算请求
            batch_request = "请批量计算以下表达式：\n" + "\n".join(
                [f"{i + 1}. {expr}" for i, expr in enumerate(expressions)]
            )

            response = self.agent(batch_request)
            # 解析响应
            if hasattr(response, 'content') and response.content:
                result_text = response.content
            elif isinstance(response, str):
                result_text = response
            elif hasattr(response, 'text'):
                result_text = response.text
            else:
                result_text = str(response)

            print(f"📋 批量计算结果:\n{result_text}")
        except Exception as e:
            logger.error(f"Batch calculation error: {str(e)}")
            print(f"❌ 批量计算失败: {str(e)}")

    def _show_help(self) -> None:
        """显示计算器帮助信息"""
        try:
            help_request = "请显示计算器的帮助信息"
            response = self.agent(help_request)
            # 解析响应
            if hasattr(response, 'content') and response.content:
                help_text = response.content
            elif isinstance(response, str):
                help_text = response
            elif hasattr(response, 'text'):
                help_text = response.text
            else:
                help_text = str(response)

            print(f"📖 计算器帮助信息:\n{help_text}")
        except Exception as e:
            logger.error(f"Failed to get help info: {str(e)}")
            print(f"❌ 获取帮助信息失败: {str(e)}")


# ==================== 本地运行入口 ====================
if __name__ == "__main__":
    print(f"✅ Natural Language Calculator Agent 创建成功: {natural_language_calculator.name}")

    # 运行命令行界面
    cli = CalculatorCLI(natural_language_calculator)
    cli.run()
