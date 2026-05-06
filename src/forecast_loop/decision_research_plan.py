from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from forecast_loop.decision_research_agenda import (
    DECISION_BLOCKER_AGENDA_BASIS,
    extract_decision_research_blockers,
)
from forecast_loop.models import (
    BacktestResult,
    BacktestRun,
    CanonicalEvent,
    EventEdgeEvaluation,
    MarketCandleRecord,
    MarketReactionCheck,
    ResearchAgenda,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.research_artifact_selection import (
    DECISION_BLOCKER_BACKTEST_ID_CONTEXT,
    DECISION_BLOCKER_WALK_FORWARD_ID_CONTEXT,
)
from forecast_loop.storage import ArtifactRepository


@dataclass(frozen=True, slots=True)
class DecisionBlockerResearchTask:
    task_id: str
    title: str
    status: str
    required_artifact: str
    artifact_id: str | None
    command_args: list[str] | None
    worker_prompt: str
    blocked_reason: str | None
    missing_inputs: list[str]
    rationale: str

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "status": self.status,
            "required_artifact": self.required_artifact,
            "artifact_id": self.artifact_id,
            "command_args": list(self.command_args) if self.command_args is not None else None,
            "worker_prompt": self.worker_prompt,
            "blocked_reason": self.blocked_reason,
            "missing_inputs": list(self.missing_inputs),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class DecisionBlockerResearchTaskPlan:
    symbol: str
    agenda_id: str
    decision_id: str | None
    blockers: list[str]
    next_task_id: str | None
    tasks: list[DecisionBlockerResearchTask]

    def task_by_id(self, task_id: str) -> DecisionBlockerResearchTask:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        raise KeyError(task_id)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "agenda_id": self.agenda_id,
            "decision_id": self.decision_id,
            "blockers": list(self.blockers),
            "next_task_id": self.next_task_id,
            "tasks": [task.to_dict() for task in self.tasks],
        }


@dataclass(frozen=True, slots=True)
class _EventEdgeInputManifest:
    event_ids: list[str]
    reaction_check_ids: list[str]
    candle_ids: list[str]
    input_watermark: datetime


def build_decision_blocker_research_task_plan(
    *,
    repository: ArtifactRepository,
    storage_dir: Path | str | None,
    symbol: str,
    now: datetime,
) -> DecisionBlockerResearchTaskPlan:
    symbol = symbol.upper()
    storage = Path(storage_dir) if storage_dir is not None else None
    agenda = _latest_decision_blocker_agenda(repository.load_research_agendas(), symbol)
    if agenda is None:
        raise ValueError(f"decision blocker research agenda not found for symbol: {symbol}")
    latest_decision = _latest_decision(repository.load_strategy_decisions(), symbol)
    blockers = extract_decision_research_blockers(latest_decision) if latest_decision else []
    if not blockers:
        blockers = _blockers_from_agenda(agenda)
    tasks = [_agenda_task(agenda, latest_decision, blockers)]
    tasks.extend(
        _evidence_tasks(
            agenda,
            storage,
            symbol,
            now,
            blockers,
            repository.load_event_edge_evaluations(),
            repository.load_canonical_events(),
            repository.load_market_reaction_checks(),
            repository.load_market_candles(),
            repository.load_backtest_runs(),
            repository.load_backtest_results(),
            repository.load_walk_forward_validations(),
        )
    )
    next_task = next((task for task in tasks if task.status != "completed"), None)
    return DecisionBlockerResearchTaskPlan(
        symbol=symbol,
        agenda_id=agenda.agenda_id,
        decision_id=latest_decision.decision_id if latest_decision else _decision_id_from_text(agenda.hypothesis),
        blockers=blockers,
        next_task_id=next_task.task_id if next_task else None,
        tasks=tasks,
    )


def _latest_decision_blocker_agenda(
    agendas: list[ResearchAgenda],
    symbol: str,
) -> ResearchAgenda | None:
    candidates = [
        agenda
        for agenda in agendas
        if agenda.symbol == symbol and agenda.decision_basis == DECISION_BLOCKER_AGENDA_BASIS
    ]
    return max(candidates, key=lambda item: (item.created_at, item.agenda_id)) if candidates else None


