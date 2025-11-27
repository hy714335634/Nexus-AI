# 在容器中执行 Docker 构建

## 🔍 问题分析

你的后端服务（`agent_deployment_service.py`）使用 `bedrock_agentcore_starter_toolkit` 的 `Runtime` 类来部署 Agent。这个工具包内部会调用 Docker 来构建镜像并推送到 ECR。

**当前架构**：
- API 服务运行在 ECS Fargate（serverless 容器）
- Fargate 容器无法直接访问 Docker daemon
- 需要 Docker 来构建 Agent 镜像

## ✅ 解决方案

### 方案 1: 使用 AWS CodeBuild（推荐）⭐

**优点**：
- ✅ 专门用于构建任务
- ✅ 自动管理 Docker 环境
- ✅ 可以并行构建多个镜像
- ✅ 与 ECR 集成良好
- ✅ 支持构建日志和监控

**实现方式**：

1. **创建 CodeBuild 项目**（通过 Terraform）

```terraform
resource "aws_codebuild_project" "agent_builder" {
  name          = "${var.project_name}-agent-builder-${var.environment}"
  description   = "Build Docker images for generated agents"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 60

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type    = "BUILD_GENERAL1_MEDIUM"
    image           = "aws/codebuild/standard:7.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true  # 必需，用于 Docker 构建

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
  }

  source {
    type            = "NO_SOURCE"
    buildspec       = "buildspec.yml"
  }
}
```

2. **修改部署服务，调用 CodeBuild**

```python
import boto3

def build_agent_image_via_codebuild(self, project_name: str, agent_name: str):
    """通过 CodeBuild 构建 Agent 镜像"""
    codebuild = boto3.client('codebuild', region_name=self.region)
    
    # 准备构建环境变量
    env_vars = [
        {'name': 'PROJECT_NAME', 'value': project_name},
        {'name': 'AGENT_NAME', 'value': agent_name},
        {'name': 'ECR_REPO', 'value': f'{self.ecr_repo}:{agent_name}'},
    ]
    
    # 启动构建
    response = codebuild.start_build(
        projectName='nexus-ai-agent-builder-prod',
        environmentVariablesOverride=env_vars,
        sourceTypeOverride='NO_SOURCE',
    )
    
    build_id = response['build']['id']
    
    # 等待构建完成
    waiter = codebuild.get_waiter('build_succeeded')
    waiter.wait(id=build_id)
    
    return build_id
```

### 方案 2: 使用 ECS Task with EC2 Launch Type

**优点**：
- ✅ 可以直接访问 Docker daemon
- ✅ 灵活性高

**缺点**：
- ❌ 需要管理 EC2 实例
- ❌ 成本较高
- ❌ 需要配置和维护

**实现方式**：

1. **创建 EC2 启动类型的 ECS 集群**

```terraform
resource "aws_ecs_cluster" "docker_builder" {
  name = "${var.project_name}-docker-builder-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# EC2 实例需要安装 Docker
# 使用 user_data 脚本安装 Docker
```

2. **在任务定义中挂载 Docker socket**

```terraform
resource "aws_ecs_task_definition" "docker_builder" {
  family = "${var.project_name}-docker-builder-${var.environment}"
  
  container_definitions = jsonencode([{
    name  = "docker-builder"
    image = aws_ecr_repository.api.repository_url
    
    mountPoints = [{
      sourceVolume  = "docker-sock"
      containerPath = "/var/run/docker.sock"
      readOnly      = false
    }]
  }])
  
  volume {
    name = "docker-sock"
    host_path = "/var/run/docker.sock"
  }
}
```

### 方案 3: 使用 Docker SDK + 外部 Docker 服务

**实现方式**：

使用 Docker SDK 连接到远程 Docker daemon（例如，运行在 EC2 上的 Docker）：

```python
import docker

def build_agent_image_via_remote_docker(self, project_name: str, agent_name: str):
    """通过远程 Docker daemon 构建镜像"""
    # 连接到远程 Docker daemon
    client = docker.DockerClient(
        base_url='tcp://docker-host:2376',
        tls=True,
        # 或使用 SSH: base_url='ssh://user@docker-host'
    )
    
    # 构建镜像
    image, logs = client.images.build(
        path=f'/app/projects/{project_name}',
        tag=f'{self.ecr_repo}:{agent_name}',
        dockerfile='Dockerfile',
    )
    
    # 推送到 ECR
    client.images.push(f'{self.ecr_repo}:{agent_name}')
```

### 方案 4: 使用 Kaniko（无 Docker daemon 构建）

**优点**：
- ✅ 不需要 Docker daemon
- ✅ 可以在 Fargate 中运行
- ✅ 安全性更好

**实现方式**：

```dockerfile
# 使用 Kaniko 构建器
FROM gcr.io/kaniko-project/executor:latest

# 复制构建上下文
COPY projects/${PROJECT_NAME} /workspace

# 构建并推送
RUN /kaniko/executor \
  --context /workspace \
  --dockerfile /workspace/Dockerfile \
  --destination ${ECR_REPO}:${AGENT_NAME}
```

