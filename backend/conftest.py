"""Pytest configuration: ensure the backend package is importable."""

import os
import sys

BACKEND_ROOT = os.path.dirname(__file__)
os.environ.setdefault("MYHR_AUTH_MODE", "local")

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
