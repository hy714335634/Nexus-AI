#!/bin/bash
# Removed 'set -e' to prevent script from exiting on non-critical errors
# Critical errors are handled explicitly

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting EC2 API service initialization at $(date)"

# Variables (will be replaced by Terraform templatefile)
EFS_FILE_SYSTEM_ID="${efs_file_system_id}"
EFS_ACCESS_POINT_ID="${efs_access_point_id}"
AWS_REGION="${aws_region}"
ECR_REPOSITORY_URL="${ecr_repository_url}"
DYNAMODB_REGION="${dynamodb_region}"
AGENT_PROJECTS_TABLE="${agent_projects_table}"
AGENT_INSTANCES_TABLE="${agent_instances_table}"
SQS_QUEUE_URL="${sqs_queue_url}"
ENVIRONMENT="${environment}"
GITHUB_REPO_URL="${github_repo_url}"
GITHUB_BRANCH="${github_branch}"

# Define path variables (from Terraform, use directly in script)
EFS_MOUNT_PATH="${efs_mount_path}"
APP_DIR="${app_dir}"
PROJECT_ROOT="${project_root}"

# Export variables for use in heredoc
export EFS_FILE_SYSTEM_ID EFS_ACCESS_POINT_ID AWS_REGION ECR_REPOSITORY_URL
export DYNAMODB_REGION
export AGENT_PROJECTS_TABLE AGENT_INSTANCES_TABLE SQS_QUEUE_URL ENVIRONMENT
export GITHUB_REPO_URL GITHUB_BRANCH
export EFS_MOUNT_PATH APP_DIR PROJECT_ROOT

# Update system
yum update -y

# Install required packages
yum install -y \
    docker \
    amazon-efs-utils \
    git \
    curl \
    jq \
    python3 \
    python3-pip \
    rsync

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start and enable Docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Create mount directory
mkdir -p ${EFS_MOUNT_PATH}

# Wait for EFS mount targets to be available (up to 2 minutes)
echo "Waiting for EFS mount targets to be available..."
MAX_RETRIES=24
RETRY_COUNT=0
MOUNT_SUCCESS=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try to mount EFS using amazon-efs-utils (more reliable than direct mount)
    if mount -t efs -o tls,accesspoint=${EFS_ACCESS_POINT_ID} ${EFS_FILE_SYSTEM_ID}:/ ${EFS_MOUNT_PATH} 2>&1; then
        if mountpoint -q ${EFS_MOUNT_PATH}; then
            echo "✅ EFS mounted successfully on attempt $((RETRY_COUNT + 1))"
            MOUNT_SUCCESS=true
            break
        fi
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "Mount attempt $RETRY_COUNT/$MAX_RETRIES failed, retrying in 5 seconds..."
        sleep 5
    fi
done

if [ "$MOUNT_SUCCESS" = false ]; then
    echo "❌ WARNING: EFS mount failed after $MAX_RETRIES attempts"
    echo "Continuing with initialization, but EFS-dependent features may not work"
    # Don't exit - allow script to continue
fi

# Add to fstab for persistence (only if mount was successful)
if [ "$MOUNT_SUCCESS" = true ]; then
    echo "${EFS_FILE_SYSTEM_ID}:/ ${EFS_MOUNT_PATH} efs _netdev,tls,accesspoint=${EFS_ACCESS_POINT_ID} 0 0" >> /etc/fstab
    echo "EFS mount added to /etc/fstab for persistence"
fi

# Create application directory
mkdir -p ${APP_DIR}

# Use EFS for entire project repository (shared across all instances)
PROJECT_ROOT_EFS="${EFS_MOUNT_PATH}/nexus-ai-repo"
PROJECT_ROOT="${PROJECT_ROOT}"

