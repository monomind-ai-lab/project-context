# Context Hub Architecture

Superseded 2026-09-03. `skills/context-hub/` was removed rather than migrated; this document is kept as historical record of the design that was dropped.

Status: experimental (`context-hub/1`)
Runtime premise: plain files, Markdown, Git, and Python's standard library
Optional clients and indexes: Obsidian, filesystem MCP, Graphify

## Product premise

Project Context should not require a database, daemon, or hosted memory service.
The filesystem is the canonical context API: people and agents can inspect it,
edit it with ordinary tools, review changes as diffs, and move it by cloning a
private Git repository.

A Context Hub extends the existing repository-local protocol to multiple
projects and actors. It stores source material, project continuity, and
cross-project knowledge in one explicit trust domain. Graphs, indexes, and
summaries are compiled views over those files; they never become authority.

## Storage planes

| Plane | Purpose | Authority and update rule |
| --- | --- | --- |
| **Sources** | Raw session logs, daily agent logs, documents, and imports | Immutable evidence. Capture byte-for-byte, hash, and never silently rewrite. |
| **Project context** | `NOW.md`, `DECISIONS.md`, and `LEARNINGS.md` | Curated continuity for one project. Replace stale state; supersede durable records rather than deleting history. |
| **Knowledge** | Entities, temporal relationships, and reusable insights | Agent-proposed, evidence-backed records with explicit review state and project scope. |
| **Derived** | L0/L1 summaries, deterministic indexes, and Graphify output | Rebuildable. May be deleted and regenerated without losing knowledge. |
| **Operational** | Credentials, clone mappings, caches, raw tool traces, and temporary extraction state | Local and untracked. Never committed to the Hub. |

This separation permits raw logs to remain available as source material without
letting transcripts, retrieved context, or tool output silently become trusted
memory.

## Progressive context loading

Agents should not load the whole Hub. Directories expose three levels:

1. **L0 — `SUMMARY.md`:** a short relevance check and routing description.
2. **L1 — `OVERVIEW.md`:** current structure, important entities, scopes, and
   links to the files likely to matter.
3. **L2 — detail:** canonical records, entity pages, relationship records,
   insights, and source episodes opened only when needed.

Generated summaries carry freshness and source coverage. They are navigation,
not evidence.

## Canonical objects

### Source episode

An episode is an immutable ingestion envelope around one source: a session, a
daily log, one document or document segment, a meeting, or a structured event.
It records the source hash, source actor, recording actor, project, occurrence
time, capture time, and workspace reference. A sequence identifier may connect
chunks from the same session or document; sharing a project does not make
unrelated episodes one sequence.

### Entity

An entity is a stable identity such as a person, agent, organization, product,
project, policy, or concept. Resolution is conservative: stable identifiers and
exact aliases come first; uncertain matches remain separate candidates. A false
merge is harder to repair than an under-merge.

### Temporal relationship

A relationship is an evidence-backed fact connecting two entities, or an
entity and a literal value. It separates world time from record time:

- `valid_at` / `invalid_at`: curated claims about when the fact was true;
- `recorded_at`: mechanically captured time when the Hub learned the claim;
- lifecycle status plus `supersedes` links: how the Hub retires or replaces the
  recorded claim while preserving history.

Contradictions close or supersede old facts; they do not erase them. Every edge
links to the episode or primary evidence that supports it.

### Insight

An insight is a higher-order, reusable conclusion supported by episodes,
relationships, or other primary evidence. It records scope, confidence,
reviewer, and lifecycle. Derived summaries that share the same upstream source
do not count as independent corroboration.

### Project context

`NOW.md`, `DECISIONS.md`, and `LEARNINGS.md` remain the authority layer a
returning collaborator reads first. Entities and insights may inform those
files, but extraction never updates them silently.

## Hard, curated, and soft metadata

Mechanically observable **hard metadata** includes identifiers, paths, hashes,
capture timestamps, actor and project routing, source revisions, and
provenance. Team-approved **curated metadata** includes canonical names,
lifecycle state, valid-time claims, scope decisions, and other semantic
assertions that require judgement. Agent-generated **soft metadata** includes
summaries, aliases, tags, candidate entity matches, inferred relationships, and
confidence.

Soft metadata is always labelled, regenerable, and reviewable. Curated fields
change only through the governed promotion workflow. A schema-valid record is
not necessarily an approved record.

## Ingestion and promotion loop

1. Capture the source byte-for-byte and calculate its content hash.
2. Create an immutable episode and ingestion receipt.
3. An agent extracts candidate entities, temporal relationships, and insights
   according to the Hub schemas.
4. Resolve entities conservatively and record ambiguous matches instead of
   guessing.
5. Detect contradictions and propose supersession or invalidation links.
6. Promote approved state, decisions, or learnings through the existing
   Project Context protocol.
