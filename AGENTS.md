# Project Context — the contract

This is the canonical contract for any agent working **on this product**. Read
it before you read anything else here, and before you write anything at all.

Host files (`CLAUDE.md`, and any equivalent a tool needs later) are pointers to
this file. A pointer says where the contract is; it never restates a rule from
here. If a pointer and this file disagree, this file is right and the pointer is
the bug.

This repository is not itself a Project Context install. There is no
`project-context/` folder here and no records to maintain — what follows are the
rules of the product's own source tree.

## What this repository is

Project Context is agent-maintained Markdown context that lives in a project's
own repository. It ships two skills and one CLI, has **zero runtime
dependencies**, and targets Python 3.10 and later. Markdown and Git are the
whole storage contract; anything a person cannot read in a pull request does not
belong in a project's `project-context/` folder.

Its affiliated product, **Project Hub**, is a separate repository. The Hub
authors the global tier and pushes it down; a repository pulls nothing by
itself. Nothing in this tree may require a Hub to exist — a repository with no
Hub simply has no `global/` and no `blueprint/`, and every feature here still
works. That is not a degraded mode. It is the product.

## Read order

Read only what the task needs, in this order, and stop when you have enough.

1. `AGENTS.md` — this file.
2. `planning/project-context-design.md` — the design and the decision record.
   It is the authority for *why*, and the resolved decisions in Part 4 are
   binding. When code and this document disagree, say so rather than picking
   one silently.
3. `planning/record-model-v1.md` — the record model, when a task touches
   frontmatter, statuses, references, or budgets.
4. `skills/project-context/SKILL.md` — the protocol text itself.
5. The one script the task touches, and its test file beside it in `tests/`.

`planning/project-context-handoff-2026-09-03.md` is history. Read it for
context, never as current direction.

## Canonical paths

| Path | Holds | Notes |
| --- | --- | --- |
| `skills/project-context/` | The protocol skill, installed **into** consuming repositories | Its `SKILL.md` and `scripts/` must be reachable from the repository they diagnose |
| `skills/project-context-init/` | The installer, which stays in this checkout | A consuming repository never carries a copy |
| `skills/project-context-init/assets/project-context/` | The scaffold templates a repository receives | |
| `src/project_context_cli/` | The console entry point, a shim only | It loads the bundled script and forwards; it never duplicates a CLI |
| `planning/` | Design, record model, and history | |
| `web/`, `docs/` | The site source and the built guide | `scripts/build_site.py` builds it |
| `tests/` | One file per script | |

## The rules

1. **One protocol text.** `skills/project-context/SKILL.md` is the only copy.
   It is installed twice — as the harness skill and as the repository's own
   instance — and `project_context_init.py` reads that file for both. Never add
   a second copy under `assets/`; that is the drift this rule exists to
   prevent.

2. **One implementation per concern.** The doctor is
   `context_doctor.py`; the initializer loads it rather than reimplementing a
   check, and so do the assembler and the review. One report shape, one set of
   issue codes. If you need a parser that already exists, import the sibling.

3. **One version number.** `VERSION` and `pyproject.toml` must agree, and every
   script reads the package version from `VERSION` through its own
   `package_version()`. `TEMPLATE_VERSION` and `SCAFFOLD_VERSION` are retired.

4. **Standard library only.** No runtime dependency, in any script, ever. The
   validator checks this for the Hub's CLI and the discipline is the same here:
   a repository adopting this product must not acquire a dependency by doing so.

5. **We own our markers and nothing outside them.** The managed block between
   `<!-- project-context:start -->` and `<!-- project-context:end -->` is ours.
   The rest of a `CLAUDE.md` or `AGENTS.md` in a consuming repository is none of
   our business — it is full of things that have nothing to do with us, and an
   install that rewrites them is a bug however good the intent.

6. **Both instruction files, always.** An install ensures `AGENTS.md` *and*
   `CLAUDE.md` carry the block, creating whichever is missing. Updating only the
   files that happened to exist left a Claude-only repository with rules no
   Claude session ever read; the doctor's `no-delivery-path` check names
   whichever is missing.

7. **Create-only, and preview before apply.** Every command takes `--dry-run`
   and `--apply`, and `--dry-run` prints the exact plan. Nothing overwrites a
   record. A file the user may have edited is skipped and the skip is reported.

8. **Records are never rewritten.** Correct interpretation through `status` and
   supersession links. History stays.

9. **No secrets, no home paths, no machine names** in anything committed here.
   `scripts/validate_repository.py` checks for them and CI runs it.

## Before you finish

```sh
python -m unittest discover -s tests -v
python scripts/validate_repository.py
```

Both must pass; CI runs exactly these, on Python 3.10 and 3.13. A new script
under `skills/*/scripts/` needs a test file in `tests/` and an entry in the
validator's `REQUIRED`, or it ships unguarded.

Write a test that states the behaviour and the reason for it. The suite here is
written to be read: a docstring saying *why* a rule exists is what stops the
next person deleting it as noise.

## What is out of scope

Do not add an embedding index, a database, or a background service to the
repository side. Retrieval is a path-prefix comparison and a token overlap over
a few hundred small files, and it is deliberate (2.5). A derived SQLite cache is
allowed on the **Hub** side only, when a measurement — not a milestone — shows a
cross-project query is slow. See the SQLite note in Part 4 of the design.

Do not build governance into the tool. `OWNERS.md` is a record, not an
enforcement mechanism; the Git host's repository permissions are the whole
model (D3).
