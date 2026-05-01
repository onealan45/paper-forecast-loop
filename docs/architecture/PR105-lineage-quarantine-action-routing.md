# PR105 Lineage Quarantine Action Routing

## Purpose

Active BTC-USD storage exposed a strategy research routing bug after PR104. The
latest lineage paper-shadow outcome was still `QUARANTINE` and negative after
costs, but its excess return was slightly less bad than the prior outcome. The
lineage summary therefore labeled the trajectory as improving and the task plan
sent the lineage toward cross-sample validation.

That was not a useful research decision. A still-quarantined strategy should
not ask for broader validation before it has a new strategy hypothesis or a
clear repair path.

## Decision

Lineage routing now treats raw paper-shadow `QUARANTINE` the same way as the
older display/action code `QUARANTINE_STRATEGY`:

- next research focus says to stop adding confidence and research a fix or new
  strategy;
- lineage task plans route to `draft_replacement_strategy_hypothesis`;
- relative improvement alone is not enough to trigger cross-sample validation
  while the latest outcome remains quarantined.

The lineage summary also falls back from `failure_attributions` to
`blocked_reasons` when an outcome has no explicit attribution. This makes the
operator-facing research focus concrete instead of saying only `主要失敗`.

## Non-Goals

- Do not weaken locked evaluation, leaderboard, baseline, walk-forward, or
  paper-shadow gates.
- Do not relabel negative after-cost evidence as promotion-ready.
- Do not auto-create the replacement strategy card in this PR.
- Do not change stored artifact schemas.

## Runtime Evidence

With active BTC-USD storage, `lineage-research-plan` now reports:

- latest outcome: `paper-shadow-outcome:4869dea3bf0fe39a`;
- latest action: `QUARANTINE`;
- next task: `draft_replacement_strategy_hypothesis`;
- next focus: research the `leaderboard_entry_not_rankable` blocker or a new
  strategy.

## Verification

Added regression coverage proving:

- raw `QUARANTINE` produces stop/new-strategy next focus even when the latest
  excess return improved versus a worse prior run;
- a still-quarantined improving lineage routes to replacement strategy research
  instead of cross-sample validation;
- blocked reasons are used as concrete failure context when paper-shadow
  failure attributions are empty.
