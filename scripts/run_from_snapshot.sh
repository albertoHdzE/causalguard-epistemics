#!/usr/bin/env bash
# Run a development command from an immutable git snapshot (worktree at a commit), writing runtime
# records to the main tree's ignored runs/ directory.  Usage:
#   scripts/run_from_snapshot.sh <commit> <log-name> python -m causalguard... [args]
# The snapshot is created once per commit under ~/.cache/causalguard/snapshots/<sha12> and never edited.
set -euo pipefail
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
SHA="$(git -C "$MAIN" rev-parse --short=12 "$1")"; shift
NAME="$1"; shift
SNAP="$HOME/.cache/causalguard/snapshots/$SHA"
[ -d "$SNAP" ] || git -C "$MAIN" worktree add -q --detach "$SNAP" "$SHA"
[ -z "$(git -C "$SNAP" status --porcelain)" ] || { echo "snapshot $SNAP is dirty" >&2; exit 1; }
mkdir -p "$MAIN/runs/logs"
cd "$SNAP"
export PYTHONPATH="$SNAP/src" CAUSALGUARD_RUNS="$MAIN/runs" MPLCONFIGDIR=/tmp/cg-mpl
shift  # drop the literal "python"
echo "snapshot=$SHA start=$(date -u +%FT%TZ) cmd=$*" >> "$MAIN/runs/logs/$NAME.log"
exec "$MAIN/.venv/bin/python" "$@" >> "$MAIN/runs/logs/$NAME.log" 2>&1
