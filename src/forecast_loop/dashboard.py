from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
import json
import os
from pathlib import Path
import tomllib

from forecast_loop.health import run_health_check
from forecast_loop.models import (
    AutomationRun,
    BaselineEvaluation,
    BrokerOrder,
    BrokerReconciliation,
    ExecutionSafetyGate,
    EvaluationSummary,
    ExperimentTrial,
    Forecast,
    ForecastScore,
    HealthFinding,
    LeaderboardEntry,
    LockedEvaluationResult,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperShadowOutcome,
    Proposal,
    ProviderRun,
    ResearchAgenda,
    ResearchAutopilotRun,
    RiskSnapshot,
    Review,
    SplitManifest,
    StrategyCard,
    StrategyDecision,
)
from forecast_loop.revision_retest_plan import RevisionRetestTaskPlan, build_revision_retest_task_plan
from forecast_loop.revision_retest_run_log import automation_run_matches_revision_retest_plan
from forecast_loop.strategy_lineage import StrategyLineageSummary, build_strategy_lineage_summary
from forecast_loop.strategy_research import resolve_latest_strategy_research_chain
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class DashboardSnapshot:
    storage_dir: Path
    dashboard_generated_at: datetime
    last_run_meta: dict | None
    last_replay_meta: dict | None
    latest_forecast: Forecast | None
    latest_score: ForecastScore | None
    latest_review: Review | None
    latest_proposal: Proposal | None
    latest_strategy_decision: StrategyDecision | None
    latest_baseline_evaluation: BaselineEvaluation | None
    latest_portfolio_snapshot: PaperPortfolioSnapshot | None
    latest_risk_snapshot: RiskSnapshot | None
    latest_strategy_card: StrategyCard | None
    latest_experiment_trial: ExperimentTrial | None
    latest_locked_evaluation: LockedEvaluationResult | None
    latest_leaderboard_entry: LeaderboardEntry | None
    latest_paper_shadow_outcome: PaperShadowOutcome | None
    latest_research_agenda: ResearchAgenda | None
    latest_research_autopilot_run: ResearchAutopilotRun | None
    latest_strategy_lineage_summary: StrategyLineageSummary | None
    latest_strategy_revision_card: StrategyCard | None
    latest_strategy_revision_agenda: ResearchAgenda | None
    latest_strategy_revision_source_outcome: PaperShadowOutcome | None
    latest_strategy_revision_retest_trial: ExperimentTrial | None
    latest_strategy_revision_split_manifest: SplitManifest | None
    latest_strategy_revision_next_required_artifacts: list[str]
    latest_strategy_revision_retest_task_plan: RevisionRetestTaskPlan | None
    latest_strategy_revision_retest_task_run: AutomationRun | None
    latest_strategy_revision_retest_autopilot_run: ResearchAutopilotRun | None
    paper_orders: list[PaperOrder]
    broker_orders: list[BrokerOrder]
    paper_fills: list[PaperFill]
    latest_broker_reconciliation: BrokerReconciliation | None
    latest_execution_safety_gate: ExecutionSafetyGate | None
    latest_provider_run: ProviderRun | None
    latest_replay_summary: EvaluationSummary | None
    forecast_count: int
    score_count: int
    review_count: int
    proposal_count: int
    replay_summary_count: int
    current_mode: str
    hourly_status: str
    hourly_status_source_at: datetime | None
    building_status: str
    building_status_source_at: datetime | None
    mode_reason: str
    replay_freshness_label: str
    replay_generated_at: datetime | None
    replay_is_stale: bool
    health_status: str
    health_severity: str
    repair_required: bool
    repair_request_id: str | None
    health_findings: list[HealthFinding]


@dataclass(slots=True)
class AutomationState:
    status: str
    updated_at: datetime | None


