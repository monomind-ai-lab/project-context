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

It also reports *conflict candidates*: pairs of accepted decisions whose scope
overlaps enough that someone should read both. It cannot tell that two
decisions contradict — that is a semantic judgement and it stays with the
person or agent reading them, exactly as the trigger window stays a judgement
in `context_triggers.py`. What a scan can establish is that two standing rules
point at the same files or the same vocabulary, and it says which ones, so the
reader can settle it in a minute instead of discovering it in a month.

`--new-decision` runs the same comparison for a decision that has not been
written yet, which is the check the protocol asks for before appending one.

Read-only, and it never exits non-zero for a finding: a backlog is not a build
failure, and CI that breaks on one teaches people to stop filing questions.
A conflict candidate is held to the same rule for a stronger reason — a tool
that failed a build on a topic overlap it cannot verify would be switched off
within a week, and every real conflict after that would go unreported.

    context_review.py --target . --open-days 14
    context_review.py --target . --new-decision "cap retries at three" \
        --new-decision-files src/api/client.py
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

# --- conflict candidates ---------------------------------------------------
#
# Two accepted decisions are a *candidate* when their scope overlaps, never a
# reported conflict. The thresholds below exist to keep the candidate list
# short enough to read; they are not a confidence score, and nothing here
# claims the pair actually disagrees.

# Shared terms needed before a topic overlap is worth a reader's time. Below
# this, two decisions in the same project share ordinary English.
DEFAULT_MIN_SHARED_TERMS = 5
# ...and the overlap has to be a real fraction of the *smaller* decision's
# vocabulary. Five shared words out of two hundred is coincidence; five out of
# fifteen means one decision's whole subject sits inside the other's.
MIN_SHARED_RATIO = 0.25
# Pairwise comparison grows with the square of the registry. Thirty decisions
# on one subsystem could produce hundreds of pairs and bury every other
# finding, so the strongest are kept and the rest are counted, never dropped
# in silence.
DEFAULT_MAX_CONFLICTS = 25
# The registry's own furniture. Every entry carries these words because the
# template prints them, so a pair that shares only these has shared nothing.
# This is not a second stopword list for the tokenizer — `context_packet.py`
# owns that, and this is applied after it — it is the field labels of the
# format being compared.
LEDGER_TERMS = frozenset(
    """
    accepted commit consequences date decision evidence files proposed
    rationale registry rejected status supersedes superseded
    """.split()
)
SUPERSEDES_LINE = re.compile(r"^\s*-\s+Supersedes:\s*(.+)$", re.M | re.I)
SUPERSEDED_BY_LINE = re.compile(r"^\s*-\s+Superseded[ -]by:\s*(.+)$", re.M | re.I)
RECORD_ID = re.compile(r"\b([A-Z]-\d{3,})\b")
# Stands in for the decision an agent is about to append, which has no ID yet.
PENDING_ID = "(new)"


_SIBLINGS: dict[str, Any] = {}


def load_sibling(filename: str) -> Any:
    """Load a script that ships beside this one, once per process.

    The doctor owns frontmatter parsing and the packet owns what a record is
    and how its text is tokenised. Re-implementing either here is how two
    readers start disagreeing about what a decision constrains, which for a
    conflict check would mean reporting pairs the packet never puts in front
    of an agent.
    """
    if filename in _SIBLINGS:
        return _SIBLINGS[filename]
    module: Any = None
    script = Path(__file__).resolve().parent / filename
    if script.is_file():
        spec = importlib.util.spec_from_file_location(filename[:-3], script)
        if spec is not None and spec.loader is not None:
            candidate = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(candidate)
            except Exception:  # a broken sibling must not take the review down
                candidate = None
            module = candidate
    _SIBLINGS[filename] = module
    return module


def load_doctor() -> Any:
    return load_sibling("context_doctor.py")


def load_packet() -> Any:
    return load_sibling("context_packet.py")


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


