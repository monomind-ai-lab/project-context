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
SCRIPT = ROOT / "skills" / "project-context" / "scripts" / "context_capture.py"
INIT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
REVIEW = ROOT / "skills" / "project-context" / "scripts" / "context_review.py"
DOCTOR = ROOT / "skills" / "project-context" / "scripts" / "context_doctor.py"


def git(target: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(target), *args], check=True, capture_output=True, text=True,
        env={**os.environ,
             "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"},
    )


class CaptureTests(unittest.TestCase):
    """`capture` writes one capsule and nothing else.

    The command exists because capture has to be cheap enough to happen during
    the work. Every test here is about a way it could stop being cheap — a
    refusal that loses the text, a duplicate a hook left behind, a record the
    doctor then rejects — or about it doing more than the one thing it is for.
    """

    def repository(self, *, installed: bool = True, committed: bool = True) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        git(directory, "init", "-q", ".")
        git(directory, "config", "user.name", "Daren Example")
        git(directory, "config", "user.email", "d@example.invalid")
        (directory / "src.py").write_text("x = 1\n", encoding="utf-8")
        if committed:
            git(directory, "add", "-A")
            git(directory, "commit", "-qm", "first")
        if installed:
            subprocess.run(
                [sys.executable, str(INIT), "init", "--target", str(directory),
                 "--profile", "full", "--apply"],
                check=True, capture_output=True, text=True,
            )
        return directory

    def capture(self, target: Path, *args: str, expected: int = 0) -> str:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target), *args],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return result.stdout + result.stderr

    def capsules(self, target: Path) -> list[Path]:
        return sorted((target / "project-context" / "inbox").glob("C-*.md"))

    def test_it_writes_one_capsule_and_touches_nothing_else(self) -> None:
        target = self.repository()
        before = {
            str(p.relative_to(target)): p.read_bytes()
            for p in target.rglob("*") if p.is_file() and ".git/" not in str(p)
        }
        self.capture(target, "--kind", "decision", "--text", "We standardise on pnpm.", "--apply")
        after = {
            str(p.relative_to(target)): p.read_bytes()
            for p in target.rglob("*") if p.is_file() and ".git/" not in str(p)
        }
        added = set(after) - set(before)
        self.assertEqual(1, len(added), added)
        self.assertTrue(next(iter(added)).startswith("project-context/inbox/C-"))
        self.assertEqual(
            {k: v for k, v in before.items()}, {k: v for k, v in after.items() if k in before}
        )

    def test_the_capsule_it_writes_passes_the_doctor(self) -> None:
        """A capture that produces a record the doctor rejects is worse than none."""
        target = self.repository()
        self.capture(target, "--kind", "learning", "--text", "Retries amplify a throttled gateway.", "--apply")
        result = subprocess.run(
            [sys.executable, str(DOCTOR), "--target", str(target)],
            check=False, capture_output=True, text=True,
        )
        report = json.loads(result.stdout)
        self.assertEqual("healthy", report["status"], report["issues"])
        self.assertEqual(1, report["records"])

    def test_review_reports_it_as_waiting_on_a_person(self) -> None:
        target = self.repository()
        self.capture(target, "--kind", "question", "--text", "Do service accounts share the tenant quota?", "--apply")
        result = subprocess.run(
            [sys.executable, str(REVIEW), "--target", str(target), "--format", "json"],
            check=False, capture_output=True, text=True,
        )
        codes = {item["code"] for item in json.loads(result.stdout)["findings"]}
        self.assertIn("unpromoted-capsule", codes)

    def test_capturing_the_same_text_twice_leaves_one_capsule(self) -> None:
        """A `Stop` hook that fires twice must not leave two identical notes."""
        target = self.repository()
        text = "The gateway throttles before the pool is exhausted."
        self.capture(target, "--kind", "learning", "--text", text, "--apply")
        output = self.capture(target, "--kind", "learning", "--text", text, "--apply")
        self.assertIn("already captured", output)
        self.assertEqual(1, len(self.capsules(target)))

    def test_it_refuses_more_than_two_hundred_words(self) -> None:
        target = self.repository()
        output = self.capture(
            target, "--kind", "learning", "--text", "word " * 201, "--apply", expected=2
        )
        self.assertIn("201 words", output)
        self.assertIn("record it should become", output)
        self.assertEqual([], self.capsules(target))

    def test_two_hundred_words_exactly_is_allowed(self) -> None:
        target = self.repository()
        self.capture(target, "--kind", "learning", "--text", "word " * 200, "--apply")
        self.assertEqual(1, len(self.capsules(target)))

    def test_it_refuses_a_repository_with_no_install(self) -> None:
        target = self.repository(installed=False)
        output = self.capture(target, "--kind", "decision", "--text", "Anything.", "--apply", expected=2)
        self.assertIn("run `project-context init` first", output)

    def test_it_records_the_provenance_the_model_asks_for(self) -> None:
        """Actor, session, harness, model, and `binding@HEAD` (2.6)."""
        target = self.repository()
        self.capture(
            target, "--kind", "constraint", "--text", "Rate limiting belongs at the edge.",
            "--actor", "agent:claude", "--session", "session:claude-code:abc123",
            "--harness", "claude-code", "--model", "opus-5",
            "--evidence", "pr:acme/api#42", "--files", "src/api.py,src/gateway.py", "--apply",
        )
        text = self.capsules(target)[0].read_text(encoding="utf-8")
        for expected in (
            "kind: capsule", "status: proposed", "capsule_kind: constraint",
            "asserted_by: agent:claude", "session: session:claude-code:abc123",
            "harness: claude-code", "model: opus-5",
            "- pr:acme/api#42", "- src/api.py", "- src/gateway.py",
        ):
            self.assertIn(expected, text, expected)
        self.assertRegex(text, r"- commit:[a-z0-9-]+:[0-9a-f]{40}")

    def test_the_actor_defaults_to_the_git_identity(self) -> None:
        target = self.repository()
        self.capture(target, "--kind", "decision", "--text", "We ship on Tuesdays.", "--apply")
        self.assertIn("asserted_by: person:daren-example", self.capsules(target)[0].read_text(encoding="utf-8"))

    def test_it_refuses_an_actor_or_session_of_the_wrong_shape(self) -> None:
        target = self.repository()
        for flag, value in (("--actor", "Daren"), ("--session", "abc123")):
            output = self.capture(
                target, "--kind", "decision", "--text", "Anything.", flag, value, "--apply", expected=2
            )
            self.assertIn("is not", output)
        self.assertEqual([], self.capsules(target))

    def test_a_dry_run_prints_the_capsule_and_writes_nothing(self) -> None:
        target = self.repository()
        output = self.capture(target, "--kind", "proposal", "--text", "Loosen the test guardrail.", "--dry-run")
        self.assertIn("kind: capsule", output)
        self.assertIn("capsule_kind: proposal", output)
        self.assertEqual([], self.capsules(target))

    def test_it_accepts_every_kind_the_design_names(self) -> None:
        target = self.repository()
        for kind in ("decision", "learning", "question", "assumption", "constraint", "proposal"):
            self.capture(target, "--kind", kind, "--text", f"A {kind} worth keeping.", "--apply")
        self.assertEqual(6, len(self.capsules(target)))

    def test_the_title_defaults_to_the_first_sentence(self) -> None:
        target = self.repository()
        self.capture(
            target, "--kind", "learning",
            "--text", "Retries amplify throttling. The pool was never the problem.", "--apply",
        )
        text = self.capsules(target)[0].read_text(encoding="utf-8")
        self.assertIn("title: Retries amplify throttling", text)
        self.assertNotIn("title: Retries amplify throttling. The pool", text)

    def test_it_works_in_a_repository_with_no_commits(self) -> None:
        """Capture must not require a history it may be the first thing to have."""
        target = self.repository(committed=False)
        self.capture(target, "--kind", "decision", "--text", "First decision, no commits yet.", "--apply")
        text = self.capsules(target)[0].read_text(encoding="utf-8")
        self.assertIn("kind: capsule", text)
        self.assertNotIn("commit:", text)

    def test_it_reaches_no_network(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for module in ("socket", "urllib", "http.client", "requests", "ftplib", "smtplib"):
            self.assertNotIn(f"import {module}", source, module)


if __name__ == "__main__":
    unittest.main()
