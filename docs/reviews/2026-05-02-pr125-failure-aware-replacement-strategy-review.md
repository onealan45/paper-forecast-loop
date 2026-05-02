# PR125 Failure-Aware Replacement Strategy Review

## Reviewer

- Subagent: James (`019de601-a1f4-7433-9067-0fe52cd68eff`)
- Scope: `codex/pr125-failure-aware-replacement-strategy` relative to `main`

## Verdict

APPROVED

## Initial Blocking Finding

### P1: Null paper-shadow metric crashes replacement drafting

`PaperShadowOutcome.max_adverse_excursion` is nullable, but the first
implementation called `float(outcome.max_adverse_excursion)` when a drawdown or
adverse-excursion failure attribution was present. A valid source outcome with
`max_adverse_excursion=None` would crash replacement drafting.

## Fix

- Added regression coverage:
  `test_execute_lineage_research_next_task_handles_missing_adverse_excursion_metric`.
- Kept deterministic exposure reduction through `max_position_multiplier=0.5`.
- Only writes `max_adverse_excursion_limit` when the source metric exists.

## Final Reviewer Notes

The reviewer confirmed:

- The original P1 is fixed.
- The regression passes.
- No lineage/retest/dashboard, live trading, secrets, runtime artifact, or
  automatic-promotion risk was found.

## Verification

Main validation after fix:

- `python -m pytest -q` -> `498 passed`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed with only CRLF warnings
