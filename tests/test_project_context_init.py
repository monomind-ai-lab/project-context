from __future__ import annotations

import json
from pathlib import Path
import subprocess
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
INSTALLER = ROOT / "scripts" / "install.py"


class InitializerTests(unittest.TestCase):
    def run_script(self, *args: str, expected: int = 0) -> tuple[dict, subprocess.CompletedProcess[str]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return json.loads(result.stdout), result

    def test_empty_directory_dry_run_apply_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            dry, _ = self.run_script("init", "--target", directory, "--dry-run")
            self.assertGreater(dry["summary"]["create"], 5)
            self.assertFalse((target / "project-context").exists())

            self.run_script("init", "--target", directory, "--apply")
            for relative in (
                "README.md",
                "SKILL.md",
                "NOW.md",
                "DECISIONS.md",
                "LEARNINGS.md",
                "decisions/TEMPLATE.md",
                "designs/TEMPLATE.md",
                "incidents/TEMPLATE.md",
                "tasks/TEMPLATE.md",
            ):
                self.assertTrue((target / "project-context" / relative).is_file(), relative)
            self.assertIn("<!-- project-context:start -->", (target / "AGENTS.md").read_text())
            doctor, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"])

            second, _ = self.run_script("init", "--target", directory, "--dry-run")
            for mutation in ("create", "append_managed_block", "update_managed_block"):
                self.assertEqual(0, second["summary"].get(mutation, 0), mutation)

    def test_core_profile_and_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script(
                "init", "--target", directory, "--profile", "core", "--apply"
            )
            context = target / "project-context"
            self.assertFalse((context / "tasks").exists())
            metadata = json.loads((context / ".project-context.json").read_text())
            self.assertEqual("core", metadata["profile"])
            doctor, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"])

    def test_one_command_installer_adds_skills_and_core_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--target",
                    directory,
                    "--profile",
                    "core",
                    "--dry-run",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, dry_run.returncode, dry_run.stderr or dry_run.stdout)
            self.assertFalse((Path(directory) / ".agents").exists())
            self.assertFalse((Path(directory) / "project-context").exists())
            result = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "--target",
                    directory,
                    "--profile",
                    "core",
                    "--apply",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            target = Path(directory)
            self.assertTrue((target / ".agents/skills/project-context/SKILL.md").is_file())
            self.assertTrue((target / ".agents/skills/project-context-init/SKILL.md").is_file())
            self.assertTrue((target / "project-context/NOW.md").is_file())

    def test_consolidation_review_classifies_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for relative in ("memory", "docs/decisions", "docs/solutions", "src/context"):
                (target / relative).mkdir(parents=True, exist_ok=True)
            (target / "STATUS.md").write_text("# Status\n", encoding="utf-8")
            before = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            review, _ = self.run_script("review", "--target", directory)
            after = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            candidates = {item["path"]: item for item in review["consolidation"]["candidates"]}
            self.assertEqual(before, after)
            self.assertEqual("general_memory", candidates["memory"]["role"])
            self.assertEqual("decisions", candidates["docs/decisions"]["role"])
            self.assertEqual("learnings", candidates["docs/solutions"]["role"])
            self.assertEqual("current_state", candidates["STATUS.md"]["role"])
            self.assertNotIn("src/context", candidates)

    def test_doctor_reports_stale_state_duplicate_ids_broken_links_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script(
                "init", "--target", directory, "--profile", "core", "--apply"
            )
            context = target / "project-context"
            (context / "NOW.md").write_text(
                "# Current Project State\n\nLast reviewed: 2020-01-01\n\n[Missing](missing.md)\n",
                encoding="utf-8",
            )
            (context / "DECISIONS.md").write_text(
                "# Decisions\n\n## D-001: First\n\n## D-001: Duplicate\n",
                encoding="utf-8",
            )
            metadata = json.loads((context / ".project-context.json").read_text())
            metadata["template_version"] = "0.1.0"
            (context / ".project-context.json").write_text(
                json.dumps(metadata), encoding="utf-8"
            )
            doctor, _ = self.run_script(
                "doctor", "--target", directory, "--stale-days", "1", expected=1
            )
            codes = {issue["code"] for issue in doctor["issues"]}
            self.assertIn("stale-current-state", codes)
            self.assertIn("duplicate-record-id", codes)
            self.assertIn("broken-relative-link", codes)
            self.assertIn("template-update-available", codes)

    def test_existing_agents_preserves_surrounding_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            original = "# Existing rules\n\nKeep this exact sentence.\n"
            (target / "AGENTS.md").write_text(original, encoding="utf-8")
            (target / "AGENTS.md").chmod(0o640)
            self.run_script("init", "--target", directory, "--apply")
            updated = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(updated.startswith(original))
            self.assertEqual(1, updated.count("<!-- project-context:start -->"))
            self.assertEqual(0o640, stat.S_IMODE((target / "AGENTS.md").stat().st_mode))

    def test_crlf_surrounding_instructions_remain_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            original = b"# Existing rules\r\n\r\nKeep this exact sentence.\r\n"
            (target / "AGENTS.md").write_bytes(original)
            self.run_script("init", "--target", directory, "--apply")
            updated = (target / "AGENTS.md").read_bytes()
            self.assertTrue(updated.startswith(original))
            self.assertNotIn(b"\n", updated.replace(b"\r\n", b""))

    def test_existing_lowercase_and_uppercase_variants_receive_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name in ("agents.md", "CLAUDE.md"):
                (target / name).write_text(f"before-{name}\nafter-{name}\n", encoding="utf-8")
            self.run_script("init", "--target", directory, "--apply")
            self.assertNotIn("AGENTS.md", {path.name for path in target.iterdir()})
            for name in ("agents.md", "CLAUDE.md"):
                content = (target / name).read_text(encoding="utf-8")
                self.assertIn(f"before-{name}\nafter-{name}", content)
                self.assertEqual(1, content.count("<!-- project-context:start -->"))

    def test_custom_context_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            context = target / "project-context"
            context.mkdir()
            custom = "# My current state\nNever overwrite this.\n"
            (context / "NOW.md").write_text(custom, encoding="utf-8")
            report, _ = self.run_script("init", "--target", directory, "--apply")
            self.assertEqual(custom, (context / "NOW.md").read_text(encoding="utf-8"))
            self.assertGreater(report["summary"].get("preserve_existing", 0), 0)

    def test_legacy_memory_is_classified_not_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            legacy = target / "memory"
            legacy.mkdir()
            (legacy / "notes.md").write_text("legacy", encoding="utf-8")
            report, _ = self.run_script("inspect", "--target", directory)
            self.assertIn("memory", report["legacy_candidates"])
            self.assertEqual("legacy", (legacy / "notes.md").read_text(encoding="utf-8"))

    def test_malformed_managed_block_aborts_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_text(
                "rules\n<!-- project-context:start -->\nbroken\n", encoding="utf-8"
            )
            report, _ = self.run_script(
                "init", "--target", directory, "--apply", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())

    def test_reversed_managed_markers_abort_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_text(
                "<!-- project-context:end -->\nrules\n<!-- project-context:start -->\n",
                encoding="utf-8",
            )
            report, _ = self.run_script(
                "init", "--target", directory, "--apply", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())

    def test_harness_directory_aborts_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").mkdir()
            report, _ = self.run_script(
                "init", "--target", directory, "--apply", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())

    def test_non_utf8_harness_aborts_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_bytes(b"\xff\xfeinvalid")
            report, _ = self.run_script(
                "init", "--target", directory, "--dry-run", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())

    def test_symlinked_context_aborts_without_following_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            target = Path(directory)
            external_path = Path(external)
            (target / "project-context").symlink_to(external_path, target_is_directory=True)
            report, _ = self.run_script(
                "init", "--target", directory, "--apply", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertEqual("conflict_symlink", report["project_context"]["state"])
            self.assertEqual([], report["project_context"]["files"])
            self.assertEqual([], list(external_path.iterdir()))

    def test_symlinked_skill_parent_aborts_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            target = Path(directory)
            external_path = Path(external)
            (target / ".agents").symlink_to(external_path, target_is_directory=True)
            report, _ = self.run_script(
                "init",
                "--target",
                directory,
                "--profile",
                "core",
                "--install-skills",
                "--apply",
                expected=2,
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())
            self.assertEqual([], list(external_path.iterdir()))

    def test_tool_markers_are_detected_without_installing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".gitnexus").mkdir()
            (target / ".gitnexus" / "gitnexus.json").write_text("{}", encoding="utf-8")
            (target / "graphify-out").mkdir()
            (target / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
            (target / "openwiki").mkdir()
            (target / "openwiki" / "index.md").write_text("# Wiki", encoding="utf-8")
            report, _ = self.run_script("inspect", "--target", directory)
            for tool in ("gitnexus", "graphify", "openwiki"):
                self.assertTrue(report["tools"][tool]["detected"], tool)

    def test_incidental_graphify_prose_is_not_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "AGENTS.md").write_text(
                "Graphify may be useful if it is installed later.\n", encoding="utf-8"
            )
            report, _ = self.run_script("inspect", "--target", directory)
            marker_signals = [
                signal
                for signal in report["tools"]["graphify"]["signals"]
                if "harness" in signal.lower()
            ]
            self.assertEqual([], marker_signals)


if __name__ == "__main__":
    unittest.main()
