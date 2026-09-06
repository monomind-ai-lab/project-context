---
name: project-context-init
description: Use when asked to install, initialize, adopt, review, repair, or health-check Project Context in a repository or project folder, including classifying the project, consolidating overlapping context safely, or installing eligible optional add-ons after opt-in.
allowed-tools: Read, Glob, Grep, Bash
---

# Initialize Project Context

Add durable project memory without overwriting existing knowledge or harness
instructions. Project Context is a simple context pipeline inside a repository
or organized project folder: work produces evidence, milestones promote current
state and durable knowledge, and future collaborators read the same context.
Git makes that history reviewable when available, but it is not required.

## Source-link invocation

When a copy-paste prompt points to this repository, read this file and
`assets/project-context/` directly from that source before planning the install.
If the source cannot be accessed, stop and ask for a local path or copy; never
recreate the templates or workflow from memory.

## 1. Start with the repository conversation

Before profiles, commands, or add-ons, ask the questions below — one at a time,
waiting for each answer before asking the next. Nothing else is asked here.

**First:**

> Is this a brand-new repository?

- If **yes**, ask: **What will this repository primarily hold or support?** Use
  the answer only to classify it as `code`, `document`, `research`, `writing`,
  `mixed`, or `general`. Do not persist the user's free-text purpose by default.
- If **no**, do not ask what it is for. Inspect the repository and classify it
  from its contents. Use aggregate signals such as manifests/source files,
  documentation formats, bibliographies/data/notebooks, or manuscripts/drafts.
  Report the proposed type and confidence; ask for correction only when the
  result is ambiguous or `mixed` would change the setup.

Repository type guides recommendations, not authority. A mixed repository may
need different evidence paths for different artifact families.

### Then ask where the records should live

> Should these records be committed to this repository?

This decides `--placement`, and it is the only question in the install whose
wrong answer cannot be fixed by re-running anything: records that were never
committed have no history to recover. Put the trade in front of the user rather
than reading them three nouns.

| Answer | `--placement` | When it is right |
| --- | --- | --- |
| Yes — this is the normal case | `in-repo` (**default**) | Almost always. The records are versioned, reviewable in a pull request, and every collaborator and agent gets them by cloning. This is the product working as designed |
| No, and they do not need to be shared | `local-only` | A public repository whose context is genuinely internal, or a spike not ready to share. The folder is created in the working tree and `/project-context/` is added to `.gitignore` |
| No, but they must still be versioned and shared | `private-sibling` | The folder is gitignored here and kept as its own git repository with its own private remote. Context that must stay off a public history and still have a history of its own |

If the user has no opinion, use `in-repo` and say that is what you are doing.

Say the cost of `local-only` plainly, every time it is chosen: no version
history, no sharing, no backup, and a fresh clone starts cold. If the reason
given is that the repository is public, recommend `private-sibling` directly —
it is usually what the person actually wants, and it keeps everything
`local-only` gives up.

`private-sibling` manages no remote. The installer does not run `git init`, does
not add a remote, and does not clone; it records the choice and writes the
ignore rule. Tell the user the remaining steps are theirs: `git -C
project-context init`, commit the scaffold, then add the private remote. Do not
create that repository or configure a remote without separate explicit
authorization.

A repository installed before this choice existed has no `placement` key in its
marker; that means `in-repo`, and neither `init` nor `update` rewrites it.

## 2. Inspect before proposing changes

When Python 3 is available, use the deterministic read-only inspection:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py inspect --target . --repo-type auto
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --repo-type TYPE --repository-stage STAGE --placement PLACEMENT --dry-run
```

For a new repository, pass the type derived from the purpose and
`--repository-stage brand-new`. For an existing repository, pass the confirmed
or inferred type and `--repository-stage existing`. Pass the placement the user
chose; omitting it means `in-repo`.

The dry run enumerates the `.gitignore` edit like every other planned change,
so show it before applying. `already_ignored` means an existing rule already
covers the folder and nothing will be added. The report's `placement` block
carries the choice, its cost, and — for `private-sibling` — the steps the
installer deliberately leaves to the user.

If Python is unavailable, perform the same workflow manually: inventory only
root instructions and likely context material, compare against
`assets/project-context/`, propose exact create-only changes, and wait for
approval. Do not claim deterministic scanning, idempotency, or doctor results
when they were not run.

The proposed plan must enumerate every root instruction file it would create or
modify. Do not touch an instruction file unless it appears in the approved plan.

If a managed block is malformed or duplicated, stop. Never repair unknown
surrounding instructions automatically.

## 3. Review possible consolidation

For an existing repository, or a new repository where inspection found prior
material, run:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py consolidate --target . --repo-type TYPE
```

