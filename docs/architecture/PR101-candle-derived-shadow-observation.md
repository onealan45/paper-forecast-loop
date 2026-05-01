# PR101 Candle-Derived Shadow Observation

## Purpose

PR100 correctly let quarantined strategy evidence enter the revision retest
loop, but the final `record_paper_shadow_outcome` step still required manually
typed returns. That is weak for autonomous research: once a caller specifies a
completed shadow window and stored candles cover it, the system should calculate
the observation itself.

## Decision

`execute-revision-retest-next-task` now supports
`--derive-shadow-returns-from-candles` for the `record_paper_shadow_outcome`
step.

The caller must still provide:

- `--shadow-window-start`
- `--shadow-window-end`

The executor then:

- verifies the shadow window is complete relative to `--now`;
- requires stored candle coverage at both requested window boundaries;
- runs the local backtest engine over that exact window;
- records strategy return as `observed_return`;
- records buy-and-hold return as `benchmark_return`;
- records backtest max drawdown as `max_adverse_excursion` unless explicitly
  overridden;
- records backtest turnover unless explicitly overridden;
- adds `derived_from_stored_candles` to the shadow outcome notes.

## Non-Goals

- Do not infer or guess the shadow window.
- Do not use incomplete candle windows.
- Do not fabricate future shadow returns.
- Do not promote a strategy because a derived shadow observation exists.

## Why This Matters

The project direction is research-first and prediction-first. Manual return
entry is too brittle for repeated self-evolution. Candle-derived observations
make the retest loop more reproducible while preserving the important boundary:
the research agent must name the window, and the repository must already contain
enough stored market data to evaluate it.
