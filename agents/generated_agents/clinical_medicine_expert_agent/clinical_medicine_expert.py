#!/usr/bin/env python3
"""
Clinical Medicine Expert Agent

This agent is a specialized clinical medicine expert that answers user questions
in the life sciences and clinical medicine domains, with a particular focus on
pharmaceutical development. It collects evidence using specialized tools and
provides rigorous, evidence-based answers with complete reasoning processes.

Key capabilities:
1. Question analysis and understanding
2. Evidence collection using specialized medical tools
3. Comprehensive evidence analysis
4. Transparent reasoning process
5. Evidence-based answer generation
6. Clear communication of limitations when evidence is insufficient

The agent follows a three-stage thinking framework:
1. Question Analysis - Understanding the question and identifying required evidence
2. Evidence Collection - Using appropriate tools to gather relevant medical evidence
3. Answer Generation - Providing professional answers based on collected evidence
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
from nexus_utils.agent_factory import create_agent_from_prompt_template
from strands.telemetry import StrandsTelemetry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up telemetry
os.environ["BYPASS_TOOL_CONSENT"] = "true"
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4318"
strands_telemetry = StrandsTelemetry()
strands_telemetry.setup_otlp_exporter()

# Create agent parameters
agent_params = {
    "env": "production",
    "version": "latest", 
    "model_id": "us.anthropic.claude-3-5-sonnet-20240620-v1:0",  # Using Claude 3.5 Sonnet for advanced medical comprehension
    "enable_logging": True
}

# Create the Clinical Medicine Expert Agent
clinical_medicine_expert = create_agent_from_prompt_template(
    agent_name="generated_agents_prompts/clinical_medicine_expert_agent/clinical_medicine_expert", 
    **agent_params
)

def answer_medical_question(query: str, 
                           max_evidence: int = 5,
                           evidence_threshold: float = 0.7) -> str:
    """
    Answer a clinical medicine or pharmaceutical development question based on evidence.
    
    Args:
        query (str): The medical or pharmaceutical question to answer
        max_evidence (int): Maximum number of evidence pieces to collect (default: 5)
        evidence_threshold (float): Minimum relevance threshold for evidence (default: 0.7)
        
    Returns:
        str: Formatted response with evidence-based answer and reasoning process
    """
    # Construct input with parameters
    input_text = f"{query}\n\n"
    
    # Add parameters if non-default
    params = []
    if max_evidence != 5:
        params.append(f"Maximum evidence: {max_evidence}")
    if evidence_threshold != 0.7:
        params.append(f"Evidence threshold: {evidence_threshold}")
    
    if params:
        input_text += "Parameters:\n" + "\n".join(f"- {param}" for param in params) + "\n\n"
    
    # Process the query through the agent
    try:
        result = clinical_medicine_expert(input_text)
        return result
    except Exception as e:
        logger.error(f"Error processing medical question: {e}")
        return f"Error processing medical question: {str(e)}"

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Clinical Medicine Expert Agent')
    parser.add_argument('-q', '--query', type=str, required=True,
                       help='Clinical medicine or pharmaceutical question')
    parser.add_argument('-e', '--max_evidence', type=int, default=5,
                       help='Maximum number of evidence pieces to collect (default: 5)')
    parser.add_argument('-t', '--threshold', type=float, default=0.7,
                       help='Minimum relevance threshold for evidence (default: 0.7)')
    
    args = parser.parse_args()
    
    print(f"✅ Clinical Medicine Expert Agent initialized")
    print(f"🔍 Analyzing question: {args.query}")
    
    # Execute search
    result = answer_medical_question(
        query=args.query,
        max_evidence=args.max_evidence,
        evidence_threshold=args.threshold
    )
    