# Worker Handoff Template

Use this after any worker or role completes a bounded task. The goal is to make
integration review fast and to prevent stale assumptions from carrying into the
next step.

```markdown
## Worker Handoff

Role:
Branch:
Task:
Owned files:

## What Changed

- Concrete file or behavior change 1.
- Concrete file or behavior change 2.

## What Deliberately Did Not Change

- Explicitly excluded scope 1.
- Explicitly excluded scope 2.

## Assumptions

- Assumption that the controller or reviewer should know.
- Dependency on an existing artifact, command, or test.

## Remaining Risks

- Risk that remains after this task.
- Follow-up that should not block this task unless the controller decides it does.

## Tests Added Or Updated

- `tests/test_example.py::test_specific_behavior`

## Verification Commands

```powershell
python -m pytest tests\test_example.py -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

## Runtime / Secret Check

- `.codex/` not staged.
- `paper_storage/` not staged.
- `reports/` not staged.
- `output/` not staged.
- `.env` not staged.

## Handoff Decision

- Ready for integration.
- Needs controller decision.
- Blocked by specific issue.
```

## Rules

- Be specific. Do not say only that tests passed.
- Include commands and results.
- Do not include secrets or private runtime artifact contents.
- If UX browser validation is part of the task, state whether Edge was used.
