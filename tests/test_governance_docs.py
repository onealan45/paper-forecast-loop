from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]

PR11_DOCS = [
    REPO_ROOT / "docs" / "architecture" / "PR11-codex-governance-docs-prompts.md",
    REPO_ROOT / "docs" / "controller" / "controller-governance.md",
    REPO_ROOT / "docs" / "runbooks" / "windows-autopilot-controller.md",
    REPO_ROOT / "docs" / "prompts" / "controller-decision-template.md",
    REPO_ROOT / "docs" / "prompts" / "worker-handoff-template.md",
    REPO_ROOT / "docs" / "prompts" / "final-reviewer-prompt.md",
]

MACHINE_GATES = [
    "python -m pytest -q",
    "python -m compileall -q src tests run_forecast_loop.py sitecustomize.py",
    r"python .\run_forecast_loop.py --help",
    "git diff --check",
]

RUNTIME_EXCLUSIONS = [".codex/", "paper_storage/", "reports/", "output/", ".env", "secrets"]


def test_pr11_governance_docs_exist_and_contain_required_contracts():
    missing = [str(path.relative_to(REPO_ROOT)) for path in PR11_DOCS if not path.exists()]
    assert missing == []

    combined = "\n".join(path.read_text(encoding="utf-8") for path in PR11_DOCS)
    required_phrases = [
        "ChatGPT Pro Controller",
        "controller_decision_id",
        *MACHINE_GATES,
        "docs/reviews/",
        *RUNTIME_EXCLUSIONS,
        "Edge",
        "reviewer subagent",
        "APPROVED",
    ]
    missing_phrases = [phrase for phrase in required_phrases if phrase not in combined]
    assert missing_phrases == []


def test_critical_governance_docs_each_preserve_gates_and_exclusions():
    critical_docs = [
        REPO_ROOT / "docs" / "architecture" / "PR11-codex-governance-docs-prompts.md",
        REPO_ROOT / "docs" / "controller" / "controller-governance.md",
        REPO_ROOT / "docs" / "runbooks" / "windows-autopilot-controller.md",
        REPO_ROOT / "docs" / "prompts" / "controller-decision-template.md",
        REPO_ROOT / "docs" / "prompts" / "final-reviewer-prompt.md",
    ]
    required_phrases = [
        *MACHINE_GATES,
        "docs/reviews/",
        *RUNTIME_EXCLUSIONS,
        "reviewer subagent",
        "APPROVED",
    ]

    violations: list[str] = []
    for path in critical_docs:
        text = path.read_text(encoding="utf-8")
        for phrase in required_phrases:
            if phrase not in text:
                violations.append(f"{path.relative_to(REPO_ROOT)} missing {phrase}")

    assert violations == []


def test_browser_rule_is_explicit_in_human_facing_governance_docs():
    docs_requiring_browser_rule = [
        REPO_ROOT / "docs" / "architecture" / "PR11-codex-governance-docs-prompts.md",
        REPO_ROOT / "docs" / "runbooks" / "windows-autopilot-controller.md",
        REPO_ROOT / "docs" / "prompts" / "final-reviewer-prompt.md",
    ]
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in docs_requiring_browser_rule
        if "Edge" not in path.read_text(encoding="utf-8")
    ]

    assert missing == []


def test_agents_role_catalog_points_to_existing_role_docs():
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    role_paths = sorted(set(re.findall(r"docs/roles/[a-z-]+\.md", agents)))
    assert role_paths

    missing = [role_path for role_path in role_paths if not (REPO_ROOT / role_path).exists()]
    assert missing == []


def test_pr11_governance_docs_do_not_keep_placeholders():
    placeholder_patterns = ["TBD", "TODO", "<placeholder>", "<storageDir>", "fill in"]
    violations: list[str] = []
    for path in PR11_DOCS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in placeholder_patterns:
            if pattern in text:
                violations.append(f"{path.relative_to(REPO_ROOT)} contains {pattern}")

    assert violations == []
