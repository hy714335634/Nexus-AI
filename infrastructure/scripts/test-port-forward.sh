#!/bin/bash
# 测试端口转发配置

set -e

cd "$(dirname "$0")"

# 获取配置
BASTION_IP=$(terraform output -raw bastion_public_ip 2>/dev/null || echo "")
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "")
KEY_NAME=$(terraform output -raw bastion_ssh_command 2>/dev/null | grep -oP '(?<=-i\s)[^\s]+' || echo "$HOME/.ssh/Og_Normal.pem")

if [ -z "$BASTION_IP" ] || [ -z "$ALB_DNS" ]; then
    echo "❌ 无法获取配置信息，请确保 terraform apply 已完成"
    exit 1
fi

echo "🔍 端口转发测试工具"
echo "===================="
echo "Bastion IP: $BASTION_IP"
echo "ALB DNS: $ALB_DNS"
echo "Key: $KEY_NAME"
echo ""

# 测试 1: SSH 连接
echo "1️⃣ 测试 SSH 连接到 Bastion..."
if ssh -i "$KEY_NAME" -o ConnectTimeout=5 -o StrictHostKeyChecking=no ec2-user@$BASTION_IP "echo 'SSH OK'" >/dev/null 2>&1; then
    echo "✅ SSH 连接成功"
else
    echo "❌ SSH 连接失败，请检查："
    echo "   - Key 文件是否存在: $KEY_NAME"
    echo "   - Key 文件权限是否正确 (chmod 400)"
    echo "   - Bastion Host 是否运行中"
    exit 1
fi

# 测试 2: 从 Bastion 访问 ALB
echo ""
echo "2️⃣ 测试从 Bastion 访问 ALB..."
HTTP_CODE=$(ssh -i "$KEY_NAME" -o ConnectTimeout=10 ec2-user@$BASTION_IP \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://$ALB_DNS" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "404" ]; then
    echo "✅ ALB 可从 Bastion 访问 (HTTP $HTTP_CODE)"
else
    echo "❌ ALB 无法从 Bastion 访问 (HTTP $HTTP_CODE)"
    echo "   可能原因："
    echo "   - ALB 安全组不允许从 VPC CIDR 访问"
    echo "   - ALB DNS 名称不正确"
    echo "   - ALB 后端服务未运行"
fi

# 显示端口转发命令
echo ""
echo "3️⃣ 端口转发命令："
echo "===================="
echo "ssh -i $KEY_NAME \\"
echo "    -L 8088:$ALB_DNS:80 \\"
echo "    ec2-user@$BASTION_IP \\"
echo "    -N"
echo ""
echo "然后在另一个终端运行："
echo "  curl http://localhost:8088"
echo ""

# 可选：自动启动端口转发
read -p "是否现在启动端口转发？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 启动端口转发（按 Ctrl+C 停止）..."
    ssh -i "$KEY_NAME" \
        -L 8088:$ALB_DNS:80 \
        ec2-user@$BASTION_IP \
        -N -v
fi

