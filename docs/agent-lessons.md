# Agent Lessons Learned

## Purpose

This file records execution lessons from multi-agent work in this repository so future work can avoid repeated coordination failures and wasted time.

## 2026-04-23: Subagent Capacity and Lifecycle

### What went wrong

During multi-task execution with implementer and reviewer agents, the thread hit the subagent limit and new agent spawns started failing with:

```text
agent thread limit reached (max 6)
```

At the same time, some attempts to close agents failed with `not found`, which made the state look inconsistent.

### Root cause

The main issue was not that subagents were globally broken. The issue was that:

- several old agents were still open in the thread
- the thread has a finite agent count limit
- some agent ids were stale because those agents had already ended or been cleaned up
- `close_agent` behaves differently depending on whether an agent still exists:
  - existing agent -> returns `previous_status`
  - stale / already-gone agent -> returns `not found`

So the practical failure mode was:

- old agents consumed the available slots
- a new spawn failed because the thread was already at capacity

### What worked

The following recovery pattern was confirmed to work:

1. try closing known finished reviewers and workers
2. accept that some ids may return `not found`
3. retry a minimal spawn
4. verify that a tiny explorer can complete and then be closed

Once enough stale open agents were cleared, spawning and closing worked again.

### Guardrails

From now on:

- close implementer and reviewer agents after each task is actually complete
- do not keep old reviewers around once their findings are integrated
- treat `not found` on close as normal for stale agent ids, not as proof the tool is broken
- if spawn fails with the thread limit error, clear old agents before assuming a deeper platform issue
- avoid building large review trees when the task can be completed inline more cheaply

### Efficiency rule

Use subagents only when they materially improve throughput or review quality.

If the work is already local, narrow, and well understood:

- prefer direct edits
- prefer one fresh reviewer instead of a stack of lingering agents

### What not to do

- do not assume a successful task automatically means the agent closed
- do not keep spawning reviewers without cleaning up prior ones
- do not interpret every `close_agent not found` result as a new bug

## Current Recommendation

For this repository, the preferred order is:

1. local implementation for narrow correctness fixes
2. one spec or code-quality review agent when needed
3. immediate cleanup of completed agents

This keeps capacity available for the cases where delegation is actually valuable.
