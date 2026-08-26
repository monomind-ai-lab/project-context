# Copy-paste prompt: install Project Context

Paste the prompt below into an AI agent that can read and edit the repository or
project folder you want to initialize.

```text
Install Project Context into the current repository or project folder from:
https://github.com/monomind-ai-lab/project-context

Project Context is a general-purpose context pipeline for repo-bound
collaborative projects and for projects organized in a shared folder. It is not
limited to software or to Git repositories.

Start by asking me exactly one question: “Is this a brand-new repository?”
Wait for my answer.

If I answer yes, ask what the repository will primarily hold or support, then
classify it as code, document, research, writing, mixed, or general. Do not
store my free-text answer by default. If I answer no, inspect the repository
and infer its type from aggregate content signals; do not ask what it is for.
Report the inferred type and confidence, and ask for correction only if the
result is ambiguous or choosing mixed would change the plan.

Then read `skills/project-context-init/SKILL.md` and
`skills/project-context-init/assets/project-context/` directly from the source
repository; no skill launcher is required. If you cannot access the source,
stop and ask me for a local path or copy instead of recreating templates from
memory. Perform a read-only adoption review. Find existing current-state,
decision, learning, task, design, incident, memory, status, plan, research, and
writing material that may overlap. Recommend the core or full profile and list
the exact files, links, and managed instruction-block changes you propose. Keep
primary artifacts such as source files, documents, datasets, papers, and
manuscripts in place; normally link them as evidence.

Do not write, move, merge, archive, delete, install add-ons, or edit repository
instructions until I approve the exact plan. After approval, create only missing
Project Context files and preserve differing existing content.

Consider GitNexus, Graphify, and OpenWiki only after classifying the repository.
Eliminate add-ons that are not useful for its type and actual contents. Do not
offer one merely because its repository type permits it; identify the observed
need first. For each remaining unconfigured add-on, ask independently, explain
its purpose, benefit,
footprint, dependencies, provider/local behavior, and recommendation level, and
wait for my answer. Never treat approval for one add-on as approval for another.

Use Python 3 automation when available for deterministic inspect, dry-run,
apply, idempotency, and doctor checks. Enumerate every root instruction file in
the proposed plan and do not touch one unless I approve it. If Python is
unavailable, follow the templates manually and state which automated guarantees
were not run. Finish by showing the complete diff, validation results, preserved
material, and any consolidation choices still awaiting a decision.
```
