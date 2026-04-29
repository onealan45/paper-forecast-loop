# Strategy Lineage Agenda Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `create-lineage-research-agenda` CLI command that turns the latest strategy lineage `next_research_focus` into a persisted research agenda artifact.

**Architecture:** Add a focused `forecast_loop.lineage_agenda` module that resolves the latest symbol-scoped strategy lineage, builds a deterministic `ResearchAgenda`, and saves it through the existing repository. The CLI is the only new entrypoint; it writes exactly one agenda artifact and prints the agenda plus lineage summary as JSON.

**Tech Stack:** Python dataclasses, existing JSONL repository, existing strategy research resolver, existing strategy lineage summary builder, pytest.

---

### File Structure

- Create: `src/forecast_loop/lineage_agenda.py`
  - Owns lineage-to-agenda conversion.
  - Keeps CLI thin.
- Modify: `src/forecast_loop/cli.py`
  - Adds `create-lineage-research-agenda` parser, dispatch, and output.
- Test: `tests/test_operator_console.py`
  - Reuses existing strategy lineage fixtures to prove the CLI creates a research agenda from the latest lineage focus.
- Modify: `README.md`
  - Documents the command.
- Modify: `docs/PRD.md`
  - Records PR41 behavior.
- Modify: `docs/architecture/alpha-factory-research-background.md`
  - Adds PR41 to roadmap/context.
- Create: `docs/architecture/PR41-strategy-lineage-agenda.md`
  - Explains design and non-goals.
- Create: `docs/reviews/2026-04-30-pr41-strategy-lineage-agenda-review.md`
  - Archive reviewer result.

### Task 1: RED CLI Coverage

**Files:**
- Modify: `tests/test_operator_console.py`

- [x] **Step 1: Add failing CLI test**

Add a test after the existing `strategy-lineage` CLI tests:

```python
def test_create_lineage_research_agenda_cli_persists_focus_agenda(tmp_path, capsys):
    now = datetime(2026, 4, 29, 9, 0, tzinfo=UTC)
    repository = JsonFileRepository(tmp_path)
    _seed_visible_strategy_research(repository, now)
    _seed_visible_revision_candidate(repository, now + timedelta(minutes=10))
    _seed_visible_strategy_lineage(repository, now + timedelta(minutes=20))
    _seed_visible_second_generation_strategy_lineage(repository, now + timedelta(minutes=30))

    assert main(
        [
            "create-lineage-research-agenda",
            "--storage-dir",
            str(tmp_path),
            "--symbol",
            "BTC-USD",
            "--created-at",
            "2026-04-29T10:00:00+00:00",
        ]
    ) == 0
    payload = json.loads(capsys.readouterr().out)

    agenda = payload["research_agenda"]
    assert agenda["symbol"] == "BTC-USD"
    assert agenda["decision_basis"] == "strategy_lineage_research_agenda"
    assert agenda["priority"] == "HIGH"
    assert agenda["strategy_card_ids"] == [
        "strategy-card:visible",
        "strategy-card:visible-revision",
        "strategy-card:visible-second-revision",
    ]
    assert "停止加碼此 lineage" in agenda["hypothesis"]
    assert "drawdown_breach" in agenda["hypothesis"]
    assert payload["strategy_lineage"]["next_research_focus"] == "停止加碼此 lineage，優先研究 drawdown_breach 的修正或新策略。"
    assert len(repository.load_research_agendas()) == 1
```

- [x] **Step 2: Add missing-lineage error test**

Add:

```python
def test_create_lineage_research_agenda_cli_rejects_missing_lineage(tmp_path, capsys):
    tmp_path.mkdir(exist_ok=True)

    with pytest.raises(SystemExit) as exc_info:
        main(["create-lineage-research-agenda", "--storage-dir", str(tmp_path), "--symbol", "BTC-USD"])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "strategy lineage not found for symbol: BTC-USD" in captured.err
    assert "Traceback" not in captured.err
```

- [x] **Step 3: Run RED tests**

```powershell
python -m pytest tests\test_operator_console.py -k "lineage_research_agenda" -q
```

Expected: fail because `create-lineage-research-agenda` is not recognized.

### Task 2: Minimal Implementation

**Files:**
- Create: `src/forecast_loop/lineage_agenda.py`
- Modify: `src/forecast_loop/cli.py`

- [x] **Step 1: Add lineage agenda module**

Create:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from forecast_loop.models import ResearchAgenda
from forecast_loop.storage import ArtifactRepository
from forecast_loop.strategy_lineage import StrategyLineageSummary, build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain


@dataclass(frozen=True, slots=True)
class LineageResearchAgendaResult:
    research_agenda: ResearchAgenda
    strategy_lineage: StrategyLineageSummary

    def to_dict(self) -> dict:
        return {
            "research_agenda": self.research_agenda.to_dict(),
            "strategy_lineage": asdict(self.strategy_lineage),
        }


