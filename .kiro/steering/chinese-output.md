# 中文输出规范

## 核心原则

**代码使用英文，注释使用中文，沟通交流使用中文**

### 代码规范

- 所有代码（变量名、函数名、类名、字符串等）保持英文
- 所有注释必须使用中文
- 函数和类的文档字符串必须使用中文
- 配置文件中的注释使用中文

### 代码示例

```python
# 计算产品价格的函数
def calculate_price(product_type: str, quantity: int) -> float:
    """
    计算产品价格

    参数:
        product_type (str): 产品类型
        quantity (int): 数量

    返回:
        float: 总价格
    """
    # 根据产品类型获取单价
    unit_price = get_unit_price(product_type)

    # 计算总价
    total_price = unit_price * quantity

    return total_price
```

### YAML 配置文件

```yaml
# Agent配置示例
agent:
  name: "pricing_analysis_agent"
  description: "AWS pricing analysis agent"
  category: "business_analysis"
  # 环境配置
  environments:
    production:
      max_tokens: 60000 # 最大令牌数
      temperature: 0.3 # 温度参数
```

### 错误处理

```python
try:
    # 执行业务逻辑
    result = process_data(input_data)
except ValueError as e:
    # 记录错误信息
    logger.error(f"Data processing failed: {str(e)}")
    raise Exception("Invalid input data format")
```

### 沟通交流规范

- 所有与用户的对话和交流必须使用中文
- 解释说明、回答问题使用中文
- 技术讨论和建议使用中文
- 错误提示和帮助信息使用中文

### 文档和说明

- README 文件、文档说明使用中文
- 用户界面文本使用中文
- 日志输出可以使用英文（保持代码一致性）

## 严格要求

**代码部分必须保持英文：**

- 变量名、函数名、类名
- 字符串常量和消息
- 异常信息
- 日志消息
- 配置键值

## 实施要求

1. **沟通交流**: 所有对话、解释、建议必须使用中文
2. **新代码**: 代码使用英文，注释使用中文
3. **现有代码**: 修改时保持代码英文，更新注释为中文
4. **文档更新**: 所有文档和 README 文件使用中文编写
5. **配置文件**: 配置键值使用英文，注释使用中文

## 质量标准

- 沟通交流使用自然、专业的中文表达
- 代码保持英文的专业性和国际化
- 注释使用准确、专业的中文表达
- 技术术语在注释和交流中使用规范的中文翻译
- 保持代码和注释风格的一致性

## 术语对照表

| 英文术语      | 中文翻译      |
| ------------- | ------------- |
| Agent         | 代理/智能代理 |
| Workflow      | 工作流        |
| Template      | 模板          |
| Configuration | 配置          |
| Function      | 函数          |
| Class         | 类            |
| Method        | 方法          |
| Parameter     | 参数          |
| Return        | 返回          |
| Exception     | 异常          |
| Error         | 错误          |
| Warning       | 警告          |
| Debug         | 调试          |
| Log           | 日志          |
| Database      | 数据库        |
| API           | 应用程序接口  |
| Service       | 服务          |
| Client        | 客户端        |
| Server        | 服务器        |
| Request       | 请求          |
| Response      | 响应          |
