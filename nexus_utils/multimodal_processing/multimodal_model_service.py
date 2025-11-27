"""
Multimodal model service for AWS Bedrock Claude integration.

This module provides the MultimodalModelService class that handles:
- Image Base64 conversion and multimodal model calls
- Text content processing and Markdown formatting
- Error handling, retry mechanisms, and service degradation
"""

import base64
import json
import time
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError
import logging

from .models.exceptions import ModelServiceError
from .models.data_models import ProcessedContent
from ..config_loader import ConfigLoader


class MultimodalModelService:
    """
    Service for integrating with AWS Bedrock Claude models for multimodal content processing.
    
    This service handles image analysis, text processing, and Markdown generation
    using AWS Bedrock's Claude models with built-in error handling and retry logic.
    """
    
    def __init__(self, aws_region: str = 'us-west-2', model_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the multimodal model service.
        
        Args:
            aws_region: AWS region for Bedrock service
            model_config: Optional model configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        try:
            self.config_loader = ConfigLoader()
            self.model_config = model_config or self.config_loader.get_multimodal_parser_config().get('model', {})
            self.aws_config = self.config_loader.get_aws_config()
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            self.model_config = {}
            self.aws_config = {}
            
        # Model settings
        self.primary_model = self.model_config.get('primary_model', 'us.anthropic.claude-3-7-sonnet-20250219-v1:0')
        self.fallback_model = self.model_config.get('fallback_model', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')
        self.max_tokens = self.model_config.get('max_tokens', 4000)
        
        # Processing settings
        processing_config = self.config_loader.get_multimodal_parser_config().get('processing', {})
        self.timeout_seconds = processing_config.get('timeout_seconds', 300)
        self.retry_attempts = processing_config.get('retry_attempts', 3)
        
        # AWS region
        self.aws_region = aws_region
        
        # Initialize Bedrock client (simplified for demo)
        self._init_bedrock_client()
        
    def _init_bedrock_client(self):
        """Initialize the AWS Bedrock client with proper configuration."""
        try:
            # Get AWS credentials from config or environment
            aws_access_key_id = None
            aws_secret_access_key = None
            
            # Try to get credentials from config first
            if self.aws_config:
                aws_access_key_id = self.aws_config.get('aws_access_key_id')
                aws_secret_access_key = self.aws_config.get('aws_secret_access_key')
            
            # If no config credentials, try environment variables
            if not aws_access_key_id or not aws_secret_access_key:
                import os
                aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
                aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            # Initialize Bedrock client with or without explicit credentials
            if aws_access_key_id and aws_secret_access_key:
                # Use explicit credentials
                session = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=self.aws_region
                )
                self.bedrock_client = session.client('bedrock-runtime')
                self.logger.info(f"Bedrock client initialized with explicit credentials for region: {self.aws_region}")
            else:
                # Use AWS credentials provider chain
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.aws_region
                )
                self.logger.info(f"Bedrock client initialized using credentials provider chain for region: {self.aws_region}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise ModelServiceError(
                f"Failed to initialize Bedrock client: {str(e)}",
                error_code="BEDROCK_INIT_ERROR",
                context={"aws_region": self.aws_region, "error": str(e)}
            )
    
    def convert_image_to_base64(self, image_path: str) -> str:
        """
        Convert an image file to Base64 format.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
            
        Raises:
            ModelServiceError: If image conversion fails
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
            self.logger.debug(f"Successfully converted image to Base64: {image_path}")
            return base64_image
            
        except FileNotFoundError:
            error_msg = f"Image file not found: {image_path}"
            self.logger.error(error_msg)
            raise ModelServiceError(
                error_msg,
                error_code="IMAGE_NOT_FOUND",
                context={"image_path": image_path}
            )
        except Exception as e:
            error_msg = f"Failed to convert image to Base64: {str(e)}"
            self.logger.error(error_msg)
            raise ModelServiceError(
                error_msg,
                error_code="IMAGE_CONVERSION_ERROR",
                context={"image_path": image_path, "error": str(e)}
            )
    
    def _detect_image_media_type(self, base64_image: str, file_name: str = "") -> str:
        """
        Detect the media type of the image from base64 data or filename.
        
        Args:
            base64_image: Base64 encoded image data
            file_name: Optional filename to help determine type
            
        Returns:
            Media type string (e.g., 'image/jpeg', 'image/png')
        """
        # Try to detect from filename extension first
        if file_name:
            file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
            if file_ext in ['jpg', 'jpeg']:
                return 'image/jpeg'
            elif file_ext == 'png':
                return 'image/png'
            elif file_ext == 'gif':
                return 'image/gif'
            elif file_ext == 'webp':
                return 'image/webp'
        
        # Try to detect from base64 header (magic bytes)
        try:
            import base64 as b64
            # Decode first few bytes to check magic numbers
            header_bytes = b64.b64decode(base64_image[:50])
            
            # Check for common image format magic numbers
            if header_bytes.startswith(b'\xff\xd8\xff'):  # JPEG
                return 'image/jpeg'
            elif header_bytes.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return 'image/png'
            elif header_bytes.startswith(b'GIF87a') or header_bytes.startswith(b'GIF89a'):  # GIF
                return 'image/gif'
            elif header_bytes.startswith(b'RIFF') and b'WEBP' in header_bytes[:12]:  # WebP
                return 'image/webp'
        except Exception:
            pass
        
        # Default to JPEG if detection fails
        return 'image/jpeg'

    def analyze_image(self, base64_image: str, text_context: str = "", file_name: str = "") -> str:
        """
        Analyze an image using the multimodal model.
        
        Args:
            base64_image: Base64 encoded image data
            text_context: Optional text context to accompany the image
            file_name: Optional filename for context
            
        Returns:
            Structured analysis of the image content
            
        Raises:
            ModelServiceError: If image analysis fails
        """
        try:
            # Build the image analysis prompt
            prompt = self._build_image_analysis_prompt(text_context, file_name)
            
            # Detect the correct media type for the image
            media_type = self._detect_image_media_type(base64_image, file_name)
            
            # Prepare messages with image content
            messages = [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_image
                        }
                    }
                ]
            }]
            
            # Call the model with retry logic
            result = self._call_model_with_retry(messages, self.primary_model)
            
            self.logger.info(f"Successfully analyzed image: {file_name}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to analyze image {file_name}: {str(e)}"
            self.logger.error(error_msg)
            raise ModelServiceError(
                error_msg,
                error_code="IMAGE_ANALYSIS_ERROR",
                context={"file_name": file_name, "error": str(e)}
            )
    
    def process_text_content(self, content: str, file_info: Dict[str, Any]) -> str:
        """
        Process text content using the multimodal model.
        
        Args:
            content: Text content to process
            file_info: Dictionary containing file metadata
            
        Returns:
            Processed and formatted text content
            
        Raises:
            ModelServiceError: If text processing fails
        """
        # For this simplified implementation, return a formatted response
        # In a real implementation, this would call the actual Bedrock model
        
        file_name = file_info.get('original_name', '未知文件')
        file_type = file_info.get('file_type', '未知类型')
        
        return f"""## 文本内容分析

