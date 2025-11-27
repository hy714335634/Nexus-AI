"""
自然语言数学表达式解析和计算工具

本模块提供自然语言数学表达式的解析和计算功能，支持中文数字和多种运算符表达方式。
"""

from strands import tool
from typing import Dict, Any, Optional, List, Tuple
import re
import json


# ==================== 中文数字转换 ====================

# 中文数字映射表
CHINESE_NUM_MAP = {
    '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000,
    '亿': 100000000,
    '〇': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4,
    '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
    '拾': 10, '佰': 100, '仟': 1000, '萬': 10000
}

# 运算符映射表
OPERATOR_MAP = {
    # 加法
    '加': '+', '加上': '+', '和': '+', '与': '+', '再加': '+',
    '加以': '+', '相加': '+', 'plus': '+', '+': '+', '＋': '+',
    
    # 减法
    '减': '-', '减去': '-', '减掉': '-', '去掉': '-', '去': '-',
    '少': '-', '扣除': '-', '扣掉': '-', 'minus': '-', '-': '-', '－': '-',
    
    # 乘法
    '乘': '*', '乘以': '*', '乘上': '*', '乘于': '*', '相乘': '*',
    '乘与': '*', 'multiply': '*', 'times': '*', '*': '*', '×': '*', 'x': '*',
    
    # 除法
    '除': '/', '除以': '/', '除于': '/', '除去': '/', '被': '/',
    '相除': '/', 'divide': '/', 'divided': '/', '/': '/', '÷': '/'
}

# 数字词模式
NUMBER_WORDS = [
    '零', '一', '二', '三', '四', '五', '六', '七', '八', '九',
    '十', '百', '千', '万', '亿', '〇',
    '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾', '佰', '仟', '萬'
]


def chinese_to_number(chinese_str: str) -> Optional[float]:
    """
    将中文数字字符串转换为阿拉伯数字
    
    Args:
        chinese_str: 中文数字字符串，如"一百零八"、"二十三"
        
    Returns:
        转换后的数字，如果无法转换则返回None
    """
    if not chinese_str:
        return None
    
    chinese_str = chinese_str.strip()
    
    # 如果已经是阿拉伯数字，直接返回
    try:
        return float(chinese_str)
    except ValueError:
        pass
    
    # 特殊处理：单个数字
    if len(chinese_str) == 1 and chinese_str in CHINESE_NUM_MAP:
        return float(CHINESE_NUM_MAP[chinese_str])
    
    # 解析复杂中文数字
    result = 0
    section = 0
    unit = 1
    
    i = 0
    while i < len(chinese_str):
        char = chinese_str[i]
        
        if char not in CHINESE_NUM_MAP:
            i += 1
            continue
        
        num = CHINESE_NUM_MAP[char]
        
        # 处理单位
        if num >= 10:
            if num == 10:
                # 处理"十"开头的情况
                if section == 0:
                    section = 1
                section *= num
            elif num >= 100:
                if section == 0:
                    section = 1
                section *= num
            
            # 处理万、亿等大单位
            if num >= 10000:
                result += section
                result *= num
                section = 0
        else:
            section += num * unit
        
        i += 1
    
    result += section
    return float(result)


def extract_numbers_from_text(text: str) -> List[Tuple[str, float]]:
    """
    从文本中提取所有数字（阿拉伯数字和中文数字）
    
    Args:
        text: 输入文本
        
    Returns:
        提取的数字列表，每个元素为(原始文本, 数值)元组
    """
    numbers = []
    
    # 提取阿拉伯数字（包括小数）
    arabic_pattern = r'\d+\.?\d*'
    for match in re.finditer(arabic_pattern, text):
        num_str = match.group()
        try:
            num_val = float(num_str)
            numbers.append((num_str, num_val))
        except ValueError:
            continue
    
    # 提取中文数字
    chinese_pattern = '[' + ''.join(NUMBER_WORDS) + ']+'
    for match in re.finditer(chinese_pattern, text):
        num_str = match.group()
        num_val = chinese_to_number(num_str)
        if num_val is not None:
            numbers.append((num_str, num_val))
    
    return numbers


