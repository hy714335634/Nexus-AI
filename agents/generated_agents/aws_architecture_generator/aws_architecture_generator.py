#!/usr/bin/env python3
"""
AWS Architecture Generator Agent

A specialized agent that generates AWS architecture diagrams based on natural language descriptions
of infrastructure requirements. The agent understands IT technology stacks and maps them to appropriate
AWS managed services, creates coherent architectures, and generates visual diagrams showing relationships
between services.

The agent follows a workflow of:
1. Understanding the user's requirements
2. Mapping requirements to appropriate AWS services
3. Designing a coherent architecture
4. Validating the architecture against best practices
5. Generating a visual diagram
6. Providing explanations for service choices and design decisions

This agent integrates:
- AWS Service Knowledge Base Tool: For AWS service information and mapping
- Architecture Diagram Generator Tool: For creating visual architecture diagrams
- Architecture Validator Tool: For validating architectures against AWS best practices
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

class AwsArchitectureGenerator:
    """
    Helper class for AWS Architecture Generator Agent to manage state and provide utility functions.
    """
    
    def __init__(self):
        """Initialize the AWS Architecture Generator helper."""
        self.current_architecture = None
        self.last_diagram = None
        self.architecture_history = []
        self.service_mappings = {}
        
    def save_architecture(self, architecture: Dict[str, Any]) -> None:
        """
        Save the current architecture and add it to history.
        
        Args:
            architecture: The architecture description to save
        """
        if self.current_architecture:
            self.architecture_history.append(self.current_architecture)
        self.current_architecture = architecture
        
    def get_current_architecture(self) -> Optional[Dict[str, Any]]:
        """
        Get the current architecture description.
        
        Returns:
            The current architecture description or None if not set
        """
        return self.current_architecture
    
    def save_diagram(self, diagram: Dict[str, Any]) -> None:
        """
        Save the last generated diagram.
        
        Args:
            diagram: The diagram data to save
        """
        self.last_diagram = diagram
        
    def get_last_diagram(self) -> Optional[Dict[str, Any]]:
        """
        Get the last generated diagram.
        
        Returns:
            The last diagram data or None if not generated
        """
        return self.last_diagram
    
    def add_service_mapping(self, technology: str, aws_service: str) -> None:
        """
        Add a mapping from technology to AWS service.
        
        Args:
            technology: The technology or concept
            aws_service: The corresponding AWS service
        """
        self.service_mappings[technology.lower()] = aws_service
        
    def get_service_mapping(self, technology: str) -> Optional[str]:
        """
        Get the AWS service mapping for a technology.
        
        Args:
            technology: The technology or concept to look up
            
        Returns:
            The corresponding AWS service or None if not found
        """
        return self.service_mappings.get(technology.lower())
    
    def clear_state(self) -> None:
        """Clear the current state but keep history."""
        self.current_architecture = None
        self.last_diagram = None


# Create agent with common parameters
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "default"
}

# Create the AWS Architecture Generator agent using the prompt template
aws_architecture_generator = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/aws_architecture_generator/aws_architecture_generator", 
    **agent_params
)

# Create helper instance
helper = AwsArchitectureGenerator()

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AWS Architecture Generator Agent')
    parser.add_argument('-i', '--input', type=str, 
                       default="Please generate an AWS architecture for a three-tier web application with high availability.",
                       help='The architecture requirements to process')
    parser.add_argument('-f', '--format', type=str, 
                       default="mermaid",
                       choices=["mermaid", "drawio", "ascii"],
                       help='The diagram format to generate')
    parser.add_argument('-d', '--detailed', action='store_true',
                       help='Generate detailed architecture with explanations')
    args = parser.parse_args()
    
    print(f"✅ AWS Architecture Generator Agent created successfully: {aws_architecture_generator.name}")
    
    # Build the test input
    test_input = args.input
    if args.format != "mermaid":
        test_input += f"\nPlease generate the diagram in {args.format} format."
    if args.detailed:
        test_input += "\nPlease provide detailed explanations for your architecture choices."
    
    print(f"🎯 Test input: {test_input}")
    
    try:
        result = aws_architecture_generator(test_input)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.exception("Error during agent execution")