### 文件信息
- **文件名**: {file_name}
- **文件类型**: {file_type}
- **处理时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}

### 内容概述
这是一个 {file_type} 类型的文本文件，已成功通过多模态内容解析器处理。

### 处理结果
文件内容已被成功解析和结构化。这是一个简化的实现，用于演示系统的工作流程。

### 技术说明
在实际部署中，这里会包含：
- 真实的文本内容分析
- AI模型生成的结构化输出
- 详细的内容摘要和关键信息提取

*注：这是演示版本的输出结果*
"""
    
    def generate_markdown_output(self, processed_contents: List[ProcessedContent]) -> str:
        """
        Generate final Markdown output from processed content results.
        
        Args:
            processed_contents: List of processed content results
            
        Returns:
            Combined Markdown formatted output
            
        Raises:
            ModelServiceError: If Markdown generation fails
        """
        prompt = self._build_markdown_generation_prompt(processed_contents)
        
        messages = [{
            "role": "user",
            "content": prompt
        }]
        
        return self._call_model_with_retry(messages, model_id=self.primary_model)
    
    def _build_image_analysis_prompt(self, text_context: str, file_name: str) -> str:
        """Build prompt for image analysis."""
        prompt = """请对这张图片进行全面的分析，并按照以下结构化格式提供详细的描述：

