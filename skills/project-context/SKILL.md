---
name: project-context
description: "Use when asked about Project Context or its Markdown records and tooling."
---

# Project Context

Project Context is plain Markdown. Read `project-context/README.md`, then `NOW.md`; search `DECISIONS.md` and `LEARNINGS.md` for the current topic and follow relevant evidence. Search decisions before changing security, identity, upstream-sync or credential behaviour. Give each decision a stable ID, date, statement, rationale and evidence; supersede rather than edit an old statement. Update current state and record reusable evidence when warranted. Preserve historical records.

The optional `project-context check --target .` reports broken references, edited decision statements, stale current state, and broken registry links. No command is required to read or maintain the Markdown. Legacy installations can use `project-context migrate --dry-run` followed by `--apply` to replace managed instruction regions.
