# Controller Governance

## Mission

This document turns the ChatGPT Pro Controller model into a repo-level operating
contract. It is for autonomous or semi-autonomous Codex work where a controller
routes tasks, records decisions, requests review, and decides whether a PR can
move forward.

The controller is not a fake runtime service. It is a documented workflow role
that produces controller decisions, worker prompts, acceptance gates, operator
digests, and review archives.

## Preflight

Before starting a milestone:

1. Read `AGENTS.md`.
2. Read the relevant architecture doc under `docs/architecture/`.
3. Read the latest review under `docs/reviews/`.
4. Check current branch and worktree:

```powershell
git status --short --branch
```

5. Confirm runtime files are not part of the intended change:

```powershell
git status --short
```

The controller must keep these paths out of staged changes:

- `.codex/`
- `paper_storage/`
- `reports/`
- `output/`
- `.env`
- secrets

Do not continue if the worktree contains unrelated user edits in files that the
milestone must modify. Stop and ask for direction only when the conflict cannot
be resolved safely.

## Controller Decision Record

Use `docs/prompts/controller-decision-template.md` for direction changes,
roadmap changes, repair escalation, branch merge decisions, or broad research
strategy changes.

Minimum fields:

- `controller_decision_id`
- `created_at`
- `decision_type`
- `scope`
- `decision`
- `rationale`
- `allowed_worker_roles`
- `blocked_actions`
- `affected_files`
- `acceptance_summary`
- `machine_gates`

## Role Routing

Choose the smallest role set that separates risk.

Use `controller + docs + verifier + reviewer` when the milestone is docs,
runbooks, prompts, governance, or process hardening.

Use `controller + feature + verifier + reviewer + docs` when adding a bounded
feature with clear acceptance criteria.

Use `controller + recovery + contract + replay + verifier + docs` for loop
correctness, artifact semantics, provider coverage, and replay behavior.

Use `controller + data + infra + verifier + docs` for ingestion, pipeline,
CI, scheduler, and automation plumbing.

Use `controller + feature + ui + verifier + docs` for user-facing UI.

The final reviewer must be a reviewer subagent, not the implementer.

## Worker Prompt Structure

Every worker prompt should include:

- repo path;
- branch name;
- role;
- explicit ownership files;
- what the worker may change;
- what the worker must not change;
- acceptance criteria;
- tests to run;
- handoff requirements.

Workers should not edit files outside their assigned ownership without asking
the controller. If ownership changes, the controller records the handoff.

## Handoff Protocol

Every handoff must state:

- what changed;
- what deliberately did not change;
- assumptions;
- remaining risks;
- tests added or updated;
- exact verification commands run and results.

Use `docs/prompts/worker-handoff-template.md` for the handoff format.

## Review Gate

Final review is required before PR merge.

Reviewer prompt requirements:

- say the reviewer is a reviewer subagent;
- say review only, no file edits;
- include scope and changed file summary;
- include machine gates already run;
- ask for P0/P1/P2 findings with file/line references when possible;
- ask for `APPROVED` only when no blocking finding remains.

Use `docs/prompts/final-reviewer-prompt.md` as the base prompt.

## Merge Gate

The controller can merge only when all conditions are true:

- `python -m pytest -q` passes.
- `python -m compileall -q src tests run_forecast_loop.py sitecustomize.py`
  passes.
- `python .\run_forecast_loop.py --help` exits successfully.
- `git diff --check` passes.
- Milestone-specific smoke tests pass.
- Reviewer subagent returns `APPROVED`.
- Review archive exists under `docs/reviews/`.
- Runtime files and secrets are not staged.
- GitHub PR checks pass.
- PR merge state is clean or mergeable after updating branch safely.

## Stop Rules

Stop instead of merging when:

- a blocking reviewer finding remains;
- tests or compileall fail after a safe repair attempt;
- a change would add real order submission, real capital movement, or committed
  secrets;
- the branch contains unrelated user edits that cannot be separated safely;
- a PR requires weakening evaluation gates after seeing results.

When stopped, write a blocker report under `docs/reviews/`.

## Operator Digest

After a completed milestone, the final user-facing digest should be in
Traditional Chinese and include:

- PR number and URL;
- merge commit;
- changed capability;
- commands run and results;
- reviewer verdict;
- runtime/secret exclusion status;
- next recommended milestone.
