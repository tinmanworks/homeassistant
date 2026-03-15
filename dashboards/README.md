# Dashboards

Production Lovelace dashboards are YAML-managed here.

- `dashboards.yaml` is the only dashboard registry file.
- `views/` holds general user-facing dashboards.
- `rooms/` holds room-focused dashboards.
- `admin/` holds operational/admin dashboards.

Draft or unvalidated dashboards belong in `experiments/drafts/dashboards/` until validated.

## Live Entity Sync

Populate/update `views/all_entities.yaml` from live Home Assistant entities:

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\"
```

This command computes missing entities (`live - curated`), updates `views/all_entities.yaml`,
and leaves curated dashboards unchanged.

Compatibility mode:

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\" --catalog-only
```

## Raw YAML Export (Copy-Paste Friendly)

Use canonical dashboard files in this directory as source, then generate one combined raw YAML:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Output:
- `experiments/drafts/dashboards/raw/combined_dashboard.yaml`
- `experiments/drafts/dashboards/raw/combined_dashboard_report.md`

By default, only dashboards with `show_in_sidebar: true` are included.
Use `--include-hidden` to include admin/hidden dashboards.