def identify_operator(text: str) -> Optional[str]:
    """
    从文本中识别运算符
    
    Args:
        text: 输入文本
        
    Returns:
        标准化的运算符(+, -, *, /)，如果未找到则返回None
    """
    # 按长度排序，优先匹配较长的运算符表达
    sorted_ops = sorted(OPERATOR_MAP.keys(), key=len, reverse=True)
    
    for op in sorted_ops:
        if op in text:
            return OPERATOR_MAP[op]
    
    return None


def parse_math_expression(text: str) -> Dict[str, Any]:
    """
    解析自然语言数学表达式
    
    Args:
        text: 自然语言数学表达式
        
    Returns:
        解析结果字典，包含operand1, operator, operand2和错误信息
    """
    result = {
        "success": False,
        "operand1": None,
        "operator": None,
        "operand2": None,
        "error": None
    }
    
    # 识别运算符
    operator = identify_operator(text)
    if not operator:
        result["error"] = "无法识别运算符，请明确指定运算（加、减、乘、除）"
        return result
    
    result["operator"] = operator
    
    # 提取数字
    numbers = extract_numbers_from_text(text)
    
    if len(numbers) < 2:
        result["error"] = "表达式不完整，需要两个数字"
        return result
    
    # 取前两个数字作为操作数
    result["operand1"] = numbers[0][1]
    result["operand2"] = numbers[1][1]
    result["success"] = True
    
    return result


def calculate(operand1: float, operator: str, operand2: float) -> Dict[str, Any]:
    """
    执行数学计算
    
    Args:
        operand1: 第一个操作数
        operator: 运算符(+, -, *, /)
        operand2: 第二个操作数
        
    Returns:
        计算结果字典
    """
    result = {
        "success": False,
        "result": None,
        "error": None
    }
    
    try:
        if operator == '+':
            result["result"] = operand1 + operand2
        elif operator == '-':
            result["result"] = operand1 - operand2
        elif operator == '*':
            result["result"] = operand1 * operand2
        elif operator == '/':
            if operand2 == 0:
                result["error"] = "除数不能为0"
                return result
            result["result"] = operand1 / operand2
        else:
            result["error"] = f"不支持的运算符: {operator}"
            return result
        
        result["success"] = True
        
    except Exception as e:
        result["error"] = f"计算错误: {str(e)}"
    
    return result


# ==================== Strands Tool Functions ====================

@tool
def parse_natural_language_math(expression: str) -> str:
    """
    解析自然语言数学表达式，提取操作数和运算符
    
    支持中文数字和多种运算符表达方式，如：
    - "一加一"
    - "10减去5"
    - "三乘以四"
    - "20除以4"
    
    Args:
        expression: 自然语言数学表达式
        
    Returns:
        JSON格式的解析结果，包含operand1、operator、operand2和错误信息
    """
    try:
        if not expression or not expression.strip():
            return json.dumps({
                "success": False,
                "error": "表达式不能为空",
                "operand1": None,
                "operator": None,
                "operand2": None
            }, ensure_ascii=False, indent=2)
        
        parse_result = parse_math_expression(expression)
        
        return json.dumps(parse_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"解析失败: {str(e)}",
            "operand1": None,
            "operator": None,
            "operand2": None
        }, ensure_ascii=False, indent=2)


@tool
def calculate_math_expression(operand1: float, operator: str, operand2: float) -> str:
    """
    执行数学计算
    
    支持基本四则运算：加(+)、减(-)、乘(*)、除(/)
    
    Args:
        operand1: 第一个操作数
        operator: 运算符(+, -, *, /)
        operand2: 第二个操作数
        
    Returns:
        JSON格式的计算结果
    """
    try:
        calc_result = calculate(operand1, operator, operand2)
        
        return json.dumps(calc_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"计算失败: {str(e)}",
            "result": None
        }, ensure_ascii=False, indent=2)


