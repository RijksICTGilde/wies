#!/usr/bin/env bash
# Installs package-lock.json and copies the files Wies serves into
# wies/core/static/vendor. Runs in the Dockerfile's vendor stage; `just vendor`
# runs that stage, so Node on the host is optional.
set -euo pipefail
cd "$(dirname "$0")/.."

npm ci --ignore-scripts --no-audit --no-fund

dest=wies/core/static/vendor
nldd=node_modules/@nldd/design-system
rm -rf "$dest"
mkdir -p "$dest/htmx" "$dest/nldd"

cp node_modules/htmx.org/dist/htmx.min.js "$dest/htmx/"

# dist/ is copied as-is so the relative @import and url('../fonts/...') paths
# keep resolving.
cp "$nldd/dist/nldd.min.js" "$dest/nldd/"
cp -R "$nldd/dist/css" "$nldd/dist/fonts" "$dest/nldd/"

nldd_version="$(node -p "require('./$nldd/package.json').version")"
printf '@nldd/design-system %s\nvendored via scripts/vendor.sh\n' "$nldd_version" > "$dest/nldd/VERSION.txt"
