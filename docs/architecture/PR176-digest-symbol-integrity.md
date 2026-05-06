# PR176: Strategy Research Digest Symbol Integrity

## Context

PR175 made `health-check` validate that the latest
`StrategyResearchDigest` evidence ids point to existing local artifacts. That
prevents broken dashboard/operator-console evidence links, but existence alone
does not prove the linked artifact belongs to the same market symbol.

A BTC digest linking an ETH backtest, walk-forward validation, event-edge
evaluation, strategy decision, or research agenda would be more dangerous than
a missing link: the UX would show plausible evidence for the wrong research
context.

## Decision

`health-check` now checks symbol integrity for known, symbol-bearing digest
artifact links on the latest digest per symbol.

The following mismatch findings are blocking and repair-required:

- `strategy_research_digest_symbol_mismatch_strategy_card`
- `strategy_research_digest_symbol_mismatch_paper_shadow_outcome`
- `strategy_research_digest_symbol_mismatch_research_autopilot_run`
- `strategy_research_digest_symbol_mismatch_decision`
- `strategy_research_digest_symbol_mismatch_backtest_result`
- `strategy_research_digest_symbol_mismatch_walk_forward`
- `strategy_research_digest_symbol_mismatch_event_edge`
- `strategy_research_digest_symbol_mismatch_leaderboard_entry`
- `strategy_research_digest_symbol_mismatch_experiment_trial`
- `strategy_research_digest_symbol_mismatch_research_agenda`

For `StrategyCard`, the digest symbol must be present in `card.symbols`.
For other checked artifacts, `artifact.symbol` must match the digest symbol
case-insensitively.

## Boundaries

- `locked-evaluation` is still existence-only in this PR because the model
  does not carry a direct `symbol` field. Its semantic integrity can be checked
  later through linked trial/card/split artifacts if needed.
- Historical non-latest digests remain out of the operational health gate, as
  decided in PR175.
- This does not change digest generation, dashboard rendering, or strategy
  decision gating.

## Verification

Red/green test:

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_detects_latest_strategy_research_digest_symbol_mismatches -q
```

Focused gate:

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_detects_strategy_research_digest_missing_artifact_links tests\test_m1_strategy.py::test_health_check_allows_strategy_research_digest_placeholder_evidence_ids tests\test_m1_strategy.py::test_health_check_allows_strategy_research_digest_persisted_research_evidence tests\test_m1_strategy.py::test_health_check_scopes_strategy_research_digest_link_gate_to_latest_symbol_digest tests\test_m1_strategy.py::test_health_check_detects_latest_strategy_research_digest_symbol_mismatches -q
```

Full gate before merge:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
```
