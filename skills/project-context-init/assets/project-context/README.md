# Project Context

This directory is the Git-tracked, harness-neutral entrypoint for durable
project knowledge. It records current state, decisions that constrain future
work, reusable learnings, and typed supporting evidence.

## Read order

1. Read [`SKILL.md`](SKILL.md) for the operating protocol.
2. Read [`NOW.md`](NOW.md) for current state, active work, blockers, and next actions.
3. Search [`DECISIONS.md`](DECISIONS.md) and [`LEARNINGS.md`](LEARNINGS.md) by topic.
4. Open only the linked decision, design, incident, task, source, and test
   evidence needed for the current work.

## Artifact roles

| Location | Authority and purpose | Update rule |
| --- | --- | --- |
| `NOW.md` | Current snapshot and handoff | Replace stale state; keep concise |
| `DECISIONS.md` | Accepted and superseded decisions | Append or supersede; never silently reverse |
| `LEARNINGS.md` | Verified, reusable lessons | Promote only evidence-backed lessons |
| `decisions/` | Detailed decision records | Link from the registry; preserve status |
| `designs/` | Designs and alternatives | Keep decisions separate from proposals |
| `incidents/` | Root cause, remediation, prevention | Preserve history; promote reusable lessons |
| `tasks/` | Plans, progress, validation, outcomes | Keep completed records immutable |

Source code, tests, and verified operational evidence remain authoritative for
actual behavior. Generated indexes and wikis are auxiliary views.

## Promotion workflow

At a meaningful milestone or handoff:

1. Update the active task record with progress and validation evidence.
2. Update `NOW.md` when active state, blockers, or next actions changed.
3. Add a decision only when it constrains future work.
4. Add a learning only when verified and reusable beyond one task.
5. Link promoted knowledge to its source task, code, test, incident, or commit.
6. Mark replaced knowledge `superseded` and link both directions.

Do not store raw chat transcripts, credentials, private host paths, sensitive
customer data, ambient profiles, or unverified speculation here.

