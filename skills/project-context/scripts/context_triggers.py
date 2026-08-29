#!/usr/bin/env python3
"""Detect project-context update triggers and report them to the harness.

The trigger contract lives in project-context/SKILL.md. This script only
detects that a trigger *window* is open: work has landed since project context
was last updated. Deciding which documents actually fire is the agent's job,
because only the agent knows whether a choice constrained future work or an
observation generalises beyond one task.

Commands:
  report  read hook JSON on stdin, emit SessionStart additionalContext
  gate    read hook JSON on stdin, emit a Stop decision (blocks at most once
          per session so it can never loop)
  ack     record that the triggers were evaluated and none fired
  status  human-readable summary for manual runs

Read-only except for its own state file. Never fails a session: any unexpected
error exits 0 with no decision.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CONTEXT_DIR = "project-context"
STATE_RELATIVE = Path(".claude") / "project-context-state.json"
STATE_POSIX = STATE_RELATIVE.as_posix()
EXCLUDED = {
    ".git", "node_modules", "vendor", "dist", "build", "coverage", ".venv",
    "venv", "__pycache__", ".next", "target", "out", ".claude", ".agents",
    "graphify-out", "openwiki",
}
PLACEHOLDERS = (
    "Describe the current stable state.",
    "## D-000: Example decision",
    "## L-000: Example learning",
)

TRIGGER_TABLE = """\
NOW.md — the state a next contributor would act on changed:
  work landed that changes what happens next; an initiative started, finished,
  or changed status; a blocker appeared or cleared; a recorded next action was
  done; the session is ending with work in flight.
DECISIONS.md — a choice now constrains future work:
  one option was taken over a viable alternative; a convention, boundary,
  interface, format, dependency, or tool was fixed; the user stated a standing
  rule; something was deliberately ruled out of scope; an earlier decision was
  reversed or narrowed (supersede it, do not rewrite it).
