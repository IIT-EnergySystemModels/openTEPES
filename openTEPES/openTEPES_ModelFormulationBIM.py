"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 20, 2026

openTEPES.openTEPES_ModelFormulationBIM — AC network constraints in bus-injection form. Fires for ``IndACPowerFlow`` 2 and 3 only.

The comparator to the branch flow model in ``openTEPES_ModelFormulationAC``. Bose & Low prove the two SOC relaxations give the same BOUND; they say
nothing about conditioning, solve time or behaviour inside branch and bound, which is what this exists to measure.

  * mode 2, W space   ``W_ii = |V_i|^2`` and ``W_ij = V_i conj(V_j)`` carried as ``vW``, ``vWre`` and ``vWim``. The rank constraint is dropped and
                      replaced by the rotated cone ``vWre^2 + vWim^2 <= vW_i vW_j``, which is the standard SOC relaxation.

KNOWN FRAGILITY, mode 2. This formulation is delicate for a barrier solver and the reason is worth stating, because it is not a modelling error.

Expanded, the cone is ``4 Wre^2 + 4 Wim^2 - 4 Wi Wj <= 0``. That quadratic form is INDEFINITE, so the model is convex only if the solver recognises the
rotated cone. Gurobi does, but the recognition is brittle: writing the same constraint as ``... <= (Wi + Wj)^2 + 1e-6`` loses it, and Gurobi then says
"Continuous model is non-convex but QCP duals are requested". openTEPES sets ``QCPDual = 1`` for locational prices, which rules out the NonConvex = 2
fallback, so a model that is mathematically convex becomes unsolvable through an option set for an unrelated reason.

Even when the cone IS recognised, barrier can stop with "numerical trouble": widening the thermal limit by 1.5% was enough to flip a solving model into
a failing one. That cannot be infeasibility -- loosening a constraint cannot remove a feasible point -- and it cannot be unboundedness, since every
variable here is bounded. It is the barrier failing on a feasible bounded convex problem. The likely cause is that the relaxation is EXACT on these
cases, so every one of the cones is active at the optimum and the feasible set has almost no interior for the central path to follow.

Consequences to know before using or comparing this: ``DualReductions = 0`` is set automatically for modes 2 and 3 because without it barrier fails
outright; the angle band that would make the comparison against branch flow fair cannot currently be switched on; and a dedicated conic solver rather
than a general barrier is the obvious next thing to try.
  * mode 3, rectangular ``V = e + jf`` carried as ``vVre`` and ``vVim``, with the exact non-convex products. No relaxation, needs a non-linear solver.

Both reuse ``vFlowElec``, ``vFlowReactFrw`` and the far-end pair, and both leave ``eBalanceElec`` to the shared AC balance, so the nodal balance, the
output layer and the ten string-keyed dual readers are identical across formulations and the comparison isolates the network representation.

Branch model, per the pi equivalent with an off-nominal tap ``tau`` at the sending end (``pLineTapFactor`` is ``1/tau``):

    y = 1/(r + jx),  ys = j b/2,  a = 1/tau
    S_ij = conj(y + ys) a^2 W_ii - conj(y) a W_ij          S_ji = conj(y + ys) W_jj - conj(y) a conj(W_ij)

``IndACCycle`` adds the loop condition ``sum arg(W_ij) = 0`` around each independent cycle. In W space nothing else ties the angle around a loop, so
without it a solution can carry branch flows no set of bus angles reproduces. Under branch flow the angle is an explicit node potential and the same
sum is identically zero, which is why the option is refused there.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict

from pyomo.environ import Constraint, Reals, Var


def _tap(mTEPES, la):
    return mTEPES.pLineTapFactor[la]


