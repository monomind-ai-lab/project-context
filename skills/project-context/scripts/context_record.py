#!/usr/bin/env python3
"""Create one durable Project Context record, plus its registry link when needed.

Agents decide *whether* a decision, question, task, design, or incident exists.
This command handles the mechanical part they should not improvise: stable IDs,
frontmatter, provenance, filenames, and decision/question registry links.

    context_record.py --kind task --title "Ship the retry guard" \
        --text "Implement and verify the bounded retry path." --apply
"""

from __future__ import annotations

import argparse
from datetime import date
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


CONTEXT_DIRNAME = "project-context"
NON_RECORD_NAMES = {"README.md", "TEMPLATE.md", "INDEX.md"}
ACTOR_PATTERN = re.compile(r"^(?:person|agent):[^\s:][^\s]*$")
SESSION_PATTERN = re.compile(r"^session:[A-Za-z0-9._-]+:[A-Za-z0-9._-]+$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")

RECORD_SPECS: dict[str, dict[str, Any]] = {
    "decision": {
        "directory": "decisions", "prefix": "D", "default_status": "proposed",
        "statuses": ("proposed", "accepted", "superseded", "rejected"),
        "heading": "Decision", "registry": "DECISIONS.md", "registry_label": "Decision",
    },
    "question": {
        "directory": "questions", "prefix": "Q", "default_status": "open",
        "statuses": ("open", "answered", "superseded"),
        "heading": "What is unresolved", "registry": "QUESTIONS.md", "registry_label": "Question",
    },
    "task": {
        "directory": "tasks", "prefix": "T", "default_status": "proposed",
        "statuses": ("proposed", "active", "done", "dropped"),
        "heading": "Objective", "registry": None,
    },
    "design": {
        "directory": "designs", "prefix": "DS", "default_status": "proposed",
        "statuses": ("proposed", "accepted", "superseded", "rejected"),
        "heading": "Proposed design", "registry": None,
    },
    "incident": {
        "directory": "incidents", "prefix": "I", "default_status": "open",
        "statuses": ("open", "resolved", "superseded"),
        "heading": "Impact and evidence", "registry": None,
    },
}
RECORD_KINDS = tuple(RECORD_SPECS)


def slug(value: str) -> str:
    return SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")


def run_git(target: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", "-C", str(target), *args),
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = result.stdout.strip()
    return output if result.returncode == 0 and output else None


def default_actor(target: Path) -> str:
    name = run_git(target, "config", "user.name")
    return f"person:{slug(name)}" if name and slug(name) else "person:unknown"


def binding(target: Path) -> str:
    remote = run_git(target, "remote", "get-url", "origin")
    if remote:
        tail = remote.rstrip("/").rsplit("/", 1)[-1]
        return slug(tail[:-4] if tail.endswith(".git") else tail) or slug(target.name)
    return slug(target.name) or "repository"


def provenance(target: Path, args: argparse.Namespace) -> dict[str, Any]:
    found: dict[str, Any] = {"asserted_by": args.actor or default_actor(target)}
    for key in ("harness", "model", "session"):
        value = getattr(args, key)
        if value:
            found[key] = value
    evidence = list(args.evidence or [])
    head = run_git(target, "rev-parse", "HEAD")
    if head:
        evidence.append(f"commit:{binding(target)}:{head}")
    if evidence:
        found["evidence"] = evidence
    if args.files:
        found["files"] = [item.strip() for item in args.files.split(",") if item.strip()]
    return found


def frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---\n"):
        return {}
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        return {}
    fields: dict[str, str] = {}
    for line in block.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.+)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    return fields


def records(context: Path) -> list[tuple[Path, dict[str, str]]]:
    found: list[tuple[Path, dict[str, str]]] = []
    for spec in RECORD_SPECS.values():
        directory = context / spec["directory"]
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            if path.name not in NON_RECORD_NAMES:
                found.append((path, frontmatter(path)))
    return found


