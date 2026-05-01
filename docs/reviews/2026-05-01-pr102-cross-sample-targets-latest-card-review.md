# PR102 Cross-Sample Targets Latest Card Review

## Review Scope

- Branch: `codex/pr102-cross-sample-targets-latest-card`
- Reviewer subagent: Sagan (`019de34d-8cda-7db0-aafb-598f755f03cb`)
- Scope:
  - `lineage_cross_sample_validation_agenda` should always include the root strategy card.
  - If the latest lineage outcome belongs to a DRAFT revision, the agenda must also include that latest revision card.
  - If the latest lineage outcome belongs to a linked replacement, existing replacement targeting must remain valid.
  - Existing stale or polluted agendas must not be reused as completed current-target evidence.
  - No promotion, locked-evaluation, leaderboard, or paper-shadow gate may be weakened.

## Initial Review

Verdict: `APPROVED`

Blocking findings: none.

Non-blocking note: add a defensive regression for unrelated latest-card filtering.

## Follow-Up Review

Verdict: `CHANGES_REQUESTED`

Blocking finding:

- `src/forecast_loop/lineage_research_plan.py` accepted an existing agenda when
  the expected target ids were only a subset of `agenda.strategy_card_ids`.
  That allowed a polluted agenda containing `[root, latest_revision, unrelated]`
  to be treated as valid, skipping `verify_cross_sample_persistence`.

Required fix:

- Existing cross-sample agenda target matching must use exact target-set
  equality.
- Add a regression proving polluted agenda targets are ignored.

## Final Review

Verdict: `APPROVED`

Blocking findings: none.

Reviewer confirmation:

- `lineage_research_plan.py` now uses exact target-set comparison.
- The prior reproduction now returns to `verify_cross_sample_persistence=ready`
  instead of skipping to `record_cross_sample_autopilot_run`.
- No live execution, secret, runtime artifact, or gate-bypass risk was found.

## Verification

- `python -m pytest .\tests\test_lineage_research_executor.py .\tests\test_lineage_research_plan.py -q` -> `33 passed`
- `python -m pytest -q` -> `465 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with CRLF warnings only
