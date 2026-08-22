"""The competing AC network formulations, as single-snapshot economic dispatch models in Pyomo.

Every prototype minimises the same objective over the same generator set and differs only in how it
represents the network. That is the point: any difference in the answer is attributable to the network
formulation and nothing else.

Everything is in per unit on the case's SBase, converted back to MW only at the boundary.

Sign conventions, fixed once here because getting them wrong produces plausible-looking wrong answers:

  * ``P[i,j,c]`` is the active power entering branch (i,j,c) at its *from* end i. Losses are ``P_ij + P_ji``.
  * A shunt susceptance ``b > 0`` is capacitive and **injects** ``b * u`` of reactive power.
  * Line charging is the pi model: half the branch's total ``b_pu`` is lumped at each end bus.
  * ``B_ij``, ``G_ij`` are the off-diagonal admittance entries: ``G = r/(r^2+x^2)``, ``B = -x/(r^2+x^2)``.
"""
from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx
import pyomo.environ as pyo

L_SEGMENTS = 10          # piecewise-linear segments per square term, matching openTEPES_PRO's RangeSet(10)


# ----------------------------------------------------------------------------------------------------
# shared scaffolding
# ----------------------------------------------------------------------------------------------------

def _topology(snap):
    """Return (branch list, incident maps, per-bus lumped shunt g/b in p.u.)."""
    br = list(snap.branches.index)
    frm, to = defaultdict(list), defaultdict(list)
    for (i, j, c) in br:
        frm[i].append((i, j, c))
        to[j].append((i, j, c))

    gsh, bsh = defaultdict(float), defaultdict(float)
    for (i, j, c), row in snap.branches.iterrows():
        bsh[i] += row.b_pu / 2.0                 # pi model: half the charging at each end
        bsh[j] += row.b_pu / 2.0
    if not snap.shunts.empty:
        for _, row in snap.shunts.iterrows():
            if row["Node"] in snap.buses:
                bsh[row["Node"]] += float(row["Bshb"])
                gsh[row["Node"]] += float(row.get("Gshb", 0.0))
    return br, frm, to, gsh, bsh


def _cycles(snap, shortest: bool = True):
    """Independent cycles as ordered lists of (i, j, c, orientation).

    ``shortest=True`` follows Chowdhury et al., who take the shortest mesh cycle when a branch belongs to
    several; ``False`` uses networkx's cycle basis, which is what openTEPES does today.
    """
    g = nx.Graph()
    for (i, j, c) in snap.branches.index:
        g.add_edge(i, j)
    basis = nx.minimum_cycle_basis(g) if shortest else nx.cycle_basis(g)

    out = []
    for cyc in basis:
        # minimum_cycle_basis returns an unordered node set; walk it into a closed path
        sub = g.subgraph(cyc)
        try:
            order = nx.cycle_basis(sub)[0] if not shortest else _order_cycle(sub, cyc)
        except (IndexError, ValueError):
            continue
        edges = []
        ok = True
        for a, b in zip(order, order[1:] + order[:1]):
            match = [(i, j, c) for (i, j, c) in snap.branches.index if (i, j) == (a, b) or (i, j) == (b, a)]
            if not match:
                ok = False
                break
            i, j, c = match[0]
            edges.append((i, j, c, +1 if (i, j) == (a, b) else -1))
        if ok and edges:
            out.append(edges)
    return out


def _order_cycle(sub, nodes):
    start = next(iter(nodes))
    order, seen, cur = [start], {start}, start
    while len(order) < len(nodes):
        nxt = [n for n in sub.neighbors(cur) if n not in seen]
        if not nxt:
            raise ValueError("cycle does not close")
        cur = nxt[0]
        order.append(cur)
        seen.add(cur)
    return order


