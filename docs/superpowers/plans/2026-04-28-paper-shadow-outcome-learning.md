# PR8 Paper-Shadow Outcome Learning Plan

## Goal

Add the first paper-shadow outcome learning layer after PR7 leaderboard gates.

PR8 should let the repo record what happened after a rankable leaderboard candidate
entered a paper-shadow window, then produce an auditable recommendation:

- continue paper-shadow;
- revise the strategy;
- retire the strategy;
- quarantine the strategy candidate;
- mark the candidate as promotion-ready inside research artifacts.

This PR does not run a full autopilot loop and does not mutate strategy cards
automatically.

## Scope

### Add artifact

Add `paper_shadow_outcomes.jsonl`.

Each outcome links:

- leaderboard entry;
- locked evaluation;
- strategy card;
- experiment trial;
- symbol;
- shadow window;
- observed return;
- benchmark return;
- excess return after costs;
- max adverse excursion;
- turnover;
- outcome grade;
- failure attribution labels;
- recommended promotion stage;
- recommended strategy action;
- blocked reasons;
- decision basis.

### Add service

Add a small paper-shadow service that:

- validates linked leaderboard/evaluation/trial/card artifacts;
- rejects unrelated or blocked leaderboard entries;
- computes excess return;
- assigns outcome grade;
- assigns failure attribution;
- outputs recommendation without automatically changing strategy state.

### Add CLI

Add:

```powershell
python .\run_forecast_loop.py record-paper-shadow-outcome --storage-dir <dir> --leaderboard-entry-id <id> --window-start <iso> --window-end <iso> --observed-return <float> --benchmark-return <float>
```

Optional flags:

- `--max-adverse-excursion`
- `--turnover`
- `--created-at`
- `--note`

### Add persistence

Support JSONL and SQLite repository parity:

- save/load paper-shadow outcomes;
- migrate JSONL to SQLite;
- export SQLite to JSONL;
- include in db-health counts.

### Add health-check links

Health-check should detect:

- duplicate paper-shadow outcome id;
- missing leaderboard entry;
- missing locked evaluation;
- missing strategy card;
- missing experiment trial;
- symbol mismatch between outcome and leaderboard entry.

## Out Of Scope

- No automatic strategy card mutation.
- No full research autopilot loop.
- No dashboard redesign.
- No live trading or real capital movement.
- No real broker execution.
- No event-driven paper-shadow scheduler.

## Tests First

Add tests for:

- JSONL round trip.
- SQLite parity.
- positive paper-shadow result becomes promotion-ready.
- negative result becomes retire or revise.
- blocked / unrankable leaderboard entry cannot be promotion-ready.
- health-check detects broken paper-shadow links.
- CLI records outcome and prints JSON.

## Acceptance

- Full local gate passes:
  - `python -m pytest -q`
  - `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - `python .\run_forecast_loop.py --help`
  - `git diff --check`
- Independent reviewer subagent approves.
- Review is archived under `docs/reviews/`.
- No runtime/secrets files are staged.
