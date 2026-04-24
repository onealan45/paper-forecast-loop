# Operator Dashboard Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current static inspector into an operator-readable, read-only dashboard that answers “what mode is the system in, what is the latest forecast, how fresh is replay context, and what should I trust first” without forcing the user to parse raw metadata.

**Architecture:** Keep the current `render-dashboard` command and static HTML output. Improve the `DashboardSnapshot` model to compute operator-facing status and readability helpers, then restructure `render_dashboard_html()` so the first screen prioritizes mode, latest forecast, and replay freshness while demoting raw metadata into collapsed debug details. Preserve the paper-only contract and avoid adding a server or interactive controls.

**Tech Stack:** Python 3.13, stdlib (`dataclasses`, `datetime`, `html`, `json`, `pathlib`, `tomllib`), existing `forecast_loop.dashboard` and `forecast_loop.cli`, pytest

---

## File Structure

- Modify: `src/forecast_loop/dashboard.py`
  - Rework the snapshot helpers and the HTML hierarchy for operator readability.
- Modify: `src/forecast_loop/cli.py`
  - Keep the existing `render-dashboard` entrypoint but update any metadata it exposes if needed by the redesigned dashboard.
- Modify: `tests/test_dashboard.py`
  - Add operator-facing regression tests for layout semantics, freshness framing, and metadata de-emphasis.
- Modify: `README.md`
  - Update the “Read-Only Inspector” section so it describes the operator-first reading order and limits.

### Task 1: Make The First Screen Answer the Operator’s Core Questions

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing operator-summary tests**

```python
def test_render_dashboard_promotes_operator_summary_over_internal_counts(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert "Loop Status" in html
    assert "What You Should Know Now" in html
    assert "Forecasts" not in html.split("What You Should Know Now", 1)[0]


def test_render_dashboard_labels_replay_as_historical_context(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    repository = JsonFileRepository(tmp_path)
    forecast = Forecast(
        forecast_id="forecast:live",
        symbol="BTC-USD",
        created_at=datetime(2026, 4, 23, 13, 23, tzinfo=UTC),
        anchor_time=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_start=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        target_window_end=datetime(2026, 4, 24, 13, 0, tzinfo=UTC),
        candle_interval_minutes=60,
        expected_candle_count=25,
        status="pending",
        status_reason="awaiting_horizon_end",
        predicted_regime="trend_down",
        confidence=0.55,
        provider_data_through=datetime(2026, 4, 23, 13, 0, tzinfo=UTC),
        observed_candle_count=8,
    )
    replay_summary = build_evaluation_summary(
        replay_id="replay:old",
        generated_at=datetime(2026, 4, 22, 18, 40, tzinfo=UTC),
        forecasts=[],
        scores=[],
        reviews=[],
        proposals=[],
    )
    repository.save_forecast(forecast)
    repository.save_evaluation_summary(replay_summary)

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert "Historical Replay Context" in html
    assert "Generated At" in html
    assert "historical" in html.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_promotes_operator_summary_over_internal_counts tests/test_dashboard.py::test_render_dashboard_labels_replay_as_historical_context -q`
Expected: FAIL because the current hero is still count-led and the replay panel title is still too internal

- [ ] **Step 3: Write minimal implementation**

```python
def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>...</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <div class="shell">
    <aside class="sidebar">...</aside>
    <main id="main-content">
      <section class="panel hero" id="system">
        <div class="kicker">Loop Status</div>
        <h2>What You Should Know Now</h2>
        <div class="meta">{escape(snapshot.mode_reason)}</div>
        <div class="stat-grid">
          <div class="stat">
            <div class="stat-label">Mode</div>
            <div class="stat-value">{escape(snapshot.current_mode)}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Forecast State</div>
            <div class="stat-value">{escape(snapshot.latest_forecast.status if snapshot.latest_forecast else "No forecast")}</div>
          </div>
          <div class="stat">
            <div class="stat-label">Replay Context</div>
            <div class="stat-value">{escape(snapshot.replay_freshness_label)}</div>
          </div>
        </div>
      </section>
      ...
      <section class="panel third" id="replay">
        <div class="kicker">Historical Replay Context</div>
        {render_replay_panel(snapshot.latest_replay_summary)}
      </section>
    </main>
  </div>
</body>
</html>"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_promotes_operator_summary_over_internal_counts tests/test_dashboard.py::test_render_dashboard_labels_replay_as_historical_context -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/dashboard.py tests/test_dashboard.py
git commit -m "feat: prioritize operator summary in dashboard"
```

### Task 2: Rebalance Layout So the Latest Forecast Is the Main Read Target

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing layout tests**

