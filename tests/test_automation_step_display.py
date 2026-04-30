from forecast_loop.automation_step_display import display_step_artifact, display_step_name


def test_display_step_name_translates_lineage_blocked_context():
    assert display_step_name("next_task_blocked_reason") == "下一個任務阻擋原因"
    assert display_step_name("next_task_missing_inputs") == "缺少證據輸入"
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
    assert display_step_artifact("other_step", "artifact:test") == "artifact:test"
    assert display_step_artifact("other_step", None) == "none"
