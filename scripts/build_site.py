#!/usr/bin/env python3
"""Render site/_content/** into the deployable site/ folder.

Zero dependencies, stdlib only — the same constraint the shipped CLI holds
itself to. Cloudflare Pages runs this through site/sync.sh.

Content model, one directory per route under web/content/:

    meta.json    route, output path, title, description, nav, footer links
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
OUT = ROOT / "site"

PLACEHOLDER = re.compile(r"\{\{([a-z0-9_]+)\}\}")


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


def nav_html(links: list[dict], mobile: bool = False) -> str:
    """Render one nav link list. The desktop and mobile navs are the same list
    rendered twice — they cannot drift because there is only one source."""
    out = []
    indent = "    " if mobile else "      "
    for link in links:
        attrs = [f'href="{html.escape(link["href"])}"']
        cls = [] if mobile else ["nav-link"]
        body = html.escape(link["label"])
        if link.get("external"):
            cls.append("notranslate")
            attrs.append('translate="no"')
            attrs.append('rel="noopener noreferrer"')
            attrs.append('target="_blank"')
            # Add external link icon
            body += ' <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="display:inline;margin-left:4px;vertical-align:-2px"><path d="M2 10H1V1h9v1M11 1l-4 4M11 1v3.5M11 1h-3.5"/></svg>'
        if link.get("current"):
            attrs.append('aria-current="page"')
        if link.get("i18n"):
            attrs.append(f'data-i18n="{html.escape(link["i18n"])}"')
        cls_attr = f'class="{" ".join(cls)}" ' if cls else ""
        out.append(f'{indent}<a {cls_attr}{" ".join(attrs)}>{body}</a>')
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


def build_page(src: pathlib.Path, version: str) -> tuple[pathlib.Path, int]:
    meta = json.loads((src / "meta.json").read_text())
    template = LAYOUT.read_text()

    page_css = (src / "page.css").read_text().strip() if (src / "page.css").exists() else ""
    i18n = (src / "i18n.js").read_text().strip() if (src / "i18n.js").exists() else ""
    page_js = (src / "page.js").read_text().strip() if (src / "page.js").exists() else ""

    values = {
        "lang": meta.get("lang", "en"),
        "title": html.escape(meta["title"], quote=True),
        "description": html.escape(meta["description"], quote=True),
        "og_image": meta.get("og_image", "/og-image.jpg"),
        "og_image_alt": html.escape(meta.get("og_image_alt", f'{meta["title"]} — MonoMind AI Lab'), quote=True),
        "asset_version": version,
        "page_style": f"<style>\n{page_css}\n</style>" if page_css else "",
        "nav_desktop": nav_html(meta.get("nav", [])),
        "nav_mobile": nav_html(meta.get("nav", []), mobile=True),
        "content": (src / "page.html").read_text().rstrip("\n"),
        "footer_links": footer_html(meta.get("footer_links", [])),
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
    return dest, len(rendered)


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

    for src in pages:
        dest, size = build_page(src, version)
        print(f"  {dest.relative_to(OUT)!s:34} {size / 1024:6.1f}K   <- _content/{src.name}")
    print(f"built {len(pages)} page(s), assets v{version}")
    if args.check:
        print(f"(check mode: output in {OUT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
