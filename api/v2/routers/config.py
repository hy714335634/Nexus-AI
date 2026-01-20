"""
Config API Router

配置管理相关的 API 端点
"""
from fastapi import APIRouter, HTTPException, Path, Body
from typing import Optional, Dict, Any, List
import logging
import os
import yaml
from datetime import datetime, timezone
import uuid
from pathlib import Path as PathLib

from api.v2.models.schemas import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Config"])

# 配置文件目录 - 使用更可靠的路径计算方式
# 从当前文件向上找到项目根目录
def _get_config_dir() -> str:
    """获取配置目录的绝对路径"""
    # 当前文件: api/v2/routers/config.py
    # 项目根目录: Nexus-AI/
    current_file = PathLib(__file__).resolve()
    # 向上 4 级: config.py -> routers -> v2 -> api -> Nexus-AI
    project_root = current_file.parent.parent.parent.parent
    config_dir = project_root / "config"
    
    logger.info(f"Config directory resolved to: {config_dir}")
    
    return str(config_dir)

CONFIG_DIR = _get_config_dir()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _request_id() -> str:
    return str(uuid.uuid4())


def _get_config_files() -> List[Dict[str, Any]]:
    """获取配置目录下的所有配置文件"""
    files = []
    
    logger.info(f"Looking for config files in: {CONFIG_DIR}")
    
    if not os.path.exists(CONFIG_DIR):
        logger.warning(f"Config directory does not exist: {CONFIG_DIR}")
        return files
    
    try:
        dir_contents = os.listdir(CONFIG_DIR)
        logger.info(f"Directory contents: {dir_contents}")
    except Exception as e:
        logger.error(f"Failed to list directory {CONFIG_DIR}: {e}")
        return files
    
    for filename in dir_contents:
        if filename.endswith(('.yaml', '.yml', '.json')):
            filepath = os.path.join(CONFIG_DIR, filename)
            try:
                stat = os.stat(filepath)
                files.append({
                    'name': filename,
                    'path': f"config/{filename}",
                    'size': stat.st_size,
                    'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace('+00:00', 'Z'),
                    'type': 'yaml' if filename.endswith(('.yaml', '.yml')) else 'json'
                })
                logger.info(f"Found config file: {filename}")
            except Exception as e:
                logger.error(f"Failed to stat file {filepath}: {e}")
    
    return sorted(files, key=lambda x: x['name'])


def _read_config_file(filename: str) -> Dict[str, Any]:
    """读取配置文件内容"""
    filepath = os.path.join(CONFIG_DIR, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"配置文件 {filename} 不存在")
    
    # 安全检查：确保文件在配置目录内
    real_path = os.path.realpath(filepath)
    real_config_dir = os.path.realpath(CONFIG_DIR)
    if not real_path.startswith(real_config_dir):
        raise ValueError("非法的文件路径")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        if filename.endswith(('.yaml', '.yml')):
            return yaml.safe_load(f)
        else:
            import json
            return json.load(f)


