#!/bin/bash
# 快速启动端口转发

cd "$(dirname "$0")"
BASTION_IP=$(terraform output -raw bastion_public_ip)
ALB_DNS=$(terraform output -raw alb_dns_name)
KEY="$HOME/.ssh/Og_Normal.pem"

echo "🚀 启动端口转发..."
echo "Bastion: $BASTION_IP"
echo "ALB: $ALB_DNS"
echo "本地端口: localhost:8088 -> ALB:80"
echo ""
echo "按 Ctrl+C 停止"
echo ""

ssh -i "$KEY" \
    -L 8088:$ALB_DNS:80 \
    ec2-user@$BASTION_IP \
    -N -v
