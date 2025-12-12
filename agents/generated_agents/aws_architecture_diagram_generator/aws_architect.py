#!/usr/bin/env python3
"""
AWS Architecture Diagram Generator

A professional AWS solution architect specialized in generating AWS architecture diagrams.
This agent understands natural language architecture requirements, maps IT technology stacks
to appropriate AWS managed services, validates architecture designs for best practices,
and generates architecture diagrams in multiple formats (mermaid, markdown, drawio, PPT).

Features:
1. Natural language architecture requirement understanding
2. IT technology stack to AWS service mapping
3. Architecture validation based on AWS best practices
4. Multi-format diagram generation (mermaid, markdown, drawio, PPT)
5. AWS official style and layout optimization
6. VPC service placement validation
7. Real-time AWS service information querying

Tools:
- aws_service_tools: Maps technology stack to AWS services, validates architecture
- diagram_generator: Generates diagrams in multiple formats (mermaid, markdown, drawio)
- ppt_generator_and_validator: Creates professional PowerPoint presentations
- use_aws: Queries AWS service information in real-time
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import the agent factory from the appropriate location
try:
    # Try the standard import path first
    from nexus_utils.agent_factory import create_agent_from_prompt_template
except ImportError:
    # Fall back to the utils path if the standard path is not available
    from nexus_utils.agent_factory import create_agent_from_prompt_template

from strands.telemetry import StrandsTelemetry
from nexus_utils.config_loader import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = ConfigLoader()

# Configure telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
otel_endpoint = config.get_with_env_override(
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "nexus_ai", "OTEL_EXPORTER_OTLP_ENDPOINT",
    default="http://localhost:4318"
)
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", otel_endpoint)
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Define agent creation parameters
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# Create the AWS Architect agent using the prompt template
aws_architect = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/aws_architecture_diagram_generator/aws_architect", 
    **agent_params
)


class AWSArchitectCLI:
    """Command-line interface for the AWS Architecture Diagram Generator"""
    
    def __init__(self, agent):
        """Initialize the AWS Architect CLI

        Args:
            agent: The initialized AWS Architect agent
        """
        self.agent = agent
        self.parser = self._create_parser()
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser

        Returns:
            argparse.ArgumentParser: The argument parser object
        """
        parser = argparse.ArgumentParser(
            description='AWS Architecture Diagram Generator - Generate architecture diagrams from natural language descriptions'
        )
        parser.add_argument(
            '-r', '--requirement', 
            type=str,
            help='Natural language description of architecture requirements'
        )
        parser.add_argument(
            '-f', '--file', 
            type=str,
            help='Path to a file containing architecture requirements'
        )
        parser.add_argument(
            '-o', '--output-formats',
            type=str,
            default='all',
            help='Comma-separated list of output formats (mermaid,markdown,drawio,ppt) or "all"'
        )
        parser.add_argument(
            '-t', '--title',
            type=str,
            default='AWS Architecture Diagram',
            help='Title for the architecture diagram'
        )
        parser.add_argument(
            '--template',
            type=str,
            help='Path to PowerPoint template file for PPT output'
        )
        parser.add_argument(
            '--interactive', 
            action='store_true',
            help='Enable interactive mode for multi-turn conversation'
        )
        return parser
    
    def run(self) -> None:
        """Run the AWS Architect CLI"""
        args = self.parser.parse_args()
        
        # Get architecture requirements
        requirement = self._get_requirement(args)
        if not requirement:
            print("❌ Error: Please provide architecture requirements (use -r or -f option)")
            return
        
        # Process output formats
        output_formats = self._parse_output_formats(args.output_formats)
        
        # Add output format preference to the requirement
        if output_formats != ['all']:
            formats_str = ', '.join(output_formats)
            requirement += f"\n\nPlease generate the architecture diagram in the following formats: {formats_str}."
        
        # Add diagram title to the requirement
        requirement += f"\n\nDiagram title: {args.title}"
        
        # Add template information if provided
        if args.template:
            template_path = Path(args.template)
            if template_path.exists():
                requirement += f"\n\nUse the PowerPoint template at: {template_path.absolute()}"
            else:
                print(f"⚠️ Warning: Template file not found: {args.template}")
        
        print(f"🔍 Analyzing architecture requirements and generating diagrams...\n")
        
        try:
            if args.interactive:
                self._run_interactive_mode(requirement)
            else:
                response = self.agent(requirement)
                print(f"📋 AWS Architecture Diagram Generator Response:\n{response}")
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
    
    def _get_requirement(self, args) -> Optional[str]:
        """Get architecture requirements from command line arguments or file

        Args:
            args: Parsed command line arguments

        Returns:
            Optional[str]: Architecture requirements text, or None if not provided
        """
        if args.requirement:
            return args.requirement
        elif args.file:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                print(f"❌ Failed to read file: {str(e)}")
                return None
        elif args.interactive:
            return input("Please describe your architecture requirements: ")
        else:
            return None
    
    def _parse_output_formats(self, formats_str: str) -> List[str]:
        """Parse output formats from command line argument

        Args:
            formats_str (str): Comma-separated list of formats or "all"

        Returns:
            List[str]: List of output formats
        """
        if formats_str.lower() == 'all':
            return ['all']
        
        valid_formats = {'mermaid', 'markdown', 'drawio', 'ppt'}
        formats = [fmt.strip().lower() for fmt in formats_str.split(',')]
        
        # Validate formats
        invalid_formats = [fmt for fmt in formats if fmt not in valid_formats]
        if invalid_formats:
            print(f"⚠️ Warning: Invalid output formats: {', '.join(invalid_formats)}")
            print(f"Valid formats are: {', '.join(valid_formats)}")
        
        # Filter out invalid formats
        return [fmt for fmt in formats if fmt in valid_formats]
    
    def _run_interactive_mode(self, initial_requirement: str) -> None:
        """Run interactive mode for multi-turn conversation

        Args:
            initial_requirement (str): Initial architecture requirements
        """
        print("🔄 Entering interactive mode (type 'exit' or 'quit' to end)\n")
        
        conversation_history = [
            {"role": "user", "content": initial_requirement}
        ]
        
        # First response
        response = self.agent(initial_requirement)
        print(f"📋 AWS Architect:\n{response}\n")
        
        conversation_history.append({"role": "assistant", "content": response})
        
        # Continue conversation
        while True:
            user_input = input("Your response (exit/quit to end): ")
            if user_input.lower() in ['exit', 'quit']:
                print("👋 Thank you for using the AWS Architecture Diagram Generator!")
                break
            
            conversation_history.append({"role": "user", "content": user_input})
            
            # Build complete conversation history
            full_prompt = self._build_conversation_prompt(conversation_history)
            
            response = self.agent(full_prompt)
            print(f"\n📋 AWS Architect:\n{response}\n")
            
            conversation_history.append({"role": "assistant", "content": response})
    
    def _build_conversation_prompt(self, history: List[Dict[str, str]]) -> str:
        """Build complete prompt with conversation history

        Args:
            history (List[Dict[str, str]]): Conversation history

        Returns:
            str: Complete prompt with conversation history
        """
        prompt = ""
        for message in history:
            if message["role"] == "user":
                prompt += f"User: {message['content']}\n\n"
            else:
                prompt += f"AWS Architect: {message['content']}\n\n"
        
        return prompt


def main():
    """Main function to run the AWS Architecture Diagram Generator"""
    print(f"✅ AWS Architecture Diagram Generator created successfully: {aws_architect.name}")
    
    # Run the command line interface
    cli = AWSArchitectCLI(aws_architect)
    cli.run()


if __name__ == "__main__":
    main()