def _write_config_file(filename: str, content: Dict[str, Any]) -> None:
    """写入配置文件"""
    filepath = os.path.join(CONFIG_DIR, filename)
    
    # 安全检查：确保文件在配置目录内
    real_path = os.path.realpath(filepath)
    real_config_dir = os.path.realpath(CONFIG_DIR)
    if not real_path.startswith(real_config_dir):
        raise ValueError("非法的文件路径")
    
    # 备份原文件
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak"
        import shutil
        shutil.copy2(filepath, backup_path)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if filename.endswith(('.yaml', '.yml')):
            yaml.dump(content, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            import json
            json.dump(content, f, ensure_ascii=False, indent=2)


@router.get("", response_model=APIResponse)
async def list_config_files():
    """
    获取配置文件列表
    """
    try:
        files = _get_config_files()
        
        return APIResponse(
            success=True,
            data={'files': files, 'config_dir': CONFIG_DIR},
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except Exception as e:
        logger.error(f"Failed to list config files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取配置文件列表失败: {str(e)}")


@router.get("/{filename}", response_model=APIResponse)
async def get_config_file(
    filename: str = Path(..., description="配置文件名")
):
    """
    获取配置文件内容
    """
    try:
        content = _read_config_file(filename)
        
        # 同时返回原始 YAML 文本用于编辑
        filepath = os.path.join(CONFIG_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        return APIResponse(
            success=True,
            data={
                'filename': filename,
                'content': content,
                'raw_content': raw_content,
                'type': 'yaml' if filename.endswith(('.yaml', '.yml')) else 'json'
            },
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read config file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")


@router.put("/{filename}", response_model=APIResponse)
async def update_config_file(
    filename: str = Path(..., description="配置文件名"),
    body: Dict[str, Any] = Body(..., description="配置内容")
):
    """
    更新配置文件
    
    支持两种更新方式：
    1. 传入 content 字段（解析后的对象）
    2. 传入 raw_content 字段（原始文本）
    """
    try:
        if 'raw_content' in body:
            # 使用原始文本更新
            raw_content = body['raw_content']
            filepath = os.path.join(CONFIG_DIR, filename)
            
            # 安全检查
            real_path = os.path.realpath(filepath)
            real_config_dir = os.path.realpath(CONFIG_DIR)
            if not real_path.startswith(real_config_dir):
                raise ValueError("非法的文件路径")
            
            # 验证 YAML 格式
            if filename.endswith(('.yaml', '.yml')):
                try:
                    yaml.safe_load(raw_content)
                except yaml.YAMLError as e:
                    raise HTTPException(status_code=400, detail=f"YAML 格式错误: {str(e)}")
            
            # 备份并写入
            if os.path.exists(filepath):
                import shutil
                shutil.copy2(filepath, f"{filepath}.bak")
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(raw_content)
        
        elif 'content' in body:
            # 使用解析后的对象更新
            _write_config_file(filename, body['content'])
        
        else:
            raise HTTPException(status_code=400, detail="请提供 content 或 raw_content 字段")
        
        return APIResponse(
            success=True,
            message=f"配置文件 {filename} 更新成功",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update config file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新配置文件失败: {str(e)}")


@router.post("/{filename}/validate", response_model=APIResponse)
async def validate_config(
    filename: str = Path(..., description="配置文件名"),
    body: Dict[str, Any] = Body(..., description="要验证的配置内容")
):
    """
    验证配置内容格式
    """
    try:
        raw_content = body.get('raw_content', '')
        
        if filename.endswith(('.yaml', '.yml')):
            try:
                parsed = yaml.safe_load(raw_content)
                return APIResponse(
                    success=True,
                    data={'valid': True, 'parsed': parsed},
                    timestamp=_now(),
                    request_id=_request_id()
                )
            except yaml.YAMLError as e:
                return APIResponse(
                    success=True,
                    data={'valid': False, 'error': str(e)},
                    timestamp=_now(),
                    request_id=_request_id()
                )
        else:
            import json
            try:
                parsed = json.loads(raw_content)
                return APIResponse(
                    success=True,
                    data={'valid': True, 'parsed': parsed},
                    timestamp=_now(),
                    request_id=_request_id()
                )
            except json.JSONDecodeError as e:
                return APIResponse(
                    success=True,
                    data={'valid': False, 'error': str(e)},
                    timestamp=_now(),
                    request_id=_request_id()
                )
    
    except Exception as e:
        logger.error(f"Failed to validate config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证配置失败: {str(e)}")


@router.post("/{filename}/restore", response_model=APIResponse)
async def restore_config_backup(
    filename: str = Path(..., description="配置文件名")
):
    """
    从备份恢复配置文件
    """
    try:
        filepath = os.path.join(CONFIG_DIR, filename)
        backup_path = f"{filepath}.bak"
        
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail=f"备份文件 {filename}.bak 不存在")
        
        # 安全检查
        real_path = os.path.realpath(filepath)
        real_config_dir = os.path.realpath(CONFIG_DIR)
        if not real_path.startswith(real_config_dir):
            raise ValueError("非法的文件路径")
        
        import shutil
        shutil.copy2(backup_path, filepath)
        
        return APIResponse(
            success=True,
            message=f"配置文件 {filename} 已从备份恢复",
            timestamp=_now(),
            request_id=_request_id()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore config backup {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"恢复配置备份失败: {str(e)}")
