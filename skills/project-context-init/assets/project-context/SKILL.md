---
name: project-context
description: "Read and maintain this repository's durable, Git-tracked current state, decisions, learnings, designs, incidents, and task evidence."
---

# Project Context

Use this local protocol whenever repository work needs prior decisions, current
handoff state, verified learnings, or a durable end-of-task update.

## Start

1. Read `project-context/NOW.md`.
2. Search `project-context/DECISIONS.md` and `project-context/LEARNINGS.md` for
   the task's topics.
3. Follow only relevant links into detailed records, source code, tests, and
   operational evidence.
4. Treat entries marked `superseded` as history only.

Do not load every historical task or generated wiki page. Current code, tests,
verified operational state, explicit user direction, and repository
instructions take precedence over summaries.

## Maintain

- Keep plans, chronological progress, validation, and outcomes in `tasks/`.
- Keep `NOW.md` short and actionable.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings with stable IDs, evidence, scope, and a concrete future action.
- Preserve completed evidence and correct its interpretation through status and
  supersession links rather than rewriting history.

Never store secrets, sensitive customer data, raw transcripts, private host
paths, ambient profiles, or unverified claims.
