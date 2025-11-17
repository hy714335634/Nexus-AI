#!/usr/bin/env python3
"""
技术文档多Agent系统 - Swarm编排脚本

使用Swarm框架编排三个Agent完成技术文档的生成、审核和HTML转换流程：
1. document_writer_agent: 根据用户需求生成技术文档
2. document_reviewer_agent: 审核文档并给出反馈
3. content_processor_agent: 将审核通过的文档转换为HTML格式

工作流程：
用户输入 -> 文档生成 -> 审核 -> [未通过则修改] -> 审核通过 -> HTML转换 -> 输出

项目: tech_doc_multi_agent_system
框架: Strands SDK + Swarm
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Strands SDK 导入
from strands.multiagent import Swarm
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 直接导入工具函数（用于HTML转换）
from tools.generated_tools.tech_doc_multi_agent_system.document_structure_parser import (
    parse_document_structure,
    validate_document_structure,
    analyze_document_complexity
)
from tools.generated_tools.tech_doc_multi_agent_system.html_generator import (
    generate_html,
    generate_html_with_syntax_highlighting,
    generate_responsive_html
)

# 配置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tech_doc_swarm")

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class TechDocSwarmSystem:
    """
    技术文档多Agent系统 - Swarm编排类
    
    使用Swarm框架协调三个Agent完成技术文档的完整处理流程
    """
    
    def __init__(
        self,
        env: str = "production",
        version: str = "latest",
        model_id: str = "default",
        max_review_iterations: int = 5
    ):
        """
        初始化技术文档Swarm系统
        
        Args:
            env: 运行环境 (development/production/testing)
            version: Agent版本
            model_id: 使用的模型ID
            max_review_iterations: 最大审核迭代次数
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        self.max_review_iterations = max_review_iterations
        
        # 工作流上下文（用于Agent之间传递数据，不使用本地文件）
        self.context = {
            "user_requirement": "",
            "document_content": None,
            "review_result": None,
            "html_output": None,
            "iteration_count": 0,
            "workflow_status": "initialized"
        }
        
        # 创建三个Agent实例
        logger.info("正在创建Agent实例...")
        self._create_agents()
        
        # 创建Swarm编排
        logger.info("正在创建Swarm编排...")
        self._create_swarm()
        
        logger.info("✅ 技术文档Swarm系统初始化完成")
    
    def _create_agents(self):
        """使用create_agent_from_prompt_template统一创建三个Agent实例"""
        try:
            # 统一的Agent创建参数
            agent_params = {
                "env": self.env,
                "version": self.version,
                "model_id": self.model_id
            }
            
            # 创建文档编写Agent
            self.document_writer = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/tech_doc_multi_agent_system/document_writer_agent",
                **agent_params
            )
            logger.info(f"✅ Document Writer Agent创建成功: {self.document_writer.name}")
            
            # 创建文档审核Agent
            self.document_reviewer = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/tech_doc_multi_agent_system/document_reviewer_agent",
                **agent_params
            )
            logger.info(f"✅ Document Reviewer Agent创建成功: {self.document_reviewer.name}")
            
            # 创建内容处理Agent
            self.content_processor = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/tech_doc_multi_agent_system/content_processor_agent",
                **agent_params
            )
            logger.info(f"✅ Content Processor Agent创建成功: {self.content_processor.name}")
            
        except Exception as e:
            logger.error(f"❌ Agent创建失败: {str(e)}")
            raise
    
    def _create_swarm(self):
        """创建Swarm编排对象"""
        try:
            # 创建Swarm，传入所有Agent对象列表（现在都是统一的Agent对象）
            agent_instances = [
                self.document_writer,      # Agent对象
                self.document_reviewer,   # Agent对象
                self.content_processor     # Agent对象
            ]
            
            # 创建Swarm
            self.swarm = Swarm(
                agent_instances,
                max_handoffs=30,
                max_iterations=30,
                execution_timeout=600.0,  # 10分钟
                node_timeout=300.0,       # 5分钟每个Agent
                repetitive_handoff_detection_window=10,
                repetitive_handoff_min_unique_agents=2
            )
            logger.info("✅ Swarm创建完成")
            logger.info(f"   - 包含 {len(agent_instances)} 个Agent")
            logger.info(f"   - 入口Agent: {self.document_writer.name}")
            
        except Exception as e:
            logger.error(f"❌ Swarm创建失败: {str(e)}")
            raise
    
    def process_user_requirement(
        self,
        user_requirement: str,
        style_config: Optional[Dict[str, Any]] = None,
        pass_threshold: float = 75.0
    ) -> Dict[str, Any]:
        """
        处理用户需求，完成完整的技术文档生成流程
        
        Args:
            user_requirement: 用户自然语言需求描述
            style_config: HTML样式配置（可选）
            pass_threshold: 审核通过阈值（默认75分）
            
        Returns:
            Dict包含完整处理结果：
            {
                "status": "success" | "error",
                "document_content": {...},
                "html_output": "...",
                "processing_info": {...},
                "iteration_count": int,
                "workflow_summary": {...}
            }
        """
        try:
            logger.info("="*80)
            logger.info("🚀 开始处理用户需求")
            logger.info("="*80)
            logger.info(f"📝 用户需求: {user_requirement[:100]}...")
            
            # 更新上下文
            self.context["user_requirement"] = user_requirement
            self.context["workflow_status"] = "processing"
            self.context["iteration_count"] = 0
            
            # 步骤1: 生成初始文档
            logger.info("\n" + "="*80)
            logger.info("📝 [步骤1] 生成初始技术文档")
            logger.info("="*80)
            
            generation_result = self._generate_initial_document(user_requirement)
            
            if generation_result["status"] != "success":
                raise ValueError(f"文档生成失败: {generation_result.get('error_message', '未知错误')}")
            
            document_content = generation_result["document_content"]
            self.context["document_content"] = document_content
            self.context["iteration_count"] = 1
            
            logger.info(f"✅ 初始文档生成完成")
            logger.info(f"   - 标题: {document_content.get('title', 'Untitled')}")
            logger.info(f"   - 章节数: {len(document_content.get('sections', []))}")
            
            # 步骤2: 审核循环（直到通过或达到最大迭代次数）
            logger.info("\n" + "="*80)
            logger.info("🔍 [步骤2] 文档审核循环")
            logger.info("="*80)
            
            review_iteration = 0
            is_approved = False
            
            while review_iteration < self.max_review_iterations and not is_approved:
                review_iteration += 1
                logger.info(f"\n--- 审核迭代 {review_iteration}/{self.max_review_iterations} ---")
                
                # 执行审核
                review_result = self._review_document(
                    document_content,
                    pass_threshold=pass_threshold
                )
                
                self.context["review_result"] = review_result
                
                # 检查审核决策
                decision = review_result.get("review_decision", {}).get("decision", "unknown")
                overall_score = review_result.get("quality_assessment", {}).get("overall_score", 0)
                
                logger.info(f"📊 审核结果:")
                logger.info(f"   - 决策: {decision}")
                logger.info(f"   - 总分: {overall_score:.1f}")
                
                if decision == "pass":
                    is_approved = True
                    logger.info("✅ 文档审核通过！")
                    break
                
                # 如果未通过，处理反馈并修改文档
                logger.info("⚠️  文档未通过审核，开始处理反馈...")
                
                feedback_result = self._process_review_feedback(document_content, review_result)
                
                if feedback_result["status"] == "approved":
                    # 特殊情况：Agent判断已通过
                    is_approved = True
                    logger.info("✅ Agent判断文档已通过")
                    break
                elif feedback_result["status"] == "max_iterations_reached":
                    logger.warning(f"⚠️  已达到最大迭代次数 ({self.max_review_iterations})")
                    break
                elif feedback_result["status"] == "revised":
                    # 更新文档内容
                    document_content = feedback_result["document_content"]
                    self.context["document_content"] = document_content
                    self.context["iteration_count"] += 1
                    logger.info(f"✅ 文档已修改 (总迭代: {self.context['iteration_count']})")
                else:
                    logger.error(f"❌ 反馈处理失败: {feedback_result.get('error_message', '未知错误')}")
                    break
            
            if not is_approved:
                logger.warning("⚠️  文档未能在最大迭代次数内通过审核，将使用当前版本继续处理")
            
            # 步骤3: 转换为HTML
            logger.info("\n" + "="*80)
            logger.info("🔄 [步骤3] 转换为HTML格式")
            logger.info("="*80)
            
            html_result = self._process_document_to_html(
                document_content=document_content,
                style_config=style_config,
                enable_syntax_highlighting=True,
                enable_responsive_design=True
            )
            
            if html_result["status"] != "success":
                raise ValueError(f"HTML转换失败: {html_result.get('error_message', '未知错误')}")
            
            self.context["html_output"] = html_result["html_output"]
            self.context["workflow_status"] = "completed"
            
            logger.info("✅ HTML转换完成")
            logger.info(f"   - HTML大小: {html_result['processing_info']['html_size']} 字节")
            
            # 构建最终结果
            result = {
                "status": "success",
                "document_content": document_content,
                "html_output": html_result["html_output"],
                "processing_info": html_result["processing_info"],
                "iteration_count": self.context["iteration_count"],
                "review_iterations": review_iteration,
                "is_approved": is_approved,
                "workflow_summary": {
                    "user_requirement": user_requirement,
                    "document_title": document_content.get("title", "Untitled"),
                    "total_iterations": self.context["iteration_count"],
                    "review_iterations": review_iteration,
                    "final_status": "approved" if is_approved else "max_iterations_reached",
                    "html_size": html_result["processing_info"]["html_size"],
                    "completed_at": datetime.now().isoformat()
                }
            }
            
            logger.info("\n" + "="*80)
            logger.info("✅ 工作流执行完成")
            logger.info("="*80)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 工作流执行失败: {str(e)}", exc_info=True)
            self.context["workflow_status"] = "error"
            return {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "context": self.context
            }
    
    def _generate_initial_document(self, user_requirement: str) -> Dict[str, Any]:
        """
        生成初始文档（使用document_writer Agent）
        
        Args:
            user_requirement: 用户需求描述
            
        Returns:
            Dict包含文档内容和状态
        """
        try:
            logger.info("📝 开始生成初始文档...")
            
            # 构建提示
            prompt = f"""# 初始文档生成请求

## 用户需求
{user_requirement}

## 期望输出
请根据上述需求，完成以下任务：

1. 分析我的文档需求，提取关键信息点
2. 设计适合的文档结构和大纲
3. 生成完整、专业的技术文档内容
4. 确保文档的技术准确性和可读性

## 文档格式要求
- 使用Markdown格式
- 包含清晰的章节结构
- 提供必要的代码示例和说明
- 使用专业、准确的技术术语

## 输出格式
请以JSON格式输出文档内容，包含以下字段：
- title: 文档标题
- sections: 章节列表（每个章节包含title和content）
- metadata: 元数据（作者、日期、版本等）
"""
            
            # 调用Agent生成文档
            response = self.document_writer(prompt)
            
            # 解析响应
            document_content = self._parse_agent_response(response)
            
            if not document_content:
                raise ValueError("文档生成失败：响应为空")
            
            logger.info("✅ 初始文档生成完成")
            
            return {
                "status": "success",
                "document_content": document_content,
                "iteration": 1
            }
        
        except Exception as e:
            logger.error(f"❌ 文档生成失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__
            }
    
    def _process_review_feedback(
        self,
        document_content: Dict[str, Any],
        review_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理审核反馈并修改文档（使用document_writer Agent）
        
        Args:
            document_content: 当前文档内容
            review_feedback: 审核反馈内容
            
        Returns:
            Dict包含修改后的文档和状态
        """
        try:
            # 检查迭代次数
            if self.context["iteration_count"] >= self.max_review_iterations:
                logger.warning(f"⚠️ 已达到最大迭代次数 ({self.max_review_iterations})")
                return {
                    "status": "max_iterations_reached",
                    "message": f"已达到最大迭代次数 {self.max_review_iterations}",
                    "document_content": document_content
                }
            
            logger.info(f"🔄 处理审核反馈 (迭代 {self.context['iteration_count'] + 1})...")
            
            # 检查是否通过审核
            if review_feedback.get("review_decision", {}).get("decision") == "pass":
                logger.info("✅ 文档已通过审核")
                return {
                    "status": "approved",
                    "document_content": document_content,
                    "iteration": self.context["iteration_count"] + 1
                }
            
            # 构建反馈处理提示
            doc_str = json.dumps(document_content, ensure_ascii=False, indent=2)
            feedback_str = json.dumps(review_feedback, ensure_ascii=False, indent=2)
            
            prompt = f"""# 文档反馈处理请求

## 原始文档
```json
{doc_str}
```

## 审核反馈
```json
{feedback_str}
```

## 处理要求
请根据上述审核反馈，完成以下任务：

1. 分析审核反馈，提取关键修改点和优先级
2. 根据反馈修改文档内容
3. 保留已通过的部分，仅针对反馈进行修改
4. 提供修改说明，解释如何应对每条反馈

## 输出格式
请以JSON格式输出修改后的文档内容，包含以下字段：
- title: 文档标题
- sections: 章节列表（每个章节包含title和content）
- metadata: 元数据
- modification_notes: 修改说明
"""
            
            # 调用Agent处理反馈
            response = self.document_writer(prompt)
            
            # 解析响应
            modified_content = self._parse_agent_response(response)
            
            if not modified_content:
                raise ValueError("文档修改失败：响应为空")
            
            logger.info(f"✅ 文档修改完成 (迭代 {self.context['iteration_count'] + 1})")
            
            return {
                "status": "revised",
                "document_content": modified_content,
                "iteration": self.context["iteration_count"] + 1
            }
        
        except Exception as e:
            logger.error(f"❌ 反馈处理失败: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "error_type": type(e).__name__
            }
    
    def _parse_agent_response(self, response) -> Optional[Dict[str, Any]]:
        """
        解析Agent响应
        
        Args:
            response: Agent返回的响应对象
            
        Returns:
            解析后的文档内容字典，失败返回None
        """
        try:
            # 多层级属性检查
            if hasattr(response, 'content') and response.content:
                content = response.content
            elif isinstance(response, str):
                content = response
            elif hasattr(response, 'text'):
                content = response.text
            else:
                content = str(response)
            
            # 尝试提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_result = json.loads(json_str)
                return parsed_result
            
            # 如果没有JSON，返回文本内容
            return {
                "title": "Generated Document",
                "sections": [
                    {
                        "title": "Content",
                        "content": content
                    }
                ],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "format": "text"
                }
            }
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"响应解析失败: {str(e)}")
            return None
    
    def _process_document_to_html(
        self,
        document_content: Dict[str, Any],
        style_config: Optional[Dict[str, Any]] = None,
        enable_syntax_highlighting: bool = True,
        enable_responsive_design: bool = True
    ) -> Dict[str, Any]:
        """
        将文档内容转换为HTML格式（内联实现）
        
        此函数封装了完整的HTML转换流程：
        1. 解析文档结构
        2. 验证文档有效性
        3. 分析文档复杂度
        4. 生成HTML文档
        5. 应用语法高亮和响应式设计
        
        Args:
            document_content: DocumentContent对象，包含审核通过的文档内容
            style_config: 样式配置，如主题、语言等
            enable_syntax_highlighting: 是否启用语法高亮
            enable_responsive_design: 是否启用响应式设计
            
        Returns:
            包含HTML内容和处理信息的字典：
            {
                "status": "success" | "error",
                "html_output": "完整的HTML字符串",
                "processing_info": {...},
                "error_message": "错误信息（如果有）"
            }
        """
        try:
            logger.info("开始HTML转换流程")
            start_time = datetime.now()
            
            # 验证输入
            if not isinstance(document_content, dict):
                raise ValueError("document_content必须是字典类型")
            
            if "title" not in document_content or "sections" not in document_content:
                raise ValueError("document_content必须包含title和sections字段")
            
            logger.info(f"处理文档: {document_content.get('title', 'Untitled')}")
            
            # 1. 验证文档结构
            logger.info("验证文档结构...")
            validation_result = json.loads(validate_document_structure(document_content))
            
            if validation_result.get("status") != "success":
                logger.error(f"文档验证失败: {validation_result}")
                return {
                    "status": "error",
                    "error_message": "文档结构验证失败",
                    "validation_result": validation_result
                }
            
            if not validation_result.get("is_valid", False):
                logger.warning(f"文档存在验证错误: {validation_result.get('validation_errors', [])}")
                return {
                    "status": "error",
                    "error_message": "文档结构无效",
                    "validation_errors": validation_result.get("validation_errors", [])
                }
            
            logger.info("✓ 文档结构验证通过")
            
            # 2. 解析文档结构
            logger.info("解析文档结构...")
            parse_result = json.loads(parse_document_structure(document_content, parse_mode="auto"))
            
            if parse_result.get("status") != "success":
                logger.error(f"文档解析失败: {parse_result}")
                return {
                    "status": "error",
                    "error_message": "文档结构解析失败",
                    "parse_result": parse_result
                }
            
            document_tree = parse_result.get("document_tree", {})
            logger.info(f"✓ 文档解析完成，共{parse_result['parse_info']['element_count']}个元素")
            
            # 3. 分析文档复杂度
            logger.info("分析文档复杂度...")
            complexity_result = json.loads(analyze_document_complexity(document_content))
            
            if complexity_result.get("status") == "success":
                complexity_level = complexity_result.get("complexity_level", "moderate")
                complexity_score = complexity_result.get("complexity_score", 0)
                logger.info(f"✓ 文档复杂度: {complexity_level} (评分: {complexity_score})")
                
                # 根据复杂度调整样式配置
                if style_config is None:
                    style_config = {}
                
                if "include_toc" not in style_config:
                    # 复杂文档自动添加目录
                    style_config["include_toc"] = complexity_level in ["moderate", "complex"]
            
            # 4. 生成HTML
            logger.info("生成HTML文档...")
            
            if enable_syntax_highlighting and enable_responsive_design:
                # 先生成带语法高亮的HTML
                highlight_result = json.loads(
                    generate_html_with_syntax_highlighting(
                        parse_result,
                        style_config,
                        highlight_library="prism"
                    )
                )
                
                if highlight_result.get("status") != "success":
                    logger.error(f"语法高亮生成失败: {highlight_result}")
                    return {
                        "status": "error",
                        "error_message": "HTML生成失败（语法高亮）",
                        "generation_result": highlight_result
                    }
                
                # 直接使用带语法高亮的HTML作为基础，再应用响应式
                final_result = json.loads(
                    generate_responsive_html(
                        parse_result,
                        style_config
                    )
                )
                
                # 合并语法高亮和响应式
                if final_result.get("status") == "success":
                    html_content = final_result.get("html_content", "")
                    # 添加Prism.js库
                    if "prism" not in html_content:
                        prism_css = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css" />'
                        prism_js = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>'
                        html_content = html_content.replace("</head>", f"  {prism_css}\n</head>")
                        html_content = html_content.replace("</body>", f"  {prism_js}\n</body>")
                        final_result["html_content"] = html_content
                
            elif enable_syntax_highlighting:
                final_result = json.loads(
                    generate_html_with_syntax_highlighting(
                        parse_result,
                        style_config,
                        highlight_library="prism"
                    )
                )
            elif enable_responsive_design:
                final_result = json.loads(
                    generate_responsive_html(
                        parse_result,
                        style_config
                    )
                )
            else:
                final_result = json.loads(
                    generate_html(
                        parse_result,
                        style_config
                    )
                )
            
            if final_result.get("status") != "success":
                logger.error(f"HTML生成失败: {final_result}")
                return {
                    "status": "error",
                    "error_message": "HTML生成失败",
                    "generation_result": final_result
                }
            
            html_output = final_result.get("html_content", "")
            html_size = final_result.get("html_size", 0)
            
            logger.info(f"✓ HTML生成完成，大小: {html_size} 字节")
            
            # 计算总处理时间
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # 构建处理信息
            processing_info = {
                "document_title": document_content.get("title", ""),
                "processing_time": processing_time,
                "html_size": html_size,
                "element_count": parse_result["parse_info"]["element_count"],
                "complexity_level": complexity_result.get("complexity_level", "unknown"),
                "complexity_score": complexity_result.get("complexity_score", 0),
                "features": {
                    "syntax_highlighting": enable_syntax_highlighting,
                    "responsive_design": enable_responsive_design,
                    "table_of_contents": style_config.get("include_toc", True) if style_config else True
                },
                "validation_warnings": validation_result.get("validation_warnings", []),
                "processed_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ HTML转换完成，总耗时: {processing_time:.2f}秒")
            
            return {
                "status": "success",
                "html_output": html_output,
                "processing_info": processing_info
            }
            
        except Exception as e:
            logger.error(f"❌ HTML转换失败: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error_message": f"HTML转换异常: {str(e)}",
                "error_type": type(e).__name__
            }
    
    def _review_document(
        self,
        document: Any,
        pass_threshold: float = 75.0
    ) -> Dict[str, Any]:
        """
        执行文档审核（内联实现，替代review_document函数）
        
        Args:
            document: 文档内容（字符串或字典）
            pass_threshold: 通过阈值
            
        Returns:
            Dict: 审核结果
        """
        try:
            # 解析文档内容
            doc_dict = self._parse_document_content(document)
            logger.info(f"开始审核文档: {doc_dict.get('title', '未命名')}")
            
            # 格式化审核请求
            request = self._format_review_request(doc_dict, pass_threshold=pass_threshold)
            logger.info(f"审核请求已生成，长度: {len(request)}")
            
            # 调用Agent进行审核
            logger.info("正在调用审核Agent...")
            response = self.document_reviewer(request)
            logger.info("Agent响应完成")
            
            # 提取审核结果
            result = self._extract_review_result(response)
            
            # 添加元数据
            result["document_title"] = doc_dict.get("title", "未命名文档")
            result["review_parameters"] = {"pass_threshold": pass_threshold}
            
            logger.info(f"审核完成，决策: {result.get('review_decision', {}).get('decision', 'unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"文档审核失败: {str(e)}")
            return {
                "status": "error",
                "error": f"文档审核失败: {str(e)}"
            }
    
    def _parse_document_content(self, document_input: Any) -> Dict[str, Any]:
        """
        解析文档内容输入
        
        Args:
            document_input: 文档内容，可以是字符串或字典
        
        Returns:
            Dict: 标准化的文档内容对象
        """
        try:
            if isinstance(document_input, str):
                # 尝试解析JSON字符串
                try:
                    document = json.loads(document_input)
                except json.JSONDecodeError:
                    # 如果不是JSON，创建基本文档结构
                    document = {
                        "title": "待审核文档",
                        "sections": [
                            {
                                "title": "内容",
                                "content": document_input
                            }
                        ],
                        "metadata": {}
                    }
            elif isinstance(document_input, dict):
                document = document_input
            else:
                raise ValueError(f"不支持的文档输入类型: {type(document_input)}")
            
            # 验证必要字段
            if "title" not in document:
                document["title"] = "未命名文档"
            if "sections" not in document:
                document["sections"] = []
            if "metadata" not in document:
                document["metadata"] = {}
            
            return document
            
        except Exception as e:
            logger.error(f"解析文档内容失败: {str(e)}")
            raise
    
    def _format_review_request(self, document: Dict[str, Any], **kwargs) -> str:
        """
        格式化审核请求
        
        Args:
            document: 文档内容对象
            **kwargs: 其他审核参数
        
        Returns:
            str: 格式化的审核请求文本
        """
        # 提取文档内容摘要
        title = document.get("title", "未命名文档")
        section_count = len(document.get("sections", []))
        
        # 计算文档总字数
        total_words = 0
        for section in document.get("sections", []):
            content = section.get("content", "")
            total_words += len(content)
        
        # 构建请求文本
        request_parts = [
            f"请审核以下技术文档：",
            f"",
            f"文档标题：{title}",
            f"章节数量：{section_count}",
            f"文档字数：约{total_words}字",
            f"",
            f"完整文档内容：",
            json.dumps(document, ensure_ascii=False, indent=2),
            f"",
            f"审核要求：",
        ]
        
        # 添加自定义审核参数
        if "dimensions" in kwargs:
            request_parts.append(f"- 评估维度：{', '.join(kwargs['dimensions'])}")
        else:
            request_parts.append("- 评估维度：全部维度（内容完整性、技术准确性、逻辑连贯性、格式规范性、语言表达）")
        
        if "focus_areas" in kwargs:
            request_parts.append(f"- 重点关注：{', '.join(kwargs['focus_areas'])}")
        
        if "pass_threshold" in kwargs:
            request_parts.append(f"- 通过阈值：{kwargs['pass_threshold']}分")
        else:
            request_parts.append("- 通过阈值：75分")
        
        request_parts.extend([
            "",
            "请提供详细的审核报告，包括：",
            "1. 多维度质量评分",
            "2. 识别的具体问题",
            "3. 改进建议",
            "4. 审核决策（通过/不通过）",
            "5. 决策理由"
        ])
        
        return "\n".join(request_parts)
    
    def _extract_review_result(self, response: Any) -> Dict[str, Any]:
        """
        从Agent响应中提取审核结果
        
        Args:
            response: Agent的响应对象
        
        Returns:
            Dict: 结构化的审核结果
        """
        try:
            # 提取响应内容
            if hasattr(response, 'content') and response.content:
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            elif hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)
            
            logger.info(f"提取到的响应内容长度: {len(response_text)}")
            
            # 尝试从响应中提取JSON
            try:
                # 查找JSON块
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    review_result = json.loads(json_str)
                    logger.info("成功从响应中解析JSON审核结果")
                    return review_result
                else:
                    logger.warning("响应中未找到JSON格式数据")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败: {str(e)}")
            
            # 如果无法解析JSON，创建基本结果结构
            review_result = {
                "status": "success",
                "review_summary": {
                    "overall_score": 75.0,
                    "decision": "needs_review",
                    "review_text": response_text
                },
                "quality_assessment": {
                    "overall_score": 75.0,
                    "dimension_scores": {}
                },
                "identified_issues": {
                    "total_count": 0,
                    "issues": []
                },
                "review_feedback": {
                    "feedback_summary": "审核已完成，请查看详细内容",
                    "improvement_suggestions": []
                },
                "review_decision": {
                    "decision": "needs_review",
                    "decision_summary": "审核结果需要人工确认"
                },
                "raw_response": response_text
            }
            
            return review_result
            
        except Exception as e:
            logger.error(f"提取审核结果失败: {str(e)}")
            return {
                "status": "error",
                "error": f"提取审核结果失败: {str(e)}",
                "raw_response": str(response)
            }
    
    def get_context(self) -> Dict[str, Any]:
        """获取当前工作流上下文"""
        return self.context.copy()
    
    def reset_context(self):
        """重置工作流上下文"""
        self.context = {
            "user_requirement": "",
            "document_content": None,
            "review_result": None,
            "html_output": None,
            "iteration_count": 0,
            "workflow_status": "initialized"
        }
        logger.info("🔄 工作流上下文已重置")


def create_tech_doc_swarm_system(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    max_review_iterations: int = 5
) -> TechDocSwarmSystem:
    """
    创建技术文档Swarm系统实例
    
    Args:
        env: 运行环境
        version: Agent版本
        model_id: 模型ID
        max_review_iterations: 最大审核迭代次数
        
    Returns:
        TechDocSwarmSystem实例
    """
    return TechDocSwarmSystem(
        env=env,
        version=version,
        model_id=model_id,
        max_review_iterations=max_review_iterations
    )


# 主程序入口
if __name__ == "__main__":
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(
        description='技术文档多Agent系统 - Swarm编排脚本'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="请创建一个关于RESTful API设计最佳实践的技术文档",
        help='用户需求描述（自然语言）'
    )
    parser.add_argument(
        '-e', '--env',
        type=str,
        default="production",
        choices=["development", "production", "testing"],
        help='运行环境'
    )
    parser.add_argument(
        '-v', '--version',
        type=str,
        default="latest",
        help='Agent版本'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=5,
        help='最大审核迭代次数（默认5次）'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=75.0,
        help='审核通过阈值（默认75.0分）'
    )
    parser.add_argument(
        '--theme',
        type=str,
        default="default",
        choices=["default", "dark", "light"],
        help='HTML主题（默认: default）'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='输出HTML文件路径（可选）'
    )
    parser.add_argument(
        '--output-json',
        type=str,
        help='输出完整结果JSON文件路径（可选）'
    )
    
    args = parser.parse_args()
    
    # 创建Swarm系统
    print("🚀 正在启动技术文档Swarm系统...")
    system = create_tech_doc_swarm_system(
        env=args.env,
        version=args.version,
        max_review_iterations=args.max_iterations
    )
    
    # 配置HTML样式
    style_config = {
        "theme": args.theme,
        "language": "zh-CN",
        "include_toc": True
    }
    
    # 执行工作流
    print(f"\n📋 用户需求: {args.input}\n")
    
    try:
        result = system.process_user_requirement(
            user_requirement=args.input,
            style_config=style_config,
            pass_threshold=args.threshold
        )
        
        if result["status"] == "success":
            print("\n" + "="*80)
            print("✅ 工作流执行成功")
            print("="*80)
            
            summary = result["workflow_summary"]
            print(f"\n📊 工作流摘要:")
            print(f"  - 文档标题: {summary['document_title']}")
            print(f"  - 总迭代次数: {summary['total_iterations']}")
            print(f"  - 审核迭代次数: {summary['review_iterations']}")
            print(f"  - 最终状态: {summary['final_status']}")
            print(f"  - HTML大小: {summary['html_size']} 字节")
            
            # 保存HTML文件
            if args.output:
                try:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        f.write(result["html_output"])
                    print(f"\n💾 HTML已保存到: {args.output}")
                except Exception as e:
                    print(f"\n❌ HTML文件保存失败: {e}")
            
            # 保存完整结果JSON
            if args.output_json:
                try:
                    with open(args.output_json, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    print(f"💾 完整结果已保存到: {args.output_json}")
                except Exception as e:
                    print(f"❌ JSON文件保存失败: {e}")
            
            print("\n✅ 处理完成")
            exit(0)
        else:
            print("\n" + "="*80)
            print("❌ 工作流执行失败")
            print("="*80)
            print(f"\n错误信息: {result.get('error_message', '未知错误')}")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ 执行异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

