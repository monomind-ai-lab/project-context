# Archive

Documents kept for the record, not for use. Everything here describes a design
that shipped and was then dropped, or a handoff that has been superseded. None
of it describes how Project Context works today.

For that, read the repository [README](../../README.md), the
[builder's guide](../builders-guide.md), or `planning/project-context-design.md`.

| Document | What it was | Superseded |
| --- | --- | --- |
| [context-hub-architecture.md](context-hub-architecture.md) | The Context Hub's design: actors, episodes, entities, bitemporal relationships, and a two-plane durable/purgeable store | 2026-09-03 |
| [context-hub-handoff.md](context-hub-handoff.md) | The Codex handoff that delivered that design as `skills/context-hub/` in 0.6.0 | 2026-09-03 |

## Why these are kept

`skills/context-hub/` was removed rather than migrated, because it implemented a
design that had been dropped rather than a version of the one that replaced it.
Deleting the reasoning along with the code would have thrown away the part worth
keeping: these documents record what was tried, and why the two-product split
replaced it.

Four ideas survived into the current record model — the attribution triple,
content-addressed receipts, `path@commit` anchors, and the safety engineering
around create-only writes. Everything else here is history.

**Read them as evidence of a decision, not as instructions.** Their internals
still name `context-hub/1`, `SCAFFOLD_VERSION`, and a 0.6.0 baseline. All three
are retired.
