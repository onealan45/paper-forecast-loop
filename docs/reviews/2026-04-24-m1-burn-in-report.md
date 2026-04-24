# M1.5 Burn-in Report

## Scope

- Stage: M1.5 Burn-in Report
- Repo: `onealan45/paper-forecast-loop`
- Branch: `codex/m15-burn-in`
- Active storage: `paper_storage/hourly-paper-forecast/coingecko/BTC-USD`
- Report time: 2026-04-24
- Boundary: report-only; no M2 implementation in this stage.

## Commands Run

```powershell
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
python .\run_forecast_loop.py repair-storage --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD
python .\run_forecast_loop.py render-dashboard --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD
python .\run_forecast_loop.py health-check --storage-dir .\paper_storage\hourly-paper-forecast\coingecko\BTC-USD --symbol BTC-USD
```

## Artifact Counts

| Artifact | Count | Bad rows | Duplicate IDs |
| --- | ---: | ---: | ---: |
| Forecasts | 35 | 0 | 0 |
| Scores | 15 | 0 | 0 |
| Baseline evaluations | 2 | 0 | 0 |
| Strategy decisions | 2 | 0 | 0 |
| Reviews | 13 | 0 | 0 |
| Proposals | 5 | 0 | 0 |
| Portfolio snapshots | 1 | 0 | 0 |
| Repair requests | 0 | 0 | 0 |

## Latest Forecast

- Forecast ID: `forecast:21cfb53da1d7`
- Symbol: `BTC-USD`
- Created at: `2026-04-24T13:36:41.346154+00:00`
- Anchor time: `2026-04-24T13:00:00+00:00`
- Target window: `2026-04-24T13:00:00+00:00` to `2026-04-25T13:00:00+00:00`
- Status: `pending`
- Status reason: `awaiting_horizon_end`
- Predicted regime: `trend_up`
- Confidence: `0.55`
- `last_run_meta.json` forecast ID: `forecast:21cfb53da1d7`
- `last_run_meta.json` run status: `forecast_created`

## Latest Strategy Decision

- Decision ID: `decision:92ceb07e74d7ea3f`
- Created at: `2026-04-24T13:36:41.346154+00:00`
- Action: `HOLD`
- Evidence grade: `D`
- Risk level: `MEDIUM`
- Tradeable: `false`
- Blocked reason: `model_not_beating_baseline`
- Confidence: `0.55`
- Recommended position percent: `0.0`
- Current position percent: `0.0`
- Reason summary: model evidence did not beat the naive persistence baseline, so BUY/SELL remains blocked.

## Latest Baseline / Quality State

- Baseline ID: `baseline:1be3d1a007be20ab`
- Sample size: 15 scored forecasts
- Directional accuracy: `0.6666666666666666`
- Baseline accuracy: `0.9285714285714286`
- Model edge: `-0.261904761904762`
- Recent score: `0.4`
- Evidence grade: `D`

Interpretation: the system is correctly fail-closed. It has enough scored history to compute a baseline comparison, but current model edge is negative, so it should not emit BUY/SELL.

## Health / Repair State

- Latest explicit health-check result: `healthy`
- Health severity: `none`
- Repair required: `false`
- Repair request count: 0
- Storage repair status: `no_legacy_forecasts_found`
- Storage repair generated at: `2026-04-24T15:05:14.282895+00:00`
- Active forecast count in repair report: 35
- Latest forecast ID in repair report: `forecast:21cfb53da1d7`

The refreshed repair report aligns with the latest forecast tail and active forecast count.

## Dashboard Freshness

- Dashboard path: `paper_storage/hourly-paper-forecast/coingecko/BTC-USD/dashboard.html`
- Dashboard last modified UTC: `2026-04-24T15:05:20.989250+00:00`
- Dashboard contains generated-at context: yes
- Dashboard contains strategy decision context: yes
- Dashboard contains health/repair context: yes

Dashboard was regenerated after refreshing the repair report.

## M2 Readiness Decision

M2 may proceed.

Rationale:

- Active storage is readable.
- No bad JSON rows were detected.
- No duplicate artifact IDs were detected.
- `last_run_meta.json` aligns with the latest forecast tail.
- Health-check is healthy with no findings.
- No repair requests are pending.
- The latest strategy decision is conservative and non-tradeable because model quality does not beat baseline.
- The system remains paper-only.

## Residual Risks To Carry Into M2

- JSONL remains the canonical store until M2A; this is acceptable for M1.5 but is the main reason M2A should add a SQLite repository.
- Current decision quality is weak versus baseline; M2 should not loosen BUY/SELL gates.
- Dashboard is static HTML, so generated-at context remains important to avoid mistaking stale output for live state.

## Final Reviewer

- Reviewer subagent: `019dc007-0b73-78c2-a78b-c5788a3f1da5`
- Status: `APPROVED`
- Blocking findings: none

Reviewer notes:

- M1.5 stayed report-only.
- No M2 SQLite, paper order ledger, NAV, or risk gate implementation was added.
- The report includes the required counts, latest decision, latest health status, duplicate-ID check, bad-row check, dashboard freshness, and M2 readiness decision.
- No `.env`, `.codex/`, `paper_storage/`, runtime artifact, or secret commit risk was found.
- `paper_storage/` remains ignored by `.gitignore`.
