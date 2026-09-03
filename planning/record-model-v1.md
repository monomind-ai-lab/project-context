# Record model v1 — the shared contract

Status: build contract, written 2026-09-03. This is the concrete specification
that `planning/project-context-design.md` Part 2 describes in prose. Both
products implement it, and every parallel workstream builds against this file so
the pieces fit without reconciliation.

Authority: the design plan governs intent; this file governs the bytes. Where
they disagree, the plan is right and this file is a bug.

## 1. One schema string, one marker, one version

- Schema string is `project-context/1`. The `context-hub/1` string is retired.
- The marker is `project-context/.project-context.json` in a repo and
  `.project-hub.json` at the root of a Hub.
- There is one version number: the package version. `TEMPLATE_VERSION` and
  `SCAFFOLD_VERSION` are retired and the scripts read `VERSION`.

## 2. Frontmatter: at most 8 required keys

Detail records (`decisions/`, `questions/`, `tasks/`, `inbox/`) carry YAML
frontmatter. Registries (`DECISIONS.md`, `LEARNINGS.md`, `QUESTIONS.md`,
`NOW.md`, `PLAN.md`) do not — they stay plain Markdown, as they are today.

Required, and nothing else is required:

| Key | Value |
| --- | --- |
| `id` | Stable ID: `D-001`, `L-003`, `Q-002`, `T-012`, `C-2026-09-03-a1b2` |
| `kind` | `decision` \| `learning` \| `question` \| `task` \| `capsule` |
| `status` | See the lifecycle below |
| `title` | One line, no trailing period |
| `created` | `YYYY-MM-DD` |
| `asserted_by` | Actor string, `person:<name>` or `agent:<name>` |

Six, not eight. Eight is the ceiling, not the target; do not add two keys
because there is room.

Optional, validated only when present: `approved_by`, `supersedes`,
`superseded_by`, `evidence` (list), `files` (list), `serves` (list, plan items
only), `valid_at`, `invalid_at`, `session`, `harness`, `model`.

Retired: the three-block metadata format, and every required-but-empty field
(`generated_at`, `generated_by`, `confidence`, `aliases`, and the empty
`supersedes: []` / `superseded_by: []` pairs). Absent means absent.

## 3. Lifecycle, one vocabulary

```
proposed → accepted → superseded | rejected
```

`candidate → approved → superseded` is retired. Where existing text says
`candidate`, read `proposed`; where it says `approved`, read `accepted`. The
`approved_by` *field* keeps its name — it records who accepted.

## 4. Reference grammar

Validated by shape everywhere a reference appears. Resolution is optional and
never required.

```text
session:<harness>:<id>          commit:<binding>:<sha>
pr:<binding>#<number>           review:<binding>#<pr>/<comment-id>
ticket:<tracker>:<key>          doc:<binding>:<path>@<commit>
url:<https://...>               capsule:<id>
```

## 5. The authored set and the pushed set

In a project repository:

- **Authored** — `SUMMARY.md`, `NOW.md`, `PLAN.md`, `tasks/`, `DECISIONS.md`,
  `decisions/`, `LEARNINGS.md`, `QUESTIONS.md`, `questions/`, `inbox/`,
  `indexes/`. Builders write these. `/hub-pull` collects them.
- **Pushed** — `global/` and `blueprint/` (which holds `EPIC.md` and
  `ARCHITECTURE.md`). Owner-authored in the Hub, read-only in the repo.
- **Never in Git** — `sessions/`.

In a Hub: `global/`, `projects/<id>/`, `owners_window/`, `registry.md`.
`owners_window/` is never pushed, never linted, never pulled into.

## 6. Stamps

Pushed files stay clean Markdown. No metadata is injected into them. Stamps live
in the marker:

```json
{
  "schema": "project-context/1",
  "version": "0.7.0",
  "project_id": "project-context",
  "pushed": {
    "global/GUARDRAILS.md": {
      "sha256": "<hex>",
      "source_commit": "<hub sha>",
      "pushed_at": "2026-09-03T00:00:00Z"
    }
  }
}
```

The doctor recomputes `sha256` over the file bytes and compares. A mismatch is
an error naming the Hub as the place to change it.

## 7. Conformance: `PLAN.md` serves `blueprint/EPIC.md`

Each `PLAN.md` milestone item carries a `Serves:` line naming one or more epic
item IDs (`E-001`). The doctor:

| Condition | Result |
| --- | --- |
| Plan item with no `Serves:`, and `blueprint/EPIC.md` exists | error |
| Epic item no plan item serves | warning, listed by `review` |
| `Serves:` names an epic item that does not exist | error |
| No `blueprint/` present | silent — a repo with no Hub has no epic |

## 8. Budgets

`SUMMARY.md` ≤ 150 words · `NOW.md` ≤ 400 · capsule ≤ 200 ·
`blueprint/EPIC.md` ≤ 600 · `blueprint/ARCHITECTURE.md` ≤ 1,200 ·
packet ≤ 4,000 tokens. Warnings by default; errors under `--strict`.

## 9. The managed instruction block

Identical text in both `CLAUDE.md` and `AGENTS.md` at the repository root,
creating whichever is missing. Delimited by `<!-- project-context:start -->`
and `<!-- project-context:end -->`. Nothing outside the markers is ever read or
written. Re-running is idempotent. The text is drafted in design plan 2.2.

## 10. Non-negotiables for every workstream

- Zero runtime dependencies. Python standard library only, 3.11+.
- Create-only writes. Never overwrite a user's record. Never delete one.
- Deterministic dry-run, then apply. Idempotent re-runs.
- Never create a remote, never push, never invite. `/hub-push` is the single
  exception and it works on a branch, shows the diff, and asks first.
- No secrets, no absolute home paths, no machine names in any committed file.
