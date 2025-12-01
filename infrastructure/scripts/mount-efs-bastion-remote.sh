#!/bin/bash
# Remote script to mount EFS on Bastion host via SSM
# This script runs on your local machine and executes commands on the Bastion instance

set -e

echo "=== Remote EFS Mount Script for Bastion Host ==="
echo ""

cd "$(dirname "$0")/.." || exit 1

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "Error: Terraform not initialized. Please run 'terraform init' first."
    exit 1
fi

# Get Terraform outputs
echo "Getting Terraform outputs..."
EFS_FILE_SYSTEM_ID=$(terraform output -raw efs_file_system_id 2>/dev/null || echo "")
EFS_ACCESS_POINT_ID=$(terraform output -raw efs_access_point_id 2>/dev/null || echo "")
BASTION_INSTANCE_ID=$(terraform output -raw bastion_instance_id 2>/dev/null || echo "")

if [ -z "$EFS_FILE_SYSTEM_ID" ] || [ -z "$EFS_ACCESS_POINT_ID" ] || [ -z "$BASTION_INSTANCE_ID" ]; then
    echo "Error: Could not get required Terraform outputs"
    echo "Please ensure:"
    echo "  1. Terraform is initialized (terraform init)"
    echo "  2. Infrastructure is deployed (terraform apply)"
    echo "  3. Bastion host is enabled (enable_bastion = true)"
    exit 1
fi

echo "EFS File System ID: $EFS_FILE_SYSTEM_ID"
echo "EFS Access Point ID: $EFS_ACCESS_POINT_ID"
echo "Bastion Instance ID: $BASTION_INSTANCE_ID"
echo ""

# Create the mount script content
MOUNT_SCRIPT=$(cat << 'SCRIPTEOF'
#!/bin/bash
set -e

EFS_FILE_SYSTEM_ID="${EFS_FILE_SYSTEM_ID}"
EFS_ACCESS_POINT_ID="${EFS_ACCESS_POINT_ID}"
EFS_MOUNT_PATH="/mnt/efs"

echo "=== Mounting EFS on Bastion Host ==="
echo "EFS File System: $EFS_FILE_SYSTEM_ID"
echo "Access Point: $EFS_ACCESS_POINT_ID"
echo "Mount Path: $EFS_MOUNT_PATH"
echo ""

# Check if already mounted
if mountpoint -q "$EFS_MOUNT_PATH"; then
    echo "✅ EFS is already mounted at $EFS_MOUNT_PATH"
    df -h "$EFS_MOUNT_PATH"
    exit 0
fi

# Install amazon-efs-utils if needed
if ! command -v mount.efs &> /dev/null; then
    echo "Installing amazon-efs-utils..."
    yum install -y amazon-efs-utils || {
        echo "Trying alternative installation method..."
        yum install -y git rpm-build make
        cd /tmp
        if [ ! -d "efs-utils" ]; then
            git clone https://github.com/aws/efs-utils
        fi
        cd efs-utils
        make rpm
        yum install -y build/amazon-efs-utils*rpm
    }
fi

# Create mount directory
mkdir -p "$EFS_MOUNT_PATH"

# Mount EFS with retries
MAX_RETRIES=5
RETRY_COUNT=0
MOUNT_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Mount attempt $((RETRY_COUNT + 1))/$MAX_RETRIES..."
    
    if mount -t efs -o tls,accesspoint="$EFS_ACCESS_POINT_ID" "$EFS_FILE_SYSTEM_ID":/ "$EFS_MOUNT_PATH" 2>&1; then
        sleep 2
        if mountpoint -q "$EFS_MOUNT_PATH"; then
            echo "✅ EFS mounted successfully!"
            MOUNT_SUCCESS=true
            break
        fi
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    [ $RETRY_COUNT -lt $MAX_RETRIES ] && sleep 5
done

if [ "$MOUNT_SUCCESS" = false ]; then
    echo "❌ ERROR: EFS mount failed after $MAX_RETRIES attempts"
    exit 1
fi

# Add to fstab if not already present
FSTAB_ENTRY="$EFS_FILE_SYSTEM_ID:/ $EFS_MOUNT_PATH efs _netdev,tls,accesspoint=$EFS_ACCESS_POINT_ID 0 0"
if ! grep -q "$EFS_MOUNT_PATH" /etc/fstab; then
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "✅ Added to /etc/fstab for automatic mounting"
fi

# Verify mount
echo ""
echo "Mount verification:"
df -h "$EFS_MOUNT_PATH"

# Test write access
TEST_FILE="$EFS_MOUNT_PATH/.bastion-test-$(date +%s)"
if echo "Test at $(date)" > "$TEST_FILE" 2>/dev/null && [ -f "$TEST_FILE" ]; then
    echo "✅ Write access verified"
    rm -f "$TEST_FILE"
else
    echo "⚠️  Write access test failed"
fi

echo ""
echo "✅ EFS mount completed successfully!"
SCRIPTEOF
)

# Replace variables in the script
MOUNT_SCRIPT="${MOUNT_SCRIPT//\$\{EFS_FILE_SYSTEM_ID\}/$EFS_FILE_SYSTEM_ID}"
MOUNT_SCRIPT="${MOUNT_SCRIPT//\$\{EFS_ACCESS_POINT_ID\}/$EFS_ACCESS_POINT_ID}"

echo "Sending mount command to Bastion instance..."
echo ""

# Execute via SSM
aws ssm send-command \
  --instance-ids "$BASTION_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[$(echo "$MOUNT_SCRIPT" | jq -Rs .)]" \
  --output json \
  --query 'Command.{CommandId:CommandId,Status:Status}' \
  --output table

echo ""
echo "Waiting for command to complete..."

# Get command ID
COMMAND_ID=$(aws ssm send-command \
  --instance-ids "$BASTION_INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters "commands=[$(echo "$MOUNT_SCRIPT" | jq -Rs .)]" \
  --query 'Command.CommandId' \
  --output text)

# Wait for command to complete and show output
sleep 3
aws ssm get-command-invocation \
  --command-id "$COMMAND_ID" \
  --instance-id "$BASTION_INSTANCE_ID" \
  --query '[Status,StandardOutputContent,StandardErrorContent]' \
  --output text

echo ""
echo "Done! Check the output above to verify EFS is mounted."

