#!/usr/bin/env python3
"""
儿童智能陪伴对话系统 - Kids Companion Chatbot

专业的儿童陪伴对话助手，为3-12岁儿童提供安全、有趣、个性化的对话体验。
支持多轮对话、用户画像管理、跨会话记忆和年龄适配功能。

功能特性：
- 与3-12岁儿童进行多轮自然对话
- 根据儿童年龄段自动调整对话风格
- 构建和更新儿童用户画像
- 实现跨会话记忆和个性化交互
- 确保对话内容安全和适龄性
- 引导积极话题和互动

技术栈：
- Python 3.13+
- Strands SDK
- AWS Bedrock Claude Sonnet 4.5
- 本地缓存存储

作者: Nexus-AI Agent Developer
版本: 1.0.0
日期: 2025-11-26
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('.cache/kids_companion_chatbot/agent.log')
    ]
)
logger = logging.getLogger("kids_companion_chatbot")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class KidsCompanionChatbot:
    """
    儿童智能陪伴对话系统主类
    
    功能：
    - 管理对话会话
    - 处理用户画像
    - 协调Agent调用
    - 处理对话流程
    """
    
    def __init__(self):
        """初始化儿童陪伴对话系统"""
        logger.info("初始化儿童陪伴对话系统...")
        
        # 创建Agent参数
        agent_params = {
            "env": "production",
            "version": "latest", 
            "model_id": "default",
            "enable_logging": True
        }
        
        # 使用agent_factory创建Agent
        try:
            self.agent = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/kids_companion_chatbot/kids_companion_chatbot", 
                **agent_params
            )
            logger.info(f"✅ Agent创建成功: {self.agent.name}")
        except Exception as e:
            logger.error(f"❌ Agent创建失败: {e}")
            raise RuntimeError(f"Agent初始化失败: {e}")
        
        # 初始化会话状态
        self.current_session: Optional[Dict[str, Any]] = None
        self.current_child_id: Optional[str] = None
        self.conversation_history: list = []
        
        # 确保缓存目录存在
        self._ensure_cache_directory()
        
    def _ensure_cache_directory(self):
        """确保缓存目录存在"""
        cache_dirs = [
            ".cache/kids_companion_chatbot",
            ".cache/kids_companion_chatbot/profiles",
            ".cache/kids_companion_chatbot/sessions"
        ]
        for cache_dir in cache_dirs:
            os.makedirs(cache_dir, exist_ok=True)
            logger.debug(f"缓存目录已创建: {cache_dir}")
    
    def start_conversation(self, child_id: str, child_name: Optional[str] = None, 
                          child_age: Optional[int] = None) -> Dict[str, Any]:
        """
        开始新的对话会话
        
        Args:
            child_id: 儿童唯一标识符
            child_name: 儿童姓名（可选）
            child_age: 儿童年龄（可选）
            
        Returns:
            会话启动结果
        """
        logger.info(f"开始新对话会话: child_id={child_id}")
        
        try:
            self.current_child_id = child_id
            
            # 构建启动消息
            start_message = f"child_id: {child_id}"
            if child_name:
                start_message += f", name: {child_name}"
            if child_age:
                start_message += f", age: {child_age}"
            
            start_message += "\n\n开始新的对话会话，请加载用户画像（如果存在）并开始友好的对话。"
            
            # 调用Agent启动会话
            response = self.agent(start_message)
            
            # 解析响应
            response_text = self._extract_response_text(response)
            
            # 记录会话历史
            self.conversation_history.append({
                "role": "user",
                "content": start_message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info("✅ 对话会话启动成功")
            
            return {
                "status": "success",
                "child_id": child_id,
                "response": response_text,
                "session_started": True
            }
            
        except Exception as e:
            logger.error(f"❌ 启动对话会话失败: {e}")
            return {
                "status": "error",
                "message": f"启动对话失败: {str(e)}"
            }
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """
        进行对话交互
        
        Args:
            user_message: 用户输入的消息
            
        Returns:
            对话响应结果
        """
        if not self.current_child_id:
            return {
                "status": "error",
                "message": "请先启动对话会话（调用start_conversation）"
            }
        
        logger.info(f"处理用户消息: {user_message[:50]}...")
        
        try:
            # 调用Agent处理消息
            response = self.agent(user_message)
            
            # 解析响应
            response_text = self._extract_response_text(response)
            
            # 记录对话历史
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info("✅ 对话响应成功")
            
            return {
                "status": "success",
                "response": response_text,
                "conversation_turns": len(self.conversation_history) // 2
            }
            
        except Exception as e:
            logger.error(f"❌ 对话处理失败: {e}")
            return {
                "status": "error",
                "message": f"对话处理失败: {str(e)}"
            }
    
    def end_conversation(self, session_summary: Optional[str] = None) -> Dict[str, Any]:
        """
        结束当前对话会话
        
        Args:
            session_summary: 会话摘要（可选）
            
        Returns:
            会话结束结果
        """
        if not self.current_child_id:
            return {
                "status": "error",
                "message": "没有活动的对话会话"
            }
        
        logger.info(f"结束对话会话: child_id={self.current_child_id}")
        
        try:
            # 构建结束消息
            end_message = f"对话结束。child_id: {self.current_child_id}"
            if session_summary:
                end_message += f"\n会话摘要: {session_summary}"
            end_message += "\n\n请保存会话数据并更新用户画像。"
            
            # 调用Agent结束会话
            response = self.agent(end_message)
            response_text = self._extract_response_text(response)
            
            # 保存会话历史
            self._save_conversation_history()
            
            # 清理会话状态
            conversation_turns = len(self.conversation_history) // 2
            child_id = self.current_child_id
            
            self.current_child_id = None
            self.current_session = None
            self.conversation_history = []
            
            logger.info("✅ 对话会话结束")
            
            return {
                "status": "success",
                "child_id": child_id,
                "conversation_turns": conversation_turns,
                "response": response_text
            }
            
        except Exception as e:
            logger.error(f"❌ 结束对话会话失败: {e}")
            return {
                "status": "error",
                "message": f"结束会话失败: {str(e)}"
            }
    
    def _extract_response_text(self, response: Any) -> str:
        """
        从Agent响应中提取文本内容
        
        Args:
            response: Agent响应对象
            
        Returns:
            提取的文本内容
        """
        try:
            # 多层级属性检查
            if hasattr(response, 'content') and response.content:
                return str(response.content)
            elif isinstance(response, str):
                return response
            elif hasattr(response, 'text'):
                return str(response.text)
            elif hasattr(response, 'message'):
                return str(response.message)
            else:
                return str(response)
        except Exception as e:
            logger.warning(f"响应文本提取失败，使用默认转换: {e}")
            return str(response)
    
    def _save_conversation_history(self):
        """保存对话历史到本地文件"""
        if not self.current_child_id or not self.conversation_history:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = f".cache/kids_companion_chatbot/sessions/{self.current_child_id}/history_{timestamp}.json"
            
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "child_id": self.current_child_id,
                    "timestamp": timestamp,
                    "conversation_turns": len(self.conversation_history) // 2,
                    "history": self.conversation_history
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"对话历史已保存: {history_file}")
        except Exception as e:
            logger.error(f"保存对话历史失败: {e}")
    
    def get_conversation_history(self) -> list:
        """获取当前对话历史"""
        return self.conversation_history.copy()
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取当前会话信息"""
        return {
            "child_id": self.current_child_id,
            "conversation_turns": len(self.conversation_history) // 2,
            "is_active": self.current_child_id is not None
        }


