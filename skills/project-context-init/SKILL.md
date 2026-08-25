---
name: project-context-init
description: Safely initialize durable project-context Markdown in an empty or existing repository, preserving existing instructions and legacy memory while offering GitNexus, Graphify, and OpenWiki only through separate informed opt-ins.
allowed-tools: Read, Glob, Grep, Bash
---

# Initialize Project Context

Create a portable `project-context/` package without overwriting existing
knowledge or harness instructions. Initialization and optional tool setup are
separate decisions.

## 1. Inspect before proposing changes

Run from the target repository:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py inspect --target .
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --dry-run
```

Review all classifications. The script reports existing core files, custom
content, managed instruction blocks, legacy memory candidates, and detection
signals for GitNexus, Graphify, and OpenWiki. Do not infer that legacy material
should be merged, renamed, or deleted.

If a managed block is malformed or duplicated, stop and ask the user how to
resolve it. Never repair unknown surrounding instructions automatically.

## 2. Ask about missing tools independently

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

## 3. Apply the context package

After the user approves the dry-run plan:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --apply
```

The script creates only missing templates, preserves different existing files,
and updates only the managed project-context block in every existing root
`AGENTS.md`, `agents.md`, `CLAUDE.md`, or `claude.md`. When none exists it
creates `AGENTS.md`. Re-run the dry-run after apply; it should report no writes.

## 4. Install only selected missing tools

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

## 5. Guide provider and secret setup

After an opted-in install, explain only the settings needed for the chosen
mode. Describe local/offline options when upstream supports them. Do not request
secret values in chat or place them in tracked files, task records, or agent
instructions. Use environment variables, an OS secret manager, CI secret store,
or a tool-owned user-level credential store; verify presence without printing
values.

## 6. Verify and hand off

- Re-run `inspect` and `init --dry-run`.
- Confirm only selected tools were added.
- Check `git diff --check` and inspect the complete diff for private paths,
  credentials, customer data, or product-specific assumptions.
- Tell the user which material was preserved and which legacy candidates still
  need deliberate classification.
