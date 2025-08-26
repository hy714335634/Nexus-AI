# System Tools 系统工具

本目录包含 Nexus-AI 平台的核心系统工具，为 Strands agents 提供完整的项目管理、模板管理、配置管理等功能。

## 📋 工具概览

| 工具文件 | 描述 | 工具数量 |
|---------|------|---------|
| [agent_template_provider.py](#1-agenttemplateprovider) | Agent模板管理工具 | 6 |
| [content_generator.py](#2-contentgenerator) | 内容生成工具 | 5 |
| [local_tools_manager.py](#3-localtoolsmanager) | 本地工具管理器 | 3 |
| [mcp_config_manager.py](#4-mcpconfigmanager) | MCP配置管理工具 | 10 |
| [project_manager.py](#5-projectmanager) | 项目管理工具 | 12 |
| [prompt_template_provider.py](#6-prompttemplateprovider) | 提示词模板提供工具 | 8 |
| [tool_template_provider.py](#7-tooltemplateprovider) | 工具模板提供工具 | 10 |

---

## 1. agent_template_provider.py
> **Agent模板管理工具**

### 🔧 可用工具

- **`get_all_templates`** - 获取所有可用的Agent模板信息
- **`search_templates_by_tags`** - 根据标签搜索模板
- **`search_templates_by_description`** - 根据描述关键词搜索模板
- **`get_template_by_id`** - 根据模板ID获取特定模板信息
- **`get_template_content`** - 获取模板文件的内容
- **`get_available_tags`** - 获取所有可用的标签

---

## 2. content_generator.py
> **内容生成工具**

### 🔧 可用工具

- **`generate_content`** - 根据类型生成内容文件
- **`check_file_exists`** - 检查指定类型和名称的文件是否已存在
- **`list_generated_files`** - 列出指定类型的所有已生成文件
- **`get_available_name_suggestions`** - 为冲突的文件名提供可用的名称建议
- **`list_project_agents`** - 列出所有项目agent目录

---

## 3. local_tools_manager.py
> **本地工具管理器**

### 🔧 可用工具

- **`get_local_tools_scripts`** - 获取tools/system_tools目录下除自身外所有本地工具脚本的名称及路径
- **`get_local_tools_descriptions`** - 获取tools/system_tools目录下除自身外所有本地工具的描述信息
- **`get_local_tools_info_by_path`** - 根据给定的路径，返回该路径脚本中所有本地工具的信息

---

## 4. mcp_config_manager.py
> **MCP配置管理工具**

### 🔧 可用工具

- **`get_all_mcp_servers`** - 获取所有MCP服务器配置信息
- **`get_enabled_mcp_servers`** - 获取所有启用的MCP服务器配置信息
- **`get_mcp_server_by_name`** - 根据服务器名称获取特定MCP服务器配置信息
- **`search_mcp_servers_by_command`** - 根据命令搜索MCP服务器
- **`search_mcp_servers_by_args`** - 根据参数关键词搜索MCP服务器
- **`get_mcp_servers_with_auto_approve`** - 获取配置了自动批准工具的MCP服务器
- **`get_mcp_servers_with_env_vars`** - 获取配置了环境变量的MCP服务器
- **`get_mcp_server_statistics`** - 获取MCP服务器配置统计信息
- **`reload_mcp_configs`** - 重新加载MCP配置文件
- **`validate_mcp_server_config`** - 验证指定MCP服务器的配置是否有效

---

## 5. project_manager.py
> **项目管理工具**

### 🔧 可用工具

- **`project_init`** - 项目初始化
  - 根据项目名称在 projects/ 下创建完整的项目目录结构
  - 自动生成 config.yaml, README.md, status.yaml 文件
  - 创建 agents/, tools/, prompts/ 子目录

- **`update_project_config`** - 更新项目配置
  - 根据项目名称创建或更新项目配置文件
  - 支持自定义描述和版本号，保留现有配置

- **`get_project_config`** - 获取项目配置
  - 获取指定项目的配置信息
  - 返回JSON格式的完整配置数据和文件元信息

- **`update_project_readme`** - 更新项目README
  - 根据项目配置和状态自动生成 README.md
  - 包含项目描述、目录结构、各Agent阶段进度，支持添加额外内容

- **`get_project_readme`** - 获取项目README
  - 获取指定项目的README.md内容
  - 返回完整内容和文件统计信息（行数、字数、字符数）

- **`update_project_status`** - 更新项目状态
  - 更新 status.yaml 中的阶段状态
  - 支持6个标准阶段，自动创建Agent条目和所有阶段结构

- **`get_project_status`** - 查询项目状态
  - 查询项目状态信息
  - 支持查询所有Agent、指定Agent或指定阶段，返回详细的状态信息

- **`update_project_stage_content`** - 写入阶段内容
  - 将内容写入 projects/<project_name>/<agent_name>/<stage_name>.json
  - 自动创建必要的目录结构

- **`get_project_stage_content`** - 读取阶段内容
  - 读取指定阶段文件的内容
  - 返回文件内容和元数据信息

- **`list_project_agents`** - 列出项目Agent
  - 列出指定项目中的所有Agent目录
  - 包含文件统计和阶段文件信息

- **`list_all_projects`** - 列出所有项目
  - 列出所有项目，包含项目配置信息和Agent数量统计

- **`generate_content`**

## 6. prompt_template_provider.py
> **提示词模板提供工具**

### 🔧 可用工具

- **`list_prompt_templates`** - 列出所有可用的提示词模板
- **`get_prompt_template`** - 获取指定提示词模板的完整内容
- **`get_template_metadata`** - 获取指定模板的元数据信息（不包含完整内容）
- **`get_prompt_template_info`** - 获取提示词模板的基本信息（不包含完整内容）
- **`validate_prompt_template`** - 验证提示词模板文件的格式是否正确
- **`validate_all_templates`** - 验证所有提示词模板文件的格式
- **`get_template_structure`** - 获取提示词模板的结构概览
- **`search_templates_by_category`** - 根据分类搜索模板

---

## 7. tool_template_provider.py
> **工具模板提供工具**

### 🔧 可用工具

- **`list_all_tools`** - 列出所有可用的工具，包括模板工具、生成工具和内置工具
- **`get_builtin_tools`** - 获取所有内置工具信息
- **`get_template_tools`** - 获取所有模板工具信息
- **`get_generated_tools`** - 获取所有生成工具信息
- **`search_tools_by_name`** - 根据工具名称搜索工具
- **`search_tools_by_category`** - 根据分类搜索工具
- **`get_tool_details`** - 获取特定工具的详细信息
- **`get_tool_content`** - 获取工具的源代码内容
- **`validate_tool_file`** - 验证工具文件的格式和语法
- **`get_available_categories`** - 获取所有可用的工具分类

---

## 📚 使用说明

1. **工具调用格式**: 所有工具都使用 `@tool` 装饰器，可被 Strands agents 直接调用
2. **返回格式**: 大部分工具返回 JSON 格式的结构化数据，便于程序处理
3. **错误处理**: 所有工具都包含完整的错误处理和参数验证
4. **文档完整**: 每个工具都有详细的文档字符串，说明参数和返回值

## 🔗 相关文档

- [Strands Framework 文档](https://docs.strands.ai/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [AWS Bedrock 文档](https://docs.aws.amazon.com/bedrock/)

---

*最后更新: 2025-08-25*
