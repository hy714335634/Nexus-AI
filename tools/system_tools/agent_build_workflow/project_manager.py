#!/usr/bin/env python3
# project_manager/project_init - 根据项目名称在 projects/ 下创建完整的项目目录结构，自动生成 config.yaml, README.md, status.yaml 文件，创建 agents/, tools/, prompts/ 子目录
# project_manager/update_project_config - 根据项目名称创建或更新项目配置文件，支持自定义描述和版本号，保留现有配置
# project_manager/get_project_config - 获取指定项目的配置信息，返回JSON格式的完整配置数据和文件元信息
# project_manager/update_project_readme - 根据项目配置和状态自动生成 README.md，包含项目描述、目录结构、各Agent阶段进度，支持添加额外内容
# project_manager/get_project_readme - 获取指定项目的README.md内容，返回完整内容和文件统计信息
# project_manager/update_project_status - 更新 status.yaml 中的阶段状态，支持6个标准阶段，自动创建Agent条目和所有阶段结构，支持agent_artifact_path数组字段
# project_manager/get_project_status - 查询项目状态信息，支持查询所有Agent、指定Agent或指定阶段，返回详细的状态信息和制品路径摘要
# project_manager/update_agent_artifact_path - 专门更新指定阶段的agent_artifact_path字段，支持prompt_engineer、tools_developer、agent_code_developer阶段
# project_manager/get_agent_artifact_paths - 获取指定Agent的制品路径信息，支持查询所有阶段或特定阶段的制品路径
# project_manager/update_project_stage_content - 将内容写入 projects/<project_name>/<agent_name>/<stage_name>.json，自动创建必要的目录结构
# project_manager/get_project_stage_content - 读取指定阶段文件的内容，返回文件内容和元数据信息
# project_manager/list_project_agents - 列出指定项目中的所有Agent目录，包含文件统计和阶段文件信息
# project_manager/list_all_projects - 列出所有项目，包含项目配置信息和Agent数量统计
# project_manager/generate_content - 根据类型生成内容文件，支持agent、prompt、tool三种类型，分别输出到对应的generated目录
"""
项目管理工具

提供项目初始化、配置管理、状态跟踪等功能，支持多Agent项目的完整生命周期管理
"""

import os
import json
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Literal
from pathlib import Path

from strands import Agent,tool


def _enhance_content_with_context(content: str, project_name: str, agent_name: str, stage_name: str) -> str:
    """
    为内容添加项目和Agent上下文信息
    
    Args:
        content (str): 原始内容
        project_name (str): 项目名称
        agent_name (str): Agent名称
        stage_name (str): 阶段名称
        
    Returns:
        str: 增强后的内容
    """
    # 创建上下文头部信息
    context_header = f"""# 项目上下文信息

**项目名称**: {project_name}
**Agent名称**: {agent_name}  
**开发阶段**: {stage_name}
**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

"""
    
    # 如果内容已经包含上下文信息，则不重复添加
    if f"**项目名称**: {project_name}" in content:
        return content
    
    # 添加上下文头部到内容前面
    return context_header + content

# @tool
# def set_current_project_stats(action: str, agent: Agent):
#     """设置项目基本信息"""
#     action_count = agent.state.get("action_count") or 0

#     # Update state
#     agent.state.set("action_count", action_count + 1)
#     agent.state.set("last_action", action)

#     return f"Action '{action}' recorded. Total actions: {action_count + 1}"

# @tool
# def get_current_project_stats(agent: Agent):
#     """获取当前项目基本信息"""
#     action_count = agent.state.get("action_count") or 0
#     last_action = agent.state.get("last_action") or "none"

#     return f"Actions performed: {action_count}, Last action: {last_action}"


@tool
def project_init(project_name: str) -> str:
    """
    根据项目名称初始化项目目录结构
    
    Args:
        project_name (str): 项目名称，将作为目录名使用
        
    Returns:
        str: 操作结果信息，包含创建的目录结构
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        # 清理项目名称，移除不安全字符
        project_name = project_name.strip()
        if "/" in project_name or "\\" in project_name or ".." in project_name:
            return "错误：项目名称不能包含路径分隔符或相对路径"
        
        # 创建项目根目录
        project_root = os.path.join("projects", project_name)
        
        # 检查项目是否已存在
        if os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 已存在"
        
        # 创建目录结构
        directories = [
            project_root,
            os.path.join(project_root, "agents")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # 创建基础文件
        files_created = []
        
        # 创建 config.yaml
        config_path = os.path.join(project_root, "config.yaml")
        config_content = {
            "project": {
                "name": project_name,
                "description": f"AI智能体项目：{project_name}",
                "version": "1.0.0",
                "created_date": datetime.now(timezone.utc).isoformat()
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f, default_flow_style=False, allow_unicode=True, indent=2)
        files_created.append("config.yaml")
        
        # 创建 README.md
        readme_path = os.path.join(project_root, "README.md")
        readme_content = f"""# {project_name}

## 项目描述
AI智能体项目：{project_name}

