# Project Context

<p align="left">
  <img src="assets/project-context-cover.jpg" alt="Project Context — Clarity Comes With Context" style="width: 100%; max-width: 100%;">
</p>

> **Shared project context that outlives any one person, agent, or chat.**

Project Context builds a context pipeline right into a repository or project
folder. As work produces evidence, milestones promote the current state, durable
decisions, and verified learnings into small Markdown files—Git-tracked when
version control is available. Unlike chat history, proprietary memory, or
generated documentation, that context stays portable across collaborators and
tools—and remains owned by the project.

For teams and people working across several projects, the same protocol can now
live in a separate **Context Hub**: a private, Git-backed Markdown workspace
that is independent of the repositories or folders it describes. It can be
opened in Obsidian, reached through filesystem-aware agents or MCP, and indexed
by Graphify as an optional derived graph. Markdown and Git remain the storage
contract; no database, vector store, or server is required.

Project Context works with software, document, research, writing, and mixed
projects. Context can live beside one project or in a hub that coordinates many
projects and collaborators, while primary work remains in its original home.

Project Context is **agent-operated and human-readable**. People provide intent,
answer onboarding and opt-in questions, and approve proposed changes. Agents
read the skills and Markdown instructions, run the tooling, maintain the context
files, and verify the result. Humans can review or edit the Markdown at any time,
but they are not expected to invoke skills or run Python commands themselves.



---

## 🚀 Quick Start (30 Seconds)

Two ways in — one command if you have Python tooling, one pasted prompt if you
have nothing but an AI agent. Both preview the exact plan before writing.

### Single-command install (recommended)

With `uvx` or `pipx`:

```sh
uvx --from git+https://github.com/monomind-ai-lab/project-context project-context init --target . --install-skills --apply
```

Or install once and reuse:

```sh
pipx install git+https://github.com/monomind-ai-lab/project-context
project-context init --target . --install-skills --apply
```

The CLI is deterministic: swap `--apply` for `--dry-run` to preview the exact
file plan first. Zero runtime dependencies — stdlib Python 3.10+. Available
embedded-mode subcommands: `init`, `inspect`, `review`, `doctor`. Context Hub
operations live under the separate `hub` namespace.

### Agent-guided install

**No skill launcher, Python tooling, or manual setup required** — your AI agent
does the work, asks the onboarding question, and shows you the plan for
approval. Paste this prompt into any AI agent that can read and edit your
target repository or project folder:

```text
Install Project Context in the current repository or project folder using
https://github.com/monomind-ai-lab/project-context. Read and follow
`skills/project-context-init/SKILL.md`, starting with its required onboarding
question. Show me the proposed plan and wait for my approval before making changes.
```

The agent starts by asking whether the repository is brand-new, then adapts the
pipeline to software, documents, research, writing, mixed, or general work.
Before writing anything, it proposes the profile, the exact file changes, and any
relevant optional tools, and waits for your approval.

- **[Standalone installation prompt](prompts/install-project-context.md)** — an
  easy-to-copy version of the prompt above. The full behavior stays in the skill
  so the prompt does not drift or duplicate instructions.
- **[Maintenance prompt](prompts/maintain-project-context.md)** — use the
  pipeline after installation, including with agents that do not support
  installed skills.
- **[Context Hub creation prompt](prompts/create-context-hub.md)** — have an
  agent create and validate a local private-hub scaffold without creating a
  remote repository or pushing anything.



---

## 🏠 Choose Where Context Lives

Project Context supports three context-placement modes:

| Mode | Context location | Status and fit |
| --- | --- | --- |
| **Embedded** | `project-context/` inside the working project | Supported. Best when the work and its context share the same collaborators and visibility. |
| **Hub-native** | A separate Context Hub repository or folder | Supported. Best for a team, multiple projects, or an Obsidian-based context workspace. |
| **Linked** | Work stays in an external project; authoritative context lives in a hub | Supported. `bind-project` records portable Git/folder metadata while keeping each clone's absolute path in ignored local configuration. |

The Hub-native mode is deliberately filesystem-first. Its core is ordinary
Markdown, JSON Schema documentation, and deterministic Python tooling. Obsidian
is an optional client, not a required runtime, and Graphify is an optional
rebuildable navigation layer rather than a source of truth.

The design rationale and adaptations from OpenViking, Zep/Graphiti, and AGORA
are documented in the [Context Hub architecture](docs/context-hub-architecture.md).

An initialized hub has this portable shape:

```text
context-hub/
├── .context-hub.json              # hub identity and scaffold marker
├── .context-hub/receipts/        # content-addressed ingestion receipts
├── SUMMARY.md / OVERVIEW.md      # L0/L1 routing views
├── actors/                       # scoped people and agent identities
├── projects/<project-id>/        # curated context and typed knowledge
│   ├── PROJECT.md / SUMMARY.md / OVERVIEW.md
│   ├── NOW.md / DECISIONS.md / LEARNINGS.md
│   └── entities/ / relationships/ / insights/
├── sources/raw/<project-id>/YYYY/MM/
├── sources/episodes/<project-id>/YYYY/MM/
├── shared/                       # reviewed cross-project records only
├── schemas/ / templates/
└── .obsidian/                    # optional safe core configuration
```

### The Context Hub pipeline

```text
immutable raw sources + episode envelopes
  → candidate entities + temporal relationships + insights
  → reviewed NOW.md + DECISIONS.md + LEARNINGS.md
  → optional Graphify graph (derived and rebuildable)
```

Sessions, daily agent logs, meeting notes, and imports enter as content-addressed
raw source bytes, a uniquely named episode envelope, and an ingestion receipt.
After their first commit, corrections are new episodes linked to the original;
agents do not silently rewrite the raw source. Extracted entities,
relationships, and insights begin as candidates. Relationships keep separate
recorded, valid, and invalid times so the hub can preserve what was known and
what was true without flattening history.

UTF-8 sources up to the safe embedding limit are also copied verbatim into a
clearly fenced, untrusted L2 section of the episode so agents and Graphify can
extract candidates. Byte-exact raw payloads are always retained and hashed;
binary and oversized sources remain link-only and `sources/raw/` is excluded
from Graphify.

Human and agent attribution is explicit. Stable actor IDs distinguish who
asserted a claim, which person or agent recorded it, and who approved it.
Reviewed consequences are promoted into the project's curated current state,
decisions, and learnings. Hub and project summaries route agents efficiently;
they do not outrank curated records or evidence.

This structure supports several projects in one trust domain and allows teams
to review candidate cross-project knowledge before promoting it into `shared/`.
Graphify can then surface relationships and paths across tracked Markdown, but
its output remains disposable: consequential claims must resolve back to a
curated record or source episode.

Retrieval defaults to the active project plus reviewed `shared/` knowledge. A
new project can reuse relevant context from a past project when its curated
`context_project_allowlist` names that project or the user explicitly expands
the scope. Soft similarity or a graph edge alone never injects one project's
private assertions into another.

### Privacy and trust boundaries

- One hub repository is one read-access trust domain. Git hosting does not
  provide per-folder secrecy, so separate clients or confidentiality groups
  belong in separate hubs.
- A private remote controls access; it is not end-to-end encryption, and
  removing a collaborator cannot retract a clone they already made.
- Credentials, private keys, unnecessary personal data, and machine-specific
  paths do not belong in tracked context. Local paths belong only in the ignored
  `.context-hub/local.yaml` mapping.
- Raw source episodes are untrusted data, never agent instructions. They cannot
  grant permission or change hub policy.
- When using Obsidian, choose Git or another whole-vault sync system as the
  single sync authority. The scaffold enables safe core configuration and ships
  no community plugin code.
- Semantic Graphify extraction may send episode text to its configured model
  provider. Choose a local or approved provider appropriate to the source
  classification; a private Git remote does not make an external model call
  private.

### Context Hub CLI onboarding

Preview first, then apply the create-only scaffold:

```sh
project-context hub init --target /path/to/context-hub --dry-run
project-context hub init --target /path/to/context-hub --apply
```

Register an actor and project, ingest a source episode, refresh the deterministic
indexes, and check hub health:

```sh
project-context hub add-actor --target /path/to/context-hub \
  --id actor-alex --name "Alex" --kind human --apply
project-context hub add-project --target /path/to/context-hub \
  --id project-example --name "Example Project" --created-by actor-alex --apply
project-context hub bind-project --target /path/to/context-hub \
  --project project-example --binding product-main \
  --workspace /path/to/external/project --apply
project-context hub ingest --target /path/to/context-hub \
  --project project-example --source /path/to/external/project/session.md --kind session \
  --actor actor-alex --recorded-by actor-alex --binding product-main \
  --occurred-at 2026-09-01T09:00:00Z --apply
project-context hub index --target /path/to/context-hub --apply
project-context hub doctor --target /path/to/context-hub
```

