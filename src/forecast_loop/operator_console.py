from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from urllib.parse import urlparse

from forecast_loop.health import run_health_check
from forecast_loop.models import (
    BacktestResult,
    BaselineEvaluation,
    HealthCheckResult,
    PaperPortfolioSnapshot,
    RepairRequest,
    RiskSnapshot,
    StrategyDecision,
    WalkForwardValidation,
)
from forecast_loop.storage import JsonFileRepository


OPERATOR_CONSOLE_PAGES = ("overview", "decisions", "portfolio", "research", "health", "control")
LOCAL_BIND_HOSTS = {"127.0.0.1", "localhost", "::1"}


@dataclass(slots=True)
class OperatorConsoleSnapshot:
    storage_dir: Path
    generated_at: datetime
    symbol: str
    health: HealthCheckResult
    decisions: list[StrategyDecision]
    latest_decision: StrategyDecision | None
    latest_portfolio: PaperPortfolioSnapshot | None
    latest_risk: RiskSnapshot | None
    latest_baseline: BaselineEvaluation | None
    latest_backtest: BacktestResult | None
    latest_walk_forward: WalkForwardValidation | None
    repair_requests: list[RepairRequest]
    counts: dict[str, int]


def build_operator_console_snapshot(
    storage_dir: Path | str,
    *,
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> OperatorConsoleSnapshot:
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        raise ValueError(f"storage dir does not exist: {storage_path}")
    if not storage_path.is_dir():
        raise ValueError(f"storage dir is not a directory: {storage_path}")

    generated_at = now or datetime.now(tz=UTC)
    repository = JsonFileRepository(storage_path)
    decisions = [item for item in repository.load_strategy_decisions() if item.symbol == symbol]
    portfolios = repository.load_portfolio_snapshots()
    risks = [item for item in repository.load_risk_snapshots() if item.symbol == symbol]
    baselines = [item for item in repository.load_baseline_evaluations() if item.symbol == symbol]
    backtests = [item for item in repository.load_backtest_results() if item.symbol == symbol]
    walk_forwards = [item for item in repository.load_walk_forward_validations() if item.symbol == symbol]
    repair_requests = repository.load_repair_requests()
    health = run_health_check(
        storage_dir=storage_path,
        symbol=symbol,
        now=generated_at,
        create_repair_request=False,
    )

    return OperatorConsoleSnapshot(
        storage_dir=storage_path,
        generated_at=generated_at,
        symbol=symbol,
        health=health,
        decisions=decisions,
        latest_decision=_latest(decisions),
        latest_portfolio=_latest(portfolios),
        latest_risk=_latest(risks),
        latest_baseline=_latest(baselines),
        latest_backtest=_latest(backtests),
        latest_walk_forward=_latest(walk_forwards),
        repair_requests=repair_requests,
        counts={
            "forecasts": len(repository.load_forecasts()),
            "scores": len(repository.load_scores()),
            "reviews": len(repository.load_reviews()),
            "decisions": len(decisions),
            "orders": len(repository.load_paper_orders()),
            "fills": len(repository.load_paper_fills()),
            "repair_requests": len(repair_requests),
            "backtests": len(backtests),
            "walk_forward_validations": len(walk_forwards),
        },
    )


def render_operator_console_page(
    snapshot: OperatorConsoleSnapshot,
    *,
    page: str = "overview",
) -> str:
    if page not in OPERATOR_CONSOLE_PAGES:
        raise ValueError(f"unknown operator console page: {page}")

    body = {
        "overview": _render_overview,
        "decisions": _render_decisions,
        "portfolio": _render_portfolio,
        "research": _render_research,
        "health": _render_health,
        "control": _render_control,
    }[page](snapshot)

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_page_title(page)} - Paper Operator Console</title>
  <style>
    :root {{
      --ink: #16201b;
      --muted: #65706a;
      --line: #d9e0da;
      --paper: #f6f2ea;
      --panel: #fffdfa;
      --accent: #1f6f4a;
      --alert: #9d2f2f;
      --warn: #8a5d15;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(31, 111, 74, 0.14), transparent 30rem),
        linear-gradient(135deg, #f6f2ea 0%, #eef3ed 100%);
      color: var(--ink);
      font-family: Georgia, "Noto Serif TC", "Microsoft JhengHei", serif;
      line-height: 1.55;
    }}
    a {{ color: inherit; }}
    .shell {{
      display: grid;
      grid-template-columns: 15rem minmax(0, 1fr);
      min-height: 100vh;
    }}
    nav {{
      border-right: 1px solid var(--line);
      padding: 2rem 1.25rem;
      background: rgba(255, 253, 250, 0.72);
      position: sticky;
      top: 0;
      height: 100vh;
    }}
    nav h1 {{
      font-size: 1rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin: 0 0 1.5rem;
    }}
    nav a {{
      display: block;
      text-decoration: none;
      padding: 0.65rem 0.75rem;
      border-radius: 0.75rem;
      margin-bottom: 0.25rem;
      color: var(--muted);
    }}
    nav a[aria-current="page"] {{
      color: var(--ink);
      background: #e3eee6;
      border: 1px solid #c1d7c8;
    }}
    nav a:focus-visible, button:focus-visible {{
      outline: 3px solid #2f7f55;
      outline-offset: 2px;
    }}
    main {{ padding: 2.5rem; }}
    .eyebrow {{
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }}
    h2 {{
      font-size: clamp(2rem, 4vw, 4.2rem);
      line-height: 0.96;
      margin: 0.25rem 0 1rem;
      max-width: 14ch;
    }}
    .lede {{
      color: var(--muted);
      max-width: 68rem;
      margin-bottom: 1.5rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 1rem;
    }}
    .wide {{ grid-column: span 2; }}
    .panel {{
      background: rgba(255, 253, 250, 0.9);
      border: 1px solid var(--line);
      border-radius: 1.2rem;
      padding: 1.2rem;
      box-shadow: 0 18px 42px rgba(40, 50, 42, 0.08);
    }}
    .panel h3 {{ margin: 0 0 0.85rem; font-size: 1.05rem; }}
    .timeline {{
      display: grid;
      gap: 1rem;
    }}
    .decision-card {{
      border: 1px solid var(--line);
      border-radius: 1rem;
      padding: 1rem;
      background: #fffdfa;
    }}
    .decision-card header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
      margin-bottom: 0.75rem;
    }}
    .decision-card h4 {{
      margin: 0;
      font-size: 1.25rem;
    }}
    .evidence-list, .conditions {{
      margin: 0.5rem 0 0;
      padding-left: 1.1rem;
    }}
    .evidence-list li, .conditions li {{
      margin: 0.25rem 0;
      overflow-wrap: anywhere;
    }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 0.65rem 0;
    }}
    .metric {{
      font-size: 2rem;
      line-height: 1;
      font-weight: 700;
    }}
    .muted {{ color: var(--muted); }}
    .status {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      border-radius: 999px;
      padding: 0.25rem 0.6rem;
      border: 1px solid var(--line);
      background: #f8fbf8;
      font-size: 0.86rem;
      font-weight: 700;
    }}
    .status.alert {{ color: var(--alert); border-color: #e6b5b5; background: #fff4f2; }}
    .status.warn {{ color: var(--warn); border-color: #ead39d; background: #fff9e9; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      font-size: 0.92rem;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 0.7rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 700; }}
    code {{
      overflow-wrap: anywhere;
      font-family: "Cascadia Mono", Consolas, monospace;
      font-size: 0.85em;
    }}
    .disabled-controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.75rem;
    }}
    button {{
      border: 1px solid var(--line);
      border-radius: 0.9rem;
      padding: 0.85rem;
      background: #edf2ed;
      color: var(--muted);
      cursor: not-allowed;
    }}
    @media (max-width: 900px) {{
      .shell {{ grid-template-columns: 1fr; }}
      nav {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      main {{ padding: 1.25rem; }}
      .grid {{ grid-template-columns: 1fr; }}
      .wide {{ grid-column: span 1; }}
      .disabled-controls {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav aria-label="Operator console sections">
      <h1>Paper Console</h1>
      {_render_nav(page)}
    </nav>
    <main>
      <div class="eyebrow">本機只讀 / Paper-only</div>
      <h2>{_page_title(page)}</h2>
      <p class="lede">這是 M5A 本機 operator console skeleton。它只讀取 paper artifacts，不提供真實交易、不提交 broker/exchange order、不讀取或顯示 secrets。</p>
      {body}
      <p class="muted">產生時間：{_format_dt(snapshot.generated_at)} / Storage：<code>{escape(str(snapshot.storage_dir))}</code></p>
    </main>
  </div>
</body>
</html>
"""


def write_operator_console_page(
    *,
    storage_dir: Path | str,
    output: Path | str,
    page: str = "overview",
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> Path:
    snapshot = build_operator_console_snapshot(storage_dir, symbol=symbol, now=now)
    html = render_operator_console_page(snapshot, page=page)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def serve_operator_console(
    *,
    storage_dir: Path | str,
    host: str = "127.0.0.1",
    port: int = 8765,
    symbol: str = "BTC-USD",
    now: datetime | None = None,
) -> None:
    validate_local_bind_host(host)
    storage_path = Path(storage_dir)

    class OperatorConsoleHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            page = parsed.path.strip("/") or "overview"
            if page not in OPERATOR_CONSOLE_PAGES:
                self.send_error(404, "Unknown operator console page")
                return
            try:
                snapshot = build_operator_console_snapshot(storage_path, symbol=symbol, now=now)
                payload = render_operator_console_page(snapshot, page=page).encode("utf-8")
            except ValueError as exc:
                self.send_error(400, str(exc))
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return

    server_class = _local_server_class(host)
    server = server_class((host, port), OperatorConsoleHandler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def validate_local_bind_host(host: str) -> None:
    if host not in LOCAL_BIND_HOSTS:
        allowed = ", ".join(sorted(LOCAL_BIND_HOSTS))
        raise ValueError(f"operator-console is local-only; host must be one of: {allowed}")


def local_address_family_for_host(host: str) -> socket.AddressFamily:
    validate_local_bind_host(host)
    return socket.AF_INET6 if host == "::1" else socket.AF_INET


def _local_server_class(host: str) -> type[ThreadingHTTPServer]:
    address_family = local_address_family_for_host(host)

    class LocalOnlyThreadingHTTPServer(ThreadingHTTPServer):
        pass

    LocalOnlyThreadingHTTPServer.address_family = address_family
    return LocalOnlyThreadingHTTPServer


def _render_nav(current_page: str) -> str:
    return "\n".join(
        f'<a href="/{page}"{_aria_current(page, current_page)}>{_page_title(page)}</a>'
        for page in OPERATOR_CONSOLE_PAGES
    )


def _aria_current(page: str, current_page: str) -> str:
    return ' aria-current="page"' if page == current_page else ""


def _render_overview(snapshot: OperatorConsoleSnapshot) -> str:
    decision = snapshot.latest_decision
    action = "尚無決策" if decision is None else _translate_action(decision.action)
    health_class = _status_class(snapshot.health.severity)
    tradeable = "否" if decision is None else ("是" if decision.tradeable else "否")
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>明日策略決策</h3>
    <div class="metric">{escape(action)}</div>
    <p>{escape(decision.reason_summary) if decision else "目前還沒有 strategy_decisions artifact。"}</p>
    <p class="muted">可交易：{tradeable} / 證據等級：{escape(decision.evidence_grade) if decision else "INSUFFICIENT"} / 風險：{escape(decision.risk_level) if decision else "UNKNOWN"}</p>
  </article>
  <article class="panel">
    <h3>健康狀態</h3>
    <span class="{health_class}">{escape(_translate_health(snapshot.health.status))}</span>
    <p class="muted">repair_required={str(snapshot.health.repair_required).lower()}</p>
  </article>
  <article class="panel">
    <h3>Paper Portfolio</h3>
    <div class="metric">{_format_money(snapshot.latest_portfolio.nav if snapshot.latest_portfolio else None)}</div>
    <p class="muted">曝險：{_format_pct(snapshot.latest_portfolio.gross_exposure_pct if snapshot.latest_portfolio else None)}</p>
  </article>
  <article class="panel">
    <h3>Artifact Counts</h3>
    {_render_counts(snapshot.counts)}
  </article>
  <article class="panel">
    <h3>研究證據</h3>
    <p>Baseline：{_artifact_id(snapshot.latest_baseline, "baseline_id")}</p>
    <p>Backtest：{_artifact_id(snapshot.latest_backtest, "result_id")}</p>
    <p>Walk-forward：{_artifact_id(snapshot.latest_walk_forward, "validation_id")}</p>
  </article>
</section>
"""


def _render_decisions(snapshot: OperatorConsoleSnapshot) -> str:
    decisions = sorted(snapshot.decisions, key=lambda item: item.created_at, reverse=True)
    latest = decisions[0] if decisions else None
    timeline = "\n".join(_decision_card(decision, is_latest=index == 0) for index, decision in enumerate(decisions[:20]))
    if not timeline:
        timeline = '<p class="muted">目前沒有 strategy_decisions artifact。</p>'
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>最新決策</h3>
    {_latest_decision_summary(latest)}
  </article>
  <article class="panel">
    <h3>讀法</h3>
    <p>此頁把每筆 paper-only strategy decision 的理由、證據連結、失效條件與 blocked reason 展開，方便追溯判斷來源。</p>
  </article>
  <article class="panel wide">
    <h3>Decision Timeline</h3>
    <div class="timeline">{timeline}</div>
  </article>
</section>
"""


def _render_portfolio(snapshot: OperatorConsoleSnapshot) -> str:
    portfolio = snapshot.latest_portfolio
    risk = snapshot.latest_risk
    positions = portfolio.positions if portfolio else []
    position_rows = "\n".join(
        "<tr>"
        f"<td>{escape(position.symbol)}</td>"
        f"<td>{position.quantity:.8f}</td>"
        f"<td>{_format_money(position.market_value)}</td>"
        f"<td>{_format_pct(position.position_pct)}</td>"
        f"<td>{_format_money(position.unrealized_pnl)}</td>"
        "</tr>"
        for position in positions
    )
    if not position_rows:
        position_rows = '<tr><td colspan="5">目前沒有 paper position。</td></tr>'
    return f"""
<section class="grid">
  <article class="panel">
    <h3>NAV / Cash</h3>
    <div class="metric">{_format_money(portfolio.nav if portfolio else None)}</div>
    <p>Cash：{_format_money(portfolio.cash if portfolio else None)}</p>
  </article>
  <article class="panel">
    <h3>Risk</h3>
    <p>Status：{escape(risk.status) if risk else "UNKNOWN"}</p>
    <p>Drawdown：{_format_pct(risk.current_drawdown_pct if risk else None)}</p>
  </article>
  <article class="panel">
    <h3>Exposure</h3>
    <p>Gross：{_format_pct(portfolio.gross_exposure_pct if portfolio else None)}</p>
    <p>Net：{_format_pct(portfolio.net_exposure_pct if portfolio else None)}</p>
  </article>
  <article class="panel wide">
    <h3>Positions</h3>
    <table>
      <thead><tr><th>Symbol</th><th>Quantity</th><th>Market Value</th><th>Position %</th><th>Unrealized PnL</th></tr></thead>
      <tbody>{position_rows}</tbody>
    </table>
  </article>
</section>
"""


def _render_research(snapshot: OperatorConsoleSnapshot) -> str:
    baseline = snapshot.latest_baseline
    backtest = snapshot.latest_backtest
    walk_forward = snapshot.latest_walk_forward
    return f"""
<section class="grid">
  <article class="panel">
    <h3>Baseline</h3>
    <p>ID：{_artifact_id(baseline, "baseline_id")}</p>
    <p>Sample：{baseline.sample_size if baseline else "n/a"}</p>
    <p>Model edge：{_format_number(baseline.model_edge if baseline else None)}</p>
  </article>
  <article class="panel">
    <h3>Backtest</h3>
    <p>ID：{_artifact_id(backtest, "result_id")}</p>
    <p>Return：{_format_pct(backtest.strategy_return if backtest else None)}</p>
    <p>Benchmark：{_format_pct(backtest.benchmark_return if backtest else None)}</p>
    <p>Max DD：{_format_pct(backtest.max_drawdown if backtest else None)}</p>
  </article>
  <article class="panel">
    <h3>Walk-forward</h3>
    <p>ID：{_artifact_id(walk_forward, "validation_id")}</p>
    <p>Windows：{walk_forward.window_count if walk_forward else "n/a"}</p>
    <p>Excess：{_format_pct(walk_forward.average_excess_return if walk_forward else None)}</p>
    <p>Overfit flags：{escape(", ".join(walk_forward.overfit_risk_flags) if walk_forward and walk_forward.overfit_risk_flags else "none")}</p>
  </article>
</section>
"""


def _render_health(snapshot: OperatorConsoleSnapshot) -> str:
    finding_rows = "\n".join(
        "<tr>"
        f"<td>{escape(finding.severity)}</td>"
        f"<td><code>{escape(finding.code)}</code></td>"
        f"<td>{escape(finding.message)}</td>"
        f"<td>{escape(finding.artifact_path or '')}</td>"
        "</tr>"
        for finding in snapshot.health.findings
    )
    if not finding_rows:
        finding_rows = '<tr><td colspan="4">目前沒有 health finding。</td></tr>'
    repair_rows = "\n".join(
        "<tr>"
        f"<td><code>{escape(repair.repair_request_id)}</code></td>"
        f"<td>{escape(repair.status)}</td>"
        f"<td>{escape(repair.severity)}</td>"
        f"<td>{escape(repair.observed_failure)}</td>"
        "</tr>"
        for repair in sorted(snapshot.repair_requests, key=lambda item: item.created_at, reverse=True)[:20]
    )
    if not repair_rows:
        repair_rows = '<tr><td colspan="4">目前沒有 repair request。</td></tr>'
    return f"""
<section class="grid">
  <article class="panel wide">
    <h3>Health Findings</h3>
    <table>
      <thead><tr><th>Severity</th><th>Code</th><th>Message</th><th>Artifact</th></tr></thead>
      <tbody>{finding_rows}</tbody>
    </table>
  </article>
  <article class="panel wide">
    <h3>Repair Queue</h3>
    <table>
      <thead><tr><th>ID</th><th>Status</th><th>Severity</th><th>Observed Failure</th></tr></thead>
      <tbody>{repair_rows}</tbody>
    </table>
  </article>
</section>
"""


def _render_control(snapshot: OperatorConsoleSnapshot) -> str:
    del snapshot
    labels = ["PAUSE", "RESUME", "STOP_NEW_ENTRIES", "REDUCE_RISK", "EMERGENCY_STOP", "SET_MAX_POSITION"]
    buttons = "\n".join(f"<button disabled>{label}（未啟用）</button>" for label in labels)
    return f"""
<section class="panel">
  <h3>Paper-only Control Placeholder</h3>
  <p>控制面板在 M5A 只顯示 skeleton。所有控制都停用，不寫入 audit log，不改變 automation，不提交任何 order。</p>
  <div class="disabled-controls">{buttons}</div>
</section>
"""


def _latest_decision_summary(decision: StrategyDecision | None) -> str:
    if decision is None:
        return "<p class=\"muted\">目前沒有最新決策。</p>"
    blocked = decision.blocked_reason or "none"
    return f"""
<div class="metric">{escape(_translate_action(decision.action))}</div>
<p>{escape(decision.reason_summary)}</p>
<div class="badge-row">
  <span class="status">Evidence {escape(decision.evidence_grade)}</span>
  <span class="status">Risk {escape(decision.risk_level)}</span>
  <span class="status">Tradeable {'是' if decision.tradeable else '否'}</span>
</div>
<p class="muted">Blocked reason：<code>{escape(blocked)}</code></p>
"""


def _decision_card(decision: StrategyDecision, *, is_latest: bool) -> str:
    blocked = decision.blocked_reason or "none"
    latest_label = '<span class="status">最新</span>' if is_latest else ""
    return f"""
<article class="decision-card">
  <header>
    <div>
      <h4>{escape(_translate_action(decision.action))} / {escape(decision.symbol)}</h4>
      <div class="muted">{_format_dt(decision.created_at)} · horizon {decision.horizon_hours}h</div>
    </div>
    {latest_label}
  </header>
  <p>{escape(decision.reason_summary)}</p>
  <div class="badge-row">
    <span class="status">Evidence {escape(decision.evidence_grade)}</span>
    <span class="status">Risk {escape(decision.risk_level)}</span>
    <span class="status">Tradeable {'是' if decision.tradeable else '否'}</span>
  </div>
  <p>建議部位：{_format_pct(decision.recommended_position_pct)} / 目前部位：{_format_pct(decision.current_position_pct)} / 上限：{_format_pct(decision.max_position_pct)}</p>
  <p>Blocked reason：<code>{escape(blocked)}</code></p>
  <h5>Evidence Links</h5>
  {_evidence_links(decision)}
  <h5>Invalidation Conditions</h5>
  {_conditions(decision.invalidation_conditions)}
</article>
"""


def _evidence_links(decision: StrategyDecision) -> str:
    groups = [
        ("Forecast", decision.forecast_ids),
        ("Score", decision.score_ids),
        ("Review", decision.review_ids),
        ("Baseline", decision.baseline_ids),
    ]
    rows = []
    for label, ids in groups:
        if ids:
            for artifact_id in ids:
                rows.append(f"<li>{label}: <code>{escape(artifact_id)}</code></li>")
        else:
            rows.append(f"<li>{label}: <span class=\"muted\">none</span></li>")
    return f"<ul class=\"evidence-list\">{''.join(rows)}</ul>"


def _conditions(conditions: list[str]) -> str:
    if not conditions:
        return '<p class="muted">未記錄失效條件。</p>'
    return "<ul class=\"conditions\">" + "".join(f"<li>{escape(condition)}</li>" for condition in conditions) + "</ul>"


def _render_counts(counts: dict[str, int]) -> str:
    return "".join(f"<p>{escape(name)}：{count}</p>" for name, count in counts.items())


def _page_title(page: str) -> str:
    return {
        "overview": "總覽",
        "decisions": "決策",
        "portfolio": "投資組合",
        "research": "研究",
        "health": "健康 / 修復",
        "control": "控制 Placeholder",
    }[page]


def _translate_action(action: str) -> str:
    return {
        "BUY": "買進",
        "SELL": "賣出",
        "HOLD": "持有",
        "REDUCE_RISK": "降低風險",
        "STOP_NEW_ENTRIES": "停止新進場",
    }.get(action, action)


def _translate_health(status: str) -> str:
    return {
        "healthy": "健康",
        "degraded": "注意",
        "unhealthy": "阻塞",
    }.get(status, status)


def _status_class(severity: str) -> str:
    if severity == "blocking":
        return "status alert"
    if severity == "warning":
        return "status warn"
    return "status"


def _latest(items: list):
    return max(items, key=lambda item: item.created_at) if items else None


def _artifact_id(item: object | None, field: str) -> str:
    if item is None:
        return "n/a"
    return f"<code>{escape(str(getattr(item, field)))}</code>"


def _format_dt(value: datetime | None) -> str:
    return "n/a" if value is None else value.astimezone(UTC).isoformat()


def _format_money(value: float | None) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def _format_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.2f}%"


def _format_number(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"
