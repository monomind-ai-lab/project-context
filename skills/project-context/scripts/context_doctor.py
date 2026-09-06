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
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


# Record model v1. One schema string for both products; `context-hub/1` is
# retired and survives here only as a diagnostic (see `legacy_hub_issues`).
SCHEMA = "project-context/1"
# One version number per product, and the two products ship on their own
# cadences. The marker records which product wrote it so a reader never assumes
# this version and a Hub's relate.
PRODUCT = "project-context"
LEGACY_SCHEMA = "context-hub/1"
LEGACY_START = "<!-- context-hub:start -->"
LEGACY_MARKER_NAME = ".context-hub.json"
MARKER_NAME = ".project-context.json"
START = "<!-- project-context:start -->"
END = "<!-- project-context:end -->"
INSTRUCTION_NAMES = ("AGENTS.md", "agents.md", "CLAUDE.md", "claude.md")
# Both files carry the same managed block, so a Claude-only repository is not
# left with rules no Claude session reads. One finding per missing file.
INSTRUCTION_ROLES = ("AGENTS.md", "CLAUDE.md")
CORE_TEMPLATE_PATHS = {"README.md", "SKILL.md", "NOW.md", "DECISIONS.md", "LEARNINGS.md"}
# Detail records carry frontmatter. Registries stay plain Markdown.
RECORD_DIRECTORIES = ("decisions", "questions", "tasks", "inbox")
# Scaffolding inside a record directory, not a record.
NON_RECORD_NAMES = {"README.md", "TEMPLATE.md", "INDEX.md"}
# `owners_window/` is the owner's own space in a Hub: never pushed, never
# linted, never pulled into. `sessions/` never reaches Git at all. Neither is
# a repository record set, so nothing below reads either one.
UNLINTED_DIRECTORIES = {"owners_window", "sessions"}
# The pushed set: owner-authored in the Hub, read-only here, verified against
# the stamps the push left in the marker.
PUSHED_ROOTS = ("global", "blueprint")
REQUIRED_KEYS = ("id", "kind", "status", "title", "created", "asserted_by")
# Validated only when present. There is deliberately no `serves` key: `PLAN.md`
# is a registry and carries no frontmatter, so the conformance anchor is a body
# line on the milestone item rather than a field.
OPTIONAL_KEYS = (
    "approved_by", "supersedes", "superseded_by", "evidence", "files",
    "valid_at", "invalid_at", "session", "harness", "model",
)
# Required-but-empty fields the three-block metadata format demanded. Absent
# means absent now, so carrying one forward is noise a reader has to skip.
RETIRED_KEYS = ("generated_at", "generated_by", "confidence", "aliases")
KINDS = ("decision", "learning", "question", "task", "capsule")
# One vocabulary per kind, and the doctor enforces *that* kind's set. A
# permissive union across all three would let two people write questions two
# different ways with nothing to catch it, which is the failure a single
# vocabulary exists to prevent. A question is not an assertion and a task is
# not a claim, so they do not share the assertion states.
LIFECYCLES = {
    "decision": ("proposed", "accepted", "superseded", "rejected"),
    "learning": ("proposed", "accepted", "superseded", "rejected"),
    "capsule": ("proposed", "accepted", "superseded", "rejected"),
    "question": ("open", "answered", "superseded"),
    "task": ("proposed", "active", "done", "dropped"),
}
# `candidate → approved → superseded` is retired everywhere, whatever the kind.
RETIRED_STATUSES = {"candidate": "proposed", "approved": "accepted"}
REGISTRY_KINDS = {
    "DECISIONS.md": "decision",
    "LEARNINGS.md": "learning",
    "QUESTIONS.md": "question",
    # A milestone item is work with an owner and an end, so it takes the task
    # vocabulary rather than a fourth one of its own.
    "PLAN.md": "task",
}
# Plan-to-epic conformance (2.4). `PLAN.md` is authored by builders in the
# repository; `blueprint/EPIC.md` is authored by the owner in the Hub and
# pushed down read-only. "Conforms" is checked here rather than exhorted in
# prose: each milestone item names the epic item it advances.
PLAN_FILE = "PLAN.md"
EPIC_RELATIVE = "blueprint/EPIC.md"
BLUEPRINT_DIRNAME = "blueprint"
PLAN_ITEM_PATTERN = re.compile(r"^##\s+(M-\d{3,}):\s*(.+)$", re.M)
SERVES_LINE_PATTERN = re.compile(r"^\s*-\s+Serves:\s*(.+)$", re.M)
# The epic's own item shape, from its template: `- **E-001 — One store.**`
EPIC_ITEM_PATTERN = re.compile(r"^\s*-\s+\*\*(E-\d{3,})\s*[—-]", re.M)
EPIC_REFERENCE_PATTERN = re.compile(r"\bE-\d{3,}\b")
# A dropped item is work that is not happening. Holding it to the epic would
# report a gap that closing the item already resolved.
UNANCHORED_EXEMPT_STATUSES = {"dropped"}
ID_PATTERN = re.compile(r"^(?:[DLQT]-\d{3,}|C-\d{4}-\d{2}-\d{2}-[0-9a-z]+)$")
ACTOR_PATTERN = re.compile(r"^(?:person|agent):[^\s:][^\s]*$")
DATE_ONLY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUS_LINE_PATTERN = re.compile(r"^\s*-\s+Status:\s*`?([A-Za-z][A-Za-z-]*)`?\s*$")
FRONTMATTER_KEY_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
FRONTMATTER_ITEM_PATTERN = re.compile(r"^\s*-\s+(.*)$")
# Reference grammar, validated by shape. Resolution is optional and never
# required, so a reference is checked for the form its scheme promises and
# nothing more. A token whose scheme is not one of these is prose.
REFERENCE_PATTERNS = {
    "session": re.compile(r"^session:[A-Za-z0-9._-]+:[A-Za-z0-9._-]+$"),
    "commit": re.compile(r"^commit:[A-Za-z0-9._/-]+:[0-9a-f]{7,40}$"),
    "pr": re.compile(r"^pr:[A-Za-z0-9._/-]+#\d+$"),
    "review": re.compile(r"^review:[A-Za-z0-9._/-]+#\d+/[A-Za-z0-9._-]+$"),
    "ticket": re.compile(r"^ticket:[A-Za-z0-9._-]+:[A-Za-z0-9._-]+$"),
    "doc": re.compile(r"^doc:[A-Za-z0-9._/-]+:\S+@[0-9a-f]{7,40}$"),
    "url": re.compile(r"^url:https?://\S+$"),
    "capsule": re.compile(r"^capsule:[A-Za-z0-9._-]+$"),
    # A record cites the Hub state it came from. `doc:` cannot serve here: it
    # needs a binding name, and a private Hub has none a project repository is
    # in a position to declare. Shape only, like every scheme above — a builder
    # holds no permission on the Hub and could not resolve it if we tried.
    "hub": re.compile(r"^hub:[A-Za-z0-9._-]+@[0-9a-f]{7,40}$"),
}
REFERENCE_TOKEN_PATTERN = re.compile(
    r"(?<![\w:/-])(" + "|".join(REFERENCE_PATTERNS) + r"):\S+"
)
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


VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)*(?:[-+.][0-9A-Za-z.-]+)?$")


def version_file() -> Path | None:
    """The one `VERSION` file this copy of the script belongs to, or None.

    There is a single version number — the package version — and the scripts
    read it rather than each carrying a constant that drifts. Two layouts hold
    it: a checkout or the wheel bundle, where `VERSION` sits beside `skills/`,
    and an installed copy under a repository's `.agents/skills/`, where the
    installer writes a `VERSION` beside `SKILL.md` so the installed doctor
    still knows which release it came from.

    The lookup is exact rather than a walk up the tree: a consuming repository
    may well have a `VERSION` of its own, and reporting the host project's
    release as ours would be worse than reporting nothing.
    """
    here = Path(__file__).resolve()
    beside = here.parents[1] / "VERSION"
    if beside.is_file():
        return beside
    if here.parents[2].name == "skills":
        packaged = here.parents[3] / "VERSION"
        if packaged.is_file():
            return packaged
    return None


def package_version() -> str:
    """The package version, or "unknown" when this copy cannot establish it."""
    path = version_file()
    if path is None:
        return "unknown"
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return "unknown"
    return text if VERSION_PATTERN.match(text) else "unknown"


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
    # One finding per missing file, named. Satisfied by *either* file, the
    # check passed a Claude-only repository whose rules only Codex would read.
    carried = {name.casefold() for name in blocks}
    for role in INSTRUCTION_ROLES:
        if role.casefold() in carried:
            continue
        issues.append(
            {
                "severity": "warning",
                "code": "missing-instruction-block",
                "path": role,
                "detail": f"root {role} does not carry the managed project-context block",
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


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, bool]:
    """(mapping, well_formed) for a leading `---` YAML block.

    A deliberately small subset: `key: value`, block sequences, and inline
    `[a, b]` lists. That is the whole of what the record model asks a record to
    carry, and parsing no more than the contract defines keeps the doctor free
    of a runtime dependency and free of opinions about YAML it will never see.

    Returns `(None, True)` when there is no frontmatter at all, and
    `(None, False)` when a block opened and never closed.
    """
    if not text.startswith("---"):
        return None, True
    lines = text.splitlines()
    if lines[0].strip() != "---":
        return None, True
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() in {"---", "..."})
    except StopIteration:
        return None, False
    fields: dict[str, Any] = {}
    key: str | None = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = FRONTMATTER_ITEM_PATTERN.match(line)
        if item is not None and key is not None and isinstance(fields.get(key), list):
            fields[key].append(unquote(item.group(1)))
            continue
        match = FRONTMATTER_KEY_PATTERN.match(line)
        if match is None:
            continue
        key, raw = match.group(1), match.group(2).strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            fields[key] = [unquote(part.strip()) for part in inner.split(",") if part.strip()]
        elif raw:
            fields[key] = unquote(raw)
        else:
            fields[key] = []
    return fields, True


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def reference_issues(values: list[str], source: str) -> list[dict[str, str]]:
    """Every token that claims a reference scheme must keep that scheme's shape.

    Shape only: resolution is optional and never required, so this says nothing
    about whether the commit, ticket, or page on the other end exists. A token
    whose scheme is not in the grammar is ordinary prose and is left alone.
    """
    issues: list[dict[str, str]] = []
    for value in values:
        for match in REFERENCE_TOKEN_PATTERN.finditer(value):
            token = match.group(0).rstrip(".,;)")
            pattern = REFERENCE_PATTERNS[match.group(1)]
            if not pattern.match(token):
                issues.append(
                    {
                        "severity": "error",
                        "code": "invalid-reference",
                        "path": source,
                        "detail": f"{token} does not match the {match.group(1)} reference grammar",
                    }
                )
    return issues


