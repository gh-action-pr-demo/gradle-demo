#!/usr/bin/env python3
"""
Generate a concise summary from grype-report.json, write to GitHub Step Summary,
persist a Markdown comment, and emit outputs for downstream steps.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


def load_matches(report_path: Path) -> List[Dict]:
    if report_path.exists() and report_path.stat().st_size > 0:
        with report_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("matches", [])
    return []


def severity_ranking() -> Dict[str, int]:
    order = ["Critical", "High", "Medium", "Low", "Negligible", "Unknown"]
    return {name: idx for idx, name in enumerate(order)}, order


def summarize_packages(matches: Iterable[Dict]) -> Tuple[Dict[str, Dict], Dict[str, int]]:
    packages: Dict[str, Dict[str, object]] = {}
    counts: Dict[str, int] = defaultdict(int)

    for match in matches:
        vuln = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        severity = (vuln.get("severity") or "Unknown").capitalize()
        counts[severity] += 1

        pkg = artifact.get("name", "unknown")
        version = artifact.get("version", "unknown")
        key = f"{pkg}@{version}"

        entry = packages.setdefault(
            key,
            {
                "name": pkg,
                "version": version,
                "severities": set(),  # type: Set[str]
                "ids": set(),  # type: Set[str]
            },
        )
        entry["severities"].add(severity)
        vuln_id = vuln.get("id") or vuln.get("dataSource") or "N/A"
        entry["ids"].add(vuln_id)

    return packages, counts


def select_top_packages(packages: Dict[str, Dict]) -> List[Dict]:
    severity_rank, _ = severity_ranking()

    def entry_score(item: Dict) -> int:
        severities = item["severities"] or {"Unknown"}
        return min(severity_rank.get(sev, len(severity_rank)) for sev in severities)

    return sorted(
        packages.values(),
        key=lambda item: (entry_score(item), -len(item["ids"])),
    )[:5]


def format_summary(matches: List[Dict], counts: Dict[str, int], fail_on: str, sha: str) -> List[str]:
    _, severity_order = severity_ranking()
    summary_lines: List[str] = [
        "## Grype 扫描摘要",
        f"- 触发提交：`{sha}`",
        f"- 失败阈值：{fail_on} 及以上",
        f"- 总匹配漏洞数：{len(matches)}",
    ]

    if matches:
        summary_lines.append("")
        summary_lines.append("### 严重等级分布")
        for sev in severity_order:
            if counts.get(sev):
                summary_lines.append(f"- {sev}: {counts[sev]}")

    return summary_lines


def format_comment(summary_lines: List[str], top_packages: List[Dict], matches_present: bool) -> str:
    severity_rank, _ = severity_ranking()

    def format_severities(values: Set[str]) -> str:
        return ", ".join(
            sorted(values, key=lambda s: severity_rank.get(s, len(severity_rank)))
        )

    def format_ids(values: Set[str]) -> str:
        return "<br>".join(sorted(values)) if values else "-"

    comment_lines = summary_lines.copy()

    if matches_present:
        comment_lines.append("")
        comment_lines.append("### 📦 高优先级依赖（最多 5 个）")
        comment_lines.append("| 依赖 | 版本 | 严重等级 | 漏洞 ID |")
        comment_lines.append("| ---- | ---- | -------- | ------- |")
        for pkg in top_packages:
            comment_lines.append(
                f"| `{pkg['name']}` | `{pkg['version']}` | "
                f"{format_severities(pkg['severities'])} | {format_ids(pkg['ids'])} |"
            )
    else:
        comment_lines.append("")
        comment_lines.append("✅ 未检测到达到阈值的漏洞。")

    comment_lines.append("")
    comment_lines.append("---")
    comment_lines.append("*此评论由 Grype 自动生成*")
    return "\n".join(comment_lines) + "\n"


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def append_summary(summary_path: Path | None, content_lines: List[str]) -> None:
    if not summary_path:
        return
    with summary_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(content_lines))
        fh.write("\n")


def write_outputs(has_vulns: bool, comment_path: Path) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"has_vulns={'true' if has_vulns else 'false'}\n")
        fh.write(f"comment_path={comment_path}\n")


def main() -> None:
    report_path = Path(os.getenv("GRYPE_REPORT_PATH", "grype-report.json"))
    comment_path = Path(os.getenv("GRYPE_COMMENT_PATH", "grype-comment.md"))
    summary_target = Path(os.getenv("GITHUB_STEP_SUMMARY", "")) if os.getenv("GITHUB_STEP_SUMMARY") else None
    fail_on = os.getenv("FAIL_ON_SEVERITY", "high").capitalize()
    sha = os.getenv("GITHUB_SHA", "")[:7]

    matches = load_matches(report_path)
    packages, counts = summarize_packages(matches)
    top_packages = select_top_packages(packages)

    summary_lines = format_summary(matches, counts, fail_on, sha)
    comment_body = format_comment(summary_lines, top_packages, bool(matches))

    write_file(comment_path, comment_body)
    append_summary(summary_target, summary_lines)
    write_outputs(bool(matches), comment_path)


if __name__ == "__main__":
    main()