This subcommand was called `review` before the assembler landed. `review` now
names the standing "what is waiting on a person?" report, which is a different
question and one asked for the life of the project rather than once at adoption.

## Carrying an existing install forward

For a repository that already has Project Context and needs the current
release — new scripts, a refreshed protocol text, scaffold files added since it
was installed:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py update --target . --dry-run
python3 PATH_TO_SKILL/scripts/project_context_init.py update --target . --apply
```

Local only; nothing in it reaches a network. It refuses a repository with no
install and tells you to run `init`.

Read the dry run before applying, and read it by authorship. `refresh` and
`regenerate_index` are files this product owns. `create` is a scaffold file the
install predates. `preserve_existing` is a record the repository wrote, and
seeing one is the command working correctly — never talk a user into
overwriting it. The pushed set is reported, never planned: a
`pushed-file-modified` entry means someone edited a copy the Hub sent, and the
fix is a question in `QUESTIONS.md`, not an edit here.

Names are discovery signals, not proof. Read only the candidate material needed
to assess overlap. For each candidate:

- summarize purpose, authority, freshness, and provenance;
- map reusable material to current state, decisions, learnings, tasks, designs,
  or incidents;
- identify conflicts, duplicates, and material that should stay where it is;
- propose keep-and-link, copy-with-provenance, or deliberate migration;
- explain what would become canonical and what remains historical.

Source papers, datasets, manuscripts, drafts, and primary project artifacts are
normally evidence to link, not context to migrate. Never move, merge, rewrite,
archive, or delete without separate explicit authorization.

## 4. Choose a profile and apply

- `core` creates `README.md`, `SKILL.md`, `NOW.md`, `DECISIONS.md`, and
  `LEARNINGS.md`. It is the universal default, and the default of `--profile`.
- `full` also creates task, design, and incident evidence folders. Offer it when
  the collaboration genuinely benefits from those record types; do not infer it
  merely from repository type.

After approval of the exact plan:

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py init --target . --profile core --repo-type TYPE --repository-stage STAGE --placement PLACEMENT --apply
```

The script creates only missing files, records the schema, the package version,
the project id, the repository type, and the placement in
`project-context/.project-context.json`,
preserves differing files, and updates only its managed block in existing root
`AGENTS.md`, `agents.md`, `CLAUDE.md`, or `claude.md`. It ensures **both** root
instruction files carry that block, creating whichever is missing, so a
Claude-only repository does not end up with rules no Claude session reads; an
existing lowercase `agents.md` or `claude.md` satisfies its role and no second
file is created. `--install-skills`
copies the `project-context` skill alone into `.agents/skills/` with the same
preserve-existing rules, and writes a thin pointer for it under `.claude/skills/`
so Claude Code can discover it — without that pointer the skill is installed but
invisible, and the managed block is the only route left. This initializer skill
is not installed: it stays in the Project Context checkout, so a consuming
repository never carries the installer or a second copy of the templates.

`project-context/SKILL.md` is written from the `project-context` skill's own
`SKILL.md` rather than from `assets/`, so the installed instance and the harness
skill are one text that cannot drift.

`--install-hooks` additionally wires the `SessionStart` and `Stop` trigger hooks
into `.claude/settings.json`, merging with any hooks already there. It implies
`--install-skills`, because the hooks call the installed trigger script. Ask
before using it: it writes to the harness's own settings file, and the protocol
still reaches an agent without it.

