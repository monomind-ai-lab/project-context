# Site plan — replacing `/guide/` with docs, tutorials, teach and compare

Status: §12.1 (stdlib Python), §12.2 (Cloudflare git-connected), §12.3 amended and
§12.5 (keep `/guide/`) all decided 2026-08-31 — see §14. Phase 0 built and verified
(§13). Written 2026-08-31 against repo `0.5.0`.

Lives in `planning/`, not `docs/` — `docs/` is the GitHub Pages deploy root
(`.github/workflows/pages.yml` uploads `./docs`), so anything left there is
published to the public site.
Target: `projectcontext.monomind.one`, deployed from `site/` via `site/sync.sh`.

---

## 1. What this changes

Today the site is three hand-authored HTML files:

| Route | Source | Size | Role |
| --- | --- | --- | --- |
| `/` | `site/index.html` (committed) | 140K | Landing |
| `/use-cases/` | `site/use-cases/index.html` (committed) | 108K | Breadth ("not only code") |
| `/guide/` | `docs/project-context-complete-guide.html`, copied at build | 320K | Everything else — 18 stacked sections |

`/guide/` is carrying six jobs at once: the pitch, the concept model, the install
instructions, the file reference, the operating protocol and the integrations
list. It reads as one long scroll, so a reader looking for "what does the doctor
report?" has to know it lives in section 11. Nothing is linkable, nothing is
findable, and a 320K single file is at the practical ceiling of hand-authoring.

The proposal splits that one artifact into a navigable set with four top-level
destinations — **Docs**, **Tutorials**, **Teach**, **Compare** — plus the
existing **Use cases**, following the shape of `skills.addy.ie`.

---

## 2. Findings that constrain the build

Five things I found in the current site that any plan has to answer for. They
are the reason this is not just "write more HTML files."

**2.1 — The CSS is inline, per page.** `site/index.html` carries the full design
token block and every rule inline. Twenty pages of that is ~2.8 MB of duplicated
stylesheet and twenty places to fix one contrast bug. Shared assets are now
mandatory, not a nicety.

**2.2 — Translation is two-tier and hand-fed.** The landing page has ~171
`data-i18n` keys for the native EN/KR/ZH-TW tier, plus Google `element.js` as
the machine tier for other languages. Hand-authoring 171+ keys per page across
twenty pages is not realistic. This needs an explicit decision (§9), not a
default.

**2.3 — The `googtrans` cookie is a live hazard.** `site/index.html:1608-1671`
contains hard-won logic that clears `googtrans` at *every* domain scope, because
the cookie is shared across all `monomind.one` subdomains and Google's
`element.js` rewrites it rather than just reading it. Commit `f95aec9` was
exactly this fix applied to the guide. Every new page must inherit that logic
from one shared file — re-deriving it per page will reintroduce the bug.

**2.4 — Accessibility was measured, not guessed.** The token block documents
specific contrast repairs against the house template (`--fg-faint`, the light
semantic hues) with measured ratios in the comments. That discipline is an asset.
New pages must consume the tokens and never hardcode a colour.

**2.5 — `site/guide/` and `site/og-image.jpg` are gitignored** and assembled by
`sync.sh` at build time, deliberately, so no 320K duplicate can drift. Any new
build step should keep that "generated output is not committed" property.

---

## 3. Target information architecture

```
/                          Landing                      (exists, nav updated)
/docs/                     Docs hub + getting started
  /docs/install/           Both install paths, per harness
  /docs/records/           NOW / DECISIONS / LEARNINGS — the spec
  /docs/profiles/          Core vs full
  /docs/operate/           The session loop (the day-2 page)
  /docs/doctor/            Health checks, checks list, JSON, exit codes
  /docs/evidence-anchors/  path@commit, drift, when to anchor
  /docs/authority/         Authority model + safety guarantees
  /docs/cli/               init / inspect / review / doctor
  /docs/integrations/      GitNexus, Graphify, OpenWiki
  /docs/troubleshooting/   Failure modes and fixes
/tutorials/                Hub, three tracks
  /tutorials/first-repo/       Beginner   · 6 steps  · 15 min
  /tutorials/existing-repo/    Intermediate · 8 steps · 30 min
  /tutorials/non-code/         Intermediate · 7 steps · 25 min
  /tutorials/team/             Advanced   · 7 steps  · 40 min
/teach/                    Media kit — decks, diagrams, share copy
/compare/                  Honest positioning against five alternatives
/use-cases/                (exists, cross-linked into docs)
/guide/                    301 -> /docs/  (README, landing and external links point here)
```

Nav: `Docs · Tutorials · Use cases · Teach · Compare · GitHub`. Six items, which
is the addy.ie count minus the two slots Project Context does not need (see §6).

---

## 4. The onboarding spine — what a new user actually needs

This is the part that decides whether the pages are worth building. A new reader
arrives with five questions, in this order. The site should answer each one
*completely* before raising the next.

### Q1. "Why would I want this?" — 20 seconds

The existing framing is right and should be reused verbatim as the spine: **a
collaborator returning after three weeks should not rebuild the project from
stale chats.** They should be able to answer four questions — what is true now,
which decisions constrain the work, what has already been learned, where is the
evidence.

What is missing today is *proof*. The concept is abstract until you see the
files. **Every top-of-funnel page must show a real `NOW.md` in the first
viewport.** Not a diagram of one — the actual Markdown, ~12 lines, from
`examples/sample-project-context/`. This is the single highest-leverage change
in the whole plan.

