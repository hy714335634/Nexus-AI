from strands import tool
import pandas as pd
import json
import yaml
import os
from typing import Dict, Any, Optional, List, Union, Tuple
import io
from datetime import datetime

@tool
def pandas(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    operation: str,
    parameters: Optional[Dict[str, Any]] = None,
    input_format: str = "json",
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    使用pandas进行数据处理和分析。
    
    Args:
        data: 要处理的数据，可以是JSON字符串、字典或字典列表
        operation: 要执行的操作，如filter、sort、group、pivot、merge等
        parameters: 操作的参数
        input_format: 输入数据格式，可选值：json, csv, dict, list
        output_format: 输出数据格式，可选值：json, csv, dict, records, html, markdown
    
    Returns:
        Dict[str, Any]: 包含处理结果的字典
    """
    if parameters is None:
        parameters = {}
    
    try:
        # 将输入数据转换为DataFrame
        df = None
        
        if input_format == "json" and isinstance(data, str):
            df = pd.read_json(data, orient='records')
        elif input_format == "csv" and isinstance(data, str):
            df = pd.read_csv(io.StringIO(data))
        elif input_format == "dict" and isinstance(data, dict):
            df = pd.DataFrame(data)
        elif input_format == "list" and isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            # 尝试自动推断格式
            if isinstance(data, str):
                try:
                    df = pd.read_json(data, orient='records')
                except:
                    try:
                        df = pd.read_csv(io.StringIO(data))
                    except:
                        return {
                            "status": "error",
                            "error_type": "ValueError",
                            "error_message": "无法解析输入数据，请检查数据格式"
                        }
            elif isinstance(data, dict):
                df = pd.DataFrame(data)
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "不支持的数据类型"
                }
        
        # 执行操作
        result_df = None
        
        if operation == "filter":
            # 参数: column, operator, value
            column = parameters.get("column")
            operator = parameters.get("operator", "==")
            value = parameters.get("value")
            
            if column is None or value is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "过滤操作需要column和value参数"
                }
            
            if operator == "==":
                result_df = df[df[column] == value]
            elif operator == "!=":
                result_df = df[df[column] != value]
            elif operator == ">":
                result_df = df[df[column] > value]
            elif operator == ">=":
                result_df = df[df[column] >= value]
            elif operator == "<":
                result_df = df[df[column] < value]
            elif operator == "<=":
                result_df = df[df[column] <= value]
            elif operator == "in":
                result_df = df[df[column].isin(value)]
            elif operator == "not in":
                result_df = df[~df[column].isin(value)]
            elif operator == "contains":
                result_df = df[df[column].str.contains(value, na=False)]
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": f"不支持的操作符: {operator}"
                }
        
        elif operation == "sort":
            # 参数: columns, ascending
            columns = parameters.get("columns")
            ascending = parameters.get("ascending", True)
            
            if columns is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "排序操作需要columns参数"
                }
            
            result_df = df.sort_values(by=columns, ascending=ascending)
        
        elif operation == "group":
            # 参数: by, aggregation
            by = parameters.get("by")
            aggregation = parameters.get("aggregation", "count")
            
            if by is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "分组操作需要by参数"
                }
            
            if aggregation == "count":
                result_df = df.groupby(by).size().reset_index(name='count')
            else:
                result_df = df.groupby(by).agg(aggregation).reset_index()
        
        elif operation == "pivot":
            # 参数: index, columns, values, aggfunc
            index = parameters.get("index")
            columns = parameters.get("columns")
            values = parameters.get("values")
            aggfunc = parameters.get("aggfunc", "mean")
            
            if index is None or columns is None or values is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "透视表操作需要index、columns和values参数"
                }
            
            result_df = pd.pivot_table(df, values=values, index=index, columns=columns, aggfunc=aggfunc)
            result_df = result_df.reset_index()
        
        elif operation == "merge":
            # 参数: right_data, how, left_on, right_on
            right_data = parameters.get("right_data")
            how = parameters.get("how", "inner")
            left_on = parameters.get("left_on")
            right_on = parameters.get("right_on")
            
            if right_data is None or left_on is None or right_on is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "合并操作需要right_data、left_on和right_on参数"
                }
            
            # 将right_data转换为DataFrame
            right_df = None
            if isinstance(right_data, str):
                try:
                    right_df = pd.read_json(right_data, orient='records')
                except:
                    try:
                        right_df = pd.read_csv(io.StringIO(right_data))
                    except:
                        return {
                            "status": "error",
                            "error_type": "ValueError",
                            "error_message": "无法解析right_data，请检查数据格式"
                        }
            elif isinstance(right_data, dict):
                right_df = pd.DataFrame(right_data)
            elif isinstance(right_data, list):
                right_df = pd.DataFrame(right_data)
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "不支持的right_data类型"
                }
            
            result_df = pd.merge(df, right_df, how=how, left_on=left_on, right_on=right_on)
        
        elif operation == "select":
            # 参数: columns
            columns = parameters.get("columns")
            
            if columns is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "选择操作需要columns参数"
                }
            
            result_df = df[columns]
        
        elif operation == "drop":
            # 参数: columns
            columns = parameters.get("columns")
            
            if columns is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "删除操作需要columns参数"
                }
            
            result_df = df.drop(columns=columns)
        
        elif operation == "rename":
            # 参数: columns
            columns = parameters.get("columns")
            
            if columns is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "重命名操作需要columns参数(字典)"
                }
            
            result_df = df.rename(columns=columns)
        
        elif operation == "fillna":
            # 参数: value, columns
            value = parameters.get("value")
            columns = parameters.get("columns")
            
            if value is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "填充操作需要value参数"
                }
            
            if columns:
                for column in columns:
                    df[column] = df[column].fillna(value)
                result_df = df
            else:
                result_df = df.fillna(value)
        
        elif operation == "dropna":
            # 参数: subset, how
            subset = parameters.get("subset")
            how = parameters.get("how", "any")
            
            result_df = df.dropna(subset=subset, how=how)
        
        elif operation == "describe":
            # 参数: include, percentiles
            include = parameters.get("include", None)
            percentiles = parameters.get("percentiles", [0.25, 0.5, 0.75])
            
            result_df = df.describe(include=include, percentiles=percentiles)
        
        elif operation == "value_counts":
            # 参数: column, normalize
            column = parameters.get("column")
            normalize = parameters.get("normalize", False)
            
            if column is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "value_counts操作需要column参数"
                }
            
            result_series = df[column].value_counts(normalize=normalize)
            result_df = result_series.reset_index()
            result_df.columns = [column, 'count']
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的操作: {operation}"
            }
        
        # 将结果转换为指定的输出格式
        if output_format == "json":
            result = result_df.to_json(orient='records', date_format='iso')
            return {
                "status": "success",
                "result": json.loads(result),
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        elif output_format == "csv":
            result = result_df.to_csv(index=False)
            return {
                "status": "success",
                "result": result,
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        elif output_format == "dict":
            result = result_df.to_dict()
            return {
                "status": "success",
                "result": result,
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        elif output_format == "records":
            result = result_df.to_dict(orient='records')
            return {
                "status": "success",
                "result": result,
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        elif output_format == "html":
            result = result_df.to_html(index=False)
            return {
                "status": "success",
                "result": result,
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        elif output_format == "markdown":
            result = result_df.to_markdown(index=False)
            return {
                "status": "success",
                "result": result,
                "rows": len(result_df),
                "columns": list(result_df.columns)
            }
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的输出格式: {output_format}"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def json_processor(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    operation: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    处理JSON数据。
    
    Args:
        data: 要处理的JSON数据，可以是JSON字符串、字典或字典列表
        operation: 要执行的操作，如parse、filter、transform、merge、extract等
        parameters: 操作的参数
        output_format: 输出格式，可选值：json, yaml, string
    
    Returns:
        Dict[str, Any]: 包含处理结果的字典
    """
    if parameters is None:
        parameters = {}
    
    try:
        # 解析输入数据
        parsed_data = None
        if isinstance(data, str):
            parsed_data = json.loads(data)
        else:
            parsed_data = data
        
        # 执行操作
        result = None
        
        if operation == "parse":
            # 直接返回解析后的数据
            result = parsed_data
        
        elif operation == "filter":
            # 参数: path, value, operator
            path = parameters.get("path")
            value = parameters.get("value")
            operator = parameters.get("operator", "==")
            
            if path is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "过滤操作需要path参数"
                }
            
            # 处理路径
            parts = path.split('.')
            
            # 如果是列表，则过滤列表中的元素
            if isinstance(parsed_data, list):
                filtered_list = []
                for item in parsed_data:
                    # 获取路径指向的值
                    current = item
                    valid = True
                    for part in parts:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            valid = False
                            break
                    
                    if not valid:
                        continue
                    
                    # 应用操作符
                    if operator == "==" and current == value:
                        filtered_list.append(item)
                    elif operator == "!=" and current != value:
                        filtered_list.append(item)
                    elif operator == ">" and current > value:
                        filtered_list.append(item)
                    elif operator == ">=" and current >= value:
                        filtered_list.append(item)
                    elif operator == "<" and current < value:
                        filtered_list.append(item)
                    elif operator == "<=" and current <= value:
                        filtered_list.append(item)
                    elif operator == "in" and current in value:
                        filtered_list.append(item)
                    elif operator == "not in" and current not in value:
                        filtered_list.append(item)
                    elif operator == "contains" and isinstance(current, str) and value in current:
                        filtered_list.append(item)
                    elif operator == "exists" and current is not None:
                        filtered_list.append(item)
                
                result = filtered_list
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "过滤操作只支持列表数据"
                }
        
        elif operation == "extract":
            # 参数: path
            path = parameters.get("path")
            
            if path is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "提取操作需要path参数"
                }
            
            # 处理路径
            parts = path.split('.')
            
            # 提取数据
            current = parsed_data
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                elif isinstance(current, list) and part.isdigit():
                    index = int(part)
                    if 0 <= index < len(current):
                        current = current[index]
                    else:
                        return {
                            "status": "error",
                            "error_type": "IndexError",
                            "error_message": f"索引{index}超出列表范围"
                        }
                else:
                    return {
                        "status": "error",
                        "error_type": "KeyError",
                        "error_message": f"路径{path}不存在"
                    }
            
            result = current
        
        elif operation == "merge":
            # 参数: data2
            data2 = parameters.get("data2")
            
            if data2 is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "合并操作需要data2参数"
                }
            
            # 解析data2
            parsed_data2 = None
            if isinstance(data2, str):
                parsed_data2 = json.loads(data2)
            else:
                parsed_data2 = data2
            
            # 合并数据
            if isinstance(parsed_data, dict) and isinstance(parsed_data2, dict):
                result = {**parsed_data, **parsed_data2}
            elif isinstance(parsed_data, list) and isinstance(parsed_data2, list):
                result = parsed_data + parsed_data2
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "合并操作需要相同类型的数据(dict+dict或list+list)"
                }
        
        elif operation == "transform":
            # 参数: mapping
            mapping = parameters.get("mapping")
            
            if mapping is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "转换操作需要mapping参数"
                }
            
            # 转换数据
            if isinstance(parsed_data, list):
                transformed_list = []
                for item in parsed_data:
                    transformed_item = {}
                    for new_key, path in mapping.items():
                        # 处理路径
                        parts = path.split('.')
                        
                        # 获取路径指向的值
                        current = item
                        valid = True
                        for part in parts:
                            if isinstance(current, dict) and part in current:
                                current = current[part]
                            else:
                                valid = False
                                break
                        
                        if valid:
                            transformed_item[new_key] = current
                    
                    transformed_list.append(transformed_item)
                
                result = transformed_list
            elif isinstance(parsed_data, dict):
                transformed_item = {}
                for new_key, path in mapping.items():
                    # 处理路径
                    parts = path.split('.')
                    
                    # 获取路径指向的值
                    current = parsed_data
                    valid = True
                    for part in parts:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            valid = False
                            break
                    
                    if valid:
                        transformed_item[new_key] = current
                
                result = transformed_item
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "转换操作只支持字典或列表数据"
                }
        
        elif operation == "flatten":
            # 参数: separator
            separator = parameters.get("separator", ".")
            
            def flatten_dict(d, parent_key='', sep=separator):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    else:
                        items.append((new_key, v))
                return dict(items)
            
            if isinstance(parsed_data, dict):
                result = flatten_dict(parsed_data)
            elif isinstance(parsed_data, list):
                result = [flatten_dict(item) if isinstance(item, dict) else item for item in parsed_data]
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "扁平化操作只支持字典或列表数据"
                }
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的操作: {operation}"
            }
        
        # 将结果转换为指定的输出格式
        if output_format == "json":
            return {
                "status": "success",
                "result": result
            }
        elif output_format == "yaml":
            return {
                "status": "success",
                "result": yaml.dump(result, default_flow_style=False)
            }
        elif output_format == "string":
            return {
                "status": "success",
                "result": json.dumps(result, ensure_ascii=False, indent=2)
            }
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的输出格式: {output_format}"
            }
    
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error_type": "JSONDecodeError",
            "error_message": f"JSON解析错误: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }

@tool
def yaml_processor(
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    operation: str,
    parameters: Optional[Dict[str, Any]] = None,
    output_format: str = "yaml"
) -> Dict[str, Any]:
    """
    处理YAML数据。
    
    Args:
        data: 要处理的YAML数据，可以是YAML字符串、字典或字典列表
        operation: 要执行的操作，如parse、dump、merge等
        parameters: 操作的参数
        output_format: 输出格式，可选值：yaml, json, string
    
    Returns:
        Dict[str, Any]: 包含处理结果的字典
    """
    if parameters is None:
        parameters = {}
    
    try:
        # 解析输入数据
        parsed_data = None
        if isinstance(data, str):
            parsed_data = yaml.safe_load(data)
        else:
            parsed_data = data
        
        # 执行操作
        result = None
        
        if operation == "parse":
            # 直接返回解析后的数据
            result = parsed_data
        
        elif operation == "dump":
            # 参数: default_flow_style, indent
            default_flow_style = parameters.get("default_flow_style", False)
            indent = parameters.get("indent", 2)
            
            # 转换为YAML
            yaml_result = yaml.dump(parsed_data, default_flow_style=default_flow_style, indent=indent)
            
            # 根据输出格式返回
            if output_format == "yaml":
                return {
                    "status": "success",
                    "result": yaml_result
                }
            elif output_format == "string":
                return {
                    "status": "success",
                    "result": yaml_result
                }
            elif output_format == "json":
                return {
                    "status": "success",
                    "result": parsed_data
                }
            else:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": f"不支持的输出格式: {output_format}"
                }
        
        elif operation == "merge":
            # 参数: data2
            data2 = parameters.get("data2")
            
            if data2 is None:
                return {
                    "status": "error",
                    "error_type": "ValueError",
                    "error_message": "合并操作需要data2参数"
                }
            
            # 解析data2
            parsed_data2 = None
            if isinstance(data2, str):
                parsed_data2 = yaml.safe_load(data2)
            else:
                parsed_data2 = data2
            
            # 合并数据
            if isinstance(parsed_data, dict) and isinstance(parsed_data2, dict):
                result = {**parsed_data, **parsed_data2}
            elif isinstance(parsed_data, list) and isinstance(parsed_data2, list):
                result = parsed_data + parsed_data2
            else:
                return {
                    "status": "error",
                    "error_type": "TypeError",
                    "error_message": "合并操作需要相同类型的数据(dict+dict或list+list)"
                }
        
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的操作: {operation}"
            }
        
        # 将结果转换为指定的输出格式
        if output_format == "yaml":
            return {
                "status": "success",
                "result": yaml.dump(result, default_flow_style=False)
            }
        elif output_format == "json":
            return {
                "status": "success",
                "result": result
            }
        elif output_format == "string":
            if isinstance(result, (dict, list)):
                return {
                    "status": "success",
                    "result": yaml.dump(result, default_flow_style=False)
                }
            else:
                return {
                    "status": "success",
                    "result": str(result)
                }
        else:
            return {
                "status": "error",
                "error_type": "ValueError",
                "error_message": f"不支持的输出格式: {output_format}"
            }
    
    except yaml.YAMLError as e:
        return {
            "status": "error",
            "error_type": "YAMLError",
            "error_message": f"YAML解析错误: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e)
        }