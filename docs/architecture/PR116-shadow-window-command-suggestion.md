# PR116 Shadow Window Command Suggestion

## Problem

PR112 and PR113 made blocked shadow-outcome retest tasks explain whether a
post-leaderboard candle-aligned observation window is available. The remaining
gap was operational: once `candidate_window_ready=true`, the next automation or
agent still had to parse the rationale and manually assemble the
`execute-revision-retest-next-task` command.

## Decision

`record_paper_shadow_outcome` remains a blocked task until a paper-shadow
outcome artifact is actually recorded. When the first aligned start candle and
the next required end candle both exist, the task now includes a concrete
`command_args` suggestion:

- `execute-revision-retest-next-task`
- the current storage directory
- the active revision card id
- the symbol
- `--shadow-window-start`
- `--shadow-window-end`
- `--derive-shadow-returns-from-candles`

This gives the next loop a deterministic command to execute without weakening
the executor gate.

## Boundary

This is a command suggestion, not automatic execution. The executor still
validates:

- the task is the next retest task
- shadow window start and end are present
- the window starts after the leaderboard entry exists
- the end is not in the future relative to the executor timestamp
- stored candles cover the requested window when returns are derived
- no real orders or real capital are involved

If only one post-entry candle exists, or no storage directory is available,
`command_args` stays `null`.

## Acceptance

- Incomplete shadow windows expose readiness rationale but no command.
- Complete aligned shadow windows expose the next-task command suggestion.
- The task status remains `blocked` until the outcome artifact exists.
- Existing executor safety checks remain the source of truth.
