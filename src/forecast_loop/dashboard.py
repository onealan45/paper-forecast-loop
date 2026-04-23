from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import escape
import json
import os
from pathlib import Path
import tomllib

from forecast_loop.models import EvaluationSummary, Forecast, ForecastScore, Proposal, Review
from forecast_loop.storage import JsonFileRepository


@dataclass(slots=True)
class DashboardSnapshot:
    storage_dir: Path
    last_run_meta: dict | None
    last_replay_meta: dict | None
    latest_forecast: Forecast | None
    latest_score: ForecastScore | None
    latest_review: Review | None
    latest_proposal: Proposal | None
    latest_replay_summary: EvaluationSummary | None
    forecast_count: int
    score_count: int
    review_count: int
    proposal_count: int
    replay_summary_count: int
    current_mode: str
    hourly_status: str
    building_status: str
    mode_reason: str
    replay_freshness_label: str
    replay_generated_at: datetime | None
    replay_is_stale: bool


def build_dashboard_snapshot(storage_dir: Path | str) -> DashboardSnapshot:
    storage_dir = Path(storage_dir)
    repository = JsonFileRepository(storage_dir)
    forecasts = repository.load_forecasts()
    scores = repository.load_scores()
    reviews = repository.load_reviews()
    proposals = repository.load_proposals()
    replay_summaries = repository.load_evaluation_summaries()
    latest_forecast = forecasts[-1] if forecasts else None
    latest_replay_summary = replay_summaries[-1] if replay_summaries else None
    hourly_status = _load_automation_status("hourly-paper-forecast")
    building_status = _load_automation_status("loop-building-heartbeat")
    current_mode, mode_reason = _derive_mode(hourly_status, building_status)
    replay_freshness_label, replay_generated_at, replay_is_stale = _derive_replay_freshness(
        latest_replay_summary,
        latest_forecast,
    )

    return DashboardSnapshot(
        storage_dir=storage_dir,
        last_run_meta=_load_json(storage_dir / "last_run_meta.json"),
        last_replay_meta=_load_json(storage_dir / "last_replay_meta.json"),
        latest_forecast=latest_forecast,
        latest_score=scores[-1] if scores else None,
        latest_review=reviews[-1] if reviews else None,
        latest_proposal=proposals[-1] if proposals else None,
        latest_replay_summary=latest_replay_summary,
        forecast_count=len(forecasts),
        score_count=len(scores),
        review_count=len(reviews),
        proposal_count=len(proposals),
        replay_summary_count=len(replay_summaries),
        current_mode=current_mode,
        hourly_status=hourly_status,
        building_status=building_status,
        mode_reason=mode_reason,
        replay_freshness_label=replay_freshness_label,
        replay_generated_at=replay_generated_at,
        replay_is_stale=replay_is_stale,
    )


