# Project Context

<p align="left">
  <img src="assets/project-context-cover.jpg" alt="Project Context — Clarity Comes With Context" style="width: 100%; max-width: 100%;">
</p>

> **Shared project context that outlives any one person, agent, or chat.**

Project Context is a simple way to build a context pipeline right into a
repository or project folder. It is best suited to repo-bound collaborative
projects, where version control makes shared context easy to review and evolve.
But it also works well for any project whose working materials are organized in
one folder that people and AI agents can access consistently.

It works with software, document, research, writing, and mixed projects. As
work produces evidence, milestones promote the current state, durable decisions,
and verified learnings into small Markdown files—Git-tracked when version
control is available. Unlike chat history, proprietary memory, or generated
documentation, that context stays portable across collaborators and tools—and
remains owned by the project.

Project Context is **agent-operated and human-readable**. People provide intent,
answer onboarding and opt-in questions, and approve proposed changes. Agents
read the skills and Markdown instructions, run the tooling, maintain the context
files, and verify the result. Humans can review or edit the Markdown at any time,
but they are not expected to invoke skills or run Python commands themselves.



---

## ✅ Why it matters

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



---

## ✅ What this repository does

This repository is an agent-facing installation and operating package. It
contains two reusable skills, a safe initializer, project-context templates,
copy-paste prompts, and validation tests. An AI agent uses them to add and
maintain a small `project-context/` directory without replacing the project's
primary materials or existing instructions.



---

### How agents find the instructions

Installation creates two complementary trigger paths:

1. Agent harnesses that support the Agent Skills convention can discover the
   installed `project-context` and `project-context-init` skills directly.
2. The initializer adds a managed Project Context block to existing root agent
   instructions such as `AGENTS.md` or `CLAUDE.md`. That block tells any agent
   to read the local `project-context/SKILL.md` and current-state files before
   substantial work—even when the harness has no skill launcher.

This makes the Markdown operational instructions for agents while keeping it
plain and readable for people.

The resulting directory acts as a routing and continuity layer:

| File | What it answers |
| --- | --- |
| `NOW.md` | What is true now, what is active, and what happens next? |
| `DECISIONS.md` | Which accepted choices constrain future work, and why? |
| `LEARNINGS.md` | Which verified lessons should future collaborators reuse? |
| Linked evidence | Which source, document, dataset, review, result, or record supports the context? |

Project Context does not copy the whole project into a second knowledge base.
Primary artifacts stay where they belong. The context files summarize only the
durable state and point collaborators to the evidence they need.

### How the context pipeline works

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

## ✅ Interactive guide