def build_dashboard_snapshot(storage_dir: Path | str) -> DashboardSnapshot:
    storage_dir = Path(storage_dir)
    repository = JsonFileRepository(storage_dir)
    forecasts = repository.load_forecasts()
    scores = repository.load_scores()
    reviews = repository.load_reviews()
    proposals = repository.load_proposals()
    strategy_decisions = repository.load_strategy_decisions()
    baseline_evaluations = repository.load_baseline_evaluations()
    portfolio_snapshots = repository.load_portfolio_snapshots()
    risk_snapshots = repository.load_risk_snapshots()
    paper_orders = repository.load_paper_orders()
    broker_orders = repository.load_broker_orders()
    paper_fills = repository.load_paper_fills()
    broker_reconciliations = repository.load_broker_reconciliations()
    execution_safety_gates = repository.load_execution_safety_gates()
    provider_runs = repository.load_provider_runs()
    replay_summaries = repository.load_evaluation_summaries()
    latest_forecast = forecasts[-1] if forecasts else None
    dashboard_symbol = latest_forecast.symbol if latest_forecast else (strategy_decisions[-1].symbol if strategy_decisions else "BTC-USD")
    strategy_cards = [item for item in repository.load_strategy_cards() if dashboard_symbol in item.symbols]
    experiment_trials = [item for item in repository.load_experiment_trials() if item.symbol == dashboard_symbol]
    all_locked_evaluations = repository.load_locked_evaluation_results()
    split_manifests = repository.load_split_manifests()
    leaderboard_entries = [item for item in repository.load_leaderboard_entries() if item.symbol == dashboard_symbol]
    paper_shadow_outcomes = [item for item in repository.load_paper_shadow_outcomes() if item.symbol == dashboard_symbol]
    research_agendas = [item for item in repository.load_research_agendas() if item.symbol == dashboard_symbol]
    research_autopilot_runs = [item for item in repository.load_research_autopilot_runs() if item.symbol == dashboard_symbol]
    automation_runs = [item for item in repository.load_automation_runs() if item.symbol == dashboard_symbol]
    research_chain = resolve_latest_strategy_research_chain(
        symbol=dashboard_symbol,
        strategy_cards=strategy_cards,
        experiment_trials=experiment_trials,
        locked_evaluations=all_locked_evaluations,
        split_manifests=split_manifests,
        leaderboard_entries=leaderboard_entries,
        paper_shadow_outcomes=paper_shadow_outcomes,
        research_agendas=research_agendas,
        research_autopilot_runs=research_autopilot_runs,
    )
    latest_review = reviews[-1] if reviews else None
    latest_proposal = _latest_proposal_for_review(proposals, latest_review)
    latest_replay_summary = replay_summaries[-1] if replay_summaries else None
    hourly_state = _load_automation_state("hourly-paper-forecast")
    building_state = _load_automation_state("loop-building-heartbeat")
    current_mode, mode_reason = _derive_mode(hourly_state.status, building_state.status)
    replay_freshness_label, replay_generated_at, replay_is_stale = _derive_replay_freshness(
        latest_replay_summary,
        latest_forecast,
    )
    health_result = run_health_check(
        storage_dir=storage_dir,
        symbol=latest_forecast.symbol if latest_forecast else "BTC-USD",
        now=datetime.now(tz=UTC),
        create_repair_request=False,
    )
    revision_card = research_chain.revision_candidate.strategy_card if research_chain.revision_candidate else None
    revision_task_plan = _safe_revision_retest_task_plan(
        repository=repository,
        storage_dir=storage_dir,
        symbol=dashboard_symbol,
        revision_card=revision_card,
    )
    revision_autopilot_run = _latest_revision_retest_autopilot_run(research_autopilot_runs, revision_card)
    lineage_summary = build_strategy_lineage_summary(
        root_card=research_chain.strategy_card,
        strategy_cards=strategy_cards,
        paper_shadow_outcomes=paper_shadow_outcomes,
    )

    return DashboardSnapshot(
        storage_dir=storage_dir,
        dashboard_generated_at=datetime.now(tz=UTC),
        last_run_meta=_load_json(storage_dir / "last_run_meta.json"),
        last_replay_meta=_load_json(storage_dir / "last_replay_meta.json"),
        latest_forecast=latest_forecast,
        latest_score=scores[-1] if scores else None,
        latest_review=latest_review,
        latest_proposal=latest_proposal,
        latest_strategy_decision=strategy_decisions[-1] if strategy_decisions else None,
        latest_baseline_evaluation=baseline_evaluations[-1] if baseline_evaluations else None,
        latest_portfolio_snapshot=portfolio_snapshots[-1] if portfolio_snapshots else None,
        latest_risk_snapshot=risk_snapshots[-1] if risk_snapshots else None,
        latest_strategy_card=research_chain.strategy_card,
        latest_experiment_trial=research_chain.experiment_trial,
        latest_locked_evaluation=research_chain.locked_evaluation,
        latest_leaderboard_entry=research_chain.leaderboard_entry,
        latest_paper_shadow_outcome=research_chain.paper_shadow_outcome,
        latest_research_agenda=research_chain.research_agenda,
        latest_research_autopilot_run=research_chain.research_autopilot_run,
        latest_strategy_lineage_summary=lineage_summary,
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
        paper_orders=paper_orders,
        broker_orders=broker_orders,
        paper_fills=paper_fills,
        latest_broker_reconciliation=broker_reconciliations[-1] if broker_reconciliations else None,
        latest_execution_safety_gate=execution_safety_gates[-1] if execution_safety_gates else None,
        latest_provider_run=provider_runs[-1] if provider_runs else None,
        latest_replay_summary=latest_replay_summary,
        forecast_count=len(forecasts),
        score_count=len(scores),
        review_count=len(reviews),
        proposal_count=len(proposals),
        replay_summary_count=len(replay_summaries),
        current_mode=current_mode,
        hourly_status=hourly_state.status,
        hourly_status_source_at=hourly_state.updated_at,
        building_status=building_state.status,
        building_status_source_at=building_state.updated_at,
        mode_reason=mode_reason,
        replay_freshness_label=replay_freshness_label,
        replay_generated_at=replay_generated_at,
        replay_is_stale=replay_is_stale,
        health_status=health_result.status,
        health_severity=health_result.severity,
        repair_required=health_result.repair_required,
        repair_request_id=health_result.repair_request_id,
        health_findings=health_result.findings,
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


def _latest_revision_retest_autopilot_run(
    runs: list[ResearchAutopilotRun],
    revision_card: StrategyCard | None,
) -> ResearchAutopilotRun | None:
    if revision_card is None:
        return None
    matches = [
        run
        for run in runs
        if run.strategy_card_id == revision_card.card_id
        and run.decision_basis == "research_paper_autopilot_loop"
        and run.strategy_decision_id is None
        and run.paper_shadow_outcome_id is not None
    ]
    return max(matches, key=lambda run: run.created_at) if matches else None


def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    latest_forecast = snapshot.latest_forecast
    latest_review = snapshot.latest_review
    latest_proposal = snapshot.latest_proposal
    latest_replay = snapshot.latest_replay_summary

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Paper Forecast Loop 儀表板</title>
  <style>
    html {{ color-scheme: dark; }}
    :root {{
      --bg: #08111b;
      --panel: rgba(11, 24, 38, 0.88);
      --panel-2: rgba(18, 34, 51, 0.9);
      --line: rgba(116, 150, 181, 0.24);
      --text: #eaf1f7;
      --muted: #8fa7be;
      --accent: #7dd3fc;
      --ok: #8df5ae;
      --warn: #ffd479;
      --focus: #f8fafc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Inter", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(78, 168, 222, 0.12), transparent 28%),
        linear-gradient(180deg, #08111b 0%, #0b1521 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    .skip-link {{
      position: absolute;
      top: 12px;
      left: 12px;
      transform: translateY(-150%);
      padding: 10px 14px;
      border-radius: 12px;
      background: rgba(248, 250, 252, 0.96);
      color: #08111b;
      text-decoration: none;
      z-index: 20;
    }}
    .skip-link:focus-visible {{
      transform: translateY(0);
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 190px minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      border-right: 1px solid var(--line);
      background: rgba(5, 12, 19, 0.62);
      padding: 20px 14px;
      position: sticky;
      top: 0;
      height: 100vh;
    }}
    .brand {{
      font-size: 0.78rem;
      letter-spacing: 0.14em;
      color: var(--accent);
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 1.8rem;
      line-height: 1.1;
      text-wrap: balance;
    }}
    .subtitle {{
      color: var(--muted);
      margin: 0 0 24px;
      font-size: 0.84rem;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }}
    .nav-list {{
      list-style: none;
      padding: 0;
      margin: 28px 0 0;
      display: grid;
      gap: 10px;
    }}
    .nav-list a {{
      display: block;
      padding: 8px 10px;
      border: 1px solid transparent;
      border-radius: 10px;
      color: var(--muted);
      text-decoration: none;
      background: transparent;
      font-size: 0.92rem;
    }}
    .nav-list a:hover {{
      color: var(--text);
      border-color: var(--line);
      background: rgba(125, 211, 252, 0.06);
    }}
    .nav-list a:focus-visible,
    summary:focus-visible {{
      outline: 2px solid var(--focus);
      outline-offset: 3px;
      color: var(--text);
      border-color: var(--accent);
    }}
    main {{
      padding: 28px 32px 42px;
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 18px;
    }}
    section[id] {{
      scroll-margin-top: 24px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      backdrop-filter: blur(18px);
      box-shadow: 0 10px 35px rgba(0, 0, 0, 0.18);
    }}
    .hero,
    .half {{ grid-column: 1 / -1; }}
    .panel h2 {{
      margin: 0 0 8px;
      font-size: 1.05rem;
      letter-spacing: 0.01em;
      text-wrap: balance;
      overflow-wrap: anywhere;
    }}
    .panel h3 {{
      margin: 0 0 8px;
      font-size: 0.98rem;
      letter-spacing: 0.01em;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 14px;
      overflow-wrap: anywhere;
    }}
    .lead {{
      margin: 0 0 18px;
      font-size: 1rem;
      line-height: 1.55;
      color: var(--text);
      max-width: 72ch;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .summary-card {{
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: var(--panel-2);
    }}
    .summary-label {{
      font-size: 0.74rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .summary-value {{
      font-size: 1.05rem;
      font-weight: 600;
      margin-bottom: 6px;
    }}
    .summary-copy {{
      color: var(--muted);
      line-height: 1.5;
      font-size: 0.92rem;
    }}
    .summary-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .summary-note {{
      color: var(--muted);
      line-height: 1.55;
      margin: 0;
      max-width: 70ch;
    }}
    .primary-card {{
      padding: 26px;
    }}
    .primary-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0 0;
    }}
    .stat-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      padding: 14px 14px 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel-2);
    }}
    .secondary-panel {{
      background: rgba(9, 19, 30, 0.72);
      border-color: rgba(116, 150, 181, 0.16);
    }}
    .evidence-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
      gap: 16px;
      margin-top: 18px;
    }}
    .evidence-block {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel-2);
    }}
    .micro-copy {{
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.55;
    }}
    .decision-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
      gap: 16px;
      margin-top: 18px;
    }}
    .decision-block {{
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel-2);
    }}
    .decision-emphasis {{
      margin: 0;
      font-size: 1rem;
      line-height: 1.65;
      color: var(--text);
    }}
    .drawer-stack {{
      display: grid;
      gap: 14px;
    }}
    .command-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .drawer-intro {{
      margin: 0 0 14px;
      color: var(--muted);
      line-height: 1.55;
      max-width: 72ch;
    }}
    .stat-label {{
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 1.35rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .kicker {{
      color: var(--accent);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 6px;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
    dl {{
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 10px 16px;
      margin: 0;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    .tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(125, 211, 252, 0.08);
      font-size: 0.85rem;
    }}
    .tag.warn {{
      background: rgba(255, 212, 121, 0.1);
      color: var(--warn);
    }}
    .tag.ok {{
      background: rgba(141, 245, 174, 0.1);
      color: var(--ok);
    }}
    pre {{
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      background: rgba(4, 11, 18, 0.92);
      border: 1px solid var(--line);
      color: #d4e6f8;
      overflow: auto;
      font-size: 0.82rem;
      line-height: 1.5;
    }}
    details {{
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 16px;
    }}
    summary {{
      cursor: pointer;
      color: var(--muted);
    }}
    @media (max-width: 980px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      .half {{ grid-column: span 12; }}
      .summary-grid,
      .primary-grid,
      .stat-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .decision-grid,
      .evidence-grid {{ grid-template-columns: 1fr; }}
      main {{ padding: 24px 18px 32px; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">跳到主要內容</a>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">Paper-Only Inspector</div>
      <h1>Paper Forecast Loop</h1>
      <p class="subtitle">以最新預測為優先的靜態操作視圖，方便先看當前判讀，再對照 replay 與原始中繼資料。</p>
      <nav aria-label="儀表板區段">
        <ul class="nav-list">
          <li><a href="#strategy">明日決策</a></li>
          <li><a href="#strategy-research">策略研究</a></li>
          <li><a href="#summary">操作摘要</a></li>
          <li><a href="#portfolio">投資組合與風險</a></li>
          <li><a href="#broker">Broker / Sandbox</a></li>
          <li><a href="#provider">資料來源健康</a></li>
          <li><a href="#forecast">目前預測</a></li>
          <li><a href="#decision">本輪判讀與建議</a></li>
          <li><a href="#evidence">證據快照</a></li>
          <li><a href="#replay">歷史脈絡</a></li>
          <li><a href="#raw">原始中繼資料</a></li>
        </ul>
      </nav>
    </aside>
    <main id="main-content">
      <section class="panel hero primary-card" id="strategy">
        {render_strategy_panel(snapshot)}
      </section>
      <section class="panel hero primary-card" id="strategy-research">
        {render_strategy_research_panel(snapshot)}
      </section>
      <section class="panel hero" id="summary">
        {render_operator_summary(snapshot)}
      </section>
      <section class="panel hero" id="portfolio">
        {render_portfolio_risk_panel(snapshot)}
      </section>
      <section class="panel" id="broker">
        {render_broker_panel(snapshot)}
      </section>
      <section class="panel" id="provider">
        {render_provider_panel(snapshot)}
      </section>
      <section class="panel hero primary-card" id="forecast">
        {render_forecast_panel(latest_forecast)}
      </section>
      <section class="panel" id="decision">
        {render_decision_panel(latest_review, latest_proposal)}
      </section>
      <section class="panel" id="evidence">
        {render_evidence_panel(snapshot)}
      </section>
      <section class="panel half secondary-panel" id="replay">
        {render_replay_panel(snapshot, latest_replay)}
      </section>
      <section class="panel" id="raw">
        <div class="kicker">Audit / Debug</div>
        <h2>原始中繼資料</h2>
        <p class="drawer-intro">只有在比對 dashboard 所用來源、追查欄位映射或人工稽核原始 JSON 時，才需要展開下面兩個 debug drawer。日常操作請以前面的預測、檢討與證據區為主。</p>
        <details>
          <summary>last_run_meta.json</summary>
          <pre>{escape(json.dumps(snapshot.last_run_meta, ensure_ascii=False, indent=2) if snapshot.last_run_meta else "目前還沒有執行中繼資料。")}</pre>
        </details>
        <details>
          <summary>last_replay_meta.json</summary>
          <pre>{escape(json.dumps(snapshot.last_replay_meta, ensure_ascii=False, indent=2) if snapshot.last_replay_meta else "目前還沒有 replay 中繼資料。")}</pre>
        </details>
      </section>
    </main>
  </div>
</body>
</html>"""


def render_operator_summary(snapshot: DashboardSnapshot) -> str:
    health_label, health_copy = _summarize_health(snapshot)
    judgment_copy = _summarize_judgment(snapshot)
    replay_tag_class = "warn" if snapshot.replay_is_stale else "ok"
    replay_copy = (
        "僅供歷史脈絡參考。replay 落後於最新預測時，不應覆蓋目前預測卡的判讀。"
        if snapshot.replay_is_stale
        else "replay 與最新預測足夠接近，可作為目前操作判讀的補充脈絡。"
    )

    return f"""
      <div class="kicker">操作摘要</div>
      <h2>操作摘要</h2>
      <div class="summary-grid">
        <div class="summary-card">
          <div class="summary-label">健康度</div>
          <div class="summary-value">{escape(_display_health_label(health_label))}</div>
          <div class="summary-copy">{escape(_display_health_copy(health_label, health_copy))}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">模式</div>
          <div class="summary-value">{escape(_display_mode(snapshot.current_mode))}</div>
          <div class="summary-copy">{escape(_display_mode_reason(snapshot.current_mode, snapshot.mode_reason))}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">判斷</div>
          <div class="summary-value">{escape(_display_judgment_label(_judgment_label(snapshot)))}</div>
          <div class="summary-copy">{escape(_display_judgment_copy(snapshot, judgment_copy))}</div>
        </div>
      </div>
      <div class="summary-tags">
        <span class="tag">{escape(f"每小時：{_display_automation_status(snapshot.hourly_status)}")}</span>
        <span class="tag">{escape(f"建置心跳：{_display_automation_status(snapshot.building_status)}")}</span>
        <span class="tag {replay_tag_class}">{escape(_display_replay_freshness(snapshot.replay_freshness_label))}</span>
      </div>
      <div class="meta">{escape(_dashboard_freshness_copy(snapshot))}</div>
      <p class="summary-note">{escape(replay_copy)}</p>
    """


def render_strategy_panel(snapshot: DashboardSnapshot) -> str:
    decision = snapshot.latest_strategy_decision
    baseline = snapshot.latest_baseline_evaluation
    portfolio = snapshot.latest_portfolio_snapshot
    risk = snapshot.latest_risk_snapshot
    repair_copy = (
        "需要 Codex 修復，暫停新進場。"
        if snapshot.repair_required
        else "未偵測到阻擋性的修復請求。"
    )
    health_tag_class = "warn" if snapshot.repair_required or snapshot.health_severity != "none" else "ok"
    if decision is None:
        return f"""
      <div class="kicker">明日策略決策</div>
      <h2>明日策略決策</h2>
      <p class="lead">目前還沒有策略決策。請執行 <code>decide</code> 產生 paper-only 決策建議。</p>
      <div class="summary-tags">
        <span class="tag {health_tag_class}">{escape(_display_health_status(snapshot.health_status, snapshot.repair_required))}</span>
        <span class="tag">{escape(repair_copy)}</span>
      </div>
    """

    current_position = "無" if decision.current_position_pct is None else f"{decision.current_position_pct:.2%}"
    recommended_position = (
        "無"
        if decision.recommended_position_pct is None
        else f"{decision.recommended_position_pct:.2%}"
    )
    baseline_copy = (
        "尚無基準線評估。"
        if baseline is None
        else (
            f"樣本 {baseline.sample_size}；模型正確率 {_format_optional_ratio(baseline.directional_accuracy)}；"
            f"基準線 {_format_optional_ratio(baseline.baseline_accuracy)}；相對優勢 {_format_optional_ratio(baseline.model_edge)}。"
        )
    )
    portfolio_copy = (
        "目前沒有 paper 投資組合快照。"
        if portfolio is None
        else f"NAV {portfolio.nav or portfolio.equity:.2f}，淨曝險 {portfolio.net_exposure_pct:.2%}。"
    )
    risk_copy = (
        "尚無 risk-check 快照。"
        if risk is None
        else f"風險狀態 {_display_risk_status(risk.status)}；最大回撤 {risk.max_drawdown_pct:.2%}。"
    )
    blocked_copy = _display_blocked_reason(decision.blocked_reason)
    return f"""
      <div class="kicker">明日策略決策</div>
      <h2>明日策略決策</h2>
      <p class="lead">{escape(_display_strategy_reason(decision))}</p>
      <div class="summary-tags">
        <span class="tag">{escape(_display_strategy_action(decision.action))}</span>
        <span class="tag">{escape(_display_evidence_grade(decision.evidence_grade))}</span>
        <span class="tag">{escape(_display_risk_level(decision.risk_level))}</span>
        <span class="tag {health_tag_class}">{escape(_display_health_status(snapshot.health_status, snapshot.repair_required))}</span>
      </div>
      <div class="primary-grid">
        <div class="summary-card"><div class="summary-label">目前 paper 部位</div><div class="summary-value">{escape(current_position)}</div><div class="summary-copy">目前 paper 投資組合對 {escape(decision.symbol)} 的曝險。</div></div>
        <div class="summary-card"><div class="summary-label">建議 paper 部位</div><div class="summary-value">{escape(recommended_position)}</div><div class="summary-copy">這不是真實下單，只是 paper-only 研究建議。</div></div>
        <div class="summary-card"><div class="summary-label">可交易性</div><div class="summary-value">{escape(_display_boolean(decision.tradeable))}</div><div class="summary-copy">{escape(blocked_copy)}</div></div>
        <div class="summary-card"><div class="summary-label">健康檢查</div><div class="summary-value">{escape(_display_health_status(snapshot.health_status, snapshot.repair_required))}</div><div class="summary-copy">{escape(repair_copy)}</div></div>
      </div>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>預測品質 vs 基準線</h3>
          <p class="micro-copy">{escape(baseline_copy)}</p>
        </div>
        <div class="evidence-block">
          <h3>Paper 投資組合 / 修復狀態</h3>
          <p class="micro-copy">{escape(portfolio_copy)}</p>
          <p class="micro-copy">{escape(risk_copy)}</p>
          <p class="micro-copy">{escape(repair_copy)}</p>
        </div>
      </div>
      <details>
        <summary>展開策略決策詳細欄位</summary>
        <dl>
          <dt>決策 ID</dt><dd>{escape(decision.decision_id)}</dd>
          <dt>Forecast IDs</dt><dd>{escape(", ".join(decision.forecast_ids) or "無")}</dd>
          <dt>Score IDs</dt><dd>{escape(", ".join(decision.score_ids) or "無")}</dd>
          <dt>Review IDs</dt><dd>{escape(", ".join(decision.review_ids) or "無")}</dd>
          <dt>Baseline IDs</dt><dd>{escape(", ".join(decision.baseline_ids) or "無")}</dd>
          <dt>失效條件</dt><dd>{escape("；".join(decision.invalidation_conditions))}</dd>
        </dl>
        <pre>{escape(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))}</pre>
      </details>
    """


def render_strategy_research_panel(snapshot: DashboardSnapshot) -> str:
    card = snapshot.latest_strategy_card
    trial = snapshot.latest_experiment_trial
    evaluation = snapshot.latest_locked_evaluation
    leaderboard = snapshot.latest_leaderboard_entry
    outcome = snapshot.latest_paper_shadow_outcome
    agenda = snapshot.latest_research_agenda
    autopilot = snapshot.latest_research_autopilot_run
    revision_block = _render_strategy_revision_candidate(snapshot)
    lineage_block = _render_strategy_lineage_summary(snapshot.latest_strategy_lineage_summary)
    if (
        card is None
        and evaluation is None
        and leaderboard is None
        and outcome is None
        and agenda is None
        and autopilot is None
        and snapshot.latest_strategy_revision_card is None
    ):
        return """
      <div class="kicker">策略研究焦點</div>
      <h2>策略研究焦點</h2>
      <p class="lead">目前尚無 strategy card、leaderboard、paper-shadow 或 research autopilot artifact。</p>
      <p class="empty">研究頁會在相關 artifact 出現後顯示具體策略假設與證據鏈。</p>
    """

    return f"""
      <div class="kicker">策略研究焦點</div>
      <h2>策略研究焦點</h2>
      <p class="lead">{escape(card.hypothesis if card else "目前沒有策略假設 artifact。")}</p>
      <div class="summary-tags">
        <span class="tag">Strategy {_dashboard_artifact_id(card, "card_id")}</span>
        <span class="tag">Leaderboard {_dashboard_artifact_id(leaderboard, "entry_id")}</span>
        <span class="tag">下一步 {escape(autopilot.next_research_action if autopilot else "n/a")}</span>
      </div>
      {revision_block}
      {lineage_block}
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>目前策略假設</h3>
          <p class="decision-emphasis">{escape(card.strategy_name if card else "尚無策略卡")}</p>
          <dl>
            <dt>Family / Version</dt><dd>{escape(card.strategy_family if card else "n/a")} / {escape(card.version if card else "n/a")}</dd>
            <dt>Status</dt><dd>{escape(card.status if card else "n/a")}</dd>
            <dt>Signal</dt><dd>{escape(card.signal_description if card else "n/a")}</dd>
            <dt>參數</dt><dd>{_dashboard_dict_inline(card.parameters if card else {})}</dd>
          </dl>
        </div>
        <div class="evidence-block">
          <h3>下一步研究動作</h3>
          <p class="decision-emphasis">{escape(autopilot.next_research_action if autopilot else "n/a")}</p>
          <dl>
            <dt>Autopilot Run</dt><dd>{_dashboard_artifact_id(autopilot, "run_id")}</dd>
            <dt>Loop Status</dt><dd>{escape(autopilot.loop_status if autopilot else "n/a")}</dd>
            <dt>Blocked</dt><dd>{_dashboard_list_inline(autopilot.blocked_reasons if autopilot else [])}</dd>
          </dl>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>Evidence Gates</h3>
          <dl>
            <dt>Evaluation</dt><dd>{_dashboard_artifact_id(evaluation, "evaluation_id")}</dd>
            <dt>Passed / Rankable</dt><dd>{_display_boolean(evaluation.passed) if evaluation else "否"} / {_display_boolean(evaluation.rankable) if evaluation else "否"}</dd>
            <dt>alpha_score</dt><dd>{_format_optional_number(evaluation.alpha_score if evaluation else None)}</dd>
            <dt>Blocked</dt><dd>{_dashboard_list_inline(evaluation.blocked_reasons if evaluation else [])}</dd>
            <dt>Gate Metrics</dt><dd>{_dashboard_dict_inline(evaluation.gate_metrics if evaluation else {})}</dd>
          </dl>
        </div>
        <div class="evidence-block">
          <h3>Leaderboard</h3>
          <dl>
            <dt>Entry</dt><dd>{_dashboard_artifact_id(leaderboard, "entry_id")}</dd>
            <dt>Rankable</dt><dd>{_display_boolean(leaderboard.rankable) if leaderboard else "否"}</dd>
            <dt>alpha_score</dt><dd>{_format_optional_number(leaderboard.alpha_score if leaderboard else None)}</dd>
            <dt>Promotion</dt><dd>{escape(leaderboard.promotion_stage if leaderboard else "n/a")}</dd>
            <dt>Rules</dt><dd>{escape(leaderboard.leaderboard_rules_version if leaderboard else "n/a")}</dd>
          </dl>
        </div>
      </div>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>Paper-shadow 歸因</h3>
          <dl>
            <dt>Outcome</dt><dd>{_dashboard_artifact_id(outcome, "outcome_id")}</dd>
            <dt>Grade</dt><dd>{escape(outcome.outcome_grade if outcome else "n/a")}</dd>
            <dt>Excess after costs</dt><dd>{_format_optional_ratio(outcome.excess_return_after_costs if outcome else None)}</dd>
            <dt>Recommended</dt><dd>{escape(outcome.recommended_strategy_action if outcome else "n/a")}</dd>
            <dt>Failure attribution</dt><dd>{_dashboard_list_inline(outcome.failure_attributions if outcome else [])}</dd>
          </dl>
        </div>
        <div class="evidence-block">
          <h3>策略規則</h3>
          <dl>
            <dt>進場規則</dt><dd>{_dashboard_list_inline(card.entry_rules if card else [])}</dd>
            <dt>出場規則</dt><dd>{_dashboard_list_inline(card.exit_rules if card else [])}</dd>
            <dt>風控規則</dt><dd>{_dashboard_list_inline(card.risk_rules if card else [])}</dd>
            <dt>資料需求</dt><dd>{_dashboard_list_inline(card.data_requirements if card else [])}</dd>
          </dl>
        </div>
      </div>
      <details>
        <summary>展開 Research Agenda / Trial / Autopilot Steps</summary>
        <div class="drawer-stack">
          <dl>
            <dt>Agenda</dt><dd>{_dashboard_artifact_id(agenda, "agenda_id")} / {escape(agenda.title if agenda else "n/a")}</dd>
            <dt>Agenda Hypothesis</dt><dd>{escape(agenda.hypothesis if agenda else "n/a")}</dd>
            <dt>Acceptance</dt><dd>{_dashboard_list_inline(agenda.acceptance_criteria if agenda else [])}</dd>
            <dt>Trial</dt><dd>{_dashboard_artifact_id(trial, "trial_id")} / {escape(trial.status if trial else "n/a")}</dd>
            <dt>Trial Metrics</dt><dd>{_dashboard_dict_inline(trial.metric_summary if trial else {})}</dd>
            <dt>Autopilot Steps</dt><dd>{_dashboard_steps_inline(autopilot)}</dd>
          </dl>
        </div>
      </details>
    """


def _render_strategy_lineage_summary(summary: StrategyLineageSummary | None) -> str:
    if summary is None:
        return """
      <div class="evidence-block">
        <h3>策略 lineage</h3>
        <p class="micro-copy">目前沒有可彙整的策略 lineage。</p>
      </div>
    """
    return f"""
      <div class="evidence-block">
        <h3>策略 lineage</h3>
        <dl>
          <dt>Root Strategy</dt><dd><code>{escape(summary.root_card_id)}</code></dd>
          <dt>Revision Count</dt><dd>{summary.revision_count}</dd>
          <dt>Revision Cards</dt><dd>{_dashboard_list_inline(summary.revision_card_ids)}</dd>
          <dt>Revision Tree</dt><dd>{_dashboard_revision_tree(summary)}</dd>
          <dt>Shadow Outcomes</dt><dd>{summary.outcome_count}</dd>
          <dt>Actions</dt><dd>{_dashboard_dict_inline(summary.action_counts)}</dd>
          <dt>Failure Attribution</dt><dd>{_dashboard_dict_inline(summary.failure_attribution_counts)}</dd>
          <dt>Best / Worst Excess</dt><dd>{_format_optional_number(summary.best_excess_return_after_costs)} / {_format_optional_number(summary.worst_excess_return_after_costs)}</dd>
          <dt>Latest Outcome</dt><dd><code>{escape(summary.latest_outcome_id or "none")}</code></dd>
        </dl>
      </div>
    """


def _dashboard_revision_tree(summary: StrategyLineageSummary) -> str:
    if not summary.revision_nodes:
        return "none"
    return "<br>".join(
        f"Depth {node.depth} / Parent {escape(node.parent_card_id)} / <code>{escape(node.card_id)}</code>"
        f" / {escape(node.status)} / Name {escape(node.strategy_name)}"
        f" / Hypothesis {escape(node.hypothesis)}"
        f" / Source {escape(node.source_outcome_id or 'none')}"
        f" / Fixes {escape('；'.join(node.failure_attributions) if node.failure_attributions else 'none')}"
        for node in summary.revision_nodes
    )


def _render_strategy_revision_candidate(snapshot: DashboardSnapshot) -> str:
    revision = snapshot.latest_strategy_revision_card
    if revision is None:
        return """
      <div class="evidence-block">
        <h3>策略修正候選</h3>
        <p class="micro-copy">目前沒有 DRAFT 策略修正候選。若 paper-shadow 失敗，可用 <code>propose-strategy-revision</code> 建立下一個 retest hypothesis。</p>
      </div>
    """

    agenda = snapshot.latest_strategy_revision_agenda
    source = snapshot.latest_strategy_revision_source_outcome
    retest_trial = snapshot.latest_strategy_revision_retest_trial
    retest_split = snapshot.latest_strategy_revision_split_manifest
    attributions = revision.parameters.get("revision_failure_attributions", [])
    attribution_list = [str(item) for item in attributions] if isinstance(attributions, list) else [str(attributions)]
    return f"""
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>策略修正候選</h3>
          <p class="decision-emphasis">{escape(revision.strategy_name)}</p>
          <dl>
            <dt>Revision</dt><dd>{_dashboard_artifact_id(revision, "card_id")} / {escape(revision.status)}</dd>
            <dt>父策略</dt><dd>{escape(revision.parent_card_id or "n/a")}</dd>
            <dt>來源失敗</dt><dd>{_dashboard_artifact_id(source, "outcome_id")}</dd>
            <dt>Failure attribution</dt><dd>{_dashboard_list_inline(attribution_list)}</dd>
          </dl>
        </div>
        <div class="evidence-block">
          <h3>修正重點 / 重新測試 agenda</h3>
          <dl>
            <dt>修正假設</dt><dd>{escape(revision.hypothesis)}</dd>
            <dt>修正規則</dt><dd>{_dashboard_list_inline(revision.entry_rules + revision.exit_rules + revision.risk_rules)}</dd>
            <dt>Retest Agenda</dt><dd>{_dashboard_artifact_id(agenda, "agenda_id")} / {escape(agenda.title if agenda else "n/a")}</dd>
            <dt>Acceptance</dt><dd>{_dashboard_list_inline(agenda.acceptance_criteria if agenda else [])}</dd>
          </dl>
        </div>
      </div>
      <div class="evidence-block">
        <h3>Revision Retest Scaffold</h3>
        <dl>
          <dt>Retest Trial</dt><dd>{_dashboard_artifact_id(retest_trial, "trial_id")} / {escape(retest_trial.status if retest_trial else "尚未建立")}</dd>
          <dt>Dataset</dt><dd>{escape(retest_trial.dataset_id if retest_trial and retest_trial.dataset_id else "n/a")}</dd>
          <dt>Locked Split</dt><dd>{_dashboard_artifact_id(retest_split, "manifest_id")} / {escape(retest_split.status if retest_split else "尚未鎖定")}</dd>
          <dt>Next Required</dt><dd>{_dashboard_list_inline(snapshot.latest_strategy_revision_next_required_artifacts)}</dd>
        </dl>
        {_render_revision_retest_task_plan(snapshot.latest_strategy_revision_retest_task_plan)}
        {_render_revision_retest_task_run(snapshot.latest_strategy_revision_retest_task_run)}
        {_render_revision_retest_autopilot_run(snapshot.latest_strategy_revision_retest_autopilot_run)}
      </div>
    """


def _render_revision_retest_task_plan(plan: RevisionRetestTaskPlan | None) -> str:
    if plan is None:
        return """
        <div class="evidence-block subtle">
          <h4>下一個 retest 研究任務</h4>
          <p class="micro-copy">目前沒有可解析的 retest task plan。</p>
        </div>
        """
    next_task = plan.task_by_id(plan.next_task_id) if plan.next_task_id else None
    command = " ".join(next_task.command_args) if next_task and next_task.command_args else "無"
    return f"""
        <div class="evidence-block subtle">
          <h4>下一個 retest 研究任務</h4>
          <dl>
            <dt>Task</dt><dd><code>{escape(next_task.task_id if next_task else "none")}</code> / {escape(next_task.status if next_task else "completed")}</dd>
            <dt>Required Artifact</dt><dd><code>{escape(next_task.required_artifact if next_task else "none")}</code></dd>
            <dt>Blocked Reason</dt><dd>{escape(next_task.blocked_reason if next_task and next_task.blocked_reason else "none")}</dd>
            <dt>Missing Inputs</dt><dd>{_dashboard_list_inline(next_task.missing_inputs if next_task else [])}</dd>
            <dt>Command Args</dt><dd><code>{escape(command)}</code><br><span class="micro-copy">只顯示，不執行。</span></dd>
          </dl>
        </div>
    """


def _render_revision_retest_task_run(run: AutomationRun | None) -> str:
    if run is None:
        return """
        <div class="evidence-block subtle">
          <h4>最新 retest task run log</h4>
          <p class="micro-copy">尚未記錄 retest task run log；可用 <code>record-revision-retest-task-run</code> 寫入唯讀稽核紀錄。</p>
        </div>
        """
    return f"""
        <div class="evidence-block subtle">
          <h4>最新 retest task run log</h4>
          <dl>
            <dt>Status</dt><dd><span class="{_dashboard_automation_status_class(run.status)}">{escape(run.status)}</span></dd>
            <dt>Run ID</dt><dd><code>{escape(run.automation_run_id)}</code></dd>
            <dt>Command</dt><dd><code>{escape(run.command)}</code></dd>
            <dt>Completed</dt><dd>{escape(run.completed_at.isoformat())}</dd>
            <dt>Steps</dt><dd>{_dashboard_run_step_list(run)}</dd>
          </dl>
          <p class="micro-copy">這是 PR18 寫入的稽核紀錄；只顯示，不執行。</p>
        </div>
    """


def _render_revision_retest_autopilot_run(run: ResearchAutopilotRun | None) -> str:
    if run is None:
        return """
        <div class="evidence-block subtle">
          <h4>最新 revision retest autopilot run</h4>
          <p class="micro-copy">尚未記錄 completed revision retest chain 的 research autopilot run；可用 <code>record-revision-retest-autopilot-run</code> 寫入閉環證據。</p>
        </div>
        """
    return f"""
        <div class="evidence-block subtle">
          <h4>最新 revision retest autopilot run</h4>
          <dl>
            <dt>Loop Status</dt><dd><span class="{_dashboard_automation_status_class(run.loop_status)}">{escape(run.loop_status)}</span></dd>
            <dt>Run ID</dt><dd><code>{escape(run.run_id)}</code></dd>
            <dt>Next Action</dt><dd>{escape(run.next_research_action)}</dd>
            <dt>Paper-shadow Outcome</dt><dd><code>{escape(run.paper_shadow_outcome_id or "none")}</code></dd>
            <dt>Blocked</dt><dd>{_dashboard_list_inline(run.blocked_reasons)}</dd>
            <dt>Steps</dt><dd>{_dashboard_steps_inline(run)}</dd>
          </dl>
          <p class="micro-copy">這是 revision retest 完整閉環的 research autopilot 紀錄；只顯示，不執行。</p>
        </div>
    """


def _dashboard_run_step_list(run: AutomationRun) -> str:
    if not run.steps:
        return '<span class="micro-copy">沒有 step 記錄。</span>'
    rows = "".join(
        "<li>"
        f"{escape(step.get('name') or '')}: {escape(step.get('status') or '')} "
        f"<code>{escape(step.get('artifact_id') or 'none')}</code>"
        "</li>"
        for step in run.steps
    )
    return f'<ul class="compact-list">{rows}</ul>'


def _dashboard_automation_status_class(status: str) -> str:
    if status in {"BLOCKED", "RETEST_TASK_BLOCKED", "failed", "repair_required"}:
        return "tag warn"
    return "tag ok"


def render_portfolio_risk_panel(snapshot: DashboardSnapshot) -> str:
    portfolio = snapshot.latest_portfolio_snapshot
    risk = snapshot.latest_risk_snapshot
    if portfolio is None:
        return """
      <div class="kicker">投資組合與風險</div>
      <h2>Paper NAV / 風險</h2>
      <p class="lead">目前還沒有 paper 投資組合快照。請先用 <code>portfolio-snapshot</code> 或 paper fill 產生 NAV 資料。</p>
      <p class="empty">沒有 portfolio snapshot。</p>
    """

    nav = portfolio.nav if portfolio.nav is not None else portfolio.equity
    risk_status = "尚無 risk-check 快照。" if risk is None else _display_risk_status(risk.status)
    risk_copy = (
        "請執行 risk-check 產生 drawdown 與 exposure gate。"
        if risk is None
        else "；".join(risk.findings) if risk.findings else "目前沒有 drawdown 或曝險超標 finding。"
    )
    return f"""
      <div class="kicker">投資組合與風險</div>
      <h2>Paper NAV / 風險</h2>
      <p class="lead">這裡只顯示 paper-only 投資組合、PnL、drawdown 和曝險，不代表任何真實帳戶或外部 broker 狀態。</p>
      <div class="primary-grid">
        <div class="summary-card"><div class="summary-label">NAV / Equity</div><div class="summary-value">{nav:.2f}</div><div class="summary-copy">paper-only 淨值，不是真實資金。</div></div>
        <div class="summary-card"><div class="summary-label">現金</div><div class="summary-value">{portfolio.cash:.2f}</div><div class="summary-copy">內部 paper ledger 現金。</div></div>
        <div class="summary-card"><div class="summary-label">已實現 / 未實現 PnL</div><div class="summary-value">{portfolio.realized_pnl:.2f} / {portfolio.unrealized_pnl:.2f}</div><div class="summary-copy">由 local paper fills 與 mark-to-market 推導。</div></div>
        <div class="summary-card"><div class="summary-label">風險狀態</div><div class="summary-value">{escape(risk_status)}</div><div class="summary-copy">{escape(risk_copy)}</div></div>
      </div>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>曝險</h3>
          <p class="micro-copy">Gross exposure：{portfolio.gross_exposure_pct:.2%}；Net exposure：{portfolio.net_exposure_pct:.2%}。</p>
        </div>
        <div class="evidence-block">
          <h3>Drawdown Gate</h3>
          <p class="micro-copy">{escape(_risk_threshold_copy(risk))}</p>
        </div>
      </div>
    """


def render_broker_panel(snapshot: DashboardSnapshot) -> str:
    gate = snapshot.latest_execution_safety_gate
    reconciliation = snapshot.latest_broker_reconciliation
    portfolio = snapshot.latest_portfolio_snapshot
    active_broker_orders = _active_broker_orders(snapshot.broker_orders)
    open_paper_orders = [order for order in snapshot.paper_orders if order.status == "CREATED"]
    latest_fill = snapshot.paper_fills[-1] if snapshot.paper_fills else None
    broker_mode = _broker_mode(snapshot)
    gate_status = "尚無 execution-gate。"
    failed_checks: list[str] = []
    if gate is not None:
        gate_status = "允許 sandbox/paper 執行" if gate.allowed else "執行被安全門擋下"
        failed_checks = [check.get("code", "unknown") for check in gate.checks if check.get("status") == "fail"]
    reconciliation_status = "尚無 broker reconciliation。"
    if reconciliation is not None:
        reconciliation_status = (
            "對帳通過"
            if not reconciliation.repair_required and reconciliation.severity != "blocking"
            else "對帳有阻擋性差異"
        )
    account_copy = (
        "尚無 paper portfolio snapshot，因此沒有可對照的帳戶摘要。"
        if portfolio is None
        else f"NAV {portfolio.nav or portfolio.equity:.2f}；Cash {portfolio.cash:.2f}；部位數 {len(portfolio.positions)}。"
    )
    order_copy = (
        f"Open paper orders：{len(open_paper_orders)}；active broker lifecycle rows：{len(active_broker_orders)}。"
    )
    fill_copy = (
        "尚無 paper fills。"
        if latest_fill is None
        else f"最新 fill {latest_fill.fill_id}；{latest_fill.symbol} {latest_fill.side} {latest_fill.quantity} @ {latest_fill.fill_price:.2f}。"
    )
    mismatch_copy = _broker_mismatch_copy(reconciliation)
    failed_check_copy = "無" if not failed_checks else "、".join(failed_checks)
    return f"""
      <div class="kicker">Broker / Sandbox</div>
      <h2>Broker / Sandbox 狀態</h2>
      <p class="lead">這裡只讀本地 paper/sandbox artifacts，不連線 broker、不讀 secrets、不送出任何訂單。</p>
      <div class="primary-grid">
        <div class="summary-card"><div class="summary-label">Broker Mode</div><div class="summary-value">{escape(broker_mode)}</div><div class="summary-copy">允許的模式只有 EXTERNAL_PAPER / SANDBOX；LIVE 不可用。</div></div>
        <div class="summary-card"><div class="summary-label">Execution Gate</div><div class="summary-value">{escape(gate.status if gate else "MISSING")}</div><div class="summary-copy">{escape(gate_status)}</div></div>
        <div class="summary-card"><div class="summary-label">Reconciliation</div><div class="summary-value">{escape(reconciliation.status if reconciliation else "MISSING")}</div><div class="summary-copy">{escape(reconciliation_status)}</div></div>
        <div class="summary-card"><div class="summary-label">Broker Health</div><div class="summary-value">{escape(_broker_health_from_gate(gate))}</div><div class="summary-copy">來自最近一次 execution-gate 的 broker health fixture 檢查。</div></div>
      </div>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>帳戶快照 / Positions</h3>
          <p class="micro-copy">{escape(account_copy)}</p>
          <p class="micro-copy">{escape(_positions_copy(portfolio))}</p>
        </div>
        <div class="evidence-block">
          <h3>Orders / Fills</h3>
          <p class="micro-copy">{escape(order_copy)}</p>
          <p class="micro-copy">{escape(fill_copy)}</p>
        </div>
        <div class="evidence-block">
          <h3>Mismatch Warnings</h3>
          <p class="micro-copy">{escape(mismatch_copy)}</p>
        </div>
        <div class="evidence-block">
          <h3>Execution Enabled / Disabled</h3>
          <p class="micro-copy">{escape(_display_boolean(gate.allowed) if gate else "否")}</p>
          <p class="micro-copy">Failed checks：{escape(failed_check_copy)}</p>
        </div>
      </div>
      <details>
        <summary>展開 broker artifacts</summary>
        <dl>
          <dt>Execution Gate ID</dt><dd>{escape(gate.gate_id if gate else "無")}</dd>
          <dt>Broker Reconciliation ID</dt><dd>{escape(reconciliation.reconciliation_id if reconciliation else "無")}</dd>
          <dt>最新 Broker Order</dt><dd>{escape(snapshot.broker_orders[-1].broker_order_id if snapshot.broker_orders else "無")}</dd>
          <dt>最新 Paper Fill</dt><dd>{escape(latest_fill.fill_id if latest_fill else "無")}</dd>
        </dl>
      </details>
    """


def render_provider_panel(snapshot: DashboardSnapshot) -> str:
    provider_run = snapshot.latest_provider_run
    if provider_run is None:
        return """
      <div class="kicker">資料來源健康</div>
      <h2>Provider Audit</h2>
      <p class="lead">目前還沒有 provider run audit。下一次 run-once 會記錄資料來源讀取狀態。</p>
      <p class="empty">沒有 provider_runs.jsonl。</p>
    """

    status_class = "warn" if provider_run.status in {"error", "empty"} else "ok"
    data_window = (
        "無"
        if provider_run.data_start is None or provider_run.data_end is None
        else _format_window_label(provider_run.data_start, provider_run.data_end)
    )
    error_copy = (
        "沒有 provider error。"
        if provider_run.error_type is None
        else f"{provider_run.error_type}: {provider_run.error_message}"
    )
    return f"""
      <div class="kicker">資料來源健康</div>
      <h2>Provider Audit</h2>
      <p class="lead">這裡顯示最近一次資料來源讀取，不代表交易所或 broker 狀態。</p>
      <div class="primary-grid">
        <div class="summary-card"><div class="summary-label">Provider</div><div class="summary-value">{escape(provider_run.provider)}</div><div class="summary-copy">{escape(provider_run.symbol)} / {escape(provider_run.operation)}</div></div>
        <div class="summary-card"><div class="summary-label">狀態</div><div class="summary-value"><span class="tag {status_class}">{escape(_display_provider_status(provider_run.status))}</span></div><div class="summary-copy">{escape(error_copy)}</div></div>
        <div class="summary-card"><div class="summary-label">資料筆數</div><div class="summary-value">{provider_run.candle_count}</div><div class="summary-copy">market candle rows observed by this provider call。</div></div>
        <div class="summary-card"><div class="summary-label">資料視窗</div><div class="summary-value">{escape(data_window)}</div><div class="summary-copy">schema {escape(provider_run.schema_version)}；完成 {escape(provider_run.completed_at.isoformat())}</div></div>
      </div>
    """


def render_forecast_panel(forecast: Forecast | None) -> str:
    if forecast is None:
        return """
      <div class="kicker">主要視圖</div>
      <h2>目前預測</h2>
      <p class="lead">目前還沒有預測資料。當預測循環寫入新產物後，這個面板會成為操作員優先查看的主卡片。</p>
      <p class="empty">目前還沒有預測資料。</p>
    """

    return f"""
      <div class="kicker">主要視圖</div>
      <h2>目前預測</h2>
      <p class="lead">{escape(forecast.symbol)} 是目前的即時操作視圖。解讀 replay 或原始中繼資料前，請先讀這張卡片。</p>
      <div class="meta"><span class="tag">{escape(_display_forecast_status(forecast.status))}</span> <span class="tag">{escape(_display_status_reason(forecast.status_reason))}</span></div>
      <div class="primary-grid">
        <div class="summary-card"><div class="summary-label">預測 regime</div><div class="summary-value">{escape(_display_regime(forecast.predicted_regime))}</div><div class="summary-copy">這一輪對市場狀態的判讀。</div></div>
        <div class="summary-card"><div class="summary-label">信心值</div><div class="summary-value">{escape(str(forecast.confidence))}</div><div class="summary-copy">模型對這筆預測的信心。</div></div>
        <div class="summary-card"><div class="summary-label">已觀測 K 線</div><div class="summary-value">{forecast.observed_candle_count} / {forecast.expected_candle_count}</div><div class="summary-copy">目前已捕捉到的覆蓋進度。</div></div>
        <div class="summary-card"><div class="summary-label">目標視窗</div><div class="summary-value">{escape(_format_window_label(forecast.target_window_start, forecast.target_window_end))}</div><div class="summary-copy">這筆預測目前對應的觀察區間。</div></div>
      </div>
      <details>
        <summary>展開 forecast 詳細欄位</summary>
        <dl>
          <dt>Forecast ID</dt><dd>{escape(forecast.forecast_id)}</dd>
          <dt>Anchor</dt><dd>{escape(forecast.anchor_time.isoformat())}</dd>
          <dt>目標視窗</dt><dd>{escape(forecast.target_window_start.isoformat())} → {escape(forecast.target_window_end.isoformat())}</dd>
          <dt>建立時間</dt><dd>{escape(forecast.created_at.isoformat())}</dd>
          <dt>K 線間隔</dt><dd>{forecast.candle_interval_minutes} 分鐘</dd>
          <dt>Provider Through</dt><dd>{escape(str(forecast.provider_data_through.isoformat()) if forecast.provider_data_through else "None")}</dd>
        </dl>
        <pre>{escape(json.dumps(forecast.to_dict(), ensure_ascii=False, indent=2))}</pre>
      </details>
    """


def render_score_panel(score: ForecastScore | None) -> str:
    if score is None:
        return """
      <div class="kicker">最新評分</div>
      <h2>評分快照</h2>
      <p class="empty">目前還沒有評分資料。</p>
    """

    return f"""
      <div class="kicker">最新評分</div>
      <h2>評分快照</h2>
      <div class="meta">{escape(_display_regime(score.predicted_regime))} → {escape(_display_regime(score.actual_regime))}</div>
      <dl>
        <dt>Score ID</dt><dd>{escape(score.score_id)}</dd>
        <dt>分數</dt><dd>{score.score:.2f}</dd>
        <dt>對應預測</dt><dd>{escape(score.forecast_id)}</dd>
        <dt>已觀測 K 線</dt><dd>{score.observed_candle_count} / {score.expected_candle_count}</dd>
        <dt>Provider Through</dt><dd>{escape(score.provider_data_through.isoformat())}</dd>
      </dl>
    """


def render_evidence_panel(snapshot: DashboardSnapshot) -> str:
    latest_score = snapshot.latest_score
    evidence_lead = _summarize_evidence(snapshot)
    score_html = (
        f"""
      <dl>
        <dt>Score ID</dt><dd>{escape(latest_score.score_id)}</dd>
        <dt>分數</dt><dd>{latest_score.score:.2f}</dd>
        <dt>對應預測</dt><dd>{escape(latest_score.forecast_id)}</dd>
        <dt>已觀測 K 線</dt><dd>{latest_score.observed_candle_count} / {latest_score.expected_candle_count}</dd>
      </dl>
        """
        if latest_score is not None
        else '<p class="empty">最新評分尚未產生；這不影響目前預測主卡的閱讀順序。</p>'
    )
    score_detail_html = (
        f"""
        <details>
          <summary>展開最新 score 詳細欄位</summary>
          <pre>{escape(json.dumps(latest_score.to_dict(), ensure_ascii=False, indent=2))}</pre>
        </details>
        """
        if latest_score is not None
        else ""
    )
    return f"""
      <div class="kicker">證據鏈</div>
      <h2>支撐依據</h2>
      <p class="lead">{escape(evidence_lead)}</p>
      <div class="evidence-grid">
        <div class="evidence-block">
          <h3>已儲存產物</h3>
          <div class="meta">儲存位置：{escape(str(snapshot.storage_dir.resolve()))}</div>
          <div class="stat-grid">
            <div class="stat"><div class="stat-label">預測</div><div class="stat-value">{snapshot.forecast_count}</div></div>
            <div class="stat"><div class="stat-label">評分</div><div class="stat-value">{snapshot.score_count}</div></div>
            <div class="stat"><div class="stat-label">檢討</div><div class="stat-value">{snapshot.review_count}</div></div>
            <div class="stat"><div class="stat-label">提案</div><div class="stat-value">{snapshot.proposal_count}</div></div>
            <div class="stat"><div class="stat-label">Replay 摘要</div><div class="stat-value">{snapshot.replay_summary_count}</div></div>
          </div>
        </div>
        <div class="evidence-block">
          <h3>最新評分與唯讀指令</h3>
          <p class="micro-copy">評分只作為檢討證據補充。即使這裡有新資料，操作員也不應跳過上方的目前預測與檢討主卡。</p>
          {score_html}
          {score_detail_html}
          <div class="command-tags">
            <span class="tag">run-once</span>
            <span class="tag">replay-range</span>
            <span class="tag">render-dashboard</span>
          </div>
        </div>
      </div>
    """


def render_decision_panel(review: Review | None, proposal: Proposal | None) -> str:
    if review is None:
        return """
      <div class="kicker">操作判讀</div>
      <h2>本輪判讀與建議</h2>
      <p class="lead">目前還沒有 review/proposal 產物，因此這一區暫時只能維持「等待檢討」狀態。</p>
      <p class="empty">目前還沒有檢討資料。</p>
    """

    proposal_summary = _summarize_proposal_surface(proposal)
    proposal_html = (
        f"""
        <details>
          <summary>最新提案</summary>
          <pre>{escape(json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2))}</pre>
        </details>
        """
        if proposal is not None
        else '<p class="empty">目前沒有產生提案。</p>'
    )
    return f"""
      <div class="kicker">操作判讀</div>
      <h2>本輪判讀與建議</h2>
      <p class="lead">{escape(review.summary)}</p>
      <div class="decision-grid">
        <div class="decision-block">
          <h3>本輪結論</h3>
          <p class="decision-emphasis">{escape(_display_decision_surface(review, proposal))}</p>
        </div>
        <div class="decision-block">
          <h3>操作面建議</h3>
          <div class="meta">{escape(proposal_summary)}</div>
          <div class="stat-grid">
            <div class="stat"><div class="stat-label">平均分數</div><div class="stat-value">{review.average_score:.2f}</div></div>
            <div class="stat"><div class="stat-label">門檻值</div><div class="stat-value">{review.threshold_used:.2f}</div></div>
            <div class="stat"><div class="stat-label">需要提案</div><div class="stat-value">{escape(_display_boolean(review.proposal_recommended))}</div></div>
          </div>
        </div>
      </div>
      <details>
        <summary>展開 review / proposal 詳細欄位</summary>
        <div class="drawer-stack">
          <dl>
            <dt>Review ID</dt><dd>{escape(review.review_id)}</dd>
            <dt>Forecast IDs</dt><dd>{escape(", ".join(review.forecast_ids) or "None")}</dd>
            <dt>Score IDs</dt><dd>{escape(", ".join(review.score_ids) or "None")}</dd>
            <dt>Decision Basis</dt><dd>{escape(review.decision_basis)}</dd>
            <dt>Proposal Reason</dt><dd>{escape(review.proposal_reason)}</dd>
          </dl>
          <pre>{escape(json.dumps(review.to_dict(), ensure_ascii=False, indent=2))}</pre>
          {proposal_html}
        </div>
      </details>
    """


def render_replay_panel(snapshot: DashboardSnapshot, summary: EvaluationSummary | None) -> str:
    if summary is None:
        return """
      <div class="kicker">歷史脈絡</div>
      <h2>歷史脈絡</h2>
      <p class="empty">目前還沒有 replay 摘要。</p>
    """

    replay_copy = (
        "僅供歷史脈絡參考。replay 落後最新預測時，仍應以目前預測卡為主。"
        if snapshot.replay_is_stale
        else "replay 證據足夠新，可補充操作脈絡，但仍是次要參考。"
    )
    replay_tag_class = "warn" if snapshot.replay_is_stale else "ok"

    return f"""
      <div class="kicker">歷史脈絡</div>
      <h2>歷史脈絡</h2>
      <p class="micro-copy">{escape(replay_copy)}</p>
      <div class="summary-tags">
        <span class="tag {replay_tag_class}">{escape(_display_replay_freshness(snapshot.replay_freshness_label))}</span>
        <span class="tag">產生時間：{escape(summary.generated_at.isoformat())}</span>
      </div>
      <dl>
        <dt>Forecast 數量</dt><dd>{summary.forecast_count}</dd>
        <dt>已完成</dt><dd>{summary.resolved_count}</dd>
        <dt>等待中</dt><dd>{summary.waiting_for_data_count}</dd>
        <dt>無法評分</dt><dd>{summary.unscorable_count}</dd>
        <dt>平均分數</dt><dd>{escape("無" if summary.average_score is None else f"{summary.average_score:.2f}")}</dd>
      </dl>
      <details>
        <summary>展開 replay 詳細資料</summary>
        <dl>
          <dt>Summary ID</dt><dd>{escape(summary.summary_id)}</dd>
          <dt>產生時間</dt><dd>{escape(summary.generated_at.isoformat())}</dd>
          <dt>視窗</dt><dd>{escape(str(summary.replay_window_start.isoformat()) if summary.replay_window_start else "None")} → {escape(str(summary.replay_window_end.isoformat()) if summary.replay_window_end else "None")}</dd>
        </dl>
      </details>
    """


def write_dashboard_html(storage_dir: Path | str, output_path: Path | str | None = None) -> Path:
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        raise ValueError(f"storage dir does not exist: {storage_path}")
    if not storage_path.is_dir():
        raise ValueError(f"storage dir is not a directory: {storage_path}")

    snapshot = build_dashboard_snapshot(storage_path)
    html = render_dashboard_html(snapshot)
    output_path = Path(output_path) if output_path is not None else storage_path / "dashboard.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_proposal_for_review(proposals: list[Proposal], review: Review | None) -> Proposal | None:
    if review is None:
        return None
    return next((proposal for proposal in reversed(proposals) if proposal.review_id == review.review_id), None)


def _load_automation_state(automation_id: str) -> AutomationState:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    path = codex_home / "automations" / automation_id / "automation.toml"
    if not path.exists():
        return AutomationState(status="NOT_FOUND", updated_at=None)
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return AutomationState(
        status=payload.get("status", "UNKNOWN"),
        updated_at=_automation_timestamp(payload.get("updated_at")),
    )


def _automation_timestamp(raw_value) -> datetime | None:
    if not isinstance(raw_value, int | float):
        return None
    return datetime.fromtimestamp(raw_value / 1000, tz=UTC)


def _derive_mode(hourly_status: str, building_status: str) -> tuple[str, str]:
    if building_status == "ACTIVE":
        return "Building Mode", "Loop Building Heartbeat is active while the system is still being improved."
    if hourly_status == "ACTIVE":
        return "Hourly Research Mode", "Hourly Paper Forecast is active and the system is running paper-only prediction cycles."
    if hourly_status == "PAUSED":
        return "Paused Prediction Mode", "Hourly Paper Forecast is paused while the system remains under manual inspection."
    return "Manual Mode", "No known automation is currently active for this workspace."


def _derive_replay_freshness(
    summary: EvaluationSummary | None,
    latest_forecast: Forecast | None,
) -> tuple[str, datetime | None, bool]:
    if summary is None:
        return "No replay summary yet", None, False
    if latest_forecast is None or summary.anchor_time_end is None:
        return "Historical replay available", summary.generated_at, False
    delta = latest_forecast.anchor_time - summary.anchor_time_end
    if delta > timedelta(hours=1):
        hours = int(delta.total_seconds() // 3600)
        return f"Replay is historical ({hours}h behind latest forecast)", summary.generated_at, True
    return "Replay aligns with the latest forecast window", summary.generated_at, False


def _summarize_health(snapshot: DashboardSnapshot) -> tuple[str, str]:
    if snapshot.latest_forecast is None:
        return "Waiting", "Waiting for the first forecast cycle."
    status = snapshot.latest_forecast.status
    if status == "pending":
        return "Open Forecast", "Current forecast is still open, so operator attention should stay on the live forecast card."
    if status == "waiting_for_data":
        return "Waiting For Data", "The forecast horizon has ended, but provider coverage is not complete yet."
    if status == "unscorable":
        return "Unscorable", "The forecast horizon finished, but the realized candle window is incomplete or invalid."
    if snapshot.latest_review is not None:
        return "Reviewed", "Latest resolved forecast has review output recorded for operator follow-through."
    if status == "resolved":
        return "Resolved", "Latest forecast has resolved, but downstream review output has not been recorded yet."
    return "Needs Attention", "Latest forecast is in a terminal or degraded state that should be inspected before relying on it."


def _judgment_label(snapshot: DashboardSnapshot) -> str:
    if snapshot.latest_review is not None:
        if snapshot.latest_review.proposal_recommended:
            return "Change Recommended"
        return "Keep Current Setup"
    if snapshot.latest_forecast is None:
        return "No Judgment Yet"
    if snapshot.latest_forecast.status == "pending":
        return "Awaiting Horizon End"
    if snapshot.latest_forecast.status == "waiting_for_data":
        return "Waiting For Data"
    if snapshot.latest_forecast.status == "unscorable":
        return "Unscorable"
    return "Awaiting Review"


def _summarize_judgment(snapshot: DashboardSnapshot) -> str:
    if snapshot.latest_review is not None:
        return snapshot.latest_review.summary
    if snapshot.latest_forecast is None:
        return "No judgment is available yet because no forecast cycle has produced a current forecast artifact."
    if snapshot.latest_forecast.status == "pending":
        return "The current forecast window is still live, so replay should be treated as supporting history rather than the latest judgment."
    if snapshot.latest_forecast.status == "waiting_for_data":
        return "The forecast horizon has ended, but provider coverage is still incomplete."
    if snapshot.latest_forecast.status == "unscorable":
        return "The forecast horizon ended, but the realized window could not be scored."
    return "The latest forecast has finished its window, but review and proposal artifacts have not been written yet."


def _display_mode(mode: str) -> str:
    mapping = {
        "Building Mode": "建置模式",
        "Hourly Research Mode": "每小時研究模式",
        "Paused Prediction Mode": "暫停預測模式",
        "Manual Mode": "手動模式",
    }
    return mapping.get(mode, mode)


def _display_mode_reason(mode: str, reason: str) -> str:
    mapping = {
        "Building Mode": "Loop Building Heartbeat 目前啟用，系統仍在調整與建置中。",
        "Hourly Research Mode": "Hourly Paper Forecast 目前啟用，系統正在執行 paper-only 預測循環。",
        "Paused Prediction Mode": "Hourly Paper Forecast 目前暫停，系統處於人工檢查狀態。",
        "Manual Mode": "這個工作區目前沒有已知的自動化正在執行。",
    }
    return mapping.get(mode, reason)


def _display_automation_status(status: str) -> str:
    mapping = {
        "ACTIVE": "啟用中（ACTIVE）",
        "PAUSED": "已暫停（PAUSED）",
        "NOT_FOUND": "未找到（NOT_FOUND）",
        "UNKNOWN": "未知（UNKNOWN）",
    }
    return mapping.get(status, status)


def _display_strategy_action(action: str) -> str:
    mapping = {
        "BUY": "買進（BUY）",
        "SELL": "賣出（SELL）",
        "HOLD": "持有（HOLD）",
        "REDUCE_RISK": "降低風險（REDUCE_RISK）",
        "STOP_NEW_ENTRIES": "停止新進場（STOP_NEW_ENTRIES）",
    }
    return mapping.get(action, action)


def _display_strategy_reason(decision: StrategyDecision) -> str:
    if decision.blocked_reason == "health_check_repair_required":
        return "health-check 需要修復；Codex 修復完成前停止新進場。"
    if decision.blocked_reason == "missing_latest_forecast":
        return "目前沒有最新 forecast；系統不能產生方向性的 paper-only 決策。"
    if decision.blocked_reason == "latest_forecast_stale":
        return "最新 forecast 已超過允許時效；停止新進場直到資料恢復新鮮。"
    if decision.blocked_reason == "insufficient_evidence":
        return "已評分 forecast 樣本不足，不足以支持買進或賣出。"
    if decision.blocked_reason == "model_not_beating_baseline":
        return "模型證據沒有打贏 naive persistence baseline，因此買進/賣出被擋住。"
    if decision.blocked_reason == "evidence_grade_too_weak_for_directional_action":
        return "證據方向偏正面，但強度不足以支持買進或賣出。"
    if decision.blocked_reason == "unknown_forecast_regime":
        return "最新 forecast regime 方向性不足，不應產生買進或賣出。"
    if decision.blocked_reason == "risk_stop_new_entries":
        return "風險檢查觸發停止新進場 gate；暫停方向性 paper order。"
    if decision.blocked_reason == "risk_reduce_required_but_no_position":
        return "風險檢查要求降低風險，但目前沒有可降低的 paper 部位。"
    if decision.blocked_reason == "risk_snapshot_missing":
        return "缺少 risk-check 快照，方向性買進/賣出被停止。"
    if decision.blocked_reason == "risk_snapshot_stale":
        return "risk-check 快照已過期，方向性買進/賣出被停止。"
    if decision.blocked_reason == "risk_snapshot_symbol_mismatch":
        return "risk-check 快照 symbol 不一致，方向性買進/賣出被停止。"
    if decision.action == "BUY":
        return "最新 forecast 偏多，且模型證據在品質足夠時打贏 baseline。"
    if decision.action == "SELL":
        return "最新 forecast 偏空，且模型證據在品質足夠時打贏 baseline。"
    if decision.action == "REDUCE_RISK":
        return "近期 forecast 分數偏弱，建議降低 paper 風險。"
    if decision.action == "STOP_NEW_ENTRIES":
        return "系統目前不允許新增進場，請先檢查 health 與資料新鮮度。"
    return decision.reason_summary


def _display_evidence_grade(grade: str) -> str:
    mapping = {
        "A": "證據等級 A",
        "B": "證據等級 B",
        "C": "證據等級 C",
        "D": "證據等級 D",
        "INSUFFICIENT": "證據不足（INSUFFICIENT）",
    }
    return mapping.get(grade, grade)


def _display_risk_level(level: str) -> str:
    mapping = {
        "LOW": "低風險（LOW）",
        "MEDIUM": "中風險（MEDIUM）",
        "HIGH": "高風險（HIGH）",
        "UNKNOWN": "風險未知（UNKNOWN）",
    }
    return mapping.get(level, level)


def _display_risk_status(status: str) -> str:
    mapping = {
        "OK": "正常（OK）",
        "REDUCE_RISK": "降低風險（REDUCE_RISK）",
        "STOP_NEW_ENTRIES": "停止新進場（STOP_NEW_ENTRIES）",
    }
    return mapping.get(status, status)


def _display_provider_status(status: str) -> str:
    mapping = {
        "success": "正常（success）",
        "empty": "空資料（empty）",
        "error": "失敗（error）",
    }
    return mapping.get(status, status)


def _risk_threshold_copy(risk: RiskSnapshot | None) -> str:
    if risk is None:
        return "尚未執行 risk-check，因此沒有 drawdown gate 快照。"
    return (
        f"目前回撤 {risk.current_drawdown_pct:.2%}；最大回撤 {risk.max_drawdown_pct:.2%}；"
        f"降低風險門檻 {risk.reduce_risk_drawdown_pct:.2%}；"
        f"停止新進場門檻 {risk.stop_new_entries_drawdown_pct:.2%}。"
    )


def _broker_mode(snapshot: DashboardSnapshot) -> str:
    if snapshot.latest_execution_safety_gate is not None:
        return snapshot.latest_execution_safety_gate.broker_mode
    if snapshot.latest_broker_reconciliation is not None:
        return snapshot.latest_broker_reconciliation.broker_mode
    if snapshot.broker_orders:
        return snapshot.broker_orders[-1].broker_mode
    return "尚無 broker mode artifact"


def _broker_health_from_gate(gate: ExecutionSafetyGate | None) -> str:
    if gate is None:
        return "MISSING"
    broker_health = next((check for check in gate.checks if check.get("code") == "broker_health"), None)
    if broker_health is None:
        return "MISSING"
    return "HEALTHY" if broker_health.get("status") == "pass" else "BLOCKING"


def _active_broker_orders(orders: list[BrokerOrder]) -> list[BrokerOrder]:
    terminal = {"FILLED", "CANCELLED", "REJECTED", "EXPIRED", "ERROR"}
    return [order for order in orders if order.status not in terminal]


def _positions_copy(portfolio: PaperPortfolioSnapshot | None) -> str:
    if portfolio is None or not portfolio.positions:
        return "目前沒有 paper positions。"
    return "；".join(
        f"{position.symbol} qty {position.quantity:g} / value {position.market_value:.2f}"
        for position in portfolio.positions[:5]
    )


def _broker_mismatch_copy(reconciliation: BrokerReconciliation | None) -> str:
    if reconciliation is None:
        return "尚無 reconciliation artifact；M6E broker-reconcile 尚未執行。"
    if not reconciliation.findings:
        return "沒有 reconciliation mismatch finding。"
    codes = [str(finding.get("code", "unknown")) for finding in reconciliation.findings[:6]]
    return "；".join(codes)


def _display_health_status(status: str, repair_required: bool) -> str:
    if repair_required:
        return "需要修復（repair required）"
    mapping = {
        "healthy": "健康（healthy）",
        "degraded": "降級（degraded）",
        "unhealthy": "不健康（unhealthy）",
    }
    return mapping.get(status, status)


def _display_blocked_reason(reason: str | None) -> str:
    mapping = {
        None: "未被決策 gate 阻擋",
        "health_check_repair_required": "health-check 要求修復，停止新進場。",
        "missing_latest_forecast": "缺少最新 forecast，不能做方向性決策。",
        "latest_forecast_stale": "最新 forecast 已過期，不能做方向性決策。",
        "insufficient_evidence": "證據不足，不能支持買進或賣出。",
        "model_not_beating_baseline": "模型沒有打贏基準線，買進/賣出被擋住。",
        "evidence_grade_too_weak_for_directional_action": "證據等級不足，不能支持買進或賣出。",
        "unknown_forecast_regime": "forecast regime 方向性不足。",
        "risk_stop_new_entries": "風險 gate 觸發停止新進場。",
        "risk_reduce_required_but_no_position": "風險 gate 要求降風險，但目前沒有可降低的 paper 部位。",
        "risk_snapshot_missing": "缺少 risk-check 快照，方向性買進/賣出被停止。",
        "risk_snapshot_stale": "risk-check 快照已過期，方向性買進/賣出被停止。",
        "risk_snapshot_symbol_mismatch": "risk-check 快照 symbol 不一致，方向性買進/賣出被停止。",
    }
    return mapping.get(reason, reason or "未被決策 gate 阻擋")


def _display_health_label(label: str) -> str:
    mapping = {
        "Waiting": "等待中",
        "Open Forecast": "進行中預測",
        "Waiting For Data": "等待資料覆蓋",
        "Unscorable": "無法評分",
        "Reviewed": "已檢討",
        "Resolved": "已結束",
        "Needs Attention": "需要檢查",
    }
    return mapping.get(label, label)


def _display_health_copy(label: str, copy: str) -> str:
    mapping = {
        "Waiting": "等待第一筆預測循環。",
        "Open Forecast": "目前這筆預測仍在開放視窗內，操作注意力應優先放在即時預測卡。",
        "Waiting For Data": "預測視窗已結束，但仍在等待 provider 補齊目標視窗資料。",
        "Unscorable": "目標視窗資料不完整或無效，這筆預測不能被當成已正常評分。",
        "Reviewed": "最新已結束的預測已留下檢討輸出，可直接往後續追蹤。",
        "Resolved": "最新預測已結束，但下游檢討輸出尚未寫入。",
        "Needs Attention": "最新預測處於需要人工確認的狀態，先檢查詳細欄位再判斷。",
    }
    return mapping.get(label, copy)


def _display_judgment_label(label: str) -> str:
    mapping = {
        "Change Recommended": "建議調整",
        "Keep Current Setup": "維持目前設定",
        "No Judgment Yet": "尚無判斷",
        "Awaiting Horizon End": "等待視窗結束",
        "Waiting For Data": "等待資料覆蓋",
        "Unscorable": "無法評分",
        "Awaiting Review": "等待檢討",
    }
    return mapping.get(label, label)


def _display_judgment_copy(snapshot: DashboardSnapshot, copy: str) -> str:
    if snapshot.latest_review is not None:
        return copy
    if snapshot.latest_forecast is None:
        return "目前還沒有可供判讀的預測產物，因此暫時沒有判斷結果。"
    if snapshot.latest_forecast.status == "pending":
        return "目前預測視窗仍在進行中，因此 replay 應視為輔助歷史，而不是最新判斷。"
    if snapshot.latest_forecast.status == "waiting_for_data":
        return "預測視窗已結束，但仍在等待 provider 補齊目標視窗資料。"
    if snapshot.latest_forecast.status == "unscorable":
        return "目標視窗資料不完整或無效，這筆預測不能作為正常評分依據。"
    return "最新預測已完成視窗，但檢討與提案產物尚未寫出。"


def _display_replay_freshness(label: str) -> str:
    if label == "No replay summary yet":
        return "目前還沒有 replay 摘要"
    if label == "Historical replay available":
        return "已有歷史 replay 可供參考"
    if label == "Replay aligns with the latest forecast window":
        return "replay 與最新預測視窗大致對齊"
    if label.startswith("Replay is historical (") and label.endswith(")"):
        detail = label.removeprefix("Replay is historical (").removesuffix(")")
        if detail.endswith("h behind latest forecast"):
            hours = detail.removesuffix("h behind latest forecast").strip()
            detail = f"落後最新預測 {hours} 小時"
        return f"replay 僅供歷史脈絡參考（{detail}）"
    return label


def _display_forecast_status(status: str) -> str:
    mapping = {
        "pending": "待完成（pending）",
        "resolved": "已完成（resolved）",
        "waiting_for_data": "等待資料覆蓋（waiting_for_data）",
        "unscorable": "無法評分（unscorable）",
        "failed": "失敗（failed）",
        "cancelled": "已取消（cancelled）",
    }
    return mapping.get(status, status)


def _display_status_reason(reason: str) -> str:
    mapping = {
        "awaiting_horizon_end": "等待視窗結束（awaiting_horizon_end）",
        "awaiting_provider_coverage": "等待 provider 補齊目標視窗（awaiting_provider_coverage）",
        "scored": "已評分（scored）",
        "score_already_recorded": "評分已存在（score_already_recorded）",
        "missing_expected_candles": "缺少必要 K 線（missing_expected_candles）",
        "empty_realized_window": "實際觀測視窗為空（empty_realized_window）",
        "insufficient_realized_candles": "實際 K 線不足（insufficient_realized_candles）",
        "legacy_unscorable": "舊版無法評分狀態（legacy_unscorable）",
        "legacy_status": "舊版狀態（legacy_status）",
    }
    return mapping.get(reason, reason)


def _dashboard_freshness_copy(snapshot: DashboardSnapshot) -> str:
    hourly_source = _format_optional_timestamp(snapshot.hourly_status_source_at)
    building_source = _format_optional_timestamp(snapshot.building_status_source_at)
    return (
        f"Dashboard 產生時間：{snapshot.dashboard_generated_at.isoformat()}；"
        f"Automation 狀態來源：hourly {hourly_source}，building {building_source}。"
    )


def _format_optional_timestamp(value: datetime | None) -> str:
    if value is None:
        return "未找到"
    return value.isoformat()


def _display_regime(regime: str | None) -> str:
    mapping = {
        "trend_up": "上行趨勢（trend_up）",
        "trend_down": "下行趨勢（trend_down）",
        "range": "區間盤整（range）",
    }
    if regime is None:
        return "無"
    return mapping.get(regime, regime)


def _display_boolean(value: bool) -> str:
    return "是" if value else "否"


def _format_window_label(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%m-%d %H:%M')} → {end.strftime('%m-%d %H:%M')}"


def _format_optional_ratio(value: float | None) -> str:
    if value is None:
        return "無"
    return f"{value:.2%}"


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "無"
    return f"{value:.4f}"


def _dashboard_artifact_id(item: object | None, field: str) -> str:
    if item is None:
        return "<span class=\"empty\">無</span>"
    return f"<code>{escape(str(getattr(item, field)))}</code>"


def _dashboard_list_inline(items: list[str]) -> str:
    if not items:
        return '<span class="empty">none</span>'
    return "；".join(f"<code>{escape(item)}</code>" for item in items)


def _dashboard_dict_inline(values: dict[str, object]) -> str:
    if not values:
        return '<span class="empty">none</span>'
    return "；".join(
        f"<code>{escape(str(key))}</code>={escape(_dashboard_value(value))}"
        for key, value in sorted(values.items(), key=lambda item: str(item[0]))
    )


def _dashboard_steps_inline(run: ResearchAutopilotRun | None) -> str:
    if run is None or not run.steps:
        return '<span class="empty">none</span>'
    return "；".join(
        f"{escape(step.get('name') or '')}:{escape(step.get('status') or '')} "
        f"<code>{escape(step.get('artifact_id') or 'none')}</code>"
        for step in run.steps
    )


def _dashboard_value(value: object) -> str:
    if isinstance(value, float):
        return _format_optional_number(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in sorted(value.items(), key=lambda item: str(item[0])))
    return str(value)


def _display_decision_surface(review: Review, proposal: Proposal | None) -> str:
    if review.proposal_recommended and proposal is not None:
        return "目前判讀偏向需要調整 paper-only 參數，請先讀提案摘要，再決定是否進入人工覆核。"
    if review.proposal_recommended:
        return "review 判定需要調整，但目前只看到檢討結果，尚未看到完整提案內容。"
    return "目前判讀偏向維持既有設定，除非後續新 evidence 推翻這次 review。"


def _summarize_proposal_surface(proposal: Proposal | None) -> str:
    if proposal is None:
        return "目前沒有額外 proposal，代表這輪 review 沒有提出新的調整單。"
    change_keys = ", ".join(sorted(proposal.changes))
    return f"提案類型為 {proposal.proposal_type}，目前涉及 {change_keys}。"


def _summarize_evidence(snapshot: DashboardSnapshot) -> str:
    latest_score = snapshot.latest_score
    if latest_score is None:
        return "這一區用來確認目前操作判讀背後的證據鏈是否完整。若最新 score 尚未產生，代表證據鏈仍在補齊中。"
    return (
        f"目前最新 score 為 {latest_score.score:.2f}，"
        f"對應 { _display_regime(latest_score.predicted_regime) } 與 { _display_regime(latest_score.actual_regime) }。"
        " 這些產物數量與最新 score 共同支撐上方的本輪判讀。"
    )
