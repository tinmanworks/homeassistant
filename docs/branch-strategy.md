# Branch Strategy

## Branch Roles

- `master`: stable, validated production-ready state only.
- `feature/<area>-<change>`: planned improvements and refactors.
- `fix/<area>-<issue>`: targeted production fixes.
- `experiment/<area>-<idea>`: drafts, UI explorations, risky changes.

## Merge Policy

- Never merge `experiment/*` directly into `master`.
- Promote experiment output by creating a `feature/*` branch and cherry-picking/curating validated files.
- Require PR review and validation checklist completion before merging to `master`.

## Protected Stable Expectations

Configure branch protection on the remote for `master`:
- pull-request-only merges
- no force pushes
- required status checks
- optional: require linear history
