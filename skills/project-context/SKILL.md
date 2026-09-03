---
name: project-context
description: "Use when a repository or project folder contains project-context/, especially before meaningful work, when resuming or handing off, or when current state, decisions, learnings, and linked evidence need to be read or maintained."
---

# Project Context

Use this protocol when this repository or project folder contains
`project-context/` and collaborative work needs memory that survives any one
person, agent, or chat session. It applies to software, document, research,
writing, mixed, and folder-based projects.

This is the only copy of the protocol. It is installed twice — as the harness
skill at `.agents/skills/project-context/SKILL.md`, and as this repository's own
instance at `project-context/SKILL.md` — so the two can never say different
things. Read whichever one you found; they are the same text.

## Start

1. Read `project-context/NOW.md`.
2. Search `project-context/DECISIONS.md` and `project-context/LEARNINGS.md` for
   the current topic.
3. Follow only relevant links into detailed decisions, designs, incidents,
   tasks, primary artifacts, and evidence.
4. Treat entries marked `superseded` as historical evidence only.

Do not load every historical task or generated page. Current primary artifacts
and evidence—such as source and tests, approved documents, citations and data,
or the manuscript and editorial record—take precedence over summaries alongside
explicit user direction and repository instructions.

## Triggers

Update a document when its trigger fires — not when someone asks for an update.
Evaluate every trigger below wherever work lands: before a commit, before a
handoff, and before ending a session.

- **`NOW.md` — the state a next contributor would act on changed.** Work landed
  that changes what happens next; an initiative started, finished, or changed
  status; a blocker appeared or cleared; a recorded next action was done; the
  session is ending with work in flight. Replace stale state rather than
  appending to it, and set `Last reviewed` to today.
- **`DECISIONS.md` — a choice now constrains future work.** One option was taken
  over a viable alternative; a convention, boundary, interface, format,
  dependency, or tool was fixed; the user stated a standing rule; something was
  ruled out of scope; an earlier decision was reversed or narrowed — supersede
  it, never rewrite its meaning. Do not record an implementation detail a future
  contributor may freely change.
- **`LEARNINGS.md` — evidence changed what is believed, and it will recur.** A
  root cause the code did not make obvious; an approach that failed in a way
  that would repeat; an assumption disproved by an observed result; a tool or
  platform behaving unlike its documentation; a rule that would have prevented a
  review finding. Evidence is required, and it must apply beyond this one task.

### When nothing fired

Say so and move on. Silence is a valid outcome. Padding the registries with
choices that constrain nothing, or lessons nobody verified, makes them
unreadable — the exact failure these files exist to prevent.

Record that outcome instead of editing a file to quiet the check:

    python3 .agents/skills/project-context/scripts/context_triggers.py \
        ack --note "<what you evaluated>"

`ack` stores what was acknowledged against the current commit. The window
reopens on the next commit, and as soon as uncommitted work the acknowledgement
never saw appears — so it can record an honest evaluation, but it cannot
become a standing way to skip one.

## Maintain

- Use `tasks/` for plans, progress, validation, and outcomes when the full
  profile is present; otherwise link the repository's existing task system.
- Keep `NOW.md` concise and actionable; remove stale state after linking its
  durable result.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings only when evidence supports reuse beyond one task.
- Pin evidence that can move: cite a repository path as `path/to/file@<commit>`,
  either plainly on an `- Evidence:` line or as a link target. The doctor then
  reports `evidence-drift` when that path changed after the commit it was cited
  at — the entry's justification may no longer hold. Re-read the evidence, then
  either re-anchor the entry to the current commit or supersede it.
- After adding an entry or changing a status, regenerate the registry indexes
  with `context_index.py` (see Automation). They are derived tables that let an
  agent find the entries that constrain a task without reading either registry
  end to end; a stale index is worse than none, because it is trusted.
- In the full profile, create detailed designs or incident records when their
  evidence will help future work.
- Preserve completed historical records. Correct interpretation through status
  and supersession links instead of rewriting history.

## Safety

Never store secrets, sensitive personal or customer data, raw chat transcripts,
private host paths, ambient user profiles, copyrighted source material copied
without need, or unverified claims. Generated wikis and indexes are auxiliary
discovery systems; they do not replace tracked Markdown authority.

## Automation

Three scripts support this protocol. Where the skill is installed here they live
under `.agents/skills/project-context/scripts/`; if the skills are not installed
in this repository, run the same commands from the Project Context checkout,
passing this project folder wherever a target is required.

`context_triggers.py` detects the trigger *window* — work has landed since
project context was last updated — and reports it at session start and again
before a session ends. It cannot judge whether a decision or a learning fired;
that judgment stays with the agent reading this file.

    python3 .agents/skills/project-context/scripts/context_triggers.py status

Run `status` to see the window without waiting for a hook, and `ack` to record
an honest "nothing fired". If it reports that it resolved the repository from
its own install root, or that it could not find one at all, treat that as a
wiring problem rather than a quiet session: nothing was evaluated. Its state is
per-clone bookkeeping and is kept out of the work tree.

`context_index.py` regenerates the registry indexes. They are derived tables —
a hand-edited one is overwritten, and `--check` exits non-zero when they are
stale, so CI can hold the line.

    python3 .agents/skills/project-context/scripts/context_index.py --check

## Health

When context appears stale, contradictory, or hard to navigate, run the
read-only doctor. It checks core files, the package version recorded in the
marker, review freshness, duplicate decision and learning IDs, broken relative
links, and pinned evidence that has drifted, without rewriting content.

    python3 .agents/skills/project-context/scripts/context_doctor.py --target .

It also validates records against the record model: a detail record in
`decisions/`, `questions/`, `tasks/`, or `inbox/` carries six frontmatter keys —
`id`, `kind`, `status`, `title`, `created`, `asserted_by` — and nothing else is
required. Each kind has exactly one status vocabulary, and a status is checked
against its own kind's set: a `decision`, `learning`, or `capsule` is `proposed`
→ `accepted` → `superseded` | `rejected`; a `question` is `open` → `answered` →
`superseded`; a `task` is `proposed` → `active` → `done` | `dropped`. A state
that belongs to another kind is an error, and `candidate` and `approved` are
retired everywhere. A reference is validated by shape, never by resolving it.

Where a Project Hub owner has pushed `global/` or `blueprint/` into this
repository, those files are read-only here. The doctor recomputes each one's
digest against the stamp in `.project-context.json` and reports an edit as an
error naming the Hub. To change a pushed record, raise a question rather than
editing the copy; the next push would overwrite the edit anyway.

It also checks reachability: whether the managed instruction block, the harness
skill pointer, or a declared session hook will still deliver this protocol to an
agent. Both `AGENTS.md` and `CLAUDE.md` carry the same managed block, and the
doctor names whichever is missing it. A `no-delivery-path` error means the
context files are intact but nothing loads them into a session — fix that before
trusting the rest.

The `project-context-init` skill, which stays in the Project Context checkout
rather than being installed here, exposes the same check as
`project_context_init.py doctor --target .` and additionally handles installs,
upgrades, and consolidation review.
