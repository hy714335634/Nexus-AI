#!/bin/bash
# ============================================
# Jaeger访问脚本
# ============================================

set -e

cd "$(dirname "$0")/.."

echo "🔍 获取Jaeger访问信息..."
echo ""

ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
REGION=$(terraform output -raw region 2>/dev/null || echo "us-west-2")
ALB_INTERNAL=$(terraform output -raw alb_internal 2>/dev/null || echo "false")

if [ -z "$ALB_DNS" ]; then
    echo "❌ 无法获取ALB DNS名称"
    echo "   请确保已运行 terraform apply"
    exit 1
fi

JAEGER_URL="http://$ALB_DNS/jaeger/"

echo "📊 Jaeger配置信息"
echo "=========================================="
echo "ALB DNS:     $ALB_DNS"
echo "ALB类型:     $([ "$ALB_INTERNAL" = "true" ] && echo "内部 (仅VPC内访问)" || echo "外部 (互联网可访问)")"
echo "区域:        $REGION"
echo ""

if [ "$ALB_INTERNAL" = "true" ]; then
    echo "📡 ALB是内部的，需要通过端口转发访问"
    echo ""
    
    BASTION_IP=$(terraform output -raw bastion_public_ip 2>/dev/null || echo "")
    KEY_NAME=$(terraform output -raw bastion_key_name 2>/dev/null || echo "Og_Normal")
    
    if [ -z "$BASTION_IP" ]; then
        echo "❌ 无法获取Bastion IP，无法建立端口转发"
        echo ""
        echo "💡 替代方案："
        echo "   1. 通过VPN连接到VPC"
        echo "   2. 从VPC内部的资源访问"
        exit 1
    fi
    
    echo "🔧 端口转发步骤："
    echo "=========================================="
    echo ""
    echo "1. 在一个终端运行以下命令建立端口转发："
    echo ""
    echo "   ssh -i ~/.ssh/$KEY_NAME.pem \\"
    echo "       -L 8088:$ALB_DNS:80 \\"
    echo "       ec2-user@$BASTION_IP \\"
    echo "       -N"
    echo ""
    echo "2. 保持该终端窗口打开，然后在浏览器访问："
    echo ""
    echo "   http://localhost:8088/jaeger/"
    echo ""
    echo "3. 完成后，按 Ctrl+C 停止端口转发"
    echo ""
    
    # 可选：自动打开
    read -p "是否现在建立端口转发？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 建立端口转发..."
        ssh -i ~/.ssh/$KEY_NAME.pem \
            -L 8088:$ALB_DNS:80 \
            ec2-user@$BASTION_IP \
            -N &
        SSH_PID=$!
        echo "✅ 端口转发已建立 (PID: $SSH_PID)"
        echo ""
        echo "🌐 Jaeger UI访问地址:"
        echo "   http://localhost:8088/jaeger/"
        echo ""
        echo "按 Ctrl+C 停止端口转发"
        trap "kill $SSH_PID 2>/dev/null" EXIT
        wait $SSH_PID
    fi
else
    echo "🌐 Jaeger UI访问地址："
    echo "=========================================="
    echo "   $JAEGER_URL"
    echo ""
    
    # 检查Jaeger是否启用
    ENABLE_JAEGER=$(grep -E "^enable_jaeger\s*=" terraform.tfvars 2>/dev/null | grep -oE "(true|false)" || echo "")
    if [ "$ENABLE_JAEGER" != "true" ]; then
        echo "⚠️  警告: enable_jaeger 可能未设置为 true"
        echo "   请检查 terraform.tfvars 中的配置"
        echo ""
    fi
    
    # 测试连接
    echo "🔍 测试连接..."
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$JAEGER_URL" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Jaeger UI可访问 (HTTP $HTTP_CODE)"
    elif [ "$HTTP_CODE" = "404" ]; then
        echo "⚠️  返回404，可能原因："
        echo "   - Jaeger容器未添加到Task Definition"
        echo "   - ALB路由规则未配置"
        echo "   - 检查文档: infrastructure/docs/jaeger-access-guide.md"
    elif [ "$HTTP_CODE" = "502" ] || [ "$HTTP_CODE" = "503" ]; then
        echo "⚠️  返回$HTTP_CODE，可能原因："
        echo "   - Jaeger容器未运行"
        echo "   - Target Group中没有健康的目标"
        echo "   - 检查ECS服务状态: aws ecs describe-services --cluster nexus-ai-cluster-prod --services nexus-ai-api-prod"
    elif [ "$HTTP_CODE" = "000" ]; then
        echo "❌ 无法连接到服务器"
        echo "   请检查网络连接或ALB状态"
    else
        echo "⚠️  返回HTTP $HTTP_CODE"
        echo "   请检查Jaeger配置和状态"
    fi
    
    echo ""
    echo "💡 提示: 直接复制上面的URL到浏览器打开"
    
    # macOS/Linux: 尝试打开浏览器
    if command -v open &> /dev/null; then
        read -p "是否在浏览器中打开？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open "$JAEGER_URL"
        fi
    elif command -v xdg-open &> /dev/null; then
        read -p "是否在浏览器中打开？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            xdg-open "$JAEGER_URL"
        fi
    fi
fi

echo ""
echo "📚 更多信息请查看: infrastructure/docs/jaeger-access-guide.md"

