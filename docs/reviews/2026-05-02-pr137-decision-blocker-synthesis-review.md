# PR137 Decision Blocker Synthesis Review

Date: 2026-05-02

Reviewer: Hegel, reviewer subagent

Branch: `codex/pr137-decision-blocker-synthesis`

## Scope

PR137 improves strategy-decision readability. When a decision is blocked by weak research evidence, the visible reason summary now names the main research blockers instead of only showing the generic baseline failure sentence.

This PR does not change BUY/SELL gates, execution behavior, broker behavior, or runtime automation state.

## Initial Findings

### P1: Dashboard lead still overrode the blocker synthesis

The dashboard helper still mapped `model_not_beating_baseline` to the old generic baseline explanation, which meant the new synthesized blocker summary existed in the decision artifact but did not appear in the primary strategy panel.

Resolution: `_display_strategy_reason()` now uses `decision.reason_summary` when it contains the synthesized `主要研究阻擋` phrase, with the older generic text retained as fallback.

### P2: Dashboard test could pass from raw JSON instead of visible strategy text

The first dashboard regression test asserted against the full HTML, so it could pass if the blocker text appeared only inside collapsed raw metadata.

Resolution: `test_dashboard_uses_specific_blocked_decision_reason_summary` now scopes assertions to the rendered `id="strategy"` section and verifies the old generic baseline sentence is not used there.

## Final Reviewer Result

APPROVED.

Reviewer conclusion:

- The P1 and P2 findings are resolved.
- The strategy lead now contains the synthesized research blocker summary.
- No new blocking findings were found.
- BUY/SELL gate behavior was not changed by this PR.

## Verification

Commands run by implementation before final review:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_uses_specific_blocked_decision_reason_summary -q
python -m pytest tests\test_m1_strategy.py tests\test_research_gates.py tests\test_dashboard.py::test_dashboard_uses_specific_blocked_decision_reason_summary tests\test_dashboard.py::test_dashboard_prioritizes_strategy_decision_and_health_status -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- Targeted dashboard regression: `1 passed`
- Related decision/dashboard gate set: `41 passed`
- Full test suite: `519 passed`
- Compileall: passed
- CLI help: passed
- Diff check: only CRLF warnings

Reviewer also reran:

- Targeted pytest subset: `4 passed`
- Custom render inspection: strategy lead contained the blocker summary and did not contain the old generic copy
- Full test suite: `519 passed`
- Compileall: passed
- CLI help: passed
- Diff check: only CRLF warnings

## Remaining Risk

No blocking risk remains for PR137. The main remaining product gap is broader: active strategy decisions still need deeper research evidence, stronger predictive modeling, and richer UX exposure of concrete strategy hypotheses in future milestones.