### Q2. "Will it fit *my* project?" — 40 seconds

Project Context works for research, writing, documents and mixed projects, not
just code, and it does not require Git. That is a real differentiator and it is
currently buried on `/use-cases/`, behind the guide. Answer it early with a short
fit matrix on `/docs/`:

| Your project | Fits? | Start here |
| --- | --- | --- |
| Code repository, several agents touch it | Yes — the core case | `/tutorials/existing-repo/` |
| Brand-new repository, nothing written yet | Yes | `/tutorials/first-repo/` |
| Research corpus, papers, datasets | Yes | `/tutorials/non-code/` |
| Writing or documents project | Yes | `/tutorials/non-code/` |
| A shared folder with no Git | Yes — Git adds history, is not required | `/docs/install/` |
| A project you will not return to | No — nothing to hand off | — |

The last row matters. Telling a reader when *not* to install buys credibility
for every other row.

### Q3. "What will it do to my repo?" — the adoption blocker

This tool edits `CLAUDE.md` and `AGENTS.md`. Any careful reader stops here, and
the answer is currently in section 15 of the guide. It should be **on the install
page, above the install command**, stated as a promise list:

- Existing context files are preserved byte-for-byte.
- Existing `AGENTS.md` / `CLAUDE.md` content is preserved outside one managed
  block — including file mode and CRLF line endings.
- Unknown or overlapping memory is reviewed and classified, never migrated
  behind your back.
- Malformed blocks, unsafe symlinks and non-UTF-8 instructions stop apply mode
  before any write.
- Add-ons need a separate, informed opt-in each. Nothing is a default checklist.
- 13 files. One skill. Zero runtime dependencies, stdlib Python 3.10+.

And then lead with the safe command, not the applying one:

```sh
uvx --from git+https://github.com/monomind-ai-lab/project-context project-context init --target . --dry-run
```

`--dry-run` first, `--apply` second. The current README leads with `--apply`;
the site should invert that. A reader who runs a preview and sees a 13-file plan
converts better than one who is asked to trust a write.

### Q4. "What did it just create?" — the annotated tour

The moment after install is where adoption is usually lost: the user has three
Markdown files and no feel for them. `/docs/records/` should be an **annotated
tour, not a table**. For each of the three records:

- What question it answers (one line).
- A real example, rendered as the file, with margin annotations on 3–4 lines.
- **What does *not* go in it** — the boundary is what makes the three files stay
  distinct. `NOW.md` is not a changelog. `DECISIONS.md` is not a design doc; it
  holds the constraint and the reason, and points at the design. `LEARNINGS.md`
  is not a diary; an entry earns its place by being reusable and verified.
- One good entry and one bad entry, side by side. This teaches faster than a
  schema.
- How it changes over time — decisions are superseded, not deleted.

### Q5. "What do I do from now on?" — the loop

Most installs die because nobody knows the day-2 ritual. `/docs/operate/` is the
page that prevents that, and it should be blunt:

1. **Before substantial work** — the agent reads `NOW.md`, `DECISIONS.md`,
   `LEARNINGS.md`. Automatic in harnesses that discover the skill; the managed
   block in `AGENTS.md` / `CLAUDE.md` covers the rest.
2. **During work** — trigger detection flags moments that produce a durable
   record: an accepted trade-off, a reproduced bug, a verified benchmark. The
   agent proposes; `ack` confirms.
3. **At the end** — `NOW.md` is updated to what is now true. Decisions and
   learnings are appended if they were earned.
4. **When state may be stale** — the doctor runs. Read-only. It flags; it never
   rewrites.

Close it with a **first-week checklist** — five concrete things to have written
down by day 7 (one real decision with its reason, one learning with evidence, a
`NOW.md` that a stranger could act on, one anchored evidence link, one clean
doctor run). A reader who completes that has actually adopted the tool. This is
the equivalent of addy.ie's "Your first 10 minutes" and it is the piece that
converts an install into a habit.

---

## 5. Page-by-page content specs

### `/docs/` — hub and getting started

One page, not a bare index. Sections in order: the four questions · a live
`NOW.md` sample · the fit matrix (Q2) · install in 30 seconds (both paths, tabbed)
· what got created (13-file tree, annotated) · the loop in four steps · four CTA
cards out to Tutorials, Records, Operate, Compare. Left sidebar carries the full
docs tree; it is the only page that must work as a standalone read.

### `/docs/install/`

Safety promises above the fold (Q3) · dry-run first · **tabbed native setup** by
harness — Claude Code, Cursor, Windsurf, Copilot Chat, Aider, Claude Desktop,
ChatGPT, "any other agent" — each tab showing the exact discovery path (installed
skill vs. the managed block in root agent instructions) · the copy-paste agent
prompt for harnesses with no launcher, with a copy button · the onboarding
question the initializer asks and why it asks it · verifying the install ·
uninstalling. Every install path ends at the same next link: `/docs/records/`.

### `/docs/records/`

Per §4/Q4. Also carries the file-tree reference and the routing-layer table.

### `/docs/profiles/`

Core (README, SKILL, NOW, DECISIONS, LEARNINGS) vs full (adds `decisions/`,
`designs/`, `incidents/`, `tasks/` with templates). Framed as *when to upgrade*,
not as a feature comparison: start core, move to full when a single record file
stops holding one project's worth of judgement. Show the actual templates.

