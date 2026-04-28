# Controller Decision Template

Use this template when ChatGPT Pro Controller or the local controller changes
direction, approves a milestone, records a repair path, or defines a new
research objective.

```yaml
controller_decision_id: controller-decision:YYYY-MM-DD-short-topic
created_at: 2026-04-29T00:00:00+08:00
decision_type: roadmap | architecture | repair | merge | research_direction
scope: repo, milestone, PR, module, artifact family, or runbook
decision: concise Traditional Chinese statement of the decision
rationale:
  - why this improves research, prediction, backtesting, simulation, or governance
  - why this does not weaken locked evaluation gates
allowed_worker_roles:
  - controller
  - feature
  - verifier
  - reviewer
  - docs
blocked_actions:
  - real order submission
  - real capital movement
  - committed secrets
  - weakening evaluation gates after seeing results
affected_files:
  - docs/architecture/example.md
  - src/forecast_loop/example.py
acceptance_summary:
  - implementation matches documented scope
  - machine gates pass
  - reviewer subagent returns APPROVED
machine_gates:
  - python -m pytest -q
  - python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
  - python .\run_forecast_loop.py --help
  - git diff --check
runtime_exclusions:
  - .codex/
  - paper_storage/
  - reports/
  - output/
  - .env
review_archive: docs/reviews/YYYY-MM-DD-topic-review.md
```

## Usage Rules

- Write the decision before implementation when it changes direction or scope.
- Keep the decision concrete enough for a reviewer subagent to evaluate.
- Do not use the template to claim features that are not implemented.
- Do not turn this template into a fake controller runtime service.
- If a browser is needed for UX validation, use Edge.
