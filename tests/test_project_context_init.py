from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import stat
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
DOCTOR = ROOT / "skills" / "project-context" / "scripts" / "context_doctor.py"
INSTALLER = ROOT / "scripts" / "install.py"


class InitializerTests(unittest.TestCase):
    def run_script(
        self,
        *args: str,
        expected: int = 0,
        env: dict[str, str] | None = None,
    ) -> tuple[dict, subprocess.CompletedProcess[str]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return json.loads(result.stdout), result

    def test_empty_directory_dry_run_apply_and_idempotency(self) -> None:
        """The default install: core files only, nothing left to propose after."""
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
            ):
                self.assertTrue((target / "project-context" / relative).is_file(), relative)
            # core is the default: the evidence folders are opt-in, not scaffolded
            # into every repository that will never file a design or an incident.
            for absent in ("tasks", "decisions", "designs", "incidents"):
                self.assertFalse((target / "project-context" / absent).exists(), absent)
            metadata = json.loads(
                (target / "project-context" / ".project-context.json").read_text()
            )
            self.assertEqual("core", metadata["profile"])
            self.assertIn("<!-- project-context:start -->", (target / "AGENTS.md").read_text())
            doctor, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"])

            second, _ = self.run_script("init", "--target", directory, "--dry-run")
            self.assertEqual({"unchanged"}, set(second["summary"]))

    def test_full_profile_adds_the_evidence_folders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--profile", "full", "--apply")
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
            metadata = json.loads(
                (target / "project-context" / ".project-context.json").read_text()
            )
            self.assertEqual("full", metadata["profile"])
            doctor, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"])

            second, _ = self.run_script(
                "init", "--target", directory, "--profile", "full", "--dry-run"
            )
            self.assertEqual({"unchanged"}, set(second["summary"]))

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
            self.assertTrue((target / "project-context/NOW.md").is_file())
            # The installer stays upstream. Shipping it into every consuming
            # repository dragged a second copy of the whole template tree with
            # it, and gave the protocol two texts to drift apart.
            self.assertFalse((target / ".agents/skills/project-context-init").exists())
            self.assertFalse((target / ".claude/skills/project-context-init").exists())

    def test_skill_install_writes_discoverable_harness_pointers(self) -> None:
        """A skill only under .agents/ is invisible to Claude Code.

        Without a pointer the description that is supposed to trigger the
        protocol can never match, and discovery falls back entirely to the
        managed instruction block.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            pointer = target / ".claude" / "skills" / "project-context" / "SKILL.md"
            self.assertTrue(pointer.is_file())
            text = pointer.read_text(encoding="utf-8")
            self.assertIn("name: project-context", text)
            self.assertIn(".agents/skills/project-context/SKILL.md", text)
            source = (
                ROOT / "skills" / "project-context" / "SKILL.md"
            ).read_text(encoding="utf-8")
            description = source.split("description:", 1)[1].splitlines()[0].strip()
            self.assertIn(description.strip('"'), text)
            # A quoted source description must not become a doubled scalar.
            self.assertNotIn('description: ""', text)
            # The pointer redirects; it never copies the protocol body.
            self.assertNotIn("## Start", text)
            # Nothing points at an installer that was never installed.
            self.assertEqual(
                ["project-context"],
                sorted(path.name for path in (target / ".claude" / "skills").iterdir()),
            )
            self.assertEqual(
                ["project-context"],
                sorted(path.name for path in (target / ".agents" / "skills").iterdir()),
            )

    def test_harness_pointer_is_idempotent_and_symlink_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            second, _ = self.run_script(
                "init", "--target", directory, "--install-skills", "--dry-run"
            )
            for mutation in ("create", "append_managed_block", "update_managed_block"):
                self.assertEqual(0, second["summary"].get(mutation, 0), mutation)

        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            target = Path(directory)
            external_path = Path(external)
            (target / ".claude").symlink_to(external_path, target_is_directory=True)
            report, _ = self.run_script(
                "init",
                "--target",
                directory,
                "--install-skills",
                "--apply",
                expected=2,
            )
            self.assertTrue(report["has_conflicts"])
            self.assertEqual([], list(external_path.iterdir()))

    def test_installed_instance_skill_documents_the_doctor(self) -> None:
        """The instance copy is the one the managed block points an agent at.

        If the diagnostic is documented only in the skill copy, stale or
        contradictory context has no advertised route to being checked.
        """
        with tempfile.TemporaryDirectory() as directory:
            self.run_script("init", "--target", directory, "--apply")
            text = (Path(directory) / "project-context" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("## Health", text)
            self.assertIn("doctor", text)

    def test_installed_instance_is_the_same_text_as_the_skill(self) -> None:
        """Two positions, one protocol.

        The instance and the harness skill used to be hand-maintained
        near-copies, so a change to one silently contradicted the other.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            instance = (target / "project-context" / "SKILL.md").read_text(encoding="utf-8")
            installed = (
                target / ".agents/skills/project-context/SKILL.md"
            ).read_text(encoding="utf-8")
            self.assertEqual(installed, instance)
            self.assertEqual(
                (ROOT / "skills/project-context/SKILL.md").read_text(encoding="utf-8"),
                instance,
            )

    def test_doctor_runs_standalone_from_the_installed_skill(self) -> None:
        """The doctor has to work in a repository that never had the installer."""
        with tempfile.TemporaryDirectory() as directory:
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            direct = subprocess.run(
                [sys.executable, str(DOCTOR), "--target", directory],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(0, direct.returncode, direct.stderr or direct.stdout)
            standalone = json.loads(direct.stdout)
            self.assertEqual("healthy", standalone["status"])
            # The delegating subcommand must report exactly what the file does.
            delegated, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual(delegated, standalone)

    def test_doctor_reports_the_routes_that_deliver_the_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            report, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", report["status"])
            self.assertTrue(report["reachability"]["delivers"])
            self.assertIn("AGENTS.md", report["reachability"]["instruction_blocks"])
            self.assertEqual(
                [".claude/skills/project-context/SKILL.md"],
                report["reachability"]["harness_pointers"],
            )

    def test_doctor_errors_when_nothing_delivers_the_protocol(self) -> None:
        """The reported failure: healthy documents, zero reachability.

        The doctor certified a repository whose hooks were unloaded, whose
        skill was undiscoverable, and whose managed block was gone.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            shutil.rmtree(target / ".claude")
            for name in ("AGENTS.md", "CLAUDE.md"):
                (target / name).write_text("# Repo\n", encoding="utf-8")
            report, _ = self.run_script("doctor", "--target", directory, expected=1)
            self.assertEqual("error", report["status"])
            self.assertFalse(report["reachability"]["delivers"])
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("no-delivery-path", codes)
            self.assertIn("missing-harness-pointer", codes)
            # One finding per missing file, named — not a single verdict that
            # either file could satisfy.
            self.assertEqual(
                ["AGENTS.md", "CLAUDE.md"],
                sorted(
                    issue["path"]
                    for issue in report["issues"]
                    if issue["code"] == "missing-instruction-block"
                ),
            )

    def test_doctor_flags_dangling_pointer_and_unresolved_hook(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            # The pointer under .claude/ survives while the skill it redirects
            # to is gone, and with it the hook script — the reported case, where
            # the hook is declared but silently never runs.
            shutil.rmtree(target / ".agents" / "skills" / "project-context")
            (target / ".claude" / "settings.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "python3 .agents/skills/project-context/scripts/context_triggers.py report",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            report, _ = self.run_script("doctor", "--target", directory, expected=1)
            codes = {issue["code"] for issue in report["issues"]}
            self.assertIn("harness-pointer-dangling", codes)
            self.assertIn("hook-command-unresolved", codes)

    def test_doctor_ignores_hooks_belonging_to_other_tooling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-skills", "--apply")
            (target / ".claude" / "settings.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "python3 scripts/unrelated_tool.py run",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            report, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", report["status"])

    def test_install_hooks_merges_without_disturbing_existing_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".claude").mkdir()
            (target / ".claude" / "settings.json").write_text(
                json.dumps(
                    {
                        "permissions": {"allow": ["Bash(npm test)"]},
                        "hooks": {
                            "SessionStart": [
                                {"hooks": [{"type": "command", "command": "echo mine"}]}
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.run_script("init", "--target", directory, "--install-hooks", "--apply")
            settings = json.loads((target / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(["Bash(npm test)"], settings["permissions"]["allow"])
            commands = [
                entry["command"]
                for event in settings["hooks"].values()
                for group in event
                for entry in group["hooks"]
            ]
            self.assertIn("echo mine", commands)
            self.assertTrue(any("context_triggers.py" in c and " report " in c for c in commands))
            self.assertTrue(any("context_triggers.py" in c and " gate " in c for c in commands))
            # SessionStart carries two of ours: the packet the session should
            # have read, then the triggers it still owes. Adding the second must
            # not strip the first.
            self.assertTrue(any("context_packet.py" in c and " onboard " in c for c in commands))
            session_start = [
                entry["command"]
                for group in settings["hooks"]["SessionStart"]
                for entry in group["hooks"]
            ]
            self.assertEqual(3, len(session_start), session_start)
            self.assertLess(
                next(i for i, c in enumerate(session_start) if "context_packet.py" in c),
                next(i for i, c in enumerate(session_start) if "context_triggers.py" in c),
            )
            # --install-hooks implies --install-skills: a hook whose script is
            # missing is a hook that silently never runs.
            self.assertTrue(
                (target / ".agents/skills/project-context/scripts/context_triggers.py").is_file()
            )
            doctor, _ = self.run_script("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"])
            self.assertIn(".claude/settings.json", doctor["reachability"]["hooks"])

    def test_install_hooks_is_idempotent_and_self_heals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.run_script("init", "--target", directory, "--install-hooks", "--apply")
            settings = target / ".claude" / "settings.json"
            first = settings.read_text(encoding="utf-8")
            second, _ = self.run_script(
                "init", "--target", directory, "--install-hooks", "--dry-run"
            )
            self.assertEqual(0, second["summary"].get("create", 0))
            self.assertEqual(0, second["summary"].get("update_hooks", 0))

            # A hand-edited duplicate is replaced, not compounded.
            payload = json.loads(first)
            payload["hooks"]["SessionStart"].append(
                {"hooks": [{"type": "command", "command": "python3 context_triggers.py report"}]}
            )
            settings.write_text(json.dumps(payload), encoding="utf-8")
            self.run_script("init", "--target", directory, "--install-hooks", "--apply")
            self.assertEqual(first, settings.read_text(encoding="utf-8"))

    def test_unparseable_hook_settings_abort_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".claude").mkdir()
            (target / ".claude" / "settings.json").write_text("{ not json", encoding="utf-8")
            report, _ = self.run_script(
                "init", "--target", directory, "--install-hooks", "--apply", expected=2
            )
            self.assertTrue(report["has_conflicts"])
            self.assertFalse((target / "project-context").exists())
            self.assertEqual("{ not json", (target / ".claude" / "settings.json").read_text())

    def test_consolidation_review_classifies_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for relative in ("memory", "docs/decisions", "docs/solutions", "src/context"):
                (target / relative).mkdir(parents=True, exist_ok=True)
            (target / "STATUS.md").write_text("# Status\n", encoding="utf-8")
            before = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            report, _ = self.run_script("consolidate", "--target", directory)
            after = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            candidates = {item["path"]: item for item in report["consolidation"]["candidates"]}
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
            metadata["version"] = "0.1.0"
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

    def test_repository_type_classification_uses_aggregate_signals(self) -> None:
        fixtures = {
            "code": (("pyproject.toml", "[project]\nname='sample'\n"), ("src/app.py", "print('ok')\n")),
            "document": (("docs/handbook.md", "# Handbook\n"), ("reports/annual.pdf", "%PDF placeholder\n")),
            "research": (("research/sources.bib", "@article{x}\n"), ("data/results.csv", "x,y\n1,2\n")),
            "writing": (("chapters/one.md", "# Chapter one\n"), ("drafts/outline.txt", "Act I\n")),
        }
        for expected_type, files in fixtures.items():
            with self.subTest(expected_type=expected_type), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                for relative, content in files:
                    path = target / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                report, _ = self.run_script("inspect", "--target", directory)
                self.assertEqual(expected_type, report["repository"]["type"])
                serialized = json.dumps(report["repository"])
                for relative, _ in files:
                    self.assertNotIn(relative, serialized)

    def test_declared_type_and_brand_new_stage_are_recorded_without_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            report, _ = self.run_script(
                "init",
                "--target",
                directory,
                "--profile",
                "core",
                "--repo-type",
                "writing",
                "--repository-stage",
                "brand-new",
                "--apply",
            )
            self.assertEqual("writing", report["repository"]["type"])
            metadata = json.loads((target / "project-context/.project-context.json").read_text())
            self.assertEqual("writing", metadata["repository_type"])
            self.assertEqual("brand-new", report["repository_stage"])
            self.assertNotIn("purpose", metadata)
            self.assertNotIn("repository_stage", metadata)

    def test_repository_classifier_ignores_generated_and_installed_skill_trees(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            generated = target / "work/generated"
            generated.mkdir(parents=True)
            for index in range(20):
                (generated / f"artifact-{index}.ts").write_text("export {}\n", encoding="utf-8")
            installed = target / ".agents/skills/example/references"
            installed.mkdir(parents=True)
            (installed / "paper.md").write_text("# Reference\n", encoding="utf-8")
            report, _ = self.run_script("inspect", "--target", directory)
            self.assertEqual("general", report["repository"]["type"])
            self.assertEqual(0.0, report["repository"]["scores"]["code"])
            self.assertEqual({}, report["repository"]["signals"])

    def test_mixed_repository_considers_cross_artifact_and_code_tools(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "src").mkdir()
            (target / "docs").mkdir()
            (target / "pyproject.toml").write_text("[project]\nname='mixed'\n", encoding="utf-8")
            for index in range(4):
                (target / f"src/module-{index}.py").write_text("pass\n", encoding="utf-8")
            for index in range(6):
                (target / f"docs/section-{index}.md").write_text("# Section\n", encoding="utf-8")
            clean_env = dict(os.environ)
            clean_env["PATH"] = ""
            report, _ = self.run_script("inspect", "--target", directory, env=clean_env)
            self.assertEqual("mixed", report["repository"]["type"])
            self.assertEqual(
                {"gitnexus", "graphify"},
                set(report["optional_tool_guidance"]["proposal_order"]),
            )
            self.assertEqual(
                "deferred",
                report["optional_tool_guidance"]["tools"]["openwiki"]["status"],
            )

    def test_optional_tools_are_filtered_by_repository_type(self) -> None:
        fixtures = {
            "code": (["pyproject.toml", *[f"src/module-{index}.py" for index in range(4)]], {"gitnexus"}),
            "document": ([f"docs/section-{index}.md" for index in range(6)], {"graphify"}),
            "research": (["research/one.bib", "research/two.bib"], {"graphify"}),
            "writing": ([f"chapters/chapter-{index}.md" for index in range(3)], {"graphify"}),
            "general": ([], set()),
        }
        clean_env = dict(os.environ)
        clean_env["PATH"] = ""
        for repo_type, (files, proposed) in fixtures.items():
            with self.subTest(repo_type=repo_type), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                for relative in files:
                    path = target / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("# fixture\n", encoding="utf-8")
                report, _ = self.run_script(
                    "inspect",
                    "--target",
                    directory,
                    "--repo-type",
                    repo_type,
                    env=clean_env,
                )
                self.assertEqual(
                    proposed,
                    set(report["optional_tool_guidance"]["proposal_order"]),
                )
                self.assertNotIn("openwiki", report["optional_tool_guidance"]["proposal_order"])

    def test_cli_availability_is_distinct_from_project_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as bin_directory:
            target = Path(directory)
            (target / "docs").mkdir()
            for index in range(6):
                (target / f"docs/section-{index}.md").write_text("# Section\n", encoding="utf-8")
            executable = Path(bin_directory) / "graphify"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = bin_directory
            available, _ = self.run_script(
                "inspect", "--target", directory, "--repo-type", "document", env=env
            )
            self.assertEqual("available-unconfigured", available["tools"]["graphify"]["state"])
            guidance = available["optional_tool_guidance"]["tools"]["graphify"]
            self.assertEqual("offer-project-configuration", guidance["action"])

            (target / "graphify-out").mkdir()
            (target / "graphify-out/graph.json").write_text("{}", encoding="utf-8")
            configured, _ = self.run_script(
                "inspect", "--target", directory, "--repo-type", "document", env=env
            )
            self.assertEqual("project-configured", configured["tools"]["graphify"]["state"])
            self.assertNotIn("graphify", configured["optional_tool_guidance"]["proposal_order"])


class ManagedBlockTests(unittest.TestCase):
    """The block is somebody else's file, and it says so.

    Everything here is about the one region Project Context writes into a
    repository it does not own: that it announces itself, that it stays inside
    the budget it claims, and that a file we had to create is a file a person
    can read from the top.
    """

    ROOT = Path(__file__).resolve().parents[1]

    def module(self):
        import importlib.util
        script = self.ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
        spec = importlib.util.spec_from_file_location("project_context_init", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def prose(self, block: str) -> list[str]:
        body = re.sub(r"<!--.*?-->", "", block, flags=re.S)
        return re.sub(r"^#+\s.*$", "", body, flags=re.M).split()

    def test_the_block_announces_that_it_is_managed(self) -> None:
        """A rule enforced silently is one that gets broken in good faith.

        The markers make the region safe on our side — only what is between
        them is replaced, and a malformed pair is refused rather than repaired.
        Nothing said so to the person or agent reading the file, who saw prose
        indistinguishable from what their own team wrote.
        """
        block = self.module().MANAGED_BLOCK
        self.assertIn("Managed region", block)
        for promise in ("rewrites everything between these", "the rest of the file is yours"):
            self.assertIn(promise, block, promise)
        # It names no command. `project-context update` is specified in the
        # design (2.10) and is not built, so promising it here would put a
        # command that does not exist into every repository that installs.
        self.assertNotIn("project-context update", block)
        # The warning is the first thing in the region, not a footnote.
        body = block.split("## Project Context", 1)[1]
        self.assertLess(body.index("Managed region"), 20)

    def test_the_block_stays_inside_the_budget_it_claims(self) -> None:
        """It was 153 words against a stated 150, checked by nothing."""
        module = self.module()
        words = self.prose(module.MANAGED_BLOCK)
        self.assertLessEqual(
            len(words), module.MANAGED_BLOCK_WORD_BUDGET,
            f"the managed block is {len(words)} prose words; it loads into every session",
        )

    def test_a_created_file_does_not_open_mid_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(
                [sys.executable, str(SCRIPT), "init", "--target", directory, "--apply"],
                check=True, capture_output=True, text=True,
            )
            for name in ("AGENTS.md", "CLAUDE.md"):
                text = (target / name).read_text(encoding="utf-8")
                self.assertTrue(text.startswith("# "), f"{name} opens with {text[:30]!r}")
                self.assertLess(text.index("# "), text.index("<!-- project-context:start -->"))
                self.assertIn("yours to write", text)

    def test_the_header_we_write_is_outside_the_markers_and_never_touched(self) -> None:
        """We write it once. Every word of it is the reader's to replace."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(
                [sys.executable, str(SCRIPT), "init", "--target", directory, "--apply"],
                check=True, capture_output=True, text=True,
            )
            agents = target / "AGENTS.md"
            rewritten = agents.read_text(encoding="utf-8").replace(
                "# Agent instructions", "# Acme API — how we work here", 1
            )
            agents.write_text(rewritten, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(SCRIPT), "init", "--target", directory, "--apply"],
                check=True, capture_output=True, text=True,
            )
            after = agents.read_text(encoding="utf-8")
            self.assertIn("# Acme API — how we work here", after)
            self.assertNotIn("# Agent instructions", after)

    def test_both_files_carry_the_same_block(self) -> None:
        """Duplicated on purpose: every file is self-sufficient.

        A pointer would be less text, but it makes one file's usefulness depend
        on another being read, and the delivery failure this rule exists to
        prevent is exactly a session that never read the other file.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(
                [sys.executable, str(SCRIPT), "init", "--target", directory, "--apply"],
                check=True, capture_output=True, text=True,
            )
            block = self.module().MANAGED_BLOCK
            for name in ("AGENTS.md", "CLAUDE.md"):
                self.assertIn(block, (target / name).read_text(encoding="utf-8"), name)


if __name__ == "__main__":
    unittest.main()