def _latest_decision(
    decisions: list[StrategyDecision],
    symbol: str,
) -> StrategyDecision | None:
    matches = [decision for decision in decisions if decision.symbol == symbol]
    return max(matches, key=lambda decision: (decision.created_at, decision.decision_id)) if matches else None


def _agenda_task(
    agenda: ResearchAgenda,
    decision: StrategyDecision | None,
    blockers: list[str],
) -> DecisionBlockerResearchTask:
    decision_id = decision.decision_id if decision else _decision_id_from_text(agenda.hypothesis) or "unknown"
    return DecisionBlockerResearchTask(
        task_id="resolve_decision_blocker_research_agenda",
        title="Resolve decision blocker research agenda",
        status="completed",
        required_artifact="research_agenda",
        artifact_id=agenda.agenda_id,
        command_args=None,
        worker_prompt=(
            f"Use agenda {agenda.agenda_id} for decision {decision_id}. "
            f"Research blockers: {', '.join(blockers) if blockers else 'unknown'}."
        ),
        blocked_reason=None,
        missing_inputs=[],
        rationale="A decision-blocker agenda already exists and anchors this task plan.",
    )


def _evidence_tasks(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    event_edges: list[EventEdgeEvaluation],
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
    backtest_runs: list[BacktestRun],
    backtests: list[BacktestResult],
    walk_forwards: list[WalkForwardValidation],
) -> list[DecisionBlockerResearchTask]:
    tasks: list[DecisionBlockerResearchTask] = []
    expected = set(agenda.expected_artifacts)
    if "event_edge_evaluation" in expected:
        tasks.append(_event_edge_task(agenda, storage, symbol, now, blockers, event_edges, events, reactions, candles))
    if "backtest_result" in expected:
        tasks.append(_backtest_task(agenda, storage, symbol, now, blockers, candles, backtest_runs, backtests))
    if "walk_forward_validation" in expected:
        tasks.append(_walk_forward_task(agenda, storage, symbol, now, blockers, candles, walk_forwards))
    if "baseline_evaluation" in expected:
        tasks.append(_baseline_task(blockers))
    return tasks


def _event_edge_task(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    event_edges: list[EventEdgeEvaluation],
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
) -> DecisionBlockerResearchTask:
    latest_edge = _latest_current_event_edge(
        event_edges=event_edges,
        agenda=agenda,
        now=now,
        events=events,
        reactions=reactions,
        candles=candles,
    )
    if latest_edge is not None:
        return DecisionBlockerResearchTask(
            task_id="build_event_edge_evaluation",
            title="Build event-edge evaluation for decision blocker",
            status="completed",
            required_artifact="event_edge_evaluation",
            artifact_id=latest_edge.evaluation_id,
            command_args=None,
            worker_prompt=_worker_prompt("event-edge evaluation", blockers),
            blocked_reason=None,
            missing_inputs=[],
            rationale="A same-symbol event-edge evaluation already covers the current blocker input set.",
        )
    missing = _missing_event_edge_inputs(
        symbol=symbol,
        now=now,
        events=events,
        reactions=reactions,
        candles=candles,
    )
    if missing:
        return DecisionBlockerResearchTask(
            task_id="build_event_edge_evaluation",
            title="Build event-edge evaluation for decision blocker",
            status="blocked",
            required_artifact="event_edge_evaluation",
            artifact_id=None,
            command_args=None,
            worker_prompt=_worker_prompt("event-edge evaluation", blockers),
            blocked_reason="missing_event_edge_inputs",
            missing_inputs=missing,
            rationale="Event-edge evaluation needs historical events, market reactions, and candles before execution.",
        )
    missing = [] if storage is not None else ["storage_dir"]
    command = None
    if storage is not None:
        command = _base_command() + [
            "build-event-edge",
            "--storage-dir",
            str(storage),
            "--symbol",
            symbol,
            "--created-at",
            now.isoformat(),
        ]
    return DecisionBlockerResearchTask(
        task_id="build_event_edge_evaluation",
        title="Build event-edge evaluation for decision blocker",
        status="ready" if not missing else "blocked",
        required_artifact="event_edge_evaluation",
        artifact_id=None,
        command_args=command,
        worker_prompt=_worker_prompt("event-edge evaluation", blockers),
        blocked_reason="missing_storage_dir" if missing else None,
        missing_inputs=missing,
        rationale="The latest decision is blocked by event-edge evidence, so event edge should be rebuilt first.",
    )


