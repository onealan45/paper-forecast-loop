# PR97: Strategy Research Digest Cycle Refresh

## Context

PR95 added the persisted `StrategyResearchDigest` artifact and PR96 surfaced the
latest digest in the dashboard and operator console. That made the strategy
research summary visible, but a normal `run-once --also-decide` cycle still did
not refresh the digest. Automation could therefore update forecasts, decisions,
notifications, and automation logs while the visible strategy digest stayed
stale until a separate `strategy-research-digest` command was run.

## Decision

Refresh the strategy research digest inside `run-once --also-decide` only when
the storage already contains strategy research artifacts for the requested
symbol.

Research artifacts currently mean at least one of:

- strategy card referencing the symbol;
- paper-shadow outcome for the symbol;
- research agenda for the symbol;
- research autopilot run for the symbol.

When no such artifact exists, the cycle records no digest and prints
`"strategy_research_digest_id": null`.

## Rationale

The digest should be automation-friendly and current, but fresh forecast-only
storage should not accumulate low-signal `no_strategy_card` rows every hourly
cycle. The separate `strategy-research-digest` CLI remains available for
explicit inspection or fixture generation.

## Scope

Included:

- `run-once --also-decide` digest refresh for storages with strategy research
  artifacts.
- `strategy_research_digest_id` in successful `run-once` JSON output.
- Automation step recording for completed or skipped digest refresh.
- Regression tests covering refresh and skip behavior.

Excluded:

- generating new strategy cards or agendas;
- mutating strategy hypotheses;
- dashboard render-time digest generation;
- broker/exchange execution.

## Verification

- `python -m pytest tests/test_strategy_research_digest.py -q`
- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
