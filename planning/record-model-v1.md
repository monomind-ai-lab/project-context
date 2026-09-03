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
  `.project-hub.json` at the root of a Hub. Every marker carries a `product`
  key — `project-context` or `project-hub` — so a reader knows whose version it
  is holding and never compares one product's number against the other's. A
  marker naming a foreign product is a warning, not an upgrade prompt.
- **One version number per product**, read from that product's `VERSION`.
  `TEMPLATE_VERSION` and `SCAFFOLD_VERSION` are retired: a product does not
  version its templates or its scaffold separately from itself. The two products
  version independently — Project Context and the Hub scaffold ship on their own
  cadences — so a marker records both which product wrote it and that product's
  version, and a migration reader must never assume the two numbers relate.
  (Clarified 2026-09-03: the original wording read as though both products
  shared one number.)

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
`superseded_by`, `evidence` (list), `files` (list), `valid_at`, `invalid_at`,
`session`, `harness`, `model`.

There is deliberately no `serves` frontmatter key. `PLAN.md` is a registry and
carries no frontmatter, so the conformance anchor in §7 is a body line on the
milestone item, not a field. (Corrected 2026-09-03; the key as first listed had
nowhere to live.)

Retired: the three-block metadata format, and every required-but-empty field
(`generated_at`, `generated_by`, `confidence`, `aliases`, and the empty
`supersedes: []` / `superseded_by: []` pairs). Absent means absent.

## 3. Lifecycle, one vocabulary per kind

Revised 2026-09-03 after the slice-2 build found two real gaps: §3 as first
written contradicted design 2.6 on questions, and it gave a task no terminal
state — a finished task was neither `accepted` nor `superseded` nor `rejected`.

One vocabulary is the goal, but a question is not an assertion and a task is not
a claim, so forcing all three through one set of words was the error. Each kind
has exactly one vocabulary, and the doctor enforces *that* kind's set — not a
permissive union of all of them, which would let two people write questions two
different ways with nothing to catch it.

| Kind | States |
| --- | --- |
| `decision`, `learning`, `capsule` | `proposed → accepted → superseded \| rejected` |
| `question` | `open → answered → superseded` |
| `task` | `proposed → active → done \| dropped` |

`candidate → approved → superseded` is retired everywhere. Where existing text
says `candidate`, read `proposed`; where it says `approved`, read `accepted`.
The `approved_by` *field* keeps its name — it records who accepted.

`NOW.md`'s activity column is prose about work, not a record status, and stays
as it is.

## 4. Reference grammar

Validated by shape everywhere a reference appears. Resolution is optional and
never required.

```text
session:<harness>:<id>          commit:<binding>:<sha>
pr:<binding>#<number>           review:<binding>#<pr>/<comment-id>
ticket:<tracker>:<key>          doc:<binding>:<path>@<commit>
url:<absolute-url>              capsule:<id>
```

Angle brackets mark a metavariable and are never literal: a URL reference is
written `url:https://example.com/x`, not `url:<https://example.com/x>`.

One scheme was missing and is added 2026-09-03: a pulled record had no way to
cite the Hub state it came from, since `doc:` assumes a binding name a Hub
cannot declare.

```text
hub:<hub-id>@<commit>
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
`owners_window/` is never pushed, never linted, never pulled into. "Never
linted" is carried by the shared doctor itself, which excludes
`owners_window/` and `sessions/` from every scan, so the guarantee holds however
the doctor is invoked rather than depending on a wrapper.

**Which part of `global/` is shareable.** Added 2026-09-03; the design said
"shareable subset" and named no mechanism, which left it for each implementer to
invent. It is an allow-list in the Hub marker, plus two structural filters and
one absolute rule:

| | Entries |
| --- | --- |
| Default | `SUMMARY.md`, `GUARDRAILS.md`, `WORKFLOWS.md`, `skills/`, `shared/` |
| Opt-in per project | `GOALS.md`, `RESOURCES.md`, `people/`, `agents/` — objectives across every project, internal dashboards, and a roster of people are each more sensitive than the guardrails a builder needs to do the work |
| **Never, at any setting** | `IDENTITY.md` (decision D9) |
| Filtered structurally | any `README.md` — it explains the Hub, not the organisation; and any file still carrying `<!-- project-hub:unfilled -->`, because an empty guardrail in front of an agent is worse than no guardrail |

`IDENTITY.md` is not a default a marker may override. A Hub whose configuration
lists it does not get to push it: the entry is dropped and the caller is told.

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

Keys are POSIX paths relative to `project-context/`, so the example above is
the file at `project-context/global/GUARDRAILS.md`. The doctor recomputes
`sha256` over the file bytes and compares. A mismatch is an error naming the Hub
as the place to change it; a file under a pushed prefix with no stamp at all is
a warning, since a hand-added file is worth naming but is not a broken install.

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

The pushed set has two more, added 2026-09-03 because "stays under the global
budget" named no number and blocked anyone implementing push: **any one file in
`global/` ≤ 400 words, and the whole pushed subset ≤ 2,000**. Over-budget refuses
the push and names the file to trim first. Word counts strip frontmatter, fenced
code, and HTML comments. All of these are overridable in the Hub marker; the
budget is a default, unlike D9.

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
