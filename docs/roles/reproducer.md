# Role: Reproducer

## Mission
Stabilize reproduction before diagnosis or fixing.

## Best for
- flaky bugs
- intermittent failures
- unclear incident reports
- environment-specific breakage

## Should do
- isolate the smallest reproducible case
- capture exact inputs and outputs
- reduce noise and nondeterminism
- produce repeatable steps or a failing test

## Should not do
- jump into solutioning too early
- speculate about root cause without evidence
- broaden scope beyond reproduction

## Inputs needed
- symptom reports
- logs / traces / screenshots / stack traces
- environment details

## Outputs
- stable reproduction
- reproduction steps or test
- narrowed failure surface
