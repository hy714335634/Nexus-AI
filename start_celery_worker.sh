#!/bin/bash

echo "🚀 启动 Celery Worker"
echo "===================="

# 激活虚拟环境并启动Celery worker
source venv/bin/activate && celery -A api.core.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --queues=agent_builds,status_updates,default \
  --hostname=worker@%h