def next_id(context: Path, prefix: str, existing: list[tuple[Path, dict[str, str]]]) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    numbers = []
    for _path, fields in existing:
        match = pattern.match(fields.get("id", ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def render(record: dict[str, Any], heading: str, text: str) -> str:
    lines = ["---"]
    for key in ("id", "kind", "status", "title", "created", "asserted_by"):
        lines.append(f"{key}: {record[key]}")
    for key in ("harness", "model", "session"):
        if record.get(key):
            lines.append(f"{key}: {record[key]}")
    for key in ("evidence", "files"):
        if record.get(key):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in record[key])
    lines.extend(
        ["---", "", f"# {record['id']}: {record['title']}", "", f"## {heading}", "", text, ""]
    )
    return "\n".join(lines)


def registry_entry(record: dict[str, Any], path: Path, context: Path, text: str) -> str:
    spec = RECORD_SPECS[record["kind"]]
    summary = " ".join(text.split())
    if len(summary) > 240:
        summary = summary[:237].rstrip() + "..."
    relative = path.relative_to(context).as_posix()
    return "\n".join(
        [
            f"## {record['id']}: {record['title']}",
            "",
            f"- Status: `{record['status']}`",
            f"- Date: {record['created']}",
            f"- {spec['registry_label']}: {summary}",
            f"- Detail: [{record['id']}]({relative})",
            "",
        ]
    )


def refresh_index(registry: Path, content: str) -> str:
    """Keep the derived decision index current in the same write."""
    if registry.name != "DECISIONS.md":
        return content
    script = Path(__file__).with_name("context_index.py")
    try:
        spec = importlib.util.spec_from_file_location("project_context_index", script)
        if spec is None or spec.loader is None:
            return content
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        registry_spec = next(item for item in module.REGISTRIES if item["file"] == registry.name)
        return module.rebuild(content, registry_spec)
    except (OSError, SyntaxError, ImportError, StopIteration):
        return content


def build(target: Path, args: argparse.Namespace) -> dict[str, Any]:
    target = target.resolve()
    context = target / CONTEXT_DIRNAME
    if not context.is_dir() or context.is_symlink():
        return {"status": "refused", "reason": "no project-context/ here; run `project-context init` first"}
    spec = RECORD_SPECS[args.kind]
    directory = context / spec["directory"]
    if not directory.is_dir() or directory.is_symlink():
        return {
            "status": "refused",
            "reason": f"project-context/{spec['directory']}/ is missing; this record needs the full profile",
        }
    title = " ".join(args.title.split()).strip().rstrip(".")
    text = args.text.strip()
    if not title or not text:
        return {"status": "refused", "reason": "--title and --text must both contain content"}
    if args.actor and not ACTOR_PATTERN.match(args.actor):
        return {"status": "refused", "reason": f"--actor {args.actor!r} is not `person:<name>` or `agent:<name>`"}
    if args.session and not SESSION_PATTERN.match(args.session):
        return {"status": "refused", "reason": f"--session {args.session!r} is not `session:<harness>:<id>`"}
    status = args.status or spec["default_status"]
    if status not in spec["statuses"]:
        return {
            "status": "refused",
            "reason": f"--status {status!r} is not valid for {args.kind}; use " + ", ".join(spec["statuses"]),
        }

    existing = records(context)
    for path, fields in existing:
        if fields.get("kind") == args.kind and fields.get("title", "").casefold() == title.casefold():
            return {"status": "unchanged", "path": str(path), "id": fields.get("id", "")}

    record_id = args.record_id or next_id(context, spec["prefix"], existing)
    expected = re.compile(rf"^{re.escape(spec['prefix'])}-\d{{3,}}$")
    if not expected.match(record_id):
        return {
            "status": "refused",
            "reason": f"--id {record_id!r} must match {spec['prefix']}-NNN for a {args.kind}",
        }
    if any(fields.get("id") == record_id for _path, fields in existing):
        return {"status": "refused", "reason": f"record ID {record_id} already exists"}

    today = date.today().isoformat()
    record: dict[str, Any] = {
        "id": record_id, "kind": args.kind, "status": status,
        "title": title, "created": today,
    }
    record.update(provenance(target, args))
    destination = directory / f"{record_id}-{slug(title)[:64] or 'record'}.md"
    content = render(record, spec["heading"], text)
    report: dict[str, Any] = {
        "status": "planned", "path": str(destination), "id": record_id,
        "kind": args.kind, "content": content,
    }
    if spec["registry"]:
        registry = context / spec["registry"]
        if not registry.is_file() or registry.is_symlink():
            return {"status": "refused", "reason": f"required registry {registry} is missing or unsafe"}
        addition = registry_entry(record, destination, context, text)
        updated = registry.read_text(encoding="utf-8").rstrip() + "\n\n" + addition
        report.update(
            {
                "registry_path": str(registry),
                "registry_addition": addition,
                "registry_content": refresh_index(registry, updated),
            }
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--kind", choices=RECORD_KINDS, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--text", required=True, help="the durable fact, objective, design, or incident evidence")
    parser.add_argument("--status")
    parser.add_argument("--id", dest="record_id", help="stable ID; generated when omitted")
    parser.add_argument("--evidence", action="append", help="a reference; repeatable")
    parser.add_argument("--files", default="", help="comma-separated paths this record concerns")
    parser.add_argument("--actor", help="person:<name> or agent:<name>; defaults to the git identity")
    parser.add_argument("--session", help="session:<harness>:<id>")
    parser.add_argument("--harness", help="the tool writing this record")
    parser.add_argument("--model", help="the model writing this record")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    report = build(target, args)
    if report["status"] == "refused":
        print(report["reason"], file=sys.stderr)
        return 2
    if report["status"] == "unchanged":
        print(f"record already exists: {report['id']} -> {report['path']}")
        return 0
    if args.dry_run:
        print(f"# record: {report['path']}\n\n{report['content']}", end="")
        if report.get("registry_addition"):
            print(f"\n# registry addition: {report['registry_path']}\n\n{report['registry_addition']}", end="")
        return 0

    destination = Path(report["path"])
    created = False
    try:
        with destination.open("x", encoding="utf-8") as handle:
            handle.write(report["content"])
        created = True
        if report.get("registry_path"):
            Path(report["registry_path"]).write_text(report["registry_content"], encoding="utf-8")
    except OSError as error:
        if created and destination.is_file() and report.get("registry_path"):
            try:
                destination.unlink()
            except OSError:
                pass
        print(f"could not write record: {error}", file=sys.stderr)
        return 2
    suffix = f" and linked {Path(report['registry_path']).name}" if report.get("registry_path") else ""
    print(f"recorded {report['id']} ({report['kind']}) -> {report['path']}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
