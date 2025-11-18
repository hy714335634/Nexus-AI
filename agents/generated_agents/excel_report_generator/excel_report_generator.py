#!/usr/bin/env python3
"""
Excel智能报表生成Agent

专业的Excel数据分析与报表生成专家，能够自动分析Excel数据，生成专业的可视化图表和综合分析报告。
支持深度数据分析、多类型图表生成、HTML报告输出、幂等性保证、缓存管理等功能。

核心功能：
- Excel文件读取与解析（支持.xlsx, .xls格式）
- 数据深度分析（统计分析、趋势识别、相关性分析、异常检测）
- 报表策略智能制定
- 多类型图表生成（饼图、折线图、热图、柱状图、散点图）
- HTML综合报告生成
- 幂等性保证（相同输入产生一致输出）
- 缓存管理（会话隔离、文件复用）

技术栈：
- Strands SDK: Agent框架
- AWS Bedrock: AI模型推理（claude-sonnet-4-5）
- pandas: 数据处理
- matplotlib/seaborn: 图表生成
- openpyxl: Excel读取
- jinja2: HTML模板

作者：Agent Code Developer
版本：1.0.0
日期：2025-11-18
"""

import os
import sys
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# 导入Strands SDK和工具
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 导入自定义工具
from tools.generated_tools.excel_report_generator import (
    excel_data_reader,
    data_analyzer,
    generate_pie_chart,
    generate_line_chart,
    generate_heatmap,
    generate_bar_chart,
    generate_scatter_plot,
    html_report_builder,
    cache_manager
)

# 初始化缓存目录
CACHE_BASE_PATH = '.cache/excel_report_generator'
CACHE_DIR = Path(CACHE_BASE_PATH)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CACHE_DIR / 'agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("excel_report_generator")

# 设置环境变量
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"

# 初始化遥测
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()


