#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Set

SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "moderate": 2,
    "medium": 2,
    "low": 1,
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def severity_rank(value: str) -> int:
    if not value:
        return 0
    return SEVERITY_ORDER.get(value.lower(), 0)


def meets_severity(entry: dict, min_severity: str) -> bool:
    return severity_rank(entry.get("severity")) >= severity_rank(min_severity)


def load_allowlist(path: Path | None, debug: bool = False) -> Set[str]:
    entries: Set[str] = set()
    if not path:
        return entries

    if not path.exists():
        if debug:
            print(f"[filter-allowlist] Allowlist file not found: {path}", file=sys.stderr)
        return entries

    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            normalized = line.lower()
            parts = [p for p in normalized.split(":") if p]

            entries.add(normalized)
            if parts:
                # add last token (artifact/package) for loose matching
                entries.add(parts[-1])
                # add last two tokens (e.g., group:artifact)
                if len(parts) >= 2:
                    entries.add(f"{parts[-2]}:{parts[-1]}")

    if debug:
        preview = ", ".join(sorted(list(entries))[:20])
        print(
            f"[filter-allowlist] Loaded {len(entries)} allowlist entries from {path}: {preview}",
            file=sys.stderr,
        )
    return entries


def candidate_keys(entry: dict) -> Set[str]:
    keys: Set[str] = set()

    def add(value: str | None):
        if value:
            keys.add(value.lower())

    pkg = entry.get("package")
    pkg_id = entry.get("package_id")
    ecosystem = entry.get("ecosystem")
    group = entry.get("group")
    artifact = entry.get("artifact") or entry.get("package")

    add(pkg)
    add(pkg_id)
    add(artifact)

    if ecosystem:
        add(f"{ecosystem}:{pkg}" if pkg else None)
        add(f"{ecosystem}:{pkg_id}" if pkg_id else None)
        add(f"{ecosystem}:{artifact}" if artifact else None)

    if group and artifact:
        add(f"{group}:{artifact}")
        if ecosystem:
            add(f"{ecosystem}:{group}:{artifact}")

    return keys


def log_debug(enabled: bool, message: str):
    if enabled:
        print(f"[filter-allowlist] {message}", file=sys.stderr)


def filter_entries(
    entries: Iterable[dict],
    allowlist: Set[str],
    min_severity: str,
    debug: bool = False,
) -> List[dict]:
    allowlist_active = len(allowlist) > 0
    filtered: List[dict] = []
    inspected = 0

    for entry in entries:
        inspected += 1
        package_name = entry.get("package_id") or entry.get("package") or "unknown"
        severity = entry.get("severity")

        if allowlist_active:
            entry_keys = candidate_keys(entry)
            match = any(key in allowlist for key in entry_keys)
            log_debug(
                debug,
                f"Evaluate {package_name}: severity={severity}, keys={list(entry_keys)}, matched={match}",
            )
            if not match:
                continue
        else:
            if not meets_severity(entry, min_severity):
                log_debug(
                    debug,
                    f"Skip {package_name}: severity {severity} < min {min_severity}",
                )
                continue

        filtered.append(entry)

    log_debug(
        debug,
        f"Entries inspected={inspected}, filtered={len(filtered)}, allowlist_active={allowlist_active}",
    )
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter Grype vulnerable changes via allowlist + severity.")
    parser.add_argument("--input", required=True, help="Path to vuln-changes JSON")
    parser.add_argument("--output", required=True, help="Destination JSON with filtered results")
    parser.add_argument("--min-severity", default="critical", help="Minimum severity (critical/high/moderate/low)")
    parser.add_argument("--allowlist", help="Path to allowlist file (optional)")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    allowlist_path = Path(args.allowlist).resolve() if args.allowlist else None
    debug = args.debug

    if not input_path.exists():
        print(f"[filter-allowlist] Input file not found: {input_path}", file=sys.stderr)
        return 1

    data = load_json(input_path)
    entries = data.get("vulnerable_changes", [])
    allow_entries = load_allowlist(allowlist_path, debug=debug)

    filtered_entries = filter_entries(
        entries,
        allow_entries,
        args.min_severity,
        debug=debug,
    )

    result = {
        "vulnerable_changes": filtered_entries,
        "summary": {
            "total": len(entries),
            "filtered": len(filtered_entries),
            "min_severity": args.min_severity,
            "allowlist_entries": len(allow_entries),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    print(
        f"[filter-allowlist] Total: {len(entries)}, "
        f"Matched: {len(filtered_entries)}, Allowlist entries: {len(allow_entries)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

