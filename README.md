# Project Context

<p align="left">
  <img src="assets/project-context-cover.jpg" alt="Project Context — Clarity Comes With Context" width="720">
</p>

> **Shared project context that outlives any one person, agent, or chat.**

Project Context is a simple way to build a context pipeline right into a
repository or project folder. It is best suited to repo-bound collaborative
projects, where version control makes shared context easy to review and evolve.
But it also works well for any project whose working materials are organized in
one folder that people and AI agents can access consistently.

It works with software, document, research, writing, and mixed repositories. As
work produces evidence, milestones promote the current state, durable decisions,
and verified learnings into small Markdown files—Git-tracked when version
control is available. Unlike chat history, proprietary memory, or generated
documentation, that context stays portable across collaborators and tools—and
remains owned by the project.

## Why it matters

A collaborator returning after three weeks should not reconstruct the project
from stale chats and scattered plans. They should be able to answer four questions:

1. What is true now?
2. Which decisions constrain the work?
3. What has already been learned?
4. Where is the evidence?

Project Context provides those answers through a small set of typed Markdown
records and a maintenance protocol that works across repositories and agent
harnesses.
See the [filled example](examples/sample-project-context/) for the complete
core-profile experience.

## What is included

- **`project-context-init`** — reviews an existing repository, suggests safe
  consolidation, initializes the right profile, and validates context health.
- **`project-context`** — reads and maintains durable project-folder context.
- **Deterministic tooling** — dry-run/apply initialization, idempotency,
  scaffold version checks, and a read-only doctor.
- **Two profiles** — lightweight adoption or full evidence structure.
- **Two ready-to-copy prompts** — install or maintain the pipeline with any AI
  agent that can read and edit the repository.

## Install with any AI agent

No skill launcher or Python runtime is required for the agent-guided path. Copy
the prompt below into an AI agent that can access the target repository or
project folder. The agent starts by asking whether the repository is brand-new,
then adapts the pipeline to software, documents, research, writing, mixed, or
general work.

```text
Install Project Context into the current repository from
https://github.com/monomind-ai-lab/project-context.

Start by asking me exactly: “Is this a brand-new repository?” Wait for my
answer. If yes, ask what it will primarily hold or support and classify it. If
no, inspect the repository and infer whether it is code, document, research,
writing, mixed, or general without asking its purpose. Report the inferred type
and confidence; ask for correction only if ambiguity would change the plan.

Then read `skills/project-context-init/SKILL.md` and its templates directly from
the source repository; no skill launcher is required. If the source is
unavailable, ask me for a local copy rather than recreating it from memory.
Perform a read-only adoption and consolidation review. Recommend core or full,
list every proposed change, and wait for approval before writing. Preserve
existing context and primary artifacts. Consider GitNexus, Graphify, and
OpenWiki only after classification; offer an add-on only when an observed need
justifies it, and ask independently about each remaining option. Use Python
automation when available, but follow the templates manually when it is not.
Finish with the complete diff and validation results.
```

Use the [full installation prompt](prompts/install-project-context.md) when you
want every safety and add-on instruction included. After installation, the
[maintenance prompt](prompts/maintain-project-context.md) works with agents that
do not support installed skills.

## Deterministic CLI setup (optional)

From a checkout of this repository, inspect the exact changes first:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --dry-run
```

Then apply the approved plan:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --apply
```

This installs both skills under `.agents/skills/`, creates the selected
`project-context/` profile, preserves custom files, and adds or refreshes only
the managed Project Context block in existing root agent instructions.

For a brand-new repository, first decide its primary type from its intended
purpose, then use `--repository-stage brand-new --repo-type TYPE`. The CLI never
stores the free-text purpose.

### Profiles

| Profile | Creates | Best for |
| --- | --- | --- |
| `core` | `README.md`, `SKILL.md`, `NOW.md`, `DECISIONS.md`, `LEARNINGS.md` | Small repositories, evaluation, and first-time adoption |
| `full` | Core plus `tasks/`, `designs/`, and `incidents/` templates | Long-lived projects, teams, and evidence-rich workflows |

Every installation records its profile, repository type, and template version
in `project-context/.project-context.json`. The user's free-text purpose is not
stored automatically. Existing custom context is never
silently upgraded or overwritten; the doctor reports available scaffold updates
for deliberate review.

## Repository review and consolidation

For existing repositories, the skill first classifies the project from aggregate
content signals and looks for material that may already serve the same purpose:

- memory and context folders;
- status, current-state, and handoff files;
- ADR and decision records;
- plans, task logs, progress notes, and agent logs;
- solutions, lessons, learnings, and retrospectives;
- designs, specifications, RFCs, incidents, and postmortems;
- research plans, references, datasets, manuscripts, chapters, and drafts that
  should usually remain primary evidence and be linked rather than migrated.

Run the read-only review directly:

```sh
python3 skills/project-context-init/scripts/project_context_init.py review --target /path/to/repository --repo-type auto
```

Candidates are classified by likely role and confidence. The skill then reviews
their actual purpose, authority, freshness, provenance, overlaps, and conflicts
before suggesting one of three approaches:

- keep in place and link;
- copy selected knowledge with provenance;
- deliberately migrate into the canonical Project Context structure.

The review **never moves, merges, rewrites, archives, or deletes automatically**.

## Health checks

```sh
python3 skills/project-context-init/scripts/project_context_init.py doctor --target /path/to/repository
```

The doctor checks:

- required core files;
- installed scaffold version;
- freshness of `NOW.md`;
- duplicate decision and learning IDs;
- broken relative Markdown links.

It reports issues without rewriting custom knowledge.

## Daily workflow

At the start of meaningful work:

1. Read `project-context/NOW.md`.
2. Search `DECISIONS.md` and `LEARNINGS.md` for the task topic.
3. Follow only relevant links into detailed evidence.
4. Confirm important claims against current primary artifacts and evidence.

At a milestone or handoff:

1. Update the active task evidence.
2. Promote changed current state into `NOW.md`.
3. Record only decisions that constrain future work.
4. Promote only evidence-backed, reusable learnings.
5. Supersede stale knowledge instead of silently rewriting history.

## Authority model

| Layer | Role | Authority |
| --- | --- | --- |
| Primary artifacts and verified evidence | Actual project truth | Highest for factual claims |
| `project-context/` | Current state, decisions, learnings, evidence routing | Canonical project continuity |
| Agent instructions | Tell agents how to use context | Pointer and protocol only |
| Generated indexes and wikis | Discovery and explanation | Derived; never current-state authority |

Project Context uses the standard Agent Skills shape (`SKILL.md`, `scripts/`,
`references/`, and `assets/`) while keeping project knowledge in ordinary
Markdown. Git provides reviewable history when available, but the context
pipeline also works in a consistently shared project folder.

<details>
<summary><strong>Advanced integrations: GitNexus, Graphify, and OpenWiki</strong></summary>

Project Context works without any of these tools. The initializer detects each
potentially relevant tool before proposing changes and requires a separate
informed decision for every eligible, unconfigured tool.

| Tool | Primary purpose | Choose it when |
| --- | --- | --- |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | Code symbols, relationships, impact, and execution flows | A code or mixed repository contains a meaningful software system |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Relationships across supported code, documents, research artifacts, and media | A substantial corpus needs cross-file or cross-format navigation |
| [OpenWiki](https://github.com/langchain-ai/openwiki) | Ongoing generated documentation and navigation | A stable, complex project has a clear audience for a maintained derived wiki |

The initializer filters this list by repository type and observed contents. It
does not ask writing projects about code analysis or present every add-on as a
default checklist.

Current setup notes, footprints, provider boundaries, and official links live
in [the optional-tools reference](skills/project-context-init/references/optional-tools.md).

</details>

## Safety guarantees

- Existing context files are preserved byte-for-byte.
- Existing `AGENTS.md`, `agents.md`, `CLAUDE.md`, and `claude.md` content is
  preserved outside one managed block, including file mode and CRLF endings.
- Unknown or overlapping memory is reviewed and classified, not migrated.
- Malformed blocks, unsafe symlinks, non-file harness paths, and non-UTF-8
  instructions stop apply mode before writes.
- Add-ons are filtered by repository type, then installed or configured only
  after an independent informed opt-in.
- Secrets never belong in tracked context, prompts, logs, or commits.

## Manual skill installation

If you only want the skills and not the scaffold:

```sh
mkdir -p .agents/skills
cp -R /path/to/project-context/skills/project-context .agents/skills/
cp -R /path/to/project-context/skills/project-context-init .agents/skills/
```

Then invoke `$project-context-init` in the target repository.

## Development and validation

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

The behavioral suite covers empty and existing repositories, repository-type
classification, add-on filtering, both profiles, skill installation,
dry-run/apply/idempotency, consolidation discovery, doctor checks, custom
context, instruction preservation, malformed markers, and path hazards.

## License

[MIT](LICENSE)
