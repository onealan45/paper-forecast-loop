# 2026-04-24 M1 Strategy Research Robot Review

## Scope

Review of the M1 strategy research robot implementation:

- strategy decision artifact and decision gates
- baseline evaluation and evidence-grade behavior
- paper-only broker boundary
- health-check and Codex repair request behavior
- dashboard decision/health-first read-only UX
- CLI `decide`, `health-check`, and `run-once --also-decide`
- README, PRD, ADR, and implementation plan updates

## Reviewer Sources

- Controller implementation pass in this workspace.
- Final reviewer subagent `reviewer` / `gpt-5.5` / `xhigh` reasoning.
- Reviewer rule: only subagent review counts as final review; controller did not self-approve.

## Blocking Findings Found And Fixed

- `decision.py`: `decide` could crash on corrupt storage before emitting `STOP_NEW_ENTRIES`. Fixed by fail-closing before reading artifacts when health-check is blocking.
- `health.py`: baseline broken links were not health-checked. Fixed by validating baseline forecast and score references.
- `health.py`: corrupt `portfolio_snapshots.jsonl` was not health-gated before `decide` read it. Fixed by loading portfolio snapshots in health-check.
- `health.py` / `storage.py`: corrupt local `repair_requests.jsonl` could prevent repair request creation. Fixed by skipping corrupt existing rows during append-unique.
- `health.py`: corrupt global `.codex/repair_requests/repair_requests.jsonl` could prevent missing-storage repair request creation. Fixed by skipping corrupt existing rows in the global repair log append.
- `cli.py`: `decide` created a missing storage directory before health-check could diagnose it. Fixed by running health-check before repository creation and returning a fail-closed decision without creating the typo path.
- `health.py`: non-replay `evaluation_summaries.jsonl` evidence links were not validated. Fixed by checking forecast, scored forecast, score, review, and proposal links for non-replay summaries.
- `health.py` / `cli.py`: storage path pointing to an existing file could crash repair creation or `decide`. Fixed by treating non-directory storage paths as blocking health and fail-closing `decide`.

## Final Reviewer Result

Final reviewer result: `APPROVED`.

No blocking findings remain.

Non-blocking follow-up risks:

- `run-once` and `replay-range` can still be hardened for existing-file storage path errors.
- `render-dashboard` still assumes artifacts are readable; recommended future improvement is to show a repair panel or require health-check preflight.
- Replay-scoped `EvaluationSummary` link validation depends on replay window fields; update health rules if replay summary schema changes.

## Verification

Commands run:

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python -m pytest -q
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
python .\run_forecast_loop.py run-once --provider coingecko --symbol BTC-USD --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --also-decide
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD
git diff --check
```

Results:

- `python -m pytest -q`: `72 passed`
- `compileall`: passed
- active storage `health-check`: `healthy`, `repair_required=false`
- active storage `run-once --also-decide`: succeeded, produced `HOLD`
- active storage `render-dashboard`: succeeded
- `git diff --check`: no whitespace errors; only Windows CRLF warnings

## Automation Decision

The final review no longer blocks automation.

Hourly automation may be resumed only with an M1-aware prompt that includes:

- health-check
- paper-only run cycle
- strategy decision generation
- dashboard refresh
- repair/building mode when blocking findings occur

