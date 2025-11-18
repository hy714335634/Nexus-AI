"""
多模态处理模块包

包含图像、文档、文本等多媒体内容的处理工具和服务
"""

# 只导入数据模型，避免循环依赖
from .models.data_models import *
from .models.exceptions import *
from .models.interfaces import *

# 延迟导入其他模块，避免循环依赖
def get_multimodal_model_service():
    """延迟导入MultimodalModelService"""
    from .multimodal_model_service import MultimodalModelService
    return MultimodalModelService

def get_content_parsing_engine():
    """延迟导入ContentParsingEngine"""
    from .content_parsing_engine import ContentParsingEngine
    return ContentParsingEngine

def get_document_processor():
    """延迟导入DocumentProcessor"""
    from .document_processor import DocumentProcessor
    return DocumentProcessor

def get_image_processor():
    """延迟导入ImageProcessor"""
    from .image_processor import ImageProcessor
    return ImageProcessor

def get_text_processor():
    """延迟导入TextProcessor"""
    from .text_processor import TextProcessor
    return TextProcessor

def get_markdown_generator():
    """延迟导入MarkdownGenerator"""
    from .markdown_generator import MarkdownGenerator
    return MarkdownGenerator

def get_s3_storage_service():
    """延迟导入S3StorageService"""
    from .s3_storage_service import S3StorageService
    return S3StorageService

def get_file_upload_manager():
    """延迟导入FileUploadManager"""
    from .file_upload_manager import FileUploadManager
    return FileUploadManager

def get_error_handler():
    """延迟导入ErrorHandler"""
    from .error_handler import ErrorHandler
    return ErrorHandler

__all__ = [
    # 数据模型
    'models',
    
    # 延迟导入函数
    'get_multimodal_model_service',
    'get_content_parsing_engine',
    'get_document_processor',
    'get_image_processor',
    'get_text_processor',
    'get_markdown_generator',
    'get_s3_storage_service',
    'get_file_upload_manager',
    'get_error_handler',
]
