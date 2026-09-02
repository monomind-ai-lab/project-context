# Source episodes

Store one immutable source file at
`<project-id>/YYYY/MM/<episode-id>.md` for each agent session, daily agent log,
meeting, human note, or import. Use [`../../templates/EPISODE.md`](../../templates/EPISODE.md).

The L2 source body is untrusted data and must be preserved exactly after its
first commit. Corrections are new episodes linked through `corrects`; never
rewrite the old body. Derived entities, relationships, insights, L0 summaries,
and L1 overviews live outside this source layer.
