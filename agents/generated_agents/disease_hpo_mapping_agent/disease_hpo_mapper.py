#!/usr/bin/env python3
"""
Disease HPO Mapper Agent

专业的疾病-HPO映射专家，能够从医生主诉中提取疾病名称并关联到HPO ID。
支持中英文双语疾病名称处理、多级匹配策略和本地缓存机制。
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"

# 配置遥测
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 创建 agent 的通用参数
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"  # 默认使用 Claude Opus
}

# 使用 agent_factory 创建 agent
disease_hpo_mapper = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/disease_hpo_mapping_agent/disease_hpo_mapper", 
    **agent_params
)


def extract_and_map_diseases(medical_description: str, language: str = "auto", 
                            threshold: float = 0.7, max_results: int = 5) -> Dict[str, Any]:
    """
    从医生主诉中提取疾病名称并映射到HPO ID
    
    Args:
        medical_description (str): 医生主诉文本
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        threshold (float): 匹配阈值，范围0-1，默认0.7
        max_results (int): 最大返回结果数，默认5
    
    Returns:
        Dict[str, Any]: 包含疾病-HPO映射结果的字典
    """
    try:
        # 构建输入
        input_text = f"""请从以下医生主诉中提取疾病名称并关联到HPO ID：

{medical_description}

参数：
- 语言：{language}
- 匹配阈值：{threshold}
- 最大返回结果数：{max_results}
"""
        
        # 调用Agent
        response = disease_hpo_mapper(input_text)
        
        # 处理AgentResult对象
        if hasattr(response, 'content'):
            # 如果是AgentResult对象，获取其内容
            response_text = response.content
        else:
            # 如果已经是字符串，直接使用
            response_text = str(response)
        
        # 尝试解析JSON响应
        try:
            # 查找JSON内容（可能嵌在Markdown代码块中）
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("无法解析Agent响应为JSON格式")
            return {
                "success": False,
                "error": "无法解析响应为JSON格式",
                "original_response": response
            }
    
    except Exception as e:
        logger.error(f"提取和映射疾病时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "original_text": medical_description
        }


def batch_process_medical_descriptions(descriptions: List[str], 
                                      language: str = "auto", 
                                      threshold: float = 0.7, 
                                      max_results: int = 5) -> Dict[str, Any]:
    """
    批量处理多条医生主诉
    
    Args:
        descriptions (List[str]): 医生主诉文本列表
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        threshold (float): 匹配阈值，范围0-1，默认0.7
        max_results (int): 最大返回结果数，默认5
    
    Returns:
        Dict[str, Any]: 包含批量处理结果的字典
    """
    results = []
    
    for i, description in enumerate(descriptions):
        logger.info(f"处理第 {i+1}/{len(descriptions)} 条医生主诉")
        result = extract_and_map_diseases(
            description, 
            language=language, 
            threshold=threshold, 
            max_results=max_results
        )
        results.append(result)
    
    return {
        "success": True,
        "total_processed": len(descriptions),
        "results": results
    }


def get_hpo_info_by_id(hpo_id: str) -> Dict[str, Any]:
    """
    根据HPO ID获取详细信息
    
    Args:
        hpo_id (str): HPO ID，格式如 "HPO:0000123"
    
    Returns:
        Dict[str, Any]: 包含HPO详细信息的字典
    """
    try:
        # 构建输入
        input_text = f"""请提供以下HPO ID的详细信息：

{hpo_id}

我需要了解这个HPO术语的名称、定义、同义词和相关疾病。
"""
        
        # 调用Agent
        response = disease_hpo_mapper(input_text)
        
        # 处理AgentResult对象
        if hasattr(response, 'content'):
            # 如果是AgentResult对象，获取其内容
            response_text = response.content
        else:
            # 如果已经是字符串，直接使用
            response_text = str(response)
        
        # 尝试解析JSON响应
        try:
            # 查找JSON内容（可能嵌在Markdown代码块中）
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("无法解析Agent响应为JSON格式")
            return {
                "success": False,
                "error": "无法解析响应为JSON格式",
                "original_response": response
            }
    
    except Exception as e:
        logger.error(f"获取HPO信息时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "hpo_id": hpo_id
        }


def search_disease_by_name(disease_name: str, language: str = "auto", 
                          exact_match: bool = False) -> Dict[str, Any]:
    """
    根据疾病名称搜索相关的HPO ID
    
    Args:
        disease_name (str): 疾病名称
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
        exact_match (bool): 是否进行精确匹配，默认为False
    
    Returns:
        Dict[str, Any]: 包含搜索结果的字典
    """
    try:
        # 构建输入
        match_type = "精确匹配" if exact_match else "模糊匹配"
        input_text = f"""请根据以下疾病名称搜索相关的HPO ID：

疾病名称：{disease_name}
语言：{language}
匹配类型：{match_type}

请返回所有相关的HPO ID及其详细信息。
"""
        
        # 调用Agent
        response = disease_hpo_mapper(input_text)
        
        # 处理AgentResult对象
        if hasattr(response, 'content'):
            # 如果是AgentResult对象，获取其内容
            response_text = response.content
        else:
            # 如果已经是字符串，直接使用
            response_text = str(response)
        
        # 尝试解析JSON响应
        try:
            # 查找JSON内容（可能嵌在Markdown代码块中）
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("无法解析Agent响应为JSON格式")
            return {
                "success": False,
                "error": "无法解析响应为JSON格式",
                "original_response": response
            }
    
    except Exception as e:
        logger.error(f"搜索疾病时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "disease_name": disease_name
        }


def standardize_disease_term(term: str, language: str = "auto") -> Dict[str, Any]:
    """
    标准化疾病术语
    
    Args:
        term (str): 需要标准化的疾病术语
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
    
    Returns:
        Dict[str, Any]: 包含标准化结果的字典
    """
    try:
        # 构建输入
        input_text = f"""请将以下疾病术语标准化为正式医学名称：

