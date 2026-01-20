"""
Message definitions for internationalization

All user-facing strings are defined here in a structured format.
To add a new language, add a new key to MESSAGES dict.
To add a new message, add it to ALL language sections to maintain consistency.
"""

from typing import Optional

# Current language setting
_current_language = 'en'

# Message definitions - all languages must have the same keys
MESSAGES = {
    'en': {
        # Common messages
        'common': {
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'aborted': 'Aborted.',
            'operation_cancelled': 'Operation cancelled.',
            'confirm_continue': 'Are you sure you want to continue?',
            'dry_run_header': '[DRY RUN] Would perform the following operations:',
            'run_without_dry_run': 'Run without --dry-run to execute these operations.',
            'total_items_removed': 'Total: {count} items removed',
            'not_found': "'{name}' not found",
            'missing_dependency': 'Missing dependency - {error}',
            'import_error': 'Cannot import API configuration. Make sure you are in the Nexus-AI directory.',
        },
        
        # Init command messages
        'init': {
            'title': 'Nexus-AI Infrastructure Initialization',
            'init_tables': 'Initializing DynamoDB tables...',
            'init_queues': 'Initializing SQS queues...',
            'region': 'Region: {region}',
            'endpoint': 'Endpoint: {endpoint}',
            'table_exists': 'Table exists: {name}',
            'table_created': 'Created table: {name}',
            'queue_exists': 'Queue exists: {name}',
            'queue_created': 'Created queue: {name}',
            'tables_created_count': 'Created {count} new tables',
            'queues_created_count': 'Created {count} new queues',
            'complete': 'Initialization complete!',
        },
        
        # Job command messages
        'job': {
            'clear_title': 'Nexus-AI Data Cleanup Tool',
            'delete_title': 'Delete Data for Agent: {name}',
            'list_title': 'Nexus-AI Task List',
            'view_title': 'Task Details: {id}',
            'clear_warning': 'WARNING: This will delete ALL data and cannot be undone!',
            'delete_warning': "WARNING: This will delete ALL data for agent '{name}'!",
            'clearing_tables': 'Clearing DynamoDB tables...',
            'clearing_queues': 'Clearing SQS queues...',
            'clearing_table': 'Clearing table: {name} (keys: {keys})',
            'clearing_queue': 'Clearing queue: {name}',
            'table_not_found': 'Table not found, skipping',
            'queue_not_found': 'Queue not found, skipping',
            'queue_purge_in_progress': 'Purge already in progress, skipping',
            'deleted_records': 'Deleted {count} records',
            'queue_cleared': 'Queue cleared',
            'total_deleted': 'Total deleted: {count} records',
            'queues_cleared': 'Cleared {count} queues',
            'cleanup_complete': 'Data cleanup complete!',
            'finding_agent': "Finding agent records for '{name}'...",
            'found_agents': 'Found {count} agent record(s)',
            'no_exact_match': 'No exact matches found, will try: {name}',
            'deleting_from_table': 'Deleting from {table} table...',
            'deleted_agent': 'Deleted agent: {id}',
            'deleted_invocations': 'Deleted {count} invocations for {id}',
            'deleted_sessions': 'Deleted {count} sessions for {id}',
            'deleted_messages': 'Deleted {count} messages',
            'delete_complete': "Deleted {count} total records for agent '{name}'",
            'no_tasks': 'No tasks found',
            'task_not_found': "Task '{id}' not found",
            'tasks_found': 'Found {count} task(s)',
            'filter_status': 'Status filter: {status}',
            'filter_type': 'Type filter: {type}',
            'queue_stats_title': 'Queue Statistics',
            'queue_name': 'Queue: {name}',
            'queue_messages': 'Messages: {available} available, {in_flight} in flight, {delayed} delayed',
            'queue_not_exists': 'Queue does not exist',
        },
        
        # Agents delete command messages
        'agents_delete': {
            'deleting': "Deleting agent '{name}' and all related resources...",
            'local_dirs_to_delete': 'Local directories to be deleted:',
            'cloud_resources_detected': 'Cloud resources detected:',
            'cloud_will_delete': 'Cloud resources WILL be deleted (--include-cloud specified)',
            'cloud_will_not_delete': 'Cloud resources will NOT be deleted (use --include-cloud to delete)',
            'dirs_not_exist': 'Directories that do not exist (will be skipped):',
            'all_dirs_exist': '(all directories exist)',
            'cloud_warning_header': 'Cloud resources detected for this agent:',
            'cloud_not_deleted_hint': 'These cloud resources will NOT be deleted.',
            'cloud_use_flag_hint': 'Use --include-cloud to delete them as well.',
            'delete_warning': "WARNING: This will permanently delete agent '{name}' and ALL related resources",
            'dirs_to_delete': 'The following will be deleted:',
            'cloud_to_delete': 'Cloud resources to be deleted:',
            'deleting_cloud': 'Deleting cloud resources...',
            'deleting_local': 'Deleting local directories...',
            'deleted_dir': 'Deleted {type}: {path}/',
            'failed_delete_dir': 'Failed to delete {path}/: {error}',
            'delete_success': "Agent '{name}' and all related resources deleted successfully",
            'not_found': "Agent '{name}' not found (no related directories or cloud resources exist)",
            'checked_locations': 'Checked locations:',
            'agentcore_runtime': 'AgentCore Runtime: {arn}',
            'ecr_repository': 'ECR Repository: {name}',
            'deleted_agentcore': 'Deleted AgentCore runtime: {name}',
            'deleted_ecr': 'Deleted ECR repository: {name} ({count} images)',
            'failed_delete_agentcore': 'Failed to delete AgentCore runtime: {error}',
            'failed_delete_ecr': 'Failed to delete ECR repository: {error}',
            'boto3_not_available': 'boto3 not available, cannot delete cloud resources',
        },
        
        # Cloud resource messages
        'cloud': {
            'region': 'Region: {region}',
            'status': 'Status: {status}',
            'uri': 'URI: {uri}',
            'images': 'Images: {count}',
        },
        
        # Agents build command messages
        'agents_build': {
            'title': 'Deploy Agent to AgentCore',
            'checking_project': "Checking project '{name}'...",
            'project_not_found': "Project '{name}' not found",
            'project_status': 'Project Status',
            'project_id': 'Project ID: {id}',
            'current_stage': 'Current Stage: {stage}',
            'db_status': 'DB Status: {status}',
            'existing_deployment': 'Existing Deployment',
            'deployment_type': 'Type: {type}',
            'deployment_status': 'Status: {status}',
            'agent_runtime_arn': 'Runtime ARN: {arn}',
            'readiness_check': 'Readiness Check',
            'check_passed': '✓ {item}',
            'check_failed': '✗ {item}',
            'project_ready': 'Project is ready for deployment',
            'project_not_ready': 'Project is not ready for deployment',
            'issues_found': 'Issues found:',
            'dry_run_complete': 'Dry run completed successfully',
            'dry_run_details': 'Deployment would proceed with:',
            'deploying': "Deploying '{name}' to AgentCore...",
            'deploy_region': 'Region: {region}',
            'deploy_progress': 'This may take several minutes...',
            'deploy_success': 'Deployment successful!',
            'deploy_failed': 'Deployment failed',
            'result_agent_id': 'Agent ID: {id}',
            'result_runtime_arn': 'Runtime ARN: {arn}',
            'result_alias_arn': 'Alias ARN: {arn}',
            'result_status': 'Status: {status}',
            'updating_db': 'Updating project status in database...',
            'db_updated': 'Database updated',
            'confirm_deploy': 'Deploy this agent to AgentCore?',
            'confirm_redeploy': 'Agent is already deployed. Redeploy?',
        },
    },
    
    'zh': {
        # 通用消息
        'common': {
            'success': '成功',
            'error': '错误',
            'warning': '警告',
            'aborted': '已取消。',
            'operation_cancelled': '操作已取消。',
            'confirm_continue': '确定要继续吗？',
            'dry_run_header': '[模拟运行] 将执行以下操作：',
            'run_without_dry_run': '移除 --dry-run 参数以执行实际操作。',
            'total_items_removed': '共删除 {count} 个项目',
            'not_found': "'{name}' 未找到",
            'missing_dependency': '缺少依赖 - {error}',
            'import_error': '无法导入 API 配置。请确保在 Nexus-AI 目录中运行。',
        },
        
        # Init 命令消息
        'init': {
            'title': 'Nexus-AI 基础设施初始化',
            'init_tables': '正在初始化 DynamoDB 表...',
            'init_queues': '正在初始化 SQS 队列...',
            'region': '区域: {region}',
            'endpoint': '端点: {endpoint}',
            'table_exists': '表已存在: {name}',
            'table_created': '创建表: {name}',
            'queue_exists': '队列已存在: {name}',
            'queue_created': '创建队列: {name}',
            'tables_created_count': '新建 {count} 个表',
            'queues_created_count': '新建 {count} 个队列',
            'complete': '初始化完成！',
        },
        
        # Job 命令消息
        'job': {
            'clear_title': 'Nexus-AI 数据清理工具',
            'delete_title': '删除 Agent 数据: {name}',
            'list_title': 'Nexus-AI 任务列表',
            'view_title': '任务详情: {id}',
            'clear_warning': '警告: 此操作将删除所有数据，无法恢复！',
            'delete_warning': "警告: 此操作将删除 Agent '{name}' 的所有数据！",
            'clearing_tables': '正在清空 DynamoDB 表...',
            'clearing_queues': '正在清空 SQS 队列...',
            'clearing_table': '清空表: {name} (主键: {keys})',
            'clearing_queue': '清空队列: {name}',
            'table_not_found': '表不存在，跳过',
            'queue_not_found': '队列不存在，跳过',
            'queue_purge_in_progress': '队列正在清空中，跳过',
            'deleted_records': '已删除 {count} 条记录',
            'queue_cleared': '队列已清空',
            'total_deleted': '总计删除 {count} 条记录',
            'queues_cleared': '已清空 {count} 个队列',
            'cleanup_complete': '数据清理完成！',
            'finding_agent': "正在查找 Agent '{name}' 的记录...",
            'found_agents': '找到 {count} 条 Agent 记录',
            'no_exact_match': '未找到精确匹配，将尝试: {name}',
            'deleting_from_table': '正在从 {table} 表删除...',
            'deleted_agent': '已删除 Agent: {id}',
            'deleted_invocations': '已删除 {count} 条调用记录 ({id})',
            'deleted_sessions': '已删除 {count} 条会话记录 ({id})',
            'deleted_messages': '已删除 {count} 条消息',
            'delete_complete': "已删除 Agent '{name}' 的 {count} 条记录",
            'no_tasks': '未找到任务',
            'task_not_found': "任务 '{id}' 未找到",
            'tasks_found': '找到 {count} 个任务',
            'filter_status': '状态筛选: {status}',
            'filter_type': '类型筛选: {type}',
            'queue_stats_title': '队列统计',
            'queue_name': '队列: {name}',
            'queue_messages': '消息: {available} 可用, {in_flight} 处理中, {delayed} 延迟',
            'queue_not_exists': '队列不存在',
        },
        
        # Agents delete 命令消息
        'agents_delete': {
            'deleting': "正在删除 Agent '{name}' 及所有相关资源...",
            'local_dirs_to_delete': '将删除的本地目录:',
            'cloud_resources_detected': '检测到云资源:',
            'cloud_will_delete': '云资源将被删除 (已指定 --include-cloud)',
            'cloud_will_not_delete': '云资源不会被删除 (使用 --include-cloud 删除)',
            'dirs_not_exist': '不存在的目录 (将跳过):',
            'all_dirs_exist': '(所有目录都存在)',
            'cloud_warning_header': '检测到此 Agent 的云资源:',
            'cloud_not_deleted_hint': '这些云资源不会被删除。',
            'cloud_use_flag_hint': '使用 --include-cloud 参数一并删除。',
            'delete_warning': "警告: 此操作将永久删除 Agent '{name}' 及所有相关资源",
            'dirs_to_delete': '将删除以下内容:',
            'cloud_to_delete': '将删除的云资源:',
            'deleting_cloud': '正在删除云资源...',
            'deleting_local': '正在删除本地目录...',
            'deleted_dir': '已删除 {type}: {path}/',
            'failed_delete_dir': '删除 {path}/ 失败: {error}',
            'delete_success': "Agent '{name}' 及所有相关资源已成功删除",
            'not_found': "Agent '{name}' 未找到 (无相关目录或云资源)",
            'checked_locations': '已检查的位置:',
            'agentcore_runtime': 'AgentCore 运行时: {arn}',
            'ecr_repository': 'ECR 仓库: {name}',
            'deleted_agentcore': '已删除 AgentCore 运行时: {name}',
            'deleted_ecr': '已删除 ECR 仓库: {name} ({count} 个镜像)',
            'failed_delete_agentcore': '删除 AgentCore 运行时失败: {error}',
            'failed_delete_ecr': '删除 ECR 仓库失败: {error}',
            'boto3_not_available': 'boto3 不可用，无法删除云资源',
        },
        
        # 云资源消息
        'cloud': {
            'region': '区域: {region}',
            'status': '状态: {status}',
            'uri': 'URI: {uri}',
            'images': '镜像数: {count}',
        },
        
        # Agents build 命令消息
        'agents_build': {
            'title': '部署 Agent 到 AgentCore',
            'checking_project': "正在检查项目 '{name}'...",
            'project_not_found': "项目 '{name}' 未找到",
            'project_status': '项目状态',
            'project_id': '项目 ID: {id}',
            'current_stage': '当前阶段: {stage}',
            'db_status': '数据库状态: {status}',
            'existing_deployment': '现有部署',
            'deployment_type': '类型: {type}',
            'deployment_status': '状态: {status}',
            'agent_runtime_arn': '运行时 ARN: {arn}',
            'readiness_check': '就绪检查',
            'check_passed': '✓ {item}',
            'check_failed': '✗ {item}',
            'project_ready': '项目已准备好部署',
            'project_not_ready': '项目尚未准备好部署',
            'issues_found': '发现问题:',
            'dry_run_complete': '模拟运行完成',
            'dry_run_details': '部署将使用以下配置:',
            'deploying': "正在部署 '{name}' 到 AgentCore...",
            'deploy_region': '区域: {region}',
            'deploy_progress': '这可能需要几分钟...',
            'deploy_success': '部署成功！',
            'deploy_failed': '部署失败',
            'result_agent_id': 'Agent ID: {id}',
            'result_runtime_arn': '运行时 ARN: {arn}',
            'result_alias_arn': '别名 ARN: {arn}',
            'result_status': '状态: {status}',
            'updating_db': '正在更新数据库中的项目状态...',
            'db_updated': '数据库已更新',
            'confirm_deploy': '确定要将此 Agent 部署到 AgentCore 吗？',
            'confirm_redeploy': 'Agent 已部署。确定要重新部署吗？',
        },
    },
}


def set_language(lang: str) -> None:
    """Set the current language"""
    global _current_language
    if lang in MESSAGES:
        _current_language = lang
    else:
        raise ValueError(f"Unsupported language: {lang}. Available: {list(MESSAGES.keys())}")


def get_current_language() -> str:
    """Get the current language"""
    return _current_language


def get_message(key: str, **kwargs) -> str:
    """
    Get a translated message by key.
    
    Args:
        key: Dot-separated key path (e.g., 'init.creating_table')
        **kwargs: Format arguments for the message
    
    Returns:
        Translated and formatted message string
    
    Example:
        get_message('init.table_created', name='nexus_agents')
        # Returns: 'Created table: nexus_agents' (en) or '创建表: nexus_agents' (zh)
    """
    messages = MESSAGES.get(_current_language, MESSAGES['en'])
    
    # Navigate nested keys
    parts = key.split('.')
    value = messages
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            # Fallback to English if key not found
            value = MESSAGES['en']
            for p in parts:
                if isinstance(value, dict) and p in value:
                    value = value[p]
                else:
                    return f"[Missing: {key}]"
            break
    
    # Format with kwargs if it's a string
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    return value if isinstance(value, str) else f"[Invalid: {key}]"
