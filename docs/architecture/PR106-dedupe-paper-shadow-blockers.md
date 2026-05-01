# PR106 Dedupe Paper-Shadow Blockers

## Purpose

Active BTC-USD storage exposed duplicated blocker codes in paper-shadow outcome
artifacts. The duplicates came from overlapping sources:

- leaderboard-entry blockers;
- locked-evaluation blockers;
- link-integrity blockers.

Those sources are all useful, but the same machine code can appear in more than
one source. If the merged list is stored or counted as-is, strategy lineage
summaries overstate repeated failure concentration and make the next research
focus noisier than the evidence supports.

## Decision

Paper-shadow outcome recording now preserves first-seen blocker order while
deduplicating the merged blocker list before it is persisted.

Strategy lineage summaries also defensively deduplicate failure references when
falling back from `failure_attributions` to `blocked_reasons`. This keeps older
runtime artifacts readable without requiring a storage rewrite.

## Non-Goals

- Do not rewrite existing `paper_shadow_outcomes.jsonl` runtime artifacts.
- Do not weaken any leaderboard, locked-evaluation, link-integrity, or
  paper-shadow gate.
- Do not collapse semantically different blocker codes.
- Do not change artifact schemas.

## Verification

Regression coverage proves:

- overlapping leaderboard/evaluation/link blockers are persisted only once per
  blocker code;
- lineage summaries read older duplicated `blocked_reasons` defensively and
  count each blocker only once per outcome fallback.
