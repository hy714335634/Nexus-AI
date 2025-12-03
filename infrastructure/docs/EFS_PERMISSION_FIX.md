# EFS Permission Fix

## Problem
The API Fargate service was unable to write to the EFS mount point, showing this error:
```
Current user: uid=1000(app) gid=1000(app) groups=1000(app)
EFS mount permissions: drwxr-xr-x 2 root root 6144 Dec  3 01:05 /mnt/efs
⚠️  Cannot create lock file (may be permission issue), waiting for another task...
```

## Root Cause
The EFS file system was mounted directly without an access point. When Fargate mounts EFS without an access point, the root directory is owned by `root:root` with `755` permissions. The container runs as user `app` (uid=1000, gid=1000), which only has read and execute permissions, not write permissions.

## Solution
Added an **EFS Access Point** with proper POSIX user/group configuration:

### Changes Made

#### 1. Added EFS Access Point (`02-storage-efs.tf`)
```hcl
resource "aws_efs_access_point" "nexus_ai" {
  count = var.create_vpc ? 1 : 0

  file_system_id = aws_efs_file_system.nexus_ai[0].id

  posix_user {
    uid = 1000  # Match container user
    gid = 1000  # Match container group
  }

  root_directory {
    path = "/nexus-ai"
    creation_info {
      owner_uid   = 1000  # Set directory owner to app user
      owner_gid   = 1000  # Set directory group to app group
      permissions = "755" # rwxr-xr-x
    }
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-efs-ap-${var.environment}"
  })
}
```

#### 2. Updated ECS Task Definitions (`05-compute-ecs.tf`)
Modified both API and Frontend task definitions to use the access point:

```hcl
volume {
  name = "efs-storage"

  efs_volume_configuration {
    file_system_id          = aws_efs_file_system.nexus_ai[0].id
    root_directory          = "/"
    transit_encryption      = "ENABLED"
    authorization_config {
      access_point_id = aws_efs_access_point.nexus_ai[0].id
      iam             = "DISABLED"
    }
  }
}
```

## How It Works

1. **EFS Access Point** creates a dedicated entry point into the EFS file system
2. **POSIX User Mapping**: All file operations through the access point are performed as uid=1000, gid=1000
3. **Root Directory Creation**: The access point automatically creates `/nexus-ai` directory with proper ownership (1000:1000)
4. **Container Mount**: When the container mounts `/mnt/efs`, it actually mounts to `/nexus-ai` on EFS with full write permissions

## Benefits

- ✅ Container can write to EFS without permission errors
- ✅ Proper isolation - each access point can have different permissions
- ✅ No need to run containers as root
- ✅ Follows AWS security best practices
- ✅ Automatic directory creation with correct ownership

## Deployment Steps

1. Apply the Terraform changes:
   ```bash
   cd infrastructure
   terraform plan
   terraform apply
   ```

2. The access point will be created automatically

3. Restart ECS services to pick up the new task definitions:
   ```bash
   aws ecs update-service --cluster nexus-ai-cluster-dev \
     --service nexus-ai-api-dev --force-new-deployment
   ```

4. Verify the fix by checking container logs:
   ```bash
   aws logs tail /ecs/nexus-ai-api-dev --follow
   ```

You should now see:
```
✅ Lock file created, starting git clone...
✅ Repository cloned successfully to EFS
```

## References
- [AWS EFS Access Points Documentation](https://docs.aws.amazon.com/efs/latest/ug/efs-access-points.html)
- [ECS Task Definition EFS Volume Configuration](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efs-volumes.html)
