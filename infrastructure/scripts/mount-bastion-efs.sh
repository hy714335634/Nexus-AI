#!/bin/bash
# Quick script to mount EFS on existing Bastion instance
# Usage: ./mount-bastion-efs.sh

set -e

cd "$(dirname "$0")"

echo "🔧 Mounting EFS on Bastion Host..."
echo ""

# Get Terraform outputs
EFS_FILE_SYSTEM_ID=$(terraform output -raw efs_file_system_id 2>/dev/null)
EFS_ACCESS_POINT_ID=$(terraform output -raw efs_access_point_id 2>/dev/null)
BASTION_INSTANCE_ID=$(terraform output -raw bastion_instance_id 2>/dev/null)

if [ -z "$EFS_FILE_SYSTEM_ID" ] || [ -z "$EFS_ACCESS_POINT_ID" ] || [ -z "$BASTION_INSTANCE_ID" ]; then
    echo "❌ Error: Could not get Terraform outputs"
    echo "Please ensure infrastructure is deployed and bastion is enabled"
    exit 1
fi

echo "📋 Configuration:"
echo "   EFS ID: $EFS_FILE_SYSTEM_ID"
echo "   Access Point: $EFS_ACCESS_POINT_ID"
echo "   Bastion Instance: $BASTION_INSTANCE_ID"
echo ""

# Create mount command
MOUNT_CMD=$(cat << 'CMDEOF'
set -e
EFS_ID="${EFS_ID}"
AP_ID="${AP_ID}"
MOUNT_PATH="/mnt/efs"

# Check if already mounted
if mountpoint -q "$MOUNT_PATH"; then
    echo "✅ EFS already mounted"
    df -h "$MOUNT_PATH"
    exit 0
fi

# Install amazon-efs-utils
if ! command -v mount.efs &> /dev/null; then
    echo "Installing amazon-efs-utils..."
    yum install -y amazon-efs-utils || {
        yum install -y git rpm-build make
        cd /tmp && [ ! -d efs-utils ] && git clone https://github.com/aws/efs-utils
        cd efs-utils && make rpm && yum install -y build/amazon-efs-utils*rpm
    }
fi

# Create mount point
mkdir -p "$MOUNT_PATH"

# Mount with retries
for i in {1..5}; do
    echo "Mount attempt $i/5..."
    if mount -t efs -o tls,accesspoint="$AP_ID" "$EFS_ID":/ "$MOUNT_PATH" 2>&1; then
        sleep 2
        if mountpoint -q "$MOUNT_PATH"; then
            echo "✅ Mounted successfully!"
            break
        fi
    fi
    [ $i -lt 5 ] && sleep 5
done

if ! mountpoint -q "$MOUNT_PATH"; then
    echo "❌ Mount failed"
    exit 1
fi

# Add to fstab
if ! grep -q "$MOUNT_PATH" /etc/fstab; then
    echo "$EFS_ID:/ $MOUNT_PATH efs _netdev,tls,accesspoint=$AP_ID 0 0" >> /etc/fstab
    echo "✅ Added to /etc/fstab"
fi

# Verify
df -h "$MOUNT_PATH"
echo "✅ EFS mount completed!"
CMDEOF
)

# Replace variables
MOUNT_CMD="${MOUNT_CMD//\$\{EFS_ID\}/$EFS_FILE_SYSTEM_ID}"
MOUNT_CMD="${MOUNT_CMD//\$\{AP_ID\}/$EFS_ACCESS_POINT_ID}"

# Escape for JSON
ESCAPED_CMD=$(echo "$MOUNT_CMD" | jq -Rs .)

echo "📤 Sending command to Bastion..."
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$BASTION_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[$ESCAPED_CMD]" \
  --query 'Command.CommandId' \
  --output text)

echo "⏳ Waiting for command to complete..."
sleep 5

# Get output
aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$BASTION_INSTANCE_ID" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' \
  --output text | while read -r status stdout stderr; do
    echo ""
    echo "Status: $status"
    echo "Output:"
    echo "$stdout"
    [ -n "$stderr" ] && echo "Errors: $stderr"
done

echo ""
echo "✨ Done! Check output above for mount status."

