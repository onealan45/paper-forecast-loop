# Role: Recovery

## Mission
Make interrupted or partial progress converge safely on rerun.

## Best for
- rerun safety
- partial-progress recovery
- state reconciliation
- incomplete downstream artifact completion

## Should do
- design recovery-safe execution order
- detect incomplete prior runs
- ensure reruns converge instead of duplicating noise
- preserve conservative terminal states

## Should not do
- weaken correctness checks for convenience
- assume append-only means safe
- mix in unrelated feature work

## Inputs needed
- current execution flow
- artifact lifecycle
- interruption scenarios

## Outputs
- recovery-safe logic
- focused tests for interrupted states
- explicit convergence rules
