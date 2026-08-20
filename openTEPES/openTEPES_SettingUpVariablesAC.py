"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_SettingUpVariablesAC — decision variables for the AC optimal power flow.

Called once from ``SettingUpVariables``; a no-op when ``IndACPowerFlow`` is 0.

The formulation is the **branch flow model** of Chowdhury, Kamalasadan & Paudyal (IEEE TPWRS 39(1), 2024) as embedded in expansion planning by
Alvarez, Lopez, Olmos & Ramos (SEGAN 39:101413, 2024). Its variables are

    vW    [nd]  = |V_nd|^2                 squared voltage magnitude at the bus
    vCurr [la]  = |I_la|^2                 squared current magnitude through the branch
    vFlowElec / vFlowElecBck  [la]         active   power entering the branch at each end
    vFlowReactFrw / vFlowReactBck [la]     reactive power entering the branch at each end
    vTheta[nd]                             voltage angle, already declared by SettingUpVariables

Every branch equation is linear in these except the single current definition ``vCurr = (P^2 + Q^2) / vW``, which Phase 4 replaces either with a
second-order cone or with a piecewise linearisation. See doc/design/AC_OPF_Formulation_Choices.md.

Two decisions worth stating:

  * ``vFlowElec`` keeps the meaning it has in the DC model — the active power leaving ``ni`` towards ``nf`` — so the eight places that already read it
    keep working and the output layer is not forked. ``vFlowElecBck`` is the far end; their sum is the branch loss.
  * There is no separate voltage-magnitude variable. ``vW`` is the square, and the square root belongs in the output layer: introducing ``vVoltage``
    with ``vVoltage^2 == vW`` would put a non-convexity back into a formulation built to avoid one.

