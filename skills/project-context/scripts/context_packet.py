#!/usr/bin/env python3
"""Assemble the packet a session should read before it starts working.

Retrieval here is deliberately dumb: a path-prefix comparison and a token
overlap, over a few hundred small Markdown files. There are no embeddings and
no index to keep warm, because the signal that actually decides relevance is
already written down — a decision cites the files it constrains, and the task
names the files it touches. Comparing those two is a scan, and a scan of one
repository's records is cheaper than the machinery that would guard it.

The order matters more than the matching. Owner-authored constraints
(`global/`, `blueprint/`) come first because a packet that leads with a
builder's own notes buries the thing that was not negotiable; project state
comes next; matched records last. When the budget runs out the remainder
becomes links rather than being silently dropped, so the packet never implies
that what it left out does not exist.

    context_packet.py context --task "add rate limiting" --files src/api.py
    context_packet.py context --mode review --diff        # packet for a review
    context_packet.py onboard                             # the first-session preset
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


MODES = ("plan", "implement", "review")
# The size guard's packet budget (2.7). A caller may raise it; nothing here
# assumes the default.
DEFAULT_BUDGET = 4000
# Tokens are estimated, never counted: this runs without a tokenizer and the
# budget is a guard rail rather than an accounting boundary. Four characters
# per token is the conventional English approximation and errs high, which is
# the safe direction for a guard.
CHARS_PER_TOKEN = 4

CONTEXT_DIRNAME = "project-context"
# Written by `/hub-push` into a file it has not been filled in yet. Pushing
# skips them, so one reaching a repository means the owner published a blank —
# it carries no information and costs budget, so the packet skips it too.
UNFILLED_MARKER = "<!-- project-hub:unfilled -->"

# Step 1 of the assembly order: always present, small by rule.
GLOBAL_ALWAYS = ("SUMMARY.md", "IDENTITY.md", "GUARDRAILS.md")
# Step 2: the epic is the constraint in every mode. Architecture is a planning
# and review concern — an implement packet that carries it spends a quarter of
# the budget on a document the task at hand is not allowed to change anyway.
BLUEPRINT_ALWAYS = ("EPIC.md",)
BLUEPRINT_BY_MODE = {"plan": ("ARCHITECTURE.md",), "review": ("ARCHITECTURE.md",)}
# The `onboard` preset (2.6): what a person or agent meeting the project for
# the first time needs, and nothing task-specific, because there is no task.
ONBOARD_GLOBAL = ("SUMMARY.md", "IDENTITY.md", "WORKFLOWS.md")

REGISTRIES = {
    "DECISIONS.md": "decision",
    "LEARNINGS.md": "learning",
    "QUESTIONS.md": "question",
}
RECORD_DIRECTORIES = ("decisions", "questions", "tasks", "inbox")
NON_RECORD_NAMES = {"README.md", "TEMPLATE.md", "INDEX.md"}
# "Verified" per 2.5. A question is verified once it has an answer; an
# assertion once it is accepted. Everything else is proposed, and shows in its
# own labelled section rather than mixed in with what the project settled.
VERIFIED_STATUSES = {"accepted", "answered", "done", "active"}

ENTRY_HEADING = re.compile(r"^##\s+([A-Z]-\d{3,}|C-\d{4}-\d{2}-\d{2}-[0-9a-z]+):\s*(.+)$", re.M)
STATUS_LINE = re.compile(r"^\s*-\s+Status:\s*`?([A-Za-z][A-Za-z-]*)`?\s*$", re.M)
SERVES_LINE = re.compile(r"^\s*-\s+Serves:\s*(.+)$", re.M)
# `src/server.py@a1b2c3d` — the same shape the doctor validates, read here for
# the path half only. The commit is what pins the citation; the path is what
# makes it findable.
ANCHOR = re.compile(r"(?<![\w@])([\w.-]*[./][\w./-]*)@([0-9a-f]{7,40})\b")
FILES_LINE = re.compile(r"^\s*-\s+Files:\s*(.+)$", re.M)
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

# Ordinary English plus the vocabulary every record in this system contains.
# A task line saying "decision" should not match every decision ever recorded.
STOPWORDS = frozenset(
    """
    a about add after all also and any are as at back be because been before being
    but by can change changed check could did do does doing done down each even
    every fix fixed for from get give go going had has have her here him his how
    into its just keep know like make made many may more most much must need new
    not now of off on once one only or other our out over own put ran run said
    same see set should show since so some still such take than that the their
    them then there these they this those through to too under until up upon use
    used using very was way we well were what when where which while who why will
    with within would you your
    context project record records decision decisions learning learnings question
    questions task tasks note notes file files code repository repo update
    """.split()
)


def load_sibling(filename: str) -> Any:
    """Load a script that ships beside this one.

    The doctor owns frontmatter parsing, and duplicating it here is how two
    parsers start disagreeing about what a record is. Both files are installed
    together under the same `scripts/` directory, so this import cannot dangle
    in an install; it can only fail in a checkout someone has taken apart.
    """
    script = Path(__file__).resolve().parent / filename
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # a broken sibling must not take the packet down with it
        return None
    return module


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def read(path: Path) -> str | None:
    """Read a packet source, or return None when there is nothing worth reading."""
    if not path.is_file() or path.is_symlink():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text or UNFILLED_MARKER in text:
        return None
    return text


def tokens_of(text: str) -> set[str]:
    return {word.lower() for word in WORD.findall(text)} - STOPWORDS


def anchor_paths(body: str) -> set[str]:
    """Every repository path this entry claims to be about.

    Two sources, and they answer different questions. An evidence anchor says
    what the entry was justified by; a `Files:` line says what it governs. An
    entry that constrains a file it never had to cite is the common case — a
    naming convention, say — so reading only anchors would miss exactly the
    entries a builder most needs to see before touching that file.
    """
    paths = {path for path, _ in ANCHOR.findall(body)}
    for line in FILES_LINE.findall(body):
        for item in re.split(r"[,\s]+", line.strip()):
            cleaned = item.strip("`<>()[]'\"")
            if cleaned and ("/" in cleaned or "." in cleaned):
                paths.add(cleaned.split("@", 1)[0])
    return {path.strip("/") for path in paths if path.strip("/")}


def shares_prefix(left: str, right: str) -> bool:
    """Do two repository paths overlap on a directory boundary?

    Both directions count. `src/api/` matches a task touching
    `src/api/routes.py` because the record governs the directory; and a record
    anchored at `src/api/routes.py` matches a task given `src/api` because the
    task named the directory the record lives under. What must not match is
    `src/api` against `src/apiary.py`, which a bare `startswith` would accept —
    hence the separator.
    """
    left, right = left.strip("/"), right.strip("/")
    if not left or not right:
        return False
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def entries(context: Path) -> list[dict[str, Any]]:
    """Every record the packet may draw on, registries and detail files alike.

    A registry entry and a detail record carry the same four facts the
    assembler needs — id, kind, status, and the text — in two different
    shapes, so they are flattened into one list here and nothing downstream
    has to care which file a record came from.
    """
    doctor = load_sibling("context_doctor.py")
    found: list[dict[str, Any]] = []
    for name, kind in REGISTRIES.items():
        text = read(context / name)
        if text is None:
            continue
        heads = list(ENTRY_HEADING.finditer(text))
        for index, head in enumerate(heads):
            end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
            body = text[head.end():end].strip()
            status = STATUS_LINE.search(body)
            found.append(
                {
                    "id": head.group(1),
                    "kind": kind,
                    "title": head.group(2).strip(),
                    "status": (status.group(1).lower() if status else "accepted"),
                    "source": name,
                    "body": body,
                    "paths": anchor_paths(body),
                    "tokens": tokens_of(head.group(2) + " " + body),
                }
            )
    for directory in RECORD_DIRECTORIES:
        root = context / directory
        if not root.is_dir() or root.is_symlink():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name in NON_RECORD_NAMES:
                continue
            text = read(path)
            if text is None:
                continue
            front: dict[str, Any] | None = None
            if doctor is not None:
                front, _ = doctor.parse_frontmatter(text)
            front = front if isinstance(front, dict) else {}
            body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()
            found.append(
                {
                    "id": str(front.get("id") or path.stem),
                    "kind": str(front.get("kind") or directory.rstrip("s")),
                    "title": str(front.get("title") or path.stem),
                    "status": str(front.get("status") or "proposed").lower(),
                    "source": path.relative_to(context).as_posix(),
                    "body": body,
                    "paths": anchor_paths(text),
                    "tokens": tokens_of(str(front.get("title", "")) + " " + body),
                }
            )
    return found


def changed_paths(target: Path) -> list[str]:
    """The paths a review is actually about.

    `HEAD` rather than the merge base on purpose: the merge base needs a
    branch to compare against and guessing one wrongly produces a packet about
    somebody else's work. Untracked files are included because a new file is
    the one most likely to need a decision read before it is reviewed.
    """
    paths: list[str] = []
    for args in (
        ("diff", "--name-only", "HEAD"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        try:
            result = subprocess.run(
                ("git", "-C", str(target), *args),
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return paths
        if result.returncode == 0:
            paths.extend(line for line in result.stdout.splitlines() if line.strip())
    return sorted(dict.fromkeys(paths))


def plan_items(context: Path, active_only: bool = True) -> list[dict[str, str]]:
    """Milestone items from `PLAN.md`, with the epic item each one serves."""
    text = read(context / "PLAN.md")
    if text is None:
        return []
    items: list[dict[str, str]] = []
    heads = list(ENTRY_HEADING.finditer(text))
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
        body = text[head.end():end].strip()
        status = STATUS_LINE.search(body)
        state = status.group(1).lower() if status else "active"
        if active_only and state in {"done", "dropped"}:
            continue
        serves = SERVES_LINE.search(body)
        items.append(
            {
                "id": head.group(1),
                "title": head.group(2).strip(),
                "status": state,
                "serves": " ".join(serves.group(1).split()) if serves else "",
                "body": body,
            }
        )
    return items


def section(title: str, source: str, text: str) -> dict[str, Any]:
    return {"title": title, "source": source, "text": text, "tokens": estimate_tokens(text)}


def build_packet(
    target: Path,
    task: str = "",
    files: list[str] | None = None,
    mode: str = "implement",
    budget: int = DEFAULT_BUDGET,
    verified_only: bool = False,
    preset: str = "context",
) -> dict[str, Any]:
    target = target.resolve()
    context = target / CONTEXT_DIRNAME
    files = [path.strip().strip("/") for path in (files or []) if path.strip()]
    task_tokens = tokens_of(task)

    # Everything is gathered first and admitted second. Building the whole
    # candidate list before spending any budget is what lets the overflow
    # become links: a section that did not fit is still known, with its path.
    candidates: list[dict[str, Any]] = []
    globals_wanted = ONBOARD_GLOBAL if preset == "onboard" else GLOBAL_ALWAYS
    for name in globals_wanted:
        text = read(context / "global" / name)
        if text is not None:
            candidates.append(section(f"Global — {name}", f"global/{name}", text))
    if preset != "onboard":
        for name in BLUEPRINT_ALWAYS + BLUEPRINT_BY_MODE.get(mode, ()):
            text = read(context / "blueprint" / name)
            if text is not None:
                candidates.append(section(f"Blueprint — {name}", f"blueprint/{name}", text))

    now = read(context / "NOW.md")
    if now is not None:
        candidates.append(section("Current state — NOW.md", "NOW.md", now))

    if preset != "onboard":
        active = plan_items(context)
        if active:
            rendered = "\n\n".join(
                f"### {item['id']}: {item['title']}\n\n{item['body']}" for item in active
            )
            candidates.append(section("Active plan items — PLAN.md", "PLAN.md", rendered))

    matched: list[dict[str, Any]] = []
    if preset != "onboard":
        for entry in entries(context):
            by_path = [path for path in entry["paths"] if any(shares_prefix(path, f) for f in files)]
            overlap = entry["tokens"] & task_tokens
            if not by_path and not overlap:
                continue
            # A record that names one of the task's own files is evidence about
            # this task; a record that merely shares vocabulary is a guess. The
            # weighting keeps the guesses below the evidence rather than
            # excluding them, because the vocabulary match is what finds the
            # convention nobody thought to anchor.
            entry = dict(entry)
            entry["reason"] = "path" if by_path else "topic"
            entry["score"] = (10 if by_path else 0) + len(overlap)
            entry["matched_paths"] = sorted(by_path)
            matched.append(entry)
    # Decisions before learnings before questions, and inside a kind the
    # strongest match first. `implement` leads with the decisions whose anchors
    # overlap the task's paths (2.6), which is what this ordering produces.
    rank = {"decision": 0, "learning": 1, "question": 2, "task": 3, "capsule": 4}
    matched.sort(key=lambda item: (rank.get(item["kind"], 9), -item["score"], item["id"]))

    verified = [item for item in matched if item["status"] in VERIFIED_STATUSES]
    proposed = [] if verified_only else [item for item in matched if item["status"] not in VERIFIED_STATUSES]

    for item in verified:
        candidates.append(
            section(
                f"{item['kind'].title()} {item['id']}: {item['title']}",
                item["source"],
                item["body"],
            )
            | {"match": item["reason"], "score": item["score"]}
        )

    if preset != "onboard":
        for name in ("skills", "shared"):
            root = context / "global" / name
            if not root.is_dir() or root.is_symlink():
                continue
            for path in sorted(root.rglob("*.md")):
                if path.name in NON_RECORD_NAMES:
                    continue
                text = read(path)
                if text is None:
                    continue
                relative = path.relative_to(context).as_posix()
                applies = tokens_of(text) & task_tokens or any(
                    shares_prefix(anchor, f) for anchor in anchor_paths(text) for f in files
                )
                if applies or mode in tokens_of(text):
                    candidates.append(section(f"Global {name[:-1]} — {path.stem}", relative, text))

    spent, sections, links = 0, [], []
    for candidate in candidates:
        if spent + candidate["tokens"] <= budget:
            sections.append(candidate)
            spent += candidate["tokens"]
        else:
            links.append({"source": candidate["source"], "title": candidate["title"], "reason": "over budget"})
    for item in proposed:
        links.append(
            {
                "source": item["source"],
                "title": f"{item['id']}: {item['title']}",
                "reason": f"proposed ({item['kind']})",
            }
        )

    return {
        "target": str(target),
        "task": task,
        "mode": mode,
        "preset": preset,
        "files": files,
        "budget": budget,
        "tokens": spent,
        "truncated": bool([link for link in links if link["reason"] == "over budget"]),
        "sections": sections,
        "links": links,
        "matched": [
            {"id": item["id"], "kind": item["kind"], "status": item["status"],
             "reason": item["reason"], "score": item["score"], "source": item["source"]}
            for item in matched
        ],
    }


def render(packet: dict[str, Any]) -> str:
    """Markdown, because the consumer is a session and not a program.

    A `SessionStart` hook pastes this straight into a context window and the
    managed instruction block tells other harnesses to run the command and read
    what comes back. Both want prose with headings; `--format json` exists for
    the callers that want to inspect the selection instead of read it.
    """
    lines: list[str] = ["# Project context packet", ""]
    if packet["task"]:
        lines.append(f"Task: {packet['task']}")
    shape = packet["preset"] if packet["preset"] != "context" else packet["mode"]
    lines.append(f"Mode: `{shape}` · budget {packet['budget']} tokens · using {packet['tokens']}")
    if packet["files"]:
        lines.append("Files: " + ", ".join(f"`{path}`" for path in packet["files"]))
    lines.append("")
    if not packet["sections"]:
        lines.append("No project context was found to load. Check that `project-context/` is installed.")
        return "\n".join(lines) + "\n"
    for entry in packet["sections"]:
        lines.append(f"## {entry['title']}")
        note = f"`{entry['source']}`"
        if entry.get("match"):
            note += f" · matched by {entry['match']}"
        lines.extend([note, "", entry["text"], ""])
    if packet["links"]:
        lines.extend(["## Not loaded", "", "Read these directly if the task turns out to need them.", ""])
        for link in packet["links"]:
            lines.append(f"- `{link['source']}` — {link['title']} ({link['reason']})")
        lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("context", "assemble a packet for a task"),
        ("onboard", "assemble the first-session preset"),
    ):
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--target", default=".", type=Path)
        subparser.add_argument("--budget", default=DEFAULT_BUDGET, type=int)
        subparser.add_argument("--format", choices=("markdown", "json"), default="markdown")
        if name == "context":
            subparser.add_argument("--task", default="", help="one line describing the work")
            subparser.add_argument("--files", default="", help="comma-separated paths the task touches")
            subparser.add_argument("--mode", choices=MODES, default="implement")
            subparser.add_argument("--verified-only", action="store_true")
            subparser.add_argument(
                "--diff",
                action="store_true",
                help="take the file set from the working tree's changes",
            )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    if args.command == "onboard":
        packet = build_packet(target, budget=args.budget, preset="onboard")
    else:
        files = [item for item in args.files.split(",") if item.strip()]
        if args.diff:
            files = sorted(set(files) | set(changed_paths(target)))
        packet = build_packet(
            target, args.task, files, args.mode, args.budget, args.verified_only
        )
    if args.format == "json":
        print(json.dumps(packet, indent=2, sort_keys=True))
    else:
        print(render(packet), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
