#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Set

SEVERITY_ORDER = {
    "critical": 5,
    "high": 4,
    "moderate": 3,
    "medium": 3,
    "low": 2,
    "info": 1,
}

SEVERITY_BADGES = {
    "critical": "🔴 Critical",
    "high": "🟠 High",
    "moderate": "🟡 Moderate",
    "medium": "🟡 Medium",
    "low": "🔵 Low",
    "info": "⚪️ Info",
}


def sanitize(value: Any) -> str:
    """Convert value to string and escape pipe characters for Markdown tables."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|")


def load_vulnerable_changes(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("vulnerable_changes", [])


def severity_rank(value: str | None) -> int:
    if not value:
        return 0
    return SEVERITY_ORDER.get(value.lower(), 0)


def severity_badge(value: str | None) -> str:
    if not value:
        return "⚪️ Unknown"
    key = value.lower()
    label = SEVERITY_BADGES.get(key)
    if label:
        return label
    return f"⚪️ {value.title()}"


def group_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}

    for entry in entries:
        package = entry.get("package") or entry.get("package_id") or "(unknown)"
        key = package.lower()
        group = grouped.setdefault(
            key,
            {
                "package": package,
                "versions": set(),  # type: Set[str]
                "ecosystem": entry.get("ecosystem") or "(unknown)",
                "vulns": [],
            },
        )

        version = entry.get("version") or "(unknown)"
        group["versions"].add(version)

        if entry.get("ecosystem"):
            group["ecosystem"] = entry.get("ecosystem")

        group["vulns"].append(
            {
                "id": entry.get("vuln_id") or "(unknown)",
                "severity": entry.get("severity"),
            }
        )

    rows: List[Dict[str, Any]] = []

    for data in grouped.values():
        vulns = sorted(
            data["vulns"],
            key=lambda vuln: (-severity_rank(vuln.get("severity")), vuln.get("id", "")),
        )
        versions = sorted(data["versions"])
        rows.append(
            {
                "package": data["package"],
                "versions": versions,
                "ecosystem": data.get("ecosystem") or "(unknown)",
                "vulns": vulns,
            }
        )

    rows.sort(key=lambda row: row["package"].lower())
    return rows


def to_markdown(entries: List[Dict[str, Any]]) -> List[str]:
    if not entries:
        return ["> No vulnerable changes detected."]

    lines = [
        "| Package | Versions | Ecosystem | Vulnerabilities |",
        "| --- | --- | --- | --- |",
    ]

    for row in group_entries(entries):
        vuln_cell = "<br>".join(
            f"{severity_badge(vuln.get('severity'))} `{vuln.get('id')}`"
            for vuln in row["vulns"]
        )
        versions = ", ".join(row["versions"]) if row["versions"] else "(unknown)"
        lines.append(
            "| {package} | {versions} | {ecosystem} | {vulns} |".format(
                package=sanitize(row["package"]),
                versions=sanitize(versions),
                ecosystem=sanitize(row["ecosystem"]),
                vulns=sanitize(vuln_cell) if vuln_cell else "(unknown)",
            )
        )

    return lines


def write_output(lines: List[str], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Grype vulnerable-changes JSON into Markdown table."
    )
    parser.add_argument("--input", required=True, help="Path to vuln-changes JSON")
    parser.add_argument("--output", required=True, help="Destination Markdown file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    entries = load_vulnerable_changes(input_path)
    markdown_lines = to_markdown(entries)
    write_output(markdown_lines, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