### `/docs/operate/`

Per §4/Q5, plus the first-week checklist and worked examples of trigger
detection with `ack`.

### `/docs/doctor/`

What it checks, every check by name, what each warning means in plain language,
the JSON shape, exit codes, and running it in CI as a soft gate. Emphasise
read-only — this is the page that proves the tool never rewrites your judgement.

### `/docs/evidence-anchors/`

`path/to/file@<commit>`. The two warnings — `evidence-drift` and
`evidence-unverifiable` — with the exact remediation sentence: re-verify, then
re-anchor or supersede. **When to anchor:** a design trade-off, a performance
baseline, a bug reproduction, a research finding the project depends on. Optional
and Git-gated; warnings only, never errors.

### `/docs/authority/`

The four-layer authority table (primary artifacts > `project-context/` > agent
instructions > generated indexes and wikis) and the full safety guarantee list.
The one-line version worth pulling out as a callout: **generated documentation is
derived and is never current-state authority.**

### `/docs/cli/`

`init`, `inspect`, `review`, `doctor` — flags, output, exit codes. Zero runtime
dependencies, stdlib Python 3.10+. Both `uvx` and `pipx` forms.

### `/docs/integrations/`

The three-tool table with the "choose it when" column, the independence and
attribution notice kept intact and prominent, and the credential-handling
protocol (local/no-key mode offered first, agent never reads the secret). Framed
throughout as *earn their place* — Project Context works with none of them.

### `/docs/troubleshooting/`

Agent does not see the skill · managed block missing or malformed · doctor
reports drift after a rebase · non-UTF-8 instructions halt apply · translation
cookie stuck (see §2.3) · install ran but nothing gets updated during sessions.

### `/tutorials/`

Card grid, addy.ie's format: difficulty badge, step count, time estimate,
one-line premise, "Start tutorial". Four tracks:

| Track | Level | Premise |
| --- | --- | --- |
| `first-repo` | Beginner · 6 steps · 15 min | Empty folder to a `NOW.md` a stranger could act on |
| `existing-repo` | Intermediate · 8 steps · 30 min | Install into a codebase with existing `CLAUDE.md`; review, do not migrate; record the first decision with an anchor |
| `non-code` | Intermediate · 7 steps · 25 min | A research corpus with no Git; the three records for papers and findings |
| `team` | Advanced · 7 steps · 40 min | Two agents, two machines, a superseded decision, and the doctor as a CI gate |

Each tutorial page: prerequisites · numbered steps with exact commands and the
exact expected output · a "you should now see" checkpoint every 2–3 steps · the
finished files shown in full at the end · what to try next. `existing-repo` is
the most valuable of the four — brownfield is the real adoption case, and it is
where the safety guarantees stop being abstract.

### `/teach/`

Media kit, not a deck. Three decks — **101** (why context dies · the four
questions · the three records · install · the loop), **201** (evidence anchors ·
superseding a decision · authority model · the doctor · multi-agent handoff),
**301** (team rollout · CI gate · non-code projects · integrations · what
adoption looks like at day 30). Browser presentation with arrow keys, `F` for
fullscreen, `P` for print-to-PDF. Plus: the pipeline and authority diagrams as
downloadable SVG/PNG, and short share-ready copy for a talk abstract or a
README blurb. The **`tedandlisa` skill already builds MonoMind-branded HTML
decks** — use it rather than hand-authoring, which makes this the cheapest of
the four sections to produce.

### `/compare/`

Deliberately neutral, following addy.ie's stated posture — no star counts, no
adoption figures, honest tradeoffs, no declared winner. Compare against five
alternatives, which is more useful than the two-or-three the reference site does:

| | Project Context | `CLAUDE.md` / `AGENTS.md` alone | Harness memory (Cursor rules, chat memory) | OpenWiki | Graphify / GitNexus |
| --- | --- | --- | --- | --- | --- |
| What it records | Decisions, learnings, current state | Instructions to the agent | Session-local recall | Derived docs of what the code is | Relationships and structure |
| Derivable from the code? | No | n/a | No | Yes | Yes |
| Survives a new agent | Yes | Yes | No | Yes | Yes |
| Survives a new machine / tool | Yes | Yes | No | Yes | Yes |
| Human-readable and reviewable in PR | Yes | Yes | No | Partly | No |
| Answers "why did we choose this?" | Yes | No | Sometimes, unreliably | No | No |
| Runtime footprint | Zero deps, stdlib Python | None | Vendor | Node ≥22, 25 deps | Varies |

The honest paragraph that has to sit under it: **these mostly compose rather than
compete.** OpenWiki answers "what is this codebase?"; Project Context answers
"what did we decide, what did we learn, what is next?" Losing derived docs costs
tokens; losing decisions and learnings costs knowledge. Say the second half of
that out loud — it is the strongest single argument the project has, and it is
currently a footnote in the README.

Also worth its own short section: **what Project Context is not.** It is not a
task tracker, not a wiki, not a memory vendor, not an agent framework.

---

## 6. What to take from `skills.addy.ie`, and what not to

**Take:** the six-item flat nav; the tabbed per-tool setup block; tutorial cards
with difficulty, step count and time; the neutral comparison table with an
explicit "we leave out star counts" note; `/teach/` as a media kit with
downloadable decks and diagrams rather than one deck; the four CTA cards at the
foot of every page; a copy button on every code block.

