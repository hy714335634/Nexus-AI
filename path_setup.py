#!/usr/bin/env python3
"""
Universal path setup for all scripts in the project
Import this at the beginning of any script to ensure proper Python path
"""
import sys
import os

# Get the directory where this file is located (project root)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Add project root to Python path if not already there
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Also add to PYTHONPATH environment variable
os.environ['PYTHONPATH'] = PROJECT_ROOT + ':' + os.environ.get('PYTHONPATH', '')

print(f"Added {PROJECT_ROOT} to Python path")
