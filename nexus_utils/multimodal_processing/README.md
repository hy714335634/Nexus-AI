# 多模态处理模块 (Multimodal Processing Module)

## 概述

这个模块提供了完整的多模态内容处理能力，包括图像、文档、文本等多媒体内容的解析、处理和转换。

## 目录结构

```
utils/multimodal_processing/
├── __init__.py                    # 包初始化文件
├── models/                        # 数据模型定义
│   ├── __init__.py
│   ├── data_models.py            # 核心数据模型
│   ├── exceptions.py              # 异常处理类
│   └── interfaces.py              # 接口定义
├── multimodal_model_service.py    # 多模态模型服务
├── content_parsing_engine.py      # 内容解析引擎
├── document_processor.py          # 文档处理器
├── image_processor.py             # 图像处理器
├── text_processor.py              # 文本处理器
├── markdown_generator.py          # Markdown生成器
├── s3_storage_service.py          # S3存储服务
├── file_upload_manager.py         # 文件上传管理器
└── error_handler.py               # 错误处理器
```

## 使用方法

### 1. 基本导入

```python
# 导入数据模型
from nexus_utils.multimodal_processing.models.data_models import FileMetadata, ProcessedContent

# 使用延迟导入避免循环依赖
from nexus_utils.multimodal_processing import get_multimodal_model_service, get_content_parsing_engine

# 获取服务实例
multimodal_service = get_multimodal_model_service()()
parsing_engine = get_content_parsing_engine()()
```

### 2. 处理单个文件

```python
from nexus_utils.multimodal_processing import get_image_processor, get_document_processor

# 图像处理
image_processor = get_image_processor()()
file_metadata = FileMetadata(
    original_name="example.jpg",
    file_type="jpg",
    file_size=1024000
)
result = image_processor.process(file_metadata)

# 文档处理
doc_processor = get_document_processor()()
result = doc_processor.process(file_metadata)
```

### 3. 批量处理文件

```python
from nexus_utils.multimodal_processing import get_content_parsing_engine

parsing_engine = get_content_parsing_engine()()
file_list = [file_metadata1, file_metadata2, file_metadata3]
results = parsing_engine.parse_files(file_list)
```

### 4. 使用S3存储

```python
from nexus_utils.multimodal_processing import get_s3_storage_service

s3_service = get_s3_storage_service()(
    bucket_name="my-bucket",
    aws_region="us-west-2"
)

# 上传文件
s3_service.upload_file("local_file.txt", "remote_path.txt")

# 下载文件
s3_service.download_file("remote_path.txt", "local_file.txt")
```

## 核心功能

### 多模态模型服务 (MultimodalModelService)
- AWS Bedrock Claude模型集成
- 图像Base64转换
- 文本处理和Markdown格式化
- 错误处理和重试机制

### 内容解析引擎 (ContentParsingEngine)
- 文件类型检测和处理器选择
- 批量文件处理
- 结果组合和错误聚合
- 统一Markdown输出生成

### 文件处理器
- **图像处理器**: 支持JPG, PNG, GIF等格式
- **文档处理器**: 支持Excel, Word, PDF等格式
- **文本处理器**: 支持TXT, MD, JSON等格式

### 存储和上传
- **S3存储服务**: AWS S3集成
- **文件上传管理器**: 文件上传和验证

## 配置

模块使用配置文件来管理设置：

```yaml
multimodal_parser:
  model:
    primary_model: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    fallback_model: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
    max_tokens: 4000
  processing:
    timeout_seconds: 300
    retry_attempts: 3
  aws:
    bedrock_region: "us-west-2"
    s3_bucket: "nexus-ai-file-storage"
    s3_prefix: "multimodal-content/"
```

## 依赖要求

```txt
pandas
Pillow
python-docx
PyPDF2
openpyxl
boto3
PyYAML
```

## 注意事项

1. **延迟导入**: 为了避免循环依赖，模块使用延迟导入模式
2. **错误处理**: 所有操作都有完善的错误处理机制
3. **配置管理**: 支持环境变量和配置文件
4. **AWS集成**: 需要配置AWS凭证和权限

## 示例

完整的使用示例请参考 `tools/system_tools/multimodal_content_parser.py` 文件。