**Do not take:** their `/skills/` catalog — Project Context has one skill, not
24, and a catalog page would be a page with one card on it. That nav slot becomes
`/docs/records/` instead: the three files *are* the catalog here. Their
`/lifecycle/` and `/loops/` pages both map onto a single `/docs/operate/`;
Project Context has one loop, not eight slash commands, and splitting it would
manufacture depth that does not exist.

---

## 7. Build approach

**Recommended: a small stdlib-Python static generator, no npm.**

```
site/_layout/base.html        One shell: head, nav, footer, theme + i18n boot
site/_assets/site.css         The token block and every rule, extracted once
site/_assets/site.js          Theme toggle, nav, copy buttons, language widget
site/_content/**/*.md         Page content, front-matter for title/desc/nav
scripts/build_site.py         ~250 lines stdlib; renders _content -> site/
site/sync.sh                  Calls build_site.py, keeps the og-image copy
```

Rationale: the repo's whole claim is zero runtime dependencies and stdlib Python
3.10+. Adding a Node toolchain to ship its own documentation would contradict the
pitch on the page the pitch is printed on. Cloudflare Pages already runs
`bash site/sync.sh` as the build command, so the change is one line inside a
script that already exists, and generated output stays gitignored exactly as
`site/guide/` is today.

**Alternative, if you want the ecosystem:** Eleventy or Astro gives free search,
syntax highlighting, sitemap and RSS, at the cost of a `package.json` and a Node
build on Pages. It is a defensible choice — but it should be a deliberate one,
not something that arrives because Markdown-to-HTML felt like a solved problem.

Either way, the three existing pages get their inline CSS extracted into
`site/_assets/site.css` in the same pass. That refactor is unavoidable and is
the first task, not the last.

**One risk to flag:** memory notes that some `monomind.one` Pages projects are
direct-upload with no git source. Confirm this project is the git-connected one
before relying on a build command, or the generator has to run locally and the
output be uploaded — which changes the "generated output is not committed"
property in §2.5.

---

## 8. Keeping twenty pages from drifting

The canon lives in `README.md`, `skills/project-context/SKILL.md` and
`skills/project-context-init/SKILL.md`. Twenty prose pages will fork it within
two releases unless something stops them.

- Install commands, the version string, the file tree and the check names are
  **included from the repo at build time**, not retyped into Markdown.
- `scripts/validate_site.py` runs in CI: every install command on the site must
  match the README; every `path@commit` example must parse; every internal link
  must resolve; the version on the page must equal `VERSION`.
- Examples come from `examples/sample-project-context/`, so the samples on the
  site are the samples that are tested.

---

## 9. Translation — decide before building

The native EN/KR/ZH-TW tier costs ~171 hand-authored keys per page. Across twenty
pages that is not a content task, it is a translation project.

**Recommendation:** keep the native tier on `/`, `/use-cases/` and `/docs/` (the
three pages a non-English reader lands on), and run tutorials, reference docs,
compare and teach on the machine tier only. The language widget stays on every
page, and the `googtrans` clearing logic from §2.3 moves into `site/_assets/site.js`
so all twenty pages inherit the fix rather than twenty copies of it.

---

## 10. Retiring `/guide/`

Do not delete it — `README.md`, the landing nav and any external links point
there. `/guide/` becomes a 301 to `/docs/`.

Its 18 sections are good, translated, working prose and are the raw material for
the docs, not something to rewrite from scratch:

| Guide section | Lands in |
| --- | --- |
| "A collaborator returning after three weeks…" | `/docs/` (Q1) |
| "How the context pipeline works" / "The pipeline, end to end" | `/docs/` + `/docs/operate/` |
| "Agent-operated, human-readable" | `/docs/` |
| "Install with any AI agent" / "What the initializer does" | `/docs/install/` |
| "Two profiles" | `/docs/profiles/` |
| "A routing and continuity layer" / "Repository structure" | `/docs/records/` |
| "What agents do during project work" / "From work to durable context" | `/docs/operate/` |
| "Existing context is reviewed, never migrated behind your back" | `/docs/install/` (Q3) |
| "When context may be stale, the agent runs the doctor" | `/docs/doctor/` |
| "Authority model" / "Safety guarantees" | `/docs/authority/` |
| "Advanced integrations" | `/docs/integrations/` |

Nothing in the guide maps to `/docs/evidence-anchors/`, `/docs/cli/` or
`/docs/troubleshooting/` — those are new writing, and evidence anchors being
absent from the guide is itself a gap worth closing, since it is a 0.5.0 feature.

---

## 11. Phasing

| Phase | Scope | Why this order |
| --- | --- | --- |
| **0** | Extract CSS/JS to shared assets, build the layout shell and generator, port the three existing pages onto it unchanged | Nothing else is safe to build until one stylesheet exists. Ends with a visually identical site. |
| **1** | `/docs/` hub + install + records + operate. `/guide/` 301s. Nav updated. | These four answer Q1–Q5. Highest onboarding value per page; ship-worthy on its own. |
| **2** | Remaining docs pages: profiles, doctor, evidence anchors, authority, CLI, integrations, troubleshooting | Reference depth. Turns the site into something linkable from issues. |
| **3** | `/tutorials/` hub + `existing-repo` + `first-repo`, then `non-code` and `team` | Brownfield first — it is the real adoption case. |
| **4** | `/compare/` | Needs the docs to link into. Highest inbound-search value of any page here. |
| **5** | `/teach/` decks and diagrams | Cheapest, via the `tedandlisa` skill; last because it depends on settled messaging. |

