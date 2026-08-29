---
name: project-context
description: "Use before meaningful work, when resuming or handing off, or when this project folder's current state, decisions, learnings, and linked evidence need to be read or maintained."
---

# Project Context

Use this local protocol whenever repository-bound work needs prior decisions,
current handoff state, verified learnings, or a durable milestone update across
software, document, research, writing, and mixed project folders.

## Start

1. Read `project-context/NOW.md`.
2. Search `project-context/DECISIONS.md` and `project-context/LEARNINGS.md` for
   the task's topics.
3. Follow only relevant links into detailed records, primary project artifacts,
   and evidence.
4. Treat entries marked `superseded` as history only.

Do not load every historical task or generated wiki page. Current primary
artifacts and verified evidence take precedence over summaries alongside
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
- Keep `NOW.md` short and actionable.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings with stable IDs, evidence, scope, and a concrete future action.
- After adding an entry or changing a status, regenerate the registry indexes
  (see Automation). They are derived tables that let an agent find the entries
  constraining a task without reading either registry end to end; a stale index
  is worse than none, because it is trusted.
- In the full profile, use `designs/` and `incidents/` for evidence that will
  help future work.
- Preserve completed evidence and correct its interpretation through status and
  supersession links rather than rewriting history.

Never store secrets, sensitive customer data, raw transcripts, private host
paths, ambient profiles, or unverified claims.

## Automation

The installed `project-context` skill ships
`scripts/context_triggers.py`, which detects the trigger *window* — work has
landed since project context was last updated — and reports it at session start
and again before a session ends. It cannot judge whether a decision or a
learning fired; that judgment stays with the agent reading this file.

    python3 .agents/skills/project-context/scripts/context_triggers.py status

Run `status` to see the window without waiting for a hook, and `ack` to record
an honest "nothing fired". If it reports that it resolved the repository from
its own install root, or that it could not find one at all, treat that as a
wiring problem rather than a quiet session: nothing was evaluated.

Its sibling `scripts/context_index.py` regenerates the registry indexes. They
are derived tables — a hand-edited one is overwritten, and `--check` exits
non-zero when they are stale, so CI can hold the line.

    python3 .agents/skills/project-context/scripts/context_index.py --check

## Health

When context looks stale, contradictory, or hard to navigate, run the
`project-context-init` skill's read-only doctor. It checks core files, scaffold
version, review freshness, duplicate decision and learning IDs, broken relative
links, and whether anything still delivers this protocol to an agent. It never
rewrites content.

If the skills were installed into this repository:

    python3 .agents/skills/project-context-init/scripts/project_context_init.py doctor --target .

Otherwise run the same `doctor` command from wherever the `project-context-init`
skill is available, passing `--target` this project folder.

A `no-delivery-path` error means nothing will load this protocol into a session:
the managed instruction block is gone and no harness pointer survives. Fix that
before trusting anything else the doctor reports.
