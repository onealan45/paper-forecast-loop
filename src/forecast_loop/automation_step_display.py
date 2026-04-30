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


def display_required_artifacts(artifact_ids: list[str]) -> list[str]:
    return [display_step_artifact("next_task_required_artifact", artifact_id) for artifact_id in artifact_ids]


def _artifact_copy(artifact_id: str) -> str:
    labels = {
        "experiment_trial": "實驗 trial",
        "split_manifest": "切分清單",
        "cost_model_snapshot": "成本模型快照",
        "baseline_evaluation": "baseline 評估",
        "backtest_result": "回測結果",
        "walk_forward_validation": "walk-forward 驗證",
        "locked_evaluation_result": "鎖定評估結果",
        "leaderboard_entry": "leaderboard 條目",
        "research_agenda": "研究議程",
        "research_autopilot_run": "研究自動化執行紀錄",
        "strategy_card": "策略卡",
        "paper_shadow_outcome": "paper-shadow 結果",
    }
    return labels.get(artifact_id, artifact_id)


def _missing_input_copy(artifact_id: str) -> str:
    labels = {
        "dataset_id": "dataset id",
        "storage_dir": "storage 目錄",
        "train_start": "訓練開始",
        "train_end": "訓練結束",
        "validation_start": "驗證開始",
        "validation_end": "驗證結束",
        "holdout_start": "holdout 開始",
        "holdout_end": "holdout 結束",
        "split_manifest": "切分清單",
        "pending_retest_trial": "pending retest trial",
        "backtest_result": "回測結果",
        "linked_backtest_walk_forward_pair": "backtest / walk-forward 配對",
        "max_trials": "最大 trial 數",
        "passed_retest_trial": "通過 retest trial",
        "cost_model_snapshot": "成本模型快照",
        "baseline_evaluation": "baseline 評估",
        "leaderboard_entry": "leaderboard 條目",
        "window_start": "觀察視窗開始",
        "window_end": "觀察視窗結束",
        "observed_return": "觀察報酬",
        "benchmark_return": "benchmark 報酬",
        "locked_evaluation": "鎖定評估",
        "walk_forward_validation": "walk-forward 驗證",
        "paper_shadow_outcome": "paper-shadow outcome",
        "research_autopilot_run": "research autopilot run",
    }
    inputs = [item.strip() for item in artifact_id.split(",") if item.strip()]
    return ", ".join(labels.get(item, item) for item in inputs) or artifact_id
