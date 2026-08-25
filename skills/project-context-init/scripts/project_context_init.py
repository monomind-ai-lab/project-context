#!/usr/bin/env python3
"""Inspect, review, initialize, and validate repository-local project context."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any


TEMPLATE_VERSION = "0.2.0"
START = "<!-- project-context:start -->"
END = "<!-- project-context:end -->"
MANAGED_BLOCK = """<!-- project-context:start -->
## Project Context

Before substantial repository work, read `project-context/SKILL.md` and
`project-context/NOW.md`, then search `project-context/DECISIONS.md` and
`project-context/LEARNINGS.md` for relevant constraints and evidence. Update
project context at meaningful milestones and handoffs. Treat generated indexes
and wikis as auxiliary views, not authority.
<!-- project-context:end -->"""

INSTRUCTION_NAMES = ("AGENTS.md", "agents.md", "CLAUDE.md", "claude.md")
CORE_TEMPLATE_PATHS = {"README.md", "SKILL.md", "NOW.md", "DECISIONS.md", "LEARNINGS.md"}
EXCLUDED_SCAN_PARTS = {
    ".git", "node_modules", "vendor", "dist", "build", "coverage",
    "graphify-out", "openwiki", "__pycache__",
}
DOCUMENT_ROOTS = {"docs", "documentation", ".claude", ".codex", ".agents"}
DIRECTORY_ROLES = {
    "memory": ("general_memory", "strong"),
    "memories": ("general_memory", "strong"),
    ".memory": ("general_memory", "strong"),
    "context": ("general_memory", "possible"),
    "project-memory": ("general_memory", "strong"),
    "project_memory": ("general_memory", "strong"),
    "decisions": ("decisions", "strong"),
    "decision-records": ("decisions", "strong"),
    "adr": ("decisions", "strong"),
    "adrs": ("decisions", "strong"),
    "architecture-decisions": ("decisions", "strong"),
    "learnings": ("learnings", "strong"),
    "lessons": ("learnings", "strong"),
    "solutions": ("learnings", "possible"),
    "retrospectives": ("learnings", "possible"),
    "tasks": ("tasks", "possible"),
    "plans": ("tasks", "possible"),
    "progress": ("tasks", "possible"),
    "agent_logs": ("tasks", "strong"),
    "agent-logs": ("tasks", "strong"),
    "designs": ("designs", "possible"),
    "specs": ("designs", "possible"),
    "specifications": ("designs", "possible"),
    "rfcs": ("designs", "possible"),
    "incidents": ("incidents", "strong"),
    "postmortems": ("incidents", "strong"),
    "post-mortems": ("incidents", "strong"),
}
FILE_ROLES = {
    "now.md": ("current_state", "strong"),
    "current.md": ("current_state", "strong"),
    "current-state.md": ("current_state", "strong"),
    "status.md": ("current_state", "possible"),
    "project-status.md": ("current_state", "strong"),
    "handoff.md": ("current_state", "strong"),
    "decisions.md": ("decisions", "strong"),
    "decision-log.md": ("decisions", "strong"),
    "learnings.md": ("learnings", "strong"),
    "lessons.md": ("learnings", "strong"),
    "tasks.md": ("tasks", "possible"),
    "plan.md": ("tasks", "possible"),
    "roadmap.md": ("tasks", "possible"),
    "incidents.md": ("incidents", "strong"),
    "postmortems.md": ("incidents", "strong"),
}
ROLE_DESTINATIONS = {
    "current_state": "project-context/NOW.md",
    "decisions": "project-context/DECISIONS.md and project-context/decisions/",
    "learnings": "project-context/LEARNINGS.md",
    "tasks": "project-context/tasks/",
    "designs": "project-context/designs/",
    "incidents": "project-context/incidents/",
    "general_memory": "the relevant project-context registries and evidence folders",
}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def template_root() -> Path:
    return skill_root() / "assets" / "project-context"


def template_files(profile: str) -> list[Path]:
    root = template_root()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if profile == "core":
        return [path for path in files if str(path.relative_to(root)) in CORE_TEMPLATE_PATHS]
    return files


def metadata_content(profile: str) -> str:
    return json.dumps(
        {"authority": "tracked-markdown", "profile": profile, "template_version": TEMPLATE_VERSION},
        indent=2,
        sort_keys=True,
    ) + "\n"


def instruction_paths(target: Path) -> list[Path]:
    supported = {name.casefold() for name in INSTRUCTION_NAMES}
    return sorted(
        (path for path in target.iterdir() if path.name.casefold() in supported),
        key=lambda path: path.name,
    )


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def add_file_action(actions: list[dict[str, Any]], destination: Path, content: str) -> None:
    if not destination.exists():
        actions.append({"kind": "create", "path": str(destination), "content": content})
        return
    if destination.is_file() and not destination.is_symlink():
        try:
            current = destination.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            current = None
        if current == content:
            actions.append({"kind": "unchanged", "path": str(destination), "reason": "matches source"})
            return
        actions.append(
            {
                "kind": "preserve_existing",
                "path": str(destination),
                "reason": "existing content differs; review deliberately",
            }
        )
        return
    actions.append(
        {
            "kind": "preserve_existing",
            "path": str(destination),
            "reason": "existing path is not a regular file",
        }
    )


def instruction_plan(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {"kind": "conflict", "path": str(path), "reason": "root harness instruction is a symlink"}
    if not path.is_file():
        return {"kind": "conflict", "path": str(path), "reason": "root harness instruction is not a regular file"}
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            original = handle.read()
    except UnicodeDecodeError:
        return {"kind": "conflict", "path": str(path), "reason": "root harness instruction is not valid UTF-8"}
    newline = "\r\n" if original.count("\r\n") and original.count("\n") == original.count("\r\n") else "\n"
    managed_block = MANAGED_BLOCK.replace("\n", newline)
    starts, ends = original.count(START), original.count(END)
    if starts != ends or starts > 1:
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": f"managed markers are malformed or duplicated ({starts} start, {ends} end)",
        }
    if starts == 0:
        separator = "" if not original else (newline if original.endswith(("\n", "\r")) else newline * 2)
        return {"kind": "append_managed_block", "path": str(path), "content": original + separator + managed_block + newline}
    start_index, raw_end_index = original.index(START), original.index(END)
    if raw_end_index < start_index:
        return {"kind": "conflict", "path": str(path), "reason": "managed end marker appears before start marker"}
    end_index = raw_end_index + len(END)
    if original[start_index:end_index] == managed_block:
        return {"kind": "unchanged", "path": str(path), "reason": "managed block is current"}
    return {
        "kind": "update_managed_block",
        "path": str(path),
        "content": original[:start_index] + managed_block + original[end_index:],
    }


def detect_tools(target: Path) -> dict[str, dict[str, Any]]:
    harnesses = [path for path in instruction_paths(target) if path.is_file() and not path.is_symlink()]
    harness_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in harnesses)
    codex_config = target / ".codex" / "config.toml"
    gitnexus: list[str] = []
    if shutil.which("gitnexus"):
        gitnexus.append("gitnexus CLI on PATH")
    for relative in (".gitnexus/gitnexus.json", ".gitnexus/meta.json", ".gitnexus/run.cjs", ".gitnexusrc"):
        if (target / relative).exists():
            gitnexus.append(relative)
    if "<!-- gitnexus:start -->" in harness_text:
        gitnexus.append("GitNexus managed harness block")
    if codex_config.is_file() and "gitnexus" in codex_config.read_text(encoding="utf-8", errors="replace").lower():
        gitnexus.append("project Codex GitNexus configuration")
    graphify: list[str] = []
    if shutil.which("graphify"):
        graphify.append("graphify CLI on PATH")
    for relative in (
        "graphify-out/graph.json", "graphify-out/.graphify_root", "graphify-out/.graphify_python",
        ".graphifyignore", ".codex/skills/graphify/SKILL.md", ".agents/skills/graphify/SKILL.md",
    ):
        if (target / relative).exists():
            graphify.append(relative)
    codex_hooks = target / ".codex" / "hooks.json"
    if codex_hooks.is_file() and "graphify" in codex_hooks.read_text(encoding="utf-8", errors="replace").lower():
        graphify.append("project Codex Graphify hook configuration")
    openwiki: list[str] = []
    if shutil.which("openwiki"):
        openwiki.append("openwiki CLI on PATH")
    for relative in (
        "openwiki/index.md", "openwiki/.last-update.json", "openwiki/.claims", "openwiki/.run.json",
        "openwiki/INSTRUCTIONS.md", ".openwikiignore", ".agents/skills/openwiki",
    ):
        if (target / relative).exists():
            openwiki.append(relative)
    if "<!-- OPENWIKI:START -->" in harness_text:
        openwiki.append("OpenWiki managed harness block")
    if codex_config.is_file() and "openwiki" in codex_config.read_text(encoding="utf-8", errors="replace").lower():
        openwiki.append("project Codex OpenWiki configuration")
    workflows = target / ".github" / "workflows"
    if workflows.is_dir() and any("openwiki" in path.name.lower() for path in workflows.iterdir()):
        openwiki.append("OpenWiki GitHub workflow")
    return {
        "gitnexus": {"detected": bool(gitnexus), "signals": gitnexus},
        "graphify": {"detected": bool(graphify), "signals": graphify},
        "openwiki": {"detected": bool(openwiki), "signals": openwiki},
    }


def consolidation_candidates(target: Path, limit: int = 5000) -> tuple[list[dict[str, str]], bool]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    truncated = False
    scanned = 0

    def consider(path: Path, kind: str) -> None:
        relative = path.relative_to(target)
        parts = tuple(part.casefold() for part in relative.parts)
        in_doc_location = len(parts) == 1 or parts[0] in DOCUMENT_ROOTS
        role_info = (
            DIRECTORY_ROLES.get(path.name.casefold())
            if kind == "directory" and in_doc_location
            else FILE_ROLES.get(path.name.casefold())
            if kind == "file" and in_doc_location
            else None
        )
        if not role_info:
            return
        relative_text = str(relative)
        if relative_text in seen:
            return
        seen.add(relative_text)
        role, confidence = role_info
        destination = ROLE_DESTINATIONS[role]
        candidates.append(
            {
                "confidence": confidence,
                "kind": kind,
                "path": relative_text,
                "reason": f"name and location suggest {role.replace('_', ' ')} content",
                "role": role,
                "suggestion": (
                    f"Review for overlap with {destination}; propose links or a provenance-preserving "
                    "migration, but do not move or delete automatically."
                ),
            }
        )

    for root_text, directory_names, file_names in os.walk(target, followlinks=False):
        root = Path(root_text)
        relative_root = root.relative_to(target)
        root_parts = tuple(part.casefold() for part in relative_root.parts)
        if root_parts and (
            root_parts[0] == "project-context"
            or any(part in EXCLUDED_SCAN_PARTS for part in root_parts)
            or ("skills" in root_parts and any(part in {".agents", ".codex", ".claude"} for part in root_parts))
        ):
            directory_names[:] = []
            continue
        directory_names[:] = [
            name
            for name in directory_names
            if name.casefold() not in EXCLUDED_SCAN_PARTS
            and not (root == target and name.casefold() == "project-context")
            and not (root / name).is_symlink()
        ]
        for name in directory_names:
            scanned += 1
            if scanned > limit:
                truncated = True
                break
            consider(root / name, "directory")
        if truncated:
            break
        for name in file_names:
            scanned += 1
            if scanned > limit:
                truncated = True
                break
            path = root / name
            if not path.is_symlink():
                consider(path, "file")
        if truncated:
            break
    candidates.sort(key=lambda item: (item["confidence"] != "strong", item["role"], item["path"]))
    return candidates, truncated


def inspect(target: Path) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    files: list[str] = []
    if context.is_dir() and not context.is_symlink():
        files = sorted(str(path.relative_to(context)) for path in context.rglob("*") if path.is_file())
    if context.is_symlink():
        state = "conflict_symlink"
    elif not context.exists():
        state = "absent"
    elif context.is_dir():
        state = "directory"
    else:
        state = "conflict_non_directory"
    candidates, truncated = consolidation_candidates(target)
    return {
        "target": str(target),
        "git_repository": (target / ".git").exists(),
        "project_context": {"state": state, "files": files},
        "instruction_files": [path.name for path in instruction_paths(target)],
        "legacy_candidates": sorted({item["path"] for item in candidates if item["role"] == "general_memory"}),
        "consolidation": {
            "candidates": candidates,
            "count": len(candidates),
            "scan_truncated": truncated,
            "rule": "suggest only; never move, merge, rewrite, or delete automatically",
        },
        "tools": detect_tools(target),
    }


def plan_skill_install(target: Path, actions: list[dict[str, Any]]) -> None:
    source_parent = skill_root().parent
    for skill_name in ("project-context", "project-context-init"):
        source = source_parent / skill_name
        destination_root = target / ".agents" / "skills" / skill_name
        destination_chain = (target / ".agents", target / ".agents" / "skills", destination_root)
        if any(path.is_symlink() for path in destination_chain) or (
            destination_root.exists() and not destination_root.is_dir()
        ):
            actions.append({"kind": "conflict", "path": str(destination_root), "reason": "skill destination is unsafe"})
            continue
        for source_file in sorted(path for path in source.rglob("*") if path.is_file()):
            if "__pycache__" in source_file.parts or source_file.name == ".DS_Store":
                continue
            add_file_action(
                actions,
                destination_root / source_file.relative_to(source),
                source_file.read_text(encoding="utf-8"),
            )


def build_plan(target: Path, profile: str = "full", install_skills: bool = False) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    actions: list[dict[str, Any]] = []
    if context.is_symlink():
        actions.append({"kind": "conflict", "path": str(context), "reason": "project-context is a symlink"})
    elif context.exists() and not context.is_dir():
        actions.append({"kind": "conflict", "path": str(context), "reason": "project-context is not a directory"})
    else:
        for source in template_files(profile):
            relative = source.relative_to(template_root())
            content = source.read_text(encoding="utf-8")
            if str(relative) == "NOW.md":
                content = content.replace("YYYY-MM-DD", date.today().isoformat(), 1)
            add_file_action(actions, context / relative, content)
        add_file_action(actions, context / ".project-context.json", metadata_content(profile))
    harnesses = instruction_paths(target)
    if harnesses:
        actions.extend(instruction_plan(path) for path in harnesses)
    else:
        actions.append({"kind": "create", "path": str(target / "AGENTS.md"), "content": MANAGED_BLOCK + "\n"})
    if install_skills:
        plan_skill_install(target, actions)
    report = inspect(target)
    report.update({"profile": profile, "install_skills": install_skills, "actions": actions})
    report["summary"] = {
        kind: sum(action["kind"] == kind for action in actions)
        for kind in sorted({action["kind"] for action in actions})
    }
    report["has_conflicts"] = any(action["kind"] == "conflict" for action in actions)
    return report


def public_report(report: dict[str, Any]) -> dict[str, Any]:
    clean = json.loads(json.dumps(report))
    for action in clean.get("actions", []):
        action.pop("content", None)
    return clean


def apply_plan(report: dict[str, Any]) -> int:
    if report["has_conflicts"]:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
        print("Refusing to write because the plan contains conflicts.", file=sys.stderr)
        return 2
    for action in report["actions"]:
        if action["kind"] in {"create", "append_managed_block", "update_managed_block"}:
            atomic_write(Path(action["path"]), action["content"])
    refreshed = build_plan(Path(report["target"]), report["profile"], report["install_skills"])
    print(json.dumps(public_report(refreshed), indent=2, sort_keys=True))
    return 0


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
    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "target": str(target),
        "template_version": TEMPLATE_VERSION,
        "status": "error" if errors else ("warning" if warnings else "healthy"),
        "summary": {"errors": errors, "warnings": warnings},
        "issues": issues,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("inspect", "inspect without writing"), ("review", "find consolidation candidates")):
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--target", default=".", type=Path)
    doctor_parser = subparsers.add_parser("doctor", help="validate project-context health")
    doctor_parser.add_argument("--target", default=".", type=Path)
    doctor_parser.add_argument("--stale-days", default=30, type=int)
    init_parser = subparsers.add_parser("init", help="plan or apply initialization")
    init_parser.add_argument("--target", default=".", type=Path)
    init_parser.add_argument("--profile", choices=("core", "full"), default="full")
    init_parser.add_argument("--install-skills", action="store_true")
    mode = init_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    if args.command == "inspect":
        print(json.dumps(inspect(target), indent=2, sort_keys=True))
        return 0
    if args.command == "review":
        report = inspect(target)
        print(json.dumps({"target": report["target"], "consolidation": report["consolidation"]}, indent=2, sort_keys=True))
        return 0
    if args.command == "doctor":
        report = doctor(target, args.stale_days)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["summary"]["errors"] else 0
    report = build_plan(target, args.profile, args.install_skills)
    if args.dry_run:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
        return 2 if report["has_conflicts"] else 0
    return apply_plan(report)


if __name__ == "__main__":
    raise SystemExit(main())
