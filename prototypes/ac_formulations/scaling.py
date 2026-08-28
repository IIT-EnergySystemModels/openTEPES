"""How the two formulations scale as commitment binaries and periods are added.

The snapshot study compared continuous relaxations and found the SOCP tighter and faster. This asks the
question that actually decides the matter for a planning model: with binaries in the problem, which one
does branch-and-bound get through?

Gurobi handles a second-order cone inside a MIP by outer-approximating it at nodes of the tree, so the
cone is paid for repeatedly rather than once. A MILP has no such overhead. The hypothesis is that the
ordering from the snapshot study reverses, and that it reverses harder as the tree grows.
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
warnings.filterwarnings("ignore")

import pyomo.environ as pyo

from multiperiod import build_uc, load_window
from race import _size

TIME_LIMIT = 300.0
MIP_GAP = 1e-4


def solve(m, label):
    nv, nc = _size(m)
    nb = sum(1 for v in m.component_data_objects(pyo.Var, active=True) if v.is_binary())
    opt = pyo.SolverFactory("gurobi")
    opt.options["TimeLimit"] = TIME_LIMIT
    opt.options["MIPGap"] = MIP_GAP
    opt.options["Threads"] = 4
    t0 = time.perf_counter()
    try:
        res = opt.solve(m, load_solutions=False)
    except Exception as e:
        return {"label": label, "status": f"error {type(e).__name__}", "vars": nv, "cons": nc, "bins": nb,
                "solve_s": time.perf_counter() - t0}
    dt = time.perf_counter() - t0
    tc = str(res.solver.termination_condition)
    row = {"label": label, "status": tc, "vars": nv, "cons": nc, "bins": nb, "solve_s": dt}
    try:
        lb, ub = float(res.problem.lower_bound), float(res.problem.upper_bound)
        row["obj"] = ub
        row["mipgap_%"] = 100.0 * abs(ub - lb) / max(abs(ub), 1e-9)
    except Exception:
        pass
    return row


def run(case_dir, case, periods=(1, 2, 4, 8, 12, 24), start=4000, invest=False):
    print(f"{case}  start={start}  invest={invest}  (time limit {TIME_LIMIT:.0f}s, MIP gap {MIP_GAP})")
    hdr = (f"{'T':>3s} {'formulation':>12s} {'status':>12s} {'objective':>13s} {'gap%':>7s} "
           f"{'vars':>7s} {'cons':>7s} {'bins':>6s} {'solve s':>9s} {'x vs LP':>8s}")
    print(hdr)
    print("-" * len(hdr))
    for T in periods:
        w = load_window(case_dir, case, start=start, n_hours=T)
        row_lp = solve(build_uc(w, conic=False, cycles=True, segments=10, invest=invest), "LP L=10")
        row_so = solve(build_uc(w, conic=True,  cycles=True,               invest=invest), "SOCP")
        for r in (row_lp, row_so):
            ratio = (r["solve_s"] / row_lp["solve_s"]) if row_lp["solve_s"] > 0 else float("nan")
            print(f"{T:3d} {r['label']:>12s} {r['status']:>12s} {r.get('obj', float('nan')):13.1f} "
                  f"{r.get('mipgap_%', float('nan')):7.3f} {r['vars']:7d} {r['cons']:7d} {r['bins']:6d} "
                  f"{r['solve_s']:9.2f} {ratio:8.1f}")
        print()


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "openTEPES/cases/9n_AC"
    c = sys.argv[2] if len(sys.argv) > 2 else "9n_AC"
    T = tuple(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else (1, 2, 4, 8, 12, 24)
    inv = len(sys.argv) > 4 and sys.argv[4].lower() in ("1", "true", "invest")
    run(d, c, periods=T, invest=inv)
