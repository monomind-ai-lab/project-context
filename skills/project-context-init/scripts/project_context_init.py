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


TEMPLATE_VERSION = "0.3.0"
START = "<!-- project-context:start -->"
END = "<!-- project-context:end -->"
MANAGED_BLOCK = """<!-- project-context:start -->
## Project Context

Before substantial repository work, read `project-context/SKILL.md` and
`project-context/NOW.md`, then search `project-context/DECISIONS.md` and
`project-context/LEARNINGS.md` for relevant constraints and evidence. Update
project context at meaningful milestones and handoffs. Confirm important claims
against the repository's primary artifacts and evidence. Treat generated indexes
and wikis as auxiliary views, not authority.
<!-- project-context:end -->"""

INSTRUCTION_NAMES = ("AGENTS.md", "agents.md", "CLAUDE.md", "claude.md")
CORE_TEMPLATE_PATHS = {"README.md", "SKILL.md", "NOW.md", "DECISIONS.md", "LEARNINGS.md"}
EXCLUDED_SCAN_PARTS = {
    ".git", "node_modules", "vendor", "dist", "build", "coverage",
    "graphify-out", "openwiki", "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", ".next", "target", "out", "work", "outputs",
}
REPOSITORY_TYPES = ("auto", "code", "document", "research", "writing", "mixed", "general")
CODE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".ex", ".exs", ".go", ".h", ".hpp",
    ".html", ".java", ".js", ".jsx", ".kt", ".kts", ".lua", ".php", ".py",
    ".rb", ".rs", ".scala", ".sh", ".sql", ".swift", ".ts", ".tsx", ".vue",
}
CODE_MANIFESTS = {
    "cargo.toml", "composer.json", "deno.json", "gemfile", "go.mod", "mix.exs",
    "package.json", "pom.xml", "pyproject.toml", "requirements.txt", "setup.py",
}
DOCUMENT_EXTENSIONS = {".doc", ".docx", ".md", ".odt", ".pdf", ".ppt", ".pptx", ".rtf", ".txt", ".xls", ".xlsx"}
RESEARCH_EXTENSIONS = {".bib", ".csv", ".ipynb", ".parquet", ".ris", ".sav", ".tsv"}
WRITING_EXTENSIONS = {".fountain", ".scriv", ".tex"}
DOCUMENT_DIRECTORIES = {"docs", "documentation", "handbook", "minutes", "policies", "reports"}
RESEARCH_DIRECTORIES = {"datasets", "experiments", "literature", "papers", "research"}
WEAK_RESEARCH_DIRECTORIES = {"analysis", "data", "references"}
WRITING_DIRECTORIES = {"book", "chapters", "drafts", "essays", "manuscript", "screenplay", "stories"}
DOCUMENT_ROOTS = {"docs", "documentation", ".claude", ".codex", ".agents"}
DIRECTORY_ROLES = {
    "memory": ("general_memory", "strong"),
    "memories": ("general_memory", "strong"),
    ".memory": ("general_memory", "strong"),
    "context": ("general_memory", "possible"),
    "project-memory": ("general_memory", "strong"),
    "project_memory": ("general_memory", "strong"),
    "project-notes": ("general_memory", "strong"),
    "research-notes": ("general_memory", "possible"),
    "editorial-notes": ("general_memory", "possible"),
    "worldbuilding": ("general_memory", "possible"),
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
    "outlines": ("designs", "possible"),
    "briefs": ("designs", "possible"),
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
    "editorial-status.md": ("current_state", "strong"),
    "decisions.md": ("decisions", "strong"),
    "decision-log.md": ("decisions", "strong"),
    "learnings.md": ("learnings", "strong"),
    "lessons.md": ("learnings", "strong"),
    "tasks.md": ("tasks", "possible"),
    "plan.md": ("tasks", "possible"),
    "roadmap.md": ("tasks", "possible"),
    "research-log.md": ("tasks", "possible"),
    "editorial-plan.md": ("tasks", "possible"),
    "outline.md": ("designs", "possible"),
    "project-notes.md": ("general_memory", "strong"),
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


def classify_repository(target: Path, limit: int = 5000) -> dict[str, Any]:
    scores = {kind: 0.0 for kind in ("code", "document", "research", "writing")}
    signal_counts: dict[str, dict[str, int]] = {kind: {} for kind in scores}
    scanned = 0

    def add(kind: str, weight: float, signal: str) -> None:
        scores[kind] += weight
        signal_counts[kind][signal] = signal_counts[kind].get(signal, 0) + 1

    for root_text, directory_names, file_names in os.walk(target, followlinks=False):
        root = Path(root_text)
        relative_root = root.relative_to(target)
        root_parts = tuple(part.casefold() for part in relative_root.parts)
        if root_parts and (
            any(part in EXCLUDED_SCAN_PARTS or part == "project-context" for part in root_parts)
            or ("skills" in root_parts and any(part in {".agents", ".codex", ".claude"} for part in root_parts))
        ):
            directory_names[:] = []
            continue
        directory_names[:] = [
            name for name in directory_names
            if name.casefold() not in EXCLUDED_SCAN_PARTS
            and name.casefold() != "project-context"
            and not (root / name).is_symlink()
        ]
        for name in directory_names:
            folded = name.casefold()
            if folded in DOCUMENT_DIRECTORIES:
                add("document", 3.0, f"directory:{folded}")
            if folded in RESEARCH_DIRECTORIES:
                add("research", 4.0, f"directory:{folded}")
            elif folded in WEAK_RESEARCH_DIRECTORIES:
                add("research", 1.0, f"directory:{folded}")
            if folded in WRITING_DIRECTORIES:
                add("writing", 4.0, f"directory:{folded}")
        for name in file_names:
            scanned += 1
            if scanned > limit:
                break
            path = root / name
            if path.is_symlink():
                continue
            folded = name.casefold()
            suffix = path.suffix.casefold()
            if folded in CODE_MANIFESTS:
                add("code", 4.0, "project-manifest")
            if suffix in CODE_EXTENSIONS:
                add("code", 1.0, f"extension:{suffix}")
            if suffix in DOCUMENT_EXTENSIONS:
                weight = 0.25 if suffix in {".md", ".txt"} else 2.0
                if root_parts and root_parts[0] in DOCUMENT_DIRECTORIES:
                    weight += 0.5
                add("document", weight, f"extension:{suffix}")
            if suffix in RESEARCH_EXTENSIONS:
                add("research", 2.0, f"extension:{suffix}")
            if suffix in WRITING_EXTENSIONS:
                add("writing", 2.0, f"extension:{suffix}")
            if any(part in WRITING_DIRECTORIES for part in root_parts) and suffix in DOCUMENT_EXTENSIONS:
                add("writing", 1.5, "document-in-writing-tree")
            if any(part in RESEARCH_DIRECTORIES for part in root_parts) and suffix in DOCUMENT_EXTENSIONS:
                add("research", 1.0, "document-in-research-tree")
        if scanned > limit:
            break

    ranked = sorted(scores, key=lambda kind: scores[kind], reverse=True)
    highest, second = ranked[0], ranked[1]
    if scores[highest] < 2.0:
        selected = "general"
    elif scores[second] >= 3.0 and scores[second] >= scores[highest] * 0.75:
        selected = "mixed"
    else:
        selected = highest
    confidence = "strong" if scores[highest] >= 6.0 and scores[highest] - scores[second] >= 2.0 else "possible"
    return {
        "type": selected,
        "confidence": confidence if selected != "general" else "unknown",
        "scores": {kind: round(value, 2) for kind, value in scores.items()},
        "signals": {kind: values for kind, values in signal_counts.items() if values},
        "scan_truncated": scanned > limit,
    }


def repository_classification(target: Path, requested: str = "auto") -> dict[str, Any]:
    inferred = classify_repository(target)
    if requested == "auto":
        return inferred
    return {
        **inferred,
        "type": requested,
        "confidence": "declared",
        "inferred_type": inferred["type"],
    }


def optional_tool_guidance(repository: dict[str, Any], tools: dict[str, dict[str, Any]]) -> dict[str, Any]:
    repo_type = repository["type"]
    scores = repository.get("scores", {})
    relevance: dict[str, tuple[str, str]] = {}
    deferred: dict[str, str] = {}
    if repo_type == "code" and scores.get("code", 0) >= 3:
        relevance = {
            "gitnexus": ("recommended", "The repository is code-centered, so symbol and impact analysis can add value."),
        }
        deferred["openwiki"] = "Consider only after a clear audience and stable need for generated navigation are established."
    elif repo_type == "document" and scores.get("document", 0) >= 6:
        relevance = {
            "graphify": ("recommended", "Cross-file concept and evidence relationships fit this repository type."),
        }
        deferred["openwiki"] = "Consider only when the corpus has a clear audience for a maintained generated browse layer."
    elif repo_type == "research" and scores.get("research", 0) >= 6:
        relevance = {
            "graphify": ("recommended", "Cross-source, data, and evidence relationships fit this repository type."),
        }
        deferred["openwiki"] = "Defer until claims and structure are stable and generated navigation has a clear audience."
    elif repo_type == "writing" and scores.get("writing", 0) >= 8:
        relevance = {
            "graphify": ("optional", "A relationship graph may help a large multi-file manuscript or story corpus."),
        }
    elif repo_type == "mixed":
        if sum(value > 0 for value in scores.values()) >= 2:
            relevance["graphify"] = ("recommended", "The repository spans artifact types that benefit from cross-file relationships.")
        if repository.get("scores", {}).get("code", 0) >= 3:
            relevance["gitnexus"] = ("optional", "The mixed repository contains enough code for structural analysis to be useful.")
        deferred["openwiki"] = "Consider only after collaborators demonstrate a need for maintained generated navigation."

    entries: dict[str, dict[str, Any]] = {}
    proposal_order: list[str] = []
    for tool_name in ("gitnexus", "graphify", "openwiki"):
        tool_state = tools[tool_name]["state"]
        if tool_state == "project-configured":
            entries[tool_name] = {
                "status": "already-configured",
                "relevance": relevance.get(tool_name, ("not-applicable", "No change should be proposed for this repository type."))[0],
                "reason": "Existing configuration is reported for awareness; do not reinstall it.",
            }
        elif tool_name in relevance:
            level, reason = relevance[tool_name]
            action = "offer-project-configuration" if tool_state == "available-unconfigured" else "offer-installation"
            entries[tool_name] = {
                "status": "ask-independently",
                "action": action,
                "relevance": level,
                "reason": reason,
            }
            proposal_order.append(tool_name)
        elif tool_name in deferred:
            entries[tool_name] = {
                "status": "deferred",
                "relevance": "conditional",
                "reason": deferred[tool_name],
            }
        else:
            entries[tool_name] = {
                "status": "do-not-propose",
                "relevance": "not-applicable",
                "reason": "This add-on is unlikely to help the classified repository type.",
            }
    return {
        "repository_type": repo_type,
        "proposal_order": proposal_order,
        "tools": entries,
        "rule": "Ask only about tools in proposal_order, one at a time; never install or configure without authorization.",
    }


def metadata_content(profile: str, repo_type: str) -> str:
    return json.dumps(
        {
            "authority": "tracked-markdown",
            "profile": profile,
            "repository_type": repo_type,
            "template_version": TEMPLATE_VERSION,
        },
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
    gitnexus_cli = bool(shutil.which("gitnexus"))
    gitnexus: list[str] = []
    for relative in (".gitnexus/gitnexus.json", ".gitnexus/meta.json", ".gitnexus/run.cjs", ".gitnexusrc"):
        if (target / relative).exists():
            gitnexus.append(relative)
    if "<!-- gitnexus:start -->" in harness_text:
        gitnexus.append("GitNexus managed harness block")
    if codex_config.is_file() and "gitnexus" in codex_config.read_text(encoding="utf-8", errors="replace").lower():
        gitnexus.append("project Codex GitNexus configuration")
    graphify_cli = bool(shutil.which("graphify"))
    graphify: list[str] = []
    for relative in (
        "graphify-out/graph.json", "graphify-out/.graphify_root", "graphify-out/.graphify_python",
        ".graphifyignore", ".codex/skills/graphify/SKILL.md", ".agents/skills/graphify/SKILL.md",
    ):
        if (target / relative).exists():
            graphify.append(relative)
    codex_hooks = target / ".codex" / "hooks.json"
    if codex_hooks.is_file() and "graphify" in codex_hooks.read_text(encoding="utf-8", errors="replace").lower():
        graphify.append("project Codex Graphify hook configuration")
    openwiki_cli = bool(shutil.which("openwiki"))
    openwiki: list[str] = []
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
    def result(cli_available: bool, project_signals: list[str]) -> dict[str, Any]:
        if project_signals:
            state = "project-configured"
        elif cli_available:
            state = "available-unconfigured"
        else:
            state = "not-detected"
        signals = (["CLI on PATH"] if cli_available else []) + project_signals
        return {
            "detected": cli_available or bool(project_signals),
            "state": state,
            "cli_available": cli_available,
            "project_configured": bool(project_signals),
            "signals": signals,
        }

    return {
        "gitnexus": result(gitnexus_cli, gitnexus),
        "graphify": result(graphify_cli, graphify),
        "openwiki": result(openwiki_cli, openwiki),
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


def inspect(target: Path, repo_type: str = "auto") -> dict[str, Any]:
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
    repository = repository_classification(target, repo_type)
    tools = detect_tools(target)
    return {
        "target": str(target),
        "git_repository": (target / ".git").exists(),
        "repository": repository,
        "project_context": {"state": state, "files": files},
        "instruction_files": [path.name for path in instruction_paths(target)],
        "legacy_candidates": sorted({item["path"] for item in candidates if item["role"] == "general_memory"}),
        "consolidation": {
            "candidates": candidates,
            "count": len(candidates),
            "scan_truncated": truncated,
            "rule": "suggest only; never move, merge, rewrite, or delete automatically",
        },
        "tools": tools,
        "optional_tool_guidance": optional_tool_guidance(repository, tools),
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


def build_plan(
    target: Path,
    profile: str = "full",
    install_skills: bool = False,
    repo_type: str = "auto",
    repository_stage: str = "existing",
) -> dict[str, Any]:
    target = target.resolve()
    context = target / "project-context"
    actions: list[dict[str, Any]] = []
    repository = repository_classification(target, repo_type)
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
        add_file_action(
            actions,
            context / ".project-context.json",
            metadata_content(profile, repository["type"]),
        )
    harnesses = instruction_paths(target)
    if harnesses:
        actions.extend(instruction_plan(path) for path in harnesses)
    else:
        actions.append({"kind": "create", "path": str(target / "AGENTS.md"), "content": MANAGED_BLOCK + "\n"})
    if install_skills:
        plan_skill_install(target, actions)
    report = inspect(target, repo_type)
    report.update(
        {
            "profile": profile,
            "install_skills": install_skills,
            "repository_stage": repository_stage,
            "actions": actions,
        }
    )
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
    refreshed = build_plan(
        Path(report["target"]),
        report["profile"],
        report["install_skills"],
        report["repository"]["type"],
        report["repository_stage"],
    )
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
        subparser.add_argument("--repo-type", choices=REPOSITORY_TYPES, default="auto")
    doctor_parser = subparsers.add_parser("doctor", help="validate project-context health")
    doctor_parser.add_argument("--target", default=".", type=Path)
    doctor_parser.add_argument("--stale-days", default=30, type=int)
    init_parser = subparsers.add_parser("init", help="plan or apply initialization")
    init_parser.add_argument("--target", default=".", type=Path)
    init_parser.add_argument("--profile", choices=("core", "full"), default="full")
    init_parser.add_argument("--repo-type", choices=REPOSITORY_TYPES, default="auto")
    init_parser.add_argument(
        "--repository-stage",
        choices=("brand-new", "existing"),
        default="existing",
    )
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
        print(json.dumps(inspect(target, args.repo_type), indent=2, sort_keys=True))
        return 0
    if args.command == "review":
        report = inspect(target, args.repo_type)
        print(
            json.dumps(
                {
                    "target": report["target"],
                    "repository": report["repository"],
                    "consolidation": report["consolidation"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "doctor":
        report = doctor(target, args.stale_days)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["summary"]["errors"] else 0
    report = build_plan(
        target,
        args.profile,
        args.install_skills,
        args.repo_type,
        args.repository_stage,
    )
    if args.dry_run:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
        return 2 if report["has_conflicts"] else 0
    return apply_plan(report)


if __name__ == "__main__":
    raise SystemExit(main())
