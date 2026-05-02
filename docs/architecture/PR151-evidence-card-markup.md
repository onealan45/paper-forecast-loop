# PR151 Evidence Card Markup

## Context

PR150 made digest evidence metrics visible as structured sections. The active
dashboard refresh then showed an HTML escaping issue in the dashboard evidence
metric list: artifact ids appeared as literal `&lt;code&gt;...&lt;/code&gt;`
text instead of styled ids.

## Decision

Render digest evidence metrics with dedicated HTML list markup instead of
passing preformatted metric strings through generic escaping list helpers.

This keeps:

- metric labels readable;
- artifact ids styled with real `<code>` elements;
- flags escaped as text;
- the UI read-only.

## Non-Goals

- No artifact schema change.
- No strategy gate change.
- No new metric computation.
