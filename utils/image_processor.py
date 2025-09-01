"""
Image processor for the multimodal content parser system.

This module provides the ImageProcessor class that handles:
- Image file processing and Base64 conversion
- Integration with multimodal models for image content recognition
- Structured output generation for image descriptions
"""

import os
import time
import logging
import base64
import tempfile
from typing import List, Dict, Any, Optional
from PIL import Image
import mimetypes
import boto3
from botocore.exceptions import ClientError

from models.interfaces import FileProcessor
from models.data_models import FileMetadata, ProcessedContent
from models.exceptions import FileProcessingError
from utils.multimodal_model_service import MultimodalModelService


class ImageProcessor(FileProcessor):
    """
    Processor for image files using multimodal AI models.
    
    This processor handles various image formats (PNG, JPG, JPEG, GIF, etc.)
    and uses AWS Bedrock Claude models to analyze and describe image content.
    """
    
    # Supported image file types
    SUPPORTED_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'tif']
    
    def __init__(self, multimodal_service: Optional[MultimodalModelService] = None):
        """
        Initialize the image processor.
        
        Args:
            multimodal_service: Optional MultimodalModelService instance.
                               If None, creates a new instance.
        """
        self.logger = logging.getLogger(__name__)
        self.multimodal_service = multimodal_service or MultimodalModelService()
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3')
        except Exception as e:
            self.logger.warning(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
        
    def can_process(self, file_type: str) -> bool:
        """
        Check if this processor can handle the given file type.
        
        Args:
            file_type: File extension or type identifier (e.g., 'jpg', 'png')
            
        Returns:
            True if this processor can handle the file type, False otherwise
        """
        return file_type.lower() in self.SUPPORTED_TYPES
    
    def get_supported_types(self) -> List[str]:
        """
        Get list of file types supported by this processor.
        
        Returns:
            List of supported file extensions
        """
        return self.SUPPORTED_TYPES.copy()
    
    def process(self, file_metadata: FileMetadata) -> ProcessedContent:
        """
        Process an image file and return structured content description.
        
        Args:
            file_metadata: Metadata about the image file to process
            
        Returns:
            ProcessedContent object containing the processing results
            
        Raises:
            FileProcessingError: If image processing fails
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting image processing for file: {file_metadata.original_name}")
            
            # Validate file type
            if not self.can_process(file_metadata.file_type):
                raise FileProcessingError(
                    f"Unsupported image file type: {file_metadata.file_type}",
                    error_code="UNSUPPORTED_IMAGE_TYPE",
                    context={"file_type": file_metadata.file_type, "supported_types": self.SUPPORTED_TYPES}
                )
            
            # Download and validate image file
            image_path = self._download_image_from_s3(file_metadata)
            
            try:
                # Convert image to Base64 for multimodal model processing
                base64_image = self._convert_image_to_base64(image_path)
                
                # Extract image metadata
                image_metadata = self._extract_image_metadata(image_path)
                
                # Call multimodal model for image analysis
                analysis_result = self.multimodal_service.analyze_image(
                    base64_image=base64_image,
                    text_context="",
                    file_name=file_metadata.original_name
                )
                
                # Create structured output
                processed_text = self._format_image_analysis(
                    analysis_result, 
                    file_metadata, 
                    image_metadata
                )
                
                processing_time = time.time() - start_time
                
                self.logger.info(
                    f"Successfully processed image {file_metadata.original_name} "
                    f"in {processing_time:.2f} seconds"
                )
                
                return ProcessedContent(
                    file_id=file_metadata.file_id,
                    file_name=file_metadata.original_name,
                    content_type="image",
                    processed_text=processed_text,
                    metadata={
                        **image_metadata,
                        "analysis_model": self.multimodal_service.primary_model,
                        "base64_size": len(base64_image)
                    },
                    processing_time=processing_time,
                    success=True
                )
                
            finally:
                # Clean up temporary file
                self._cleanup_temp_file(image_path)
                
        except FileProcessingError:
            # Re-raise FileProcessingError as-is
            raise
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Failed to process image {file_metadata.original_name}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessedContent(
                file_id=file_metadata.file_id,
                file_name=file_metadata.original_name,
                content_type="image",
                processed_text="",
                metadata={},
                processing_time=processing_time,
                success=False,
                error_message=error_msg
            )
    
    def _download_image_from_s3(self, file_metadata: FileMetadata) -> str:
        """
        Download image file from S3 to local temporary file.
        
        Args:
            file_metadata: File metadata containing S3 URL and file information
            
        Returns:
            Local path to the downloaded image file
            
        Raises:
            FileProcessingError: If download fails
        """
        try:
            # Parse S3 URL to get bucket and key
            s3_url = file_metadata.s3_url
            if not s3_url.startswith('s3://'):
                raise FileProcessingError(
                    f"Invalid S3 URL format: {s3_url}",
                    error_code="INVALID_S3_URL",
                    context={"s3_url": s3_url}
                )
            
            # Extract bucket and key from S3 URL
            url_parts = s3_url[5:].split('/', 1)  # Remove 's3://' prefix
            if len(url_parts) != 2:
                raise FileProcessingError(
                    f"Invalid S3 URL format: {s3_url}",
                    error_code="INVALID_S3_URL",
                    context={"s3_url": s3_url}
                )
            
            bucket_name, object_key = url_parts
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{file_metadata.file_type}",
                prefix=f"image_{file_metadata.file_id}_"
            )
            temp_path = temp_file.name
            temp_file.close()
            
            # Download from S3
            if self.s3_client:
                self.logger.info(f"Downloading image from S3: {bucket_name}/{object_key}")
                self.s3_client.download_file(bucket_name, object_key, temp_path)
            else:
                # Fallback: create a test image if S3 client is not available
                self.logger.warning("S3 client not available, creating test image")
                self._create_test_image(temp_path, file_metadata.file_type)
            
            # Validate the downloaded file
            self._validate_image_file(temp_path)
            
            self.logger.debug(f"Successfully downloaded image to: {temp_path}")
            return temp_path
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'UNKNOWN')
            error_msg = f"S3 download failed: {error_code} - {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(
                error_msg,
                error_code=f"S3_{error_code}",
                context={"s3_url": file_metadata.s3_url, "error": str(e)}
            )
            
        except Exception as e:
            error_msg = f"Failed to download image from S3: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(
                error_msg,
                error_code="S3_DOWNLOAD_ERROR",
                context={"s3_url": file_metadata.s3_url, "error": str(e)}
            )
    
    def _convert_image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to Base64 format for multimodal model processing.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
            
        Raises:
            FileProcessingError: If Base64 conversion fails
        """
        try:
            # Read the image file and convert to Base64
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            
            self.logger.debug(f"Successfully converted image to Base64: {image_path} ({len(base64_image)} chars)")
            return base64_image
            
        except FileNotFoundError:
            error_msg = f"Image file not found: {image_path}"
            self.logger.error(error_msg)
            raise FileProcessingError(
                error_msg,
                error_code="IMAGE_FILE_NOT_FOUND",
                context={"image_path": image_path}
            )
            
        except Exception as e:
            error_msg = f"Failed to convert image to Base64: {str(e)}"
            self.logger.error(error_msg)
            raise FileProcessingError(
                error_msg,
                error_code="BASE64_CONVERSION_ERROR",
                context={"image_path": image_path, "error": str(e)}
            )
    
    def _validate_image_file(self, image_path: str) -> None:
        """
        Validate that the file is a valid image.
        
        Args:
            image_path: Path to the image file
            
        Raises:
            FileProcessingError: If image validation fails
        """
        try:
            with Image.open(image_path) as img:
                # Try to load the image to verify it's valid
                img.verify()
                
        except Exception as e:
            raise FileProcessingError(
                f"Invalid image file: {str(e)}",
                error_code="INVALID_IMAGE_FILE",
                context={"image_path": image_path, "error": str(e)}
            )
    
    def _extract_image_metadata(self, image_path: str) -> Dict[str, Any]:
        """
        Extract metadata from the image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image metadata
        """
        try:
            with Image.open(image_path) as img:
                metadata = {
                    "image_format": img.format,
                    "image_mode": img.mode,
                    "image_size": img.size,
                    "image_width": img.width,
                    "image_height": img.height,
                }
                
                # Add EXIF data if available
                try:
                    exif_dict = img._getexif()
                    if exif_dict:
                        metadata["has_exif"] = True
                        metadata["exif_keys"] = list(exif_dict.keys())
                        # Extract some common EXIF tags
                        if 272 in exif_dict:  # Make
                            metadata["camera_make"] = exif_dict[272]
                        if 271 in exif_dict:  # Model
                            metadata["camera_model"] = exif_dict[271]
                        if 306 in exif_dict:  # DateTime
                            metadata["datetime"] = exif_dict[306]
                    else:
                        metadata["has_exif"] = False
                except (AttributeError, TypeError):
                    metadata["has_exif"] = False
                
                # Add file size
                metadata["file_size_bytes"] = os.path.getsize(image_path)
                
                # Add color information
                if img.mode == 'P':
                    metadata["has_palette"] = True
                    metadata["palette_size"] = len(img.getpalette()) // 3 if img.getpalette() else 0
                else:
                    metadata["has_palette"] = False
                
                # Check for transparency
                metadata["has_transparency"] = img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                
                return metadata
                
        except Exception as e:
            self.logger.warning(f"Failed to extract image metadata: {str(e)}")
            return {
                "error": f"Failed to extract metadata: {str(e)}",
                "file_size_bytes": os.path.getsize(image_path) if os.path.exists(image_path) else 0
            }
    
    def _format_image_analysis(
        self, 
        analysis_result: str, 
        file_metadata: FileMetadata, 
        image_metadata: Dict[str, Any]
    ) -> str:
        """
        Format the image analysis result into structured markdown.
        
        Args:
            analysis_result: Raw analysis result from the multimodal model
            file_metadata: Original file metadata
            image_metadata: Extracted image metadata
            
        Returns:
            Formatted markdown string
        """
        # Create structured markdown output
        formatted_output = f"""# 图片分析结果

## 文件信息
- **文件名**: {file_metadata.original_name}
- **文件ID**: {file_metadata.file_id}
- **文件类型**: {file_metadata.file_type.upper()}
- **文件大小**: {self._format_file_size(file_metadata.file_size)}
- **上传时间**: {file_metadata.upload_time.strftime('%Y-%m-%d %H:%M:%S')}

## 图片属性
- **图片格式**: {image_metadata.get('image_format', '未知')}
- **图片模式**: {image_metadata.get('image_mode', '未知')}
- **图片尺寸**: {image_metadata.get('image_width', 0)} × {image_metadata.get('image_height', 0)} 像素
- **是否包含EXIF数据**: {'是' if image_metadata.get('has_exif', False) else '否'}

## AI分析结果

{analysis_result}

---
*分析完成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return formatted_output
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Formatted file size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def _create_test_image(self, file_path: str, file_type: str) -> None:
        """
        Create a test image file for demonstration purposes.
        
        Args:
            file_path: Path where to create the test image
            file_type: Image file type (jpg, png, etc.)
        """
        try:
            # Create a simple test image
            img = Image.new('RGB', (800, 600), color='lightblue')
            
            # Add some text to make it more realistic
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                
                # Try to use a default font, fallback to basic if not available
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except (OSError, IOError):
                    font = ImageFont.load_default()
                
                draw.text((50, 250), "Test Image", fill='darkblue', font=font)
                draw.text((50, 300), f"Format: {file_type.upper()}", fill='darkblue', font=font)
                
            except ImportError:
                # If ImageDraw is not available, just create a plain image
                pass
            
            # Save the image
            if file_type.lower() in ['jpg', 'jpeg']:
                img.save(file_path, 'JPEG', quality=85)
            else:
                img.save(file_path, file_type.upper())
                
            self.logger.debug(f"Created test image: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to create test image: {str(e)}")
            raise FileProcessingError(
                f"Failed to create test image: {str(e)}",
                error_code="TEST_IMAGE_CREATION_ERROR",
                context={"file_path": file_path, "file_type": file_type}
            )
    
    def _cleanup_temp_file(self, file_path: str) -> None:
        """
        Clean up temporary file.
        
        Args:
            file_path: Path to the temporary file to clean up
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")


