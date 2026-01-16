#!/bin/bash
# ============================================================================
# HCLS Newsletter Agent 定时任务脚本
# 功能：每周二、周五自动采集生命科学行业新闻并生成报告
# ============================================================================
#
# 【使用方法】
#
# 1. 添加执行权限：
#    chmod +x agents/generated_agents/lifescience_news_collector/run_newsletter.sh
#
# 2. 手动测试运行（在 Nexus-AI 目录下）：
#    ./agents/generated_agents/lifescience_news_collector/run_newsletter.sh
#
# 3. 配置 Crontab（每周二、周五中午12点 UTC+8）：
#    crontab -e
#    添加以下行：
#    0 12 * * 2,5 /home/ec2-user/Nexus-AI/agents/generated_agents/lifescience_news_collector/run_newsletter.sh
#
# 4. 查看已配置的定时任务：
#    crontab -l
#
# 5. 查看执行日志：
#    tail -f ~/Nexus-AI/logs/lifescience_news_collector/newsletter_*.log
#
# ============================================================================

# 获取脚本所在目录，推导项目根目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# 日志目录
LOG_DIR="${PROJECT_DIR}/logs/lifescience_news_collector"
LOG_FILE="${LOG_DIR}/newsletter_$(date +%Y%m%d_%H%M%S).log"

# 确保日志目录存在
mkdir -p "${LOG_DIR}"

# 进入项目目录
cd "${PROJECT_DIR}"

# 激活虚拟环境
source .venv/bin/activate

# 执行 Agent
echo "========== Newsletter Agent 开始执行 $(date) ==========" >> "${LOG_FILE}"

python -u agents/generated_agents/lifescience_news_collector/lifescience_news_collector.py -i "采集过去7天生命科学行业新闻，要求：
1. 每个分类至少5篇文章，优先AI制药、出海、新药研发、生成式AI行业应用方向
2. 必须提供文章详情页URL（非首页/列表页）
3. 摘要需包含涉及的公司名称和关键数据
4. 生成完整HTML报告并上传S3
注意:收集信息及生成的报告尽量完整、全面，不要简化最终的报告" >> "${LOG_FILE}" 2>&1

echo "========== Newsletter Agent 执行完成 $(date) ==========" >> "${LOG_FILE}"
