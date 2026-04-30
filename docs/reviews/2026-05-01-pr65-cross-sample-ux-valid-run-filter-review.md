# PR65 Cross-Sample UX Valid Run Filter Review

## Scope

- Branch: `codex/cross-sample-ux-valid-run-filter`
- Reviewer: Harvey subagent (`reviewer` role)
- Review date: 2026-05-01

## Reviewer Result

Final result: `APPROVED`

Initial reviewer pass found one blocking issue mirrored across dashboard and
operator console: the replacement/revision retest selector still accepted a
generic `strategy_card` step, so a newer same-card cross-sample run could
masquerade as retest closure.

## Fix After Review

- Added dashboard and operator-console regressions where a newer same-card
  generic cross-sample autopilot run must not replace the valid replacement
  retest run.
- Changed the retest selector to require the run's `experiment_trial_id` to
  point at a revision-retest protocol trial for the exact revision or
  replacement strategy card.
- Preserved repair-oriented retest visibility: blocked revision retest runs can
  still be shown when they are tied to a valid retest trial.

## Verification

- `python -m pytest .\tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_retest_scaffold .\tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_retest_scaffold .\tests\test_dashboard.py::test_dashboard_shows_lineage_cross_sample_validation_agenda .\tests\test_operator_console.py::test_operator_console_shows_lineage_cross_sample_validation_agenda -q` -> 4 passed
- `python -m pytest .\tests\test_dashboard.py .\tests\test_operator_console.py -q` -> 66 passed
- `python -m pytest -q` -> 426 passed
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py` -> passed
- `python .\run_forecast_loop.py --help` -> passed
- `git diff --check` -> passed
- `git ls-files .codex paper_storage reports output .env` -> empty

## Remaining Risk

- The dashboard and operator console still contain parallel selector logic. This
  is acceptable for PR65 because the regression coverage covers both surfaces,
  but future cleanup should extract shared research-UX selection helpers.

