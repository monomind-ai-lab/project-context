/* =====================================================================
   1. DICTIONARY
   English only, by decision (site-plan §9): the docs reference pages run
   on the machine-translation tier. Only the shared chrome (nav, language
   widget, footer, sign-off band) and the copy-button machinery carry
   data-i18n keys here; the page body is plain English and
   machine-translated. If this page is ever promoted to the
   hand-translated tier, add `ko` and `zh-TW` blocks with the SAME keys —
   the build enforces parity for every locale present.
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
"cta.scroll": "scroll →",
"cta.copy": "Copy the install command",
"cta.copied": "Copied",
"cta.guide": "Read the guide",
"footer.agency": "<b>AI Innovation Studio</b> for the autonomous agent era — intelligent engineering, intentional design.",
"brand.tagline": "Clarity comes with context.",
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
