#!/usr/bin/env python3
"""Generate and sync Home Assistant dashboard YAML artifacts."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "dashboards" / "dashboards.yaml"
DEFAULT_OUTPUT = (
    REPO_ROOT / "experiments" / "drafts" / "dashboards" / "raw" / "combined_dashboard.yaml"
)
DEFAULT_REPORT = (
    REPO_ROOT
    / "experiments"
    / "drafts"
    / "dashboards"
    / "raw"
    / "combined_dashboard_report.md"
)
DEFAULT_LIVE_SNAPSHOT = (
    REPO_ROOT
    / "experiments"
    / "drafts"
    / "dashboards"
    / "live"
    / "live_states_snapshot.json"
)
DEFAULT_LIVE_REPORT = (
    REPO_ROOT / "experiments" / "drafts" / "dashboards" / "live" / "sync_live_report.md"
)
DEFAULT_CATALOG_OUTPUT = REPO_ROOT / "dashboards" / "views" / "all_entities.yaml"

ALL_ENTITIES_DASHBOARD_ID = "all_entities"
ALL_ENTITIES_DASHBOARD_TITLE = "All Entities"
ALL_ENTITIES_ICON = "mdi:format-list-bulleted"
ALL_ENTITIES_PATH = "all-entities"

CARD_RADIUS_STYLE = "ha-card { border-radius: 18px; }"

CONTROL_DOMAIN_ORDER = [
    "light",
    "switch",
    "fan",
    "climate",
    "cover",
    "lock",
    "button",
    "media_player",
    "remote",
    "vacuum",
    "input_boolean",
    "input_select",
    "input_number",
    "input_datetime",
    "number",
    "select",
    "person",
    "device_tracker",
]
SENSOR_DOMAIN_ORDER = ["binary_sensor", "sensor", "weather"]
UPDATE_DOMAIN_ORDER = ["update"]

NOISY_DOMAINS = {"event"}
NOISY_OBJECT_SUBSTRINGS = [
    "_linkquality",
    "_rssi",
    "_last_seen",
    "_last_reset",
    "_last_boot",
    "_signal_strength_dbm",
    "_packet_error",
    "_lqi",
]


class ExportError(RuntimeError):
    """Raised when dashboard export inputs are invalid."""


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ExportError(f"YAML file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    loaded = yaml.safe_load(text)
    return loaded if loaded is not None else {}


def _dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, default_flow_style=False, allow_unicode=False),
        encoding="utf-8",
    )


def _dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _git_commit_sha() -> str:
    try:
        result = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            text=True,
        )
        sha = result.strip()
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
        )
        if dirty.stdout.strip():
            return f"{sha}-dirty"
        return sha
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _collect_dashboard_entries(
    registry: dict[str, Any], include_hidden: bool
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for dashboard_id, config in registry.items():
        if not isinstance(config, dict):
            raise ExportError(f"Invalid registry entry for '{dashboard_id}': expected mapping")

        mode = config.get("mode", "yaml")
        if mode != "yaml":
            continue

        show_in_sidebar = bool(config.get("show_in_sidebar", True))
        if not include_hidden and not show_in_sidebar:
            continue

        filename = config.get("filename")
        if not isinstance(filename, str) or not filename:
            raise ExportError(f"Registry entry '{dashboard_id}' is missing a valid filename")

        selected.append(
            {
                "dashboard_id": dashboard_id,
                "title": config.get("title", dashboard_id),
                "show_in_sidebar": show_in_sidebar,
                "filename": filename,
            }
        )

    if not selected:
        raise ExportError("No dashboards matched export filters.")
    return selected


def _extract_entity_ids(node: Any) -> set[str]:
    entity_ids: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"entity", "entity_id"} and isinstance(child, str) and "." in child:
                    entity_ids.add(child)
                if key == "entities" and isinstance(child, list):
                    for item in child:
                        if isinstance(item, str) and "." in item:
                            entity_ids.add(item)
                        elif isinstance(item, dict):
                            if isinstance(item.get("entity"), str) and "." in item["entity"]:
                                entity_ids.add(item["entity"])
                            if isinstance(item.get("entity_id"), str) and "." in item["entity_id"]:
                                entity_ids.add(item["entity_id"])
                            walk(item)
                walk(child)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(node)
    return entity_ids


def _build_combined_payload(selected: list[dict[str, Any]], title: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    combined_views: list[dict[str, Any]] = []
    included: list[dict[str, Any]] = []

    for entry in selected:
        dashboard_file = _resolve_path(entry["filename"])
        dashboard_yaml = _load_yaml(dashboard_file)
        if not isinstance(dashboard_yaml, dict):
            raise ExportError(
                f"Dashboard YAML must be a mapping: {_relative(dashboard_file)}"
            )

        views = dashboard_yaml.get("views")
        if not isinstance(views, list):
            raise ExportError(
                f"Dashboard YAML has invalid or missing views list: {_relative(dashboard_file)}"
            )

        for idx, view in enumerate(views, start=1):
            if not isinstance(view, dict):
                raise ExportError(
                    f"View #{idx} in {_relative(dashboard_file)} is not a mapping"
                )
            combined_views.append(copy.deepcopy(view))

        included.append(
            {
                "dashboard_id": entry["dashboard_id"],
                "title": str(entry["title"]),
                "filename": _relative(dashboard_file),
                "view_count": len(views),
                "show_in_sidebar": entry["show_in_sidebar"],
            }
        )

    payload = {"title": title, "views": combined_views}
    return payload, included


def _write_combined_report(
    report_path: Path,
    include_hidden: bool,
    registry_path: Path,
    output_path: Path,
    included: list[dict[str, Any]],
    view_count: int,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Combined Dashboard Export Report",
        "",
        f"- Source commit: `{_git_commit_sha()}`",
        f"- Registry: `{_relative(registry_path)}`",
        f"- Output: `{_relative(output_path)}`",
        f"- Include hidden dashboards: `{str(include_hidden).lower()}`",
        f"- Dashboards included: `{len(included)}`",
        f"- Total views exported: `{view_count}`",
        "",
        "## Included Dashboards (Registry Order)",
        "",
    ]

    for index, item in enumerate(included, start=1):
        lines.append(
            f"{index}. `{item['dashboard_id']}` -> `{item['filename']}` "
            f"({item['view_count']} view(s), show_in_sidebar={item['show_in_sidebar']})"
        )

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_live_states_from_api(ha_url: str, ha_token: str) -> list[dict[str, Any]]:
    base = ha_url.rstrip("/")
    endpoint = f"{base}/api/states"
    request = urllib.request.Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise ExportError(
            f"Home Assistant API error {err.code} at {endpoint}: {body[:300]}"
        ) from err
    except urllib.error.URLError as err:
        raise ExportError(f"Could not connect to Home Assistant at {endpoint}: {err}") from err

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as err:
        raise ExportError("Home Assistant API returned invalid JSON from /api/states") from err

    if not isinstance(data, list):
        raise ExportError("Home Assistant /api/states payload was not a list")

    normalized: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or "." not in entity_id:
            continue
        normalized.append(item)

    return normalized


def _load_live_states_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ExportError(f"Live states file does not exist: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ExportError(f"States file is not valid JSON: {path}") from err

    if not isinstance(data, list):
        raise ExportError(f"States file must be a JSON list: {path}")

    normalized: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or "." not in entity_id:
            continue
        normalized.append(item)

    return normalized

def _collect_curated_entities(registry: dict[str, Any]) -> set[str]:
    curated_entities: set[str] = set()
    for dashboard_id, config in registry.items():
        if not isinstance(config, dict):
            continue
        if config.get("mode", "yaml") != "yaml":
            continue
        if dashboard_id == ALL_ENTITIES_DASHBOARD_ID:
            continue
        filename = config.get("filename")
        if not isinstance(filename, str) or not filename:
            continue
        dashboard_file = _resolve_path(filename)
        if not dashboard_file.exists():
            continue
        dashboard_yaml = _load_yaml(dashboard_file)
        if isinstance(dashboard_yaml, dict):
            curated_entities.update(_extract_entity_ids(dashboard_yaml))
    return curated_entities


def _noisy_reason(entity_id: str, state_obj: dict[str, Any]) -> str | None:
    if "." not in entity_id:
        return "invalid_entity_id"

    domain, object_id = entity_id.split(".", 1)
    if domain in NOISY_DOMAINS:
        return f"excluded_domain:{domain}"

    attributes = state_obj.get("attributes")
    if isinstance(attributes, dict):
        category = attributes.get("entity_category")
        if category in {"diagnostic", "config"}:
            return f"entity_category:{category}"

    for token in NOISY_OBJECT_SUBSTRINGS:
        if token in object_id:
            return f"name_pattern:{token}"

    return None


def _ordered_domains(domain_to_entities: dict[str, list[str]], ordered_domains: list[str]) -> list[str]:
    prioritized = [d for d in ordered_domains if d in domain_to_entities]
    remaining = sorted(d for d in domain_to_entities if d not in ordered_domains)
    return prioritized + remaining


def _entities_card(domain: str, entities: list[str]) -> dict[str, Any]:
    return {
        "type": "entities",
        "title": domain.replace("_", " ").title(),
        "entities": entities,
        "card_mod": {"style": CARD_RADIUS_STYLE},
    }


def _build_catalog_dashboard(
    included_entities: list[str],
    counts: dict[str, int],
) -> dict[str, Any]:
    domain_to_entities: dict[str, list[str]] = defaultdict(list)
    for entity_id in sorted(included_entities):
        domain = entity_id.split(".", 1)[0]
        domain_to_entities[domain].append(entity_id)

    controls = {d: domain_to_entities[d] for d in domain_to_entities if d in CONTROL_DOMAIN_ORDER}
    sensors = {d: domain_to_entities[d] for d in domain_to_entities if d in SENSOR_DOMAIN_ORDER}
    updates = {d: domain_to_entities[d] for d in domain_to_entities if d in UPDATE_DOMAIN_ORDER}
    others = {
        d: domain_to_entities[d]
        for d in domain_to_entities
        if d not in CONTROL_DOMAIN_ORDER and d not in SENSOR_DOMAIN_ORDER and d not in UPDATE_DOMAIN_ORDER
    }

    sections: list[dict[str, Any]] = [
        {
            "type": "grid",
            "cards": [
                {
                    "type": "markdown",
                    "content": (
                        "# All Entities Catalog\n"
                        f"Generated: `{_now_iso()}`\n\n"
                        f"Live total: **{counts['live_total']}**\n"
                        f"Curated: **{counts['curated_total']}**\n"
                        f"Catalog included: **{counts['catalog_included']}**\n"
                        f"Excluded noisy/internal: **{counts['excluded_total']}**"
                    ),
                    "card_mod": {"style": CARD_RADIUS_STYLE},
                }
            ],
        }
    ]

    if controls:
        cards: list[dict[str, Any]] = [{"type": "heading", "heading": "Controls"}]
        for domain in _ordered_domains(controls, CONTROL_DOMAIN_ORDER):
            cards.append(_entities_card(domain, controls[domain]))
        sections.append({"type": "grid", "cards": cards})

    if sensors:
        cards = [{"type": "heading", "heading": "Sensors"}]
        for domain in _ordered_domains(sensors, SENSOR_DOMAIN_ORDER):
            cards.append(_entities_card(domain, sensors[domain]))
        sections.append({"type": "grid", "cards": cards})

    if updates:
        cards = [{"type": "heading", "heading": "Updates & Diagnostics"}]
        for domain in _ordered_domains(updates, UPDATE_DOMAIN_ORDER):
            cards.append(_entities_card(domain, updates[domain]))
        sections.append({"type": "grid", "cards": cards})

    if others:
        cards = [{"type": "heading", "heading": "Other Entities"}]
        for domain in _ordered_domains(others, []):
            cards.append(_entities_card(domain, others[domain]))
        sections.append({"type": "grid", "cards": cards})

    if len(sections) == 1:
        sections.append(
            {
                "type": "grid",
                "cards": [
                    {
                        "type": "markdown",
                        "content": "No missing entities found after exclusions.",
                        "card_mod": {"style": CARD_RADIUS_STYLE},
                    }
                ],
            }
        )

    view = {
        "type": "sections",
        "title": ALL_ENTITIES_DASHBOARD_TITLE,
        "sub_title": "Complete live entity catalog",
        "path": ALL_ENTITIES_PATH,
        "icon": ALL_ENTITIES_ICON,
        "max_columns": 3,
        "sections": sections,
    }

    return {
        "title": ALL_ENTITIES_DASHBOARD_TITLE,
        "views": [view],
    }


def _ensure_all_entities_registry_entry(registry_path: Path, registry: dict[str, Any], catalog_output: Path) -> None:
    original = copy.deepcopy(registry)
    relative_catalog = _relative(catalog_output)
    existing = registry.get(ALL_ENTITIES_DASHBOARD_ID)
    if not isinstance(existing, dict):
        existing = {}
    existing.update(
        {
            "mode": "yaml",
            "title": ALL_ENTITIES_DASHBOARD_TITLE,
            "icon": ALL_ENTITIES_ICON,
            "show_in_sidebar": True,
            "filename": relative_catalog,
        }
    )
    registry[ALL_ENTITIES_DASHBOARD_ID] = existing
    if registry != original:
        _dump_yaml(registry_path, registry)


def _write_sync_report(
    report_path: Path,
    source: str,
    snapshot_path: Path,
    registry_path: Path,
    catalog_output: Path,
    counts: dict[str, int],
    included_entities: list[str],
    exclusions: dict[str, list[str]],
) -> None:
    lines = [
        "# Live Entity Sync Report",
        "",
        f"- Source commit: `{_git_commit_sha()}`",
        f"- Synced at: `{_now_iso()}`",
        f"- Live source: `{source}`",
        f"- Snapshot: `{_relative(snapshot_path)}`",
        f"- Registry: `{_relative(registry_path)}`",
        f"- Catalog output: `{_relative(catalog_output)}`",
        "- Curated auto-generation: `disabled`",
        "",
        "## Counts",
        "",
        f"- Live entities: **{counts['live_total']}**",
        f"- Curated entities: **{counts['curated_total']}**",
        f"- Missing before exclusion: **{counts['missing_total']}**",
        f"- Added to catalog: **{counts['catalog_included']}**",
        f"- Excluded noisy/internal: **{counts['excluded_total']}**",
    ]

    lines.extend(
        [
            "",
            "## Included Domains",
            "",
        ]
    )

    domain_counts: dict[str, int] = defaultdict(int)
    for entity_id in included_entities:
        domain_counts[entity_id.split(".", 1)[0]] += 1
    if domain_counts:
        for domain, count in sorted(domain_counts.items()):
            lines.append(f"- `{domain}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Exclusions by Reason", ""])
    if exclusions:
        for reason, entities in sorted(exclusions.items()):
            lines.append(f"- `{reason}`: {len(entities)}")
    else:
        lines.append("- none")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def generate_combined(args: argparse.Namespace) -> int:
    if args.raw_export != "combined":
        raise ExportError("Only '--raw-export combined' is supported.")

    registry_path = _resolve_path(args.registry)
    output_path = _resolve_path(args.output)
    report_path = _resolve_path(args.report)

    registry_yaml = _load_yaml(registry_path)
    if not isinstance(registry_yaml, dict):
        raise ExportError("Dashboard registry must be a YAML mapping.")

    selected = _collect_dashboard_entries(registry_yaml, args.include_hidden)
    payload, included = _build_combined_payload(selected, args.title)
    _dump_yaml(output_path, payload)
    _write_combined_report(
        report_path=report_path,
        include_hidden=args.include_hidden,
        registry_path=registry_path,
        output_path=output_path,
        included=included,
        view_count=len(payload["views"]),
    )

    print(f"Exported combined dashboard to {_relative(output_path)}")
    print(f"Wrote report to {_relative(report_path)}")
    return 0


def sync_live(args: argparse.Namespace) -> int:
    registry_path = _resolve_path(args.registry)
    snapshot_path = _resolve_path(args.snapshot)
    report_path = _resolve_path(args.report)
    catalog_output = _resolve_path(args.catalog_output)

    registry_yaml = _load_yaml(registry_path)
    if not isinstance(registry_yaml, dict):
        raise ExportError("Dashboard registry must be a YAML mapping.")

    states_source = ""
    if args.states_file:
        states_file = _resolve_path(args.states_file)
        live_states = _load_live_states_from_file(states_file)
        states_source = f"file:{_relative(states_file)}"
    else:
        ha_url = args.ha_url or os.environ.get("HA_URL")
        ha_token = args.ha_token or os.environ.get("HA_TOKEN")
        if not ha_url or not ha_token:
            raise ExportError(
                "Missing Home Assistant credentials. Provide --ha-url/--ha-token or HA_URL/HA_TOKEN env vars."
            )
        live_states = _fetch_live_states_from_api(ha_url, ha_token)
        states_source = "api:/api/states"

    live_map: dict[str, dict[str, Any]] = {}
    for item in live_states:
        entity_id = item.get("entity_id")
        if isinstance(entity_id, str) and "." in entity_id:
            live_map[entity_id] = item

    live_entities = set(live_map)
    curated_entities = _collect_curated_entities(registry_yaml)
    missing_entities = sorted(live_entities - curated_entities)

    included_entities: list[str] = []
    exclusions: dict[str, list[str]] = defaultdict(list)

    for entity_id in missing_entities:
        reason = None
        if not args.include_noisy:
            reason = _noisy_reason(entity_id, live_map.get(entity_id, {}))
        if reason:
            exclusions[reason].append(entity_id)
            continue
        included_entities.append(entity_id)

    counts = {
        "live_total": len(live_entities),
        "curated_total": len(curated_entities),
        "missing_total": len(missing_entities),
        "catalog_included": len(included_entities),
        "excluded_total": sum(len(v) for v in exclusions.values()),
    }

    catalog_payload = _build_catalog_dashboard(included_entities, counts)

    if args.dry_run:
        print("Dry run summary:")
        print(json.dumps(counts, indent=2, sort_keys=True))
        return 0

    _dump_json(snapshot_path, live_states)
    _dump_yaml(catalog_output, catalog_payload)
    _ensure_all_entities_registry_entry(registry_path, registry_yaml, catalog_output)
    _write_sync_report(
        report_path=report_path,
        source=states_source,
        snapshot_path=snapshot_path,
        registry_path=registry_path,
        catalog_output=catalog_output,
        counts=counts,
        included_entities=included_entities,
        exclusions=exclusions,
    )

    print(f"Wrote live snapshot to {_relative(snapshot_path)}")
    print(f"Wrote catalog dashboard to {_relative(catalog_output)}")
    print(f"Wrote sync report to {_relative(report_path)}")
    print(json.dumps(counts, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dashboard export and live sync utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser(
        "generate", help="Generate dashboard export artifacts."
    )
    generate_parser.add_argument(
        "--raw-export",
        required=True,
        choices=["combined"],
        help="Type of raw export to generate.",
    )
    generate_parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include dashboards where show_in_sidebar is false.",
    )
    generate_parser.add_argument(
        "--title",
        default="Combined Dashboard",
        help="Top-level dashboard title for raw export output.",
    )
    generate_parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY.relative_to(REPO_ROOT)),
        help="Path to dashboard registry YAML.",
    )
    generate_parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT.relative_to(REPO_ROOT)),
        help="Path to output combined dashboard YAML.",
    )
    generate_parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT.relative_to(REPO_ROOT)),
        help="Path to export traceability report.",
    )
    generate_parser.set_defaults(func=generate_combined)

    sync_parser = subparsers.add_parser(
        "sync-live", help="Sync live Home Assistant entities into an All Entities catalog view."
    )
    sync_parser.add_argument(
        "--ha-url",
        default=None,
        help="Home Assistant base URL (fallback: HA_URL env var).",
    )
    sync_parser.add_argument(
        "--ha-token",
        default=None,
        help="Home Assistant long-lived access token (fallback: HA_TOKEN env var).",
    )
    sync_parser.add_argument(
        "--states-file",
        default=None,
        help="Optional JSON file of /api/states payload for offline runs.",
    )
    sync_parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY.relative_to(REPO_ROOT)),
        help="Path to dashboard registry YAML.",
    )
    sync_parser.add_argument(
        "--catalog-output",
        default=str(DEFAULT_CATALOG_OUTPUT.relative_to(REPO_ROOT)),
        help="Path to generated All Entities dashboard YAML.",
    )
    sync_parser.add_argument(
        "--snapshot",
        default=str(DEFAULT_LIVE_SNAPSHOT.relative_to(REPO_ROOT)),
        help="Path to write fetched live states snapshot JSON.",
    )
    sync_parser.add_argument(
        "--report",
        default=str(DEFAULT_LIVE_REPORT.relative_to(REPO_ROOT)),
        help="Path to write sync report markdown.",
    )
    sync_parser.add_argument(
        "--include-noisy",
        action="store_true",
        help="Include entities normally excluded as noisy/internal.",
    )
    sync_parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Compatibility flag. Curated auto-generation is disabled and sync-live updates the catalog only.",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute counts without writing files.",
    )
    sync_parser.set_defaults(func=sync_live)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ExportError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
