"""Run the formulation race over many load levels and report the distribution, not a single draw.

One snapshot tells you almost nothing: the binding constraints change with the loading, and a formulation
that looks accurate at one operating point can be the worst at another. This samples load levels across
the year and reports median and worst case for each metric.
"""
from __future__ import annotations

import statistics
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
warnings.filterwarnings("ignore")

import pyomo.environ as pyo

from case import load_snapshot
from formulations import build_bfm, build_dc
from race import evaluate
from reference import true_acopf

SPECS = [
    ("DC",                     lambda s: build_dc(s)),
    ("DC + 2% loss factor",    lambda s: build_dc(s, loss_factor=0.02)),
    ("BFM-SOCP, no cycles",    lambda s: build_bfm(s, conic=True,  cycles=False)),
    ("BFM-SOCP + cycles [A]",  lambda s: build_bfm(s, conic=True,  cycles=True)),
    ("BFM-LP + cycles [B] L=4",  lambda s: build_bfm(s, conic=False, cycles=True, segments=4)),
    ("BFM-LP + cycles [B] L=10", lambda s: build_bfm(s, conic=False, cycles=True, segments=10)),
    ("BFM-LP + cycles [B] L=25", lambda s: build_bfm(s, conic=False, cycles=True, segments=25)),
]


def run(case_dir, case, n_hours=24, stride=None):
    import pandas as pd
    dem = pd.read_csv(Path(case_dir) / f"oT_Data_Demand_{case}.csv", encoding="utf-8-sig", index_col=[0, 1, 2])
    total = len(dem)
    stride = stride or max(1, total // n_hours)
    hours = list(range(0, total, stride))[:n_hours]

    acc = {name: [] for name, _ in SPECS}
    n_ref_ok = 0
    for h in hours:
        snap = load_snapshot(case_dir, case, hour=h)
        ref = true_acopf(snap)
        if not ref["ok"]:
            continue
        n_ref_ok += 1
        for name, mk in SPECS:
            try:
                row = evaluate(name, mk(snap), snap, ref)
            except Exception as e:
                row = {"status": f"error {type(e).__name__}"}
            if row.get("status") == "optimal":
                acc[name].append(row)

    print(f"{case}: {n_ref_ok}/{len(hours)} sampled load levels where the exact AC OPF converged\n")

    def stat(rows, key, worst="max"):
        vals = [r[key] for r in rows if key in r and r[key] == r[key]]
        if not vals:
            return float("nan"), float("nan")
        return statistics.median(vals), (max(vals) if worst == "max" else min(vals))

    hdr = (f"{'formulation':26s} {'gap% med':>9s} {'gap% worst':>11s} {'lossErr med':>12s} {'lossErr worst':>14s} "
           f"{'cycMis worst':>13s} {'load% worst':>12s} {'solve med':>10s} {'solve worst':>12s}  n")
    print(hdr)
    print("-" * len(hdr))
    for name, _ in SPECS:
        rows = acc[name]
        if not rows:
            print(f"{name:26s} (no successful solves)")
            continue
        g_med, _ = stat(rows, "gap_%")
        g_wst = max((abs(r["gap_%"]) for r in rows if "gap_%" in r), default=float("nan"))
        le_med, _ = stat(rows, "loss_err_MW")
        le_wst = max((abs(r["loss_err_MW"]) for r in rows if "loss_err_MW" in r), default=float("nan"))
        cm_wst, _ = stat(rows, "cycle_mismatch_deg")
        cm_wst = max((r.get("cycle_mismatch_deg", 0.0) for r in rows), default=float("nan"))
        ld_wst = max((r.get("max_loading_%", 0.0) for r in rows), default=float("nan"))
        s_med, s_wst = stat(rows, "solve_s")
        print(f"{name:26s} {g_med:+9.3f} {g_wst:11.3f} {le_med:+12.3f} {le_wst:14.3f} "
              f"{cm_wst:13.3f} {ld_wst:12.1f} {s_med:10.3f} {s_wst:12.3f}  {len(rows)}")


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "openTEPES/cases/9n_AC"
    c = sys.argv[2] if len(sys.argv) > 2 else "9n_AC"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    run(d, c, n_hours=n)
