---
name: project-context
description: "Use when a repository or project folder contains project-context/, especially before meaningful work, when resuming or handing off, or when current state, decisions, learnings, and linked evidence need to be read or maintained."
---

# Project Context

Use this protocol when a repository or organized project folder contains
`project-context/` and collaborative work needs memory that survives any one
person, agent, or chat session. It applies to software, document, research,
writing, mixed, and folder-based projects.

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

Never store secrets, sensitive personal or customer data, raw chat transcripts,
private host paths, ambient user profiles, copyrighted source material copied
without need, or unverified claims. Generated wikis and indexes are auxiliary
discovery systems; they do not replace tracked Markdown authority.

## Health

When context appears stale, contradictory, or hard to navigate, use the sibling
`project-context-init` skill's `doctor` workflow. It checks core files, scaffold
version, review freshness, duplicate decision/learning IDs, and broken relative
links without rewriting content.

It also checks reachability: whether the managed instruction block, the harness
skill pointers, or a declared session hook will still deliver this protocol to
an agent. A `no-delivery-path` error means the context files are intact but
nothing loads them into a session — fix that before trusting the rest.
