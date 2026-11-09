#!/bin/sh
# Fetch the pinned upstream CausalBool revision (read-only parity reference; not redistributed).
# Usage: scripts/fetch_upstream.sh <target-dir>   then: export CAUSALBOOL_ROOT=<target-dir>
set -eu
DEST="${1:?target directory}"
REV=376a11ddf25063d49dc8f6cd98bbb3baf2e1cc43
if [ ! -d "$DEST/.git" ]; then
  git clone --filter=blob:none --no-checkout https://github.com/albertoHdzE/CausalBool "$DEST"
fi
git -C "$DEST" fetch --quiet origin "$REV" || true
git -C "$DEST" checkout --quiet "$REV"
git -C "$DEST" rev-parse HEAD
