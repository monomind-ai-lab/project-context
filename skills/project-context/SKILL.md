---
name: project-context
description: "Read and maintain a repository's durable, Git-tracked project context: current state, decisions, learnings, designs, incidents, and task evidence. Use when repository work needs prior context or a durable handoff; do not use generated indexes as authority."
---

# Project Context

Use this protocol when a repository contains `project-context/` and work needs
prior decisions, current handoff state, or a durable update.

## Start

1. Read `project-context/NOW.md`.
2. Search `project-context/DECISIONS.md` and `project-context/LEARNINGS.md` for
   the current topic.
3. Follow only relevant links into detailed decisions, designs, incidents,
   tasks, source code, tests, and operational evidence.
4. Treat entries marked `superseded` as historical evidence only.

Do not load every historical task or generated page. Current code, tests,
verified operational state, explicit user direction, and repository instructions
take precedence over summaries.

## Maintain

- Keep plans, chronological progress, validation, and outcomes in `tasks/`.
- Keep `NOW.md` concise and actionable; remove stale state after linking its
  durable result.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings only when evidence supports reuse beyond one task.
- Create detailed designs or incident records when their evidence will help
  future work.
- Preserve completed historical records. Correct interpretation through status
  and supersession links instead of rewriting history.

## Safety

Never store secrets, sensitive customer data, raw chat transcripts, private
host paths, ambient user profiles, or unverified claims. Generated wikis and
indexes are auxiliary discovery systems; they do not replace tracked Markdown
authority.
