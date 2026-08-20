"""Race the AC formulations and report accuracy against CPU time.

Three numbers matter and they measure different things:

  * **optimality gap** — cost against the exact AC OPF. A relaxation lands below it, an approximation or a
    restriction can land either side. Sign is informative: below means optimistic, above means conservative.
  * **physical error** — take the dispatch the formulation chose, solve an exact AC power flow with it, and
    compare what the formulation *predicted* against what the network *does*. This is the error a planning
    study inherits, and it is not the optimality gap.
  * **cycle mismatch** — the sum of angle differences round each independent cycle, recovered from the branch
    flows. A W-space or branch-flow relaxation without cyclic constraints can return flows that correspond to
    no consistent set of angles; this is the metric Chowdhury et al. report in their Table I.
"""
from __future__ import annotations

import math
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
warnings.filterwarnings("ignore")

import pyomo.environ as pyo

from case import load_snapshot, summarise
from formulations import _cycles, _topology, build_bfm, build_dc
from reference import ac_powerflow, true_acopf

SOLVER = "gurobi"


def _size(m):
    nv = sum(len(v) for v in m.component_objects(pyo.Var, active=True))
    nc = sum(len(c) for c in m.component_objects(pyo.Constraint, active=True))
    return nv, nc


def _recover_angles(snap, m):
    """Angle differences implied by the branch flows, via sin(theta_ij) = M / (Vi Vj).

    Uses the formulation's own voltages when it has them, so the mismatch measured is the formulation's, not
    an artefact of assuming flat voltage.
    """
    out = {}
    for b in m.B:
        r, x = snap.branches.r_pu[b], snap.branches.x_pu[b]
        z2 = r ** 2 + x ** 2
        G, B = r / z2, -x / z2
        P = pyo.value(m.P[b])
        Q = pyo.value(m.Q[b]) if hasattr(m, "Q") else 0.0
        M = (B * P - G * Q) / (G ** 2 + B ** 2)
        if hasattr(m, "u"):
            vi = math.sqrt(max(pyo.value(m.u[b[0]]), 1e-9))
            vj = math.sqrt(max(pyo.value(m.u[b[1]]), 1e-9))
        else:
            vi = vj = 1.0
        s = max(-1.0, min(1.0, M / (vi * vj)))
        out[b] = math.asin(s)
    return out


def evaluate(name, m, snap, ref, *, build_s=0.0):
    """Solve one prototype and score it."""
    nv, nc = _size(m)
    t0 = time.perf_counter()
    res = pyo.SolverFactory(SOLVER).solve(m)
    solve_s = time.perf_counter() - t0
    status = str(res.solver.termination_condition)
    row = {"name": name, "status": status, "vars": nv, "cons": nc,
           "build_s": build_s, "solve_s": solve_s}
    if status != "optimal":
        return row

    S = snap.sbase_mva
    row["cost"] = pyo.value(m.cost)
    row["gap_%"] = 100.0 * (row["cost"] - ref["cost"]) / ref["cost"]

    dispatch = {g: pyo.value(m.Pg[g]) * S for g in m.G}
    row["pred_loss_MW"] = (sum(pyo.value(m.l[b]) * snap.branches.r_pu[b] for b in m.B) * S
                           if hasattr(m, "l") else
                           sum(pyo.value(m.Ls[b]) for b in m.B) * 2 * S if hasattr(m, "Ls") else 0.0)

    # cone exactness, where there is a cone
    if hasattr(m, "l") and hasattr(m, "u"):
        row["cone_gap"] = max(abs(pyo.value(m.u[b[0]]) * pyo.value(m.l[b])
                                  - pyo.value(m.P[b]) ** 2 - pyo.value(m.Q[b]) ** 2) for b in m.B)

    # cycle mismatch from the recovered angles
    ang = _recover_angles(snap, m)
    cyc = _cycles(snap, shortest=True)
    if cyc:
        row["cycle_mismatch_deg"] = max(abs(sum(s * ang[(i, j, c)] for (i, j, c, s) in k)) for k in cyc) * 180 / math.pi

    # physical error: replay the dispatch through an exact AC power flow
    vset = None
    if hasattr(m, "u"):
        vset = {g: math.sqrt(max(pyo.value(m.u[snap.gens.bus[g]]), 1e-9)) for g in m.G}
    pf = ac_powerflow(snap, dispatch, vset)
    if pf["ok"]:
        row["ac_loss_MW"] = pf["total_loss_mw"]
        row["loss_err_MW"] = row["pred_loss_MW"] - pf["total_loss_mw"]
        row["ac_vmin"], row["ac_vmax"] = pf["vm_min"], pf["vm_max"]
        row["v_violation"] = max(0.0, snap.vmin - pf["vm_min"]) + max(0.0, pf["vm_max"] - snap.vmax)
        if hasattr(m, "u"):
            row["v_err_pu"] = max(abs(math.sqrt(max(pyo.value(m.u[n]), 1e-9)) - pf["vm"][n]) for n in m.N)
        # worst thermal overload the dispatch actually causes
        worst = 0.0
        for b in m.B:
            key = (b[0], b[1], b[2])
            actual = math.hypot(pf["flow_p"].get(key, 0.0), pf["flow_q"].get(key, 0.0))
            worst = max(worst, actual / snap.branches.s_mva[b])
        row["max_loading_%"] = 100.0 * worst
    else:
        row["ac_pf"] = "diverged"
    return row


