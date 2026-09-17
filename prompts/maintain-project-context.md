# Copy-paste prompt: use and maintain Project Context

```text
Use this repository or project folder's project-context/ as the shared context
pipeline for this task: [DESCRIBE THE TASK]

Before working, read project-context/SKILL.md and NOW.md, then search
DECISIONS.md and LEARNINGS.md for relevant constraints. Follow only the linked
primary artifacts and evidence needed for the task. Current artifacts, verified
evidence, my instructions, and repository instructions override summaries.

At a meaningful milestone or handoff, evaluate every trigger in SKILL.md. Use
`project-context record` to create or update any decision, question, task,
design, or incident that fired; update NOW.md for changed current state and add
a learning only when it is verified and reusable. Link evidence, mark replaced
records as superseded, and preserve history. Never store secrets, sensitive
data, raw chat transcripts, private paths, or unverified claims. Finish by
summarizing context changes and validation.
```
