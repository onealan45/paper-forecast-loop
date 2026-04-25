# Secrets Management

## Current Boundary

The project is paper-only. M6B prepares safe configuration conventions but does
not implement external broker connectivity, notification delivery, sandbox
submission, or live trading.

## Rules

- Do not commit `.env`.
- Do not commit real API keys, API secrets, tokens, webhook URLs, private keys,
  or account identifiers.
- Use `.env.example` for variable names only.
- Use `config/brokers.example.yml` for non-secret broker mode examples only.
- Store future local secrets outside git.
- Do not print secret values in CLI output, dashboard HTML, operator console
  HTML, repair requests, logs, or notification artifacts.
- Do not include secrets in Codex repair request prompts.

## Ignored Files

The repo ignores:

- `.env`
- `.env.*`
- `.codex/`
- `paper_storage/`
- runtime output directories

`.env.example` is intentionally allowed because it contains blank placeholders
only.

## Health Check

M6B health-check scans repository safety files and storage artifacts for obvious
secret-looking assignments. If a finding is detected, health-check reports a
blocking `secret_leak_detected` finding and repair is required.

The scanner is intentionally conservative. It is not a complete security audit,
but it catches common mistakes before runtime artifacts or docs are trusted.

## Future Sandbox/Paper Integrations

Future milestones may use `EXTERNAL_PAPER` or `SANDBOX` modes. Those milestones
must keep secrets in local environment variables or a local secret store, never
in source or committed config files.

Live trading remains out of scope.