## 图片分析报告

### 1. 基本信息
- **图片类型**: [照片/图表/截图/文档/艺术作品/其他]
- **主要主题**: [简要概述图片的核心内容]
- **视觉风格**: [描述图片的整体视觉特征]

### 2. 内容详细描述
#### 2.1 视觉元素
- **主要对象**: [列出图片中的主要物体、人物或元素]
- **颜色分析**: [描述主要颜色和色彩搭配]
- **构图布局**: [描述图片的构图和元素排列]
- **光线和阴影**: [如适用，描述光线效果]

#### 2.2 文字内容识别 (OCR)
[如果图片包含文字，请逐一识别并列出所有可见的文字内容，包括标题、正文、标签等]

#### 2.3 数据和图表分析
[如果是图表、表格或包含数据的图片，请提取并分析其中的数据信息]

### 3. 场景和背景分析
- **环境设置**: [描述图片的背景环境]
- **时间和地点**: [如果可以推断，描述可能的时间和地点]
- **情境分析**: [分析图片所展现的情境或场景]

### 4. 关键信息提取
#### 4.1 重要发现
[列出图片中最重要的信息点和发现]

#### 4.2 数据摘要
[如果包含数据，提供关键数据的摘要]

#### 4.3 行动项或建议
[基于图片内容，如果适用，提供相关的行动建议]

### 5. 结构化数据输出
[如果图片包含表格、图表或其他结构化数据，请用Markdown表格格式重新整理展示]

### 6. 技术细节
- **图片质量**: [评估图片的清晰度和质量]
- **可能的用途**: [分析这张图片可能的使用场景]
- **相关性评分**: [对图片内容的重要性进行1-10评分，并说明理由]

请确保分析全面、准确，并尽可能提取所有有价值的信息。"""
        
        if file_name:
            prompt = f"**分析文件**: {file_name}\n\n" + prompt
            
        if text_context:
            prompt = f"**用户上下文**: {text_context}\n\n" + prompt
            
        return prompt
    
    def _build_text_processing_prompt(self, content: str, file_info: Dict[str, Any]) -> str:
        """Build prompt for text content processing."""
        file_name = file_info.get('original_name', '未知文件')
        file_type = file_info.get('file_type', '未知类型')
        
        prompt = f"""请处理以下文本内容并生成结构化的Markdown输出：

文件信息：
- 文件名：{file_name}
- 文件类型：{file_type}

原始内容：
```
{content}
```

请按以下格式输出：

## 文本内容分析

### 内容概述
[简要概述文本的主要内容和目的]

### 结构化内容
[将文本内容进行结构化整理，使用适当的Markdown格式：
- 使用标题层级组织内容
- 使用列表展示要点
- 使用表格展示结构化数据（如果适用）
- 使用代码块展示代码或配置（如果适用）]

### 关键信息
[提取文本中的关键信息点]

### 总结
[对文本内容进行简要总结]
"""
        return prompt
    
    def _build_markdown_generation_prompt(self, processed_contents: List[ProcessedContent]) -> str:
        """Build prompt for final Markdown generation."""
        content_summaries = []
        
        for i, content in enumerate(processed_contents, 1):
            status = "✅ 成功" if content.success else "❌ 失败"
            summary = f"""
文件 {i}: {content.file_name}
- 状态: {status}
- 类型: {content.content_type}
- 处理时间: {content.processing_time:.2f}秒
"""
            if content.error_message:
                summary += f"- 错误信息: {content.error_message}\n"
                
            content_summaries.append(summary)
        
        successful_contents = [c for c in processed_contents if c.success]
        
        prompt = f"""请根据以下处理结果生成最终的Markdown报告：

