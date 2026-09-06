#!/usr/bin/env python3
"""Render site/_content/** into the deployable site/ folder.

Zero dependencies, stdlib only — the same constraint the shipped CLI holds
itself to. Cloudflare Pages runs this through site/sync.sh.

Content model, one directory per route under web/content/:

    meta.json    route, output path, title, description; optional `nav` /
                 `footer_links` overrides (legacy — the global header nav and
                 footer columns live once in web/nav.json)
    page.html    the body fragment that goes inside <main id="main">
    page.css     optional page-only CSS, inlined into <style>
    i18n.js      optional `const I18N = {...}`, emitted before site.js
    page.js      optional page behaviour, emitted after site.js

Everything shared — tokens, reset, nav, language widget, footer, print rules,
and the whole translation/theme/copy machinery — lives once in web/assets/ and
is linked, not copied. Adding a page costs a directory, not a stylesheet.

web/ is the source; site/ is build output only, and nothing under it is edited
by hand or committed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "web"
CONTENT = SRC / "content"
LAYOUT = SRC / "layout" / "base.html"
ASSETS = SRC / "assets"
STATIC = SRC / "static"
NAVSPEC = SRC / "nav.json"
OUT = ROOT / "site"

PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")

# The canonical origin. Every absolute URL the build emits — canonical links,
# og:url, the sitemap, llms.txt, JSON-LD ids — is derived from this one string.
SITE_URL = "https://projectcontext.monomind.one"

# Routes served from site/ that build_site.py does not generate: the two decks
# are standalone documents copied in by scripts/sync.sh. They still belong in
# the sitemap and in llms.txt, so they are named here with the metadata a
# generated page would have carried in its meta.json.
EXTRA_ROUTES = (
    {
        "route": "/guide/builders/",
        "title": "The builder's deck — Project Context",
        "description": "A 19-slide deck for anyone working in a repository: the three records, "
                       "the session loop, the record model and evidence anchors, installing it, "
                       "and what the doctor checks afterwards.",
    },
    {
        "route": "/guide/owners/",
        "title": "The owner's deck — Project Hub",
        "description": "A 17-slide deck for anyone overseeing several repositories: scaffold versus "
                       "instance, the boundary between the two repositories, why a push arrives as a "
                       "pull request, the budgets, and what a Hub costs.",
    },
)

# The reading order llms.txt presents, which is a curated path rather than the
# sitemap's flat list: an answer engine that follows it in order learns the two
# products in the order a person would. A route absent here still reaches the
# sitemap; it simply does not get a recommended position.
LLMS_SECTIONS = (
    ("Start here", ("/", "/docs/", "/use-cases/")),
    ("Project Context — for builders working in a repository",
     ("/docs/install/", "/docs/records/", "/docs/operate/", "/docs/builders-guide/")),
    ("Project Hub — for owners overseeing several repositories",
     ("/project-hub/", "/project-hub/owners-guide/")),
    ("Slide decks", ("/guide/", "/guide/builders/", "/guide/owners/")),
)

# The global header nav and footer columns, defined ONCE in web/nav.json.
# A page's meta.json `nav` / `footer_links` still wins when present — the
# docs pages rely on that until their migration — but a page that omits
# them gets these.
_navspec = json.loads(NAVSPEC.read_text()) if NAVSPEC.exists() else {}
GLOBAL_NAV: list[dict] = _navspec.get("nav", [])
GLOBAL_FOOTER_COLUMNS: list[dict] = _navspec.get("footer_columns", [])


def page_route(output: str) -> str:
    """The route a page is served at, derived from its output path.
    `index.html` -> `/`, `use-cases/index.html` -> `/use-cases/`."""
    route = "/" + output
    if route.endswith("index.html"):
        route = route[: -len("index.html")]
    return route


def is_current(href: str, route: str) -> bool:
    """Whether an absolute nav href points at the page being built. A href
    carrying a fragment (`/#what`) is a jump, never the current page; an
    external URL never matches either."""
    if "#" in href or href.startswith(("http://", "https://")):
        return False
    return href.rstrip("/") == route.rstrip("/")


def asset_version() -> str:
    """Cache-buster derived from the shared assets, so a CSS edit invalidates
    the browser cache without anyone remembering to bump a number."""
    import hashlib

    h = hashlib.sha256()
    for name in sorted(("site.css", "site.js")):
        p = ASSETS / name
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


def nav_anchor(link: dict, route: str, cls: list[str], indent: str) -> str:
    """One nav <a>. `current` from meta is honoured (legacy override navs);
    otherwise it is derived from the page's output route."""
    attrs = [f'href="{html.escape(link["href"])}"']
    cls = list(cls)
    body = html.escape(link["label"])
    if link.get("external"):
        cls.append("notranslate")
        attrs.append('translate="no"')
        attrs.append('rel="noopener noreferrer"')
        attrs.append('target="_blank"')
        # Add external link icon
        body += ' <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline;margin-left:4px;vertical-align:-2px"><path d="M2 10H1V1h9v1M11 1l-4 4M11 1v3.5M11 1h-3.5"/></svg>'
    if link.get("current") or is_current(link["href"], route):
        attrs.append('aria-current="page"')
    if link.get("i18n"):
        attrs.append(f'data-i18n="{html.escape(link["i18n"])}"')
    cls_attr = f'class="{" ".join(cls)}" ' if cls else ""
    return f'{indent}<a {cls_attr}{" ".join(attrs)}>{body}</a>'


