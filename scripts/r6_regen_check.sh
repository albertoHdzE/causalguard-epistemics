#!/usr/bin/env bash
# R6 byte-identity check: regenerate every committed R5 and R6 analysis output from the raw runs with the current
# code and compare byte for byte (cmp).  Usage: scripts/r6_regen_check.sh OUT_DIR [workers]
set -u
OUT=${1:?out dir}; W=${2:-4}
mkdir -p "$OUT/r5" "$OUT/r6"
PY=.venv/bin/python
A="$PY -m causalguard analyze-r5"
cat > "$OUT/jobs.txt" <<EOF
r5/g_champion_selection.json|--track g-champion --run runs/r5-g-cal-v1
r5/g_evaluation.json|--track g --run runs/r5-g-eval-v1 --champion gate
r5/g_external_intact.json|--track g-external --run runs/r5-g-ext-intact-v1 --champion gate
r5/g_external_transformed.json|--track g-external --run runs/r5-g-ext-transformed-v1 --champion gate
r5/m_evaluation.json|--track m --run runs/r5-m-eval-v1
r5/a_det_evaluation.json|--track a-det --run runs/r5-a-det-eval-v1
r5/a_policy_selection.json|--track a-select --run runs/r5-a-det-cal-v1
r5/a_ai_calibration_gate.json|--track a-ai --run runs/r5-a-ai-cal-qwen25_7b-v1 --run runs/r5-a-ai-cal-mistral_small_24b-v1 --det-run runs/r5-a-det-cal-v1 --selected eig
r5/a_ai_calibration_gate_v2.json|--track a-ai --run runs/r5-a-ai-cal-qwen25_7b-v2 --run runs/r5-a-ai-cal-mistral_small_24b-v2 --det-run runs/r5-a-det-cal-v1 --selected eig
r5/a_ai_evaluation.json|--track a-ai --run runs/r5-a-ai-eval-qwen25_7b-v2 --run runs/r5-a-ai-eval-mistral_small_24b-v2 --det-run runs/r5-a-det-eval-v1 --selected eig
r5/c_benchmark.json|--track c --run runs/r5-c-bench-v2
r5/c_benchmark_n64_genve_v3.json|--track c --run runs/r5-c-bench-n64-genve-v3
r6/g_calibration.json|--track g-r6 --run runs/r6-g-cal-v1 --champion gate --method xdc[cgh_flat]
r6/g_evaluation.json|--track g-r6 --run runs/r6-g-eval-v1 --champion gate --method xdc[cgh_flat]
r6/g_external_dev.json|--track g-r6 --run runs/r6-g-ext-dev-v1 --champion gate --method xdc[cgh_flat] --external
r6/g_external_fresh.json|--track g-r6 --run runs/r6-g-ext-fresh-v1 --champion gate --method xdc[cgh_flat] --external
r6/g_evaluation_extras.json|--track g-r6-extras --run runs/r6-g-eval-v1 --champion gate --method xdc[cgh_flat]
r6/g_external_fresh_extras.json|--track g-r6-extras --run runs/r6-g-ext-fresh-v1 --champion gate --method xdc[cgh_flat] --external
r6/s_calibration_v2.json|--track s-cal --run runs/r6-s-cal-v2
r6/s_evaluation.json|--track s --run runs/r6-s-eval-v1
r6/a2_gate_loop.json|--track a2 --run runs/r6-a2-control-qwen25_7b-v1 --run runs/r6-a2-loop-qwen25_7b-v1 --run runs/r6-a2-control-mistral_small_24b-v1 --run runs/r6-a2-loop-mistral_small_24b-v1 --det-run runs/r6-a2-det-v1
EOF
run() { local o=${1%%|*} a=${1#*|}; $A $a --out "$OUT/$o" >/dev/null 2>"$OUT/$o.err" || echo "FAILED $o"; }
while IFS= read -r j; do
  while [ "$(jobs -rp | wc -l)" -ge "$W" ]; do sleep 1; done
  run "$j" &
done < "$OUT/jobs.txt"
wait
same=0; total=0
while IFS='|' read -r o _; do
  total=$((total+1)); d=reports/development_${o%%/*}/${o#*/}
  if cmp -s "$OUT/$o" "$d"; then same=$((same+1)); echo "IDENTICAL $o"; else echo "DIFFERENT $o"; fi
done < "$OUT/jobs.txt"
echo "byte-identical: $same / $total"
