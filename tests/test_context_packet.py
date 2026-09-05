from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context" / "scripts" / "context_packet.py"

SUMMARY = """# Global summary

We build one thing and we ship it small. Read GUARDRAILS before deciding.
"""
IDENTITY = "# Identity\n\nWe write plainly.\n"
GUARDRAILS = "# Guardrails\n\nNo secrets in a repository, ever.\n"
WORKFLOWS = "# Workflows\n\nBranch, review, merge.\n"

EPIC = """# Epic — notes-api

## What must be true when it is done

- **E-001 — One store.** Every note lives here.
- **E-002 — Search that finds a note.** Ranked full-text search.
"""
ARCHITECTURE = "# Architecture\n\nOne service, one database, no queue.\n"

NOW = "# Current Project State\n\nLast reviewed: 2026-09-01\n\nThe API is up.\n"

PLAN = """# Plan

## M-001: Ship the search endpoint

- Status: `active`
- Serves: E-002
- Next action: Index the body column.

## M-002: Retire the old importer

- Status: `done`
- Serves: E-001
- Next action: None.
"""

DECISIONS = """# Decision Registry

## D-001: Rate limit at the edge

- Status: `accepted`
- Decision: Throttling belongs in the gateway.
- Evidence: src/api/gateway.py@a1b2c3d

## D-002: Store timestamps in UTC

- Status: `accepted`
- Decision: Every column is UTC.
- Evidence: src/store/schema.sql@0f1e2d3

## D-003: Adopt a queue

- Status: `proposed`
- Decision: Maybe a queue for exports.
- Evidence: src/api/gateway.py@a1b2c3d
"""

LEARNINGS = """# Learning Registry

## L-001: Retries amplify a throttled gateway

- Status: `accepted`
- Scope: gateway
- Learning: A client retry loop turns throttling into an outage.
- Evidence: src/api/gateway.py@a1b2c3d
"""

QUESTIONS = """# Question Registry

## Q-001: Which quota applies to service accounts?

- Status: `open`
- Date: 2026-08-01
- Question: Do service accounts share the tenant quota?
"""


