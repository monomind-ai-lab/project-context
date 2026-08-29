#!/usr/bin/env python3
"""Check the health of an installed project-context package, without rewriting it.

This ships with the `project-context` skill rather than the installer because a
consuming repository installs only that skill: the health check has to be
reachable from the repository it diagnoses. The initializer keeps a `doctor`
subcommand that loads this file, so there is one implementation and one report
shape rather than two that drift.

Read-only. Exits 1 when any issue is an error, 0 otherwise, so CI and a hook can
both use the exit status without parsing the JSON report.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


TEMPLATE_VERSION = "0.5.0"
START = "<!-- project-context:start -->"
END = "<!-- project-context:end -->"
INSTRUCTION_NAMES = ("AGENTS.md", "agents.md", "CLAUDE.md", "claude.md")
CORE_TEMPLATE_PATHS = {"README.md", "SKILL.md", "NOW.md", "DECISIONS.md", "LEARNINGS.md"}
# Harness-specific skill locations. These hold pointers, never copies: the
# skill itself is installed once, harness-neutral, under .agents/skills/.
HARNESS_POINTER_ROOTS = ((".claude", "skills"),)
# Only the protocol skill is installed into a repository. The initializer stays
# in the Project Context checkout, so a pointer to it here would be dangling.
INSTALLED_SKILL_NAMES = ("project-context",)
HOOK_SETTINGS_PATHS = (
    Path(".claude") / "settings.json",
    Path(".claude") / "settings.local.json",
)
HOOK_PATH_PATTERN = re.compile(
    r"(?:\.agents|\.claude|scripts|bin|tools)/[A-Za-z0-9._/-]+\.[A-Za-z0-9]+"
)


def instruction_paths(target: Path) -> list[Path]:
    supported = {name.casefold() for name in INSTRUCTION_NAMES}
    return sorted(
        (path for path in target.iterdir() if path.name.casefold() in supported),
        key=lambda path: path.name,
    )


def hook_commands(target: Path) -> list[tuple[str, str]]:
    """(settings file, command) for declared hooks that name project context.

    Hooks belonging to anything else are ignored: this validates the protocol's
    own wiring, not the repository's unrelated automation.
    """
    found: list[tuple[str, str]] = []
    for relative in HOOK_SETTINGS_PATHS:
        settings = target / relative
        if not settings.is_file():
            continue
        try:
            payload = json.loads(settings.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        events = payload.get("hooks") if isinstance(payload, dict) else None
        if not isinstance(events, dict):
            continue
        for matchers in events.values():
            for matcher in matchers if isinstance(matchers, list) else []:
                entries = matcher.get("hooks") if isinstance(matcher, dict) else None
                for entry in entries if isinstance(entries, list) else []:
                    command = entry.get("command") if isinstance(entry, dict) else None
                    if isinstance(command, str) and (
                        "project-context" in command or "context_triggers" in command
                    ):
                        found.append((str(relative), command))
    return found


def reachability(target: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Can this protocol still reach an agent, and by which route?

    Every other doctor check inspects the protocol's own documents. This one
    asks the question those checks cannot: will anything ever load them into a
    session? A repository whose managed block was dropped, whose harness
    pointer was never written, and whose hooks reference a script that is not
    there is silently inert — and inert looks exactly like healthy.
    """
    issues: list[dict[str, str]] = []
    blocks: list[str] = []
    for path in instruction_paths(target):
        if not path.is_file() or path.is_symlink():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if START in text and END in text:
            blocks.append(path.name)
    if not blocks:
        issues.append(
            {
                "severity": "warning",
                "code": "missing-instruction-block",
                "path": str(target),
                "detail": "no root AGENTS.md or CLAUDE.md carries the managed project-context block",
            }
        )

    pointers: list[str] = []
    for harness_root, subdirectory in HARNESS_POINTER_ROOTS:
        for skill_name in INSTALLED_SKILL_NAMES:
            installed = target / ".agents" / "skills" / skill_name / "SKILL.md"
            pointer = target / harness_root / subdirectory / skill_name / "SKILL.md"
            if pointer.is_file():
                if installed.is_file():
                    pointers.append(str(pointer.relative_to(target)))
                else:
                    issues.append(
                        {
                            "severity": "error",
                            "code": "harness-pointer-dangling",
                            "path": str(pointer.relative_to(target)),
                            "detail": f"points at missing {installed.relative_to(target)}",
                        }
                    )
            elif installed.is_file():
                issues.append(
                    {
                        "severity": "warning",
                        "code": "missing-harness-pointer",
                        "path": str(pointer.relative_to(target)),
                        "detail": f"{skill_name} is installed but undiscoverable by this harness",
                    }
                )

    hooks: list[str] = []
    for settings_name, command in hook_commands(target):
        referenced = HOOK_PATH_PATTERN.findall(command)
        missing = [fragment for fragment in referenced if not (target / fragment).exists()]
        if missing:
            issues.append(
                {
                    "severity": "error",
                    "code": "hook-command-unresolved",
                    "path": settings_name,
                    "detail": "hook command references missing " + ", ".join(sorted(set(missing))),
                }
            )
        elif referenced:
            hooks.append(settings_name)

    paths = len(blocks) + len(pointers) + len(hooks)
    if not paths:
        issues.append(
            {
                "severity": "error",
                "code": "no-delivery-path",
                "path": str(target),
                "detail": "nothing loads this protocol into a session: no managed instruction block, no harness pointer, no working hook",
            }
        )
    return (
        {
            "delivers": bool(paths),
            "paths": paths,
            "instruction_blocks": sorted(blocks),
            "harness_pointers": sorted(pointers),
            "hooks": sorted(set(hooks)),
        },
        issues,
    )