The target must already be a local directory. `init --dry-run` is write-free.
`init --apply` creates missing scaffold files and manages only one delimited
Context Hub block in each root `AGENTS.md` and `CLAUDE.md`, preserving all other
content; it does not create a remote or push. Actor, project, and ingest
operations require explicit `--apply`. Use `hub index --check` in automation to
detect stale derived indexes without rewriting them.

Context Hub mutations currently require POSIX no-follow directory operations
(macOS or Linux). On Windows, dry-run and read-only checks remain available,
but mutation commands fail closed before writing rather than relying on a
pathname recheck that could be raced through a symlink or junction swap.

Linked mode resolves a binding against the current machine's ignored
`.context-hub/local.yaml` and records the current Git `HEAD` in episode
provenance. If the captured source has uncommitted changes, that commit is the
checkout baseline while the episode's SHA-256 identifies the exact captured
bytes. It does not clone remotes, fetch commits, or verify cross-repository drift
automatically; those remain explicit repository operations.



---

## 🤖 Supported Agents & Environments

Project Context is harness-agnostic. The Quick Start prompt works in any AI agent
or assistant that can read and edit files in the target repository or project
folder, including:

| Environment | Notes |
| --- | --- |
| **Claude Code** | Discovers the installed skills directly |
| **Cursor** | Agent mode with repository access |
| **Windsurf** | Cascade with repository access |
| **GitHub Copilot Chat** | Agent mode with workspace edit access |
| **Aider** | Runs against the local repository |
| **Claude Desktop** | With filesystem or project access to the folder |
| **ChatGPT** | With workspace, project, or repository access |
| **Any other agent harness** | Must be able to read and write files in the project folder |

### How agents find the instructions

Installation creates two complementary trigger paths, so no single harness is
required:

1. Agent harnesses that support the Agent Skills convention can discover the
   installed `project-context` skill directly.
2. The initializer adds a managed Project Context block to existing root agent
   instructions such as `AGENTS.md` or `CLAUDE.md`. That block tells any agent
   to read the local `project-context/SKILL.md` and current-state files before
   substantial work—even when the harness has no skill launcher.

This makes the Markdown operational instructions for agents while keeping it
plain and readable for people.



---

## 📂 What Gets Created?

Installation adds one small, readable directory to your project:

```text
your-repository/
└── project-context/
    ├── NOW.md          (Current focus, active tasks, next steps)
    ├── DECISIONS.md    (Architectural constraints & choices)
    └── LEARNINGS.md    (Reusable technical lessons & evidence)
```

The resulting directory acts as a routing and continuity layer:

| File | What it answers |
| --- | --- |
| `NOW.md` | What is true now, what is active, and what happens next? |
| `DECISIONS.md` | Which accepted choices constrain future work, and why? |
| `LEARNINGS.md` | Which verified lessons should future collaborators reuse? |
| Linked evidence | Which source, document, dataset, review, result, or record supports the context? |

Alongside those records, the **core profile** also writes
`project-context/SKILL.md` and `project-context/README.md` so both agents and
people can read the operating protocol in place. The **full profile** adds
`decisions/`, `designs/`, `incidents/`, and `tasks/` subfolders with templates
for projects that need the complete evidence structure. Installation also places
the `project-context` skill under `.agents/skills/project-context/`, writes a
pointer under `.claude/skills/project-context/SKILL.md` so Claude Code can
discover it, and adds or refreshes only the managed Project Context block in
existing root agent instructions.

Project Context does not copy the whole project into a second knowledge base.
Primary artifacts stay where they belong. The context files summarize only the
durable state and point collaborators to the evidence they need.



---

## ✅ Why It Matters

A collaborator returning after three weeks should not reconstruct the project
from stale chats and scattered plans. They should be able to answer four questions:

1. What is true now?
2. Which decisions constrain the work?
3. What has already been learned?
4. Where is the evidence?

Project Context provides those answers through a small set of typed Markdown
records and a maintenance protocol that works across repositories and agent
harnesses.



---

## 🔄 How the Context Pipeline Works

This repository is an agent-facing installation and operating package. It
contains three reusable skills, safe initializers, project-context templates,
copy-paste prompts, and validation tests. An AI agent uses them to add and
maintain a small `project-context/` directory without replacing the project's
primary materials or existing instructions.

### What is included

