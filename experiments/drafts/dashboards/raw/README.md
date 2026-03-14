# Raw Dashboard Exports

Generated artifacts for quick copy-paste into Home Assistant's raw YAML dashboard editor.

Primary output:
- `combined_dashboard.yaml`
- `combined_dashboard_report.md`

Generate on demand:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Include hidden/admin dashboards:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined --include-hidden
```
