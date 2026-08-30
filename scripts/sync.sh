#!/usr/bin/env bash
# Assemble the deployable site/ folder. Everything under site/ is build
# output; web/ is the source. Nothing in site/ is edited by hand or committed.
#
# Cloudflare Pages (git-connected) runs this as its build command:
#
#   build command:     bash scripts/sync.sh
#   output directory:  site
#
# Routes served:  /             -> site/index.html           (generated)
#                 /use-cases/   -> site/use-cases/index.html (generated)
#                 /guide/       -> site/guide/index.html     (copied below)
#                 /_assets/*    -> shared CSS/JS             (generated)
#                 /clarity-bg.jpg, /favicon.svg              (from web/static/)
#                 /og-image.jpg -> derived from assets/project-context-cover.jpg
#
# The interactive guide keeps its single source of truth:
# docs/project-context-complete-guide.html is copied here at build time so git
# never carries a second 320K copy that can quietly drift from the original.
#
# Run locally, then preview:  python3 -m http.server -d site 8791
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build_site.py

mkdir -p site/guide
cp docs/project-context-complete-guide.html site/guide/index.html

# The social/SEO card, derived from the repository's own cover art (1200x675)
# rather than committed twice; og:image:height in the layout matches that size.
cp assets/project-context-cover.jpg site/og-image.jpg

echo "site/ assembled:"
find site -type f | sort