# Only clone if EFS mount was successful
if [ "$MOUNT_SUCCESS" = true ]; then
    echo "Using EFS for shared project repository..."
    
    # Clone to EFS only if not already exists (first instance does this)
    if [ ! -d "$PROJECT_ROOT_EFS/.git" ]; then
        echo "First instance - cloning repository to EFS..."
        mkdir -p "$PROJECT_ROOT_EFS"
        cd "$PROJECT_ROOT_EFS"
        git clone -b ${GITHUB_BRANCH} ${GITHUB_REPO_URL} . || {
            echo "Error: Failed to clone repository to EFS"
            exit 1
        }
        echo "✅ Repository cloned to EFS: $PROJECT_ROOT_EFS"
    else
        echo "Repository already exists in EFS, pulling latest changes..."
        cd "$PROJECT_ROOT_EFS"
        git pull origin ${GITHUB_BRANCH} || echo "Warning: Failed to pull, using existing code"
    fi
    
    # Create symlink from local path to EFS
    if [ ! -L "${PROJECT_ROOT}" ]; then
        ln -sf "$PROJECT_ROOT_EFS" "${PROJECT_ROOT}"
        echo "✅ Created symlink: ${PROJECT_ROOT} -> $PROJECT_ROOT_EFS"
    fi
    
    # Verify project structure
    if [ ! -d "$PROJECT_ROOT_EFS/api" ] || [ ! -d "$PROJECT_ROOT_EFS/agents" ]; then
        echo "Error: Project structure incomplete"
        exit 1
    fi
    
    echo "✅ Using shared repository from EFS"
else
    # Fallback: clone locally if EFS mount failed
    echo "⚠️  EFS not available, cloning to local storage..."
    mkdir -p ${PROJECT_ROOT}
    cd ${PROJECT_ROOT}
    if [ ! -d ".git" ]; then
        git clone -b ${GITHUB_BRANCH} ${GITHUB_REPO_URL} . || {
            echo "Error: Failed to clone repository"
            exit 1
        }
    fi
fi

# Login to ECR
echo "Logging into ECR..."
if ! aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URL}; then
    echo "ERROR: Failed to login to ECR"
    exit 1
fi

# Pull API image
echo "Pulling API image..."
if ! docker pull ${ECR_REPOSITORY_URL}:latest; then
    echo "WARNING: Failed to pull image from ECR, container may fail to start"
fi

# Create docker-compose.yml for API service
# Build the file in parts to handle conditional EFS mount
cat > ${APP_DIR}/docker-compose.yml <<EOF
version: '3.8'

services:
  api:
    image: ${ECR_REPOSITORY_URL}:latest
    container_name: nexus-ai-api
    network_mode: host
    environment:
      - ENVIRONMENT=${ENVIRONMENT}
      - AWS_REGION=${AWS_REGION}
      - AWS_DEFAULT_REGION=${AWS_REGION}
      - DYNAMODB_REGION=${DYNAMODB_REGION}
      - AGENT_PROJECTS_TABLE=${AGENT_PROJECTS_TABLE}
      - AGENT_INSTANCES_TABLE=${AGENT_INSTANCES_TABLE}
      - SQS_QUEUE_URL=${SQS_QUEUE_URL}
      - EFS_MOUNT_PATH=${EFS_MOUNT_PATH}
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
EOF

# Add EFS volume mount conditionally
if [ "$MOUNT_SUCCESS" = true ]; then
    echo "      - ${EFS_MOUNT_PATH}:/mnt/efs:rw" >> ${APP_DIR}/docker-compose.yml
else
    echo "      # EFS mount skipped - EFS not available" >> ${APP_DIR}/docker-compose.yml
fi

# Append the rest of the docker-compose.yml
cat >> ${APP_DIR}/docker-compose.yml <<EOF
      # Mount Docker socket to allow container to build Docker images
      - /var/run/docker.sock:/var/run/docker.sock:rw
      # Mount project root (cloned from GitHub) for Docker builds
      - ${PROJECT_ROOT}:/app:rw
    # Run as root to access Docker socket
    # TODO: In production, use non-root user with docker group (GID 999 typically)
    user: root
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "awslogs"
      options:
        awslogs-group: /ecs/nexus-ai-api-${ENVIRONMENT}
        awslogs-region: ${AWS_REGION}
EOF

# Start API service
cd ${APP_DIR}
docker-compose up -d

# Wait for service to be healthy
echo "Waiting for API service to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "API service is healthy!"
        break
    fi
    echo "Attempt $i: API service not ready yet, waiting..."
    sleep 10
done

# Install CloudWatch agent for logs (optional)
# yum install -y amazon-cloudwatch-agent

echo "EC2 API service initialization completed at $(date)"