```python
def test_render_dashboard_makes_latest_forecast_primary_panel(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert "Current Forecast" in html
    assert "Latest Forecast" not in html
    assert "Latest Replay" not in html


def test_render_dashboard_hides_raw_metadata_by_default(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert "<details>" in html
    assert "<details open>" not in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_makes_latest_forecast_primary_panel tests/test_dashboard.py::test_render_dashboard_hides_raw_metadata_by_default -q`
Expected: FAIL because the panel titles and raw metadata expansion still reflect the older inspector structure

- [ ] **Step 3: Write minimal implementation**

```python
def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    ...
    <div class="grid">
      <section class="panel hero" id="forecast">
        <div class="kicker">Current Forecast</div>
        {render_forecast_panel(snapshot.latest_forecast)}
      </section>
      <section class="panel half" id="replay">
        <div class="kicker">Historical Replay Context</div>
        {render_replay_panel(snapshot.latest_replay_summary)}
      </section>
      <section class="panel half" id="review">
        <div class="kicker">Latest Review & Proposal</div>
        {render_review_panel(snapshot.latest_review, snapshot.latest_proposal)}
      </section>
    </div>
    <section class="panel" id="raw">
      <div class="kicker">Debug Details</div>
      <details>
        <summary>last_run_meta.json</summary>
        ...
      </details>
      <details>
        <summary>last_replay_meta.json</summary>
        ...
      </details>
    </section>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_makes_latest_forecast_primary_panel tests/test_dashboard.py::test_render_dashboard_hides_raw_metadata_by_default -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/dashboard.py tests/test_dashboard.py
git commit -m "feat: rebalance dashboard reading order"
```

### Task 3: Improve Accessibility and Long-String Handling Without Adding UI Controls

**Files:**
- Modify: `src/forecast_loop/dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing accessibility tests**

```python
def test_render_dashboard_includes_skip_link_and_focus_styles(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert 'class="skip-link"' in html
    assert ':focus-visible' in html


def test_render_dashboard_marks_long_operational_strings_with_wrapping_helpers(tmp_path):
    from forecast_loop.dashboard import build_dashboard_snapshot, render_dashboard_html

    snapshot = build_dashboard_snapshot(tmp_path)
    html = render_dashboard_html(snapshot)

    assert "overflow-wrap: anywhere" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_includes_skip_link_and_focus_styles tests/test_dashboard.py::test_render_dashboard_marks_long_operational_strings_with_wrapping_helpers -q`
Expected: FAIL if the dashboard structure regressed during the layout rewrite

- [ ] **Step 3: Write minimal implementation**

```python
def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <style>
    ...
    .skip-link:focus-visible {{
      transform: translateY(0);
      outline: 2px solid var(--focus);
    }}
    .meta, .panel h2, dd {{
      overflow-wrap: anywhere;
    }}
    .nav-list a:focus-visible,
    summary:focus-visible {{
      outline: 2px solid var(--focus);
      outline-offset: 3px;
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  ...
</body>
</html>"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_dashboard.py::test_render_dashboard_includes_skip_link_and_focus_styles tests/test_dashboard.py::test_render_dashboard_marks_long_operational_strings_with_wrapping_helpers -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/forecast_loop/dashboard.py tests/test_dashboard.py
git commit -m "fix: harden dashboard readability and accessibility"
```

### Task 4: Document the Inspector Reading Order and Verify the End-to-End Flow

**Files:**
- Modify: `README.md`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write the failing CLI documentation smoke test**

```python
def test_cli_render_dashboard_writes_html_file(tmp_path):
    exit_code = main(
        [
            "render-dashboard",
            "--storage-dir",
            str(tmp_path),
        ]
    )

    output_path = tmp_path / "dashboard.html"

    assert exit_code == 0
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Loop Status" in html
    assert "Current Forecast" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard.py::test_cli_render_dashboard_writes_html_file -q`
Expected: FAIL if the dashboard command or output no longer match the new operator-readable wording

- [ ] **Step 3: Update README with the new reading order**

```markdown
## Read-Only Inspector

Read the dashboard in this order:

1. Loop Status
2. Current Forecast
3. Historical Replay Context
4. Latest Review and Proposal
5. Debug Details

The first screen is intentionally optimized for operator judgment, while raw metadata is available as collapsed detail below.
```

- [ ] **Step 4: Run full verification**

Run: `pytest -q`
Expected: PASS

Run: `python run_forecast_loop.py render-dashboard --storage-dir .\\paper_storage\\hourly-paper-forecast\\coingecko\\BTC-USD`
Expected: exit 0 and a regenerated `dashboard.html` in that storage directory

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_dashboard.py src/forecast_loop/dashboard.py
git commit -m "docs: describe operator dashboard reading order"
```
