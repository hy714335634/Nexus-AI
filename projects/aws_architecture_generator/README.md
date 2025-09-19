# aws_architecture_generator

## 项目描述
AWS架构图生成智能体，能够理解IT技术栈和自然语言描述，将其转换为合理、美观的AWS架构图，包括正确的AWS服务选择、组件关系和安全配置。

## 项目结构
```
aws_architecture_generator/
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

#### aws_architecture_generator
- **requirements_analyzer**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/requirements_analyzer.json)
- **system_architect**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/system_architect.json)
- **agent_designer**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/agent_designer.json)
- **prompt_engineer**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/prompt_engineer.json)
- **tools_developer**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/tools_developer.json)
- **agent_code_developer**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/agent_code_developer.json)
- **agent_developer_manager**: ✅ 已完成 - [文档](projects/aws_architecture_generator/agents/aws_architecture_generator/agent_developer_manager.json)

## 附加信息
# AWS Architecture Generator

## Project Overview
The AWS Architecture Generator is an intelligent agent system that transforms natural language infrastructure requirements into professional AWS architecture diagrams. It bridges the gap between business needs and technical implementation by automatically generating visually appealing and technically sound AWS architecture designs.

## Project Status
✅ Requirements Analysis - Complete  
✅ System Architecture - Complete  
✅ Agent Design - Complete  
✅ Tool Development - Complete  
✅ Prompt Engineering - Complete  
✅ Agent Code Development - Complete  
✅ Project Management - Complete  

## Features
- **IT Technology Stack Mapping**: Understands common IT components and maps them to appropriate AWS services
- **Natural Language Processing**: Interprets infrastructure descriptions like "three-tier architecture" into technical components
- **Architecture Diagram Generation**: Creates visual diagrams in formats like drawio and mermaid
- **Architecture Validation**: Ensures designs follow AWS best practices and service relationships are correct
- **Visual Optimization**: Produces clean, professional diagrams using official AWS service icons
- **Architecture Pattern Recognition**: Identifies and applies common patterns based on requirements

## Directory Structure
```
aws_architecture_generator/
├── agents/
│   └── generated_agents/
│       └── aws_architecture_generator/
│           └── aws_architecture_generator.py
├── generated_agents_prompts/
│   └── aws_architecture_generator/
│       └── aws_architecture_generator.yaml
└── generated_tools/
    └── aws_architecture_generator/
        ├── aws_service_knowledge_base.py
        ├── architecture_diagram_generator.py
        └── architecture_validator.py
```

## Tools
The agent utilizes three main tool categories:

1. **AWS Service Knowledge Base**
   - Service information retrieval
   - Technology to AWS service mapping
   - Architecture pattern recognition
   - Service compatibility checking

2. **Architecture Diagram Generator**
   - Visual diagram creation in multiple formats
   - Architecture extraction from text descriptions
   - AWS service icon integration
   - Layout optimization

3. **Architecture Validator**
   - Architecture compliance checking
   - Service configuration validation
   - Compatibility verification
   - Well-Architected Framework alignment

## Usage

### Basic Usage
```bash
python aws_architecture_generator.py
```
This will generate an AWS architecture for a default three-tier web application with high availability.

### Custom Requirements
```bash
python aws_architecture_generator.py -i "Please generate an AWS architecture for a microservices e-commerce platform with high availability and disaster recovery"
```

### Output Format Selection
```bash
python aws_architecture_generator.py -f drawio
```
Supported formats: mermaid (default), drawio

### Detailed Output
```bash
python aws_architecture_generator.py -d
```
Generates detailed architecture with explanations of service choices and design decisions.

## Technical Details

### Model Requirements
The agent is designed to work with Anthropic Claude 3 Opus or similar models with strong technical understanding capabilities.

### Performance Considerations
- Response time target: <30 seconds
- Maximum architecture complexity: ~20 AWS service components
- Optimized for readability and visual appeal

## Limitations
- Does not create or deploy actual AWS resources
- Does not perform cost estimation and optimization
- Does not provide code-level implementation details
- Does not design multi-cloud architectures
- Limited to approximately 20 AWS service components per diagram

## Maintenance
- The AWS service knowledge base should be updated quarterly to include new services and features
- Consider enhancing with cost estimation capabilities in future versions
- Monitor user feedback to identify common architecture patterns for pre-optimization

## Examples
The agent can handle various architecture scenarios, including:
- Web applications (2-tier, 3-tier, n-tier)
- Microservices architectures
- Serverless applications
- Data processing pipelines
- High availability and disaster recovery setups
- Security-focused architectures

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## 使用说明
请参考项目配置文件和状态文件了解当前开发进度。

---
*最后更新时间: 2025-09-19 04:42:54 UTC*
