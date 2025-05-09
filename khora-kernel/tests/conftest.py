"""
Pytest configuration for Khora Kernel tests.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path so tests can import the package
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))
