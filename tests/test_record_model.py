"""Record model v1: one schema, one lifecycle, one version, stamped pushes.

Everything here is a property of the shared contract rather than of either
product, so a failure means two installs would disagree about what a valid
record is — which is the failure the unification exists to prevent.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
DOCTOR = ROOT / "skills" / "project-context" / "scripts" / "context_doctor.py"

RECORD = """---
id: D-001
kind: decision
status: accepted
title: Keep the retry loop
created: 2026-01-01
asserted_by: person:name
---

# D-001: Keep the retry loop
"""


class RecordModelTests(unittest.TestCase):
    def install(self, target: Path, *extra: str) -> None:
        subprocess.run(
            [sys.executable, str(INIT), "init", "--target", str(target), "--apply", *extra],
            check=True, capture_output=True, text=True,
        )

    def run_doctor(self, target: Path, expected: int = 0) -> dict:
        result = subprocess.run(
            [sys.executable, str(DOCTOR), "--target", str(target)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def codes(self, report: dict) -> set:
        return {issue["code"] for issue in report["issues"]}

    def issues(self, report: dict, code: str) -> list[dict]:
        return [issue for issue in report["issues"] if issue["code"] == code]

    def marker(self, target: Path) -> dict:
        return json.loads(
            (target / "project-context" / ".project-context.json").read_text(encoding="utf-8")
        )

    def write_marker(self, target: Path, payload: dict) -> None:
        (target / "project-context" / ".project-context.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def record(self, target: Path, name: str, body: str) -> Path:
        path = target / "project-context" / "decisions" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    # --- the marker -----------------------------------------------------

    def test_the_marker_carries_one_schema_and_one_version(self) -> None:
        """Two products, one contract: the marker says which contract it is."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            marker = self.marker(target)
            self.assertEqual("project-context/1", marker["schema"])
            self.assertEqual(
                (ROOT / "VERSION").read_text(encoding="utf-8").strip(), marker["version"]
            )
            self.assertNotIn("template_version", marker)
            self.assertEqual("project-context", marker["product"])
            self.assertTrue(marker["project_id"])
            # A repository with no Hub has no pushed set, and an empty stamp
            # table would imply one had been pushed and then emptied.
            self.assertNotIn("pushed", marker)
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual("project-context/1", report["schema"])

    def test_a_marker_from_before_the_unification_still_reports_the_upgrade(self) -> None:
        """`template_version` is retired, but an install carrying one is not lost.

        Consumer repositories pin the version they installed and never write
        back, so the only way an old install learns an upgrade exists is for
        the doctor to keep reading the key it was written with.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            marker = self.marker(target)
            del marker["version"]
            del marker["schema"]
            marker["template_version"] = "0.5.0"
            self.write_marker(target, marker)
            report = self.run_doctor(target)
            detail = self.issues(report, "template-update-available")[0]["detail"]
            self.assertIn("installed 0.5.0", detail)

    def test_another_products_version_is_never_read_as_an_upgrade(self) -> None:
        """The two products ship on their own cadences.

        Project Context at 0.7.0 and a Hub at 0.1.0 say nothing about each
        other, so a marker naming a different product must not produce an
        upgrade warning built on comparing the two numbers.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            marker = self.marker(target)
            marker["product"] = "project-hub"
            marker["version"] = "0.1.0"
            self.write_marker(target, marker)
            report = self.run_doctor(target)
            self.assertEqual([], self.issues(report, "template-update-available"))
            self.assertIn("foreign-product-marker", self.codes(report))

    def test_an_unknown_schema_string_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            marker = self.marker(target)
            marker["schema"] = "project-context/2"
            self.write_marker(target, marker)
            report = self.run_doctor(target, expected=1)
            self.assertIn("unsupported-schema", self.codes(report))

    # --- frontmatter ----------------------------------------------------

    def test_a_detail_record_carries_the_six_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(target, "2026-01-01-retry.md", RECORD)
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual(1, report["records"])

    def test_a_missing_required_key_names_the_key(self) -> None:
        """Six, not eight — but all six, or the record cannot be reasoned about."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(
                target,
                "2026-01-01-retry.md",
                "---\nid: D-001\nkind: decision\nstatus: accepted\n---\n\nbody\n",
            )
            report = self.run_doctor(target, expected=1)
            detail = self.issues(report, "missing-required-key")[0]["detail"]
            for key in ("title", "created", "asserted_by"):
                self.assertIn(key, detail)
            self.assertNotIn("id", detail.split("missing ", 1)[1].split(", "))

    def test_every_record_directory_is_validated_and_every_kind_accepted(self) -> None:
        """`decisions/`, `questions/`, `tasks/`, `inbox/` — one model for all four."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            context = target / "project-context"
            records = {
                "decisions/D-001.md": RECORD,
                "questions/Q-002.md": (
                    "---\nid: Q-002\nkind: question\nstatus: open\n"
                    "title: Which timeout applies\ncreated: 2026-01-01\n"
                    "asserted_by: person:name\n---\n"
                ),
                "tasks/T-012.md": (
                    "---\nid: T-012\nkind: task\nstatus: proposed\n"
                    "title: Rework the retry loop\ncreated: 2026-01-01\n"
                    "asserted_by: agent:claude\n---\n"
                ),
                "inbox/C-2026-01-01-a1b2.md": (
                    "---\nid: C-2026-01-01-a1b2\nkind: capsule\nstatus: proposed\n"
                    "title: The timeout is upstream\ncreated: 2026-01-01\n"
                    "asserted_by: agent:claude\nsession: session:claude-code:abc123\n---\n"
                ),
            }
            for relative, body in records.items():
                path = context / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual(4, report["records"])

    def test_a_capsule_id_of_the_wrong_shape_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            path = target / "project-context" / "inbox" / "capsule.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\nid: capsule-1\nkind: capsule\nstatus: proposed\n"
                "title: A thought\ncreated: 2026-01-01\nasserted_by: person:name\n---\n",
                encoding="utf-8",
            )
            report = self.run_doctor(target, expected=1)
            self.assertIn("invalid-record-id", self.codes(report))

    def test_a_detail_record_without_frontmatter_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(target, "2026-01-01-retry.md", "# A decision\n\nno frontmatter\n")
            report = self.run_doctor(target, expected=1)
            self.assertIn("missing-frontmatter", self.codes(report))

    def test_the_scaffolding_in_a_record_directory_is_not_a_record(self) -> None:
        """`README.md` and `TEMPLATE.md` are how to write one, not one."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target, "--profile", "full")
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual(0, report["records"])

    def test_a_retired_field_is_reported_without_being_rewritten(self) -> None:
        """Absent means absent; a required-but-empty field is noise."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            body = RECORD.replace(
                "asserted_by: person:name\n",
                "asserted_by: person:name\nconfidence: 0.7\nsupersedes: []\n",
            )
            path = self.record(target, "2026-01-01-retry.md", body)
            report = self.run_doctor(target)
            detail = self.issues(report, "retired-frontmatter-key")[0]["detail"]
            self.assertIn("confidence", detail)
            self.assertIn("supersedes", detail)
            # Reported, never rewritten: the record is left byte-for-byte.
            self.assertEqual(body, path.read_text(encoding="utf-8"))

    def test_an_agent_may_not_approve_what_it_asserted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(
                target,
                "2026-01-01-retry.md",
                RECORD.replace(
                    "asserted_by: person:name\n",
                    "asserted_by: agent:claude\napproved_by: agent:claude\n",
                ),
            )
            report = self.run_doctor(target, expected=1)
            self.assertIn("agent-self-approval", self.codes(report))

    # --- the lifecycle --------------------------------------------------

    def test_the_retired_lifecycle_words_are_named_and_translated(self) -> None:
        """`candidate → approved → superseded` is retired, in both positions.

        A record and a registry hold status in different places, and the old
        vocabulary has to be caught in both or half an install stays on it.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(
                target, "2026-01-01-retry.md", RECORD.replace("status: accepted", "status: approved")
            )
            registry = target / "project-context" / "DECISIONS.md"
            registry.write_text(
                registry.read_text(encoding="utf-8")
                + "\n## D-002: Another\n\n- Status: `candidate`\n",
                encoding="utf-8",
            )
            report = self.run_doctor(target, expected=1)
            details = [issue["detail"] for issue in self.issues(report, "retired-status")]
            self.assertEqual(2, len(details), report["issues"])
            self.assertTrue(any("`approved` is retired; read `accepted`" == d for d in details))
            self.assertTrue(any("`candidate` is retired; read `proposed`" == d for d in details))

    LIFECYCLES = {
        "decision": ("proposed", "accepted", "superseded", "rejected"),
        "learning": ("proposed", "accepted", "superseded", "rejected"),
        "capsule": ("proposed", "accepted", "superseded", "rejected"),
        "question": ("open", "answered", "superseded"),
        "task": ("proposed", "active", "done", "dropped"),
    }

    def kind_record(self, kind: str, status: str) -> str:
        return (
            f"---\nid: D-001\nkind: {kind}\nstatus: {status}\n"
            f"title: A record\ncreated: 2026-01-01\nasserted_by: person:name\n---\n"
        )

    def test_each_kind_admits_exactly_its_own_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            for kind, states in self.LIFECYCLES.items():
                for status in states:
                    with self.subTest(kind=kind, status=status):
                        self.record(target, "record.md", self.kind_record(kind, status))
                        report = self.run_doctor(target)
                        self.assertEqual("healthy", report["status"], report["issues"])

    def test_a_state_belonging_to_another_kind_is_an_error(self) -> None:
        """A permissive union would let two people write questions two ways.

        A question is not an assertion and a task is not a claim, so borrowing
        one kind's words for another is as wrong as inventing a word.
        """
        borrowed = (
            ("question", "accepted"),
            ("question", "rejected"),
            ("decision", "answered"),
            ("decision", "done"),
            ("learning", "open"),
            ("task", "accepted"),
            ("capsule", "active"),
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            for kind, status in borrowed:
                with self.subTest(kind=kind, status=status):
                    self.record(target, "record.md", self.kind_record(kind, status))
                    report = self.run_doctor(target, expected=1)
                    detail = self.issues(report, "invalid-status")[0]["detail"]
                    self.assertIn(f"`{status}` is not a {kind} state", detail)
                    # The message carries the vocabulary that kind does use.
                    for expected in self.LIFECYCLES[kind]:
                        self.assertIn(expected, detail)

    def test_a_task_has_terminal_states_of_its_own(self) -> None:
        """`done` and `dropped`. A finished task is not a superseded claim."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            for status in ("done", "dropped"):
                with self.subTest(status=status):
                    self.record(target, "record.md", self.kind_record("task", status))
                    self.assertEqual("healthy", self.run_doctor(target)["status"])
            self.record(target, "record.md", self.kind_record("task", "superseded"))
            report = self.run_doctor(target, expected=1)
            self.assertIn("invalid-status", self.codes(report))

    def test_an_invented_state_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.record(target, "record.md", self.kind_record("decision", "shipped"))
            report = self.run_doctor(target, expected=1)
            self.assertIn("invalid-status", self.codes(report))

    def test_a_question_registry_uses_the_question_vocabulary(self) -> None:
        """A registry has no frontmatter, so its kind comes from its filename."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            registry = target / "project-context" / "QUESTIONS.md"
            registry.write_text(
                "# Questions\n\n## Q-001: Which timeout\n\n- Status: `answered`\n",
                encoding="utf-8",
            )
            self.assertEqual("healthy", self.run_doctor(target)["status"])
            registry.write_text(
                "# Questions\n\n## Q-001: Which timeout\n\n- Status: `accepted`\n",
                encoding="utf-8",
            )
            report = self.run_doctor(target, expected=1)
            self.assertIn(
                "`accepted` is not a question state",
                self.issues(report, "invalid-status")[0]["detail"],
            )

    # --- the reference grammar ------------------------------------------

    def test_a_reference_is_validated_by_shape(self) -> None:
        """Shape only. Resolution is optional and never required."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            good = "\n".join(
                f"  - {reference}"
                for reference in (
                    "session:claude-code:abc123",
                    "commit:origin:a1b2c3d4",
                    "pr:origin#42",
                    "review:origin#42/c-9",
                    "ticket:jira:PC-17",
                    "doc:origin:docs/a.md@a1b2c3d",
                    "url:https://example.invalid/a",
                    "capsule:C-2026-01-01-a1b2",
                )
            )
            self.record(
                target,
                "2026-01-01-good.md",
                RECORD.replace("---\n\n# D-001", f"evidence:\n{good}\n---\n\n# D-001"),
            )
            self.assertEqual("healthy", self.run_doctor(target)["status"])

            self.record(
                target,
                "2026-01-01-good.md",
                RECORD.replace("---\n\n# D-001", "evidence:\n  - pr:origin#not-a-number\n---\n\n# D-001"),
            )
            report = self.run_doctor(target, expected=1)
            self.assertIn("invalid-reference", self.codes(report))

    # --- the pushed set --------------------------------------------------

    def push(self, target: Path, relative: str, body: str, *, stamp: bool = True) -> None:
        path = target / "project-context" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        if not stamp:
            return
        marker = self.marker(target)
        marker.setdefault("pushed", {})[relative] = {
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "source_commit": "0123456789abcdef0123456789abcdef01234567",
            "pushed_at": "2026-01-01T00:00:00Z",
        }
        self.write_marker(target, marker)

    def test_an_intact_pushed_set_is_healthy_and_summarised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.push(target, "global/GUARDRAILS.md", "# Guardrails\n\nOne rule.\n")
            self.push(target, "blueprint/EPIC.md", "# Epic\n\n## E-001: Ship it\n")
            report = self.run_doctor(target)
            self.assertEqual("healthy", report["status"], report["issues"])
            self.assertEqual(2, report["pushed"]["stamped"])
            self.assertEqual("2026-01-01T00:00:00Z", report["pushed"]["oldest_pushed_at"])

    def test_editing_a_pushed_file_is_an_error_that_names_the_hub(self) -> None:
        """The pushed set is read-only here, and the stamp is what proves it."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.push(target, "global/GUARDRAILS.md", "# Guardrails\n\nOne rule.\n")
            edited = target / "project-context" / "global" / "GUARDRAILS.md"
            edited.write_text("# Guardrails\n\nOne rule, reworded here.\n", encoding="utf-8")
            report = self.run_doctor(target, expected=1)
            issue = self.issues(report, "pushed-file-modified")[0]
            self.assertEqual("global/GUARDRAILS.md", issue["path"])
            self.assertIn("Hub", issue["detail"])
            self.assertEqual(1, report["pushed"]["modified"])

    def test_a_stamped_file_that_is_gone_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.push(target, "blueprint/EPIC.md", "# Epic\n")
            (target / "project-context" / "blueprint" / "EPIC.md").unlink()
            report = self.run_doctor(target, expected=1)
            self.assertIn("pushed-file-missing", self.codes(report))

    def test_a_file_added_to_the_pushed_set_by_hand_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            self.push(target, "global/LOCAL.md", "# Mine\n", stamp=False)
            report = self.run_doctor(target)
            issue = self.issues(report, "pushed-file-unstamped")[0]
            self.assertEqual("global/LOCAL.md", issue["path"])

    def test_the_owners_window_is_never_linted(self) -> None:
        """A place to think stops being one the moment it reports errors.

        `owners_window/` is Hub-only, so the repository doctor should never see
        it — and must stay silent if a folder by that name turns up anyway.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            window = target / "project-context" / "owners_window"
            window.mkdir()
            (window / "half-formed.md").write_text(
                "# Something\n\n[a broken link](nowhere.md)\n\n- Status: `candidate`\n",
                encoding="utf-8",
            )
            self.assertEqual("healthy", self.run_doctor(target)["status"])

    # --- both instruction files ------------------------------------------

    def test_install_writes_the_managed_block_into_both_files(self) -> None:
        """A Claude-only repository used to get rules no Claude session reads."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            for name in ("AGENTS.md", "CLAUDE.md"):
                text = (target / name).read_text(encoding="utf-8")
                self.assertIn("<!-- project-context:start -->", text)
                self.assertIn("<!-- project-context:end -->", text)
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                (target / "CLAUDE.md").read_text(encoding="utf-8"),
            )
            report = self.run_doctor(target)
            self.assertEqual(
                ["AGENTS.md", "CLAUDE.md"], report["reachability"]["instruction_blocks"]
            )

    def test_the_file_that_exists_gets_the_block_and_the_other_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            original = "# House rules\n\nKeep this sentence.\n"
            (target / "CLAUDE.md").write_text(original, encoding="utf-8")
            self.install(target)
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertTrue(claude.startswith(original))
            self.assertEqual(1, claude.count("<!-- project-context:start -->"))
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertEqual("healthy", self.run_doctor(target)["status"])

    def test_a_missing_block_is_one_finding_naming_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            (target / "CLAUDE.md").write_text("# House rules\n", encoding="utf-8")
            report = self.run_doctor(target)
            missing = self.issues(report, "missing-instruction-block")
            self.assertEqual(1, len(missing), report["issues"])
            self.assertEqual("CLAUDE.md", missing[0]["path"])
            self.assertIn("CLAUDE.md", missing[0]["detail"])

    def test_a_lowercase_variant_already_satisfies_its_role(self) -> None:
        """The file that is already there gets the block, whatever its casing."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "agents.md").write_text("# rules\n", encoding="utf-8")
            (target / "claude.md").write_text("# rules\n", encoding="utf-8")
            self.install(target)
            names = {path.name for path in target.iterdir()}
            self.assertNotIn("AGENTS.md", names)
            self.assertNotIn("CLAUDE.md", names)
            report = self.run_doctor(target)
            self.assertEqual([], self.issues(report, "missing-instruction-block"))

    # --- the superseded Context Hub ---------------------------------------

    def test_an_old_hub_marker_is_diagnosed_rather_than_ignored(self) -> None:
        """The only part of Context Hub that ships forward.

        A half-upgraded install has records nothing here understands. Saying so
        is the difference between a diagnosis and a repository that looks
        healthy while its context is unreadable.
        """
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            (target / ".context-hub.json").write_text(
                json.dumps({"schema_version": "context-hub/1"}), encoding="utf-8"
            )
            report = self.run_doctor(target)
            issue = self.issues(report, "legacy-context-hub-marker")[0]
            self.assertEqual(".context-hub.json", issue["path"])
            self.assertIn("superseded", issue["detail"])

    def test_an_old_schema_string_in_the_marker_is_diagnosed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            marker = self.marker(target)
            marker["schema"] = "context-hub/1"
            self.write_marker(target, marker)
            report = self.run_doctor(target)
            # Recognised, so it is a diagnosis rather than an unsupported schema.
            self.assertNotIn("unsupported-schema", self.codes(report))
            detail = self.issues(report, "legacy-context-hub-marker")[0]["detail"]
            self.assertIn("context-hub/1", detail)
            self.assertIn("project-context/1", detail)

    def test_an_old_managed_block_is_diagnosed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.install(target)
            path = target / "AGENTS.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n<!-- context-hub:start -->\nold rules\n<!-- context-hub:end -->\n",
                encoding="utf-8",
            )
            report = self.run_doctor(target)
            issue = self.issues(report, "legacy-context-hub-block")[0]
            self.assertEqual("AGENTS.md", issue["path"])

    def test_the_superseded_hub_is_gone_from_the_distribution(self) -> None:
        self.assertFalse((ROOT / "skills" / "context-hub").exists())
        self.assertFalse((ROOT / "tests" / "test_context_hub.py").exists())
        self.assertFalse((ROOT / "prompts" / "create-context-hub.md").exists())
        # Kept as historical record, headed as superseded.
        # Kept as historical record, in an archive that says so structurally
        # rather than only in a header — docs/ is the public Pages root.
        self.assertFalse((ROOT / "docs" / "context-hub-architecture.md").exists())
        archive = ROOT / "docs" / "archive"
        for name in ("context-hub-architecture.md", "context-hub-handoff.md"):
            doc = archive / name
            self.assertTrue(doc.is_file(), name)
            self.assertIn("Superseded", doc.read_text(encoding="utf-8")[:600])
        self.assertTrue((archive / "README.md").is_file())


if __name__ == "__main__":
    unittest.main()
