from datetime import UTC, datetime, timedelta
import json

import pytest

from forecast_loop.cli import main
from forecast_loop.models import StrategyDecision
from forecast_loop.storage import JsonFileRepository


def _decision(
    *,
    decision_id: str,
    symbol: str = "BTC-USD",
    created_at: datetime,
    reason_summary: str,
    blocked_reason: str | None = "model_not_beating_baseline",
) -> StrategyDecision:
    return StrategyDecision(
        decision_id=decision_id,
        created_at=created_at,
        symbol=symbol,
        horizon_hours=24,
        action="HOLD",
        confidence=0.52,
        evidence_grade="D",
        risk_level="MEDIUM",
        tradeable=False,
        blocked_reason=blocked_reason,
        recommended_position_pct=0.0,
        current_position_pct=0.0,
        max_position_pct=0.15,
        invalidation_conditions=["補齊 research blockers 後重跑 decision。"],
        reason_summary=reason_summary,
        forecast_ids=["forecast:blocker"],
        score_ids=["score:blocker"],
        review_ids=["review:blocker"],
        baseline_ids=["baseline:blocker"],
        decision_basis="test",
    )


def test_create_decision_blocker_research_agenda_cli_persists_latest_blocker_agenda(
    tmp_path,
    capsys,
):
    repository = JsonFileRepository(tmp_path)
    now = datetime(2026, 5, 2, 8, 0, tzinfo=UTC)
    repository.save_strategy_decision(
        _decision(
            decision_id="decision:older",
            created_at=now - timedelta(hours=1),
            reason_summary="較舊 decision；主要研究阻擋：backtest 缺失。",
        )
    )
    repository.save_strategy_decision(
        _decision(
            decision_id="decision:eth",
            symbol="ETH-USD",
            created_at=now + timedelta(minutes=5),
            reason_summary="ETH decision；主要研究阻擋：ETH blocker。",
        )
    )
    latest = _decision(
        decision_id="decision:latest-blocker",
        created_at=now + timedelta(minutes=10),
        reason_summary=(
            "模型證據沒有打贏 naive persistence baseline，因此買進/賣出被擋住。 "
            "主要研究阻擋：event edge 缺失、walk-forward overfit risk。"
        ),
    )
    repository.save_strategy_decision(latest)

    assert (
        main(
            [
                "create-decision-blocker-research-agenda",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--created-at",
                "2026-05-02T09:00:00+00:00",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    agenda = payload["research_agenda"]

    assert payload["strategy_decision"]["decision_id"] == latest.decision_id
    assert agenda["symbol"] == "BTC-USD"
    assert agenda["decision_basis"] == "decision_blocker_research_agenda"
    assert agenda["priority"] == "HIGH"
    assert agenda["strategy_card_ids"] == []
    assert "decision:latest-blocker" in agenda["hypothesis"]
    assert "event edge 缺失" in agenda["hypothesis"]
    assert "walk-forward overfit risk" in agenda["hypothesis"]
    assert "event_edge_evaluation" in agenda["expected_artifacts"]
    assert "walk_forward_validation" in agenda["expected_artifacts"]
    assert "strategy_decision" in agenda["expected_artifacts"]
    assert "BUY/SELL gate must remain blocked until blockers improve" in agenda["acceptance_criteria"]
    assert "directional_buy_sell_without_research_evidence" in agenda["blocked_actions"]

    assert (
        main(
            [
                "create-decision-blocker-research-agenda",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
                "--created-at",
                "2026-05-02T10:00:00+00:00",
            ]
        )
        == 0
    )
    second_payload = json.loads(capsys.readouterr().out)
    assert second_payload["research_agenda"]["agenda_id"] == agenda["agenda_id"]
    agendas = [
        item
        for item in repository.load_research_agendas()
        if item.decision_basis == "decision_blocker_research_agenda"
    ]
    assert len(agendas) == 1
    assert agendas[0].agenda_id == agenda["agenda_id"]


def test_create_decision_blocker_research_agenda_rejects_missing_blocker_summary(
    tmp_path,
    capsys,
):
    repository = JsonFileRepository(tmp_path)
    repository.save_strategy_decision(
        _decision(
            decision_id="decision:no-blocker",
            created_at=datetime(2026, 5, 2, 8, 0, tzinfo=UTC),
            reason_summary="目前只是一般 HOLD，沒有明確 research blocker。",
            blocked_reason=None,
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "create-decision-blocker-research-agenda",
                "--storage-dir",
                str(tmp_path),
                "--symbol",
                "BTC-USD",
            ]
        )
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "latest decision has no research blocker summary" in captured.err
    assert "Traceback" not in captured.err
