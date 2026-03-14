# Python

Custom Python tooling and shared code used by this HA repo.

- `tools/` for operational scripts
- `libs/` for reusable modules

## Dashboard Raw Export

Generate a single copy-paste dashboard YAML from canonical split dashboard files:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined
```

Include admin/hidden dashboards as well:

```bash
python3 python/tools/dashboard_export.py generate --raw-export combined --include-hidden
```
