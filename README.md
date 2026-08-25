# Project Context

<p align="center">
  <img src="assets/project-context-cover.png" alt="Project Context — Clarity Comes With Context" width="720">
</p>

> **Project memory that survives the agent.**

Give every coding agent the same durable project memory—tracked in Git,
portable across tools, and safe to add to existing repositories.

Project Context is the Git-native continuity layer for AI-assisted repositories.
It records what is true now, why important decisions were made, what the team
learned, and where the supporting evidence lives. Unlike chat history,
proprietary memory, or generated documentation, it is reviewable, portable, and
owned by the repository.

## Why it matters

An agent returning after three weeks should not reconstruct the project from
stale chats and scattered plans. It should be able to answer four questions:

1. What is true now?
2. Which decisions constrain the work?
3. What has already been learned?
4. Where is the evidence?

Project Context provides those answers through a small set of typed Markdown
records and a maintenance protocol that works across coding-agent harnesses.
See the [filled example](examples/sample-project-context/) for the complete
core-profile experience.

## What is included

- **`project-context-init`** — reviews an existing repository, suggests safe
  consolidation, initializes the right profile, and validates context health.
- **`project-context`** — reads and maintains durable repository context.
- **Deterministic tooling** — dry-run/apply initialization, idempotency,
  scaffold version checks, and a read-only doctor.
- **Two profiles** — lightweight adoption or full evidence structure.

## Quick start

From a checkout of this repository, inspect the exact changes first:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --dry-run
```

Then apply the approved plan:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --apply
```

This installs both skills under `.agents/skills/`, creates the selected
`project-context/` profile, preserves custom files, and adds or refreshes only
the managed Project Context block in existing root agent instructions.

### Profiles

| Profile | Creates | Best for |
| --- | --- | --- |
| `core` | `README.md`, `SKILL.md`, `NOW.md`, `DECISIONS.md`, `LEARNINGS.md` | Small repositories, evaluation, and first-time adoption |
| `full` | Core plus `tasks/`, `designs/`, and `incidents/` templates | Long-lived projects, teams, and evidence-rich workflows |

Every installation records its profile and template version in
`project-context/.project-context.json`. Existing custom context is never
silently upgraded or overwritten; the doctor reports available scaffold updates
for deliberate review.

## Repository review and consolidation

Before initialization, the skill looks for material that may already serve the
same purpose:

- memory and context folders;
- status, current-state, and handoff files;
- ADR and decision records;
- plans, task logs, progress notes, and agent logs;
- solutions, lessons, learnings, and retrospectives;
- designs, specifications, RFCs, incidents, and postmortems.

Run the read-only review directly:

```sh
python3 skills/project-context-init/scripts/project_context_init.py review --target /path/to/repository
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
4. Confirm important claims against current code, tests, or operational state.

At a milestone or handoff:

1. Update the active task evidence.
2. Promote changed current state into `NOW.md`.
3. Record only decisions that constrain future work.
4. Promote only evidence-backed, reusable learnings.
5. Supersede stale knowledge instead of silently rewriting history.

## Authority model

| Layer | Role | Authority |
| --- | --- | --- |
| Source, tests, operational evidence | Actual behavior | Highest for factual behavior |
| `project-context/` | Current state, decisions, learnings, evidence routing | Canonical project continuity |
| Agent instructions | Tell agents how to use context | Pointer and protocol only |
| Generated indexes and wikis | Discovery and explanation | Derived; never current-state authority |

Project Context uses the standard Agent Skills shape (`SKILL.md`, `scripts/`,
`references/`, and `assets/`) while keeping project knowledge in ordinary,
Git-tracked Markdown.

<details>
<summary><strong>Advanced integrations: GitNexus, Graphify, and OpenWiki</strong></summary>

Project Context works without any of these tools. The initializer detects each
one before proposing changes and requires a separate informed decision for every
missing tool.

| Tool | Primary purpose | Choose it when |
| --- | --- | --- |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | Code symbols, relationships, impact, and execution flows | Agents need repository-level code intelligence |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Relationships across supported code, documents, and media | The useful corpus extends beyond source code |
| [OpenWiki](https://github.com/langchain-ai/openwiki) | Ongoing generated documentation and navigation | A browsable derived wiki justifies inference and maintenance cost |

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
- Tool installation never follows from context initialization automatically.
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

The behavioral suite covers empty and existing repositories, both profiles,
skill installation, dry-run/apply/idempotency, consolidation discovery, doctor
checks, custom context, instruction preservation, malformed markers, non-file
and symlink hazards, and optional-tool detection.

## License

[MIT](LICENSE)