def main(case_dir, case, segments=(4, 10, 25)):
    snap = load_snapshot(case_dir, case)
    print(summarise(snap))

    ref = true_acopf(snap)
    if not ref["ok"]:
        print("reference AC OPF failed:", ref["error"])
        return
    print(f"\nreference (exact AC OPF): cost {ref['cost']:.2f} EUR/h, losses {ref['total_loss_mw']:.3f} MW, "
          f"V in [{ref['vm_min']:.4f}, {ref['vm_max']:.4f}]\n")

    specs = [
        ("DC",                      lambda: build_dc(snap)),
        ("DC + 2% loss factor",     lambda: build_dc(snap, loss_factor=0.02)),
        ("BFM-SOCP, no cycles",     lambda: build_bfm(snap, conic=True,  cycles=False)),
        ("BFM-SOCP + cycles [A]",   lambda: build_bfm(snap, conic=True,  cycles=True)),
        ("BFM-SOCP + cyc, nx basis", lambda: build_bfm(snap, conic=True, cycles=True, shortest_cycles=False)),
    ]
    for k in segments:
        specs.append((f"BFM-LP + cycles [B], L={k}", lambda k=k: build_bfm(snap, conic=False, cycles=True, segments=k)))

    rows = []
    for name, mk in specs:
        t0 = time.perf_counter()
        m = mk()
        build_s = time.perf_counter() - t0
        rows.append(evaluate(name, m, snap, ref, build_s=build_s))

    hdr = (f"{'formulation':28s} {'cost':>10s} {'gap%':>7s} {'loss MW':>8s} {'lossErr':>8s} "
           f"{'cycMis°':>8s} {'coneGap':>9s} {'Vviol':>7s} {'load%':>7s} {'vars':>6s} {'cons':>6s} {'build':>6s} {'solve':>6s}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if r.get("status") != "optimal":
            print(f"{r['name']:28s} {r['status']}")
            continue
        print(f"{r['name']:28s} {r['cost']:10.2f} {r['gap_%']:+7.2f} {r.get('pred_loss_MW',0):8.3f} "
              f"{r.get('loss_err_MW',float('nan')):+8.3f} {r.get('cycle_mismatch_deg',float('nan')):8.3f} "
              f"{r.get('cone_gap',float('nan')):9.1e} {r.get('v_violation',float('nan')):7.4f} "
              f"{r.get('max_loading_%',float('nan')):7.1f} {r['vars']:6d} {r['cons']:6d} "
              f"{r['build_s']:6.2f} {r['solve_s']:6.2f}")
    return rows


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "openTEPES/cases/9n_AC"
    c = sys.argv[2] if len(sys.argv) > 2 else "9n_AC"
    main(d, c)