Bounds come from ``openTEPES_BoundTightening``, not from the raw voltage band, because a tight bound here is what makes the cyclic constraints bind.
"""
from __future__ import annotations

import math
import time

from pyomo.environ import Var, Reals, NonNegativeReals, Binary, UnitInterval


def SettingUpVariablesAC(OptModel, mTEPES):
    """Declare the AC variables on ``OptModel``. Returns the number of variables fixed, to add to ``nFixedVariables``."""
    if not mTEPES.pIndACPowerFlow():
        return 0

    StartTime = time.time()
    nFixedVariables = 0

    # --- bus voltage -----------------------------------------------------------------------------------------------------------------------------
    # The start point is nominal CLAMPED INTO the bus's own band. Bound tightening can move a band clear of nominal — a transformer-fed bus with a tap
    # below 1 gets its upper bound pulled under pVNom^2 — and an unclamped nominal start would then sit outside the variable's own bounds, wasting the
    # warm start exactly where the tightening did the most work.
    def _pW0(OptModel, p, sc, n, nd):
        return min(max(mTEPES.pVNom() ** 2, mTEPES.pVMinBus[nd] ** 2), mTEPES.pVMaxBus[nd] ** 2)

    OptModel.vW = Var(mTEPES.psnnd, within=NonNegativeReals, initialize=_pW0,
                      bounds=lambda OptModel, p, sc, n, nd: (mTEPES.pVMinBus[nd] ** 2, mTEPES.pVMaxBus[nd] ** 2),
                      doc='squared voltage magnitude at the node [p.u.]')

    # The reference bus holds nominal voltage: it is the anchor the bound propagation spreads from, and the slack of any AC power flow the results
    # are checked against.
    for p, sc, n in mTEPES.psn:
        OptModel.vW[p, sc, n, mTEPES.rf.first()].fix(mTEPES.pVNom() ** 2)
        nFixedVariables += 1

    # --- branch flows and current ----------------------------------------------------------------------------------------------------------------
    # The thermal limit belongs on the current, not on the active power: with reactive flow and an off-nominal voltage a branch carries more MW than
    # its MVA rating suggests. The boxes on P and Q are loose enough never to bind on their own; the real limit is vCurr <= (Smax/Vmin)^2.
    OptModel.vFlowElecBck  = Var(mTEPES.psnlaa, within=Reals, doc='active   power flow leaving nf towards ni [GW]'  )
    OptModel.vFlowReactFrw = Var(mTEPES.psnlaa, within=Reals, doc='reactive power flow leaving ni towards nf [Gvar]')
    OptModel.vFlowReactBck = Var(mTEPES.psnlaa, within=Reals, doc='reactive power flow leaving nf towards ni [Gvar]')
    OptModel.vCurr         = Var(mTEPES.psnlaa, within=NonNegativeReals, initialize=0.0, doc='squared current magnitude through the branch [p.u.]')

    for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
        # |I| is capped by the rating at the lowest voltage the impedance sees at the SENDING end, tap included. The apparent power at either end is
        # then |V| * |I| with that end's own highest voltage. Using the sending end's band for the far end boxes the receiving flows about 5% tighter
        # than the physics allows on a 0.95-1.05 band wherever the sending bus is the pinned reference, which can cut off feasible operating points.
        pTapF   = mTEPES.pLineTapFactor[ni,nf,cc]
        pImaxPu = mTEPES.pLineSmax[ni,nf,cc] / mTEPES.pSBase / (mTEPES.pVMinBus[ni] * pTapF)
        pBox    = pImaxPu * mTEPES.pVMaxBus[ni] * mTEPES.pSBase
        pBoxBck = pImaxPu * mTEPES.pVMaxBus[nf] * mTEPES.pSBase
        # vFlowElec is declared by SettingUpVariables with the DC box [-pMaxNTCBck, +pMaxNTCFrw]. Under AC the binding limit is the thermal one on
        # vCurr, and the two ends of a branch must carry the same box, so widen the near end to match the other three.
        OptModel.vFlowElec[p,sc,n,ni,nf,cc].setlb(-pBox)
        OptModel.vFlowElec[p,sc,n,ni,nf,cc].setub( pBox)
        OptModel.vFlowElecBck [p,sc,n,ni,nf,cc].setlb(-pBoxBck)
        OptModel.vFlowElecBck [p,sc,n,ni,nf,cc].setub( pBoxBck)
        OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc].setlb(-pBox)
        OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc].setub( pBox)
        OptModel.vFlowReactBck[p,sc,n,ni,nf,cc].setlb(-pBoxBck)
        OptModel.vFlowReactBck[p,sc,n,ni,nf,cc].setub( pBoxBck)
        # (7) of Chowdhury et al.: the current limit is the rating at the lowest voltage the bus may hold. Using the TIGHTENED per-bus minimum rather
        # than the global VMin matters — the global value makes this limit permissive by (VMax/VMin) in apparent-power terms, which is why every
        # prototype overloaded on replay (doc/design/AC_OPF_Prototype_Results.md section 2).
        # vCurr is per unit, so the rating has to be per unit too: pLineSmax is in GVA and pSBase is the GVA base. Omitting the division is invisible
        # on a case whose base happens to be 1 GVA and wrong by a factor of ten on one whose base is 100 MVA.
        OptModel.vCurr        [p,sc,n,ni,nf,cc].setub(pImaxPu ** 2)

    # --- reactive power injection ----------------------------------------------------------------------------------------------------------------
    # The rated range is only a box. eReactiveCapability in openTEPES_ModelFormulationAC ties the output to the unit's actual state: a generator that
    # is not committed, or is producing nothing, cannot supply reactive power. Without that a unit that is off still delivers its full rated Mvar for
    # free, which systematically understates how much compensation a system needs.
    OptModel.vReactiveTotalOutput = Var(mTEPES.psngq, within=Reals, doc='reactive power output of a reactive-capable unit [Gvar]')
    for p, sc, n, gq in mTEPES.psngq:
        OptModel.vReactiveTotalOutput[p,sc,n,gq].setlb(mTEPES.pMinReactivePower[gq])
        OptModel.vReactiveTotalOutput[p,sc,n,gq].setub(mTEPES.pMaxReactivePower[gq])

    # --- reactive power not served --------------------------------------------------------------------------------------------------------------
    # eBalanceElec carries vENS; eBalanceReact carried nothing, so a node whose reactive demand could not be met made the whole problem infeasible
    # with no diagnostic pointing at the reactive side. Two non-negative parts because reactive imbalance goes both ways: a node can be short of
    # reactive power or unable to absorb what the line charging delivers.
    OptModel.vQNSPos = Var(mTEPES.psnnd, within=NonNegativeReals, initialize=0.0, doc='reactive power not served at the node [Gvar]')
    OptModel.vQNSNeg = Var(mTEPES.psnnd, within=NonNegativeReals, initialize=0.0, doc='reactive power not absorbed at the node [Gvar]')

    # --- the signed parts of the angle-envelope numerator ---------------------------------------------------------------------------------------
    # The envelope substitutes sin(theta_ij) = M / (Vi Vj) with M = (x P + r Q) / pSBase, and then has to bound M / (Vi Vj) over the voltage band. The
    # extreme is at the SMALL end of the band when M is positive and at the LARGE end when M is negative, so a single divisor cannot serve both signs:
    # using Vmin on the upper bound and Vmax on the lower, as this did first, makes the two bounds cross the moment flow runs against the direction the
    # branch happens to be listed in, and the model is infeasible for reverse flow. Splitting M into non-negative parts keeps the bounds linear and
    # valid for either sign. The split is not forced to be the minimal one; any split with vMPos - vMNeg = M is still a valid relaxation, only weaker.
    OptModel.vMPos = Var(mTEPES.psnlaa, within=NonNegativeReals, initialize=0.0, doc='positive part of the angle-envelope numerator [p.u.]')
    OptModel.vMNeg = Var(mTEPES.psnlaa, within=NonNegativeReals, initialize=0.0, doc='negative part of the angle-envelope numerator [p.u.]')
    # |M| = |x*P - r*Q| <= z*|S| by Cauchy-Schwarz, with z = sqrt(r^2+x^2) and |S| reaching Smax*Vmax/Vmin. Using (x+r)*Smax instead is SMALLER than
    # that whenever r << x, which is the normal case, and eAngleEnvM is an equality — so a box derived that way does not make the model conservative,
    # it makes it infeasible. A non-positive reactance would also flip the sign of the bound, so the magnitude is taken.
    for p, sc, n, ni, nf, cc in mTEPES.psnlaa:
        pZ      = math.sqrt(mTEPES.pLineZ2[ni,nf,cc])
        pSmaxPu = mTEPES.pLineSmax[ni,nf,cc] / mTEPES.pSBase * mTEPES.pVMaxBus[ni] / mTEPES.pVMinBus[ni]
        pMBound = abs(pZ * pSmaxPu)
        OptModel.vMPos[p,sc,n,ni,nf,cc].setub(pMBound)
        OptModel.vMNeg[p,sc,n,ni,nf,cc].setub(pMBound)

    # --- synchronous condensers ------------------------------------------------------------------------------------------------------------------
    # A candidate condenser is switched by its own investment decision, for the same reason a candidate shunt is: it never enters mTEPES.gc, because
    # gc is a subset of g and a zero-MW unit is not in g.
    if mTEPES.sqc:
        if mTEPES.pIndBinGenInvest() != 1:
            OptModel.vSynchInvest = Var(mTEPES.psqc, within=UnitInterval, doc='synchronous condenser investment decision exists in a year [0,1]')
        else:
            OptModel.vSynchInvest = Var(mTEPES.psqc, within=Binary,       doc='synchronous condenser investment decision exists in a year {0,1}')
        # the device's own columns, exactly as vShuntInvest and the ordinary generators honour theirs
        for p, sq in mTEPES.psqc:
            if mTEPES.pSynchBinUnitInvest[sq] == 0:
                OptModel.vSynchInvest[p,sq].domain = UnitInterval
            OptModel.vSynchInvest[p,sq].setlb(mTEPES.pSynchLoInvest[sq])
            OptModel.vSynchInvest[p,sq].setub(mTEPES.pSynchUpInvest[sq])

        # Flag value 2 means "no investment at all", and every other investment variable is FIXED to zero for it, not merely relaxed. Without this an
        # operation-only run pins generators and lines to zero and is still free to build condensers and pay for them.
        if mTEPES.pIndBinGenInvest() == 2:
            for p, sq in mTEPES.psqc:
                OptModel.vSynchInvest[p,sq].fix(0)
                nFixedVariables += 1

    # --- shunt devices ---------------------------------------------------------------------------------------------------------------------------
    if mTEPES.sh:
        OptModel.vQShunt = Var(mTEPES.psnsh, within=Reals, doc='reactive power injected by a bus shunt device [Gvar]')
        # Q = Bshb * vW * pSBase, so the reachable range follows from the voltage band at the device's own bus and the sign of the susceptance.
        # A reactor (Bshb < 0) absorbs; a capacitor injects.
        for p, sc, n, sh in mTEPES.psnsh:
            nd  = mTEPES.sh2n[sh]
            pQ1 = mTEPES.pBusBshb[sh]() * mTEPES.pVMinBus[nd] ** 2 * mTEPES.pSBase
            pQ2 = mTEPES.pBusBshb[sh]() * mTEPES.pVMaxBus[nd] ** 2 * mTEPES.pSBase
            # A CANDIDATE device can be off, and off means zero injection, so its range has to contain zero. For a capacitor both endpoints above are
            # strictly positive, so taking them as the bounds would put the lower bound above the zero that eShuntQOff1/2 force when it is not built —
            # and the only way to satisfy both is to build it. That makes the investment decision unavoidable regardless of its cost.
            if sh in mTEPES.shc:
                pQ1, pQ2 = min(0.0, pQ1, pQ2), max(0.0, pQ1, pQ2)
            OptModel.vQShunt[p,sc,n,sh].setlb(min(pQ1, pQ2))
            OptModel.vQShunt[p,sc,n,sh].setub(max(pQ1, pQ2))

        # A shunt with a non-zero conductance also draws ACTIVE power, P_injected = -Gshb * vW * pSBase. Reading Gshb and then never using it leaves
        # that load out of the system entirely. Declared only when some device actually has a conductance, which is the normal case's zero.
        if any(mTEPES.pBusGshb[sh]() for sh in mTEPES.sh):
            OptModel.vPShunt = Var(mTEPES.psnsh, within=Reals, doc='active power injected by a bus shunt device [GW]')
            for p, sc, n, sh in mTEPES.psnsh:
                nd  = mTEPES.sh2n[sh]
                pP1 = -mTEPES.pBusGshb[sh]() * mTEPES.pVMinBus[nd] ** 2 * mTEPES.pSBase
                pP2 = -mTEPES.pBusGshb[sh]() * mTEPES.pVMaxBus[nd] ** 2 * mTEPES.pSBase
                if sh in mTEPES.shc:                       # a candidate can be off, so its range has to contain zero
                    pP1, pP2 = min(0.0, pP1, pP2), max(0.0, pP1, pP2)
                OptModel.vPShunt[p,sc,n,sh].setlb(min(pP1, pP2))
                OptModel.vPShunt[p,sc,n,sh].setub(max(pP1, pP2))

        if mTEPES.shc:
            # A candidate shunt is switched by an investment decision. Existing devices are always in service and get no variable at all rather than
            # one fixed to 1 — one fewer column per device per period.
            if mTEPES.pIndBinNetElecInvest() != 1:
                OptModel.vShuntInvest = Var(mTEPES.pshc, within=UnitInterval, doc='shunt investment decision exists in a year [0,1]')
            else:
                OptModel.vShuntInvest = Var(mTEPES.pshc, within=Binary,       doc='shunt investment decision exists in a year {0,1}')
            for p, sh in mTEPES.pshc:
                if mTEPES.pShuntBinUnitInvest[sh] == 0:
                    OptModel.vShuntInvest[p,sh].domain = UnitInterval
                OptModel.vShuntInvest[p,sh].setlb(mTEPES.pShuntLoInvest[sh])
                OptModel.vShuntInvest[p,sh].setub(mTEPES.pShuntUpInvest[sh])
            # same as the condensers above: flag 2 is "no investment", so fix rather than only relax. The fix comes after the bounds so it overrides
            # a non-zero InvestmentLo.
            if mTEPES.pIndBinNetElecInvest() == 2:
                for p, sh in mTEPES.pshc:
                    OptModel.vShuntInvest[p,sh].fix(0)
                    nFixedVariables += 1

    # --- the AC branch loss bound ----------------------------------------------------------------------------------------------------------------
    # vLineLosses is bounded in SettingUpVariables at half the DC loss FACTOR times the rating. That is the right bound for the linear loss
    # approximation and far too tight for the exact loss. eLineLossesAC sets the same variable to the real half loss, and on a loaded branch that is
    # several times the loss-factor figure: on RTS-GMLC_AC (loss factor 0.01) the DC bound is 0.875 MW on Node_101-Node_103 where the exact half loss
    # reaches 9.33 MW, so it binds at about 30% loading and squeezes the flows with no message. Replace it with the largest half loss the thermal
    # limit itself permits, 0.5 * r * (Smax/Vmin)^2, in GW.
    if mTEPES.pIndBinSingleNode() == 0:
        for p,sc,n,ni,nf,cc in mTEPES.psnlaa:
            if (p,ni,nf,cc) in mTEPES.pll:
                pIMax = (mTEPES.pLineSmax[ni,nf,cc] / mTEPES.pSBase / (mTEPES.pVMinBus[ni] * mTEPES.pLineTapFactor[ni,nf,cc])) ** 2
                OptModel.vLineLosses[p,sc,n,ni,nf,cc].setub(0.5 * mTEPES.pLineR[ni,nf,cc] * pIMax * mTEPES.pSBase)

    print('Setting up AC variables                ... ', round(time.time() - StartTime), 's')
    return nFixedVariables
