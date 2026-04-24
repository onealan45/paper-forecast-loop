# M1 to M6 Autonomous Execution Contract

This roadmap is the machine-gated execution contract for advancing the project
from M1 through M6.

## Stop Conditions

Autonomous execution stops only when:

- M6 is complete and the final report is written.
- A blocking failure cannot be safely repaired.
- A safety boundary would be violated.
- A timebox requires writing an autonomous progress report.

## Safety Boundaries

Never implement or commit:

- live trading
- real-money trading
- live broker/exchange order submission
- real API key handling in source
- automatic promotion from paper to live
- secrets
- `.env`
- `.codex/`
- `paper_storage/`

M6 may use only internal paper, external paper, sandbox, or testnet broker
interfaces. Live mode remains unavailable.

## Global Machine Gate

Before merging any milestone PR:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Also run milestone-specific smoke tests.

A milestone may merge only when:

- tests pass
- compileall passes
- required CLI smoke tests show no raw traceback
- final reviewer subagent approves
- final review is archived under `docs/reviews/`
- no live trading path exists
- no secrets or runtime files are staged
- docs match implementation
- PR is mergeable

## Stage Order

Run in this order:

1. M1 Finalize
2. M1.5 Burn-in Report
3. M2A SQLite Repository
4. M2B Paper Order Ledger
5. M2C Paper Fills / Positions / NAV
6. M2D Risk Gates + Portfolio Dashboard
7. M3A Asset Registry
8. M3B Provider Audit Layer
9. M3C Deterministic Historical Candles
10. M3D ETF/Stock Data Prototype
11. M3E Macro Event Model
12. M3F Per-Symbol Multi-Asset Decisions
13. M4A Research Dataset + Leakage Checks
14. M4B Baseline Expansion
15. M4C Backtest Engine
16. M4D Walk-Forward Validation
17. M4E Research Report
18. M4F Research-Based Decision Gates
19. M5A Local Operator Console Skeleton
20. M5B Decision Timeline
21. M5C Portfolio / Risk UI
22. M5D Health / Repair Queue
23. M5E Paper-Only Control Plane
24. M5F Automation Run Log
25. M5G Notification Artifacts
26. M6A Broker Adapter Contract V2
27. M6B Secret / Config Safety
28. M6C First Sandbox Broker Adapter
29. M6D External Paper Order Lifecycle
30. M6E Broker Reconciliation
31. M6F External Paper Execution Safety Gates
32. M6G Broker Dashboard

Do not skip a stage unless tests, docs, and reviewer approval prove it is
already complete. Archive the skip decision under `docs/reviews/`.

## Branch And PR Rules

Use one PR per milestone substage.

Preferred branch names:

- `codex/m1-finalize`
- `codex/m15-burn-in`
- `codex/m2a-sqlite-repository`
- `codex/m2b-paper-order-ledger`
- `codex/m2c-paper-fills-nav`
- `codex/m2d-risk-gates`

Continue the same pattern for later stages.

PR title format:

```text
[M2A] Add SQLite canonical repository
```

Legacy PRs may keep their existing branch names if they predate this roadmap,
but the review archive must record the exception.

## Reporting

If the run stops before M6 due to timebox or a blocking issue, write:

```text
docs/reviews/YYYY-MM-DD-autonomous-progress-report.md
```

or:

```text
docs/reviews/YYYY-MM-DD-autonomous-blocker-report.md
```

The report must include the latest completed milestone, latest merged PR, latest
open PR, exact tests run, remaining stages, and the recommended resume prompt.
