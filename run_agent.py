#!/usr/bin/env python3
"""
Quick start script for Super Agent
Run this to start the agent in interactive mode.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from super_agent.cli import main

if __name__ == "__main__":
    # Default to interactive mode if no arguments
    if len(sys.argv) == 1:
        sys.argv.append("interactive")
    main()
