#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

# Import directly to avoid nexus_utils __init__.py
from nexus_utils.cli.main import main

if __name__ == '__main__':
    main()
