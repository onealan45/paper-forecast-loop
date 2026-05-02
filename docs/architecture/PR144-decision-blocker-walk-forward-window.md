# PR144 Decision-Blocker Walk-Forward Window

## Problem

After PR143, the decision-blocker research loop can create market-derived event
inputs and execute the first event-edge evidence task. The next blocker is
usually walk-forward validation, but the planner still treated it as
under-specified even when the storage already contained enough same-symbol
candles to define a conservative rolling validation window.

That created an avoidable manual gap: the research loop could identify the next
needed evidence, but it could not turn existing candle coverage into a concrete
operator command.

## Decision

Update `decision-blocker-research-plan` so the walk-forward task has three
explicit states:

- completed when a same-symbol `walk_forward_validation` exists at or after the
  blocker agenda timestamp;
- ready when stored same-symbol candles imported by plan time cover at least the
  minimum rolling validation window;
- blocked with `market_candles` as the missing input when that coverage is not
  available.

The ready command uses the existing `walk-forward` CLI with conservative default
windows:

- `train-size=4`
- `validation-size=3`
- `test-size=3`
- `step-size=1`

The planner remains read-only. It emits command arguments, but it does not
execute the walk-forward validation.

## Execution Boundary

`execute-decision-blocker-research-next-task` still only supports
`build_event_edge_evaluation`. If the next task is a ready walk-forward
validation, the executor fails closed with an unsupported-task error and writes
no `AutomationRun`.

This keeps PR144 scoped to safe planning. Automatic walk-forward execution can
be added later with its own tests, artifact verification, and review.

## Verification

Regression coverage proves:

- walk-forward planning stays blocked when same-symbol market candles are
  missing;
- walk-forward planning emits a concrete `walk-forward` command when candles
  cover the conservative window;
- the executor rejects ready but unsupported walk-forward tasks without writing
  a false automation-run success;
- active-like storage can now move from event-edge completion to walk-forward
  planning without hand-written start/end timestamps.
