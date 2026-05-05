# PR152 - Agenda-Anchored Digest Keeps Shadow Outcome Context

## Context

Decision-blocker research agendas can be created after a strategy already has
paper-shadow evidence. Before this change, `StrategyResearchDigest` used the
newer agenda as the latest research anchor and returned only the strategy card
plus agenda. That made the digest say there was no paper-shadow result even
when the same strategy card already had a valid outcome.

## Decision

When an agenda is the latest research anchor, the strategy chain now keeps the
latest same-card, same-symbol research evidence rather than treating the agenda
as a replacement for the strategy state. If that latest evidence is a
`PaperShadowOutcome`, the digest's primary strategy state continues to show the
shadow outcome grade, after-cost excess return, and recommended strategy
action. If the same card has a newer trial, locked evaluation, or leaderboard
entry that is still waiting for a fresh paper-shadow outcome, the digest stays
in `WAIT_FOR_PAPER_SHADOW_OUTCOME` and does not reattach an older outcome.

## Why

The dashboard and operator console should expose concrete strategy evidence,
not hide it behind a newer research task. A newer decision-blocker agenda means
"what to research next"; it does not erase the latest known paper-shadow result
for the strategy.

## Verification

- Added a regression test for a newer decision-blocker agenda that points to a
  strategy card with an existing paper-shadow outcome.
- Added a regression test for a newer same-card retest / leaderboard that is
  still waiting for paper-shadow evidence, so older outcomes cannot mask the
  waiting state.
- Verified the active BTC-USD dashboard refresh now shows the linked
  `paper-shadow-outcome:b8824f418cf79b18` as `BLOCKED / QUARANTINE` instead of
  reporting that no paper-shadow result exists.
