#!/usr/bin/env python3
"""Inspect, review, initialize, and validate repository-local project context."""

from __future__ import annotations

import argparse
from datetime import date
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Any


SCHEMA = "project-context/1"
# The two products version independently, so the marker names the product that
# wrote it alongside that product's version.
PRODUCT = "project-context"
MARKER_NAME = ".project-context.json"
START = "<!-- project-context:start -->"
END = "<!-- project-context:end -->"
# One text, both files. The block is loaded into every session in the
# repository, so it is held to the L0 budget and says what to do, never what
# the product is. A repository with no Hub simply has no `blueprint/` and no
# `global/`, and those two paragraphs are inert rather than wrong.
#
# It opens with the guardrail because the region is the one part of somebody
# else's file that we rewrite. The markers already make that safe on our side —
# only what sits between them is ever replaced, and a malformed pair is refused
# rather than repaired — but nothing said so to the person or the agent reading
# the file, who saw prose indistinguishable from what their team wrote. A rule
# enforced silently is one that gets broken in good faith.
MANAGED_BLOCK_WORD_BUDGET = 150
MANAGED_BLOCK = """<!-- project-context:start -->
## Project Context

**Managed region.** Project Context rewrites everything between these markers
and nothing outside them — the rest of the file is yours. Leave both markers in
place; a broken pair stops the update rather than being repaired.

Before substantial work, run `project-context context --task "<one line>"`, or
read `project-context/NOW.md` and `project-context/PLAN.md` if the CLI is not
available. Search `DECISIONS.md`, `LEARNINGS.md`, and `QUESTIONS.md` for
constraints touching the files you are about to change.

When planning, read `project-context/blueprint/` first: `EPIC.md` is the goal,
`ARCHITECTURE.md` the shape to keep. Every `PLAN.md` item names the epic item
it serves.

`project-context/global/` and `project-context/blueprint/` are owner-authored
and read-only here. To change one, run `project-context capture --kind
proposal` or file a question in `QUESTIONS.md`; it reaches the owner on their
next pull.

Record decisions, learnings, and questions as they happen with `project-context
capture`.
<!-- project-context:end -->"""

# What a file we create opens with. An install that had to create `AGENTS.md`
# or `CLAUDE.md` used to write the managed block and nothing else, so the
# repository gained a file that begins mid-instruction, with no title, no
# statement of what it is for, and no sign that the rest of it is the team's to
# write. This header sits *outside* the markers, which means we write it once
# and never touch it again — the reader can rewrite every word of it.
CREATED_INSTRUCTION_HEADER = """# Agent instructions

Instructions for anyone working in this repository, person or agent. Project
Context created this file because the repository had none; everything outside
the managed block below is yours to write, and no update will touch it.

"""
INSTRUCTION_NAMES = ("AGENTS.md", "agents.md", "CLAUDE.md", "claude.md")
# Install ensures *both* root instruction files carry the block, creating
# whichever is missing. Updating only the files that happened to exist left a
# Claude-only repository with rules no Claude session ever reads.
INSTRUCTION_ROLES = ("AGENTS.md", "CLAUDE.md")
# Harness-specific skill locations. These hold pointers, never copies: the
# skill itself is installed once, harness-neutral, under .agents/skills/.
HARNESS_POINTER_ROOTS = ((".claude", "skills"),)
# Only the protocol skill is installed into a repository. The initializer stays
# in this checkout: a consuming repository never needs to carry its own copy of
# the installer, and shipping one duplicated the whole template tree.
INSTALLED_SKILL_NAMES = ("project-context",)
SKILL_SCRIPTS_RELATIVE = ".agents/skills/project-context/scripts"
TRIGGER_SCRIPT_RELATIVE = f"{SKILL_SCRIPTS_RELATIVE}/context_triggers.py"
PACKET_SCRIPT_RELATIVE = f"{SKILL_SCRIPTS_RELATIVE}/context_packet.py"
# `SessionStart` does two different jobs and they are separate hooks on
# purpose. The packet is what the session should have read; the trigger report
# is what the session still owes. Emitting the packet first means the state a
# contributor would act on is in the window before anything else is said about
# it. `onboard` rather than `context` because a session start has no task yet.
HOOK_EVENTS = (
    ("SessionStart", PACKET_SCRIPT_RELATIVE, "onboard", "Loading project context"),
    ("SessionStart", TRIGGER_SCRIPT_RELATIVE, "report", "Checking project context"),
    ("Stop", TRIGGER_SCRIPT_RELATIVE, "gate", "Checking project context triggers"),
)
# Hooks this installer owns, identified by the script they call so a repository's
# own hooks are never dropped.
OWNED_HOOK_SCRIPTS = ("context_triggers.py", "context_packet.py")
# The core profile's files. SKILL.md is listed here but has no template under
# assets/: build_plan writes it from the project-context skill's own SKILL.md.
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


VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+)*(?:[-+.][0-9A-Za-z.-]+)?$")
PROJECT_ID_PATTERN = re.compile(r"[^a-z0-9]+")


def version_file() -> Path | None:
    """The one `VERSION` file this copy of the script belongs to, or None.

    There is a single version number — the package version — and the scripts
    read it rather than each carrying a constant of their own. `VERSION` sits
    beside `skills/` both in a checkout and in the wheel bundle. The lookup is
    exact rather than a walk up the tree, because a consuming repository may
    well have a `VERSION` of its own and reporting that one would be worse than
    reporting nothing.
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


def project_id(target: Path) -> str:
    """A stable, portable identifier for this project.

    The folder name, slugified: it is the one name every clone agrees on, and
    it carries no absolute path, no host, and no account.
    """
    slug = PROJECT_ID_PATTERN.sub("-", target.name.casefold()).strip("-")
    return slug or "project"


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def template_root() -> Path:
    return skill_root() / "assets" / "project-context"


def protocol_source() -> Path:
    """The single copy of the protocol text, installed in two places.

    `.agents/skills/project-context/SKILL.md` and the instance at
    `project-context/SKILL.md` are the same bytes. Keeping a second copy under
    `assets/` meant two hand-maintained texts that drifted apart, so the skill's
    own file is now the source for both.
    """
    return skill_root().parent / "project-context" / "SKILL.md"


def protocol_script(filename: str) -> Path:
    """A script that ships with the installed skill rather than with this one.

    A consuming repository installs only `project-context`, so anything it has
    to be able to run against itself — the health check, the assembler, the
    review — lives there and is reached from here.
    """
    return skill_root().parent / "project-context" / "scripts" / filename


def doctor_script() -> Path:
    return protocol_script("context_doctor.py")


def load_protocol(filename: str) -> Any:
    """Import one of those scripts from its file, or None if it cannot be loaded.

    Delegation rather than a second implementation: one report shape, one set
    of issue codes. Fail-soft so a missing or broken sibling is reported as a
    wiring problem instead of a traceback.
    """
    path = protocol_script(filename)
    try:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (OSError, SyntaxError, ImportError):
        return None
    return module


def load_doctor() -> Any:
    return load_protocol("context_doctor.py")


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


def metadata_content(target: Path, profile: str, repo_type: str) -> str:
    """The one marker both products write.

    One schema string, one version number per product, and the project id.
    `pushed` is absent until a Hub owner pushes something: a repository with no
    Hub is a complete product, and an empty stamp table would imply otherwise.
    """
    return json.dumps(
        {
            "authority": "tracked-markdown",
            "product": PRODUCT,
            "profile": profile,
            "project_id": project_id(target),
            "repository_type": repo_type,
            "schema": SCHEMA,
            "version": package_version(),
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


def skill_description(source_skill: Path) -> str:
    """The `description:` line from a skill's frontmatter, or "" when absent.

    Harness pointers reuse the source description verbatim so the text a
    harness matches on cannot drift away from the skill it points at.
    """
    try:
        text = source_skill.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    match = re.search(r"^description:\s*(.+?)\s*$", text, re.MULTILINE)
    if not match:
        return ""
    value = match.group(1).strip()
    # Source frontmatter may or may not already be quoted; carry the text, not
    # the quoting, so the pointer never emits a doubled-quote scalar.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def pointer_content(skill_name: str, description: str) -> str:
    """A thin harness file that redirects to the harness-neutral skill.

    Harness-specific locations hold pointers, not copies: the protocol has one
    source of truth under `.agents/skills/`, and this file exists so a harness
    that only discovers skills from its own directory can still find it.
    """
    heading = skill_name.replace("-", " ").title()
    front = ["---", f"name: {skill_name}"]
    if description:
        # json.dumps yields a valid YAML double-quoted scalar for arbitrary text.
        front.append(f"description: {json.dumps(description)}")
    front.append("---")
    body = [
        f"# {heading}",
        "",
        "This repository keeps its skills harness-neutral under `.agents/skills/`.",
        "",
        f"Read `.agents/skills/{skill_name}/SKILL.md` and follow it exactly. It is",
        f"the protocol; this file only makes it reachable as `/{skill_name}`",
        "and discoverable by description when no other path has loaded it.",
    ]
    if skill_name == "project-context":
        body += [
            "",
            "`project-context/SKILL.md` is this repository's installed instance of",
            "the same text. Either copy is authoritative; read whichever one you",
            "reach first.",
        ]
    return "\n".join(front + [""] + body) + "\n"


def plan_skill_install(target: Path, actions: list[dict[str, Any]]) -> None:
    source_parent = skill_root().parent
    for skill_name in INSTALLED_SKILL_NAMES:
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
        # The installed copy carries the release it came from, so the doctor
        # running inside a repository can still say which version it is. It is
        # derived from the one `VERSION` file, never hand-maintained.
        version = package_version()
        if version != "unknown":
            add_file_action(actions, destination_root / "VERSION", version + "\n")
        plan_harness_pointer(target, skill_name, source / "SKILL.md", actions)


def plan_harness_pointer(
    target: Path, skill_name: str, source_skill: Path, actions: list[dict[str, Any]]
) -> None:
    """Write the Claude Code pointer that makes an installed skill discoverable.

    Without this the skill lands under `.agents/skills/` only, where Claude Code
    never looks: its `description:` cannot match, there is no slash command, and
    discovery falls back entirely to the managed instruction block.
    """
    for harness_root, subdirectory in HARNESS_POINTER_ROOTS:
        pointer_root = target / harness_root / subdirectory / skill_name
        pointer_chain = (
            target / harness_root,
            target / harness_root / subdirectory,
            pointer_root,
        )
        if any(path.is_symlink() for path in pointer_chain) or (
            pointer_root.exists() and not pointer_root.is_dir()
        ):
            actions.append(
                {"kind": "conflict", "path": str(pointer_root), "reason": "harness pointer destination is unsafe"}
            )
            continue
        add_file_action(
            actions,
            pointer_root / "SKILL.md",
            pointer_content(skill_name, skill_description(source_skill)),
        )



def hook_command(script_relative: str, command: str) -> str:
    """The shell for one hook event.

    Guarded with a file test so a repository that has not installed the skills,
    or a harness opened elsewhere, degrades to a no-op instead of erroring at
    session start.
    """
    script = '"${CLAUDE_PROJECT_DIR:-$PWD}/' + script_relative + '"'
    return f's={script}; [ -f "$s" ] && python3 "$s" {command} || true'


def hook_group(command: str, status_message: str) -> dict[str, Any]:
    return {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": 15,
                "statusMessage": status_message,
            }
        ]
    }


def owned_hook(group: Any) -> bool:
    """Is this matcher group one we wrote, rather than the repository's own?"""
    entries = group.get("hooks") if isinstance(group, dict) else None
    return isinstance(entries, list) and any(
        isinstance(entry, dict)
        and isinstance(entry.get("command"), str)
        and any(script in entry["command"] for script in OWNED_HOOK_SCRIPTS)
        for entry in entries
    )


