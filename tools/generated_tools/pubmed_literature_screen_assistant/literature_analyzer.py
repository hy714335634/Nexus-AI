#!/usr/bin/env python3
"""
Literature Analysis Agent

专业文献分析智能体，基于给定的文献全文完成问题回答、内容分析和总结等多场景任务。

功能特点:
- 基于PMC ID获取文献全文
- 深度问题回答，包含答案内容和标准文献引用
- 全面内容分析，涵盖研究方法、结果、结论和局限性
- 结构化内容总结
- 专业文献写作风格
- 严谨、全面的输出
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry
from strands.session.file_session_manager import FileSessionManager
from strands import tool

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


def preprocess_fulltext(content: str, max_length: int = 100000) -> str:
    """
    预处理全文内容，去除引用部分
    
    Args:
        content: 原始全文内容
        
    Returns:
        清理后的内容
    """
    if len(content) > max_length:
        logger.warning(f"文件过大 ({len(content)} 字符)，截断到 {max_length} 字符")
        content = content[:max_length] + "\n\n...[内容已截断以符合模型上下文限制]"
    if not content:
        return ""
    
    # 1. 去除引用部分（==== Refs之后的所有内容）
    refs_pattern = r'====\s*Refs.*'
    content = re.sub(refs_pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. 去除过多的空行（连续3个以上空行合并为2个）
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


class LiteratureAnalyzerAgent:
    """文献分析智能体类"""
    
    def __init__(self, session_manager=None, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化文献分析智能体
        
        Args:
            session_manager: 会话管理器
            env: 环境配置 (development, production, testing)
            version: 智能体版本
            model_id: 使用的模型ID
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        self.session_manager = session_manager
        
        # 智能体参数
        self.agent_params = {
            "env": self.env,
            "version": self.version,
            "model_id": self.model_id
        }
        
        # 智能体配置路径
        self.agent_config_path = "generated_agents_prompts/literature_analysis_agent/literature_analyzer"
        
        # 创建智能体实例
        self.agent = create_agent_from_prompt_template(
            agent_name=self.agent_config_path,
            session_manager=self.session_manager,
            **self.agent_params
        )
        
        logger.info(f"文献分析智能体初始化完成: {self.agent.name}")
    
    def analyze_literature(self, user_query: str) -> str:
        """
        分析文献并回答用户问题
        
        Args:
            user_query: 用户问题或分析需求
            
        Returns:
            分析结果（包含答案内容和文献引用说明）
        """
        response = self.agent(user_query)
        print("="*100)
        # Access metrics through the AgentResult
        print(f"Total tokens: {response.metrics.accumulated_usage}")
        print(f"Execution time: {sum(response.metrics.cycle_durations):.2f} seconds")
        print(f"Tools used: {list(response.metrics.tool_metrics.keys())}")
        print("="*100)
        
        # 处理response.message可能是字典的情况
        message = response.message
        if isinstance(message, dict):
            # 提取content中的text内容
            if "content" in message:
                text_parts = []
                for item in message["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                return "\n".join(text_parts)
            else:
                # 如果不是标准格式，转为JSON字符串
                return json.dumps(message, ensure_ascii=False)
        else:
            return str(message)
    
    def answer_question(self, question: str, pmc_ids: List[str]) -> str:
        """
        基于文献回答具体问题
        
        Args:
            question: 用户问题
            pmc_ids: PMC ID列表
            
        Returns:
            问题答案（包含答案内容和文献引用说明）
        """
        return self.analyze_literature(
            user_query=f"请回答以下问题：{question}",
            pmc_ids=pmc_ids
        )
    
    def summarize_literature(self, pmc_ids: List[str], summary_type: str = "comprehensive") -> str:
        """
        总结文献内容
        
        Args:
            pmc_ids: PMC ID列表
            summary_type: 总结类型 (brief/comprehensive/detailed)
            
        Returns:
            文献总结
        """
        summary_instructions = {
            "brief": "请生成简明的文献摘要，包含核心要点和主要结论。",
            "comprehensive": "请生成全面的文献总结，包含研究背景、方法、结果、结论和意义。",
            "detailed": "请生成详细的文献分析报告，包含研究背景、方法、结果、讨论、结论、局限性和应用价值。"
        }
        
        instruction = summary_instructions.get(summary_type, summary_instructions["comprehensive"])
        
        return self.analyze_literature(
            user_query=instruction,
            pmc_ids=pmc_ids
        )
    
    def analyze_methods(self, pmc_ids: List[str]) -> str:
        """
        分析文献的研究方法
        
        Args:
            pmc_ids: PMC ID列表
            
        Returns:
            研究方法分析
        """
        return self.analyze_literature(
            user_query="请详细分析这些文献的研究方法，包括研究设计、样本特征、数据收集方法和统计分析方法。",
            pmc_ids=pmc_ids
        )
    
    def extract_key_findings(self, pmc_ids: List[str]) -> str:
        """
        提取文献的关键发现
        
        Args:
            pmc_ids: PMC ID列表
            
        Returns:
            关键发现列表
        """
        return self.analyze_literature(
            user_query="请提取这些文献的关键发现和核心结论，包括具体数据和统计结果。",
            pmc_ids=pmc_ids
        )


@tool
def analyze_literature_with_query(research_id: str, user_query: str, pmc_ids: List[str], env: str = "production") -> str:
    """
    便捷函数：基于文献回答问题或完成分析任务
    
    Args:
        research_id: 研究项目ID
        user_query: 用户问题或分析需求
        pmc_ids: PMC ID列表
        env: 环境配置, 默认为production
        
    Returns:
        JSON格式的分析结果
    """
    from tools.generated_tools.pubmed_literature_screen_assistant.get_fulltext_content import get_fulltext_content
    fulltext_content = json.loads(get_fulltext_content(pmc_ids, research_id))
    if fulltext_content['status'] == "error":
        return fulltext_content['message']
    
    # 检查是否有结果
    if not fulltext_content.get('results') or len(fulltext_content['results']) == 0:
        return json.dumps({
            "pmcid": pmc_ids[0] if pmc_ids else "",
            "should_mark": False,
            "error": "未找到文献全文",
            "reasoning": "文献全文未下载或未找到"
        }, ensure_ascii=False)
    
    # 检查第一个结果是否有 content 字段
    first_result = fulltext_content['results'][0]
    if 'content' not in first_result:
        return json.dumps({
            "pmcid": pmc_ids[0] if pmc_ids else "",
            "should_mark": False,
            "error": "文献全文未找到或未下载",
            "reasoning": f"文献状态: {first_result.get('status', 'unknown')}"
        }, ensure_ascii=False)
    
    # 预处理全文内容，去除引用部分
    raw_content = first_result['content']
    preprocessed_content = preprocess_fulltext(raw_content)
    
    logger.info(f"原文长度: {len(raw_content)}, 预处理后长度: {len(preprocessed_content)}")
    
    prompt = f"""
    ============================
    research_topic: {user_query}
    ============================
    pmcid: {pmc_ids}
    ============================
    research_id: {research_id}
    ============================
    fulltext_content: {preprocessed_content}
    ============================
    
    请完成以下任务：
    1. 分析这篇文献与研究主题的相关性，判断是否应该标记为相关文献
    2. 从文献全文(fulltext_content)中提取以下结构化元数据：
       - title: 文献标题
       - abstract: 文献摘要
       - keywords: 关键词列表
       - methods: 研究方法部分的核心内容（200-500字）
       - results: 研究结果部分的关键内容（200-500字）
       - conclusions: 研究结论部分的核心观点（100-300字）
    
    **重要提示**：
    1. 必须返回ONLY JSON格式的分析结果，不要添加任何其他文字
    2. 不要生成综述或报告内容
    3. 只提供判断理由和关键发现，不生成文章内容
    4. methods、results、conclusions要包含核心信息和关键数据，尽量保留原文关键内容
    5. 如果没有相应部分，返回空字符串或空数组
    
    请严格按照JSON格式输出所有字段（只输出JSON，不要添加任何其他文字）
    """
    agent = LiteratureAnalyzerAgent(env=env)
    response = agent.analyze_literature(prompt)
    
    # 确保response是字符串
    if not isinstance(response, str):
        response = str(response)
    
    logger.info(f"analyze_literature_with_query raw response: {response[:200]}...")
    
    # 尝试从响应中提取JSON
    import re
    
    # 辅助函数：提取完整的JSON对象（处理嵌套大括号）
    def extract_complete_json(text, start_marker=None):
        """提取匹配的JSON对象，处理嵌套大括号"""
        if start_marker:
            start_idx = text.find(start_marker)
            if start_idx == -1:
                return None, -1, -1
            # 找到标记后的第一个 {
            start_idx = text.find('{', start_idx)
        else:
            start_idx = text.find('{')
        
        if start_idx == -1:
            return None, -1, -1
        
        # 找到匹配的最后一个 }
        brace_count = 0
        end_idx = -1
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        else:
            return None, -1, -1
        
        return text[start_idx:end_idx + 1], start_idx, end_idx
    
    # 第一步：尝试提取代码块中的JSON（```json ... ```）
    code_block_start = response.find('```')
    if code_block_start != -1:
        # 找到代码块结束标记
        code_block_end = response.find('```', code_block_start + 3)
        if code_block_end != -1:
            # 提取代码块中的JSON
            json_str, _, _ = extract_complete_json(response, start_marker='```')
            if json_str:
                try:
                    parsed = json.loads(json_str)
                    # 确保必要字段存在
                    if "pmcid" not in parsed:
                        parsed["pmcid"] = pmc_ids[0] if pmc_ids else ""
                    # 确保包含所有元数据字段
                    for field in ["title", "abstract", "keywords", "methods", "results", "conclusions"]:
                        if field not in parsed:
                            if field == "keywords":
                                parsed[field] = []
                            else:
                                parsed[field] = ""
                    logger.info(f"Successfully extracted JSON from code block")
                    return json.dumps(parsed, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    logger.warning(f"Code block JSON is not valid: {e}")
    
    # 第二步：尝试从纯文本中提取JSON（寻找第一个{到最后一个}，处理嵌套）
    json_str, _, _ = extract_complete_json(response)
    if json_str:
        try:
            parsed = json.loads(json_str)
            # 确保必要字段存在
            if "pmcid" not in parsed:
                parsed["pmcid"] = pmc_ids[0] if pmc_ids else ""
            # 确保包含所有元数据字段
            for field in ["title", "abstract", "keywords", "methods", "results", "conclusions"]:
                if field not in parsed:
                    if field == "keywords":
                        parsed[field] = []
                    else:
                        parsed[field] = ""
            logger.info(f"Successfully extracted JSON from text")
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"Extracted JSON is not valid: {e}")
    
    # 第三步：使用正则表达式尝试提取包含pmcid的JSON对象（作为最后手段）
    json_match = re.search(r'\{[\s\S]*?"pmcid"[\s\S]*?\}', response)
    if json_match:
        json_str = json_match.group(0)
        try:
            parsed = json.loads(json_str)
            if "pmcid" not in parsed:
                parsed["pmcid"] = pmc_ids[0] if pmc_ids else ""
            for field in ["title", "abstract", "keywords", "methods", "results", "conclusions"]:
                if field not in parsed:
                    if field == "keywords":
                        parsed[field] = []
                    else:
                        parsed[field] = ""
            logger.info(f"Successfully extracted JSON using fallback method")
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.warning(f"Fallback JSON is not valid: {e}")
    
    # 如果没有找到JSON，返回错误
    logger.error(f"Failed to extract JSON from response. Full response: {response}")
    return json.dumps({
        "pmcid": pmc_ids[0] if pmc_ids else "",
        "should_mark": False,
        "relevance_score": 0.0,
        "title": "",
        "abstract": "",
        "keywords": [],
        "methods": "",
        "results": "",
        "conclusions": "",
        "authors": "",
        "journal": "",
        "impact_factor": "",
        "publication_date": "",
        "reasoning": "",
        "key_findings": [],
        "relevance_aspects": {
            "topic_match": "低",
            "methodology": "不相关",
            "conclusions": "无价值"
        },
        "recommendation": "不推荐标记",
        "confidence": "低",
        "error": "未能获取有效的JSON格式分析结果",
        "raw_response": response[:500]
    }, ensure_ascii=False)


if __name__ == "__main__":
    # 测试示例
    test_pmc_ids = ["PMC6613702"]
    test_query = "ADMET（吸收、分布、代谢、排泄和毒性）预测是新药研发中的关键环节。调研一下当前大多数state of the art的ADMET预测工具，写一份关于ADMET预测工具的调研报告（深度学习的，大模型的，强算法类的等等）,要求查看近五年的文献"
    
    result = analyze_literature_with_query("admet_prediction_20251023", test_query, test_pmc_ids)
    print(result)
