#!/usr/bin/env python3
"""Inspect and safely initialize a repository-local project-context package."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any


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
LEGACY_CANDIDATES = (
    "memory",
    ".memory",
    "context",
    "project-memory",
    "project_memory",
    "docs/memory",
    "docs/context",
    ".ijfw/memory",
)


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def template_root() -> Path:
    return skill_root() / "assets" / "project-context"


def template_files() -> list[Path]:
    root = template_root()
    return sorted(path for path in root.rglob("*") if path.is_file())


def instruction_paths(target: Path) -> list[Path]:
    """Return matching directory entries once, including non-file conflicts."""
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


def instruction_plan(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": "root harness instruction is a symlink; resolve it deliberately",
        }
    if not path.is_file():
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": "root harness instruction path exists but is not a regular file",
        }
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            original = handle.read()
    except UnicodeDecodeError:
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": "root harness instruction is not valid UTF-8",
        }
    newline = (
        "\r\n"
        if original.count("\r\n") > 0 and original.count("\n") == original.count("\r\n")
        else "\n"
    )
    managed_block = MANAGED_BLOCK.replace("\n", newline)
    starts = original.count(START)
    ends = original.count(END)
    if starts != ends or starts > 1:
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": f"managed markers are malformed or duplicated ({starts} start, {ends} end)",
        }

    if starts == 0:
        separator = "" if not original else (newline if original.endswith(("\n", "\r")) else newline * 2)
        return {
            "kind": "append_managed_block",
            "path": str(path),
            "content": original + separator + managed_block + newline,
        }

    start_index = original.index(START)
    raw_end_index = original.index(END)
    if raw_end_index < start_index:
        return {
            "kind": "conflict",
            "path": str(path),
            "reason": "managed end marker appears before its start marker",
        }
    end_index = raw_end_index + len(END)
    current = original[start_index:end_index]
    if current == managed_block:
        return {"kind": "unchanged", "path": str(path), "reason": "managed block is current"}

    return {
        "kind": "update_managed_block",
        "path": str(path),
        "content": original[:start_index] + managed_block + original[end_index:],
    }


def detect_tools(target: Path) -> dict[str, dict[str, Any]]:
    harnesses = [path for path in instruction_paths(target) if path.is_file() and not path.is_symlink()]
    harness_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in harnesses
    )

    gitnexus_signals: list[str] = []
    if shutil.which("gitnexus"):
        gitnexus_signals.append("gitnexus CLI on PATH")
    for relative in (
        ".gitnexus/gitnexus.json",
        ".gitnexus/meta.json",
        ".gitnexus/run.cjs",
        ".gitnexusrc",
    ):
        if (target / relative).exists():
            gitnexus_signals.append(relative)
    if "<!-- gitnexus:start -->" in harness_text:
        gitnexus_signals.append("GitNexus managed harness block")
    codex_config = target / ".codex" / "config.toml"
    if codex_config.is_file() and "gitnexus" in codex_config.read_text(
        encoding="utf-8", errors="replace"
    ).lower():
        gitnexus_signals.append("project Codex GitNexus configuration")

    graphify_signals: list[str] = []
    if shutil.which("graphify"):
        graphify_signals.append("graphify CLI on PATH")
    for relative in (
        "graphify-out/graph.json",
        "graphify-out/.graphify_root",
        "graphify-out/.graphify_python",
        ".graphifyignore",
        ".codex/skills/graphify/SKILL.md",
        ".agents/skills/graphify/SKILL.md",
    ):
        if (target / relative).exists():
            graphify_signals.append(relative)
    codex_hooks = target / ".codex" / "hooks.json"
    if codex_hooks.is_file() and "graphify" in codex_hooks.read_text(
        encoding="utf-8", errors="replace"
    ).lower():
        graphify_signals.append("project Codex Graphify hook configuration")

    openwiki_signals: list[str] = []
    if shutil.which("openwiki"):
        openwiki_signals.append("openwiki CLI on PATH")
    for relative in (
        "openwiki/index.md",
        "openwiki/.last-update.json",
        "openwiki/.claims",
        "openwiki/.run.json",
        "openwiki/INSTRUCTIONS.md",
        ".openwikiignore",
        ".agents/skills/openwiki",
    ):
        if (target / relative).exists():
            openwiki_signals.append(relative)
    if "<!-- OPENWIKI:START -->" in harness_text:
        openwiki_signals.append("OpenWiki managed harness block")
    if codex_config.is_file() and "openwiki" in codex_config.read_text(
        encoding="utf-8", errors="replace"
    ).lower():
        openwiki_signals.append("project Codex OpenWiki configuration")
    workflows = target / ".github" / "workflows"
    if workflows.is_dir() and any("openwiki" in path.name.lower() for path in workflows.iterdir()):
        openwiki_signals.append("OpenWiki GitHub workflow")

    return {
        "gitnexus": {"detected": bool(gitnexus_signals), "signals": gitnexus_signals},
        "graphify": {"detected": bool(graphify_signals), "signals": graphify_signals},
        "openwiki": {"detected": bool(openwiki_signals), "signals": openwiki_signals},
    }


def inspect(target: Path) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    legacy = [relative for relative in LEGACY_CANDIDATES if (target / relative).exists()]
    instruction_files = [path.name for path in instruction_paths(target)]
    existing_context: list[str] = []
    if context.is_dir() and not context.is_symlink():
        existing_context = sorted(
            str(path.relative_to(context)) for path in context.rglob("*") if path.is_file()
        )
    if context.is_symlink():
        context_state = "conflict_symlink"
    elif not context.exists():
        context_state = "absent"
    elif context.is_dir():
        context_state = "directory"
    else:
        context_state = "conflict_non_directory"
    return {
        "target": str(target),
        "git_repository": (target / ".git").exists(),
        "project_context": {
            "state": context_state,
            "files": existing_context,
        },
        "instruction_files": instruction_files,
        "legacy_candidates": legacy,
        "tools": detect_tools(target),
    }


def build_plan(target: Path) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    actions: list[dict[str, Any]] = []

    if context.is_symlink():
        actions.append(
            {
                "kind": "conflict",
                "path": str(context),
                "reason": "project-context is a symlink; resolve it deliberately",
            }
        )
    elif context.exists() and not context.is_dir():
        actions.append(
            {
                "kind": "conflict",
                "path": str(context),
                "reason": "project-context exists but is not a directory",
            }
        )
    else:
        for source in template_files():
            relative = source.relative_to(template_root())
            destination = context / relative
            content = source.read_text(encoding="utf-8")
            if not destination.exists():
                actions.append({"kind": "create", "path": str(destination), "content": content})
            elif destination.is_file() and destination.read_text(encoding="utf-8") == content:
                actions.append(
                    {"kind": "unchanged", "path": str(destination), "reason": "matches template"}
                )
            else:
                actions.append(
                    {
                        "kind": "preserve_existing",
                        "path": str(destination),
                        "reason": "existing content differs from template",
                    }
                )

    harness_paths = instruction_paths(target)
    if harness_paths:
        actions.extend(instruction_plan(path) for path in harness_paths)
    else:
        actions.append(
            {
                "kind": "create",
                "path": str(target / "AGENTS.md"),
                "content": MANAGED_BLOCK + "\n",
            }
        )

    report = inspect(target)
    report["actions"] = actions
    report["summary"] = {
        kind: sum(1 for action in actions if action["kind"] == kind)
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
    print(json.dumps(public_report(build_plan(Path(report["target"]))), indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="inspect without writing")
    inspect_parser.add_argument("--target", default=".", type=Path)

    init_parser = subparsers.add_parser("init", help="plan or apply initialization")
    init_parser.add_argument("--target", default=".", type=Path)
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

    report = build_plan(target)
    if args.dry_run:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
        return 2 if report["has_conflicts"] else 0
    return apply_plan(report)


if __name__ == "__main__":
    raise SystemExit(main())
