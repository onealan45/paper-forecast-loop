# PR13 Strategy Revision Visibility Review

## Scope

Branch: `codex/strategy-revision-visibility`

PR13 makes PR12 DRAFT strategy revision candidates visible in the static
dashboard and local operator console.

Implemented behavior:

- `resolve_latest_strategy_research_chain` now resolves a separate latest
  `StrategyRevisionCandidate`.
- Dashboard strategy research panel shows `策略修正候選`.
- Operator console research page and overview preview show the latest DRAFT
  revision card, source paper-shadow failure, parent strategy, mutation rules,
  and retest agenda.
- Existing parent autopilot chain remains separate from latest revision
  candidate visibility.

## Reviewer

Independent reviewer subagent: `019dd5c7-44b9-7241-aaaa-45c7924f0636`

Review policy: review only, no file edits.

## Initial Findings

### P2: Restrict revision agenda fallback

File: `src/forecast_loop/strategy_research.py`

The reviewer found that revision-candidate resolution fell back to any latest
agenda containing the revision card when no
`paper_shadow_strategy_revision_agenda` existed. That could render an unrelated
agenda as the PR13 `Retest Agenda`.

Resolution:

- Added regression test
  `test_dashboard_does_not_label_unrelated_agenda_as_revision_retest`.
- Removed arbitrary agenda fallback.
- Revision candidates now link only research agendas with
  `decision_basis == "paper_shadow_strategy_revision_agenda"`.

### P2: Research page rendered the same revision twice

File: `src/forecast_loop/operator_console.py`

The reviewer found that the operator console research page rendered the same
`策略修正候選` block twice, which could imply two revision candidates.

Resolution:

- Added assertion `research_html.count("策略修正候選") == 1`.
- Removed the duplicate lower panel and kept one placement near the research
  action.

## Verification

Commands run after fixes:

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_does_not_label_unrelated_agenda_as_revision_retest tests\test_dashboard.py::test_dashboard_shows_strategy_revision_candidate_even_when_autopilot_chain_points_to_parent -q
python -m pytest tests\test_operator_console.py::test_operator_console_shows_strategy_revision_candidate -q
python -m pytest tests\test_dashboard.py tests\test_operator_console.py tests\test_research_autopilot.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- dashboard targeted tests: `2 passed`
- operator console targeted test: `1 passed`
- related tests: `49 passed`
- full test suite: `309 passed`
- compileall: passed
- CLI help: passed
- diff check: passed

## Final Reviewer Result

`APPROVED`

Reviewer note:

> Re-reviewed only the two fixes. The agenda fallback is removed, unrelated
> agendas are no longer labeled as retest agendas, and the operator console
> research page now renders `策略修正候選` once.

## Residual Risk

- Broader multi-candidate ordering is still only covered indirectly by latest
  created-at selection. A future stage can add a full revision-candidate
  timeline instead of only the latest candidate.
