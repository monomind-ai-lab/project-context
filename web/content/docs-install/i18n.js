/* =====================================================================
   1. DICTIONARY
   English only, deliberately: per the site plan's translation tiers, the
   docs pages run on the machine tier. The language widget still works —
   site.js falls back to `en` for the hand-translated locales and routes
   everything else through the shared machine-translation path. Adding a
   hand translation later means adding a `ko` / `zh-TW` block with the
   SAME keys; the build will enforce the symmetry.
   Values may contain trusted inline <b>/<code>/<em> only.
   ===================================================================== */
const I18N = {
"en": {
"nav.skip": "Skip to content",
"nav.home": "Home",
"nav.docs": "Docs",
"nav.usecases": "Use cases",
"nav.guide": "Guide",
"ui.theme": "Toggle theme",
"ui.lang": "Language",
"ui.langSearch": "Search languages…",
"ui.langNative": "Translated by hand",
"ui.langAuto": "Machine translated",

"hero.eyebrow": "Install",
"hero.title": "Read the plan <b>before</b> anything is written.",
"hero.sub": "This tool edits <code>AGENTS.md</code> and <code>CLAUDE.md</code>, and any careful reader stops right there. So the promises come first, the preview command comes second, and the write comes only after you have read its plan.",

"prom.eyebrow": "before the command",
"prom.title": "What it will never do to your repo",
"prom.lede": "Six promises, enforced by the installer itself and covered by the test suite — not aspirations.",
"prom.c1.title": "Byte-for-byte preservation",
"prom.c1.body": "Existing context files are preserved byte-for-byte.",
"prom.c2.title": "One managed block, nothing else",
"prom.c2.body": "Existing <code>AGENTS.md</code> / <code>CLAUDE.md</code> content is preserved outside one clearly marked managed block — including file mode and CRLF line endings.",
"prom.c3.title": "Review, never migrate",
"prom.c3.body": "Unknown or overlapping memory — old status files, ADRs, lessons folders — is reviewed and classified, never migrated behind your back.",
"prom.c4.title": "Halt before harm",
"prom.c4.body": "Malformed blocks, unsafe symlinks and non-UTF-8 instructions stop apply mode before any write.",
"prom.c5.title": "Add-ons are opt-in, each",
"prom.c5.body": "Optional tools need a separate, informed opt-in each. Nothing is a default checklist.",
"prom.c6.title": "A small, inspectable footprint",
"prom.c6.body": "13 files. One skill. Zero runtime dependencies — stdlib Python 3.10+. The installer itself is never copied into your repo.",

"inst.eyebrow": "the command",
"inst.title": "Dry-run first, apply second",
"inst.lede": "The CLI is deterministic: the plan <code>--dry-run</code> prints is exactly what <code>--apply</code> will do, and running it twice changes nothing the second time.",
"inst.step1": "1 · preview the exact file plan — nothing is written",
"inst.step2": "2 · apply the plan you just read",
"inst.pipx": "prefer pipx · install once, keep init / inspect / review / doctor on your path",
"inst.onboard": "<b>One question before anything else.</b> The initializer asks whether the repository is brand-new or existing — because an existing project may already hold status files, ADRs or lessons that deserve review, and a brand-new one has nothing to review. It then adapts to software, document, research, writing, mixed or general work, proposes the profile and the exact file changes, and waits for approval.",

"har.eyebrow": "per harness",
"har.title": "How your agent finds it",
"har.lede": "Installation creates two complementary trigger paths, so no single harness is required: harnesses that support the Agent Skills convention discover the installed skill directly, and a managed block in the root agent instructions routes everything else. This is the whole block, verbatim:",
"har.blockfoot": "everything outside these two markers is never touched",
"har.th.env": "Environment",
"har.th.how": "How the protocol reaches it",
"har.r1.how": "Discovers the installed skill through the pointer at <code>.claude/skills/project-context/SKILL.md</code>; the managed block in <code>CLAUDE.md</code> covers it too.",
"har.r2.how": "Agent mode with repository access. The managed block in <code>AGENTS.md</code> routes them into the record before substantial work.",
"har.r3.how": "Filesystem, workspace or project access to the folder. The managed block applies, and the paste-in prompt below works with no tooling at all.",
"har.r4.how": "If it can read and write files in the project folder, it is supported — the managed block is the delivery path, and no launcher is required.",

"pr.eyebrow": "zero tooling",
"pr.title": "No Python, no CLI — one prompt",
"pr.lede": "Paste this into any AI agent that can read and edit the target folder. The agent asks the onboarding question, shows you the plan, and waits for approval — the same guarantees, delivered by the agent instead of the CLI.",
"pr.label": "install prompt · paste into your agent",
"pr.copy": "Copy the install prompt",

"ver.eyebrow": "verify",
"ver.title": "Prove it took",
"ver.lede": "A read-only doctor checks the install end to end. It reports; it never rewrites. With pipx it is simply <code>project-context doctor --target .</code>",
"ver.label": "health check · read-only",
"ver.p1": "required core files",
"ver.p2": "installed scaffold version",
"ver.p3": "NOW.md freshness",
"ver.p4": "duplicate decision and learning IDs",
"ver.p5": "broken relative links",
"ver.p6": "reachability — something still delivers the protocol",
"ver.reach": "The last check is the one that matters. A healthy result names the routes that carry the protocol into a session — the managed block, the harness pointer, any hooks. <code>no-delivery-path</code> is an error, because perfect files that nothing ever loads would otherwise report healthy.",

"un.eyebrow": "uninstall",
"un.title": "Leaving is four deletions",
"un.lede": "There is no uninstall command because nothing needs one: everything the installer creates is a plain file in your repo. Removal is deleting them.",
"un.c1.title": "Delete the records",
"un.c1.body": "Remove the <code>project-context/</code> directory. Consider keeping a copy first — it holds your project's decisions and learnings, not the tool's.",
"un.c2.title": "Delete the skill and its pointer",
"un.c2.body": "Remove <code>.agents/skills/project-context/</code> and the pointer at <code>.claude/skills/project-context/</code>.",
"un.c3.title": "Remove the managed block",
"un.c3.body": "In <code>AGENTS.md</code> / <code>CLAUDE.md</code>, delete everything between <code>&lt;!-- project-context:start --&gt;</code> and <code>&lt;!-- project-context:end --&gt;</code>, markers included. The rest of the file was never touched.",
"un.c4.title": "If you opted into hooks",
"un.c4.body": "Remove the two Project Context entries from <code>.claude/settings.json</code> — they are the ones whose commands call <code>context_triggers.py</code>. Hooks exist only if you explicitly opted in.",

"next.eyebrow": "next",
"next.title": "You have three new files. Now meet them.",
"next.lede": "The moment after install is where adoption is usually lost. The records page walks each file — what it answers, what does not belong in it, and what a good entry looks like next to a bad one.",
"next.cta": "The three records, annotated",
"next.cta2": "The session loop",

"cta.scroll": "scroll →",
"cta.copy": "Copy the install command",
"cta.copied": "Copied",
"cta.guide": "Read the guide",
"brand.tagline": "Clarity comes with context.",
"footer.agency": "<b>AI Innovation Studio</b> for the autonomous agent era — intelligent engineering, intentional design.",
"footer.s1": "Product strategy",
"footer.s2": "Agent Experience (AX)",
"footer.s3": "Agent &amp; harness engineering",
"footer.s4": "Advanced RAG",
"footer.s5": "Brand identity",
"footer.s6": "Web experience",
"footer.s7": "AI transformation",
"footer.home": "Home",
"footer.license": "<b>MIT + Commons Clause</b> — free to use, modify, and ship in your products, including commercially; the components themselves may not be sold or redistributed standalone."
}
};
