from __future__ import annotations


def display_step_name(name: str) -> str:
    labels = {
        "next_task_blocked_reason": "下一個任務阻擋原因",
        "next_task_missing_inputs": "缺少證據輸入",
        "next_task_required_artifact": "下一個任務要求產物",
    }
    return labels.get(name, name)


def display_step_artifact(name: str, artifact_id: str | None) -> str:
    if artifact_id is None:
        return "none"
    if name == "next_task_blocked_reason" and artifact_id == "cross_sample_autopilot_run_missing":
        return f"缺少 cross-sample autopilot run ({artifact_id})"
    if name == "next_task_missing_inputs":
        return f"{_missing_input_copy(artifact_id)} ({artifact_id})"
    if name == "next_task_required_artifact":
        return f"{_artifact_copy(artifact_id)} ({artifact_id})"
    return artifact_id


def _artifact_copy(artifact_id: str) -> str:
    labels = {
        "research_agenda": "研究議程",
        "research_autopilot_run": "研究自動化執行紀錄",
        "strategy_card": "策略卡",
        "paper_shadow_outcome": "paper-shadow 結果",
    }
    return labels.get(artifact_id, artifact_id)


def _missing_input_copy(artifact_id: str) -> str:
    labels = {
        "locked_evaluation": "鎖定評估",
        "walk_forward_validation": "walk-forward 驗證",
        "paper_shadow_outcome": "paper-shadow outcome",
        "research_autopilot_run": "research autopilot run",
    }
    inputs = [item.strip() for item in artifact_id.split(",") if item.strip()]
    return ", ".join(labels.get(item, item) for item in inputs) or artifact_id
