# Strategy Lineage CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `strategy-lineage` CLI command that emits the latest strategy lineage summary as JSON, including performance verdict and next research focus.

**Architecture:** Reuse the existing strategy research resolver and `build_strategy_lineage_summary`. The command is read-only and writes no artifacts. It exists so automation/research steps can consume lineage evidence without scraping dashboard/operator-console HTML.

**Tech Stack:** Python argparse CLI, JSON output via dataclass `asdict`, existing `JsonFileRepository`, pytest.

---

### Task 1: CLI Command

**Files:**
- Modify: `src/forecast_loop/cli.py`
- Test: `tests/test_operator_console.py`

- [x] **Step 1: Write failing CLI test**

Seed existing strategy research/lineage fixtures, run:

```python
main(["strategy-lineage", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])
```

Assert JSON contains:

```python
payload["strategy_lineage"]["root_card_id"] == "strategy-card:visible"
payload["strategy_lineage"]["performance_verdict"] == "惡化"
payload["strategy_lineage"]["next_research_focus"] == "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
payload["strategy_lineage"]["outcome_count"] == 3
```

- [x] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests\test_operator_console.py -k "strategy_lineage_cli" -q
```

Expected: fail because `strategy-lineage` is not a recognized command.

- [x] **Step 3: Implement CLI**

Add parser:

```python
strategy_lineage_cmd = subparsers.add_parser("strategy-lineage")
strategy_lineage_cmd.add_argument("--storage-dir", required=True)
strategy_lineage_cmd.add_argument("--symbol", default="BTC-USD")
```

Add dispatch:

```python
if args.command == "strategy-lineage":
    return _strategy_lineage(args)
```

Implement `_strategy_lineage(args)`:

```python
repository = JsonFileRepository(args.storage_dir)
chain = resolve_latest_strategy_research_chain(repository, args.symbol.upper())
summary = build_strategy_lineage_summary(
    root_card=chain.strategy_card,
    strategy_cards=repository.load_strategy_cards(),
    paper_shadow_outcomes=repository.load_paper_shadow_outcomes(),
)
print(json.dumps({"strategy_lineage": asdict(summary) if summary else None}, ensure_ascii=False))
return 0
```

- [x] **Step 4: Re-run CLI test**

Expected: pass.

### Task 2: Docs, Review, Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/architecture/PR40-strategy-lineage-cli.md`
- Create: `docs/reviews/2026-04-30-pr40-strategy-lineage-cli-review.md`

- [x] **Step 1: Update docs**

Document that `strategy-lineage` exposes the read-only lineage summary JSON for automation/research consumers.

- [x] **Step 2: Run gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```

- [x] **Step 3: Subagent review and archive**

Use reviewer subagent only. Archive PASS or findings under `docs/reviews/`.

- [ ] **Step 4: Commit and publish**

Commit:

```text
Add strategy lineage CLI
```

PR:

```text
[PR40] Add strategy lineage CLI
```
