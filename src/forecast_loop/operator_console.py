from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from urllib.parse import urlparse

from forecast_loop.automation_step_display import display_step_artifact, display_step_name
from forecast_loop.control import PaperControlState, current_control_state
from forecast_loop.health import run_health_check
from forecast_loop.models import (
    AutomationRun,
    BacktestResult,
    BaselineEvaluation,
    ExperimentTrial,
    HealthCheckResult,
    HealthFinding,
    LeaderboardEntry,
    LockedEvaluationResult,
    NotificationArtifact,
    PaperControlEvent,
    PaperPortfolioSnapshot,
    PaperShadowOutcome,
    ResearchAgenda,
    ResearchAutopilotRun,
    RepairRequest,
    RiskSnapshot,
    SplitManifest,
    StrategyCard,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.lineage_research_plan import LineageResearchTaskPlan, build_lineage_research_task_plan
from forecast_loop.research_ux_selectors import (
    latest_autopilot_run_for_agenda as _latest_autopilot_run_for_agenda,
    latest_cross_sample_autopilot_run as _latest_cross_sample_autopilot_run,
    latest_revision_retest_autopilot_run as _latest_revision_retest_autopilot_run,
    research_agenda_by_id as _research_agenda_by_id,
    strategy_card_by_id as _strategy_card_by_id,
)
from forecast_loop.lineage_research_run_log import automation_run_matches_lineage_research_plan
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
from forecast_loop.revision_retest_run_log import automation_run_matches_revision_retest_plan
from forecast_loop.strategy_evolution import REPLACEMENT_DECISION_BASIS
from forecast_loop.strategy_lineage import StrategyLineageSummary, build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain
from forecast_loop.storage import JsonFileRepository


OPERATOR_CONSOLE_PAGES = ("overview", "decisions", "portfolio", "research", "health", "control")
LOCAL_BIND_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(slots=True)
class OperatorConsoleSnapshot:
    storage_dir: Path
    generated_at: datetime
    symbol: str
    health: HealthCheckResult
    decisions: list[StrategyDecision]
    latest_decision: StrategyDecision | None
    latest_portfolio: PaperPortfolioSnapshot | None
    latest_risk: RiskSnapshot | None
    latest_baseline: BaselineEvaluation | None
    latest_backtest: BacktestResult | None
    latest_walk_forward: WalkForwardValidation | None
    latest_strategy_card: StrategyCard | None
    latest_experiment_trial: ExperimentTrial | None
    latest_locked_evaluation: LockedEvaluationResult | None
    latest_leaderboard_entry: LeaderboardEntry | None
    latest_paper_shadow_outcome: PaperShadowOutcome | None
    latest_research_agenda: ResearchAgenda | None
    latest_research_autopilot_run: ResearchAutopilotRun | None
    latest_strategy_lineage_summary: StrategyLineageSummary | None
    latest_lineage_research_agenda: ResearchAgenda | None
    latest_lineage_research_task_plan: LineageResearchTaskPlan | None
    latest_lineage_research_task_run: AutomationRun | None
    latest_lineage_cross_sample_agenda: ResearchAgenda | None
    latest_lineage_cross_sample_autopilot_run: ResearchAutopilotRun | None
    latest_lineage_replacement_strategy_card: StrategyCard | None
    latest_lineage_replacement_retest_task_plan: RevisionRetestTaskPlan | None
    latest_lineage_replacement_retest_task_run: AutomationRun | None
    latest_lineage_replacement_retest_autopilot_run: ResearchAutopilotRun | None
    latest_strategy_revision_card: StrategyCard | None
    latest_strategy_revision_agenda: ResearchAgenda | None
    latest_strategy_revision_source_outcome: PaperShadowOutcome | None
    latest_strategy_revision_retest_trial: ExperimentTrial | None
    latest_strategy_revision_split_manifest: SplitManifest | None
    latest_strategy_revision_next_required_artifacts: list[str]
    latest_strategy_revision_retest_task_plan: RevisionRetestTaskPlan | None
    latest_strategy_revision_retest_task_run: AutomationRun | None
    latest_strategy_revision_retest_autopilot_run: ResearchAutopilotRun | None
    repair_requests: list[RepairRequest]
    control_events: list[PaperControlEvent]
    control_state: PaperControlState
    automation_runs: list[AutomationRun]
    latest_automation_run: AutomationRun | None
    notifications: list[NotificationArtifact]
    counts: dict[str, int]


def build_operator_console_snapshot(
    storage_dir: Path | str,
    *,
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> OperatorConsoleSnapshot:
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        raise ValueError(f"storage dir does not exist: {storage_path}")
    if not storage_path.is_dir():
        raise ValueError(f"storage dir is not a directory: {storage_path}")

    generated_at = now or datetime.now(tz=UTC)
    repository = JsonFileRepository(storage_path)
    health = run_health_check(
        storage_dir=storage_path,
        symbol=symbol,
        now=generated_at,
        create_repair_request=False,
    )
    forecasts = _safe_load(repository.load_forecasts)
    scores = _safe_load(repository.load_scores)
    reviews = _safe_load(repository.load_reviews)
    decisions = [item for item in _safe_load(repository.load_strategy_decisions) if item.symbol == symbol]
    portfolios = _safe_load(repository.load_portfolio_snapshots)
    risks = [item for item in _safe_load(repository.load_risk_snapshots) if item.symbol == symbol]
    baselines = [item for item in _safe_load(repository.load_baseline_evaluations) if item.symbol == symbol]
    backtests = [item for item in _safe_load(repository.load_backtest_results) if item.symbol == symbol]
    walk_forwards = [item for item in _safe_load(repository.load_walk_forward_validations) if item.symbol == symbol]
    strategy_cards = [item for item in _safe_load(repository.load_strategy_cards) if symbol in item.symbols]
    strategy_card_ids = {item.card_id for item in strategy_cards}
    experiment_trials = [item for item in _safe_load(repository.load_experiment_trials) if item.symbol == symbol]
    trial_ids = {item.trial_id for item in experiment_trials}
    all_locked_evaluations = _safe_load(repository.load_locked_evaluation_results)
    split_manifests = _safe_load(repository.load_split_manifests)
    locked_evaluations = [
        item
        for item in all_locked_evaluations
        if item.strategy_card_id in strategy_card_ids or item.trial_id in trial_ids
    ]
    leaderboard_entries = [item for item in _safe_load(repository.load_leaderboard_entries) if item.symbol == symbol]
    paper_shadow_outcomes = [item for item in _safe_load(repository.load_paper_shadow_outcomes) if item.symbol == symbol]
    research_agendas = [item for item in _safe_load(repository.load_research_agendas) if item.symbol == symbol]
    research_autopilot_runs = [item for item in _safe_load(repository.load_research_autopilot_runs) if item.symbol == symbol]
    research_chain = resolve_latest_strategy_research_chain(
        symbol=symbol,
        strategy_cards=strategy_cards,
        experiment_trials=experiment_trials,
        locked_evaluations=all_locked_evaluations,
        split_manifests=split_manifests,
        leaderboard_entries=leaderboard_entries,
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=research_agendas,
        research_autopilot_runs=research_autopilot_runs,
    )
    repair_requests = _safe_load(repository.load_repair_requests)
    control_events = _safe_load(repository.load_control_events)
    control_state = current_control_state(control_events, symbol=symbol)
    automation_runs = [item for item in _safe_load(repository.load_automation_runs) if item.symbol == symbol]
    notifications = [item for item in _safe_load(repository.load_notification_artifacts) if item.symbol == symbol]
    revision_card = research_chain.revision_candidate.strategy_card if research_chain.revision_candidate else None
    revision_task_plan = _safe_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        revision_card=revision_card,
    )
    revision_autopilot_run = _latest_revision_retest_autopilot_run(
        research_autopilot_runs,
        revision_card,
        experiment_trials,
    )
    lineage_summary = build_strategy_lineage_summary(
        root_card=research_chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )
    lineage_research_task_plan = _safe_lineage_research_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        has_lineage_agenda=_has_lineage_research_agenda(research_agendas),
    )
    if lineage_research_task_plan is not None and (
        lineage_summary is None or lineage_summary.root_card_id != lineage_research_task_plan.root_card_id
    ):
        lineage_summary = build_strategy_lineage_summary(
            root_card=_strategy_card_by_id(strategy_cards, lineage_research_task_plan.root_card_id),
            strategy_cards=strategy_cards,
            paper_shadow_outcomes=paper_shadow_outcomes,
        )
    lineage_research_agenda = _lineage_research_agenda_for_plan(research_agendas, lineage_research_task_plan)
    if lineage_research_agenda is None:
        lineage_research_agenda = _latest_lineage_research_agenda(research_agendas, lineage_summary)
    lineage_cross_sample_agenda = _lineage_cross_sample_agenda_for_plan(
        research_agendas,
        lineage_research_task_plan,
    )
    lineage_cross_sample_autopilot_run = _latest_autopilot_run_for_agenda(
        research_autopilot_runs,
        lineage_cross_sample_agenda,
        paper_shadow_outcomes,
        lineage_summary,
    )
    if lineage_cross_sample_agenda is None:
        lineage_cross_sample_autopilot_run = _latest_cross_sample_autopilot_run(
            research_autopilot_runs,
            research_agendas,
            lineage_summary,
            lineage_research_task_plan,
            paper_shadow_outcomes,
        )
    if lineage_cross_sample_autopilot_run is not None and lineage_cross_sample_agenda is None:
        lineage_cross_sample_agenda = _research_agenda_by_id(
            research_agendas,
            lineage_cross_sample_autopilot_run.agenda_id,
        )
    lineage_replacement_card = _latest_lineage_replacement_strategy_card(
        strategy_cards,
        paper_shadow_outcomes,
        lineage_research_task_plan,
    )
    lineage_replacement_retest_task_plan = _safe_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_path,
        symbol=symbol,
        revision_card=lineage_replacement_card,
    )

    return OperatorConsoleSnapshot(
        storage_dir=storage_path,
        generated_at=generated_at,
        symbol=symbol,
        health=health,
        decisions=decisions,
        latest_decision=_latest(decisions),
        latest_portfolio=_latest(portfolios),
        latest_risk=_latest(risks),
        latest_baseline=_latest(baselines),
        latest_backtest=_latest(backtests),
        latest_walk_forward=_latest(walk_forwards),
        latest_strategy_card=research_chain.strategy_card,
        latest_experiment_trial=research_chain.experiment_trial,
        latest_locked_evaluation=research_chain.locked_evaluation,
        latest_leaderboard_entry=research_chain.leaderboard_entry,
        latest_paper_shadow_outcome=research_chain.paper_shadow_outcome,
        latest_research_agenda=research_chain.research_agenda,
        latest_research_autopilot_run=research_chain.research_autopilot_run,
        latest_strategy_lineage_summary=lineage_summary,
        latest_lineage_research_agenda=lineage_research_agenda,
        latest_lineage_research_task_plan=lineage_research_task_plan,
        latest_lineage_research_task_run=_latest_lineage_research_task_run(
            automation_runs,
            lineage_research_task_plan,
        ),
        latest_lineage_cross_sample_agenda=lineage_cross_sample_agenda,
        latest_lineage_cross_sample_autopilot_run=lineage_cross_sample_autopilot_run,
        latest_lineage_replacement_strategy_card=lineage_replacement_card,
        latest_lineage_replacement_retest_task_plan=lineage_replacement_retest_task_plan,
        latest_lineage_replacement_retest_task_run=_latest_revision_retest_executor_run(
            automation_runs,
            lineage_replacement_retest_task_plan,
        ),
        latest_lineage_replacement_retest_autopilot_run=_latest_revision_retest_autopilot_run(
            research_autopilot_runs,
            lineage_replacement_card,
            experiment_trials,
        ),
        latest_strategy_revision_card=revision_card,
        latest_strategy_revision_agenda=(
            research_chain.revision_candidate.research_agenda if research_chain.revision_candidate else None
        ),
        latest_strategy_revision_source_outcome=(
            research_chain.revision_candidate.source_outcome if research_chain.revision_candidate else None
        ),
        latest_strategy_revision_retest_trial=(
            research_chain.revision_candidate.retest_trial if research_chain.revision_candidate else None
        ),
        latest_strategy_revision_split_manifest=(
            research_chain.revision_candidate.retest_split_manifest if research_chain.revision_candidate else None
        ),
        latest_strategy_revision_next_required_artifacts=(
            research_chain.revision_candidate.retest_next_required_artifacts
            if research_chain.revision_candidate
            else []
        ),
        latest_strategy_revision_retest_task_plan=revision_task_plan,
        latest_strategy_revision_retest_task_run=_latest_revision_retest_task_run(automation_runs, revision_task_plan),
        latest_strategy_revision_retest_autopilot_run=revision_autopilot_run,
        repair_requests=repair_requests,
        control_events=control_events,
        control_state=control_state,
        automation_runs=automation_runs,
        latest_automation_run=_latest(automation_runs, "completed_at"),
        notifications=notifications,
        counts={
            "forecasts": len(forecasts),
            "scores": len(scores),
            "reviews": len(reviews),
            "decisions": len(decisions),
            "orders": len(_safe_load(repository.load_paper_orders)),
            "fills": len(_safe_load(repository.load_paper_fills)),
            "repair_requests": len(repair_requests),
            "control_events": len(control_events),
            "automation_runs": len(automation_runs),
            "notifications": len(notifications),
            "backtests": len(backtests),
            "walk_forward_validations": len(walk_forwards),
            "strategy_cards": len(strategy_cards),
            "experiment_trials": len(experiment_trials),
            "split_manifests": len(split_manifests),
            "locked_evaluations": len(locked_evaluations),
            "leaderboard_entries": len(leaderboard_entries),
            "paper_shadow_outcomes": len(paper_shadow_outcomes),
            "research_agendas": len(research_agendas),
            "research_autopilot_runs": len(research_autopilot_runs),
        },
    )