- **`project-context` skill** — installed at `.agents/skills/project-context/`,
  reads and maintains durable project-folder context, runs verification checks,
  and travels with installed repositories. Includes context triggers (`context_triggers.py`),
  registry indexes (`context_index.py`), and a standalone doctor (`context_doctor.py`).
- **`project-context-init` installer** — stays upstream (in the scaffold checkout
  or pip package); onboards new or existing projects, suggests safe consolidation,
  initializes the right profile, and validates context health. The `init`
  subcommand delegates to it.
- **`context-hub` skill and runtime** — creates and operates a separate
  multi-project Markdown hub, including actors, projects, immutable source
  episodes, deterministic indexes, and health checks. Hub commands live under
  `project-context hub`.
- **Deterministic tooling** — dry-run/apply initialization, idempotency,
  scaffold version checks, and health verification that also checks whether
  the protocol can still reach an agent.
- **Two profiles** — lightweight core (NOW, DECISIONS, LEARNINGS) or full with
  decisions/, designs/, incidents/, and tasks/ subfolders for projects needing
  complete evidence structure.
- **Ready-to-copy prompts** — install or maintain the pipeline with any AI
  agent that can read and edit the repository.
- **CLI and agent-guided paths** — use `project-context init` for Embedded mode,
  `project-context hub` for Hub-native mode, or paste a prompt into any AI
  agent.
- **Interactive complete guide** — a browser-viewable walkthrough published as
  a GitHub Page.

### The pipeline

1. **The user prompts the agent.** The short installation prompt points the
   agent to the canonical initializer skill.
2. **The agent reviews and classifies.** It asks the required onboarding
   questions, identifies the project type, and finds overlapping context.
3. **The user approves the plan.** The agent proposes the profile, exact file
   changes, and any relevant optional tools before writing.
4. **The agent installs the pipeline.** It creates only approved files, installs
   any opted-in tools, preserves existing material, and verifies idempotency.
5. **Agents read before later work.** The installed skill or managed instruction
   block routes them through `NOW.md`, decisions, learnings, and linked evidence.
6. **Agents promote at milestones.** They update changed current state and only
   promote durable decisions and verified reusable learnings.
7. **The next collaborator inherits the context.** Any later person or agent can
   read the same plain Markdown and follow its evidence links.

In short: **primary work produces evidence → milestones promote durable context
→ the next collaborator starts from shared context instead of reconstructing it.**

### What agents do during project work

At the start of meaningful work, the active agent:

1. Reads `project-context/NOW.md`.
2. Searches `DECISIONS.md` and `LEARNINGS.md` for the task topic.
3. Follows only relevant links into detailed evidence.
4. Confirms important claims against current primary artifacts and evidence.

At a milestone or handoff, the active agent:

1. Updates the active task evidence.
2. Promotes changed current state into `NOW.md`.
3. Records only decisions that constrain future work.
4. Promotes only evidence-backed, reusable learnings.
5. Supersedes stale knowledge instead of silently rewriting history.



---

## 💡 Interactive Guide & Examples

