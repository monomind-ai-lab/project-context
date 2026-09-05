# Project Context — Builder's Guide

For **builders**: anyone working in a project repository that has Project
Context installed. If you administer a Project Hub instead, you want the
[owner's guide](https://github.com/monomind-ai-lab/project-hub) in that
repository.

Written against **0.10.0**. Everything here is built and tested unless it appears
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
| `--profile core` (default) | `README.md`, `SKILL.md`, `NOW.md`, `DECISIONS.md`, `LEARNINGS.md` — the three registries and the protocol, and no subfolders. Enough for most repositories. |
| `--profile full` | Adds `PLAN.md` and `QUESTIONS.md`, and the `decisions/`, `questions/`, `tasks/`, `inbox/`, `designs/` and `incidents/` subfolders. Take this when the project already has that much going on. |
| `--repo-type` | `auto` by default. Also `code`, `document`, `research`, `writing`, `mixed`, `general`. |
| `--install-skills` | Installs the protocol skill so agents in this repo can find it. |
| `--install-hooks` | Wires the session hooks into `.claude/settings.json`. Opt-in, never assumed. |

### What lands in your repository

```text
project-context/
  NOW.md                  current state, active work, blockers, next action
  PLAN.md                 the current milestone; full profile
  DECISIONS.md            the decision registry
  LEARNINGS.md            verified reusable lessons
  QUESTIONS.md            open questions and the assumptions you proceed on
  decisions/              detail records, one per decision that needs room
  questions/              a question that needs more room than the registry gives
  inbox/                  capsules from `capture`, waiting to be promoted
  tasks/ designs/ incidents/     full profile only
  README.md               what this folder is, for a human who found it
  SKILL.md                the protocol, readable in place
  .project-context.json   the marker: product, schema, version, stamps
```

And a managed block in **both** `CLAUDE.md` and `AGENTS.md` at the repository
root, creating whichever is missing. The block is delimited by
`<!-- project-context:start -->` and `<!-- project-context:end -->`. **Nothing
outside those markers is ever read or written** — whatever house rules you keep
in those files are untouched, and re-running install is idempotent.

If you had neither file, you get both, and each opens with a short header
saying what it is and that everything outside the block is yours to write. That
matters: an earlier version created only `AGENTS.md`, so a Claude-only
repository ended up with rules no Claude session ever read.

The block now opens by saying it is managed. That is not decoration — before it
did, the region read like prose your own team had written, and there was
nothing to tell a colleague or another agent that editing it would be undone
the next time anyone ran an update.

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

### Reading before you work

```bash
project-context context --task "add rate limiting" --files src/api/gateway.py
```

Assembles what matters for that task instead of making you read the folder: the
owner's `global/` summary and guardrails, the `blueprint/` epic, `NOW.md` and
the active `PLAN.md` items, then the decisions, learnings and questions whose
evidence anchors share a path prefix with the files you named — and after those,
the ones that merely share vocabulary with the task line.

The order is the point. A packet that led with your own notes would bury the
constraint that was not negotiable. What does not fit the token budget comes
back as a link rather than being dropped, so it never implies that what it left
out does not exist.

Use `--mode plan` when writing a plan — it leads with `blueprint/` — and
`--mode review --diff` to assemble the packet for whatever is currently changed
in your working tree. `project-context onboard` is the preset for a first
session, and is what the `SessionStart` hook emits.

Only `accepted` and `answered` records are loaded. Proposed ones are listed as
links, so you can see they exist without being told they are settled.

### What to write, and where

| When | Write |
| --- | --- |
| A choice now constrains future work | A decision in `DECISIONS.md`; a detail record in `decisions/` if it needs room for alternatives and consequences |
| You learned something that generalises past this task | A learning in `LEARNINGS.md` |
| The state of play changed | `NOW.md` — keep it under 400 words; it is read every session |
| You are unsure and the answer changes the work | A question in `QUESTIONS.md`. Ask it before implementing, not after |
| Something is worth keeping but you cannot yet say what it is | `project-context capture`. It lands in `inbox/` and the judgement waits |

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

## Capturing without stopping

```bash
project-context capture --kind decision \
  --text "We standardise on pnpm; npm workspaces could not hoist the native deps." --apply
```

The point is that it is cheap. A decision worth recording almost always
surfaces mid-task, and stopping to write a registry entry with an ID, a
rationale and consequences is exactly the interruption you decline — so the
decision goes unrecorded and the reason is lost. `capture` writes one short,
dated, attributed note into `inbox/` and gets out of your way.

`--kind` is `decision`, `learning`, `question`, `assumption`, `constraint`, or
`proposal`. It says what the note is *about*; every capsule is `kind: capsule`
in the record model. A `proposal` is how you ask for a change to something the
Hub pushed — you cannot edit those, and a proposal reaches the owner at their
next `/hub-pull`.

You do not supply provenance. It records the actor from your git identity
(`--actor agent:<name>` when an agent writes it), `--session`, `--harness` and
`--model` where the harness knows them, and the current commit as evidence.

Two limits worth knowing: a capsule is at most 200 words and a longer one is
refused, because anything longer is the record it should become; and capturing
the same text twice on the same day writes once, so a hook that fires twice
does not leave you two identical notes to triage.

Promotion is yours. Write the registry entry the capsule earns and set its
`status` to `accepted` with a link to what it became, or `rejected` when it
belongs nowhere. Leaving it `proposed` is the only outcome that is not a
resolution — and `project-context review` will keep raising it until you pick.

---

## Checking your work

### The doctor

```bash
python3 .agents/skills/project-context/scripts/context_doctor.py --target .
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
python3 .agents/skills/project-context/scripts/context_triggers.py status
```

It detects that work has landed since project context was last touched, and nags
once per session. It does **not** decide what to write — only you know whether a
choice constrained future work. When you have genuinely evaluated and there is
nothing to record:

```bash
python3 .agents/skills/project-context/scripts/context_triggers.py ack --note "reviewed; nothing constraining"
```

The acknowledgement is bound to the commit it evaluated, so it cannot be used to
wave away later work.

### The indexes

```bash
python3 .agents/skills/project-context/scripts/context_index.py --check
```

`DECISIONS.md` and `LEARNINGS.md` grow without bound and get read end to end.
The index tables at the top let a reader answer "does anything here constrain
what I am about to do?" without paying for the whole file. `--check` verifies
they are current; run it in CI.

### The standing review

```bash
project-context review --open-days 14
```

The doctor answers "is this correct?". This answers a different question: what
has been sitting here waiting for a person? Proposed records, questions open
past their window, capsules nobody promoted, assumptions nobody confirmed,
drifted evidence anchors, a stale `NOW.md`, a pushed snapshot the owner has not
refreshed.

Oldest first, because latency is the failure this system is exposed to — a
five-week-old question matters more than a fresh one whatever their subjects.
It exits zero whatever it finds: a backlog is not a build failure, and CI that
broke on an open question would teach everyone to stop filing them.

### Plans and epics

Where a Hub owner has pushed `blueprint/EPIC.md` into your repository, each
`## M-NNN:` item in your `PLAN.md` names the epic item it advances:

```markdown
## M-001: Ship the search endpoint

- Status: `active`
- Serves: E-002
```

The doctor enforces the pair, and the asymmetry is deliberate. A plan item that
names no epic item is an **error** — the project is spending effort the epic
does not ask for, and the fix is to anchor it or raise a question. An epic item
no plan item serves is only a **warning**, because an epic is allowed to run
ahead of the milestone in front of you.

No `blueprint/` means no epic, and `PLAN.md` stands alone with nothing checked
against it. Project Context is a complete product without a Hub.

---

## Keeping up to date

```bash
project-context update --dry-run    # the exact plan
project-context update --apply
```

Local only — nothing in it reaches a network. Read the dry run by authorship:

- **`refresh`** and **`regenerate_index`** — files this product owns, brought to
  the current release.
- **`create`** — a scaffold file your install predates.
- **`preserve_existing`** — a record you wrote. Seeing one is the command
  working correctly.

It never writes to `global/` or `blueprint/`. Those are verified against their
stamps and reported: a `pushed-file-modified` entry means someone edited a copy
the Hub sent, and the fix is a question, not an edit.

Re-running `init` will not do this. Install is create-only for everything,
which is right for your records and means it carries nothing forward.

---

## Not built yet

Named here so you do not go looking for them:

- **`SessionEnd` session capsules** — writing a capsule automatically at the end
  of a session that produced none. `capture` is manual today, and the `Stop`
  gate offers it rather than doing it.
- **A `promote` command** — promotion is editing: write the registry entry and
  set the capsule's status. There is no one-liner for it yet.
- **Cross-project retrieval** — assembling context across several projects at
  once. That belongs to the Hub side and is deliberately not on the repository
  side: your packet sees this project and the global snapshot, which is the
  correct blast radius.

---

## Rules that will not change

- Records are never rewritten by tooling. Create-only, always.
- Nothing in this product reaches the network.
- The tool never creates a remote, never pushes, never invites anyone.
- Zero runtime dependencies.

---

*Mirrored to the Builder's Guide page in Notion. When the two disagree, this
file is the one that ships with the code.*
