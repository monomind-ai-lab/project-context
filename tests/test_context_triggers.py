from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"


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


class TriggerTests(unittest.TestCase):
    def install(self, target: Path) -> Path:
        subprocess.run(
            [sys.executable, str(INIT), "init", "--target", str(target), "--install-skills", "--apply"],
            check=True, capture_output=True, text=True,
        )
        return target / ".agents/skills/project-context/scripts/context_triggers.py"

    def repository(self, stack) -> tuple[Path, Path]:
        """A git repository with project-context installed and one work commit."""
        workspace = Path(stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        target = workspace / "myrepo"
        target.mkdir()
        git(target, "init", "-q", ".")
        script = self.install(target)
        git(target, "add", "-A")
        git(target, "commit", "-qm", "install")
        (target / "feature.txt").write_text("work\n", encoding="utf-8")
        git(target, "add", "-A")
        git(target, "commit", "-qm", "ship a feature")
        return target, script

    def run_script(self, script: Path, *args: str, cwd: Path, expected: int = 0):
        result = subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd, check=False, capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return result

    def test_resolves_from_a_parent_directory_instead_of_exiting_mute(self) -> None:
        """The harness opening a workspace folder above the repository.

        Every cwd-derived candidate lands outside the repository, so the check
        used to exit 0 with no output — indistinguishable from a session where
        no trigger was open.
        """
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            result = self.run_script(script, "status", cwd=target.parent)
            self.assertIn(str(target), result.stdout)
            self.assertIn("update due", result.stdout)
            # It says it fell back rather than pretending the cwd was the repo.
            self.assertIn("install root", result.stdout)

            from_root = self.run_script(script, "status", cwd=Path(os.sep))
            self.assertIn(str(target), from_root.stdout)

    def test_a_real_project_directory_still_wins_over_the_fallback(self) -> None:
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            other = target.parent / "other"
            other.mkdir()
            subprocess.run(
                [sys.executable, str(INIT), "init", "--target", str(other), "--apply"],
                check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                [sys.executable, str(script), "status"],
                cwd=target.parent, check=False, capture_output=True, text=True,
                env={**os.environ, "CLAUDE_PROJECT_DIR": str(other)},
            )
            self.assertIn(str(other), result.stdout)
            self.assertNotIn("install root", result.stdout)

    def test_unresolvable_repository_is_reported_not_silent(self) -> None:
        with tempfile.TemporaryDirectory() as loose:
            source = (
                ROOT / "skills/project-context/scripts/context_triggers.py"
            ).read_text(encoding="utf-8")
            script = Path(loose) / "context_triggers.py"
            script.write_text(source, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), "status"],
                cwd=loose, check=False, capture_output=True, text=True,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("could not locate", result.stderr)
            self.assertIn("not a clean bill of health", result.stderr)

    def test_ack_closes_the_window_and_the_next_commit_reopens_it(self) -> None:
        """The honest "nothing fired" outcome must be expressible.

        Otherwise the only way to close the window is to edit a context file,
        which trains exactly the cosmetic-edit habit the protocol prevents.
        """
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            self.assertIn("update due", self.run_script(script, "status", cwd=target).stdout)

            acked = self.run_script(script, "ack", "--note", "docs only", cwd=target)
            self.assertIn("acknowledged", acked.stdout)
            after = self.run_script(script, "status", cwd=target)
            self.assertIn("status: current", after.stdout)
            # The ack is visible, and says what it covered.
            self.assertIn("none fired", after.stdout)
            self.assertIn("docs only", after.stdout)

            (target / "later.txt").write_text("more\n", encoding="utf-8")
            git(target, "add", "-A")
            git(target, "commit", "-qm", "later work")
            self.assertIn("update due", self.run_script(script, "status", cwd=target).stdout)

    def test_ack_does_not_cover_uncommitted_work_it_never_saw(self) -> None:
        """This is what stops `ack` becoming a one-keystroke session-long skip."""
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            self.run_script(script, "ack", "--note", "evaluated", cwd=target)
            self.assertIn(
                "status: current", self.run_script(script, "status", cwd=target).stdout
            )
            (target / "brand_new.txt").write_text("uncommitted\n", encoding="utf-8")
            reopened = self.run_script(script, "status", cwd=target)
            self.assertIn("update due", reopened.stdout)
            self.assertIn("brand_new.txt", reopened.stdout)

    def test_state_file_is_bookkeeping_not_work(self) -> None:
        """Writing an ack must not immediately invalidate that ack.

        Per-clone state also has no business in the work tree: under .claude/ it
        appeared in `git status` and rode along in `git add -A` commits, so an
        honest acknowledgement produced a tracked file change.
        """
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            self.run_script(script, "ack", "--note", "evaluated", cwd=target)
            self.assertTrue((target / ".git/project-context-state.json").is_file())
            self.assertFalse((target / ".claude/project-context-state.json").exists())
            self.assertEqual("", git(target, "status", "--porcelain").strip())
            result = self.run_script(script, "status", cwd=target)
            self.assertIn("status: current", result.stdout)
            self.assertNotIn("project-context-state.json", result.stdout)

    def test_state_falls_back_into_the_project_folder_without_git(self) -> None:
        """A plain project folder has no .git/ to hide bookkeeping in."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            script = self.install(target)
            self.assertFalse((target / ".git").exists())
            acked = self.run_script(script, "ack", "--note", "evaluated", cwd=target)
            self.assertIn("acknowledged", acked.stdout)
            self.assertTrue((target / ".claude/project-context-state.json").is_file())
            self.assertIn(
                "status: current", self.run_script(script, "status", cwd=target).stdout
            )

    def test_legacy_state_in_the_work_tree_is_still_honoured(self) -> None:
        """An ack recorded before the move must not silently reopen."""
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            self.run_script(script, "ack", "--note", "evaluated", cwd=target)
            moved = target / ".git/project-context-state.json"
            legacy = target / ".claude/project-context-state.json"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_text(moved.read_text(encoding="utf-8"), encoding="utf-8")
            moved.unlink()
            self.assertIn(
                "status: current", self.run_script(script, "status", cwd=target).stdout
            )

    def test_gate_blocks_once_then_stops(self) -> None:
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            hook = json.dumps({"session_id": "s1", "cwd": str(target)})
            first = subprocess.run(
                [sys.executable, str(script), "gate"], cwd=target, input=hook,
                check=False, capture_output=True, text=True,
            )
            payload = json.loads(first.stdout)
            self.assertEqual("block", payload["decision"])
            self.assertIn("ack", payload["reason"])
            second = subprocess.run(
                [sys.executable, str(script), "gate"], cwd=target, input=hook,
                check=False, capture_output=True, text=True,
            )
            self.assertEqual("", second.stdout.strip())

    def test_session_start_reports_the_open_window(self) -> None:
        import contextlib

        with contextlib.ExitStack() as stack:
            target, script = self.repository(stack)
            result = subprocess.run(
                [sys.executable, str(script), "report"], cwd=target,
                input=json.dumps({"session_id": "s1", "cwd": str(target)}),
                check=False, capture_output=True, text=True,
            )
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("pending updates", context)
            self.assertIn("ship a feature", context)


if __name__ == "__main__":
    unittest.main()
