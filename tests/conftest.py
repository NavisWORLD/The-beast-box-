"""Repo-root import bootstrap for the test suite.

pyproject.toml already sets pythonpath [".", ...], so `import world.*` and
`import scripts.*` resolve from a repo-root pytest run. This conftest inserts
the repo root defensively (it also covers running pytest from elsewhere), so
the `from scripts.zeref_world_tick import ...` / `from world... import ...`
imports in the world-tick test files always work.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