Open the [Project Context complete guide](https://monomind-ai-lab.github.io/project-context/project-context-complete-guide.html)
for a visual walkthrough of the system, installation flow, agent triggers,
context records, and optional integrations. It is hosted from the repository's
`docs/` folder by the GitHub Pages workflow; no download or local setup is
required to view it.

## ✅ What is included

- **`project-context-init`** — onboards a new or existing project, suggests safe
  consolidation, initializes the right profile, and validates context health.
- **`project-context`** — reads and maintains durable project-folder context.
- **`project-context-update`** — checks for a newer release and pulls it in
  without overwriting what the project has adapted.
- **Deterministic tooling** — dry-run/apply initialization, idempotency,
  scaffold version checks, and a read-only doctor.
- **Two profiles** — lightweight adoption or full evidence structure.
- **Two ready-to-copy prompts** — install or maintain the pipeline with any AI
  agent that can read and edit the repository.
- **Interactive complete guide** — a browser-viewable walkthrough published as
  a GitHub Page.


---

## ✅ The skills

Project Context ships three skills. One is loaded by agents on their own; the
other two exist for you to ask for.

| Skill | What it does | When it runs |
| --- | --- | --- |
| **`project-context`** | The operating protocol. What to read before work, and how to keep current state, decisions, learnings, and evidence links maintained. | **On its own.** An agent loads it before substantial work in a project that has `project-context/`, and maintains the files as milestones and handoffs happen. You never invoke it. |
| **`project-context-init`** | Installs, adopts, reviews, repairs, and health-checks the pipeline. Classifies the project, proposes a create-only plan, and waits for approval. | **When you ask.** Setting it up in a new project, adopting it in an existing one, or checking health when context looks stale or contradictory. |
| **`project-context-update`** | Checks whether a newer release exists and, once you approve, pulls it in — replacing only files this project has not adapted. | **When you ask.** After a release lands, or any time you want to know whether the scaffold has moved on. |

### How agents reach them

Harnesses that support the Agent Skills convention discover the installed skills
directly. Everything else follows the managed block that installation adds to
`AGENTS.md` or `CLAUDE.md`, which points at `project-context/SKILL.md`. Both
paths lead to the same instructions, so no harness is a special case.

### What you actually type

You do not run Python or memorize command names. Ask in plain language:

- *"Install Project Context here"* — or paste the installation prompt below.
- *"Check whether Project Context has a newer release"* — runs
  `project-context-update`, which reports before it proposes anything.
- *"Run the Project Context doctor"* — runs the read-only health check in
  `project-context-init`.

The third skill is the one you will never need to ask for: maintaining the
context files is part of how an agent works in the project, not a separate
request.


---

## ✅ Install with any AI agent

No skill launcher or Python runtime is required for the agent-guided path. Copy
the prompt below into an AI agent that can access the target repository or
project folder. The agent starts by asking whether the repository is brand-new,
then adapts the pipeline to software, documents, research, writing, mixed, or
general work.

```text
Install Project Context in the current repository or project folder using
https://github.com/monomind-ai-lab/project-context. Read and follow
`skills/project-context-init/SKILL.md`, starting with its required onboarding
question. Show me the proposed plan and wait for my approval before making changes.
```

Use the [standalone installation prompt](prompts/install-project-context.md) for
an easy-to-copy version. The full behavior stays in the skill so the prompt does
not drift or duplicate instructions. After installation, the
[maintenance prompt](prompts/maintain-project-context.md) works with agents that
do not support installed skills.



---

## ✅ Agent implementation reference: deterministic CLI

The installing agent normally runs these commands after the user approves its
plan. They are documented for transparency, debugging, and contributors; most
users do not need to run them manually.

The agent first inspects the exact changes:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --dry-run
```

It then applies the approved plan:

```sh
python3 scripts/install.py --target /path/to/repository --profile core --repo-type auto --repository-stage existing --apply
```

This installs both skills under `.agents/skills/`, creates the selected
`project-context/` profile, preserves custom files, and adds or refreshes only
the managed Project Context block in existing root agent instructions.

For a brand-new repository, the agent derives the primary type from the user's
purpose and uses `--repository-stage brand-new --repo-type TYPE`. The CLI never
stores the free-text purpose.



---

## ✅ Repository review and consolidation

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



---

## ✅ Agent health checks

When context may be stale or inconsistent, the agent runs:

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



---

## ✅ What agents do during project work

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

## ✅ Authority model

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

## Optional integrations: GitNexus, Graphify, and OpenWiki

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

## ✅ Safety guarantees

- Existing context files are preserved byte-for-byte.
- Existing `AGENTS.md`, `agents.md`, `CLAUDE.md`, and `claude.md` content is
  preserved outside one managed block, including file mode and CRLF endings.
- Unknown or overlapping memory is reviewed and classified, not migrated.
- Malformed blocks, unsafe symlinks, non-file harness paths, and non-UTF-8
  instructions stop apply mode before writes.
- Add-ons are filtered by repository type, then installed or configured only
  after an independent informed opt-in.
- Secrets never belong in tracked context, prompts, logs, or commits.



---

## ✅ Harness-maintainer fallback

If an agent harness cannot copy skills automatically, a harness maintainer can
install only the skills without the scaffold:

```sh
mkdir -p .agents/skills
cp -R /path/to/project-context/skills/project-context .agents/skills/
cp -R /path/to/project-context/skills/project-context-init .agents/skills/
```

Then invoke `$project-context-init` in the target repository.



---

## ✅ Development and validation

```sh
python3 -m unittest discover -s tests -v
python3 scripts/validate_repository.py
```

The behavioral suite covers empty and existing repositories, repository-type
classification, add-on filtering, both profiles, skill installation,
dry-run/apply/idempotency, consolidation discovery, doctor checks, custom
context, instruction preservation, malformed markers, and path hazards.



---

## ✅ License

[MIT](LICENSE)
