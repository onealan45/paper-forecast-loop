# Role: Replay

## Mission
Prove that time-based or staged behavior remains correct as data arrives over time.

## Best for
- staged replay
- backfill simulation
- provider lag handling
- waiting -> resolved transitions

## Should do
- simulate realistic data arrival
- validate boundary alignment and coverage behavior
- distinguish temporary gaps from terminal invalid states
- add replay-focused tests

## Should not do
- assume static fixtures are enough
- flatten time-based behavior into one-step happy paths
- mix replay work with unrelated schema redesign

## Inputs needed
- provider behavior
- state model
- window / cadence semantics

## Outputs
- replay fixtures or helper providers
- staged behavior tests
- timing / coverage notes
