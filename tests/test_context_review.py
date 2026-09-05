from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context" / "scripts" / "context_review.py"


def days_ago(count: int) -> str:
    return (date.today() - timedelta(days=count)).isoformat()


class ReviewTests(unittest.TestCase):
    def target(self) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        context = directory / "project-context"
        context.mkdir()
        (context / "NOW.md").write_text(
            f"# Current Project State\n\nLast reviewed: {days_ago(2)}\n", encoding="utf-8"
        )
        (context / "DECISIONS.md").write_text(
            "# Decision Registry\n\n"
            "## D-001: Settled\n\n- Status: `accepted`\n- Date: " + days_ago(100) + "\n\n"
            "## D-002: Still open for debate\n\n- Status: `proposed`\n- Date: " + days_ago(40) + "\n",
            encoding="utf-8",
        )
        (context / "QUESTIONS.md").write_text(
            "# Question Registry\n\n"
            "## Q-001: Old and unanswered\n\n- Status: `open`\n- Date: " + days_ago(35) + "\n\n"
            "## Q-002: Asked this morning\n\n- Status: `open`\n- Date: " + days_ago(1) + "\n\n"
            "## Q-003: Closed\n\n- Status: `answered`\n- Date: " + days_ago(90) + "\n",
            encoding="utf-8",
        )
        (context / "LEARNINGS.md").write_text("# Learning Registry\n", encoding="utf-8")
        return directory

    def review(self, target: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target), "--format", "json", *args],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def codes(self, report: dict) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for item in report["findings"]:
            found.setdefault(item["code"], []).append(item["title"])
        return found

    def test_a_question_is_reported_only_once_it_has_aged(self) -> None:
        """A fresh question is the discuss primitive working, not a backlog."""
        report = self.review(self.target(), "--open-days", "14")
        titles = self.codes(report).get("open-question", [])
        self.assertTrue(any("Q-001" in title for title in titles))
        self.assertFalse(any("Q-002" in title for title in titles))
        self.assertFalse(any("Q-003" in title for title in titles))

    def test_proposed_records_are_listed_and_accepted_ones_are_not(self) -> None:
        report = self.review(self.target())
        titles = self.codes(report).get("proposed-record", [])
        self.assertTrue(any("D-002" in title for title in titles))
        self.assertFalse(any("D-001" in title for title in titles))

    def test_findings_are_sorted_oldest_first(self) -> None:
        """Latency is the failure mode, so age outranks kind."""
        report = self.review(self.target())
        ages = [item["age_days"] for item in report["findings"] if item["age_days"] is not None]
        self.assertEqual(sorted(ages, reverse=True), ages)

    def test_an_unpromoted_capsule_is_named_as_one(self) -> None:
        target = self.target()
        inbox = target / "project-context" / "inbox"
        inbox.mkdir()
        (inbox / "C-2026-01-01-topic.md").write_text(
            "---\nid: C-2026-01-01-topic\nkind: capsule\nstatus: proposed\n"
            f"title: A note from a session\ncreated: {days_ago(21)}\nasserted_by: agent:test\n---\n\nA note.\n",
            encoding="utf-8",
        )
        report = self.review(target)
        self.assertTrue(any("A note from a session" in title
                            for title in self.codes(report).get("unpromoted-capsule", [])))

    def test_an_assumption_nobody_confirmed_is_a_finding(self) -> None:
        target = self.target()
        questions = target / "project-context" / "questions"
        questions.mkdir()
        (questions / "Q-010-quota.md").write_text(
            "---\nid: Q-010\nkind: question\nstatus: answered\n"
            f"title: Quota shape\ncreated: {days_ago(30)}\nasserted_by: person:daren\n---\n\n"
            "- Assumption: service accounts share the tenant quota.\n",
            encoding="utf-8",
        )
        report = self.review(target)
        self.assertIn("unconfirmed-assumption", self.codes(report))

    def test_a_confirmed_assumption_is_not(self) -> None:
        target = self.target()
        questions = target / "project-context" / "questions"
        questions.mkdir()
        (questions / "Q-010-quota.md").write_text(
            "---\nid: Q-010\nkind: question\nstatus: answered\n"
            f"title: Quota shape\ncreated: {days_ago(30)}\nasserted_by: person:daren\n---\n\n"
            "- Assumption: service accounts share the tenant quota.\n"
            "- Confirmed: checked against the provider's quota page, 2026-08-20.\n",
            encoding="utf-8",
        )
        self.assertNotIn("unconfirmed-assumption", self.codes(self.review(target)))

    def test_a_stale_pushed_snapshot_is_reported_to_the_builder(self) -> None:
        target = self.target()
        context = target / "project-context"
        (context / "global").mkdir()
        (context / "global" / "SUMMARY.md").write_text("# Global summary\n\nWe ship.\n", encoding="utf-8")
        import hashlib
        digest = hashlib.sha256((context / "global" / "SUMMARY.md").read_bytes()).hexdigest()
        (context / ".project-context.json").write_text(
            json.dumps(
                {
                    "schema": "project-context/1", "product": "project-context", "version": "0.7.0",
                    "pushed": {
                        "global/SUMMARY.md": {
                            "sha256": digest, "source_commit": "a" * 40, "pushed_at": days_ago(200),
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        report = self.review(target, "--snapshot-days", "90")
        self.assertIn("stale-snapshot", self.codes(report))

    def test_a_quiet_project_says_so_and_exits_zero(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        (directory / "project-context").mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(directory)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Nothing is waiting on a person", result.stdout)

    def test_a_backlog_is_not_a_build_failure(self) -> None:
        """CI that breaks on an open question teaches people to stop filing them."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(self.target())],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("waiting on a person", result.stdout)

    def test_the_scaffolds_own_examples_are_not_a_backlog(self) -> None:
        """A fresh install must not open with four items it did not create."""
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        init = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
        subprocess.run(
            [sys.executable, str(init), "init", "--target", str(directory),
             "--profile", "full", "--apply"],
            check=True, capture_output=True, text=True,
        )
        report = self.review(directory)
        self.assertEqual([], report["findings"], report["findings"])


if __name__ == "__main__":
    unittest.main()
