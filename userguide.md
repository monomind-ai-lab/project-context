# User Guide: Multiple agents, worktrees, and branches

This guide explains how to use Project Context when several agents work in parallel across multiple worktrees and branches.

The short version:

- Project Context is a shared, repo-level memory layer.
- Branch-local work stays in branch-local task records.
- Shared project truth stays in the repo's `project-context/` directory.
- Merge time is the reconciliation point.
- Supersede and document conflicts instead of silently rewriting history.

## Why this matters

Parallel work is normal in modern coding workflows, especially when each agent gets a dedicated worktree or branch. Without a shared context protocol, agents tend to overwrite one another, duplicate assumptions, or silently disagree about current state.

Project Context is designed to prevent that. It keeps the repository's durable state readable in Markdown, while allowing each agent to keep its own branch-local task record.

## Principles

1. One repository, one shared context
   - All agents read the same `project-context/` directory.
   - Shared truth lives there only when it is intentionally updated.
   - An agent's local session memory is not repo truth.

2. Branch-local work stays branch-local
   - Each branch or agent may keep a task record under `project-context/tasks/`.
   - That record explains what the branch is doing, what is completed, and what remains.

3. Shared files are only for shared truth
   - `NOW.md`: current state, blockers, next action
   - `PLAN.md`: active plan or milestone
   - `DECISIONS.md`: durable constraints and accepted choices
   - `LEARNINGS.md`: reusable, evidence-backed lessons
   - `QUESTIONS.md`: unresolved or repo-wide ambiguities
   - `inbox/`: candidate notes that are not yet promoted

4. History is preserved, not rewritten
   - If a decision is reversed or narrowed, do not silently reword the earlier record into agreement.
   - Use status transitions and supersession links instead.

5. Merge is the reconciliation point
   - Parallel development is fine.
   - Shared context is reconciled during review or merge, not by multiple agents blindly editing the same files.

## Recommended layout

Use this layout in a repo with multiple agents:

```text
project-context/
├── NOW.md
├── PLAN.md
├── DECISIONS.md
├── LEARNINGS.md
├── QUESTIONS.md
├── inbox/
├── tasks/
│   ├── agent-a-auth-flow.md
│   ├── agent-b-cache-layer.md
│   └── agent-c-queue-fix.md
├── decisions/
├── questions/
├── designs/
├── incidents/
└── .project-context.json
```

The important split is:

- `project-context/tasks/` = branch-local or agent-local work
- `project-context/NOW.md`, `PLAN.md`, `DECISIONS.md`, `LEARNINGS.md`, `QUESTIONS.md` = shared truth
- `project-context/inbox/` = tentative notes waiting for promotion

## Working model

### Shared repo context

Use the repo-level Project Context files for facts that affect the whole project:

- What is true now
- What is active and blocking work
- Which choices constrain future work
- Which reusable learnings have been verified
- Which unresolved questions still affect the repository

Only update these when the change is genuinely repository-wide.

### Branch-local context

Each branch or agent should own a task record under `project-context/tasks/`.

Example:

```text
project-context/tasks/agent-b-cache-layer.md
```

A task file should include:

- what this branch is doing
- what is done
- what is still in progress
- any blockers or open questions
- what assumptions the branch is making
- any evidence or validation notes

This keeps parallel work visible without forcing every agent to write to the same shared files.

## What not to do

Avoid these patterns:

- Multiple agents directly editing `NOW.md` at the same time
- Multiple agents silently rewriting the same decision in different ways
- Treating local session notes as final repo truth
- Editing an old decision into agreement with a newer one without noting the supersession

If multiple branches touch the same shared file, one person or one merge steward must reconcile the final state.

## Merge steward role

In a multi-agent workflow, designate one person or one review owner to act as the merge steward.

The merge steward is responsible for:

- reviewing branch task records
- checking for conflicting shared-state changes
- reconciling `NOW.md` and `PLAN.md`
- promoting items from `inbox/`
- checking for decision conflicts and supersessions
- ensuring the repo remains readable and internally consistent

This role is coordination, not gatekeeping. The goal is readable, reviewable project context.

## Recommended workflow

### At session start

Each agent should:

1. Run the project-context packet for the files it may touch.
2. Read relevant decisions, learnings, and questions.
3. Create or update its branch task file.

Example:

```sh
project-context context --task "add retry handling to the API client" --files src/api/client.py
```

### During work

- Keep branch-local notes in `project-context/tasks/`
- Use `project-context/inbox/` for emerging insights that are not yet proven or repo-wide
- Avoid editing shared files unless the project’s actual shared truth changed

### Before merge

- Read the task files from all active branches
- Review shared files for actual project-wide change
- Check whether any branch created a new decision, learning, or question that should be promoted
- Review any `inbox/` notes for promotion or rejection
- Update `NOW.md` and `PLAN.md` only when the repository’s current state really changed

### After merge

- Shared files should reflect the reconciled project truth
- Task files remain useful as branch history
- Conflicting or outdated project facts should be handled with supersession, not silent rewrite

## Conflict policy

When two branches propose different project rules or different interpretations:

- Do not rewrite the earlier record in place.
- Do not quietly prefer whichever branch merged last.
- Add a new decision or update and explain the difference.
- Mark the older record as superseded or rejected as appropriate.
- Keep the old text as historical evidence.

This matches Project Context’s philosophy: preserve history and interpret through status and supersession links.

## Example multi-agent pattern

```text
Worktree 1: auth branch
  - project-context/tasks/auth-branch.md
  - works on login flows
  - adds a candidate note to inbox/ if a new assumption surfaces

Worktree 2: cache branch
  - project-context/tasks/cache-branch.md
  - works on request memoization
  - reads shared project context before making assumptions

Merge steward
  - reviews both task files
  - resolves project-wide changes
  - updates NOW.md / PLAN.md / DECISIONS.md when needed
  - promotes or rejects inbox entries
```

This keeps each branch focused while preserving repo-level continuity.

## Practical rule set

If you want a simple policy to adopt, use this:

- Shared facts live in `project-context/`
- Branch facts live in `project-context/tasks/`
- Uncertain observations live in `project-context/inbox/`
- Review and merge reconcile the shared truth
- Supersede, do not rewrite

That is the cleanest fit for Project Context in a multi-agent, worktree-based workflow.

## Related tools

Use the project-context packet and review commands to stay aligned:

```sh
project-context context --task "<one line>" --files <paths>
project-context review --open-days 14
project-context capture --kind decision --text "<note>" --apply
```

This keeps agents grounded in the current project state instead of relying on memory from a single session.

## Summary

Project Context works well with parallel agents when you treat it as a repo-level memory system rather than a shared editing surface.

The effective pattern is:

- one shared project context that remains readable and reviewable
- one task record per branch or agent
- one merge steward for repo-level reconciliation
- explicit promotion and supersession instead of silent overwrite

That gives you parallel work without losing the project’s continuity.