def nav_html(links: list[dict], route: str = "", mobile: bool = False) -> str:
    """Render one nav link list. The desktop and mobile navs are the same list
    rendered twice — they cannot drift because there is only one source.

    A link with `items` is a dropdown: on desktop it renders as a disclosure
    (a real <button> trigger + panel, wired up in site.js §7, same house
    pattern as the language picker); on mobile the group is flattened into
    the list under a small header. A link with `cta` renders as the compact
    pill button instead of a plain nav link."""
    out = []
    indent = "    " if mobile else "      "
    for n, link in enumerate(links):
        if link.get("items"):
            label = html.escape(link["label"])
            i18n = f' data-i18n="{html.escape(link["i18n"])}"' if link.get("i18n") else ""
            if mobile:
                out.append(f'{indent}<span class="nav-mobile-hd"{i18n}>{label}</span>')
                for item in link["items"]:
                    if item.get("heading"):
                        # A group label inside a dropdown. On mobile the whole
                        # dropdown is already flattened under its own header, so
                        # a group reads as a sub-header rather than a second nav.
                        h = html.escape(item["heading"])
                        hi = f' data-i18n="{html.escape(item["i18n"])}"' if item.get("i18n") else ""
                        out.append(f'{indent}<span class="nav-mobile-sub"{hi}>{h}</span>')
                        continue
                    out.append(nav_anchor(item, route, ["nav-sub"], indent))
            else:
                bid, pid = f"navDropBtn{n}", f"navDropPanel{n}"
                out.append(f'{indent}<div class="navdrop">')
                out.append(f'{indent}  <button type="button" class="nav-link navdrop-btn" id="{bid}" '
                           f'aria-haspopup="true" aria-expanded="false" aria-controls="{pid}">'
                           f'<span{i18n}>{label}</span><span class="caret" aria-hidden="true"></span></button>')
                out.append(f'{indent}  <div class="navdrop-panel" id="{pid}" hidden>')
                for item in link["items"]:
                    if item.get("heading"):
                        # Not a link and not focusable: a caption for the group
                        # under it, so a seven-item panel reads as three short
                        # lists rather than one long one. `role="presentation"`
                        # keeps it out of the menu's item count for a screen
                        # reader, which would otherwise announce it as a choice.
                        h = html.escape(item["heading"])
                        hi = f' data-i18n="{html.escape(item["i18n"])}"' if item.get("i18n") else ""
                        out.append(f'{indent}    <p class="navdrop-hd" role="presentation"{hi}>{h}</p>')
                        continue
                    out.append(nav_anchor(item, route, [], indent + "    "))
                out.append(f'{indent}  </div>')
                out.append(f'{indent}</div>')
            continue
        if link.get("cta"):
            cls = ["nav-mobile-cta"] if mobile else ["nav-cta"]
        else:
            cls = [] if mobile else ["nav-link"]
        out.append(nav_anchor(link, route, cls, indent))
    return "\n".join(out)


# Inline marks usable as a footer link's body. `label` is escaped, so an icon
# cannot travel through it; a named icon keeps the markup out of the content
# files and gives every future page the same one.
FOOTER_ICONS = {
    "github": ('<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" aria-hidden="true" focusable="false"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>'),
}