def _backtest_task(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    candles: list[MarketCandleRecord],
    backtest_runs: list[BacktestRun],
    backtests: list[BacktestResult],
) -> DecisionBlockerResearchTask:
    if storage is None:
        return _window_blocked_task(
            task_id="run_backtest",
            title="Run blocker-focused backtest",
            required_artifact="backtest_result",
            blocked_reason="missing_storage_dir",
            worker_prompt=_worker_prompt("backtest", blockers),
            rationale="Backtest evidence needs a storage directory before a command can be emitted.",
            missing_inputs=["storage_dir"],
        )
    window_candles = _candle_window_records(candles, symbol=symbol, now=now, min_count=10)
    if window_candles is None:
        return _window_blocked_task(
            task_id="run_backtest",
            title="Run blocker-focused backtest",
            required_artifact="backtest_result",
            blocked_reason="missing_backtest_window",
            worker_prompt=_worker_prompt("backtest", blockers),
            rationale="Backtest evidence needs at least 10 same-symbol candles imported by plan time.",
            missing_inputs=["market_candles"],
        )
    start, end = window_candles[0].timestamp, window_candles[-1].timestamp
    current_backtest = _latest_backtest_for_current_window(
        backtests=backtests,
        backtest_runs=backtest_runs,
        symbol=symbol,
        start=start,
        end=end,
        candle_ids=[candle.candle_id for candle in window_candles],
        input_watermark=_candle_input_watermark(window_candles),
        now=now,
    )
    if current_backtest is not None:
        return DecisionBlockerResearchTask(
            task_id="run_backtest",
            title="Run blocker-focused backtest",
            status="completed",
            required_artifact="backtest_result",
            artifact_id=current_backtest.result_id,
            command_args=None,
            worker_prompt=_worker_prompt("backtest", blockers),
            blocked_reason=None,
            missing_inputs=[],
            rationale="A blocker-focused backtest already covers the unchanged current candle window.",
        )
    command = _base_command() + [
        "backtest",
        "--storage-dir",
        str(storage),
        "--symbol",
        symbol,
        "--start",
        start.isoformat(),
        "--end",
        end.isoformat(),
        "--created-at",
        now.isoformat(),
        "--as-of",
        now.isoformat(),
    ]
    return DecisionBlockerResearchTask(
        task_id="run_backtest",
        title="Run blocker-focused backtest",
        status="ready",
        required_artifact="backtest_result",
        artifact_id=None,
        command_args=command,
        worker_prompt=_worker_prompt("backtest", blockers),
        blocked_reason=None,
        missing_inputs=[],
        rationale="Stored candles cover a conservative backtest window and the command pins the plan-time as-of set.",
    )


