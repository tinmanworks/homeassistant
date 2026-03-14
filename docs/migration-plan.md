# Migration Plan

Date: 2026-03-14

## 1. Snapshot and Preserve

- Archive tags created:
  - `archive-native-ha-dashboard-2026-03-14`
  - `archive-hacs-integrated-ha-dashboard-2026-03-14`
- Draft dashboard snapshots copied to:
  - `experiments/drafts/dashboards/`
- Frozen historical dashboard snapshots copied to:
  - `archive/legacy/configs/`

## 2. Scaffold Foundation

- Repository reorganized into modular directories for dashboards, automations, scripts, scenes, helpers, templates, packages, themes, blueprints, AI, custom components, AppDaemon, Python, docs, archive, and experiments.
- `configuration.yaml` now uses include-based modular loading.

## 3. Stabilize Dashboards

- YAML dashboard registry defined in `dashboards/dashboards.yaml`.
- Minimal production-safe dashboards created under `dashboards/views/`, `dashboards/rooms/`, and `dashboards/admin/`.
- Existing HACS-heavy dashboards remain drafts until validated.

## 4. Validate and Promote

- Run config checks in a non-stable environment.
- Validate dashboard rendering and entity references.
- Promote validated draft files through `feature/*` PRs only.

## 5. Cleanup Completion

- Keep historical branch refs temporarily.
- Delete obsolete legacy branch names only after confirmation and migration completion.
