#!/bin/bash
# ============================================
# DynamoDB连接诊断脚本
# ============================================

set -e

cd "$(dirname "$0")/.."

echo "🔍 DynamoDB连接诊断"
echo "=========================================="
echo ""

REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "nexus-ai-cluster-prod")
SERVICE_NAME="nexus-ai-api-prod"

echo "📊 基本信息"
echo "  区域: $REGION"
echo "  集群: $CLUSTER_NAME"
echo "  服务: $SERVICE_NAME"
echo ""

# 1. 检查DynamoDB表
echo "1️⃣  检查DynamoDB表..."
TABLES=(
  "AgentProjects"
  "AgentInstances"
  "AgentInvocations"
  "AgentSessions"
  "AgentSessionMessages"
)

for TABLE in "${TABLES[@]}"; do
  STATUS=$(aws dynamodb describe-table \
    --table-name "$TABLE" \
    --region "$REGION" \
    --query 'Table.TableStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")
  
  if [ "$STATUS" = "ACTIVE" ]; then
    echo "  ✅ $TABLE: ACTIVE"
  elif [ "$STATUS" = "NOT_FOUND" ]; then
    echo "  ❌ $TABLE: 不存在"
  else
    echo "  ⚠️  $TABLE: $STATUS"
  fi
done
echo ""

# 2. 检查Task Role
echo "2️⃣  检查ECS Task Role..."
TASK_ROLE_NAME="nexus-ai-ecs-task-prod"

# 检查角色是否存在
ROLE_ARN=$(aws iam get-role \
  --role-name "$TASK_ROLE_NAME" \
  --query 'Role.Arn' \
  --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
  echo "  ❌ Task Role '$TASK_ROLE_NAME' 不存在"
else
  echo "  ✅ Task Role: $ROLE_ARN"
  
  # 检查策略
  POLICIES=$(aws iam list-role-policies \
    --role-name "$TASK_ROLE_NAME" \
    --query 'PolicyNames' \
    --output text 2>/dev/null || echo "")
  
  if echo "$POLICIES" | grep -q "dynamodb"; then
    echo "  ✅ 找到DynamoDB策略"
    
    # 检查策略内容
    DYNAMODB_POLICY=$(aws iam list-role-policies \
      --role-name "$TASK_ROLE_NAME" \
      --query 'PolicyNames[?contains(@, `dynamodb`)]' \
      --output text 2>/dev/null | head -1)
    
    if [ -n "$DYNAMODB_POLICY" ]; then
      echo "  📋 策略名称: $DYNAMODB_POLICY"
      
      # 检查ListTables权限
      POLICY_JSON=$(aws iam get-role-policy \
        --role-name "$TASK_ROLE_NAME" \
        --policy-name "$DYNAMODB_POLICY" \
        --query 'PolicyDocument' \
        --output json 2>/dev/null)
      
      if echo "$POLICY_JSON" | grep -q "ListTables"; then
        # 检查是否有Resource = "*"的ListTables权限
        LIST_TABLES_STMT=$(echo "$POLICY_JSON" | jq -r '.Statement[] | select(.Action[]? == "dynamodb:ListTables" or (.Action | type == "array" and any(. == "dynamodb:ListTables"))) | .Resource' 2>/dev/null || echo "")
        
        if echo "$LIST_TABLES_STMT" | grep -q "\"*\"" || echo "$LIST_TABLES_STMT" | grep -q '"\*"'; then
          echo "  ✅ ListTables权限配置正确 (Resource = *)"
        else
          echo "  ⚠️  ListTables权限可能未正确配置 (需要Resource = *)"
        fi
      else
        echo "  ❌ 策略中未找到ListTables权限"
      fi
    fi
  else
    echo "  ❌ 未找到DynamoDB策略"
  fi
fi
echo ""

# 3. 检查Task Definition
echo "3️⃣  检查ECS Task Definition..."
TASK_DEF_ARN=$(aws ecs describe-services \
  --cluster "$CLUSTER_NAME" \
  --services "$SERVICE_NAME" \
  --region "$REGION" \
  --query 'services[0].taskDefinition' \
  --output text 2>/dev/null || echo "")

if [ -z "$TASK_DEF_ARN" ]; then
  echo "  ❌ 无法获取Task Definition"
else
  echo "  ✅ Task Definition: $TASK_DEF_ARN"
  
  TASK_ROLE_ARN=$(aws ecs describe-task-definition \
    --task-definition "$TASK_DEF_ARN" \
    --region "$REGION" \
    --query 'taskDefinition.taskRoleArn' \
    --output text 2>/dev/null || echo "")
  
  if [ -z "$TASK_ROLE_ARN" ]; then
    echo "  ❌ Task Definition中未配置Task Role"
  else
    echo "  ✅ Task Role ARN: $TASK_ROLE_ARN"
    
    # 验证是否匹配
    if echo "$TASK_ROLE_ARN" | grep -q "$TASK_ROLE_NAME"; then
      echo "  ✅ Task Role名称匹配"
    else
      echo "  ⚠️  Task Role名称可能不匹配"
    fi
  fi
  
  # 检查环境变量
  DYNAMODB_REGION=$(aws ecs describe-task-definition \
    --task-definition "$TASK_DEF_ARN" \
    --region "$REGION" \
    --query 'taskDefinition.containerDefinitions[0].environment[?name==`DYNAMODB_REGION`].value' \
    --output text 2>/dev/null || echo "")
  
  if [ -n "$DYNAMODB_REGION" ]; then
    echo "  ✅ DYNAMODB_REGION: $DYNAMODB_REGION"
  else
    echo "  ⚠️  DYNAMODB_REGION环境变量未设置"
  fi
fi
echo ""

# 4. 检查运行中的任务
echo "4️⃣  检查运行中的ECS任务..."
TASK_ARNS=$(aws ecs list-tasks \
  --cluster "$CLUSTER_NAME" \
  --service-name "$SERVICE_NAME" \
  --region "$REGION" \
  --query 'taskArns[]' \
  --output text 2>/dev/null || echo "")

if [ -z "$TASK_ARNS" ]; then
  echo "  ⚠️  没有运行中的任务"
else
  TASK_COUNT=$(echo "$TASK_ARNS" | wc -w | tr -d ' ')
  echo "  ✅ 找到 $TASK_COUNT 个运行中的任务"
  
  # 检查第一个任务的健康状态
  FIRST_TASK=$(echo "$TASK_ARNS" | awk '{print $1}')
  TASK_STATUS=$(aws ecs describe-tasks \
    --cluster "$CLUSTER_NAME" \
    --tasks "$FIRST_TASK" \
    --region "$REGION" \
    --query 'tasks[0].lastStatus' \
    --output text 2>/dev/null || echo "UNKNOWN")
  
  echo "  📋 第一个任务状态: $TASK_STATUS"
fi
echo ""

# 5. 测试API连接
echo "5️⃣  测试API连接..."
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")

if [ -z "$ALB_DNS" ]; then
  echo "  ⚠️  无法获取ALB DNS名称"
else
  echo "  📋 ALB DNS: $ALB_DNS"
  
  HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time 10 \
    "http://$ALB_DNS/api/v1/statistics/overview" 2>/dev/null || echo "000")
  
  if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ API响应正常 (HTTP $HTTP_CODE)"
  elif [ "$HTTP_CODE" = "500" ]; then
    echo "  ❌ API返回500错误 (可能是DynamoDB连接问题)"
    
    # 获取错误详情
    ERROR_MSG=$(curl -s --max-time 10 \
      "http://$ALB_DNS/api/v1/statistics/overview" 2>/dev/null | jq -r '.detail // "Unknown error"' || echo "无法获取错误信息")
    echo "  📋 错误信息: $ERROR_MSG"
  else
    echo "  ⚠️  API响应异常 (HTTP $HTTP_CODE)"
  fi
fi
echo ""

# 6. 建议的修复步骤
echo "📝 建议的修复步骤"
echo "=========================================="
echo ""
echo "如果诊断发现问题，请按以下步骤修复："
echo ""
echo "1. 修复IAM策略（如果ListTables权限不正确）："
echo "   cd infrastructure"
echo "   terraform apply"
echo ""
echo "2. 强制更新ECS服务（使新IAM策略生效）："
echo "   aws ecs update-service \\"
echo "     --cluster $CLUSTER_NAME \\"
echo "     --service $SERVICE_NAME \\"
echo "     --force-new-deployment \\"
echo "     --region $REGION"
echo ""
echo "3. 等待任务重新部署后，再次测试API："
echo "   curl -X GET \\"
echo "     'http://$ALB_DNS/api/v1/statistics/overview' \\"
echo "     -H 'accept: application/json'"
echo ""
echo "4. 查看API日志（如果问题仍然存在）："
echo "   aws logs tail /ecs/nexus-ai-api-prod \\"
echo "     --follow \\"
echo "     --region $REGION"
echo ""

