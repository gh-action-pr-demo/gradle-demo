#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def sanitize(value: Any) -> str:
    """Convert value to string and escape pipe characters for Markdown tables."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|")


def load_vulnerable_changes(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("vulnerable_changes", [])


def to_markdown(entries: List[Dict[str, Any]]) -> List[str]:
    if not entries:
        return ["> No vulnerable changes detected."]

    lines = [
        "| Package | Version | Ecosystem | Vulnerability | Severity |",
        "| --- | --- | --- | --- | --- |",
    ]

    for entry in entries:
        lines.append(
            "| {package} | {version} | {ecosystem} | {vuln_id} | {severity} |".format(
                package=sanitize(entry.get("package") or "(unknown)"),
                version=sanitize(entry.get("version") or "(unknown)"),
                ecosystem=sanitize(entry.get("ecosystem") or "(unknown)"),
                vuln_id=sanitize(entry.get("vuln_id") or "(unknown)"),
                severity=sanitize(entry.get("severity") or "(unknown)"),
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

