#!/bin/bash
# Script to mount EFS on an existing Bastion instance
# This can be run manually if EFS is not mounted after terraform apply

set -e

echo "=== EFS Mount Script for Bastion Host ==="
echo "This script will mount EFS on an existing Bastion instance"
echo ""

# Get EFS information from Terraform outputs or environment
# You can also set these variables manually
EFS_FILE_SYSTEM_ID="${EFS_FILE_SYSTEM_ID:-}"
EFS_ACCESS_POINT_ID="${EFS_ACCESS_POINT_ID:-}"
EFS_MOUNT_PATH="${EFS_MOUNT_PATH:-/mnt/efs}"
AWS_REGION="${AWS_REGION:-us-west-2}"

# Check if variables are set
if [ -z "$EFS_FILE_SYSTEM_ID" ] || [ -z "$EFS_ACCESS_POINT_ID" ]; then
    echo "Error: EFS_FILE_SYSTEM_ID and EFS_ACCESS_POINT_ID must be set"
    echo ""
    echo "Usage:"
    echo "  export EFS_FILE_SYSTEM_ID=fs-xxxxx"
    echo "  export EFS_ACCESS_POINT_ID=fsap-xxxxx"
    echo "  sudo bash mount-efs-on-bastion.sh"
    echo ""
    echo "Or get values from Terraform:"
    echo "  cd infrastructure"
    echo "  export EFS_FILE_SYSTEM_ID=\$(terraform output -raw efs_file_system_id)"
    echo "  export EFS_ACCESS_POINT_ID=\$(terraform output -raw efs_access_point_id)"
    echo "  sudo EFS_FILE_SYSTEM_ID=\$EFS_FILE_SYSTEM_ID EFS_ACCESS_POINT_ID=\$EFS_ACCESS_POINT_ID bash mount-efs-on-bastion.sh"
    exit 1
fi

echo "Configuration:"
echo "  EFS File System ID: $EFS_FILE_SYSTEM_ID"
echo "  EFS Access Point ID: $EFS_ACCESS_POINT_ID"
echo "  Mount Path: $EFS_MOUNT_PATH"
echo "  AWS Region: $AWS_REGION"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Install amazon-efs-utils if not already installed
if ! command -v mount.efs &> /dev/null; then
    echo "Installing amazon-efs-utils..."
    yum install -y amazon-efs-utils || {
        echo "Failed to install amazon-efs-utils via yum, trying alternative method..."
        yum install -y git rpm-build make
        if [ ! -d "/tmp/efs-utils" ]; then
            cd /tmp
            git clone https://github.com/aws/efs-utils
        fi
        cd /tmp/efs-utils
        make rpm
        yum install -y build/amazon-efs-utils*rpm
    }
    echo "✅ amazon-efs-utils installed"
fi

# Create mount directory
echo "Creating mount directory..."
mkdir -p ${EFS_MOUNT_PATH}
echo "✅ Mount directory created"

# Check if already mounted
if mountpoint -q ${EFS_MOUNT_PATH}; then
    echo "✅ EFS is already mounted at ${EFS_MOUNT_PATH}"
    df -h ${EFS_MOUNT_PATH}
    
    # Verify write access
    TEST_FILE="${EFS_MOUNT_PATH}/.bastion-mount-test-$(date +%s)"
    if echo "Test write at $(date)" > "$TEST_FILE" 2>/dev/null; then
        if [ -f "$TEST_FILE" ]; then
            echo "✅ EFS write access verified"
            rm -f "$TEST_FILE"
        fi
    fi
    exit 0
fi

# Try to mount EFS with retries
echo "Mounting EFS file system..."
MAX_RETRIES=5
RETRY_COUNT=0
MOUNT_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $((RETRY_COUNT + 1))/$MAX_RETRIES..."
    
    if mount -t efs -o tls,accesspoint=${EFS_ACCESS_POINT_ID} ${EFS_FILE_SYSTEM_ID}:/ ${EFS_MOUNT_PATH} 2>&1; then
        sleep 2
        if mountpoint -q ${EFS_MOUNT_PATH}; then
            echo "✅ EFS mounted successfully!"
            MOUNT_SUCCESS=true
            break
        else
            echo "⚠️  Mount command succeeded but mountpoint check failed"
        fi
    else
        echo "⚠️  Mount attempt failed"
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Waiting 5 seconds before retry..."
        sleep 5
    fi
done

if [ "$MOUNT_SUCCESS" = false ]; then
    echo "❌ ERROR: EFS mount failed after $MAX_RETRIES attempts"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check security group rules (EFS security group should allow port 2049 from Bastion security group)"
    echo "2. Check IAM permissions (Bastion instance profile should have EFS permissions)"
    echo "3. Check network connectivity (Bastion should be able to reach EFS mount targets)"
    echo "4. Check CloudWatch logs: /var/log/user-data.log"
    exit 1
fi

# Add to fstab for persistence
FSTAB_ENTRY="${EFS_FILE_SYSTEM_ID}:/ ${EFS_MOUNT_PATH} efs _netdev,tls,accesspoint=${EFS_ACCESS_POINT_ID} 0 0"
if ! grep -q "${EFS_MOUNT_PATH}" /etc/fstab; then
    echo "Adding EFS to /etc/fstab for automatic mounting on boot..."
    echo "${FSTAB_ENTRY}" >> /etc/fstab
    echo "✅ EFS entry added to /etc/fstab"
else
    echo "✅ EFS entry already exists in /etc/fstab"
fi

# Verify mount and permissions
echo ""
echo "Verifying mount..."
df -h ${EFS_MOUNT_PATH}

# Test write access
TEST_FILE="${EFS_MOUNT_PATH}/.bastion-mount-test-$(date +%s)"
if echo "Bastion host mounted EFS at $(date)" > "$TEST_FILE" 2>/dev/null; then
    if [ -f "$TEST_FILE" ]; then
        echo "✅ EFS write access verified"
        rm -f "$TEST_FILE"
    else
        echo "⚠️  EFS write access may be limited"
    fi
else
    echo "⚠️  Could not write test file to EFS"
fi

# Set permissions for ec2-user
echo "Setting permissions for ec2-user..."
chown -R ec2-user:ec2-user ${EFS_MOUNT_PATH} 2>/dev/null || echo "Note: Some files may have restricted permissions"

echo ""
echo "✅ EFS mount completed successfully!"
echo "Mount point: ${EFS_MOUNT_PATH}"
echo "The EFS will be automatically mounted on system reboot via /etc/fstab"