LEARNINGS.md — evidence changed what is believed, and it will recur:
  a root cause the code did not make obvious; an approach that failed in a way
  that would repeat; an assumption disproved by an observed result; a tool,
  API, or platform behaving unlike its documentation; a rule that would have
  prevented a review finding or incident. Evidence required, and it must apply
  beyond this one task."""


def run(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    # rstrip only newlines: git status --porcelain encodes state in leading columns
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def newest_mtime(root: Path, inside: bool) -> float:
    """Newest file mtime inside project-context/ (inside=True) or outside it."""
    newest = 0.0
    for current, directories, files in os.walk(root):
        directories[:] = [
            d for d in directories if d not in EXCLUDED and not d.startswith(".")
        ]
        relative = Path(current).relative_to(root)
        if (relative.parts[:1] == (CONTEXT_DIR,)) != inside:
            continue
        for name in files:
            if name.startswith("."):
                continue
            try:
                newest = max(newest, (Path(current) / name).stat().st_mtime)
            except OSError:
                continue
    return newest


def evaluate(target: Path) -> dict:
    context = target / CONTEXT_DIR
    state: dict = {
        "target": str(target),
        "installed": context.is_dir(),
        "head": "",
        "work_commits": [],
        "dirty_paths": [],
        "context_touched": False,
        "placeholders": [],
        "last_reviewed": None,
        "review_age_days": None,
        "git": False,
    }
    if not state["installed"]:
        return state

    now_file = context / "NOW.md"
    if now_file.is_file():
        text = now_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^Last reviewed:\s*(\d{4}-\d{2}-\d{2})", text, re.MULTILINE)
        if match:
            state["last_reviewed"] = match.group(1)
            try:
                parsed = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                state["review_age_days"] = (date.today() - parsed).days
            except ValueError:
                pass

    for relative in ("NOW.md", "DECISIONS.md", "LEARNINGS.md"):
        candidate = context / relative
        if not candidate.is_file():
            continue
        body = candidate.read_text(encoding="utf-8", errors="replace")
        if any(marker in body for marker in PLACEHOLDERS):
            state["placeholders"].append(relative)

    state["git"] = bool(run(["git", "rev-parse", "--is-inside-work-tree"], target))
    if state["git"]:
        state["head"] = run(["git", "rev-parse", "HEAD"], target)
        for line in run(["git", "status", "--porcelain"], target).splitlines():
            path = line[3:].strip().strip('"').split(" -> ")[-1]
            if path.startswith(f"{CONTEXT_DIR}/"):
                state["context_touched"] = True
            elif path and path != STATE_POSIX:
                # This script's own state file is bookkeeping, never work. If it
                # counted, writing an ack would immediately invalidate that ack.
                state["dirty_paths"].append(path)

        anchor = run(["git", "log", "-1", "--format=%H", "--", CONTEXT_DIR], target)
        if anchor and anchor == state["head"]:
            state["context_touched"] = True
        span = f"{anchor}..HEAD" if anchor else "HEAD"
        log = run(
            ["git", "log", span, "--format=%h %s", "--", ".", f":(exclude){CONTEXT_DIR}"],
            target,
        )
        state["work_commits"] = [line for line in log.splitlines() if line.strip()]
    else:
        if newest_mtime(target, inside=False) > newest_mtime(target, inside=True):
            state["dirty_paths"].append("files changed more recently than project-context/")

    return state


def reasons_for(state: dict) -> list[str]:
    """Why the window is open, before any acknowledgement is applied."""
    if not state["installed"] or state["context_touched"]:
        return []
    reasons: list[str] = []
    if state["placeholders"]:
        reasons.append(
            "project context is still at its installed template values ("
            + ", ".join(state["placeholders"])
            + ")"
        )
    if state["work_commits"]:
        count = len(state["work_commits"])
        reasons.append(
            f"{count} commit{'s' if count != 1 else ''} since project context was last updated"
        )
    if state["dirty_paths"]:
        count = len(state["dirty_paths"])
        reasons.append(f"{count} uncommitted path{'s' if count != 1 else ''} outside project-context/")
    return reasons


def ack_covers(state: dict, ack: dict) -> bool:
    """Does a recorded acknowledgement still speak for the current work?

    An ack is a claim about specific work: "I evaluated these triggers against
    this HEAD and these uncommitted paths, and none fired." It stays valid only
    while that claim is still about the same work. A new commit moves HEAD and
    reopens the window; uncommitted work the ack never saw reopens it too. That
    is what keeps `ack` from becoming a one-keystroke way to skip the
    evaluation for the rest of the session.
    """
    if not ack:
        return False
    if ack.get("head", "") != state.get("head", ""):
        return False
    return not (set(state["dirty_paths"]) - set(ack.get("dirty", [])))


def due(state: dict, ack: dict) -> list[str]:
    reasons = reasons_for(state)
    return [] if ack_covers(state, ack) else reasons


def detail(state: dict) -> str:
    lines: list[str] = []
    if state["work_commits"]:
        lines.append("Unrecorded commits:")
        lines.extend(f"  {entry}" for entry in state["work_commits"][:10])
        if len(state["work_commits"]) > 10:
            lines.append(f"  … and {len(state['work_commits']) - 10} more")
    if state["dirty_paths"]:
        lines.append("Uncommitted work:")
        lines.extend(f"  {path}" for path in state["dirty_paths"][:10])
        if len(state["dirty_paths"]) > 10:
            lines.append(f"  … and {len(state['dirty_paths']) - 10} more")
    if state["last_reviewed"]:
        age = state["review_age_days"]
        plural = "" if age == 1 else "s"
        suffix = f" ({age} day{plural} ago)" if isinstance(age, int) else ""
        lines.append(f"NOW.md last reviewed: {state['last_reviewed']}{suffix}")
    return "\n".join(lines)


def load_state(target: Path) -> dict:
    path = target / STATE_RELATIVE
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def save_state(target: Path, sessions: dict) -> None:
    path = target / STATE_RELATIVE
    reserved = {key: value for key, value in sessions.items() if key.startswith("_")}
    entries = {key: value for key, value in sessions.items() if not key.startswith("_")}
    trimmed = dict(list(entries.items())[-20:])
    trimmed.update(reserved)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trimmed, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def ack_line(state: dict, ack: dict) -> str:
    if not ack_covers(state, ack):
        return ""
    when = ack.get("at", "unknown time")
    note = f" — {ack['note']}" if ack.get("note") else ""
    covered = ack.get("reasons") or []
    what = "; ".join(covered) if covered else "no open trigger"
    return (
        f"Project context triggers were evaluated at {when} and none fired{note}.\n"
        f"Acknowledged: {what}.\n"
        "The window reopens on the next commit, or as soon as uncommitted work "
        "the acknowledgement did not cover appears."
    )


def read_hook_input() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
    except (OSError, UnicodeDecodeError):
        return {}
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def script_root() -> str:
    """The repository this script is installed in.

    The script lives at <root>/.agents/skills/project-context/scripts/, so the
    fourth parent is the root. This is the fallback for the case the upward
    walk cannot serve: the harness opened a directory *above* the repository,
    or beside it, so neither the cwd nor any of its parents holds
    project-context/ — while the script being executed is sitting inside a
    repository that does.
    """
    try:
        return str(Path(__file__).resolve().parents[3])
    except (IndexError, OSError):
        return ""


def resolve_target(hook: dict) -> tuple[Path, str, list[str]]:
    """Locate the repository, and say how it was found.

    Returns (path, how, searched). `how` is "cwd" for a directory the harness
    actually opened, "script" when only the install-root fallback matched, and
    "none" when nothing did. Callers report the last two rather than exiting
    mute: a silent clean exit makes "the check could not find the repository"
    indistinguishable from "no trigger was open", and both look like a quiet,
    healthy session.
    """
    searched: list[str] = []
    candidates = (
        ("cwd", os.environ.get("CLAUDE_PROJECT_DIR")),
        ("cwd", hook.get("cwd")),
        ("cwd", os.getcwd()),
        ("script", script_root()),
    )
    for how, candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).resolve()
        searched.append(str(path))
        if (path / CONTEXT_DIR).is_dir():
            return path, how, searched
        for parent in path.parents:
            if (parent / CONTEXT_DIR).is_dir():
                return parent, how, searched
    return Path(os.getcwd()).resolve(), "none", searched


def unresolved_note(searched: list[str]) -> str:
    locations = "\n".join(f"  {item}" for item in dict.fromkeys(searched))
    return (
        "The project-context trigger check could not locate a repository "
        f"containing {CONTEXT_DIR}/. It looked in:\n"
        f"{locations}\n"
        "No trigger was evaluated this session — this is a wiring problem, not "
        "a clean bill of health."
    )


def command_report(hook: dict, target: Path, how: str, searched: list[str]) -> int:
    if how == "none":
        emit_context(unresolved_note(searched))
        return 0
    state = evaluate(target)
    if not state["installed"]:
        return 0
    sessions = load_state(target)
    ack = sessions.get("_ack") or {}
    reasons = due(state, ack)
    session = str(hook.get("session_id") or "unknown")
    sessions[session] = {"opened": datetime.now().isoformat(timespec="seconds"), "blocked": 0}
    save_state(target, sessions)

    blocks: list[str] = []
    if how == "script":
        blocks.append(
            f"The harness opened a directory outside this repository; project "
            f"context was resolved from the trigger script's own install root "
            f"({target}). Commands that assume the working directory is the "
            f"repository may not behave as expected."
        )
    if reasons:
        blocks.append(
            "\n".join(
                [
                    "Project context has pending updates: " + "; ".join(reasons) + ".",
                    "",
                    detail(state),
                    "",
                    "Read project-context/NOW.md, then evaluate these triggers as this",
                    "session's work lands — do not wait to be asked:",
                    "",
                    TRIGGER_TABLE,
                ]
            )
        )
    else:
        acknowledged = ack_line(state, ack)
        if acknowledged:
            blocks.append(acknowledged)
    if not blocks:
        return 0
    emit_context("\n\n".join(blocks))
    return 0


def emit_context(text: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        },
        sys.stdout,
    )


def command_gate(hook: dict, target: Path, how: str) -> int:
    if hook.get("stop_hook_active") or how == "none":
        return 0
    state = evaluate(target)
    sessions = load_state(target)
    reasons = due(state, sessions.get("_ack") or {})
    if not reasons:
        return 0
    session = str(hook.get("session_id") or "unknown")
    entry = sessions.get(session) or {"opened": datetime.now().isoformat(timespec="seconds"), "blocked": 0}
    if entry.get("blocked", 0) >= 1:
        return 0
    entry["blocked"] = entry.get("blocked", 0) + 1
    entry["last_block"] = datetime.now().isoformat(timespec="seconds")
    sessions[session] = entry
    save_state(target, sessions)
    reason = "\n".join(
        [
            "Project context is behind the repository: " + "; ".join(reasons) + ".",
            "",
            detail(state),
            "",
            "Evaluate each document's trigger and update the ones that fired:",
            "",
            TRIGGER_TABLE,
            "",
            "Where a trigger fired, update the document — set NOW.md's",
            "`Last reviewed` to today and make the snapshot, active work, and",
            "blockers match the repository. Where none fired, say so and record",
            "it instead of editing a file to silence this:",
            "",
            "  python3 .agents/skills/project-context/scripts/context_triggers.py \\",
            "      ack --note \"<what you evaluated>\"",
            "",
            "This check does not block again in this session.",
        ]
    )
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    return 0


def command_ack(target: Path, note: str, how: str, searched: list[str]) -> int:
    if how == "none":
        print(unresolved_note(searched), file=sys.stderr)
        return 1
    state = evaluate(target)
    if not state["installed"]:
        print(f"no {CONTEXT_DIR}/ in {target}", file=sys.stderr)
        return 1
    sessions = load_state(target)
    reasons = reasons_for(state)
    if not reasons:
        print("nothing to acknowledge: no trigger window is open")
        return 0
    sessions["_ack"] = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "head": state["head"],
        "reasons": reasons,
        "commits": [entry.split(" ", 1)[0] for entry in state["work_commits"]],
        "dirty": sorted(state["dirty_paths"]),
        "note": note or "",
    }
    save_state(target, sessions)
    print("acknowledged: " + "; ".join(reasons))
    if note:
        print(f"note: {note}")
    print(
        "The window reopens on the next commit, or as soon as uncommitted work "
        "this acknowledgement did not cover appears."
    )
    return 0


def command_status(target: Path, how: str, searched: list[str]) -> int:
    if how == "none":
        print(unresolved_note(searched), file=sys.stderr)
        return 1
    if how == "script":
        print("note: resolved from the script's install root, not the working directory")
    state = evaluate(target)
    if not state["installed"]:
        print(f"no {CONTEXT_DIR}/ in {target}", file=sys.stderr)
        return 1
    sessions = load_state(target)
    ack = sessions.get("_ack") or {}
    reasons = due(state, ack)
    print(f"target: {target}")
    print(f"status: {'update due' if reasons else 'current'}")
    for reason in reasons:
        print(f"  - {reason}")
    body = detail(state)
    if body:
        print(body)
    acknowledged = ack_line(state, ack)
    if acknowledged:
        print(acknowledged)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", nargs="?", default="status",
        choices=("report", "gate", "ack", "status"),
    )
    parser.add_argument("--note", default="", help="what was evaluated, recorded with an ack")
    args = parser.parse_args(argv[1:])
    hook = read_hook_input() if args.command in {"report", "gate"} else {}
    target, how, searched = resolve_target(hook)
    if args.command == "report":
        return command_report(hook, target, how, searched)
    if args.command == "gate":
        return command_gate(hook, target, how)
    if args.command == "ack":
        return command_ack(target, args.note, how, searched)
    return command_status(target, how, searched)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:  # never break a session over a context check
        sys.exit(0)
