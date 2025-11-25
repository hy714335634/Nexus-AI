"""
Agent 分类器
使用 Strands Agent 自动分类 Agent 模板并生成富文本文档
"""

from strands import Agent
from typing import Dict, Any
import json
import os
import re


# 读取系统提示词
def _load_system_prompt() -> str:
    """加载 agent classifier 的系统提示词"""
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "../../../prompts/system_agents_prompts/agent_classifier/agent_classifier_prompt.md"
    )

    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # 处理文件不存在的情况
        raise FileNotFoundError(f"File not found: {prompt_path}")



# 创建 Agent Classifier Agent 实例
_system_prompt = _load_system_prompt()
agent_classifier_agent = Agent(
    system_prompt=_system_prompt,
    model="us.anthropic.claude-sonnet-4-20250514-v1:0"
)


async def classify_and_document(
    agent_id: str,
    agent_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    分类 Agent 并生成文档

    Args:
        agent_id: Agent ID
        agent_config: Agent 配置字典，包含：
            - name: Agent 名称
            - description: Agent 描述
            - tags: 标签列表
            - agent_dependencies: Agent 依赖列表
            - tools_dependencies: 工具依赖列表
            - path: 文件路径
            - prompt_template: 提示词模板路径

    Returns:
        字典包含：
            - classification: 分类信息
                - core_functions: 核心功能分类列表
                - business_scenario: 业务场景（internal_efficiency 或 external_empowerment）
                - industries: 行业领域列表
                - subcategories: 子分类列表
                - use_cases: 使用场景列表
            - document: 生成的富文本文档
    """

    # 构建用户提示词
    user_prompt = f"""
请分析以下 Agent 配置，完成分类和文档生成任务：

---

## Agent 配置信息

**Agent ID**: {agent_id}

**名称**: {agent_config['name']}

**描述**: {agent_config['description']}

**标签**: {', '.join(agent_config.get('tags', []))}

**Agent 依赖**: {', '.join(agent_config.get('agent_dependencies', [])) if agent_config.get('agent_dependencies') else 'None'}

**工具依赖**:
{chr(10).join([f"  - {tool}" for tool in agent_config.get('tools_dependencies', [])])}

**文件路径**: {agent_config['path']}

**提示词模板**: {agent_config['prompt_template']}

---

现在请开始分析和生成！
"""

    # 调用 Strands Agent
    try:
        response = agent_classifier_agent(user_prompt)
        response_text = str(response).strip()

        # 如果输出在代码块中，提取出来
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text and response_text.startswith("```"):
            # 如果以 ``` 开头（没有语言标识）
            first_newline = response_text.find("\n")
            json_end = response_text.find("```", first_newline)
            response_text = response_text[first_newline+1:json_end].strip()

        # 解析 JSON
        result = _parse_json_response(response_text)

        return result

    except Exception as e:
        # 如果解析失败，使用后备方案
        print(f"[WARNING] 解析 JSON 响应失败: {e}")
        print(f"原始响应: {response_text if 'response_text' in locals() else 'No response'}")

        # 使用简单的关键词匹配作为后备方案
        return _fallback_classification(agent_id, agent_config, response_text if 'response_text' in locals() else "")


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    解析 JSON 格式的响应

    Args:
        response_text: JSON 格式的响应文本

    Returns:
        包含 classification 和 document 的字典
    """
    # 解析 JSON
    data = json.loads(response_text)

    # 验证必需字段
    if "metadata" not in data or "document" not in data:
        raise ValueError("JSON 响应缺少必需字段 'metadata' 或 'document'")

    # 提取分类信息
    metadata = data["metadata"]
    classification = {
        "core_functions": metadata.get("core_functions", []),
        "business_scenario": metadata.get("business_scenario", ""),
        "business_scenario_cn": metadata.get("business_scenario_cn", ""),
        "industries": metadata.get("industries", []),
        "subcategories": metadata.get("subcategories", []),
        "use_cases": metadata.get("use_cases", [])
    }

    return {
        "classification": classification,
        "document": data["document"]
    }


def _fallback_classification(
    agent_id: str,
    agent_config: Dict[str, Any],
    llm_response: str
) -> Dict[str, Any]:
    """
    后备分类方案（如果 LLM 输出解析失败）

    使用简单的关键词匹配
    """
    description = agent_config.get('description', '').lower()
    tags = [tag.lower() for tag in agent_config.get('tags', [])]

    # 核心功能分类
    core_functions = []
    if any(kw in description for kw in ['文档', '处理', 'document', 'pdf', 'ppt', 'html']):
        core_functions.append('Document Processing')
    if any(kw in description for kw in ['数据', '分析', 'data', 'analysis', '统计']):
        core_functions.append('Data Analysis')
    if any(kw in description for kw in ['检索', '研究', 'research', 'retrieval', '搜索']):
        core_functions.append('Research & Retrieval')
    if any(kw in description for kw in ['生成', '创作', 'generation', 'content']):
        core_functions.append('Content Generation')
    if any(kw in description for kw in ['集成', 'integration', 'api']):
        core_functions.append('System Integration')

    # 业务场景
    internal_keywords = ['分析', '处理', '管理', '优化', 'analyzer', 'processor', 'optimizer']
    external_keywords = ['生成', '创作', '转换', 'generator', 'creator', 'converter']

    internal_score = sum(1 for kw in internal_keywords if kw in description)
    external_score = sum(1 for kw in external_keywords if kw in description)

    if internal_score > external_score:
        business_scenario = "internal_efficiency"
        business_scenario_cn = "内部提效"
    else:
        business_scenario = "external_empowerment"
        business_scenario_cn = "外部赋能"

    # 行业领域
    industries = []
    if any(kw in description for kw in ['医学', '医疗', 'medical', 'healthcare']):
        industries.append('Healthcare')
    if any(kw in description for kw in ['aws', '云', 'cloud']):
        industries.append('Cloud Computing')
    if any(kw in description for kw in ['文档', 'document']):
        industries.append('Document Management')

    # 生成文档主体
    document = f"""# Agent: {agent_config['name']}
Agent ID: {agent_id}

## Description
{agent_config['description']}

## Classification
Core Functions: {', '.join(core_functions) if core_functions else 'General Purpose'}
Industries: {', '.join(industries) if industries else 'General'}
Business Scenario: {business_scenario_cn} ({business_scenario})

## Agent Dependencies
{'This agent depends on: ' + ', '.join(agent_config.get('agent_dependencies', [])) if agent_config.get('agent_dependencies') else 'This agent is standalone.'}

## Tool Dependencies
{chr(10).join([f'- {tool}' for tool in agent_config.get('tools_dependencies', [])])}

## Technical Details
- File Path: {agent_config['path']}
- Prompt Template: {agent_config['prompt_template']}
"""

    return {
        "classification": {
            "core_functions": core_functions,
            "business_scenario": business_scenario,
            "business_scenario_cn": business_scenario_cn,
            "industries": industries,
            "subcategories": [],
            "use_cases": []
        },
        "document": document
    }


# 保持向后兼容的接口
class AgentClassifier:
    """
    Agent 分类器包装类
    提供与原有代码兼容的接口
    """

    async def classify_and_document(
        self,
        agent_id: str,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分类 Agent 并生成文档"""
        return await classify_and_document(agent_id, agent_config)


# 创建全局实例
agent_classifier = AgentClassifier()