class PacketTests(unittest.TestCase):
    def target(self, *, blueprint: bool = True, globals_: bool = True) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        context = directory / "project-context"
        context.mkdir()
        for name, text in (
            ("NOW.md", NOW), ("PLAN.md", PLAN), ("DECISIONS.md", DECISIONS),
            ("LEARNINGS.md", LEARNINGS), ("QUESTIONS.md", QUESTIONS),
        ):
            (context / name).write_text(text, encoding="utf-8")
        if globals_:
            (context / "global").mkdir()
            for name, text in (
                ("SUMMARY.md", SUMMARY), ("IDENTITY.md", IDENTITY),
                ("GUARDRAILS.md", GUARDRAILS), ("WORKFLOWS.md", WORKFLOWS),
            ):
                (context / "global" / name).write_text(text, encoding="utf-8")
        if blueprint:
            (context / "blueprint").mkdir()
            (context / "blueprint" / "EPIC.md").write_text(EPIC, encoding="utf-8")
            (context / "blueprint" / "ARCHITECTURE.md").write_text(ARCHITECTURE, encoding="utf-8")
        return directory

    def packet(self, target: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--target", str(target), "--format", "json"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def sources(self, packet: dict) -> list[str]:
        return [section["source"] for section in packet["sections"]]

    def test_owner_constraints_lead_the_packet(self) -> None:
        """Order is the load-bearing part: what was not negotiable comes first.

        A packet that leads with the builder's own notes buries the guardrail
        and the epic under material the reader could have found anyway.
        """
        packet = self.packet(self.target(), "context", "--task", "rate limiting")
        sources = self.sources(packet)
        self.assertEqual(
            ["global/SUMMARY.md", "global/IDENTITY.md", "global/GUARDRAILS.md",
             "blueprint/EPIC.md", "NOW.md", "PLAN.md"],
            sources[:6],
        )

    def test_architecture_is_a_planning_and_review_concern(self) -> None:
        target = self.target()
        for mode in ("plan", "review"):
            self.assertIn(
                "blueprint/ARCHITECTURE.md",
                self.sources(self.packet(target, "context", "--mode", mode)),
                mode,
            )
        self.assertNotIn(
            "blueprint/ARCHITECTURE.md",
            self.sources(self.packet(target, "context", "--mode", "implement")),
        )

    def test_only_active_plan_items_are_carried(self) -> None:
        packet = self.packet(self.target(), "context")
        plan = next(item for item in packet["sections"] if item["source"] == "PLAN.md")
        self.assertIn("M-001", plan["text"])
        self.assertNotIn("M-002", plan["text"])

    def test_path_anchors_beat_topic_overlap(self) -> None:
        """A record naming the task's own file is evidence; shared words are a guess."""
        packet = self.packet(
            self.target(), "context", "--task", "queue timestamps", "--files", "src/api/gateway.py"
        )
        matched = {item["id"]: item for item in packet["matched"]}
        self.assertEqual("path", matched["D-001"]["reason"])
        self.assertEqual("topic", matched["D-002"]["reason"])
        self.assertGreater(matched["D-001"]["score"], matched["D-002"]["score"])
        self.assertLess(self.sources(packet).index("DECISIONS.md"), len(packet["sections"]))

    def test_a_directory_prefix_does_not_match_a_similarly_named_sibling(self) -> None:
        packet = self.packet(self.target(), "context", "--files", "src/apiary/report.py")
        self.assertNotIn("D-001", {item["id"] for item in packet["matched"] if item["reason"] == "path"})
        packet = self.packet(self.target(), "context", "--files", "src/api")
        self.assertIn("D-001", {item["id"] for item in packet["matched"] if item["reason"] == "path"})

    def test_proposed_records_are_linked_rather_than_loaded(self) -> None:
        """Verified means accepted or answered; the rest is labelled, not mixed in."""
        packet = self.packet(self.target(), "context", "--files", "src/api/gateway.py")
        self.assertNotIn("D-003", "".join(item["text"] for item in packet["sections"]))
        reasons = {link["title"]: link["reason"] for link in packet["links"]}
        self.assertIn("proposed (decision)", reasons["D-003: Adopt a queue"])

    def test_verified_only_omits_the_proposed_section_entirely(self) -> None:
        packet = self.packet(
            self.target(), "context", "--files", "src/api/gateway.py", "--verified-only"
        )
        self.assertEqual([], [link for link in packet["links"] if link["reason"].startswith("proposed")])

    def test_overflow_becomes_links_and_never_silence(self) -> None:
        """A packet must not imply that what it left out does not exist."""
        packet = self.packet(self.target(), "context", "--task", "rate limiting", "--budget", "40")
        self.assertTrue(packet["truncated"])
        self.assertLessEqual(packet["tokens"], 40)
        self.assertIn("blueprint/EPIC.md", [link["source"] for link in packet["links"]])

    def test_a_repository_with_no_hub_still_assembles(self) -> None:
        packet = self.packet(self.target(blueprint=False, globals_=False), "context", "--task", "rate limiting")
        self.assertEqual(["NOW.md", "PLAN.md"], self.sources(packet)[:2])

    def test_onboard_is_a_preset_not_a_task_packet(self) -> None:
        packet = self.packet(self.target(), "onboard")
        self.assertEqual(
            ["global/SUMMARY.md", "global/IDENTITY.md", "global/WORKFLOWS.md", "NOW.md"],
            self.sources(packet),
        )
        self.assertEqual([], packet["matched"])

    def test_an_unfilled_pushed_file_costs_no_budget(self) -> None:
        target = self.target()
        (target / "project-context" / "global" / "IDENTITY.md").write_text(
            "<!-- project-hub:unfilled -->\n# Identity\n", encoding="utf-8"
        )
        self.assertNotIn("global/IDENTITY.md", self.sources(self.packet(target, "context")))

    def test_markdown_output_names_why_each_record_was_selected(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "context", "--task", "rate limiting",
             "--files", "src/api/gateway.py", "--target", str(self.target())],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("# Project context packet", result.stdout)
        self.assertIn("matched by path", result.stdout)
        self.assertIn("## Not loaded", result.stdout)

    def test_diff_takes_the_file_set_from_the_working_tree(self) -> None:
        target = self.target()
        subprocess.run(["git", "-C", str(target), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(target), "config", "user.email", "t@example.com"], check=True)
        subprocess.run(["git", "-C", str(target), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(target), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(target), "commit", "-qm", "first"], check=True)
        (target / "src" / "api").mkdir(parents=True)
        (target / "src" / "api" / "gateway.py").write_text("# changed\n", encoding="utf-8")
        packet = self.packet(target, "context", "--mode", "review", "--diff")
        self.assertIn("src/api/gateway.py", packet["files"])
        self.assertIn("D-001", {item["id"] for item in packet["matched"] if item["reason"] == "path"})


if __name__ == "__main__":
    unittest.main()