def _safe_revision_retest_task_plan(
    *,
    repository: JsonFileRepository,
    storage_dir: Path,
    symbol: str,
    revision_card: StrategyCard | None,
) -> RevisionRetestTaskPlan | None:
    if revision_card is None:
        return None
    try:
        return build_revision_retest_task_plan(
            repository=repository,
            storage_dir=storage_dir,
            symbol=symbol,
            revision_card_id=revision_card.card_id,
        )
    except ValueError:
        return None


def _safe_lineage_research_task_plan(
    *,
    repository: JsonFileRepository,
    storage_dir: Path,
    symbol: str,
    has_lineage_agenda: bool,
) -> LineageResearchTaskPlan | None:
    if not has_lineage_agenda:
        return None
    try:
        return build_lineage_research_task_plan(
            repository=repository,
            storage_dir=storage_dir,
            symbol=symbol,
        )
    except ValueError:
        return None


def _has_lineage_research_agenda(agendas: list[ResearchAgenda]) -> bool:
    return any(agenda.decision_basis == "strategy_lineage_research_agenda" for agenda in agendas)


def _lineage_research_agenda_for_plan(
    agendas: list[ResearchAgenda],
    task_plan: LineageResearchTaskPlan | None,
) -> ResearchAgenda | None:
    if task_plan is None:
        return None
    return next((agenda for agenda in agendas if agenda.agenda_id == task_plan.agenda_id), None)


def _lineage_cross_sample_agenda_for_plan(
    agendas: list[ResearchAgenda],
    task_plan: LineageResearchTaskPlan | None,
) -> ResearchAgenda | None:
    if task_plan is None:
        return None
    try:
        task = task_plan.task_by_id("verify_cross_sample_persistence")
    except KeyError:
        return None
    if not task.artifact_id:
        return None
    return next(
        (
            agenda
            for agenda in agendas
            if agenda.agenda_id == task.artifact_id
            and agenda.decision_basis == "lineage_cross_sample_validation_agenda"
        ),
        None,
    )


def _latest_lineage_replacement_strategy_card(
    cards: list[StrategyCard],
    paper_shadow_outcomes: list[PaperShadowOutcome],
    task_plan: LineageResearchTaskPlan | None,
) -> StrategyCard | None:
    if task_plan is None or task_plan.latest_outcome_id is None:
        return None
    cards_by_id = {card.card_id: card for card in cards}
    latest_outcome = next(
        (outcome for outcome in paper_shadow_outcomes if outcome.outcome_id == task_plan.latest_outcome_id),
        None,
    )
    if latest_outcome is not None:
        outcome_card = cards_by_id.get(latest_outcome.strategy_card_id)
        if (
            outcome_card is not None
            and outcome_card.decision_basis == REPLACEMENT_DECISION_BASIS
            and outcome_card.parameters.get("replacement_source_lineage_root_card_id") == task_plan.root_card_id
        ):
            return outcome_card
    matches = [
        card
        for card in cards
        if card.decision_basis == REPLACEMENT_DECISION_BASIS
        and card.parameters.get("replacement_source_outcome_id") == task_plan.latest_outcome_id
        and card.parameters.get("replacement_source_lineage_root_card_id") == task_plan.root_card_id
    ]
    return max(matches, key=lambda card: card.created_at) if matches else None


def _latest_revision_retest_task_run(
    runs: list[AutomationRun],
    task_plan: RevisionRetestTaskPlan | None,
) -> AutomationRun | None:
    if task_plan is None:
        return None
    matches = [
        run
        for run in runs
        if automation_run_matches_revision_retest_plan(run, task_plan)
    ]
    return max(matches, key=lambda run: run.completed_at) if matches else None


def _latest_revision_retest_executor_run(
    runs: list[AutomationRun],
    task_plan: RevisionRetestTaskPlan | None,
) -> AutomationRun | None:
    if task_plan is None:
        return None
    matches = [
        run
        for run in runs
        if run.symbol == task_plan.symbol
        and run.provider == "research"
        and run.command == "execute-revision-retest-next-task"
        and run.decision_basis == "revision_retest_task_execution"
        and _automation_step_artifact_id(run, "revision_card") == task_plan.strategy_card_id
        and _automation_step_artifact_id(run, "source_outcome") == task_plan.source_outcome_id
    ]
    return max(matches, key=lambda run: run.completed_at) if matches else None


def _automation_step_artifact_id(run: AutomationRun, name: str) -> str | None:
    for step in run.steps:
        if step.get("name") == name:
            artifact_id = step.get("artifact_id")
            return str(artifact_id) if artifact_id is not None else None
    return None


def _latest_lineage_research_task_run(
    runs: list[AutomationRun],
    task_plan: LineageResearchTaskPlan | None,
) -> AutomationRun | None:
    if task_plan is None:
        return None
    matches = [
        run
        for run in runs
        if automation_run_matches_lineage_research_plan(run, task_plan)
    ]
    return max(matches, key=lambda run: run.completed_at) if matches else None


def _latest_lineage_research_agenda(
    agendas: list[ResearchAgenda],
    summary: StrategyLineageSummary | None,
) -> ResearchAgenda | None:
    candidates = [item for item in agendas if item.decision_basis == "strategy_lineage_research_agenda"]
    if summary is not None:
        lineage_ids = {summary.root_card_id, *summary.revision_card_ids}
        candidates = [item for item in candidates if lineage_ids.intersection(item.strategy_card_ids)]
    return max(candidates, key=lambda item: item.created_at) if candidates else None


