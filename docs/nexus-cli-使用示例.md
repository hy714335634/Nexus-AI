# Nexus-CLI 功能说明和使用示例

## 📋 目录
- [功能概览](#功能概览)
- [项目管理命令](#项目管理命令)
- [代理管理命令](#代理管理命令)
- [备份管理命令](#备份管理命令)
- [系统概览命令](#系统概览命令)

---

## 功能概览

Nexus-CLI 是一个 kubectl 风格的命令行工具，用于管理 Nexus-AI 后端资源，包括：
- ✅ 项目管理（创建、列表、详情、构建、备份、恢复、删除）
- ✅ 代理管理（列表、详情）
- ✅ 备份管理（列表、详情、验证、删除）
- ✅ 系统概览（统计信息）

**版本**: 2.1.0

---

## 项目管理命令

### 1. `project list` - 列出所有项目

**功能描述**: 显示所有项目的简要信息，包括名称、描述、代理数量、模板数量、提示词数量、工具数量和创建时间。

**命令参数**:
```bash
./nexus-cli project list [--output <format>]
```

**参数说明**:
- `--output, -o`: 输出格式，可选值：`json`、`table`（默认）、`text`

**使用示例**:
```bash
# 默认表格格式
./nexus-cli project list

# JSON 格式（用于脚本处理）
./nexus-cli project list --output json

# 文本格式
./nexus-cli project list --output text
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 2. `project describe` - 查看项目详情

**功能描述**: 显示项目的详细信息，包括：
- 项目基本信息和描述
- 所有代理及其描述
- 依赖的工具、提示词、模板
- 项目位置和文档路径

**命令参数**:
```bash
./nexus-cli project describe <name> [--output <format>]
```

**参数说明**:
- `<name>`: 项目名称（必需）
- `--output, -o`: 输出格式，可选值：`json`、`table`、`text`（默认）

**使用示例**:
```bash
# 查看项目详情（文本格式）
./nexus-cli project describe aws_pricing_agent

# JSON 格式输出
./nexus-cli project describe aws_pricing_agent --output json

# 查看其他项目
./nexus-cli project describe html_courseware_generator
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 3. `project init` - 创建新项目

**功能描述**: 初始化一个新的 Nexus-AI 项目，创建必要的目录结构和配置文件。

**命令参数**:
```bash
./nexus-cli project init <name> [--description <text>] [--dry-run]
```

**参数说明**:
- `<name>`: 项目名称（必需）
- `--description, -d`: 项目描述（可选）
- `--dry-run`: 预览模式，不实际执行操作

**使用示例**:
```bash
# 创建基本项目
./nexus-cli project init my_new_project

# 创建带描述的项目
./nexus-cli project init my_new_project --description "我的新 AI 代理项目"

# 预览创建操作（不实际创建）
./nexus-cli project init my_new_project --dry-run
```

**是否破坏性**: ⚠️ **可能破坏性** - 如果项目已存在会报错，不会覆盖现有项目

---

### 4. `project backup` - 备份项目

**功能描述**: 创建项目的完整备份，包括：
- 项目配置和元数据
- 所有生成的代理
- 代理提示词和配置
- 自定义工具和实用程序
- SHA-256 校验和用于完整性验证

备份文件格式：`<project-name>_YYYYMMDD_HHMMSS.tar.gz`

**命令参数**:
```bash
./nexus-cli project backup <name> [--output <path>] [--dry-run] [--source-delete]
```

**参数说明**:
- `<name>`: 项目名称（必需）
- `--output, -o`: 自定义备份输出路径（可选，默认：`backups/`）
- `--dry-run`: 预览模式，显示将要备份的内容但不实际执行
- `--source-delete`: ⚠️ **危险选项** - 备份成功后删除源目录

**使用示例**:
```bash
# 基本备份
./nexus-cli project backup aws_pricing_agent

# 备份到自定义位置
./nexus-cli project backup aws_pricing_agent --output /path/to/backups/

# 预览备份操作（不实际执行）
./nexus-cli project backup aws_pricing_agent --dry-run

# ⚠️ 备份并删除源目录（危险操作）
./nexus-cli project backup aws_pricing_agent --source-delete
```

**是否破坏性**: 
- 默认：❌ **非破坏性** - 只创建备份，不删除源文件
- 使用 `--source-delete`：⚠️ **高度破坏性** - 会删除项目目录、代理目录、提示词目录和工具目录

---

### 5. `project restore` - 从备份恢复项目

**功能描述**: 从备份文件恢复项目，包括所有资源。支持：
- 恢复到原始名称（从备份推断）
- 恢复到不同名称（项目克隆）
- 强制覆盖现有项目（会创建安全备份）

**命令参数**:
```bash
./nexus-cli project restore [--name <name>] --from-backup <path> [--force] [--dry-run]
```

**参数说明**:
- `--name, -n`: 项目名称（可选，默认从备份推断）
- `--from-backup`: 备份文件路径（必需）
- `--force, -f`: 强制覆盖现有项目（会先创建安全备份）
- `--dry-run`: 预览模式

**使用示例**:
```bash
# 恢复到原始名称（从备份推断）
./nexus-cli project restore --from-backup backups/aws_pricing_agent_20241125_143022.tar.gz

# 恢复到原始名称（显式指定）
./nexus-cli project restore --name aws_pricing_agent --from-backup backups/aws_pricing_agent_20241125.tar.gz

# 克隆项目（恢复到不同名称）
./nexus-cli project restore --name dev_pricing_agent --from-backup backups/aws_pricing_agent_20241125.tar.gz

# 强制覆盖现有项目（会先创建安全备份）
./nexus-cli project restore --name aws_pricing_agent --from-backup backups/aws_pricing_agent_20241125.tar.gz --force

# 预览恢复操作
./nexus-cli project restore --from-backup backups/aws_pricing_agent_20241125.tar.gz --dry-run
```

**是否破坏性**: 
- 默认（项目不存在）：❌ **非破坏性** - 只创建新项目
- 默认（项目已存在）：⚠️ **会失败** - 需要 `--force` 才能覆盖
- 使用 `--force`：⚠️ **破坏性** - 会覆盖现有项目，但会先创建安全备份

---

### 6. `project delete` - 删除项目

**功能描述**: 永久删除项目及其所有相关资源，包括：
- 项目目录
- 所有代理文件
- 所有提示词文件
- 所有工具文件

**命令参数**:
```bash
./nexus-cli project delete <name> [--force] [--dry-run]
```

**参数说明**:
- `<name>`: 项目名称（必需）
- `--force, -f`: 跳过确认提示
- `--dry-run`: 预览模式，显示将要删除的内容

**使用示例**:
```bash
# 交互式删除（会提示确认）
./nexus-cli project delete my_test_project

# 强制删除（跳过确认）
./nexus-cli project delete my_test_project --force

# 预览删除操作（不实际执行）
./nexus-cli project delete my_test_project --dry-run
```

**是否破坏性**: ⚠️ **高度破坏性** - 永久删除项目及其所有资源，无法恢复（除非有备份）

---

### 7. `project build` - 构建 Docker 镜像

**功能描述**: 为项目构建 Docker 镜像。默认构建项目中的所有代理，也可以指定特定代理。

**命令参数**:
```bash
./nexus-cli project build <project_name> [--agent <name>] [--tag <tag>] [--no-cache] [--push [<registry>]] [--platform <platform>] [--build-arg <KEY=VALUE>] [--no-create-repo]
```

**参数说明**:
- `<project_name>`: 项目名称（必需）
- `--agent, -a`: 构建特定代理（可选，默认构建所有代理）
- `--tag, -t`: 自定义镜像标签（默认：`latest`）
- `--no-cache`: 不使用缓存构建
- `--push`: 推送到注册表（无参数使用默认注册表，或提供自定义 URI）
- `--platform`: 目标平台（如：`linux/amd64`）
- `--build-arg`: 构建参数（格式：`KEY=VALUE`，可多次使用）
- `--no-create-repo`: 禁用自动创建 ECR 仓库

**使用示例**:
```bash
# 构建项目中的所有代理
./nexus-cli project build aws_pricing_agent

# 构建特定代理
./nexus-cli project build aws_pricing_agent --agent requirements_analyzer

# 使用自定义标签构建
./nexus-cli project build aws_pricing_agent --tag v1.0.0

# 不使用缓存构建
./nexus-cli project build aws_pricing_agent --no-cache

# 构建并推送到默认注册表
./nexus-cli project build aws_pricing_agent --push

# 构建并推送到自定义注册表
./nexus-cli project build aws_pricing_agent --push=123456.dkr.ecr.us-east-1.amazonaws.com/my-registry

# 为特定平台构建
./nexus-cli project build aws_pricing_agent --platform linux/amd64

# 使用构建参数
./nexus-cli project build aws_pricing_agent --build-arg AWS_REGION=us-east-1
```

**是否破坏性**: ❌ **非破坏性** - 只构建镜像，不修改项目文件（需要 Docker 运行）

---

## 代理管理命令

### 8. `agents list` - 列出所有代理

**功能描述**: 显示所有代理的简要信息，包括名称、描述、所属项目、工具数量和创建时间。

**命令参数**:
```bash
./nexus-cli agents list [--project <name>] [--output <format>]
```

**参数说明**:
- `--project, -p`: 按项目过滤（可选）
- `--output, -o`: 输出格式，可选值：`json`、`table`（默认）、`text`

**使用示例**:
```bash
# 列出所有代理
./nexus-cli agents list

# 列出特定项目的代理
./nexus-cli agents list --project aws_pricing_agent

# JSON 格式输出
./nexus-cli agents list --output json

# 列出特定项目的代理（JSON 格式）
./nexus-cli agents list --project aws_pricing_agent --output json
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 9. `agents describe` - 查看代理详情

**功能描述**: 显示代理的详细信息，包括：
- 基本信息和描述
- 功能和能力
- 工具和依赖
- 支持的模型
- 交互方法
- 文档路径

**命令参数**:
```bash
./nexus-cli agents describe <name> [--output <format>]
```

**参数说明**:
- `<name>`: 代理名称（必需）
- `--output, -o`: 输出格式，可选值：`json`、`table`、`text`（默认）

**使用示例**:
```bash
# 查看代理详情
./nexus-cli agents describe requirements_analyzer

# JSON 格式输出
./nexus-cli agents describe requirements_analyzer --output json

# 查看其他代理
./nexus-cli agents describe aws_architect
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

## 备份管理命令

### 10. `backup list` - 列出所有备份

**功能描述**: 显示所有备份文件的列表，包括文件名、项目名称、文件大小和创建时间。

**命令参数**:
```bash
./nexus-cli backup list [--output <format>]
```

**参数说明**:
- `--output, -o`: 输出格式，可选值：`json`、`table`（默认）、`text`

**使用示例**:
```bash
# 列出所有备份（表格格式）
./nexus-cli backup list

# JSON 格式输出
./nexus-cli backup list --output json

# 文本格式输出
./nexus-cli backup list --output text
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 11. `backup describe` - 查看备份详情

**功能描述**: 显示备份文件的详细信息，包括：
- 基本元数据（项目、大小、创建日期）
- 清单详情（版本、文件数量）
- 资源分解（代理、提示词、工具）
- 完整性状态（校验和、验证）

**命令参数**:
```bash
./nexus-cli backup describe <name> [--output <format>]
```

**参数说明**:
- `<name>`: 备份文件名（必需）
- `--output, -o`: 输出格式，可选值：`json`、`table`、`text`（默认）

**使用示例**:
```bash
# 查看备份详情
./nexus-cli backup describe aws_pricing_agent_20241125_143022.tar.gz

# JSON 格式输出
./nexus-cli backup describe aws_pricing_agent_20241125_143022.tar.gz --output json

# 查看其他备份
./nexus-cli backup describe html_courseware_generator_20241125.tar.gz
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 12. `backup validate` - 验证备份完整性

**功能描述**: 对备份文件执行全面的完整性验证，包括：
- 归档格式验证（tar.gz）
- 清单存在性和有效性
- 所有文件的 SHA-256 校验和验证
- 路径结构验证
- 版本兼容性检查

**命令参数**:
```bash
./nexus-cli backup validate <path>
```

**参数说明**:
- `<path>`: 备份文件路径（必需）

**使用示例**:
```bash
# 验证备份文件
./nexus-cli backup validate backups/aws_pricing_agent_20241125_143022.tar.gz

# 验证其他备份
./nexus-cli backup validate backups/html_courseware_generator_20241125.tar.gz

# 使用通配符（需要 shell 展开）
./nexus-cli backup validate backups/aws_pricing_agent_*.tar.gz
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

### 13. `backup delete` - 删除备份文件

**功能描述**: 永久删除备份文件。默认会提示确认，除非使用 `--force` 选项。

**命令参数**:
```bash
./nexus-cli backup delete <name> [--force]
```

**参数说明**:
- `<name>`: 备份文件名（必需）
- `--force, -f`: 跳过确认提示

**使用示例**:
```bash
# 交互式删除（会提示确认）
./nexus-cli backup delete aws_pricing_agent_20241125_143022.tar.gz

# 强制删除（跳过确认）
./nexus-cli backup delete aws_pricing_agent_20241125_143022.tar.gz --force

# 清理旧备份
./nexus-cli backup list
./nexus-cli backup delete old_backup_20241001.tar.gz --force
```

**是否破坏性**: ⚠️ **破坏性** - 永久删除备份文件，无法恢复（但不会影响原始项目）

---

## 系统概览命令

### 14. `overview` - 系统概览

**功能描述**: 显示系统范围的统计信息，包括：
- 项目总数
- 代理总数
- 模板总数
- 提示词总数
- 工具总数

**命令参数**:
```bash
./nexus-cli overview [--output <format>]
```

**参数说明**:
- `--output, -o`: 输出格式，可选值：`json`、`table`（默认）、`text`

**使用示例**:
```bash
# 查看系统概览（表格格式）
./nexus-cli overview

# JSON 格式输出（用于脚本处理）
./nexus-cli overview --output json

# 文本格式输出
./nexus-cli overview --output text
```

**是否破坏性**: ❌ **非破坏性** - 只读操作，不会修改任何数据

---

## 📊 破坏性操作总结

### 高度破坏性操作（需谨慎使用）

1. **`project delete`** - 永久删除项目及其所有资源
   - 使用前建议先备份：`./nexus-cli project backup <name>`
   - 可以使用 `--dry-run` 预览

2. **`project backup --source-delete`** - 备份后删除源目录
   - ⚠️ 会删除项目目录、代理目录、提示词目录和工具目录
   - 确保备份成功后再删除

3. **`backup delete`** - 永久删除备份文件
   - 不会影响原始项目，但备份无法恢复

### 可能破坏性操作（有安全保护）

1. **`project restore --force`** - 强制恢复（覆盖现有项目）
   - ✅ 会自动创建安全备份
   - ✅ 会提示确认（除非使用 `--force`）

2. **`project init`** - 创建新项目
   - 如果项目已存在会报错，不会覆盖

### 非破坏性操作（安全使用）

- `project list` / `describe`
- `agents list` / `describe`
- `backup list` / `describe` / `validate`
- `overview`
- `project backup`（默认，不使用 `--source-delete`）
- `project build`

---

## 🔒 安全建议

1. **重要操作前先备份**:
   ```bash
   ./nexus-cli project backup <project_name>
   ```

2. **使用 `--dry-run` 预览操作**:
   ```bash
   ./nexus-cli project delete <name> --dry-run
   ./nexus-cli project restore --from-backup <backup> --dry-run
   ```

3. **验证备份完整性**:
   ```bash
   ./nexus-cli backup validate <backup_file>
   ```

4. **定期清理旧备份**:
   ```bash
   ./nexus-cli backup list
   ./nexus-cli backup delete <old_backup> --force
   ```

---

## 📝 完整工作流示例

### 示例 1: 创建和管理项目

```bash
# 1. 创建新项目
./nexus-cli project init my_test_project --description "测试项目"

# 2. 查看项目列表
./nexus-cli project list

# 3. 查看项目详情
./nexus-cli project describe my_test_project

# 4. 创建备份
./nexus-cli project backup my_test_project

# 5. 验证备份
./nexus-cli backup validate backups/my_test_project_*.tar.gz

# 6. 查看备份列表
./nexus-cli backup list
```

### 示例 2: 项目克隆

```bash
# 1. 备份源项目
./nexus-cli project backup aws_pricing_agent

# 2. 从备份克隆到新名称
./nexus-cli project restore --name aws_pricing_agent_dev --from-backup backups/aws_pricing_agent_*.tar.gz

# 3. 验证克隆的项目
./nexus-cli project describe aws_pricing_agent_dev
```

### 示例 3: 灾难恢复

```bash
# 1. 验证备份完整性
./nexus-cli backup validate backups/aws_pricing_agent_20241125.tar.gz

# 2. 强制恢复（覆盖现有项目，会自动创建安全备份）
./nexus-cli project restore --name aws_pricing_agent --from-backup backups/aws_pricing_agent_20241125.tar.gz --force

# 3. 验证恢复的项目
./nexus-cli project describe aws_pricing_agent
```

### 示例 4: 系统监控

```bash
# 1. 查看系统概览
./nexus-cli overview

# 2. 列出所有项目
./nexus-cli project list --output json

# 3. 列出所有代理
./nexus-cli agents list --output json

# 4. 查看备份统计
./nexus-cli backup list --output json
```

---

## 🛠️ 故障排除

### 命令未找到
```bash
# 确保在 Nexus-AI 根目录
cd /path/to/Nexus-AI

# 确保脚本可执行
chmod +x nexus-cli

# 或使用 Python 直接运行
python -m nexus_utils.cli.main --help
```

### 项目已存在错误
```bash
# 使用 --force 强制覆盖（会创建安全备份）
./nexus-cli project restore --name <name> --from-backup <backup> --force

# 或先删除再恢复
./nexus-cli project delete <name> --force
./nexus-cli project restore --name <name> --from-backup <backup>
```

### 备份验证失败
```bash
# 验证备份
./nexus-cli backup validate <backup_file>

# 如果损坏，尝试其他备份
./nexus-cli backup list
./nexus-cli project restore --from-backup <other_backup>
```

---

## 📚 更多帮助

```bash
# 查看主帮助
./nexus-cli --help

# 查看命令组帮助
./nexus-cli project --help
./nexus-cli agents --help
./nexus-cli backup --help

# 查看子命令帮助
./nexus-cli project backup --help
./nexus-cli project restore --help
```

---

**版本**: 2.1.0  
**最后更新**: 基于代码分析生成

