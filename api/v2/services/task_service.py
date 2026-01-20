"""
Task Service - 任务管理服务

职责:
- 查询任务状态
- 更新任务状态
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from api.v2.database import db_client
from api.v2.models.schemas import TaskStatus

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""
    
    def __init__(self):
        self.db = db_client
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        return self.db.get_task(task_id)
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新任务状态"""
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        updates = {'status': status.value}
        
        if status == TaskStatus.RUNNING:
            updates['started_at'] = now
            if worker_id:
                updates['worker_id'] = worker_id
        
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            updates['completed_at'] = now
        
        if result is not None:
            updates['result'] = result
        
        if error_message:
            updates['error_message'] = error_message
        
        return self.db.update_task(task_id, updates)
    
    def increment_retry_count(self, task_id: str) -> Dict[str, Any]:
        """增加重试计数"""
        task = self.db.get_task(task_id)
        if task:
            retry_count = task.get('retry_count', 0) + 1
            return self.db.update_task(task_id, {'retry_count': retry_count})
        return {}


# 全局单例
task_service = TaskService()
