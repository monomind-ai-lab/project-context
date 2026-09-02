# Context Hub — Review Handoff

Status: draft implementation on `codex/context-hub-no-db`
Baseline commit: `ec5db82`
Repository state: uncommitted working-tree changes; no remote was created, no
push was made, and no collaborator was invited.

## Purpose

This handoff lets another agent review the Context Hub without reconstructing
the full conversation. It separates implemented work from designed-but-unbuilt
work and includes the user's open database question.

Treat the current work as three layers:

1. **Implemented:** a database-free, filesystem-first Context Hub v0.6.
2. **Designed, not implemented:** artifact lineage, archival/purge, governed
   skill evolution, and scale-oriented retrieval changes.
3. **Not authorized or performed:** remote creation, hosting configuration,
   invitations, pushes, provider-backed Graphify extraction, or source deletion.

## User objective

Project Context originally served a solo project in a local folder/private
repository, or projects whose context could safely remain public. The intended
expansion is a private team-capable context workspace:

- private Git repository, optionally opened as an Obsidian vault;
- sessions and daily logs retained as raw evidence;
- people/agent identities, project folders, entities, relationships, and
  insights with provenance;
- optional Graphify-assisted retrieval and relationship discovery;
- cross-project reuse without silently injecting one project's assertions into
  another;
- no required database, server, RAG service, or hosted memory vendor.

The user also requested future support for session artifacts, archival that
purges sessions while retaining useful context/insights, self-evolution of
skills, and a red-team review of latency and token cost.

## Current implementation

### Product model

The filesystem is the canonical context API. Markdown, JSON Schema
documentation, Git review, and standard-library Python are authoritative.
Indexes, Graphify output, and summaries are rebuildable views, not authority.

| Plane | Current role |
| --- | --- |
| Sources | Raw sessions, daily logs, imports, immutable episode envelopes, receipts |
| Project context | `NOW.md`, `DECISIONS.md`, `LEARNINGS.md` |
| Knowledge | Candidate/approved/superseded entities, temporal relationships, insights |
| Derived | L0/L1 routing, deterministic Markdown indexes, optional Graphify output |
| Operational | Ignored clone paths, credentials, caches, temporary tool state |

L0/L1/L2 loading is explicit: Hub/project `SUMMARY.md`, then `OVERVIEW.md`,
then only relevant detailed records and evidence.

### Delivered files and commands

New material:

- `skills/context-hub/` — agent skill, scaffold, templates, schemas, runtime.
- `docs/context-hub-architecture.md` — architecture and research synthesis.
- `prompts/create-context-hub.md` — agent-guided local onboarding.
- `tests/test_context_hub.py` — behavior/security coverage.

Changed integration material:

- `project-context hub ...` dispatch in `src/project_context_cli/__init__.py`.
- Version bump to `0.6.0` plus packaging/validator integration.
- README and homepage copy in English, Korean, and Traditional Chinese.

Implemented commands:

```text
project-context hub init --target <hub> --dry-run|--apply
project-context hub add-actor ... --apply
project-context hub add-project ... --apply
project-context hub bind-project ... --apply
project-context hub ingest ... --apply
project-context hub index --check|--apply
project-context hub doctor
```

### Implemented behavior

- Safe create-only initialization and thin managed `AGENTS.md`/`CLAUDE.md`
  pointers that preserve unrelated instructions.
- Copyable private Git/Obsidian scaffold with safe core Obsidian settings.
- Stable actors, projects, external bindings, and ignored local absolute paths.
- Immutable ingestion: exact raw bytes, SHA-256, envelope/receipt hashes,
  actor/recorder attribution, event-tuple dedupe, portable Git/folder provenance.
- Candidate → approved → superseded lifecycle for semantic records and temporal
  relationship facts.
- Deterministic entity, relationship, insight, and wikilink indexes.
- `doctor` checks scaffold integrity, record contracts, receipts, bindings,
  effective Git exclusions, local path leakage, Obsidian state, and symlinks.

### Security/platform boundary

macOS/Linux mutations use no-follow directory-descriptor operations and were
tested against a live parent-directory swap. Windows mutations fail closed until
an equivalent no-reparse write backend exists; dry-run/read-only use remains.

## Research synthesis

