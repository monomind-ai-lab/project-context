from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context" / "scripts" / "context_record.py"
INIT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
DOCTOR = ROOT / "skills" / "project-context" / "scripts" / "context_doctor.py"
REVIEW = ROOT / "skills" / "project-context" / "scripts" / "context_review.py"


def git(target: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(target), *args], check=True, capture_output=True, text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


class RecordWriterTests(unittest.TestCase):
    def repository(self, profile: str = "full") -> Path:
        target = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, target, True)
        git(target, "init", "-q", ".")
        git(target, "config", "user.name", "Daren Example")
        git(target, "config", "user.email", "d@example.invalid")
        subprocess.run(
            [sys.executable, str(INIT), "init", "--target", str(target),
             "--profile", profile, "--install-skills", "--apply"],
            check=True, capture_output=True, text=True,
        )
        git(target, "add", "-A")
        git(target, "commit", "-qm", "install")
        return target

    def record(self, target: Path, *args: str, expected: int = 0) -> str:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target), *args],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return result.stdout + result.stderr

    def test_every_operational_kind_gets_a_durable_record(self) -> None:
        target = self.repository()
        expected = {
            "decision": ("decisions", "D-001", "proposed"),
            "question": ("questions", "Q-001", "open"),
            "task": ("tasks", "T-001", "proposed"),
            "design": ("designs", "DS-001", "proposed"),
            "incident": ("incidents", "I-001", "open"),
        }
        for kind, (directory, record_id, status) in expected.items():
            with self.subTest(kind=kind):
                self.record(
                    target, "--kind", kind, "--title", f"A {kind}",
                    "--text", f"Durable {kind} evidence.", "--actor", "agent:codex", "--apply",
                )
                path = next((target / "project-context" / directory).glob(f"{record_id}-*.md"))
                body = path.read_text(encoding="utf-8")
                for value in (
                    f"id: {record_id}", f"kind: {kind}", f"status: {status}",
                    "asserted_by: agent:codex", f"# {record_id}: A {kind}",
                ):
                    self.assertIn(value, body)

        result = subprocess.run(
            [sys.executable, str(DOCTOR), "--target", str(target)],
            check=False, capture_output=True, text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual(0, result.returncode, report["issues"])
        self.assertEqual(5, report["records"])

        review = subprocess.run(
            [sys.executable, str(REVIEW), "--target", str(target), "--format", "json"],
            check=False, capture_output=True, text=True,
        )
        pending = {item["kind"] for item in json.loads(review.stdout)["findings"]}
        self.assertTrue({"decision", "design", "incident"}.issubset(pending))

    def test_decisions_and_questions_are_linked_from_their_registries(self) -> None:
        target = self.repository()
        for kind in ("decision", "question"):
            self.record(
                target, "--kind", kind, "--title", f"The {kind} title",
                "--text", f"The {kind} body.", "--apply",
            )
        decisions = (target / "project-context" / "DECISIONS.md").read_text(encoding="utf-8")
        questions = (target / "project-context" / "QUESTIONS.md").read_text(encoding="utf-8")
        self.assertIn("## D-001: The decision title", decisions)
        self.assertIn("[D-001](decisions/D-001-the-decision-title.md)", decisions)
        self.assertIn("## Q-001: The question title", questions)
        self.assertIn("[Q-001](questions/Q-001-the-question-title.md)", questions)

    def test_repeating_the_same_kind_and_title_is_idempotent(self) -> None:
        target = self.repository()
        args = ("--kind", "task", "--title", "Bound retries", "--text", "Cap retries at three.")
        self.record(target, *args, "--apply")
        output = self.record(target, *args, "--apply")
        self.assertIn("already exists", output)
        self.assertEqual(1, len(list((target / "project-context" / "tasks").glob("T-*.md"))))

    def test_dry_run_prints_both_planned_writes_and_changes_nothing(self) -> None:
        target = self.repository()
        output = self.record(
            target, "--kind", "decision", "--title", "Use SQLite",
            "--text", "Keep local state in one file.", "--dry-run",
        )
        self.assertIn("# record:", output)
        self.assertIn("# registry addition:", output)
        self.assertEqual([], list((target / "project-context" / "decisions").glob("D-*.md")))

    def test_core_profile_refuses_a_detail_record(self) -> None:
        target = self.repository("core")
        output = self.record(
            target, "--kind", "task", "--title", "Anything", "--text", "Anything.",
            "--apply", expected=2,
        )
        self.assertIn("needs the full profile", output)

    def test_cli_exposes_the_same_record_writer(self) -> None:
        target = self.repository()
        result = subprocess.run(
            [sys.executable, str(INIT), "record", "--target", str(target),
             "--kind", "design", "--title", "Queue topology",
             "--text", "Use one queue per tenant.", "--actor", "agent:codex", "--apply"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertTrue(any((target / "project-context" / "designs").glob("DS-*.md")))

    def test_it_reaches_no_network(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for module in ("socket", "urllib", "http.client", "requests", "ftplib", "smtplib"):
            self.assertNotIn(f"import {module}", source, module)


if __name__ == "__main__":
    unittest.main()
