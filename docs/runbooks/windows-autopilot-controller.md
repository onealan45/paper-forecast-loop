# Windows Autopilot Controller Runbook

This runbook is for local Windows PowerShell execution in this repository. It
describes how a controller should run a bounded PR from branch creation through
GitHub merge without committing runtime files or secrets.

## Preconditions

- Shell: PowerShell.
- Browser for UX checks: Edge.
- Repo path example:

```powershell
Set-Location C:\Users\User\Documents\Codex\2026-04-21-new-chat
```

- Current boundary: no real order submission, no real capital movement, no
  committed secrets.
- Research, prediction, backtesting, simulation, natural-language strategy
  control, and tool-rich automation are allowed when they do not submit real
  orders.

## Preflight

```powershell
git status --short --branch
git fetch origin
git status --short
```

If unrelated user edits are present in files you need to modify, stop and ask
how to proceed. If unrelated runtime files are present, leave them unstaged.

Never stage these paths:

- `.codex/`
- `paper_storage/`
- `reports/`
- `output/`
- `.env`

## Create Branch

Use the `codex/` prefix:

```powershell
git switch -c codex/example-milestone
```

## Implementation Discipline

For every milestone:

1. Write or update a plan under `docs/superpowers/plans/`.
2. Add tests before implementation when behavior is testable.
3. Keep docs aligned with actual implementation.
4. Use independent reviewer subagent review before merge.
5. Archive review under `docs/reviews/`.

## Required Machine Gates

Run these before commit and again after merge when practical:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Add milestone-specific smoke tests when touching CLI, storage, dashboard,
operator console, ingestion, backtest, research gates, or broker/sandbox
simulation.

## Review Request

Use a reviewer subagent. The reviewer must not edit files.

Minimum reviewer prompt content:

- branch name;
- scope;
- changed file summary;
- commands already run;
- safety/runtime exclusions;
- request P0/P1/P2 findings or `APPROVED`.

Archive the result under `docs/reviews/` before merging.

## Precise Staging

Do not use broad staging when runtime files exist. Prefer exact paths:

```powershell
git add README.md docs\PRD.md docs\architecture\example.md tests\test_example.py
git status --short
git diff --cached --check
```

Confirm the staged list does not include `.codex/`, `paper_storage/`,
`reports/`, `output/`, `.env`, or secrets.

## Commit

```powershell
git commit -m "docs: add controller governance runbook"
```

## Push And PR

```powershell
git push -u origin codex/example-milestone
gh pr create --title "[PR11] Add Codex governance docs and prompts" --body-file $env:TEMP\pr-body.md --base main --head codex/example-milestone
```

Do not create a PR before local gates pass unless the purpose is explicitly to
debug GitHub-only CI.

## GitHub CI And Merge

Inspect PR status:

```powershell
gh pr view 49 --json number,url,isDraft,mergeStateStatus,mergeable,statusCheckRollup
gh pr checks 49 --watch --interval 10
```

Merge only when checks pass and the merge state is clean or safely mergeable:

```powershell
gh pr merge 49 --merge --delete-branch
```

After merge:

```powershell
git status --short --branch
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Stop Conditions

Stop and write a blocker report under `docs/reviews/` when:

- tests fail and cannot be safely repaired;
- reviewer subagent reports an unresolved P0/P1 blocker;
- runtime or secrets would need to be committed;
- a change would submit real orders or move real capital;
- evaluation gates would be weakened after seeing results.

## Final Digest

Final user-facing reports should be Traditional Chinese and include:

- PR URL;
- merge commit;
- verification commands and results;
- reviewer verdict;
- whether runtime/secrets were excluded;
- next recommended stage.
