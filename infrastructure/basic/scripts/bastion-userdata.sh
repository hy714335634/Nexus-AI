#!/bin/bash
# Use set -e carefully - we'll handle errors explicitly for non-critical steps
set -e

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting Bastion Host initialization at $(date)"

# Variables (will be replaced by Terraform templatefile)
EFS_FILE_SYSTEM_ID="${efs_file_system_id}"
AWS_REGION="${aws_region}"
EFS_MOUNT_PATH="${efs_mount_path}"

# Export variables for use in script
export EFS_FILE_SYSTEM_ID AWS_REGION EFS_MOUNT_PATH

# Update system (non-critical, continue on failure)
echo "Updating system packages..."
yum update -y || echo "⚠️  Warning: System update had some issues, continuing..."

# Install required packages (critical packages first)
echo "Installing required packages..."

# Note: curl command is provided by curl-minimal (already installed on Amazon Linux 2023)
# So we don't need to install the 'curl' package separately
# Check if curl command is available
if ! command -v curl &> /dev/null; then
    echo "⚠️  Warning: curl command not found, but curl-minimal should provide it"
fi

# Install packages (excluding curl to avoid conflict with curl-minimal)
yum install -y \
    amazon-efs-utils \
    git \
    jq \
    python3 \
    python3-pip || {
    echo "❌ Error: Failed to install critical packages"
    exit 1
}

# Install Docker (optional - continue on failure)
echo "Installing Docker..."
if yum install -y docker 2>&1; then
    echo "✅ Docker installed successfully"
    # Start and enable Docker (optional, continue on failure)
    systemctl start docker || echo "⚠️  Warning: Could not start Docker service"
    systemctl enable docker || echo "⚠️  Warning: Could not enable Docker service"
    usermod -a -G docker ec2-user || echo "⚠️  Warning: Could not add ec2-user to docker group"
else
    echo "⚠️  Warning: Docker installation failed, continuing without Docker"
fi

# Install Docker Compose (optional - try multiple methods)
echo "Installing Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose is already installed"
elif yum install -y docker-compose 2>&1; then
    echo "✅ docker-compose installed via yum"
else
    echo "⚠️  docker-compose not available via yum, trying GitHub release..."
    # Try to install from GitHub (for ARM64 architecture)
    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    
    # Map architecture names
    if [ "$ARCH" = "aarch64" ]; then
        ARCH="arm64"
    fi
    
    # Try to download and install docker-compose
    # Note: OS and ARCH are shell variables, escape $ so Terraform doesn't parse them
    if curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$OS-$ARCH" -o /usr/local/bin/docker-compose 2>/dev/null; then
    chmod +x /usr/local/bin/docker-compose
        echo "✅ docker-compose installed from GitHub"
    else
        echo "⚠️  Warning: Could not install docker-compose, continuing without it"
    fi
fi

# Wait for network and EFS mount targets to be ready
echo "Waiting for network and EFS mount targets to be ready..."
sleep 30

# Create mount directory (critical)
echo "Creating EFS mount directory..."
mkdir -p "$${EFS_MOUNT_PATH}" || {
    echo "❌ Error: Failed to create mount directory"
    exit 1
}

# Debug: Print EFS configuration
echo "EFS Configuration:"
echo "  - EFS File System ID: $${EFS_FILE_SYSTEM_ID}"
echo "  - EFS Mount Path: $${EFS_MOUNT_PATH}"
echo "  - AWS Region: $${AWS_REGION}"

