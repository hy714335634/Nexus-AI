#!/usr/bin/env python3
"""
Nexus AI Worker Service

监听 SQS 队列并处理构建任务

使用方法:
    python -m worker.main [--queue build|deploy] [--once]

参数:
    --queue: 监听的队列类型 (build/deploy)，默认 build
    --once: 只处理一条消息后退出（用于测试）
"""
import argparse
import logging
import signal
import sys
import time
import threading
from typing import Optional

# 添加项目根目录到路径
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.v2.database import sqs_client
from worker.config import worker_settings
from worker.handlers import BuildHandler
from worker.handlers.workflow_handler import WorkflowHandler

# 配置日志
logging.basicConfig(
    level=getattr(logging, worker_settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Worker:
    """Worker 服务主类"""
    
    def __init__(self, queue_type: str = "build"):
        self.queue_type = queue_type
        self.worker_id = worker_settings.WORKER_ID
        self.running = False
        self._shutdown_event = threading.Event()
        
        # 根据队列类型选择队列名称和处理器
        if queue_type == "build":
            self.queue_name = worker_settings.SQS_BUILD_QUEUE_NAME
            # 使用统一的 WorkflowHandler 处理所有工作流类型
            self.handler = WorkflowHandler()
            self.visibility_timeout = worker_settings.VISIBILITY_TIMEOUT
        elif queue_type == "deploy":
            self.queue_name = worker_settings.SQS_DEPLOY_QUEUE_NAME
            self.handler = None  # TODO: 实现 DeployHandler
            self.visibility_timeout = 600
        else:
            raise ValueError(f"Unknown queue type: {queue_type}")
        
        logger.info(f"Worker {self.worker_id} initialized for {queue_type} queue")
    
    def start(self, once: bool = False):
        """
        启动 Worker
        
        Args:
            once: 是否只处理一条消息后退出
        """
        self.running = True
        logger.info(f"Worker {self.worker_id} starting...")
        logger.info(f"Listening to queue: {self.queue_name}")
        logger.info(f"Poll interval: {worker_settings.POLL_INTERVAL_SECONDS}s")
        logger.info(f"Visibility timeout: {self.visibility_timeout}s")
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        poll_count = 0
        
        try:
            while self.running and not self._shutdown_event.is_set():
                poll_count += 1
                logger.debug(f"Poll cycle #{poll_count}")
                
                self._poll_and_process()
                
                if once:
                    logger.info("--once flag set, exiting after first poll")
                    break
                
                # 等待一段时间再轮询（使用 shutdown_event 以便能快速响应停止信号）
                if not self._shutdown_event.is_set():
                    self._shutdown_event.wait(timeout=1)  # 短暂等待，因为 receive_messages 已经有长轮询
        
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        
        finally:
            self.running = False
            logger.info(f"Worker {self.worker_id} stopped after {poll_count} poll cycles")
    
    def stop(self):
        """停止 Worker"""
        logger.info(f"Stopping worker {self.worker_id}...")
        self.running = False
        self._shutdown_event.set()
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        if self._shutdown_event.is_set():
            # 第二次收到信号，强制退出
            logger.warning("Received second signal, forcing exit...")
            sys.exit(1)
        
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        logger.info("Press Ctrl+C again to force exit")
        self.stop()
    
    def _poll_and_process(self):
        """轮询并处理消息"""
        try:
            logger.debug(f"Polling queue {self.queue_name}...")
            
            # 从队列接收消息
            messages = sqs_client.receive_messages(
                queue_name=self.queue_name,
                max_messages=worker_settings.MAX_MESSAGES_PER_POLL,
                wait_time_seconds=worker_settings.POLL_INTERVAL_SECONDS,
                visibility_timeout=self.visibility_timeout
            )
            
            if not messages:
                logger.debug("No messages received, continuing to poll...")
                return
            
            logger.info(f"Received {len(messages)} message(s)")
            
            for message in messages:
                if not self.running:
                    logger.info("Worker stopping, skipping remaining messages")
                    break
                self._process_message(message)
        
        except Exception as e:
            logger.error(f"Error polling messages: {e}", exc_info=True)
            time.sleep(5)  # 出错后等待一段时间
    
    def _process_message(self, message: dict):
        """处理单条消息"""
        message_id = message.get('message_id')
        receipt_handle = message.get('receipt_handle')
        
        logger.info(f"Processing message {message_id}")
        
        heartbeat_thread = None
        
        try:
            # 启动心跳线程（延长可见性超时）
            heartbeat_thread = self._start_heartbeat(receipt_handle)
            
            # 处理消息
            if self.handler:
                success = self.handler.handle(message)
            else:
                logger.warning(f"No handler for queue type {self.queue_type}")
                success = False
            
            if success:
                # 删除消息（确认处理完成）
                sqs_client.delete_message(self.queue_name, receipt_handle)
                logger.info(f"Message {message_id} processed successfully")
            else:
                # 处理失败，消息会在可见性超时后重新可见
                logger.warning(f"Message {message_id} processing failed, will retry")
        
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}", exc_info=True)
        
        finally:
            # 停止心跳线程
            if heartbeat_thread:
                heartbeat_thread.cancel()
            logger.debug(f"Finished processing message {message_id}")
    
    def _start_heartbeat(self, receipt_handle: str) -> Optional[threading.Timer]:
        """
        启动心跳线程
        
        定期延长消息的可见性超时，防止长时间任务超时
        """
        heartbeat_stop = threading.Event()
        
        def heartbeat():
            while not heartbeat_stop.is_set() and self.running:
                try:
                    sqs_client.change_message_visibility(
                        self.queue_name,
                        receipt_handle,
                        self.visibility_timeout
                    )
                    logger.debug("Heartbeat: extended message visibility")
                except Exception as e:
                    logger.warning(f"Heartbeat failed: {e}")
                    break
                
                # 等待下一次心跳，但可以被中断
                heartbeat_stop.wait(timeout=worker_settings.HEARTBEAT_INTERVAL)
        
        # 创建一个包装类来管理心跳线程
        class HeartbeatThread:
            def __init__(self, stop_event: threading.Event, thread: threading.Thread):
                self.stop_event = stop_event
                self.thread = thread
            
            def cancel(self):
                self.stop_event.set()
                # 不等待线程结束，让它自然退出
        
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        
        return HeartbeatThread(heartbeat_stop, thread)


def main():
    parser = argparse.ArgumentParser(description='Nexus AI Worker Service')
    parser.add_argument(
        '--queue',
        type=str,
        default='build',
        choices=['build', 'deploy'],
        help='Queue type to listen (default: build)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Process only one message and exit'
    )
    
    args = parser.parse_args()
    
    worker = Worker(queue_type=args.queue)
    worker.start(once=args.once)


if __name__ == '__main__':
    main()