def status_issues(status: str, kind: str, source: str) -> list[dict[str, str]]:
    """Validate a status against the vocabulary of *that record's kind*.

    A state that belongs to a different kind is as wrong as one that belongs to
    no kind: `accepted` on a question and `answered` on a decision are both
    errors, because a question is not an assertion. When the kind is missing or
    unrecognised there is no vocabulary to check against, and the record
    already carries the error that says so — only the retired words are still
    worth naming, since they are retired whatever the kind.
    """
    if status in RETIRED_STATUSES:
        return [
            {
                "severity": "error",
                "code": "retired-status",
                "path": source,
                "detail": f"`{status}` is retired; read `{RETIRED_STATUSES[status]}`",
            }
        ]
    allowed = LIFECYCLES.get(kind)
    if allowed is None or status in allowed:
        return []
    return [
        {
            "severity": "error",
            "code": "invalid-status",
            "path": source,
            "detail": f"`{status}` is not a {kind} state; a {kind} is "
            + " → ".join(allowed[:2])
            + " → "
            + " | ".join(allowed[2:]),
        }
    ]


def record_issues(source: str, text: str) -> list[dict[str, str]]:
    """Validate one detail record against the six required frontmatter keys.

    Six, not eight. Eight is the ceiling the model allows, not a target, so
    everything else is optional and is checked only when it is present.
    """
    issues: list[dict[str, str]] = []
    fields, well_formed = parse_frontmatter(text)
    if not well_formed:
        return [
            {
                "severity": "error",
                "code": "malformed-frontmatter",
                "path": source,
                "detail": "the frontmatter block opened and never closed",
            }
        ]
    if fields is None:
        return [
            {
                "severity": "error",
                "code": "missing-frontmatter",
                "path": source,
                "detail": "a detail record carries frontmatter with " + ", ".join(REQUIRED_KEYS),
            }
        ]
    missing = [key for key in REQUIRED_KEYS if not fields.get(key)]
    if missing:
        issues.append(
            {
                "severity": "error",
                "code": "missing-required-key",
                "path": source,
                "detail": "frontmatter is missing " + ", ".join(missing),
            }
        )
    retired = [key for key in RETIRED_KEYS if key in fields]
    retired += [
        key for key in ("supersedes", "superseded_by")
        if isinstance(fields.get(key), list) and not fields[key]
    ]
    if retired:
        issues.append(
            {
                "severity": "warning",
                "code": "retired-frontmatter-key",
                "path": source,
                "detail": "absent means absent; drop " + ", ".join(sorted(retired)),
            }
        )
    record_id = fields.get("id")
    if isinstance(record_id, str) and record_id and not ID_PATTERN.match(record_id):
        issues.append(
            {
                "severity": "error",
                "code": "invalid-record-id",
                "path": source,
                "detail": f"`{record_id}` is not a stable ID such as D-001, L-003, Q-002, T-012, or C-2026-09-03-a1b2",
            }
        )
    kind = fields.get("kind") if isinstance(fields.get("kind"), str) else ""
    if kind and kind not in KINDS:
        issues.append(
            {
                "severity": "error",
                "code": "invalid-kind",
                "path": source,
                "detail": f"`{kind}` is not one of {', '.join(KINDS)}",
            }
        )
    status = fields.get("status")
    if isinstance(status, str) and status:
        issues.extend(status_issues(status, kind, source))
    title = fields.get("title")
    if isinstance(title, str) and title.endswith("."):
        issues.append(
            {
                "severity": "warning",
                "code": "title-trailing-period",
                "path": source,
                "detail": "a title is one line with no trailing period",
            }
        )
    for key in ("created", "valid_at", "invalid_at"):
        value = fields.get(key)
        if isinstance(value, str) and value and not DATE_ONLY_PATTERN.match(value):
            issues.append(
                {
                    "severity": "error",
                    "code": "invalid-date",
                    "path": source,
                    "detail": f"{key} is `{value}`; the record model uses YYYY-MM-DD",
                }
            )
    for key in ("asserted_by", "approved_by"):
        value = fields.get(key)
        if isinstance(value, str) and value and not ACTOR_PATTERN.match(value):
            issues.append(
                {
                    "severity": "error",
                    "code": "invalid-actor",
                    "path": source,
                    "detail": f"{key} is `{value}`; an actor is person:<name> or agent:<name>",
                }
            )
    asserted_by, approved_by = fields.get("asserted_by"), fields.get("approved_by")
    if (
        isinstance(asserted_by, str)
        and asserted_by == approved_by
        and asserted_by.startswith("agent:")
    ):
        # A correctness check on the record, not an access control: an agent
        # that accepts its own assertion has recorded no second judgement.
        issues.append(
            {
                "severity": "error",
                "code": "agent-self-approval",
                "path": source,
                "detail": f"{asserted_by} both asserted and approved this record",
            }
        )
    for key in ("evidence", "supersedes", "superseded_by", "session"):
        value = fields.get(key)
        values = value if isinstance(value, list) else [value] if isinstance(value, str) else []
        issues.extend(reference_issues([item for item in values if isinstance(item, str)], source))
    return issues


