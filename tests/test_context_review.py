from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "project-context" / "scripts" / "context_review.py"


def days_ago(count: int) -> str:
    return (date.today() - timedelta(days=count)).isoformat()


class ReviewTests(unittest.TestCase):
    def target(self) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        context = directory / "project-context"
        context.mkdir()
        (context / "NOW.md").write_text(
            f"# Current Project State\n\nLast reviewed: {days_ago(2)}\n", encoding="utf-8"
        )
        (context / "DECISIONS.md").write_text(
            "# Decision Registry\n\n"
            "## D-001: Settled\n\n- Status: `accepted`\n- Date: " + days_ago(100) + "\n\n"
            "## D-002: Still open for debate\n\n- Status: `proposed`\n- Date: " + days_ago(40) + "\n",
            encoding="utf-8",
        )
        (context / "QUESTIONS.md").write_text(
            "# Question Registry\n\n"
            "## Q-001: Old and unanswered\n\n- Status: `open`\n- Date: " + days_ago(35) + "\n\n"
            "## Q-002: Asked this morning\n\n- Status: `open`\n- Date: " + days_ago(1) + "\n\n"
            "## Q-003: Closed\n\n- Status: `answered`\n- Date: " + days_ago(90) + "\n",
            encoding="utf-8",
        )
        (context / "LEARNINGS.md").write_text("# Learning Registry\n", encoding="utf-8")
        return directory

    def review(self, target: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target), "--format", "json", *args],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def codes(self, report: dict) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for item in report["findings"]:
            found.setdefault(item["code"], []).append(item["title"])
        return found

    def test_a_question_is_reported_only_once_it_has_aged(self) -> None:
        """A fresh question is the discuss primitive working, not a backlog."""
        report = self.review(self.target(), "--open-days", "14")
        titles = self.codes(report).get("open-question", [])
        self.assertTrue(any("Q-001" in title for title in titles))
        self.assertFalse(any("Q-002" in title for title in titles))
        self.assertFalse(any("Q-003" in title for title in titles))

    def test_proposed_records_are_listed_and_accepted_ones_are_not(self) -> None:
        report = self.review(self.target())
        titles = self.codes(report).get("proposed-record", [])
        self.assertTrue(any("D-002" in title for title in titles))
        self.assertFalse(any("D-001" in title for title in titles))

    def test_findings_are_sorted_oldest_first(self) -> None:
        """Latency is the failure mode, so age outranks kind."""
        report = self.review(self.target())
        ages = [item["age_days"] for item in report["findings"] if item["age_days"] is not None]
        self.assertEqual(sorted(ages, reverse=True), ages)

    def test_an_unpromoted_capsule_is_named_as_one(self) -> None:
        target = self.target()
        inbox = target / "project-context" / "inbox"
        inbox.mkdir()
        (inbox / "C-2026-01-01-topic.md").write_text(
            "---\nid: C-2026-01-01-topic\nkind: capsule\nstatus: proposed\n"
            f"title: A note from a session\ncreated: {days_ago(21)}\nasserted_by: agent:test\n---\n\nA note.\n",
            encoding="utf-8",
        )
        report = self.review(target)
        self.assertTrue(any("A note from a session" in title
                            for title in self.codes(report).get("unpromoted-capsule", [])))

    def test_an_assumption_nobody_confirmed_is_a_finding(self) -> None:
        target = self.target()
        questions = target / "project-context" / "questions"
        questions.mkdir()
        (questions / "Q-010-quota.md").write_text(
            "---\nid: Q-010\nkind: question\nstatus: answered\n"
            f"title: Quota shape\ncreated: {days_ago(30)}\nasserted_by: person:daren\n---\n\n"
            "- Assumption: service accounts share the tenant quota.\n",
            encoding="utf-8",
        )
        report = self.review(target)
        self.assertIn("unconfirmed-assumption", self.codes(report))

    def test_a_confirmed_assumption_is_not(self) -> None:
        target = self.target()
        questions = target / "project-context" / "questions"
        questions.mkdir()
        (questions / "Q-010-quota.md").write_text(
            "---\nid: Q-010\nkind: question\nstatus: answered\n"
            f"title: Quota shape\ncreated: {days_ago(30)}\nasserted_by: person:daren\n---\n\n"
            "- Assumption: service accounts share the tenant quota.\n"
            "- Confirmed: checked against the provider's quota page, 2026-08-20.\n",
            encoding="utf-8",
        )
        self.assertNotIn("unconfirmed-assumption", self.codes(self.review(target)))

    def test_a_stale_pushed_snapshot_is_reported_to_the_builder(self) -> None:
        target = self.target()
        context = target / "project-context"
        (context / "global").mkdir()
        (context / "global" / "SUMMARY.md").write_text("# Global summary\n\nWe ship.\n", encoding="utf-8")
        import hashlib
        digest = hashlib.sha256((context / "global" / "SUMMARY.md").read_bytes()).hexdigest()
        (context / ".project-context.json").write_text(
            json.dumps(
                {
                    "schema": "project-context/1", "product": "project-context", "version": "0.7.0",
                    "pushed": {
                        "global/SUMMARY.md": {
                            "sha256": digest, "source_commit": "a" * 40, "pushed_at": days_ago(200),
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        report = self.review(target, "--snapshot-days", "90")
        self.assertIn("stale-snapshot", self.codes(report))

    def test_a_quiet_project_says_so_and_exits_zero(self) -> None:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        (directory / "project-context").mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(directory)],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Nothing is waiting on a person", result.stdout)

    def test_a_backlog_is_not_a_build_failure(self) -> None:
        """CI that breaks on an open question teaches people to stop filing them."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(self.target())],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("waiting on a person", result.stdout)

    def test_the_scaffolds_own_examples_are_not_a_backlog(self) -> None:
        """A fresh install must not open with four items it did not create."""
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        init = ROOT / "skills" / "project-context-init" / "scripts" / "project_context_init.py"
        subprocess.run(
            [sys.executable, str(init), "init", "--target", str(directory),
             "--profile", "full", "--apply"],
            check=True, capture_output=True, text=True,
        )
        report = self.review(directory)
        self.assertEqual([], report["findings"], report["findings"])


class ConflictCandidateTests(unittest.TestCase):
    """Accepted decisions whose scope overlaps enough that someone should look.

    The check reports *candidates*, never conflicts. A script cannot know that
    two decisions contradict — that is a semantic judgement, and it stays with
    the person or agent reading them, exactly as the trigger window stays a
    judgement in `context_triggers.py`. These tests hold it to that promise
    from both sides: it must surface the overlaps a reader could not have
    remembered, and it must stay quiet everywhere else, because a check that
    cried conflict on every shared topic would be switched off within a week
    and every real conflict after that would go unreported.
    """

    def target(self, decisions: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        context = directory / "project-context"
        context.mkdir()
        (context / "NOW.md").write_text(
            f"# Current Project State\n\nLast reviewed: {days_ago(2)}\n", encoding="utf-8"
        )
        (context / "DECISIONS.md").write_text("# Decision Registry\n\n" + decisions, encoding="utf-8")
        (context / "LEARNINGS.md").write_text("# Learning Registry\n", encoding="utf-8")
        (context / "QUESTIONS.md").write_text("# Question Registry\n", encoding="utf-8")
        return directory

    def run_review(self, target: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target), *args],
            check=False, capture_output=True, text=True,
        )

    def review(self, target: Path, *args: str) -> dict:
        result = self.run_review(target, "--format", "json", *args)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def candidates(self, report: dict) -> list[dict]:
        return [item for item in report["findings"] if item["code"] == "conflict-candidate"]

    def test_two_accepted_decisions_on_the_same_path_are_reported_as_a_pair(self) -> None:
        """The strongest signal available: two standing rules over one file.

        Reported as a pair with both IDs, both titles, and the path they share,
        because "these two both constrain src/api/client.py" is something a
        reader can settle in a minute. "Possible conflict" is something a
        reader learns to skip.
        """
        target = self.target(
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n"
            "- Decision: The gateway retries an upstream call at most three times.\n\n"
            "## D-003: Retry until the caller's deadline expires\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(40) + "\n"
            "- Files: src/api/client.py, src/api/retry.py\n"
            "- Decision: The gateway keeps retrying with jittered backoff until the deadline.\n"
        )
        found = self.candidates(self.review(target))
        self.assertEqual(1, len(found), found)
        self.assertEqual(["D-001", "D-003"], found[0]["pair"])
        self.assertEqual("path", found[0]["signal"])
        self.assertIn("src/api/client.py", found[0]["shared_paths"])
        self.assertIn("Cap outbound retries at three attempts", found[0]["title"])
        self.assertIn("Retry until the caller's deadline expires", found[0]["title"])
        self.assertIn("src/api/client.py", found[0]["detail"])

    def test_a_properly_superseded_pair_is_not_reported(self) -> None:
        """A recorded supersession is a disagreement someone already settled.

        Reporting it would be pure noise, and noise is how this check gets
        turned off. The old entry carries `superseded`, so it never reaches the
        comparison at all — the status vocabulary is doing the work here, not a
        special case.
        """
        target = self.target(
            "## D-005: Session cookies expire after eight hours\n\n"
            "- Status: `superseded`\n- Date: " + days_ago(180) + "\n"
            "- Superseded by: D-006\n- Files: src/session/cookie.py\n"
            "- Decision: A session cookie expires eight hours after issue.\n\n"
            "## D-006: Session cookies expire after thirty days with rotation\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(80) + "\n"
            "- Supersedes: D-005\n- Files: src/session/cookie.py\n"
            "- Decision: A session cookie lasts thirty days and rotates on each use.\n"
        )
        self.assertEqual([], self.candidates(self.review(target)))

    def test_a_supersession_link_settles_a_pair_that_is_still_accepted(self) -> None:
        """Belt and braces for a half-finished supersession.

        Someone who wrote `Supersedes:` on the new entry but forgot to set the
        old one's status has still said which of the two wins. The doctor is
        the right place to complain about the status; repeating it here as a
        conflict would report the same slip twice under a name that suggests
        nobody has decided.
        """
        target = self.target(
            "## D-005: Session cookies expire after eight hours\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(180) + "\n"
            "- Files: src/session/cookie.py\n"
            "- Decision: A session cookie expires eight hours after issue.\n\n"
            "## D-006: Session cookies expire after thirty days with rotation\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(80) + "\n"
            "- Supersedes: D-005\n- Files: src/session/cookie.py\n"
            "- Decision: A session cookie lasts thirty days and rotates on each use.\n"
        )
        self.assertEqual([], self.candidates(self.review(target)))

    def test_two_unrelated_decisions_are_not_a_pair(self) -> None:
        """Every entry shares the registry's own furniture, and that is not a topic.

        `Status`, `Date`, `Decision`, `Rationale`, `Consequences`, `Evidence`:
        the template prints those words into every decision ever written. If
        they counted, every project would open its first review with a
        complete graph of false conflicts.
        """
        target = self.target(
            "## D-002: Store session state in Postgres, not Redis\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(150) + "\n"
            "- Files: src/session/store.py\n"
            "- Decision: Session state is written to Postgres with a TTL column.\n"
            "- Rationale: One datastore to operate.\n"
            "- Consequences: Session reads add a database round trip.\n"
            "- Evidence: Load test results.\n\n"
            "## D-004: Log timestamps in UTC with ISO-8601\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(120) + "\n"
            "- Files: src/logging/format.py\n"
            "- Decision: Every log line carries an ISO-8601 UTC timestamp.\n"
            "- Rationale: Mixed local timezones made incident timelines impossible to align.\n"
            "- Consequences: Local-time readers convert.\n"
            "- Evidence: Two incident write-ups.\n"
        )
        self.assertEqual([], self.candidates(self.review(target)))

    def test_substantial_topic_overlap_is_reported_with_the_terms_they_share(self) -> None:
        """The weaker signal, and it has to say what it saw to be worth reading.

        Two decisions that never named a file can still both be standing rules
        about rate limiting. The report names the shared terms so the reader
        can dismiss a coincidence without opening either record.
        """
        target = self.target(
            "## D-001: Rate limit per tenant, not per API key\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(150) + "\n"
            "- Decision: The rate limiter buckets requests by tenant identifier.\n"
            "- Rationale: A tenant rotating keys was buying itself extra quota.\n\n"
            "## D-002: Rate limit per API key so one key cannot starve a tenant\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(25) + "\n"
            "- Decision: The rate limiter buckets requests by API key under a tenant ceiling.\n"
            "- Rationale: One batch job key consumed the whole tenant quota.\n"
        )
        found = self.candidates(self.review(target))
        self.assertEqual(1, len(found), found)
        self.assertEqual("topic", found[0]["signal"])
        self.assertIn("tenant", found[0]["shared_terms"])
        self.assertIn("limit", found[0]["shared_terms"])

    def test_a_proposed_decision_is_not_yet_a_standing_rule(self) -> None:
        """Only accepted decisions constrain anything.

        A proposed one is already reported as `proposed-record` — it is waiting
        on a person for a different reason — and pairing it here would report
        the same entry twice under a name that overstates its authority.
        """
        target = self.target(
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n\n"
            "## D-003: Retry until the caller's deadline expires\n\n"
            "- Status: `proposed`\n- Date: " + days_ago(40) + "\n"
            "- Files: src/api/client.py\n"
        )
        self.assertEqual([], self.candidates(self.review(target)))

    def test_a_decision_is_not_in_conflict_with_its_own_detail_record(self) -> None:
        """One decision written in two places is still one decision.

        The registry entry and `decisions/D-001-*.md` share every path by
        construction, so a check that compared them would report every
        well-documented decision as conflicting with itself.
        """
        target = self.target(
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n"
        )
        decisions = target / "project-context" / "decisions"
        decisions.mkdir()
        (decisions / "D-001-retries.md").write_text(
            "---\nid: D-001\nkind: decision\nstatus: accepted\n"
            "title: Cap outbound retries at three attempts\ncreated: " + days_ago(200) + "\n"
            "asserted_by: person:daren\nfiles:\n  - src/api/client.py\n---\n\n"
            "# D-001: Cap outbound retries at three attempts\n",
            encoding="utf-8",
        )
        self.assertEqual([], self.candidates(self.review(target)))

    def test_finding_candidates_is_not_a_build_failure(self) -> None:
        """The same rule the rest of this report lives by, for a stronger reason.

        A candidate is an overlap the tool cannot verify. Failing CI on one
        would teach a team to stop running the check, and the conflicts it
        would have caught after that go unreported. Exit zero, always.
        """
        target = self.target(
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n\n"
            "## D-003: Retry until the caller's deadline expires\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(40) + "\n"
            "- Files: src/api/client.py\n"
        )
        result = self.run_review(target)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("conflict-candidate", result.stdout)
        self.assertIn("D-001", result.stdout)
        self.assertIn("D-003", result.stdout)

    def test_a_long_candidate_list_is_trimmed_and_says_it_was(self) -> None:
        """Pairs grow with the square of the registry, and the report has to stay readable.

        Thirty decisions over one subsystem would bury every other finding
        under hundreds of pairs. The strongest survive — but the count of what
        was left out is reported, because a list that silently truncates
        implies the overlaps it dropped do not exist.
        """
        entries = "".join(
            f"## D-00{index}: Standing rule number {index}\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(100 + index) + "\n"
            "- Files: src/api/client.py\n\n"
            for index in (1, 2, 3)
        )
        report = self.review(self.target(entries), "--max-conflicts", "1")
        self.assertEqual(1, len(self.candidates(report)))
        trimmed = [item for item in report["findings"] if item["code"] == "conflict-list-trimmed"]
        self.assertEqual(1, len(trimmed), report["findings"])
        self.assertIn("2 further", trimmed[0]["title"])

    def test_the_pair_ages_from_the_newer_of_the_two(self) -> None:
        """A pair cannot be older than the second decision in it.

        The report is sorted oldest first because latency is the failure mode,
        and the latency here started the day the second rule was written, not
        the day the first one was.
        """
        target = self.target(
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n\n"
            "## D-003: Retry until the caller's deadline expires\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(40) + "\n"
            "- Files: src/api/client.py\n"
        )
        self.assertEqual(40, self.candidates(self.review(target))[0]["age_days"])


class NewDecisionGateTests(unittest.TestCase):
    """The check an agent runs *before* appending a decision.

    Recording a decision that contradicts an accepted one, silently, is the
    failure this closes. The author of the thirtieth decision cannot remember
    the other twenty-nine, so the protocol asks the tool first and the tool
    answers with the entries that already stand on that ground.
    """

    def target(self) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, True)
        context = directory / "project-context"
        context.mkdir()
        (context / "NOW.md").write_text(
            f"# Current Project State\n\nLast reviewed: {days_ago(2)}\n", encoding="utf-8"
        )
        (context / "DECISIONS.md").write_text(
            "# Decision Registry\n\n"
            "## D-001: Cap outbound retries at three attempts\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(200) + "\n"
            "- Files: src/api/client.py\n"
            "- Decision: The gateway retries an upstream call at most three times.\n\n"
            "## D-002: Adopt Terraform for cloud provisioning\n\n"
            "- Status: `accepted`\n- Date: " + days_ago(120) + "\n"
            "- Files: infra/terraform/\n"
            "- Decision: All cloud resources are declared in Terraform modules.\n",
            encoding="utf-8",
        )
        (context / "QUESTIONS.md").write_text(
            "## Q-001: Old and unanswered\n\n- Status: `open`\n- Date: " + days_ago(90) + "\n",
            encoding="utf-8",
        )
        return directory

    def gate(self, target: Path, text: str, files: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(target),
             "--new-decision", text, "--new-decision-files", files],
            check=False, capture_output=True, text=True,
        )

    def test_a_new_decision_on_an_occupied_path_names_what_already_stands(self) -> None:
        result = self.gate(
            self.target(), "Retry an upstream call at most once, then fail fast", "src/api/client.py"
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("D-001", result.stdout)
        self.assertIn("Cap outbound retries at three attempts", result.stdout)
        self.assertNotIn("D-002", result.stdout)

    def test_the_gate_says_what_to_do_about_a_candidate(self) -> None:
        """A finding nobody knows how to resolve is a finding people route around.

        Both resolutions are named, and neither of them is "append it anyway
        and say nothing", which is the failure being closed.
        """
        result = self.gate(
            self.target(), "Retry an upstream call at most once, then fail fast", "src/api/client.py"
        )
        self.assertIn("supersedes:", result.stdout)
        self.assertIn("superseded_by:", result.stdout)
        self.assertIn("why both stand", result.stdout)

    def test_a_new_decision_on_fresh_ground_is_cleared_to_be_recorded(self) -> None:
        """The common answer, and it has to be short enough to trust.

        Most decisions collide with nothing. If the gate answered those with a
        page of backlog nobody would run it before the thirtieth decision,
        which is the only one where it matters.
        """
        result = self.gate(self.target(), "Ship a Debian package beside the image", "packaging/deb/")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Record it.", result.stdout)

    def test_the_gate_reports_nothing_but_conflict_candidates(self) -> None:
        """One question is being asked, so one kind of answer comes back.

        The project has a ninety-day-old open question. It is a real finding of
        the ordinary review and it is none of this author's business right now.
        """
        result = self.gate(self.target(), "Ship a Debian package beside the image", "packaging/deb/")
        self.assertNotIn("Q-001", result.stdout)

    def test_a_new_decision_that_already_supersedes_the_old_one_is_not_a_candidate(self) -> None:
        """Naming the entry you replace is the resolution the gate asks for.

        Re-reporting it would mean the only way to satisfy the check is to not
        write decisions, which teaches exactly the wrong lesson.
        """
        result = self.gate(
            self.target(),
            "Supersedes D-001: retry twice with jitter, then fail fast",
            "src/api/client.py",
        )
        self.assertIn("Record it.", result.stdout)


if __name__ == "__main__":
    unittest.main()
