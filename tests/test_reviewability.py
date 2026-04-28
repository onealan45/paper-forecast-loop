from pathlib import Path


MAX_REVIEWABLE_PYTHON_LINE_LENGTH = 1000


def _python_files_to_check() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    paths = [
        *sorted((repo_root / "src").rglob("*.py")),
        *sorted((repo_root / "tests").rglob("*.py")),
        repo_root / "run_forecast_loop.py",
        repo_root / "sitecustomize.py",
    ]
    return [path for path in paths if path.exists()]


def test_python_source_files_do_not_have_pathological_long_lines():
    violations: list[str] = []
    for path in _python_files_to_check():
        relative_path = path.relative_to(Path(__file__).resolve().parents[1])
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line_length = len(line)
            if line_length > MAX_REVIEWABLE_PYTHON_LINE_LENGTH:
                violations.append(
                    f"{relative_path}:{line_number} has {line_length} characters "
                    f"(max {MAX_REVIEWABLE_PYTHON_LINE_LENGTH})"
                )

    assert violations == []
