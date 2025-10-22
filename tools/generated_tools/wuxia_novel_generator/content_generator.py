import json
import os
import boto3
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from strands import tool, Agent
from strands.models import BedrockModel

class ContentGenerator:
    """Content generation system for wuxia novel generation."""
    
    def __init__(self, cache_dir: str = ".cache/wuxia_novel_generator"):
        """Initialize the content generator."""
        self.cache_dir = cache_dir
        self.content_dir = os.path.join(cache_dir, "content")
        os.makedirs(self.content_dir, exist_ok=True)
    
    def _get_content_path(self, novel_id: str, chapter_id: str) -> str:
        """Get the path to a content file."""
        novel_dir = os.path.join(self.content_dir, novel_id)
        os.makedirs(novel_dir, exist_ok=True)
        return os.path.join(novel_dir, f"{chapter_id}.json")
    
    def save_chapter_content(self, novel_id: str, chapter_id: str, 
                           content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save chapter content."""
        now = datetime.now().isoformat()
        
        # Add metadata
        content = {
            "novel_id": novel_id,
            "chapter_id": chapter_id,
            "created_date": now,
            "last_updated": now,
            **content_data
        }
        
        # Save content to file
        file_path = self._get_content_path(novel_id, chapter_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        return content
    
    def get_chapter_content(self, novel_id: str, chapter_id: str) -> Optional[Dict[str, Any]]:
        """Get chapter content."""
        file_path = self._get_content_path(novel_id, chapter_id)
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def generate_chapter_content(self, novel_id: str, chapter_id: str, 
                               prompt: str, style: str = "traditional") -> Dict[str, Any]:
        """Generate chapter content using AWS Bedrock."""
        try:
            # Initialize Bedrock client
            bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
            
            # Prepare the prompt for content generation
            generation_prompt = f"""
            ########## 开始给定内容 ##########
            风格：{style}
            
            背景设定：
            {prompt}
            ########## 结束给定内容 ##########
            """
            
            bedrock_model = BedrockModel(
                model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                region_name="us-west-2",
                temperature=0.7,
                max_tokens=20000,
            )

            agent = Agent(
                model=bedrock_model,
                callback_handler=None,
                system_prompt=(
                    """
你是一个专业的武侠小说创作专家，请以经典武侠小说的风格创作一个详细、引人入胜的章节。
包含生动的描述、激烈的打斗场景和富有意义的对话。章节字数至少2000字。
**重要:**请直接输出小说内容，不要输出任何其他内容，不要输出任何解释。
请根据用户给定的内容和信息生成武侠小说章节，并确保生成的章节内容符合用户的要求。
                    """
                )
            )
            generated_content = agent(generation_prompt)
            
            # Save the generated content
            content_data = {
                "content": generated_content.message,
                "style": style,
                "prompt": prompt,
                "generation_method": "us.deepseek.r1-v1:0"
            }
            
            return self.save_chapter_content(novel_id, chapter_id, content_data)
        
        except Exception as e:
            # Fallback to simulated content for testing or when API is unavailable
            content_data = {
                "content": f"[Simulated chapter content due to API error: {str(e)}]",
                "style": style,
                "prompt": prompt,
                "generation_method": "us.deepseek.r1-v1:0"
            }
            
            return self.save_chapter_content(novel_id, chapter_id, content_data)

# Initialize the content generator
_content_generator = ContentGenerator()

@tool
def generate_chapter(novel_id: str, chapter_id: str, prompt: str, style: str = "traditional") -> str:
    """生成武侠小说章节内容。
    
    使用场景：当需要为特定章节生成详细内容时使用，适用于小说创作过程中的内容生成和扩展。
    建议条件：prompt应包含详细的章节事件、角色和场景描述，style选择应与小说整体风格保持一致。
    
    Args:
        novel_id: 小说ID
        chapter_id: 章节ID
        prompt: 详细描述章节事件、角色和场景的提示
        style: 写作风格（如"traditional", "modern", "poetic"）
    
    Returns:
        包含生成章节内容的JSON字符串
    """
    try:
        content = _content_generator.generate_chapter_content(novel_id, chapter_id, prompt, style)
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_chapter_content(novel_id: str, chapter_id: str) -> str:
    """获取武侠小说章节内容。
    
    使用场景：当需要查看已生成的章节内容时使用，适用于内容回顾、编辑修改或导出功能。
    建议条件：确保章节已生成内容，适用于需要查看或处理特定章节内容的场景。
    
    Args:
        novel_id: 小说ID
        chapter_id: 章节ID
    
    Returns:
        包含章节内容或错误信息的JSON字符串
    """
    try:
        content = _content_generator.get_chapter_content(novel_id, chapter_id)
        if content is None:
            return json.dumps({"error": "Chapter content not found"})
        return json.dumps(content, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    _content_generator = ContentGenerator()
    content = _content_generator.generate_chapter_content("f34a3cb0-7965-4062-afa7-cbda0febacee", "1", "这是一个测试章节")
    print(json.dumps(content, ensure_ascii=False))
    