术语：{term}
语言：{language}

请提供标准化后的中英文名称和相关信息。
"""
        
        # 调用Agent
        response = disease_hpo_mapper(input_text)
        
        # 处理AgentResult对象
        if hasattr(response, 'content'):
            # 如果是AgentResult对象，获取其内容
            response_text = response.content
        else:
            # 如果已经是字符串，直接使用
            response_text = str(response)
        
        # 尝试解析JSON响应
        try:
            # 查找JSON内容（可能嵌在Markdown代码块中）
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("无法解析Agent响应为JSON格式")
            return {
                "success": False,
                "error": "无法解析响应为JSON格式",
                "original_response": response
            }
    
    except Exception as e:
        logger.error(f"标准化疾病术语时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "term": term
        }


def extract_diseases_from_text(text: str, language: str = "auto") -> Dict[str, Any]:
    """
    从文本中提取疾病名称
    
    Args:
        text (str): 输入文本
        language (str): 语言，可选值：'en'（英文）、'zh'（中文）或'auto'（自动检测）
    
    Returns:
        Dict[str, Any]: 包含提取结果的字典
    """
    try:
        # 构建输入
        input_text = f"""请从以下文本中提取所有疾病名称：

{text}

语言：{language}

请仅提取疾病名称，不需要进行HPO映射。
"""
        
        # 调用Agent
        response = disease_hpo_mapper(input_text)
        
        # 处理AgentResult对象
        if hasattr(response, 'content'):
            # 如果是AgentResult对象，获取其内容
            response_text = response.content
        else:
            # 如果已经是字符串，直接使用
            response_text = str(response)
        
        # 尝试解析JSON响应
        try:
            # 查找JSON内容（可能嵌在Markdown代码块中）
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("无法解析Agent响应为JSON格式")
            return {
                "success": False,
                "error": "无法解析响应为JSON格式",
                "original_response": response
            }
    
    except Exception as e:
        logger.error(f"提取疾病名称时出错: {str(e)}")
        return {
            "success": False,
            "error": f"处理失败: {str(e)}",
            "text": text[:100] + "..." if len(text) > 100 else text
        }


if __name__ == "__main__":
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='疾病-HPO映射Agent')
    parser.add_argument('-i', '--input', type=str, 
                       help='医生主诉文本或疾病名称')
    parser.add_argument('-l', '--language', type=str, default="auto",
                       choices=["auto", "en", "zh"],
                       help='语言，可选值：auto（自动检测）、en（英文）、zh（中文）')
    parser.add_argument('-m', '--mode', type=str, default="extract_and_map",
                       choices=["extract_and_map", "search", "standardize", "extract", "hpo_info"],
                       help='操作模式：extract_and_map（提取并映射）、search（搜索疾病）、standardize（标准化术语）、extract（提取疾病名称）、hpo_info（获取HPO信息）')
    parser.add_argument('-t', '--threshold', type=float, default=0.7,
                       help='匹配阈值，范围0-1')
    parser.add_argument('-r', '--max_results', type=int, default=5,
                       help='最大返回结果数')
    parser.add_argument('-e', '--exact_match', action='store_true',
                       help='是否进行精确匹配（仅在search模式下有效）')
    parser.add_argument('--hpo_id', type=str,
                       help='HPO ID（仅在hpo_info模式下有效）')
    
    args = parser.parse_args()
    
    print(f"✅ Disease HPO Mapper Agent 创建成功: {disease_hpo_mapper.name}")
    
    # 如果没有提供输入
    if not args.input and args.mode != "hpo_info":
        print("请提供输入文本。使用 -h 查看帮助信息。")
        exit(1)
    
    if args.mode == "hpo_info" and not args.hpo_id:
        print("在hpo_info模式下，请提供HPO ID。使用 -h 查看帮助信息。")
        exit(1)
    
    # 根据模式执行不同操作
    try:
        if args.mode == "extract_and_map":
            print(f"📋 从医生主诉中提取疾病名称并映射到HPO ID...")
            result = extract_and_map_diseases(
                args.input, 
                language=args.language,
                threshold=args.threshold,
                max_results=args.max_results
            )
        elif args.mode == "search":
            print(f"🔍 搜索疾病: {args.input}...")
            result = search_disease_by_name(
                args.input,
                language=args.language,
                exact_match=args.exact_match
            )
        elif args.mode == "standardize":
            print(f"📝 标准化疾病术语: {args.input}...")
            result = standardize_disease_term(
                args.input,
                language=args.language
            )
        elif args.mode == "extract":
            print(f"🔍 提取疾病名称...")
            result = extract_diseases_from_text(
                args.input,
                language=args.language
            )
        elif args.mode == "hpo_info":
            print(f"ℹ️ 获取HPO信息: {args.hpo_id}...")
            result = get_hpo_info_by_id(args.hpo_id)
        
        # 打印结果
        print(f"📋 结果:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")