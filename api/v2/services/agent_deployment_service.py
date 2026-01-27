"""Services responsible for deploying generated agents to runtime environments."""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

import yaml

from api.v2.config import settings
from api.v2.core.exceptions import APIException
from api.v2.database import db_client
from api.v2.models.schemas import AgentStatus, AgentRecord, AgentCoreConfig

logger = logging.getLogger(__name__)


class AgentDeploymentError(APIException):
    """Raised when an agent deployment fails."""


@dataclass
class DeploymentResult:
    agent_id: str
    project_id: str
    project_name: str
    deployment_type: str
    deployment_status: str
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "deployment_type": self.deployment_type,
            "deployment_status": self.deployment_status,
        }
        payload.update(self.details)
        return payload


class AgentDeploymentService:
    """High-level service to deploy generated agents to AgentCore."""

    def __init__(self) -> None:
        self.db = db_client
        # Use REPO_ROOT env var if available (for EFS mount), otherwise calculate from file location
        self.repo_root = Path(os.getenv("REPO_ROOT", Path(__file__).resolve().parents[3]))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def deploy_to_agentcore(
        self,
        *,
        project_name: str,
        project_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_script_path: Optional[str] = None,
        requirements_path: Optional[str] = None,
        region: Optional[str] = None,
        agent_name_override: Optional[str] = None,
    ) -> DeploymentResult:
        """Deploy the specified agent to Amazon Bedrock AgentCore."""

        project_dir = self.repo_root / "projects" / project_name
        if not project_dir.exists():
            raise AgentDeploymentError(f"项目目录不存在: {project_dir}")

        self._materialize_project_artifacts(
            project_dir,
            project_name,
            project_id or project_name,
            agent_name_override,
        )
        project_config = self._load_project_config(project_dir)

        script_path, prompt_path, tools_path, metadata = self._extract_artifacts(
            project_dir,
            project_config,
            override_script=agent_script_path,
            agent_name_override=agent_name_override,
        )

        resolved_project_id = project_id or project_config.get("project_id") or project_name
        resolved_agent_id = agent_id or self._build_agent_id(
            resolved_project_id,
            metadata.agent_name,
        )

        agent_record = self._ensure_agent_record(
            agent_id=resolved_agent_id,
            project_id=resolved_project_id,
            project_name=project_name,
            script_path=script_path,
            prompt_path=prompt_path,
            tools_path=tools_path,
            metadata=metadata,
        )

        deployment_region = (
            region
            or settings.AGENTCORE_REGION
            or settings.AWS_DEFAULT_REGION
        )

        requirements_file = self._resolve_requirements_path(
            project_dir,
            project_config,
            requirements_path,
        )
        deployment_dir = self._ensure_deployment_directory(project_name, metadata.agent_name)

        # Determine execution parameters
        dry_run = settings.AGENTCORE_DEPLOY_DRY_RUN
        alias = settings.AGENTCORE_DEFAULT_ALIAS or "DEFAULT"
        execution_role_name = settings.AGENTCORE_EXECUTION_ROLE_NAME

        if dry_run:
            logger.info(
                "Dry-run enabled. Skipping actual AgentCore deployment for agent %s",
                resolved_agent_id,
            )
            self._update_agent_record_after_deploy(
                agent_record.agent_id,
                status=AgentStatus.OFFLINE,
                deployment_status="dry_run",
                agentcore_arn=None,
                agentcore_alias=alias,
                region=deployment_region,
                last_deployed_at=datetime.utcnow(),
                last_deployment_error=None,
                deployment_type="agentcore",
            )
            return DeploymentResult(
                agent_id=agent_record.agent_id,
                project_id=agent_record.project_id,
                project_name=project_name,
                deployment_type="agentcore",
                deployment_status="dry_run",
                details={
                    "message": "Dry-run mode: deployment skipped.",
                    "region": deployment_region,
                    "requirements": str(requirements_file),
                    "deployment_directory": str(deployment_dir),
                },
            )

        # Set AWS region environment variable before initializing Runtime
        # This ensures bedrock-agentcore-starter-toolkit uses the correct region
        original_region = os.environ.get("AWS_DEFAULT_REGION")
        os.environ["AWS_DEFAULT_REGION"] = deployment_region
        logger.info("Setting AWS_DEFAULT_REGION=%s for AgentCore deployment", deployment_region)

        try:
            runtime = self._initialize_runtime()

            runtime.configure(
                entrypoint=str(script_path),
                agent_name=metadata.agent_name,
                requirements_file=str(requirements_file) if requirements_file else None,
                requirements=metadata.dependencies or None,
                execution_role=execution_role_name,
                auto_create_execution_role=settings.AGENTCORE_AUTO_CREATE_EXECUTION_ROLE,
                auto_create_ecr=settings.AGENTCORE_AUTO_CREATE_ECR,
                region=deployment_region,
            )

            self._ensure_local_package_installation(project_name)

            # 启用 auto_update_on_conflict 以支持更新已存在的同名 Agent
            launch_result = runtime.launch(
                auto_update_on_conflict=settings.AGENTCORE_AUTO_UPDATE_ON_CONFLICT
            )
            status_response = runtime.status()

            # 部署完成后将生成的配置文件移动到 deployment 目录，保持主目录整洁
            self._archive_deployment_artifacts(deployment_dir)

            agent_runtime_arn = self._extract_runtime_arn(launch_result)
            agent_alias_id = self._extract_agent_alias_id(launch_result)
            agent_alias_arn = self._extract_agent_alias_arn(launch_result)
            deployment_status = self._extract_runtime_status(status_response)

            post_deploy_details: Dict[str, Any] = {
                "agent_runtime_arn": agent_runtime_arn,
                "agent_alias_id": agent_alias_id,
                "agent_alias_arn": agent_alias_arn,
                "status_response": status_response,
                "launch_result": launch_result,
                "region": deployment_region,
                "requirements": str(requirements_file) if requirements_file else None,
                "deployment_directory": str(deployment_dir),
            }

            if settings.AGENTCORE_POST_DEPLOY_TEST and not dry_run and agent_runtime_arn:
                try:
                    invoke_payload = settings.AGENTCORE_POST_DEPLOY_TEST_PROMPT or "Hello"
                    invocation_result = runtime.invoke({"prompt": invoke_payload})
                    post_deploy_details["post_deploy_test"] = {
                        "prompt": invoke_payload,
                        "result": invocation_result,
                    }
                except Exception as exc:  # pragma: no cover - diagnostics only
                    logger.warning(
                        "AgentCore post-deploy invocation failed: %s", exc,
                        extra={"agent_id": agent_record.agent_id},
                    )
                    post_deploy_details["post_deploy_test_error"] = str(exc)

            self._update_agent_record_after_deploy(
                agent_record.agent_id,
                status=AgentStatus.RUNNING,
                deployment_status=deployment_status or "deployed",
                agentcore_arn=agent_runtime_arn,
                agentcore_alias=alias,
                region=deployment_region,
                last_deployed_at=datetime.utcnow(),
                last_deployment_error=None,
                deployment_type="agentcore",
            )

            # Register agent instance after successful deployment (Task 18.2)
            if agent_runtime_arn and agent_alias_id and agent_alias_arn:
                self._register_agent_instance(
                    agent_id=agent_record.agent_id,
                    project_id=agent_record.project_id,
                    agent_name=metadata.agent_name,
                    agent_runtime_arn=agent_runtime_arn,
                    agent_alias_id=agent_alias_id,
                    agent_alias_arn=agent_alias_arn,
                    description=metadata.description,
                    category=metadata.category,
                    region=deployment_region,
                )

            return DeploymentResult(
                agent_id=agent_record.agent_id,
                project_id=agent_record.project_id,
                project_name=project_name,
                deployment_type="agentcore",
                deployment_status=deployment_status or "deployed",
                details=self._stringify_details(post_deploy_details),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("AgentCore deployment failed for %s", agent_record.agent_id)
            # 清理可能残留在主目录的临时文件
            self._cleanup_temp_artifacts_from_root()
            self._update_agent_record_after_deploy(
                agent_record.agent_id,
                status=AgentStatus.OFFLINE,
                deployment_status="failed",
                agentcore_arn=None,
                agentcore_alias=None,
                region=deployment_region,
                last_deployment_error=str(exc),
                deployment_type="local",
            )
            raise AgentDeploymentError(str(exc)) from exc
        finally:
            # Restore original AWS region environment variable
            if original_region is not None:
                os.environ["AWS_DEFAULT_REGION"] = original_region
            elif "AWS_DEFAULT_REGION" in os.environ:
                os.environ.pop("AWS_DEFAULT_REGION")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_project_config(self, project_dir: Path) -> Dict[str, Any]:
        config_path = project_dir / "project_config.json"
        if not config_path.exists():
            raise AgentDeploymentError(f"项目配置不存在: {config_path}")
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise AgentDeploymentError(f"无法解析项目配置文件: {config_path}") from exc

    def _materialize_project_artifacts(
        self,
        project_dir: Path,
        project_name: str,
        project_id: Optional[str],
        agent_name_override: Optional[str],
    ) -> None:
        config_path = project_dir / "project_config.json"
        if config_path.exists():
            return

        logger.info(
            "project_config.json missing for project %s; rebuilding from stage artifacts",
            project_name,
        )

        agents_root = project_dir / "agents"
        if not agents_root.exists():
            raise AgentDeploymentError("项目尚未生成任何Agent阶段文档")

        agent_dirs = [d for d in agents_root.iterdir() if d.is_dir()]
        if not agent_dirs:
            raise AgentDeploymentError("项目尚未生成任何Agent阶段文档")

        target_dir = None
        if agent_name_override:
            for candidate in agent_dirs:
                candidate_name = candidate.name
                if candidate_name == agent_name_override or candidate_name == f"{agent_name_override}_agent":
                    target_dir = candidate
                    break
        if target_dir is None:
            target_dir = agent_dirs[0]

        agent_dir = target_dir
        agent_name = agent_dir.name

        code_json_path = agent_dir / "agent_code_developer.json"
        prompt_json_path = agent_dir / "prompt_engineer.json"
        tools_json_path = agent_dir / "tools_developer.json"

        if not code_json_path.exists():
            raise AgentDeploymentError("缺少 agent_code_developer.json，无法生成Agent代码")

        agent_code_data = json.loads(code_json_path.read_text(encoding="utf-8"))
        agent_code = agent_code_data.get("agent_code") or {}

        prompt_data = {}
        if prompt_json_path.exists():
            prompt_json = json.loads(prompt_json_path.read_text(encoding="utf-8"))
            prompt_data = prompt_json.get("prompt_engineering") or {}

        tools_data: List[Dict[str, Any]] = []
        if tools_json_path.exists():
            tools_json = json.loads(tools_json_path.read_text(encoding="utf-8"))
            tools_data = tools_json.get("tools_development", {}).get("tools", [])

        script_output = self._write_agent_script(project_name, agent_name, agent_code)
        prompt_output = self._write_prompt_file(project_name, agent_name, prompt_data)
        tool_outputs = self._write_tool_files(project_name, tools_data)
        requirements_file = self._ensure_requirements_file(project_dir, agent_code, tools_data)

        project_config = {
            "project_name": project_name,
            "project_id": project_id,
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "agent_scripts": [
                {
                    "script_path": str(script_output.relative_to(self.repo_root)),
                    "syntax_valid": True,
                    "dependencies": agent_code.get("dependencies", []),
                    "error_message": "",
                    "argparse_params": agent_code.get("execution_params") or [],
                }
            ],
            "prompt_files": [
                {
                    "prompt_path": str(prompt_output.relative_to(self.repo_root)) if prompt_output else None,
                    "tool_count": len(tools_data),
                    "valid": True,
                    "error_message": "",
                    "agent_info": {
                        "name": agent_name,
                        "description": agent_code.get("description"),
                        "category": agent_code.get("implementation_details", {}).get("architecture"),
                    },
                    "metadata": {
                        "prompt_variables": prompt_data.get("prompt_variables", []),
                        "tags": prompt_data.get("tags", []),
                    },
                }
            ],
            "generated_tools": [
                {"tool_path": str(path.relative_to(self.repo_root))}
                for path in tool_outputs
            ],
            "requirements_path": str(requirements_file.relative_to(self.repo_root))
            if requirements_file
            else None,
        }

        config_path.write_text(
            json.dumps(project_config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("Generated project_config.json for project %s", project_name)

    @dataclass
    class _ArtifactMetadata:
        agent_name: str
        description: Optional[str]
        category: Optional[str]
        supported_models: Optional[List[str]]
        tags: Optional[List[str]]
        dependencies: Optional[List[str]]

    def _extract_artifacts(
        self,
        project_dir: Path,
        project_config: Dict[str, Any],
        *,
        override_script: Optional[str] = None,
        agent_name_override: Optional[str] = None,
    ) -> tuple[Path, Optional[Path], Optional[Path], "AgentDeploymentService._ArtifactMetadata"]:
        scripts = project_config.get("agent_scripts") or []
        prompts = project_config.get("prompt_files") or []
        tools = project_config.get("generated_tools") or []

        script_entry = None
        if agent_name_override:
            script_entry = next(
                (
                    entry
                    for entry in scripts
                    if self._match_agent_name(entry.get("script_path"), agent_name_override)
                ),
                None,
            )
        if script_entry is None and scripts:
            script_entry = scripts[0]

        if override_script:
            script_path = self._resolve_path(override_script)
        elif script_entry and script_entry.get("script_path"):
            script_path = self._resolve_path(script_entry.get("script_path"))
        else:
            raise AgentDeploymentError("项目配置中缺少 agent 脚本路径信息")

        prompt_entry = None
        if agent_name_override:
            prompt_entry = next(
                (
                    entry
                    for entry in prompts
                    if self._match_agent_name(
                        self._extract_prompt_name(entry),
                        agent_name_override,
                    )
                ),
                None,
            )
        if prompt_entry is None and prompts:
            prompt_entry = prompts[0]

        prompt_path = None
        agent_name = agent_name_override or script_path.stem
        description = None
        category = None
        supported_models = None
        tags = None
        dependencies = script_entry.get("dependencies") if script_entry else None

        if prompt_entry:
            raw_prompt_path = prompt_entry.get("prompt_path")
            if raw_prompt_path:
                prompt_path = self._resolve_path(raw_prompt_path)
            agent_info = prompt_entry.get("agent_info") or {}
            metadata = prompt_entry.get("metadata") or {}
            agent_name = agent_info.get("name") or agent_name
            description = agent_info.get("description")
            category = agent_info.get("category")
            supported_models = metadata.get("supported_models")
            tags = metadata.get("tags")

        tools_entry = None
        if agent_name_override:
            tools_entry = next(
                (
                    entry
                    for entry in tools
                    if self._match_agent_name(entry.get("tool_path"), agent_name_override)
                ),
                None,
            )
        if tools_entry is None and tools:
            tools_entry = tools[0]

        tools_path = None
        if tools_entry:
            raw_tool_path = tools_entry.get("tool_path")
            if raw_tool_path:
                tools_path = self._resolve_path(raw_tool_path)

        return (
            script_path,
            prompt_path,
            tools_path,
            AgentDeploymentService._ArtifactMetadata(
                agent_name=agent_name,
                description=description,
                category=category,
                supported_models=supported_models,
                tags=tags,
                dependencies=dependencies,
            ),
        )

    def _match_agent_name(self, source: Optional[str], target: str) -> bool:
        if not source or not target:
            return False

        candidate = str(source).strip()
        if not candidate:
            return False

        candidate_name = candidate
        if any(sep in candidate for sep in ("/", "\\")) or "." in candidate:
            candidate_name = Path(candidate).stem

        normalized_candidate = candidate_name.replace("-", "_")
        normalized_target = target.replace("-", "_")

        return normalized_candidate == normalized_target or normalized_candidate == f"{normalized_target}_agent"

    def _extract_prompt_name(self, entry: Optional[Dict[str, Any]]) -> Optional[str]:
        if not entry:
            return None

        agent_info = entry.get("agent_info") or {}
        name = agent_info.get("name")
        if name:
            return name

        prompt_path = entry.get("prompt_path")
        if prompt_path:
            return Path(prompt_path).stem

        return None

    def _ensure_local_package_installation(self, project_name: str) -> None:
        """Patch generated Dockerfile so local packages (e.g. nexus_utils) are available."""
        dockerfile_path = self.repo_root / "Dockerfile"
        if not dockerfile_path.exists():
            return

        try:
            dockerfile_content = dockerfile_path.read_text(encoding="utf-8")
        except OSError:
            return

        copy_marker = (
            f"COPY projects/{project_name}/requirements.txt projects/{project_name}/requirements.txt"
        )
        if copy_marker in dockerfile_content and "COPY nexus_utils nexus_utils" not in dockerfile_content:
            dockerfile_content = dockerfile_content.replace(
                copy_marker,
                copy_marker + "\nCOPY nexus_utils nexus_utils",
            )

        install_marker = f"RUN pip install -r projects/{project_name}/requirements.txt"
        if install_marker in dockerfile_content and "pip install ./nexus_utils" in dockerfile_content:
            dockerfile_content = dockerfile_content.replace(
                "\nRUN pip install ./nexus_utils",
                "",
            )

        pythonpath_line = 'ENV PYTHONPATH="/app:/app/nexus_utils:$PYTHONPATH"'
        if pythonpath_line not in dockerfile_content:
            workdir_line = "WORKDIR /app"
            if workdir_line in dockerfile_content:
                dockerfile_content = dockerfile_content.replace(
                    workdir_line,
                    workdir_line + "\n\n" + pythonpath_line,
                )

        # 确保容器内有日志目录（防止 config_loader 权限错误）
        logs_dir_line = "RUN mkdir -p /app/logs && chmod 777 /app/logs"
        if logs_dir_line not in dockerfile_content:
            # 在 COPY nexus_utils 之后添加
            nexus_copy_line = "COPY nexus_utils nexus_utils"
            if nexus_copy_line in dockerfile_content:
                dockerfile_content = dockerfile_content.replace(
                    nexus_copy_line,
                    nexus_copy_line + "\n" + logs_dir_line,
                )

        try:
            dockerfile_path.write_text(dockerfile_content, encoding="utf-8")
        except OSError:
            return

        dockerignore_path = self.repo_root / ".dockerignore"
        if dockerignore_path.exists():
            try:
                lines = dockerignore_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return

            filtered = [
                line
                for line in lines
                if line.strip() not in {"nexus_utils", "nexus_utils/"}
            ]

            if filtered != lines:
                dockerignore_path.write_text("\n".join(filtered) + "\n", encoding="utf-8")

    def _write_agent_script(
        self,
        project_name: str,
        agent_name: str,
        agent_code: Dict[str, Any],
    ) -> Path:
        generated_dir = self.repo_root / "agents" / "generated_agents" / project_name
        generated_dir.mkdir(parents=True, exist_ok=True)

        script_path = generated_dir / f"{agent_name}.py"
        if script_path.exists():
            return script_path

        main_code = agent_code.get("main_code") or "# TODO: implement agent logic\n"
        if not isinstance(main_code, str):
            main_code = str(main_code)

        script_path.write_text(main_code, encoding="utf-8")
        return script_path

    def _write_prompt_file(
        self,
        project_name: str,
        agent_name: str,
        prompt_data: Dict[str, Any],
    ) -> Optional[Path]:
        if not prompt_data:
            return None

        prompts_dir = self.repo_root / "prompts" / "generated_agents_prompts" / project_name
        prompts_dir.mkdir(parents=True, exist_ok=True)

        prompt_path = prompts_dir / f"{agent_name}.yaml"
        if prompt_path.exists():
            return prompt_path

        prompt_payload = prompt_data.get("prompt_definition") or prompt_data
        prompt_path.write_text(
            yaml.safe_dump(prompt_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return prompt_path

    def _write_tool_files(
        self,
        project_name: str,
        tools_data: List[Dict[str, Any]],
    ) -> List[Path]:
        if not tools_data:
            return []

        tools_dir = self.repo_root / "tools" / "generated_tools" / project_name
        tools_dir.mkdir(parents=True, exist_ok=True)

        outputs: List[Path] = []
        for tool in tools_data:
            name = tool.get("name") or tool.get("id")
            if not name:
                continue
            filename = f"{name}.py"
            target = tools_dir / filename
            if target.exists():
                outputs.append(target)
                continue

            code = tool.get("code") or "# TODO: implement tool logic\n"
            if not isinstance(code, str):
                code = str(code)

            target.write_text(code, encoding="utf-8")
            outputs.append(target)

        return outputs

    def _ensure_requirements_file(
        self,
        project_dir: Path,
        agent_code: Dict[str, Any],
        tools_data: List[Dict[str, Any]],
    ) -> Optional[Path]:
        # Baseline dependencies required for all agents
        baseline_deps = {
            "bedrock-agentcore",
            "strands-agents",
            "strands-agents-tools",
            "PyYAML",
        }

        deps = set(baseline_deps)
        deps.update(agent_code.get("dependencies") or [])
        for tool in tools_data:
            deps.update(tool.get("dependencies") or [])

        req_path = project_dir / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)

        req_path.write_text("\n".join(sorted(deps)) + "\n", encoding="utf-8")
        return req_path

    def _ensure_agent_record(
        self,
        *,
        agent_id: str,
        project_id: str,
        project_name: str,
        script_path: Path,
        prompt_path: Optional[Path],
        tools_path: Optional[Path],
        metadata: "AgentDeploymentService._ArtifactMetadata",
    ) -> AgentRecord:
        existing = self.db.get_agent(agent_id)
        if existing:
            return AgentRecord(**existing)

        entrypoint_module = self._to_module_path(script_path)
        now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        
        agent_data = {
            'agent_id': agent_id,
            'project_id': project_id,
            'agent_name': metadata.agent_name,
            'description': metadata.description,
            'category': metadata.category,
            'status': AgentStatus.BUILDING.value,
            'entrypoint': entrypoint_module,
            'agentcore_entrypoint': None,
            'deployment_type': 'local',
            'deployment_status': 'pending',
            'code_path': self._to_relative_path(script_path),
            'prompt_path': self._to_relative_path(prompt_path) if prompt_path else None,
            'tools_path': self._to_relative_path(tools_path) if tools_path else None,
            'dependencies': metadata.dependencies or [],
            'supported_models': metadata.supported_models or [],
            'supported_inputs': ['text'],
            'tags': metadata.tags or [],
            'created_at': now,
        }

        self.db.create_agent(agent_data)
        logger.info("Created agent record %s for project %s", agent_id, project_name)
        return AgentRecord(**agent_data)

    def _update_agent_record_after_deploy(
        self,
        agent_id: str,
        *,
        status: AgentStatus,
        deployment_status: str,
        deployment_type: str,
        agentcore_arn: Optional[str],
        agentcore_alias: Optional[str],
        region: Optional[str],
        last_deployed_at: Optional[datetime] = None,
        last_deployment_error: Optional[str] = None,
    ) -> None:
        updates = {
            'status': status.value,
            'deployment_status': deployment_status,
            'deployment_type': deployment_type,
            'agentcore_runtime_arn': agentcore_arn,
            'agentcore_runtime_alias': agentcore_alias,
            'agentcore_region': region,
        }
        if last_deployed_at:
            updates['last_deployed_at'] = last_deployed_at.isoformat().replace('+00:00', 'Z')
        if last_deployment_error:
            updates['last_deployment_error'] = last_deployment_error
        
        self.db.update_agent(agent_id, updates)

    def _initialize_runtime(self):
        try:
            from bedrock_agentcore_starter_toolkit import Runtime  # type: ignore
        except ImportError as exc:  # pragma: no cover - defensive
            raise AgentDeploymentError(
                "缺少 bedrock-agentcore-starter-toolkit 依赖，请安装后重试"
            ) from exc

        return Runtime()

    def _ensure_deployment_directory(self, project_name: str, agent_name: str) -> Path:
        target = self.repo_root / "deployment" / project_name / agent_name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _archive_deployment_artifacts(self, target_dir: Path) -> None:
        artifacts = [
            ".bedrock_agentcore.yaml",
            ".dockerignore",
            "Dockerfile",
        ]

        for artifact in artifacts:
            source = self.repo_root / artifact
            if source.exists():
                destination = target_dir / artifact
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    destination.unlink()
                shutil.move(str(source), str(destination))

    def _cleanup_temp_artifacts_from_root(self) -> None:
        """清理主目录中可能残留的临时部署文件"""
        artifacts = [
            ".bedrock_agentcore.yaml",
            ".dockerignore",
            "Dockerfile",
        ]

        for artifact in artifacts:
            source = self.repo_root / artifact
            if source.exists():
                try:
                    source.unlink()
                    logger.info("Cleaned up temporary artifact: %s", source)
                except Exception as e:
                    logger.warning("Failed to clean up %s: %s", source, e)

    def _resolve_requirements_path(
        self,
        project_dir: Path,
        project_config: Dict[str, Any],
        override: Optional[str],
    ) -> Path:
        if override:
            path = self._resolve_path(override)
            if path.exists():
                return path

        configured_path = project_config.get("requirements_path")
        if configured_path:
            path = self._resolve_path(configured_path)
            if path.exists():
                return path

        project_requirements = project_dir / "requirements.txt"
        if project_requirements.exists():
            return project_requirements

        default_path = self._resolve_path(settings.AGENTCORE_REQUIREMENTS_PATH)
        if default_path.exists():
            return default_path

        raise AgentDeploymentError("未找到可用的 requirements.txt 文件")

    def _resolve_path(self, relative_path: Optional[str]) -> Path:
        if not relative_path:
            raise AgentDeploymentError("缺少必要的路径参数")
        path = Path(relative_path)
        if not path.is_absolute():
            path = self.repo_root / path
        return path.resolve()

    def _build_agent_id(self, project_id: str, agent_name: str) -> str:
        return f"{project_id}:{agent_name}"

    def _build_image_tag(self, agent_name: str) -> str:
        template = settings.AGENTCORE_IMAGE_TAG_TEMPLATE or "{agent_name}:{timestamp}"
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return template.format(agent_name=agent_name, timestamp=timestamp)

    def _extract_runtime_arn(self, launch_result: Any) -> Optional[str]:
        if launch_result is None:
            return None
        if isinstance(launch_result, dict):
            return launch_result.get("agent_arn") or launch_result.get("agentRuntimeArn")
        return getattr(launch_result, "agent_arn", None) or getattr(launch_result, "agentRuntimeArn", None)

    def _extract_agent_alias_id(self, launch_result: Any) -> Optional[str]:
        """Extract agent_alias_id from launch result

        Requirements: 4.1
        """
        if launch_result is None:
            return None
        if isinstance(launch_result, dict):
            return launch_result.get("agent_alias_id") or launch_result.get("agentAliasId")
        return getattr(launch_result, "agent_alias_id", None) or getattr(launch_result, "agentAliasId", None)

    def _extract_agent_alias_arn(self, launch_result: Any) -> Optional[str]:
        """Extract agent_alias_arn from launch result

        Requirements: 4.1
        """
        if launch_result is None:
            return None
        if isinstance(launch_result, dict):
            return launch_result.get("agent_alias_arn") or launch_result.get("agentAliasArn")
        return getattr(launch_result, "agent_alias_arn", None) or getattr(launch_result, "agentAliasArn", None)

    def _extract_runtime_status(self, status_response: Any) -> Optional[str]:
        if status_response is None:
            return None
        if isinstance(status_response, dict):
            endpoint = status_response.get("endpoint")
            if isinstance(endpoint, dict):
                return endpoint.get("status")
            return status_response.get("status")
        endpoint = getattr(status_response, "endpoint", None)
        if endpoint is not None:
            return getattr(endpoint, "status", None)
        return getattr(status_response, "status", None)

    def _stringify_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        for key, value in details.items():
            if isinstance(value, (str, int, float, type(None))):
                payload[key] = value
            elif isinstance(value, Path):
                payload[key] = str(value)
            else:
                try:
                    payload[key] = json.loads(json.dumps(value, default=str))
                except Exception:  # pragma: no cover - defensive
                    payload[key] = str(value)
        return payload

    def _to_module_path(self, script_path: Path) -> str:
        try:
            relative = script_path.relative_to(self.repo_root)
        except ValueError:
            relative = script_path
        module = str(relative).replace("/", ".").replace("\\", ".")
        if module.endswith(".py"):
            module = module[:-3]
        return module

    def _to_relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:  # pragma: no cover - defensive
            return str(path)

    def _register_agent_instance(
        self,
        *,
        agent_id: str,
        project_id: str,
        agent_name: str,
        agent_runtime_arn: str,
        agent_alias_id: str,
        agent_alias_arn: str,
        description: Optional[str],
        category: Optional[str],
        region: Optional[str],
    ) -> None:
        """
        Register agent instance after successful deployment.

        Creates AgentInstances record with AgentCore configuration.
        Requirements: 4.1 (Task 18.2)
        """
        try:
            # Import here to avoid circular dependency
            from api.v2.services.agent_service import agent_service

            # Create AgentCore configuration
            agentcore_config = AgentCoreConfig(
                agent_arn=agent_runtime_arn,
                agent_alias_id=agent_alias_id,
                agent_alias_arn=agent_alias_arn,
            )

            # Extract capabilities from agent design
            capabilities = self._extract_capabilities(project_id, agent_name)

            # Register agent instance
            logger.info(
                "Registering agent instance %s after successful deployment",
                agent_id
            )

            agent_service.register_agent(
                agent_id=agent_id,
                project_id=project_id,
                agent_name=agent_name,
                agentcore_config=agentcore_config,
                capabilities=capabilities,
                description=description,
                category=category,
                region=region,
            )

            logger.info("Successfully registered agent instance %s", agent_id)
        except Exception as exc:
            # Log error but don't fail deployment
            logger.error(
                "Failed to register agent instance %s: %s",
                agent_id,
                str(exc),
                exc_info=True
            )

    def _extract_capabilities(self, project_id: str, agent_name: str) -> List[str]:
        """
        Extract capabilities from agent design.

        Looks for agent_designer.json in project artifacts to extract capabilities.
        Requirements: 4.1 (Task 18.2)
        """
        try:
            # Try to find agent design file
            project_name = project_id.split(":")[0] if ":" in project_id else project_id
            project_dir = self.repo_root / "projects" / project_name
            agents_dir = project_dir / "agents"

            if not agents_dir.exists():
                logger.warning(
                    "Agents directory not found for project %s, returning empty capabilities",
                    project_id
                )
                return []

            # Find agent directory
            agent_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
            target_dir = None
            for candidate in agent_dirs:
                candidate_name = candidate.name
                if candidate_name == agent_name or candidate_name == f"{agent_name}_agent":
                    target_dir = candidate
                    break

            if not target_dir:
                target_dir = agent_dirs[0] if agent_dirs else None

            if not target_dir:
                logger.warning("No agent directory found for %s", agent_name)
                return []

            # Load agent designer JSON
            designer_json_path = target_dir / "agent_designer.json"
            if not designer_json_path.exists():
                logger.warning("agent_designer.json not found for %s", agent_name)
                return []

            designer_data = json.loads(designer_json_path.read_text(encoding="utf-8"))
            agent_design = designer_data.get("agent_design") or {}

            # Extract capabilities from various fields
            capabilities = set()

            # From capabilities field
            if "capabilities" in agent_design:
                caps = agent_design["capabilities"]
                if isinstance(caps, list):
                    capabilities.update(caps)
                elif isinstance(caps, str):
                    capabilities.add(caps)

            # From tools/actions
            if "tools" in agent_design:
                tools = agent_design["tools"]
                if isinstance(tools, list):
                    for tool in tools:
                        if isinstance(tool, dict) and "name" in tool:
                            capabilities.add(f"tool:{tool['name']}")
                        elif isinstance(tool, str):
                            capabilities.add(f"tool:{tool}")

            # From supported operations
            if "supported_operations" in agent_design:
                ops = agent_design["supported_operations"]
                if isinstance(ops, list):
                    capabilities.update(ops)

            logger.info(
                "Extracted %d capabilities for agent %s: %s",
                len(capabilities),
                agent_name,
                list(capabilities)
            )

            return list(capabilities)
        except Exception as exc:
            logger.error(
                "Failed to extract capabilities for agent %s: %s",
                agent_name,
                str(exc),
                exc_info=True
            )
            return []


__all__ = [
    "AgentDeploymentService",
    "AgentDeploymentError",
    "DeploymentResult",
]
