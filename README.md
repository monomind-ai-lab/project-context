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

It works with software, document, research, writing, and mixed projects. It is
best suited to repo-bound collaborative projects, where version control makes
shared context easy to review and evolve, but it also works well for any project
whose working materials are organized in one folder that people and AI agents
can access consistently.

Project Context is **agent-operated and human-readable**. People provide intent,
answer onboarding and opt-in questions, and approve proposed changes. Agents
read the skills and Markdown instructions, run the tooling, maintain the context
files, and verify the result. Humans can review or edit the Markdown at any time,
but they are not expected to invoke skills or run Python commands themselves.



---

## 🚀 Quick Start (30 Seconds)

**No skill launcher, Python runtime, or manual setup is required for the
agent-guided path.** You do not install Project Context yourself—your AI agent
does. Paste one prompt, answer a short onboarding question, and approve the plan
the agent proposes.

Copy this prompt into any AI agent that can read and edit your target repository
or project folder:

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
   installed `project-context` and `project-context-init` skills directly.
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
both skills under `.agents/skills/`, writes a thin pointer for each under
`.claude/skills/` so Claude Code can discover them, and adds or refreshes only
the managed Project Context block in existing root agent instructions.

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
contains two reusable skills, a safe initializer, project-context templates,
copy-paste prompts, and validation tests. An AI agent uses them to add and
maintain a small `project-context/` directory without replacing the project's
primary materials or existing instructions.

### What is included

- **`project-context-init`** — onboards a new or existing project, suggests safe
  consolidation, initializes the right profile, and validates context health.
- **`project-context`** — reads and maintains durable project-folder context.
- **Deterministic tooling** — dry-run/apply initialization, idempotency,
  scaffold version checks, and a read-only doctor.
- **Two profiles** — lightweight adoption or full evidence structure.
- **Two ready-to-copy prompts** — install or maintain the pipeline with any AI
  agent that can read and edit the repository.
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

The initializer filters this list by repository type and observed contents. It
does not ask writing projects about code analysis or present every add-on as a
default checklist.

Current setup notes, footprints, provider boundaries, and official links live
in [the optional-tools reference](skills/project-context-init/references/optional-tools.md).



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
| `project-context/` | Current state, decisions, learnings, evidence routing | Canonical project continuity |
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

This installs both skills under `.agents/skills/` with harness pointers under
`.claude/skills/`, creates the selected `project-context/` profile, preserves
custom files, and adds or refreshes only the managed Project Context block in
existing root agent instructions.

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

When context may be stale or inconsistent, the agent runs:

```sh
python3 skills/project-context-init/scripts/project_context_init.py doctor --target /path/to/repository
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

### Harness-maintainer fallback

If an agent harness cannot copy skills automatically, a harness maintainer can
install only the skills without the scaffold:

```sh
mkdir -p .agents/skills
cp -R /path/to/project-context/skills/project-context .agents/skills/
cp -R /path/to/project-context/skills/project-context-init .agents/skills/
```

Then invoke `$project-context-init` in the target repository. A skill copied
this way is not yet discoverable in Claude Code, which reads skills from
`.claude/skills/`; running `init --install-skills` writes the pointers that
make it so, and `doctor` reports a `missing-harness-pointer` warning until
something does.



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

[MIT](LICENSE)
