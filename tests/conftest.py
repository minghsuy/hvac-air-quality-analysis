"""Pytest configuration to add parent directory to path"""
import sys
from pathlib import Path

# Add parent directory to Python path so tests can import main modules
sys.path.insert(0, str(Path(__file__).parent.parent))