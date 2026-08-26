---
name: project-context
description: "Read and maintain this repository's durable, Git-tracked context pipeline: current state, decisions, learnings, and linked evidence for repo-bound collaboration."
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

## Maintain

- Use `tasks/` for plans, progress, validation, and outcomes when the full
  profile is present; otherwise link the repository's existing task system.
- Keep `NOW.md` short and actionable.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings with stable IDs, evidence, scope, and a concrete future action.
- In the full profile, use `designs/` and `incidents/` for evidence that will
  help future work.
- Preserve completed evidence and correct its interpretation through status and
  supersession links rather than rewriting history.

Never store secrets, sensitive customer data, raw transcripts, private host
paths, ambient profiles, or unverified claims.
