---
schema: context-hub/insight@1
hard_metadata:
  id: insight-example
  scope:
    level: project
    project_ids:
      - project-example
  created_at: YYYY-MM-DDTHH:MM:SSZ
  recorded_by: actor-example
curated_metadata:
  status: candidate
  statement: State the proposed insight precisely.
  applicability: Describe where it should and should not be reused.
  asserted_by: actor-example
  approved_by: []
  approved_at:
  evidence:
    - episode:episode-example
  supersedes: []
  superseded_by: []
soft_metadata:
  synthesis: ""
  entity_ids: []
  relationship_ids: []
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Insight: Short title

## Reasoning

Explain how the linked evidence supports the statement, including counterevidence
or uncertainty.

## Review

- Candidate review outcome:
- Approval rationale:

## Promotion

- Resulting `NOW.md`, decision, or learning entry: none.

Lifecycle is `candidate` → `approved` → `superseded`. Approval alone does not
replace the project's curated authority files; promote any durable consequence.
