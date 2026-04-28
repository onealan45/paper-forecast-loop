# PR12 Strategy Revision Candidates

## Status

Implemented as the first bounded self-evolving strategy primitive after PR11
Codex governance docs.

PR12 does not add a scheduler, model trainer, broker adapter, live execution, or
autonomous promotion path. It adds one deterministic artifact transform:

```text
failed paper-shadow outcome -> DRAFT child strategy card -> retest agenda
```

## Purpose

The user wants stronger research ability, prediction ability, and strategy
self-reflection. PR8 and PR9 already record whether a candidate strategy passed
or failed paper-shadow observation, and PR10 makes that evidence visible. The
missing next step is to convert failure attribution into a concrete research
hypothesis instead of only saying `CREATE_REVISION_AGENDA`.

PR12 makes that step explicit and testable.

## Artifact Behavior

Command:

```powershell
python .\run_forecast_loop.py propose-strategy-revision --storage-dir .\paper_storage\manual-research --paper-shadow-outcome-id paper-shadow-outcome:example --created-at 2026-04-28T14:00:00+00:00
```

The command reads:

- `paper_shadow_outcomes.jsonl`
- `strategy_cards.jsonl`

It writes or returns existing rows in:

- `strategy_cards.jsonl`
- `research_agendas.jsonl`

The generated strategy card:

- has `status=DRAFT`;
- links to the original strategy via `parent_card_id`;
- records `revision_source_outcome_id`;
- records `revision_failure_attributions`;
- clears prior backtest, walk-forward, and event-edge IDs so the revision must
  be retested;
- adds concrete entry, exit, or risk mutations from the failure attribution.

The generated research agenda:

- links only to the revision candidate;
- requires a new experiment trial, locked evaluation, leaderboard entry, and
  paper-shadow outcome;
- blocks automatic promotion without retest.

## Failure Attribution Mapping

Current deterministic mappings:

- `negative_excess_return`: require positive after-cost edge versus the active
  baseline suite before simulated entry.
- `adverse_excursion_breach`: cut simulated max position by 50% until
  paper-shadow adverse excursion returns inside limits.
- `turnover_breach`: add cooldown / minimum hold behavior to reduce churn.
- unknown attribution: add a research rule that the next locked trial must
  isolate that attribution.

These are intentionally simple. The purpose is not to discover the final
strategy. The purpose is to create a concrete, evidence-linked next hypothesis
that future research workers can test.

## Idempotency

The same paper-shadow outcome produces the same revision card ID and agenda ID.
Rerunning the command returns existing artifacts rather than duplicating rows.

## Boundaries

Allowed:

- DRAFT strategy-card creation from failed simulated outcomes;
- linked research-agenda creation;
- natural-language rule mutation when the mutation is captured in artifacts;
- later workers using these artifacts to run backtests and locked evaluations.

Not implemented:

- model training;
- automatic strategy promotion;
- automatic live or broker execution;
- hidden mutation of existing strategy cards;
- deleting or overwriting failed evidence.

The current execution boundary remains: no real orders and no real capital
movement. Within that boundary, PR12 intentionally increases strategy-learning
surface area.

## Acceptance

PR12 is complete when:

- tests prove failed paper-shadow outcomes create DRAFT child cards and retest
  agendas;
- tests prove promotion-ready outcomes do not create revisions;
- tests prove idempotency;
- CLI output includes both generated artifacts;
- README and PRD describe PR12 as current capability;
- independent reviewer subagent approves;
- review is archived under `docs/reviews/`;
- all standard machine gates pass.
