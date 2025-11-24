#!/usr/bin/env python3
"""
Simple CLI runner that avoids nexus_utils __init__.py imports
"""

import sys
import os

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
nexus_root = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, nexus_root)

if __name__ == '__main__':
    from nexus_utils.cli.main import main
    main()