For manual installation, copy only missing template files and add a Project
Context pointer only to root instruction files the user approves. Show the full
diff. Do not silently create a product-specific harness convention.

## 5. Filter advanced add-ons before asking

Read [references/optional-tools.md](references/optional-tools.md) before making
claims or running commands. Inspect reports whether each tool is configured in
the repository, merely available on `PATH`, or absent. Do not reinstall a
configured tool.

Eliminate add-ons that do not help the observed repository:

| Repository type | Add-ons worth considering |
| --- | --- |
| Code | All three. GitNexus for symbols and impact, OpenWiki's `code` mode for the repository's wiki, Graphify for cross-file relationships |
| Document | OpenWiki's `personal` mode over the corpus, and Graphify — recommended when sizable, optional when not |
| Research | OpenWiki's `personal` mode over the corpus, and Graphify — recommended when sizable, optional when not |
| Writing | Graphify only — recommended for a sizable manuscript or story world, optional for a small one |
| Mixed | Graphify only — recommended when sizable, optional when not |
| General/uncertain | Graphify only, and optional unless the project is sizable |

The matrix is an eligibility ceiling, not a prompt checklist. Suppress options
whose stated condition is not present. For each remaining unconfigured tool,
ask separately and wait. Explain its purpose, concrete benefit here, detected
state, footprint/dependencies, recommendation level, local/provider behavior,
and that declining does not affect Project Context. Authorization for one tool
never authorizes another.

## 6. Install or configure only selected tools

Use current official commands from the optional-tools reference and re-check
state immediately before changing anything. Distinguish installing a CLI from
configuring this repository. Prefer repository-scoped, least-invasive modes.

After the user explicitly opts in to a described tool and scope, perform the
approved installation or configuration automatically and verify it. Do not hand
ordinary installation commands back to the user. Ask for user action only when
the environment requires secure authentication, secret entry, or another step
the agent cannot safely perform. An opt-in does not authorize unrelated modes or
later side effects.

### Guide secure authentication step by step

When a selected mode needs a provider account, API key, token, or other secret:

1. Explain why it is needed and offer a verified local, offline, host-agent, or
   no-key mode first when one satisfies the user's goal.
2. Name the exact provider setting or environment variable and link the current
   official setup page. Never ask the user to paste the secret into chat.
3. Tell the user where to store it safely for the selected environment—such as
   an OS secret manager, tool-owned user configuration, environment variable,
   or CI secret—and explicitly warn against tracked files and shell history.
4. Give the minimum exact user-only action, explain what success looks like, and
   pause while the user completes it. Tell them how to signal that the agent can
   continue.
5. After the user confirms, verify only credential presence or a harmless
   authenticated operation. Never print, echo, log, diff, or otherwise expose
   the value. If verification fails, guide the user through diagnosis without
   requesting the secret itself.

Keep later side effects separate: GitNexus MCP/hooks/wiki, Graphify graph builds
and semantic/provider modes, and OpenWiki's first generation each need their
own appropriate authorization. Never request secrets in chat or tracked files;
use environment variables, secret managers, CI stores, or tool-owned user
configuration and verify presence without printing values.

## 7. Verify and hand off

- Re-run inspect and the same init dry-run; it should propose no writes.
- Run `doctor --target .` when Python is available; it delegates to the
  `project-context` skill's `scripts/context_doctor.py`, which the target
  repository can also run directly once the skill is installed. Confirm `reachability`
  reports at least one delivery path; a `no-delivery-path` error means the
  context files are intact but nothing will load them into a session.
- Read `placement` in the same report. A `local-only` install always warns with
  `context-not-versioned` — that is the choice being reported honestly, not a
  fault to repair. A `private-sibling` install warns with
  `sibling-not-a-repository` until `project-context/` is its own git work tree;
  that one is a real gap, and the fix is the user's `git init` and remote.
- Confirm only approved add-ons or configurations changed.
- Inspect the complete diff for private paths, credentials, sensitive data, and
  type-specific assumptions presented as universal rules.
- Summarize the repository classification, preserved material, context pipeline,
  and any consolidation candidates still awaiting a decision.
