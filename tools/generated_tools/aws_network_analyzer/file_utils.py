from strands import tool
import os
import json
import yaml
import shutil
import tempfile
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, BinaryIO

@tool
def file_manager(
    operation: str,
    path: Optional[str] = None,
    content: Optional[Union[str, Dict[str, Any], List[Dict[str, Any]]]] = None,
    format_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    backup: bool = False
) -> Dict[str, Any]:
    """
    管理文件操作，包括读取、写入、复制、移动、删除等。
    
    Args:
        operation: 操作类型，如read、write、copy、move、delete、list等
        path: 文件或目录路径
        content: 要写入的内容，可以是字符串或字典/列表（用于JSON/YAML）
        format_type: 内容格式类型，如text、json、yaml、binary
        metadata: 要包含在输出文件中的元数据
        backup: 是否在修改前创建备份
    
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 创建缓存目录
        cache_dir = os.path.join('.cache', 'aws_network_analyzer_agent')
        os.makedirs(cache_dir, exist_ok=True)
        
        if operation == "read":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "读取操作需要path参数"
                }
            
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"文件不存在: {path}"
                }
            
            # 根据文件扩展名或指定格式读取
            if format_type == "json" or path.endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {
                    "status": "success",
                    "operation": "read",
                    "path": path,
                    "format": "json",
                    "content": data,
                    "size": os.path.getsize(path),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                }
            elif format_type == "yaml" or path.endswith(('.yaml', '.yml')):
                with open(path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                return {
                    "status": "success",
                    "operation": "read",
                    "path": path,
                    "format": "yaml",
                    "content": data,
                    "size": os.path.getsize(path),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                }
            elif format_type == "binary":
                with open(path, 'rb') as f:
                    data = f.read()
                return {
                    "status": "success",
                    "operation": "read",
                    "path": path,
                    "format": "binary",
                    "content": "二进制数据，长度: " + str(len(data)),
                    "size": os.path.getsize(path),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                }
            else:  # 默认以文本方式读取
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                return {
                    "status": "success",
                    "operation": "read",
                    "path": path,
                    "format": "text",
                    "content": data,
                    "size": os.path.getsize(path),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                }
        
        elif operation == "write":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "写入操作需要path参数"
                }
            
            if content is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "写入操作需要content参数"
                }
            
            # 确保目录存在
            directory = os.path.dirname(os.path.abspath(path))
            os.makedirs(directory, exist_ok=True)
            
            # 备份现有文件
            if backup and os.path.exists(path):
                backup_path = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                shutil.copy2(path, backup_path)
            
            # 根据格式写入
            if format_type == "json" or path.endswith('.json'):
                # 添加元数据
                if metadata and isinstance(content, dict):
                    content["_metadata"] = metadata
                
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                return {
                    "status": "success",
                    "operation": "write",
                    "path": path,
                    "format": "json",
                    "size": os.path.getsize(path),
                    "timestamp": datetime.now().isoformat()
                }
            elif format_type == "yaml" or path.endswith(('.yaml', '.yml')):
                # 添加元数据
                if metadata and isinstance(content, dict):
                    content["_metadata"] = metadata
                
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(content, f, default_flow_style=False)
                return {
                    "status": "success",
                    "operation": "write",
                    "path": path,
                    "format": "yaml",
                    "size": os.path.getsize(path),
                    "timestamp": datetime.now().isoformat()
                }
            elif format_type == "binary" and isinstance(content, bytes):
                with open(path, 'wb') as f:
                    f.write(content)
                return {
                    "status": "success",
                    "operation": "write",
                    "path": path,
                    "format": "binary",
                    "size": os.path.getsize(path),
                    "timestamp": datetime.now().isoformat()
                }
            else:  # 默认以文本方式写入
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
                return {
                    "status": "success",
                    "operation": "write",
                    "path": path,
                    "format": "text",
                    "size": os.path.getsize(path),
                    "timestamp": datetime.now().isoformat()
                }
        
        elif operation == "copy":
            # 参数: source_path, target_path
            source_path = path
            target_path = content  # 这里使用content参数作为目标路径
            
            if not source_path or not target_path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "复制操作需要source_path和target_path参数"
                }
            
            if not os.path.exists(source_path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"源文件不存在: {source_path}"
                }
            
            # 确保目标目录存在
            target_dir = os.path.dirname(os.path.abspath(target_path))
            os.makedirs(target_dir, exist_ok=True)
            
            # 复制文件
            if os.path.isfile(source_path):
                shutil.copy2(source_path, target_path)
                return {
                    "status": "success",
                    "operation": "copy",
                    "source_path": source_path,
                    "target_path": target_path,
                    "size": os.path.getsize(target_path),
                    "timestamp": datetime.now().isoformat()
                }
            elif os.path.isdir(source_path):
                shutil.copytree(source_path, target_path)
                return {
                    "status": "success",
                    "operation": "copy",
                    "source_path": source_path,
                    "target_path": target_path,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": f"无法复制: {source_path} 不是文件或目录"
                }
        
        elif operation == "move":
            # 参数: source_path, target_path
            source_path = path
            target_path = content  # 这里使用content参数作为目标路径
            
            if not source_path or not target_path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "移动操作需要source_path和target_path参数"
                }
            
            if not os.path.exists(source_path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"源文件不存在: {source_path}"
                }
            
            # 确保目标目录存在
            target_dir = os.path.dirname(os.path.abspath(target_path))
            os.makedirs(target_dir, exist_ok=True)
            
            # 移动文件
            shutil.move(source_path, target_path)
            return {
                "status": "success",
                "operation": "move",
                "source_path": source_path,
                "target_path": target_path,
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "delete":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "删除操作需要path参数"
                }
            
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"文件不存在: {path}"
                }
            
            # 备份文件
            if backup:
                backup_path = os.path.join(cache_dir, f"backup_{os.path.basename(path)}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
                if os.path.isfile(path):
                    shutil.copy2(path, backup_path)
                elif os.path.isdir(path):
                    shutil.copytree(path, backup_path)
            
            # 删除文件或目录
            if os.path.isfile(path):
                os.remove(path)
                return {
                    "status": "success",
                    "operation": "delete",
                    "path": path,
                    "type": "file",
                    "timestamp": datetime.now().isoformat(),
                    "backup_path": backup_path if backup else None
                }
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return {
                    "status": "success",
                    "operation": "delete",
                    "path": path,
                    "type": "directory",
                    "timestamp": datetime.now().isoformat(),
                    "backup_path": backup_path if backup else None
                }
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": f"无法删除: {path} 不是文件或目录"
                }
        
        elif operation == "list":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "列表操作需要path参数"
                }
            
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"路径不存在: {path}"
                }
            
            if not os.path.isdir(path):
                return {
                    "status": "error",
                    "error_type": "NotADirectoryError",
                    "error_message": f"路径不是目录: {path}"
                }
            
            # 列出目录内容
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                item_type = "file" if os.path.isfile(item_path) else "directory"
                items.append({
                    "name": item,
                    "type": item_type,
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None,
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                })
            
            return {
                "status": "success",
                "operation": "list",
                "path": path,
                "items": items,
                "count": len(items),
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "exists":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "exists操作需要path参数"
                }
            
            exists = os.path.exists(path)
            return {
                "status": "success",
                "operation": "exists",
                "path": path,
                "exists": exists,
                "type": "file" if exists and os.path.isfile(path) else "directory" if exists else None,
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "mkdir":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "mkdir操作需要path参数"
                }
            
            # 创建目录
            os.makedirs(path, exist_ok=True)
            return {
                "status": "success",
                "operation": "mkdir",
                "path": path,
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "checksum":
            if not path:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "checksum操作需要path参数"
                }
            
            if not os.path.exists(path):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"文件不存在: {path}"
                }
            
            if not os.path.isfile(path):
                return {
                    "status": "error",
                    "error_type": "IsADirectoryError",
                    "error_message": f"路径是目录，不是文件: {path}"
                }
            
            # 计算文件校验和
            algorithm = format_type or "sha256"  # 使用format_type参数指定算法
            
            if algorithm == "md5":
                hash_obj = hashlib.md5()
            elif algorithm == "sha1":
                hash_obj = hashlib.sha1()
            elif algorithm == "sha256":
                hash_obj = hashlib.sha256()
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": f"不支持的哈希算法: {algorithm}"
                }
            
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            
            checksum = hash_obj.hexdigest()
            return {
                "status": "success",
                "operation": "checksum",
                "path": path,
                "algorithm": algorithm,
                "checksum": checksum,
                "size": os.path.getsize(path),
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "temp":
            # 创建临时文件或目录
            prefix = content or "temp"
            suffix = format_type or ""
            
            if path == "file":
                fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=cache_dir)
                os.close(fd)
                return {
                    "status": "success",
                    "operation": "temp",
                    "type": "file",
                    "path": temp_path,
                    "timestamp": datetime.now().isoformat()
                }
            elif path == "dir":
                temp_path = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=cache_dir)
                return {
                    "status": "success",
                    "operation": "temp",
                    "type": "directory",
                    "path": temp_path,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "temp操作需要path参数为'file'或'dir'"
                }
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的操作: {operation}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def progress_tracker(
    operation: str,
    task_name: str,
    total_steps: Optional[int] = None,
    current_step: Optional[int] = None,
    step_description: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    跟踪和报告任务进度。
    
    Args:
        operation: 操作类型，如create、update、complete、get、reset
        task_name: 任务名称
        total_steps: 总步骤数
        current_step: 当前步骤
        step_description: 当前步骤描述
        status: 任务状态，如running、completed、failed
        metadata: 任务元数据
        log_file: 日志文件路径
    
    Returns:
        Dict[str, Any]: 包含操作结果的字典
    """
    try:
        # 创建缓存目录
        cache_dir = os.path.join('.cache', 'aws_network_analyzer_agent')
        os.makedirs(cache_dir, exist_ok=True)
        
        # 进度文件路径
        progress_file = os.path.join(cache_dir, f"{task_name.replace(' ', '_')}_progress.json")
        
        if operation == "create":
            if os.path.exists(progress_file):
                # 读取现有进度
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                
                # 如果任务已完成，不允许重新创建
                if progress_data.get("status") == "completed":
                    return {
                        "status": "error",
                        "error_type": "ValueError",
                        "error_message": f"任务'{task_name}'已完成，不能重新创建"
                    }
            
            # 创建新的进度跟踪
            progress_data = {
                "task_name": task_name,
                "total_steps": total_steps or 1,
                "current_step": 0,
                "step_description": "",
                "status": "initialized",
                "progress_percentage": 0,
                "start_time": datetime.now().isoformat(),
                "last_update_time": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # 写入进度文件
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 创建日志文件
            if log_file:
                log_dir = os.path.dirname(os.path.abspath(log_file))
                os.makedirs(log_dir, exist_ok=True)
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] 任务'{task_name}'已创建\n")
            
            return {
                "status": "success",
                "operation": "create",
                "task_name": task_name,
                "progress_file": progress_file,
                "log_file": log_file,
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "update":
            if not os.path.exists(progress_file):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"任务'{task_name}'的进度文件不存在"
                }
            
            # 读取现有进度
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # 更新进度
            if current_step is not None:
                progress_data["current_step"] = current_step
            
            if step_description is not None:
                progress_data["step_description"] = step_description
            
            if status is not None:
                progress_data["status"] = status
            
            if metadata is not None:
                progress_data["metadata"].update(metadata)
            
            # 计算进度百分比
            total = progress_data["total_steps"]
            current = progress_data["current_step"]
            progress_data["progress_percentage"] = int(current / total * 100) if total > 0 else 0
            
            # 更新时间
            progress_data["last_update_time"] = datetime.now().isoformat()
            
            # 写入进度文件
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 更新日志
            if log_file and os.path.exists(log_file):
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] 步骤 {current}/{total} ({progress_data['progress_percentage']}%): {step_description or ''}\n")
            
            return {
                "status": "success",
                "operation": "update",
                "task_name": task_name,
                "current_step": current,
                "total_steps": total,
                "progress_percentage": progress_data["progress_percentage"],
                "task_status": progress_data["status"],
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "complete":
            if not os.path.exists(progress_file):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"任务'{task_name}'的进度文件不存在"
                }
            
            # 读取现有进度
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # 标记任务完成
            progress_data["status"] = "completed"
            progress_data["current_step"] = progress_data["total_steps"]
            progress_data["progress_percentage"] = 100
            progress_data["completion_time"] = datetime.now().isoformat()
            
            # 写入进度文件
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 更新日志
            if log_file and os.path.exists(log_file):
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] 任务'{task_name}'已完成\n")
            
            return {
                "status": "success",
                "operation": "complete",
                "task_name": task_name,
                "progress_percentage": 100,
                "task_status": "completed",
                "start_time": progress_data["start_time"],
                "completion_time": progress_data["completion_time"],
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "get":
            if not os.path.exists(progress_file):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"任务'{task_name}'的进度文件不存在"
                }
            
            # 读取进度
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            return {
                "status": "success",
                "operation": "get",
                "task_name": task_name,
                "progress_data": progress_data,
                "timestamp": datetime.now().isoformat()
            }
        
        elif operation == "reset":
            if not os.path.exists(progress_file):
                return {
                    "status": "error",
                    "error_type": "FileNotFoundError",
                    "error_message": f"任务'{task_name}'的进度文件不存在"
                }
            
            # 读取现有进度
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # 重置进度
            progress_data["current_step"] = 0
            progress_data["step_description"] = ""
            progress_data["status"] = "reset"
            progress_data["progress_percentage"] = 0
            progress_data["last_update_time"] = datetime.now().isoformat()
            
            # 写入进度文件
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
            # 更新日志
            if log_file and os.path.exists(log_file):
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] 任务'{task_name}'已重置\n")
            
            return {
                "status": "success",
                "operation": "reset",
                "task_name": task_name,
                "progress_percentage": 0,
                "task_status": "reset",
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的操作: {operation}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }