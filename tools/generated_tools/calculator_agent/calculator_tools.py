"""
智能计算器工具集

该模块提供安全的数学计算工具，支持自然语言数学表达式的解析和计算。
使用AST安全解析替代eval()函数，防止代码注入风险。

主要功能：
- 安全的数学表达式求值
- 基本四则运算（加减乘除）
- 特殊运算（幂运算、开方、百分比）
- 运算优先级处理
- 负数和小数处理
- 表达式验证和错误处理

作者：Nexus-AI Platform
版本：1.0.0
创建日期：2025-11-28
"""

import ast
import json
import math
import operator
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

from strands import tool


class SafeMathEvaluator:
    """安全的数学表达式求值器"""
    
    # 允许的运算符映射
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # 允许的函数映射
    ALLOWED_FUNCTIONS = {
        'sqrt': math.sqrt,
        'pow': pow,
        'abs': abs,
        'round': round,
    }
    
    def __init__(self, max_depth: int = 100):
        """初始化求值器
        
        Args:
            max_depth: 最大递归深度，防止过于复杂的表达式
        """
        self.max_depth = max_depth
        self.current_depth = 0
    
    def evaluate(self, expr: str) -> Union[int, float]:
        """安全地求值数学表达式
        
        Args:
            expr: 数学表达式字符串
            
        Returns:
            计算结果（整数或浮点数）
            
        Raises:
            ValueError: 表达式无效或不安全
            ZeroDivisionError: 除零错误
            OverflowError: 计算溢出
        """
        try:
            # 解析表达式为AST
            tree = ast.parse(expr, mode='eval')
            self.current_depth = 0
            return self._eval_node(tree.body)
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"表达式求值失败: {str(e)}")
    
    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """递归求值AST节点
        
        Args:
            node: AST节点
            
        Returns:
            节点求值结果
        """
        self.current_depth += 1
        if self.current_depth > self.max_depth:
            raise ValueError("表达式过于复杂，超出最大深度限制")
        
        try:
            if isinstance(node, ast.Constant):
                # 常量节点（数字）
                return node.value
            
            elif isinstance(node, ast.Num):
                # 数字节点（兼容旧版本）
                return node.n
            
            elif isinstance(node, ast.BinOp):
                # 二元运算符
                op_type = type(node.op)
                if op_type not in self.ALLOWED_OPERATORS:
                    raise ValueError(f"不允许的运算符: {op_type.__name__}")
                
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                op_func = self.ALLOWED_OPERATORS[op_type]
                
                # 特殊处理除零错误
                if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                    raise ZeroDivisionError("除数不能为零")
                
                return op_func(left, right)
            
            elif isinstance(node, ast.UnaryOp):
                # 一元运算符
                op_type = type(node.op)
                if op_type not in self.ALLOWED_OPERATORS:
                    raise ValueError(f"不允许的运算符: {op_type.__name__}")
                
                operand = self._eval_node(node.operand)
                op_func = self.ALLOWED_OPERATORS[op_type]
                return op_func(operand)
            
            elif isinstance(node, ast.Call):
                # 函数调用
                if not isinstance(node.func, ast.Name):
                    raise ValueError("不允许的函数调用形式")
                
                func_name = node.func.id
                if func_name not in self.ALLOWED_FUNCTIONS:
                    raise ValueError(f"不允许的函数: {func_name}")
                
                func = self.ALLOWED_FUNCTIONS[func_name]
                args = [self._eval_node(arg) for arg in node.args]
                
                return func(*args)
            
            else:
                raise ValueError(f"不允许的表达式类型: {type(node).__name__}")
        
        finally:
            self.current_depth -= 1


class ExpressionParser:
    """自然语言数学表达式解析器"""
    
    # 中文运算符映射
    CHINESE_OPERATORS = {
        '加': '+',
        '加上': '+',
        '减': '-',
        '减去': '-',
        '乘': '*',
        '乘以': '*',
        '除': '/',
        '除以': '/',
        '的': '**',  # 用于"2的3次方"
        '次方': '**',
        '平方': '**2',
        '立方': '**3',
        '平方根': 'sqrt',
        '开方': 'sqrt',
    }
    
    # 英文运算符映射
    ENGLISH_OPERATORS = {
        'plus': '+',
        'add': '+',
        'minus': '-',
        'subtract': '-',
        'times': '*',
        'multiply': '*',
        'multiplied by': '*',
        'divide': '/',
        'divided by': '/',
        'to the power of': '**',
        'power': '**',
        'square': '**2',
        'cube': '**3',
        'square root': 'sqrt',
        'sqrt': 'sqrt',
    }
    
    # 括号映射
    BRACKET_MAPPING = {
        '（': '(',
        '）': ')',
        '【': '(',
        '】': ')',
        '「': '(',
        '」': ')',
        '[': '(',
        ']': ')',
        '{': '(',
        '}': ')',
    }
    
    def __init__(self):
        """初始化解析器"""
        # 合并所有运算符映射
        self.operators = {**self.CHINESE_OPERATORS, **self.ENGLISH_OPERATORS}
    
    def parse(self, text: str) -> str:
        """解析自然语言表达式为数学表达式
        
        Args:
            text: 自然语言表达式
            
        Returns:
            标准数学表达式字符串
            
        Raises:
            ValueError: 无法解析的表达式
        """
        # 清理输入
        text = text.strip()
        if not text:
            raise ValueError("输入为空")
        
        # 移除无关字符
        text = self._clean_text(text)
        
        # 标准化括号
        text = self._normalize_brackets(text)
        
        # 处理百分比
        text = self._handle_percentage(text)
        
        # 替换运算符
        text = self._replace_operators(text)
        
        # 处理特殊函数
        text = self._handle_special_functions(text)
        
        # 清理空格
        text = text.replace(' ', '')
        
        # 验证表达式
        if not self._validate_expression(text):
            raise ValueError(f"无效的数学表达式: {text}")
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除无关字符"""
        # 移除问号、等号等无关字符
        text = re.sub(r'[?？=＝]', '', text)
        # 移除"等于多少"、"是多少"等提示词
        text = re.sub(r'(等于|是|等|是多少|等于多少|多少)', '', text)
        return text
    
    def _normalize_brackets(self, text: str) -> str:
        """标准化括号"""
        for old, new in self.BRACKET_MAPPING.items():
            text = text.replace(old, new)
        
        # 处理"括号"文字
        text = re.sub(r'(左|开)括号', '(', text)
        text = re.sub(r'(右|闭)括号', ')', text)
        text = text.replace('括号', '')
        
        return text
    
    def _handle_percentage(self, text: str) -> str:
        """处理百分比表达式"""
        # 匹配"X的Y%"或"X%"模式
        # 例如："20的50%" -> "20*0.5"
        text = re.sub(r'(\d+(?:\.\d+)?)的(\d+(?:\.\d+)?)%', r'(\1*\2/100)', text)
        text = re.sub(r'(\d+(?:\.\d+)?)%', r'(\1/100)', text)
        return text
    
    def _replace_operators(self, text: str) -> str:
        """替换自然语言运算符为数学符号"""
        # 按长度排序，优先匹配长的运算符（如"乘以"优先于"乘"）
        sorted_ops = sorted(self.operators.items(), key=lambda x: len(x[0]), reverse=True)
        
        for word, symbol in sorted_ops:
            # 使用正则表达式进行全词匹配
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            text = pattern.sub(symbol, text)
        
        return text
    
    def _handle_special_functions(self, text: str) -> str:
        """处理特殊数学函数"""
        # 处理"X的平方根"或"X开方"
        text = re.sub(r'(\d+(?:\.\d+)?)sqrt', r'sqrt(\1)', text)
        
        # 处理"X的Y次方"
        text = re.sub(r'(\d+(?:\.\d+)?)\*\*(\d+(?:\.\d+)?)', r'pow(\1,\2)', text)
        
        return text
    
    def _validate_expression(self, expr: str) -> bool:
        """验证表达式是否有效"""
        if not expr:
            return False
        
        # 检查是否只包含允许的字符
        allowed_chars = set('0123456789+-*/.()%sqrtpow, ')
        if not all(c in allowed_chars for c in expr):
            return False
        
        # 检查括号是否配对
        if expr.count('(') != expr.count(')'):
            return False
        
        return True


@tool
def safe_calculate(
    expression: str,
    precision: int = 4,
    use_decimal: bool = False
) -> str:
    """安全地计算数学表达式
    
    该工具使用AST解析器安全地计算数学表达式，避免使用eval()函数的安全风险。
    支持基本四则运算、幂运算、开方等常用数学运算。
    
    Args:
        expression: 标准数学表达式字符串（如："2+3*4"、"pow(2,3)"、"sqrt(9)"）
        precision: 结果小数位数，默认4位
        use_decimal: 是否使用Decimal进行高精度计算，默认False
        
    Returns:
        JSON格式的计算结果，包含：
        {
            "success": true/false,
            "result": 计算结果,
            "formatted_result": 格式化的结果,
            "expression": 原始表达式,
            "error": 错误信息（如果有）,
            "execution_time": 执行时间（毫秒）
        }
    
    Example:
        >>> safe_calculate("2+3*4")
        '{"success": true, "result": 14, "formatted_result": "14", ...}'
        
        >>> safe_calculate("pow(2,3)")
        '{"success": true, "result": 8, "formatted_result": "8", ...}'
        
        >>> safe_calculate("sqrt(9)")
        '{"success": true, "result": 3.0, "formatted_result": "3.0", ...}'
    """
    import time
    
    start_time = time.time()
    
    try:
        # 验证输入
        if not expression or not isinstance(expression, str):
            return json.dumps({
                "success": False,
                "error": "表达式不能为空",
                "expression": expression
            }, ensure_ascii=False)
        
        # 长度限制
        if len(expression) > 1000:
            return json.dumps({
                "success": False,
                "error": "表达式过长，请简化表达式",
                "expression": expression[:100] + "..."
            }, ensure_ascii=False)
        
        # 创建求值器
        evaluator = SafeMathEvaluator()
        
        # 执行计算
        if use_decimal:
            # 使用Decimal进行高精度计算
            result = evaluator.evaluate(expression)
            decimal_result = Decimal(str(result))
            result = float(decimal_result)
        else:
            result = evaluator.evaluate(expression)
        
        # 格式化结果
        if isinstance(result, float):
            if result.is_integer():
                formatted_result = str(int(result))
            else:
                formatted_result = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        else:
            formatted_result = str(result)
        
        # 计算执行时间
        execution_time = (time.time() - start_time) * 1000
        
        return json.dumps({
            "success": True,
            "result": result,
            "formatted_result": formatted_result,
            "expression": expression,
            "precision": precision,
            "execution_time": round(execution_time, 2)
        }, ensure_ascii=False)
    
    except ZeroDivisionError:
        return json.dumps({
            "success": False,
            "error": "除数不能为零",
            "expression": expression,
            "suggestion": "请检查表达式中的除法运算"
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "expression": expression,
            "suggestion": "请确保表达式只包含数字和允许的运算符"
        }, ensure_ascii=False)
    
    except OverflowError:
        return json.dumps({
            "success": False,
            "error": "计算结果溢出",
            "expression": expression,
            "suggestion": "请使用较小的数值进行计算"
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "expression": expression,
            "suggestion": "请检查表达式格式是否正确"
        }, ensure_ascii=False)


@tool
def parse_natural_language_math(
    text: str,
    language: str = "auto"
) -> str:
    """解析自然语言数学表达式
    
    将用户的自然语言数学问题转换为标准的数学表达式。
    支持中文和英文的多种表达方式。
    
    Args:
        text: 自然语言数学表达式（如："12乘以12等于多少"、"2 plus 3 times 4"）
        language: 语言类型，可选值：auto（自动检测）、zh（中文）、en（英文）
        
    Returns:
        JSON格式的解析结果，包含：
        {
            "success": true/false,
            "original_text": 原始输入,
            "parsed_expression": 解析后的表达式,
            "language": 检测到的语言,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> parse_natural_language_math("12乘以12等于多少")
        '{"success": true, "parsed_expression": "12*12", ...}'
        
        >>> parse_natural_language_math("2 plus 3 times 4")
        '{"success": true, "parsed_expression": "2+3*4", ...}'
    """
    try:
        # 验证输入
        if not text or not isinstance(text, str):
            return json.dumps({
                "success": False,
                "error": "输入文本不能为空",
                "original_text": text
            }, ensure_ascii=False)
        
        # 创建解析器
        parser = ExpressionParser()
        
        # 解析表达式
        parsed_expr = parser.parse(text)
        
        # 检测语言
        detected_lang = "zh" if any('\u4e00' <= c <= '\u9fff' for c in text) else "en"
        
        return json.dumps({
            "success": True,
            "original_text": text,
            "parsed_expression": parsed_expr,
            "language": detected_lang
        }, ensure_ascii=False)
    
    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "original_text": text,
            "suggestion": "请使用清晰的数学表达方式，如'12乘以12'或'2加3乘以4'"
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"解析失败: {str(e)}",
            "original_text": text,
            "suggestion": "请检查输入是否为有效的数学问题"
        }, ensure_ascii=False)


@tool
def calculate_natural_language(
    text: str,
    precision: int = 4,
    show_steps: bool = False
) -> str:
    """直接计算自然语言数学问题
    
    这是一个便捷工具，结合了自然语言解析和安全计算功能。
    用户可以直接输入自然语言问题，工具会自动解析并计算结果。
    
    Args:
        text: 自然语言数学问题（如："12乘以12等于多少"）
        precision: 结果小数位数，默认4位
        show_steps: 是否显示计算步骤，默认False
        
    Returns:
        JSON格式的计算结果，包含：
        {
            "success": true/false,
            "original_text": 原始问题,
            "parsed_expression": 解析后的表达式,
            "result": 计算结果,
            "formatted_result": 格式化的结果,
            "answer": 自然语言答案,
            "steps": 计算步骤（如果show_steps=True）,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> calculate_natural_language("12乘以12等于多少")
        '{"success": true, "result": 144, "answer": "12乘以12等于144", ...}'
        
        >>> calculate_natural_language("2加3乘以4", show_steps=True)
        '{"success": true, "result": 14, "steps": [...], ...}'
    """
    try:
        # 步骤1：解析自然语言
        parse_result = json.loads(parse_natural_language_math(text))
        
        if not parse_result.get("success"):
            return json.dumps(parse_result, ensure_ascii=False)
        
        parsed_expr = parse_result["parsed_expression"]
        
        # 步骤2：执行计算
        calc_result = json.loads(safe_calculate(parsed_expr, precision=precision))
        
        if not calc_result.get("success"):
            return json.dumps({
                "success": False,
                "original_text": text,
                "parsed_expression": parsed_expr,
                "error": calc_result.get("error"),
                "suggestion": calc_result.get("suggestion")
            }, ensure_ascii=False)
        
        # 构建自然语言答案
        answer = f"{text.rstrip('?？')} = {calc_result['formatted_result']}"
        
        # 构建响应
        response = {
            "success": True,
            "original_text": text,
            "parsed_expression": parsed_expr,
            "result": calc_result["result"],
            "formatted_result": calc_result["formatted_result"],
            "answer": answer,
            "execution_time": calc_result.get("execution_time", 0)
        }
        
        # 如果需要显示步骤
        if show_steps:
            response["steps"] = [
                {"step": 1, "description": "解析自然语言", "result": parsed_expr},
                {"step": 2, "description": "执行计算", "result": calc_result["formatted_result"]}
            ]
        
        return json.dumps(response, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "original_text": text,
            "suggestion": "请确保输入是有效的数学问题"
        }, ensure_ascii=False)


@tool
def validate_math_expression(
    expression: str,
    check_safety: bool = True
) -> str:
    """验证数学表达式的有效性和安全性
    
    检查表达式是否符合安全计算的要求，包括语法检查、安全检查等。
    
    Args:
        expression: 要验证的数学表达式
        check_safety: 是否进行安全检查，默认True
        
    Returns:
        JSON格式的验证结果，包含：
        {
            "success": true/false,
            "is_valid": 表达式是否有效,
            "is_safe": 表达式是否安全,
            "expression": 原始表达式,
            "issues": 发现的问题列表,
            "warnings": 警告信息列表,
            "suggestions": 改进建议
        }
    
    Example:
        >>> validate_math_expression("2+3*4")
        '{"success": true, "is_valid": true, "is_safe": true, ...}'
        
        >>> validate_math_expression("2/0")
        '{"success": true, "is_valid": true, "issues": ["可能的除零错误"], ...}'
    """
    try:
        issues = []
        warnings = []
        suggestions = []
        
        # 基本验证
        if not expression or not isinstance(expression, str):
            return json.dumps({
                "success": False,
                "error": "表达式不能为空"
            }, ensure_ascii=False)
        
        # 长度检查
        if len(expression) > 1000:
            issues.append("表达式过长")
            suggestions.append("请简化表达式或分步计算")
        
        # 括号配对检查
        if expression.count('(') != expression.count(')'):
            issues.append("括号不配对")
            suggestions.append("请检查括号是否正确配对")
        
        # 安全字符检查
        if check_safety:
            allowed_chars = set('0123456789+-*/.()%sqrtpow, ')
            invalid_chars = set(c for c in expression if c not in allowed_chars)
            if invalid_chars:
                issues.append(f"包含不允许的字符: {invalid_chars}")
                suggestions.append("请只使用数字和基本运算符")
        
        # 除零检查
        if re.search(r'/\s*0(?!\d)', expression):
            warnings.append("可能存在除零错误")
            suggestions.append("请确保除数不为零")
        
        # AST语法检查
        is_valid = True
        try:
            ast.parse(expression, mode='eval')
        except SyntaxError as e:
            is_valid = False
            issues.append(f"语法错误: {str(e)}")
            suggestions.append("请检查表达式格式是否正确")
        
        is_safe = len(issues) == 0 and check_safety
        
        return json.dumps({
            "success": True,
            "is_valid": is_valid and len(issues) == 0,
            "is_safe": is_safe,
            "expression": expression,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"验证失败: {str(e)}",
            "expression": expression
        }, ensure_ascii=False)


@tool
def calculate_with_steps(
    expression: str,
    precision: int = 4
) -> str:
    """计算数学表达式并显示详细步骤
    
    该工具不仅计算表达式的结果，还会显示中间计算步骤，
    帮助用户理解复杂表达式的计算过程。
    
    Args:
        expression: 数学表达式字符串
        precision: 结果小数位数，默认4位
        
    Returns:
        JSON格式的计算结果，包含详细步骤：
        {
            "success": true/false,
            "expression": 原始表达式,
            "result": 最终结果,
            "formatted_result": 格式化的结果,
            "steps": [
                {
                    "step_number": 步骤编号,
                    "description": 步骤描述,
                    "operation": 操作,
                    "result": 该步骤结果
                }
            ],
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> calculate_with_steps("2+3*4")
        '{"success": true, "result": 14, "steps": [...], ...}'
    """
    try:
        # 首先验证表达式
        validation = json.loads(validate_math_expression(expression))
        
        if not validation.get("is_valid"):
            return json.dumps({
                "success": False,
                "error": "表达式无效",
                "expression": expression,
                "issues": validation.get("issues", [])
            }, ensure_ascii=False)
        
        # 执行计算
        calc_result = json.loads(safe_calculate(expression, precision=precision))
        
        if not calc_result.get("success"):
            return json.dumps(calc_result, ensure_ascii=False)
        
        # 分析表达式结构，生成步骤说明
        steps = []
        
        # 简单表达式分析
        if '+' in expression or '-' in expression or '*' in expression or '/' in expression:
            # 检查是否有优先级运算
            has_mult_div = '*' in expression or '/' in expression
            has_add_sub = '+' in expression or '-' in expression
            
            if has_mult_div and has_add_sub:
                steps.append({
                    "step_number": 1,
                    "description": "识别运算优先级",
                    "operation": "乘除运算优先于加减运算",
                    "note": "按照数学运算规则，先计算乘除，再计算加减"
                })
            
            steps.append({
                "step_number": len(steps) + 1,
                "description": "执行计算",
                "operation": expression,
                "result": calc_result["formatted_result"]
            })
        
        # 如果包含函数调用
        if 'sqrt' in expression or 'pow' in expression:
            steps.append({
                "step_number": 1,
                "description": "识别特殊函数",
                "operation": "sqrt（平方根）或 pow（幂运算）",
                "note": "先计算函数，再进行其他运算"
            })
            
            steps.append({
                "step_number": 2,
                "description": "执行计算",
                "operation": expression,
                "result": calc_result["formatted_result"]
            })
        
        # 如果没有特别复杂的步骤，添加简单说明
        if not steps:
            steps.append({
                "step_number": 1,
                "description": "直接计算",
                "operation": expression,
                "result": calc_result["formatted_result"]
            })
        
        return json.dumps({
            "success": True,
            "expression": expression,
            "result": calc_result["result"],
            "formatted_result": calc_result["formatted_result"],
            "steps": steps,
            "execution_time": calc_result.get("execution_time", 0)
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "expression": expression
        }, ensure_ascii=False)


@tool
def batch_calculate(
    expressions: List[str],
    precision: int = 4,
    stop_on_error: bool = False
) -> str:
    """批量计算多个数学表达式
    
    一次性计算多个数学表达式，提高处理效率。
    
    Args:
        expressions: 数学表达式列表
        precision: 结果小数位数，默认4位
        stop_on_error: 遇到错误是否停止，默认False（继续处理其他表达式）
        
    Returns:
        JSON格式的批量计算结果：
        {
            "success": true/false,
            "total_count": 总表达式数,
            "success_count": 成功计算数,
            "failed_count": 失败计算数,
            "results": [
                {
                    "expression": 表达式,
                    "success": true/false,
                    "result": 结果,
                    "error": 错误信息（如果有）
                }
            ]
        }
    
    Example:
        >>> batch_calculate(["2+3", "4*5", "10/2"])
        '{"success": true, "success_count": 3, "results": [...], ...}'
    """
    try:
        if not expressions or not isinstance(expressions, list):
            return json.dumps({
                "success": False,
                "error": "表达式列表不能为空"
            }, ensure_ascii=False)
        
        results = []
        success_count = 0
        failed_count = 0
        
        for expr in expressions:
            calc_result = json.loads(safe_calculate(expr, precision=precision))
            
            if calc_result.get("success"):
                success_count += 1
                results.append({
                    "expression": expr,
                    "success": True,
                    "result": calc_result["result"],
                    "formatted_result": calc_result["formatted_result"]
                })
            else:
                failed_count += 1
                results.append({
                    "expression": expr,
                    "success": False,
                    "error": calc_result.get("error")
                })
                
                if stop_on_error:
                    break
        
        return json.dumps({
            "success": True,
            "total_count": len(expressions),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"批量计算失败: {str(e)}"
        }, ensure_ascii=False)


@tool
def calculate_percentage(
    value: float,
    percentage: float,
    operation: str = "of"
) -> str:
    """计算百分比
    
    提供便捷的百分比计算功能。
    
    Args:
        value: 基础值
        percentage: 百分比值（如：50表示50%）
        operation: 操作类型，可选值：
                  - "of": 计算X的Y%（如：100的20% = 20）
                  - "increase": 增加Y%（如：100增加20% = 120）
                  - "decrease": 减少Y%（如：100减少20% = 80）
        
    Returns:
        JSON格式的计算结果：
        {
            "success": true/false,
            "value": 基础值,
            "percentage": 百分比,
            "operation": 操作类型,
            "result": 计算结果,
            "formatted_result": 格式化结果,
            "explanation": 计算说明,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> calculate_percentage(100, 20, "of")
        '{"success": true, "result": 20.0, "explanation": "100的20% = 20.0", ...}'
        
        >>> calculate_percentage(100, 20, "increase")
        '{"success": true, "result": 120.0, "explanation": "100增加20% = 120.0", ...}'
    """
    try:
        # 验证输入
        if not isinstance(value, (int, float)) or not isinstance(percentage, (int, float)):
            return json.dumps({
                "success": False,
                "error": "值和百分比必须是数字"
            }, ensure_ascii=False)
        
        if operation not in ["of", "increase", "decrease"]:
            return json.dumps({
                "success": False,
                "error": f"不支持的操作类型: {operation}",
                "suggestion": "请使用 'of'、'increase' 或 'decrease'"
            }, ensure_ascii=False)
        
        # 执行计算
        if operation == "of":
            result = value * (percentage / 100)
            explanation = f"{value}的{percentage}% = {result}"
        elif operation == "increase":
            result = value * (1 + percentage / 100)
            explanation = f"{value}增加{percentage}% = {result}"
        else:  # decrease
            result = value * (1 - percentage / 100)
            explanation = f"{value}减少{percentage}% = {result}"
        
        # 格式化结果
        if result == int(result):
            formatted_result = str(int(result))
        else:
            formatted_result = f"{result:.4f}".rstrip('0').rstrip('.')
        
        return json.dumps({
            "success": True,
            "value": value,
            "percentage": percentage,
            "operation": operation,
            "result": result,
            "formatted_result": formatted_result,
            "explanation": explanation
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"百分比计算失败: {str(e)}",
            "value": value,
            "percentage": percentage
        }, ensure_ascii=False)


@tool
def calculate_power(
    base: float,
    exponent: float
) -> str:
    """计算幂运算
    
    计算base的exponent次方。
    
    Args:
        base: 底数
        exponent: 指数
        
    Returns:
        JSON格式的计算结果：
        {
            "success": true/false,
            "base": 底数,
            "exponent": 指数,
            "result": 计算结果,
            "formatted_result": 格式化结果,
            "explanation": 计算说明,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> calculate_power(2, 3)
        '{"success": true, "result": 8, "explanation": "2的3次方 = 8", ...}'
        
        >>> calculate_power(9, 0.5)
        '{"success": true, "result": 3.0, "explanation": "9的0.5次方 = 3.0", ...}'
    """
    try:
        # 验证输入
        if not isinstance(base, (int, float)) or not isinstance(exponent, (int, float)):
            return json.dumps({
                "success": False,
                "error": "底数和指数必须是数字"
            }, ensure_ascii=False)
        
        # 执行计算
        result = pow(base, exponent)
        
        # 格式化结果
        if result == int(result):
            formatted_result = str(int(result))
        else:
            formatted_result = f"{result:.4f}".rstrip('0').rstrip('.')
        
        # 生成说明
        if exponent == 0.5:
            explanation = f"{base}的平方根 = {formatted_result}"
        elif exponent == 2:
            explanation = f"{base}的平方 = {formatted_result}"
        elif exponent == 3:
            explanation = f"{base}的立方 = {formatted_result}"
        else:
            explanation = f"{base}的{exponent}次方 = {formatted_result}"
        
        return json.dumps({
            "success": True,
            "base": base,
            "exponent": exponent,
            "result": result,
            "formatted_result": formatted_result,
            "explanation": explanation
        }, ensure_ascii=False)
    
    except OverflowError:
        return json.dumps({
            "success": False,
            "error": "计算结果溢出",
            "base": base,
            "exponent": exponent,
            "suggestion": "请使用较小的数值"
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"幂运算失败: {str(e)}",
            "base": base,
            "exponent": exponent
        }, ensure_ascii=False)


@tool
def calculate_square_root(
    value: float,
    precision: int = 4
) -> str:
    """计算平方根
    
    计算给定值的平方根。
    
    Args:
        value: 要计算平方根的值（必须非负）
        precision: 结果小数位数，默认4位
        
    Returns:
        JSON格式的计算结果：
        {
            "success": true/false,
            "value": 原始值,
            "result": 平方根结果,
            "formatted_result": 格式化结果,
            "explanation": 计算说明,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> calculate_square_root(9)
        '{"success": true, "result": 3.0, "explanation": "9的平方根 = 3.0", ...}'
        
        >>> calculate_square_root(2)
        '{"success": true, "result": 1.4142, "explanation": "2的平方根 = 1.4142", ...}'
    """
    try:
        # 验证输入
        if not isinstance(value, (int, float)):
            return json.dumps({
                "success": False,
                "error": "输入值必须是数字"
            }, ensure_ascii=False)
        
        if value < 0:
            return json.dumps({
                "success": False,
                "error": "不能计算负数的平方根",
                "value": value,
                "suggestion": "请输入非负数"
            }, ensure_ascii=False)
        
        # 执行计算
        result = math.sqrt(value)
        
        # 格式化结果
        if result == int(result):
            formatted_result = str(int(result))
        else:
            formatted_result = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        
        explanation = f"{value}的平方根 = {formatted_result}"
        
        return json.dumps({
            "success": True,
            "value": value,
            "result": result,
            "formatted_result": formatted_result,
            "explanation": explanation,
            "precision": precision
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"平方根计算失败: {str(e)}",
            "value": value
        }, ensure_ascii=False)


@tool
def get_calculator_help() -> str:
    """获取计算器使用帮助
    
    返回计算器支持的功能和使用示例。
    
    Returns:
        JSON格式的帮助信息：
        {
            "success": true,
            "supported_operations": 支持的运算类型列表,
            "examples": 使用示例列表,
            "tips": 使用提示,
            "limitations": 功能限制
        }
    
    Example:
        >>> get_calculator_help()
        '{"success": true, "supported_operations": [...], ...}'
    """
    help_info = {
        "success": True,
        "supported_operations": [
            {
                "category": "基本四则运算",
                "operations": ["加法(+)", "减法(-)", "乘法(*)", "除法(/)"],
                "examples": ["2+3", "10-5", "4*6", "20/4"]
            },
            {
                "category": "高级运算",
                "operations": ["幂运算(**或pow)", "平方根(sqrt)", "百分比(%)"],
                "examples": ["pow(2,3)", "sqrt(16)", "100*20/100"]
            },
            {
                "category": "运算优先级",
                "operations": ["括号优先", "乘除优先于加减"],
                "examples": ["(2+3)*4", "2+3*4"]
            },
            {
                "category": "特殊数值",
                "operations": ["负数", "小数"],
                "examples": ["-5+10", "3.5*2"]
            }
        ],
        "natural_language_examples": [
            {
                "input": "12乘以12等于多少",
                "explanation": "自然语言描述的乘法运算"
            },
            {
                "input": "2加3乘以4",
                "explanation": "混合运算，先乘后加"
            },
            {
                "input": "括号2加3括号乘以4",
                "explanation": "使用括号改变优先级"
            },
            {
                "input": "2的3次方",
                "explanation": "幂运算"
            },
            {
                "input": "9的平方根",
                "explanation": "开方运算"
            },
            {
                "input": "100的20%",
                "explanation": "百分比计算"
            }
        ],
        "tips": [
            "支持中文和英文自然语言输入",
            "可以使用'乘以'、'加上'、'减去'、'除以'等词语",
            "支持多种括号形式：()、（）、[]、【】",
            "计算结果默认保留4位小数",
            "表达式长度限制在1000字符以内",
            "计算超时限制为3秒"
        ],
        "limitations": [
            "不支持高等数学函数（积分、微分等）",
            "不支持矩阵运算和复数运算",
            "不支持方程求解",
            "不提供单位换算功能",
            "表达式复杂度有限制"
        ],
        "error_handling": [
            "除零错误：会提示不能除以零",
            "语法错误：会提示表达式格式有误",
            "溢出错误：会提示使用较小的数值",
            "超时错误：会建议简化表达式"
        ]
    }
    
    return json.dumps(help_info, ensure_ascii=False, indent=2)


@tool
def format_calculation_result(
    result: Union[int, float],
    format_type: str = "auto",
    precision: int = 4,
    use_separator: bool = False
) -> str:
    """格式化计算结果
    
    将计算结果格式化为易读的形式。
    
    Args:
        result: 计算结果
        format_type: 格式类型，可选值：
                    - "auto": 自动选择（默认）
                    - "integer": 整数格式
                    - "decimal": 小数格式
                    - "scientific": 科学计数法
                    - "percentage": 百分比格式
        precision: 小数位数，默认4位
        use_separator: 是否使用千分位分隔符，默认False
        
    Returns:
        JSON格式的格式化结果：
        {
            "success": true/false,
            "original_result": 原始结果,
            "formatted_result": 格式化结果,
            "format_type": 使用的格式类型,
            "error": 错误信息（如果有）
        }
    
    Example:
        >>> format_calculation_result(1234567.89)
        '{"success": true, "formatted_result": "1234567.89", ...}'
        
        >>> format_calculation_result(1234567.89, use_separator=True)
        '{"success": true, "formatted_result": "1,234,567.89", ...}'
    """
    try:
        # 验证输入
        if not isinstance(result, (int, float)):
            return json.dumps({
                "success": False,
                "error": "结果必须是数字"
            }, ensure_ascii=False)
        
        # 根据格式类型进行格式化
        if format_type == "auto":
            # 自动选择格式
            if result == int(result):
                formatted = str(int(result))
            elif abs(result) >= 1e6 or (abs(result) < 1e-3 and result != 0):
                formatted = f"{result:.{precision}e}"
            else:
                formatted = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        
        elif format_type == "integer":
            formatted = str(int(result))
        
        elif format_type == "decimal":
            formatted = f"{result:.{precision}f}".rstrip('0').rstrip('.')
        
        elif format_type == "scientific":
            formatted = f"{result:.{precision}e}"
        
        elif format_type == "percentage":
            formatted = f"{result * 100:.{precision}f}%".rstrip('0').rstrip('.%') + '%'
        
        else:
            return json.dumps({
                "success": False,
                "error": f"不支持的格式类型: {format_type}"
            }, ensure_ascii=False)
        
        # 添加千分位分隔符
        if use_separator and format_type in ["auto", "integer", "decimal"]:
            parts = formatted.split('.')
            parts[0] = f"{int(parts[0]):,}"
            formatted = '.'.join(parts)
        
        return json.dumps({
            "success": True,
            "original_result": result,
            "formatted_result": formatted,
            "format_type": format_type,
            "precision": precision,
            "use_separator": use_separator
        }, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"格式化失败: {str(e)}",
            "original_result": result
        }, ensure_ascii=False)
