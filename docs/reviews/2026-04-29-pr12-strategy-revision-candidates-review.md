# PR12 Strategy Revision Candidates Review

## Scope

Branch: `codex/strategy-revision-candidates`

PR12 adds the first bounded self-evolving strategy primitive:

- failed `PaperShadowOutcome` rows with `RETIRE` or `REVISE` produce a DRAFT
  child `StrategyCard`;
- the child strategy card links to the parent card through `parent_card_id`;
- the revision records `revision_source_outcome_id` and
  `revision_failure_attributions`;
- a linked `ResearchAgenda` is created for retesting;
- CLI command `propose-strategy-revision` prints both generated artifacts.

## Reviewer

Independent reviewer subagent: `019dd5b4-6dd7-75e0-8af2-e105f28449ea`

Review policy: review only, no file edits.

## Initial Findings

### P1: Revision version bypassed outcome-level idempotency

File: `src/forecast_loop/strategy_evolution.py`

The reviewer found that `--revision-version` fed into the generated strategy
card ID, allowing the same `paper_shadow_outcome_id` to create multiple child
strategy cards and agendas. This violated PR12's outcome-level idempotency
claim.

Resolution:

- Added regression test
  `test_propose_strategy_revision_ignores_later_revision_version_for_same_outcome`.
- Updated `propose_strategy_revision` to first search existing child strategy
  cards by `parent_card_id`, `decision_basis`, and
  `parameters.revision_source_outcome_id`.
- If a revision already exists for the outcome, the function returns that card
  and its existing or newly created linked agenda, ignoring later
  `revision_version` changes.

### P2: Plan file used raw angle-bracket placeholders

File: `docs/superpowers/plans/2026-04-29-strategy-revision-candidates.md`

The reviewer found executable PowerShell examples using `<tmp>`, `<id>`,
`<path>`, and `<iso>` placeholders, which conflicts with repo command hygiene
rules.

Resolution:

- Replaced placeholder commands with concrete PowerShell variables and sample
  values.
- Replaced `<parent.version>.rev1` wording with plain prose.
- Verified no raw `<...>` placeholders remain in the plan file.

## Verification

Commands run after fixes:

```powershell
python -m pytest tests\test_research_autopilot.py tests\test_governance_docs.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- targeted tests: `22 passed`
- full test suite: `306 passed`
- compileall: passed
- CLI help: passed and lists `propose-strategy-revision`
- diff check: passed

## Final Reviewer Result

`APPROVED`

Reviewer note:

> Re-reviewed only the two fixes. The temp reproduction now returns the same
> card/version/agenda with counts `strategy_card_count=2` and `agenda_count=1`,
> and the new targeted regression passed. The plan file no longer contains raw
> `<...>` placeholders.

## Residual Risks

- PR12 creates deterministic revision candidates but does not run new
  backtests, walk-forward validation, or paper-shadow windows for them.
- The mutation rules are intentionally simple. Later stages should improve
  strategy search quality, but keep the locked evaluation path fixed.