def _base_model(snap):
    """Generator variables, objective and the bookkeeping every formulation shares."""
    m = pyo.ConcreteModel()
    m.S = snap.sbase_mva
    m.G = pyo.Set(initialize=list(snap.gens.index))
    m.N = pyo.Set(initialize=snap.buses)

    m.Pg = pyo.Var(m.G, bounds=lambda m, g: (snap.gens.pmin[g] / m.S, snap.gens.pmax[g] / m.S))
    m.Qg = pyo.Var(m.G, bounds=lambda m, g: (snap.gens.qmin[g] / m.S, snap.gens.qmax[g] / m.S))

    m.cost = pyo.Objective(expr=sum(snap.gens.cost[g] * m.Pg[g] * m.S for g in m.G), sense=pyo.minimize)

    m.g_at = {n: [g for g in snap.gens.index if snap.gens.bus[g] == n] for n in snap.buses}
    m.Pd = {n: snap.pd_mw[n] / snap.sbase_mva for n in snap.buses}
    m.Qd = {n: snap.qd_mvar[n] / snap.sbase_mva for n in snap.buses}
    return m


# ----------------------------------------------------------------------------------------------------
# 1-2. DC, with and without a loss factor
# ----------------------------------------------------------------------------------------------------

def build_dc(snap, *, loss_factor: float = 0.0):
    m = _base_model(snap)
    br, frm, to, _, _ = _topology(snap)
    m.B = pyo.Set(initialize=br, dimen=3)

    m.th = pyo.Var(m.N, bounds=(-math.pi / 2, math.pi / 2), initialize=0.0)
    m.P  = pyo.Var(m.B, bounds=lambda m, i, j, c: (-snap.branches.s_mva[i, j, c] / m.S,
                                                    snap.branches.s_mva[i, j, c] / m.S))
    m.Ls = pyo.Var(m.B, within=pyo.NonNegativeReals, initialize=0.0)

    m.ref = pyo.Constraint(expr=m.th[snap.ref_bus] == 0.0)

    def kvl(m, i, j, c):
        return m.P[i, j, c] == (m.th[i] - m.th[j]) / snap.branches.x_pu[i, j, c]
    m.kvl = pyo.Constraint(m.B, rule=kvl)

    if loss_factor > 0.0:
        # openTEPES's loss model: half the loss charged at each end, linearised as two inequalities
        m.l1 = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Ls[i, j, c] >= -0.5 * loss_factor * m.P[i, j, c])
        m.l2 = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Ls[i, j, c] >= +0.5 * loss_factor * m.P[i, j, c])
    else:
        m.lfix = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Ls[i, j, c] == 0.0)

    def bal(m, n):
        return (sum(m.Pg[g] for g in m.g_at[n]) - m.Pd[n]
                - sum(m.P[b] + m.Ls[b] for b in frm[n])
                + sum(m.P[b] - m.Ls[b] for b in to[n]) == 0)
    m.bal = pyo.Constraint(m.N, rule=bal)

    m.Qg.fix(0.0)
    m._kind = "dc"
    return m


# ----------------------------------------------------------------------------------------------------
# 3-5. Branch flow model — Chowdhury et al. (SOCP) and Alvarez et al. (LP)
# ----------------------------------------------------------------------------------------------------

