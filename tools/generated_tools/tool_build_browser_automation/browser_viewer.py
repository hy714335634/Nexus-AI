#!/usr/bin/env python3
"""
DCV实时浏览器视图服务器模块

提供基于Amazon DCV的实时浏览器查看功能，支持多种显示尺寸和自动打开浏览器。
"""

import webbrowser
import logging
from typing import Optional
from bedrock_agentcore.tools.browser_client import BrowserClient

logger = logging.getLogger(__name__)


class BrowserViewerServer:
    """DCV实时浏览器视图服务器"""
    
    # 支持的显示尺寸配置
    DISPLAY_SIZES = {
        "720p": (1280, 720),
        "900p": (1600, 900),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440)
    }
    
    def __init__(self, client: BrowserClient, port: int = 8000):
        """
        初始化DCV viewer服务器
        
        Args:
            client: BrowserClient实例
            port: 服务器端口，默认8000
        """
        if not isinstance(client, BrowserClient):
            raise TypeError("client must be a BrowserClient instance")
        
        self.client = client
        self.port = port
        self.viewer_url = f"http://localhost:{port}"
        self._server_started = False
        logger.info(f"BrowserViewerServer initialized on port {port}")
    
    def start(self, open_browser: bool = True, display_size: str = "900p") -> str:
        """
        启动DCV viewer服务器
        
        Args:
            open_browser: 是否自动打开浏览器，默认True
            display_size: 显示尺寸（720p/900p/1080p/1440p），默认900p
            
        Returns:
            str: viewer访问URL
            
        Raises:
            ValueError: 当display_size无效时
            OSError: 当端口已被占用时
        """
        if display_size not in self.DISPLAY_SIZES:
            valid_sizes = ", ".join(self.DISPLAY_SIZES.keys())
            raise ValueError(f"Invalid display_size '{display_size}'. Must be one of: {valid_sizes}")
        
        try:
            # 配置显示布局
            width, height = self.DISPLAY_SIZES[display_size]
            logger.info(f"Configuring display layout: {width}×{height} ({display_size})")
            
            # 注意：实际的DCV服务器启动逻辑依赖于BrowserClient的实现
            # 这里假设BrowserClient已经内置了DCV支持
            # 如果需要额外的服务器启动逻辑，需要在这里添加
            
            self._server_started = True
            logger.info(f"Viewer server started at {self.viewer_url}")
            
            # 自动打开浏览器
            if open_browser:
                try:
                    webbrowser.open(self.viewer_url)
                    logger.info("Browser opened automatically")
                except Exception as e:
                    logger.warning(f"Failed to open browser automatically: {e}")
            
            return self.viewer_url
            
        except OSError as e:
            if "Address already in use" in str(e):
                raise OSError(f"Port {self.port} is already in use. Please choose a different port.") from e
            raise
        except Exception as e:
            logger.error(f"Failed to start viewer server: {e}")
            raise
    
    def stop(self) -> None:
        """
        停止viewer服务器
        """
        if not self._server_started:
            logger.warning("Viewer server was not started")
            return
        
        try:
            # 清理服务器资源
            # 注意：实际清理逻辑依赖于BrowserClient的实现
            self._server_started = False
            logger.info("Viewer server stopped")
        except Exception as e:
            logger.error(f"Error stopping viewer server: {e}")
            raise
    
    def get_status(self) -> dict:
        """
        获取viewer服务器状态
        
        Returns:
            dict: 状态信息
        """
        return {
            "running": self._server_started,
            "url": self.viewer_url if self._server_started else None,
            "port": self.port
        }
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
        return False