def plan_hooks(target: Path, actions: list[dict[str, Any]]) -> None:
    """Wire the session hooks that carry the protocol into a live session.

    Opt-in: this writes to the harness's own settings file, so it happens only
    when asked for. Existing hooks are preserved — ours are identified by the
    script they call, dropped, and re-added, which keeps repeated runs
    byte-identical and self-healing after a partial edit.
    """
    settings = target / ".claude" / "settings.json"
    chain = (target / ".claude", settings)
    if any(path.is_symlink() for path in chain) or (settings.exists() and not settings.is_file()):
        actions.append({"kind": "conflict", "path": str(settings), "reason": "hook settings destination is unsafe"})
        return
    payload: dict[str, Any] = {"$schema": "https://json.schemastore.org/claude-code-settings.json"}
    if settings.is_file():
        try:
            loaded = json.loads(settings.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            actions.append({"kind": "conflict", "path": str(settings), "reason": "hook settings are not valid JSON"})
            return
        if not isinstance(loaded, dict):
            actions.append({"kind": "conflict", "path": str(settings), "reason": "hook settings are not a JSON object"})
            return
        payload = loaded
    hooks = payload.get("hooks", {})
    if not isinstance(hooks, dict):
        actions.append({"kind": "conflict", "path": str(settings), "reason": "hook settings 'hooks' is not an object"})
        return
    hooks = dict(hooks)
    # Two passes: every hook of ours is dropped from an event before any is
    # re-added, so two SessionStart hooks do not have the first one stripped by
    # the second's own cleanup.
    for event, _script, _command, _status in HOOK_EVENTS:
        existing = hooks.get(event)
        hooks[event] = [group for group in existing if not owned_hook(group)] if isinstance(existing, list) else []
    for event, script, command, status_message in HOOK_EVENTS:
        hooks[event] = hooks[event] + [hook_group(hook_command(script, command), status_message)]
    payload["hooks"] = hooks
    # Insertion order, not sorted: dicts preserve the document's own key order,
    # so re-serialising leaves the rest of the user's settings where they were.
    content = json.dumps(payload, indent=2) + "\n"
    if not settings.exists():
        actions.append({"kind": "create", "path": str(settings), "content": content})
        return
    if settings.read_text(encoding="utf-8") == content:
        actions.append({"kind": "unchanged", "path": str(settings), "reason": "hooks are current"})
        return
    actions.append({"kind": "update_hooks", "path": str(settings), "content": content})


def build_plan(
    target: Path,
    profile: str = "full",
    install_skills: bool = False,
    repo_type: str = "auto",
    repository_stage: str = "existing",
    install_hooks: bool = False,
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
        # Not a template file: the instance protocol is the skill's own text, so
        # the two installed copies can never say different things.
        add_file_action(
            actions,
            context / "SKILL.md",
            protocol_source().read_text(encoding="utf-8"),
        )
        add_file_action(
            actions,
            context / MARKER_NAME,
            metadata_content(target, profile, repository["type"]),
        )
    harnesses = instruction_paths(target)
    actions.extend(instruction_plan(path) for path in harnesses)
    # Both roles, always. `agents.md` satisfies the AGENTS role — the file that
    # is already there is the one that gets the block, whatever its casing.
    carried = {path.name.casefold() for path in harnesses}
    for role in INSTRUCTION_ROLES:
        if role.casefold() not in carried:
            actions.append(
                {
                    "kind": "create",
                    "path": str(target / role),
                    "content": CREATED_INSTRUCTION_HEADER + MANAGED_BLOCK + "\n",
                }
            )
    if install_skills:
        plan_skill_install(target, actions)
    if install_hooks:
        plan_hooks(target, actions)
    report = inspect(target, repo_type)
    report.update(
        {
            "profile": profile,
            "install_skills": install_skills,
            "install_hooks": install_hooks,
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
        if action["kind"] in {"create", "append_managed_block", "update_managed_block", "update_hooks"}:
            atomic_write(Path(action["path"]), action["content"])
    refreshed = build_plan(
        Path(report["target"]),
        report["profile"],
        report["install_skills"],
        report["repository"]["type"],
        report["repository_stage"],
        report["install_hooks"],
    )
    print(json.dumps(public_report(refreshed), indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    # `consolidate` was called `review` before the assembler landed. The name
    # moved because the two answer different questions and only one of them is
    # ongoing: consolidation is an adoption-time sweep for pre-existing context
    # to fold in, while `review` is the standing "what is waiting on a person?"
    # report of 2.6, run for the life of the project.
    for name, help_text in (
        ("inspect", "inspect without writing"),
        ("consolidate", "find consolidation candidates in an existing repository"),
    ):
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--target", default=".", type=Path)
        subparser.add_argument("--repo-type", choices=REPOSITORY_TYPES, default="auto")
    doctor_parser = subparsers.add_parser("doctor", help="validate project-context health")
    doctor_parser.add_argument("--target", default=".", type=Path)
    doctor_parser.add_argument("--stale-days", default=30, type=int)
    review_parser = subparsers.add_parser("review", help="list what is waiting on a person")
    review_parser.add_argument("--target", default=".", type=Path)
    review_parser.add_argument("--open-days", default=14, type=int)
    review_parser.add_argument("--snapshot-days", default=90, type=int)
    review_parser.add_argument("--format", choices=("text", "json"), default="text")
    context_parser = subparsers.add_parser("context", help="assemble the packet for a task")
    context_parser.add_argument("--target", default=".", type=Path)
    context_parser.add_argument("--task", default="")
    context_parser.add_argument("--files", default="", help="comma-separated paths the task touches")
    context_parser.add_argument("--mode", choices=("plan", "implement", "review"), default="implement")
    context_parser.add_argument("--budget", default=4000, type=int)
    context_parser.add_argument("--verified-only", action="store_true")
    context_parser.add_argument("--diff", action="store_true")
    context_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    onboard_parser = subparsers.add_parser("onboard", help="assemble the first-session packet")
    onboard_parser.add_argument("--target", default=".", type=Path)
    onboard_parser.add_argument("--budget", default=4000, type=int)
    onboard_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    init_parser = subparsers.add_parser("init", help="plan or apply initialization")
    init_parser.add_argument("--target", default=".", type=Path)
    init_parser.add_argument("--profile", choices=("core", "full"), default="core")
    init_parser.add_argument("--repo-type", choices=REPOSITORY_TYPES, default="auto")
    init_parser.add_argument(
        "--repository-stage",
        choices=("brand-new", "existing"),
        default="existing",
    )
    init_parser.add_argument("--install-skills", action="store_true")
    init_parser.add_argument(
        "--install-hooks",
        action="store_true",
        help="wire the session hooks into .claude/settings.json; implies --install-skills",
    )
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
    if args.command == "consolidate":
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
    if args.command in {"context", "onboard"}:
        module = load_protocol("context_packet.py")
        if module is None:
            print(f"Cannot load the assembler from {protocol_script('context_packet.py')}", file=sys.stderr)
            return 2
        if args.command == "onboard":
            packet = module.build_packet(target, budget=args.budget, preset="onboard")
        else:
            files = [item for item in args.files.split(",") if item.strip()]
            if args.diff:
                files = sorted(set(files) | set(module.changed_paths(target)))
            packet = module.build_packet(
                target, args.task, files, args.mode, args.budget, args.verified_only
            )
        if args.format == "json":
            print(json.dumps(packet, indent=2, sort_keys=True))
        else:
            print(module.render(packet), end="")
        return 0
    if args.command == "review":
        module = load_protocol("context_review.py")
        if module is None:
            print(f"Cannot load the review from {protocol_script('context_review.py')}", file=sys.stderr)
            return 2
        report = module.review(target, args.open_days, args.snapshot_days)
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(module.render(report), end="")
        return 0
    if args.command == "doctor":
        module = load_doctor()
        if module is None:
            print(f"Cannot load the doctor from {doctor_script()}", file=sys.stderr)
            return 2
        report = module.doctor(target, args.stale_days)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if report["summary"]["errors"] else 0
    report = build_plan(
        target,
        args.profile,
        # Hooks call the installed trigger script, so wiring them without
        # installing the skills would plan a hook that cannot resolve.
        args.install_skills or args.install_hooks,
        args.repo_type,
        args.repository_stage,
        args.install_hooks,
    )
    if args.dry_run:
        print(json.dumps(public_report(report), indent=2, sort_keys=True))
        return 2 if report["has_conflicts"] else 0
    return apply_plan(report)


if __name__ == "__main__":
    raise SystemExit(main())
