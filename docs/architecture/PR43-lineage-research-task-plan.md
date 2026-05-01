# PR43 Lineage Research Task Plan

## Purpose

PR41 persisted a lineage-derived research agenda and PR42 made that agenda
visible. PR43 turns the agenda into a machine-readable next-task plan so an
autonomous research worker can act on lineage evidence instead of only reading a
dashboard block.

## Command

```powershell
python run_forecast_loop.py lineage-research-plan --storage-dir .\paper_storage\manual-coingecko --symbol BTC-USD
```

The command is read-only and prints:

- `agenda_id`
- lineage root and latest outcome
- performance verdict
- latest recommended strategy action
- next research focus
- ordered tasks
- `next_task_id`

## Task Routing

The planner derives one immediate task from the latest lineage verdict:

- `REVISE_STRATEGY` or weak/worsening verdict -> `propose_strategy_revision`
- `QUARANTINE_STRATEGY` -> `draft_replacement_strategy_hypothesis`
- improving/strong verdict -> `verify_cross_sample_persistence`
- missing outcome evidence -> `collect_lineage_shadow_evidence`

When the next step can use an existing CLI, the plan includes `command_args`.
For quarantined lineages, the plan deliberately emits a natural-language worker
prompt instead of pretending that another automatic revision is always the best
answer.

## Action Compatibility

The existing revision flow originally accepted only `RETIRE` and `REVISE`
paper-shadow actions. PR43 also accepts `REVISE_STRATEGY`, because the lineage
surface uses that action label for revision-required strategy research. PR100
also accepts `QUARANTINE` from blocked or quarantined paper-shadow outcomes, so
the self-evolution loop can still create a DRAFT retest hypothesis from a failed
runtime seed instead of stopping at isolation. This keeps the generated
`propose-strategy-revision` command executable for weak, failed, and quarantined
research evidence.

## Non-Goals

PR43 does not:

- create or mutate a strategy card from `lineage-research-plan`
- execute the generated command automatically
- add dashboard UI for the task plan
- submit paper, sandbox, or live orders
- add real broker behavior

## Verification

Tests cover:

- ready revision command generation for `REVISE_STRATEGY`
- quarantined lineage routing to replacement strategy research
- machine-readable CLI output
- missing-agenda CLI error without traceback
- `propose-strategy-revision` accepting lineage `REVISE_STRATEGY` and
  paper-shadow `QUARANTINE` actions

Related revision and autopilot tests were also run to confirm the new action
compatibility does not regress existing revision flows.
