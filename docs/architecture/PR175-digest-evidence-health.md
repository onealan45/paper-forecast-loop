# PR175: Strategy Research Digest Evidence Health Gate

## Context

`StrategyResearchDigest` is the compact strategy-facing summary surfaced by
the dashboard and operator console. It links the current strategy hypothesis,
decision blocker research, and evidence artifacts through fields such as:

- `strategy_card_id`
- `paper_shadow_outcome_id`
- `autopilot_run_id`
- `decision_id`
- `evidence_artifact_ids`
- `decision_research_artifact_ids`

PR172 and PR173 tightened health checks for event-edge manifests and strategy
decision `decision_basis` evidence. The remaining gap was that a digest could
still point the UX at missing research artifacts without `health-check`
creating a repair-required finding.

## Decision

`health-check` now loads `strategy_research_digests.jsonl`, checks duplicate
`digest_id` values, and validates known evidence links on the latest digest
per symbol. This matches the dashboard/operator-console behavior: the current
digest is the evidence surface that can steer the next research action.

The following missing references are blocking and repair-required:

- `strategy_research_digest_missing_strategy_card`
- `strategy_research_digest_missing_paper_shadow_outcome`
- `strategy_research_digest_missing_research_autopilot_run`
- `strategy_research_digest_missing_decision`
- `strategy_research_digest_missing_backtest_result`
- `strategy_research_digest_missing_walk_forward`
- `strategy_research_digest_missing_event_edge`
- `strategy_research_digest_missing_locked_evaluation`
- `strategy_research_digest_missing_leaderboard_entry`
- `strategy_research_digest_missing_experiment_trial`
- `strategy_research_digest_missing_research_agenda`

The placeholders `missing`, `none`, and `null` remain valid. They mean the
research gate intentionally failed closed; they are not broken artifact links.

## Boundaries

- This does not change digest generation.
- This does not change strategy decision gating.
- This does not require every future external evidence source to be local; it
  only validates the artifact id prefixes already produced by this repo.
- Unknown evidence prefixes are ignored for forward compatibility.
- Historical non-latest digests are not blocking in this gate. They may still
  be inspected by a future storage audit/repair command, but current
  `health-check` should not stop the loop on old digest rows that are no
  longer surfaced as current strategy context.

## Verification

Red/green tests:

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_detects_strategy_research_digest_missing_artifact_links tests\test_m1_strategy.py::test_health_check_allows_strategy_research_digest_placeholder_evidence_ids -q
```

Focused gates:

```powershell
python -m pytest tests\test_m1_strategy.py::test_health_check_detects_strategy_research_digest_missing_artifact_links tests\test_m1_strategy.py::test_health_check_allows_strategy_research_digest_placeholder_evidence_ids tests\test_m1_strategy.py::test_health_check_allows_strategy_research_digest_persisted_research_evidence -q
python -m pytest tests\test_m1_strategy.py::test_health_check_scopes_strategy_research_digest_link_gate_to_latest_symbol_digest -q
python -m pytest tests\test_m1_strategy.py tests\test_strategy_research_digest.py tests\test_strategy_digest_evidence.py tests\test_m7_evidence_artifacts.py -q
```

Full gate before merge:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```
