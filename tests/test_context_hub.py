from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "context-hub" / "scripts" / "context_hub.py"
CLI = ROOT / "src" / "project_context_cli" / "__init__.py"


class ContextHubTests(unittest.TestCase):
    maxDiff = None

    def run_hub(self, *args: str, expected: int = 0) -> tuple[dict, subprocess.CompletedProcess[str]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(expected, result.returncode, result.stderr or result.stdout)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"runtime did not emit one JSON document: {exc}\nstdout={result.stdout!r}\nstderr={result.stderr!r}")
        return payload, result

    def init(self, target: Path) -> dict:
        report, _ = self.run_hub("init", "--target", str(target), "--apply")
        return report

    def add_actor(self, target: Path, actor_id: str = "actor-alice", name: str = "Alice") -> dict:
        report, _ = self.run_hub(
            "add-actor", "--target", str(target), "--id", actor_id,
            "--name", name, "--kind", "human", "--apply",
        )
        return report

    def add_project(self, target: Path, project_id: str = "project-alpha", name: str = "Alpha") -> dict:
        report, _ = self.run_hub(
            "add-project", "--target", str(target), "--id", project_id,
            "--name", name, "--apply",
        )
        return report

    def ingest(
        self,
        target: Path,
        source: Path,
        *,
        occurred_at: str = "2026-09-01T10:30:00+08:00",
        recorded_by: str | None = None,
        binding: str | None = None,
    ) -> dict:
        arguments = [
            "ingest", "--target", str(target), "--project", "project-alpha",
            "--source", str(source), "--kind", "session", "--actor", "actor-alice",
            "--occurred-at", occurred_at, "--apply",
        ]
        if recorded_by:
            arguments.extend(("--recorded-by", recorded_by))
        if binding:
            arguments.extend(("--binding", binding))
        report, _ = self.run_hub(
            *arguments,
        )
        return report

    @staticmethod
    def git(path: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *args], check=False, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(result.stderr or result.stdout)
        return result.stdout.strip()

    def test_init_dry_run_apply_idempotency_and_root_instruction_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            agents_original = "# Repository instructions\n\nKeep this paragraph.\n"
            claude_original = "# Claude rules\n\nPreserve me exactly.\n"
            (target / "AGENTS.md").write_text(agents_original, encoding="utf-8")
            (target / "CLAUDE.md").write_text(claude_original, encoding="utf-8")

            dry, _ = self.run_hub("init", "--target", directory, "--dry-run")
            self.assertFalse((target / ".context-hub.json").exists())
            self.assertGreater(dry["summary"]["create"], 10)
            self.assertEqual(2, dry["summary"]["append_managed_block"])

            applied = self.init(target)
            self.assertTrue(applied["applied"])
            marker = json.loads((target / ".context-hub.json").read_text(encoding="utf-8"))
            self.assertEqual("context-hub/1", marker["schema_version"])
            self.assertEqual("0.1.0", marker["scaffold_version"])
            for instruction, original in (("AGENTS.md", agents_original), ("CLAUDE.md", claude_original)):
                content = (target / instruction).read_text(encoding="utf-8")
                self.assertTrue(content.startswith(original))
                self.assertEqual(1, content.count("<!-- context-hub:start -->"))
                self.assertEqual(1, content.count("<!-- context-hub:end -->"))
            self.assertTrue((target / ".agents/skills/context-hub/SKILL.md").is_file())
            pointer = (target / ".claude/skills/context-hub/SKILL.md").read_text(encoding="utf-8")
            self.assertIn(".agents/skills/context-hub/SKILL.md", pointer)
            for kind in ("entities", "relationships", "insights"):
                self.assertTrue((target / "shared" / kind).is_dir())

            second, _ = self.run_hub("init", "--target", directory, "--dry-run")
            self.assertEqual({"unchanged"}, set(second["summary"]))

            doctor, _ = self.run_hub("doctor", "--target", directory)
            self.assertEqual("healthy", doctor["status"], doctor["issues"])

    def test_init_refuses_symlink_non_utf8_and_malformed_managed_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            target = Path(directory)
            (Path(outside) / "instructions.md").write_text("outside\n", encoding="utf-8")
            (target / "AGENTS.md").symlink_to(Path(outside) / "instructions.md")
            (target / "CLAUDE.md").write_text(
                "<!-- context-hub:start -->\n<!-- context-hub:start -->\n<!-- context-hub:end -->\n",
                encoding="utf-8",
            )
            (target / "README.md").write_bytes(b"\xff\xfe")
            report, _ = self.run_hub("init", "--target", directory, "--dry-run", expected=2)
            reasons = "\n".join(action.get("reason", "") for action in report["actions"])
            self.assertIn("not valid UTF-8", reasons)
            self.assertIn("malformed or duplicated", reasons)
            self.assertIn("not a regular file", reasons)
            self.assertFalse((target / ".context-hub.json").exists())

    def test_init_repairs_ignore_boundaries_without_misclassifying_local_obsidian_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".gitignore").write_text("# keep me\n*.scratch\n", encoding="utf-8")
            (target / ".graphifyignore").write_text("# keep graph rule\nprivate-drafts/\n", encoding="utf-8")

            self.init(target)
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            graphifyignore = (target / ".graphifyignore").read_text(encoding="utf-8")
            self.assertTrue(gitignore.startswith("# keep me\n*.scratch\n"))
            self.assertTrue(graphifyignore.startswith("# keep graph rule\nprivate-drafts/\n"))
            self.assertIn(".context-hub/local.yaml", gitignore)
            self.assertIn(".obsidian/plugins/", gitignore)
            self.assertIn("sources/raw/", graphifyignore)
            self.assertIn(".agents/", graphifyignore)

            plugin = target / ".obsidian/plugins/local-only/main.js"
            plugin.parent.mkdir(parents=True)
            plugin.write_text("local plugin", encoding="utf-8")
            healthy, _ = self.run_hub("doctor", "--target", directory)
            self.assertEqual("healthy", healthy["status"], healthy["issues"])

            self.git(target, "init", "-q")
            (target / ".gitignore").write_text(gitignore + "\n!.context-hub/local.yaml\n", encoding="utf-8")
            broken, _ = self.run_hub("doctor", "--target", directory, expected=1)
            self.assertIn("ineffective-git-exclusion", {item["code"] for item in broken["issues"]})

            (target / ".gitignore").write_text(gitignore, encoding="utf-8")
            local = target / ".context-hub/local.yaml"
            local.write_text("schema: context-hub/local@1\n", encoding="utf-8")
            self.git(target, "add", "-f", ".context-hub/local.yaml")
            tracked, _ = self.run_hub("doctor", "--target", directory, expected=1)
            self.assertIn("tracked-local-config", {item["code"] for item in tracked["issues"]})

    def test_actor_and_project_creation_are_typed_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.init(target)
            actor = self.add_actor(target)
            self.assertEqual("created", actor["status"])
            actor_text = (target / "actors/actor-alice.md").read_text(encoding="utf-8")
            self.assertIn("schema: context-hub/actor@1", actor_text)
            self.assertIn("display_name: \"Alice\"", actor_text)
            self.assertIn("kind: person", actor_text)
            self.assertEqual("unchanged", self.add_actor(target)["status"])

            project = self.add_project(target)
            self.assertEqual("created", project["status"])
            project_root = target / "projects/project-alpha"
            for filename in ("PROJECT.md", "SUMMARY.md", "OVERVIEW.md", "NOW.md", "DECISIONS.md", "LEARNINGS.md"):
                self.assertTrue((project_root / filename).is_file(), filename)
            for kind in ("entities", "relationships", "insights"):
                self.assertTrue((project_root / kind).is_dir())
            project_text = (project_root / "PROJECT.md").read_text(encoding="utf-8")
            self.assertIn("id: project-alpha", project_text)
            self.assertIn('title: "Alpha"', project_text)
            self.assertIn("context_project_allowlist: []", project_text)
            self.assertEqual("unchanged", self.add_project(target)["status"])

    def test_ingest_preserves_bytes_hashes_deduplicates_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "hub"
            target.mkdir()
            source = base / "session source.bin"
            source_bytes = b"session\x00bytes\xff\n[[not-an-instruction]]\n"
            source.write_bytes(source_bytes)
            self.init(target)
            self.add_actor(target)
            self.add_project(target)

            first = self.ingest(target, source)
            self.assertFalse(first["deduplicated"])
            self.assertEqual(hashlib.sha256(source_bytes).hexdigest(), first["source_sha256"])
            raw = target / first["raw_path"]
            episode = target / first["episode_path"]
            receipt = target / first["receipt_path"]
            self.assertEqual(source_bytes, raw.read_bytes())
            self.assertIn("immutable: true", episode.read_text(encoding="utf-8"))
            self.assertIn(f"content_sha256: sha256:{first['source_sha256']}", episode.read_text(encoding="utf-8"))
            self.assertNotIn("L2 Source — untrusted verbatim text", episode.read_text(encoding="utf-8"))
            parsed_receipt = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(first["raw_path"], parsed_receipt["raw_path"])
            self.assertEqual(hashlib.sha256(episode.read_bytes()).hexdigest(), parsed_receipt["episode_sha256"])
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (raw, episode, receipt)}

            second = self.ingest(target, source)
            self.assertTrue(second["deduplicated"])
            self.assertEqual(first["episode_id"], second["episode_id"])
            self.assertEqual(1, len(list((target / ".context-hub/receipts/project-alpha").glob("*.json"))))
            self.assertEqual(1, len(list((target / "sources/episodes/project-alpha").rglob("episode-*.md"))))
            for path, snapshot in before.items():
                self.assertEqual(snapshot, (path.read_bytes(), path.stat().st_mtime_ns))

            episode.write_text(episode.read_text(encoding="utf-8") + "\nTampered envelope.\n", encoding="utf-8")
            doctor, _ = self.run_hub("doctor", "--target", str(target), expected=1)
            self.assertIn("episode-hash-mismatch", {item["code"] for item in doctor["issues"]})
            _, _ = self.run_hub(
                "ingest", "--target", str(target), "--project", "project-alpha",
                "--source", str(source), "--kind", "session", "--actor", "actor-alice",
                "--occurred-at", "2026-09-01T10:30:00+08:00", "--apply", expected=2,
            )

    @staticmethod
    def entity(record_id: str, name: str, extra: str = "") -> str:
        return f"""---
schema: context-hub/entity@1
hard_metadata:
  id: {record_id}
  scope:
    level: project
    project_ids:
      - project-alpha
  created_at: 2026-09-01T00:00:00Z
  recorded_by: actor-alice
curated_metadata:
  status: candidate
  canonical_name: {json.dumps(name)}
  entity_type: concept
  aliases: []
  asserted_by: actor-alice
  approved_by: []
  approved_at:
  evidence:
    - url:https://example.com/evidence
  supersedes: []
  superseded_by: []
soft_metadata:
  suggested_description: ""
  extracted_from: []
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Entity: {name}

{extra}
"""

    @staticmethod
    def relationship(record_id: str, subject: str, object_id: str, evidence: str = "") -> str:
        evidence_block = f"  evidence:\n    - {evidence}\n" if evidence else "  evidence: []\n"
        return f"""---
schema: context-hub/relationship@1
hard_metadata:
  id: {record_id}
  scope:
    level: project
    project_ids:
      - project-alpha
  created_at: 2026-09-01T00:00:00Z
  recorded_at: 2026-09-01T00:00:00Z
  recorded_by: actor-alice
curated_metadata:
  status: candidate
  subject_id: {subject}
  predicate: relates_to
  object_id: {object_id}
  valid_at: 2026-09-01
  invalid_at:
  asserted_by: actor-alice
  approved_by: []
  approved_at:
{evidence_block}  supersedes: []
  superseded_by: []
soft_metadata:
  extraction_method: human
  rationale: ""
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Relationship
"""

    @staticmethod
    def insight(record_id: str) -> str:
        return f"""---
schema: context-hub/insight@1
hard_metadata:
  id: {record_id}
  scope:
    level: project
    project_ids:
      - project-alpha
  created_at: 2026-09-01T00:00:00Z
  recorded_by: actor-alice
curated_metadata:
  status: candidate
  statement: Cross-file insight
  applicability: Test project
  asserted_by: actor-alice
  approved_by: []
  approved_at:
  evidence:
    - url:https://example.com/evidence
  supersedes: []
  superseded_by: []
soft_metadata:
  synthesis: ""
  entity_ids: []
  relationship_ids: []
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Insight: Cross-file insight
"""

    def test_index_is_deterministic_idempotent_and_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.init(target)
            self.add_project(target)
            project = target / "projects/project-alpha"
            (project / "entities/entity-beta.md").write_text(self.entity("entity-beta", "Beta"), encoding="utf-8")
            (project / "entities/entity-alpha.md").write_text(
                self.entity("entity-alpha", "Alpha", "See [[projects/project-alpha/NOW|current state]]."),
                encoding="utf-8",
            )
            (project / "relationships/rel-alpha-beta.md").write_text(
                self.relationship("rel-alpha-beta", "entity-alpha", "entity-beta"), encoding="utf-8"
            )
            (project / "insights/insight-alpha.md").write_text(self.insight("insight-alpha"), encoding="utf-8")

            stale, _ = self.run_hub("index", "--target", directory, "--check", expected=1)
            self.assertEqual("stale", stale["status"])
            applied, _ = self.run_hub("index", "--target", directory, "--apply")
            self.assertEqual(4, applied["summary"]["changed"])
            snapshots = {path: path.read_bytes() for path in sorted((target / "indexes").glob("*.md"))}
            entities = (target / "indexes/entities.md").read_text(encoding="utf-8")
            self.assertLess(entities.index("entity-alpha"), entities.index("entity-beta"))
            self.assertIn("[[projects/project-alpha/entities/entity-alpha|Alpha]]", entities)
            self.assertIn("scope: `project-alpha`", entities)
            self.assertIn("projects/project-alpha/NOW", (target / "indexes/wikilinks.md").read_text(encoding="utf-8"))

            current, _ = self.run_hub("index", "--target", directory, "--check")
            self.assertEqual("current", current["status"])
            second, _ = self.run_hub("index", "--target", directory, "--apply")
            self.assertEqual(0, second["summary"]["changed"])
            self.assertEqual(snapshots, {path: path.read_bytes() for path in sorted((target / "indexes").glob("*.md"))})

            (project / "entities/entity-gamma.md").write_text(self.entity("entity-gamma", "Gamma"), encoding="utf-8")
            drift, _ = self.run_hub("index", "--target", directory, "--check", expected=1)
            self.assertEqual(["indexes/entities.md"], drift["changed"])
            self.assertEqual(snapshots[target / "indexes/entities.md"], (target / "indexes/entities.md").read_bytes())

    def test_doctor_reports_duplicate_dangling_hash_evidence_and_obsidian_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "hub"
            target.mkdir()
            source = base / "source.md"
            source.write_text("primary source\n", encoding="utf-8")
            self.init(target)
            self.add_actor(target)
            self.add_project(target)
            ingestion = self.ingest(target, source)
            project = target / "projects/project-alpha"
            (project / "entities/entity-alpha.md").write_text(self.entity("entity-alpha", "Alpha"), encoding="utf-8")
            (target / "shared/entities/entity-duplicate.md").write_text(
                self.entity("entity-alpha", "Duplicate"), encoding="utf-8"
            )
            (project / "relationships/rel-broken.md").write_text(
                self.relationship("rel-broken", "entity-alpha", "entity-missing", "missing/evidence.md"),
                encoding="utf-8",
            )
            (target / ingestion["raw_path"]).write_bytes(b"tampered source\n")
            plugin = target / ".obsidian/plugins/example/main.js"
            plugin.parent.mkdir(parents=True)
            plugin.write_text("plugin state", encoding="utf-8")
            self.git(target, "init", "-q")
            self.git(target, "add", "-f", ".obsidian/plugins/example/main.js")

            report, _ = self.run_hub("doctor", "--target", str(target), expected=1)
            codes = {item["code"] for item in report["issues"]}
            self.assertEqual("error", report["status"])
            self.assertTrue(
                {"duplicate-id", "dangling-relationship-endpoint", "source-hash-mismatch", "invalid-evidence-ref", "tracked-obsidian-state"}.issubset(codes),
                report["issues"],
            )

    def test_doctor_accepts_actor_project_edges_and_registered_portable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.init(target)
            self.add_actor(target)
            self.add_project(target)
            project_file = target / "projects/project-alpha/PROJECT.md"
            project_text = project_file.read_text(encoding="utf-8").replace(
                "  workspace_bindings: []",
                "  workspace_bindings:\n"
                "    - binding_id: product-main\n"
                "      kind: git\n"
                "      root_path: .",
            )
            project_file.write_text(project_text, encoding="utf-8")
            relationship = target / "projects/project-alpha/relationships/rel-owner.md"
            relationship.write_text(
                self.relationship(
                    "rel-owner", "actor-alice", "project-alpha",
                    "repo:product-main:src/main.py@deadbeef",
                ),
                encoding="utf-8",
            )
            report, _ = self.run_hub("doctor", "--target", directory)
            self.assertEqual("healthy", report["status"], report["issues"])

    def test_bind_project_keeps_paths_local_and_drives_portable_ingest_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "hub"
            workspace = base / "product"
            target.mkdir()
            workspace.mkdir()
            (target / ".gitignore").write_text("# unrelated rule\n*.scratch\n", encoding="utf-8")
            self.git(target, "init", "-q")
            self.init(target)
            self.add_actor(target)
            self.add_actor(target, "actor-recorder", "Recorder")
            project, _ = self.run_hub(
                "add-project", "--target", str(target), "--id", "project-alpha",
                "--name", "Alpha", "--created-by", "actor-alice", "--apply",
            )
            self.assertEqual("actor-alice", project["project"]["created_by"])

            self.git(workspace, "init", "-q", "-b", "main")
            self.git(workspace, "config", "user.email", "test@example.com")
            self.git(workspace, "config", "user.name", "Test")
            source = workspace / "session.md"
            source.write_text("ACME selected the portable context design.\n", encoding="utf-8")
            self.git(workspace, "add", "session.md")
            self.git(workspace, "commit", "-q", "-m", "initial")
            self.git(workspace, "remote", "add", "origin", "git@github.com:acme/product.git")
            self.git(workspace, "update-ref", "refs/remotes/origin/main", "HEAD")
            self.git(workspace, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

            no_apply = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "bind-project", "--target", str(target),
                    "--project", "project-alpha", "--binding", "product-main",
                    "--workspace", str(workspace),
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(2, no_apply.returncode)
            self.assertFalse((target / ".context-hub/local.yaml").exists())

            binding, _ = self.run_hub(
                "bind-project", "--target", str(target), "--project", "project-alpha",
                "--binding", "product-main", "--workspace", str(workspace), "--apply",
            )
            self.assertEqual("updated", binding["status"])
            self.assertNotIn(str(workspace), json.dumps(binding))
            self.assertEqual(".context-hub/local.yaml", binding["binding"]["local_mapping"])
            project_text = (target / "projects/project-alpha/PROJECT.md").read_text(encoding="utf-8")
            self.assertIn("binding_id: product-main", project_text)
            self.assertIn('repository: "github.com/acme/product"', project_text)
            self.assertNotIn(str(workspace), project_text)
            local_text = (target / ".context-hub/local.yaml").read_text(encoding="utf-8")
            self.assertIn(str(workspace), local_text)
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertTrue(gitignore.startswith("# unrelated rule\n*.scratch\n"))
            self.assertIn(".context-hub/local.yaml", gitignore)
            ignored = subprocess.run(
                ["git", "-C", str(target), "check-ignore", "--no-index", "--quiet", ".context-hub/local.yaml"],
                check=False,
            )
            self.assertEqual(0, ignored.returncode)
            second_binding, _ = self.run_hub(
                "bind-project", "--target", str(target), "--project", "project-alpha",
                "--binding", "product-main", "--workspace", str(workspace), "--apply",
            )
            self.assertEqual("unchanged", second_binding["status"])
            self.run_hub(
                "add-project", "--target", str(target), "--id", "project-beta",
                "--name", "Beta", "--created-by", "actor-alice", "--apply",
            )
            duplicate_binding, _ = self.run_hub(
                "bind-project", "--target", str(target), "--project", "project-beta",
                "--binding", "product-main", "--workspace", str(workspace), "--apply", expected=2,
            )
            self.assertEqual("duplicate-binding-id", duplicate_binding["issues"][0]["code"])

            first = self.ingest(target, source, recorded_by="actor-recorder", binding="product-main")
            episode_text = (target / first["episode_path"]).read_text(encoding="utf-8")
            head = self.git(workspace, "rev-parse", "HEAD")
            expected_ref = f"repo:product-main:session.md@{head}"
            self.assertIn(expected_ref, episode_text)
            self.assertIn("recorded_by: actor-recorder", episode_text)
            self.assertIn("ACME selected the portable context design.", episode_text)
            receipt = json.loads((target / first["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(expected_ref, receipt["workspace_ref"])
            self.assertEqual("actor-recorder", receipt["recorded_by"])

            exact_repeat = self.ingest(target, source, recorded_by="actor-recorder", binding="product-main")
            self.assertTrue(exact_repeat["deduplicated"])
            later = self.ingest(
                target,
                source,
                occurred_at="2026-09-02T10:30:00+08:00",
                recorded_by="actor-recorder",
                binding="product-main",
            )
            self.assertFalse(later["deduplicated"])
            self.assertNotEqual(first["episode_id"], later["episode_id"])
            self.assertEqual(2, len(list((target / ".context-hub/receipts/project-alpha").glob("*.json"))))

    def test_symlinked_project_is_never_indexed_or_accepted_for_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "hub"
            outside = base / "outside-project"
            target.mkdir()
            (outside / "entities").mkdir(parents=True)
            (outside / "PROJECT.md").write_text("outside secret\n", encoding="utf-8")
            (outside / "entities/entity-secret.md").write_text("# SECRET-OUTSIDE-HUB\n", encoding="utf-8")
            self.init(target)
            (target / "projects/project-evil").symlink_to(outside, target_is_directory=True)

            self.run_hub("index", "--target", str(target), "--apply")
            indexes = "\n".join(path.read_text(encoding="utf-8") for path in (target / "indexes").glob("*.md"))
            self.assertNotIn("SECRET-OUTSIDE-HUB", indexes)
            doctor, _ = self.run_hub("doctor", "--target", str(target), expected=1)
            self.assertIn("unsafe-symlink", {item["code"] for item in doctor["issues"]})
            source = base / "source.md"
            source.write_text("source\n", encoding="utf-8")
            _, _ = self.run_hub(
                "ingest", "--target", str(target), "--project", "project-evil",
                "--source", str(source), "--kind", "session", "--actor", "actor-context-hub",
                "--occurred-at", "2026-09-01", "--apply", expected=2,
            )

    def test_apply_rechecks_parent_symlinks_and_doctor_checks_contract_boundaries(self) -> None:
        spec = importlib.util.spec_from_file_location("context_hub_runtime_test", SCRIPT)
        assert spec and spec.loader
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        with self.assertRaises(runtime.HubError):
            runtime.normalize_occurred_at("2026-09-01T10:30:00")
        self.assertEqual("2026-09-01", runtime.normalize_occurred_at("2026-09-01")[0])
        self.assertNotIn("\n", runtime.safe_markdown_inline("label]]\n# injected"))
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            target = Path(directory)
            outside = Path(outside_directory)
            plan = runtime.build_init_plan(target)
            (target / ".obsidian").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(runtime.HubError):
                runtime.apply_create_plan(plan)
            self.assertFalse((outside / "app.json").exists())

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.init(target)
            self.add_project(target)
            wrong = target / "projects/project-alpha/entities/entity-wrong.md"
            wrong.write_text("---\nschema: context-hub/insight@1\nhard_metadata:\n  id: entity-wrong\n---\n", encoding="utf-8")
            invalid = target / "projects/project-alpha/entities/entity-invalid.md"
            invalid.write_text(
                self.entity("entity-invalid", "Invalid")
                .replace("entity_type: concept", "entity_type: spaceship")
                .replace("  confidence:\n", "  confidence: impossible\n"),
                encoding="utf-8",
            )
            project_file = target / "projects/project-alpha/PROJECT.md"
            project_file.write_text(
                project_file.read_text(encoding="utf-8").replace(
                    "  workspace_bindings: []",
                    "  workspace_bindings:\n"
                    "    - binding_id: duplicate-main\n"
                    "      kind: folder\n"
                    "      root_path: .\n"
                    "    - binding_id: duplicate-main\n"
                    "      kind: folder\n"
                    "      root_path: .",
                ),
                encoding="utf-8",
            )
            graphifyignore = target / ".graphifyignore"
            graphifyignore.write_text(
                graphifyignore.read_text(encoding="utf-8").replace("sources/raw/\n", ""),
                encoding="utf-8",
            )
            doctor, _ = self.run_hub("doctor", "--target", directory, expected=1)
            codes = {item["code"] for item in doctor["issues"]}
            self.assertIn("wrong-record-schema", codes)
            self.assertIn("missing-required-metadata", codes)
            self.assertIn("missing-graphify-exclusion", codes)
            self.assertIn("invalid-record-enum", codes)
            self.assertIn("invalid-confidence", codes)
            self.assertIn("duplicate-binding-id", codes)

    def test_windows_mutations_fail_closed_without_pathname_write_fallback(self) -> None:
        spec = importlib.util.spec_from_file_location("context_hub_runtime_windows_test", SCRIPT)
        assert spec and spec.loader
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            original_os_name = runtime.os.name
            runtime.os.name = "nt"
            try:
                operations = (
                    (runtime.secure_mkdir, (target / "directory", target)),
                    (runtime.atomic_replace, (target / "replace.md", b"replacement", target)),
                    (runtime.exclusive_create, (target / "create.md", b"creation", target)),
                )
                for operation, arguments in operations:
                    with self.assertRaises(runtime.HubError) as raised:
                        operation(*arguments)
                    self.assertEqual("secure-write-unavailable", raised.exception.code)
            finally:
                runtime.os.name = original_os_name
            self.assertFalse((target / "directory").exists())
            self.assertFalse((target / "replace.md").exists())
            self.assertFalse((target / "create.md").exists())

    def test_runtime_has_only_standard_library_dependencies(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.issubset(sys.stdlib_module_names), imported - sys.stdlib_module_names)
        for forbidden in (
            "import yaml", "import sqlite3", "import graphify", "import networkx",
            "from yaml", "from sqlite3", "from graphify", "from networkx",
        ):
            self.assertNotIn(forbidden, source.casefold())
        result = subprocess.run(
            [sys.executable, "-S", str(SCRIPT), "--help"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("database-free", result.stdout)

    def test_distribution_cli_dispatches_hub_without_changing_embedded_commands(self) -> None:
        spec = importlib.util.spec_from_file_location("project_context_cli_dispatch_test", CLI)
        assert spec and spec.loader
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        calls: list[tuple[str, str, list[str]]] = []

        class FakeModule:
            @staticmethod
            def main(arguments: list[str]) -> int:
                calls.append(("main", "", arguments))
                return 17

        def fake_load(skill: str, filename: str) -> FakeModule:
            calls.append((skill, filename, []))
            return FakeModule()

        original_argv = sys.argv
        cli._load_script = fake_load
        try:
            sys.argv = ["project-context", "hub", "doctor", "--target", "/tmp/example"]
            self.assertEqual(17, cli.main())
            self.assertEqual(("context-hub", "context_hub.py", []), calls[0])
            self.assertEqual(["doctor", "--target", "/tmp/example"], calls[1][2])

            calls.clear()
            sys.argv = ["project-context", "doctor", "--target", "/tmp/example"]
            self.assertEqual(17, cli.main())
            self.assertEqual(("project-context-init", "project_context_init.py", []), calls[0])
            self.assertEqual(["doctor", "--target", "/tmp/example"], calls[1][2])
        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
