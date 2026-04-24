"""
Repo-local Python bootstrap for src-layout imports.

Python automatically imports `sitecustomize` (if present on sys.path) during
startup, which makes this a lightweight way to ensure `src/` is importable when
running commands from the repo root without requiring an editable install.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    if not src_dir.is_dir():
        return

    src_str = str(src_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_src_on_path()
