"""Multi-period AC unit commitment: the experiment that decides SOCP against the piecewise-linear model.

The snapshot study found the branch-flow SOCP both tighter and faster than the piecewise-linear model.
That result cannot settle the question, because the reason Alvarez et al. linearise is not the continuous
relaxation — it is that a MISOCP with commitment binaries over many periods is much harder for a
branch-and-bound solver than a MILP. Gurobi solves a MISOCP by outer-approximating the cone at every node;
a MILP has no such overhead.

So this harness adds what the snapshot lacked:

  * commitment binaries per unit per hour, with start-up/shut-down logic, minimum up and down times, ramps
    and a start-up cost;
  * optionally line investment binaries, which is the expansion-planning setting the papers target;
  * several periods, so the integer tree actually has to be searched.

Everything else — the network block, the cycle constraints, the envelope — is identical to the snapshot
prototypes, so any difference in scaling is attributable to the cone.
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo

sys.path.insert(0, str(Path(__file__).parent))
from case import _read, gen_index_col, load_snapshot          # noqa: E402
from formulations import _cycles, _topology                    # noqa: E402


@dataclass
class Window:
    """A contiguous block of load levels sharing one network and one generator fleet."""
    name:      str
    base:      object                     # a Snapshot carrying the network, gens and shunts
    hours:     list
    pd_mw:     dict                       # (t, bus) -> MW
    qd_mvar:   dict                       # (t, bus) -> Mvar
    uc:        pd.DataFrame               # per-unit commitment attributes


def load_window(case_dir, case, start=0, n_hours=24):
    """Load ``n_hours`` consecutive load levels plus the unit-commitment attributes."""
    base = load_snapshot(case_dir, case, hour=start)

    dem = _read(Path(case_dir), "Demand", case, index_col=[0, 1, 2]).fillna(0.0)
    qpath = Path(case_dir) / f"oT_Data_ReactiveDemand_{case}.csv"
    qdem = pd.read_csv(qpath, encoding="utf-8-sig", index_col=[0, 1, 2]).fillna(0.0) if qpath.exists() else dem * 0.0

    rows = list(dem.index[start:start + n_hours])
    pd_mw   = {(t, b): float(dem.loc[r].get(b, 0.0))  for t, r in enumerate(rows) for b in base.buses}
    qd_mvar = {(t, b): float(qdem.loc[r].get(b, 0.0)) for t, r in enumerate(rows) for b in base.buses}

    g = _read(Path(case_dir), "Generation", case).set_index(gen_index_col(Path(case_dir), case))
    num = g.select_dtypes("number").columns
    g = g.fillna({c: 0.0 for c in num})
    uc = pd.DataFrame({
        "pmin":    g["MinimumPower"].astype(float),
        "sucost":  g["StartUpCost"].astype(float),
        "nocost":  g["ConstantTerm"].astype(float),
        "uptime":  pd.to_numeric(g["UpTime"],   errors="coerce").fillna(0.0).clip(lower=0).astype(int),
        "dntime":  pd.to_numeric(g["DownTime"], errors="coerce").fillna(0.0).clip(lower=0).astype(int),
        "rampup":  g["RampUp"].astype(float),
        "rampdn":  g["RampDown"].astype(float),
    }).reindex(base.gens.index)
    # a zero ramp means "unlimited" in openTEPES, not "frozen"
    big = base.gens["pmax"].max()
    uc.loc[uc["rampup"] <= 0.0, "rampup"] = big
    uc.loc[uc["rampdn"] <= 0.0, "rampdn"] = big
    uc["pmin"] = uc["pmin"].clip(upper=base.gens["pmax"])

    return Window(name=f"{case}[{start}:{start+n_hours}]", base=base, hours=rows,
                  pd_mw=pd_mw, qd_mvar=qd_mvar, uc=uc)


def build_uc(w: Window, *, conic: bool = True, cycles: bool = True, segments: int = 10,
             invest: bool = False, relax_binaries: bool = False):
    """Multi-period AC unit commitment on the branch flow model.

    ``conic``  keeps the second-order cone (Chowdhury et al.); ``False`` uses the piecewise linearisation
    (Alvarez et al.), so the model becomes a pure MILP.
    ``invest`` adds a build/no-build binary per candidate branch, shared across all periods.
    """
    snap, uc = w.base, w.uc
    S = snap.sbase_mva
    T = len(w.hours)
    br, frm, to, gsh, bsh = _topology(snap)

    m = pyo.ConcreteModel()
    m.T = pyo.RangeSet(0, T - 1)
    m.G = pyo.Set(initialize=list(snap.gens.index))
    m.N = pyo.Set(initialize=snap.buses)
    m.B = pyo.Set(initialize=br, dimen=3)
    m._T, m._S = T, S

    r  = {b: snap.branches.r_pu[b] for b in br}
    x  = {b: snap.branches.x_pu[b] for b in br}
    z2 = {b: r[b] ** 2 + x[b] ** 2 for b in br}
    Gb = {b:  r[b] / z2[b] for b in br}
    Bb = {b: -x[b] / z2[b] for b in br}
    smax = {b: snap.branches.s_mva[b] / S for b in br}
    p_box = {b: smax[b] * snap.vmax / snap.vmin for b in br}
    l_hi  = {b: (smax[b] / snap.vmin) ** 2 for b in br}
    u_lo, u_hi = snap.vmin ** 2, snap.vmax ** 2

    # ---- commitment ------------------------------------------------------------------------------------
    dom = pyo.UnitInterval if relax_binaries else pyo.Binary
    m.on = pyo.Var(m.G, m.T, within=dom)
    m.su = pyo.Var(m.G, m.T, within=pyo.UnitInterval)
    m.sd = pyo.Var(m.G, m.T, within=pyo.UnitInterval)
    m.Pg = pyo.Var(m.G, m.T, within=pyo.NonNegativeReals)
    m.Qg = pyo.Var(m.G, m.T, bounds=lambda m, g, t: (snap.gens.qmin[g] / S, snap.gens.qmax[g] / S))

    m.pmax_c = pyo.Constraint(m.G, m.T, rule=lambda m, g, t: m.Pg[g, t] <= snap.gens.pmax[g] / S * m.on[g, t])
    m.pmin_c = pyo.Constraint(m.G, m.T, rule=lambda m, g, t: m.Pg[g, t] >= uc.pmin[g] / S * m.on[g, t])

    def logic(m, g, t):
        prev = m.on[g, t - 1] if t > 0 else 0.0
        return m.on[g, t] - prev == m.su[g, t] - m.sd[g, t]
    m.logic = pyo.Constraint(m.G, m.T, rule=logic)

    def minup(m, g, t):
        k = int(uc.uptime[g])
        if k <= 1 or t < k - 1:
            return pyo.Constraint.Skip
        return sum(m.su[g, tt] for tt in range(t - k + 1, t + 1)) <= m.on[g, t]
    m.minup = pyo.Constraint(m.G, m.T, rule=minup)

    def mindn(m, g, t):
        k = int(uc.dntime[g])
        if k <= 1 or t < k - 1:
            return pyo.Constraint.Skip
        return sum(m.sd[g, tt] for tt in range(t - k + 1, t + 1)) <= 1 - m.on[g, t]
    m.mindn = pyo.Constraint(m.G, m.T, rule=mindn)

    def rampu(m, g, t):
        if t == 0:
            return pyo.Constraint.Skip
        return m.Pg[g, t] - m.Pg[g, t - 1] <= uc.rampup[g] / S
    m.rampu = pyo.Constraint(m.G, m.T, rule=rampu)

    def rampd(m, g, t):
        if t == 0:
            return pyo.Constraint.Skip
        return m.Pg[g, t - 1] - m.Pg[g, t] <= uc.rampdn[g] / S
    m.rampd = pyo.Constraint(m.G, m.T, rule=rampd)

    # ---- investment ------------------------------------------------------------------------------------
    # The cheapest quarter of the branches by rating become candidates, so the integer tree carries a
    # network decision as well as a commitment one. Their flows are switched by the build variable.
    if invest:
        cand = sorted(br, key=lambda b: snap.branches.s_mva[b])[: max(1, len(br) // 4)]
        m.CAND = pyo.Set(initialize=cand, dimen=3)
        m.z = pyo.Var(m.CAND, within=dom)
        m.invcost = {b: 1000.0 * snap.branches.s_mva[b] / S for b in cand}
    else:
        m.CAND = pyo.Set(initialize=[], dimen=3)
        m.invcost = {}

    # ---- network, one block per period -----------------------------------------------------------------
    m.u = pyo.Var(m.N, m.T, bounds=(u_lo, u_hi), initialize=1.0)
    m.P = pyo.Var(m.B, m.T, bounds=lambda m, i, j, c, t: (-p_box[i, j, c], p_box[i, j, c]), initialize=0.0)
    m.Q = pyo.Var(m.B, m.T, bounds=lambda m, i, j, c, t: (-p_box[i, j, c], p_box[i, j, c]), initialize=0.0)
    m.l = pyo.Var(m.B, m.T, bounds=lambda m, i, j, c, t: (0.0, l_hi[i, j, c]), initialize=0.0)

    m.vref = pyo.Constraint(m.T, rule=lambda m, t: m.u[snap.ref_bus, t] == 1.0)

    m.drop = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                            m.u[j, t] == m.u[i, t] - 2 * (r[i, j, c] * m.P[i, j, c, t] + x[i, j, c] * m.Q[i, j, c, t])
                            + z2[i, j, c] * m.l[i, j, c, t])

    g_at = {n: [g for g in snap.gens.index if snap.gens.bus[g] == n] for n in snap.buses}

    m.pbal = pyo.Constraint(m.N, m.T, rule=lambda m, n, t:
                            sum(m.Pg[g, t] for g in g_at[n]) - w.pd_mw[t, n] / S
                            - sum(m.P[b, t] for b in frm[n])
                            + sum(m.P[b, t] - r[b] * m.l[b, t] for b in to[n])
                            - gsh[n] * m.u[n, t] == 0)

    m.qbal = pyo.Constraint(m.N, m.T, rule=lambda m, n, t:
                            sum(m.Qg[g, t] for g in g_at[n]) - w.qd_mvar[t, n] / S
                            - sum(m.Q[b, t] for b in frm[n])
                            + sum(m.Q[b, t] - x[b] * m.l[b, t] for b in to[n])
                            + bsh[n] * m.u[n, t] == 0)

    if conic:
        m.soc = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                               m.P[i, j, c, t] ** 2 + m.Q[i, j, c, t] ** 2 <= m.u[i, t] * m.l[i, j, c, t])
    else:
        m.K = pyo.RangeSet(1, segments)
        m.dP = pyo.Var(m.B, m.T, m.K, within=pyo.NonNegativeReals)
        m.dQ = pyo.Var(m.B, m.T, m.K, within=pyo.NonNegativeReals)
        m.Pp = pyo.Var(m.B, m.T, within=pyo.NonNegativeReals)
        m.Pn = pyo.Var(m.B, m.T, within=pyo.NonNegativeReals)
        m.Qp = pyo.Var(m.B, m.T, within=pyo.NonNegativeReals)
        m.Qn = pyo.Var(m.B, m.T, within=pyo.NonNegativeReals)
        d = {b: smax[b] / segments for b in br}
        m.psplit = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t: m.P[i, j, c, t] == m.Pp[i, j, c, t] - m.Pn[i, j, c, t])
        m.qsplit = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t: m.Q[i, j, c, t] == m.Qp[i, j, c, t] - m.Qn[i, j, c, t])
        m.pabs   = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t: m.Pp[i, j, c, t] + m.Pn[i, j, c, t] == sum(m.dP[i, j, c, t, k] for k in m.K))
        m.qabs   = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t: m.Qp[i, j, c, t] + m.Qn[i, j, c, t] == sum(m.dQ[i, j, c, t, k] for k in m.K))
        m.dPcap  = pyo.Constraint(m.B, m.T, m.K, rule=lambda m, i, j, c, t, k: m.dP[i, j, c, t, k] <= d[i, j, c])
        m.dQcap  = pyo.Constraint(m.B, m.T, m.K, rule=lambda m, i, j, c, t, k: m.dQ[i, j, c, t, k] <= d[i, j, c])
        m.pwl    = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                                  m.l[i, j, c, t] >= sum((2 * k - 1) * d[i, j, c] * (m.dP[i, j, c, t, k] + m.dQ[i, j, c, t, k])
                                                         for k in m.K))

    # thermal limit, switched off on a branch that is not built
    def thermal(m, i, j, c, t):
        if (i, j, c) in m.CAND:
            return m.l[i, j, c, t] <= l_hi[i, j, c] * m.z[i, j, c]
        return m.l[i, j, c, t] <= l_hi[i, j, c]
    m.thermal = pyo.Constraint(m.B, m.T, rule=thermal)

    if invest:
        # a branch that is not built carries no flow
        m.pcap1 = pyo.Constraint(m.CAND, m.T, rule=lambda m, i, j, c, t: m.P[i, j, c, t] <=  p_box[i, j, c] * m.z[i, j, c])
        m.pcap2 = pyo.Constraint(m.CAND, m.T, rule=lambda m, i, j, c, t: m.P[i, j, c, t] >= -p_box[i, j, c] * m.z[i, j, c])
        m.qcap1 = pyo.Constraint(m.CAND, m.T, rule=lambda m, i, j, c, t: m.Q[i, j, c, t] <=  p_box[i, j, c] * m.z[i, j, c])
        m.qcap2 = pyo.Constraint(m.CAND, m.T, rule=lambda m, i, j, c, t: m.Q[i, j, c, t] >= -p_box[i, j, c] * m.z[i, j, c])

    if cycles:
        m.th = pyo.Var(m.N, m.T, bounds=(-math.pi / 2, math.pi / 2), initialize=0.0)
        m.thref = pyo.Constraint(m.T, rule=lambda m, t: m.th[snap.ref_bus, t] == 0.0)

        def _M(m, i, j, c, t):
            return (Bb[i, j, c] * m.P[i, j, c, t] - Gb[i, j, c] * m.Q[i, j, c, t]) / (Gb[i, j, c] ** 2 + Bb[i, j, c] ** 2)

        def _t(i, j, c):
            return max(abs(snap.branches.angmin[i, j, c]), abs(snap.branches.angmax[i, j, c]))

        m.env_up = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                                  m.th[i, t] - m.th[j, t] <= _M(m, i, j, c, t) / (snap.vmin ** 2 * math.cos(_t(i, j, c) / 2))
                                  + math.tan(_t(i, j, c) / 2) - _t(i, j, c) / 2)
        m.env_lo = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                                  m.th[i, t] - m.th[j, t] >= _M(m, i, j, c, t) / (snap.vmax ** 2 * math.cos(_t(i, j, c) / 2))
                                  - math.tan(_t(i, j, c) / 2) + _t(i, j, c) / 2)

        cyc = _cycles(snap, shortest=True)
        m._ncycles = len(cyc)
        if cyc:
            m.C = pyo.RangeSet(0, len(cyc) - 1)
            m.cyc = pyo.Constraint(m.C, m.T, rule=lambda m, k, t:
                                   sum(s * (m.th[i, t] - m.th[j, t]) for (i, j, c, s) in cyc[k]) == 0)
        m.angb = pyo.Constraint(m.B, m.T, rule=lambda m, i, j, c, t:
                                pyo.inequality(snap.branches.angmin[i, j, c], m.th[i, t] - m.th[j, t],
                                               snap.branches.angmax[i, j, c]))
    else:
        m._ncycles = 0

    # ---- objective -------------------------------------------------------------------------------------
    m.cost = pyo.Objective(
        expr=sum(snap.gens.cost[g] * m.Pg[g, t] * S + uc.nocost[g] * m.on[g, t] + uc.sucost[g] * m.su[g, t]
                 for g in m.G for t in m.T)
             + sum(m.invcost[b] * m.z[b] for b in m.CAND),
        sense=pyo.minimize)

    m._kind = ("bfm-socp" if conic else "bfm-lp") + ("+inv" if invest else "")
    return m
