# PR10 Strategy-Visible UX Review

Date: 2026-04-29

Branch: `codex/strategy-visible-ux`

Scope:

- Surface concrete strategy research context in the static dashboard.
- Surface the same strategy chain in the local read-only operator console.
- Keep dashboard/operator console read-only.
- Update README and PRD so strategy-visible UX is no longer documented as deferred.

## Reviewer

Independent subagent reviewer: `Hypatia`

Model / effort: `gpt-5.5`, `xhigh`

Reviewer constraints:

- Review only.
- Do not edit files.
- Use AGENTS.md rule: no self-review.

## Initial Findings

### P1: Strategy chain artifacts can be mixed

The first review found that dashboard/operator console selected the latest
strategy card, leaderboard entry, paper-shadow outcome, agenda, and autopilot
run independently by symbol. With multiple active BTC-USD strategy chains, that
could display a mixed chain: one hypothesis, another leaderboard, and a third
shadow attribution.

Resolution:

- Added `src/forecast_loop/strategy_research.py`.
- Added `resolve_latest_strategy_research_chain`.
- Dashboard and operator console now use the same linked-ID resolver.
- Latest `ResearchAutopilotRun` is authoritative when available.
- Resolver follows `agenda_id`, `strategy_card_id`, `experiment_trial_id`,
  `locked_evaluation_id`, `leaderboard_entry_id`, and
  `paper_shadow_outcome_id`.
- Added regression tests with distractor same-symbol artifacts.

### P2: Agenda-only dashboard state is hidden

The first review found that a dashboard with only `research_agendas.jsonl` would
show an empty strategy research state.

Resolution:

- Dashboard strategy research empty-state now considers agenda.
- Added agenda-only dashboard regression test.

## Verification Commands

```powershell
python -m pytest tests\test_operator_console.py::test_research_page_uses_autopilot_linked_chain_instead_of_latest_symbol_artifacts -q
```

Result: `1 passed`

```powershell
python -m pytest tests\test_dashboard.py::test_dashboard_uses_autopilot_linked_chain_instead_of_latest_symbol_artifacts tests\test_dashboard.py::test_dashboard_strategy_research_panel_shows_agenda_only_state -q
```

Result: `2 passed`

```powershell
python -m pytest tests\test_dashboard.py tests\test_operator_console.py -q
```

Result: `29 passed`

```powershell
python -m pytest -q
```

Result: `296 passed`

```powershell
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
```

Result: passed

```powershell
python .\run_forecast_loop.py --help
```

Result: passed

```powershell
git diff --check
```

Result: passed with CRLF warnings only.

## Final Reviewer Verdict

Reviewer re-review:

> 前次 P1 已解：`resolve_latest_strategy_research_chain` 以 autopilot linked IDs
> 組鏈，dashboard/operator console 不再把同 symbol distractor artifacts 混入。
> 前次 P2 已解：dashboard empty state 已納入 agenda，agenda-only 狀態可顯示。
> 未發現新的 blocking finding。
> APPROVED

## Runtime / Secret Check

Reviewer and local status checks found no `.env`, secrets, `.codex/`,
`paper_storage/`, `reports/`, or `output/` artifacts intended for commit.

## Decision

APPROVED for PR creation and merge after final GitHub checks pass.
