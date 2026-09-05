#!/usr/bin/env python3
"""List what in this project's context needs a human, oldest first.

The doctor answers "is this package correct?". This answers a different
question: "what has been sitting here waiting for someone to decide?" Nothing
it reports is an error — a proposed decision is a decision working as intended,
and a question with no answer is the discuss primitive doing its job. They
become a problem only by ageing, which is exactly the thing no single session
is in a position to notice.

Oldest first, and by age rather than by severity, because latency is the one
weak point of a system where nothing moves until a person looks (2.4). A
five-week-old question is worth more attention than a fresh one whatever their
subjects, and sorting by anything else hides that.

Read-only, and it never exits non-zero for a finding: a backlog is not a build
failure, and CI that breaks on one teaches people to stop filing questions.

    context_review.py --target . --open-days 14
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any


CONTEXT_DIRNAME = "project-context"
# Findings the doctor already computes. Re-deriving them here would be a second
# implementation of drift detection that agrees with the first until it does not.
BORROWED_CODES = {
    "evidence-drift": "evidence a record was justified by has changed since it was cited",
    "stale-current-state": "NOW.md has not been reviewed recently",
    "missing-review-date": "NOW.md carries no review date, so staleness cannot be judged",
    "pushed-file-modified": "a pushed copy was edited here; the change belongs in the Hub",
}
DEFAULT_OPEN_DAYS = 14
# A snapshot that has not been refreshed in this long is reported so the owner
# can push rather than the builder wondering. Longer than the question window
# on purpose: a global tier that changes weekly would be a different problem.
DEFAULT_SNAPSHOT_DAYS = 90

REGISTRIES = {"DECISIONS.md": "decision", "LEARNINGS.md": "learning", "QUESTIONS.md": "question"}
RECORD_DIRECTORIES = ("decisions", "questions", "tasks", "inbox")
NON_RECORD_NAMES = {"README.md", "TEMPLATE.md", "INDEX.md"}
# What "needs a human" means per kind. A proposed assertion needs accepting or
# rejecting; an open question needs answering; a capsule needs promoting into a
# durable record or dropping. A task is somebody's work, not a decision
# waiting, so an active task is not a finding.
PENDING_STATUSES = {
    "decision": {"proposed"},
    "learning": {"proposed"},
    "question": {"open"},
    "capsule": {"proposed"},
}
ENTRY_HEADING = re.compile(r"^##\s+([A-Z]-\d{3,}|C-\d{4}-\d{2}-\d{2}-[0-9a-z]+):\s*(.+)$", re.M)
# `D-000`, `L-000`, `Q-000` are the scaffold's worked examples, and every fresh
# install has them. Reporting them would hand a new repository a backlog of
# four items on its first day and teach the reader to ignore the report — the
# one failure a nag has to avoid. A real first entry is `-001`.
EXAMPLE_ID = re.compile(r"^[A-Z]-0+$")
STATUS_LINE = re.compile(r"^\s*-\s+Status:\s*`?([A-Za-z][A-Za-z-]*)`?\s*$", re.M)
DATE_LINE = re.compile(r"^\s*-\s+(?:Date|Created|Asked):\s*(\d{4}-\d{2}-\d{2})\s*$", re.M)
# An assumption recorded but never confirmed is the quiet failure F6 exists to
# catch: work proceeded on something nobody checked.
ASSUMPTION_LINE = re.compile(r"^\s*-\s+Assumption:\s*(.+)$", re.M)
CONFIRMED_LINE = re.compile(r"^\s*-\s+(?:Confirmed|Verified):\s*(.+)$", re.M)


def load_doctor() -> Any:
    script = Path(__file__).resolve().parent / "context_doctor.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("context_doctor", script)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def parse_date(value: str | None) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def age_days(when: date | None, today: date) -> int | None:
    return None if when is None else (today - when).days


def finding(kind: str, code: str, source: str, title: str, days: int | None, detail: str) -> dict[str, Any]:
    return {"kind": kind, "code": code, "source": source, "title": title, "age_days": days, "detail": detail}


def pending_records(context: Path, today: date, open_days: int) -> list[dict[str, Any]]:
    """Records whose status says a person has not finished with them yet."""
    doctor = load_doctor()
    found: list[dict[str, Any]] = []

    for name, kind in REGISTRIES.items():
        path = context / name
        if not path.is_file() or path.is_symlink():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        heads = list(ENTRY_HEADING.finditer(text))
        for index, head in enumerate(heads):
            end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
            body = text[head.end():end]
            status = STATUS_LINE.search(body)
            state = status.group(1).lower() if status else ""
            when = DATE_LINE.search(body)
            days = age_days(parse_date(when.group(1) if when else None), today)
            title = f"{head.group(1)}: {head.group(2).strip()}"
            if EXAMPLE_ID.match(head.group(1)):
                continue
            if state in PENDING_STATUSES.get(kind, set()):
                if kind == "question" and days is not None and days < open_days:
                    continue
                found.append(
                    finding(
                        kind,
                        "open-question" if kind == "question" else "proposed-record",
                        name, title, days,
                        f"`{state}` and waiting on a person",
                    )
                )
            found.extend(unconfirmed(body, name, title, kind, days))

    for directory in RECORD_DIRECTORIES:
        root = context / directory
        if not root.is_dir() or root.is_symlink():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.name in NON_RECORD_NAMES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            front: dict[str, Any] | None = None
            if doctor is not None:
                front, _ = doctor.parse_frontmatter(text)
            front = front if isinstance(front, dict) else {}
            kind = str(front.get("kind") or directory.rstrip("s")).lower()
            state = str(front.get("status") or "").lower()
            days = age_days(parse_date(front.get("created")), today)
            source = path.relative_to(context).as_posix()
            title = f"{front.get('id') or path.stem}: {front.get('title') or path.stem}"
            if EXAMPLE_ID.match(str(front.get("id") or "")):
                continue
            if state in PENDING_STATUSES.get(kind, set()):
                if kind == "question" and days is not None and days < open_days:
                    continue
                code = {
                    "question": "open-question",
                    "capsule": "unpromoted-capsule",
                }.get(kind, "proposed-record")
                found.append(finding(kind, code, source, title, days, f"`{state}` and waiting on a person"))
            found.extend(unconfirmed(text, source, title, kind, days))
    return found


def unconfirmed(text: str, source: str, title: str, kind: str, days: int | None) -> list[dict[str, Any]]:
    """An assumption with no matching confirmation line, in the same record."""
    assumptions = ASSUMPTION_LINE.findall(text)
    if not assumptions or CONFIRMED_LINE.search(text):
        return []
    return [
        finding(kind, "unconfirmed-assumption", source, title, days,
                "records an assumption with no confirmation: " + " ".join(assumptions[0].split())[:120])
    ]


def snapshot_findings(report: dict[str, Any], today: date, snapshot_days: int) -> list[dict[str, Any]]:
    pushed = report.get("pushed") if isinstance(report.get("pushed"), dict) else {}
    oldest = parse_date(pushed.get("oldest_pushed_at"))
    days = age_days(oldest, today)
    if days is None or days < snapshot_days:
        return []
    return [
        finding("snapshot", "stale-snapshot", ".project-context.json",
                "pushed global/ and blueprint/ snapshot", days,
                f"last pushed {days} days ago; ask the owner for a fresh `/hub-push`")
    ]


def review(target: Path, open_days: int = DEFAULT_OPEN_DAYS, snapshot_days: int = DEFAULT_SNAPSHOT_DAYS) -> dict[str, Any]:
    target = target.resolve()
    context = target / CONTEXT_DIRNAME
    today = date.today()
    findings: list[dict[str, Any]] = []
    if context.is_dir() and not context.is_symlink():
        findings.extend(pending_records(context, today, open_days))

    doctor = load_doctor()
    report: dict[str, Any] = {}
    if doctor is not None:
        try:
            report = doctor.doctor(target)
        except Exception:
            report = {}
    for issue in report.get("issues", []) if isinstance(report.get("issues"), list) else []:
        code = issue.get("code")
        if code in BORROWED_CODES:
            findings.append(
                finding("health", code, issue.get("path", ""), issue.get("detail") or BORROWED_CODES[code],
                        None, BORROWED_CODES[code])
            )
    findings.extend(snapshot_findings(report, today, snapshot_days))

    # Oldest first; anything undated sorts after everything dated rather than
    # to the top, because an unknown age is not evidence of urgency.
    findings.sort(key=lambda item: (item["age_days"] is None, -(item["age_days"] or 0), item["source"]))
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["code"]] = counts.get(item["code"], 0) + 1
    return {
        "target": str(target),
        "open_days": open_days,
        "snapshot_days": snapshot_days,
        "summary": {"findings": len(findings), "by_code": counts},
        "findings": findings,
    }


def render(report: dict[str, Any]) -> str:
    findings = report["findings"]
    if not findings:
        return "Nothing is waiting on a person.\n"
    lines = [f"{len(findings)} item(s) waiting on a person, oldest first:", ""]
    for item in findings:
        age = f"{item['age_days']}d" if item["age_days"] is not None else "  ?"
        lines.append(f"  {age:>5}  {item['code']:<24} {item['source']}")
        lines.append(f"         {item['title']}")
        lines.append(f"         {item['detail']}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--open-days", default=DEFAULT_OPEN_DAYS, type=int,
                        help="a question is reported once it has been open this long")
    parser.add_argument("--snapshot-days", default=DEFAULT_SNAPSHOT_DAYS, type=int)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    report = review(target, args.open_days, args.snapshot_days)
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
