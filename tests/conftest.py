"""
Pytest configuration for ReportForge AI.
Ensures workspace root is in sys.path for test discovery.
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent)
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)
