#!/usr/bin/env bash
# SPRINT amendment v2-a3: one online model through the priority blocks, in order B1 (Tier W P3+P4), B2 (P5),
# B3 (Tier W P0-P2), B4 (Tier H P3+P4), B5 (Tier H P0-P2), each followed by one D85 retry pass over its failed
# items.  Stops at once if any isolation audit flags a request (stop condition).
# Amendment v2-a4 (director D118): an optional third argument names the blocks to run (e.g. "b4": the post-freeze
# Tier H supplement); then a watcher stops the block at the FIRST isolation flag, one retry pass follows, and a flag
# in the retry pass ends the block for good (no retry after a second flag).
# Usage: scripts/sprint_online_blocks.sh <commit> claude|deepseek [b1 p5 b3 b4 b5]
set -uo pipefail
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
C="$1"
case "$2" in
  claude)   M=configs/sprint/r7b_online_main_claude_opus_55;    P5=configs/sprint/p5_online_claude_opus_55.json ;;
  deepseek) M=configs/sprint/r7b_online_main_deepseek_v4_pro_low; P5=configs/sprint/p5_online_deepseek_v4_pro_low.json ;;
  *) echo "model?" >&2; exit 2 ;;
esac
LOG="$MAIN/runs/logs/sprint-online-blocks-$2.log"
CFGS=("${M}_b1.json" "$P5" "${M}_b3.json" "${M}_b4.json" "${M}_b5.json")
if [ -n "${3:-}" ]; then
  CFGS=(); for b in $3; do case "$b" in p5) CFGS+=("$P5") ;; *) CFGS+=("${M}_${b}.json") ;; esac; done
  flags() { grep -rl "isolation audit failed" "$MAIN/runs/$1/attempts" 2>/dev/null | wc -l | tr -d ' '; }
  watched() {   # v2-a4: run one pass; kill it at the first isolation flag beyond $2 already present
    "$MAIN/scripts/run_from_snapshot.sh" "$C" "$1" "${@:3}" & local pid=$!
    while kill -0 "$pid" 2>/dev/null; do
      if [ "$(flags "$1")" -gt "$2" ]; then
        pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; pkill -TERM -f "claude -p --model claude-opus-5-5 --system-prompt" 2>/dev/null
        echo "$(date -u +%FT%TZ) v2-a4: isolation flag in $1, pass stopped" >> "$LOG"; wait "$pid"; return 3
      fi
      sleep 15
    done
    wait "$pid"; return 0
  }
  for cfg in "${CFGS[@]}"; do
    rid=$(python3 -c "import json,sys; print(json.load(open('$MAIN/$cfg'))['run_id'])")
    echo "$(date -u +%FT%TZ) v2-a4 block $cfg run $rid" >> "$LOG"
    watched "$rid" "$(flags "$rid")" python -m causalguard run --config "$cfg" --quiet
    n0=$(flags "$rid")
    watched "$rid" "$n0" python -m causalguard run --config "$cfg" --quiet --resume --retry-failed
    if [ $? -eq 3 ]; then echo "$(date -u +%FT%TZ) STOP: second isolation flag in $rid" >> "$LOG"; exit 3; fi
    echo "$(date -u +%FT%TZ) done $rid (isolation flags: $(flags "$rid"))" >> "$LOG"
  done
  exit 0
fi
for cfg in "${CFGS[@]}"; do
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
