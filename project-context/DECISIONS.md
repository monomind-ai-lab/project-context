# Decisions

## D-001: Make Markdown the default interface

- Date: 2026-11-08
- Statement: Default to plain Markdown context with an optional check; use managed regions and the installed protocol only for legacy compatibility.
- Rationale: The observed work already used registries and task logs while the managed protocol and CLI did not reach the main lead repositories.
- Evidence: [Usage review](../docs/usage-review-2026-11-07.md).

## D-002: Bound optional checks and keep promotion reviewable

- Date: 2026-11-08
- Statement: Check up to 100 first-parent revisions by default, infer merged PRs from PR-number subjects, allow explicit example-file exclusions, and reject legacy-only initialization options in the default mode. For task-record promotion, prefer an explicitly invoked finish-task skill that proposes a reviewable diff.
- Rationale: These boundaries keep the optional checks practical and make promotion a deliberate review step.
- Evidence: [Usage review](../docs/usage-review-2026-11-07.md) and [promotion proposal](../docs/proposals/2026-11-08-promote-from-task-records.md).