Phase 1 alone is a meaningful improvement over the current `/guide/` and is a
reasonable place to stop and reassess.

**Acceptance criteria, every phase:** all text consumes the design tokens, no
hardcoded colours · AA contrast maintained on both themes · one shared copy of
the `googtrans` logic · no horizontal scroll at 375px · every code block has a
copy button · every page ends with a next-step link · `validate_site.py` passes.

---

## 12. Decisions I need from you

1. **Generator or SSG** — stdlib Python (recommended, §7) or Eleventy/Astro?
2. **Is this Pages project git-connected?** (§7 risk)
3. **Translation scope** — native tier on three pages only (recommended, §9)?
4. **Phase 1 only, or the full set?**
5. **Compare page** — comfortable naming OpenWiki, Cursor and harness memory
   directly in a table, in the neutral tone of §5?


---

## 13. Phase 0 — built and verified, 2026-08-31

Decision on §12.1: **stdlib Python generator**, no npm. Built.

### What exists now

```
web/assets/site.css      341 lines   tokens, reset, nav, language widget, buttons,
                                     command block, .checks, .cmp, footer, print
web/assets/site.js       417 lines   language table, googtrans, dictionaries, theme,
                                     nav, copy, reveal, boot
web/layout/base.html     154 lines   the shell: head, nav, footer, script order
web/content/<route>/     meta.json + page.html + page.css [+ i18n.js, page.js]
web/static/              favicon.svg
scripts/build_site.py    175 lines   the generator
site/                    build output only
```

`web/` is the source; `site/` is generated. Sources moved out of `site/` because
Cloudflare Pages serves that whole directory — `site/_content/index/page.html`
would otherwise have been publicly fetchable.

### The duplication is gone

| | before | after |
| --- | --- | --- |
| CSS | 508 + 376 lines, inline per page | 341 shared + 169 + 94 |
| JS | 882 + 767 lines, inline per page | 417 shared + per-page dictionaries |
| landing page HTML | 140K | 83K |
| use-cases HTML | 108K | 59K |

Every page added from here costs a directory, not a stylesheet.

### How the port was verified

Not by eyeballing. Three checks, all passing:

1. **Cascade equivalence.** Both pages' CSS was parsed into every
   (media-context, selector, property) triple and the post-cascade value
   compared against the original: **0 missing, 0 changed** on both pages. The
   only additions are the three intended reconciliations below.
2. **Markup equivalence.** Body markup compared line by line with scripts and
   styles stripped: 479 -> 479 lines on the landing page, 324 -> 324 on
   use-cases. The only diffs are attribute *order* on two GitHub links and the
   deliberate i18n key rename.
3. **Live behaviour.** Served locally and driven in a browser against the
   original as a control: theme toggle, language dropdown (both tiers), Korean
   switch (`html lang`, `EN`->`KO` badge, translated hero and nav), the
   use-cases tabs (aria-selected, panel visibility, hash) and the copy button
   (`.copied`, "Copied" live region). Zero console errors on both pages.

### Drift found and reconciled

The two pages had already forked their "shared" layer. Design tokens were
byte-identical (0 differences across 80), but below that:

- `.check h3` vs `.check h3,.check h4` — use-cases had the superset. Shared
  takes the superset.
- The `@media print` block — use-cases had one extra line
  (`.tabpanel[hidden]`). Shared takes the superset.
- The copy-button i18n key was `hero.cta.copied` on the landing page and
  `cta.copied` on use-cases, for the *same* shared machinery. Normalised to
  `cta.copied`; `hero.cta.*` renamed to `cta.*` on the landing page.
- 22 further component-level value conflicts (`.hero`, `.icard`, `.strip`,
  `.section-lede`) turned out to be deliberate subpage tuning, not drift. They
  stay as page-level overrides — which is the right default for the docs pages,
  since all of them are subpages.

This is the drift §8 predicts, already present at two pages. It is the argument
for the generator, not against it.

### One bug worth recording

The generator's placeholder pattern was `[a-z_]+`, which does not match the
digits in `{{i18n}}`. That one substitution silently did not happen and the
dictionaries never reached the page — Korean stored the selection but never
applied. The named-placeholder check could not see it, because the pattern that
was broken was the same pattern the check used. `build_site.py` now also asserts
that no `{{...}}` survives into the output, which catches the class of bug
rather than the instance.

### Latent issue, not fixed

`.sign-off p` sets `font-size:var(--text-lg)`, and `--text-lg` is not defined in
the token block. The declaration is invalid and the size inherits. Pre-existing;
flagged rather than silently changed, since the intended size is unknown.

### Not done — blocked on §12.2 and a collision

`site/` is not yet gitignored, `scripts/validate_repository.py` is not updated,
`site/sync.sh` is not moved, and `/guide/` does not yet redirect. All four touch
files that currently carry **uncommitted changes made by someone else during
this session** — `site/sync.sh` and `scripts/validate_repository.py` were both
edited to add `site/clarity-bg.jpg` (a sign-off band background; the asset is
staged but nothing references it yet). Finishing Phase 0 means editing over that
work, so it waits for a decision.

Also discovered: `.github/workflows/pages.yml` deploys `./docs` to **GitHub
Pages** — a second, separate deploy target alongside Cloudflare Pages. Any
change to how `docs/` and `site/` relate has to account for both.


