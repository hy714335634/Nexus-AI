#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务管理器 - 管理 Nexus-AI 的所有后台服务

功能:
  - 启动/停止/重启 API 服务 (FastAPI)
  - 启动/停止/重启 Worker 服务 (SQS 消费者)
  - 启动/停止/重启 Web 前端服务 (Next.js)
  - 查看服务状态
  - 查看服务日志
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ServiceType(str, Enum):
    """服务类型枚举"""
    API = "api"
    WORKER = "worker"
    WEB = "web"


class ServiceStatus(str, Enum):
    """服务状态枚举"""
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """服务信息数据类"""
    name: str
    status: ServiceStatus
    pid: Optional[int] = None
    port: Optional[int] = None
    uptime: Optional[str] = None
    log_file: Optional[str] = None


class ServiceManager:
    """
    服务管理器
    
    管理 Nexus-AI 的所有后台服务，包括 API、Worker 和 Web 前端。
    """
    
    def __init__(self, base_path: str = "."):
        """
        初始化服务管理器
        
        Args:
            base_path: 项目根目录路径
        """
        self.base_path = Path(base_path).resolve()
        self.log_dir = self.base_path / "logs"
        self.pid_dir = self.base_path / ".pids"
        self.venv_dir = self.base_path / ".venv"
        
        # 默认端口配置
        self.api_port = int(os.environ.get("API_PORT", "8000"))
        self.web_port = int(os.environ.get("WEB_PORT", "3000"))
        
        # 运行模式: dev 或 prod
        self.run_mode = os.environ.get("RUN_MODE", "prod")
        
        # 确保目录存在
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保必要的目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_pid_file(self, service: ServiceType) -> Path:
        """获取服务的 PID 文件路径"""
        return self.pid_dir / f"{service.value}.pid"
    
    def _get_log_file(self, service: ServiceType) -> Path:
        """获取服务的日志文件路径"""
        return self.log_dir / f"{service.value}.log"
    
    def _read_pid(self, service: ServiceType) -> Optional[int]:
        """读取服务的 PID"""
        pid_file = self._get_pid_file(service)
        if pid_file.exists():
            try:
                return int(pid_file.read_text().strip())
            except (ValueError, IOError):
                return None
        return None
    
    def _write_pid(self, service: ServiceType, pid: int):
        """写入服务的 PID"""
        pid_file = self._get_pid_file(service)
        pid_file.write_text(str(pid))
    
    def _remove_pid(self, service: ServiceType):
        """删除服务的 PID 文件"""
        pid_file = self._get_pid_file(service)
        if pid_file.exists():
            pid_file.unlink()
    
    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否在运行"""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def _check_port(self, port: int) -> Optional[int]:
        """
        检查端口是否被占用
        
        Returns:
            占用端口的进程 PID，如果端口空闲则返回 None
        """
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except Exception:
            pass
        return None
    
    def _kill_process(self, pid: int, force: bool = False) -> bool:
        """
        终止进程
        
        Args:
            pid: 进程 ID
            force: 是否强制终止 (SIGKILL)
        
        Returns:
            是否成功终止
        """
        try:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            
            # 等待进程退出
            for _ in range(10):
                if not self._is_process_running(pid):
                    return True
                time.sleep(0.5)
            
            # 如果还没退出且不是强制模式，尝试强制终止
            if not force and self._is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            
            return not self._is_process_running(pid)
        except (OSError, ProcessLookupError):
            return True
    
    def _get_venv_python(self) -> str:
        """获取虚拟环境的 Python 路径"""
        return str(self.venv_dir / "bin" / "python")
    
    def _get_venv_activate(self) -> str:
        """获取虚拟环境激活脚本路径"""
        return str(self.venv_dir / "bin" / "activate")
    
    def _add_log_separator(self, service: ServiceType):
        """在日志文件中添加启动分隔符"""
        log_file = self._get_log_file(service)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        separator = f"\n========== Service started {timestamp} ==========\n"
        with open(log_file, "a") as f:
            f.write(separator)
    
    def check_venv(self) -> bool:
        """检查虚拟环境是否存在"""
        return self.venv_dir.exists() and (self.venv_dir / "bin" / "python").exists()
    
    def get_status(self, service: ServiceType) -> ServiceInfo:
        """
        获取服务状态
        
        Args:
            service: 服务类型
        
        Returns:
            服务信息
        """
        pid = self._read_pid(service)
        port = None
        
        if service == ServiceType.API:
            port = self.api_port
        elif service == ServiceType.WEB:
            port = self.web_port
        
        if pid and self._is_process_running(pid):
            return ServiceInfo(
                name=service.value,
                status=ServiceStatus.RUNNING,
                pid=pid,
                port=port,
                log_file=str(self._get_log_file(service))
            )
        else:
            # 清理无效的 PID 文件
            if pid:
                self._remove_pid(service)
            return ServiceInfo(
                name=service.value,
                status=ServiceStatus.STOPPED,
                port=port,
                log_file=str(self._get_log_file(service))
            )
    
    def get_all_status(self) -> List[ServiceInfo]:
        """获取所有服务的状态"""
        return [
            self.get_status(ServiceType.API),
            self.get_status(ServiceType.WORKER),
            self.get_status(ServiceType.WEB),
        ]
    
    def start_api(self) -> Tuple[bool, str]:
        """
        启动 API 服务
        
        Returns:
            (是否成功, 消息)
        """
        # 检查虚拟环境
        if not self.check_venv():
            return False, f"Virtual environment not found: {self.venv_dir}"
        
        # 检查是否已运行
        status = self.get_status(ServiceType.API)
        if status.status == ServiceStatus.RUNNING:
            return True, f"API service is already running (PID: {status.pid})"
        
        # 检查端口
        port_pid = self._check_port(self.api_port)
        if port_pid:
            self._kill_process(port_pid)
            time.sleep(1)
        
        # 添加日志分隔符
        self._add_log_separator(ServiceType.API)
        
        # 设置环境变量
        env = os.environ.copy()
        env["AWS_REGION"] = env.get("AWS_REGION", "us-west-2")
        env["LOG_LEVEL"] = env.get("LOG_LEVEL", "INFO")
        env["PYTHONUNBUFFERED"] = "1"
        
        # 启动服务
        log_file = open(self._get_log_file(ServiceType.API), "a")
        
        process = subprocess.Popen(
            [
                self._get_venv_python(), "-m", "uvicorn",
                "api.v2.main:app",
                "--host", "0.0.0.0",
                "--port", str(self.api_port),
                "--log-level", "info"
            ],
            cwd=str(self.base_path),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        # 等待启动
        time.sleep(3)
        
        if self._is_process_running(process.pid):
            self._write_pid(ServiceType.API, process.pid)
            return True, f"API service started (PID: {process.pid}, Port: {self.api_port})"
        else:
            return False, f"API service failed to start. Check log: {self._get_log_file(ServiceType.API)}"
    
    def start_worker(self) -> Tuple[bool, str]:
        """
        启动 Worker 服务
        
        Returns:
            (是否成功, 消息)
        """
        # 检查虚拟环境
        if not self.check_venv():
            return False, f"Virtual environment not found: {self.venv_dir}"
        
        # 检查是否已运行
        status = self.get_status(ServiceType.WORKER)
        if status.status == ServiceStatus.RUNNING:
            return True, f"Worker service is already running (PID: {status.pid})"
        
        # 添加日志分隔符
        self._add_log_separator(ServiceType.WORKER)
        
        # 设置环境变量
        env = os.environ.copy()
        env["AWS_REGION"] = env.get("AWS_REGION", "us-west-2")
        env["LOG_LEVEL"] = env.get("LOG_LEVEL", "INFO")
        env["PYTHONUNBUFFERED"] = "1"
        
        # 启动服务
        log_file = open(self._get_log_file(ServiceType.WORKER), "a")
        
        process = subprocess.Popen(
            [
                self._get_venv_python(), "-m", "worker.main",
                "--queue", "build"
            ],
            cwd=str(self.base_path),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        # 等待启动
        time.sleep(2)
        
        if self._is_process_running(process.pid):
            self._write_pid(ServiceType.WORKER, process.pid)
            return True, f"Worker service started (PID: {process.pid})"
        else:
            return False, f"Worker service failed to start. Check log: {self._get_log_file(ServiceType.WORKER)}"
    
    def start_web(self, force_build: bool = False) -> Tuple[bool, str]:
        """
        启动 Web 前端服务
        
        Args:
            force_build: 是否强制重新编译
        
        Returns:
            (是否成功, 消息)
        """
        web_dir = self.base_path / "web"
        
        # 检查 web 目录
        if not web_dir.exists():
            return False, f"Web directory not found: {web_dir}"
        
        # 检查是否已运行
        status = self.get_status(ServiceType.WEB)
        if status.status == ServiceStatus.RUNNING:
            return True, f"Web service is already running (PID: {status.pid})"
        
        # 检查端口
        port_pid = self._check_port(self.web_port)
        if port_pid:
            self._kill_process(port_pid)
            time.sleep(1)
        
        # 检查 node_modules
        if not (web_dir / "node_modules").exists():
            return False, "Node modules not installed. Run 'npm install' in web directory first."
        
        # 添加日志分隔符
        self._add_log_separator(ServiceType.WEB)
        
        # 设置环境变量
        env = os.environ.copy()
        env["NEXT_PUBLIC_API_URL"] = env.get("NEXT_PUBLIC_API_URL", f"http://localhost:{self.api_port}")
        env["PORT"] = str(self.web_port)
        env["HOSTNAME"] = "0.0.0.0"
        
        log_file = open(self._get_log_file(ServiceType.WEB), "a")
        
        if self.run_mode == "prod":
            # 生产模式：检查是否需要编译
            build_id_file = web_dir / ".next" / "BUILD_ID"
            
            if force_build or not build_id_file.exists():
                # 需要编译
                log_file.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Building frontend...\n")
                log_file.flush()
                
                build_result = subprocess.run(
                    ["npm", "run", "build"],
                    cwd=str(web_dir),
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT
                )
                
                if build_result.returncode != 0:
                    return False, f"Frontend build failed. Check log: {self._get_log_file(ServiceType.WEB)}"
            
            # 启动生产服务
            process = subprocess.Popen(
                ["npm", "run", "start"],
                cwd=str(web_dir),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        else:
            # 开发模式
            process = subprocess.Popen(
                ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", str(self.web_port)],
                cwd=str(web_dir),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # 等待启动
        time.sleep(5)
        
        if self._is_process_running(process.pid):
            self._write_pid(ServiceType.WEB, process.pid)
            return True, f"Web service started (PID: {process.pid}, Port: {self.web_port}, Mode: {self.run_mode})"
        else:
            return False, f"Web service failed to start. Check log: {self._get_log_file(ServiceType.WEB)}"
    
    def stop_service(self, service: ServiceType) -> Tuple[bool, str]:
        """
        停止指定服务
        
        Args:
            service: 服务类型
        
        Returns:
            (是否成功, 消息)
        """
        status = self.get_status(service)
        
        if status.status == ServiceStatus.STOPPED:
            return True, f"{service.value} service is not running"
        
        if status.pid:
            if self._kill_process(status.pid):
                self._remove_pid(service)
                return True, f"{service.value} service stopped (PID: {status.pid})"
            else:
                # 尝试强制终止
                if self._kill_process(status.pid, force=True):
                    self._remove_pid(service)
                    return True, f"{service.value} service force stopped (PID: {status.pid})"
                return False, f"Failed to stop {service.value} service"
        
        return False, f"No PID found for {service.value} service"
    
    def start_all(self, force_build: bool = False) -> List[Tuple[str, bool, str]]:
        """
        启动所有服务
        
        Args:
            force_build: 是否强制重新编译前端
        
        Returns:
            [(服务名, 是否成功, 消息), ...]
        """
        results = []
        
        # 启动 API
        success, msg = self.start_api()
        results.append(("api", success, msg))
        
        # 启动 Worker
        success, msg = self.start_worker()
        results.append(("worker", success, msg))
        
        # 启动 Web
        success, msg = self.start_web(force_build)
        results.append(("web", success, msg))
        
        return results
    
    def stop_all(self) -> List[Tuple[str, bool, str]]:
        """
        停止所有服务
        
        Returns:
            [(服务名, 是否成功, 消息), ...]
        """
        results = []
        
        # 按相反顺序停止
        for service in [ServiceType.WEB, ServiceType.WORKER, ServiceType.API]:
            success, msg = self.stop_service(service)
            results.append((service.value, success, msg))
        
        # 清理可能残留的进程
        self._cleanup_orphan_processes()
        
        return results
    
    def restart_all(self, force_build: bool = False) -> List[Tuple[str, bool, str]]:
        """
        重启所有服务
        
        Args:
            force_build: 是否强制重新编译前端
        
        Returns:
            [(服务名, 是否成功, 消息), ...]
        """
        stop_results = self.stop_all()
        time.sleep(2)
        start_results = self.start_all(force_build)
        
        # 合并结果
        results = []
        for service_name, _, _ in stop_results:
            # 找到对应的启动结果
            for s_name, success, msg in start_results:
                if s_name == service_name:
                    results.append((service_name, success, msg))
                    break
        
        return results
    
    def _cleanup_orphan_processes(self):
        """清理可能残留的孤儿进程"""
        patterns = [
            "uvicorn api.v2.main:app",
            "python -m worker.main",
            "next dev",
            "next start"
        ]
        
        for pattern in patterns:
            try:
                subprocess.run(
                    ["pkill", "-f", pattern],
                    capture_output=True
                )
            except Exception:
                pass
    
    def get_logs(self, service: Optional[ServiceType] = None, lines: int = 50) -> Dict[str, str]:
        """
        获取服务日志
        
        Args:
            service: 服务类型，None 表示所有服务
            lines: 返回的日志行数
        
        Returns:
            {服务名: 日志内容}
        """
        logs = {}
        
        services = [service] if service else [ServiceType.API, ServiceType.WORKER, ServiceType.WEB]
        
        for svc in services:
            log_file = self._get_log_file(svc)
            if log_file.exists():
                try:
                    result = subprocess.run(
                        ["tail", "-n", str(lines), str(log_file)],
                        capture_output=True,
                        text=True
                    )
                    logs[svc.value] = result.stdout
                except Exception as e:
                    logs[svc.value] = f"Error reading log: {e}"
            else:
                logs[svc.value] = "Log file not found"
        
        return logs
    
    def get_access_urls(self) -> Dict[str, str]:
        """获取服务访问地址"""
        return {
            "web": f"http://localhost:{self.web_port}",
            "api": f"http://localhost:{self.api_port}",
            "api_docs": f"http://localhost:{self.api_port}/docs",
            "health": f"http://localhost:{self.api_port}/health",
        }
