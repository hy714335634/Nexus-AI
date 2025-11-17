#!/usr/bin/env python3
"""
武侠小说生成Agent (wuxia_novel_generator)

专业的武侠小说创作专家，能够根据用户输入的设定（如人物、门派、武功、情节线索等）
自动生成符合武侠风格的小说内容，包括完整的故事情节、人物对话、武打场面描写等。

特点：
- 世界观一致性：维护统一的武侠世界观设定，确保前后文设定不冲突
- 情节连贯性：具备长期记忆能力，确保伏笔和铺垫在后续章节中呼应
- 武侠文体风格：语言风格符合武侠小说特点，武打场面描写生动
- 创意与套路平衡：遵循武侠小说经典套路的同时保持创新

集成工具：
- 角色管理工具：用于创建和管理角色信息
- 武功体系工具：用于定义和管理武功招式和内功心法
- 情节规划工具：用于设计故事大纲和章节结构
- 场景生成工具：用于生成不同场景的描写
- 对话生成工具：用于生成符合角色身份的对话
- 战斗编排工具：用于设计武打场面
- 小说缓存工具：用于管理本地缓存和检索功能
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("wuxia_novel_generator")

# 设置遥测
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# 设置缓存目录
CACHE_DIR = ".cache/wuxia_novel_generator"
os.makedirs(CACHE_DIR, exist_ok=True)

class WuxiaNovelGenerator:
    """武侠小说生成器类，封装主要功能和工作流程"""
    
    def __init__(self, agent_name: str = "generated_agents_prompts/wuxia_novel_generator/wuxia_novel_generator_prompt.yaml", 
                 env: str = "production", model_id: str = "default"):
        """
        初始化武侠小说生成器
        
        Args:
            agent_name: Agent提示词模板路径
            env: 环境设置 (development, production, testing)
            model_id: 使用的模型ID
        """
        self.agent_name = agent_name
        self.env = env
        self.model_id = model_id
        self.agent = None
        self.current_novel_id = None
        self.current_novel_info = None
        
        # 初始化Agent
        self._initialize_agent()
        
    def _initialize_agent(self) -> None:
        """初始化Agent实例"""
        try:
            logger.info(f"正在初始化武侠小说生成Agent: {self.agent_name}")
            
            agent_params = {
                "env": self.env,
                "version": "latest",
                "model_id": self.model_id,
                "enable_logging": True
            }
            
            self.agent = create_agent_from_prompt_template(
                agent_name=self.agent_name,
                **agent_params
            )
            
            logger.info(f"武侠小说生成Agent初始化成功")
        except Exception as e:
            logger.error(f"初始化Agent失败: {str(e)}")
            raise
    
    def _load_novel_info(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        加载小说信息
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说信息字典，如果不存在则返回None
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.novel_manager import get_novel
            novel_info = json.loads(get_novel(novel_id))
            
            if "error" in novel_info:
                logger.warning(f"加载小说信息失败: {novel_info['error']}")
                return None
                
            return novel_info
        except Exception as e:
            logger.error(f"加载小说信息时出错: {str(e)}")
            return None
    
    def create_new_novel(self, title: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新的武侠小说
        
        Args:
            title: 小说标题
            settings: 小说设定，包括时代背景、主要人物、核心情节等
            
        Returns:
            创建的小说信息
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.novel_manager import create_novel
            
            # 准备小说基本信息
            novel_data = {
                "title": title,
                "author": "武侠小说生成Agent",
                "created_date": datetime.now().isoformat(),
                "settings": settings,
                "chapters": []
            }
            
            # 创建小说
            result = json.loads(create_novel(novel_data))
            
            if "error" in result:
                logger.error(f"创建小说失败: {result['error']}")
                raise ValueError(result["error"])
            
            # 保存当前小说ID和信息
            self.current_novel_id = result["id"]
            self.current_novel_info = result
            
            logger.info(f"成功创建小说: {title} (ID: {self.current_novel_id})")
            
            # 创建世界观设定
            self._create_world_setting(settings)
            
            return result
        except Exception as e:
            logger.error(f"创建小说时出错: {str(e)}")
            raise
    
    def _create_world_setting(self, settings: Dict[str, Any]) -> None:
        """
        创建世界观设定
        
        Args:
            settings: 小说设定
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.worldbuilding_manager import create_or_update_world
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            # 准备世界观数据
            world_data = {
                "era": settings.get("era", "未指定时代"),
                "background": settings.get("background", ""),
                "major_events": settings.get("major_events", []),
                "locations": settings.get("locations", []),
                "factions": settings.get("factions", [])
            }
            
            # 创建世界观
            result = json.loads(create_or_update_world(self.current_novel_id, world_data))
            
            if "error" in result:
                logger.warning(f"创建世界观设定失败: {result['error']}")
            else:
                logger.info(f"成功创建世界观设定")
        except Exception as e:
            logger.warning(f"创建世界观设定时出错: {str(e)}")
    
    def load_novel(self, novel_id: str) -> Dict[str, Any]:
        """
        加载已有小说
        
        Args:
            novel_id: 小说ID
            
        Returns:
            小说信息
        """
        novel_info = self._load_novel_info(novel_id)
        
        if not novel_info:
            raise ValueError(f"找不到ID为 {novel_id} 的小说")
        
        self.current_novel_id = novel_id
        self.current_novel_info = novel_info
        
        logger.info(f"成功加载小说: {novel_info['title']} (ID: {novel_id})")
        
        return novel_info
    
    def list_novels(self) -> List[Dict[str, Any]]:
        """
        列出所有小说
        
        Returns:
            小说列表
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.novel_manager import list_novels
            
            result = json.loads(list_novels())
            
            if "error" in result:
                logger.error(f"获取小说列表失败: {result['error']}")
                return []
            
            return result
        except Exception as e:
            logger.error(f"获取小说列表时出错: {str(e)}")
            return []
    
    def create_character(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建角色
        
        Args:
            character_data: 角色数据，包括姓名、性别、年龄、门派等
            
        Returns:
            创建的角色信息
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.character_tools import create_character
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            # 创建角色
            result = json.loads(create_character(self.current_novel_id, character_data))
            
            if "error" in result:
                logger.error(f"创建角色失败: {result['error']}")
                raise ValueError(result["error"])
            
            logger.info(f"成功创建角色: {character_data.get('name', 'unnamed')}")
            
            return result
        except Exception as e:
            logger.error(f"创建角色时出错: {str(e)}")
            raise
    
    def list_characters(self) -> List[Dict[str, Any]]:
        """
        列出当前小说的所有角色
        
        Returns:
            角色列表
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.character_search import list_characters
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            result = json.loads(list_characters(self.current_novel_id))
            
            if isinstance(result, dict) and "error" in result:
                logger.error(f"获取角色列表失败: {result['error']}")
                return []
            
            return result
        except Exception as e:
            logger.error(f"获取角色列表时出错: {str(e)}")
            return []
    
    def create_plot(self, plot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建情节大纲
        
        Args:
            plot_data: 情节数据，包括主线情节、支线情节、转折点等
            
        Returns:
            创建的情节信息
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.plot_base import create_plot
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            # 准备情节数据
            plot_info = {
                "novel_id": self.current_novel_id,
                **plot_data
            }
            
            # 创建情节
            result = json.loads(create_plot(plot_info))
            
            if "error" in result:
                logger.error(f"创建情节大纲失败: {result['error']}")
                raise ValueError(result["error"])
            
            logger.info(f"成功创建情节大纲")
            
            return result
        except Exception as e:
            logger.error(f"创建情节大纲时出错: {str(e)}")
            raise
    
    def generate_chapter(self, chapter_id: str, prompt: str, style: str = "traditional") -> Dict[str, Any]:
        """
        生成章节内容
        
        Args:
            chapter_id: 章节ID
            prompt: 章节提示，描述章节的事件、角色和场景
            style: 写作风格，如"traditional"（传统）、"modern"（现代）等
            
        Returns:
            生成的章节内容
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.content_generator import generate_chapter
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            # 生成章节内容
            result = json.loads(generate_chapter(self.current_novel_id, chapter_id, prompt, style))
            
            if "error" in result:
                logger.error(f"生成章节内容失败: {result['error']}")
                raise ValueError(result["error"])
            
            logger.info(f"成功生成章节内容: {chapter_id}")
            
            # 添加章节到小说
            self._add_chapter_to_novel(chapter_id, result)
            
            return result
        except Exception as e:
            logger.error(f"生成章节内容时出错: {str(e)}")
            raise
    
    def _add_chapter_to_novel(self, chapter_id: str, chapter_content: Dict[str, Any]) -> None:
        """
        将章节添加到小说
        
        Args:
            chapter_id: 章节ID
            chapter_content: 章节内容
        """
        try:
            from tools.generated_tools.wuxia_novel_generator.plot_chapters import add_chapter
            
            if not self.current_novel_id:
                raise ValueError("未指定当前小说")
            
            # 准备章节数据
            chapter_data = {
                "chapter_id": chapter_id,
                "title": f"第{len(self.current_novel_info.get('chapters', [])) + 1}章",
                "content_summary": chapter_content.get("content", "")[:200] + "...",
                "created_date": datetime.now().isoformat()
            }
            
            # 添加章节
            result = json.loads(add_chapter(self.current_novel_id, chapter_data))
            
            if "error" in result:
                logger.warning(f"添加章节到小说失败: {result['error']}")
            else:
                # 更新当前小说信息
                self.current_novel_info = self._load_novel_info(self.current_novel_id)
                logger.info(f"成功添加章节到小说")
        except Exception as e:
            logger.warning(f"添加章节到小说时出错: {str(e)}")
    
    def export_novel(self, format: str = "markdown") -> str:
        """
        导出小说
        
        Args:
            format: 导出格式，支持"markdown"和"json"
            
        Returns:
            导出的文件路径
        """
        try:
            if format == "markdown":
                from tools.generated_tools.wuxia_novel_generator.export_tools import export_novel_to_markdown
                
                if not self.current_novel_id:
                    raise ValueError("未指定当前小说")
                
                result = json.loads(export_novel_to_markdown(self.current_novel_id))
                
                if "error" in result:
                    logger.error(f"导出小说失败: {result['error']}")
                    raise ValueError(result["error"])
                
                logger.info(f"成功导出小说为Markdown格式: {result['file_path']}")
                
                return result["file_path"]
            elif format == "json":
                from tools.generated_tools.wuxia_novel_generator.export_tools import export_novel_to_json
                
                if not self.current_novel_id:
                    raise ValueError("未指定当前小说")
                
                result = json.loads(export_novel_to_json(self.current_novel_id))
                
                if "error" in result:
                    logger.error(f"导出小说失败: {result['error']}")
                    raise ValueError(result["error"])
                
                logger.info(f"成功导出小说为JSON格式: {result['file_path']}")
                
                return result["file_path"]
            else:
                raise ValueError(f"不支持的导出格式: {format}")
        except Exception as e:
            logger.error(f"导出小说时出错: {str(e)}")
            raise
    
    def process_user_input(self, user_input: str) -> str:
        """
        处理用户输入，调用Agent生成响应
        
        Args:
            user_input: 用户输入的文本
            
        Returns:
            Agent的响应
        """
        try:
            # 如果有当前小说，添加到上下文
            context = ""
            if self.current_novel_id and self.current_novel_info:
                context = f"当前小说: {self.current_novel_info['title']} (ID: {self.current_novel_id})\n\n"
            
            # 调用Agent处理用户输入
            response = self.agent(context + user_input)
            
            return response
        except Exception as e:
            logger.error(f"处理用户输入时出错: {str(e)}")
            return f"处理您的请求时出错: {str(e)}"


# 创建全局实例
wuxia_generator = None

def get_wuxia_generator(env: str = "production", model_id: str = "default") -> WuxiaNovelGenerator:
    """
    获取或创建武侠小说生成器实例
    
    Args:
        env: 环境设置
        model_id: 模型ID
        
    Returns:
        武侠小说生成器实例
    """
    global wuxia_generator
    
    if wuxia_generator is None:
        wuxia_generator = WuxiaNovelGenerator(env=env, model_id=model_id)
    
    return wuxia_generator


if __name__ == "__main__":
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='武侠小说生成Agent')
    parser.add_argument('-e', '--env', type=str, default="production",
                        choices=["development", "production", "testing"],
                        help='运行环境 (development, production, testing)')
    parser.add_argument('-m', '--model', type=str, default="default",
                        help='使用的模型ID')
    parser.add_argument('-i', '--input', type=str,
                        default="请帮我创作一部以明朝为背景的武侠小说，主角是一位精通轻功的女侠。",
                        help='测试输入内容')
    args = parser.parse_args()
    
    # 初始化生成器
    generator = get_wuxia_generator(env=args.env, model_id=args.model)
    
    print(f"✅ 武侠小说生成Agent初始化成功")
    print(f"🎯 测试输入: {args.input}")
    
    try:
        # 处理用户输入
        result = generator.process_user_input(args.input)
        print(f"📋 Agent响应:\n{result}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")