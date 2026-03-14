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

## Repository Layout

- `dashboards/`: YAML-managed production dashboards and view files.
- `automations/`, `scripts/`, `scenes/`, `helpers/`, `templates/`, `packages/`: modular HA config.
- `themes/`, `blueprints/`, `custom_components/`: UI and extensibility.
- `ai/`: AI prompts/config related to HA operations.
- `appdaemon/`, `python/`: custom code and supporting tools.
- `docs/`: governance, testing, naming, and migration guidance.
- `archive/legacy/`: preserved historical content.
- `experiments/`: drafts not ready for stable.
