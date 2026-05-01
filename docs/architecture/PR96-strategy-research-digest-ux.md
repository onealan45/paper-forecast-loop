# PR96: Strategy Research Digest UX

## Context

PR95 created `StrategyResearchDigest` as a compact machine-readable strategy
handoff. Without UX visibility, the artifact still required CLI or JSONL
inspection, and the operator console/dashboard could continue to feel like
artifact tables instead of a strategy research cockpit.

## Decision

Load the latest digest for the active symbol and surface it in:

- dashboard strategy research panel;
- operator console research page;
- operator console overview strategy preview.

The panel shows:

- digest id;
- strategy name and status;
- latest research summary;
- paper-shadow grade / after-cost excess;
- recommended strategy action;
- concentrated failure attribution labels;
- lineage revision/outcome counts;
- next research rationale;
- linked evidence artifact ids.

## Scope

Included:

- Snapshot fields for `latest_strategy_research_digest`.
- Dashboard rendering for a `策略研究摘要` card.
- Operator console rendering for the same digest in research and overview
  contexts.
- Regression tests for both surfaces.

Excluded:

- dashboard redesign;
- strategy mutation or autopilot execution;
- digest generation inside render paths;
- broker/exchange execution.

## Verification

- `python -m pytest tests/test_dashboard.py::test_dashboard_surfaces_strategy_research_digest_summary tests/test_operator_console.py::test_operator_console_surfaces_strategy_research_digest_in_research_and_overview -q`
- `python -m pytest tests/test_dashboard.py tests/test_operator_console.py tests/test_strategy_research_digest.py -q`