def _walk_forward_task(
    agenda: ResearchAgenda,
    storage: Path | None,
    symbol: str,
    now: datetime,
    blockers: list[str],
    candles: list[MarketCandleRecord],
    walk_forwards: list[WalkForwardValidation],
) -> DecisionBlockerResearchTask:
    if storage is None:
        return _window_blocked_task(
            task_id="run_walk_forward_validation",
            title="Run blocker-focused walk-forward validation",
            required_artifact="walk_forward_validation",
            blocked_reason="missing_storage_dir",
            worker_prompt=_worker_prompt("walk-forward validation", blockers),
            rationale="Walk-forward validation needs a storage directory before a command can be emitted.",
            missing_inputs=["storage_dir"],
        )
    window_candles = _candle_window_records(candles, symbol=symbol, now=now, min_count=10)
    if window_candles is None:
        return _window_blocked_task(
            task_id="run_walk_forward_validation",
            title="Run blocker-focused walk-forward validation",
            required_artifact="walk_forward_validation",
            blocked_reason="missing_walk_forward_window",
            worker_prompt=_worker_prompt("walk-forward validation", blockers),
            rationale="Walk-forward validation needs at least 10 same-symbol candles imported by plan time.",
            missing_inputs=["market_candles"],
        )
    start, end = window_candles[0].timestamp, window_candles[-1].timestamp
    current_walk_forward = _latest_walk_forward_for_current_window(
        walk_forwards=walk_forwards,
        symbol=symbol,
        start=start,
        end=end,
        input_watermark=_candle_input_watermark(window_candles),
        now=now,
    )
    if current_walk_forward is not None:
        return DecisionBlockerResearchTask(
            task_id="run_walk_forward_validation",
            title="Run blocker-focused walk-forward validation",
            status="completed",
            required_artifact="walk_forward_validation",
            artifact_id=current_walk_forward.validation_id,
            command_args=None,
            worker_prompt=_worker_prompt("walk-forward validation", blockers),
            blocked_reason=None,
            missing_inputs=[],
            rationale="A blocker-focused walk-forward validation already covers the unchanged current candle window.",
        )
    command = _base_command() + [
        "walk-forward",
        "--storage-dir",
        str(storage),
        "--symbol",
        symbol,
        "--start",
        start.isoformat(),
        "--end",
        end.isoformat(),
        "--created-at",
        now.isoformat(),
        "--as-of",
        now.isoformat(),
        "--train-size",
        "4",
        "--validation-size",
        "3",
        "--test-size",
        "3",
        "--step-size",
        "1",
    ]
    return DecisionBlockerResearchTask(
        task_id="run_walk_forward_validation",
        title="Run blocker-focused walk-forward validation",
        status="ready",
        required_artifact="walk_forward_validation",
        artifact_id=None,
        command_args=command,
        worker_prompt=_worker_prompt("walk-forward validation", blockers),
        blocked_reason=None,
        missing_inputs=[],
        rationale="Stored candles cover a conservative walk-forward window for the blocker evidence task.",
    )


def _baseline_task(blockers: list[str]) -> DecisionBlockerResearchTask:
    return DecisionBlockerResearchTask(
        task_id="refresh_baseline_evaluation",
        title="Refresh baseline comparison evidence",
        status="blocked",
        required_artifact="baseline_evaluation",
        artifact_id=None,
        command_args=None,
        worker_prompt=_worker_prompt("baseline evaluation", blockers),
        blocked_reason="baseline_refresh_command_not_available",
        missing_inputs=["baseline_refresh_command"],
        rationale="Baseline blocker is explicit, but this repo does not yet expose a standalone baseline refresh command.",
    )


def _window_blocked_task(
    *,
    task_id: str,
    title: str,
    required_artifact: str,
    blocked_reason: str,
    worker_prompt: str,
    rationale: str,
    missing_inputs: list[str] | None = None,
) -> DecisionBlockerResearchTask:
    return DecisionBlockerResearchTask(
        task_id=task_id,
        title=title,
        status="blocked",
        required_artifact=required_artifact,
        artifact_id=None,
        command_args=None,
        worker_prompt=worker_prompt,
        blocked_reason=blocked_reason,
        missing_inputs=missing_inputs or ["start", "end"],
        rationale=rationale,
    )


def _blockers_from_agenda(agenda: ResearchAgenda) -> list[str]:
    if " because " not in agenda.hypothesis:
        return []
    blocker_text = agenda.hypothesis.split(" because ", 1)[1].split(". Research", 1)[0]
    return [item.strip().rstrip(".") for item in blocker_text.split(",") if item.strip()]


def _latest_event_edge_after_agenda(
    event_edges: list[EventEdgeEvaluation],
    agenda: ResearchAgenda,
) -> EventEdgeEvaluation | None:
    candidates = [
        evaluation
        for evaluation in event_edges
        if evaluation.symbol == agenda.symbol and evaluation.created_at >= agenda.created_at
    ]
    return max(candidates, key=lambda item: (item.created_at, item.evaluation_id)) if candidates else None


