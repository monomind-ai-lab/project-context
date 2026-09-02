---
schema: context-hub/actor@1
hard_metadata:
  id: actor-context-hub
  scope:
    level: hub
    project_ids: []
  created_at: 2026-09-01T00:00:00Z
  created_by: actor-context-hub
curated_metadata:
  kind: agent
  display_name: "Context Hub CLI"
  status: active
  aliases: []
  roles:
    - scaffold automation
soft_metadata:
  summary: "Built-in identity used only when project creation is not attributed to a registered user or agent."
  expertise: []
  tags: []
  generated_at:
  generated_by:
  confidence:
---

# Context Hub CLI

This built-in system actor records scaffold automation. Prefer
`add-project --created-by <registered-actor-id>` when a person or agent is the
actual project creator.
