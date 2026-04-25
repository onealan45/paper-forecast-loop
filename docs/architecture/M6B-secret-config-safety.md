# M6B Secret / Config Safety

## Scope

M6B prepares safe local configuration conventions and obvious secret leakage
detection.

It does not add:

- external broker connectivity
- sandbox/testnet submission
- notification delivery
- API key loading
- secret storage
- live trading

## Files

M6B adds:

- `.env.example`
- `config/brokers.example.yml`
- `docs/secrets-management.md`

`.env` and `.env.*` are ignored by git. `.env.example` remains tracked because
it contains blank placeholders only.

## Health Check

`health-check` scans:

- `.env`
- `.env.example`
- `config/brokers.example.yml`
- selected storage artifacts that could accidentally contain runtime output or
  repair/notification text

If it finds an obvious secret-looking assignment, it emits blocking
`secret_leak_detected` and marks repair required.

The finding does not echo the detected value.

## Scanner Limits

The scanner is intentionally simple. It detects common assignment-like leaks
such as:

- API keys
- API secrets
- tokens
- webhook URLs
- private keys

It is not a complete credential scanner. Before any future external sandbox or
paper broker adapter is implemented, M6C+ should keep this check and add
provider-specific validation as needed.

## Safety Boundary

M6B keeps the project paper-only. It adds no live trading path, no external API
calls, no broker submit path, and no secret handling beyond blank examples and
leak detection.
