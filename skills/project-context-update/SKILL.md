---
name: project-context-update
description: Use when asked to check for a newer Project Context release, to upgrade an installed scaffold, or to review what a release would change in a repository that already contains project-context/ — including deciding what to do about files the project has adapted locally.
allowed-tools: Read, Glob, Grep, Bash
---

# Update Project Context

Move an installed scaffold to a newer release without overwriting what this
project has since adapted. An installed scaffold is normally two things at once:
files that arrived from a release untouched, and files the project has changed
on purpose. Only the first kind is safe to replace.

This skill never edits `NOW.md`, `DECISIONS.md`, or `LEARNINGS.md`. Those are the
project's own record, not scaffold files, and no release supersedes them.

## 1. Check before proposing anything

```sh
python3 PATH_TO_SKILL/scripts/project_context_update.py check --target .
```

Reports `current`, `update-available`, `unknown-install`, or `unavailable`, with
the installed `template_version` and the latest published release. Stop here when
the answer is `current` — say so plainly rather than proposing work.

`unavailable` means the release feed could not be reached. That is a network
result, not evidence that no update exists; do not report it as "up to date".

## 2. Read what the release actually changes

Fetch the release notes for the offered tag and summarize them for the user
before any file is touched. An upgrade the user cannot describe is one they
cannot meaningfully approve.

## 3. Plan, and show the plan

```sh
python3 PATH_TO_SKILL/scripts/project_context_update.py plan --target .
```

Every scaffold file is compared three ways — as installed, as it was in the
release the install came from, and as it is in the release being offered:

| State | Meaning | Handled by |
| --- | --- | --- |
| `same` | Already identical to the offered release | Nothing to do |
| `create` | New in this release, absent here | Safe write |
| `update` | Still identical to the installed release | Safe write |
| `conflict` | Changed locally since the installed release | The user decides |
| `review` | No baseline release to compare against | The user decides |

Present the counts, then name every `conflict` and `review` path individually.
Those are the only interesting rows: they are where this project deliberately
diverged, and replacing one silently would discard a decision somebody made.

A `core` install stays `core`. The full profile's evidence folders are never
added by an upgrade; adopting them is a separate, deliberate choice.

## 4. Apply only what was approved

```sh
python3 PATH_TO_SKILL/scripts/project_context_update.py apply --target .
```

Writes only the `create` and `update` rows, then records the new
`template_version`. It never resolves a conflict on its own.

Prefer a clean working tree so the upgrade lands as a reviewable diff. If the
tree is dirty, say so and let the user decide whether to continue.

## 5. Resolve conflicts deliberately

For each conflicting file, read both versions and tell the user what diverged
and why it matters. Then let them choose: keep the local version, take the
release version, or merge specific changes. Never guess on their behalf.

When a local change exists because the scaffold lacked something the release now
provides, the local layer has served its purpose — recommend retiring it, and
record that in `DECISIONS.md` as a superseding decision rather than a silent
deletion.

## 6. Verify and report

```sh
python3 PATH_TO_SKILL/scripts/project_context_init.py doctor --target .
git diff
```

Report what moved, what was left alone and why, and any conflict still awaiting
a decision. Committing is the user's call.

## Never

- Overwrite `NOW.md`, `DECISIONS.md`, or `LEARNINGS.md`.
- Replace a `conflict` file without explicit approval for that file.
- Promote a `core` install to `full`.
- Report `unavailable` as though it meant up to date.
- Push anything back to the scaffold repository. Updates flow one way: from the
  release into the project.