def superseding_links(body: str, front: dict[str, Any]) -> set[str]:
    """Every decision ID this one is already tied to by a supersession.

    Both spellings count. A registry entry says it on a `- Supersedes:` or
    `- Superseded by:` line; a detail record says it in `supersedes:` or
    `superseded_by:` frontmatter. Either way the disagreement has been
    settled on the record, and re-reporting it would be the noise that gets a
    check like this turned off.
    """
    links: set[str] = set()
    for found in SUPERSEDES_LINE.findall(body) + SUPERSEDED_BY_LINE.findall(body):
        links.update(RECORD_ID.findall(found))
    for key in ("supersedes", "superseded_by"):
        value = front.get(key)
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, str):
                links.update(RECORD_ID.findall(item))
    return links


def accepted_decisions(context: Path) -> list[dict[str, Any]]:
    """Accepted decisions, one record per ID, read through the packet's reader.

    A decision described both in `DECISIONS.md` and in `decisions/D-00N-*.md`
    is one decision, so the two are merged: comparing them against each other
    would report every well-documented decision as conflicting with itself.
    """
    packet = load_packet()
    doctor = load_doctor()
    if packet is None:
        return []
    merged: dict[str, dict[str, Any]] = {}
    for entry in packet.entries(context):
        if str(entry.get("kind", "")).lower() != "decision":
            continue
        record_id = str(entry.get("id") or "")
        if not record_id or EXAMPLE_ID.match(record_id):
            continue
        source = str(entry.get("source") or "")
        body = str(entry.get("body") or "")
        front: dict[str, Any] = {}
        if source not in REGISTRIES and doctor is not None:
            path = context / source
            if path.is_file() and not path.is_symlink():
                parsed, _ = doctor.parse_frontmatter(
                    path.read_text(encoding="utf-8", errors="replace")
                )
                front = parsed if isinstance(parsed, dict) else {}
        found = DATE_LINE.search(body)
        when = parse_date(front.get("created")) or parse_date(found.group(1) if found else None)
        record = merged.setdefault(
            record_id,
            {
                "id": record_id,
                "title": str(entry.get("title") or record_id),
                "sources": [],
                "statuses": set(),
                "paths": set(),
                "tokens": set(),
                "links": set(),
                "date": when,
            },
        )
        record["sources"].append(source)
        record["statuses"].add(str(entry.get("status") or "").lower())
        record["paths"].update(entry.get("paths") or set())
        record["tokens"].update(entry.get("tokens") or set())
        record["links"].update(superseding_links(body, front))
        if record["date"] is None:
            record["date"] = when
    return [record for record in merged.values() if "accepted" in record["statuses"]]


def overlap(left: dict[str, Any], right: dict[str, Any], min_terms: int) -> dict[str, Any] | None:
    """What two decisions share, or None when it is not enough to report.

    Path first, and it needs no second threshold: two standing rules anchored
    to the same file is the strongest signal available and it is rare enough
    to always be worth a look. Vocabulary is a guess and is held to a higher
    bar, because the price of a wrong guess here is a reader who stops
    reading.
    """
    packet = load_packet()
    if packet is None:
        return None
    if right["id"] in left["links"] or left["id"] in right["links"]:
        return None
    shared_paths = sorted(
        {p for p in left["paths"] if any(packet.shares_prefix(p, q) for q in right["paths"])}
        | {q for q in right["paths"] if any(packet.shares_prefix(q, p) for p in left["paths"])}
    )
    if shared_paths:
        return {"signal": "path", "paths": shared_paths, "terms": [], "strength": 100 + len(shared_paths)}
    terms = (left["tokens"] & right["tokens"]) - LEDGER_TERMS
    smaller = min(len(left["tokens"] - LEDGER_TERMS), len(right["tokens"] - LEDGER_TERMS)) or 1
    if len(terms) >= min_terms and len(terms) / smaller >= MIN_SHARED_RATIO:
        # A term both titles use is what the two decisions are *about*; a term
        # buried in two rationales may be either. Only the first few reach the
        # report line, so the ones that name the subject go first.
        titled = packet.tokens_of(left["title"] + " " + right["title"])
        ordered = sorted(terms, key=lambda term: (term not in titled, term))
        return {"signal": "topic", "paths": [], "terms": ordered, "strength": len(terms)}
    return None


