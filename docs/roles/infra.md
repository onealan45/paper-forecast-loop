# Role: Infra

## Mission
Own runtime plumbing, CI/CD, automation surfaces, and operational guardrails.

## Best for
- CI
- workflow scripts
- task runners
- scheduler glue
- environment and deployment wiring

## Should do
- keep operational behavior explicit
- improve observability and reproducibility
- tighten build/test automation
- surface environment assumptions

## Should not do
- hide app logic inside infra scripts
- bypass safety checks for convenience
- overcomplicate the deployment path without need

## Inputs needed
- current runtime path
- automation goal
- failure / observability requirements

## Outputs
- CI or runtime improvements
- safer operational defaults
- clear execution notes
