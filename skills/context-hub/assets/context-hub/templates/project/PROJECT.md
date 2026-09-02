---
schema: context-hub/project@1
hard_metadata:
  id: project-example
  scope:
    level: hub
    project_ids: []
  created_at: YYYY-MM-DDTHH:MM:SSZ
  created_by: actor-example
curated_metadata:
  title: Project title
  status: active
  actor_ids:
    - actor-example
  context_project_allowlist: []
  workspace_bindings:
    - binding_id: product-main
      kind: git
      repository: owner/repository
      default_branch: main
      root_path: .
soft_metadata:
  summary: ""
  related_project_ids: []
  tags: []
  generated_at:
  generated_by:
  confidence:
---

# Project: Project title

## Purpose and boundary

- Outcome this project exists to produce:
- Included:
- Excluded:

## Authority

- Current state: [`NOW.md`](NOW.md)
- Decisions: [`DECISIONS.md`](DECISIONS.md)
- Learnings: [`LEARNINGS.md`](LEARNINGS.md)
- L0 route: [`SUMMARY.md`](SUMMARY.md)
- L1 map: [`OVERVIEW.md`](OVERVIEW.md)

## Workspace bindings

Use `repo:<binding-id>:<path>@<commit>` in evidence. Map each binding to a
machine path only in ignored `.context-hub/local.yaml`.

## Access and ownership

- Project owner or approving role:
- Intended collaborators:
- Retention or confidentiality notes:

## Cross-project context

- Approved past-project sources: none. Add stable project IDs to
  `context_project_allowlist`; do not rely on soft related-project suggestions.
