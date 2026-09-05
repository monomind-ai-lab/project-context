#!/usr/bin/env python3
"""Write one capsule into `project-context/inbox/`, and nothing else.

Capture has to be cheap enough to happen *during* the work, or it does not
happen at all. That is the whole argument for a staging area: a decision worth
recording usually surfaces mid-task, when stopping to write a registry entry
with an ID, a rationale, and consequences is exactly the interruption a person
declines. So this writes a short, dated, fully attributed note and stops. The
judgement — is this a decision, a learning, or nothing — is deferred to
promotion, where it is cheap.

The cost of a staging area is capsules nobody promotes, which is why
`context_review.py` reports an ageing one. The cost of not having one is
decisions nobody records, and that cost is silent.

It writes one file. It never edits a registry, never touches a record, and
never reaches a network.

    context_capture.py --kind decision --text "..." --apply
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


CONTEXT_DIRNAME = "project-context"
INBOX_DIRNAME = "inbox"
# The capsule's own type, from 2.6. It is not the record `kind` — that is
# `capsule` for everything here, because the record model has five kinds and a
# capsule is one of them. This says what the note is *about*, which is what a
# person needs in order to promote it later, and what `assumption` needs in
# order to be findable at all: an assumption is not a record kind and never
# becomes one, it is confirmed or refuted.
CAPSULE_KINDS = ("decision", "learning", "question", "assumption", "constraint", "proposal")
# Size guard (2.7). Enforced at creation rather than reported afterwards: the
# moment to hold a 200-word limit is before the file exists, and `inbox/`'s own
# README already tells the reader that anything longer is the record it should
# become.
MAX_WORDS = 200
ACTOR_PATTERN = re.compile(r"^(?:person|agent):[^\s:][^\s]*$")
SESSION_PATTERN = re.compile(r"^session:[A-Za-z0-9._-]+:[A-Za-z0-9._-]+$")
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


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
    """Who is asserting this, in the record model's `person:`/`agent:` form.

    Git's configured name is the best available answer and is wrong often
    enough — an agent running as the user's identity is the common case — that
    `--actor` exists and a capsule written by an agent should carry it.
    """
    name = run_git(target, "config", "user.name")
    return f"person:{slug(name)}" if name and slug(name) else "person:unknown"


def binding(target: Path) -> str:
    """The repository half of a `commit:<binding>:<sha>` reference."""
    remote = run_git(target, "remote", "get-url", "origin")
    if remote:
        tail = remote.rstrip("/").rsplit("/", 1)[-1]
        return slug(tail[:-4] if tail.endswith(".git") else tail) or slug(target.name)
    return slug(target.name) or "repository"


def provenance(target: Path, args: argparse.Namespace) -> dict[str, Any]:
    """Harness, model, actor, session, and `binding@HEAD` — 2.6's minimum.

    Everything unknown is omitted rather than recorded as unknown: absent means
    absent in this record model, and a field carrying the string "unknown" is a
    claim that reads like a value.
    """
    found: dict[str, Any] = {"asserted_by": args.actor or default_actor(target)}
    for key, value in (("harness", args.harness), ("model", args.model), ("session", args.session)):
        if value:
            found[key] = value
    evidence = list(args.evidence or [])
    head = run_git(target, "rev-parse", "HEAD")
    if head:
        found["commit"] = f"commit:{binding(target)}:{head}"
        evidence.append(found["commit"])
    if evidence:
        found["evidence"] = evidence
    if args.files:
        found["files"] = [item.strip() for item in args.files.split(",") if item.strip()]
    return found


def capsule_id(text: str, when: date) -> str:
    """`C-YYYY-MM-DD-<digest>`, stable for the same text on the same day.

    Deriving the suffix from the text rather than from a counter or the clock
    makes a repeated capture idempotent, which matters because a `Stop` hook
    that fires twice should not leave two identical capsules to promote.
    """
    return f"C-{when.isoformat()}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:6]}"


def render(record: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for key in ("id", "kind", "status", "title", "created", "asserted_by"):
        lines.append(f"{key}: {record[key]}")
    for key in ("capsule_kind", "harness", "model", "session"):
        if record.get(key):
            lines.append(f"{key}: {record[key]}")
    for key in ("evidence", "files"):
        if record.get(key):
            lines.append(f"{key}:")
            lines.extend(f"  - {item}" for item in record[key])
    lines.extend(["---", "", f"# {record['title']}", "", body, ""])
    lines.extend(
        [
            "## Promotion",
            "",
            f"Captured as a `{record['capsule_kind']}`. Promote it into the registry it",
            "belongs in and set `status: accepted`, linking the record it became; set",
            "`status: rejected` when it has been read and belongs nowhere. Either is a",
            "resolution — leaving it `proposed` is the only outcome that is not.",
            "",
        ]
    )
    return "\n".join(lines)


def build(target: Path, args: argparse.Namespace) -> dict[str, Any]:
    target = target.resolve()
    context = target / CONTEXT_DIRNAME
    inbox = context / INBOX_DIRNAME
    text = " ".join(args.text.split())

    if not context.is_dir() or context.is_symlink():
        return {"status": "refused", "reason": f"no {CONTEXT_DIRNAME}/ here; run `project-context init` first"}
    if not text:
        return {"status": "refused", "reason": "--text is empty; there is nothing to capture"}
    words = len(text.split())
    if words > MAX_WORDS:
        return {
            "status": "refused",
            "reason": f"{words} words; a capsule is at most {MAX_WORDS}. Anything longer is the "
                      "record it should become — write it in the registry instead",
        }
    if args.actor and not ACTOR_PATTERN.match(args.actor):
        return {"status": "refused", "reason": f"--actor {args.actor!r} is not `person:<name>` or `agent:<name>`"}
    if args.session and not SESSION_PATTERN.match(args.session):
        return {"status": "refused", "reason": f"--session {args.session!r} is not `session:<harness>:<id>`"}

    today = date.today()
    record: dict[str, Any] = {
        "id": capsule_id(text, today),
        "kind": "capsule",
        "status": "proposed",
        # The first sentence, or the whole thing when it is one sentence. A
        # capsule that has to be opened to find out what it says is a capsule
        # nobody triages.
        "title": args.title or (re.split(r"(?<=[.!?])\s", text)[0].rstrip(".")[:100]),
        "created": today.isoformat(),
        "capsule_kind": args.kind,
    }
    record.update(provenance(target, args))
    destination = inbox / f"{record['id']}.md"
    content = render(record, text)
    return {
        "status": "unchanged" if destination.is_file() else "planned",
        "path": str(destination),
        "id": record["id"],
        "capsule_kind": record["capsule_kind"],
        "words": words,
        "asserted_by": record["asserted_by"],
        "content": content,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--kind", choices=CAPSULE_KINDS, required=True)
    parser.add_argument("--text", required=True, help=f"the capsule, at most {MAX_WORDS} words")
    parser.add_argument("--title", help="defaults to the first sentence of --text")
    parser.add_argument("--evidence", action="append", help="a reference; repeatable")
    parser.add_argument("--files", default="", help="comma-separated paths this capsule is about")
    parser.add_argument("--actor", help="person:<name> or agent:<name>; defaults to the git identity")
    parser.add_argument("--session", help="session:<harness>:<id>")
    parser.add_argument("--harness", help="the tool this was captured in")
    parser.add_argument("--model", help="the model, when one wrote it")
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
        print(f"already captured: {report['path']}")
        return 0
    if args.dry_run:
        print(report["content"], end="")
        return 0
    destination = Path(report["path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report["content"], encoding="utf-8")
    print(f"captured {report['id']} ({report['capsule_kind']}, {report['words']} words) -> {report['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