---

## 14. Decisions, 2026-08-31

Four answers from Daren, and what each one changes.

### 14.1 `/guide/` is KEPT

The 301 in §10 is cancelled. The guide is not a draft of the docs — it is a
different *format* for the same concept, and the two coexist. §10's mapping
table stays useful as a source of raw material for the docs pages, but nothing
is retired and the guide keeps its URL.

**The consequence worth catching:** §5 proposed `/teach/` as a media kit built
around new 101/201/301 decks. The guide already *is* the 101 deck — 18 slides,
translated, with a working language switcher. Building a second introductory
deck would put two of them on the same site saying the same thing.

So `/teach/` changes shape: it hosts the existing guide as the 101 rather than
replacing it, and adds only what is genuinely missing — a 201 and 301, the
workflow diagrams as downloadable SVG/PNG, and share-ready copy. That makes
`/teach/` cheaper than planned and removes the risk of the two competing.

**Nav** becomes six items — `Docs · Tutorials · Use cases · Guide · Compare ·
GitHub`. `/teach/` does not take a nav slot; it is a low-traffic media kit,
linked from the guide and the footer. Seven top-level items is too many, and
Guide earns the slot over Teach.

### 14.2 Cloudflare will be git-connected

So the build runs on deploy. Two settings have to change in the Pages dashboard,
which is a hand action:

| | now | needs to be |
| --- | --- | --- |
| build command | `bash site/sync.sh` | `bash scripts/sync.sh` |
| output directory | `site` | `site` (unchanged) |

`sync.sh` has to move out of `site/`, because `site/` becomes generated output
and is gitignored — a build script cannot live inside its own build output.

### 14.3 V5 lands on every page, replacing the sign-off

V5 stops being a landing-page treatment and becomes shared chrome. Since
`.sign-off` currently lives in `web/assets/site.css` and `base.html`, V5
replaces it in both — one edit, inherited by every page built afterwards,
including the twenty that do not exist yet.

**The coupling this creates with §9 (translation scope).** V5's text splitter is
gated to the three hand-translated dictionaries, because Google Translate would
translate per-glyph spans individually and destroy the effect. Machine locales
get one clean text node and the blur/opacity resolve only.

That means the §9 recommendation — native dictionaries on three pages, machine
tier everywhere else — now decides *which pages get the full V5 treatment*. The
two questions are no longer separable. Either accept that docs and tutorials get
the reduced-fidelity V5, or widen the native tier and pay the per-page
dictionary cost. Flagged rather than decided; it needs Daren.

### 14.4 Phase 0 completion is gated on the above

Confirmed. `site/` gitignored, `sync.sh` moved, `validate_repository.py`
repointed, all wait until V5 is folded in, so there is one writer in the tree
and one commit that moves the architecture.

### 14.5 Fixed on the way

`planning/site-plan.md` was at `docs/site-plan.md`, inside the GitHub Pages
deploy root. The next push to `main` would have published this internal planning
document to the public site. Moved.

`.github/workflows/pages.yml` deploying `./docs` to GitHub Pages is a second
deploy target alongside Cloudflare, and `docs/` has no `index.html` — so that
Pages site almost certainly 404s at its root and serves the guide only at
`/project-context-complete-guide.html`. Worth deciding whether it is still
wanted at all now that Cloudflare serves `/guide/` properly. Not touched.


---

## 15. V5 folded in, 2026-08-31

Handed over by `project-context-8d` as a six-hunk patch against `7b1df77`, and
verified identical on both pages before applying — which is what justified
putting all of it in the shared layer rather than per page.

### Where each hunk landed

| Hunk | Content | Destination |
| --- | --- | --- |
| 1 | dark band tokens | `web/assets/site.css`, in `:root` |
| 2 | light band tokens | `web/assets/site.css`, in `[data-theme="light"]` |
| 3 | the band, 59 lines | `web/assets/site.css`, replacing the old 3-rule `.sign-off` |
| 4 | markup | `web/layout/base.html`, before `<footer>` |
| 5 | `refreshSignOff()` hook | `web/assets/site.js`, end of `applyDict` |
| 6 | splitter, 184 lines | `web/assets/site.js`, as section 10; BOOT became 11 |

Plus `web/static/clarity-bg.jpg` (154,521 bytes, referenced root-absolute as
`url(/clarity-bg.jpg)` so it resolves from `/use-cases/` too).

**Nothing went into a page file.** `page.css` and `page.js` contain zero band
code on either page, so every page built from here inherits the band from the
layout without anyone remembering to add it.

### One improvement on the handoff

The patch shipped `signoffLang()`, which re-implemented BOOT's locale
resolution. The peer flagged the risk itself: if BOOT's order ever changed and
this copy did not, the band would split its text under a machine locale and
Google Translate would shred the one-glyph spans.

Both now call a single `resolveLang()`. `signoffLang()` is gone and BOOT's
inlined copy is gone with it — three callers, one answer, nothing to drift.

### Verified

- **Korean** — 12 glyphs, 4 eojeol boxes (`명확함은 / 맥락과 / 함께 / 온다.`),
  and no jamo: `Intl.Segmenter` keeps Hangul syllables whole.
- **Traditional Chinese** — 7 boxes, 9 glyphs, with `晰，` and `來。` glued so the
  comma and full stop can never begin a line.