def registry_issues(source: str, text: str) -> list[dict[str, str]]:
    """A registry has no frontmatter, so its statuses live on `- Status:` lines."""
    kind = REGISTRY_KINDS[source]
    issues: list[dict[str, str]] = []
    for line in text.splitlines():
        match = STATUS_LINE_PATTERN.match(line)
        if match:
            issues.extend(status_issues(match.group(1), kind, source))
    return issues


def plan_conformance(context: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Check every `PLAN.md` item against the epic it is supposed to advance.

    The asymmetry between the two failures is the whole point. A plan item that
    serves no epic item is an **error**: the project is spending effort on
    something nobody asked for, and the fix is to anchor it or to raise a
    question about whether the epic is still right. An epic item no plan item
    serves is only a **warning**: an epic legitimately runs ahead of the
    current milestone, and treating that as a failure would force a project to
    plan its whole epic at once — the exact big-design-up-front the two-altitude
    split exists to avoid.

    A repository with no `blueprint/` has no epic, and `PLAN.md` stands alone.
    Silence there is deliberate: Project Context is a complete product without
    a Hub (2.8), and a doctor that nags for a file only a Hub can push would
    make the standalone install feel broken.
    """
    summary: dict[str, Any] = {"plan_items": 0, "epic_items": 0, "anchored": 0, "unserved": 0}
    issues: list[dict[str, str]] = []
    plan_path = context / PLAN_FILE
    epic_path = context / EPIC_RELATIVE
    if not plan_path.is_file() or plan_path.is_symlink():
        return summary, issues
    plan_text = plan_path.read_text(encoding="utf-8", errors="replace")

    epic_ids: set[str] = set()
    has_epic = epic_path.is_file() and not epic_path.is_symlink()
    if has_epic:
        epic_ids = set(EPIC_ITEM_PATTERN.findall(epic_path.read_text(encoding="utf-8", errors="replace")))
        summary["epic_items"] = len(epic_ids)
    elif (context / BLUEPRINT_DIRNAME).is_dir():
        # A blueprint that arrived without its epic is a broken push, not a
        # repository that never had one — worth naming, but not an error a
        # builder can fix from here.
        issues.append(
            {
                "severity": "warning", "code": "missing-epic", "path": EPIC_RELATIVE,
                "detail": "blueprint/ is present without an epic; the Hub owner pushes it",
            }
        )

    served: set[str] = set()
    heads = list(PLAN_ITEM_PATTERN.finditer(plan_text))
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(plan_text)
        body = plan_text[head.end():end]
        summary["plan_items"] += 1
        status_match = STATUS_LINE_PATTERN.search(body)
        status = status_match.group(1).lower() if status_match else ""
        serves = SERVES_LINE_PATTERN.search(body)
        named = EPIC_REFERENCE_PATTERN.findall(serves.group(1)) if serves else []
        if not has_epic:
            continue
        if not named:
            if status not in UNANCHORED_EXEMPT_STATUSES:
                issues.append(
                    {
                        "severity": "error", "code": "plan-item-unanchored", "path": PLAN_FILE,
                        "detail": f"{head.group(1)} names no epic item; anchor it with a `- Serves:` line or raise a question",
                    }
                )
            continue
        summary["anchored"] += 1
        for epic_id in named:
            if epic_id in epic_ids:
                served.add(epic_id)
            else:
                issues.append(
                    {
                        "severity": "error", "code": "plan-serves-unknown-epic-item", "path": PLAN_FILE,
                        "detail": f"{head.group(1)} serves {epic_id}, which {EPIC_RELATIVE} does not define; a newer epic may have superseded it",
                    }
                )
    for epic_id in sorted(epic_ids - served):
        summary["unserved"] += 1
        issues.append(
            {
                "severity": "warning", "code": "epic-item-unserved", "path": EPIC_RELATIVE,
                "detail": f"{epic_id} is not served by any plan item; an epic may run ahead of the milestone",
            }
        )
    return summary, issues


def file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def pushed_set(context: Path, marker: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Verify `global/` and `blueprint/` against the stamps the push left.

    The pushed set is owner-authored in the Hub and read-only here. Nothing is
    injected into the files themselves — they stay clean Markdown — so the only
    evidence that a copy is still the copy that was sent is the digest recorded
    in the marker. A mismatch names the Hub, because that is where the change
    belongs; editing it back here would only be undone by the next push.
    """
    summary: dict[str, Any] = {"stamped": 0, "modified": 0, "missing": 0, "oldest_pushed_at": None}
    issues: list[dict[str, str]] = []
    stamps = marker.get("pushed") if isinstance(marker, dict) else None
    stamps = stamps if isinstance(stamps, dict) else {}
    times: list[str] = []
    for relative in sorted(stamps):
        entry = stamps[relative]
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            issues.append(
                {
                    "severity": "error",
                    "code": "invalid-pushed-stamp",
                    "path": relative,
                    "detail": "a stamp records sha256, source_commit, and pushed_at",
                }
            )
            continue
        summary["stamped"] += 1
        if isinstance(entry.get("pushed_at"), str):
            times.append(entry["pushed_at"])
        path = context / relative
        if not path.is_file() or path.is_symlink():
            summary["missing"] += 1
            issues.append(
                {
                    "severity": "error",
                    "code": "pushed-file-missing",
                    "path": relative,
                    "detail": "stamped as pushed but not present; the Hub owner re-pushes it",
                }
            )
            continue
        if file_digest(path) != entry["sha256"]:
            summary["modified"] += 1
            issues.append(
                {
                    "severity": "error",
                    "code": "pushed-file-modified",
                    "path": relative,
                    "detail": "edited since it was pushed; change it in the Hub and push again, or raise a question here",
                }
            )
    for root in PUSHED_ROOTS:
        directory = context / root
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(context).as_posix()
            if relative not in stamps:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "pushed-file-unstamped",
                        "path": relative,
                        "detail": "in the pushed set with no stamp; it was added here rather than in the Hub",
                    }
                )
    summary["oldest_pushed_at"] = min(times) if times else None
    return summary, issues


