"""Checks protect durable context without requiring a command ritual."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/project-context/scripts/context_check.py"
spec = importlib.util.spec_from_file_location("context_check", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ContextCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.context = self.root / "project-context"
        self.context.mkdir()
        self.registry = self.context / "DECISIONS.md"
        self.registry.write_text("# Decisions\n\n## D-001: Example\n\n- Statement: Keep records.\n")
    def test_healthy_registry_is_quiet(self):
        """An uninitialized history is not evidence of a defect."""
        self.assertEqual([], module.check(self.root, 5))
    def test_missing_reference_is_reported(self):
        """A cited decision must be retrievable from the registry."""
        (self.root / "work.md").write_text("See D-002.\n")
        self.assertIn("work.md:1:", module.check(self.root, 5)[0])
    def test_broken_registry_link_is_reported(self):
        """Registry links must lead to their evidence."""
        self.registry.write_text(self.registry.read_text() + "[detail](decisions/missing.md)\n")
        self.assertIn("broken link", module.check(self.root, 5)[0])

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

    def commit(self, subject):
        self.git("add", ".")
        self.git("-c", "user.name=Tester", "-c", "user.email=test@example.invalid", "commit", "-qm", subject)

    def test_statement_change_against_git_base_is_reported(self):
        """Committed edits must not erase the earlier decision's meaning."""
        self.commit("initial")
        self.registry.write_text(self.registry.read_text().replace("Keep records.", "Discard records."))
        self.commit("change")
        self.assertTrue(any("statement changed" in issue for issue in module.check(self.root, 5)))

    def test_status_change_is_permitted(self):
        """Supersession metadata may change while the statement remains intact."""
        self.commit("initial")
        self.registry.write_text(self.registry.read_text() + "- Status: superseded\n- Superseded by: D-002\n")
        self.commit("supersede")
        self.assertFalse(any("statement changed" in issue for issue in module.check(self.root, 5)))

    def test_stale_now_after_merged_pull_requests(self):
        """Only enough identifiable merged pull requests justify a freshness finding."""
        (self.context / "NOW.md").write_text("# Now\n")
        self.commit("initial")
        (self.context / "LEARNINGS.md").write_text("# Learnings\n")
        self.commit("Document learning (#1)")
        self.assertTrue(any("unchanged across" in issue for issue in module.check(self.root, 1)))
        self.assertFalse(any("unchanged across" in issue for issue in module.check(self.root, 5)))

    def test_plain_folder_checks_references_without_git(self):
        """Reference checks do not depend on having a Git repository."""
        import shutil
        shutil.rmtree(self.root / ".git")
        (self.root / "work.md").write_text("See D-002.\n")
        self.assertTrue(any("work.md:1:" in issue for issue in module.check(self.root, 5)))

    def test_missing_registry_still_checks_references(self):
        """A missing registry must not hide a dangling decision reference."""
        self.registry.unlink()
        (self.root / "notes.md").write_text("See D-998.\n")
        self.assertTrue(any("notes.md:1:" in item and "D-998" in item for item in module.check(self.root, 5)))

    def test_all_text_extensions_and_registry_cross_references(self):
        """Code and supersession metadata can both cite decisions."""
        (self.root / "main.go").write_text("// See D-998\n")
        self.registry.write_text(self.registry.read_text() + "- Superseded by: D-999\n")
        findings = module.check(self.root, 5)
        self.assertTrue(any("main.go:1:" in item for item in findings))
        self.assertTrue(any("DECISIONS.md:6:" in item and "D-999" in item for item in findings))

    def test_invalid_explicit_base_is_an_error(self):
        """An unavailable comparison must never masquerade as a healthy check."""
        self.commit("initial")
        result = subprocess.run(["python3", str(SCRIPT), "--target", str(self.root), "--base", "DOES_NOT_EXIST"], capture_output=True, text=True)
        self.assertEqual(2, result.returncode)
        self.assertIn("cannot resolve Git base", result.stderr)

    def test_old_edit_survives_unrelated_commit_and_points_to_heading(self):
        """Looking only at the last commit loses an earlier illicit edit."""
        self.registry.write_text("# Decisions\n\nSee D-001.\n\nMore.\n\n## D-001: Example\n\n- Statement: Keep records.\n")
        self.commit("initial")
        self.registry.write_text(self.registry.read_text().replace("Keep records.", "Discard records."))
        self.commit("edit")
        (self.root / "unrelated.txt").write_text("hello\n")
        self.commit("unrelated")
        self.assertTrue(any("DECISIONS.md:7:" in item and "statement changed" in item for item in module.check(self.root, 5)))

    def test_shallow_history_is_diagnosed(self):
        """A shallow boundary must be visible to anyone relying on history."""
        self.commit("initial")
        result = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        (self.root / ".git" / "shallow").write_text(result.stdout)
        check = subprocess.run(["python3", str(SCRIPT), "--target", str(self.root)], capture_output=True, text=True)
        self.assertEqual(0, check.returncode)
        self.assertIn("shallow Git history", check.stderr)