def candidate_finding(
    left: dict[str, Any], right: dict[str, Any], shared: dict[str, Any], today: date
) -> dict[str, Any]:
    """One pair, named on both sides, with what they actually share.

    Both IDs, both titles, and the overlap itself. "These two both constrain
    `src/auth/`" is something a reader can settle; "possible conflict" is
    something a reader learns to skip.
    """
    if shared["signal"] == "path":
        what = "both constrain " + ", ".join(f"`{path}`" for path in shared["paths"][:4])
    else:
        what = "both are about " + ", ".join(shared["terms"][:6])
    pending = left["id"] == PENDING_ID
    lead = "this decision and an accepted one" if pending else "two accepted decisions"
    tail = "" if pending else (
        "; read both, then supersede one or record in the newer one why both stand"
    )
    ages = [age_days(record["date"], today) for record in (left, right)]
    dated = [value for value in ages if value is not None]
    # The pair only started existing when the second of the two was recorded,
    # so that is how long it has gone unreconciled. A decision not yet written
    # carries no date, which leaves the age of the rule it would land on top
    # of — the number the author of a new decision actually wants.
    days = min(dated) if dated else None
    sources = sorted({source for record in (left, right) for source in record["sources"]})
    return finding(
        "decision",
        "conflict-candidate",
        " + ".join(sources),
        f"{left['id']}: {left['title']}  <->  {right['id']}: {right['title']}",
        days,
        f"{lead}, {what}{tail}",
    ) | {"pair": [left["id"], right["id"]], "signal": shared["signal"],
         "shared_paths": shared["paths"], "shared_terms": shared["terms"]}


