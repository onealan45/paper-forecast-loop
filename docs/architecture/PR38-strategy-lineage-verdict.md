# PR38 Strategy Lineage Performance Verdict

## Purpose

PR37 made every lineage paper-shadow outcome visible, but the reader still had
to manually interpret whether the revision path was improving or degrading.
PR38 adds a deterministic verdict layer so the strategy UX answers the human
question first:

> Is this self-evolving strategy path getting better, worse, stalled, or still
> missing evidence?

## Scope

PR38 adds read-only derived fields to `StrategyLineageSummary`:

- `performance_verdict`
- `improved_outcome_count`
- `worsened_outcome_count`
- `unknown_outcome_count`
- `latest_change_label`
- `latest_delta_vs_previous_excess`
- `primary_failure_attribution`
- `latest_recommended_strategy_action`

The verdict is derived only from existing lineage outcome nodes and failure
attributions. It does not mutate strategy cards, promote candidates, submit
orders, or create runtime artifacts.

## Verdict Rules

- No outcome rows, or only unknown outcome rows: `證據不足`
- Latest known row improved: `改善`
- Latest known row worsened: `惡化`
- Latest known row was flat: `持平`
- Otherwise more worsened than improved rows: `偏弱`
- Otherwise more improved than worsened rows: `偏強`
- Otherwise: `觀察中`

The primary failure focus prefers the latest outcome's first failure attribution.
If the latest outcome has no attribution, it falls back to the most frequent
lineage attribution.

## UX

Dashboard and operator console now show `表現結論` before `表現軌跡`.
The rendered line includes:

- verdict
- improvement / worsening / unknown counts
- latest change label
- latest delta
- primary failure focus
- latest recommended strategy action

This keeps the raw trajectory rows available while making the strategy state
readable without manual aggregation.

## Verification

Expected focused tests:

```powershell
python -m pytest tests\test_strategy_lineage.py tests\test_dashboard.py tests\test_operator_console.py -q
```

Expected final gates:

```powershell
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
git ls-files .codex paper_storage reports output .env
```