def footer_html(links: list[dict]) -> str:
    out = []
    for i, link in enumerate(links):
        if i:
            out.append('          <span class="sep" aria-hidden="true">·</span>')
        attrs = [f'href="{html.escape(link["href"])}"']
        cls = ""
        if link.get("external"):
            cls = 'class="notranslate" translate="no" '
            attrs.append('rel="noopener"')
            attrs.append('target="_blank"')
        if link.get("i18n"):
            attrs.append(f'data-i18n="{html.escape(link["i18n"])}"')
        icon = FOOTER_ICONS.get(link.get("icon", ""))
        if icon:
            # the visible text is gone, so the name has to reach assistive tech
            attrs.append(f'aria-label="{html.escape(link["label"])}"')
            body = icon
        else:
            body = html.escape(link["label"])
        out.append(f'          <a {cls}{" ".join(attrs)}>{body}</a>')
    return "\n".join(out)


def footer_columns_html(columns: list[dict], route: str) -> str:
    """The global multi-column footer nav (web/nav.json `footer_columns`).
    Rendered only for pages WITHOUT a legacy `footer_links` override, so the
    docs pages keep their inline list until they are migrated."""
    out = []
    for col in columns:
        hd_i18n = f' data-i18n="{html.escape(col["i18n"])}"' if col.get("i18n") else ""
        out.append('      <div class="foot-col">')
        out.append(f'        <h3 class="foot-col-hd"{hd_i18n}>{html.escape(col["label"])}</h3>')
        out.append('        <ul>')
        for link in col.get("links", []):
            attrs = [f'href="{html.escape(link["href"])}"']
            cls = []
            if link.get("external"):
                cls.append("notranslate")
                attrs.append('translate="no"')
                attrs.append('rel="noopener"')
                attrs.append('target="_blank"')
            elif link.get("notranslate"):
                # A same-origin link whose label is a literal — a filename, a
                # product name — rather than a phrase to be translated.
                cls.append("notranslate")
                attrs.append('translate="no"')
            if link.get("current") or is_current(link["href"], route):
                attrs.append('aria-current="page"')
            if link.get("i18n"):
                attrs.append(f'data-i18n="{html.escape(link["i18n"])}"')
            icon = FOOTER_ICONS.get(link.get("icon", ""))
            body = html.escape(link["label"])
            if icon:
                # icon + visible text, same GitHub mark as the legacy inline list
                body = icon + body
            cls_attr = f'class="{" ".join(cls)}" ' if cls else ""
            out.append(f'          <li><a {cls_attr}{" ".join(attrs)}>{body}</a></li>')
        out.append('        </ul>')
        out.append('      </div>')
    return "\n".join(out)


def i18n_keys(js: str) -> dict[str, set[str]]:
    """Locale -> key set, parsed from a page's `const I18N = {...};` block.

    The dictionaries carry /* ... */ marker comments delimiting the machine-
    swappable locale blocks, so comments are stripped before the literal is
    read as JSON.
    """
    body = re.sub(r"/\*.*?\*/", "", js, flags=re.S).strip()
    body = re.sub(r"^\s*(?:const|var|let)\s+I18N\s*=\s*", "", body).rstrip().rstrip(";")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise SystemExit(f"i18n.js is not a readable object literal: {e}")
    return {loc: set(keys) for loc, keys in data.items()}


def check_i18n(name: str, rendered: str, js: str, scripts: str) -> list[str]:
    """Cross-check the rendered markup against the page's dictionary.

    Two drifts happened by hand on this site in one evening: a shared string
    that existed in one page's dictionary and not the other, and a key the
    markup referenced under a name the dictionary did not use. Both shipped
    silently — an untranslated string looks like English, which looks fine.
    Deriving the expected key set from the built page and failing here turns
    both into build errors instead.

    Returns hard errors. Orphans are reported separately as warnings, and the
    asymmetry there is deliberate — see the note below.
    """
    used = set(re.findall(r'data-i18n="([^"]+)"', rendered))
    for attr in re.findall(r'data-i18n-attr="([^"]+)"', rendered):
        for pair in attr.split(";"):
            if ":" in pair:
                used.add(pair.split(":", 1)[1].strip())

    locales = i18n_keys(js)
    if "en" not in locales:
        return [f"{name}: dictionary has no `en` locale"]

    errors = []
    missing = sorted(used - locales["en"])
    if missing:
        errors.append(f"{name}: markup uses {len(missing)} key(s) absent from the `en` dictionary: "
                      + ", ".join(missing[:8]) + (" ..." if len(missing) > 8 else ""))

    # every locale must carry the same keys, or a language switch renders blanks
    for loc, keys in sorted(locales.items()):
        if loc == "en":
            continue
        gap = sorted(locales["en"] - keys)
        extra = sorted(keys - locales["en"])
        if gap:
            errors.append(f"{name}: `{loc}` is missing {len(gap)} key(s) that `en` has: "
                          + ", ".join(gap[:8]) + (" ..." if len(gap) > 8 else ""))
        if extra:
            errors.append(f"{name}: `{loc}` has {len(extra)} key(s) `en` does not: "
                          + ", ".join(extra[:8]) + (" ..." if len(extra) > 8 else ""))
    return errors


