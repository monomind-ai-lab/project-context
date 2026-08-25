---
name: project-context
description: "Maintain the Git-native continuity layer for an AI-assisted repository: current state, accepted decisions, verified learnings, designs, incidents, and task evidence shared across coding agents."
---

# Project Context

Use this protocol when a repository contains `project-context/` and work needs
project memory that survives the agent or chat session.

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

- Use `tasks/` for plans, progress, validation, and outcomes when the full
  profile is present; otherwise link the repository's existing task system.
- Keep `NOW.md` concise and actionable; remove stale state after linking its
  durable result.
- Record decisions with stable IDs, status, date, statement, rationale,
  consequences, and evidence. Supersede instead of silently reversing meaning.
- Record learnings only when evidence supports reuse beyond one task.
- In the full profile, create detailed designs or incident records when their
  evidence will help future work.
- Preserve completed historical records. Correct interpretation through status
  and supersession links instead of rewriting history.

## Safety

Never store secrets, sensitive customer data, raw chat transcripts, private
host paths, ambient user profiles, or unverified claims. Generated wikis and
indexes are auxiliary discovery systems; they do not replace tracked Markdown
authority.

## Health

When context appears stale, contradictory, or hard to navigate, use the sibling
`project-context-init` skill's `doctor` workflow. It checks core files, scaffold
version, review freshness, duplicate decision/learning IDs, and broken relative
links without rewriting content.
