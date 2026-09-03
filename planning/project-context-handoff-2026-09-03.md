# Project Context — design handoff, 2026-09-03

Status: planning handoff, revised 2026-09-03 (second session of the day) after
Daren gave the two-product direction and then answered D10 and D11. Baseline: `strategy` at `083572d`
(0.6.0). Changed since the first revision: local `main` fast-forwarded to
`origin/main` (`ec5db82`), the `docs/context-hub-handoff.md` header refreshed,
and `planning/project-context-design.md` rewritten from Part 2 onward. No
commit, push, remote, or invitation was made; the working tree carries those
three edits uncommitted.
Author: Claude (Claude Code session, 2026-09-03), continuing the plan started
2026-09-02. This file exists so any model can pick the work up without the
conversation.

Read in this order:

1. This file.
2. `planning/project-context-design.md`, the plan. Parts 2 to 4 were rewritten
   for the two-product direction; Part 1 is the original review and still
   holds. It is mirrored to the Notion page "Project Context" (MonoMind
   Homebase / Projects & Tasks / Projects); find it with a Notion search on the
   title. Both copies were at the same revision when this was written.
3. `docs/context-hub-handoff.md`, the previous Codex handoff for the Context
   Hub. Its header was refreshed 2026-09-03 and now points here; read it for the
   Context Hub's rationale and its designed-but-unbuilt list.
4. The code only when a slice needs it: `src/project_context_cli/__init__.py`
   (the `project-context` entry point), `skills/`, `scripts/`, `tests/`.

## 1. Where the repository stands

Verified 2026-09-03 after `git fetch --all --prune`.

| Ref | Commit | Note |
| --- | --- | --- |
| `strategy` (local = origin) | `083572d` | 0.6.0, the Context Hub, on top of 0.5.0 and the site work |
| `origin/main` | `ec5db82` | one commit behind `strategy`; only the Context Hub is missing |
| local `main` | `ec5db82` | fast-forwarded to `origin/main` on 2026-09-03; was 20 behind at `cf19519` |
| `feat/project-context-update-skill` | `6066787` | 2 commits off `cf19519`; the `project-context-update` skill; merged nowhere. Conflicts with `strategy` in 4 files: `README.md`, `skills/project-context-init/SKILL.md`, `skills/project-context-init/scripts/project_context_init.py`, `skills/project-context/SKILL.md` |
| `origin/docs/readme-onboarding-rewrite` | `7dee0ca` | leftover; README byte-identical to pull request 4 on `strategy`; safe to delete, deletion not yet authorized |

