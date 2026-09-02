---
schema: context-hub/relationship@1
hard_metadata:
  id: rel-example
  scope:
    level: project
    project_ids:
      - project-example
  created_at: YYYY-MM-DDTHH:MM:SSZ
  recorded_at: YYYY-MM-DDTHH:MM:SSZ
  recorded_by: actor-example
curated_metadata:
  status: candidate
  subject_id: entity-subject
  predicate: depends_on
  object_id: entity-object
  valid_at: YYYY-MM-DDTHH:MM:SSZ
  invalid_at:
  asserted_by: actor-example
  approved_by: []
  approved_at:
  evidence:
    - episode:episode-example
  supersedes: []
  superseded_by: []
soft_metadata:
  extraction_method: agent
  rationale: ""
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Relationship: Subject depends on object

## Interpretation

Define the predicate precisely and distinguish the claim's real-world validity
from when it was recorded. Keep exactly one object field: `object_id` for an
entity, actor, or project relationship; or replace it with `object_value` for a
literal fact.

## Evidence notes

- Quote or summarize only the minimum evidence needed and retain its reference.

## Supersession notes

- If this fact changes, create the replacement, set `invalid_at`, and link both
  records. Do not rewrite the old subject, predicate, object, or evidence.
