"""Configuration for Ethics Council backend."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Data directory for review storage
DATA_DIR = os.getenv("ETHICS_COUNCIL_DATA_DIR", str(PROJECT_ROOT / "data" / "reviews"))

# Default preset
DEFAULT_PRESET = os.getenv("ETHICS_COUNCIL_DEFAULT_PRESET", "life-sciences")

# Server config
HOST = os.getenv("ETHICS_COUNCIL_HOST", "0.0.0.0")
PORT = int(os.getenv("ETHICS_COUNCIL_PORT", "8001"))