def doctor(target: Path, stale_days: int = 30) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    issues: list[dict[str, str]] = []
    for relative in sorted(CORE_TEMPLATE_PATHS):
        if not (context / relative).is_file():
            issues.append({"severity": "error", "code": "missing-core-file", "path": relative})
    metadata = context / ".project-context.json"
    if not metadata.is_file():
        issues.append({"severity": "warning", "code": "missing-version-metadata", "path": str(metadata)})
    else:
        try:
            installed = str(json.loads(metadata.read_text(encoding="utf-8")).get("template_version", "unknown"))
            if installed != TEMPLATE_VERSION:
                issues.append(
                    {
                        "severity": "warning", "code": "template-update-available", "path": str(metadata),
                        "detail": f"installed {installed}; available {TEMPLATE_VERSION}",
                    }
                )
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append({"severity": "error", "code": "invalid-version-metadata", "path": str(metadata)})
    now_path = context / "NOW.md"
    if now_path.is_file():
        now_text = now_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^Last reviewed:\s*(\d{4}-\d{2}-\d{2})", now_text, re.MULTILINE)
        if match:
            try:
                age = (date.today() - datetime.strptime(match.group(1), "%Y-%m-%d").date()).days
                if age > stale_days:
                    issues.append(
                        {"severity": "warning", "code": "stale-current-state", "path": str(now_path), "detail": f"last reviewed {age} days ago"}
                    )
            except ValueError:
                issues.append({"severity": "warning", "code": "invalid-review-date", "path": str(now_path)})
        else:
            issues.append({"severity": "warning", "code": "missing-review-date", "path": str(now_path)})
    ids: dict[str, list[str]] = {}
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    if context.is_dir() and not context.is_symlink():
        for markdown in context.rglob("*.md"):
            text = markdown.read_text(encoding="utf-8", errors="replace")
            for record_id in re.findall(r"^##\s+([DL]-\d{3,})\b", text, re.MULTILINE):
                ids.setdefault(record_id, []).append(str(markdown.relative_to(context)))
            for target_text in link_pattern.findall(text):
                if target_text.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                link_path = target_text.split("#", 1)[0]
                if link_path and not (markdown.parent / link_path).resolve().exists():
                    issues.append(
                        {"severity": "warning", "code": "broken-relative-link", "path": str(markdown.relative_to(context)), "detail": target_text}
                    )
    for record_id, locations in ids.items():
        if len(locations) > 1:
            issues.append(
                {"severity": "error", "code": "duplicate-record-id", "path": ", ".join(locations), "detail": record_id}
            )
    delivery, delivery_issues = reachability(target)
    issues.extend(delivery_issues)
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "target": str(target),
        "template_version": TEMPLATE_VERSION,
        "status": "error" if errors else ("warning" if warnings else "healthy"),
        "summary": {"errors": errors, "warnings": warnings},
        "reachability": delivery,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--stale-days", default=30, type=int)
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    report = doctor(target, args.stale_days)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