def render_operator_console_page(
    snapshot: OperatorConsoleSnapshot,
    *,
    page: str = "overview",
) -> str:
    if page not in OPERATOR_CONSOLE_PAGES:
        raise ValueError(f"unknown operator console page: {page}")

    body = {
        "overview": _render_overview,
        "decisions": _render_decisions,
        "portfolio": _render_portfolio,
        "research": _render_research,
        "health": _render_health,
        "control": _render_control,
    }[page](snapshot)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_page_title(page)} - Paper Operator Console</title>
  <style>
    :root {{
      --ink: #16201b;
      --muted: #65706a;
      --line: #d9e0da;
      --paper: #f6f2ea;
      --panel: #fffdfa;
      --accent: #1f6f4a;
      --alert: #9d2f2f;
      --warn: #8a5d15;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(31, 111, 74, 0.14), transparent 30rem),
        linear-gradient(135deg, #f6f2ea 0%, #eef3ed 100%);
      color: var(--ink);
      font-family: Georgia, "Noto Serif TC", "Microsoft JhengHei", serif;
      line-height: 1.55;
    }}
    a {{ color: inherit; }}
    .shell {{
      display: grid;
      grid-template-columns: 15rem minmax(0, 1fr);
      min-height: 100vh;
    }}
    nav {{
      border-right: 1px solid var(--line);
      padding: 2rem 1.25rem;
      background: rgba(255, 253, 250, 0.72);
      position: sticky;
      top: 0;
      height: 100vh;
    }}
    nav h1 {{
      font-size: 1rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin: 0 0 1.5rem;
    }}
    nav a {{
      display: block;
      text-decoration: none;
      padding: 0.65rem 0.75rem;
      border-radius: 0.75rem;
      margin-bottom: 0.25rem;
      color: var(--muted);
    }}
    nav a[aria-current="page"] {{
      color: var(--ink);
      background: #e3eee6;
      border: 1px solid #c1d7c8;
    }}
    nav a:focus-visible, button:focus-visible {{
      outline: 3px solid #2f7f55;
      outline-offset: 2px;
    }}
    main {{ padding: 2.5rem; }}
    .eyebrow {{
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    h2 {{
      font-size: clamp(2rem, 4vw, 4.2rem);
      line-height: 0.96;
      margin: 0.25rem 0 1rem;
      max-width: 14ch;
    }}
    .lede {{
      color: var(--muted);
      max-width: 68rem;
      margin-bottom: 1.5rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
    }}
    .wide {{ grid-column: span 2; }}
    .panel {{
      background: rgba(255, 253, 250, 0.9);
      border: 1px solid var(--line);
      border-radius: 1.2rem;
      padding: 1.2rem;
      box-shadow: 0 18px 42px rgba(40, 50, 42, 0.08);
    }}
    .panel h3 {{ margin: 0 0 0.85rem; font-size: 1.05rem; }}
    .timeline {{
      display: grid;
      gap: 1rem;
    }}
    .decision-card {{
      border: 1px solid var(--line);
      border-radius: 1rem;
      padding: 1rem;
      background: #fffdfa;
    }}
    .decision-card header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 0.75rem;
    }}
    .decision-card h4 {{
      margin: 0;
      font-size: 1.25rem;
    }}
    .evidence-list, .conditions {{
      margin: 0.5rem 0 0;
      padding-left: 1.1rem;
    }}
    .evidence-list li, .conditions li {{
      margin: 0.25rem 0;
      overflow-wrap: anywhere;
    }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 0.65rem 0;
    }}
    .metric {{
      font-size: 2rem;
      line-height: 1;
      font-weight: 700;
    }}
    .muted {{ color: var(--muted); }}
    .status {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      border-radius: 999px;
      padding: 0.25rem 0.6rem;
      border: 1px solid var(--line);
      background: #f8fbf8;
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .status.alert {{ color: var(--alert); border-color: #e6b5b5; background: #fff4f2; }}
    .status.warn {{ color: var(--warn); border-color: #ead39d; background: #fff9e9; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      font-size: 0.92rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 0.7rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 700; }}
    code {{
      overflow-wrap: anywhere;
      font-family: "Cascadia Mono", Consolas, monospace;
      font-size: 0.85em;
    }}
    .disabled-controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.75rem;
    }}
    button {{
      border: 1px solid var(--line);
      border-radius: 0.9rem;
      padding: 0.85rem;
      background: #edf2ed;
      color: var(--muted);
      cursor: not-allowed;
    }}
    @media (max-width: 900px) {{
      .shell {{ grid-template-columns: 1fr; }}
      nav {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      main {{ padding: 1.25rem; }}
      .grid {{ grid-template-columns: 1fr; }}
      .wide {{ grid-column: span 1; }}
      .disabled-controls {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav aria-label="Operator console sections">
      <h1>Paper Console</h1>
      {_render_nav(page)}
    </nav>
    <main>
      <div class="eyebrow">本機只讀 / Paper-only</div>
      <h2>{_page_title(page)}</h2>
      <p class="lede">這是 M5A 本機 operator console skeleton。它只讀取 paper artifacts，不提供真實交易、不提交 broker/exchange order、不讀取或顯示 secrets。</p>
      {body}
      <p class="muted">產生時間：{_format_dt(snapshot.generated_at)} / Storage：<code>{escape(str(snapshot.storage_dir))}</code></p>
    </main>
  </div>
</body>
</html>
"""


def write_operator_console_page(
    *,
    storage_dir: Path | str,
    output: Path | str,
    page: str = "overview",
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> Path:
    snapshot = build_operator_console_snapshot(storage_dir, symbol=symbol, now=now)
    html = render_operator_console_page(snapshot, page=page)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _safe_load(loader) -> list:
    try:
        return loader()
    except Exception:
        return []


def serve_operator_console(
    *,
    storage_dir: Path | str,
    host: str = "127.0.0.1",
    port: int = 8765,
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> None:
    validate_local_bind_host(host)
    storage_path = Path(storage_dir)

    class OperatorConsoleHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            page = parsed.path.strip("/") or "overview"
            if page not in OPERATOR_CONSOLE_PAGES:
                self.send_error(404, "Unknown operator console page")
                return
            try:
                snapshot = build_operator_console_snapshot(storage_path, symbol=symbol, now=now)
                payload = render_operator_console_page(snapshot, page=page).encode("utf-8")
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server_class = _local_server_class(host)
    server = server_class((host, port), OperatorConsoleHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def validate_local_bind_host(host: str) -> None:
    if host not in LOCAL_BIND_HOSTS:
        allowed = ", ".join(sorted(LOCAL_BIND_HOSTS))
        raise ValueError(f"operator-console is local-only; host must be one of: {allowed}")


def local_address_family_for_host(host: str) -> socket.AddressFamily:
    validate_local_bind_host(host)
    return socket.AF_INET6 if host == "::1" else socket.AF_INET


def _local_server_class(host: str) -> type[ThreadingHTTPServer]:
    address_family = local_address_family_for_host(host)

    class LocalOnlyThreadingHTTPServer(ThreadingHTTPServer):
        pass

    LocalOnlyThreadingHTTPServer.address_family = address_family
    return LocalOnlyThreadingHTTPServer


def _render_nav(current_page: str) -> str:
    return "\n".join(
        f'<a href="/{page}"{_aria_current(page, current_page)}>{_page_title(page)}</a>'
        for page in OPERATOR_CONSOLE_PAGES
    )


def _aria_current(page: str, current_page: str) -> str:
    return ' aria-current="page"' if page == current_page else ""


def _render_overview(snapshot: OperatorConsoleSnapshot) -> str:
    decision = snapshot.latest_decision
    action = "尚無決策" if decision is None else _translate_action(decision.action)
    health_class = _status_class(snapshot.health.severity)
    tradeable = "否" if decision is None else ("是" if decision.tradeable else "否")
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>明日策略決策</h3>
    <div class="metric">{escape(action)}</div>
    <p>{escape(decision.reason_summary) if decision else "目前還沒有 strategy_decisions artifact。"}</p>
    <p class="muted">可交易：{tradeable} / 證據等級：{escape(decision.evidence_grade) if decision else "INSUFFICIENT"} / 風險：{escape(decision.risk_level) if decision else "UNKNOWN"}</p>
  </article>
  <article class="panel">
    <h3>健康狀態</h3>
    <span class="{health_class}">{escape(_translate_health(snapshot.health.status))}</span>
    <p class="muted">repair_required={str(snapshot.health.repair_required).lower()}</p>
  </article>
  <article class="panel">
    <h3>Paper Portfolio</h3>
    <div class="metric">{_format_money(snapshot.latest_portfolio.nav if snapshot.latest_portfolio else None)}</div>
    <p class="muted">曝險：{_format_pct(snapshot.latest_portfolio.gross_exposure_pct if snapshot.latest_portfolio else None)}</p>
  </article>
  <article class="panel wide">
    <h3>策略研究焦點</h3>
    {_strategy_research_preview(snapshot)}
  </article>
  <article class="panel">
    <h3>Artifact Counts</h3>
    {_render_counts(snapshot.counts)}
  </article>
  <article class="panel wide">
    <h3>Automation Run</h3>
    {_automation_run_summary(snapshot.latest_automation_run)}
  </article>
  <article class="panel wide">
    <h3>Notifications</h3>
    {_notification_summary(snapshot.notifications)}
  </article>
  <article class="panel">
    <h3>研究證據</h3>
    <p>Baseline：{_artifact_id(snapshot.latest_baseline, "baseline_id")}</p>
    <p>Backtest：{_artifact_id(snapshot.latest_backtest, "result_id")}</p>
    <p>Walk-forward：{_artifact_id(snapshot.latest_walk_forward, "validation_id")}</p>
  </article>
</section>
"""


def _render_decisions(snapshot: OperatorConsoleSnapshot) -> str:
    decisions = sorted(snapshot.decisions, key=lambda item: item.created_at, reverse=True)
    latest = decisions[0] if decisions else None
    timeline = "\n".join(_decision_card(decision, is_latest=index == 0) for index, decision in enumerate(decisions[:20]))
    if not timeline:
        timeline = '<p class="muted">目前沒有 strategy_decisions artifact。</p>'
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>最新決策</h3>
    {_latest_decision_summary(latest)}
  </article>
  <article class="panel">
    <h3>讀法</h3>
    <p>此頁把每筆 paper-only strategy decision 的理由、證據連結、失效條件與 blocked reason 展開，方便追溯判斷來源。</p>
  </article>
  <article class="panel wide">
    <h3>Decision Timeline</h3>
    <div class="timeline">{timeline}</div>
  </article>
</section>
"""


def _render_portfolio(snapshot: OperatorConsoleSnapshot) -> str:
    portfolio = snapshot.latest_portfolio
    risk = snapshot.latest_risk
    positions = portfolio.positions if portfolio else []
    position_rows = "\n".join(
        "<tr>"
        f"<td>{escape(position.symbol)}</td>"
        f"<td>{position.quantity:.8f}</td>"
        f"<td>{_format_money(position.avg_price)}</td>"
        f"<td>{_format_money(position.market_price)}</td>"
        f"<td>{_format_money(position.market_value)}</td>"
        f"<td>{_format_pct(position.position_pct)}</td>"
        f"<td>{_format_money(position.unrealized_pnl)}</td>"
        "</tr>"
        for position in positions
    )
    if not position_rows:
        position_rows = '<tr><td colspan="7">目前沒有 paper position。</td></tr>'
    risk_findings = _risk_findings(risk)
    return f"""
<section class="grid">
  <article class="panel">
    <h3>NAV / Cash / PnL</h3>
    <div class="metric">{_format_money(portfolio.nav if portfolio else None)}</div>
    <p>Cash：{_format_money(portfolio.cash if portfolio else None)}</p>
    <p>Realized PnL：{_format_money(portfolio.realized_pnl if portfolio else None)}</p>
    <p>Unrealized PnL：{_format_money(portfolio.unrealized_pnl if portfolio else None)}</p>
  </article>
  <article class="panel">
    <h3>Drawdown</h3>
    <p>Status：{_risk_status(risk)}</p>
    <p>Current：{_format_pct(risk.current_drawdown_pct if risk else None)}</p>
    <p>Max：{_format_pct(risk.max_drawdown_pct if risk else None)}</p>
    <p>Recommended：{escape(risk.recommended_action) if risk else "UNKNOWN"}</p>
  </article>
  <article class="panel">
    <h3>Exposure</h3>
    <p>Gross：{_format_pct(portfolio.gross_exposure_pct if portfolio else None)}</p>
    <p>Net：{_format_pct(portfolio.net_exposure_pct if portfolio else None)}</p>
    <p>Position：{_format_pct(risk.position_pct if risk else None)}</p>
  </article>
  <article class="panel wide">
    <h3>Risk Gates</h3>
    <table>
      <thead><tr><th>Gate</th><th>Current</th><th>Limit / Trigger</th></tr></thead>
      <tbody>
        <tr><td>Position</td><td>{_format_pct(risk.position_pct if risk else None)}</td><td>{_format_pct(risk.max_position_pct if risk else None)}</td></tr>
        <tr><td>Gross exposure</td><td>{_format_pct(risk.gross_exposure_pct if risk else None)}</td><td>{_format_pct(risk.max_gross_exposure_pct if risk else None)}</td></tr>
        <tr><td>Reduce-risk drawdown</td><td>{_format_pct(risk.current_drawdown_pct if risk else None)}</td><td>{_format_pct(risk.reduce_risk_drawdown_pct if risk else None)}</td></tr>
        <tr><td>Stop-new-entries drawdown</td><td>{_format_pct(risk.current_drawdown_pct if risk else None)}</td><td>{_format_pct(risk.stop_new_entries_drawdown_pct if risk else None)}</td></tr>
      </tbody>
    </table>
    <p>Findings：{risk_findings}</p>
  </article>
  <article class="panel wide">
    <h3>Positions</h3>
    <table>
      <thead><tr><th>Symbol</th><th>Quantity</th><th>Avg Price</th><th>Market Price</th><th>Market Value</th><th>Position %</th><th>Unrealized PnL</th></tr></thead>
      <tbody>{position_rows}</tbody>
    </table>
  </article>
</section>
"""


def _render_research(snapshot: OperatorConsoleSnapshot) -> str:
    baseline = snapshot.latest_baseline
    backtest = snapshot.latest_backtest
    walk_forward = snapshot.latest_walk_forward
    card = snapshot.latest_strategy_card
    trial = snapshot.latest_experiment_trial
    evaluation = snapshot.latest_locked_evaluation
    leaderboard = snapshot.latest_leaderboard_entry
    outcome = snapshot.latest_paper_shadow_outcome
    agenda = snapshot.latest_research_agenda
    autopilot = snapshot.latest_research_autopilot_run
    lineage = snapshot.latest_strategy_lineage_summary
    cross_sample_panel = _lineage_cross_sample_agenda_panel(
        snapshot.latest_lineage_cross_sample_agenda,
        snapshot.latest_lineage_cross_sample_autopilot_run,
    )
    replacement_panel = _lineage_replacement_strategy_panel(
        snapshot.latest_lineage_replacement_strategy_card,
        snapshot.latest_lineage_replacement_retest_task_plan,
        snapshot.latest_lineage_replacement_retest_task_run,
        snapshot.latest_lineage_replacement_retest_autopilot_run,
    )
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>目前策略假設</h3>
    <p class="metric">{escape(card.strategy_name if card else "尚無策略卡")}</p>
    <p>{escape(card.hypothesis if card else "目前沒有 strategy_cards artifact。")}</p>
    <div class="badge-row">
      <span class="status">Family {escape(card.strategy_family if card else "n/a")}</span>
      <span class="status">Version {escape(card.version if card else "n/a")}</span>
      <span class="status">Status {escape(card.status if card else "n/a")}</span>
    </div>
    <p>ID：{_artifact_id(card, "card_id")}</p>
    <p>Signal：{escape(card.signal_description if card else "n/a")}</p>
    <h4>參數</h4>
    {_dict_rows(card.parameters if card else {})}
  </article>
  <article class="panel">
    <h3>下一步研究動作</h3>
    <div class="metric">{escape(autopilot.next_research_action if autopilot else "n/a")}</div>
    <p>Run：{_artifact_id(autopilot, "run_id")}</p>
    <p>Status：{escape(autopilot.loop_status if autopilot else "n/a")}</p>
    <p>Blocked：</p>
    {_plain_list(autopilot.blocked_reasons if autopilot else [])}
  </article>
  {_revision_candidate_panel(snapshot, wide=False)}
  {_strategy_lineage_panel(lineage)}
  {_lineage_research_agenda_panel(snapshot.latest_lineage_research_agenda)}
  {_lineage_research_task_plan_panel(snapshot.latest_lineage_research_task_plan)}
  {_lineage_research_task_run_panel(snapshot.latest_lineage_research_task_run)}
  {cross_sample_panel}
  {replacement_panel}
  <article class="panel">
    <h3>Leaderboard</h3>
    <p>ID：{_artifact_id(leaderboard, "entry_id")}</p>
    <p>Rankable：{"是" if leaderboard and leaderboard.rankable else "否"}</p>
    <p>alpha_score：{_format_number(leaderboard.alpha_score if leaderboard else None)}</p>
    <p>Promotion：{escape(leaderboard.promotion_stage if leaderboard else "n/a")}</p>
    <p>Blocked：</p>
    {_plain_list(leaderboard.blocked_reasons if leaderboard else [])}
  </article>
  <article class="panel wide">
    <h3>Evidence Gates</h3>
    <p>ID：{_artifact_id(evaluation, "evaluation_id")}</p>
    <p>Passed：{"是" if evaluation and evaluation.passed else "否"} / Rankable：{"是" if evaluation and evaluation.rankable else "否"} / alpha_score：{_format_number(evaluation.alpha_score if evaluation else None)}</p>
    <p>Blocked：</p>
    {_plain_list(evaluation.blocked_reasons if evaluation else [])}
    <h4>Gate Metrics</h4>
    {_dict_rows(evaluation.gate_metrics if evaluation else {})}
  </article>
  <article class="panel">
    <h3>Baseline</h3>
    <p>ID：{_artifact_id(baseline, "baseline_id")}</p>
    <p>Sample：{baseline.sample_size if baseline else "n/a"}</p>
    <p>Model edge：{_format_number(baseline.model_edge if baseline else None)}</p>
  </article>
  <article class="panel">
    <h3>Backtest</h3>
    <p>ID：{_artifact_id(backtest, "result_id")}</p>
    <p>Return：{_format_pct(backtest.strategy_return if backtest else None)}</p>
    <p>Benchmark：{_format_pct(backtest.benchmark_return if backtest else None)}</p>
    <p>Max DD：{_format_pct(backtest.max_drawdown if backtest else None)}</p>
  </article>
  <article class="panel">
    <h3>Walk-forward</h3>
    <p>ID：{_artifact_id(walk_forward, "validation_id")}</p>
    <p>Windows：{walk_forward.window_count if walk_forward else "n/a"}</p>
    <p>Excess：{_format_pct(walk_forward.average_excess_return if walk_forward else None)}</p>
    <p>Overfit flags：{escape(", ".join(walk_forward.overfit_risk_flags) if walk_forward and walk_forward.overfit_risk_flags else "none")}</p>
  </article>
  <article class="panel">
    <h3>Paper-shadow 歸因</h3>
    <p>ID：{_artifact_id(outcome, "outcome_id")}</p>
    <p>Grade：{escape(outcome.outcome_grade if outcome else "n/a")}</p>
    <p>Excess after costs：{_format_pct(outcome.excess_return_after_costs if outcome else None)}</p>
    <p>Recommended：{escape(outcome.recommended_strategy_action if outcome else "n/a")}</p>
    <p>Failure attribution：</p>
    {_plain_list(outcome.failure_attributions if outcome else [])}
  </article>
  <article class="panel wide">
    <h3>策略規則</h3>
    <h4>進場規則</h4>
    {_plain_list(card.entry_rules if card else [])}
    <h4>出場規則</h4>
    {_plain_list(card.exit_rules if card else [])}
    <h4>風控規則</h4>
    {_plain_list(card.risk_rules if card else [])}
    <h4>資料需求</h4>
    {_plain_list(card.data_requirements if card else [])}
  </article>
  <article class="panel">
    <h3>Experiment Trial</h3>
    <p>ID：{_artifact_id(trial, "trial_id")}</p>
    <p>Status：{escape(trial.status if trial else "n/a")}</p>
    <p>Dataset：<code>{escape(trial.dataset_id if trial and trial.dataset_id else "n/a")}</code></p>
    <h4>Metric Summary</h4>
    {_dict_rows(trial.metric_summary if trial else {})}
  </article>
  <article class="panel wide">
    <h3>Research Agenda</h3>
    <p>ID：{_artifact_id(agenda, "agenda_id")}</p>
    <p>Title：{escape(agenda.title if agenda else "n/a")}</p>
    <p>Hypothesis：{escape(agenda.hypothesis if agenda else "n/a")}</p>
    <p>Acceptance：</p>
    {_plain_list(agenda.acceptance_criteria if agenda else [])}
    <p>Blocked actions：</p>
    {_plain_list(agenda.blocked_actions if agenda else [])}
  </article>
  <article class="panel wide">
    <h3>Autopilot Steps</h3>
    {_autopilot_steps(autopilot)}
  </article>
</section>
"""


def _lineage_research_agenda_panel(agenda: ResearchAgenda | None) -> str:
    if agenda is None or agenda.decision_basis != "strategy_lineage_research_agenda":
        return ""
    return f"""
  <article class="panel wide">
    <h3>Lineage 研究 agenda</h3>
    <p>ID：{_artifact_id(agenda, "agenda_id")}</p>
    <p>Priority：{escape(agenda.priority)}</p>
    <p>Basis：{escape(agenda.decision_basis)}</p>
    <p>Hypothesis：{escape(agenda.hypothesis)}</p>
    <h4>Acceptance</h4>
    {_plain_list(agenda.acceptance_criteria)}
  </article>
"""


def _lineage_research_task_plan_panel(plan: LineageResearchTaskPlan | None) -> str:
    if plan is None:
        return ""
    next_task = plan.task_by_id(plan.next_task_id) if plan.next_task_id else None
    command = " ".join(next_task.command_args) if next_task and next_task.command_args else "無"
    required_artifact = display_step_artifact(
        "next_task_required_artifact",
        next_task.required_artifact if next_task else None,
    )
    missing_inputs = (
        display_step_artifact("next_task_missing_inputs", ", ".join(next_task.missing_inputs))
        if next_task and next_task.missing_inputs
        else "無"
    )
    return f"""
  <article class="panel wide">
    <h3>Lineage 下一個研究任務</h3>
    <p>Task：<code>{escape(next_task.task_id if next_task else "none")}</code> / {escape(next_task.status if next_task else "completed")}</p>
    <p>Required artifact：<code>{escape(required_artifact)}</code></p>
    <p>Blocked reason：{escape(next_task.blocked_reason if next_task and next_task.blocked_reason else "none")}</p>
    <p>Missing inputs：<code>{escape(missing_inputs)}</code></p>
    <p>Command args：<code>{escape(command)}</code></p>
    <h4>Worker Prompt</h4>
    <p>{escape(next_task.worker_prompt if next_task else "none")}</p>
    <h4>Rationale</h4>
    <p>{escape(next_task.rationale if next_task else "none")}</p>
    <p class="muted">只顯示，不執行。</p>
  </article>
"""


def _lineage_research_task_run_panel(run: AutomationRun | None) -> str:
    if run is None:
        return ""
    return f"""
  <article class="panel wide">
    <h3>最新 lineage task run log</h3>
    <p>Status：<span class="{_automation_status_class(run.status)}">{escape(run.status)}</span></p>
    <p>Run ID：<code>{escape(run.automation_run_id)}</code></p>
    <p>Command：<code>{escape(run.command)}</code></p>
    <p>Completed：{escape(run.completed_at.isoformat())}</p>
    {_automation_steps(run)}
    <p class="muted">這是 lineage research task plan 的稽核紀錄；只顯示，不執行。</p>
  </article>
"""


def _lineage_cross_sample_agenda_panel(
    agenda: ResearchAgenda | None,
    autopilot_run: ResearchAutopilotRun | None,
) -> str:
    if agenda is None or agenda.decision_basis != "lineage_cross_sample_validation_agenda":
        return ""
    return f"""
  <article class="panel wide">
    <h3>Lineage cross-sample validation agenda</h3>
    <p>ID：{_artifact_id(agenda, "agenda_id")}</p>
    <p>Priority：{escape(agenda.priority)}</p>
    <p>Basis：{escape(agenda.decision_basis)}</p>
    <h4>Strategy cards</h4>
    {_plain_list(agenda.strategy_card_ids)}
    <h4>Hypothesis</h4>
    <p>{escape(agenda.hypothesis)}</p>
    <h4>Expected artifacts</h4>
    {_plain_list(agenda.expected_artifacts)}
    <h4>Acceptance</h4>
    {_plain_list(agenda.acceptance_criteria)}
    <h4>Linked autopilot run</h4>
    <p>Run：{_artifact_id(autopilot_run, "run_id")} / {escape(autopilot_run.loop_status if autopilot_run else "尚未記錄")}</p>
    <p>Shadow outcome：<code>{escape(autopilot_run.paper_shadow_outcome_id if autopilot_run and autopilot_run.paper_shadow_outcome_id else "none")}</code></p>
    <p>Next research action：{escape(autopilot_run.next_research_action if autopilot_run else "等待 fresh-sample 驗證完成")}</p>
    <p class="muted">這是 fresh sample 驗證交接，不代表 locked evaluation、walk-forward 或 paper-shadow 已通過。</p>
  </article>
"""


def _lineage_replacement_strategy_panel(
    card: StrategyCard | None,
    retest_plan: RevisionRetestTaskPlan | None,
    retest_run: AutomationRun | None,
    autopilot_run: ResearchAutopilotRun | None,
) -> str:
    if card is None:
        return ""
    source_outcome_id = str(card.parameters.get("replacement_source_outcome_id") or "none")
    root_card_id = str(card.parameters.get("replacement_source_lineage_root_card_id") or "none")
    attributions = card.parameters.get("replacement_failure_attributions", [])
    attribution_list = [str(item) for item in attributions] if isinstance(attributions, list) else [str(attributions)]
    scaffold_task = retest_plan.task_by_id("create_revision_retest_scaffold") if retest_plan else None
    next_task = retest_plan.task_by_id(retest_plan.next_task_id) if retest_plan and retest_plan.next_task_id else None
    return f"""
  <article class="panel wide">
    <h3>Lineage 替代策略假說</h3>
    <p class="metric">{escape(card.strategy_name)}</p>
    <p>ID：{_artifact_id(card, "card_id")} / {escape(card.status)}</p>
    <p>Basis：{escape(card.decision_basis)}</p>
    <p>來源 lineage：<code>{escape(root_card_id)}</code></p>
    <p>來源 outcome：<code>{escape(source_outcome_id)}</code></p>
    <h4>Failure attribution</h4>
    {_plain_list(attribution_list)}
    <h4>替代策略假說</h4>
    <p>{escape(card.hypothesis)}</p>
    <h4>Signal</h4>
    <p>{escape(card.signal_description)}</p>
    <h4>Entry / Exit / Risk</h4>
    {_plain_list(card.entry_rules + card.exit_rules + card.risk_rules)}
    <h4>Parameters</h4>
    {_dict_rows(card.parameters)}
    <h4>替代策略 Retest Scaffold</h4>
    <p>Trial：<code>{escape(retest_plan.pending_trial_id if retest_plan and retest_plan.pending_trial_id else "尚未建立")}</code></p>
    <p>Dataset：<code>{escape(retest_plan.dataset_id if retest_plan and retest_plan.dataset_id else "n/a")}</code></p>
    <p>Scaffold status：{escape(scaffold_task.status if scaffold_task else "無 plan")}</p>
    <p>Retest kind：<code>{escape(_replacement_retest_kind(retest_plan))}</code></p>
    <p>Next task：<code>{escape(next_task.task_id if next_task else "none")}</code> / {escape(next_task.status if next_task else "completed")}</p>
    <p>Latest executor run：{_artifact_id(retest_run, "automation_run_id")} / {escape(retest_run.status if retest_run else "尚未執行")}</p>
    <p class="muted">這裡只顯示替代策略是否已進入 retest scaffold；不代表策略通過、晉級或下單。</p>
    <h4>替代策略 Retest Autopilot Run</h4>
    <p>Status：<span class="{_automation_status_class(autopilot_run.loop_status) if autopilot_run else "status-muted"}">{escape(autopilot_run.loop_status if autopilot_run else "尚未記錄")}</span></p>
    <p>Run ID：<code>{escape(autopilot_run.run_id if autopilot_run else "none")}</code></p>
    <p>Next action：{escape(autopilot_run.next_research_action if autopilot_run else "n/a")}</p>
    <p>Paper-shadow outcome：<code>{escape(autopilot_run.paper_shadow_outcome_id if autopilot_run and autopilot_run.paper_shadow_outcome_id else "none")}</code></p>
    <p>Blocked：</p>
    {_plain_list(autopilot_run.blocked_reasons if autopilot_run else [])}
    {_autopilot_steps(autopilot_run) if autopilot_run else '<p class="muted">尚無 completed replacement retest chain 紀錄。</p>'}
    <p class="muted">這是替代策略 retest 完成後的 research autopilot 閉環紀錄；只顯示，不代表實盤或自動晉級。</p>
  </article>
"""


def _replacement_retest_kind(plan: RevisionRetestTaskPlan | None) -> str:
    if plan is None or plan.pending_trial_id is None:
        return "not_scaffolded"
    return "lineage_replacement"


def _strategy_lineage_panel(summary: StrategyLineageSummary | None) -> str:
    if summary is None:
        return """
  <article class="panel">
    <h3>策略 lineage</h3>
    <p class="muted">目前沒有可彙整的策略 lineage。</p>
  </article>
"""
    return f"""
  <article class="panel wide">
    <h3>策略 lineage</h3>
    <p>Root：<code>{escape(summary.root_card_id)}</code></p>
    <p>Revisions：{summary.revision_count}</p>
    <p>Revision cards：</p>
    {_plain_list(summary.revision_card_ids)}
    <h4>Revision Tree</h4>
    {_strategy_lineage_tree(summary)}
    <p>Replacements：{summary.replacement_count}</p>
    <p>Replacement cards：</p>
    {_plain_list(summary.replacement_card_ids)}
    <h4>Replacement Contributions</h4>
    {_strategy_lineage_replacements(summary)}
    <h4>表現結論</h4>
    <p>{_strategy_lineage_performance_verdict(summary)}</p>
    <h4>下一步研究焦點</h4>
    <p>{escape(summary.next_research_focus)}</p>
    <h4>表現軌跡</h4>
    {_strategy_lineage_performance_trajectory(summary)}
    <p>Shadow outcomes：{summary.outcome_count}</p>
    <h4>Action counts</h4>
    {_dict_rows(summary.action_counts)}
    <h4>Failure attribution</h4>
    {_dict_rows(summary.failure_attribution_counts)}
    <p>Best / worst excess：{_format_number(summary.best_excess_return_after_costs)} / {_format_number(summary.worst_excess_return_after_costs)}</p>
    <p>Latest outcome：<code>{escape(summary.latest_outcome_id or "none")}</code></p>
  </article>
"""


def _strategy_lineage_tree(summary: StrategyLineageSummary | None) -> str:
    if summary is None or not summary.revision_nodes:
        return '<p class="muted">目前沒有 revision tree。</p>'
    return _plain_list(
        [
            f"Depth {node.depth} / Parent {node.parent_card_id} / {node.card_id}"
            f" / {node.status} / Name {node.strategy_name}"
            f" / Hypothesis {node.hypothesis}"
            f" / Source {node.source_outcome_id or 'none'}"
            f" / Fixes {', '.join(node.failure_attributions) if node.failure_attributions else 'none'}"
            for node in summary.revision_nodes
        ]
    )


def _strategy_lineage_replacements(summary: StrategyLineageSummary | None) -> str:
    if summary is None or not summary.replacement_nodes:
        return '<p class="muted">目前沒有 replacement contribution。</p>'
    return _plain_list(
        [
            f"Replacement {node.card_id}"
            f" / Source {node.source_outcome_id or 'none'}"
            f" / Latest {node.latest_outcome_id or 'none'}"
            f" / Action {node.latest_recommended_strategy_action or 'none'}"
            f" / Excess {_format_number(node.latest_excess_return_after_costs)}"
            f" / Status {node.status}"
            f" / Hypothesis {node.hypothesis}"
            f" / Failures {', '.join(node.failure_attributions) if node.failure_attributions else 'none'}"
            for node in summary.replacement_nodes
        ]
    )


def _strategy_lineage_performance_verdict(summary: StrategyLineageSummary | None) -> str:
    if summary is None:
        return "目前沒有 lineage 表現結論。"
    return (
        f"{escape(summary.performance_verdict)}"
        f" / 改善 {summary.improved_outcome_count}"
        f" / 惡化 {summary.worsened_outcome_count}"
        f" / 未知 {summary.unknown_outcome_count}"
        f" / 最新 {escape(summary.latest_change_label)}"
        f" / Delta {_format_number(summary.latest_delta_vs_previous_excess)}"
        f" / 主要失敗 {escape(summary.primary_failure_attribution or 'none')}"
        f" / 最新動作 {escape(summary.latest_recommended_strategy_action or 'none')}"
    )


def _strategy_lineage_performance_trajectory(summary: StrategyLineageSummary | None) -> str:
    if summary is None or not summary.outcome_nodes:
        return '<p class="muted">目前沒有 lineage performance trajectory。</p>'
    return _plain_list(
        [
            f"Outcome {node.outcome_id} / Card {node.strategy_card_id}"
            f" / Excess {_format_number(node.excess_return_after_costs)}"
            f" / Delta {_format_number(node.delta_vs_previous_excess)}"
            f" / {node.change_label}"
            f" / Action {node.recommended_strategy_action}"
            f" / Failures {', '.join(node.failure_attributions) if node.failure_attributions else 'none'}"
            for node in summary.outcome_nodes
        ]
    )


def _render_health(snapshot: OperatorConsoleSnapshot) -> str:
    health_class = _status_class(snapshot.health.severity)
    blocking_findings = [finding for finding in snapshot.health.findings if finding.repair_required]
    finding_rows = "\n".join(
        "<tr>"
        f"<td>{escape(finding.severity)}</td>"
        f"<td><code>{escape(finding.code)}</code></td>"
        f"<td>{escape(finding.message)}</td>"
        f"<td>{escape(finding.artifact_path or '')}</td>"
        "</tr>"
        for finding in snapshot.health.findings
    )
    if not finding_rows:
        finding_rows = '<tr><td colspan="4">目前沒有 health finding。</td></tr>'
    repair_rows = "\n".join(
        "<tr>"
        f"<td><code>{escape(repair.repair_request_id)}</code></td>"
        f"<td>{escape(repair.status)}</td>"
        f"<td>{escape(repair.severity)}</td>"
        f"<td>{escape(repair.observed_failure)}</td>"
        "</tr>"
        for repair in sorted(snapshot.repair_requests, key=lambda item: item.created_at, reverse=True)[:20]
    )
    if not repair_rows:
        repair_rows = '<tr><td colspan="4">目前沒有 repair request。</td></tr>'
    repair_cards = "\n".join(_repair_request_card(repair) for repair in sorted(snapshot.repair_requests, key=lambda item: item.created_at, reverse=True)[:10])
    if not repair_cards:
        repair_cards = '<p class="muted">目前沒有 repair request prompt 可檢查。</p>'
    blocking_rows = "\n".join(_health_finding_item(finding) for finding in blocking_findings)
    if not blocking_rows:
        blocking_rows = '<p class="muted">目前沒有 blocking health finding。</p>'
    return f"""
<section class="grid">
  <article class="panel">
    <h3>健康狀態</h3>
    <span class="{health_class}">{escape(_translate_health(snapshot.health.status))}</span>
    <p>嚴重度：{escape(snapshot.health.severity)}</p>
    <p>repair_required：{str(snapshot.health.repair_required).lower()}</p>
    <p>repair_request_id：<code>{escape(snapshot.health.repair_request_id or "none")}</code></p>
  </article>
  <article class="panel wide">
    <h3>阻塞項目</h3>
    {blocking_rows}
  </article>
  <article class="panel wide">
    <h3>健康檢查 Findings</h3>
    <table>
      <thead><tr><th>嚴重度</th><th>代碼</th><th>訊息</th><th>Artifact</th></tr></thead>
      <tbody>{finding_rows}</tbody>
    </table>
  </article>
  <article class="panel wide">
    <h3>修復佇列</h3>
    <table>
      <thead><tr><th>ID</th><th>狀態</th><th>嚴重度</th><th>觀察到的失敗</th></tr></thead>
      <tbody>{repair_rows}</tbody>
    </table>
  </article>
  <article class="panel wide">
    <h3>修復請求詳情</h3>
    <div class="timeline">{repair_cards}</div>
  </article>
</section>
"""


def _render_control(snapshot: OperatorConsoleSnapshot) -> str:
    state = snapshot.control_state
    events = sorted(snapshot.control_events, key=lambda item: item.created_at, reverse=True)[:20]
    event_rows = "\n".join(
        "<tr>"
        f"<td>{_format_dt(event.created_at)}</td>"
        f"<td><code>{escape(event.action)}</code></td>"
        f"<td>{escape(event.actor)}</td>"
        f"<td>{escape(event.symbol or 'global')}</td>"
        f"<td>{escape(event.reason)}</td>"
        f"<td>{'是' if event.requires_confirmation else '否'} / {'是' if event.confirmed else '否'}</td>"
        "</tr>"
        for event in events
    )
    if not event_rows:
        event_rows = '<tr><td colspan="6">目前沒有 control audit event。</td></tr>'
    return f"""
<section class="grid">
  <article class="panel">
    <h3>目前控制狀態</h3>
    <div class="metric">{escape(_translate_control_status(state.status))}</div>
    <p>paused：{str(state.paused).lower()}</p>
    <p>stop_new_entries：{str(state.stop_new_entries).lower()}</p>
    <p>reduce_risk：{str(state.reduce_risk).lower()}</p>
    <p>emergency_stop：{str(state.emergency_stop).lower()}</p>
    <p>max_position_pct：{_format_pct(state.max_position_pct)}</p>
    <p>latest_control_id：<code>{escape(state.latest_control_id or "none")}</code></p>
  </article>
  <article class="panel wide">
    <h3>Audit Log</h3>
    <table>
      <thead><tr><th>時間</th><th>Action</th><th>Actor</th><th>Scope</th><th>Reason</th><th>需確認 / 已確認</th></tr></thead>
      <tbody>{event_rows}</tbody>
    </table>
  </article>
  <article class="panel wide">
    <h3>可用 CLI 控制</h3>
    <p>此 console 仍然不提供表單；所有控制必須透過 CLI 寫入 audit log。</p>
    <ul class="conditions">
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action PAUSE --reason "..."</code></li>
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action STOP_NEW_ENTRIES --reason "..."</code></li>
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action REDUCE_RISK --reason "..."</code></li>
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action EMERGENCY_STOP --reason "..." --confirm</code></li>
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action SET_MAX_POSITION --max-position-pct 0.10 --reason "..." --confirm</code></li>
      <li><code>python run_forecast_loop.py operator-control --storage-dir &lt;path&gt; --action RESUME --reason "..." --confirm</code></li>
    </ul>
  </article>
</section>
"""


def _health_finding_item(finding: HealthFinding) -> str:
    return (
        "<article class=\"decision-card\">"
        f"<h4><code>{escape(finding.code)}</code></h4>"
        f"<p>{escape(finding.message)}</p>"
        f"<p>嚴重度：{escape(finding.severity)} / repair_required={str(finding.repair_required).lower()}</p>"
        f"<p>Artifact：<code>{escape(finding.artifact_path or 'none')}</code></p>"
        "</article>"
    )


def _repair_request_card(repair: RepairRequest) -> str:
    return f"""
<article class="decision-card">
  <header>
    <div>
      <h4><code>{escape(repair.repair_request_id)}</code></h4>
      <div class="muted">{_format_dt(repair.created_at)}</div>
    </div>
    <span class="{_repair_status_class(repair.status, repair.severity)}">{escape(_translate_repair_status(repair.status))}</span>
  </header>
  <p>{escape(repair.observed_failure)}</p>
  <p>嚴重度：{escape(repair.severity)}</p>
  <p>Prompt：<code>{escape(repair.prompt_path or "none")}</code></p>
  <h5>重現指令</h5>
  <p><code>{escape(repair.reproduction_command)}</code></p>
  <h5>受影響 Artifacts</h5>
  {_string_list(repair.affected_artifacts)}
  <h5>建議測試</h5>
  {_string_list(repair.recommended_tests)}
  <h5>驗收條件</h5>
  {_string_list(repair.acceptance_criteria)}
</article>
"""


def _repair_status_class(status: str, severity: str) -> str:
    if status == "pending" and severity == "blocking":
        return "status alert"
    if status == "pending":
        return "status warn"
    return "status"


def _translate_repair_status(status: str) -> str:
    return {
        "pending": "待處理 (pending)",
        "resolved": "已解決 (resolved)",
        "ignored": "已忽略 (ignored)",
    }.get(status, status)


def _string_list(items: list[str]) -> str:
    if not items:
        return '<p class="muted">none</p>'
    return "<ul class=\"conditions\">" + "".join(f"<li><code>{escape(item)}</code></li>" for item in items) + "</ul>"


def _latest_decision_summary(decision: StrategyDecision | None) -> str:
    if decision is None:
        return "<p class=\"muted\">目前沒有最新決策。</p>"
    blocked = decision.blocked_reason or "none"
    return f"""
<div class="metric">{escape(_translate_action(decision.action))}</div>
<p>{escape(decision.reason_summary)}</p>
<div class="badge-row">
  <span class="status">Evidence {escape(decision.evidence_grade)}</span>
  <span class="status">Risk {escape(decision.risk_level)}</span>
  <span class="status">Tradeable {'是' if decision.tradeable else '否'}</span>
</div>
<p class="muted">Blocked reason：<code>{escape(blocked)}</code></p>
"""


def _decision_card(decision: StrategyDecision, *, is_latest: bool) -> str:
    blocked = decision.blocked_reason or "none"
    latest_label = '<span class="status">最新</span>' if is_latest else ""
    return f"""
<article class="decision-card">
  <header>
    <div>
      <h4>{escape(_translate_action(decision.action))} / {escape(decision.symbol)}</h4>
      <div class="muted">{_format_dt(decision.created_at)} · horizon {decision.horizon_hours}h</div>
    </div>
    {latest_label}
  </header>
  <p>{escape(decision.reason_summary)}</p>
  <div class="badge-row">
    <span class="status">Evidence {escape(decision.evidence_grade)}</span>
    <span class="status">Risk {escape(decision.risk_level)}</span>
    <span class="status">Tradeable {'是' if decision.tradeable else '否'}</span>
  </div>
  <p>建議部位：{_format_pct(decision.recommended_position_pct)} / 目前部位：{_format_pct(decision.current_position_pct)} / 上限：{_format_pct(decision.max_position_pct)}</p>
  <p>Blocked reason：<code>{escape(blocked)}</code></p>
  <h5>Evidence Links</h5>
  {_evidence_links(decision)}
  <h5>Invalidation Conditions</h5>
  {_conditions(decision.invalidation_conditions)}
</article>
"""


def _evidence_links(decision: StrategyDecision) -> str:
    groups = [
        ("Forecast", decision.forecast_ids),
        ("Score", decision.score_ids),
        ("Review", decision.review_ids),
        ("Baseline", decision.baseline_ids),
    ]
    rows = []
    for label, ids in groups:
        if ids:
            for artifact_id in ids:
                rows.append(f"<li>{label}: <code>{escape(artifact_id)}</code></li>")
        else:
            rows.append(f"<li>{label}: <span class=\"muted\">none</span></li>")
    return f"<ul class=\"evidence-list\">{''.join(rows)}</ul>"


def _conditions(conditions: list[str]) -> str:
    if not conditions:
        return '<p class="muted">未記錄失效條件。</p>'
    return "<ul class=\"conditions\">" + "".join(f"<li>{escape(condition)}</li>" for condition in conditions) + "</ul>"


def _plain_list(items: list[str], *, empty: str = "none") -> str:
    if not items:
        return f'<p class="muted">{escape(empty)}</p>'
    return "<ul class=\"conditions\">" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _dict_rows(values: dict[str, object]) -> str:
    if not values:
        return '<p class="muted">none</p>'
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(str(key))}</code></td>"
        f"<td>{escape(_format_artifact_value(value))}</td>"
        "</tr>"
        for key, value in sorted(values.items(), key=lambda item: str(item[0]))
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _format_artifact_value(value: object) -> str:
    if isinstance(value, float):
        return _format_number(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in sorted(value.items(), key=lambda item: str(item[0])))
    return str(value)


def _autopilot_steps(run: ResearchAutopilotRun | None) -> str:
    if run is None:
        return '<p class="muted">目前沒有 research autopilot run。</p>'
    if not run.steps:
        return '<p class="muted">沒有 autopilot step 記錄。</p>'
    rows = "".join(
        "<li>"
        f"{escape(step.get('name') or '')}: {escape(step.get('status') or '')} "
        f"<code>{escape(step.get('artifact_id') or 'none')}</code>"
        "</li>"
        for step in run.steps
    )
    return f'<ul class="conditions">{rows}</ul>'


def _revision_candidate_panel(snapshot: OperatorConsoleSnapshot, *, wide: bool) -> str:
    revision = snapshot.latest_strategy_revision_card
    if revision is None:
        return ""
    agenda = snapshot.latest_strategy_revision_agenda
    source = snapshot.latest_strategy_revision_source_outcome
    retest_trial = snapshot.latest_strategy_revision_retest_trial
    retest_split = snapshot.latest_strategy_revision_split_manifest
    attributions = revision.parameters.get("revision_failure_attributions", [])
    attribution_list = [str(item) for item in attributions] if isinstance(attributions, list) else [str(attributions)]
    panel_class = "panel wide" if wide else "panel"
    return f"""
  <article class="{panel_class}">
    <h3>策略修正候選</h3>
    <p class="metric">{escape(revision.strategy_name)}</p>
    <p>{escape(revision.hypothesis)}</p>
    <div class="badge-row">
      <span class="status">Status {escape(revision.status)}</span>
      <span class="status">Version {escape(revision.version)}</span>
      <span class="status">Source {_artifact_id(source, "outcome_id")}</span>
    </div>
    <p>Revision：{_artifact_id(revision, "card_id")}</p>
    <p>父策略：<code>{escape(revision.parent_card_id or "n/a")}</code></p>
    <p>Retest agenda：{_artifact_id(agenda, "agenda_id")}</p>
    <p>Failure attribution：</p>
    {_plain_list(attribution_list)}
    <h4>修正規則</h4>
    {_plain_list(revision.entry_rules + revision.exit_rules + revision.risk_rules)}
    <h4>Acceptance</h4>
    {_plain_list(agenda.acceptance_criteria if agenda else [])}
    <h4>Revision Retest Scaffold</h4>
    <p>Trial：{_artifact_id(retest_trial, "trial_id")} / {escape(retest_trial.status if retest_trial else "尚未建立")}</p>
    <p>Dataset：<code>{escape(retest_trial.dataset_id if retest_trial and retest_trial.dataset_id else "n/a")}</code></p>
    <p>Locked split：{_artifact_id(retest_split, "manifest_id")} / {escape(retest_split.status if retest_split else "尚未鎖定")}</p>
    <p>Next required：</p>
    {_plain_list(snapshot.latest_strategy_revision_next_required_artifacts)}
    {_revision_retest_task_plan_panel(snapshot.latest_strategy_revision_retest_task_plan)}
    {_revision_retest_task_run_panel(snapshot.latest_strategy_revision_retest_task_run)}
    {_revision_retest_autopilot_run_panel(snapshot.latest_strategy_revision_retest_autopilot_run)}
  </article>
"""


def _revision_retest_task_plan_panel(plan: RevisionRetestTaskPlan | None) -> str:
    if plan is None:
        return """
    <h4>下一個 retest 研究任務</h4>
    <p class="muted">目前沒有可解析的 retest task plan。</p>
"""
    next_task = plan.task_by_id(plan.next_task_id) if plan.next_task_id else None
    command = " ".join(next_task.command_args) if next_task and next_task.command_args else "無"
    return f"""
    <h4>下一個 retest 研究任務</h4>
    <p>Task：<code>{escape(next_task.task_id if next_task else "none")}</code> / {escape(next_task.status if next_task else "completed")}</p>
    <p>Required artifact：<code>{escape(next_task.required_artifact if next_task else "none")}</code></p>
    <p>Blocked reason：{escape(next_task.blocked_reason if next_task and next_task.blocked_reason else "none")}</p>
    <p>Missing inputs：</p>
    {_plain_list(next_task.missing_inputs if next_task else [])}
    <p>Command args：<code>{escape(command)}</code></p>
    <p class="muted">只顯示，不執行。</p>
"""


def _revision_retest_task_run_panel(run: AutomationRun | None) -> str:
    if run is None:
        return """
    <h4>最新 retest task run log</h4>
    <p class="muted">尚未記錄 retest task run log；可用 <code>record-revision-retest-task-run</code> 寫入唯讀稽核紀錄。</p>
"""
    return f"""
    <h4>最新 retest task run log</h4>
    <p>Status：<span class="{_automation_status_class(run.status)}">{escape(run.status)}</span></p>
    <p>Run ID：<code>{escape(run.automation_run_id)}</code></p>
    <p>Command：<code>{escape(run.command)}</code></p>
    <p>Completed：{escape(run.completed_at.isoformat())}</p>
    {_automation_steps(run)}
    <p class="muted">這是 PR18 寫入的稽核紀錄；只顯示，不執行。</p>
"""


def _revision_retest_autopilot_run_panel(run: ResearchAutopilotRun | None) -> str:
    if run is None:
        return """
    <h4>最新 revision retest autopilot run</h4>
    <p class="muted">尚未記錄 completed revision retest chain 的 research autopilot run；可用 <code>record-revision-retest-autopilot-run</code> 寫入閉環證據。</p>
"""
    return f"""
    <h4>最新 revision retest autopilot run</h4>
    <p>Status：<span class="{_automation_status_class(run.loop_status)}">{escape(run.loop_status)}</span></p>
    <p>Run ID：<code>{escape(run.run_id)}</code></p>
    <p>Next action：{escape(run.next_research_action)}</p>
    <p>Paper-shadow outcome：<code>{escape(run.paper_shadow_outcome_id or "none")}</code></p>
    <p>Blocked：</p>
    {_plain_list(run.blocked_reasons)}
    {_autopilot_steps(run)}
    <p class="muted">這是 revision retest 完整閉環的 research autopilot 紀錄；只顯示，不執行。</p>
"""


def _strategy_research_preview(snapshot: OperatorConsoleSnapshot) -> str:
    card = snapshot.latest_strategy_card
    leaderboard = snapshot.latest_leaderboard_entry
    outcome = snapshot.latest_paper_shadow_outcome
    autopilot = snapshot.latest_research_autopilot_run
    revision = snapshot.latest_strategy_revision_card
    revision_agenda = snapshot.latest_strategy_revision_agenda
    revision_source = snapshot.latest_strategy_revision_source_outcome
    retest_trial = snapshot.latest_strategy_revision_retest_trial
    retest_split = snapshot.latest_strategy_revision_split_manifest
    lineage = snapshot.latest_strategy_lineage_summary
    return f"""
<p>策略卡：{_artifact_id(card, "card_id")} / {escape(card.strategy_name if card else "n/a")}</p>
<p>假設：{escape(card.hypothesis if card else "目前沒有 strategy_cards artifact。")}</p>
<p>Leaderboard：{_artifact_id(leaderboard, "entry_id")} / alpha_score={_format_number(leaderboard.alpha_score if leaderboard else None)}</p>
<p>Paper-shadow：{escape(outcome.recommended_strategy_action if outcome else "n/a")} / {escape(outcome.outcome_grade if outcome else "n/a")}</p>
<p>下一步：{escape(autopilot.next_research_action if autopilot else "n/a")} / Run {_artifact_id(autopilot, "run_id")}</p>
<p>策略修正候選：{_artifact_id(revision, "card_id")} / 來源 {_artifact_id(revision_source, "outcome_id")} / Agenda {_artifact_id(revision_agenda, "agenda_id")}</p>
<p>Revision Retest Scaffold：{_artifact_id(retest_trial, "trial_id")} / Dataset <code>{escape(retest_trial.dataset_id if retest_trial and retest_trial.dataset_id else "n/a")}</code> / Split {_artifact_id(retest_split, "manifest_id")}</p>
<p>策略 lineage：Root <code>{escape(lineage.root_card_id if lineage else "n/a")}</code> / Revisions {lineage.revision_count if lineage else "n/a"} / Outcomes {lineage.outcome_count if lineage else "n/a"}</p>
<p>Lineage best/worst：{_format_number(lineage.best_excess_return_after_costs if lineage else None)} / {_format_number(lineage.worst_excess_return_after_costs if lineage else None)} / Latest <code>{escape(lineage.latest_outcome_id if lineage and lineage.latest_outcome_id else "none")}</code></p>
<p>Revision Tree</p>
{_strategy_lineage_tree(lineage)}
<p>表現結論</p>
<p>{_strategy_lineage_performance_verdict(lineage)}</p>
<p>下一步研究焦點</p>
<p>{escape(lineage.next_research_focus if lineage else "目前沒有 lineage 下一步研究焦點。")}</p>
<p>表現軌跡</p>
{_strategy_lineage_performance_trajectory(lineage)}
{_plain_list(list(lineage.action_counts.keys()) if lineage else [], empty="目前沒有 lineage action")}
{_plain_list(list(lineage.failure_attribution_counts.keys()) if lineage else [], empty="目前沒有 lineage failure attribution")}
{_revision_retest_task_plan_panel(snapshot.latest_strategy_revision_retest_task_plan)}
{_revision_retest_task_run_panel(snapshot.latest_strategy_revision_retest_task_run)}
{_revision_retest_autopilot_run_panel(snapshot.latest_strategy_revision_retest_autopilot_run)}
{_plain_list(snapshot.latest_strategy_revision_next_required_artifacts, empty="目前沒有 pending retest scaffold")}
{_plain_list(revision.entry_rules + revision.exit_rules + revision.risk_rules if revision else [], empty="目前沒有 DRAFT 修正候選")}
"""


def _render_counts(counts: dict[str, int]) -> str:
    return "".join(f"<p>{escape(name)}：{count}</p>" for name, count in counts.items())


def _risk_status(risk: RiskSnapshot | None) -> str:
    if risk is None:
        return "UNKNOWN"
    return f'<span class="{_status_class(risk.severity)}">{escape(risk.status)}</span>'


def _risk_findings(risk: RiskSnapshot | None) -> str:
    if risk is None:
        return '<span class="muted">n/a</span>'
    if not risk.findings:
        return '<span class="muted">none</span>'
    return ", ".join(f"<code>{escape(finding)}</code>" for finding in risk.findings)


def _page_title(page: str) -> str:
    return {
        "overview": "總覽",
        "decisions": "決策",
        "portfolio": "投資組合",
        "research": "研究",
        "health": "健康 / 修復",
        "control": "控制",
    }[page]


def _translate_action(action: str) -> str:
    return {
        "BUY": "買進",
        "SELL": "賣出",
        "HOLD": "持有",
        "REDUCE_RISK": "降低風險",
        "STOP_NEW_ENTRIES": "停止新進場",
    }.get(action, action)


def _translate_health(status: str) -> str:
    return {
        "healthy": "健康",
        "degraded": "注意",
        "unhealthy": "阻塞",
    }.get(status, status)


def _translate_control_status(status: str) -> str:
    return {
        "ACTIVE": "啟用",
        "PAUSED": "已暫停",
        "STOP_NEW_ENTRIES": "停止新進場",
        "REDUCE_RISK": "降低風險",
        "EMERGENCY_STOP": "緊急停止",
    }.get(status, status)


def _status_class(severity: str) -> str:
    if severity == "blocking":
        return "status alert"
    if severity == "warning":
        return "status warn"
    return "status"


def _automation_run_summary(run: AutomationRun | None) -> str:
    if run is None:
        return '<p class="muted">目前沒有 automation run log。</p>'
    return f"""
<p>Status：<span class="{_automation_status_class(run.status)}">{escape(run.status)}</span></p>
<p>Run ID：<code>{escape(run.automation_run_id)}</code></p>
<p>Health：<code>{escape(run.health_check_id or "none")}</code> / Decision：<code>{escape(run.decision_id or "none")}</code></p>
<p>Repair：<code>{escape(run.repair_request_id or "none")}</code></p>
{_automation_steps(run)}
"""


def _automation_steps(run: AutomationRun) -> str:
    if not run.steps:
        return '<p class="muted">沒有 step 記錄。</p>'
    rows = "".join(
        "<li>"
        f"{escape(display_step_name(step.get('name') or ''))}: {escape(step.get('status') or '')} "
        f"<code>{escape(display_step_artifact(step.get('name') or '', step.get('artifact_id')))}</code>"
        "</li>"
        for step in run.steps
    )
    return f'<ul class="conditions">{rows}</ul>'


def _automation_status_class(status: str) -> str:
    if status in {"BLOCKED", "RETEST_TASK_BLOCKED", "failed", "repair_required"}:
        return "status alert"
    return "status"


def _notification_summary(notifications: list[NotificationArtifact]) -> str:
    if not notifications:
        return '<p class="muted">目前沒有 notification artifacts。</p>'
    rows = "".join(
        "<li>"
        f"<span class=\"{_notification_severity_class(notification.severity)}\">{escape(notification.severity)}</span> "
        f"{escape(notification.title)}：{escape(notification.message)} "
        f"<code>{escape(notification.notification_id)}</code>"
        "</li>"
        for notification in sorted(notifications, key=lambda item: item.created_at, reverse=True)[:5]
    )
    return f'<ul class="conditions">{rows}</ul>'


def _notification_severity_class(severity: str) -> str:
    if severity == "blocking":
        return "status alert"
    if severity == "warning":
        return "status warn"
    return "status"


def _latest(items: list, field: str = "created_at"):
    return max(items, key=lambda item: getattr(item, field)) if items else None


def _artifact_id(item: object | None, field: str) -> str:
    if item is None:
        return "n/a"
    return f"<code>{escape(str(getattr(item, field)))}</code>"


def _format_dt(value: datetime | None) -> str:
    return "n/a" if value is None else value.astimezone(UTC).isoformat()


def _format_money(value: float | None) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _format_number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"
