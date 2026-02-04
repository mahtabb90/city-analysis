"""
Pytest configuration.

Adds the 'src' directory to sys.path so that tests can import
the project package (city_vibe) when using a src/ layout.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Path to the 'src' directory
SRC_PATH = Path(__file__).resolve().parents[1] / "src"

# Ensure 'src' is in Python path
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
