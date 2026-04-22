from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src_layout() -> None:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    sys.path.insert(0, str(src_dir))


def main() -> int:
    _bootstrap_src_layout()
    from forecast_loop.cli import main as cli_main  # noqa: PLC0415

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