The design adopts useful patterns while deliberately not adopting their
operational dependencies:

| Influence | Adapted idea | Intentionally not adopted |
| --- | --- | --- |
| [OpenViking](https://github.com/volcengine/OpenViking) | filesystem-facing context, L0/L1/L2 routing, immutable archives, provenance | server, vector database, queues, workers |
| [Zep](https://help.getzep.com/overview) / [Graphiti](https://github.com/getzep/graphiti) | episodes, temporal facts, conservative entity resolution, supersession | managed graph service and graph database |
| [AGORA](https://app.notion.com/p/38dfe11b7ba78046a6deef6de4811fa2) | governed promotion, canonical units, hard/curated/soft metadata | Neo4j/AMS/object-storage operational stack |

## Validation completed

Completed before this handoff:

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: **72/72 passed**.
- `python3 scripts/validate_repository.py`: **85 required files checked**.
- `python3 scripts/build_site.py --check`: passed.
- Python compilation and `git diff --check`: passed.
- Context Hub CLI help passed with `python -S`, confirming standard-library-only
  runtime behavior.
- Independent adversarial review passed on macOS/POSIX: parent-swap race,
  Git-ignore negation, tracked local config, binding-output redaction, duplicate
  bindings, and invalid schema values.

Not completed:

- Wheel/package build in this environment; local build tooling was unavailable.
- Real Graphify semantic extraction; it may disclose text to a model provider
  and requires explicit approval for the source classification.
- Real private remote/team onboarding or a production-sized corpus.

## Critical gaps and red-team findings

### Session artifacts are not modeled yet

`artifact` is currently only an episode source kind and generic entity type.
There is no logical artifact, version, lineage, retention, or session-artifact
association record.

Recommended model:

```text
episode (event) ── input/output/modified ──> artifact version
artifact version ── revision/derivation ───> artifact
```

Keep ordinary associations in a compact session manifest. Promote only
important objects into `artifact@1` and `artifact-version@1` records. Preserve
the canonical deliverable in its bound work repository when possible; the Hub
stores a pinned portable reference, digest, classification, retention class, and
lineage. Do not make a transcript the only copy of a deliverable.

Suggested retention classes: `ephemeral`, `derived`, `source`, `project`, and
`durable-context`, with `legal-hold` as an override.

### `archived` is a label, not an archival lifecycle

The project schema accepts `archived`, but no archive/purge command exists.
Deleting a source currently breaks doctor/evidence/receipt integrity because the
runtime intentionally requires raw source and episode files to remain present.

Separate project lifecycle from source retention:

```text
active → completed → closing → frozen → archived

source: live → purge-eligible → purged
                              ↘ held / purge-failed
```

Archive in two phases:

1. **Freeze and compact:** block ingestion, classify artifacts, promote
   sole-copy deliverables, resolve/discard candidates, compute reverse
   dependencies, and produce reviewed `ARCHIVE.md` plus an archive manifest.
2. **Purge and seal:** remove sessions/raw/receipts/candidates/ephemeral
   artifacts and derived caches, rebuild active indexes, and write a minimal
   purge attestation. Surviving evidence must say `purged_by_policy`, rather
   than falsely claim deleted primary evidence remains available.

Git constraint: deleting committed files removes them from the current tip, not
from history, host backups, or prior clones. The product must distinguish:

- `history-retained`: one repo; latest revision hides source files.
- `purgeable`: durable Context Hub plus a separate short-retention source
  repository/storage domain.

The second option is the only honest default when users require actual source
purge. It remains filesystem-only and database-free.

### Self-evolution is absent

Insights and `LEARNINGS.md` can remember a recommendation, but cannot measure,
test, promote, roll back, or sunset a skill. Current indexes have no performance
or failure-evidence model.

Minimum governed evolution loop:

```text
eligible opportunity → evaluation → failure classification → versioned proposal
→ preregistered experiment → canary → independent approval → monitor/rollback
```

Recommended Markdown record types:

- `skill@1`: identity, owner, exact version/content digest, lifecycle,
  applicability, risk, replacement/migration.
- `skill-evaluation@1`: every eligible opportunity—including not-invoked and
  abstained cases—task/model/harness versions, outcome, tokens, latency,
  corrections, evaluator, evidence.
- `failure-mode@1`: normalized signature, severity, reproduction, affected
  versions/strata, evidence/counterevidence, mitigation lifecycle.
- `skill-change@1`: create/modify/deprecate/sunset/restore proposal, baseline,
  candidate, hypothesis, patch, risks, rollback target, approvals.
- `experiment@1`: frozen holdout, primary metric, guardrails, sample minimum,
  token/latency budget, stratified result, decision.
- `evaluation-summary@1`: deterministic retained aggregate after detailed events
  expire.

Agents may propose code and experiments; they must not directly activate,
approve, quarantine, or sunset their own skills. Promotion needs independent
review, material benefit, per-stratum non-regression, no critical safety issue,
and cost/latency compliance. Sunset must never be based only on low popularity
or raw failure count.

Adding schema files alone is insufficient: runtime validation and behavioral
tests must enforce the contracts. The current frontmatter parser is intentionally
small and does not implement arbitrary YAML/JSON Schema semantics.

### Indexing and token economy are acceptable at small scale, not yet Hub scale

Synthetic local-SSD benchmarks:

| Corpus | Full index | Full doctor |
| --- | ---: | ---: |
| 5,000 typed records | 0.73 s | 0.64 s |
| 1,000 episodes containing about 10 KiB each | 1.15 s | 0.58 s |

The 1,000-episode Hub occupied 23.4 MiB because small UTF-8 source text is
stored as raw bytes and embedded again inside the episode. This is useful for
one-time extraction but costly as the durable default. Graphify can read the
embedded copy even though `.graphifyignore` excludes `sources/raw/`. At roughly
four characters per token, that synthetic corpus represents about 2.5 million
input tokens before graph extraction output.

Current scale risks:

- Global full scans/rebuilds and global wikilink traversal.
- Full raw/episode hashing on every deep doctor run.
- Raw Markdown can enter the deterministic wikilink index.
- Archived projects are not yet cold/excluded by default.
- One-file-per-record eventually taxes Git, Obsidian metadata, and filesystem
  traversal.
- No enforced L0/L1/context-packet token budget or query planner.
- Monolithic entity graphs create high-fan-out nodes and irrelevant recall.
- Model/Graphify/Obsidian caches can retain data after archive/purge unless they
  are explicitly scrubbed.

Recommended no-database retrieval path:

1. Sharded rebuildable path/hash manifest by project, status, record kind, and
   time bucket.
2. Tiny global routing index, per-project active indexes, archived projects as
   cold shards.
3. Fast structural doctor plus scheduled deep byte-verification doctor.
4. One-time transient source extraction, then compact promotion capsules and
   typed candidates; do not feed cumulative raw sessions into the durable graph.
5. A transient extraction graph and separate durable graph over approved
   knowledge only.
6. Default budgets such as 150–250 tokens for L0, 600–1,000 for L1, and a
   4,000-token task packet with an explicit hard cap.

Proposed engineering targets—not current claims—are warm routing under 100 ms,
task-packet assembly under 500 ms before model inference, and incremental index
updates under one second for a small change at high record counts.

## Database question: should one be added?

### Recommendation

**Do not add a database as the canonical memory store.** Add an **optional,
local SQLite index** only after the no-database sharded-index path is defined.

SQLite is the one database option that fits the current product philosophy: one
local file, no server, no account, no network, standard Python access, easy
deletion/rebuild, and straightforward portability. SQLite FTS5 provides native
full-text search; JSON functions and transactional updates are also available
in modern builds. [FTS5](https://www.sqlite.org/fts5.html) · [JSON
functions](https://www.sqlite.org/json1.html)

### Concrete advantages

| Problem | SQLite advantage |
| --- | --- |
| Search | FTS for titles, summaries, decisions, approved insights, aliases, and metadata without scanning every Markdown file |
| Routing | Indexed filters by project, lifecycle, actor, time, classification, and record type |
| Archive | Fast reverse-dependency closure for sources/artifacts being purged |
| Evolution | Cheap aggregation of outcomes, failure modes, token/latency percentiles, and canary comparisons |
| Incremental work | Transactional updates for changed paths/hashes rather than global rebuilds |
| Local responsiveness | Faster repeat queries in a large Obsidian/Git checkout |

It does **not** solve provenance, bad extraction, access control, cross-project
privacy, Git history purge, token budgeting, or agent governance. Used poorly,
it creates a second source of truth and more maintenance.

### Fit without difficult onboarding

Keep SQLite entirely optional and derived:

```text
tracked Markdown/Git records  ── index command ──> ignored local SQLite file
                                          │
                               delete/rebuild at any time
```

Suggested user experience:

1. Default installation remains file-only; no database prompt or dependency.
2. `doctor`/`index` recommends acceleration only after a measured threshold
   such as high record count, slow full scan, or large source corpus.
3. User opts in explicitly with one command, e.g.
   `project-context hub index --engine sqlite`.
4. Runtime checks FTS5 support and falls back to sharded Markdown indexes when
   unavailable. FTS5 build availability must be checked, not assumed. [FTS5
   build notes](https://www.sqlite.org/fts5.html)
5. The database resides in ignored local operational state such as
   `.context-hub/cache/index.sqlite`; it is never committed or synchronized.
6. `project-context hub index --rebuild` deletes/recreates it deterministically
   from canonical tracked files; `doctor` reports freshness/version but never
   treats it as authority.

Initial local tables should stay narrow:

```text
files(path, content_hash, mtime, record_kind, project_id, status)
records(id, path, title, summary, classification, timestamps)
edges(subject_id, predicate, object_id, evidence_ref)
fts_records(title, summary, approved_body)
```

Do not index raw session bodies by default. If a user explicitly enables
transient source search, place it in a separate retention-aligned local index
and delete it alongside the source plane.

### Concurrency and maintenance caveat

The SQLite file should be per clone/user, not shared through Git or a folder-sync
service. With one CLI writer, build a temporary database and atomically replace
it. If a future local MCP/UI needs concurrent readers while indexing, SQLite WAL
may help, but its `-wal` and `-shm` files are local cache state and must not be
synced. [SQLite WAL documentation](https://www.sqlite.org/wal.html)

SQLite is not a shared multi-user service. Git remains the collaboration and
merge layer. Each collaborator rebuilds a local accelerator from the same
canonical Markdown.

### What not to introduce yet

- No required vector database or vector extension.
- No canonical embeddings or canonical database rows.
- No shared Postgres/Neo4j service at this stage; that introduces secrets,
  backups, migrations, access control, and operational ownership.
- No central database merely to compensate for unbounded source ingestion; fix
  retention, shards, and context budgets first.

A later enterprise/real-time tier could run a centrally hosted **replica** for
multi-writer analytics and sub-second global queries. It should ingest reviewed
Git/source events one-way, remain disposable/rebuildable, and never replace
canonical files.

## Recommended decision sequence

1. Decide whether `purgeable` source retention is a product requirement or an
   advanced mode. This decides whether raw sessions can live in the durable Hub
   repository at all.
2. Define artifact/session-manifest records and archive roots before automatic
   extraction.
3. Define capability-evolution governance before allowing agents to modify
   skills.
4. Implement sharded file indexes, cold archives, fast/deep doctor modes, and
   bounded context packets.
5. Add optional local SQLite FTS only when measurements show file indexes no
   longer meet desired latency; retain file-only operation permanently.

## Reviewer checklist

Please assess these questions explicitly:

- Is the durable-vs-purgeable two-plane model worth its extra repository/folder
  complexity?
- Should artifacts be first-class from day one, or only when promoted?
- What minimum provenance should survive source purge without retaining raw
  session content?
- Is governed skill evolution in scope for the Hub or a separate control plane?
- Are active/cold project routing and proposed token budgets appropriate?
- Is optional local SQLite FTS the correct acceleration boundary?
- Does any current feature create a false privacy or purge claim?
- Which next implementation slice is highest value: source retention, artifacts,
  archive, index architecture, or evolution governance?

## Useful entry points

- [Architecture](context-hub-architecture.md)
- [Context Hub skill](../skills/context-hub/SKILL.md)
- [Runtime](../skills/context-hub/scripts/context_hub.py)
- [Copyable scaffold](../skills/context-hub/assets/context-hub/README.md)
- [Context Hub tests](../tests/test_context_hub.py)
- [User-facing README](../README.md)