def orphan_keys(rendered: str, js: str, scripts: str) -> list[str]:
    """Dictionary keys reachable from neither the markup nor the scripts.

    NOT a build failure, and it must not become one. The symmetry with the
    checks above is only apparent: markup referencing a key the dictionary
    lacks is always a bug, but a key with no markup reference usually is not.
    Some are read from the dictionary by JS at runtime — `cta.copied` is
    exactly that, written into the copy button's live region and carrying no
    `data-i18n` anywhere. Failing the build on it would break on a key that
    works, which teaches the next person that this check is noise.

    So the scripts are searched too, and only a key that nothing can reach is
    reported — as a warning.
    """
    used = set(re.findall(r'data-i18n="([^"]+)"', rendered))
    for attr in re.findall(r'data-i18n-attr="([^"]+)"', rendered):
        for pair in attr.split(";"):
            if ":" in pair:
                used.add(pair.split(":", 1)[1].strip())
    locales = i18n_keys(js)
    out = []
    for key in sorted(locales.get("en", set()) - used):
        if f"'{key}'" not in scripts and f'"{key}"' not in scripts:
            out.append(key)
    return out


# Section names for breadcrumb trails, where the URL segment alone reads badly.
SECTION_NAMES = {
    "docs": "Docs",
    "project-hub": "Project Hub",
    "guide": "Guides & decks",
}

ORG = {
    "@type": "Organization",
    "@id": f"{SITE_URL}/#org",
    "name": "MonoMind AI Lab",
    "url": "https://monomind.one",
}


def jsonld_for(route: str, title: str, description: str) -> str:
    """The structured data for one page.

    A `@graph` rather than a bare object, so the publisher is stated once and
    referenced: an answer engine asking "who says this" gets the same node from
    every page. The home page additionally declares the SoftwareApplication the
    whole site is about; inner pages declare a WebPage and a breadcrumb trail,
    which is what turns a deep link into something an engine can place.

    Nothing here is asserted that the page does not already say — title and
    description come from the same meta.json the <title> and <meta> use.
    """
    page_id = f"{SITE_URL}{route}"
    graph: list[dict] = [ORG]

    if route == "/":
        graph.append({
            "@type": "WebSite",
            "@id": f"{SITE_URL}/#website",
            "url": SITE_URL,
            "name": "Project Context",
            "description": description,
            "publisher": {"@id": f"{SITE_URL}/#org"},
            "inLanguage": ["en", "ko", "zh-Hant"],
        })
        graph.append({
            "@type": "SoftwareApplication",
            "@id": f"{SITE_URL}/#software",
            "name": "Project Context",
            "applicationCategory": "DeveloperApplication",
            "operatingSystem": "Any, with Python 3.10 or later",
            "url": SITE_URL,
            "codeRepository": "https://github.com/monomind-ai-lab/project-context",
            "license": "https://opensource.org/license/mit",
            "publisher": {"@id": f"{SITE_URL}/#org"},
            "description": description,
            # Free to use; stated because an answer engine asked "how much does
            # it cost" should not have to infer it from the licence.
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        })
    else:
        crumbs = [{"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"}]
        parts = [seg for seg in route.strip("/").split("/") if seg]
        for i, seg in enumerate(parts, start=2):
            here = SITE_URL + "/" + "/".join(parts[: i - 1]) + "/"
            # The last crumb is this page, so it gets the page's own name rather
            # than its slug; an intermediate segment gets the section name a
            # reader would recognise from the nav, not `project hub`.
            if i - 1 == len(parts):
                name = title.split(" — ")[0]
            else:
                name = SECTION_NAMES.get(seg, seg.replace("-", " ").title())
            crumbs.append({"@type": "ListItem", "position": i, "name": name, "item": here})
        graph.append({
            "@type": "WebPage",
            "@id": page_id,
            "url": page_id,
            "name": title,
            "description": description,
            "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "about": {"@id": f"{SITE_URL}/#software"},
            "publisher": {"@id": f"{SITE_URL}/#org"},
            "inLanguage": ["en", "ko", "zh-Hant"],
            "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": crumbs},
        })

    payload = json.dumps({"@context": "https://schema.org", "@graph": graph},
                         indent=2, ensure_ascii=False)
    # `</script>` cannot appear inside a script element; nothing here should
    # contain one, but escaping it is cheaper than trusting that forever.
    payload = payload.replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{payload}\n</script>'