def SettingUpVariablesBIM(OptModel, mTEPES):
    """Declare the bus-injection voltage variables. Returns the number of variables fixed."""
    pMode = mTEPES.pIndACPowerFlow()
    if pMode not in (2, 3):
        return 0

    StartTime, nFixed = time.time(), 0

    if pMode == 2:
        # The off-diagonal of W, one entry per branch rather than a full matrix: only pairs joined by a branch appear in any constraint.
        OptModel.vWre = Var(mTEPES.psnlaa, within=Reals, doc='real part of W_ij = V_i conj(V_j) [p.u.]')
        OptModel.vWim = Var(mTEPES.psnlaa, within=Reals, doc='imag part of W_ij = V_i conj(V_j) [p.u.]')
        for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
            # |W_ij| <= |V_i||V_j|, so each part is bounded by the product of the voltage ceilings.
            pBound = mTEPES.pVMaxBus[ni] * mTEPES.pVMaxBus[nf]
            for v in (OptModel.vWre, OptModel.vWim):
                v[p,sc,n,ni,nf,cc].setlb(-pBound)
                v[p,sc,n,ni,nf,cc].setub( pBound)
            # the real part is positive for any sane operating point: it is |V_i||V_j| cos(theta_ij) and the angle stays well inside +/- 90 degrees
            OptModel.vWre[p,sc,n,ni,nf,cc].setlb(0.0)
        # u = (W_i + W_j)/2 and v = (W_i - W_j)/2, so that W_i W_j = u^2 - v^2 and the cone becomes the STANDARD form
        # ||(Wre, Wim, v)|| <= u. See the header: the rotated form is only convex if the solver recognises it, and that recognition is brittle.
        OptModel.vWsum = Var(mTEPES.psnlaa, within=Reals, doc='half sum of the two bus |V|^2 [p.u.]')
        OptModel.vWdif = Var(mTEPES.psnlaa, within=Reals, doc='half difference of the two bus |V|^2 [p.u.]')
        for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
            pHi = (mTEPES.pVMaxBus[ni] ** 2 + mTEPES.pVMaxBus[nf] ** 2) / 2.0
            OptModel.vWsum[p,sc,n,ni,nf,cc].setlb(0.0)  ; OptModel.vWsum[p,sc,n,ni,nf,cc].setub(pHi)
            OptModel.vWdif[p,sc,n,ni,nf,cc].setlb(-pHi) ; OptModel.vWdif[p,sc,n,ni,nf,cc].setub(pHi)
    else:
        OptModel.vVre = Var(mTEPES.psnnd, within=Reals, initialize=1.0, doc='real part of the bus voltage [p.u.]')
        OptModel.vVim = Var(mTEPES.psnnd, within=Reals, initialize=0.0, doc='imag part of the bus voltage [p.u.]')
        for p, sc, n, nd in mTEPES.psnnd:
            OptModel.vVre[p,sc,n,nd].setlb(-mTEPES.pVMaxBus[nd]); OptModel.vVre[p,sc,n,nd].setub(mTEPES.pVMaxBus[nd])
            OptModel.vVim[p,sc,n,nd].setlb(-mTEPES.pVMaxBus[nd]); OptModel.vVim[p,sc,n,nd].setub(mTEPES.pVMaxBus[nd])
        # the reference bus fixes the angle as well as the magnitude, which is what removes the rotational degeneracy
        ref = mTEPES.rf.first()
        for p, sc, n in mTEPES.psn:
            OptModel.vVre[p,sc,n,ref].fix(mTEPES.pVNom())
            OptModel.vVim[p,sc,n,ref].fix(0.0)
            nFixed += 2

    print('Setting up BIM variables               ... ', round(time.time() - StartTime), 's')
    return nFixed


def NetworkBIMOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Bus-injection network constraints for one (period, scenario, stage)."""
    pMode = mTEPES.pIndACPowerFlow()
    if pMode not in (2, 3):
        return

    print(f'BIM network model ({"W space" if pMode == 2 else "rectangular"}) ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    def _y(la):
        pZ2 = mTEPES.pLineZ2[la]
        return mTEPES.pLineR[la] / pZ2, -mTEPES.pLineX[la] / pZ2       # g, b of the series admittance

    # --- voltage magnitude, the link to the shared AC machinery ---------------------------------------------------------------------------------
    # vW is declared by the shared AC block and used by the shunts, the bounds and every writer, so both modes must define it rather than invent a
    # second voltage variable.
    if pMode == 3:
        def eVoltageSquare(OptModel, n, nd):
            return OptModel.vW[p,sc,n,nd] == OptModel.vVre[p,sc,n,nd] ** 2 + OptModel.vVim[p,sc,n,nd] ** 2
        setattr(OptModel, f'eVoltageSquare_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eVoltageSquare, doc='|V|^2 from the rectangular parts'))

    # --- branch flows ---------------------------------------------------------------------------------------------------------------------------
    def _flows(OptModel, n, ni, nf, cc):
        """(P_ij, Q_ij, P_ji, Q_ji) in per unit, from whichever voltage representation is active."""
        g, b   = _y((ni,nf,cc))
        bsh    = mTEPES.pLineBsh[ni,nf,cc]() / 2.0
        a      = _tap(mTEPES, (ni,nf,cc))
        if pMode == 2:
            Wii, Wjj = OptModel.vW[p,sc,n,ni], OptModel.vW[p,sc,n,nf]
            Wre, Wim = OptModel.vWre[p,sc,n,ni,nf,cc], OptModel.vWim[p,sc,n,ni,nf,cc]
        else:
            ei, fi = OptModel.vVre[p,sc,n,ni], OptModel.vVim[p,sc,n,ni]
            ej, fj = OptModel.vVre[p,sc,n,nf], OptModel.vVim[p,sc,n,nf]
            Wii, Wjj = ei*ei + fi*fi, ej*ej + fj*fj
            Wre, Wim = ei*ej + fi*fj, fi*ej - ei*fj
        # SERIES flows only, with the charging term bsh deliberately left OUT.
        #
        # eBalanceReact is shared with branch flow, where vFlowReactFrw carries the series flow and the pi-model charging is added separately as
        # pFixedCharge * vW * pSBase. Including bsh here as well counts the charging TWICE: the branch equation injects it and the balance injects it
        # again, which hands the system free reactive power and drops the objective. On 9n_AC that was most of a 10.5% gap against branch flow.
        Pij =  g * a*a * Wii - a * ( g * Wre + b * Wim)
        Qij = -b * a*a * Wii - a * ( g * Wim - b * Wre)
        Pji =  g * Wjj       - a * ( g * Wre - b * Wim)
        Qji = -b * Wjj       - a * (-g * Wim - b * Wre)
        return Pij, Qij, Pji, Qji

    for pIdx, (pVar, pName) in enumerate((('vFlowElec', 'eBIMFlowP'), ('vFlowReactFrw', 'eBIMFlowQ'),
                                          ('vFlowElecBck', 'eBIMFlowPBck'), ('vFlowReactBck', 'eBIMFlowQBck'))):
        def rule(OptModel, n, ni, nf, cc, k=pIdx, v=pVar):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return getattr(OptModel, v)[p,sc,n,ni,nf,cc] == _flows(OptModel, n, ni, nf, cc)[k] * pSBase
        setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=rule, doc='bus-injection branch flow [GW/Gvar]'))

    # --- the relaxation, and the thermal limit --------------------------------------------------------------------------------------------------
    if pMode == 2:
        # W = V V^H is rank one; dropping the rank and keeping only the 2x2 minor gives the standard SOC relaxation. Equality would be exact.
        # Written in STANDARD cone form, not as Wre^2 + Wim^2 <= W_i W_j. The natural form leaves a negative bilinear term, so the quadratic matrix
        # is indefinite and Gurobi treats the whole model as non-convex: barrier reports "numerical trouble" and only a spatial branch and bound with
        # NonConvex=2 gets an answer, which is not what a convex relaxation is for. The identity below is the usual rotated-to-standard transformation
        # and is recognised as a second-order cone:
        #     Wre^2 + Wim^2 <= W_i W_j    <=>    || (2 Wre, 2 Wim, W_i - W_j) || <= W_i + W_j        for W_i, W_j >= 0
        def eBIMWsum(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return 2.0 * OptModel.vWsum[p,sc,n,ni,nf,cc] == OptModel.vW[p,sc,n,ni] + OptModel.vW[p,sc,n,nf]
        setattr(OptModel, f'eBIMWsum_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMWsum, doc='half sum of the bus voltages squared'))

        def eBIMWdif(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return 2.0 * OptModel.vWdif[p,sc,n,ni,nf,cc] == OptModel.vW[p,sc,n,ni] - OptModel.vW[p,sc,n,nf]
        setattr(OptModel, f'eBIMWdif_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMWdif, doc='half difference of the bus voltages squared'))

        # STANDARD second-order cone: ||(Wre, Wim, v)|| <= u, one negative eigenvalue on a non-negative variable. The equivalent rotated form
        # Wre^2 + Wim^2 <= W_i W_j leaves an indefinite bilinear term whose convexity the solver has to infer.
        def eBIMCone(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vWre[p,sc,n,ni,nf,cc] ** 2 + OptModel.vWim[p,sc,n,ni,nf,cc] ** 2
                    + OptModel.vWdif[p,sc,n,ni,nf,cc] ** 2 <= OptModel.vWsum[p,sc,n,ni,nf,cc] ** 2)
        setattr(OptModel, f'eBIMCone_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMCone, doc='SOC relaxation of the rank-one condition'))

    # Plain Smax, which is NOT what branch flow admits: there the limit is on the current, so apparent power up to Smax Vmax / Vmin gets through. The
    # matched version was tried and is left out, because widening this limit by that 1.5% was on its own enough to turn a model that solved into one
    # where barrier reports numerical trouble. That fragility is worth knowing about and is recorded in the module header; it also means the two
    # formulations do not yet have the same feasible set.
    def eBIMSLimit(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        pSmax = mTEPES.pLineSmax[ni,nf,cc]
        # LINEAR in vLineCommit, not squared. Squaring puts a variable product on the right of a <=, which is non-convex and stops the barrier
        # dead with "numerical trouble" even when the variable is fixed. vLineCommit is 0 or 1, so the two forms agree where it matters.
        # Exactly what branch flow admits, transcribed. There the limit is on the current, vCurr <= (Smax/(Vmin tau))^2, and with
        # P^2 + Q^2 <= vW tau^2 vCurr S^2 that comes to P^2 + Q^2 <= (Smax/Vmin)^2 vW_i: voltage-DEPENDENT, not a flat cap at Smax. Writing it this
        # way keeps the right-hand side linear in vW, so the constraint stays a cone, and gives the two formulations the same feasible set.
        pVmin = mTEPES.pVMinBus[ni] * _tap(mTEPES, (ni,nf,cc))
        return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                <= (pSmax / pVmin) ** 2 * OptModel.vW[p,sc,n,ni] * OptModel.vLineCommit[p,sc,n,ni,nf,cc])
    setattr(OptModel, f'eBIMSLimit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eBIMSLimit, doc='apparent power limit, gated on service [GVA]'))

    # --- angle-difference bounds ----------------------------------------------------------------------------------------------------------------
    # The same band branch flow imposes on vTheta, and in W space it is LINEAR: Wre is |V_i||V_j| cos(theta_ij) and Wim is |V_i||V_j| sin(theta_ij),
    # so tan(theta_ij) = Wim / Wre and a bound on the angle is a bound on that ratio. Without these, bus injection would be missing the tightening
    # that TightenACBounds computes and the comparison would flatter branch flow for a reason that has nothing to do with the representation.
    # The same band branch flow imposes on vTheta. It still defeats the barrier even with the cone in standard form, so the rotated form was NOT the
    # cause -- an earlier version of this comment said it was, on one experiment, and that was wrong.
    if pMode == 2:
        pTanMax = math.tan(math.pi / 2 * 0.999)                 # the band is clamped below pi/2, but keep tan finite whatever arrives

        def _band(pSign, pName):
            def rule(OptModel, n, ni, nf, cc):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                pLim = mTEPES.pMaxAngleDiff[ni,nf,cc] if pSign > 0 else mTEPES.pMinAngleDiff[ni,nf,cc]
                pTan = max(-pTanMax, min(pTanMax, math.tan(pLim)))
                if pSign > 0:
                    return OptModel.vWim[p,sc,n,ni,nf,cc] <= pTan * OptModel.vWre[p,sc,n,ni,nf,cc]
                return     OptModel.vWim[p,sc,n,ni,nf,cc] >= pTan * OptModel.vWre[p,sc,n,ni,nf,cc]
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=rule, doc='angle-difference band in W space'))

        _band(+1, 'eBIMAngleUp')
        _band(-1, 'eBIMAngleLo')

    # --- the loop condition ---------------------------------------------------------------------------------------------------------------------
    # arg(W_ij) is the angle difference, and in W space nothing ties it around a loop. Linearised at the operating point: for the small angles a
    # transmission network runs at, arg(W_ij) is well approximated by vWim / vWre, and the sum of that around a cycle must vanish. This is a
    # LINEAR constraint, so it tightens the relaxation without leaving the convex world.
    if pMode == 2 and mTEPES.pIndACCycle():
        import networkx as nx
        G = nx.Graph()
        for la in mTEPES.laa:
            G.add_edge(la[0], la[1])
        pCycles = nx.cycle_basis(G)
        pEdge = {}
        for la in mTEPES.laa:
            pEdge.setdefault((la[0], la[1]), la)

        def eBIMCycle(OptModel, n, k):
            pCyc, pTerms = pCycles[k], []
            for a, b in zip(pCyc, pCyc[1:] + pCyc[:1]):
                if (a, b) in pEdge and _live(pEdge[(a, b)]):
                    la = pEdge[(a, b)]
                    pTerms.append(  OptModel.vWim[(p,sc,n)+la] / mTEPES.pVNom() ** 2)
                elif (b, a) in pEdge and _live(pEdge[(b, a)]):
                    la = pEdge[(b, a)]
                    pTerms.append(- OptModel.vWim[(p,sc,n)+la] / mTEPES.pVNom() ** 2)
            if not pTerms:
                return Constraint.Skip
            return sum(pTerms) == 0.0
        setattr(OptModel, f'eBIMCycle_{p}_{sc}_{st}',
                Constraint(mTEPES.n, range(len(pCycles)), rule=eBIMCycle, doc='loop condition around an independent cycle [rad]'))
        if pIndLogConsole:
            print(f'eBIMCycle                 ...  {len(pCycles)} cycles')

    print('Generating BIM network constraints     ... ', round(time.time() - StartTime), 's')
