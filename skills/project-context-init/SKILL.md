---
name: project-context-init
description: Safely review and initialize a repository's Git-native continuity layer, suggesting provenance-preserving consolidation of overlapping memory, status, decision, learning, task, design, and incident material without moving it automatically.
allowed-tools: Read, Glob, Grep, Bash
---

# Initialize Project Context

Create portable project memory that survives the agent without overwriting
existing knowledge or harness instructions. Review, initialization, health
checks, consolidation, and optional tool setup are distinct operations.

## 1. Inspect before proposing changes

Run from the target repository:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py inspect --target .
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --dry-run
```

Review all classifications. The script reports existing core files, custom
content, managed instruction blocks, consolidation candidates, scaffold version,
and detection signals for GitNexus, Graphify, and OpenWiki.

If a managed block is malformed or duplicated, stop and ask the user how to
resolve it. Never repair unknown surrounding instructions automatically.

## 2. Review possible consolidation

Run the read-only review explicitly when candidates exist:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py review --target .
```

The deterministic review finds likely overlaps such as `memory/`, `context/`,
status or handoff files, ADR/decision folders, plans, agent logs, solutions or
learnings, designs/specs, incidents, and postmortems. Treat names as discovery
signals, not proof.

Read only the candidate material needed to assess overlap. For each candidate:

- summarize its current purpose, authority, freshness, and provenance;
- map reusable content to `NOW.md`, `DECISIONS.md`, `LEARNINGS.md`, `tasks/`,
  `designs/`, or `incidents/`;
- identify conflicts, duplicates, and material that should remain where it is;
- propose link-only, copy-with-provenance, or deliberate migration options;
- explain what would become canonical and what would remain historical.

Present suggestions before initialization. Never move, merge, rewrite, archive,
or delete candidate material without separate, explicit authorization.

## 3. Choose a profile and apply

- `core` creates `README.md`, `SKILL.md`, `NOW.md`, `DECISIONS.md`, and
  `LEARNINGS.md`. Recommend it for small repositories and first-time adoption.
- `full` also creates task, design, and incident evidence folders and templates.

After the user approves the dry-run plan:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --profile core --apply
```

The script creates only missing files, records the scaffold version and profile,
preserves different existing files, and updates only its managed block in root
`AGENTS.md`, `agents.md`, `CLAUDE.md`, or `claude.md`. Re-run dry-run after
apply; it should report no writes.

When invoked from a checkout of this repository, `--install-skills` also copies
both skills into `.agents/skills/` using the same preserve-existing rules.

## 4. Ask about missing advanced tools independently

Read [references/optional-tools.md](references/optional-tools.md) before making
tool claims or running install commands. For **each** missing tool, ask a
separate non-leading question and wait for the user's answer before installing
anything. Each prompt must state:

- the tool's distinct purpose and concrete benefit for this repository;
- why it appears missing and what was inspected;
- its main runtime, generated files, and likely dependencies;
- whether it is optional or recommended for the observed repository;
- local/offline behavior and any provider/API requirements;
- that declining it does not affect Project Context.

An answer about one tool is not authorization for another. Record each result
as `accepted`, `declined`, or `deferred`. Do not bundle the choices behind one
yes/no prompt and do not install a declined or unanswered tool.

Keep this advanced-tool discussion after the core profile and consolidation
recommendation so it does not obscure the primary value.

## 5. Install only selected missing tools

Use the current official commands in
[references/optional-tools.md](references/optional-tools.md). Re-check detection
immediately before each install. Prefer repository-scoped and least-invasive
modes. For GitNexus, default to `analyze --skip-agents-md --skip-skills` so it
does not also edit harness files; configure MCP/hooks only if the user
separately wants them.

OpenWiki initialization generates or replaces derived wiki output and consumes
model inference. Ask again before the first generation run even after the CLI
install was approved. Graphify semantic extraction and visualization options
must follow its current official setup rather than assumed provider behavior.

## 6. Guide provider and secret setup

After an opted-in install, explain only the settings needed for the chosen
mode. Describe local/offline options when upstream supports them. Do not request
secret values in chat or place them in tracked files, task records, or agent
instructions. Use environment variables, an OS secret manager, CI secret store,
or a tool-owned user-level credential store; verify presence without printing
values.

## 7. Verify health and hand off

- Re-run `inspect` and `init --dry-run`.
- Run `doctor --target .`; explain stale state, duplicate IDs, broken links, and
  available scaffold updates without auto-fixing custom content.
- Confirm only selected tools were added.
- Check `git diff --check` and inspect the complete diff for private paths,
  credentials, customer data, or product-specific assumptions.
- Tell the user which material was preserved and which legacy candidates still
  need deliberate classification.
