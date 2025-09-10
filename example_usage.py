#!/usr/bin/env python3
"""
Example showing how to properly import and use utils package
"""

# Method 1: Import setup_path first (recommended)
import setup_path  # This adds project root to Python path

# Now you can import utils normally
from utils import PromptManager, ConfigLoader, prompts_manager
from utils.agent_factory import get_bedrock_model, get_tool_by_name

# Method 2: Direct import with sys.path manipulation
# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("Testing utils imports...")
    
    # Test PromptManager
    pm = PromptManager()
    print(f"PromptManager initialized: {type(pm)}")
    
    # Test ConfigLoader
    config_loader = ConfigLoader()
    print(f"ConfigLoader initialized: {type(config_loader)}")
    
    # Test global prompts_manager instance
    print(f"Global prompts_manager: {type(prompts_manager)}")
    
    print("All utils imports working correctly!")

if __name__ == "__main__":
    main()