def create_lineage_research_agenda(
    *,
    repository: ArtifactRepository,
    created_at: datetime,
    symbol: str,
) -> LineageResearchAgendaResult:
    symbol = symbol.upper()
    strategy_cards = [item for item in repository.load_strategy_cards() if symbol in item.symbols]
    paper_shadow_outcomes = [item for item in repository.load_paper_shadow_outcomes() if item.symbol == symbol]
    chain = resolve_latest_strategy_research_chain(
        symbol=symbol,
        strategy_cards=strategy_cards,
        experiment_trials=repository.load_experiment_trials(),
        locked_evaluations=repository.load_locked_evaluation_results(),
        split_manifests=repository.load_split_manifests(),
        leaderboard_entries=repository.load_leaderboard_entries(),
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=repository.load_research_agendas(),
        research_autopilot_runs=repository.load_research_autopilot_runs(),
    )
    summary = build_strategy_lineage_summary(
        root_card=chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    if summary is None:
        raise ValueError(f"strategy lineage not found for symbol: {symbol}")
    root_card = next(item for item in strategy_cards if item.card_id == summary.root_card_id)
    agenda = ResearchAgenda(
        agenda_id=ResearchAgenda.build_id(
            symbol=symbol,
            title=f"Lineage 研究焦點：{root_card.strategy_name}",
            hypothesis=_hypothesis(summary),
            target_strategy_family=root_card.strategy_family,
            strategy_card_ids=[summary.root_card_id, *summary.revision_card_ids],
        ),
        created_at=created_at,
        symbol=symbol,
        title=f"Lineage 研究焦點：{root_card.strategy_name}",
        hypothesis=_hypothesis(summary),
        priority=_priority(summary),
        status="OPEN",
        target_strategy_family=root_card.strategy_family,
        strategy_card_ids=[summary.root_card_id, *summary.revision_card_ids],
        expected_artifacts=[
            "strategy_revision_or_new_strategy",
            "locked_evaluation",
            "leaderboard_entry",
            "paper_shadow_outcome",
        ],
        acceptance_criteria=[
            "research focus is derived from latest strategy lineage evidence",
            "candidate strategy is evaluated through locked protocol",
            "paper-shadow outcome updates lineage verdict",
        ],
        blocked_actions=["real_order_submission", "automatic_live_execution"],
        decision_basis="strategy_lineage_research_agenda",
    )
    repository.save_research_agenda(agenda)
    return LineageResearchAgendaResult(research_agenda=agenda, strategy_lineage=summary)


def _hypothesis(summary: StrategyLineageSummary) -> str:
    latest_action = summary.latest_recommended_strategy_action or "UNKNOWN"
    return (
        f"下一步研究焦點：{summary.next_research_focus} "
        f"Lineage verdict：{summary.performance_verdict}；"
        f"latest action：{latest_action}。"
    )


def _priority(summary: StrategyLineageSummary) -> str:
    if summary.latest_recommended_strategy_action in {"QUARANTINE_STRATEGY", "REVISE_STRATEGY"}:
        return "HIGH"
    if summary.performance_verdict in {"惡化", "偏弱", "證據不足"}:
        return "HIGH"
    if summary.performance_verdict in {"改善", "偏強"}:
        return "MEDIUM"
    return "LOW"
```

- [x] **Step 2: Add CLI parser and dispatch**

In `src/forecast_loop/cli.py`, import `create_lineage_research_agenda`, add parser:

```python
lineage_agenda_cmd = subparsers.add_parser("create-lineage-research-agenda")
lineage_agenda_cmd.add_argument("--storage-dir", required=True)
lineage_agenda_cmd.add_argument("--symbol", default="BTC-USD")
lineage_agenda_cmd.add_argument("--created-at")
```

Dispatch:

```python
if args.command == "create-lineage-research-agenda":
    return _create_lineage_research_agenda(args)
```

Function:

```python
def _create_lineage_research_agenda(args) -> int:
    storage_dir = Path(args.storage_dir)
    if not storage_dir.exists():
        raise ValueError(f"storage directory does not exist: {storage_dir}")
    if not storage_dir.is_dir():
        raise ValueError(f"storage path is not a directory: {storage_dir}")
    now = _parse_datetime(args.created_at) if args.created_at else datetime.now(tz=UTC)
    result = create_lineage_research_agenda(
        repository=JsonFileRepository(storage_dir),
        created_at=now,
        symbol=args.symbol,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False))
    return 0
```

- [x] **Step 3: Run GREEN tests**

```powershell
python -m pytest tests\test_operator_console.py -k "lineage_research_agenda" -q
```

Expected: pass.

### Task 3: Docs, Review, Gates

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/architecture/alpha-factory-research-background.md`
- Create: `docs/architecture/PR41-strategy-lineage-agenda.md`
- Create: `docs/reviews/2026-04-30-pr41-strategy-lineage-agenda-review.md`
- Modify: `docs/superpowers/plans/2026-04-30-strategy-lineage-agenda.md`

- [x] **Step 1: Update docs**

Document that `create-lineage-research-agenda` persists the latest lineage next-focus as a research agenda, not as a decision or order.

- [x] **Step 2: Run full gates**

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```

- [x] **Step 3: Reviewer subagent**

Ask reviewer subagent to inspect only. Required result: PASS with no blocking finding.

- [ ] **Step 4: Archive review and publish**

Commit:

```text
Create research agendas from strategy lineage
```

PR title:

```text
[PR41] Create research agendas from strategy lineage
```
