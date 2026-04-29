# PR16 Revision Retest Task Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only revision retest task plan that converts a DRAFT strategy revision and its retest scaffold into explicit next research tasks.

**Architecture:** Add a small planner module that reads existing JSONL artifacts, derives task status, and emits command arguments only when prerequisites exist. The planner must not write artifacts, run backtests, or fabricate locked evaluation outcomes.

**Tech Stack:** Python dataclasses, current `ArtifactRepository` protocol, existing JSONL repository, existing CLI parser, pytest.

---

## Scope

PR16 advances the self-evolving strategy flow from "retest scaffold is visible" to "the system knows the next evidence-building step." It remains read-only: it does not run `backtest`, `walk-forward`, `evaluate-leaderboard-gate`, or `record-paper-shadow-outcome`.

The task planner will classify each stage as:

- `completed`: a usable artifact already exists.
- `ready`: prerequisites exist and an exact CLI argument list can be shown.
- `blocked`: prerequisites are missing, so no executable command should be shown.

## File Structure

- Create `src/forecast_loop/revision_retest_plan.py`
  - Owns `RevisionRetestTask`, `RevisionRetestTaskPlan`, and `build_revision_retest_task_plan`.
  - Reads existing artifacts through `ArtifactRepository`.
  - Emits JSON-safe dictionaries with explicit artifact IDs, missing inputs, command arguments, and next task.
- Modify `src/forecast_loop/cli.py`
  - Adds `revision-retest-plan`.
  - Prints `{"revision_retest_task_plan": ...}`.
- Modify `tests/test_research_autopilot.py`
  - Adds regression tests for read-only planning, split-aware command generation, and CLI JSON output.
- Modify docs after green tests
  - Add `docs/architecture/PR16-revision-retest-task-plan.md`.
  - Update `README.md`, `docs/PRD.md`, and `docs/architecture/alpha-factory-research-background.md` with the new research-task visibility.
  - Archive final reviewer output under `docs/reviews/2026-04-29-pr16-revision-retest-task-plan-review.md`.

## Task 1: Failing Tests

**Files:**
- Modify: `tests/test_research_autopilot.py`

- [ ] **Step 1: Import the wished-for API**

Add this import near the existing retest imports:

```python
from forecast_loop.revision_retest_plan import build_revision_retest_task_plan
```

- [ ] **Step 2: Add read-only missing-split test**

Append a test that creates a revision and pending retest scaffold without a locked split, snapshots JSONL file contents, calls `build_revision_retest_task_plan`, and asserts:

```python
assert plan.strategy_card_id == revision.card_id
assert plan.pending_trial_id == scaffold.experiment_trial.trial_id
assert plan.next_task_id == "lock_evaluation_protocol"
assert plan.task_by_id("create_revision_retest_scaffold").status == "completed"
assert plan.task_by_id("lock_evaluation_protocol").status == "blocked"
assert "split_window_inputs_required" in plan.task_by_id("lock_evaluation_protocol").blocked_reason
assert before_files == after_files
```

- [ ] **Step 3: Add split-aware command test**

Append a test that creates the same retest scaffold with train, validation, and holdout windows. Assert:

```python
assert plan.split_manifest_id == scaffold.split_manifest.manifest_id
assert plan.cost_model_id == scaffold.cost_model_snapshot.cost_model_id
assert plan.task_by_id("lock_evaluation_protocol").status == "completed"
assert plan.task_by_id("run_backtest").status == "ready"
assert "--start" in plan.task_by_id("run_backtest").command_args
assert "2026-03-02T00:00:00+00:00" in plan.task_by_id("run_backtest").command_args
assert plan.task_by_id("run_walk_forward").status == "ready"
assert "2026-01-01T00:00:00+00:00" in plan.task_by_id("run_walk_forward").command_args
```

- [ ] **Step 4: Add CLI output test**

Append a CLI test using `main([...])`:

```python
assert main(["revision-retest-plan", "--storage-dir", str(tmp_path), "--revision-card-id", revision.card_id, "--symbol", "BTC-USD"]) == 0
payload = json.loads(capsys.readouterr().out)
assert payload["revision_retest_task_plan"]["strategy_card_id"] == revision.card_id
assert payload["revision_retest_task_plan"]["next_task_id"] == "lock_evaluation_protocol"
```

- [ ] **Step 5: Verify RED**

Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -q
```

Expected result: FAIL because `forecast_loop.revision_retest_plan` does not exist.

## Task 2: Planner Module

**Files:**
- Create: `src/forecast_loop/revision_retest_plan.py`

- [ ] **Step 1: Add dataclasses**

Implement:

```python
@dataclass(frozen=True, slots=True)
class RevisionRetestTask:
    task_id: str
    title: str
    status: str
    required_artifact: str
    artifact_id: str | None
    command_args: list[str] | None
    blocked_reason: str | None
    missing_inputs: list[str]
    rationale: str

    def to_dict(self) -> dict: ...

@dataclass(frozen=True, slots=True)
class RevisionRetestTaskPlan:
    symbol: str
    strategy_card_id: str
    source_outcome_id: str
    pending_trial_id: str | None
    passed_trial_id: str | None
    dataset_id: str | None
    split_manifest_id: str | None
    cost_model_id: str | None
    baseline_id: str | None
    backtest_result_id: str | None
    walk_forward_validation_id: str | None
    locked_evaluation_id: str | None
    leaderboard_entry_id: str | None
    paper_shadow_outcome_id: str | None
    next_task_id: str | None
    tasks: list[RevisionRetestTask]

    def task_by_id(self, task_id: str) -> RevisionRetestTask: ...
    def to_dict(self) -> dict: ...