def write_sitemap(pages: list[dict]) -> None:
    """One entry per served route, newest-changed first is irrelevant to a
    crawler, so they are emitted in reading order for a human opening the file."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = _dt.date.today().isoformat()
    for page in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{html.escape(SITE_URL + page['route'])}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <priority>{'1.0' if page['route'] == '/' else '0.8'}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (OUT / "sitemap.xml").write_text("\n".join(lines) + "\n")


def write_llms(pages: list[dict]) -> None:
    """llms.txt — the site, in Markdown, for a model reading rather than
    rendering it. The format is a H1, a blockquote summary, then link lists
    under H2 sections. Ordered as a reading path, not as a file listing."""
    by_route = {page["route"]: page for page in pages}
    out = [
        "# Project Context",
        "",
        "> Small Markdown records, versioned in a project's own repository, that outlive any "
        "one person, agent, or chat. Project Context installs into a repository and serves the "
        "people building it; Project Hub is its optional other half, one private repository where "
        "an owner authors what applies across every project. Markdown and Git are the whole "
        "storage contract: no database, no server, no runtime dependency, and no command that "
        "reaches the network.",
        "",
    ]
    for heading, routes in LLMS_SECTIONS:
        listed = [by_route[r] for r in routes if r in by_route]
        if not listed:
            continue
        out.append(f"## {heading}")
        out.append("")
        for page in listed:
            out.append(f"- [{page['title']}]({SITE_URL}{page['route']}): {page['description']}")
        out.append("")
    remaining = [p for p in pages
                 if p["route"] not in {r for _, rs in LLMS_SECTIONS for r in rs}]
    if remaining:
        out.append("## Other pages")
        out.append("")
        for page in remaining:
            out.append(f"- [{page['title']}]({SITE_URL}{page['route']}): {page['description']}")
        out.append("")
    out += [
        "## Source",
        "",
        "- [project-context on GitHub](https://github.com/monomind-ai-lab/project-context): "
        "the product installed into a project repository — two skills and one CLI, standard "
        "library only.",
        "- [project-hub on GitHub](https://github.com/monomind-ai-lab/project-hub): the scaffold "
        "an owner copies into a private repository of their own.",
        "",
    ]
    (OUT / "llms.txt").write_text("\n".join(out))


def build_page(src: pathlib.Path, version: str) -> tuple[pathlib.Path, int, dict]:
    meta = json.loads((src / "meta.json").read_text())
    template = LAYOUT.read_text()

    page_css = (src / "page.css").read_text().strip() if (src / "page.css").exists() else ""
    i18n = (src / "i18n.js").read_text().strip() if (src / "i18n.js").exists() else ""
    page_js = (src / "page.js").read_text().strip() if (src / "page.js").exists() else ""

    route = page_route(meta["output"])
    # Per-page meta.json `nav` wins when present (legacy override, used by the
    # docs pages until migration); pages without one get the global nav.
    nav = meta.get("nav") or GLOBAL_NAV
    # Same principle for the footer: a page carrying `footer_links` keeps the
    # legacy inline list inside the brand column; otherwise the global
    # multi-column footer renders beside it.
    legacy_footer = meta.get("footer_links")
    if legacy_footer:
        footer_inline = ('        <p class="foot-inline">\n'
                         + footer_html(legacy_footer)
                         + '\n        </p>')
        footer_columns = ""
    else:
        footer_inline = ""
        footer_columns = footer_columns_html(GLOBAL_FOOTER_COLUMNS, route)

    values = {
        "lang": meta.get("lang", "en"),
        "title": html.escape(meta["title"], quote=True),
        "description": html.escape(meta["description"], quote=True),
        "og_image": meta.get("og_image", "/og-image.jpg"),
        "og_image_alt": html.escape(meta.get("og_image_alt", f'{meta["title"]} — MonoMind AI Lab'), quote=True),
        "asset_version": version,
        "canonical": SITE_URL + route,
        "jsonld": jsonld_for(route, meta["title"], meta["description"]),
        "page_style": f"<style>\n{page_css}\n</style>" if page_css else "",
        "nav_desktop": nav_html(nav, route),
        "nav_mobile": nav_html(nav, route, mobile=True),
        "content": (src / "page.html").read_text().rstrip("\n"),
        "footer_inline": footer_inline,
        "footer_columns": footer_columns,
        "i18n": i18n,
        "page_script": f"<script>\n{page_js}\n</script>" if page_js else "",
    }

    missing = sorted(set(PLACEHOLDER.findall(template)) - set(values))
    if missing:
        raise SystemExit(f"{src.name}: template placeholder(s) with no value: {', '.join(missing)}")

    rendered = PLACEHOLDER.sub(lambda m: values[m.group(1)], template)

    # Nothing that looks like a placeholder may survive into the output. The
    # named-placeholder check above only sees what the pattern matches, so a
    # typo'd or unmatched `{{...}}` would otherwise ship silently.
    leftover = re.findall(r"\{\{[^}\n]{0,40}\}\}", rendered)
    if leftover:
        raise SystemExit(f"{src.name}: unsubstituted placeholder(s) in output: {', '.join(sorted(set(leftover)))}")

    if i18n:
        shared_js = (ASSETS / "site.js").read_text() if (ASSETS / "site.js").exists() else ""
        scripts = shared_js + page_js
        problems = check_i18n(src.name, rendered, i18n, scripts)
        if problems:
            raise SystemExit("i18n check failed:\n  " + "\n  ".join(problems))
        for key in orphan_keys(rendered, i18n, scripts):
            print(f"  warning: {src.name}: dictionary key `{key}` is reachable from "
                  f"neither markup nor scripts")

    dest = OUT / meta["output"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(rendered)
    return dest, len(rendered), {"route": route, "title": meta["title"],
                                 "description": meta["description"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="build to a temp dir and report, without writing site/")
    args = ap.parse_args()

    if not CONTENT.exists():
        raise SystemExit(f"no content directory at {CONTENT}")

    global OUT
    if args.check:
        import tempfile
        OUT = pathlib.Path(tempfile.mkdtemp(prefix="pc-site-"))

    # shared assets and static files are copied verbatim into the output; web/
    # is the only source, site/ is entirely generated.
    (OUT / "_assets").mkdir(parents=True, exist_ok=True)
    for asset in sorted(ASSETS.glob("*")):
        if asset.is_file():
            shutil.copy2(asset, OUT / "_assets" / asset.name)
    for static in sorted(STATIC.glob("*")):
        if static.is_file():
            shutil.copy2(static, OUT / static.name)

    version = asset_version()
    pages = sorted(p for p in CONTENT.iterdir() if (p / "meta.json").exists())
    if not pages:
        raise SystemExit("no pages found under web/content/")

    entries: list[dict] = []
    for src in pages:
        dest, size, entry = build_page(src, version)
        entries.append(entry)
        print(f"  {dest.relative_to(OUT)!s:34} {size / 1024:6.1f}K   <- _content/{src.name}")

    # The decks are copied in by sync.sh after this script runs, so they are
    # named rather than discovered — see EXTRA_ROUTES.
    entries.extend(EXTRA_ROUTES)
    # Reading order, flattened from LLMS_SECTIONS, so the sitemap and llms.txt
    # present the same path through the site. Anything unlisted sorts last.
    order = {route: n for n, route in
             enumerate(r for _, routes in LLMS_SECTIONS for r in routes)}
    entries.sort(key=lambda e: order.get(e["route"], len(order)))
    write_sitemap(entries)
    write_llms(entries)
    print(f"  {'sitemap.xml':34} {len(entries):6d} url(s)")
    print(f"  {'llms.txt':34}")
    print(f"built {len(pages)} page(s), assets v{version}")
    if args.check:
        print(f"(check mode: output in {OUT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
