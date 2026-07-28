"""
Maestro CLI - AI-Assisted Music Production
A CLI-first tool for composing, arranging, orchestrating, and rendering music with LLM planning and Carla execution.
"""

__version__ = "0.1.0"
__author__ = "Jonathan"

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "configs"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
SONGS_DIR = PROJECT_ROOT / "songs" / "projects"
STATE_DIR = SONGS_DIR / "_state"  # For global state if needed

# Ensure directories exist
SONGS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)
