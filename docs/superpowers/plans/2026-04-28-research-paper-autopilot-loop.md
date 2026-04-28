# PR9 Research/Paper Autopilot Loop Plan

## Goal

Add the first auditable research/paper autopilot loop record after PR8.

PR9 should connect existing artifacts into one inspectable loop:

`agenda -> strategy card -> experiment trial -> locked evaluation -> leaderboard -> paper decision -> paper-shadow outcome -> next research action`

This PR does not generate strategies automatically, does not run a scheduler, and
does not mutate strategy cards. It creates the artifact contract that later
workers can use to run the loop repeatedly.

## New Artifacts

### `research_agendas.jsonl`

One agenda records:

- agenda id;
- created at;
- symbol;
- title;
- hypothesis;
- priority;
- status;
- target strategy family;
- linked strategy card ids;
- expected artifacts;
- acceptance criteria;
- blocked actions;
- decision basis.

### `research_autopilot_runs.jsonl`

One run records:

- run id;
- created at;
- symbol;
- agenda id;
- strategy card id;
- experiment trial id;
- locked evaluation id;
- leaderboard entry id;
- strategy decision id;
- paper-shadow outcome id;
- ordered steps;
- loop status;
- next research action;
- blocked reasons;
- decision basis.

## CLI

Create agenda:

```powershell
python .\run_forecast_loop.py create-research-agenda --storage-dir .\paper_storage\manual-research --symbol BTC-USD --title "Trend candidate" --hypothesis "Trend continuation" --strategy-family trend_following --strategy-card-id strategy-card:example
```

Record autopilot loop from existing artifacts:

```powershell
python .\run_forecast_loop.py record-research-autopilot-run --storage-dir .\paper_storage\manual-research --agenda-id research-agenda:example --strategy-card-id strategy-card:example --experiment-trial-id experiment-trial:example --locked-evaluation-id locked-evaluation:example --leaderboard-entry-id leaderboard-entry:example --strategy-decision-id decision:example --paper-shadow-outcome-id paper-shadow-outcome:example
```

## Loop Status Rules

- Missing required evidence -> `BLOCKED`.
- Blocked leaderboard or locked evaluation -> `BLOCKED`.
- Paper-shadow `PROMOTION_READY` -> `READY_FOR_OPERATOR_REVIEW`.
- Paper-shadow `RETIRE` -> `REVISION_REQUIRED`.
- Paper-shadow `QUARANTINE` -> `QUARANTINED`.
- Missing paper-shadow outcome -> `WAITING_FOR_SHADOW_OUTCOME`.

## Storage And Health

Support JSONL and SQLite parity:

- save/load agendas;
- save/load autopilot runs;
- migrate/export/db-health counts;
- health-check duplicate ids and missing links.

## Out Of Scope

- No automatic strategy generation.
- No strategy card mutation.
- No scheduler.
- No browser UI redesign.
- No broker execution.
- No live trading or real capital movement.

## Tests

Add tests for:

- agenda JSONL round trip;
- autopilot run from promotion-ready outcome;
- autopilot run blocks missing or blocked evidence;
- CLI creates agenda and run;
- health-check detects broken links;
- SQLite migration/export parity.

## Acceptance

- `python -m pytest -q`
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
- `python .\run_forecast_loop.py --help`
- `git diff --check`
- Independent reviewer subagent approves.
- Review is archived under `docs/reviews/`.