# Function to mount EFS
mount_efs() {
    echo "Mounting EFS file system..."
    
    # Check if already mounted
    if mountpoint -q "$${EFS_MOUNT_PATH}"; then
        echo "✅ EFS is already mounted at $${EFS_MOUNT_PATH}"
        df -h "$${EFS_MOUNT_PATH}"
        return 0
    fi
    
    # Try to mount EFS with retries
    MAX_RETRIES=10
    RETRY_COUNT=0
    MOUNT_SUCCESS=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # Mount EFS directly without access point (full permissions)
        echo "Attempting to mount EFS (attempt $(expr $RETRY_COUNT + 1)/$MAX_RETRIES)..."
        if mount -t efs -o tls "$${EFS_FILE_SYSTEM_ID}:/" "$${EFS_MOUNT_PATH}" 2>&1; then
            sleep 2
            if mountpoint -q "$${EFS_MOUNT_PATH}"; then
                echo "✅ EFS mounted successfully on attempt $(expr $RETRY_COUNT + 1)"
                MOUNT_SUCCESS=true
                break
            fi
        fi
        
        RETRY_COUNT=$(expr $RETRY_COUNT + 1)
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Mount attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 10 seconds..."
            sleep 10
        fi
    done
    
    if [ "$MOUNT_SUCCESS" = false ]; then
        echo "❌ EFS mount failed after $MAX_RETRIES attempts"
        echo "Debug information:"
        echo "  - Mount point exists: $([ -d "$${EFS_MOUNT_PATH}" ] && echo 'yes' || echo 'no')"
        echo "  - EFS utils installed: $(command -v mount.efs >/dev/null && echo 'yes' || echo 'no')"
        return 1
    fi
    
    return 0
}

# Mount EFS
if ! mount_efs; then
    echo "⚠️  WARNING: EFS mount failed, but continuing with initialization"
    echo "EFS will be added to /etc/fstab and will mount on next reboot"
fi

# Add to fstab for persistence (check if already exists to avoid duplicates)
FSTAB_ENTRY="$${EFS_FILE_SYSTEM_ID}:/ $${EFS_MOUNT_PATH} efs _netdev,tls 0 0"

if ! grep -q "$${EFS_MOUNT_PATH}" /etc/fstab; then
    echo "Adding EFS to /etc/fstab for automatic mounting on boot..."
    echo "$${FSTAB_ENTRY}" >> /etc/fstab
    echo "✅ EFS entry added to /etc/fstab"
else
    echo "✅ EFS entry already exists in /etc/fstab"
fi

# Verify mount
if mountpoint -q "$${EFS_MOUNT_PATH}"; then
    echo "✅ EFS mounted successfully at $${EFS_MOUNT_PATH}"
    df -h "$${EFS_MOUNT_PATH}"

# Create a test file to verify write access
TEST_FILE="$${EFS_MOUNT_PATH}/.bastion-test-$(date +%s)"
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

# Set permissions for EFS root directory to allow all users to write
# This is necessary for Fargate containers (UID 1000) to create directories
echo "Setting EFS root directory permissions..."
chmod 777 "$${EFS_MOUNT_PATH}" 2>/dev/null || echo "Note: Could not set EFS root permissions"
echo "EFS root permissions: $(ls -ld "$${EFS_MOUNT_PATH}" | awk '{print $1, $3, $4}')"

# Set permissions for ec2-user (optional, for any files created by Bastion)
chown -R ec2-user:ec2-user "$${EFS_MOUNT_PATH}" 2>/dev/null || echo "Note: Some files may have restricted permissions"
    
    # Note: Git clone will be performed by Fargate containers, not Bastion
    # Bastion only sets up EFS permissions to allow Fargate to write
    echo "✅ EFS is ready for Fargate containers to clone repository"
else
    echo "⚠️  EFS is not currently mounted, but it will be mounted automatically on next reboot via /etc/fstab"
fi

# Create a systemd service to ensure EFS is mounted on boot (as a backup to /etc/fstab)
cat > /etc/systemd/system/mount-efs.service << 'EOFSERVICE'
[Unit]
Description=Mount EFS File System
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'if ! mountpoint -q /mnt/efs; then mount -a -t efs || exit 0; fi'

[Install]
WantedBy=multi-user.target
EOFSERVICE

systemctl daemon-reload || echo "⚠️  Warning: Failed to reload systemd daemon"
systemctl enable mount-efs.service || echo "⚠️  Warning: Failed to enable mount-efs service"

echo "Bastion Host initialization completed at $(date)"