```

- [ ] **Step 2: Add artifact selection helpers**

Select the latest valid artifacts by `created_at`:

```python
def _latest(items):
    return max(items, key=lambda item: item.created_at) if items else None
```

Use read-only filters:

- revision card: DRAFT, `paper_shadow_strategy_revision_candidate`, symbol matches, optional card ID matches.
- source outcome: `revision_source_outcome_id` from the card, symbol matches.
- pending trial: `PENDING`, same strategy card, `revision_retest_protocol == "pr14-v1"`.
- passed trial: `PASSED`, same strategy card, same retest protocol, backtest and walk-forward IDs present.
- split manifest: same strategy card, dataset ID, symbol, status `LOCKED`.
- cost model: latest `LOCKED` cost model for the symbol.
- baseline: latest baseline evaluation for the symbol.
- backtest: passed trial linked result if available; otherwise latest result matching split holdout window.
- walk-forward: passed trial linked validation if available; otherwise latest validation matching split full window.
- locked evaluation and leaderboard: exact matching trial IDs.
- paper shadow outcome: latest matching leaderboard entry.

- [ ] **Step 3: Build tasks in fixed order**

Emit these task IDs:

```python
[
    "create_revision_retest_scaffold",
    "lock_evaluation_protocol",
    "generate_baseline_evaluation",
    "run_backtest",
    "run_walk_forward",
    "record_passed_retest_trial",
    "evaluate_leaderboard_gate",
    "record_paper_shadow_outcome",
]
```

Rules:

- `create_revision_retest_scaffold` is completed when a pending or passed retest trial exists.
- `lock_evaluation_protocol` is blocked with `split_window_inputs_required` when no split exists.
- `generate_baseline_evaluation` is ready with `decide` command when no baseline exists and a storage directory is supplied.
- `run_backtest` is ready when split exists and no matching backtest result exists.
- `run_walk_forward` is ready when split exists and no matching walk-forward validation exists.
- `record_passed_retest_trial` is ready only when baseline, backtest, and walk-forward artifacts exist but no passed retest trial exists.
- `evaluate_leaderboard_gate` is ready only when split, cost, baseline, passed trial, backtest, and walk-forward IDs exist.
- `record_paper_shadow_outcome` remains blocked until a leaderboard entry exists because observed return inputs must come from a real future shadow window.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py -q
```

Expected result: PASS.

## Task 3: CLI Wiring

**Files:**
- Modify: `src/forecast_loop/cli.py`

- [ ] **Step 1: Import planner**

```python
from forecast_loop.revision_retest_plan import build_revision_retest_task_plan
```

- [ ] **Step 2: Add parser**

Add after `create-revision-retest-scaffold`:

```python
revision_retest_plan_cmd = subparsers.add_parser("revision-retest-plan")
revision_retest_plan_cmd.add_argument("--storage-dir", required=True)
revision_retest_plan_cmd.add_argument("--revision-card-id")
revision_retest_plan_cmd.add_argument("--symbol", default="BTC-USD")
```

- [ ] **Step 3: Add handler**

```python
def _revision_retest_plan(args) -> int:
    plan = build_revision_retest_task_plan(
        repository=JsonFileRepository(args.storage_dir),
        storage_dir=args.storage_dir,
        symbol=args.symbol.upper(),
        revision_card_id=args.revision_card_id,
    )
    print(json.dumps({"revision_retest_task_plan": plan.to_dict()}, ensure_ascii=False))
    return 0
```

- [ ] **Step 4: Wire command dispatch**

```python
if args.command == "revision-retest-plan":
    return _revision_retest_plan(args)
```

- [ ] **Step 5: Verify CLI test**

Run:

```powershell
python -m pytest .\tests\test_research_autopilot.py::test_cli_revision_retest_plan_outputs_json -q
```

Expected result: PASS.

## Task 4: Docs And Review

**Files:**
- Create: `docs/architecture/PR16-revision-retest-task-plan.md`
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/reviews/2026-04-29-pr16-revision-retest-task-plan-review.md`

- [ ] **Step 1: Document behavior**

Document that `revision-retest-plan` is a read-only research planning command. It shows what to run next and what is blocked; it does not create evaluation artifacts.

- [ ] **Step 2: Run full local gates**

Run:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Expected result: all pass.

- [ ] **Step 3: Request reviewer subagent**

Use one reviewer subagent only. Scope: PR16 changes only. The reviewer must check that the planner is read-only, commands are not fake-complete, and docs match implementation.

- [ ] **Step 4: Archive review**

Write the final reviewer result to:

```text
docs/reviews/2026-04-29-pr16-revision-retest-task-plan-review.md
```

## Acceptance Criteria

- `revision-retest-plan` prints a deterministic JSON task plan.
- The planner is read-only and tests prove artifact files do not change.
- Missing split windows are clearly blocked rather than represented as a runnable command.
- Existing split manifests produce runnable `backtest` and `walk-forward` command arguments.
- The plan exposes the exact next task ID.
- Tests and compileall pass.
- Reviewer subagent approves or all findings are fixed and re-reviewed.
