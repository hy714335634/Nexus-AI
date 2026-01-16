"""
Slack Bot 启动脚本

使用方法:
    python -m extensions.slack.main
    
或:
    python extensions/slack/main.py
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from extensions.slack import SlackBot


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/slack_bot.log', encoding='utf-8')
        ]
    )


def main():
    """主函数"""
    # 配置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 创建并启动 Slack Bot
        bot = SlackBot()
        bot.start()
        
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.info("\n请设置环境变量:")
        logger.info("export SLACK_BOT_TOKEN='xoxb-your-token'")
        logger.info("export SLACK_APP_TOKEN='xapp-your-token'")
        logger.info("\n获取 Token:")
        logger.info("1. 访问: https://api.slack.com/apps")
        logger.info("2. 选择你的 App")
        logger.info("3. Bot Token: OAuth & Permissions → Bot User OAuth Token")
        logger.info("4. App Token: Socket Mode → App-Level Token")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"启动失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
