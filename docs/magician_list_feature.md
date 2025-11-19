# Magician Agent List 功能使用说明

## 新增功能

为magician.py添加了`list`参数功能，允许用户查看所有可用的generated agents。

## 使用方法

### 1. 查看所有generated agents
```bash
python agents/system_agents/magician.py list
```

### 2. 查看帮助信息
```bash
python agents/system_agents/magician.py --help
```

## 功能特性

### 新增函数

1. **`get_generated_agents()`**
   - 获取所有generated agents的列表
   - 返回格式化的agent信息，包含：
     - name: Agent名称
     - description: Agent描述
     - path: Agent模板路径
     - category: Agent分类
     - tags: Agent标签

2. **`print_generated_agents()`**
   - 打印所有generated agents的详细信息
   - 格式化输出，包含编号、描述、路径、分类和标签

### 命令行参数

- `list`: 位置参数，显示所有可用的generated agents列表
- `-a, --agent`: 指定要使用的Agent模板路径
- `-i, --input`: 指定用户输入内容

## 输出格式

当使用`python agents/system_agents/magician.py list`时，会显示：

```
================================================================================
🤖 Generated Agents 列表 (共 X 个)
================================================================================

1. Agent名称
   描述: Agent功能描述
   路径: generated_agents_prompts/project_name/agent_name
   分类: Agent分类
   标签: tag1, tag2, tag3
   ------------------------------------------------------------

2. 另一个Agent名称
   描述: 另一个Agent功能描述
   路径: generated_agents_prompts/project_name/agent_name
   分类: Agent分类
   标签: tag1, tag2
   ------------------------------------------------------------

...

✅ 显示完成，共 X 个generated agents
```

## 代码实现

### 主要修改

1. **添加了`get_generated_agents()`函数**
   ```python
   def get_generated_agents():
       """获取所有generated agents的列表"""
       try:
           generated_agents = json.loads(list_prompt_templates(type="generated"))
           agents_list = generated_agents.get("templates", [])
           
           # 过滤并格式化generated agents信息
           formatted_agents = []
           for agent in agents_list:
               if "relative_path" in agent:
                   formatted_agent = {
                       "name": agent.get("name", "Unknown"),
                       "description": agent.get("description", "No description"),
                       "path": agent.get("relative_path", ""),
                       "category": agent.get("category", "Unknown"),
                       "tags": agent.get("tags", [])
                   }
                   formatted_agents.append(formatted_agent)
           
           return formatted_agents
       except Exception as e:
           print(f"❌ 获取generated agents时出现错误: {e}")
           return []
   ```

2. **添加了`print_generated_agents()`函数**
   ```python
   def print_generated_agents():
       """打印所有generated agents的详细信息"""
       agents = get_generated_agents()
       
       if not agents:
           print("❌ 没有找到任何generated agents")
           return
       
       print(f"\n{'='*80}")
       print(f"🤖 Generated Agents 列表 (共 {len(agents)} 个)")
       print(f"{'='*80}")
       
       for i, agent in enumerate(agents, 1):
           print(f"\n{i}. {agent['name']}")
           print(f"   描述: {agent['description']}")
           print(f"   路径: {agent['path']}")
           print(f"   分类: {agent['category']}")
           if agent['tags']:
               print(f"   标签: {', '.join(agent['tags'])}")
           print(f"   {'-'*60}")
       
       print(f"\n✅ 显示完成，共 {len(agents)} 个generated agents")
   ```

3. **修改了命令行参数解析**
   ```python
   parser.add_argument('list', nargs='?', const='list', 
                      help='显示所有可用的generated agents列表')
   ```

4. **添加了list参数处理逻辑**
   ```python
   # 处理list参数
   if args.list:
       print_generated_agents()
       return
   ```

## 注意事项

1. **只显示generated agents**: 该功能只显示通过`list_prompt_templates(type="generated")`获取的agents，不包含template agents
2. **错误处理**: 如果获取agents时出现错误，会显示错误信息并返回空列表
3. **格式化输出**: 输出格式清晰，包含所有重要信息
4. **兼容性**: 新功能不影响原有的其他功能

## 使用示例

```bash
# 查看所有generated agents
python agents/system_agents/magician.py list

# 使用特定agent
python agents/system_agents/magician.py -a "generated_agents_prompts/aws_pricing_agent/aws_pricing_agent" -i "查询AWS EC2价格"

# 使用magician编排功能
python agents/system_agents/magician.py -i "我需要一个数据分析工具"
```
