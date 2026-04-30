# PR54 Lineage Replacement Outcome Summary Review

Date: 2026-04-30

Reviewer: Harvey (`019ddad3-2758-75c1-bb0d-7046ffe645cc`)

## Scope

Reviewed branch `codex/lineage-replacement-outcome-summary`.

PR54 changes make root-linked replacement strategy paper-shadow outcomes count
toward the source strategy lineage summary. The review also covered dashboard
and operator-console behavior after a replacement retest outcome becomes the
lineage latest outcome.

## Initial Finding

Harvey reported one P2 finding:

- Replacement retest outcomes could become the lineage `latest_outcome_id`, but
  the dashboard and operator console still selected the replacement strategy
  card by matching `replacement_source_outcome_id == latest_outcome_id`. That
  made the replacement strategy, retest scaffold, and retest autopilot panels
  disappear after PR54 data became visible.

## Resolution

- `src/forecast_loop/dashboard.py` and
  `src/forecast_loop/operator_console.py` now resolve the latest lineage outcome
  to its `strategy_card_id` first. If that strategy card is a root-linked
  replacement, the UX keeps rendering the replacement panel.
- The old `replacement_source_outcome_id` lookup remains as a fallback for
  pre-retest replacement hypotheses.
- Dashboard and operator-console regression tests now save a replacement
  `PaperShadowOutcome`, verify it becomes the lineage latest outcome, and verify
  the replacement strategy/retest/autopilot panels still render.
- `docs/architecture/PR54-lineage-replacement-outcome-summary.md` documents the
  replacement-card identity preservation behavior.

## Verification Evidence

- `python -m pytest tests\test_dashboard.py::test_dashboard_shows_lineage_replacement_retest_scaffold -q` -> 1 passed
- `python -m pytest tests\test_operator_console.py::test_operator_console_shows_lineage_replacement_retest_scaffold -q` -> 1 passed
- `python -m pytest tests\test_strategy_lineage.py -q` -> 10 passed
- `python -m pytest tests\test_dashboard.py tests\test_operator_console.py -k "lineage or replacement" -q` -> 22 passed, 42 deselected

## Final Reviewer Result

APPROVED

No remaining blocking findings were reported by Harvey.

## Safety / Runtime Artifact Check

This review did not approve any real-order, real-capital, broker-live, secret,
or runtime artifact path. Runtime and local-only folders remain excluded from
Git scope.
