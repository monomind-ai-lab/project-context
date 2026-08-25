# Project Context

Project Context is a small, Git-tracked memory system for software repositories.
It gives humans and coding agents the same durable source for current state,
decisions, verified learnings, designs, incidents, and task evidence without
depending on a particular agent product or chat history.

The system has two reusable skills:

- **`project-context`** reads and maintains an existing context package.
- **`project-context-init`** safely installs the package in an empty or existing
  repository and optionally helps configure complementary indexing tools.

## Why tracked Markdown is the authority

`project-context/` is reviewable in pull requests, available in clean clones,
portable across agent harnesses, and understandable without a database or
service. Generated wikis and indexes can improve discovery, but they are derived
views. They must not override current source code, tests, operational evidence,
or accepted records in `project-context/`.

The initialized package looks like this:

```text
project-context/
├── README.md
├── SKILL.md
├── NOW.md
├── DECISIONS.md
├── LEARNINGS.md
├── decisions/
│   ├── README.md
│   └── TEMPLATE.md
├── designs/
│   ├── README.md
│   └── TEMPLATE.md
├── incidents/
│   ├── README.md
│   └── TEMPLATE.md
└── tasks/
    ├── README.md
    └── TEMPLATE.md
```

## Install the skills

Copy or symlink the skill directories into a skill location recognized by your
agent harness. For Codex, a common project-scoped layout is:

```sh
mkdir -p .agents/skills
cp -R /path/to/project-context/skills/project-context .agents/skills/
cp -R /path/to/project-context/skills/project-context-init .agents/skills/
```

Then invoke `$project-context-init` from the target repository. The skill first
inspects the repository and shows a dry-run plan. It applies changes only after
the user approves them.

You can also inspect or initialize directly with the bundled deterministic
script:

```sh
python3 skills/project-context-init/scripts/project_context_init.py inspect --target /path/to/repo
python3 skills/project-context-init/scripts/project_context_init.py init --target /path/to/repo --dry-run
python3 skills/project-context-init/scripts/project_context_init.py init --target /path/to/repo --apply
```

`--apply` creates missing templates and adds or refreshes only the managed
`project-context` block in existing `AGENTS.md`, `agents.md`, `CLAUDE.md`, or
`claude.md`. It never overwrites custom context files. If none of those harness
files exists, it creates `AGENTS.md`. Re-running the command is idempotent.

## Daily use

At the start of meaningful repository work:

1. Read `project-context/NOW.md`.
2. Search `DECISIONS.md` and `LEARNINGS.md` for the task topic.
3. Open only the linked detailed records needed for the task.
4. Confirm important claims against current code, tests, or operational state.

At a milestone or handoff, update the active task record, then promote only
durable knowledge: current state into `NOW.md`, constraining choices into
`DECISIONS.md`, and evidence-backed reusable lessons into `LEARNINGS.md`.

## Optional building blocks

Project Context works without any of these tools. The initializer detects each
one before proposing changes and must ask about every missing tool separately.

| Tool | Primary purpose | Best when | Typical footprint and boundary |
| --- | --- | --- | --- |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | Code structure, symbols, relationships, impact, and execution flows | Agents need repository-level code intelligence and change-impact queries | Node.js 22+, native Tree-sitter/LadybugDB components, local `.gitnexus/` index; core indexing needs no API key |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Relate heterogeneous repository files, including supported documents and media | The useful corpus extends beyond source code or cross-file concepts matter | Python 3.10+ package `graphifyy` and derived `graphify-out/`; code indexing is local, while semantic extraction for non-code may use the host agent or a configured model |
| [OpenWiki](https://github.com/langchain-ai/openwiki) | Ongoing generated documentation and navigation | A browsable derived wiki should track repository evolution | Node.js 22+, generated `openwiki/`, local state under `~/.openwiki`; generation requires a host agent or configured model provider |

Choose tools by the question you need answered, not by an assumption that all
three are required. GitNexus is the recommended code-intelligence companion.
Graphify is valuable for mixed code/document/media corpora. OpenWiki is useful
when generated explanatory documentation is worth its inference and maintenance
cost. None replaces the tracked Markdown authority.

The current setup notes, detection markers, privacy boundaries, and official
links are maintained in
[`skills/project-context-init/references/optional-tools.md`](skills/project-context-init/references/optional-tools.md).

## Safety model

- Existing context files are preserved byte-for-byte.
- Unknown `memory`, `context`, or legacy context directories are reported, not
  migrated automatically.
- Malformed or duplicated managed instruction blocks stop apply mode before any
  write.
- Tool installation is never implied by context initialization.
- Each missing tool requires an independent, informed user decision.
- Secrets belong in environment variables, secret managers, or tool-owned
  user-level stores—not tracked files, prompts, logs, or commits.

## Validation

Run the complete local test suite:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

The scenarios cover an empty directory, existing upper- and lowercase harness
files, custom project context, legacy memory, malformed managed blocks,
dry-run/apply behavior, and idempotency.

## License

[MIT](LICENSE)
