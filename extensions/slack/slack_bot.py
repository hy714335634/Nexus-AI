"""
Slack Bot 核心模块

提供 Slack 消息监听、处理和响应功能。
支持并发处理多个用户请求。
"""

import os
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .agent_router import AgentRouter

logger = logging.getLogger(__name__)


class SlackBot:
    """
    Slack Bot 主类
    
    功能:
    - Slack 消息监听和处理
    - Agent 路由集成
    - 并发请求处理
    - 命令处理
    - 错误处理和日志记录
    """
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        app_token: Optional[str] = None,
        config_path: Optional[str] = None,
        max_workers: int = 5
    ):
        """
        初始化 Slack Bot
        
        参数:
            bot_token: Slack Bot User OAuth Token (xoxb-)
            app_token: Slack App-Level Token (xapp-)
            config_path: Agent 配置文件路径
            max_workers: 最大并发处理线程数
        """
        # 从环境变量或参数获取 Token
        self.bot_token = bot_token or os.getenv("SLACK_BOT_TOKEN")
        self.app_token = app_token or os.getenv("SLACK_APP_TOKEN")
        
        if not self.bot_token or not self.app_token:
            raise ValueError(
                "缺少必需的 Token。请设置环境变量 SLACK_BOT_TOKEN 和 SLACK_APP_TOKEN，"
                "或在初始化时传入参数。"
            )
        
        # 初始化 Slack App
        self.app = App(token=self.bot_token)
        
        # 初始化 Agent Router
        self.router = AgentRouter(config_path)
        
        # 初始化线程池用于并发处理
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 注册事件处理器
        self._register_handlers()
        
        logger.info(f"SlackBot 初始化完成（最大并发: {max_workers}）")
    
    def _process_request(self, user_input: str, user: str, say, event_logger, thread_ts: Optional[str] = None):
        """
        在后台线程中处理用户请求
        
        参数:
            user_input: 用户输入
            user: 用户 ID
            say: Slack say 函数
            event_logger: 事件日志记录器
            thread_ts: Thread 时间戳（如果在 thread 中）
        """
        try:
            event_logger.info(f"开始处理来自 {user} 的请求")
            
            # 通过 Router 调用 Agent，返回字符串
            response = self.router.call_agent(user_input)
            
            # 添加免责声明
            disclaimer = self.router.get_disclaimer()
            if disclaimer:
                response += f"\n\n_{disclaimer}_"
            
            # 回复消息（如果在 thread 中则回复到 thread）
            if thread_ts:
                say(text=f"<@{user}> {response}", thread_ts=thread_ts)
            else:
                say(f"<@{user}> {response}")
            
            event_logger.info(f"已完成来自 {user} 的请求")
            
        except Exception as e:
            event_logger.error(f"处理来自 {user} 的请求时出错: {e}", exc_info=True)
            if thread_ts:
                say(text=f"<@{user}> ❌ 抱歉，处理你的请求时出现错误: {str(e)}", thread_ts=thread_ts)
            else:
                say(f"<@{user}> ❌ 抱歉，处理你的请求时出现错误: {str(e)}")
    
    def _register_handlers(self):
        """注册 Slack 事件处理器"""
        
        @self.app.event("app_mention")
        def handle_mention(event, say, logger):
            """处理 @mention 消息（异步）"""
            try:
                text = event.get('text', '')
                user = event.get('user')
                thread_ts = event.get('thread_ts')  # 获取 thread 时间戳
                
                # 移除 @机器人 部分，获取用户实际输入
                user_input = text.split('>', 1)[-1].strip()
                
                logger.info(f"收到来自 {user} 的查询: {user_input}")
                
                # 处理特殊命令（同步处理）
                if self._handle_command(user_input, say, user, thread_ts):
                    return
                
                # 提交到线程池异步处理
                self.executor.submit(
                    self._process_request,
                    user_input,
                    user,
                    say,
                    logger,
                    thread_ts  # 传递 thread_ts
                )
                
                logger.info(f"已提交来自 {user} 的请求到处理队列")
                
            except Exception as e:
                logger.error(f"处理消息时出错: {e}", exc_info=True)
                say(f"<@{user}> ❌ 抱歉，处理你的请求时出现错误: {str(e)}")
    
    def _handle_command(self, user_input: str, say, user: str = None, thread_ts: Optional[str] = None) -> bool:
        """
        处理特殊命令
        
        参数:
            user_input: 用户输入
            say: Slack say 函数
            user: 用户 ID（可选）
            thread_ts: Thread 时间戳（可选）
            
        返回:
            如果是命令则返回 True，否则返回 False
        """
        command = user_input.lower().strip()
        
        # 帮助命令
        if command in ['help', '帮助', 'agents', '列表']:
            response = self.router.list_agents()
            response += "\n\n💡 使用方法:\n"
            response += "   @nexus-ai-agent 你的问题"
            if user:
                msg = f"<@{user}> {response}"
            else:
                msg = response
            
            if thread_ts:
                say(text=msg, thread_ts=thread_ts)
            else:
                say(msg)
            return True
        
        # 清除缓存命令
        if command in ['clear', 'clear cache', '清除缓存']:
            self.router.clear_cache()
            msg = "✅ Agent 缓存已清除"
            if user:
                msg = f"<@{user}> {msg}"
            
            if thread_ts:
                say(text=msg, thread_ts=thread_ts)
            else:
                say(msg)
            return True
        
        return False
    
    def start(self):
        """启动 Slack Bot 服务"""
        logger.info("=" * 60)
        logger.info("🤖 Nexus-AI Slack Bot 启动中...")
        logger.info("=" * 60)
        
        # 显示已加载的 Agent
        logger.info("\n📋 已配置的 Agent:")
        for i, agent in enumerate(self.router.agents_config, 1):
            default_mark = " (默认)" if agent['name'] == self.router.default_agent_name else ""
            
            # 检查 prompt 是否存在
            prompt_path = self.router._find_prompt_path(agent['name'])
            status = "✅" if prompt_path else "❌"
            
            logger.info(f"   {status} {i}. {agent['name']}{default_mark}")
            logger.info(f"      {agent.get('description', '无描述')}")
            if prompt_path:
                logger.info(f"      Prompt: {prompt_path}")
        
        logger.info("\n✅ 已连接到 Slack")
        logger.info("📡 等待 @mention 消息...")
        logger.info("🔄 支持并发处理多个请求")
        logger.info("\n💡 使用方法:")
        logger.info("   @nexus-ai-agent 你的问题")
        logger.info("   @nexus-ai-agent help  (查看可用 Agent)")
        logger.info("\n按 Ctrl+C 停止服务")
        logger.info("=" * 60)
        
        try:
            # 使用 Socket Mode 启动（不需要公网 URL）
            handler = SocketModeHandler(self.app, self.app_token)
            handler.start()
        except KeyboardInterrupt:
            logger.info("\n\n👋 正在关闭服务...")
            self.executor.shutdown(wait=True)
            logger.info("服务已停止")
        except Exception as e:
            logger.error(f"\n❌ 错误: {e}", exc_info=True)
            self.executor.shutdown(wait=False)
            raise