@tool
def natural_language_calculator(expression: str) -> str:
    """
    自然语言计算器 - 一站式解析和计算
    
    接收自然语言数学表达式，自动解析并计算结果。
    支持中文数字和多种运算符表达方式。
    
    示例：
    - "一加一等于几" → 2
    - "10减去5" → 5
    - "三乘以四" → 12
    - "20除以4" → 5
    
    Args:
        expression: 自然语言数学表达式
        
    Returns:
        JSON格式的完整结果，包含解析过程和计算结果
    """
    try:
        if not expression or not expression.strip():
            return json.dumps({
                "success": False,
                "error": "表达式不能为空",
                "expression": expression,
                "parse_result": None,
                "calculation_result": None
            }, ensure_ascii=False, indent=2)
        
        # 解析表达式
        parse_result = parse_math_expression(expression)
        
        if not parse_result["success"]:
            return json.dumps({
                "success": False,
                "error": parse_result["error"],
                "expression": expression,
                "parse_result": parse_result,
                "calculation_result": None
            }, ensure_ascii=False, indent=2)
        
        # 执行计算
        calc_result = calculate(
            parse_result["operand1"],
            parse_result["operator"],
            parse_result["operand2"]
        )
        
        if not calc_result["success"]:
            return json.dumps({
                "success": False,
                "error": calc_result["error"],
                "expression": expression,
                "parse_result": parse_result,
                "calculation_result": calc_result
            }, ensure_ascii=False, indent=2)
        
        # 格式化结果
        result_value = calc_result["result"]
        # 如果结果是整数，显示为整数
        if isinstance(result_value, float) and result_value.is_integer():
            result_value = int(result_value)
        
        return json.dumps({
            "success": True,
            "expression": expression,
            "parse_result": parse_result,
            "calculation_result": calc_result,
            "answer": result_value,
            "formatted_answer": f"{parse_result['operand1']} {parse_result['operator']} {parse_result['operand2']} = {result_value}"
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"处理失败: {str(e)}",
            "expression": expression,
            "parse_result": None,
            "calculation_result": None
        }, ensure_ascii=False, indent=2)


@tool
def validate_math_expression(expression: str) -> str:
    """
    验证自然语言数学表达式的有效性
    
    检查表达式是否包含必要的元素（两个数字和一个运算符），
    并提供详细的验证反馈。
    
    Args:
        expression: 要验证的自然语言数学表达式
        
    Returns:
        JSON格式的验证结果
    """
    try:
        validation_result = {
            "is_valid": False,
            "expression": expression,
            "issues": [],
            "suggestions": []
        }
        
        if not expression or not expression.strip():
            validation_result["issues"].append("表达式为空")
            validation_result["suggestions"].append("请输入数学表达式，例如：'1加1'")
            return json.dumps(validation_result, ensure_ascii=False, indent=2)
        
        # 检查运算符
        operator = identify_operator(expression)
        if not operator:
            validation_result["issues"].append("未找到运算符")
            validation_result["suggestions"].append("请明确指定运算符（加、减、乘、除）")
        
        # 检查数字
        numbers = extract_numbers_from_text(expression)
        if len(numbers) < 2:
            validation_result["issues"].append(f"数字不足，找到{len(numbers)}个，需要2个")
            validation_result["suggestions"].append("请提供两个数字进行运算")
        elif len(numbers) > 2:
            validation_result["issues"].append(f"数字过多，找到{len(numbers)}个，只需要2个")
            validation_result["suggestions"].append("请简化表达式，只包含两个数字")
        
        # 检查除零
        if operator == '/' and len(numbers) >= 2 and numbers[1][1] == 0:
            validation_result["issues"].append("除数为0")
            validation_result["suggestions"].append("除数不能为0，请修改第二个数字")
        
        # 判断是否有效
        if not validation_result["issues"]:
            validation_result["is_valid"] = True
            validation_result["suggestions"].append("表达式有效，可以进行计算")
        
        return json.dumps(validation_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "is_valid": False,
            "expression": expression,
            "issues": [f"验证过程出错: {str(e)}"],
            "suggestions": ["请检查表达式格式"]
        }, ensure_ascii=False, indent=2)