def conflict_candidates(
    context: Path,
    today: date,
    min_terms: int = DEFAULT_MIN_SHARED_TERMS,
    max_conflicts: int = DEFAULT_MAX_CONFLICTS,
    pending: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Pairs of accepted decisions whose scope overlaps.

    With `pending`, every pair has the not-yet-written decision on one side:
    that is the pre-append check, and it stays quiet about the rest of the
    registry so the answer to "may I record this?" is not buried in a backlog.
    """
    records = sorted(accepted_decisions(context), key=lambda item: item["id"])
    pairs: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    if pending is not None:
        for record in records:
            shared = overlap(pending, record, min_terms)
            if shared is not None:
                pairs.append((pending, record, shared))
    else:
        for index, left in enumerate(records):
            for right in records[index + 1:]:
                shared = overlap(left, right, min_terms)
                if shared is not None:
                    pairs.append((left, right, shared))
    pairs.sort(key=lambda pair: (-pair[2]["strength"], pair[0]["id"], pair[1]["id"]))
    kept = pairs[:max_conflicts]
    found = [candidate_finding(left, right, shared, today) for left, right, shared in kept]
    trimmed = len(pairs) - len(kept)
    if trimmed:
        found.append(
            finding(
                "decision", "conflict-list-trimmed", "DECISIONS.md",
                f"{trimmed} further overlapping pair(s) not listed", None,
                "the strongest overlaps are shown above; raise `--max-conflicts` to see the rest",
            )
        )
    return found


def pending_decision(text: str, files: list[str]) -> dict[str, Any] | None:
    """The decision an agent is about to append, shaped like a recorded one.

    Tokenised by the packet, so a decision compares the same way before it is
    written as it will the moment after.
    """
    packet = load_packet()
    if packet is None:
        return None
    title = " ".join(text.split())
    return {
        "id": PENDING_ID,
        "title": (title[:77] + "...") if len(title) > 80 else title,
        "sources": ["(not recorded yet)"],
        "statuses": {"accepted"},
        "paths": {path.strip().strip("/") for path in files if path.strip()}
        | packet.anchor_paths(text),
        "tokens": packet.tokens_of(text),
        # A new decision that already names the one it replaces has done the
        # thing this check exists to ask for, so that pair is not a candidate.
        "links": set(RECORD_ID.findall(text)),
        # Undated on purpose: see candidate_finding.
        "date": None,
    }


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


def review(
    target: Path,
    open_days: int = DEFAULT_OPEN_DAYS,
    snapshot_days: int = DEFAULT_SNAPSHOT_DAYS,
    min_shared_terms: int = DEFAULT_MIN_SHARED_TERMS,
    max_conflicts: int = DEFAULT_MAX_CONFLICTS,
    new_decision: str = "",
    new_decision_files: list[str] | None = None,
) -> dict[str, Any]:
    target = target.resolve()
    context = target / CONTEXT_DIRNAME
    today = date.today()
    findings: list[dict[str, Any]] = []

    if new_decision.strip():
        # The pre-append check. One question is being asked — does anything
        # accepted already cover this ground? — so nothing else is reported.
        pending = pending_decision(new_decision, new_decision_files or [])
        # An agent is about to act on this answer, so "no candidates" and "the
        # check never ran" must not read the same. A silent all-clear from a
        # broken install is worse than no check at all.
        checked = context.is_dir() and not context.is_symlink() and pending is not None
        if checked and pending is not None:
            findings = conflict_candidates(context, today, min_shared_terms, max_conflicts, pending)
        return {
            "target": str(target),
            "mode": "new-decision",
            "checked": checked,
            "open_days": open_days,
            "snapshot_days": snapshot_days,
            "summary": {"findings": len(findings),
                        "by_code": {"conflict-candidate": len(findings)} if findings else {}},
            "findings": findings,
        }

    if context.is_dir() and not context.is_symlink():
        findings.extend(pending_records(context, today, open_days))
        findings.extend(conflict_candidates(context, today, min_shared_terms, max_conflicts))

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
        "mode": "backlog",
        "open_days": open_days,
        "snapshot_days": snapshot_days,
        "summary": {"findings": len(findings), "by_code": counts},
        "findings": findings,
    }


def render(report: dict[str, Any]) -> str:
    findings = report["findings"]
    gate = report.get("mode") == "new-decision"
    if gate and not report.get("checked", True):
        return (
            "The conflict check could not run: no `project-context/` here, or\n"
            "`context_packet.py` is not installed beside this script. Nothing was\n"
            "compared. Search DECISIONS.md for the paths and terms this decision is\n"
            "about before appending it.\n"
        )
    if gate and not findings:
        return "No accepted decision shares this one's paths or terms. Record it.\n"
    if not findings:
        return "Nothing is waiting on a person.\n"
    if gate:
        lines = [f"{len(findings)} accepted decision(s) already stand on this ground:", ""]
    else:
        lines = [f"{len(findings)} item(s) waiting on a person, oldest first:", ""]
    for item in findings:
        age = f"{item['age_days']}d" if item["age_days"] is not None else "  ?"
        lines.append(f"  {age:>5}  {item['code']:<24} {item['source']}")
        lines.append(f"         {item['title']}")
        lines.append(f"         {item['detail']}")
    if gate:
        # The gate exists to be acted on, so it says what acting looks like.
        # Neither branch is "carry on and append quietly", which is the
        # failure this check was added to close.
        lines.extend([
            "",
            "Read each one before appending. Then either supersede it — `supersedes:` on the",
            "new decision, `status: superseded` and `superseded_by:` on the old — or state in",
            "the new decision why both stand.",
        ])
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=".", type=Path)
    parser.add_argument("--open-days", default=DEFAULT_OPEN_DAYS, type=int,
                        help="a question is reported once it has been open this long")
    parser.add_argument("--snapshot-days", default=DEFAULT_SNAPSHOT_DAYS, type=int)
    parser.add_argument("--min-shared-terms", default=DEFAULT_MIN_SHARED_TERMS, type=int,
                        help="terms two decisions must share before a topic overlap is reported")
    parser.add_argument("--max-conflicts", default=DEFAULT_MAX_CONFLICTS, type=int,
                        help="how many overlapping decision pairs to list; the rest are counted")
    parser.add_argument("--new-decision", default="",
                        help="check a decision not yet written against the accepted ones, and "
                             "report nothing else")
    parser.add_argument("--new-decision-files", default="",
                        help="comma-separated paths the new decision would constrain")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    target = args.target.resolve()
    if not target.exists() or not target.is_dir():
        print(f"Target must be an existing directory: {target}", file=sys.stderr)
        return 2
    report = review(
        target,
        args.open_days,
        args.snapshot_days,
        args.min_shared_terms,
        args.max_conflicts,
        args.new_decision,
        [item for item in args.new_decision_files.split(",") if item.strip()],
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