## 🎯 推荐方案：AWS CodeBuild

### 为什么选择 CodeBuild？

1. **专门用于构建任务**：CodeBuild 就是为构建 Docker 镜像设计的
2. **无需管理基础设施**：完全托管，无需管理 EC2 实例
3. **自动扩展**：可以并行构建多个镜像
4. **与 ECR 集成**：自动处理 ECR 认证
5. **成本效益**：按使用量付费，比维护 EC2 实例更便宜

### 实现步骤

#### 1. 创建 CodeBuild 项目（Terraform）

```terraform
# infrastructure/09-codebuild.tf

resource "aws_iam_role" "codebuild" {
  name = "${var.project_name}-codebuild-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "codebuild.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/codebuild/${var.project_name}-agent-builder-*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
        ]
        Resource = "${aws_s3_bucket.codebuild_artifacts.arn}/*"
      },
    ]
  })
}

resource "aws_codebuild_project" "agent_builder" {
  name          = "${var.project_name}-agent-builder-${var.environment}"
  description   = "Build Docker images for generated agents"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 60

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_MEDIUM"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.account_id
    }
  }

  source {
    type            = "NO_SOURCE"
    buildspec       = file("${path.module}/buildspec-agent.yml")
  }

  logs_config {
    cloudwatch_logs {
      group_name  = "/aws/codebuild/${var.project_name}-agent-builder-${var.environment}"
      stream_name = "build-logs"
    }
  }
}

# S3 bucket for build artifacts (如果需要)
resource "aws_s3_bucket" "codebuild_artifacts" {
  bucket = "${var.project_name}-codebuild-artifacts-${var.environment}"
}
```

#### 2. 创建 buildspec 文件

```yaml
# infrastructure/buildspec-agent.yml

version: 0.2

phases:
  pre_build:
    commands:
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com
      - REPOSITORY_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$ECR_REPO_NAME
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:=latest}
  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image...
      - cd /codebuild/output/src
      - docker build -t $REPOSITORY_URI:$IMAGE_TAG -f projects/$PROJECT_NAME/$AGENT_NAME/Dockerfile projects/$PROJECT_NAME/$AGENT_NAME
      - docker tag $REPOSITORY_URI:$IMAGE_TAG $REPOSITORY_URI:latest
  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker images...
      - docker push $REPOSITORY_URI:$IMAGE_TAG
      - docker push $REPOSITORY_URI:latest
      - echo Writing image definitions file...
      - printf '[{"name":"%s","imageUri":"%s"}]' $CONTAINER_NAME $REPOSITORY_URI:$IMAGE_TAG > imagedefinitions.json
```

#### 3. 修改部署服务调用 CodeBuild

```python
# api/services/agent_deployment_service.py

import boto3
from botocore.exceptions import ClientError

def build_agent_image_via_codebuild(
    self, 
    project_name: str, 
    agent_name: str,
    ecr_repo_name: str
) -> str:
    """通过 CodeBuild 构建 Agent 镜像"""
    codebuild = boto3.client('codebuild', region_name=self.region)
    
    # 准备构建环境变量
    env_vars = [
        {'name': 'PROJECT_NAME', 'value': project_name},
        {'name': 'AGENT_NAME', 'value': agent_name},
        {'name': 'ECR_REPO_NAME', 'value': ecr_repo_name},
        {'name': 'CONTAINER_NAME', 'value': agent_name},
    ]
    
    try:
        # 启动构建
        response = codebuild.start_build(
            projectName=f'{settings.PROJECT_NAME}-agent-builder-{settings.ENVIRONMENT}',
            environmentVariablesOverride=env_vars,
            sourceTypeOverride='NO_SOURCE',
        )
        
        build_id = response['build']['id']
        logger.info(f"Started CodeBuild: {build_id}")
        
        # 等待构建完成（可选，也可以异步处理）
        waiter = codebuild.get_waiter('build_succeeded')
        waiter.wait(id=build_id)
        
        logger.info(f"Build completed: {build_id}")
        return build_id
        
    except ClientError as e:
        logger.error(f"CodeBuild failed: {e}")
        raise AgentDeploymentError(f"构建失败: {e}")
```

## 📝 总结

**推荐使用 AWS CodeBuild**，因为：
1. ✅ 专门用于构建任务
2. ✅ 完全托管，无需管理基础设施
3. ✅ 可以在 Fargate 容器中调用
4. ✅ 自动处理 Docker 和 ECR 认证
5. ✅ 支持并行构建和监控

**不推荐在 Fargate 容器中直接运行 Docker**，因为：
- ❌ Fargate 是 serverless，无法访问 Docker daemon
- ❌ 需要额外的 EC2 实例和配置
- ❌ 安全性和隔离性较差