@tool
def convert_chinese_number(chinese_num: str) -> str:
    """
    将中文数字转换为阿拉伯数字
    
    支持简体和繁体中文数字，如：
    - "一" → 1
    - "二十三" → 23
    - "一百零八" → 108
    - "三千五百" → 3500
    
    Args:
        chinese_num: 中文数字字符串
        
    Returns:
        JSON格式的转换结果
    """
    try:
        if not chinese_num or not chinese_num.strip():
            return json.dumps({
                "success": False,
                "error": "输入不能为空",
                "chinese_number": chinese_num,
                "arabic_number": None
            }, ensure_ascii=False, indent=2)
        
        result = chinese_to_number(chinese_num)
        
        if result is None:
            return json.dumps({
                "success": False,
                "error": "无法转换，请检查输入格式",
                "chinese_number": chinese_num,
                "arabic_number": None
            }, ensure_ascii=False, indent=2)
        
        # 如果结果是整数，显示为整数
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        
        return json.dumps({
            "success": True,
            "chinese_number": chinese_num,
            "arabic_number": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"转换失败: {str(e)}",
            "chinese_number": chinese_num,
            "arabic_number": None
        }, ensure_ascii=False, indent=2)


@tool
def get_supported_operators() -> str:
    """
    获取支持的运算符列表
    
    返回所有支持的运算符表达方式，帮助用户了解可用的表达方式。
    
    Returns:
        JSON格式的运算符列表
    """
    try:
        operators_by_type = {
            "加法": [],
            "减法": [],
            "乘法": [],
            "除法": []
        }
        
        for op_text, op_symbol in OPERATOR_MAP.items():
            if op_symbol == '+':
                operators_by_type["加法"].append(op_text)
            elif op_symbol == '-':
                operators_by_type["减法"].append(op_text)
            elif op_symbol == '*':
                operators_by_type["乘法"].append(op_text)
            elif op_symbol == '/':
                operators_by_type["除法"].append(op_text)
        
        return json.dumps({
            "success": True,
            "operators": operators_by_type,
            "total_count": len(OPERATOR_MAP),
            "examples": {
                "加法": "1加1、一加一、1 plus 1",
                "减法": "5减3、五减三、5 minus 3",
                "乘法": "2乘3、二乘三、2 times 3",
                "除法": "10除以2、十除以二、10 divide 2"
            }
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取运算符列表失败: {str(e)}",
            "operators": None
        }, ensure_ascii=False, indent=2)


@tool
def batch_calculate(expressions: List[str]) -> str:
    """
    批量计算多个自然语言数学表达式
    
    同时处理多个表达式，返回所有计算结果。
    
    Args:
        expressions: 自然语言数学表达式列表
        
    Returns:
        JSON格式的批量计算结果
    """
    try:
        if not expressions:
            return json.dumps({
                "success": False,
                "error": "表达式列表为空",
                "results": []
            }, ensure_ascii=False, indent=2)
        
        results = []
        success_count = 0
        
        for i, expr in enumerate(expressions):
            # 解析表达式
            parse_result = parse_math_expression(expr)
            
            if not parse_result["success"]:
                results.append({
                    "index": i,
                    "expression": expr,
                    "success": False,
                    "error": parse_result["error"],
                    "answer": None
                })
                continue
            
            # 执行计算
            calc_result = calculate(
                parse_result["operand1"],
                parse_result["operator"],
                parse_result["operand2"]
            )
            
            if calc_result["success"]:
                success_count += 1
                answer = calc_result["result"]
                if isinstance(answer, float) and answer.is_integer():
                    answer = int(answer)
                
                results.append({
                    "index": i,
                    "expression": expr,
                    "success": True,
                    "answer": answer,
                    "formatted": f"{parse_result['operand1']} {parse_result['operator']} {parse_result['operand2']} = {answer}"
                })
            else:
                results.append({
                    "index": i,
                    "expression": expr,
                    "success": False,
                    "error": calc_result["error"],
                    "answer": None
                })
        
        return json.dumps({
            "success": True,
            "total_expressions": len(expressions),
            "successful_calculations": success_count,
            "failed_calculations": len(expressions) - success_count,
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"批量计算失败: {str(e)}",
            "results": []
        }, ensure_ascii=False, indent=2)