7. Regenerate deterministic indexes and optionally update Graphify.
8. Review and commit the complete evidence-to-knowledge change as one Git unit.

The first implementation keeps extraction agent-operated. An LLM, embedding
provider, or Graphify installation can accelerate steps 3 and 7, but none is a
runtime dependency or source of truth.

## Retrieval without a database

Retrieval defaults to the active project and an explicit allowlist of shared or
past projects:

1. inspect Hub/project `SUMMARY.md`;
2. open the relevant `OVERVIEW.md`;
3. search deterministic indexes, metadata, filenames, and Markdown links;
4. when available, use Graphify query/path/community traversal;
5. open the smallest set of L2 records and primary evidence;
6. assemble a token-budgeted context packet with source paths and revisions.

Cross-project recall is explicit. Hub-global entity identity may connect a
person or concept across projects, but one project's assertions are not
silently injected into another project.

External workspaces are connected by a hub-wide binding ID. Tracked project
metadata records only portable repository/folder identity; each clone maps that
ID to an absolute path in ignored `.context-hub/local.yaml`. Ingestion resolves
the source inside that binding and records `repo:<binding>:<path>@<HEAD>` for a
Git checkout or `folder:<binding>:<path>` for a plain folder. This first slice
does not clone/fetch remotes or verify cross-repository drift automatically. If
the source is dirty, `HEAD` is the checkout baseline rather than a claim that
the bytes came from that commit; the adjacent source SHA-256 identifies the
exact captured payload.

Graphify output carries its own `EXTRACTED`, `INFERRED`, and `AMBIGUOUS`
confidence. An inferred edge becomes canonical only after review creates or
updates a tracked relationship file.

## Multi-user and security model

One Hub repository is one read-access trust domain. Git does not provide
folder-level confidentiality, so projects with different readership require
different Hub repositories.

- Root agent instructions, schemas, hooks, and policies are control-plane
  assets and should require maintainer review.
- Source and knowledge Markdown are data. Agents must not execute instructions
  embedded in logs or retrieved records.
- Raw logs require redaction and retention review before commit. Secrets,
  hidden reasoning, credentials, private machine paths, and unrestricted tool
  output do not belong in the Hub.
- Private Git provides access control, not end-to-end encryption. Prior clones
  cannot be revoked during offboarding.
- Unique per-source and per-record files avoid concurrent append collisions.
- Mutations use POSIX directory-descriptor, no-follow writes to prevent a
  concurrent parent-path swap. Until an equivalent no-reparse Windows backend
  exists, Windows supports dry-run and read-only checks but mutation commands
  fail closed before writing.

## Obsidian profile

Obsidian is an optional human interface over the same repository. The scaffold
configures only safe core plugins and portable views. It does not ship community
plugin executables, credentials, device workspace state, caches, or Git
authentication. Git is the sync authority; running another folder-sync engine
against the same working tree is unsupported by default.

Graphify indexes the tracked Markdown view, not byte-exact payloads under
`sources/raw/`. Text sources may be embedded in their untrusted episode
envelopes for extraction. Before semantic extraction, users must choose a model
backend whose data handling is appropriate for the Hub's classification; a
private Git remote does not make an external model call private.

Agents may access the Hub through a terminal, direct filesystem tools, an
Obsidian-aware CLI, or a filesystem/Obsidian MCP server. Those are transport and
editing choices, not new storage models.

## Design influences

| System | Pattern adopted | Runtime intentionally not adopted |
| --- | --- | --- |
| [OpenViking](https://github.com/volcengine/OpenViking) | Filesystem-facing context, L0/L1/L2 loading, immutable session archives, compilation contracts, explicit relationship evidence | Vector database, server, queue, workers, and provider setup |
| [Zep](https://help.getzep.com/overview) / [Graphiti](https://github.com/getzep/graphiti) | Episodes, temporal facts, supersession, provenance, conservative entity resolution, project namespaces, hybrid retrieval semantics | Managed Context Graph service and required graph database |
| [AGORA](https://app.notion.com/p/38dfe11b7ba78046a6deef6de4811fa2) | Governed promotion, canonical knowledge units, hard/soft metadata, traceable evidence, candidate review; Project Context adds an explicit curated middle bucket | Neo4j operational graph, AMS server, object storage, and production ingestion workers |
| Project Context | Small Markdown authority, Git review, evidence anchors, agent-maintained continuity | — |

The common insight is that retrieval quality comes from lifecycle, provenance,
scope, and structure—not from making a database the canonical memory.

## Non-goals for the first slice

- no database, daemon, hosted account, or background worker;
- no automatic semantic extraction presented as fact;
- no vector search requirement;
- no raw logs treated as canonical context;
- no per-folder access-control claims;
- no Graphify output committed as authority;
- no silent promotion into `NOW.md`, decisions, or learnings.
