#!/usr/bin/env bash
# SPRINT (lock v2): local P5 runs on LM Studio, one model at a time, in the addendum's order, each loaded with a
# 16384-token context (as in the R7b main panel) and unloaded afterwards.  Usage: scripts/sprint_local_p5.sh <commit>
set -uo pipefail
MAIN="$(cd "$(dirname "$0")/.." && pwd)"
LMS="$HOME/.lmstudio/bin/lms"
C="$1"
for pair in "gemma3_4b google/gemma-3-4b" "mistral_small_24b mistral-small-3.2-24b-instruct-2506-mlx" \
            "llama33_70b llama-3.3-70b-instruct" "gemma4_12b gemma-4-12b-it-mlx" \
            "r1_distill_qwen_32b deepseek-r1-distill-qwen-32b"; do
  set -- $pair
  echo "$(date -u +%FT%TZ) load $2" >> "$MAIN/runs/logs/sprint-local-p5.log"
  "$LMS" unload --all >/dev/null 2>&1
  "$LMS" load "$2" --context-length 16384 -y >> "$MAIN/runs/logs/sprint-local-p5.log" 2>&1
  "$MAIN/scripts/run_from_snapshot.sh" "$C" "p5-$1" python -m causalguard run --config "configs/sprint/p5_$1.json" --quiet
  "$MAIN/scripts/run_from_snapshot.sh" "$C" "p5-$1" python -m causalguard run --config "configs/sprint/p5_$1.json" --quiet --resume --retry-failed
  echo "$(date -u +%FT%TZ) done $1" >> "$MAIN/runs/logs/sprint-local-p5.log"
done
"$LMS" unload --all >/dev/null 2>&1
