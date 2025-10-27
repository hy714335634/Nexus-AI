#!/usr/bin/env python3
"""
Literature Content Extractor Agent

专业文献内容提取智能体，基于用户需求从完整文献中提取相关的原文内容。

功能特点:
- 基于PMC ID获取文献全文
- 根据用户需求精准提取相关内容
- 返回markdown格式的原文内容
- 支持表格、图表等复杂内容提取
- 保持原文准确性和完整性
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
    预处理全文内容
    
    Args:
        content: 原始全文内容
        max_length: 最大长度限制
        
    Returns:
        清理后的内容
    """
    if len(content) > max_length:
        logger.warning(f"文件过大 ({len(content)} 字符)，截断到 {max_length} 字符")
        content = content[:max_length] + "\n\n...[内容已截断以符合模型上下文限制]"
    
    if not content:
        return ""
    
    # 去除引用部分（==== Refs之后的所有内容）
    refs_pattern = r'====\s*Refs.*'
    content = re.sub(refs_pattern, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 去除过多的空行
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()


class LiteratureContentExtractorAgent:
    """文献内容提取智能体类"""
    
    def __init__(self, session_manager=None, env: str = "production", version: str = "latest", model_id: str = "default"):
        """
        初始化文献内容提取智能体
        
        Args:
            session_manager: 会话管理器
            env: 环境配置
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
        self.agent_config_path = "generated_agents_prompts/pubmed_literature_writing_assistant/literature_content_extractor"
        
        # 创建智能体实例
        self.agent = create_agent_from_prompt_template(
            agent_name=self.agent_config_path,
            session_manager=self.session_manager,
            **self.agent_params
        )
        
        logger.info(f"文献内容提取智能体初始化完成: {self.agent.name}")
    
    def extract_content(self, user_query: str, fulltext_content: str) -> str:
        """
        根据用户需求提取文献内容
        
        Args:
            user_query: 用户需求描述
            fulltext_content: 文献全文内容
            
        Returns:
            提取的markdown格式内容
        """
        prompt = f"""
请根据以下用户需求，从文献全文中提取相关的原文内容：

用户需求：
{user_query}

文献全文：
{fulltext_content}

请提取与用户需求相关的所有原文内容，以markdown格式返回。确保：
1. 内容准确，不要改写
2. 包含相关的表格、数据、结论
3. 按逻辑顺序组织
4. 标注内容来源位置
"""
        
        response = self.agent(prompt)
        
        # 处理response.message可能是字典的情况
        message = response.message
        if isinstance(message, dict):
            if "content" in message:
                text_parts = []
                for item in message["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                return "\n".join(text_parts)
            else:
                return json.dumps(message, ensure_ascii=False)
        else:
            return str(message)


@tool
def extract_literature_content(pmcid: str, user_requirement: str, research_id: str, env: str = "production") -> str:
    """
    从指定文献中提取关键信息和内容
    
    Args:
        pmcid: PMC ID（单个）
        user_requirement: 需求描述，例如："请提取文章中关于xxx工具对比分析内容，以及总结的结论"
        research_id: 研究项目ID
        
    Returns:
        提取的markdown格式内容
    """
    try:
        # 导入获取全文内容的工具
        from tools.generated_tools.pubmed_literature_screen_assistant.get_fulltext_content import get_fulltext_content
        
        # 确保pmcid格式正确
        if not pmcid.startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        # 获取文献全文
        fulltext_result = json.loads(get_fulltext_content([pmcid], research_id))
        
        if fulltext_result['status'] == "error":
            return f"错误：{fulltext_result['message']}"
        
        # 检查是否有结果
        if not fulltext_result.get('results') or len(fulltext_result['results']) == 0:
            return f"错误：未找到文献 {pmcid} 的全文内容"
        
        # 检查第一个结果是否有 content 字段
        first_result = fulltext_result['results'][0]
        if 'content' not in first_result:
            return f"错误：文献 {pmcid} 的全文未下载或未找到，状态: {first_result.get('status', 'unknown')}"
        
        # 预处理全文内容
        raw_content = first_result['content']
        preprocessed_content = preprocess_fulltext(raw_content)
        
        logger.info(f"处理文献 {pmcid}，原文长度: {len(raw_content)}, 预处理后长度: {len(preprocessed_content)}")
        
        # 创建内容提取智能体并执行提取
        extractor = LiteratureContentExtractorAgent(env=env)
        extracted_content = extractor.extract_content(user_requirement, preprocessed_content)
        
        # 添加文献信息头部
        result = f"""# 文献内容提取结果

**文献ID**: {pmcid}  
**提取需求**: {user_requirement}  
**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{extracted_content}

---

*注：以上内容提取自文献 {pmcid}，保持原文准确性*
"""
        
        return result
        
    except Exception as e:
        logger.error(f"提取文献内容时发生错误: {str(e)}")
        return f"错误：提取文献内容时发生异常 - {str(e)}"


@tool
def extract_multiple_literature_content(pmcids: List[str], user_requirement: str, research_id: str, env: str = "production") -> str:
    """
    从多篇文献中提取用户需要的内容
    
    Args:
        pmcids: PMC ID列表
        user_requirement: 用户需求描述
        research_id: 研究项目ID
        env: 环境配置，默认为production
        
    Returns:
        提取的markdown格式内容（多篇文献合并）
    """
    try:
        results = []
        
        for pmcid in pmcids:
            logger.info(f"正在处理文献: {pmcid}")
            content = extract_literature_content(pmcid, user_requirement, research_id, env)
            results.append(content)
        
        # 合并多篇文献的结果
        combined_result = f"""# 多文献内容提取结果

**文献数量**: {len(pmcids)}  
**文献ID列表**: {', '.join(pmcids)}  
**提取需求**: {user_requirement}  
**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""
        
        for i, result in enumerate(results, 1):
            combined_result += f"\n## 文献 {i}: {pmcids[i-1]}\n\n"
            # 移除单个文献结果中的头部信息，只保留内容部分
            content_start = result.find("---\n") + 4
            content_end = result.rfind("\n---\n")
            if content_start > 3 and content_end > content_start:
                actual_content = result[content_start:content_end]
            else:
                actual_content = result
            combined_result += actual_content + "\n\n"
        
        combined_result += "---\n\n*注：以上内容提取自多篇文献，保持原文准确性*"
        
        return combined_result
        
    except Exception as e:
        logger.error(f"提取多文献内容时发生错误: {str(e)}")
        return f"错误：提取多文献内容时发生异常 - {str(e)}"


if __name__ == "__main__":
    # 测试示例
    test_pmcid = "PMC7517894"
    test_requirement = "17个免费和13个商业ADMET预测软件工具都有哪些，对比结果如何"
    test_research_id = "literature_search_20251027"
    
    result = extract_literature_content(test_pmcid, test_requirement, test_research_id)
    print(result)