- **The machine-tier gate** — under Japanese (`googtrans=/en/ja`), the band has
  **0 spans and a single text node**. This is the one that matters: it is what
  stops Google translating two dozen one-glyph spans individually.
- **Round trip** en → zh-TW → ko → ja with no residue; the band is rebuilt from
  `I18N[lang][key]`, never from the DOM, so it is idempotent by construction.
- **Seam** — 0px between band and footer, and `--seam-1` matches `--bg-subtle`
  in both themes, which is the footer's actual ground.
- **Contrast** — 5.72:1 light, 7.19:1 dark, reconstructing the composite in
  canvas and sampling under the glyph boxes. `project-context-8d` independently
  measured 5.59:1 on this build in the tightest case (ko / light / 375), so two
  reconstructions agree. Against a 4.5 target that is ~1.1 of headroom, and the
  tagline is 52px display type, where AA asks only 3:1.

  A first pass here reported 4.70:1. That number was wrong, and the reason is
  worth keeping: the sampling selector was `.sign-line .sg, .sign-line`, so it
  swept the whole line *box* — including the inter-word gaps and the slack left
  by `text-wrap:balance`, where no glyph actually sits. The worst pixel it found
  was at x=104, off the end of the first word. Restricting the sweep to `.sg`
  boxes gives 5.72. (The peer proposed a different cause — that the scrim's two
  gradients had been composited in the wrong order. That one was not it: CSS
  paints the first-listed layer on top, and the harness already drew
  image → radial → linear. Recorded because the wrong diagnosis is as easy to
  inherit as the wrong number.)

  The scrim was left exactly as tuned. It is deliberately as light as the
  numbers allow; darkening it to buy headroom would flatten the photograph, and
  the headroom turned out to be there already.

### Two bugs I introduced and fixed

Applying hunk 6 broke the file twice, both times on comment boundaries: the
hunk's added lines begin *inside* a comment block and end *inside* another, so
replacing the old `10. BOOT` banner wholesale removed the `/*` that opened the
new section and the `*/` that closed the next one. `node --check` caught both.
Worth remembering when porting patches that start mid-comment.

### `--text-lg` resolved

The dead token flagged in §13 is gone: it lived only in the old `.sign-off p`
rule, which hunk 3 replaced. `.sign-line` sets its own
`font-size:clamp(1.65rem,5.2vw,3.25rem)`. Grepped for sibling `--text-*`
references — there are none.

### Still deferred: a shared dictionary tier

`brand.tagline` already existed in both dictionaries with the correct Korean and
Chinese, so V5 needed no new keys. But the peer's wider point stands: every page
carries its own copy of the chrome keys (`nav.*`, `ui.*`, `footer.*`, `brand.*`,
`cta.*`) in three locales, which is the surface that produced the
`hero.cta.copied` / `cta.copied` drift in §13. At twenty pages that is a
liability. A shared dictionary tier merged under the page dictionary is the fix,
and it should be its own change — V5 first, verified; the i18n refactor next, on
its own, also verified.


### Audit by `project-context-8d`, after the port

Read-only pass over the ported tree, checking the details that fail silently
rather than loudly. All present: the band-specific `prefers-reduced-motion`
override (the global rule only clamps duration to `.001ms`, so without this the
opening frame still flashes), `document.fonts.ready → layoutSignOff` (offsets
are measured, so they are wrong against fallback metrics for Noto CJK), the
debounced resize handler, the a11y layer, `max-height:720px`, `inset:-6%`, and
the 360px padding guard.

One note from that audit worth carrying into the shared-dictionary work: the
peer reports the Use cases dictionary was generated *from its markup*, which is
why it never drifted while the hand-maintained one did. If that holds,
generating page dictionaries from their own `data-i18n` attributes may be
cheaper than a shared tier — or complementary to it. Unverified here; it is a
claim about how that page was built, not something the artefacts show.


---

## 16. i18n drift is now a build error

§8 asked for something to stop twenty prose pages forking the canon. The first
piece of it exists, and it came out of the two drifts that actually happened
tonight rather than from imagining what might.

`scripts/build_site.py` now derives the expected key set from the **rendered
page** and checks it against that page's dictionary before the file is written.
Three failures, all hard:

| Failure | Real example |
| --- | --- |
| markup uses a key the `en` dictionary lacks | `hero.cta.copied` vs `cta.copied` — §13 |
| a `data-i18n-attr` key is absent | same class, harder to spot |
| a locale is missing a key `en` has | `footer.s1–s6`, per `project-context-8d` |

The third is the nastiest, because a missing key renders as an empty string only
in the locale nobody on the team reads.

Verified by deliberately introducing each of the three and confirming the build
fails, then confirming the clean build still passes. A check that has never been
seen to fail is not evidence of anything.

**Credit and correction.** The idea is `project-context-8d`'s: the Use cases
dictionary never drifted because it was *generated from its markup*, while the
hand-maintained page drifted twice. They parked the original scripts
(`build_i18n.py`, `check.js`) and were straight that they are scratch — a
hardcoded filename, no arguments, and an `eval()` of the dictionary literal.
Not imported. What transferred is the principle, moved into the build so it
runs every time rather than when someone remembers.

