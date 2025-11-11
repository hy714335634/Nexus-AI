#!/usr/bin/env python3
"""
工具版本生成器：为 Agent Update Workflow 提供受控的工具脚本生成能力。

功能：
1. 基于项目信息与脚本名称创建 tools/generated_tools/<project>/<version>/ 目录下的新文件
2. 校验工具内容必须包含 @tool 装饰器且符合基本结构
3. 阻止覆盖已有工具脚本，确保更新流程仅创建新版本
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from strands import tool

GENERATED_TOOL_ROOT = Path("tools") / "generated_tools"
TOOL_DECORATOR_PATTERN = re.compile(r"^\s*@tool\b", re.MULTILINE)


def _validate_names(project_name: str, version_id: str, module_name: str) -> None:
    for value, label in [
        (project_name, "project_name"),
        (version_id, "version_id"),
        (module_name, "module_name"),
    ]:
        if not value or value.strip() == "":
            raise ValueError(f"{label} 不能为空")
        if any(token in value for token in ("/", "\\", "..")):
            raise ValueError(f"{label} 包含非法字符")


def _target_directory(project_name: str, version_id: str) -> Path:
    return GENERATED_TOOL_ROOT / project_name / version_id


def _target_file(project_name: str, version_id: str, module_name: str) -> Path:
    directory = _target_directory(project_name, version_id)
    filename = f"{module_name}.py"
    return directory / filename


def _validate_tool_content(content: str) -> None:
    if "@tool(" in content:
        return
    if not TOOL_DECORATOR_PATTERN.search(content):
        raise ValueError("工具脚本必须包含 @tool 装饰器函数")


@tool
def create_versioned_tool(
    project_name: str,
    version_id: str,
    module_name: str,
    content: str,
) -> str:
    """
    创建版本化工具脚本。

    Args:
        project_name: 项目名称
        version_id: 新的版本目录
        module_name: 工具脚本文件名（不含扩展名）
        content: 脚本文本内容（必须包含 @tool 装饰器）
    """
    _validate_names(project_name, version_id, module_name)
    if content is None or content.strip() == "":
        raise ValueError("content 不能为空")

    target_file = _target_file(project_name, version_id, module_name)
    if target_file.exists():
        raise FileExistsError(f"工具脚本已存在，禁止覆盖: {target_file}")

    _validate_tool_content(content)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with target_file.open("w", encoding="utf-8") as fh:
        fh.write(content)

    return json.dumps(
        {
            "result": "success",
            "project_name": project_name,
            "version_id": version_id,
            "module_name": module_name,
            "file_path": str(target_file),
            "bytes_written": len(content.encode("utf-8")),
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def list_version_tools(project_name: str, version_id: Optional[str] = None) -> str:
    """
    列出指定项目版本目录下的工具脚本。
    """
    if not project_name or project_name.strip() == "":
        raise ValueError("project_name 不能为空")
    if any(token in project_name for token in ("/", "\\", "..")):
        raise ValueError("project_name 包含非法字符")

    root = GENERATED_TOOL_ROOT / project_name
    if not root.exists():
        raise FileNotFoundError(f"项目工具目录不存在: {root}")

    def _collect(directory: Path) -> list[str]:
        result: list[str] = []
        for path in sorted(directory.glob("*.py")):
            result.append(str(path))
        return result

    records = []
    if version_id:
        if any(token in version_id for token in ("/", "\\", "..")):
            raise ValueError("version_id 包含非法字符")
        target_dir = root / version_id
        if target_dir.exists():
            records.extend(_collect(target_dir))
    else:
        for child in sorted(root.iterdir()):
            if child.is_dir():
                records.extend(_collect(child))

    return json.dumps(
        {
            "project_name": project_name,
            "version_id": version_id,
            "tool_files": records,
            "count": len(records),
        },
        ensure_ascii=False,
        indent=2,
    )