def _latest_current_event_edge(
    *,
    event_edges: list[EventEdgeEvaluation],
    agenda: ResearchAgenda,
    now: datetime,
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
) -> EventEdgeEvaluation | None:
    input_watermark = _event_edge_input_watermark(
        symbol=agenda.symbol,
        now=now,
        events=events,
        reactions=reactions,
        candles=candles,
    )
    if input_watermark is None:
        return None
    candidates: list[EventEdgeEvaluation] = []
    for evaluation in event_edges:
        if evaluation.symbol != agenda.symbol or evaluation.created_at > now:
            continue
        if _has_event_edge_input_manifest(evaluation):
            current_manifest = _event_edge_input_manifest_for_evaluation(
                evaluation=evaluation,
                now=now,
                events=events,
                reactions=reactions,
                candles=candles,
            )
            if current_manifest is None:
                continue
            if not _event_edge_manifest_matches(evaluation, current_manifest):
                continue
            if evaluation.input_watermark is None or evaluation.input_watermark < current_manifest.input_watermark:
                continue
            if evaluation.created_at < current_manifest.input_watermark:
                continue
            candidates.append(evaluation)
            continue
        if evaluation.created_at >= input_watermark:
            candidates.append(evaluation)
    return max(candidates, key=lambda item: (item.created_at, item.evaluation_id)) if candidates else None


def _has_event_edge_input_manifest(evaluation: EventEdgeEvaluation) -> bool:
    return bool(evaluation.input_event_ids or evaluation.input_reaction_check_ids or evaluation.input_candle_ids)


def _event_edge_manifest_matches(
    evaluation: EventEdgeEvaluation,
    manifest: _EventEdgeInputManifest,
) -> bool:
    return (
        sorted(evaluation.input_event_ids) == manifest.event_ids
        and sorted(evaluation.input_reaction_check_ids) == manifest.reaction_check_ids
        and sorted(evaluation.input_candle_ids) == manifest.candle_ids
    )


def _event_edge_input_manifest_for_evaluation(
    *,
    evaluation: EventEdgeEvaluation,
    now: datetime,
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
) -> _EventEdgeInputManifest | None:
    usable_events = {
        event.event_id: event
        for event in events
        if _event_edge_event_available(event, symbol=evaluation.symbol, now=now)
        and event.event_family == evaluation.event_family
        and event.event_type == evaluation.event_type
    }
    if not usable_events:
        return None
    latest_reactions = _latest_event_edge_reactions_by_event(reactions, now=now)
    candles_by_symbol = _event_edge_candles_by_symbol(candles, now=now)
    symbol_candles = candles_by_symbol.get(evaluation.symbol, [])
    event_ids: list[str] = []
    reaction_check_ids: list[str] = []
    candle_ids: list[str] = []
    watermarks: list[datetime] = []
    for event_id, event in sorted(usable_events.items()):
        reaction = latest_reactions.get(event_id)
        if reaction is None or not reaction.passed:
            continue
        sample_candle_ids = _event_edge_sample_candle_ids(
            event=event,
            reaction=reaction,
            candles=symbol_candles,
            horizon_hours=evaluation.horizon_hours,
        )
        if sample_candle_ids is None:
            continue
        event_ids.append(event.event_id)
        reaction_check_ids.append(reaction.check_id)
        candle_ids.extend(sample_candle_ids)
        event_values = [event.available_at, event.fetched_at]
        if event.created_at is not None:
            event_values.append(event.created_at)
        watermarks.append(max(value for value in event_values if value is not None))
        watermarks.append(reaction.created_at)
        for candle in symbol_candles:
            if candle.candle_id in sample_candle_ids:
                watermarks.append(max(candle.timestamp, candle.imported_at))
    if not event_ids or not watermarks:
        return None
    return _EventEdgeInputManifest(
        event_ids=sorted(set(event_ids)),
        reaction_check_ids=sorted(set(reaction_check_ids)),
        candle_ids=sorted(set(candle_ids)),
        input_watermark=max(watermarks),
    )


