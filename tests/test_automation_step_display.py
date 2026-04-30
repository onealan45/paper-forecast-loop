from forecast_loop.automation_step_display import (
    display_required_artifacts,
    display_step_artifact,
    display_step_name,
)


def test_display_step_name_translates_lineage_blocked_context():
    assert display_step_name("next_task_blocked_reason") == "下一個任務阻擋原因"
    assert display_step_name("next_task_missing_inputs") == "缺少證據輸入"
    assert display_step_name("next_task_required_artifact") == "下一個任務要求產物"
    assert display_step_name("revision_card") == "修正策略卡"
    assert display_step_name("source_outcome") == "來源 paper-shadow 結果"
    assert display_step_name("lock_evaluation_protocol") == "鎖定評估協議"
    assert display_step_name("unknown_step") == "unknown_step"


def test_display_step_artifact_adds_readable_copy_without_losing_codes():
    blocked = display_step_artifact("next_task_blocked_reason", "cross_sample_autopilot_run_missing")
    missing = display_step_artifact(
        "next_task_missing_inputs",
        "locked_evaluation, walk_forward_validation, paper_shadow_outcome, research_autopilot_run",
    )

    assert blocked == "缺少 cross-sample autopilot run (cross_sample_autopilot_run_missing)"
    assert missing == (
        "鎖定評估, walk-forward 驗證, paper-shadow outcome, research autopilot run "
        "(locked_evaluation, walk_forward_validation, paper_shadow_outcome, research_autopilot_run)"
    )
    assert display_step_artifact("next_task_required_artifact", "research_agenda") == (
        "研究議程 (research_agenda)"
    )
    assert display_step_artifact("next_task_required_artifact", "research_autopilot_run") == (
        "研究自動化執行紀錄 (research_autopilot_run)"
    )
    assert display_step_artifact("next_task_required_artifact", "strategy_card") == (
        "策略卡 (strategy_card)"
    )
    assert display_step_artifact("next_task_required_artifact", "paper_shadow_outcome") == (
        "paper-shadow 結果 (paper_shadow_outcome)"
    )
    assert display_step_artifact("next_task_required_artifact", "cost_model_snapshot") == (
        "成本模型快照 (cost_model_snapshot)"
    )
    assert display_step_artifact("next_task_required_artifact", "split_manifest") == (
        "切分清單 (split_manifest)"
    )
    assert display_step_artifact(
        "next_task_missing_inputs",
        "train_start, validation_end, storage_dir",
    ) == "訓練開始, 驗證結束, storage 目錄 (train_start, validation_end, storage_dir)"
    assert display_step_artifact("other_step", "artifact:test") == "artifact:test"
    assert display_step_artifact("other_step", None) == "none"


def test_display_required_artifacts_reuses_artifact_copy():
    assert display_required_artifacts(["baseline_evaluation", "backtest_result"]) == [
        "baseline 評估 (baseline_evaluation)",
        "回測結果 (backtest_result)",
    ]