class ExcelReportGeneratorAgent:
    """
    Excel报表生成Agent包装类
    
    提供完整的Excel数据分析和报表生成流程管理，包括：
    - 会话管理
    - 缓存管理
    - 流程协调
    - 错误处理
    - 进度跟踪
    """
    
    def __init__(
        self,
        env: str = "production",
        version: str = "latest",
        model_id: str = "default",
        enable_logging: bool = True
    ):
        """
        初始化Excel报表生成Agent
        
        Args:
            env: 运行环境（production/development）
            version: Agent版本
            model_id: 模型ID
            enable_logging: 是否启用日志
        """
        self.env = env
        self.version = version
        self.model_id = model_id
        self.enable_logging = enable_logging
        
        # 创建Agent实例
        agent_params = {
            "env": env,
            "version": version,
            "model_id": model_id,
            "enable_logging": enable_logging
        }
        
        try:
            self.agent = create_agent_from_prompt_template(
                agent_name="generated_agents_prompts/excel_report_generator/excel_report_generator",
                **agent_params
            )
            logger.info(f"✅ Excel Report Generator Agent初始化成功: {self.agent.name}")
        except Exception as e:
            logger.error(f"❌ Agent初始化失败: {str(e)}")
            raise RuntimeError(f"Agent初始化失败: {str(e)}")
        
        # 初始化会话状态
        self.session_id = None
        self.session_path = None
        self.processing_log = []
        
    def create_session(self) -> str:
        """
        创建新的会话
        
        Returns:
            session_id: 会话ID
        """
        try:
            self.session_id = str(uuid.uuid4())
            
            # 使用cache_manager创建会话目录
            result = cache_manager(
                operation="create_session",
                session_id=self.session_id,
                config={"base_path": CACHE_BASE_PATH}
            )
            
            if not result.get("success", False):
                raise RuntimeError(f"会话创建失败: {result.get('error', 'Unknown error')}")
            
            self.session_path = result.get("session_path")
            logger.info(f"✅ 会话创建成功: {self.session_id}")
            logger.info(f"📁 会话路径: {self.session_path}")
            
            self.processing_log.append({
                "step": "session_creation",
                "status": "success",
                "session_id": self.session_id,
                "session_path": self.session_path
            })
            
            return self.session_id
            
        except Exception as e:
            logger.error(f"❌ 会话创建失败: {str(e)}")
            self.processing_log.append({
                "step": "session_creation",
                "status": "error",
                "error": str(e)
            })
            raise
    
    def read_excel_file(self, file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        读取Excel文件
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称（可选）
            
        Returns:
            读取结果字典
        """
        try:
            logger.info(f"📖 正在读取Excel文件: {file_path}")
            
            # 验证文件存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 调用excel_data_reader工具
            result = excel_data_reader(
                file_path=file_path,
                sheet_name=sheet_name
            )
            
            if not result.get("success", False):
                raise RuntimeError(f"Excel读取失败: {result.get('error', 'Unknown error')}")
            
            logger.info(f"✅ Excel文件读取成功")
            logger.info(f"📊 数据行数: {result.get('metadata', {}).get('rows', 0)}")
            logger.info(f"📋 数据列数: {len(result.get('metadata', {}).get('columns', []))}")
            
            self.processing_log.append({
                "step": "excel_reading",
                "status": "success",
                "file_path": file_path,
                "metadata": result.get("metadata")
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Excel读取失败: {str(e)}")
            self.processing_log.append({
                "step": "excel_reading",
                "status": "error",
                "file_path": file_path,
                "error": str(e)
            })
            raise
    
    def analyze_data(self, df, analysis_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        分析数据
        
        Args:
            df: pandas DataFrame
            analysis_config: 分析配置
            
        Returns:
            分析结果字典
        """
        try:
            logger.info(f"🔍 正在进行数据分析...")
            
            # 调用data_analyzer工具
            result = data_analyzer(
                df=df,
                analysis_config=analysis_config
            )
            
            logger.info(f"✅ 数据分析完成")
            logger.info(f"📈 发现洞察数量: {len(result.get('insights', []))}")
            logger.info(f"⚠️ 异常值数量: {len(result.get('anomalies', []))}")
            
            self.processing_log.append({
                "step": "data_analysis",
                "status": "success",
                "insights_count": len(result.get('insights', [])),
                "anomalies_count": len(result.get('anomalies', []))
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 数据分析失败: {str(e)}")
            self.processing_log.append({
                "step": "data_analysis",
                "status": "error",
                "error": str(e)
            })
            raise
    
    def generate_charts(
        self,
        df,
        analysis_results: Dict[str, Any],
        user_requirements: str
    ) -> List[Dict[str, str]]:
        """
        生成图表
        
        Args:
            df: pandas DataFrame
            analysis_results: 分析结果
            user_requirements: 用户需求
            
        Returns:
            图表信息列表
        """
        try:
            logger.info(f"📊 正在生成图表...")
            
            chart_paths = []
            
            # 基于分析结果和用户需求确定图表策略
            # 这里简化处理，实际应该由Agent智能决策
            
            # 获取数据列信息
            columns = list(df.columns)
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            # 生成饼图（如果有分类数据）
            if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                try:
                    output_path = os.path.join(self.session_path, "pie_chart.png")
                    result = generate_pie_chart(
                        df=df,
                        category_col=categorical_cols[0],
                        value_col=numeric_cols[0],
                        title=f"{categorical_cols[0]}分布图",
                        output_path=output_path
                    )
                    
                    if result.get("success", False):
                        chart_paths.append({
                            "title": f"{categorical_cols[0]}分布图",
                            "path": output_path,
                            "description": f"展示{categorical_cols[0]}的分布情况"
                        })
                        logger.info(f"✅ 饼图生成成功")
                except Exception as e:
                    logger.warning(f"⚠️ 饼图生成失败: {str(e)}")
            
            # 生成折线图（如果有时间序列或趋势数据）
            if len(numeric_cols) >= 2:
                try:
                    output_path = os.path.join(self.session_path, "line_chart.png")
                    result = generate_line_chart(
                        df=df,
                        x_col=columns[0],
                        y_cols=numeric_cols[:3],  # 最多3条线
                        title="数据趋势图",
                        output_path=output_path
                    )
                    
                    if result.get("success", False):
                        chart_paths.append({
                            "title": "数据趋势图",
                            "path": output_path,
                            "description": "展示数据的变化趋势"
                        })
                        logger.info(f"✅ 折线图生成成功")
                except Exception as e:
                    logger.warning(f"⚠️ 折线图生成失败: {str(e)}")
            
            # 生成热图（如果有相关性数据）
            if len(numeric_cols) >= 3:
                try:
                    # 计算相关系数矩阵
                    corr_matrix = df[numeric_cols].corr()
                    output_path = os.path.join(self.session_path, "heatmap.png")
                    result = generate_heatmap(
                        data=corr_matrix,
                        title="相关性热图",
                        output_path=output_path
                    )
                    
                    if result.get("success", False):
                        chart_paths.append({
                            "title": "相关性热图",
                            "path": output_path,
                            "description": "展示变量间的相关性"
                        })
                        logger.info(f"✅ 热图生成成功")
                except Exception as e:
                    logger.warning(f"⚠️ 热图生成失败: {str(e)}")
            
            # 生成柱状图（如果有对比数据）
            if len(categorical_cols) > 0 and len(numeric_cols) > 0:
                try:
                    output_path = os.path.join(self.session_path, "bar_chart.png")
                    result = generate_bar_chart(
                        df=df,
                        x_col=categorical_cols[0],
                        y_col=numeric_cols[0],
                        title=f"{categorical_cols[0]} vs {numeric_cols[0]}",
                        output_path=output_path
                    )
                    
                    if result.get("success", False):
                        chart_paths.append({
                            "title": f"{categorical_cols[0]} vs {numeric_cols[0]}",
                            "path": output_path,
                            "description": f"对比不同{categorical_cols[0]}的{numeric_cols[0]}"
                        })
                        logger.info(f"✅ 柱状图生成成功")
                except Exception as e:
                    logger.warning(f"⚠️ 柱状图生成失败: {str(e)}")
            
            # 生成散点图（如果有两个数值变量）
            if len(numeric_cols) >= 2:
                try:
                    output_path = os.path.join(self.session_path, "scatter_plot.png")
                    result = generate_scatter_plot(
                        df=df,
                        x_col=numeric_cols[0],
                        y_col=numeric_cols[1],
                        title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
                        output_path=output_path
                    )
                    
                    if result.get("success", False):
                        chart_paths.append({
                            "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
                            "path": output_path,
                            "description": f"展示{numeric_cols[0]}和{numeric_cols[1]}的关系"
                        })
                        logger.info(f"✅ 散点图生成成功")
                except Exception as e:
                    logger.warning(f"⚠️ 散点图生成失败: {str(e)}")
            
            logger.info(f"✅ 图表生成完成，共生成 {len(chart_paths)} 个图表")
            
            self.processing_log.append({
                "step": "chart_generation",
                "status": "success",
                "charts_count": len(chart_paths)
            })
            
            return chart_paths
            
        except Exception as e:
            logger.error(f"❌ 图表生成失败: {str(e)}")
            self.processing_log.append({
                "step": "chart_generation",
                "status": "error",
                "error": str(e)
            })
            # 返回空列表而不是抛出异常，允许部分失败
            return []
    
    def build_html_report(
        self,
        title: str,
        summary: str,
        analysis_results: Dict[str, Any],
        chart_paths: List[Dict[str, str]],
        conclusions: str
    ) -> Dict[str, Any]:
        """
        构建HTML报告
        
        Args:
            title: 报告标题
            summary: 报告摘要
            analysis_results: 分析结果
            chart_paths: 图表路径列表
            conclusions: 结论和建议
            
        Returns:
            HTML报告生成结果
        """
        try:
            logger.info(f"📝 正在构建HTML报告...")
            
            output_path = os.path.join(self.session_path, "report.html")
            
            # 调用html_report_builder工具
            result = html_report_builder(
                title=title,
                summary=summary,
                analysis_results=analysis_results,
                chart_paths=chart_paths,
                conclusions=conclusions,
                output_path=output_path,
                metadata={
                    "session_id": self.session_id,
                    "generated_at": str(Path(output_path).stat().st_mtime) if os.path.exists(output_path) else None
                }
            )
            
            if not result.get("success", False):
                raise RuntimeError(f"HTML报告生成失败: {result.get('error', 'Unknown error')}")
            
            logger.info(f"✅ HTML报告生成成功")
            logger.info(f"📄 报告路径: {output_path}")
            
            self.processing_log.append({
                "step": "html_report_generation",
                "status": "success",
                "report_path": output_path
            })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ HTML报告生成失败: {str(e)}")
            self.processing_log.append({
                "step": "html_report_generation",
                "status": "error",
                "error": str(e)
            })
            raise
    
    def process_excel_report(
        self,
        file_path: str,
        user_requirements: str,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理Excel报表生成完整流程
        
        Args:
            file_path: Excel文件路径
            user_requirements: 用户需求描述
            sheet_name: 工作表名称（可选）
            
        Returns:
            处理结果字典
        """
        try:
            # 1. 创建会话
            session_id = self.create_session()
            
            # 2. 读取Excel文件
            excel_data = self.read_excel_file(file_path, sheet_name)
            df = excel_data.get("data")
            
            # 3. 数据分析
            analysis_results = self.analyze_data(df)
            
            # 4. 生成图表
            chart_paths = self.generate_charts(df, analysis_results, user_requirements)
            
            # 5. 构建HTML报告
            html_result = self.build_html_report(
                title=f"Excel数据分析报告 - {Path(file_path).name}",
                summary=f"基于用户需求：{user_requirements}",
                analysis_results=analysis_results,
                chart_paths=chart_paths,
                conclusions="基于以上分析，建议关注关键指标的变化趋势和异常值。"
            )
            
            # 6. 返回结果
            result = {
                "status": "success",
                "session_id": session_id,
                "html_report_path": html_result.get("file_path"),
                "generated_charts": chart_paths,
                "analysis_summary": {
                    "insights_count": len(analysis_results.get('insights', [])),
                    "anomalies_count": len(analysis_results.get('anomalies', [])),
                    "charts_count": len(chart_paths)
                },
                "processing_log": self.processing_log
            }
            
            logger.info(f"✅ Excel报表生成完成")
            logger.info(f"📊 会话ID: {session_id}")
            logger.info(f"📄 报告路径: {html_result.get('file_path')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Excel报表生成失败: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "processing_log": self.processing_log
            }
    
    def __call__(self, user_input: str) -> str:
        """
        Agent调用接口（通过提示词模板处理）
        
        Args:
            user_input: 用户输入
            
        Returns:
            Agent响应
        """
        try:
            # 调用底层Agent
            response = self.agent(user_input)
            
            # 解析响应
            if hasattr(response, 'content') and response.content:
                return response.content
            elif isinstance(response, str):
                return response
            elif hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"❌ Agent调用失败: {str(e)}")
            return f"处理失败: {str(e)}"


# 创建Agent工厂函数
def create_excel_report_generator_agent(
    env: str = "production",
    version: str = "latest",
    model_id: str = "default",
    enable_logging: bool = True
) -> ExcelReportGeneratorAgent:
    """
    创建Excel报表生成Agent实例
    
    Args:
        env: 运行环境
        version: Agent版本
        model_id: 模型ID
        enable_logging: 是否启用日志
        
    Returns:
        ExcelReportGeneratorAgent实例
    """
    return ExcelReportGeneratorAgent(
        env=env,
        version=version,
        model_id=model_id,
        enable_logging=enable_logging
    )


# 全局Agent实例
excel_report_generator = create_excel_report_generator_agent()


# 命令行接口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Excel智能报表生成Agent')
    parser.add_argument('-i', '--input', type=str,
                       default="请分析这个Excel文件并生成报告",
                       help='用户需求描述')
    parser.add_argument('-f', '--file', type=str,
                       help='Excel文件路径')
    parser.add_argument('-s', '--sheet', type=str,
                       help='工作表名称（可选）')
    parser.add_argument('-e', '--env', type=str,
                       default="production",
                       help='运行环境 (默认: production)')
    parser.add_argument('-v', '--version', type=str,
                       default="latest",
                       help='Agent版本 (默认: latest)')
    parser.add_argument('--process', action='store_true',
                       help='直接处理Excel文件（跳过对话模式）')
    args = parser.parse_args()
    
    # 创建Agent实例
    agent = create_excel_report_generator_agent(env=args.env, version=args.version)
    
    print(f"✅ Excel Report Generator Agent 创建成功: {agent.agent.name}")
    print(f"🎯 运行环境: {args.env}")
    print(f"📌 版本: {args.version}")
    
    # 处理模式选择
    if args.process and args.file:
        # 直接处理模式
        print(f"\n📊 处理模式: 直接处理Excel文件")
        print(f"📁 文件路径: {args.file}")
        print(f"📋 用户需求: {args.input}")
        
        result = agent.process_excel_report(
            file_path=args.file,
            user_requirements=args.input,
            sheet_name=args.sheet
        )
        
        print(f"\n{'='*60}")
        print(f"📊 处理结果:")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    else:
        # 对话模式
        print(f"\n💬 对话模式: 通过自然语言交互")
        print(f"🎯 测试输入: {args.input}")
        
        if args.file:
            test_input = f"{args.input}\n\nExcel文件路径: {args.file}"
            if args.sheet:
                test_input += f"\n工作表名称: {args.sheet}"
        else:
            test_input = args.input
        
        try:
            response = agent(test_input)
            print(f"\n{'='*60}")
            print(f"📋 Agent响应:")
            print(f"{'='*60}")
            print(response)
        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
