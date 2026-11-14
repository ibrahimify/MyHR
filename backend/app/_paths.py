"""Make the repository root importable so the backend can reuse `src`.

Phase 1 reuses the existing desktop Python packages (`src.database`,
`src.services`) instead of duplicating them. The repository root is two
levels above this file (`backend/app/_paths.py` -> repo root).
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
