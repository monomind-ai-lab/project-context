---
schema: context-hub/entity@1
hard_metadata:
  id: entity-example
  scope:
    level: project
    project_ids:
      - project-example
  created_at: YYYY-MM-DDTHH:MM:SSZ
  recorded_by: actor-example
curated_metadata:
  status: candidate
  canonical_name: Example entity
  entity_type: concept
  aliases: []
  asserted_by: actor-example
  approved_by: []
  approved_at:
  evidence:
    - episode:episode-example
  supersedes: []
  superseded_by: []
soft_metadata:
  suggested_description: ""
  extracted_from:
    - episode:episode-example
  labels: []
  generated_at:
  generated_by:
  confidence:
---

# Entity: Example entity

## Canonical description

State only what approved evidence supports. Keep inferred descriptions in soft
metadata until reviewed.

## Stable identifiers

- External or project identifiers: none.

## Evidence notes

- Explain which source establishes identity or aliases.
- Keep uncertain matches as separate candidates until stable identifiers or
  reviewed evidence support a merge.
