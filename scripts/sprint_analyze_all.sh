#!/usr/bin/env bash
# SPRINT: every analysis behind the report, from the run records, into <out> (default reports/sprint_all):
# main panel (6 local models in the lock's order, then the online runs: Claude v1 + priority blocks, DeepSeek
# low-effort blocks), P5 (same order), then the report data (report/data.json).  Online runs that do not exist
# are skipped (D103: nothing requires an online result to exist).  Usage: scripts/sprint_analyze_all.sh [out]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-reports/sprint_all}"
R="${CAUSALGUARD_RUNS:-runs}"
LOCAL="gemma3_4b qwen25_7b mistral_small_24b llama33_70b gemma4_12b r1_distill_qwen_32b"
main=(); p5=()
for m in $LOCAL; do main+=(--run-dir "$R/r7b-main-$m-v1"); p5+=(--p5-run "$R/p5-$m-v1"); done
for r in r7b-main-claude_opus_55-v1 r7b-main-claude_opus_55-v2-b1 r7b-main-claude_opus_55-v2-b3 \
         r7b-main-claude_opus_55-v2-b4 r7b-main-claude_opus_55-v2-b5 r7b-main-deepseek_v4_pro_low-v1-b1 \
         r7b-main-deepseek_v4_pro_low-v1-b3 r7b-main-deepseek_v4_pro_low-v1-b4 r7b-main-deepseek_v4_pro_low-v1-b5; do
  [ -f "$R/$r/plan.json" ] && main+=(--run-dir "$R/$r")
done
for r in p5-claude_opus_55-v1 p5-deepseek_v4_pro_low-v1; do [ -f "$R/$r/plan.json" ] && p5+=(--p5-run "$R/$r"); done
mainp=(); for ((i=1; i<${#main[@]}; i+=2)); do mainp+=(--main-run "${main[$i]}"); done
.venv/bin/python -m causalguard sprint-analyze "${main[@]}" --out "$OUT"
.venv/bin/python -m causalguard sprint-p5 analyze "${p5[@]}" "${mainp[@]}" --out "$OUT"
.venv/bin/python -m causalguard sprint-report-data --out "$OUT"