**This does not close §15.** As they put it, the two problems are different:
generation fixes whether the dictionary and the markup *agree*; a shared tier
fixes where shared strings *live*. Tonight produced one of each. This change
does the first. Every page still carries its own copy of `nav.*`, `ui.*`,
`footer.*`, `brand.*` and `cta.*` in three locales, and the check will now
notice when those copies disagree — but noticing is not the same as not having
five copies. The shared tier is still worth doing, and still its own change.


### The fourth case is a warning, and must stay one

The obvious next check — "dictionary has a key no markup uses" — looks
symmetrical with the three above. It is not, and making it a hard failure would
be a mistake.

`cta.copied` is the counter-example, and it is real: verified as the *only*
orphan on either page, and it is read from the dictionary by the copy handler
when the button flashes. It carries no `data-i18n` anywhere. A build that failed
on it would be failing on a key that works correctly — and the first person to
hit that concludes the check is noise and switches it off, which is worse than
never having had it.

So the build searches `site.js` and the page's `page.js` as well, and warns only
about keys nothing can reach. Today that is zero on both pages. The asymmetry in
one line: **markup-without-key is always a bug; key-without-markup usually
isn't.** The rule is written into the docstring of `orphan_keys()`, next to the
code, because that is where someone about to "fix the inconsistency" will be.

Credit to `project-context-8d`, who flagged the trap before it was walked into.

### A rule for negative tests, learned twice tonight

**A negative test must be shown to perturb the thing it claims to perturb.
Assert the mutation landed before believing the failure — or the pass.**

This bit twice within an hour, in two different shapes:

1. Testing that a missing markup key fails the build, the mutation targeted
   `data-i18n="nav.record"` in `page.html`. Nav comes from `meta.json` now, so
   the string was not there and `.replace()` returned the input unchanged. The
   build went green and very nearly certified a check that had done nothing.
2. Testing the orphan warning, keys were inserted after the `I18N:KO:START`
   marker line rather than after the `"ko": {` line, which put them at the top
   level of the object. The build failed — but for the wrong reason, reporting
   `zz.dead.key` as a locale missing 153 keys.

Case 1 is the dangerous one, because its failure mode is silence. Case 2 was
loud, and it happened to demonstrate that the checks report malformed input
rather than passing it.

Both tests now assert their own setup: case 1 asserts the target string exists
before replacing it, case 2 re-parses the mutated dictionary and asserts all
three locales are intact and carry the key. Any test whose setup can fail
quietly will eventually certify a check that does nothing.


---

## 17. Five footer and copy changes, 2026-08-31

Relayed from Daren by `project-context-8d`, applied to the shared layer so both
pages and every future page get them from one place.

1. **GitHub footer link is now the mark, not the URL.** `footer_html()` escapes
   `label`, so an icon cannot travel through it. Added a named-icon table
   (`FOOTER_ICONS`) and an optional `"icon"` field in `meta.json`, which keeps
   the SVG out of the content files and gives every future page the same one.
   The anchor carries `aria-label="GitHub"` since the visible text is gone, and
   the `<svg>` is `aria-hidden`.
2. **Licence paragraph is full width** — the `max-width:var(--maxw-prose)` cap
   is gone.
3. **Seventh capability** — `footer.s7`, "AI transformation" / "AI 전환" /
   "AI 轉型".
4. **Korean copy** — `brand.tagline` → 맥락이 만들어내는 명확함, and
   `footer.agency`'s slogan half → 스마트 엔지니어링, 목적 지향적 디자인. The
   `<b>` around *AI Innovation Studio* and the 「자율 에이전트 시대를 위한」 opening
   are unchanged, as is zh-TW.
5. **Machine-translation note removed** from the language selector — markup,
   CSS rule, and the `ui.langAutoNote` key in all three locales. The
   "Machine translated" group label (`ui.langAuto`) stays.

### The checks earned their keep immediately

Both new checks fired on their first real change, which is the outcome §16 was
built for:

- Adding the `footer.s7` markup before the dictionary values **failed the
  build**: `markup uses 1 key(s) absent from the 'en' dictionary: footer.s7`.
- Deleting the note markup while the key remained produced exactly the intended
  warning on both pages — `ui.langAutoNote is reachable from neither markup nor
  scripts` — at exit 0, not a failure. Removing the key cleared it. This was the
  first genuine orphan the check has seen, and it behaved as designed.
- Removing that key also left a trailing comma, because it was last in its
  locale block. The parser caught that too rather than emitting broken JS.

### One correction to the handed-over CSS

The icon alignment shipped as `display:inline-flex;align-items:center`, which
left the mark riding 3px high: `.foot-inline` aligns its children on the text
baseline, and an icon-only inline-flex box has no text to derive a baseline
from, so it is aligned by its bottom edge instead. Adding `align-self:center`
centres it against the flex line. Measured at 1280px: centre-to-centre delta
0.0px against the adjacent text link, down from 3.0px.

### Two things flagged rather than changed

**The licence line length.** At 1120px the paragraph now runs ~158 characters
per line, against a comfortable maximum of roughly 75–90. `--maxw-prose` was
presumably there for exactly this reason. Daren asked for full width explicitly,
so it ships, but it is worth a look on a wide display.

**The Korean corrections are corrections.** Daren's message wrote 「명황함」 and
「목적 지형적」. Neither is a word — 명확함 is clarity (명황함 is not a term), and
지형 is terrain where 지향 is oriented-toward. Both are a single jamo from the
obviously intended word. `project-context-8d` caught this and is confirming with
him; the corrected forms are what is in the build. If he meant something else,
this is the thing to re-check first.