Open the [Project Context complete guide](https://monomind-ai-lab.github.io/project-context/project-context-complete-guide.html)
for a visual walkthrough of the system, installation flow, agent triggers,
context records, and optional integrations. It is hosted from the repository's
`docs/` folder by the GitHub Pages workflow; no download or local setup is
required to view it.

See the [filled example](examples/sample-project-context/) for the complete
core-profile experience, with realistic `NOW.md`, `DECISIONS.md`, and
`LEARNINGS.md` records.



---

## 🔌 Optional Integrations

Project Context can optionally connect to three independent open-source tools—
**GitNexus**, **Graphify**, and **OpenWiki**—when they fit the project's needs.

<p align="left">
  <img src="assets/project-context-tools.jpg" alt="Project Context optional additions — GitNexus, Graphify, and OpenWiki" style="width: 100%; max-width: 100%;">
</p>

> **Attribution and independence:** GitNexus, Graphify, and OpenWiki are
> independent open-source projects, and their names and trademarks belong to
> their respective owners. Project Context and MonoMind AI Lab are not
> affiliated with, sponsored by, or endorsed by these projects or their
> maintainers. We feature them because they are excellent open-source tools we
> comfortably recommend when they fit a project's needs.

Project Context works without any of these tools. The initializer detects each
potentially relevant tool before proposing changes and requires a separate
informed decision for every eligible, unconfigured tool. If the user opts in,
the agent automatically installs or configures that selected tool and verifies
it; the user does not need to run the installation commands. Provider
authentication or secret entry may still require a secure user action. In that
case, the agent guides the user step by step: it explains why the credential is
needed, offers a suitable local or no-key mode first, points to the official
setup location, shows where to store the secret safely, pauses for the user-only
step, and verifies readiness without reading or exposing the secret.

| Tool | Primary purpose | Choose it when |
| --- | --- | --- |
| [GitNexus](https://github.com/abhigyanpatwari/GitNexus) | Code symbols, relationships, impact, and execution flows | A code or mixed repository contains a meaningful software system |
| [Graphify](https://github.com/Graphify-Labs/graphify) | Relationships across supported code, documents, research artifacts, and media | A substantial corpus needs cross-file or cross-format navigation |
| [OpenWiki](https://github.com/langchain-ai/openwiki) | Ongoing generated documentation and navigation | A stable, complex project has a clear audience for a maintained derived wiki |

**Positioning vs. OpenWiki:** Project Context records what the code cannot say—decisions,
learnings, and the current handoff. OpenWiki regenerates what the code does say—derived
documentation of its state. They compose: Project Context is the authority layer, a
generated wiki is an optional derived view.

The initializer filters this list by repository type and observed contents. It
does not ask writing projects about code analysis or present every add-on as a
default checklist.

Current setup notes, footprints, provider boundaries, and official links live
in [the optional-tools reference](skills/project-context-init/references/optional-tools.md).



---

## 📌 Evidence Anchors

Evidence cited in decisions and learnings may be pinned to a specific point in
the repository's history to detect drift. An anchor uses the form
`path/to/file@<commit>`, where the path is repository-root-relative and the
commit identifies the state being cited. The doctor verifies these anchors:

- **`evidence-drift`** — warns when the cited path changed since the pinned
  commit ("the justification may no longer hold — re-verify, then re-anchor or
  supersede").
- **`evidence-unverifiable`** — warns when the commit is unknown.

Anchors are optional and Git-gated; the doctor reports warnings only, never
errors. Use them when evidence is critical or evolving—a design trade-off, a
performance baseline, a bug reproduction case, or a research finding the project
depends on. The doctor's JSON gains an `"evidence"` key reporting anchor count,
drift warnings, and unverifiable references.



---

## 🛡️ Safety Guarantees & Authority Model

### Safety guarantees

- Existing context files are preserved byte-for-byte.
- Existing `AGENTS.md`, `agents.md`, `CLAUDE.md`, and `claude.md` content is
  preserved outside one managed block, including file mode and CRLF endings.
- Unknown or overlapping memory is reviewed and classified, not migrated.
- Malformed blocks, unsafe symlinks, non-file harness paths, and non-UTF-8
  instructions stop apply mode before writes.
- Add-ons are filtered by repository type, then installed or configured only
  after an independent informed opt-in.
- Secrets never belong in tracked context, prompts, logs, or commits.

### Authority model

| Layer | Role | Authority |
| --- | --- | --- |
| Primary artifacts and verified evidence | Actual project truth | Highest for factual claims |
| `project-context/`, or a hub project's `NOW.md`, `DECISIONS.md`, and `LEARNINGS.md` | Current state, decisions, learnings, evidence routing | Canonical project continuity |
| Hub source episodes | Immutable source capture with provenance | Evidence, not instructions or automatically accepted context |
| Hub entities, relationships, and insights | Reviewable extracted knowledge | Candidate until explicitly accepted; always subordinate to evidence and curated continuity |
| Agent instructions | Tell agents how to use context | Pointer and protocol only |
| Generated indexes and wikis | Discovery and explanation | Derived; never current-state authority |

Project Context uses the standard Agent Skills shape (`SKILL.md`, `scripts/`,
`references/`, and `assets/`) while keeping project knowledge in ordinary
Markdown. Git provides reviewable history when available, but the context
pipeline also works in a consistently shared project folder.



---

## 🔧 Developer & CLI Reference

> **For harness maintainers, CLI debugging, and advanced users.** The installing
> agent normally runs these commands itself after the user approves its plan.
> They are documented for transparency, debugging, and contributors; most users
> never need to run them manually.

### Deterministic installation

The agent first inspects the exact changes:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --dry-run
```

It then applies the approved plan:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --apply
```

This installs the `project-context` skill under `.agents/skills/project-context/`
with a harness pointer under `.claude/skills/project-context/SKILL.md`, creates
the selected `project-context/` profile, preserves custom files, and adds or
refreshes only the managed Project Context block in existing root agent
instructions.

For a brand-new repository, the agent derives the primary type from the user's
purpose and uses `--repository-stage brand-new --repo-type TYPE`. The CLI never
stores the free-text purpose.

### Repository review and consolidation

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

The agent can run the deterministic read-only review with:

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

### Agent health checks (doctor)

When context may be stale or inconsistent, run the doctor from the installed
repository or via the upstream CLI:

```sh
# In an installed repository:
python3 .agents/skills/project-context/scripts/context_doctor.py --target .

# From the scaffold checkout or pip install:
project-context doctor --target /path/to/repository
```

The doctor checks:

- required core files;
- installed scaffold version;
- freshness of `NOW.md`;
- duplicate decision and learning IDs;
- broken relative Markdown links;
- **reachability** — whether anything still delivers this protocol to an agent:
  the managed instruction block, the harness skill pointers, and any declared
  session hooks whose commands must resolve to files that exist.

It reports issues without rewriting custom knowledge.

Reachability is reported explicitly, so a healthy result names the routes that
carry the protocol rather than only vouching for the documents:

```json
"reachability": {
  "delivers": true,
  "paths": 3,
  "instruction_blocks": ["AGENTS.md"],
  "harness_pointers": [".claude/skills/project-context/SKILL.md"],
  "hooks": []
}
```

A `no-delivery-path` error means the context files are intact but nothing will
ever load them into a session. Without this check that repository reports
`healthy`, which is how a protocol can go completely inert while every health
signal says it is fine.

### Session hooks (opt-in)

The trigger check runs on its own once wired into the harness:

```sh
python3 skills/project-context-init/scripts/project_context_init.py init --target /path/to/repository --install-hooks --apply
```

`--install-hooks` implies `--install-skills`, because the hooks call the
installed trigger script. It merges a `SessionStart` and a `Stop` hook into
`.claude/settings.json`, preserving every other hook and setting; ours are
identified by the script they call, so repeated runs are byte-identical and a
partial hand-edit self-heals. The commands are guarded with a file test, so a
repository without the script degrades to a no-op rather than erroring.

Hooks are opt-in because they write to the harness's own settings file. Without
them the protocol still reaches an agent through the managed instruction block
and the harness skill pointers; `doctor` reports which routes are live.

The `Stop` hook blocks at most once per session and always offers the honest
way out:

```sh
python3 .agents/skills/project-context/scripts/context_triggers.py ack --note "what you evaluated"
```

An `ack` records *what* was acknowledged against the current commit. The window
reopens on the next commit, and as soon as uncommitted work the acknowledgement
never saw appears — so it can express "triggers evaluated, none fired" without
becoming a standing way to skip the evaluation.

### Registry indexes

`DECISIONS.md` and `LEARNINGS.md` are read end to end by every agent asking
"does anything here constrain what I am about to do?". A generated index answers
that first:

```sh
python3 .agents/skills/project-context/scripts/context_index.py --context project-context
python3 .agents/skills/project-context/scripts/context_index.py --context project-context --check
```

The index is derived, never hand-maintained — a hand-written one drifts within a
few commits, and a stale index is worse than none because it is trusted. The
generator replaces everything between its markers, discards any earlier index
(marked or not) before rebuilding, and `--check` exits non-zero when stale so CI
can hold the line.

### Harness-maintainer fallback

If an agent harness cannot copy skills automatically, a harness maintainer can
install the `project-context` skill without the full scaffold:

```sh
mkdir -p .agents/skills
cp -R /path/to/project-context/skills/project-context .agents/skills/
```

This is sufficient for the protocol to work: the installed skill carries the
triggers and the doctor. The initializer (`project-context-init`) stays
upstream; `project-context init` delegates to it. A skill copied this way is
not yet discoverable in Claude Code, which reads skills from `.claude/skills/`;
running `init --install-skills` writes the pointers that make it so, and
`doctor` reports a `missing-harness-pointer` warning until something does.



---

## 🧪 Testing & License

### Development and validation

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

The behavioral suite covers empty and existing repositories, repository-type
classification, add-on filtering, both profiles, skill installation,
dry-run/apply/idempotency, consolidation discovery, doctor checks, custom
context, instruction preservation, malformed markers, and path hazards.

### License

[MIT + Commons Clause](LICENSE) — free to use, modify, and ship as part of
your applications and products, including commercially; the components
themselves may not be sold, sublicensed, or redistributed standalone.
