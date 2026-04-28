# M7B Source Registry And Source Document Import Review

**日期：** 2026-04-28
**Branch：** `codex/m7b-source-registry-import`
**Reviewer：** independent reviewer subagent `019dd4b2-1cf0-7090-ac7a-40067944ff4f`
**Scope：** M7B source registry, fixture source document import, health/storage/CLI/docs

## Verdict

**APPROVED**

## Initial Finding

### P1 - Fixture payload could override registry authority

The reviewer found that the importer initially allowed a fixture row to override
registry-authoritative metadata:

- `source_name`
- `source_type`
- `source_reliability_score`
- `license_note`

That would have allowed a row imported under `source_id=sample_news` to claim it
was an official or high-reliability source, weakening the M7B source registry
contract that later M7C reliability gates depend on.

## Resolution

`src/forecast_loop/source_documents.py` now always uses `SourceRegistryEntry`
for registry-authoritative fields:

- `source_name`
- `source_type`
- `source_reliability_score`
- `license_note`

Payload rows cannot override those fields.

Regression coverage was added:

- `test_import_source_documents_registry_metadata_is_authoritative`

## Reviewer Follow-Up

Reviewer confirmed the P1 was resolved and returned `APPROVED`.

Reviewer reran:

```powershell
python -m pytest tests\test_source_registry.py tests\test_source_document_import.py -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
git diff --check
```

Results:

- source registry/import tests: `7 passed`
- compileall: passed
- `git diff --check`: passed with Windows LF/CRLF warnings only

## Implementation Verification

Implementation verification:

```powershell
python -m pytest tests\test_source_registry.py tests\test_source_document_import.py -q
python -m pytest -q
python -m compileall -q src tests run_forecast_loop.py sitecustomize.py
python .\run_forecast_loop.py --help
git diff --check
```

Results:

- M7B tests: `7 passed`
- full test suite: `228 passed`
- compileall: passed
- CLI help: passed and included `import-source-documents` / `source-registry`
- `git diff --check`: passed with Windows LF/CRLF warnings only

Fixture smoke:

```powershell
python .\run_forecast_loop.py import-source-documents --storage-dir <temp> --input .\fixtures\source_documents\sample_news.jsonl --source sample_news --imported-at 2026-04-28T10:05:00+00:00
python .\run_forecast_loop.py source-registry --storage-dir <temp> --format json
```

Result: passed and produced `source_registry.jsonl`, `source_documents.jsonl`,
and `source_ingestion_runs.jsonl` in the temporary storage directory.

## Scope Check

Reviewer confirmed:

- no live fetch was added;
- no paid provider dependency was added;
- no secret handling path was added;
- no broker or live order path was added;
- M7C-M7F event reliability, market reaction, historical edge, and decision
  integration were not implemented in this PR.
