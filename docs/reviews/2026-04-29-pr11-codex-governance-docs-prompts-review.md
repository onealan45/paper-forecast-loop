# PR11 Codex Governance Docs And Prompts Review

Date: 2026-04-29

Branch: `codex/codex-governance-docs-prompts`

Scope:

- Add controller governance docs.
- Add Windows autopilot controller runbook.
- Add reusable controller decision, worker handoff, and final reviewer prompt
  templates.
- Add docs tests that enforce required governance contracts.
- Update README, PRD, master decision, and research background docs.

## Reviewer

Independent subagent reviewer: `Laplace`

Model / effort: `gpt-5.5`, `xhigh`

Reviewer constraints:

- Review only.
- Do not edit files.
- Use AGENTS.md rule: no self-review.

## Initial Finding

### P2: Governance docs test is too coarse

The initial review found that `tests/test_governance_docs.py` checked required
phrases only after concatenating all PR11 docs. That proved the document set had
the required terms, but did not guarantee that each critical governance doc kept
the machine gates, runtime exclusions, review archive rule, reviewer subagent
rule, or Edge browser rule.

Resolution:

- Strengthened `tests/test_governance_docs.py`.
- Added per-file checks for critical governance docs.
- Required each critical doc to keep:
  - `python -m pytest -q`
  - `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  - `python .\run_forecast_loop.py --help`
  - `git diff --check`
  - `docs/reviews/`
  - `.codex/`
  - `paper_storage/`
  - `reports/`
  - `output/`
  - `.env`
  - `secrets`
  - `reviewer subagent`
  - `APPROVED`
- Added Edge browser rule checks for human-facing governance docs.
- Updated `docs/controller/controller-governance.md` with explicit runtime and
  secret exclusion list.

## Verification Commands

```powershell
python -m pytest tests\test_governance_docs.py -q
```

Result: `5 passed`

```powershell
python -m pytest -q
```

Result: `301 passed`

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

> P2 已解。`tests/test_governance_docs.py` 現在有逐檔 critical governance
> docs 檢查，涵蓋 machine gates、`docs/reviews/`、runtime exclusions、
> reviewer subagent、`APPROVED`，也新增 Edge browser rule 測試；
> `docs/controller/controller-governance.md` 已補明確 runtime/secret
> exclusion 清單。
>
> 未發現新的 P0/P1/P2 blocking finding。
>
> APPROVED

## Runtime / Secret Check

Reviewer and local status checks found no `.env`, secrets, `.codex/`,
`paper_storage/`, `reports/`, or `output/` artifacts intended for commit.

## Decision

APPROVED for PR creation and merge after final GitHub checks pass.