def render_dashboard_html(snapshot: DashboardSnapshot) -> str:
    latest_forecast = snapshot.latest_forecast
    latest_review = snapshot.latest_review
    latest_proposal = snapshot.latest_proposal
    latest_replay = snapshot.latest_replay_summary

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Paper Forecast Loop Dashboard</title>
  <style>
    html {{ color-scheme: dark; }}
    :root {{
      --bg: #08111b;
      --panel: rgba(11, 24, 38, 0.88);
      --panel-2: rgba(18, 34, 51, 0.9);
      --line: rgba(116, 150, 181, 0.24);
      --text: #eaf1f7;
      --muted: #8fa7be;
      --accent: #7dd3fc;
      --ok: #8df5ae;
      --warn: #ffd479;
      --focus: #f8fafc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Inter", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(78, 168, 222, 0.12), transparent 28%),
        linear-gradient(180deg, #08111b 0%, #0b1521 100%);
      color: var(--text);
      min-height: 100vh;
    }}
    .skip-link {{
      position: absolute;
      top: 12px;
      left: 12px;
      transform: translateY(-150%);
      padding: 10px 14px;
      border-radius: 12px;
      background: rgba(248, 250, 252, 0.96);
      color: #08111b;
      text-decoration: none;
      z-index: 20;
    }}
    .skip-link:focus-visible {{
      transform: translateY(0);
      outline: 2px solid var(--focus);
      outline-offset: 2px;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 280px 1fr;
      min-height: 100vh;
    }}
    .sidebar {{
      border-right: 1px solid var(--line);
      background: rgba(5, 12, 19, 0.82);
      padding: 28px 22px;
      position: sticky;
      top: 0;
      height: 100vh;
    }}
    .brand {{
      font-size: 0.78rem;
      letter-spacing: 0.14em;
      color: var(--accent);
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 1.8rem;
      line-height: 1.1;
      text-wrap: balance;
    }}
    .subtitle {{
      color: var(--muted);
      margin: 0 0 24px;
      font-size: 0.95rem;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }}
    .nav-list {{
      list-style: none;
      padding: 0;
      margin: 28px 0 0;
      display: grid;
      gap: 10px;
    }}
    .nav-list a {{
      display: block;
      padding: 10px 12px;
      border: 1px solid transparent;
      border-radius: 12px;
      color: var(--muted);
      text-decoration: none;
      background: transparent;
    }}
    .nav-list a:hover {{
      color: var(--text);
      border-color: var(--line);
      background: rgba(125, 211, 252, 0.06);
    }}
    .nav-list a:focus-visible,
    summary:focus-visible {{
      outline: 2px solid var(--focus);
      outline-offset: 3px;
      color: var(--text);
      border-color: var(--accent);
    }}
    main {{
      padding: 34px 40px 48px;
      display: grid;
      gap: 22px;
    }}
    section[id] {{
      scroll-margin-top: 24px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      backdrop-filter: blur(18px);
      box-shadow: 0 10px 35px rgba(0, 0, 0, 0.18);
    }}
    .hero {{ grid-column: span 12; }}
    .half {{ grid-column: span 6; }}
    .third {{ grid-column: span 4; }}
    .panel h2 {{
      margin: 0 0 8px;
      font-size: 1.05rem;
      letter-spacing: 0.01em;
      text-wrap: balance;
      overflow-wrap: anywhere;
    }}
    .meta {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 14px;
      overflow-wrap: anywhere;
    }}
    .stat-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      padding: 14px 14px 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel-2);
    }}
    .stat-label {{
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: 1.35rem;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }}
    .kicker {{
      color: var(--accent);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 6px;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
    dl {{
      display: grid;
      grid-template-columns: 180px 1fr;
      gap: 10px 16px;
      margin: 0;
    }}
    dt {{ color: var(--muted); }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    .tag {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(125, 211, 252, 0.08);
      font-size: 0.85rem;
    }}
    .tag.warn {{
      background: rgba(255, 212, 121, 0.1);
      color: var(--warn);
    }}
    .tag.ok {{
      background: rgba(141, 245, 174, 0.1);
      color: var(--ok);
    }}
    pre {{
      margin: 0;
      padding: 14px;
      border-radius: 14px;
      background: rgba(4, 11, 18, 0.92);
      border: 1px solid var(--line);
      color: #d4e6f8;
      overflow: auto;
      font-size: 0.82rem;
      line-height: 1.5;
    }}
    details {{
      border-top: 1px solid var(--line);
      padding-top: 14px;
      margin-top: 16px;
    }}
    summary {{
      cursor: pointer;
      color: var(--muted);
    }}
    @media (max-width: 980px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      .half, .third {{ grid-column: span 12; }}
      .stat-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      main {{ padding: 24px 18px 32px; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">Paper-Only Inspector</div>
      <h1>Paper Forecast Loop</h1>
      <p class="subtitle">A read-only operator view for the current forecast loop, replay summaries, and artifact provenance.</p>
      <ul class="nav-list">
        <li><a href="#system">System State</a></li>
        <li><a href="#forecast">Latest Forecast</a></li>
        <li><a href="#review">Review & Proposal</a></li>
        <li><a href="#replay">Replay Summary</a></li>
        <li><a href="#raw">Raw Metadata</a></li>
      </ul>
    </aside>
    <main id="main-content">
      <section class="panel hero" id="system">
        <div class="kicker">Current Mode</div>
        <h2>System State</h2>
        <div class="meta">
          <span class="tag">{escape(snapshot.current_mode)}</span>
          <span class="tag">{escape(f"Hourly: {snapshot.hourly_status}")}</span>
          <span class="tag">{escape(f"Building: {snapshot.building_status}")}</span>
          <span class="tag {'warn' if snapshot.replay_is_stale else 'ok'}">{escape(snapshot.replay_freshness_label)}</span>
        </div>
        <div class="meta">Storage: {escape(str(snapshot.storage_dir.resolve()))}</div>
        <div class="meta">{escape(snapshot.mode_reason)}</div>
        <div class="stat-grid">
          <div class="stat"><div class="stat-label">Forecasts</div><div class="stat-value">{snapshot.forecast_count}</div></div>
          <div class="stat"><div class="stat-label">Scores</div><div class="stat-value">{snapshot.score_count}</div></div>
          <div class="stat"><div class="stat-label">Reviews</div><div class="stat-value">{snapshot.review_count}</div></div>
          <div class="stat"><div class="stat-label">Proposals</div><div class="stat-value">{snapshot.proposal_count}</div></div>
          <div class="stat"><div class="stat-label">Replay Summaries</div><div class="stat-value">{snapshot.replay_summary_count}</div></div>
        </div>
      </section>
      <div class="grid">
        <section class="panel half" id="forecast">
          <div class="kicker">Latest Forecast</div>
          {render_forecast_panel(latest_forecast)}
        </section>
        <section class="panel half" id="review">
          <div class="kicker">Latest Review</div>
          {render_review_panel(latest_review, latest_proposal)}
        </section>
        <section class="panel third">
          <div class="kicker">Latest Score</div>
          {render_score_panel(snapshot.latest_score)}
        </section>
        <section class="panel third" id="replay">
          <div class="kicker">Latest Replay</div>
          {render_replay_panel(latest_replay)}
        </section>
        <section class="panel third">
          <div class="kicker">Main Program</div>
          <dl>
            <dt>run-once</dt><dd><span class="tag">available</span></dd>
            <dt>replay-range</dt><dd><span class="tag">available</span></dd>
            <dt>render-dashboard</dt><dd><span class="tag">available</span></dd>
          </dl>
        </section>
      </div>
      <section class="panel" id="raw">
        <div class="kicker">Raw Metadata</div>
        <h2>Inspector Inputs</h2>
        <details open>
          <summary>last_run_meta.json</summary>
          <pre>{escape(json.dumps(snapshot.last_run_meta, ensure_ascii=False, indent=2) if snapshot.last_run_meta else "No run metadata yet.")}</pre>
        </details>
        <details>
          <summary>last_replay_meta.json</summary>
          <pre>{escape(json.dumps(snapshot.last_replay_meta, ensure_ascii=False, indent=2) if snapshot.last_replay_meta else "No replay metadata yet.")}</pre>
        </details>
      </section>
    </main>
  </div>
</body>
</html>"""


def render_forecast_panel(forecast: Forecast | None) -> str:
    if forecast is None:
        return '<p class="empty">No forecasts yet.</p>'

    return f"""
      <h2>{escape(forecast.symbol)}</h2>
      <div class="meta"><span class="tag">{escape(forecast.status)}</span> <span class="tag">{escape(forecast.status_reason)}</span></div>
      <dl>
        <dt>Anchor</dt><dd>{escape(forecast.anchor_time.isoformat())}</dd>
        <dt>Target Window</dt><dd>{escape(forecast.target_window_start.isoformat())} → {escape(forecast.target_window_end.isoformat())}</dd>
        <dt>Predicted Regime</dt><dd>{escape(str(forecast.predicted_regime))}</dd>
        <dt>Confidence</dt><dd>{escape(str(forecast.confidence))}</dd>
        <dt>Provider Through</dt><dd>{escape(str(forecast.provider_data_through.isoformat()) if forecast.provider_data_through else "None")}</dd>
        <dt>Observed Candles</dt><dd>{forecast.observed_candle_count} / {forecast.expected_candle_count}</dd>
      </dl>
    """


def render_score_panel(score: ForecastScore | None) -> str:
    if score is None:
        return '<p class="empty">No scores yet.</p>'

    return f"""
      <h2>{escape(score.score_id)}</h2>
      <div class="meta">{escape(score.predicted_regime)} → {escape(score.actual_regime)}</div>
      <dl>
        <dt>Score</dt><dd>{score.score:.2f}</dd>
        <dt>Forecast</dt><dd>{escape(score.forecast_id)}</dd>
        <dt>Observed Candles</dt><dd>{score.observed_candle_count} / {score.expected_candle_count}</dd>
        <dt>Provider Through</dt><dd>{escape(score.provider_data_through.isoformat())}</dd>
      </dl>
    """


def render_review_panel(review: Review | None, proposal: Proposal | None) -> str:
    if review is None:
        return '<p class="empty">No reviews yet.</p>'

    proposal_html = (
        f"""
        <details open>
          <summary>Latest Proposal</summary>
          <pre>{escape(json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2))}</pre>
        </details>
        """
        if proposal is not None
        else '<p class="empty">No proposal generated.</p>'
    )
    return f"""
      <h2>{escape(review.review_id)}</h2>
      <div class="meta">{escape(review.summary)}</div>
      <dl>
        <dt>Average Score</dt><dd>{review.average_score:.2f}</dd>
        <dt>Threshold</dt><dd>{review.threshold_used:.2f}</dd>
        <dt>Forecast IDs</dt><dd>{escape(", ".join(review.forecast_ids) or "None")}</dd>
        <dt>Score IDs</dt><dd>{escape(", ".join(review.score_ids) or "None")}</dd>
        <dt>Proposal Recommended</dt><dd>{escape(str(review.proposal_recommended))}</dd>
      </dl>
      {proposal_html}
    """


def render_replay_panel(summary: EvaluationSummary | None) -> str:
    if summary is None:
        return '<p class="empty">No replay summary yet.</p>'

    return f"""
      <h2>{escape(summary.summary_id)}</h2>
      <div class="meta">Historical replay evidence for the current scoped artifacts.</div>
      <dl>
        <dt>Generated At</dt><dd>{escape(summary.generated_at.isoformat())}</dd>
        <dt>Forecast Count</dt><dd>{summary.forecast_count}</dd>
        <dt>Resolved</dt><dd>{summary.resolved_count}</dd>
        <dt>Waiting</dt><dd>{summary.waiting_for_data_count}</dd>
        <dt>Unscorable</dt><dd>{summary.unscorable_count}</dd>
        <dt>Average Score</dt><dd>{escape("None" if summary.average_score is None else f"{summary.average_score:.2f}")}</dd>
        <dt>Window</dt><dd>{escape(str(summary.replay_window_start.isoformat()) if summary.replay_window_start else "None")} → {escape(str(summary.replay_window_end.isoformat()) if summary.replay_window_end else "None")}</dd>
      </dl>
    """


def write_dashboard_html(storage_dir: Path | str, output_path: Path | str | None = None) -> Path:
    snapshot = build_dashboard_snapshot(storage_dir)
    html = render_dashboard_html(snapshot)
    output_path = Path(output_path) if output_path is not None else Path(storage_dir) / "dashboard.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_automation_status(automation_id: str) -> str:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    path = codex_home / "automations" / automation_id / "automation.toml"
    if not path.exists():
        return "NOT_FOUND"
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    return payload.get("status", "UNKNOWN")


def _derive_mode(hourly_status: str, building_status: str) -> tuple[str, str]:
    if building_status == "ACTIVE":
        return "Building Mode", "Loop Building Heartbeat is active while the system is still being improved."
    if hourly_status == "ACTIVE":
        return "Hourly Research Mode", "Hourly Paper Forecast is active and the system is running paper-only prediction cycles."
    if hourly_status == "PAUSED":
        return "Paused Prediction Mode", "Hourly Paper Forecast is paused while the system remains under manual inspection."
    return "Manual Mode", "No known automation is currently active for this workspace."


def _derive_replay_freshness(
    summary: EvaluationSummary | None,
    latest_forecast: Forecast | None,
) -> tuple[str, datetime | None, bool]:
    if summary is None:
        return "No replay summary yet", None, False
    if latest_forecast is None or summary.anchor_time_end is None:
        return "Historical replay available", summary.generated_at, False
    delta = latest_forecast.anchor_time - summary.anchor_time_end
    if delta > timedelta(hours=1):
        hours = int(delta.total_seconds() // 3600)
        return f"Replay is historical ({hours}h behind latest forecast)", summary.generated_at, True
    return "Replay aligns with the latest forecast window", summary.generated_at, False
