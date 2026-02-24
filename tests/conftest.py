"""Pytest configuration for StupiPHI tests.

Ensures the src/ directory is on sys.path so `import stupiphi` works
without requiring an editable install.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

