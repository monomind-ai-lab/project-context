---
target: docs/project-context-complete-guide.html
total_score: 25
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 0
timestamp: 2026-09-03T18-16-46Z
slug: docs-project-context-complete-guide-html
---
Method: dual-agent (A: design review · B: detector + browser evidence), run in isolation. A third measurement by the parent settled a disagreement between them.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Counter and progress track exactly under real key events. Content clipped silently at 1280x720 on two slides — fixed. |
| 2 | Match System / Real World | 3 | Strong engineer's register, but "the doctor", "the trigger gate", "the managed block" are coinages used before they are defined. |
| 3 | User Control and Freedom | 2 | 14 slides, one arrow press at a time. No contents menu — the intake chose menu items ["start"], so the template's TOC builder is inert. |
| 4 | Consistency and Standards | 3 | Record inventory disagreed across slides 5, 6 and 10 — fixed. `lead` still present on 9 slides and absent on 5. |
| 5 | Error Prevention | 3 | Slide 11's guarantees are genuinely strong; they arrive seven slides after the moment of hesitation. |
| 6 | Recognition Rather Than Recall | 2 | Slide 3 uses four terms defined 5-6 slides later; slide 9 says "the owner" before slide 10 defines it. |
| 7 | Flexibility and Efficiency | 3 | Copy button now wired. Keyboard hint still advertises only arrows though Home/End/PageUp/PageDown all work. |
| 8 | Aesthetic and Minimalist Design | 4 | One type scale (12 x 47px), exactly one accent element per slide, zero of 239 text boxes below 4.5:1. |
| 9 | Error Recovery | n/a | Read/Persuade surface accepting no input — no user error to recover from. |
| 10 | Help and Documentation | 2 | The deck is the documentation, yet ships empty speaker notes, no contents, no glossary for its coined terms. |
| **Total** | | **25/36** | **Good** (two heuristics' worth above the midpoint; 9 scored, 1 n/a) |

## Design Specificity Verdict

The words are specific to Project Context. The composition is not. Strip the copy and what remains is the `monomind-deck` component gallery in default order, thirteen times. Nine of fourteen slides survive a find-and-replace onto an unrelated developer tool with no visual change.

The sharpest observation from the review: fourteen slides argue that a project's state should live as readable Markdown in the repository, and the reader never sees one. The only artifact rendered is a seven-line YAML header. No filled `NOW.md`, no diff, no repository tree with records sitting among real source files.

Deterministic scan: 30 findings, all `warning` (24 quality, 6 slop) once the HTML parsers were staged — the entrypoint runs degraded without them and undercounts to 6. The 12 `low-contrast` findings are false: measured against painted pixels, 239 rendered text boxes have a minimum ratio of 4.71:1, and the element the detector calls 3.1:1 measures 5.11:1. Both detectors resolved the backdrop to the light-theme token rather than the painted dark ground. `side-tab` was a degraded-mode regex artifact. `overused-font` is the MonoMind brand face.

No user-visible overlay is available: injection succeeded over CDP for measurement, but the normal attach path writes a script tag into the target file and was deliberately skipped.

## Overall Impression

The writing is the best thing here by a distance, and the restraint against the design system is real. The single biggest opportunity is that a deck about making project state legible never shows the reader a record.

## What's Working

1. Sentence-level authorship with a point of view. "Documentation explains what the code does — the code already does that." "A perfect record set no session reads is worth nothing." Not generated filler.
2. Slide 8 is exemplary: one idea, one artifact, four rows, no decoration, and it advances the most defensible claim in the deck.
3. Genuine discipline against the shipped system — one accent element per slide across all seven that use one, one type scale, no invented colour. And slide 12 exists at all: shipping an "unbuilt commands" slide inside a persuasion deck is an editorial choice most authors would not make.

## Priority Issues

- **[P2] Content clipped at 720p.** Slides 7 and 10 lost their closing callout at 1280x720 with no scrollbar and no indication — including the only instruction for a reader who disagrees with what an owner pushed. **Fixed**: both promoted into their slide's lead. *Command: /impeccable adapt*
- **[P2] The deck's one call to action had no copy button.** The template ships the entire mechanism and the prompt already carried the binding id; it was wired to nothing. **Fixed.** *Command: /impeccable polish*
- **[P2] CLI flags with no command named.** An engineer told to paste a prompt into an agent cannot act on bare `--dry-run`. **Fixed**: both flags now name `project-context init`. *Command: /impeccable clarify*
- **[P3] Reassurance arrives seven slides after the fear.** Slide 11 is the strongest trust asset and is filed under Reference; the hesitation is on slide 4. **Left alone** — reordering changes the deck's narrative and is the author's call.
- **[P3] Slide 13 occupies the peak-end slot with a directory listing.** Its one persuasive fact, 90 tests, is set at 13.5px as a tree descriptor. **Left alone** — same reason.

## Persona Red Flags

**Jordan (first-timer evaluating adoption)**: "Show me a record" goes unanswered — four chips naming files, one YAML header, a directory tree of the scaffold rather than a consumer repo. Coined vocabulary lands before its definitions on slides 3 and 9.

**Casey (distracted, on a phone)**: under Chrome's mobile ICB rule at 390px the hamburger and slide counter render outside the viewport entirely. Emulation-only finding, unconfirmed on a device — and it is shipped chrome, not this deck's content.

**Sam (accessibility-dependent)**: 14 of 20 tab stops have no focus indicator, `#deck-progress` carries an invalid `aria-hidden=""`, and heading order skips h2 to h4. All three are in shipped chrome or shipped component markup.

## Minor Observations

- 25 `notranslate` wrappers protect terms against a translation UI this deck does not have — the English-only build stripped it. Harmless, inconsistently applied.
- Speaker notes ship as `[]` for a 14-slide guide with five coined terms.
- Slide 7's frontmatter is `p.code`; a screen reader renders it as one run-on paragraph.
- `created: 2026-09-03` in the sample record will visibly date the deck.
- The deck reopens where you left off via localStorage, so a shared link can start mid-deck.

## Reported, not fixed — all in shipped template chrome

1. **Focus indicator dead on 14 of 20 tab stops.** `.slide.dark .brand-mark { box-shadow: none }` (0-3-0) beats `a.brand-mark:focus-visible` (0-2-1). Every slide is `.dark`. The comment in the template shows the author anticipated the collision; the fix loses.
2. **`#deck-progress` has `aria-hidden=""`.** An empty string is not a valid ARIA token, so it is not hidden — the opposite of intent.
3. **Fixed chrome outside the viewport under mobile ICB** at 390px.
4. **Tab leaves the deck off-snap**, landing mid-slide with the counter still reading the previous number.
5. **Heading order h2 to h4** — the `qcard` and `dg-chip` components ship `h4`.
6. **Personal metadata in the embedded artwork.** The 79KB inline JPEG carries XMP `dc:creator: Daren Kang` and `dc:title: Project Context 16-9 - 9`. This ships in every deck built from `monomind-deck`, and this one is published publicly.
