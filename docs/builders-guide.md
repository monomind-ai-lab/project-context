# Project Context — Builder's Guide

For **builders**: anyone working in a project repository that has Project
Context installed. If you administer a Project Hub instead, you want the
[owner's guide](https://github.com/monomind-ai-lab/project-hub) in that
repository.

Written against **0.7.0**. Everything here is built and tested unless it appears
under [Not built yet](#not-built-yet), which is honest about the gaps rather
than quiet about them.

---

## What this is

Project Context is a folder of plain Markdown inside your repository. It holds
what a newcomer — human or agent — needs to know before changing anything: the
current state, the decisions that constrain the work, and the lessons already
paid for.

It is not documentation. Documentation explains what the code does; the code
already does that. Project Context records what the code *cannot* say: why this
approach and not the obvious one, what was tried and failed, what is in flight
right now.

Three properties matter, and they are the reason to trust it:

- **Plain files in your repo.** No database, no server, no account. `git log` is
  the history. `grep` is the search.
- **Zero runtime dependencies.** Python standard library only. Nothing to
  install.
- **Nothing is ever rewritten.** Every write is create-only. The tool refuses
  before it overwrites a record you wrote.

---

## Installing it

From a Project Context checkout, pointed at your repository:

```bash
python3 skills/project-context-init/scripts/project_context_init.py init --target /path/to/your/repo --dry-run
```

Read what it plans. Then swap `--dry-run` for `--apply`.

| Flag | Does |
| --- | --- |
| `--profile core` (default) | `NOW.md`, `DECISIONS.md`, `LEARNINGS.md`, `decisions/`. Enough for most repositories. |
| `--profile full` | Adds `tasks/`, `designs/`, `incidents/`. Take this when the project already has that much going on. |
| `--repo-type` | `auto` by default. Also `code`, `document`, `research`, `writing`, `mixed`, `general`. |
| `--install-skills` | Installs the protocol skill so agents in this repo can find it. |
| `--install-hooks` | Wires the session hooks into `.claude/settings.json`. Opt-in, never assumed. |

### What lands in your repository

```text
project-context/
  NOW.md                  current state, active work, blockers, next action
  DECISIONS.md            the decision registry
  LEARNINGS.md            verified reusable lessons
  decisions/              detail records, one per decision that needs room
  tasks/ designs/ incidents/     full profile only
  indexes/                derived tables, regenerated
  README.md               what this folder is, for a human who found it
  .project-context.json   the marker: product, schema, version, stamps
```

And a managed block in **both** `CLAUDE.md` and `AGENTS.md` at the repository
root, creating whichever is missing. The block is delimited by
`<!-- project-context:start -->` and `<!-- project-context:end -->`. **Nothing
outside those markers is ever read or written** — whatever house rules you keep
in those files are untouched, and re-running install is idempotent.

If you had neither file, you get both. That matters: an earlier version created
only `AGENTS.md`, so a Claude-only repository ended up with rules no Claude
session ever read.

---

## Using it day to day

### The authority ladder

When two sources disagree, this is the order:

1. **Primary artifacts** — the code, the commit, the pull request, the test result.
2. **Curated records** — `NOW.md`, `DECISIONS.md`, `LEARNINGS.md`.
3. **Candidate knowledge** — anything proposed but not accepted.
4. **Derived views** — generated indexes, wikis, summaries.

A generated index is never authority. If an index and a record disagree,
regenerate the index.

### What to write, and where

| When | Write |
| --- | --- |
| A choice now constrains future work | A decision in `DECISIONS.md`; a detail record in `decisions/` if it needs room for alternatives and consequences |
| You learned something that generalises past this task | A learning in `LEARNINGS.md` |
| The state of play changed | `NOW.md` — keep it under 400 words; it is read every session |
| You are unsure and the answer changes the work | A question. Ask it before implementing, not after |

The test for a decision is not "was this hard" but **"would someone six months
from now redo this badly without knowing?"** If no, leave it out. Less is
better: the folder is read on every session and you pay for it every time.

### Records and their shape

Detail records in `decisions/`, `questions/`, `tasks/` and `inbox/` carry YAML
frontmatter with six required keys and no more:

```yaml
---
id: D-004
kind: decision
status: accepted
title: Serve thumbnails from the CDN, not the app
created: 2026-09-03
asserted_by: person:ren
---
```

Registries — `NOW.md`, `DECISIONS.md`, `LEARNINGS.md` — carry no frontmatter.
They stay plain Markdown.

**Status vocabulary depends on the kind**, because a question is not an
assertion and a task is not a claim:

| Kind | States |
| --- | --- |
| `decision`, `learning`, `capsule` | `proposed` → `accepted` → `superseded` \| `rejected` |
| `question` | `open` → `answered` → `superseded` |
| `task` | `proposed` → `active` → `done` \| `dropped` |

The doctor checks a status against its own kind and names the right vocabulary
when you get it wrong. `accepted` on a question is an error.

**Correction, not edit.** When something turns out wrong, supersede it or add a
correcting record. Never rewrite the meaning of a record someone may have acted
on. The history of a decision is worth more than its tidiness.

### Referring to evidence

One grammar, validated by shape wherever a reference appears:

```text
session:<harness>:<id>          commit:<binding>:<sha>
pr:<binding>#<number>           review:<binding>#<pr>/<comment-id>
ticket:<tracker>:<key>          doc:<binding>:<path>@<commit>
url:https://...                 capsule:<id>
hub:<hub-id>@<commit>
```

Pin a repository path to the state it cites: `src/auth/session.py@a1b2c3d`. A
reference to a moving file is a reference to nothing.

---

## The pushed set — files you must not edit

If your organisation runs a [Project Hub](https://github.com/monomind-ai-lab/project-hub),
two folders arrive in your repository from it:

- `project-context/global/` — organisation guardrails, workflows, skills, shared
  records
- `project-context/blueprint/` — `EPIC.md`, the high-level plan this project
  serves, and `ARCHITECTURE.md`, the shape it has to keep

**These are read-only here.** They are stamped in the marker with a hash, and
the doctor errors if one is edited, naming the Hub as the place to change it:

```text
[error] pushed-file-modified: edited since it was pushed; change it in the
Hub and push again, or raise a question here
```

That is not bureaucracy. Your edit would be silently overwritten by the next
sync, and the owner would never learn you disagreed. **Raise a question in your
own `project-context/` instead** — it reaches the owner the next time they pull,
and it arrives with the project context that explains it.

An owner's push does not land on your default branch. It arrives on a
`hub-sync` branch as a pull request you review like any other.

A repository with no Hub simply has neither folder, and nothing about that is
degraded.

---

## Checking your work

### The doctor

```bash
python3 skills/project-context/scripts/context_doctor.py --target /path/to/your/repo
```

Read-only. Exits 1 if anything is an error, 0 otherwise — so CI and a git hook
can both use the exit status without parsing the JSON.

What it catches, among others:

- **`no-delivery-path`** — context is intact but nothing loads it. This is the
  check worth knowing about: a perfect `project-context/` that no session ever
  reads is worth nothing. It names which of `CLAUDE.md` / `AGENTS.md` is missing
  the block.
- `pushed-file-modified` — you edited a file the Hub owns.
- `missing-required-key`, `invalid-status`, `invalid-reference` — record shape.
- `legacy-context-hub-marker` — a half-upgraded install from the retired
  Context Hub.
- Staleness — `NOW.md` untouched while work landed.

### The trigger gate

```bash
python3 skills/project-context/scripts/context_triggers.py status
```

It detects that work has landed since project context was last touched, and nags
once per session. It does **not** decide what to write — only you know whether a
choice constrained future work. When you have genuinely evaluated and there is
nothing to record:

```bash
python3 skills/project-context/scripts/context_triggers.py ack --note "reviewed; nothing constraining"
```

The acknowledgement is bound to the commit it evaluated, so it cannot be used to
wave away later work.

### The indexes

```bash
python3 skills/project-context/scripts/context_index.py --check
```

`DECISIONS.md` and `LEARNINGS.md` grow without bound and get read end to end.
The index tables at the top let a reader answer "does anything here constrain
what I am about to do?" without paying for the whole file. `--check` verifies
they are current; run it in CI.

---

## Not built yet

Named here so you do not go looking for them:

- **`capture`** — one-command capsules into `inbox/`. Write records by hand for
  now.
- **`context --task`** — the retrieval packet that assembles what matters for a
  task. Read `NOW.md` and grep the registries.
- **`/projectcontext-update`** — reconciling the pushed set and carrying the
  scaffold forward.
- **The `Serves:` conformance check** — `PLAN.md` items anchoring to epic items.
  A convention today, not enforced.

---

## Rules that will not change

- Records are never rewritten by tooling. Create-only, always.
- Nothing in this product reaches the network.
- The tool never creates a remote, never pushes, never invites anyone.
- Zero runtime dependencies.

---

*Mirrored to the Builder's Guide page in Notion. When the two disagree, this
file is the one that ships with the code.*
