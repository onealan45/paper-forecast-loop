# PR27: Revision Retest Completed Chain Visibility

## Context

PR20 through PR26 made the revision retest chain executable from protocol
locking through explicit paper-shadow outcome recording. The resolver that feeds
the dashboard and operator console still treated only `PENDING` revision retest
trials as visible retest scaffolds.

That meant a completed retest chain could look unfinished from the strategy
research surface even though the artifacts already existed.

## Change

PR27 updates `resolve_latest_strategy_research_chain` so the latest DRAFT
revision candidate can attach a matching `PASSED` retest trial as well as a
pending scaffold.

The resolver now derives coarse remaining artifact requirements from the
available retest evidence:

- locked split manifest
- linked backtest result
- linked walk-forward validation
- locked evaluation result
- leaderboard entry
- paper-shadow outcome

When all linked evidence exists, `retest_next_required_artifacts` is empty.

## Non-Goals

- No strategy promotion is added.
- No retest execution behavior is changed.
- No broker, sandbox, or live execution path is added.
- No runtime storage artifacts are committed.

## Verification

The regression test seeds a complete PR20-PR26 retest chain, records explicit
shadow-window observations, and asserts the resolver reports the revision retest
trial as `PASSED` with no remaining required artifacts.
