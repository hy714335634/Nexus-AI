#!/usr/bin/env python3
"""
代理调用服务 - 管理代理构建和调用
"""

import subprocess
import threading
import time
import uuid
import streamlit as st
from pathlib import Path
from typing import Dict, List, Iterator, Optional
from datetime import datetime
import json
import os
import sys

class AgentService:
    """代理服务类，负责代理的构建和调用"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.active_processes = {}
        self.build_status_cache = {}
        self.log_files = {}  # 存储日志文件路径
        
        # 确保日志目录存在
        self.logs_dir = self.project_root / "logs" / "web_builds"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 添加项目根目录到Python路径
        sys.path.insert(0, str(self.project_root))
    
    def start_build_workflow(self, user_input: str, project_name: str = None, task_id: str = None) -> Dict:
        """启动代理构建工作流"""
        
        if not task_id:
            task_id = str(uuid.uuid4())
        
        try:
            # 构建工作流脚本路径
            workflow_script = self.project_root / "agents" / "system_agents" / "agent_build_workflow" / "agent_build_workflow.py"
            
            if not workflow_script.exists():
                raise FileNotFoundError(f"工作流脚本不存在: {workflow_script}")
            
            # 准备命令
            cmd = [
                sys.executable, 
                str(workflow_script),
                "-i", user_input
            ]
            
            # 启动子进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root),
                env=os.environ.copy()
            )
            
            # 保存进程信息
            self.active_processes[task_id] = {
                'process': process,
                'start_time': datetime.now(),
                'user_input': user_input,
                'project_name': project_name,
                'status': 'running'
            }
            
            # 启动监控线程
            monitor_thread = threading.Thread(
                target=self._monitor_build_process,
                args=(task_id, process),
                daemon=True
            )
            monitor_thread.start()
            
            return {
                'task_id': task_id,
                'status': 'started',
                'start_time': datetime.now().isoformat(),
                'message': '构建工作流已启动'
            }
            
        except Exception as e:
            st.error(f"启动构建工作流失败: {str(e)}")
            raise

    def stream_build_workflow(self, user_input: str, project_name: str = None, task_id: str = None) -> Iterator[str]:
        """流式启动代理构建工作流，实时输出日志"""
        
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # 创建日志文件
        log_filename = f"build_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file_path = self.logs_dir / log_filename
        self.log_files[task_id] = log_file_path
        
        try:
            # 构建工作流脚本路径
            workflow_script = self.project_root / "agents" / "system_agents" / "agent_build_workflow" / "agent_build_workflow.py"
            
            if not workflow_script.exists():
                error_msg = f"❌ 错误: 工作流脚本不存在: {workflow_script}"
                self._write_to_log_file(task_id, error_msg)
                yield error_msg
                return
            
            # 准备环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root)
            
            # 准备命令
            cmd = [
                sys.executable, 
                str(workflow_script),
                "-i", user_input
            ]
            
            # 输出启动信息
            startup_info = [
                f"🚀 启动构建工作流",
                f"📁 工作目录: {self.project_root}",
                f"🐍 Python: {sys.executable}",
                f"📜 工作流脚本: {workflow_script}",
                f"📝 用户输入: {user_input[:100]}...",
                f"📄 日志文件: {log_file_path}",
                f"{'='*60}"
            ]
            
            for info in startup_info:
                self._write_to_log_file(task_id, info)
                yield info
            
            # 启动子进程
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 合并stderr到stdout
                    text=True,
                    cwd=str(self.project_root),
                    env=env,
                    bufsize=0,  # 无缓冲
                    universal_newlines=True
                )
            except Exception as e:
                error_msg = f"❌ 启动进程失败: {str(e)}"
                self._write_to_log_file(task_id, error_msg)
                yield error_msg
                return
            
            # 保存进程信息
            self.active_processes[task_id] = {
                'process': process,
                'start_time': datetime.now(),
                'user_input': user_input,
                'project_name': project_name,
                'status': 'running',
                'log_file': log_file_path
            }
            
            # 流式读取输出
            while True:
                output = process.stdout.readline()
                
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    line = output.strip()
                    if line:
                        # 写入日志文件
                        self._write_to_log_file(task_id, line)
                        yield line
            
            # 检查返回码
            return_code = process.poll()
            completion_info = [
                f"{'='*60}",
                f"✅ 构建工作流完成，返回码: {return_code}"
            ]
            
            if return_code != 0:
                completion_info.append(f"❌ 构建工作流异常退出，返回码: {return_code}")
            else:
                # 构建成功，刷新项目状态
                completion_info.append(f"🔄 刷新项目状态...")
                try:
                    self._refresh_projects_status()
                    completion_info.append(f"✅ 项目状态已刷新")
                except Exception as e:
                    completion_info.append(f"⚠️ 刷新项目状态失败: {str(e)}")
            
            for info in completion_info:
                self._write_to_log_file(task_id, info)
                yield info
            
            # 清理进程信息
            if task_id in self.active_processes:
                del self.active_processes[task_id]
                
        except Exception as e:
            error_msg = f"❌ 构建工作流执行失败: {str(e)}"
            self._write_to_log_file(task_id, error_msg)
            yield error_msg
    
    def _monitor_build_process(self, task_id: str, process: subprocess.Popen):
        """监控构建进程"""
        try:
            # 实时读取输出
            logs = []
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    log_entry = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'level': 'INFO',
                        'message': output.strip()
                    }
                    logs.append(log_entry)
                    
                    # 写入日志文件
                    self._write_to_log_file(task_id, output.strip())
                    
                    # 更新构建状态缓存 - 只保留最近的1000条日志用于web显示
                    display_logs = logs[-10000:] if len(logs) > 10000 else logs
                    self._update_build_status(task_id, {
                        'status': 'running',
                        'logs': display_logs,
                        'total_log_count': len(logs),
                        'current_stage': self._parse_current_stage(output),
                        'elapsed_time': self._calculate_elapsed_time(task_id)
                    })
            
            # 进程结束，获取返回码
            return_code = process.poll()
            
            completion_msg = f"构建完成，返回码: {return_code}"
            self._write_to_log_file(task_id, completion_msg)
            
            if return_code == 0:
                # 构建成功
                display_logs = logs[-1000:] if len(logs) > 1000 else logs
                self._update_build_status(task_id, {
                    'status': 'completed',
                    'logs': display_logs,
                    'total_log_count': len(logs),
                    'completion_time': datetime.now().isoformat()
                })
            else:
                # 构建失败
                stderr_output = process.stderr.read() if process.stderr else ""
                error_msg = f"构建失败，错误信息: {stderr_output}"
                self._write_to_log_file(task_id, error_msg)
                
                display_logs = logs[-1000:] if len(logs) > 1000 else logs
                self._update_build_status(task_id, {
                    'status': 'failed',
                    'logs': display_logs,
                    'total_log_count': len(logs),
                    'error_message': stderr_output,
                    'completion_time': datetime.now().isoformat()
                })
            
            # 清理进程信息
            if task_id in self.active_processes:
                del self.active_processes[task_id]
                
        except Exception as e:
            error_msg = f"监控构建进程失败: {str(e)}"
            st.error(error_msg)
            self._write_to_log_file(task_id, error_msg)
            self._update_build_status(task_id, {
                'status': 'failed',
                'error_message': str(e)
            })
    
    def _parse_current_stage(self, output: str) -> int:
        """解析当前构建阶段"""
        # 根据输出内容判断当前阶段
        if "需求分析" in output or "requirements_analyzer" in output:
            return 1
        elif "系统架构" in output or "system_architect" in output:
            return 2
        elif "Agent设计" in output or "agent_designer" in output:
            return 3
        elif "提示词工程" in output or "prompt_engineer" in output:
            return 4
        elif "工具开发" in output or "tool_developer" in output:
            return 5
        elif "代码开发" in output or "agent_code_developer" in output:
            return 6
        elif "部署测试" in output or "deployment" in output:
            return 7
        else:
            return 1  # 默认第一阶段
    
    def _calculate_elapsed_time(self, task_id: str) -> str:
        """计算已用时间"""
        if task_id in self.active_processes:
            start_time = self.active_processes[task_id]['start_time']
            elapsed = datetime.now() - start_time
            minutes = int(elapsed.total_seconds() / 60)
            seconds = int(elapsed.total_seconds() % 60)
            return f"{minutes}分{seconds}秒"
        return "未知"
    
    def _write_to_log_file(self, task_id: str, message: str):
        """写入日志到文件"""
        try:
            if task_id in self.log_files:
                log_file_path = self.log_files[task_id]
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()  # 确保立即写入
        except Exception as e:
            print(f"写入日志文件失败: {str(e)}")
    
    def _update_build_status(self, task_id: str, status_update: Dict):
        """更新构建状态缓存"""
        if task_id not in self.build_status_cache:
            self.build_status_cache[task_id] = {}
        
        self.build_status_cache[task_id].update(status_update)
        self.build_status_cache[task_id]['last_updated'] = datetime.now().isoformat()
        
        # 添加日志文件路径信息
        if task_id in self.log_files:
            self.build_status_cache[task_id]['log_file_path'] = str(self.log_files[task_id])
    
    def get_build_status(self, task_id: str) -> Dict:
        """获取构建状态"""
        if task_id in self.build_status_cache:
            status = self.build_status_cache[task_id].copy()
            
            # 生成7阶段状态
            current_stage = status.get('current_stage', 1)
            stages = []
            
            stage_names = [
                "需求分析", "系统架构", "Agent设计", "提示词工程", 
                "工具开发", "代码开发", "部署测试"
            ]
            
            for i, name in enumerate(stage_names, 1):
                if i < current_stage:
                    stage_status = "completed"
                elif i == current_stage:
                    stage_status = "current"
                else:
                    stage_status = "pending"
                
                stages.append({
                    "name": name,
                    "status": stage_status,
                    "duration": "3分钟" if stage_status == "completed" else ("进行中" if stage_status == "current" else "等待中")
                })
            
            status['stages'] = stages
            
            # 添加当前工作详情
            if status.get('status') == 'running':
                status['current_work'] = {
                    'agent_name': f"{stage_names[current_stage-1]}Agent",
                    'details': f"正在执行{stage_names[current_stage-1]}阶段的工作...",
                    'reusable_resources': [
                        {
                            'name': '文本分类器v2.1',
                            'description': '现有Agent组件',
                            'compatibility': 85
                        },
                        {
                            'name': '报告模板生成器',
                            'description': '现有工具',
                            'compatibility': 92
                        }
                    ]
                }
            
            return status
        else:
            return {
                'status': 'not_found',
                'message': '未找到构建任务'
            }
    
    def get_full_logs(self, task_id: str) -> str:
        """获取完整日志内容"""
        try:
            if task_id in self.log_files:
                log_file_path = self.log_files[task_id]
                if log_file_path.exists():
                    with open(log_file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            return "日志文件不存在或已被清理"
        except Exception as e:
            return f"读取日志文件失败: {str(e)}"
    
    def get_log_file_info(self, task_id: str) -> Dict:
        """获取日志文件信息"""
        try:
            if task_id in self.log_files:
                log_file_path = self.log_files[task_id]
                if log_file_path.exists():
                    stat = log_file_path.stat()
                    return {
                        'path': str(log_file_path),
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'exists': True
                    }
            return {'exists': False, 'message': '日志文件不存在'}
        except Exception as e:
            return {'exists': False, 'error': str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = 7):
        """清理旧的日志文件"""
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            cleaned_count = 0
            
            for log_file in self.logs_dir.glob("build_*.log"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            
            return {'cleaned_count': cleaned_count, 'message': f'清理了 {cleaned_count} 个旧日志文件'}
        except Exception as e:
            return {'error': str(e)}
    
    def call_agent(self, agent_id: str, user_input: str) -> Iterator[str]:
        """调用生成的代理"""
        # 创建代理调用日志文件
        call_id = str(uuid.uuid4())[:8]
        log_filename = f"agent_call_{agent_id}_{call_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_file_path = self.logs_dir / log_filename
        
        def write_log(message: str):
            """写入日志到文件"""
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(log_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()
            except Exception as e:
                print(f"写入代理调用日志失败: {str(e)}")
        
        try:
            # 构建正确的代理路径 - 使用agent_id构建路径
            agent_path = self.project_root / "agents" / "generated_agents" / agent_id / f"{agent_id}.py"
            
            if not agent_path.exists():
                error_msg = f"❌ 错误: 代理脚本不存在: {agent_path}"
                write_log(error_msg)
                yield error_msg
                return
            
            # 检查文件是否可读
            if not agent_path.is_file():
                error_msg = f"❌ 错误: 路径不是文件: {agent_path}"
                write_log(error_msg)
                yield error_msg
                return
            
            # 检查文件大小
            file_size = agent_path.stat().st_size
            size_msg = f"📄 代理脚本大小: {file_size} 字节"
            write_log(size_msg)
            yield size_msg
            
            # 准备环境变量，确保Python路径正确
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root)
            
            # 检测代理的参数格式
            input_param = self._detect_agent_input_parameter(agent_path)
            
            # 准备命令 - 使用虚拟环境的Python
            venv_python = self.project_root / "venv" / "bin" / "python"
            
            if venv_python.exists():
                # 使用虚拟环境的Python
                cmd = [str(venv_python), str(agent_path), input_param, user_input]
            else:
                # 使用系统Python
                cmd = [sys.executable, str(agent_path), input_param, user_input]
            
            # 启动进程，设置正确的工作目录和环境变量
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # 合并stderr到stdout
                    text=True,
                    cwd=str(self.project_root),  # 设置工作目录为项目根目录
                    env=env,  # 传递包含PYTHONPATH的环境变量
                    bufsize=0,  # 无缓冲，确保实时输出
                    universal_newlines=True
                )
            except Exception as e:
                error_msg = f"❌ 启动进程失败: {str(e)}"
                write_log(error_msg)
                yield error_msg
                return
            
            # 首先输出启动信息
            startup_info = [
                f"🚀 启动代理: {agent_id}",
                f"📁 工作目录: {self.project_root}",
                f"🐍 Python路径: {cmd[0]}",
                f"📜 代理脚本: {agent_path}",
                f"⚙️ 参数: {input_param} '{user_input}'",
                f"📄 日志文件: {log_file_path}",
                f"{'='*50}"
            ]
            
            for info in startup_info:
                write_log(info)
                yield info
            
            # 流式读取输出，保存所有日志
            while True:
                output = process.stdout.readline()
                
                if output == '' and process.poll() is not None:
                    break
                
                if output:
                    line = output.strip()
                    if line:  # 只输出非空行
                        write_log(line)
                        yield line
            
            # 检查返回码
            return_code = process.poll()
            completion_info = [
                f"{'='*50}",
                f"✅ 进程完成，返回码: {return_code}"
            ]
            
            if return_code != 0:
                completion_info.append(f"❌ 进程异常退出，返回码: {return_code}")
            
            for info in completion_info:
                write_log(info)
                yield info
            
        except Exception as e:
            error_msg = f"调用代理失败: {str(e)}"
            write_log(error_msg)
            yield error_msg
    
    # 已移除 _should_filter_agent_output 方法，现在直接输出所有日志
    
    def _detect_agent_input_parameter(self, agent_path: Path) -> str:
        """检测代理脚本使用的输入参数格式"""
        try:
            with open(agent_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查常见的参数格式
            if "add_argument('-i'" in content or "add_argument('--input'" in content:
                return "-i"
            elif "add_argument('-d'" in content or "add_argument('--data'" in content:
                return "-d"
            elif "add_argument('-m'" in content or "add_argument('--message'" in content:
                return "-m"
            elif "add_argument('-t'" in content or "add_argument('--text'" in content:
                return "-t"
            else:
                # 默认尝试 -i（大多数生成的代理使用这个格式）
                return "-i"
        except Exception:
            # 如果检测失败，使用默认值
            return "-i"
    
    def terminate_process(self, task_id: str):
        """终止构建进程"""
        try:
            if task_id in self.active_processes:
                process = self.active_processes[task_id]['process']
                process.terminate()
                
                # 等待进程结束
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                # 更新状态
                self._update_build_status(task_id, {
                    'status': 'terminated',
                    'termination_time': datetime.now().isoformat()
                })
                
                # 清理进程信息
                del self.active_processes[task_id]
                
                return True
            else:
                return False
                
        except Exception as e:
            st.error(f"终止进程失败: {str(e)}")
            return False
    
    def _refresh_projects_status(self):
        """刷新项目状态文件"""
        try:
            from web.services.data_service import DataService
            data_service = DataService()
            
            # 强制刷新项目数据
            success = data_service.refresh_projects_from_agents()
            
            if success:
                # 清除Streamlit缓存，确保UI能看到最新数据
                if hasattr(st, 'cache_data'):
                    st.cache_data.clear()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"刷新项目状态失败: {str(e)}")
            return False
    
    def list_available_agents(self) -> List[Dict]:
        """列出可用的代理"""
        try:
            agents = []
            generated_agents_dir = self.project_root / "agents" / "generated_agents"
            
            if generated_agents_dir.exists():
                for agent_dir in generated_agents_dir.iterdir():
                    if agent_dir.is_dir():
                        # 查找主脚本
                        main_script = None
                        for possible_name in [f"{agent_dir.name}.py", "main.py", "agent.py"]:
                            possible_script = agent_dir / possible_name
                            if possible_script.exists():
                                main_script = possible_script
                                break
                        
                        if main_script:
                            agents.append({
                                'name': agent_dir.name.replace('_', ' ').title(),
                                'path': str(agent_dir.relative_to(self.project_root)),
                                'script': str(main_script.relative_to(self.project_root)),
                                'created_at': datetime.fromtimestamp(agent_dir.stat().st_ctime).isoformat()
                            })
            
            return agents
            
        except Exception as e:
            st.error(f"列出代理失败: {str(e)}")
            return []