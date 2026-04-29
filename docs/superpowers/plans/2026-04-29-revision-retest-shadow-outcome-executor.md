# Revision Retest Shadow Outcome Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow `execute-revision-retest-next-task` to complete `record_paper_shadow_outcome` only when explicit shadow-window observation inputs are provided.

**Architecture:** Keep the revision retest executor as a whitelist over domain functions. The task planner remains blocked by default because it must not fabricate future returns; the executor may override only the specific `shadow_window_observation_required` block when all observation inputs are supplied by CLI/API arguments.

**Tech Stack:** Python dataclasses, argparse CLI, JSONL repository, pytest.

---

## File Structure

- Modify `src/forecast_loop/revision_retest_executor.py`: add optional shadow observation inputs, branch guard, and domain call to `record_paper_shadow_outcome`.
- Modify `src/forecast_loop/cli.py`: add optional shadow observation arguments to `execute-revision-retest-next-task` and parse them.
- Modify `tests/test_research_autopilot.py`: add executor and CLI coverage for explicit shadow observation execution and blocked behavior without inputs.
- Modify `README.md`, `docs/PRD.md`, and `docs/architecture/alpha-factory-research-background.md`: document PR26.
- Create `docs/architecture/PR26-revision-retest-shadow-outcome-executor.md`: explain boundary and verification.
- Create `docs/reviews/2026-04-29-pr26-revision-retest-shadow-outcome-executor-review.md`: archive final reviewer output.

## Tasks

### Task 1: Failing Tests

- [ ] Add a test that builds the chain through `evaluate_leaderboard_gate`, calls `execute_revision_retest_next_task` without shadow inputs, and asserts it still raises `revision_retest_next_task_not_ready:record_paper_shadow_outcome`.
- [ ] Add a test that calls `execute_revision_retest_next_task` with `shadow_window_start`, `shadow_window_end`, `shadow_observed_return`, and `shadow_benchmark_return`, then asserts one `PaperShadowOutcome` is written and the after-plan is complete.
- [ ] Add a CLI test using `execute-revision-retest-next-task` with `--shadow-window-start`, `--shadow-window-end`, `--shadow-observed-return`, and `--shadow-benchmark-return`.
- [ ] Run the focused tests and confirm failure before production edits.

### Task 2: Executor Implementation

- [ ] Add optional shadow observation parameters to `execute_revision_retest_next_task`.
- [ ] Permit execution of blocked `record_paper_shadow_outcome` only when `task.blocked_reason == "shadow_window_observation_required"` and every required observation input is present.
- [ ] Call `record_paper_shadow_outcome` with the plan-linked `leaderboard_entry_id`.
- [ ] Return the new `PaperShadowOutcome.outcome_id`.
- [ ] Preserve the existing not-ready error when inputs are missing or the blocked reason is different.

### Task 3: CLI Implementation

- [ ] Add shadow observation args to `execute-revision-retest-next-task`.
- [ ] Parse datetime inputs with the existing `_parse_datetime` helper.
- [ ] Pass optional floats/strings through to the executor.
- [ ] Keep raw traceback hidden behind the existing argparse-style error path.

### Task 4: Docs And Review

- [ ] Update docs to say PR26 supports explicit shadow outcome execution while still never fabricating returns.
- [ ] Run focused tests, full tests, compileall, CLI help, and diff-check.
- [ ] Request reviewer subagent review.
- [ ] Archive approval under `docs/reviews/`.

## Acceptance Criteria

- Missing shadow observation inputs still keep `record_paper_shadow_outcome` blocked.
- Explicit observation inputs write exactly one paper shadow outcome linked to the current leaderboard entry.
- The after-plan has no next task after the shadow outcome is recorded.
- No shell/subprocess/arbitrary command args are executed.
- No live trading, broker execution, or real capital path is added.
