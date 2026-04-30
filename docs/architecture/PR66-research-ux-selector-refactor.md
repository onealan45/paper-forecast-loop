# PR66: Research UX Selector Refactor

## Context

PR65 hardened the dashboard and operator console against invalid cross-sample
autopilot evidence. The same selector rules existed in both files, which made
future drift likely.

## Decision

Move the shared research-UX selector logic into
`src/forecast_loop/research_ux_selectors.py`.

The shared module now owns:

- latest revision/replacement retest autopilot run selection;
- latest linked cross-sample autopilot run selection;
- current-lineage cross-sample agenda filtering;
- cross-sample run validity checks;
- shared lookup helpers for strategy cards and research agendas.

Dashboard and operator console keep their rendering code local, but they no
longer maintain separate implementations of the evidence-selection contract.

## Verification

- `python -m pytest .\tests\test_dashboard.py .\tests\test_operator_console.py -q`