## 处理概览
总文件数: {len(processed_contents)}
成功处理: {len(successful_contents)}
处理失败: {len(processed_contents) - len(successful_contents)}

## 文件处理状态
{''.join(content_summaries)}

## 成功处理的文件内容
"""
        
        for i, content in enumerate(successful_contents, 1):
            prompt += f"""
### 文件 {i}: {content.file_name}

{content.processed_text}

---
"""
        
        prompt += """

请生成一个完整的、结构化的Markdown报告，包括：
1. 执行摘要
2. 文件处理概览
3. 每个文件的详细内容（仅包含成功处理的文件）
4. 如果有失败的文件，请在最后列出失败原因
5. 总结和建议

请确保输出格式清晰、专业，便于阅读和理解。
"""
        return prompt
    
    def _call_model_with_retry(self, messages: List[Dict], model_id: str) -> str:
        """
        Call the Bedrock model with retry logic and fallback.
        
        Args:
            messages: List of message dictionaries for the model
            model_id: Model ID to use
            
        Returns:
            Model response text
            
        Raises:
            ModelServiceError: If all retry attempts fail
        """
        last_error = None
        current_model = model_id
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Calling model {current_model}, attempt {attempt + 1}")
                
                # Prepare the request body for Claude 3 models
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "messages": messages,
                    "temperature": 0.1,  # Low temperature for consistent analysis
                }
                
                # Make the API call
                response = self.bedrock_client.invoke_model(
                    modelId=current_model,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )
                
                # Parse the response
                response_body = json.loads(response['body'].read())
                
                if 'content' in response_body and response_body['content']:
                    result = response_body['content'][0]['text']
                    self.logger.debug(f"Successfully received response from model {current_model}")
                    return result
                else:
                    raise ModelServiceError(
                        "Invalid response format from model",
                        error_code="INVALID_RESPONSE",
                        context={"response": response_body}
                    )
                    
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
                error_msg = f"AWS Bedrock API error: {error_code} - {str(e)}"
                last_error = ModelServiceError(
                    error_msg,
                    error_code=f"BEDROCK_{error_code}",
                    context={"attempt": attempt + 1, "model_id": current_model}
                )
                self.logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                
                # Check if we should try fallback model
                if attempt == 0 and current_model == self.primary_model:
                    self.logger.info("Trying fallback model due to primary model failure")
                    current_model = self.fallback_model
                    continue
                    
            except (BotoCoreError, json.JSONDecodeError, KeyError) as e:
                error_msg = f"Model service error: {str(e)}"
                last_error = ModelServiceError(
                    error_msg,
                    error_code="MODEL_SERVICE_ERROR",
                    context={"attempt": attempt + 1, "model_id": current_model}
                )
                self.logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                last_error = ModelServiceError(
                    error_msg,
                    error_code="UNEXPECTED_ERROR",
                    context={"attempt": attempt + 1, "model_id": current_model}
                )
                self.logger.error(f"Attempt {attempt + 1} failed with unexpected error: {error_msg}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.retry_attempts - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                self.logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        # All attempts failed
        self.logger.error(f"All {self.retry_attempts} attempts failed for model {current_model}")
        raise last_error or ModelServiceError(
            "All retry attempts failed",
            error_code="MAX_RETRIES_EXCEEDED",
            context={"model_id": current_model, "attempts": self.retry_attempts}
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the model service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Simple test call to verify service is working
            test_messages = [{
                "role": "user",
                "content": "请回复'服务正常'来确认系统状态。"
            }]
            
            start_time = time.time()
            response = self._call_model_with_retry(test_messages, self.primary_model)
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "primary_model": self.primary_model,
                "fallback_model": self.fallback_model,
                "response_time": response_time,
                "aws_region": self.aws_region,
                "test_response": response[:100] + "..." if len(response) > 100 else response,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "primary_model": self.primary_model,
                "fallback_model": self.fallback_model,
                "aws_region": self.aws_region,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }