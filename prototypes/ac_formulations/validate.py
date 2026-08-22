"""Check a solved openTEPES AC case against physics computed outside openTEPES.

Every other check in this repository compares the model against itself. The relaxation gap in
``oT_Result_ACRelaxationGapSummary`` says the cone is closed; the angle band, the envelope and the
restoration pass all measure the model against its own definition of the relations they enforce. None of
that can detect a consistently wrong premise, and one went undetected through ten code reviews: the
angle-to-flow relation was written ``x P + r Q`` when it is ``x P - r Q``. It was found here.

Three checks, cheapest first. Run them on any solved AC case:

    python prototypes/ac_formulations/validate.py <case-dir> <case-name> [load-levels]

``branch_residual``  Compares the model's own branch flows against the textbook pi-model computed from
                     the model's own voltages and angles. Independent of every openTEPES constraint,
                     because the formula is derived from scratch. This is the check that caught the sign.

``loop_residual``    Recovers each branch's angle from its own flows and sums around each independent
                     cycle. The branch flow model works in |V|^2, P, Q and current; angles never appear
                     in its core equations. For a radial network that is complete. For a meshed one the
                     recovered angles must also close around every loop, and a solution whose loops do
                     not close is not an operating point the system can take up, however tight the cone.

``powerflow_error``  Rebuilds the network in pandapower from the same r, x, b and tap data, injects the
                     setpoints openTEPES chose, and runs Newton-Raphson. The strongest check: other
                     people's code, from the same inputs, must return the same voltages.

Two traps, both of which cost real time when this was written:

  * Use the susceptance actually IN SERVICE, not the nameplate. A candidate shunt the model declined to
    build has ``vQShunt = 0`` while ``pBusBshb`` still holds its rating, and injecting the rating put
    299 Mvar into the network that the solution did not contain.
  * HVDC links carry active power that has to appear at both ends. Leaving them out moves every voltage.
"""
from __future__ import annotations

import cmath
import math
import sys

import networkx as nx


def _v(m, p, sc, n, nd):
    return math.sqrt(max(m.vW[p, sc, n, nd](), 0.0))


def branch_residual(m, p, sc, n):
    """Worst mismatch in MW and Mvar between the model's branch flows and the exact series relation."""
    S = m.pSBase()
    wP = wQ = 0.0
    for (ni, nf, cc) in m.laa:
        tapf = m.pLineTapFactor[ni, nf, cc]
        Vi = cmath.rect(_v(m, p, sc, n, ni) * tapf, m.vTheta[p, sc, n, ni]())
        Vj = cmath.rect(_v(m, p, sc, n, nf),        m.vTheta[p, sc, n, nf]())
        y  = 1.0 / complex(m.pLineR[ni, nf, cc], m.pLineX[ni, nf, cc])
        Sij = Vi * ((Vi - Vj) * y).conjugate()
        wP = max(wP, abs(Sij.real - m.vFlowElec    [p, sc, n, ni, nf, cc]() / S) * S * 1000.0)
        wQ = max(wQ, abs(Sij.imag - m.vFlowReactFrw[p, sc, n, ni, nf, cc]() / S) * S * 1000.0)
    return wP, wQ


def loop_residual(m, p, sc, n):
    """Worst angle mismatch, in radians, around the independent cycles of the AC network."""
    S = m.pSBase()
    G = nx.Graph()
    for (ni, nf, cc) in m.laa:
        G.add_edge(ni, nf)
    th = {}
    for (ni, nf, cc) in m.laa:
        vi = _v(m, p, sc, n, ni) * m.pLineTapFactor[ni, nf, cc]
        vj = _v(m, p, sc, n, nf)
        # MINUS. See section 16 of doc/design/AC_OPF_Prototype_Results.md for the derivation and for what
        # a plus costs: 38 MW of branch flow error, invisible to every self-consistency check.
        val = (m.pLineX[ni, nf, cc] * m.vFlowElec    [p, sc, n, ni, nf, cc]()
             - m.pLineR[ni, nf, cc] * m.vFlowReactFrw[p, sc, n, ni, nf, cc]()) / S / max(vi * vj, 1e-12)
        th[(ni, nf)] = math.asin(max(-1.0, min(1.0, val)))
    worst = 0.0
    for cyc in nx.cycle_basis(G):
        tot = 0.0
        for a, b in zip(cyc, cyc[1:] + cyc[:1]):
            tot += th.get((a, b), 0.0) - th.get((b, a), 0.0)
        worst = max(worst, abs(tot))
    return worst


def powerflow_error(m, p, sc, n, kv=100.0, f_hz=50.0):
    """Worst voltage and angle difference against a pandapower Newton-Raphson power flow."""
    import pandapower as pp

    S  = m.pSBase() * 1000.0
    ZB = kv * kv / S
    net = pp.create_empty_network(sn_mva=S, f_hz=f_hz)
    b   = {nd: pp.create_bus(net, vn_kv=kv, name=str(nd)) for nd in m.nd}
    ref = m.rf.first()
    pp.create_ext_grid(net, b[ref], vm_pu=_v(m, p, sc, n, ref), va_degree=0.0)

    for (ni, nf, cc) in m.laa:
        r, x, bsh = m.pLineR[ni, nf, cc], m.pLineX[ni, nf, cc], m.pLineBsh[ni, nf, cc]()
        tap = 1.0 / m.pLineTapFactor[ni, nf, cc]
        if abs(tap - 1.0) < 1e-12:
            pp.create_line_from_parameters(net, b[ni], b[nf], length_km=1.0, r_ohm_per_km=r * ZB,
                                           x_ohm_per_km=x * ZB, max_i_ka=100.0,
                                           c_nf_per_km=bsh / ZB / (2.0 * math.pi * f_hz) * 1e9)
        else:
            pp.create_transformer_from_parameters(net, hv_bus=b[ni], lv_bus=b[nf], sn_mva=S,
                                                  vn_hv_kv=kv * tap, vn_lv_kv=kv, pfe_kw=0.0,
                                                  vkr_percent=r * 100.0, i0_percent=bsh * 100.0,
                                                  vk_percent=math.hypot(r, x) * 100.0)

    for la in getattr(m, 'lad', []):
        if (p,) + la not in m.pla:
            continue
        f_mw = m.vFlowElec[(p, sc, n) + la]() * 1000.0
        h_mw = (m.vLineLosses[(p, sc, n) + la]() * 1000.0) if (p,) + la in m.pll else 0.0
        pp.create_sgen(net, b[la[0]], p_mw=-(f_mw + h_mw), q_mvar=0.0)
        pp.create_sgen(net, b[la[1]], p_mw= (f_mw - h_mw), q_mvar=0.0)

    gen2n, q2n, sh2n = {}, {}, {}
    for nd, g in m.n2g:  gen2n.setdefault(nd, []).append(g)
    for nd, g in m.n2gq: q2n.setdefault(nd, []).append(g)
    for nd, sh in getattr(m, 'n2sh', []): sh2n.setdefault(nd, []).append(sh)

    for nd in m.nd:
        pD, qD = m.pDemandElec[p, sc, n, nd]() * 1000.0, m.pReactiveDemand[p, sc, n, nd]() * 1000.0
        pE = m.vENS[p, sc, n, nd]() * 1000.0
        qN = (m.vQNSPos[p, sc, n, nd]() - m.vQNSNeg[p, sc, n, nd]()) * 1000.0
        if pD or qD:
            pp.create_load(net, b[nd], p_mw=pD, q_mvar=qD)
        if pE or qN:
            pp.create_sgen(net, b[nd], p_mw=pE, q_mvar=qN)
        pG = sum(m.vTotalOutput[p, sc, n, g]() for g in gen2n.get(nd, []) if (p, g) in m.pg) * 1000.0
        pC = sum(m.vESSTotalCharge[p, sc, n, e]() for e in gen2n.get(nd, [])
                 if e in m.eh and (p, e) in m.peh) * 1000.0
        qG = sum(m.vReactiveTotalOutput[p, sc, n, g]() for g in q2n.get(nd, []) if (p, g) in m.pgq) * 1000.0
        if nd != ref and (pG or qG or pC):
            pp.create_sgen(net, b[nd], p_mw=pG - pC, q_mvar=qG)
        for sh in sh2n.get(nd, []):
            if (p, sc, n, sh) in m.psnsh:
                pW = m.vW[p, sc, n, nd]()
                pp.create_shunt(net, b[nd], p_mw=0.0,
                                q_mvar=-(m.vQShunt[p, sc, n, sh]() / pW if pW > 1e-9 else 0.0) * 1000.0)

    pp.runpp(net, algorithm='nr', max_iteration=100, tolerance_mva=1e-10, init='flat')
    dV = max(abs(net.res_bus.vm_pu.at[b[nd]] - _v(m, p, sc, n, nd)) for nd in m.nd)
    dA = max(abs(math.radians(net.res_bus.va_degree.at[b[nd]])
                 - (m.vTheta[p, sc, n, nd]() - m.vTheta[p, sc, n, ref]())) for nd in m.nd)
    return dV, dA


def validate(m, levels=3):
    """Run all three checks on the first ``levels`` load levels and print a table."""
    print(f'\n{"load level":18} {"dP [MW]":>10} {"dQ [Mvar]":>11} {"loop [rad]":>12} '
          f'{"dV [p.u.]":>12} {"dAngle [rad]":>13}')
    for (p, sc, n) in [k for k in m.psn][:levels]:
        wP, wQ = branch_residual(m, p, sc, n)
        loop   = loop_residual(m, p, sc, n)
        try:
            dV, dA = powerflow_error(m, p, sc, n)
            pf = f'{dV:12.9f} {dA:13.9f}'
        except Exception as e:                      # pandapower absent, or the flow did not converge
            pf = f'{type(e).__name__:>26}'
        print(f'{str(n)[:18]:18} {wP:10.5f} {wQ:11.5f} {loop:12.3e} {pf}')


if __name__ == '__main__':
    import os
    sys.path.insert(0, os.path.abspath('.'))
    from openTEPES.openTEPES import openTEPES_run

    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mTEPES = openTEPES_run(sys.argv[1], sys.argv[2], 'gurobi', 0, 0)
    validate(mTEPES, int(sys.argv[3]) if len(sys.argv) > 3 else 3)
