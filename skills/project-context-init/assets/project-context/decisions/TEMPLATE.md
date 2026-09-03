---
id: D-001
kind: decision
status: proposed
title: Decision title
created: 2026-01-01
asserted_by: person:name
---

# D-001: Decision title

The six keys above are the whole of what a record must carry. Everything else
is optional and is validated only when present: `approved_by`, `supersedes`,
`superseded_by`, `evidence`, `files`, `valid_at`, `invalid_at`, `session`,
`harness`, `model`. Absent means absent — do not carry an empty field forward.

`status` is one of `proposed`, `accepted`, `superseded`, `rejected` — the
vocabulary a `decision`, a `learning`, and a `capsule` share. A `question` uses
`open` → `answered` → `superseded`, and a `task` uses `proposed` → `active` →
`done` | `dropped`; the doctor checks a status against its own kind's set.
`asserted_by` and `approved_by` are `person:<name>` or `agent:<name>`, and an
agent may not approve what it asserted.

- Registry: [`D-001`](../DECISIONS.md)

## Context

What constraint or opportunity requires a decision?

## Decision

What will the project do?

## Alternatives considered

- Alternative and reason it was not selected.

## Consequences

- Benefits, costs, risks, and follow-up work.

## Evidence

- Links to primary artifacts, reviews, tests, tasks, incidents, measurements,
  citations, or official references. Pin a repository path to the state it
  cites: `path/to/file@<commit>`.
- A reference may also use the shared grammar, validated by shape:
  `commit:<binding>:<sha>`, `pr:<binding>#<number>`,
  `review:<binding>#<pr>/<comment-id>`, `ticket:<tracker>:<key>`,
  `doc:<binding>:<path>@<commit>`, `session:<harness>:<id>`, `url:https://…`,
  or `capsule:<id>`.
