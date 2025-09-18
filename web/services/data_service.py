#!/usr/bin/env python3
"""
数据服务层 - 管理项目状态数据和文件系统交互
"""

import json
import os
import streamlit as st
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import uuid

class DataService:
    """数据服务类，负责项目状态数据的管理"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.projects_file = self.project_root / "web" / "data" / "projects_status.json"
        self.sessions_dir = self.project_root / "web" / "data" / "sessions"
        self.cache_ttl = 60  # 缓存60秒
        
        # 确保数据目录存在
        self.projects_file.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化项目状态文件
        self._init_projects_file()
    
    def _init_projects_file(self):
        """初始化项目状态文件"""
        if not self.projects_file.exists():
            initial_data = {
                "projects": [],
                "last_updated": datetime.now().isoformat(),
                "total_projects": 0,
                "active_projects": 0,
                "system_metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 62.1,
                    "disk_usage": 78.5
                }
            }
            self._save_projects_data(initial_data)
    
    @st.cache_data(ttl=60)
    def get_projects_status(_self) -> Dict:
        """获取项目状态数据（带缓存）"""
        try:
            if _self.projects_file.exists():
                with open(_self.projects_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 同步扫描generated_agents目录
                _self._sync_with_generated_agents(data)
                return data
            else:
                return _self._get_default_data()
        except Exception as e:
            st.error(f"读取项目数据失败: {str(e)}")
            return _self._get_default_data()
    
    def _get_default_data(self) -> Dict:
        """获取默认数据结构"""
        return {
            "projects": [],
            "last_updated": datetime.now().isoformat(),
            "total_projects": 0,
            "active_projects": 0,
            "system_metrics": {
                "cpu_usage": 45.2,
                "memory_usage": 62.1,
                "disk_usage": 78.5
            }
        }
    
    def _sync_with_generated_agents(self, data: Dict):
        """同步扫描generated_agents目录"""
        try:
            generated_agents_dir = self.project_root / "agents" / "generated_agents"
            
            if generated_agents_dir.exists():
                # 使用agent_path作为唯一标识符，而不是project id
                existing_agent_paths = {p.get('agent_path', '') for p in data.get('projects', [])}
                
                # 扫描目录中的代理
                for agent_dir in generated_agents_dir.iterdir():
                    if agent_dir.is_dir() and not agent_dir.name.startswith('.'):
                        agent_path = str(agent_dir.relative_to(self.project_root))
                        
                        # 如果这个代理路径不存在，创建新的项目记录
                        if agent_path not in existing_agent_paths:
                            project_data = self._create_project_from_agent_dir(agent_dir)
                            data['projects'].append(project_data)
                
                # 更新统计信息
                data['total_projects'] = len(data['projects'])
                data['active_projects'] = len([p for p in data['projects'] if p.get('status') == 'running'])
                data['last_updated'] = datetime.now().isoformat()
                
                # 保存更新后的数据
                self._save_projects_data(data)
        
        except Exception as e:
            st.warning(f"同步代理目录失败: {str(e)}")
    
    def _create_project_from_agent_dir(self, agent_dir: Path) -> Dict:
        """从代理目录创建项目数据"""
        # 尝试从代理目录中读取更多信息
        agent_info = self._extract_agent_info(agent_dir)
        
        return {
            "id": agent_dir.name,  # 使用目录名作为ID，保持一致性
            "name": agent_info.get('name', agent_dir.name.replace('_', ' ').title()),
            "description": agent_info.get('description', f"基于{agent_dir.name}的AI代理系统"),
            "status": "running",
            "created_at": agent_info.get('created_at', datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "build_time": agent_info.get('build_time', "未知"),
            "version": agent_info.get('version', "v1.0"),
            "agent_path": str(agent_dir.relative_to(self.project_root)),
            "agents": agent_info.get('agents', []),
            "metrics": {
                "total_calls": 0,
                "success_rate": 100.0,
                "avg_response_time": "2.3s",
                "last_call": None
            },
            "build_history": agent_info.get('build_history', [])
        }
    
    def _extract_agent_info(self, agent_dir: Path) -> Dict:
        """从代理目录中提取信息"""
        info = {}
        
        try:
            # 检查是否有配置文件或README
            config_files = [
                agent_dir / "config.yaml",
                agent_dir / "agent_config.json",
                agent_dir / "README.md"
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    if config_file.suffix == '.yaml':
                        import yaml
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data = yaml.safe_load(f)
                            if config_data:
                                info.update(config_data)
                    elif config_file.suffix == '.json':
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                            if config_data:
                                info.update(config_data)
                    elif config_file.name == 'README.md':
                        # 从README中提取描述
                        with open(config_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            lines = content.split('\n')
                            if lines:
                                # 使用第一行作为描述（去掉markdown标记）
                                first_line = lines[0].strip().lstrip('#').strip()
                                if first_line:
                                    info['description'] = first_line
                    break
            
            # 检查代理文件的修改时间
            agent_files = list(agent_dir.glob("*.py"))
            if agent_files:
                # 使用最新修改的文件时间作为创建时间
                latest_mtime = max(f.stat().st_mtime for f in agent_files)
                info['created_at'] = datetime.fromtimestamp(latest_mtime).isoformat()
        
        except Exception as e:
            # 如果提取信息失败，返回空字典
            pass
        
        return info
    
    def _save_projects_data(self, data: Dict):
        """保存项目数据到文件"""
        try:
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"保存项目数据失败: {str(e)}")
    
    def update_project_status(self, project_id: str, status_update: Dict):
        """更新项目状态"""
        try:
            data = self.get_projects_status()
            
            # 查找并更新项目
            for project in data['projects']:
                if project['id'] == project_id:
                    project.update(status_update)
                    project['updated_at'] = datetime.now().isoformat()
                    break
            
            # 更新统计信息
            data['active_projects'] = len([p for p in data['projects'] if p.get('status') == 'running'])
            data['last_updated'] = datetime.now().isoformat()
            
            self._save_projects_data(data)
            
            # 清除缓存
            st.cache_data.clear()
            
        except Exception as e:
            st.error(f"更新项目状态失败: {str(e)}")
    
    def add_new_project(self, project_data: Dict) -> str:
        """添加新项目"""
        try:
            data = self.get_projects_status()
            
            # 生成项目ID
            project_id = str(uuid.uuid4())
            project_data['id'] = project_id
            project_data['created_at'] = datetime.now().isoformat()
            project_data['updated_at'] = datetime.now().isoformat()
            
            # 添加到项目列表
            data['projects'].append(project_data)
            
            # 更新统计信息
            data['total_projects'] = len(data['projects'])
            data['active_projects'] = len([p for p in data['projects'] if p.get('status') == 'running'])
            data['last_updated'] = datetime.now().isoformat()
            
            self._save_projects_data(data)
            
            # 清除缓存
            st.cache_data.clear()
            
            return project_id
            
        except Exception as e:
            st.error(f"添加项目失败: {str(e)}")
            return None
    
    def get_project_by_id(self, project_id: str) -> Optional[Dict]:
        """根据ID获取项目"""
        data = self.get_projects_status()
        return next((p for p in data['projects'] if p['id'] == project_id), None)
    
    def update_agent_metrics(self, agent_id: str, metrics_update: Dict):
        """更新代理性能指标"""
        try:
            data = self.get_projects_status()
            
            for project in data['projects']:
                if project['id'] == agent_id:
                    if 'metrics' not in project:
                        project['metrics'] = {}
                    
                    project['metrics'].update(metrics_update)
                    project['updated_at'] = datetime.now().isoformat()
                    break
            
            self._save_projects_data(data)
            st.cache_data.clear()
            
        except Exception as e:
            st.error(f"更新代理指标失败: {str(e)}")
    
    def get_build_logs(self, project_id: str) -> List[str]:
        """获取构建日志"""
        try:
            # 这里应该从实际的日志文件中读取
            logs_dir = self.project_root / "logs"
            log_file = logs_dir / f"{project_id}.log"
            
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    return f.readlines()
            else:
                return ["暂无日志记录"]
                
        except Exception as e:
            st.error(f"读取日志失败: {str(e)}")
            return [f"日志读取错误: {str(e)}"]
    
    def save_chat_session(self, agent_id: str, session_data: Dict):
        """保存聊天会话数据"""
        try:
            session_file = self.sessions_dir / f"{agent_id}_chat.json"
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            st.error(f"保存会话数据失败: {str(e)}")
    
    def load_chat_session(self, agent_id: str) -> Dict:
        """加载聊天会话数据"""
        try:
            session_file = self.sessions_dir / f"{agent_id}_chat.json"
            
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"chat_history": [], "session_id": str(uuid.uuid4())}
                
        except Exception as e:
            st.error(f"加载会话数据失败: {str(e)}")
            return {"chat_history": [], "session_id": str(uuid.uuid4())}
    
    def scan_generated_agents(self) -> List[Dict]:
        """扫描generated_agents目录，返回所有发现的代理信息"""
        agents = []
        
        try:
            generated_agents_dir = self.project_root / "agents" / "generated_agents"
            
            if generated_agents_dir.exists():
                for agent_dir in generated_agents_dir.iterdir():
                    if agent_dir.is_dir() and not agent_dir.name.startswith('.'):
                        agent_info = {
                            "name": agent_dir.name,
                            "path": str(agent_dir.relative_to(self.project_root)),
                            "full_path": str(agent_dir),
                            "exists": True,
                            "files": []
                        }
                        
                        # 扫描代理文件
                        try:
                            for file_path in agent_dir.iterdir():
                                if file_path.is_file():
                                    agent_info["files"].append({
                                        "name": file_path.name,
                                        "size": file_path.stat().st_size,
                                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                                    })
                        except Exception:
                            pass
                        
                        agents.append(agent_info)
        
        except Exception as e:
            st.error(f"扫描代理目录失败: {str(e)}")
        
        return agents
    
    def refresh_projects_from_agents(self):
        """强制刷新项目数据，从generated_agents目录重新扫描"""
        try:
            # 清除缓存
            st.cache_data.clear()
            
            # 获取当前数据
            data = self._get_default_data()
            
            # 如果文件存在，读取现有数据
            if self.projects_file.exists():
                with open(self.projects_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # 保留系统指标
                    data['system_metrics'] = existing_data.get('system_metrics', data['system_metrics'])
            
            # 强制同步代理目录
            self._sync_with_generated_agents(data)
            
            return True
            
        except Exception as e:
            st.error(f"刷新项目数据失败: {str(e)}")
            return False