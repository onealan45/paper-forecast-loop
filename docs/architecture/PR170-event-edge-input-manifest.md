# PR170: Event-Edge Input Manifest

## Context

PR169 stopped duplicate decision-blocker research when the data window was
unchanged. The remaining weakness was event-edge reuse: it could only compare
same-symbol freshness through an input watermark. That prevents obvious stale
reuse, but it does not explain exactly which events, market reactions, and
candles produced the evaluation.

For strategy research, that is too opaque. The system should show and compare
the exact evidence set behind event-edge metrics.

## Decision

`EventEdgeEvaluation` now records an input manifest:

- `input_event_ids`
- `input_reaction_check_ids`
- `input_candle_ids`
- `input_watermark`

The event-edge builder writes these fields from the samples used to create the
evaluation. The decision-blocker planner uses the manifest when present:

- manifested event-edge evidence must match the current event ids, reaction
  check ids, and candle ids for the same symbol/event family/event type/horizon;
- the evaluation and its recorded input watermark must be fresh relative to the
  current manifest watermark;
- future-dated evaluations are ignored;
- legacy evaluations without a manifest keep the PR169 watermark fallback for
  backward compatibility.

## Boundaries

- This does not change event-edge scoring math.
- This does not force a migration of old JSONL rows.
- This does not delete legacy event-edge artifacts.
- This does not change BUY/SELL gates.

## Verification

- Red/green tests:
  `python -m pytest tests\test_event_edge.py::test_build_event_edge_passes_when_after_cost_edge_is_positive -q`
  `python -m pytest tests\test_decision_research_plan.py::test_decision_blocker_research_plan_does_not_reuse_event_edge_when_manifest_mismatches -q`
- Focused suites:
  `python -m pytest tests\test_event_edge.py -q`
  `python -m pytest tests\test_decision_research_plan.py -q`
  `python -m pytest tests\test_decision_research_executor.py -q`
