#!/usr/bin/env bash
# SPRINT amendment v2-a3: one online model through the priority blocks, in order B1 (Tier W P3+P4), B2 (P5),
# B3 (Tier W P0-P2), B4 (Tier H P3+P4), B5 (Tier H P0-P2), each followed by one D85 retry pass over its failed
# items.  Stops at once if any isolation audit flags a request (stop condition).
# Usage: scripts/sprint_online_blocks.sh <commit> claude|deepseek
set -uo pipefail
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
C="$1"
case "$2" in
  claude)   M=configs/sprint/r7b_online_main_claude_opus_55;    P5=configs/sprint/p5_online_claude_opus_55.json ;;
  deepseek) M=configs/sprint/r7b_online_main_deepseek_v4_pro_low; P5=configs/sprint/p5_online_deepseek_v4_pro_low.json ;;
  *) echo "model?" >&2; exit 2 ;;
esac
LOG="$MAIN/runs/logs/sprint-online-blocks-$2.log"
for cfg in "${M}_b1.json" "$P5" "${M}_b3.json" "${M}_b4.json" "${M}_b5.json"; do
  rid=$(python3 -c "import json,sys; print(json.load(open('$MAIN/$cfg'))['run_id'])")
  echo "$(date -u +%FT%TZ) block $cfg run $rid" >> "$LOG"
  "$MAIN/scripts/run_from_snapshot.sh" "$C" "$rid" python -m causalguard run --config "$cfg" --quiet
  "$MAIN/scripts/run_from_snapshot.sh" "$C" "$rid" python -m causalguard run --config "$cfg" --quiet --resume --retry-failed
  if grep -rlq "isolation audit failed" "$MAIN/runs/$rid/attempts" 2>/dev/null; then
    echo "$(date -u +%FT%TZ) STOP: isolation audit flagged a request in $rid" >> "$LOG"; exit 3
  fi
  if grep -rlq "hard stop" "$MAIN/runs/$rid/attempts" 2>/dev/null; then
    echo "$(date -u +%FT%TZ) hard stop reached in $rid; later blocks not started" >> "$LOG"; exit 0
  fi
  echo "$(date -u +%FT%TZ) done $rid" >> "$LOG"
done
