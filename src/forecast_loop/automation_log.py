from __future__ import annotations

from datetime import datetime

from forecast_loop.models import AutomationRun, HealthCheckResult, StrategyDecision


def automation_step(name: str, status: str, artifact_id: str | None = None) -> dict[str, str | None]:
    return {
        "name": name,
        "status": status,
        "artifact_id": artifact_id,
    }


def record_automation_run(
    *,
    repository,
    started_at: datetime,
    completed_at: datetime,
    status: str,
    symbol: str,
    provider: str,
    command: str,
    steps: list[dict[str, str | None]],
    health_result: HealthCheckResult | None = None,
    decision: StrategyDecision | None = None,
) -> AutomationRun:
    run = AutomationRun(
        automation_run_id=AutomationRun.build_id(
            started_at=started_at,
            completed_at=completed_at,
            symbol=symbol,
            provider=provider,
            command=command,
            status=status,
        ),
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        symbol=symbol,
        provider=provider,
        command=command,
        steps=steps,
        health_check_id=health_result.check_id if health_result else None,
        decision_id=decision.decision_id if decision else None,
        repair_request_id=health_result.repair_request_id if health_result else None,
        decision_basis="paper-only automation run log",
    )
    repository.save_automation_run(run)
    return run
