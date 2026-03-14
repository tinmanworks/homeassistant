# Testing Playbook

## Pre-PR Validation

1. Configuration check
- Run `ha core check` (or equivalent `check_config`) in your environment.
- Resolve all errors before opening a PR.

2. Dashboard verification
- Confirm each file registered in `dashboards/dashboards.yaml` exists and loads.
- Verify no missing card/resource references.

3. Functional smoke testing
- Trigger key automations/scripts/scenes in a non-stable HA instance.
- Confirm expected state changes and no runtime errors.

4. Secret hygiene
- Ensure no secrets/runtime artifacts are included in git diff.

## Merge Gate for `master`

- PR reviewed
- validation checklist complete
- no experimental/draft-only files promoted without evidence of validation
