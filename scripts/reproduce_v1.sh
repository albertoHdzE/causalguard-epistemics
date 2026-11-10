#!/usr/bin/env bash
# Byte-for-byte reproduction of the iteration-1 (v0.1.0-dev) development summaries with the HISTORICAL code.
# Uses a detached worktree of the tag and the raw run records in ./runs (from the v0.1.0-dev release asset).
set -euo pipefail
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
WT="${TMPDIR:-/tmp}/causalguard-v0.1.0-dev"
OUT="${TMPDIR:-/tmp}/causalguard-v1-repro"
[ -d "$WT" ] || git -C "$MAIN" worktree add -q --detach "$WT" v0.1.0-dev
ln -sfn "$MAIN/runs" "$WT/runs"
mkdir -p "$OUT"
cd "$WT"
export PYTHONPATH="$WT/src" MPLCONFIGDIR="${TMPDIR:-/tmp}/cg-mpl"
"$MAIN/.venv/bin/python" -m causalguard analyze-s2 --run-id S2-dev-v1 --run-id S2-dev-null-v1 --out "$OUT/s2" >/dev/null
"$MAIN/.venv/bin/python" -m causalguard analyze-s1 --run-id S1-dev-v1 --run-id S1-dev-v1-rerun --out "$OUT/s1" >/dev/null
fail=0
for f in s2/s2_summary.json s1/s1_summary.json; do
  ref="$MAIN/reports/development/$(basename $f)"
  a=$(shasum -a 256 "$OUT/$f" | cut -d' ' -f1); b=$(shasum -a 256 "$ref" | cut -d' ' -f1)
  if [ "$a" = "$b" ]; then echo "MATCH $f $a"; else echo "MISMATCH $f $a != $b"; fail=1; fi
done
exit $fail
