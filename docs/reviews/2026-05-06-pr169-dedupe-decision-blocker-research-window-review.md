# PR169 Dedupe Decision-Blocker Research Window Review

## Scope

Branch: `codex/pr169-dedupe-decision-blocker-research-window`

Reviewed changes:

- `src/forecast_loop/decision_research_plan.py`
- `src/forecast_loop/research_artifact_selection.py`
- `tests/test_decision_research_plan.py`
- `docs/architecture/PR169-dedupe-decision-blocker-research-window.md`

Goal: prevent decision-blocker research from rerunning identical event-edge,
backtest, and walk-forward tasks when a new blocker agenda is created but the
underlying data/window has not changed.

## Review Method

Per repo rule, final review was performed by subagents only. The controller did
not self-review.

Reviewers:

- `Gauss` first pass: `CHANGES_REQUESTED`
- `Godel` second pass: `CHANGES_REQUESTED`
- `Nietzsche` final pass: `APPROVED`

## Findings And Resolution

### First Pass Findings

1. Backtest after-agenda path bypassed window/context checks.
   Resolution: removed the after-agenda shortcut and required current-window
   matching for symbol, start/end, exact candle ids, decision-blocker context,
   and input freshness.

2. Walk-forward after-agenda path ignored current window/context.
   Resolution: removed the after-agenda shortcut and required current-window
   matching for symbol, start/end, decision-blocker context, and input freshness.

3. Event-edge after-agenda path could reuse stale input evidence.
   Resolution: event-edge reuse now requires evaluation freshness against the
   current event/reaction/candle input watermark.

### Second Pass Finding

1. Backtest reuse could accept a stale run when a newer result pointed at it.
   Resolution: both `BacktestRun.created_at` and `BacktestResult.created_at`
   must be fresh relative to the candle input watermark; both must also be
   non-future relative to planner `now`.

## Final Review Result

Final reviewer result: `APPROVED`.

Final reviewer residual risks:

- Event-edge reuse is keyed by same symbol plus input watermark rather than an
  artifact-level input manifest. This is acceptable for the current scope, but a
  future task should add finer context if event-edge tasks split by horizon,
  cost model, event family, or strategy-specific input manifest.

## Verification

Commands verified before final approval:

```powershell
python -m pytest tests\test_decision_research_plan.py -q
python -m pytest tests\test_decision_research_executor.py -q
python -m pytest tests\test_strategy_research_digest.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- Planner suite: `18 passed`
- Executor suite: `8 passed`
- Digest suite: `23 passed`
- Full test suite: `582 passed`
- Compileall: passed
- CLI help: passed
- Diff check: passed with CRLF warnings only

Active storage smoke:

```powershell
python .\run_forecast_loop.py decision-blocker-research-plan --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
```

Result: latest blocker plan returned `next_task_id=null` and reused:

- `event-edge:f7b06184e9ac2aec`
- `backtest-result:1787cd6b5c1a7343`
- `walk-forward:a70090702312832f`

## Automation Impact

This change reduces duplicate research artifact growth when blocker agendas
repeat over unchanged data. It does not change BUY/SELL gates, strategy
decision generation, or any execution boundary.
