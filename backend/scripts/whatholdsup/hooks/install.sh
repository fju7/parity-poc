#!/bin/sh
# Install the pre-push guard into this clone.
#
# Hooks live in .git/hooks, which git does not version and does not clone.
# So the hook is kept in the repo and copied into place by this script, and
# anyone working on a fresh clone has to run it. There is no way around that
# short of core.hooksPath, which changes behaviour for every hook in the repo.

set -e
ROOT=$(git rev-parse --show-toplevel)
SRC="$ROOT/backend/scripts/whatholdsup/hooks/pre-push"
DST="$ROOT/.git/hooks/pre-push"

[ -f "$SRC" ] || { echo "missing: $SRC"; exit 1; }

if [ -f "$DST" ] && ! cmp -s "$SRC" "$DST"; then
    cp "$DST" "$DST.replaced.$(date +%Y%m%d%H%M%S)"
    echo "  kept your existing hook as $DST.replaced.*"
fi

cp "$SRC" "$DST"
chmod +x "$DST"
echo "installed: $DST"
echo
echo "Check it works — this should print what is and is not signed off:"
echo "    python3 backend/scripts/whatholdsup/guard_published.py"
