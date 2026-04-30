# PR58: Execute Lineage Cross-Sample Task

## Context

PR56 made improving replacement retests visible to the lineage task planner, and
PR57 persisted the resulting worker prompt/rationale in automation run logs.
The remaining gap was execution: `execute-lineage-research-next-task` could
draft a replacement hypothesis, but it rejected
`verify_cross_sample_persistence` even when that was the next concrete research
task.

## Decision

`verify_cross_sample_persistence` now executes by creating a dedicated
`ResearchAgenda` with `decision_basis =
lineage_cross_sample_validation_agenda`.

The agenda is a handoff artifact, not a claim that validation already passed.
It records:

- the lineage root strategy id
- the latest lineage outcome marker
- the replacement-aware worker prompt when applicable
- required downstream artifacts: locked evaluation, walk-forward validation, and
  paper-shadow outcome
- acceptance criteria that keep confidence increases blocked until fresh-sample
  evidence is linked

The task planner treats a matching
`lineage_cross_sample_validation_agenda` as completion for the
`verify_cross_sample_persistence` task when the agenda references the same root
card and latest lineage outcome.

## Scope

Implemented:

- plan-level detection of existing cross-sample validation agendas
- executor support for `verify_cross_sample_persistence`
- automation-run evidence for the executed task
- regression tests for ready, executed, and already-complete cross-sample task
  states

Deferred:

- actual locked evaluation execution for the fresh sample
- walk-forward validation execution
- paper-shadow outcome generation for the cross-sample agenda
- confidence or promotion changes based on the agenda alone

## Verification

- `python -m pytest tests\test_lineage_research_plan.py tests\test_lineage_research_executor.py -q`

