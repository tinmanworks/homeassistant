# Dashboard Promotion Plan

Date: 2026-03-14

This plan defines how to safely promote cards and entities from archived draft dashboards into stable YAML dashboards.

## Source of Truth for Drafts

- `experiments/drafts/dashboards/2026-03-14_hacs_dashboard.yaml`
- `experiments/drafts/dashboards/2026-03-14_native_dashboard.yaml`

## Target Production Files

- `dashboards/views/home.yaml`
- `dashboards/views/energy.yaml`
- `dashboards/views/system.yaml`
- `dashboards/rooms/workspace.yaml`
- `dashboards/rooms/lounge.yaml`
- `dashboards/admin/updates.yaml`
- `dashboards/admin/backups.yaml`

## Promotion Sequence

1. Create branch `feature/dashboard-promotion-phase-1` from `master` after foundation branch merge.
2. Promote low-risk native cards first (core card types, no custom resources).
3. Validate in test HA instance and run config check.
4. Merge Phase 1 PR into `master`.
5. Create branch `feature/dashboard-promotion-phase-2` for HACS-dependent cards.
6. Confirm required resources/integrations are available in test instance.
7. Validate entity IDs and popup actions (`browser_mod`, custom cards).
8. Merge Phase 2 PR only after runtime validation passes.

## Gating Rules

A dashboard change is promotable only if all checks pass:

- `ha core check` (or equivalent) passes
- Dashboard file loads with no missing YAML include paths
- Referenced entities exist in test environment
- No runtime-only/generated files appear in git diff
- Reviewer verifies no experimental placeholders remain

## Validation Checklist per Dashboard

For each target dashboard file:

1. Open dashboard in test HA instance
2. Confirm cards render without errors
3. Confirm entity interactions behave as expected
4. Confirm hold/tap actions are safe and intentional
5. Capture notes for any skipped entities/integrations

## Handling HACS and Advanced UI Features

- Keep custom card usage isolated and clearly commented in YAML.
- If a custom card is unavailable in test instance, keep that section in `experiments/drafts/dashboards/`.
- Do not block stable promotion of native-card sections due to optional custom-card sections.

## Rollback Approach

- Revert only the affected dashboard file in a `fix/dashboard-rollback-<area>` branch.
- Keep failed section in `experiments/drafts/dashboards/` with notes.