def legacy_hub_issues(target: Path, marker: Any) -> list[dict[str, str]]:
    """Recognise a Context Hub install so a half-upgraded one is not silent.

    Context Hub is superseded, not migrated: its record model, its second
    doctor, and its second schema string are gone. This recognition is the only
    part of it that ships forward, and it exists so a repository still carrying
    `context-hub/1` reports that fact instead of appearing healthy while
    nothing understands its records.
    """
    issues: list[dict[str, str]] = []
    legacy_marker = target / LEGACY_MARKER_NAME
    if legacy_marker.is_file():
        issues.append(
            {
                "severity": "warning",
                "code": "legacy-context-hub-marker",
                "path": LEGACY_MARKER_NAME,
                "detail": "a Context Hub scaffold; Context Hub is superseded and its records are not read by this protocol",
            }
        )
    if isinstance(marker, dict) and LEGACY_SCHEMA in {
        marker.get("schema"), marker.get("schema_version")
    }:
        issues.append(
            {
                "severity": "warning",
                "code": "legacy-context-hub-marker",
                "path": MARKER_NAME,
                "detail": f"the marker still declares {LEGACY_SCHEMA}; the record model is {SCHEMA}",
            }
        )
    for path in instruction_paths(target):
        if not path.is_file() or path.is_symlink():
            continue
        if LEGACY_START in path.read_text(encoding="utf-8", errors="replace"):
            issues.append(
                {
                    "severity": "warning",
                    "code": "legacy-context-hub-block",
                    "path": path.name,
                    "detail": f"carries a {LEGACY_START} block; the managed block is {START}",
                }
            )
    return issues