def _latest_backtest_for_current_window(
    *,
    backtests: list[BacktestResult],
    backtest_runs: list[BacktestRun],
    symbol: str,
    start: datetime,
    end: datetime,
    candle_ids: list[str],
    input_watermark: datetime,
    now: datetime,
) -> BacktestResult | None:
    run_by_id = {run.backtest_id: run for run in backtest_runs}
    current_candle_ids = sorted(candle_ids)
    candidates: list[BacktestResult] = []
    for result in backtests:
        run = run_by_id.get(result.backtest_id)
        if run is None:
            continue
        if result.symbol != symbol or run.symbol != symbol:
            continue
        if result.start != start or result.end != end or run.start != start or run.end != end:
            continue
        if sorted(run.candle_ids) != current_candle_ids:
            continue
        if DECISION_BLOCKER_BACKTEST_ID_CONTEXT not in run.decision_basis:
            continue
        if run.created_at > now or result.created_at > now:
            continue
        if result.created_at < run.created_at:
            continue
        if run.created_at < input_watermark or result.created_at < input_watermark:
            continue
        candidates.append(result)
    return max(candidates, key=lambda item: (item.created_at, item.result_id)) if candidates else None


def _latest_walk_forward_for_current_window(
    *,
    walk_forwards: list[WalkForwardValidation],
    symbol: str,
    start: datetime,
    end: datetime,
    input_watermark: datetime,
    now: datetime,
) -> WalkForwardValidation | None:
    candidates = [
        validation
        for validation in walk_forwards
        if validation.symbol == symbol
        and validation.start == start
        and validation.end == end
        and validation.created_at >= input_watermark
        and validation.created_at <= now
        and DECISION_BLOCKER_WALK_FORWARD_ID_CONTEXT in validation.decision_basis
    ]
    return max(candidates, key=lambda item: (item.created_at, item.validation_id)) if candidates else None


def _candle_window(
    candles: list[MarketCandleRecord],
    *,
    symbol: str,
    now: datetime,
    min_count: int,
) -> tuple[datetime, datetime] | None:
    records = _candle_window_records(candles, symbol=symbol, now=now, min_count=min_count)
    if records is None:
        return None
    return records[0].timestamp, records[-1].timestamp


def _candle_window_records(
    candles: list[MarketCandleRecord],
    *,
    symbol: str,
    now: datetime,
    min_count: int,
) -> list[MarketCandleRecord] | None:
    by_time: dict[datetime, MarketCandleRecord] = {}
    for candle in candles:
        if candle.symbol != symbol:
            continue
        if candle.timestamp > now or candle.imported_at > now:
            continue
        existing = by_time.get(candle.timestamp)
        if existing is None or (candle.imported_at, candle.source, candle.candle_id) > (
            existing.imported_at,
            existing.source,
            existing.candle_id,
        ):
            by_time[candle.timestamp] = candle
    timestamps = sorted(by_time)
    if len(timestamps) < min_count:
        return None
    return [by_time[timestamp] for timestamp in timestamps]


def _candle_input_watermark(candles: list[MarketCandleRecord]) -> datetime:
    return max(max(candle.timestamp, candle.imported_at) for candle in candles)


def _event_edge_input_watermark(
    *,
    symbol: str,
    now: datetime,
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
) -> datetime | None:
    watermarks: list[datetime] = []
    for event in events:
        if _event_edge_event_available(event, symbol=symbol, now=now):
            event_values = [event.available_at, event.fetched_at]
            if event.created_at is not None:
                event_values.append(event.created_at)
            watermarks.append(max(value for value in event_values if value is not None))
    for reaction in reactions:
        if reaction.symbol == symbol and reaction.created_at <= now:
            watermarks.append(reaction.created_at)
    for candle in candles:
        if candle.symbol == symbol and candle.timestamp <= now and candle.imported_at <= now:
            watermarks.append(max(candle.timestamp, candle.imported_at))
    return max(watermarks) if watermarks else None


def _missing_event_edge_inputs(
    *,
    symbol: str,
    now: datetime,
    events: list[CanonicalEvent],
    reactions: list[MarketReactionCheck],
    candles: list[MarketCandleRecord],
) -> list[str]:
    missing: list[str] = []
    usable_events = {
        event.event_id: event
        for event in events
        if _event_edge_event_available(event, symbol=symbol, now=now)
    }
    if not usable_events:
        missing.append("canonical_events")
    latest_reactions = _latest_event_edge_reactions_by_event(reactions, now=now)
    usable_reactions = {
        event_id: reaction
        for event_id, reaction in latest_reactions.items()
        if reaction.passed and event_id in usable_events
    }
    if not usable_reactions:
        missing.append("market_reaction_checks")
    candles_by_symbol = _event_edge_candles_by_symbol(candles, now=now)
    symbol_candles = candles_by_symbol.get(symbol, [])
    if usable_reactions:
        sample_exists = any(
            _has_event_edge_sample(
                event=usable_events[event_id],
                reaction=reaction,
                candles=symbol_candles,
            )
            for event_id, reaction in usable_reactions.items()
        )
    else:
        sample_exists = bool(symbol_candles)
    if not sample_exists:
        missing.append("market_candles")
    return missing


