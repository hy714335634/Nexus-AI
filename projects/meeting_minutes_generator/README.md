# meeting_minutes_generator

## 项目描述
一个能够从视频会议中提取音频，转换为文本，并生成标准会议纪要的智能体

## 项目结构
```
meeting_minutes_generator/
├── agents/          # Agent实现文件
├── config.yaml      # 项目配置文件
├── README.md        # 项目说明文档
└── status.yaml      # 项目状态跟踪文件
```

## Agent开发阶段

### 阶段说明
1. **requirements_analyzer**: 需求分析阶段
2. **system_architect**: 系统架构设计阶段
3. **agent_designer**: Agent设计阶段
4. **prompt_engineer**: 提示词工程阶段
5. **tools_developer**: 工具开发阶段
6. **agent_code_developer**: Agent代码开发阶段
7. **agent_developer_manager**: Agent开发管理阶段

### 各Agent阶段结果

#### meeting_minutes_generator
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/meeting_minutes_generator/agents/meeting_minutes_generator/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成

## 附加信息
# 视频会议纪要生成智能体

## 项目概述

视频会议纪要生成智能体是一个专业工具，能够自动处理视频会议文件，提取音频内容，转换为文本，并生成符合企业标准的会议纪要。该智能体旨在大幅降低人工记录和整理会议内容的时间成本，提高会议效率，确保会议关键信息的准确捕获和标准化输出。

### 核心功能

- **视频处理**：支持主流视频格式（MP4、AVI、MOV等）的读取和处理
- **音频提取**：从视频文件中提取高质量音频内容
- **语音转文本**：将音频内容转换为文本，支持说话人分离
- **会议纪要生成**：基于文本内容生成结构化的会议纪要
- **标准化输出**：按照企业标准格式生成会议纪要

## 技术架构

该项目采用单Agent架构，基于document_processor_agent模板开发，并添加视频处理和音频转文本功能。主要技术组件包括：

- **FFmpeg**：用于视频处理和音频提取
- **AWS Transcribe**：用于高质量语音转文本，支持说话人分离
- **AWS Bedrock**：使用Claude模型进行文本分析和会议纪要生成
- **Strands SDK**：提供Agent框架和工具集成能力

## 目录结构

```
meeting_minutes_generator/
├── agents/
│   └── generated_agents/
│       └── meeting_minutes_generator/
│           └── meeting_minutes_generator.py  # Agent主代码
├── prompts/
│   └── generated_agents_prompts/
│       └── meeting_minutes_generator/
│           └── meeting_minutes_generator.yaml  # Agent提示词
├── tools/
│   └── generated_tools/
│       └── meeting_minutes_generator/
│           └── video_processing_tools.py  # 视频处理工具
├── projects/
│   └── meeting_minutes_generator/
│       ├── agents/
│       │   └── meeting_minutes_generator/
│       │       ├── requirements_analyzer.json  # 需求分析文档
│       │       ├── system_architect.json  # 系统架构设计文档
│       │       ├── agent_designer.json  # Agent设计文档
│       │       ├── prompt_engineer.json  # 提示词工程文档
│       │       ├── tools_developer.json  # 工具开发文档
│       │       └── agent_code_developer.json  # Agent代码开发文档
│       ├── requirements.txt  # 项目依赖
│       └── README.md  # 项目说明
```

## 使用方式

### 命令行使用

```bash
# 基本用法
python meeting_minutes_generator.py -v /path/to/video.mp4

# 带参数的用法
python meeting_minutes_generator.py -v /path/to/video.mp4 -t "产品规划会议" -d "2025-09-22" -p "张三,李四,王五" -l zh-CN -f detailed -o /path/to/output

# 交互模式
python meeting_minutes_generator.py -i
```

### 参数说明

- `-v, --video`：视频文件路径（必需）
- `-t, --title`：会议标题（可选）
- `-d, --date`：会议日期（可选）
- `-p, --participants`：参会人员，用逗号分隔（可选）
- `-l, --language`：语言代码，默认为中文(zh-CN)（可选）
- `-f, --format`：纪要格式类型（standard, detailed, summary）（可选）
- `-o, --output`：输出目录路径（可选）
- `-i, --interactive`：交互模式，直接与Agent对话（可选）

### API调用

```python
from agents.generated_agents.meeting_minutes_generator.meeting_minutes_generator import process_video

# 处理视频并生成会议纪要
result = process_video(
    video_path="/path/to/video.mp4",
    meeting_title="产品规划会议",
    meeting_date="2025-09-22",
    participants=["张三", "李四", "王五"],
    language_code="zh-CN",
    format_type="detailed",
    output_dir="/path/to/output"
)

# 输出结果
if result.get("success", False):
    print(f"会议纪要已保存至: {result.get('minutes_path')}")
else:
    print(f"处理失败: {result.get('error')}")
```

## 依赖项

- Python 3.13+
- FFmpeg
- AWS账户（用于Transcribe和Bedrock服务）
- Strands SDK

详细依赖列表请参见`requirements.txt`文件。

## 注意事项

1. **视频文件限制**：
   - 建议视频大小不超过10GB
   - 建议视频时长不超过3小时
   - 需要清晰的音频质量以确保转录准确性

2. **AWS服务依赖**：
   - 需要配置AWS凭证以使用Transcribe和Bedrock服务
   - 处理时间与视频长度和复杂度成正比

3. **语言支持**：
   - 初期版本仅支持中文会议内容
   - 未来计划添加更多语言支持

## 功能限制

- 不支持实时会议记录
- 不进行视频内容的视觉分析
- 不自动识别会议参与者身份
- 不提供会议纪要的自动分发功能

## 项目状态

- 版本：1.0.0
- 状态：已完成
- 开发阶段：
  - [x] 需求分析
  - [x] 系统架构设计
  - [x] Agent设计
  - [x] 提示词工程
  - [x] 工具开发
  - [x] Agent代码开发
  - [x] 开发管理与交付

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-22 18:10:57 UTC*
