---
name: browser-automation
description: 使用AI驱动的浏览器自动化工具集，支持自然语言指令执行网页交互、数据提取、表单填写等任务。集成Amazon Bedrock AgentCore、Nova Act和Browser Use，提供实时浏览器视图和批量数据采集能力。
---

# 浏览器自动化技能

当你需要进行网页交互、数据提取、自动化操作或批量数据采集时，使用此技能。该技能集提供5个强大的工具，支持自然语言指令驱动的浏览器自动化任务。

## 使用说明

1. **工具选择**：
   - **browser_with_nova_act**：基础浏览器自动化，适合简单任务（搜索、点击、提取）
   - **browser_with_live_view_nova**：Nova Act + 实时视图，适合需要监控的自动化任务
   - **browser_with_live_view_use**：AI驱动自动化，适合复杂的多步骤任务
   - **manage_browser_session**：会话管理，用于创建、查询、停止浏览器会话
   - **batch_extract_from_urls**：批量数据采集，适合从多个URL提取数据

2. **自然语言指令编写**：
   - 使用清晰、具体的指令描述任务
   - 对于多步骤任务，按顺序描述每个步骤
   - 明确指定要提取的数据类型和格式
   - 示例：
     - ✅ "搜索'Python教程'并提取前10个结果的标题和链接"
     - ✅ "在表单中填写姓名、邮箱和电话，然后点击提交按钮"
     - ❌ "搜索一些东西"（太模糊）

3. **实时视图使用**：
   - `browser_with_live_view_nova` 和 `browser_with_live_view_use` 提供实时浏览器视图
   - 通过 `viewer_url` 可以实时查看浏览器操作过程
   - 设置 `open_browser=False` 可以关闭自动打开浏览器（适合批量操作）
   - 如果端口冲突，修改 `viewer_port` 参数

4. **批量采集**：
   - 使用 `batch_extract_from_urls` 处理多个URL
   - `urls` 参数必须是JSON数组字符串格式
   - 设置合理的 `max_concurrent`（默认3），避免过载
   - 单个URL失败不影响其他URL的处理

5. **会话管理**：
   - 创建会话后保存 `session_id` 以便后续使用
   - 使用完会话后及时调用 `stop` 操作释放资源
   - 使用 `list_all` 查看所有活跃会话

6. **错误处理**：
   - 所有工具返回JSON格式，检查 `status` 字段
   - 常见错误类型：
     - `ValidationError`：参数验证错误
     - `ConnectionError`：网络连接错误
     - `TimeoutError`：操作超时
     - `ResourceError`：资源不可用（端口占用、会话不存在）

## Examples

- **网页搜索和数据提取**：
  ```
  使用 browser_with_nova_act 在Google搜索"机器学习教程"，
  提取前10个结果的标题、链接和描述
  ```

- **电商产品信息采集**：
  ```
  使用 browser_with_live_view_use 在亚马逊搜索"笔记本电脑"，
  提取前10个产品的名称、价格、评分和详细规格
  ```

- **批量网站监控**：
  ```
  使用 batch_extract_from_urls 批量检查多个网站的可用性，
  提取页面标题、加载时间和HTTP状态码，并发数设置为3
  ```

- **表单自动填写**：
  ```
  使用 browser_with_nova_act 访问联系表单页面，
  填写姓名、邮箱、电话和留言内容，然后提交表单
  ```

## Guidelines

- **API密钥安全**：不要在代码中硬编码API密钥，使用环境变量或安全配置管理
- **并发控制**：批量操作时设置合理的并发数，避免对目标网站造成过大压力
- **超时设置**：复杂任务建议增加超时时间，单个URL采集默认超时60秒
- **资源管理**：使用完会话后及时停止，避免会话泄漏导致资源浪费
- **实时视图**：批量操作时建议关闭自动打开浏览器（`open_browser=False`）
- **错误重试**：对于网络错误，可以考虑重试机制
- **遵守网站条款**：确保自动化操作符合目标网站的使用条款和robots.txt
- **数据验证**：提取的数据应该进行验证，确保格式和完整性
- **任务复杂度**：简单任务使用Nova Act，复杂多步骤任务使用Browser Use
- **性能优化**：批量采集时合理设置并发数，平衡速度和稳定性