@tool
def get_calculator_help() -> str:
    """
    获取计算器使用帮助信息
    
    返回详细的使用说明、支持的功能和示例。
    
    Returns:
        JSON格式的帮助信息
    """
    try:
        help_info = {
            "success": True,
            "tool_name": "自然语言计算器",
            "version": "1.0.0",
            "description": "支持中文自然语言数学表达式的智能计算器",
            "supported_features": {
                "数字格式": [
                    "阿拉伯数字：1, 2, 3, 10, 100",
                    "中文数字：一、二、三、十、百、千、万",
                    "繁体中文：壹、贰、叁、拾、佰、仟",
                    "混合表达：一百零八、二十三"
                ],
                "运算类型": [
                    "加法：加、加上、和、plus",
                    "减法：减、减去、minus",
                    "乘法：乘、乘以、times",
                    "除法：除、除以、divide"
                ],
                "特殊处理": [
                    "自动识别中文数字",
                    "支持多种运算符表达",
                    "除零错误检测",
                    "结果格式化（整数显示为整数）"
                ]
            },
            "usage_examples": [
                {
                    "input": "一加一等于几",
                    "output": "2",
                    "explanation": "解析中文数字'一'和'一'，识别运算符'加'，计算结果为2"
                },
                {
                    "input": "10减去5",
                    "output": "5",
                    "explanation": "混合使用阿拉伯数字和中文运算符"
                },
                {
                    "input": "三乘以四",
                    "output": "12",
                    "explanation": "全中文表达式"
                },
                {
                    "input": "20除以4",
                    "output": "5",
                    "explanation": "阿拉伯数字加中文运算符"
                }
            ],
            "limitations": [
                "仅支持两个数字的运算",
                "仅支持基本四则运算",
                "不支持括号和运算优先级",
                "不支持连续运算（如1+2+3）",
                "除数不能为0"
            ],
            "error_handling": {
                "表达式为空": "请输入数学表达式",
                "运算符缺失": "请明确指定运算（加、减、乘、除）",
                "数字不足": "请提供两个数字进行运算",
                "除数为0": "除数不能为0，请修改"
            },
            "available_tools": [
                {
                    "name": "natural_language_calculator",
                    "description": "一站式解析和计算（推荐使用）"
                },
                {
                    "name": "parse_natural_language_math",
                    "description": "仅解析表达式，不执行计算"
                },
                {
                    "name": "calculate_math_expression",
                    "description": "执行数学计算（需要提供解析后的参数）"
                },
                {
                    "name": "convert_chinese_number",
                    "description": "中文数字转阿拉伯数字"
                },
                {
                    "name": "validate_math_expression",
                    "description": "验证表达式有效性"
                },
                {
                    "name": "batch_calculate",
                    "description": "批量计算多个表达式"
                },
                {
                    "name": "get_supported_operators",
                    "description": "获取支持的运算符列表"
                }
            ]
        }
        
        return json.dumps(help_info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"获取帮助信息失败: {str(e)}"
        }, ensure_ascii=False, indent=2)
