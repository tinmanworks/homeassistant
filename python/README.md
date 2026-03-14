# Python

Custom Python tooling and shared code used by this HA repo.

- `tools/` for operational scripts
- `libs/` for reusable modules

## Dashboard Raw Export

Sync current Home Assistant entities and refresh the All Entities catalog:

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\"
```

Catalog-only mode (no curated auto-section updates):

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\" --catalog-only
```

Offline mode from a saved states payload:

```bash
python3 python/tools/dashboard_export.py sync-live --states-file experiments/drafts/dashboards/live/live_states_snapshot.json
```

Dry run (no file writes):

```bash
python3 python/tools/dashboard_export.py sync-live --ha-url \"$HA_URL\" --ha-token \"$HA_TOKEN\" --dry-run
```

Generate a single copy-paste dashboard YAML from canonical split dashboard files:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Include admin/hidden dashboards as well:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined --include-hidden
```