def _event_edge_event_available(event: CanonicalEvent, *, symbol: str, now: datetime) -> bool:
    return (
        event.symbol == symbol
        and event.available_at is not None
        and event.available_at <= now
        and event.fetched_at <= now
        and (event.created_at is None or event.created_at <= now)
    )


def _latest_event_edge_reactions_by_event(
    reactions: list[MarketReactionCheck],
    *,
    now: datetime,
) -> dict[str, MarketReactionCheck]:
    latest: dict[str, MarketReactionCheck] = {}
    for reaction in sorted(reactions, key=lambda item: (item.created_at, item.check_id)):
        if reaction.created_at > now:
            continue
        latest[reaction.event_id] = reaction
    return latest


def _event_edge_candles_by_symbol(
    candles: list[MarketCandleRecord],
    *,
    now: datetime,
) -> dict[str, list[MarketCandleRecord]]:
    by_symbol_and_time: dict[tuple[str, datetime], MarketCandleRecord] = {}
    for candle in candles:
        if candle.timestamp > now or candle.imported_at > now:
            continue
        key = (candle.symbol, candle.timestamp)
        existing = by_symbol_and_time.get(key)
        if existing is None or (candle.imported_at, candle.source, candle.candle_id) > (
            existing.imported_at,
            existing.source,
            existing.candle_id,
        ):
            by_symbol_and_time[key] = candle
    result: dict[str, list[MarketCandleRecord]] = {}
    for candle in by_symbol_and_time.values():
        result.setdefault(candle.symbol, []).append(candle)
    for symbol_candles in result.values():
        symbol_candles.sort(key=lambda item: item.timestamp)
    return result


def _has_event_edge_sample(
    *,
    event: CanonicalEvent,
    reaction: MarketReactionCheck,
    candles: list[MarketCandleRecord],
) -> bool:
    if reaction.symbol != event.symbol:
        return False
    if reaction.event_timestamp_used != _hour_boundary(reaction.event_timestamp_used):
        return False
    start = reaction.event_timestamp_used
    end = start + timedelta(hours=24)
    start_candle = _candle_at(candles, start)
    end_candle = _candle_at(candles, end)
    return start_candle is not None and end_candle is not None and start_candle.close != 0


def _event_edge_sample_candle_ids(
    *,
    event: CanonicalEvent,
    reaction: MarketReactionCheck,
    candles: list[MarketCandleRecord],
    horizon_hours: int,
) -> list[str] | None:
    if reaction.symbol != event.symbol:
        return None
    if reaction.event_timestamp_used != _hour_boundary(reaction.event_timestamp_used):
        return None
    start = reaction.event_timestamp_used
    end = start + timedelta(hours=horizon_hours)
    start_candle = _candle_at(candles, start)
    end_candle = _candle_at(candles, end)
    if start_candle is None or end_candle is None or start_candle.close == 0:
        return None
    return sorted(candle.candle_id for candle in candles if start <= candle.timestamp <= end)


def _hour_boundary(timestamp: datetime) -> datetime:
    return timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _candle_at(candles: list[MarketCandleRecord], timestamp: datetime) -> MarketCandleRecord | None:
    for candle in candles:
        if candle.timestamp == timestamp:
            return candle
    return None


def _decision_id_from_text(value: str) -> str | None:
    for token in value.split():
        if token.startswith("decision:"):
            return token.rstrip(".,;")
    return None


def _worker_prompt(evidence_name: str, blockers: list[str]) -> str:
    return (
        f"Build {evidence_name} for the latest decision blockers: "
        f"{', '.join(blockers) if blockers else 'unknown'}."
    )


def _base_command() -> list[str]:
    return ["python", "run_forecast_loop.py"]
