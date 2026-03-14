# UI vs YAML Policy

## Stable Branch Policy

YAML in this repository is the source of truth for production.

## UI-Managed Work

UI editing is allowed for prototyping only in:
- non-stable HA instances
- `experiment/*` branches after exporting config snapshots

## Promotion Rule

No UI-only config reaches `master`.

Required promotion path:
1. export or rewrite UI changes as YAML
2. place files in production structure
3. validate in test environment
4. merge through PR into `master`
