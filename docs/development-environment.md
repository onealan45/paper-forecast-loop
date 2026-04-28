# Development Environment

This document records the portable parts of the local Codex development environment.

It intentionally excludes machine-local runtime state such as `.codex/`,
`paper_storage/`, screenshots, caches, automation TOML files, thread ids, and
generated run artifacts.

## Supported Local Environment

- OS shell: Windows PowerShell
- Python: `>=3.13`
- Test runner: `pytest`
- Browser for UI inspection: Edge
- Package layout: source code under `src/`
- Preferred CLI entrypoint: `python .\run_forecast_loop.py ...`

Use the wrapper entrypoint instead of direct module execution unless there is a
specific reason. The wrapper adds `src\` to `sys.path` for this checkout.

## Setup

Install development dependencies:

```powershell
python -m pip install -e .[dev]
```

## Reviewability And Formatting

PR0 establishes a reviewability gate before additional Alpha Evidence Engine
work. The current codebase has no pathological Python source line longer than
1,000 characters, so this stage uses a guard test instead of broad behavior-free
rewrites.

Policy:

- Keep source and test files readable in GitHub diffs.
- Do not commit generated, minified, or one-line Python source unless it is
  explicitly excluded by a documented generated-file exception.
- Prefer small, behavior-preserving formatting diffs before adding strategy
  logic.
- Do not add runtime formatting dependencies. Dev-only formatters may be added
  later if they are useful and do not change runtime dependencies.

The guard is:

```powershell
python -m pytest tests\test_reviewability.py -q
```

Run the standard verification set:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

## Active Paper Storage

The current local active storage path is:

```text
paper_storage/hourly-paper-forecast/coingecko/BTC-USD
```

That directory is intentionally ignored by Git. It contains local paper-only
artifacts, not source-of-truth project configuration.

Useful checks:

```powershell
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
python .\run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --also-decide
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD
```

## Automation Boundary

Codex automation files live outside the repo under the user's local Codex app
state. Do not commit those runtime files.

Repository docs may describe automation behavior, but the actual local
automation state is machine-specific and may contain:

- thread ids
- timestamps
- local app state
- temporary prompts
- paused/active runtime status

The expected M1 hourly loop is:

1. run `health-check`
2. run one paper-only forecast cycle with `--also-decide`
3. review matured forecasts when complete
4. compare quality against baselines
5. emit or refresh the latest strategy decision
6. render the read-only dashboard
7. if blocking health appears, create or inspect the Codex repair request and stay in repair/building mode

## Git Hygiene

Commit portable source, tests, and documentation:

- `AGENTS.md`
- `docs/`
- `src/`
- `tests/`
- `README.md`
- `pyproject.toml`
- `run_forecast_loop.py`
- `sitecustomize.py`

Do not commit generated or local runtime data:

- `.codex/`
- `.pytest_cache/`
- `__pycache__/`
- `paper_storage/`
- `output/`
- local sample run directories
- virtual environments

## Review Archive

Every substantive review must be archived under:

```text
docs/reviews/
```

Use this filename format:

```text
YYYY-MM-DD-<topic>.md
```

Final review must be done by a subagent, not by the same agent that implemented
the change.
