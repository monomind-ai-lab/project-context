#!/usr/bin/env bash
# Assemble the deployable site/ folder. Everything under site/ is build
# output; web/ is the source. Nothing in site/ is edited by hand or committed.
#
# Cloudflare Pages (git-connected) runs this as its build command:
#
#   build command:     bash scripts/sync.sh
#   output directory:  site
#
# Routes served:  /                  -> site/index.html                (generated)
#                 /use-cases/        -> generated
#                 /project-hub/      -> generated
#                 /docs/*            -> generated
#                 /guide/            -> the deck chooser               (generated)
#                 /guide/builders/   -> site/guide/builders/index.html (copied below)
#                 /guide/owners/     -> site/guide/owners/index.html   (copied below)
#                 /_assets/*         -> shared CSS/JS                  (generated)
#                 /clarity-bg.jpg, /favicon.svg                        (from web/static/)
#                 /og-image.jpg -> derived from assets/project-context-cover.jpg
#
# The two decks keep their single source of truth: docs/guide-builders.html and
# docs/guide-owners.html are copied here at build time so git never carries a
# second copy of a 200K file that can quietly drift from the original. They are
# standalone documents, not site pages — they carry their own design system and
# do not go through build_site.py.
#
# Order matters: build_site.py generates site/guide/index.html (the chooser),
# and the decks are copied into subdirectories beneath it afterwards.
#
# Run locally, then preview:  python3 -m http.server -d site 8791
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build_site.py

mkdir -p site/guide/builders site/guide/owners
cp docs/guide-builders.html site/guide/builders/index.html
cp docs/guide-owners.html   site/guide/owners/index.html

# The social/SEO card, derived from the repository's own cover art (1200x675)
# rather than committed twice; og:image:height in the layout matches that size.
cp assets/project-context-cover.jpg site/og-image.jpg

echo "site/ assembled:"
find site -type f | sort
