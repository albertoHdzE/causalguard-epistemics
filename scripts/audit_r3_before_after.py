#!/usr/bin/env python3
"""Field-level before/after audit of the iteration-3 reanalysis of the PRESERVED development records.

Compares reports/development_r2/* (R2 analysis, v0.2.0-dev) with reports/development_r3/* (R3 analysis of the same
raw runs) and checks that scientific estimates are unchanged while metadata/RSS/coherence/baselines are corrected.
Writes reports/development_r3/before_after_audit.json.  Exit 1 if a protected scientific block changed.

  .venv/bin/python scripts/audit_r3_before_after.py [--quiet]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2, R3 = ROOT / "reports/development_r2", ROOT / "reports/development_r3"

# blocks whose values must be identical (scientific estimates / scores)
PROTECTED = {
    "S1": ["correctness", "completion", "latency_completed_queries", "median_archive_bits", "amortized_totals",
           "construction_seconds_median", "certificate_levels", "large_n_unsat_type_validation",
           "outcome_balance_by_construction", "codec_roundtrip_failures", "independent_worlds", "worlds_by_cell",
           "decoder_bundle"],
    "S2": ["secondary_exploratory", "null_uniform_H", "EXPLORATORY_structured_minus_null|index-vs_majority",
           "stress_descriptive", "curves", "exact_verdict_vs_sat_B16", "ties", "null_overlap_audit", "mc_diagnostic",
           "design_simulation_revised_primary", "design_simulation_null_index_minus_majority",
           "primary_complete_case", "primary_terminal_accounting"],
    "S3": ["arms", "target", "contrasts", "transforms", "revisions", "confusion_balanced", "round_paths_balanced"],
}


def leaves(x, prefix=""):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out.update(leaves(v, f"{prefix}/{k}"))
        return out or {prefix: {}}
    return {prefix: x}


def diff(a, b):
    la, lb = leaves(a), leaves(b)
    return {"added": sorted(set(lb) - set(la)), "removed": sorted(set(la) - set(lb)),
            "changed": sorted(k for k in set(la) & set(lb) if la[k] != lb[k])}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def top_changes(a: dict, b: dict) -> dict:
    d = diff(a, b)
    groups = {}
    for kind in ("added", "removed", "changed"):
        for path in d[kind]:
            top = path.split("/")[1]
            groups.setdefault(top, {"added": 0, "removed": 0, "changed": 0})[kind] += 1
    return groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.parse_args()
    out, bad = {"r2_dir": str(R2.relative_to(ROOT)), "r3_dir": str(R3.relative_to(ROOT)), "studies": {}}, []
    # ---------------- S1
    a, b = (json.loads((d / "s1_v2_summary.json").read_text()) for d in (R2, R3))
    s1 = {"protected_identical": {k: a.get(k) == b.get(k) for k in PROTECTED["S1"]},
          "top_level_changes": top_changes(a, b),
          "rss_r2_zero_cells": sum(v == 0 for v in a["peak_rss_mib_median"].values()),
          "rss_cells": len(b["peak_rss_mib_median"]),
          "rss_r3_null_cells": sum(v is None for v in b["peak_rss_mib_median"].values()),
          "rss_r3_measured_items": sum(c["measured"] for c in b["peak_rss_coverage"].values()),
          "rss_r3_ok_items": sum(c["ok_items"] for c in b["peak_rss_coverage"].values()),
          "rss_r3_mib_median_range": [min(v for v in b["peak_rss_mib_median"].values() if v is not None),
                                      max(v for v in b["peak_rss_mib_median"].values() if v is not None)],
          "query_grid_reconciliation": b["query_grid_reconciliation"]}
    out["studies"]["S1"] = s1
    # ---------------- S2
    a, b = (json.loads((d / "s2_v2_summary.json").read_text()) for d in (R2, R3))
    pa, pb = dict(a["primary"]), dict(b["primary"])
    st = (pa.pop("status"), pb.pop("status"))
    s2 = {"protected_identical": {k: a.get(k) == b.get(k) for k in PROTECTED["S2"]},
          "primary_numbers_identical": pa == pb, "primary_status_text": {"r2": st[0], "r3": st[1]},
          "primary_estimate": pb["estimate"], "primary_ci95": pb["ci95"], "primary_n_worlds": pb["n_worlds"],
          "per_world_csv_byte_identical": sha(R2 / "s2_v2_per_world.csv") == sha(R3 / "s2_v2_per_world.csv"),
          "per_world_csv_sha256": sha(R3 / "s2_v2_per_world.csv"),
          "completeness": {k: b["completeness"][k]["status"] for k in ("structured_primary", "required_null",
                                                                         "overall_study")},
          "legacy_row_outputs": {rid: r["ok_outputs_with_legacy_rows(no qid)"] for rid, r in b["runs"].items()},
          "top_level_changes": top_changes(a, b)}
    for k in ("primary_numbers_identical", "per_world_csv_byte_identical"):
        if not s2[k]:
            bad.append(f"S2 {k}")
    out["studies"]["S2"] = s2
    # ---------------- S3
    a, b = (json.loads((d / "s3_v2_summary.json").read_text()) for d in (R2, R3))
    s3 = {}
    for rid in b["runs"]:
        sa, sb = a["runs"][rid]["summary"], b["runs"][rid]["summary"]
        hist = {k: sa["baselines"][k] == sb["baselines"][k] for k in sa["baselines"]}
        au = b["runs"][rid]["r3_audits"]
        tgt = {n: sb["baselines"][f"{n}|target"] for n in ("majority", "surface_rule", "role_surface_rule",
                                                           "design_known_budget_rule")}
        s3[rid] = {"protected_identical": {k: sa[k] == sb[k] for k in PROTECTED["S3"]},
                   "historical_baselines_identical": all(hist.values()),
                   "new_baseline_keys": sorted(set(sb["baselines"]) - set(sa["baselines"])),
                   "target_baselines": {n: {"correct": round(v["accuracy"] * v["items"]), "items": v["items"]}
                                        for n, v in tgt.items()},
                   "C_balanced_aggregate_coherence": au["coherence_final_answers"]["by_arm"].get("C|balanced"),
                   "identical_claim_worlds": au["target_novelty"]["identical_claim_worlds"],
                   "focus": sb["contrasts"]["FOCUS|T_cert-T_label|target_accuracy"],
                   "exploratory_focus_excluding_identical": au["EXPLORATORY_focus_excluding_identical_claim_worlds"],
                   "top_level_run_changes": sorted(k for k in set(a["runs"][rid]) | set(b["runs"][rid])
                                                   if a["runs"][rid].get(k) != b["runs"][rid].get(k))}
        if not all(s3[rid]["protected_identical"].values()) or not s3[rid]["historical_baselines_identical"]:
            bad.append(f"S3 {rid}")
    out["studies"]["S3"] = s3
    for study in ("S1", "S2"):
        bad += [f"{study} {k}" for k, v in out["studies"][study]["protected_identical"].items() if not v]
    out["protected_blocks_changed"] = bad
    out["verdict"] = "PASS: scientific blocks unchanged" if not bad else "FAIL"
    (R3 / "before_after_audit.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=float))
    if args_quiet():
        print(out["verdict"], bad)
    else:
        print(json.dumps(out, indent=1, sort_keys=True, default=float))
    return 0 if not bad else 1


def args_quiet() -> bool:
    return "--quiet" in sys.argv


if __name__ == "__main__":
    sys.exit(main())