def doctor(target: Path, stale_days: int = 30) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    issues: list[dict[str, str]] = []
    for relative in sorted(CORE_TEMPLATE_PATHS):
        if not (context / relative).is_file():
            issues.append({"severity": "error", "code": "missing-core-file", "path": relative})
    available = package_version()
    marker: Any = None
    metadata = context / MARKER_NAME
    if not metadata.is_file():
        issues.append({"severity": "warning", "code": "missing-version-metadata", "path": str(metadata)})
    else:
        try:
            marker = json.loads(metadata.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append({"severity": "error", "code": "invalid-version-metadata", "path": str(metadata)})
    if isinstance(marker, dict):
        schema = marker.get("schema")
        if isinstance(schema, str) and schema not in {SCHEMA, LEGACY_SCHEMA}:
            issues.append(
                {
                    "severity": "error", "code": "unsupported-schema", "path": str(metadata),
                    "detail": f"marker declares {schema}; this doctor reads {SCHEMA}",
                }
            )
        product = marker.get("product")
        foreign = isinstance(product, str) and product != PRODUCT
        if foreign:
            issues.append(
                {
                    "severity": "warning", "code": "foreign-product-marker", "path": str(metadata),
                    "detail": f"written by {product}; its version does not relate to this one, so no upgrade is inferred",
                }
            )
        # `template_version` is retired. A marker written before the version
        # numbers were unified carries only that key, and reading it is what
        # lets the doctor tell such an install that an upgrade is waiting
        # rather than silently comparing against nothing.
        installed = marker.get("version") or marker.get("template_version") or "unknown"
        if not foreign and available != "unknown" and str(installed) != available:
            issues.append(
                {
                    "severity": "warning", "code": "template-update-available", "path": str(metadata),
                    "detail": f"installed {installed}; available {available} — run `project-context update`",
                }
            )
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
    records = 0
    if context.is_dir() and not context.is_symlink():
        for markdown in sorted(context.rglob("*.md")):
            relative_path = markdown.relative_to(context)
            if UNLINTED_DIRECTORIES.intersection(relative_path.parts[:-1]):
                continue
            text = markdown.read_text(encoding="utf-8", errors="replace")
            source = relative_path.as_posix()
            if relative_path.parts[0] in RECORD_DIRECTORIES and markdown.name not in NON_RECORD_NAMES:
                records += 1
                issues.extend(record_issues(source, text))
            elif source in REGISTRY_KINDS:
                issues.extend(registry_issues(source, text))
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
    pushed, pushed_issues = pushed_set(context, marker)
    issues.extend(pushed_issues)
    conformance, conformance_issues = plan_conformance(context)
    issues.extend(conformance_issues)
    issues.extend(legacy_hub_issues(target, marker))
    delivery, delivery_issues = reachability(target)
    issues.extend(delivery_issues)
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "target": str(target),
        "schema": SCHEMA,
        "product": PRODUCT,
        "version": available,
        "status": "error" if errors else ("warning" if warnings else "healthy"),
        "summary": {"errors": errors, "warnings": warnings},
        "reachability": delivery,
        "evidence": evidence,
        "records": records,
        "pushed": pushed,
        "conformance": conformance,
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
