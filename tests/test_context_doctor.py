from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCTOR = ROOT / "skills" / "project-context" / "scripts" / "context_doctor.py"
INIT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"

SERVER = "def serve():\n    return 1\n"
UNKNOWN_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def git(target: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    ).stdout


class EvidenceAnchorTests(unittest.TestCase):
    """`path@commit` citations, and what the doctor can say about them.

    A resolving link proves the cited file exists; it says nothing about
    whether the file still supports the entry citing it. These cover the pin
    that makes that question answerable.
    """

    def install(self, target: Path) -> None:
        subprocess.run(
            [sys.executable, str(INIT), "init", "--target", str(target), "--install-skills", "--apply"],
            check=True, capture_output=True, text=True,
        )

    def repository(self, directory: str) -> Path:
        """A git repository with project-context installed and one citable file."""
        target = Path(directory).resolve()
        (target / "src").mkdir()
        (target / "src" / "server.py").write_text(SERVER, encoding="utf-8")
        git(target, "init", "-q", ".")
        self.install(target)
        git(target, "add", "-A")
        git(target, "commit", "-qm", "seed the repository")
        return target

    def head(self, target: Path) -> str:
        return git(target, "rev-parse", "--short=7", "HEAD").strip()

    def cite(self, target: Path, body: str, name: str = "DECISIONS.md") -> None:
        path = target / "project-context" / name
        path.write_text(path.read_text(encoding="utf-8") + body, encoding="utf-8")

    def rework_server(self, target: Path) -> None:
        path = target / "src" / "server.py"
        path.write_text(SERVER + "\n\ndef retry():\n    return serve()\n", encoding="utf-8")
        git(target, "add", "-A")
        git(target, "commit", "-qm", "add a retry loop")

    def run_doctor(self, target: Path, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(DOCTOR), "--target", str(target)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def codes(self, report: dict) -> set:
        return {issue["code"] for issue in report["issues"]}

    def detail(self, report: dict, code: str) -> str:
        details = [issue["detail"] for issue in report["issues"] if issue["code"] == code]
        self.assertEqual(1, len(details), report["issues"])
        return details[0]

    def test_a_pinned_link_target_is_checked_without_the_pin(self) -> None:
        """`src/server.py@a1b2c3d` names a file, not a file named `...@a1b2c3d`.

        Before the suffix was stripped, every anchored citation reported as a
        broken relative link — which trains contributors to stop anchoring.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                "- Status: `accepted`\n"
                f"- Evidence: [the retry loop](../src/server.py@{commit})\n",
            )
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertNotIn("broken-relative-link", self.codes(report))
            # One anchor, not two: read from the repository root the same text
            # points outside it, and an anchor the doctor cannot place is not
            # an anchor it reports on.
            self.assertEqual({"anchors": 1, "drifted": 0, "unverifiable": 0}, report["evidence"])

    def test_a_cited_path_that_moved_on_is_reported_as_drift(self) -> None:
        """The whole point: the link still resolves, the justification may not."""
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                "- Status: `accepted`\n"
                f"- Evidence: [the retry loop](../src/server.py@{commit})\n",
            )
            self.rework_server(target)

            report = self.run_doctor(target)
            self.assertEqual("warning", report["status"])
            self.assertIn("evidence-drift", self.codes(report))
            self.assertEqual(1, report["evidence"]["drifted"])
            detail = self.detail(report, "evidence-drift")
            self.assertIn("src/server.py", detail)
            self.assertIn(commit, detail)
            self.assertIn("changed in 1 commit ", detail)

    def test_an_unknown_commit_is_unverifiable_rather_than_drift(self) -> None:
        """A shallow clone or a typo is not evidence that anything changed."""
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                "- Status: `accepted`\n"
                f"- Evidence: [the retry loop](../src/server.py@{UNKNOWN_COMMIT})\n",
            )
            report = self.run_doctor(target)
            self.assertEqual("warning", report["status"])
            self.assertIn("evidence-unverifiable", self.codes(report))
            self.assertNotIn("evidence-drift", self.codes(report))
            self.assertNotIn("broken-relative-link", self.codes(report))
            self.assertEqual({"anchors": 1, "drifted": 0, "unverifiable": 1}, report["evidence"])
            self.assertIn(UNKNOWN_COMMIT, self.detail(report, "evidence-unverifiable"))

    def test_a_plain_text_anchor_resolves_from_the_repository_root(self) -> None:
        """An evidence line names a path the way it is typed at the root.

        Resolving it beside the registry file would look for
        `project-context/src/server.py`, which nobody meant.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## L-001: The retry loop hides the real timeout\n\n"
                "- Status: `accepted`\n"
                f"- Evidence: src/server.py@{commit} — the retry loop was added here\n",
                name="LEARNINGS.md",
            )
            self.rework_server(target)

            report = self.run_doctor(target)
            self.assertEqual("warning", report["status"])
            self.assertEqual({"anchors": 1, "drifted": 1, "unverifiable": 0}, report["evidence"])
            drift = [issue for issue in report["issues"] if issue["code"] == "evidence-drift"]
            self.assertEqual(["LEARNINGS.md"], [issue["path"] for issue in drift])
            self.assertIn("src/server.py", drift[0]["detail"])

    def test_a_plain_text_anchor_whose_path_is_gone_drifts(self) -> None:
        """Deletion is the strongest form of drift, and nothing else reports it.

        A plain-text anchor is not a link, so the relative-link check never
        looks at it.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## L-001: The retry loop hides the real timeout\n\n"
                f"- Evidence: src/server.py@{commit} — the retry loop was added here\n",
                name="LEARNINGS.md",
            )
            (target / "src" / "server.py").unlink()
            git(target, "add", "-A")
            git(target, "commit", "-qm", "drop the server")

            report = self.run_doctor(target)
            self.assertIn("evidence-drift", self.codes(report))
            self.assertEqual(1, report["evidence"]["drifted"])
            self.assertIn("no longer exists", self.detail(report, "evidence-drift"))

    def test_a_pin_on_a_missing_path_is_one_problem_not_two(self) -> None:
        """The link check already says the path is gone; drift would repeat it."""
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                f"- Evidence: [the retry loop](../src/gone.py@{commit})\n",
            )
            report = self.run_doctor(target)
            self.assertEqual("warning", report["status"])
            self.assertEqual(["broken-relative-link"], sorted(self.codes(report)))
            # The detail quotes what is written in the file, pin included.
            self.assertIn(f"@{commit}", self.detail(report, "broken-relative-link"))
            self.assertEqual({"anchors": 1, "drifted": 0, "unverifiable": 0}, report["evidence"])

    def test_addresses_and_version_pins_are_not_citations(self) -> None:
        """`@` is common punctuation; only a path pinned to a commit is an anchor.

        Reporting drift for `user@example.com` would make the check noise, and
        noise is how a warning stops being read.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = self.repository(directory)
            commit = self.head(target)
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                f"- Evidence: src/server.py@{commit}; ask user@example.com; pinned pkg@1.2.3\n"
                "- Evidence: [the notes](../src/server.py), owner user@example.com, node@18.1.2\n",
            )
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            # The scan ran — it found the real anchor and rejected the decoys.
            self.assertEqual({"anchors": 1, "drifted": 0, "unverifiable": 0}, report["evidence"])

    def test_a_project_folder_without_git_is_not_second_guessed(self) -> None:
        """No history means no comparison, not a report full of unverifiables."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            (target / "src").mkdir()
            (target / "src" / "server.py").write_text(SERVER, encoding="utf-8")
            self.install(target)
            self.assertFalse((target / ".git").exists())
            self.cite(
                target,
                "\n## D-001: Keep the retry loop\n\n"
                "- Evidence: [the retry loop](../src/server.py@a1b2c3d)\n"
                "- Evidence: src/server.py@a1b2c3d — the retry loop was added here\n",
            )
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual({"anchors": 0, "drifted": 0, "unverifiable": 0}, report["evidence"])
            self.assertFalse([code for code in self.codes(report) if code.startswith("evidence-")])


if __name__ == "__main__":
    unittest.main()
