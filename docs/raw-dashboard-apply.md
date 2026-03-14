# Raw Dashboard Apply Guide

This guide is for using a copy-paste workflow with Home Assistant's raw YAML editor while keeping repo files canonical.

## Generate Combined Raw YAML

From repo root:

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\"
```

Then generate combined raw output:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Optional (include hidden/admin dashboards):

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined --include-hidden
```

Generated files:
- `experiments/drafts/dashboards/raw/combined_dashboard.yaml`
- `experiments/drafts/dashboards/raw/combined_dashboard_report.md`

## Apply in Home Assistant UI

1. Open the target dashboard in Home Assistant.
2. Open the raw configuration editor.
3. Replace existing content with `combined_dashboard.yaml`.
4. Save.
5. Verify:
   - all views load
   - cards render without errors
   - entity interactions behave as expected

## Operating Rule

- Source of truth remains file-based YAML in repo.
- Raw-editor paste is a convenience apply path, not a replacement for canonical files.
