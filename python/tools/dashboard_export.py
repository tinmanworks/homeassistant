#!/usr/bin/env python3
"""Generate raw-editor dashboard YAML from canonical dashboard files."""

from __future__ import annotations

import argparse
import copy
import subprocess
import sys
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


def _write_report(
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
    _write_report(
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dashboard export utilities for raw YAML editor workflows.",
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
