"""Markdown-first initialization and migration preserve authored text."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/project-context-init/scripts/project_context_init.py"

class MarkdownInitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
    def run_cli(self, command, mode):
        return subprocess.run([sys.executable, str(SCRIPT), command, "--target", str(self.root), mode], capture_output=True, text=True)
    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
    def test_init_and_markerless_update(self):
        """A normal setup requires no installed protocol or later rewrite."""
        self.assertEqual(0, self.run_cli("init", "--dry-run").returncode)
        self.assertEqual({}, self.snapshot())
        self.assertEqual(0, self.run_cli("init", "--apply").returncode)
        before = self.snapshot()
        self.assertNotIn("project-context/SKILL.md", before)
        self.assertNotIn("AGENTS.md", before)
        self.assertEqual(0, self.run_cli("update", "--apply").returncode)
        self.assertEqual(before, self.snapshot())
    def test_migrate_preserves_surrounding_content(self):
        """Only the owned region can be replaced; a subsequent update stays inert."""
        self.assertEqual(0, subprocess.run([sys.executable, str(SCRIPT), "init", "--legacy", "--target", str(self.root), "--apply"], capture_output=True).returncode)
        claude = self.root / "CLAUDE.md"
        original = claude.read_text()
        claude.write_text("Owner before\n" + original + "Owner after\n")
        before = self.snapshot()
        self.assertEqual(0, self.run_cli("migrate", "--dry-run").returncode)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(0, self.run_cli("migrate", "--apply").returncode)
        migrated = claude.read_text()
        self.assertIn("Owner before\n", migrated)
        self.assertIn("Owner after\n", migrated)
        self.assertNotIn("<!-- project-context:start -->", migrated)
        before = self.snapshot()
        self.assertEqual(0, self.run_cli("update", "--apply").returncode)
        self.assertEqual(before, self.snapshot())

    def test_symlinked_record_directory_aborts(self):
        """A nested symlink cannot redirect initialization outside the target."""
        with tempfile.TemporaryDirectory() as outside:
            context = self.root / "project-context"
            context.mkdir()
            (context / "decisions").symlink_to(outside, target_is_directory=True)
            result = self.run_cli("init", "--apply")
            self.assertEqual(2, result.returncode)
            self.assertEqual([], list(Path(outside).iterdir()))

    def test_dangling_destination_symlink_aborts(self):
        """A dangling symlink is an existing path, not an empty slot to overwrite."""
        context = self.root / "project-context"
        context.mkdir()
        (context / "NOW.md").symlink_to(self.root / "missing")
        self.assertEqual(2, self.run_cli("init", "--apply").returncode)
        self.assertTrue((context / "NOW.md").is_symlink())

    def test_unsupported_opt_ins_fail_before_writing(self):
        """Explicit placement and tooling requests must not be silently ignored."""
        for args in (("--install-skills",), ("--install-hooks",), ("--placement", "local-only"), ("--profile", "full")):
            result = subprocess.run([sys.executable, str(SCRIPT), "init", "--target", str(self.root), *args, "--apply"], capture_output=True, text=True)
            self.assertEqual(2, result.returncode)
            self.assertIn("require --legacy", result.stderr)
            self.assertEqual({}, self.snapshot())