Validation on Python 3.13.9, re-run 2026-09-03:

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests` | 72 passed |
| `python3 scripts/validate_repository.py` | 85 required files present |
| `python3 scripts/build_site.py --check` | 6 pages build |

Still not done from the Context Hub handoff: no wheel build, no real Graphify
extraction, no real team onboarding, no Windows write backend.

What exists in 0.6.0, in one paragraph: an embedded mode (`project-context/`
folder, skill `project-context`, `TEMPLATE_VERSION 0.5.0`, evidence anchors,
trigger gate with `ack`, registry indexes, single-command install) and a
separate Context Hub (skill `context-hub`, `SCAFFOLD_VERSION 0.1.0`, actors,
episodes, entities, relationships, two doctors). The plan's Part 1 reviews
both; finding F1 is that they are two incompatible *record models* and must
become one. F1 is not an argument against two products: the new direction keeps
one schema, one doctor, one CLI, and one version number, and ships them as two
installables with two audiences. Today's Context Hub is the ancestor of Project
Hub, but Project Hub is a much smaller thing.

## 2. The design in one paragraph

**Superseded 2026-09-03 by Daren's deterministic direction.** One record model,
two products, and every movement between them a pull. **Project Context** is
installed in each project repository and serves its builders; its records live
in that repository and it never writes outside it. `/projectcontext-init`
installs it and writes the managed block into both `CLAUDE.md` and `AGENTS.md`;
`/projectcontext-update` reconciles what the owner pushed and touches no
network. **Project Hub** is one private repository owned by the organisation
leader, closed to builders entirely; it authors the global tier and holds a
folder per project carrying a `MARK.md` (repo info and URLs), a summary,
`blueprint/` holding `EPIC.md` and `ARCHITECTURE.md`, plus a pulled copy of the
repo's authored records.
`/hub-push <repo>` sends `global/` and `blueprint/` (which holds `EPIC.md` and
`ARCHITECTURE.md`) into a repo;
`/hub-pull <repo>` brings that repo's records up into the Hub; `/hub-init
<repo>` writes the mark and an initial summary, installs Project Context, and
pushes — all of which the owner can do because they administer the repo.
Sessions stay local and are distilled into capsules; no shared repository holds
transcripts. Full text: plan Part 2. Naming and upgrade path: Part 3. Slices and
decisions: Part 4.

What this withdrew: the per-user vault, the repo-to-vault mirror, branch
mirrors, the `OWNERS.md` approval gate with its `Context-Approved-By:` trailer
and signature verification, `sync --propose`, and the
`local`/`personal`/`team` placement continuum. D10(b) additionally withdrew the
global distribution repository, and with it the last network call in the
builder's product.

**The authored set and the pushed set.** This is the organising idea of the
whole design. Builders author `SUMMARY`, `NOW`, `PLAN`, `tasks/`, `DECISIONS`,
`LEARNINGS`, `QUESTIONS`, `inbox/`; the owner authors `global/` and
`blueprint/` in the Hub and pushes them down. The pushed set is exactly those
two paths. The pushed set is read-only in the
repo and the doctor enforces it by stamp. `PLAN.md` must conform to
`blueprint/EPIC.md`
through a checked `Serves:` anchor. A builder who disagrees with anything pushed
files a question or a `proposal` capsule, which reaches the owner at the next
`/hub-pull`.

## 3. Daren's direction, 2026-09-03 (deterministic)

Given verbatim in substance:

1. **Project Context** is for collaborators — *builders* — of each project,
   working in each repo, so its project context lives in each project repo. It
   pulls the global guide and resources from Project Hub via
   `/projectcontext-update`, which is a pull-only action, and which also works
   with hooks such as a new repo or a new install (`/projectcontext-init`).
2. **Project Hub** is where the global context and all project context live,
   for organisation leaders. It is a private repo managed by the organisation
   owner, with no permission for builders; builders can only pull global
   context and knowledge via `/projectcontext-update`. It is an authoring space
   for global context and project plans. Every project in the repo has a
   dedicated folder with a mark carrying the repo's basic info and URLs. The
   Hub owner, who has access to all or most repos in the organisation, can pull
   a project's context into the Hub with `/hub-pull [repo]`, or with
   `/hub-init [repo]` if the repo has no project context installed yet.
   `/hub-init [repo]` creates an initial summary of the repo inside the Hub and
   also installs Project Context into the repo, which is possible because the
   Hub owner has access to the project repo.

**Second round, the same day**, answering D10 and D11 and adding one
instruction:

3. **D10 = (b), plus `/hub-push [repo]`.** No global distribution repository.
   The owner pushes global content into each repo.
4. **D11 = two altitudes.** High-level plans are authored by the owner, in the
   Hub, as `epic.md`; project-level plans stay `plan.md` in the repo and must
   conform to the epic. `architecture.md` is likewise authored in the Hub and
   goes into a `blueprint` folder in each project, pushed by the owner.
   (Filenames are written uppercase in the plan to match the existing record
   convention, and both owner-authored project records live in `blueprint/`
   together: `blueprint/EPIC.md`, `PLAN.md`, `blueprint/ARCHITECTURE.md`.)
5. **Install must append the needed rules into `claude.md` and `agents.md`.**

The whole of plan Part 2 is the working-out of those paragraphs. The
asymmetry is the design: the builder's tooling has no Hub credential and no
command that writes to the Hub; the owner's tooling has repo credentials
because the owner administers the repos. Neither product needs a permission
model of its own — the Git host's repository permissions are the governance,
which is what makes it work on GitHub Free.

## 4. Decisions

**Resolved.**

- **D1** Raw sessions are never committed to a shared repo by default. Capsules
  only. Unaffected by the split.
- **D2** Superseded. Project knowledge is authored in the project repository
  and copied into the Hub by the owner's `/hub-pull`. No vault, no mirror, no
  placement continuum.
- **D3** Resolved structurally. The Hub is private and closed to builders, so
  repository permissions are the whole mechanism and they work on GitHub Free.
  The tool-enforced `OWNERS.md` gate, the `Context-Approved-By:` trailer, and
  signature verification are deleted. `OWNERS.md` survives as a record; the
  agent self-approval error survives as a record check.
- **D5** Tracked, and D10(b) settles it beyond argument: the push *is* a commit,
  so an excluded pushed set could not travel at all.
- **D6** Deleted, not deferred. There is no repo-to-Hub push to propose
  against. A builder's feedback is a question or a `proposal` capsule in their
  own repo, which reaches the owner at the next `/hub-pull`.
- **D8** Moot. There is no vault; the Hub is created deliberately by an owner.
- **D10** Daren, 2026-09-03: **option (b)**, with a new `/hub-push [repo]`.
  No global distribution repository. The owner pushes `global/` and
  `blueprint/` into each repo; builders hold no permission on the Hub, not even
  read; `/projectcontext-update` becomes a purely local reconcile and the
  builder's product stops touching the network entirely. Accepted cost: a global
  change is N branches and N merges, mitigated by `--all` and by the doctor
  reporting stamp age.
- **D11** Daren, 2026-09-03: **two records at two altitudes with a conformance
  relation.** `EPIC.md` is the high-level plan, owner-authored; `PLAN.md` is the
  project-level plan, builder-authored, and must conform to the epic.
  `ARCHITECTURE.md` also moves to owner authorship. Both owner-authored project
  records live together in `blueprint/`, pushed whole, so the pushed set is
  exactly `global/` plus `blueprint/`. Conformance is checked, not exhorted: a
  `Serves:` line per plan item, a doctor error for plan work no epic item asks
  for, a warning for epic items nothing serves.

**Also instructed 2026-09-03.** Install must write the managed block into
**both** `CLAUDE.md` and `AGENTS.md`, creating whichever is missing. Today's
installer updates every instruction file it finds but creates only `AGENTS.md`
when none exists, so a Claude-only repo ends up with rules no Claude session
reads. The doctor's `no-delivery-path` check is tightened to name the missing
file, and `/projectcontext-update` refreshes the blocks so rule changes reach
installed repos.

**On SQLite** (Daren confirmed SQLite, and noted Obsidian already brings it into
the vault picture): keep it, Hub side only, as a derived regenerable cache,
`.gitignore`d, triggered by a measurement rather than a milestone. Never in a
project repo — a binary in `project-context/` would be the first thing there a
human cannot read, diff, or review in a pull request. The dependency argument
was never the issue: `sqlite3` is in the Python standard library. One factual
caveat on the Obsidian point: what is verifiable is that SQLite in Obsidian is a
*community-plugin* story — plugins ship a WASM engine and read `.db` files
placed in a vault — not that core Obsidian bundles a SQLite store; that part
could not be confirmed and deserves a link if a decision ever rests on it. The
useful consequence holds either way: a `.db` in a Hub that is also a vault is an
ordinary, browsable citizen, which makes the Hub the right side for a cache and
argues for deferring it until an automated query, not a human one, proves slow.
Full reasoning in plan Part 4.

**Open, with the plan's recommendation.**

| ID | Question | Plan says |
| --- | --- | --- |
| D4 | Entities and relationships in v1 or an extension | Extension |
| D7 | Which branch does `/hub-pull` read | Default branch only |
| D9 | Does `IDENTITY.md` ever reach a project repo | No for identity; yes for guardrails, the epic, and the blueprint |

None of the three gates any v1 slice.

## 4b. Repo split and onboarding, 2026-09-03 (third round)

**Two repositories.** `project-context` stays as it is, with the README gaining
a section on extensibility with the Hub and the optional tools (GitNexus,
Graphify, OpenWiki) kept. `project-hub` is a **new public MIT repository**.

*Scaffold versus instance.* The public repo is the **scaffold** — installer,
templates, skills, vault seed — exactly as `project-context` is today. A **Hub
instance** created from it is private and closed to builders, which is what
plan Part 2 describes. Say so in both READMEs or the first question anyone asks
is why the private thing is public.

**`skills/context-hub/` is superseded** (Daren): it implemented the dropped
design. Remove the skill, `tests/test_context_hub.py`, the `pyproject.toml`
entry, the `scripts/validate_repository.py` entries, `prompts/create-context-hub.md`,
and the README section, in slice 2. Keep `docs/context-hub-handoff.md` and
`docs/context-hub-architecture.md` as historical record. Keep the doctor's
recognition of the old marker for two releases.

**No vendored plugins; an onboarding agent instead** (Daren). Plan 2.9 has the
design. The bootstrap works because the owner opens the Hub folder in Claude
Code or Codex, so no in-vault runtime plugin has to be shipped to get started.
Reference studied: `mypka-scaffold-latest` in Daren's Obsidian folder — its
`ADAPTER-PROMPT.md` is the model. What was taken: host detection with graceful
degradation, placeholder personalisation asked once, a thin generated host
pointer, two-layers-never-three, check-skip-report idempotency, and an
LLM-readable migration changelog. What was not: it vendors one terminal plugin
as its bootstrap, which we do not need.

**Open, and both shape the repos:**

- **License.** `project-context` is MIT + Commons Clause v1.0 (© 2026 MonoMind
  AI Lab); Daren asked for plain MIT on the Hub. That makes the more
  strategically valuable half the more permissive one. Deliberate or not?
- **Where the shared code lives.** The design promises one record model, one
  doctor, one schema, one version — now across two repos, with zero runtime
  dependencies ruling out a shared published package. Options: one repo that
  publishes the Hub scaffold from it; or `project-hub` vendors a synced copy of
  the protocol code, making the Hub just another consumer of the one-way flow
  the product already enforces. The second is the recommendation.

## 5. Next steps, in order

1. **Mirror this revision to the Notion page.** Search-and-replace or a
   content replace that keeps the inline Tasks database referenced; never drop
   it. Keep both copies at the same revision.
2. **Finish slice 1.** The `feat/project-context-update-skill` branch conflicts
   with `strategy` in four files (`README.md`,
   `skills/project-context-init/SKILL.md`, its init script,
   `skills/project-context/SKILL.md`) and its merge base is 20 commits back;
   slice 2 rewrites the same files, so the recommendation is to defer it and
   re-apply the capability on the unified model. Deleting
   `origin/docs/readme-onboarding-rewrite` and moving `main` to the Context Hub
   both need Daren's yes.
3. **Slice 2, one record model.** The unification commit; the gate for
   everything else. Nothing is blocked on an open decision.
4. **Slices 3 to 7** in the plan's order: Project Context standalone (including
   the `CLAUDE.md` / `AGENTS.md` blocks), Project Hub standalone, `/hub-push`
   and the pushed set, `/hub-init`, then retrieval and conformance.

## 6. Working rules for the next model

- Consumer repositories never write back to this scaffold and never bump a
  local template version; the flow is one way. The two-product split makes this
  stronger: the only write into a repository from outside is `/hub-init`, on a
  branch, with the diff shown and confirmation required.
- `docs/` is the GitHub Pages deploy root; planning documents live in
  `planning/`.
- Never create a remote, push, or invite. Commit only when asked, only the
  task's files, on a branch other than `main`.
- Zero runtime dependencies; deterministic dry-run and apply; idempotent
  re-runs; create-only writes; records are never rewritten by tooling.
- Run the three validation commands before handing off:
  `python3 -m unittest discover -s tests` (72 pass),
  `python3 scripts/validate_repository.py` (85 files),
  `python3 scripts/build_site.py --check` (6 pages). All three green
  2026-09-03.
- Skill names, Daren 2026-09-03: `/projectcontext-init`,
  `/projectcontext-update`, `/hub-init`, `/hub-pull`, `/hub-push`. They replace
  the `/context-init`, `/context-vault-init`, `/context-sync`,
  `/context-upgrade` set. The protocol skill keeps the name `project-context`.
- The pushed set (`global/` and `blueprint/`, the latter holding `EPIC.md` and
  `ARCHITECTURE.md`) is read-only in a project
  repo. Never author it there, and never add a path that lets a repo write to
  the Hub. `/hub-push` is the only write into a repository the Hub does not live
  in: branch only, diff shown, confirmation required, never a force-push.
- Claude Code sessions in this repository also carry auto-memory notes on these
  decisions; other models should rely on this file and the plan.
