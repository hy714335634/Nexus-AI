"""
Nexus-AI Slack Extension

企业级 Slack 集成模块，提供智能 Agent 路由和消息处理能力。
"""

__version__ = "1.0.0"
__author__ = "Nexus-AI Team"

from .agent_router import AgentRouter
from .slack_bot import SlackBot

__all__ = ["AgentRouter", "SlackBot"]
