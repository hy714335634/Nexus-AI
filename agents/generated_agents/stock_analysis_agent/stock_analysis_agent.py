"""
Stock Analysis Agent - 智能股票分析系统主协调器

这是一个复杂的多Agent股票分析系统，包含7个专业Agent：
1. CoordinatorAgent - 流程协调
2. DataCollectorAgent - 数据采集  
3. ValuationAgent - DCF估值
4. PredictionAgent - 盈利预测
5. RiskAssessmentAgent - 风险评估
6. BenchmarkAgent - 对比分析
7. ReportGeneratorAgent - 报告生成

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock
- numpy, pandas, scipy
- Streamlit

作者：Nexus AI Agent Developer
版本：1.0.0
日期：2025-11-07
"""

import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext
from datetime import datetime

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 导入Strands SDK
from nexus_utils.agent_factory import create_agent_from_prompt_template

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stock_analysis_agent")

# 创建 BedrockAgentCoreApp 实例
app = BedrockAgentCoreApp()


class StockAnalysisSystem:
    """股票分析系统主类"""
    
    def __init__(self, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化股票分析系统
        
        Args:
            env: 环境配置
            version: 版本
            model_id: 模型ID
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        
        # 创建Agent参数
        self.agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id
        }
        
        # 初始化所有Agent
        self._initialize_agents()
        
        logger.info("✅ 股票分析系统初始化成功")
    
    def _initialize_agents(self):
        """初始化所有专业Agent"""
        try:
            # 1. 协调器Agent
            self.coordinator_agent = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/stock_analysis_agent/coordinator_agent",
                **self.agent_params
            )
            logger.info("✅ CoordinatorAgent创建成功")
            
        except Exception as e:
            logger.error(f"❌ Agent初始化失败: {str(e)}")
            raise RuntimeError(f"Agent初始化失败: {str(e)}")
    
    def analyze_stock(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        执行完整的股票分析流程
        
        Args:
            symbol: 股票代码
            **kwargs: 其他分析参数
            
        Returns:
            Dict[str, Any]: 完整的分析结果
        """
        try:
            logger.info(f"🚀 开始分析股票: {symbol}")
            
            # 构建分析请求
            analysis_request = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "parameters": kwargs
            }
            
            # 1. 通过协调器Agent启动分析流程
            logger.info("📋 步骤1: 启动协调器Agent")
            coordinator_request = f"""
请协调完整的股票分析流程，分析股票代码：{symbol}

分析要求：
1. 验证股票代码有效性
2. 按顺序调用各专业Agent
3. 收集和整合所有分析结果
4. 处理可能的错误和异常
5. 生成最终分析报告

请开始执行分析流程。
"""
            
            coordinator_response = self.coordinator_agent(coordinator_request)
            
            # 解析协调器响应
            coordinator_result = self._parse_agent_response(coordinator_response)
            
            if not coordinator_result.get("success", False):
                logger.error(f"❌ 协调器执行失败: {coordinator_result.get('message', '未知错误')}")
                return {
                    "status": "error",
                    "message": coordinator_result.get("message", "协调器执行失败"),
                    "symbol": symbol
                }
            
            logger.info("✅ 股票分析完成")
            
            # 返回完整结果
            return {
                "status": "success",
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "analysis_result": coordinator_result,
                "message": "股票分析完成"
            }
            
        except Exception as e:
            logger.error(f"❌ 股票分析失败: {str(e)}")
            return {
                "status": "error",
                "message": f"股票分析异常: {str(e)}",
                "symbol": symbol
            }
    
    def _parse_agent_response(self, response: Any) -> Dict[str, Any]:
        """
        解析Agent响应
        
        Args:
            response: Agent响应
            
        Returns:
            Dict[str, Any]: 解析后的结果
        """
        try:
            # 多层级属性检查
            if hasattr(response, 'content') and response.content:
                extracted_content = response.content
            elif isinstance(response, str):
                extracted_content = response
            elif hasattr(response, 'text'):
                extracted_content = response.text
            else:
                extracted_content = str(response)
            
            # 尝试JSON提取
            try:
                json_start = extracted_content.find('{')
                json_end = extracted_content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = extracted_content[json_start:json_end]
                    parsed_result = json.loads(json_str)
                    return parsed_result
                else:
                    return {"success": True, "content": extracted_content}
            except json.JSONDecodeError:
                return {"success": True, "content": extracted_content}
                
        except Exception as e:
            logger.error(f"响应解析失败: {str(e)}")
            return {
                "success": False,
                "message": f"响应解析异常: {str(e)}"
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            Dict[str, Any]: 系统状态信息
        """
        return {
            "status": "healthy",
            "agents": {
                "coordinator": "ready" if self.coordinator_agent else "not_ready"
            },
            "environment": self.env,
            "version": self.version,
            "timestamp": datetime.now().isoformat()
        }


# ==================== AgentCore 入口点（必须包含）====================
@app.entrypoint
async def handler(payload: Dict[str, Any], context: RequestContext):
    """
    AgentCore 标准入口点（支持流式响应）

    Args:
        payload: AgentCore 传入的请求体，包含:
            - prompt: 用户消息
            - symbol: 股票代码（可选）
        context: 请求上下文，包含:
            - session_id: 会话ID

    Yields:
        str: 流式响应的文本片段
    """
    session_id = context.session_id
    print(f"📥 Received payload: {json.dumps(payload, ensure_ascii=False)}, session_id: {session_id}")

    prompt = payload.get("prompt") or payload.get("message") or payload.get("input", "")

    if not prompt:
        yield "Error: Missing 'prompt' in request"
        return

    print(f"🔄 Processing prompt: {prompt}")

    try:
        # 初始化系统
        system = StockAnalysisSystem()
        
        # 使用coordinator处理请求
        stream = system.coordinator_agent.stream_async(prompt)
        async for event in stream:
            print(f"📤 Streaming event: {event}")
            yield event

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        yield f"Error: {str(e)}"

if __name__ == "__main__":
    """主函数"""
    parser = argparse.ArgumentParser(description='Stock Analysis Agent - 智能股票分析系统')
    parser.add_argument('-s', '--symbol', type=str, help='股票代码 (例如: AAPL, TSLA)')
    parser.add_argument('--env', type=str, default='production', help='环境配置')
    parser.add_argument('--version', type=str, default='latest', help='版本')
    parser.add_argument('--model-id', type=str, default='default', help='模型ID')
    parser.add_argument('--status', action='store_true', help='显示系统状态')
    parser.add_argument('-it', '--interactive', action='store_true', help='启动交互式多轮对话模式')
    
    args = parser.parse_args()

    # 检查是否在 Docker 容器中运行（AgentCore 部署）
    is_docker = os.environ.get("DOCKER_CONTAINER") == "1"

    if is_docker:
        # AgentCore 部署模式：启动 HTTP 服务器
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()

    try:
        # 初始化系统
        logger.info("🚀 初始化股票分析系统...")
        system = StockAnalysisSystem(
            env=args.env,
            version=args.version,
            model_id=args.model_id
        )
        
        # 如果请求状态
        if args.status:
            status = system.get_system_status()
            print("\n📊 系统状态:")
            print(json.dumps(status, indent=2, ensure_ascii=False))
            sys.exit(0)
        
        # 交互式模式
        if args.interactive:
            print("✅ 股票分析系统创建成功")
            print("💬 进入交互式对话模式（输入 'quit' 或 'exit' 退出）\n")
            
            while True:
                try:
                    user_input = input("You: ")
                    user_input = user_input.encode('utf-8', errors='ignore').decode('utf-8').strip()
                    
                    if user_input.lower() in ['quit', 'exit']:
                        print("👋 退出交互式对话")
                        break
                    if not user_input:
                        continue
                    
                    # 使用coordinator处理用户输入
                    system.coordinator_agent(user_input)
                    print()
                except KeyboardInterrupt:
                    print("\n👋 退出交互式对话")
                    break
                except Exception as e:
                    print(f"❌ 错误: {e}\n")
            sys.exit(0)
        elif args.symbol:
            # 执行股票分析
            logger.info(f"📈 开始分析股票: {args.symbol}")
            result = system.analyze_stock(args.symbol)
            
            # 输出结果
            print("\n" + "="*80)
            print("📋 股票分析结果")
            print("="*80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*80 + "\n")
            
            # 根据结果状态设置退出码
            sys.exit(0 if result.get("status") == "success" else 1)
        
        print("🚀 启动 AgentCore HTTP 服务器，端口: 8080")
        app.run()
    except Exception as e:
        logger.error(f"❌ 系统执行失败: {str(e)}")
        print(f"\n❌ 错误: {str(e)}\n")
        sys.exit(1)