def main():
    """主函数 - 命令行交互测试"""
    import argparse
    
    parser = argparse.ArgumentParser(description='儿童智能陪伴对话系统')
    parser.add_argument('-i', '--input', type=str, 
                       default="你好，我想和你聊天",
                       help='用户输入消息')
    parser.add_argument('--child-id', type=str, 
                       default="test_child_001",
                       help='儿童ID')
    parser.add_argument('--child-name', type=str, 
                       default="小明",
                       help='儿童姓名')
    parser.add_argument('--child-age', type=int, 
                       default=7,
                       help='儿童年龄')
    parser.add_argument('--interactive', action='store_true',
                       help='启动交互模式')
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎈 儿童智能陪伴对话系统 v1.0")
    print("=" * 60)
    
    # 创建聊天机器人实例
    try:
        chatbot = KidsCompanionChatbot()
        print(f"✅ 系统初始化成功")
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return
    
    # 启动对话会话
    print(f"\n🚀 启动对话会话...")
    print(f"   儿童ID: {args.child_id}")
    print(f"   姓名: {args.child_name}")
    print(f"   年龄: {args.child_age}")
    
    start_result = chatbot.start_conversation(
        child_id=args.child_id,
        child_name=args.child_name,
        child_age=args.child_age
    )
    
    if start_result["status"] != "success":
        print(f"❌ 启动会话失败: {start_result.get('message')}")
        return
    
    print(f"\n🤖 助手: {start_result['response']}")
    
    # 交互模式或单次测试
    if args.interactive:
        print("\n" + "=" * 60)
        print("💬 进入交互模式 (输入 'quit' 或 'exit' 退出)")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n👦 你: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', '退出', '再见']:
                    print("\n👋 准备结束对话...")
                    end_result = chatbot.end_conversation(
                        session_summary="用户主动结束对话"
                    )
                    if end_result["status"] == "success":
                        print(f"🤖 助手: {end_result['response']}")
                        print(f"\n📊 对话统计: 共 {end_result['conversation_turns']} 轮对话")
                    break
                
                # 处理用户消息
                chat_result = chatbot.chat(user_input)
                
                if chat_result["status"] == "success":
                    print(f"\n🤖 助手: {chat_result['response']}")
                else:
                    print(f"\n❌ 错误: {chat_result.get('message')}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 检测到中断，正在结束对话...")
                chatbot.end_conversation(session_summary="用户中断对话")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                break
    else:
        # 单次测试模式
        print(f"\n💬 测试消息: {args.input}")
        chat_result = chatbot.chat(args.input)
        
        if chat_result["status"] == "success":
            print(f"\n🤖 助手: {chat_result['response']}")
            print(f"\n📊 对话轮次: {chat_result['conversation_turns']}")
        else:
            print(f"\n❌ 错误: {chat_result.get('message')}")
        
        # 结束会话
        print("\n👋 结束对话会话...")
        end_result = chatbot.end_conversation()
        if end_result["status"] == "success":
            print(f"✅ 会话已结束，共 {end_result['conversation_turns']} 轮对话")
    
    print("\n" + "=" * 60)
    print("👋 感谢使用儿童智能陪伴对话系统！")
    print("=" * 60)


if __name__ == "__main__":
    main()