## 平台目录结构
```
nexus-ai/
├── agents/                    # 智能体实现
│   ├── system_agents/         # 核心平台智能体
│   ├── template_agents/       # 可复用智能体模板 —— 后续Agent代码开发需要参考模版文件
│   └── generated_agents/      # 动态创建的智能体 —— 后续开发的Agent代码应存储在此目录
├── prompts/                   # YAML提示词模板
│   ├── system_agents_prompts/ # 系统智能体提示词
│   ├── template_prompts/      # 模板提示词 —— 后续Agent提示词开发需要参考模版文件
│   └── generated_agents_prompts/ # 生成的提示词 —— 后续开发的Agent提示词应存储在此目录
├── tools/                     # 工具实现
│   ├── system_tools/          # 核心平台工具
│   ├── template_tools/        # 工具模板  —— 后续Agent工具开发需要参考模版文件
│   └── generated_tools/       # 生成的工具 —— 后续开发的Agent工具应存储在此目录
├── projects/                  # 用户项目目录  —— Agent开发过程文件及项目管理文件存储在对应项目目录中
│   └── <project_name>/
│       ├── agents/
│       │   └── <agent_name>/
        │       ├── requirements_analyzer.json       #需求分析师输出文档
        │       ├── system_architect.json            #Agent系统架构师输出文档
        │       ├── agent_designer.json              #agent设计师输出文档
        │       ├── prompt_engineer.json             #提示词工程师输出文档
        │       ├── tools_developer.json             #工具开发者输出文档
        │       ├── agent_code_developer.json        #agent代码开发工程师输出文档
        │       └── agent_developer_manager.json     #项目开发审核结果
│       ├── config.yaml          # 项目基本配置
│       ├── README.md            # 项目说明
│       └── status.yaml          # 项目需求文档和进度追踪
└── utils/                     # 共享工具

## Agent开发阶段

### 阶段说明
1. **requirements_analyzer**: 需求分析阶段
2. **system_architect**: 系统架构设计阶段
3. **agent_designer**: Agent设计阶段
4. **prompt_engineer**: 提示词工程阶段
5. **tools_developer**: 工具开发阶段
6. **agent_code_developer**: Agent代码开发阶段
7. **agent_developer_manager**: Agent开发管理阶段

### 各Agent阶段结果
项目状态和各阶段结果将在开发过程中更新到此文档。

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        files_created.append("README.md")
        
        # 创建 status.yaml
        status_path = os.path.join(project_root, "status.yaml")
        status_content = {
            "project_info": [
                {
                    "name": project_name,
                    "description": f"AI智能体项目：{project_name}",
                    "version": "1.0.0",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "progress": [
                        {
                            "total": 0,
                            "completed": 0
                        }
                    ],
                    "agents": []
                }
            ]
        }
        
        with open(status_path, 'w', encoding='utf-8') as f:
            yaml.dump(status_content, f, default_flow_style=False, allow_unicode=True, indent=2)
        files_created.append("status.yaml")
        
        # 返回成功信息
        result = {
            "status": "success",
            "message": f"项目 '{project_name}' 初始化成功",
            "project_path": project_root,
            "directories_created": [
                "agents/"
            ],
            "files_created": files_created,
            "created_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限创建项目目录 {project_root}"
    except OSError as e:
        return f"错误：文件系统操作失败: {str(e)}"
    except Exception as e:
        return f"项目初始化时出现错误: {str(e)}"


@tool
def update_project_config(project_name: str, description: str = None, version: str = None) -> str:
    """
    根据项目名称创建或更新项目配置文件
    
    Args:
        project_name (str): 项目名称
        description (str, optional): 项目描述，如果不提供则使用默认描述
        version (str, optional): 项目版本，如果不提供则使用默认版本
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在，请先使用 project_init 初始化项目"
        
        config_path = os.path.join(project_root, "config.yaml")
        
        # 读取现有配置（如果存在）
        existing_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                return f"错误：无法解析现有配置文件: {str(e)}"
        
        # 准备新配置
        config_content = {
            "project": {
                "name": project_name,
                "description": description or existing_config.get("project", {}).get("description", f"AI智能体项目：{project_name}"),
                "version": version or existing_config.get("project", {}).get("version", "1.0.0"),
                "created_date": existing_config.get("project", {}).get("created_date", datetime.now(timezone.utc).isoformat()),
                "updated_date": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # 保留其他现有配置
        for key, value in existing_config.items():
            if key != "project":
                config_content[key] = value
        
        # 写入配置文件
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_content, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        result = {
            "status": "success",
            "message": f"项目 '{project_name}' 配置更新成功",
            "config_path": config_path,
            "config": config_content["project"],
            "updated_date": config_content["project"]["updated_date"]
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入配置文件"
    except Exception as e:
        return f"更新项目配置时出现错误: {str(e)}"


@tool
def update_project_readme(project_name: str, additional_content: str = None) -> str:
    """
    根据项目名称创建或更新项目README.md文件
    
    Args:
        project_name (str): 项目名称
        additional_content (str, optional): 额外要添加的内容
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在，请先使用 project_init 初始化项目"
        
        # 读取项目配置以获取描述
        config_path = os.path.join(project_root, "config.yaml")
        project_description = f"AI智能体项目：{project_name}"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    project_description = config.get("project", {}).get("description", project_description)
            except yaml.YAMLError:
                pass  # 使用默认描述
        
        # 读取项目状态以生成阶段结果
        status_path = os.path.join(project_root, "status.yaml")
        agents_status = []
        
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r', encoding='utf-8') as f:
                    status = yaml.safe_load(f) or {}
                    # 兼容新格式
                    if "project_info" in status and isinstance(status["project_info"], list):
                        for project in status["project_info"]:
                            if project.get("name") == project_name:
                                agents_status = project.get("agents", [])
                                break
                    else:
                        # 兼容旧格式
                        agents_status = status.get("project", [])
            except yaml.YAMLError:
                pass  # 使用空列表
        
        # 生成README内容
        readme_content = f"""# {project_name}

## 项目描述
{project_description}

## 项目结构
```
{project_name}/
├── agents/          # Agent实现文件
├── config.yaml      # 项目配置文件
├── README.md        # 项目说明文档
└── status.yaml      # 项目状态跟踪文件
```

## Agent开发阶段

### 阶段说明
1. **requirements_analyzer**: 需求分析阶段
2. **system_architect**: 系统架构设计阶段
3. **agent_designer**: Agent设计阶段
4. **prompt_engineer**: 提示词工程阶段
5. **tools_developer**: 工具开发阶段
6. **agent_code_developer**: Agent代码开发阶段
7. **agent_developer_manager**: Agent开发管理阶段

### 各Agent阶段结果
"""
        
        # 添加各Agent的状态信息
        if agents_status:
            for agent in agents_status:
                agent_name = agent.get("name", "未知Agent")
                readme_content += f"\n#### {agent_name}\n"
                
                pipeline = agent.get("pipeline", [])
                for stage_entry in pipeline:
                    if isinstance(stage_entry, dict) and "stage" in stage_entry:
                        # 新格式
                        stage_name = stage_entry.get("stage", "")
                        stage_status = "✅ 已完成" if stage_entry.get("status", False) else "⏳ 待完成"
                        doc_path = stage_entry.get("doc_path", "")
                        readme_content += f"- **{stage_name}**: {stage_status}"
                        if doc_path:
                            readme_content += f" - [文档]({doc_path})"
                        readme_content += "\n"
                    else:
                        # 兼容旧格式
                        for stage_name, stage_info in stage_entry.items():
                            if isinstance(stage_info, dict):
                                status = "✅ 已完成" if stage_info.get("status", False) else "⏳ 待完成"
                                doc_path = stage_info.get("doc_path", "")
                                readme_content += f"- **{stage_name}**: {status}"
                                if doc_path:
                                    readme_content += f" - [文档]({doc_path})"
                                readme_content += "\n"
                            else:
                                status = "✅ 已完成" if stage_info else "⏳ 待完成"
                                readme_content += f"- **{stage_name}**: {status}\n"
        else:
            readme_content += "\n项目状态和各阶段结果将在开发过程中更新到此文档。\n"
        
        # 添加额外内容
        if additional_content:
            readme_content += f"\n## 附加信息\n{additional_content}\n"
        
        readme_content += f"""
## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
        
        # 写入README文件
        readme_path = os.path.join(project_root, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        result = {
            "status": "success",
            "message": f"项目 '{project_name}' README.md 更新成功",
            "readme_path": readme_path,
            "content_length": len(readme_content),
            "agents_count": len(agents_status),
            "updated_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入README文件"
    except Exception as e:
        return f"更新项目README时出现错误: {str(e)}"


@tool
def update_project_status(project_name: str, agent_name: str, stage: str, status: bool, doc_path: str = "", agent_artifact_path: List[str] = None) -> str:
    """
    更新项目状态文件中指定Agent的指定阶段状态
    
    Args:
        project_name (str): 项目名称（必须）
        agent_name (str): Agent名称（必须）
        stage (str): 阶段名称（必须） - requirements_analyzer, system_architect, agent_designer, prompt_engineer, tools_developer, agent_code_developer, agent_developer_manager
        status (bool): 阶段状态（必须） - True表示完成，False表示未完成
        doc_path (str, optional): 文档路径
        agent_artifact_path (List[str], optional): 制品路径数组，用于prompt_engineer、tools_developer、agent_code_developer阶段
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证必须参数
        if not project_name or not project_name.strip():
            return "错误：项目名称（project_name）是必须参数，不能为空"
        
        if not agent_name or not agent_name.strip():
            return "错误：Agent名称（agent_name）是必须参数，不能为空"
        
        if not stage or not stage.strip():
            return "错误：阶段名称（stage）是必须参数，不能为空"
        
        if status is None:
            return "错误：阶段状态（status）是必须参数，不能为None"
        
        # 验证阶段名称
        valid_stages = [
            "requirements_analyzer", "system_architect", "agent_designer",
            "prompt_engineer", "tools_developer", "agent_code_developer","agent_developer_manager"
        ]
        
        if stage not in valid_stages:
            return f"错误：无效的阶段名称 '{stage}'，有效阶段包括: {', '.join(valid_stages)}"
        
        project_name = project_name.strip()
        agent_name = agent_name.strip()
        stage = stage.strip()
        
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在，请先使用 project_init 初始化项目"
        
        status_path = os.path.join(project_root, "status.yaml")
        
        # 读取项目配置获取项目描述
        config_path = os.path.join(project_root, "config.yaml")
        project_description = f"AI智能体项目：{project_name}"
        project_version = "1.0.0"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    project_config = config.get("project", {})
                    project_description = project_config.get("description", project_description)
                    project_version = project_config.get("version", project_version)
            except yaml.YAMLError:
                pass  # 使用默认值
        
        # 读取现有状态
        status_data = {}
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r', encoding='utf-8') as f:
                    status_data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                return f"错误：无法解析状态文件: {str(e)}"
        
        # 初始化或更新项目信息
        if "project_info" not in status_data:
            status_data["project_info"] = []
        
        # 查找或创建项目条目
        project_entry = None
        for project in status_data["project_info"]:
            if project.get("name") == project_name:
                project_entry = project
                break
        
        if project_entry is None:
            # 创建新的项目条目
            project_entry = {
                "name": project_name,
                "description": project_description,
                "version": project_version,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "progress": [
                    {
                        "total": 0,
                        "completed": 0
                    }
                ],
                "agents": []
            }
            status_data["project_info"].append(project_entry)
        else:
            # 更新项目基本信息
            project_entry["name"] = project_name
            project_entry["description"] = project_description
            project_entry["version"] = project_version
            project_entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # 确保agents字段存在
        if "agents" not in project_entry:
            project_entry["agents"] = []
        
        # 查找或创建Agent条目
        agent_entry = None
        for agent in project_entry["agents"]:
            if agent.get("name") == agent_name:
                agent_entry = agent
                break
        
        if agent_entry is None:
            # 创建新的Agent条目，包含所有阶段
            agent_entry = {
                "name": agent_name,
                "description": f"智能体：{agent_name}",
                "created_date": datetime.now(timezone.utc).isoformat(),
                "pipeline": []
            }
            
            # 初始化所有阶段
            for stage_name in valid_stages:
                stage_entry = {
                    "description": _get_stage_description(stage_name),
                    "doc_path": "",
                    "stage": stage_name,
                    "status": False,
                    "updated_date": None
                }
                agent_entry["pipeline"].append(stage_entry)
            
            project_entry["agents"].append(agent_entry)
        
        # 更新Agent的最后更新时间
        agent_entry["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # 更新指定阶段的状态
        pipeline = agent_entry.get("pipeline", [])
        stage_found = False
        
        for stage_entry in pipeline:
            if stage_entry.get("stage") == stage:
                stage_entry["status"] = status
                stage_entry["doc_path"] = doc_path
                stage_entry["updated_date"] = datetime.now(timezone.utc).isoformat()
                
                # 如果提供了agent_artifact_path，更新制品路径
                artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
                if stage in artifact_stages and agent_artifact_path:
                    stage_entry["agent_artifact_path"] = agent_artifact_path
                
                stage_found = True
                break
        
        # 如果阶段不存在，添加它
        if not stage_found:
            new_stage_entry = {
                "description": _get_stage_description(stage),
                "doc_path": doc_path,
                "stage": stage,
                "status": status,
                "updated_date": datetime.now(timezone.utc).isoformat()
            }
            
            # 如果提供了agent_artifact_path，添加到新阶段
            artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
            if stage in artifact_stages and agent_artifact_path:
                new_stage_entry["agent_artifact_path"] = agent_artifact_path
            
            agent_entry["pipeline"].append(new_stage_entry)
        
        # 计算项目整体进度
        all_agents = project_entry["agents"]
        total_project_stages = 0
        completed_project_stages = 0
        
        for agent in all_agents:
            agent_pipeline = agent.get("pipeline", [])
            for stage_entry in agent_pipeline:
                total_project_stages += 1
                if stage_entry.get("status", False):
                    completed_project_stages += 1
        
        # 更新项目进度
        if "progress" not in project_entry:
            project_entry["progress"] = []
        
        if len(project_entry["progress"]) == 0:
            project_entry["progress"].append({
                "total": total_project_stages,
                "completed": completed_project_stages
            })
        else:
            project_entry["progress"][0] = {
                "total": total_project_stages,
                "completed": completed_project_stages
            }
        
        # 写入状态文件
        with open(status_path, 'w', encoding='utf-8') as f:
            yaml.dump(status_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        result = {
            "status": "success",
            "message": f"项目 '{project_name}' 中 Agent '{agent_name}' 的阶段 '{stage}' 状态更新成功",
            "project_info": {
                "project_name": project_name,
                "project_description": project_description,
                "agent_name": agent_name,
                "stage": stage,
                "new_status": status,
                "doc_path": doc_path,
                "project_progress": project_entry["progress"][0] if project_entry["progress"] else {"total": 0, "completed": 0}
            },
            "updated_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入状态文件"
    except Exception as e:
        return f"更新项目状态时出现错误: {str(e)}"


def _get_stage_description(stage_name: str) -> str:
    """获取阶段描述"""
    stage_descriptions = {
        "requirements_analyzer": "需求分析阶段 - 分析用户需求，定义功能规格",
        "system_architect": "系统架构设计阶段 - 设计系统架构和技术方案",
        "agent_designer": "Agent设计阶段 - 设计智能体结构和交互模式",
        "prompt_engineer": "提示词工程阶段 - 设计和优化提示词模板",
        "tools_developer": "工具开发阶段 - 开发必要的工具和函数",
        "agent_code_developer": "Agent代码开发阶段 - 实现智能体代码",
        "agent_developer_manager": "Agent开发管理阶段 - 管理和协调开发流程"
    }
    return stage_descriptions.get(stage_name, f"阶段：{stage_name}")



@tool
def get_project_status(project_name: str, agent_name: str = None) -> str:
    """
    查询项目状态信息
    
    Args:
        project_name (str): 项目名称（必须）
        agent_name (str, optional): Agent名称，如果不提供则返回指定项目完整status.yaml内容
        
    Returns:
        str: 查询结果信息，如果未指定agent_name则返回完整status.yaml内容，否则返回指定Agent的详细信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        status_path = os.path.join(project_root, "status.yaml")
        
        # 检查状态文件是否存在
        if not os.path.exists(status_path):
            return f"错误：项目 '{project_name}' 的状态文件不存在"
        
        # 读取状态文件
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                status_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            return f"错误：无法解析状态文件: {str(e)}"
        
        # 获取项目信息，兼容新旧格式
        project_info = None
        agents_data = []
        
        if "project_info" in status_data and isinstance(status_data["project_info"], list):
            # 新格式 - project_info 是列表
            for project in status_data["project_info"]:
                if project.get("name") == project_name:
                    project_info = project
                    agents_data = project.get("agents", [])
                    break
        elif "project_info" in status_data and isinstance(status_data["project_info"], dict):
            # 兼容格式 - project_info 是字典
            project_info = status_data["project_info"]
            agents_data = project_info.get("agents", [])
        else:
            # 旧格式兼容
            agents_data = status_data.get("project", [])
        
        if project_info is None:
            project_info = {
                "name": project_name,
                "description": f"AI智能体项目：{project_name}",
                "version": "1.0.0"
            }
        
        # 计算项目整体进度
        total_agents = len(agents_data)
        total_completed_stages = 0
        total_stages = 0
        
        for agent in agents_data:
            pipeline = agent.get("pipeline", [])
            if pipeline and isinstance(pipeline[0], dict) and "stage" in pipeline[0]:
                # 新格式
                for stage_entry in pipeline:
                    total_stages += 1
                    if stage_entry.get("status", False):
                        total_completed_stages += 1
            else:
                # 旧格式兼容
                for stage_entry in pipeline:
                    for stage_name, stage_info in stage_entry.items():
                        total_stages += 1
                        if isinstance(stage_info, dict) and stage_info.get("status", False):
                            total_completed_stages += 1
                        elif stage_info:
                            total_completed_stages += 1
        
        project_progress = {
            "total_agents": total_agents,
            "total_stages": total_stages,
            "completed_stages": total_completed_stages,
            "completion_percentage": round((total_completed_stages / total_stages) * 100, 1) if total_stages > 0 else 0
        }
        
        # 如果没有指定Agent，返回完整的status.yaml内容
        if not agent_name:
            return json.dumps(status_data, ensure_ascii=False, indent=2)
        
        # 查找指定Agent
        agent_name = agent_name.strip()
        target_agent = None
        
        for agent in agents_data:
            if agent.get("name") == agent_name:
                target_agent = agent
                break
        
        if target_agent is None:
            return f"错误：在项目 '{project_name}' 中未找到 Agent '{agent_name}'"
        
        # 分析制品路径信息
        artifact_info = {}
        artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
        
        for stage_entry in target_agent.get("pipeline", []):
            stage_name = stage_entry.get("stage", "")
            if stage_name in artifact_stages and "agent_artifact_path" in stage_entry:
                artifact_paths = stage_entry.get("agent_artifact_path", [])
                if artifact_paths:
                    artifact_info[stage_name] = {
                        "artifact_count": len(artifact_paths),
                        "artifact_paths": artifact_paths,
                        "stage_status": stage_entry.get("status", False)
                    }
        
        # 返回指定Agent的详细信息
        result = {
            "status": "success",
            "project_info": project_info,
            "agent_info": {
                "name": target_agent.get("name", agent_name),
                "description": target_agent.get("description", f"智能体：{agent_name}"),
                "created_date": target_agent.get("created_date", ""),
                "last_updated": target_agent.get("last_updated", "")
            },
            "agent_data": target_agent,
            "artifact_summary": artifact_info,
            "query_date": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "project_name": project_info.get("name", project_name),
                "agent_name": agent_name,
                "total_stages": len(target_agent.get("pipeline", [])),
                "completed_stages": sum(1 for stage in target_agent.get("pipeline", []) if stage.get("status", False)),
                "total_artifacts": sum(len(info["artifact_paths"]) for info in artifact_info.values()),
                "artifact_stages_with_content": len(artifact_info)
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"查询项目状态时出现错误: {str(e)}"


@tool
def get_agent_artifact_paths(project_name: str, agent_name: str, stage: str = None) -> str:
    """
    获取指定Agent的制品路径信息
    
    Args:
        project_name (str): 项目名称（必须）
        agent_name (str): Agent名称（必须）
        stage (str, optional): 阶段名称，如果不提供则返回所有支持制品路径的阶段信息
        
    Returns:
        str: 制品路径信息
    """
    try:
        # 验证必须参数
        if not project_name or not project_name.strip():
            return "错误：项目名称（project_name）是必须参数，不能为空"
        
        if not agent_name or not agent_name.strip():
            return "错误：Agent名称（agent_name）是必须参数，不能为空"
        
        project_name = project_name.strip()
        agent_name = agent_name.strip()
        
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        status_path = os.path.join(project_root, "status.yaml")
        
        # 检查状态文件是否存在
        if not os.path.exists(status_path):
            return f"错误：项目 '{project_name}' 的状态文件不存在"
        
        # 读取状态文件
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                status_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            return f"错误：无法解析状态文件: {str(e)}"
        
        # 查找项目条目
        project_entry = None
        if "project_info" in status_data:
            for project in status_data["project_info"]:
                if project.get("name") == project_name:
                    project_entry = project
                    break
        
        if project_entry is None:
            return f"错误：在状态文件中未找到项目 '{project_name}'"
        
        # 查找Agent条目
        agent_entry = None
        for agent in project_entry.get("agents", []):
            if agent.get("name") == agent_name:
                agent_entry = agent
                break
        
        if agent_entry is None:
            return f"错误：在项目 '{project_name}' 中未找到 Agent '{agent_name}'"
        
        # 支持制品路径的阶段
        artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
        
        # 收集制品路径信息
        artifact_info = {}
        pipeline = agent_entry.get("pipeline", [])
        
        for stage_entry in pipeline:
            stage_name = stage_entry.get("stage", "")
            if stage_name in artifact_stages:
                artifact_paths = stage_entry.get("agent_artifact_path", [])
                artifact_info[stage_name] = {
                    "stage": stage_name,
                    "description": stage_entry.get("description", ""),
                    "status": stage_entry.get("status", False),
                    "doc_path": stage_entry.get("doc_path", ""),
                    "agent_artifact_path": artifact_paths,
                    "artifact_count": len(artifact_paths),
                    "updated_date": stage_entry.get("updated_date", "")
                }
        
        # 如果指定了特定阶段
        if stage and stage.strip():
            stage = stage.strip()
            if stage not in artifact_stages:
                return f"错误：阶段 '{stage}' 不支持制品路径，支持的阶段包括: {', '.join(artifact_stages)}"
            
            if stage not in artifact_info:
                return f"错误：在 Agent '{agent_name}' 中未找到阶段 '{stage}'"
            
            result = {
                "status": "success",
                "project_name": project_name,
                "agent_name": agent_name,
                "stage_info": artifact_info[stage],
                "query_date": datetime.now(timezone.utc).isoformat()
            }
        else:
            # 返回所有支持制品路径的阶段信息
            total_artifacts = sum(info["artifact_count"] for info in artifact_info.values())
            stages_with_artifacts = sum(1 for info in artifact_info.values() if info["artifact_count"] > 0)
            
            result = {
                "status": "success",
                "project_name": project_name,
                "agent_name": agent_name,
                "artifact_stages": artifact_info,
                "summary": {
                    "total_artifact_stages": len(artifact_info),
                    "stages_with_artifacts": stages_with_artifacts,
                    "total_artifacts": total_artifacts,
                    "supported_stages": artifact_stages
                },
                "query_date": datetime.now(timezone.utc).isoformat()
            }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取制品路径信息时出现错误: {str(e)}"


@tool
def update_project_stage_content(project_name: str, agent_name: str, stage_name: str, content: str, agent_artifact_path: List[str] = None) -> str:
    """
    将内容写入指定的项目阶段文件，自动添加项目和Agent上下文信息
    
    Args:
        project_name (str): 项目名称
        agent_name (str): Agent名称
        stage_name (str): 阶段名称
        content (str): 要写入的内容
        agent_artifact_path (List[str], optional): 生成的制品路径数组，用于代码开发、工具生成、提示词生成阶段
        
    Returns:
        str: 操作结果信息
        
    说明：
    - 文件路径：projects/<project_name>/agents/<agent_name>/<stage_name>.json
    - 自动创建必要的目录结构
    - 自动添加项目上下文信息到文件头部
    - 如果提供了agent_artifact_path，会同时更新status.yaml中的构件路径
    - 支持制品路径的阶段：prompt_engineer、tools_developer、agent_code_developer
    """
    try:
        # 验证参数
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        if not agent_name or not agent_name.strip():
            return "错误：Agent名称不能为空"
        
        if not stage_name or not stage_name.strip():
            return "错误：阶段名称不能为空"
        
        if content is None:
            return "错误：内容不能为None"
        
        project_name = project_name.strip()
        agent_name = agent_name.strip()
        stage_name = stage_name.strip()
        
        # 验证路径安全性
        if "/" in agent_name or "\\" in agent_name or ".." in agent_name:
            return "错误：Agent名称不能包含路径分隔符或相对路径"
        
        if "/" in stage_name or "\\" in stage_name or ".." in stage_name:
            return "错误：阶段名称不能包含路径分隔符或相对路径"
        
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在，请先使用 project_init 初始化项目"
        
        # 创建Agent目录
        agent_dir = os.path.join(project_root, "agents", agent_name)
        os.makedirs(agent_dir, exist_ok=True)
        
        # 创建阶段文件路径
        stage_file_path = os.path.join(agent_dir, f"{stage_name}.json")
        
        # 增强内容，添加项目和Agent上下文信息
        enhanced_content = _enhance_content_with_context(content, project_name, agent_name, stage_name)
        
        # 写入内容
        with open(stage_file_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
        
        # 如果提供了agent_artifact_path，同时更新status.yaml中对应阶段的制品路径
        artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
        if stage_name in artifact_stages and agent_artifact_path:
            status_path = os.path.join(project_root, "status.yaml")
            if os.path.exists(status_path):
                try:
                    with open(status_path, 'r', encoding='utf-8') as f:
                        status_data = yaml.safe_load(f) or {}
                    
                    # 查找并更新对应的阶段
                    if "project_info" in status_data:
                        for project in status_data["project_info"]:
                            if project.get("name") == project_name:
                                for agent in project.get("agents", []):
                                    if agent.get("name") == agent_name:
                                        for stage_entry in agent.get("pipeline", []):
                                            if stage_entry.get("stage") == stage_name:
                                                stage_entry["agent_artifact_path"] = agent_artifact_path
                                                stage_entry["updated_date"] = datetime.now(timezone.utc).isoformat()
                                                break
                                        break
                                break
                    
                    # 写回status.yaml
                    with open(status_path, 'w', encoding='utf-8') as f:
                        yaml.dump(status_data, f, default_flow_style=False, allow_unicode=True, indent=2)
                        
                except (yaml.YAMLError, PermissionError):
                    pass  # 如果更新status.yaml失败，不影响主要功能
        
        # 构建返回结果
        result = {
            "status": "success",
            "message": f"成功写入阶段内容到 '{stage_file_path}'",
            "project_name": project_name,
            "agent_name": agent_name,
            "stage_name": stage_name,
            "file_path": stage_file_path,
            "content_length": len(content),
            "updated_date": datetime.now(timezone.utc).isoformat()
        }
        
        # 如果提供了制品路径，添加到结果中
        if agent_artifact_path:
            result["agent_artifact_path"] = agent_artifact_path
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件"
    except Exception as e:
        return f"写入项目阶段内容时出现错误: {str(e)}"


@tool
def update_agent_artifact_paths(project_name: str, agent_name: str, stage: str, agent_artifact_path: List[str]) -> str:
    """
    专门更新指定阶段的agent_artifact_path字段
    
    Args:
        project_name (str): 项目名称（必须）
        agent_name (str): Agent名称（必须）
        stage (str): 阶段名称（必须） - prompt_engineer, tools_developer, agent_code_developer
        agent_artifact_path (List[str]): 制品路径数组（必须）
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证必须参数
        if not project_name or not project_name.strip():
            return "错误：项目名称（project_name）是必须参数，不能为空"
        
        if not agent_name or not agent_name.strip():
            return "错误：Agent名称（agent_name）是必须参数，不能为空"
        
        if not stage or not stage.strip():
            return "错误：阶段名称（stage）是必须参数，不能为空"
        
        if not agent_artifact_path or not isinstance(agent_artifact_path, list):
            return "错误：agent_artifact_path必须是有效的路径数组"
        
        # 验证阶段名称
        valid_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
        
        if stage not in valid_stages:
            return f"错误：无效的阶段名称 '{stage}'，支持制品路径的阶段包括: {', '.join(valid_stages)}"
        
        project_name = project_name.strip()
        agent_name = agent_name.strip()
        stage = stage.strip()
        
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在，请先使用 project_init 初始化项目"
        
        status_path = os.path.join(project_root, "status.yaml")
        
        # 检查状态文件是否存在
        if not os.path.exists(status_path):
            return f"错误：项目 '{project_name}' 的状态文件不存在"
        
        # 读取现有状态
        status_data = {}
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                status_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            return f"错误：无法解析状态文件: {str(e)}"
        
        # 查找项目条目
        project_entry = None
        if "project_info" in status_data:
            for project in status_data["project_info"]:
                if project.get("name") == project_name:
                    project_entry = project
                    break
        
        if project_entry is None:
            return f"错误：在状态文件中未找到项目 '{project_name}'"
        
        # 查找Agent条目
        agent_entry = None
        for agent in project_entry.get("agents", []):
            if agent.get("name") == agent_name:
                agent_entry = agent
                break
        
        if agent_entry is None:
            return f"错误：在项目 '{project_name}' 中未找到 Agent '{agent_name}'"
        
        # 更新指定阶段的agent_artifact_path
        pipeline = agent_entry.get("pipeline", [])
        stage_found = False
        
        for stage_entry in pipeline:
            if stage_entry.get("stage") == stage:
                stage_entry["agent_artifact_path"] = agent_artifact_path
                stage_entry["updated_date"] = datetime.now(timezone.utc).isoformat()
                stage_found = True
                break
        
        if not stage_found:
            return f"错误：在 Agent '{agent_name}' 中未找到阶段 '{stage}'"
        
        # 写入状态文件
        try:
            with open(status_path, 'w', encoding='utf-8') as f:
                yaml.dump(status_data, f, default_flow_style=False, allow_unicode=True, indent=2)
        except PermissionError:
            return f"错误：没有权限写入状态文件"
        
        result = {
            "status": "success",
            "message": f"成功更新 Agent '{agent_name}' 的阶段 '{stage}' 制品路径",
            "project_name": project_name,
            "agent_name": agent_name,
            "stage": stage,
            "agent_artifact_path": agent_artifact_path,
            "artifact_count": len(agent_artifact_path),
            "updated_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"更新制品路径时出现错误: {str(e)}"


@tool
def get_project_stage_content(project_name: str, agent_name: str, stage_name: str) -> str:
    """
    读取指定项目阶段文件的内容
    
    Args:
        project_name (str): 项目名称
        agent_name (str): Agent名称
        stage_name (str): 阶段名称
        
    Returns:
        str: 文件内容或错误信息
    """
    try:
        # 验证参数
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        if not agent_name or not agent_name.strip():
            return "错误：Agent名称不能为空"
        
        if not stage_name or not stage_name.strip():
            return "错误：阶段名称不能为空"
        
        project_name = project_name.strip()
        agent_name = agent_name.strip()
        stage_name = stage_name.strip()
        
        # 验证路径安全性
        if "/" in agent_name or "\\" in agent_name or ".." in agent_name:
            return "错误：Agent名称不能包含路径分隔符或相对路径"
        
        if "/" in stage_name or "\\" in stage_name or ".." in stage_name:
            return "错误：阶段名称不能包含路径分隔符或相对路径"
        
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        # 构建文件路径
        stage_file_path = os.path.join(project_root, "agents", agent_name, f"{stage_name}.json")
        
        # 检查文件是否存在
        if not os.path.exists(stage_file_path):
            return f"错误：阶段文件 '{stage_file_path}' 不存在"
        
        # 读取文件内容
        with open(stage_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件信息
        file_stat = os.stat(stage_file_path)
        import time
        
        # 构建基本结果
        result = {
            "status": "success",
            "project_name": project_name,
            "agent_name": agent_name,
            "stage_name": stage_name,
            "file_path": stage_file_path,
            "content": content,
            "content_length": len(content),
            "file_size": file_stat.st_size,
            "modified_time": time.ctime(file_stat.st_mtime),
            "query_date": datetime.now(timezone.utc).isoformat()
        }
        
        # 尝试从status.yaml中获取agent_artifact_path信息
        artifact_stages = ["prompt_engineer", "tools_developer", "agent_code_developer"]
        if stage_name in artifact_stages:
            status_path = os.path.join(project_root, "status.yaml")
            if os.path.exists(status_path):
                try:
                    with open(status_path, 'r', encoding='utf-8') as f:
                        status_data = yaml.safe_load(f) or {}
                    
                    # 查找对应阶段的agent_artifact_path
                    if "project_info" in status_data:
                        for project in status_data["project_info"]:
                            if project.get("name") == project_name:
                                for agent in project.get("agents", []):
                                    if agent.get("name") == agent_name:
                                        for stage_entry in agent.get("pipeline", []):
                                            if stage_entry.get("stage") == stage_name:
                                                artifact_path = stage_entry.get("agent_artifact_path")
                                                if artifact_path:
                                                    result["agent_artifact_path"] = artifact_path
                                                break
                                        break
                                break
                except (yaml.YAMLError, PermissionError):
                    pass  # 如果读取失败，不影响主要功能
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限读取文件"
    except Exception as e:
        return f"读取项目阶段内容时出现错误: {str(e)}"


@tool
def list_project_agents(project_name: str) -> str:
    """
    列出指定项目中的所有Agent目录
    
    Args:
        project_name (str): 项目名称
        
    Returns:
        str: Agent列表信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        # 获取所有Agent目录
        agents_root = os.path.join(project_root, "agents")
        agent_dirs = []
        
        # 检查agents目录是否存在
        if not os.path.exists(agents_root):
            return f"错误：项目 '{project_name}' 中不存在agents目录"
        
        for item in os.listdir(agents_root):
            item_path = os.path.join(agents_root, item)
            if os.path.isdir(item_path):
                # 统计目录中的文件数量
                file_count = 0
                stage_files = []
                try:
                    for file_item in os.listdir(item_path):
                        file_path = os.path.join(item_path, file_item)
                        if os.path.isfile(file_path):
                            file_count += 1
                            if file_item.endswith('.json'):
                                stage_name = file_item[:-5]  # 移除.json扩展名
                                stage_files.append(stage_name)
                except PermissionError:
                    file_count = -1  # 表示无法访问
                
                dir_stat = os.stat(item_path)
                import time
                agent_dirs.append({
                    "agent_name": item,
                    "directory_path": item_path,
                    "file_count": file_count,
                    "stage_files": stage_files,
                    "modified_time": time.ctime(dir_stat.st_mtime)
                })
        
        # 按名称排序
        agent_dirs.sort(key=lambda x: x["agent_name"])
        
        result = {
            "status": "success",
            "project_name": project_name,
            "project_directory": project_root,
            "agent_count": len(agent_dirs),
            "agents": agent_dirs,
            "query_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"列出项目Agent时出现错误: {str(e)}"


@tool
def list_all_projects() -> str:
    """
    列出所有项目
    
    Returns:
        str: 项目列表信息
    """
    try:
        projects_dir = "projects"
        
        # 检查projects目录是否存在
        if not os.path.exists(projects_dir):
            return f"项目目录 {projects_dir} 不存在"
        
        # 获取所有项目目录
        project_dirs = []
        for item in os.listdir(projects_dir):
            item_path = os.path.join(projects_dir, item)
            if os.path.isdir(item_path):
                # 读取项目配置
                config_path = os.path.join(item_path, "config.yaml")
                project_info = {
                    "project_name": item,
                    "directory_path": item_path,
                    "description": f"AI智能体项目：{item}",
                    "version": "未知",
                    "created_date": "未知"
                }
                
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f) or {}
                            project_config = config.get("project", {})
                            project_info.update({
                                "description": project_config.get("description", project_info["description"]),
                                "version": project_config.get("version", project_info["version"]),
                                "created_date": project_config.get("created_date", project_info["created_date"])
                            })
                    except (yaml.YAMLError, PermissionError):
                        pass  # 使用默认信息
                
                # 统计Agent数量
                agent_count = 0
                try:
                    agents_dir = os.path.join(item_path, "agents")
                    if os.path.exists(agents_dir):
                        for sub_item in os.listdir(agents_dir):
                            sub_item_path = os.path.join(agents_dir, sub_item)
                            if os.path.isdir(sub_item_path):
                                agent_count += 1
                except PermissionError:
                    agent_count = -1  # 表示无法访问
                
                project_info["agent_count"] = agent_count
                
                dir_stat = os.stat(item_path)
                import time
                project_info["modified_time"] = time.ctime(dir_stat.st_mtime)
                
                project_dirs.append(project_info)
        
        # 按名称排序
        project_dirs.sort(key=lambda x: x["project_name"])
        
        result = {
            "status": "success",
            "projects_directory": projects_dir,
            "project_count": len(project_dirs),
            "projects": project_dirs,
            "query_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"列出所有项目时出现错误: {str(e)}"


@tool
def get_project_context(project_name: str, agent_name: str = None) -> str:
    """
    获取项目上下文信息，用于Agent输出时包含项目和Agent名称
    
    Args:
        project_name (str): 项目名称
        agent_name (str, optional): Agent名称
        
    Returns:
        str: 项目上下文信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        # 读取项目配置
        config_path = os.path.join(project_root, "config.yaml")
        project_description = f"AI智能体项目：{project_name}"
        project_version = "1.0.0"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    project_config = config.get("project", {})
                    project_description = project_config.get("description", project_description)
                    project_version = project_config.get("version", project_version)
            except yaml.YAMLError:
                pass  # 使用默认值
        
        # 构建上下文信息
        context_info = {
            "project_name": project_name,
            "project_description": project_description,
            "project_version": project_version,
            "current_time": datetime.now(timezone.utc).isoformat(),
            "context_header": f"""# 项目上下文信息

**项目名称**: {project_name}
**项目描述**: {project_description}
**项目版本**: {project_version}"""
        }
        
        # 如果提供了Agent名称，添加Agent信息
        if agent_name and agent_name.strip():
            agent_name = agent_name.strip()
            context_info["agent_name"] = agent_name
            context_info["context_header"] += f"""
**Agent名称**: {agent_name}"""
        
        context_info["context_header"] += f"""
**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

---

"""
        
        return json.dumps(context_info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取项目上下文时出现错误: {str(e)}"

@tool
def get_project_from_stats(agent: Agent):
    """Get user statistics from agent state."""
    all_state = agent.state.get()

    return f"项目初始化信息: {all_state}"

@tool
def get_project_config(project_name: str) -> str:
    """
    获取指定项目的配置信息
    
    Args:
        project_name (str): 项目名称
        
    Returns:
        str: JSON格式的项目配置信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        config_path = os.path.join(project_root, "config.yaml")
        
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            return f"错误：项目 '{project_name}' 的配置文件不存在"
        
        # 读取配置文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            return f"错误：无法解析配置文件: {str(e)}"
        
        # 获取文件信息
        file_stat = os.stat(config_path)
        import time
        
        result = {
            "status": "success",
            "project_name": project_name,
            "config_file_path": config_path,
            "config_data": config_data,
            "file_size": file_stat.st_size,
            "modified_time": time.ctime(file_stat.st_mtime),
            "query_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取项目配置时出现错误: {str(e)}"


@tool
def get_project_readme(project_name: str) -> str:
    """
    获取指定项目的README.md内容
    
    Args:
        project_name (str): 项目名称
        
    Returns:
        str: JSON格式的README内容和信息
    """
    try:
        # 验证项目名称
        if not project_name or not project_name.strip():
            return "错误：项目名称不能为空"
        
        project_name = project_name.strip()
        project_root = os.path.join("projects", project_name)
        
        # 检查项目目录是否存在
        if not os.path.exists(project_root):
            return f"错误：项目 '{project_name}' 不存在"
        
        readme_path = os.path.join(project_root, "README.md")
        
        # 检查README文件是否存在
        if not os.path.exists(readme_path):
            return f"错误：项目 '{project_name}' 的README.md文件不存在"
        
        # 读取README文件
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # 获取文件信息
        file_stat = os.stat(readme_path)
        import time
        
        # 统计基本信息
        lines = readme_content.split('\n')
        line_count = len(lines)
        word_count = len(readme_content.split())
        char_count = len(readme_content)
        
        result = {
            "status": "success",
            "project_name": project_name,
            "readme_file_path": readme_path,
            "content": readme_content,
            "file_info": {
                "file_size": file_stat.st_size,
                "line_count": line_count,
                "word_count": word_count,
                "char_count": char_count,
                "modified_time": time.ctime(file_stat.st_mtime)
            },
            "query_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"获取项目README时出现错误: {str(e)}"


@tool
def generate_content(type: Literal["agent", "prompt", "tool"], content: str, project_name: str, artifact_name: str) -> str:
    """
    根据类型生成内容文件到指定目录
    
    Args:
        type (Literal["agent", "prompt", "tool"]): 内容类型（必须），可以是 "agent"、"prompt" 或 "tool"
        content (str): 要写入的文件内容（必须）
        project_name (str): 项目名称（必须）
        artifact_name (str): 名称（必须）,若type为agent或tool，则为脚本名称，若type为prompt，则为Prompt yaml文件名称
        
    Returns:
        str: 操作结果信息
    """
    try:
        # 验证必须参数
        if type not in ["agent", "prompt", "tool"]:
            return "错误：type参数必须是 'agent'、'prompt' 或 'tool'"
        
        if not content or not content.strip():
            return "错误：content参数（内容）是必须参数，不能为空"
        
        if not project_name or not project_name.strip():
            return "错误：project_name参数（项目名称）是必须参数，不能为空"
        
        if not artifact_name or not artifact_name.strip():
            return "错误：artifact_name参数（构件名称）是必须参数，不能为空"
        
        # 清理参数
        project_name = project_name.strip()
        artifact_name = artifact_name.strip()
        
        # 验证名称格式（避免路径遍历攻击）
        if "/" in project_name or "\\" in project_name or ".." in project_name:
            return "错误：项目名称不能包含路径分隔符或相对路径"
        
        if "/" in artifact_name or "\\" in artifact_name or ".." in artifact_name:
            return "错误：Agent名称不能包含路径分隔符或相对路径"
        
        # 根据类型确定目标目录和文件扩展名
        if type == "agent":
            target_dir = os.path.join("agents", "generated_agents", project_name)
            filename = f"{artifact_name}" if artifact_name.endswith('.py') else f"{artifact_name}.py"
        elif type == "prompt":
            target_dir = os.path.join("prompts", "generated_agents_prompts", project_name)
            filename = f"{artifact_name}" if artifact_name.endswith('.yaml') else f"{artifact_name}.yaml"
        elif type == "tool":
            target_dir = os.path.join("tools", "generated_tools", project_name)
            filename = f"{artifact_name}" if artifact_name.endswith('.py') else f"{artifact_name}.py"
        
        # 确保目标目录存在
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        
        # 构建完整文件路径
        file_path = os.path.join(target_dir, filename)
        
        # 检查文件是否已存在
        if os.path.exists(file_path):
            return f"错误：文件 '{filename}' 已存在于 {target_dir} 目录中，请使用不同的名称或删除现有文件"
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 返回成功信息
        result = {
            "status": "success",
            "message": f"成功创建{type}文件",
            "type": type,
            "project_name": project_name,
            "agent_name": artifact_name,
            "file_path": file_path,
            "file_name": filename,
            "target_directory": target_dir,
            "content_length": len(content),
            "created_date": datetime.now(timezone.utc).isoformat()
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except PermissionError:
        return f"错误：没有权限写入文件到 {target_dir}"
    except OSError as e:
        return f"错误：文件系统操作失败: {str(e)}"
    except Exception as e:
        return f"生成内容文件时出现错误: {str(e)}"


# 主函数，用于直接调用测试
def main():
    """主函数，用于测试项目管理工具"""
    print("=== 项目管理工具测试 ===")
    
    # 测试项目初始化
    print("\n1. 测试项目初始化:")
    result = project_init("test_project")
    print(result)
    
    # 测试更新项目配置
    print("\n2. 测试更新项目配置:")
    result = update_project_config("test_project", "这是一个测试项目", "1.1.0")
    print(result)
    
    # 测试更新项目状态
    print("\n3. 测试更新项目状态:")
    result = update_project_status("test_project", "test_agent", "requirements_analyzer", True, "docs/requirements.md")
    print(result)
    
    # 测试更新带制品路径的项目状态
    print("\n3.1 测试更新带制品路径的项目状态:")
    artifact_paths = [
        "prompts/generated_agents_prompts/test_project/test_agent.yaml",
        "prompts/generated_agents_prompts/test_project/test_agent_v2.yaml"
    ]
    result = update_project_status("test_project", "test_agent", "prompt_engineer", True, "docs/prompt_design.md", artifact_paths)
    print(result)
    
    # 测试查询项目状态
    print("\n4. 测试查询项目状态:")
    result = get_project_status("test_project", "test_agent")
    print(result)
    
    # 测试获取制品路径信息
    print("\n4.1 测试获取制品路径信息:")
    result = get_agent_artifact_paths("test_project", "test_agent")
    print(result)
    
    # 测试获取特定阶段制品路径信息
    print("\n4.2 测试获取特定阶段制品路径信息:")
    result = get_agent_artifact_paths("test_project", "test_agent", "prompt_engineer")
    print(result)
    
    # 测试更新制品路径
    print("\n4.3 测试更新制品路径:")
    tool_paths = [
        "tools/generated_tools/test_project/test_tool.py",
        "tools/generated_tools/test_project/helper_tool.py"
    ]
    result = update_agent_artifact_paths("test_project", "test_agent", "tools_developer", tool_paths)
    print(result)
    
    # 测试写入阶段内容
    print("\n5. 测试写入阶段内容:")
    test_content = '{"requirements": "这是需求分析的结果", "timestamp": "2025-08-25"}'
    result = update_project_stage_content("test_project", "test_agent", "requirements_analyzer", test_content)
    print(result)
    
    # 测试读取阶段内容
    print("\n6. 测试读取阶段内容:")
    result = get_project_stage_content("test_project", "test_agent", "requirements_analyzer")
    print(result)
    
    # 测试更新README
    print("\n7. 测试更新README:")
    result = update_project_readme("test_project", "这是额外的项目信息")
    print(result)
    
    # 测试列出项目Agent
    print("\n8. 测试列出项目Agent:")
    result = list_project_agents("test_project")
    print(result)
    
    # 测试列出所有项目
    print("\n9. 测试列出所有项目:")
    result = list_all_projects()
    print(result)
    
    # 测试获取项目配置
    print("\n10. 测试获取项目配置:")
    result = get_project_config("test_project")
    print(result)
    
    # 测试获取项目README
    print("\n11. 测试获取项目README:")
    result = get_project_readme("test_project")
    print(result)
    
    # 测试生成内容
    print("\n12. 测试生成Agent内容:")
    test_agent_content = '''#!/usr/bin/env python3
"""
测试生成的Agent
"""

from strands import tool

@tool
def test_function():
    """测试函数"""
    return "这是一个测试Agent"

if __name__ == "__main__":
    print("测试Agent运行")
'''
    result = generate_content("agent", test_agent_content, "test_project", "test_generated_agent")
    print(result)
    
    print("\n13. 测试生成Prompt内容:")
    test_prompt_content = '''agent:
  name: "test_generated_prompt"
  description: "测试生成的提示词"
  category: "test"
  versions:
    - version: "1.0.0"
      prompt: "这是一个测试提示词"
'''
    result = generate_content("prompt", test_prompt_content, "test_project", "test_generated_prompt")
    print(result)
    
    print("\n14. 测试生成Tool内容:")
    test_tool_content = '''#!/usr/bin/env python3
"""
测试生成的工具
"""

from strands import tool

@tool
def test_tool(input_text: str) -> str:
    """
    测试工具函数
    
    Args:
        input_text (str): 输入文本
        
    Returns:
        str: 处理后的文本
    """
    return f"处理结果: {input_text}"
'''
    result = generate_content("tool", test_tool_content, "test_project", "test_generated_tool")
    print(result)


if __name__ == "__main__":
    main()