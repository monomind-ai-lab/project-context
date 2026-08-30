#!/usr/bin/env bash
# Assemble the deployable site/ folder from the repository's real artifacts.
#
# The landing page and its images are committed under site/. The interactive
# guide is not: docs/project-context-complete-guide.html is its single source
# of truth, and it is copied to site/guide/index.html at deploy time so git
# never carries a second 326K copy that can quietly drift from the original.
#
# Cloudflare Pages runs this as its build command, with build output
# directory `site`:
#
#   build command:     bash site/sync.sh
#   output directory:  site
#
# Routes served:  /             -> site/index.html          (committed)
#                 /use-cases/   -> site/use-cases/index.html (committed)
#                 /guide/       -> site/guide/index.html     (copied here)
#                 /og-image.jpg -> derived from assets/project-context-cover.jpg
#
# Run it locally before previewing site/index.html.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p site/guide
cp docs/project-context-complete-guide.html site/guide/index.html

# The social/SEO card. Derived from the repository's own cover art (1200x675)
# rather than committed twice; og:image:height in index.html matches that size.
cp assets/project-context-cover.jpg site/og-image.jpg

echo "site/ assembled:"
find site -type f | sort
