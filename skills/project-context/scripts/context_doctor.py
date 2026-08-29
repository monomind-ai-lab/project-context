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
import subprocess
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
# Evidence anchors: `src/server.py@a1b2c3d` pins a citation to the state it
# cited. Git object names are 40 hex characters and 7 is the conventional short
# form, so 7-40 covers every abbreviation a person would paste.
ANCHOR_LINK_PATTERN = re.compile(r"^(.+)@([0-9a-f]{7,40})$")
# The same anchor written plainly on an `- Evidence:` line. The path half must
# contain a `/` or a `.` so ordinary prose cannot be read as a citation, and the
# lookbehind refuses a match that starts mid-token or straight after an `@` —
# together those keep `user@example.com` (no separator in `user`, and
# `example.com` follows an `@`) and `pkg@1.2.3` (no separator, no hex run) out.
ANCHOR_TEXT_PATTERN = re.compile(
    r"(?<![\w@])([\w.-]*[./][\w./-]*)@([0-9a-f]{7,40})\b"
)
EVIDENCE_LINE_PATTERN = re.compile(r"^\s*- Evidence:")


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


def run_git(target: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """Run one read-only git command in `target`, or None if it could not run.

    Every anchor check funnels through here so that a missing git, a repository
    git refuses to read, or a call that hangs degrades to "this anchor went
    unchecked". A read-only diagnostic that crashes — or that invents drift
    from a failed subprocess — is worse than one that stays quiet.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=target,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def repo_relative(target: Path, path: Path) -> str | None:
    """`path` as a target-relative POSIX string, or None when it escapes.

    Git resolves a pathspec against the working directory, so an anchor that
    points outside the repository names nothing this doctor can verify.
    """
    try:
        return path.resolve().relative_to(target).as_posix()
    except (OSError, ValueError):
        return None


def verify_anchors(
    target: Path, anchors: list[tuple[str, str, str, str]]
) -> tuple[dict[str, int], list[dict[str, str]]]:
    """Check each `path@commit` citation against the repository's history.

    A link that still resolves proves the cited file exists, not that it still
    says what it said when it was cited. Pinning the commit makes the citation
    falsifiable: if the path moved on since, the reasoning resting on it may no
    longer hold, and the entry needs re-reading rather than trusting.

    Warnings only, and git only. Outside a work tree nothing is checked and
    nothing is reported — a plain project folder has no history to compare
    against, and a scaffold that cannot be wrong should not be nagged about.
    """
    summary = {"anchors": 0, "drifted": 0, "unverifiable": 0}
    issues: list[dict[str, str]] = []
    if not anchors:
        return summary, issues
    inside = run_git(target, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return summary, issues
    # One verdict per pinned state, however many entries cite it.
    unique: dict[tuple[str, str], tuple[str, str]] = {}
    for path, commit, source, form in anchors:
        unique.setdefault((path, commit), (source, form))
    for (path, commit), (source, form) in sorted(unique.items()):
        known = run_git(target, "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}")
        if known is None:
            continue
        if known.returncode != 0:
            summary["anchors"] += 1
            summary["unverifiable"] += 1
            issues.append(
                {
                    "severity": "warning",
                    "code": "evidence-unverifiable",
                    "path": source,
                    "detail": f"{path}@{commit}: commit {commit} is unknown here — a shallow clone, or a typo",
                }
            )
            continue
        if not (target / path).exists():
            summary["anchors"] += 1
            # A link-form anchor already produced broken-relative-link from the
            # existence check above; saying it twice under a second code reads
            # as two problems.
            if form == "text":
                summary["drifted"] += 1
                issues.append(
                    {
                        "severity": "warning",
                        "code": "evidence-drift",
                        "path": source,
                        "detail": f"{path} no longer exists; cited at {commit}",
                    }
                )
            continue
        changed = run_git(target, "diff", "--quiet", commit, "HEAD", "--", path)
        if changed is None or changed.returncode not in (0, 1):
            continue
        summary["anchors"] += 1
        if changed.returncode == 0:
            continue
        summary["drifted"] += 1
        detail = f"{path} changed since {commit}"
        # How far it moved, when git can say. The count is empty for an anchor
        # that is not an ancestor of HEAD, where "0 commits" would be a lie.
        counted = run_git(target, "rev-list", "--count", f"{commit}..HEAD", "--", path)
        if counted is not None and counted.returncode == 0:
            number = counted.stdout.strip()
            if number.isdigit() and int(number) > 0:
                plural = "" if number == "1" else "s"
                detail = f"{path} changed in {number} commit{plural} since {commit}"
        issues.append(
            {
                "severity": "warning",
                "code": "evidence-drift",
                "path": source,
                "detail": detail,
            }
        )
    return summary, issues


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
    # (repository-relative path, commit, citing file, "link" or "text")
    anchors: list[tuple[str, str, str, str]] = []
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    if context.is_dir() and not context.is_symlink():
        for markdown in context.rglob("*.md"):
            text = markdown.read_text(encoding="utf-8", errors="replace")
            source = str(markdown.relative_to(context))
            for record_id in re.findall(r"^##\s+([DL]-\d{3,})\b", text, re.MULTILINE):
                ids.setdefault(record_id, []).append(source)
            for target_text in link_pattern.findall(text):
                if target_text.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                link_path = target_text.split("#", 1)[0]
                anchor = ANCHOR_LINK_PATTERN.match(link_path)
                if anchor:
                    # `../src/server.py@a1b2c3d` names src/server.py pinned to a
                    # commit, not a file whose name ends in one: check the path
                    # without the pin, and hand the pin to the anchor check.
                    link_path = anchor.group(1)
                    relative = repo_relative(target, markdown.parent / link_path)
                    if relative:
                        anchors.append((relative, anchor.group(2), source, "link"))
                if link_path and not (markdown.parent / link_path).resolve().exists():
                    issues.append(
                        {"severity": "warning", "code": "broken-relative-link", "path": source, "detail": target_text}
                    )
            for line in text.splitlines():
                # Plain-text anchors are repository-root-relative: an evidence
                # line names a path the way a person would type it at the root,
                # not relative to whichever registry file it landed in.
                if not EVIDENCE_LINE_PATTERN.match(line):
                    continue
                for cited, commit in ANCHOR_TEXT_PATTERN.findall(line):
                    relative = repo_relative(target, target / cited)
                    if relative:
                        anchors.append((relative, commit, source, "text"))
    for record_id, locations in ids.items():
        if len(locations) > 1:
            issues.append(
                {"severity": "error", "code": "duplicate-record-id", "path": ", ".join(locations), "detail": record_id}
            )
    evidence, evidence_issues = verify_anchors(target, anchors)
    issues.extend(evidence_issues)
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
        "evidence": evidence,
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