def build_bfm(snap, *, conic: bool = True, cycles: bool = True, shortest_cycles: bool = True,
              segments: int = L_SEGMENTS):
    """Branch flow model.

    ``conic=True``  keeps the exact-current equation as the second-order cone (14) of Chowdhury et al.
    ``conic=False`` replaces it with the piecewise linearisation of Alvarez et al., giving an LP.
    ``cycles``      adds the cyclic angle constraint (15) with the convex envelope (16)-(17).
    """
    m = _base_model(snap)
    br, frm, to, gsh, bsh = _topology(snap)
    m.B = pyo.Set(initialize=br, dimen=3)

    smax = {b: snap.branches.s_mva[b] / m.S for b in br}
    r    = {b: snap.branches.r_pu[b] for b in br}
    x    = {b: snap.branches.x_pu[b] for b in br}
    z2   = {b: r[b] ** 2 + x[b] ** 2 for b in br}
    Gb   = {b:  r[b] / z2[b] for b in br}
    Bb   = {b: -x[b] / z2[b] for b in br}

    u_lo, u_hi = snap.vmin ** 2, snap.vmax ** 2
    l_hi = {b: (smax[b] / snap.vmin) ** 2 for b in br}          # (7): current limit at the lowest voltage

    # The thermal limit belongs on the current, not on the active power: with reactive flow and an off-nominal
    # voltage a branch can carry more MW than its MVA rating suggests. Bounding P by smax would silently impose a
    # tighter limit than the physics and cost the relaxation its status as a lower bound. The boxes below are loose
    # enough never to bind; the real limit is l <= l_hi together with the cone.
    p_box = {b: smax[b] * snap.vmax / snap.vmin for b in br}

    m.u = pyo.Var(m.N, bounds=(u_lo, u_hi), initialize=1.0)
    m.P = pyo.Var(m.B, bounds=lambda m, i, j, c: (-p_box[i, j, c], p_box[i, j, c]), initialize=0.0)
    m.Q = pyo.Var(m.B, bounds=lambda m, i, j, c: (-p_box[i, j, c], p_box[i, j, c]), initialize=0.0)
    m.l = pyo.Var(m.B, bounds=lambda m, i, j, c: (0.0, l_hi[i, j, c]), initialize=0.0)

    # The reference bus voltage is pinned, matching the slack of the exact AC power flow the prototypes are
    # measured against. Without it the prototypes optimise a degree of freedom the reference does not have.
    m.vref = pyo.Constraint(expr=m.u[snap.ref_bus] == 1.0)

    # (9) voltage drop along the branch
    m.drop = pyo.Constraint(m.B, rule=lambda m, i, j, c:
                            m.u[j] == m.u[i] - 2 * (r[i, j, c] * m.P[i, j, c] + x[i, j, c] * m.Q[i, j, c])
                            + z2[i, j, c] * m.l[i, j, c])

    # (11)/(12) balances. The from-end carries P; the to-end receives P - r*l. A capacitive shunt injects.
    def pbal(m, n):
        return (sum(m.Pg[g] for g in m.g_at[n]) - m.Pd[n]
                - sum(m.P[b] for b in frm[n])
                + sum(m.P[b] - r[b] * m.l[b] for b in to[n])
                - gsh[n] * m.u[n] == 0)
    m.pbal = pyo.Constraint(m.N, rule=pbal)

    def qbal(m, n):
        return (sum(m.Qg[g] for g in m.g_at[n]) - m.Qd[n]
                - sum(m.Q[b] for b in frm[n])
                + sum(m.Q[b] - x[b] * m.l[b] for b in to[n])
                + bsh[n] * m.u[n] == 0)
    m.qbal = pyo.Constraint(m.N, rule=qbal)

    if conic:
        # (14) rotated second-order cone: P^2 + Q^2 <= u_i * l_ij
        m.soc = pyo.Constraint(m.B, rule=lambda m, i, j, c:
                               m.P[i, j, c] ** 2 + m.Q[i, j, c] ** 2 <= m.u[i] * m.l[i, j, c])
    else:
        # Piecewise linearisation of the square terms, holding u_i at nominal. |P| = sum of segment
        # contributions and P^2 = sum (2k-1) * delta * segment, the classic staircase used in openTEPES_PRO.
        m.K = pyo.RangeSet(1, segments)
        m.dP = pyo.Var(m.B, m.K, within=pyo.NonNegativeReals)
        m.dQ = pyo.Var(m.B, m.K, within=pyo.NonNegativeReals)
        m.Pp = pyo.Var(m.B, within=pyo.NonNegativeReals)
        m.Pn = pyo.Var(m.B, within=pyo.NonNegativeReals)
        m.Qp = pyo.Var(m.B, within=pyo.NonNegativeReals)
        m.Qn = pyo.Var(m.B, within=pyo.NonNegativeReals)
        delta = {b: smax[b] / segments for b in br}

        m.psplit = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.P[i, j, c] == m.Pp[i, j, c] - m.Pn[i, j, c])
        m.qsplit = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Q[i, j, c] == m.Qp[i, j, c] - m.Qn[i, j, c])
        m.pabs   = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Pp[i, j, c] + m.Pn[i, j, c] == sum(m.dP[i, j, c, k] for k in m.K))
        m.qabs   = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.Qp[i, j, c] + m.Qn[i, j, c] == sum(m.dQ[i, j, c, k] for k in m.K))
        m.dPcap  = pyo.Constraint(m.B, m.K, rule=lambda m, i, j, c, k: m.dP[i, j, c, k] <= delta[i, j, c])
        m.dQcap  = pyo.Constraint(m.B, m.K, rule=lambda m, i, j, c, k: m.dQ[i, j, c, k] <= delta[i, j, c])
        m.pwl    = pyo.Constraint(m.B, rule=lambda m, i, j, c:
                                  m.l[i, j, c] >= sum((2 * k - 1) * delta[i, j, c] * (m.dP[i, j, c, k] + m.dQ[i, j, c, k])
                                                      for k in m.K))

    # (7) thermal limit expressed on the squared current
    m.thermal = pyo.Constraint(m.B, rule=lambda m, i, j, c: m.l[i, j, c] <= l_hi[i, j, c])

    if cycles:
        m.th = pyo.Var(m.N, bounds=(-math.pi / 2, math.pi / 2), initialize=0.0)
        m.ref = pyo.Constraint(expr=m.th[snap.ref_bus] == 0.0)

        # (16)-(17) the convex envelope on the angle difference, from the polyhedral sine envelope
        # sin d in [cos(t/2)(d + t/2) - sin(t/2), cos(t/2)(d - t/2) + sin(t/2)] with sin d = M/(Vi Vj).
        def env_up(m, i, j, c):
            t = max(abs(snap.branches.angmin[i, j, c]), abs(snap.branches.angmax[i, j, c]))
            M = (Bb[i, j, c] * m.P[i, j, c] - Gb[i, j, c] * m.Q[i, j, c]) / (Gb[i, j, c] ** 2 + Bb[i, j, c] ** 2)
            return m.th[i] - m.th[j] <= M / (snap.vmin ** 2 * math.cos(t / 2)) + math.tan(t / 2) - t / 2
        m.env_up = pyo.Constraint(m.B, rule=env_up)

        def env_lo(m, i, j, c):
            t = max(abs(snap.branches.angmin[i, j, c]), abs(snap.branches.angmax[i, j, c]))
            M = (Bb[i, j, c] * m.P[i, j, c] - Gb[i, j, c] * m.Q[i, j, c]) / (Gb[i, j, c] ** 2 + Bb[i, j, c] ** 2)
            return m.th[i] - m.th[j] >= M / (snap.vmax ** 2 * math.cos(t / 2)) - math.tan(t / 2) + t / 2
        m.env_lo = pyo.Constraint(m.B, rule=env_lo)

        # (15) the angle differences round every independent cycle sum to zero
        cyc = _cycles(snap, shortest=shortest_cycles)
        m.C = pyo.RangeSet(0, len(cyc) - 1) if cyc else pyo.RangeSet(0, -1)
        m._ncycles = len(cyc)
        if cyc:
            m.cyc = pyo.Constraint(m.C, rule=lambda m, k:
                                   sum(s * (m.th[i] - m.th[j]) for (i, j, c, s) in cyc[k]) == 0)
        # angle-difference band per branch
        m.angb = pyo.Constraint(m.B, rule=lambda m, i, j, c:
                                pyo.inequality(snap.branches.angmin[i, j, c], m.th[i] - m.th[j],
                                               snap.branches.angmax[i, j, c]))
    else:
        m._ncycles = 0

    m._kind = "bfm-socp" if conic else "bfm-lp"
    return m
