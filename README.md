# Home Assistant Repository (Stable-First)

This repository is organized for safe, scalable Home Assistant development with `master` as the only stable branch.

## Architecture

- Stable production config is YAML-first and lives in structured folders.
- Experimental/unvalidated work lives under `experiments/` and `experiment/*` branches.
- Historical or unclear content is preserved under `archive/legacy/`.
- Dashboard registration is centralized in `dashboards/dashboards.yaml`.

## Branch Workflow

- Stable: `master`
- Feature work: `feature/<area>-<change>`
- Bug fixes: `fix/<area>-<issue>`
- Draft/risky work: `experiment/<area>-<idea>`

Rules:
- Never commit experimental work directly to `master`.
- `experiment/*` branches do not merge directly into `master`.
- Promote validated changes from `experiment/*` into `feature/*` via curated PRs.

See `docs/branch-strategy.md` and `docs/migration-plan.md`.

## Quickstart

1. Create a branch from `master`:
   - `git checkout master`
   - `git pull`
   - `git checkout -b feature/<area>-<change>`
2. Edit YAML under production folders (`dashboards/`, `automations/`, `packages/`, etc).
3. Validate safely:
   - `ha core check` (or `check_config` equivalent in your environment)
   - Use a non-stable HA instance for runtime testing.
4. Open PR to `master` after checks pass.

## Raw YAML Editor Workflow

Canonical dashboard source stays file-based in this repo, but you can generate a single copy-paste payload for Home Assistant's raw YAML editor:

```bash
export HA_URL=\"http://homeassistant.local:8123\"
export HA_TOKEN=\"<LONG_LIVED_TOKEN>\"
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\"
```

This sync updates `dashboards/views/all_entities.yaml` with missing live entities not already in curated views.

Then regenerate combined copy-paste YAML:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Optional (include hidden/admin dashboards):

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined --include-hidden
```

See `docs/raw-dashboard-apply.md` for apply steps.

## Repository Layout

- `dashboards/`: YAML-managed production dashboards and view files.
- `automations/`, `scripts/`, `scenes/`, `helpers/`, `templates/`, `packages/`: modular HA config.
- `themes/`, `blueprints/`, `custom_components/`: UI and extensibility.
- `ai/`: AI prompts/config related to HA operations.
- `appdaemon/`, `python/`: custom code and supporting tools.
- `docs/`: governance, testing, naming, and migration guidance.
- `archive/legacy/`: preserved historical content.
- `experiments/`: drafts not ready for stable.
