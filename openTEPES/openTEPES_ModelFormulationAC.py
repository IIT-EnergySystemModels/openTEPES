"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_ModelFormulationAC — AC network constraints on the branch flow model.

Two functions, both no-ops when ``IndACPowerFlow`` is 0 and both registered as rows of ``FORMULATION_REGISTRY``:

  * ``NetworkACOperationModelFormulation`` — everything shared by all three AC formulations.
  * ``NetworkACCurrentModelFormulation``   — the one equation that is not shared, ``vCurr = (P^2 + Q^2) / vW``.

Formulation: the branch flow model of Chowdhury, Kamalasadan & Paudyal (IEEE TPWRS 39(1), 2024) as embedded in expansion planning by Alvarez, Lopez,
Olmos & Ramos (SEGAN 39:101413, 2024). Constraint numbers below are theirs.

  (9)      eVoltageDropUp/Lo   vW_j = vW_i - 2(r P + x Q)/S + (r^2+x^2) vCurr, released out of service
  (11)     eBalanceElec        the AC branch of the existing active power balance — SAME NAME, see below
  (12)     eBalanceReact       the reactive counterpart, with a slack so infeasibility is diagnosable
  (16)(17) eAngleEnvUp/Lo      the convex envelope tying the angle difference to the branch flows
  (6a-c)   eShuntQ*            reactive injection from a bus shunt device
  (7)      eCurrentLimit       the thermal limit, gated on service
  --       eFlowElecBck        the far end of the branch, from which the loss follows
  --       eLineLossesAC       vLineLosses defined exactly, so every existing loss report stays correct

Four things here are load-bearing, and each was got wrong once.

**``eBalanceElec`` keeps its name and its ``(n, nd)`` index.** ``collect_duals`` stores every dual as ``str(name) + str(index)``, and ten places across
``OutputResultsEconomic``, ``OutputResultsSummary`` and ``ProblemSolvingSectorDecomposition`` read the literal
``f"eBalanceElec_{p}_{sc}_{st}('{n}', '{nd}')"`` back out for locational marginal prices, generator revenues and the sector-decomposition cut. The rule
bound to the name differs under AC; the constraint's identity does not.

**HVDC lines are in the active balance.** ``mTEPES.laa`` holds AC branches only, and the DC ``eBalanceElec`` is skipped under AC, so building the
balance from ``laa`` alone drops every HVDC link out of the model — it can then carry nothing, so it is never worth building, silently. DC branches
(``mTEPES.lad``) appear here exactly as they do in the DC balance: a controllable flow with the loss factor and no Kirchhoff voltage law.

**The gate is ``vLineCommit``, not ``vNetworkInvest``.** ``vLineCommit`` is fixed to 1 for an existing non-switchable line, tied to ``vNetworkInvest``
by ``eLineStateCand`` for a candidate, and free for a switchable one. Gating on it releases an unbuilt candidate AND a line switched out of service;
gating on the investment variable releases only the first, and line switching then misbehaves silently, because ``eKirchhoff2ndLaw1/2`` — which
carries that release in the DC model — is skipped under AC.

**The angle-to-flow relation is ``|V_i||V_j| sin(theta_ij) = x P + r Q``**, with the sign explicit. Deriving it through the admittance matrix invites
an error: the off-diagonal entry carries the opposite sign to the series admittance. Checked against an exact AC power flow — for a lossless branch it
collapses to ``theta = x P``, matching DC. It holds for the SERIES flow, which is what this model carries; the line charging is lumped at the buses.
The envelope divides that numerator by the voltage product, and the extreme of the quotient sits at the small end of the voltage band when the
numerator is positive and the large end when it is negative, so one divisor cannot serve both signs — hence the split into ``vMPos`` / ``vMNeg``.
With a single divisor the two bounds cross and the model is infeasible for any reverse flow.

The cyclic constraint (15) is deliberately **not** built. Both papers impose it because they eliminate the angles and write the cycle sums on the
flows; with ``vTheta`` explicit the sum round any closed cycle telescopes to zero identically. Measured on both bundled cases, the envelope and the
cyclic equation together move the objective by exactly zero — doc/design/AC_OPF_Prototype_Results.md section 10. The envelope is kept because without
it ``vTheta`` is unconstrained and the reported angles would be meaningless, not because it tightens anything.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict

from pyomo.environ import Constraint, NonNegativeReals, RangeSet, Var

# Segments in the piecewise linearisation of each square term. Ten is where the loss error stops improving materially on the bundled cases while the
# model is still an order of magnitude smaller than at twenty-five: 0.42 MW at L=4, 0.08 at L=10, 0.01 at L=25.
PWL_SEGMENTS = 10


def _smax_pu(mTEPES, la):
    """Largest apparent power the model permits on a branch, in per unit.

    The thermal limit is written on the current as ``vCurr <= (Smax/Vmin)^2``, and the current definition gives ``P^2 + Q^2 <= vW*vCurr``, so the
    apparent power the model actually admits is ``Smax * Vmax / Vmin`` — not ``Smax``. Every big-M and every variable box derived in this module uses
    this value, so that they dominate what the model can reach rather than what a first reading of the rating suggests.
    """
    return mTEPES.pLineSmax[la] / mTEPES.pSBase * mTEPES.pVMaxBus[la[0]] / mTEPES.pVMinBus[la[0]]


def _z(mTEPES, la):
    return math.sqrt(mTEPES.pLineZ2[la])


# An off-nominal transformer is an ideal ratio tau at the sending end followed by the series impedance. The impedance therefore sees |V_i|/tau, not
# |V_i|, and every branch equation that reads the sending-end voltage has to read the transformed one. pLineTapFactor is 1/tau, so the effective
# sending voltage is |V_i| * pLineTapFactor and the effective squared voltage is w_i * pLineTapFactor^2.
#
# Leaving this out solves every transformer as 1:1. It is silent: the model stays feasible and the voltages simply come out wrong. RTS-GMLC_AC ships
# 16 transformers with taps of 1.015 and 1.03, so roughly a 3% error in the voltage the impedance sees, and a matching error in the reactive flow.
def _tap2(mTEPES, la):
    return mTEPES.pLineTapFactor[la] ** 2


def _vlo_from(mTEPES, la):
    """Lowest voltage the series impedance sees at the sending end, tap included."""
    return mTEPES.pVMinBus[la[0]] * mTEPES.pLineTapFactor[la]


def _vhi_from(mTEPES, la):
    """Highest voltage the series impedance sees at the sending end, tap included."""
    return mTEPES.pVMaxBus[la[0]] * mTEPES.pLineTapFactor[la]


def NetworkACOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Add the AC network constraints for one (period, scenario, stage)."""
    if not mTEPES.pIndACPowerFlow():
        return

    print('AC network operation model constraints ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    # --- topology, hoisted once ------------------------------------------------------------------------------------------------------------------
    acOut, acIn = defaultdict(list), defaultdict(list)
    for la in mTEPES.laa:
        if _live(la):
            acOut[la[0]].append(la)
            acIn [la[1]].append(la)

    dcOut, dcIn = defaultdict(list), defaultdict(list)
    for la in mTEPES.lad:
        if _live(la):
            dcOut[la[0]].append(la)
            dcIn [la[1]].append(la)

    g2n, e2n = defaultdict(set), defaultdict(set)
    for nd, g in mTEPES.n2g:
        g2n[nd].add(g)
        if g in mTEPES.eh:
            e2n[nd].add(g)

    # from n2gq, not from n2g filtered by gq: a synchronous condenser has MaximumPower = 0 and so is not in mTEPES.g, hence not in n2g
    q2n = defaultdict(set)
    for nd, gq in mTEPES.n2gq:
        q2n[nd].add(gq)

    sh2nd = defaultdict(list)
    for nd, sh in mTEPES.n2sh:
        sh2nd[nd].append(sh)

    # A shunt conductance draws active power. It is zero in almost every case, so the whole active-shunt block is built only when some device has one.
    pShuntG = any(mTEPES.pBusGshb[sh]() for sh in mTEPES.sh) if mTEPES.sh else False

    # Unfiltered branch incidence, matching what the dual readers in OutputResultsEconomic use to decide a node has a balance.
    ndHasBranch = defaultdict(bool)
    for la in mTEPES.la:
        ndHasBranch[la[0]] = True
        ndHasBranch[la[1]] = True

    # Half the line charging susceptance at each end, the pi model, for branches that exist in this period. A branch whose commitment can fall to zero
    # contributes through the switched term instead: a line out of service charges nothing.
    pFixedCharge, pSwitchedChrg = defaultdict(float), defaultdict(list)
    for la in mTEPES.laa:
        if not _live(la):
            continue
        for nd in (la[0], la[1]):
            # a switchable EXISTING line has a free vLineCommit too, so its charging is switched, not fixed
            if la in mTEPES.lca or mTEPES.pIndBinLineSwitch[la]:
                pSwitchedChrg[nd].append(la)
            else:
                pFixedCharge[nd] += mTEPES.pLineBsh[la]() / 2.0

    # --- (11) active power balance ---------------------------------------------------------------------------------------------------------------
    def eBalanceElecAC(OptModel, n, nd):
        # The demand test is load-bearing. acOut/acIn/dcOut/dcIn are filtered by _live(), so a node whose only connection is a candidate line
        # not yet in its period window has all four empty. Skipping there would delete pDemandElec from the model rather than report it as
        # ENS, and the run would understate served demand with no infeasibility and no message. The DC balance does not have this problem
        # because it builds lout/lin over all of mTEPES.la with no period filter.
        # The test uses the UNFILTERED branch lists. OutputResultsEconomic decides whether a node has a dual to read with
        # `bool(lout[nd]) or bool(lin[nd]) or any generator`, built over all of mTEPES.la with no period filter. Skipping on the _live()-filtered
        # lists would make this constraint absent where the reader still expects it, and the run would die with a KeyError on pDuals after solving
        # successfully. The demand term is kept so a node with no branch at all still reports its load as ENS.
        if not (g2n[nd] or ndHasBranch[nd] or mTEPES.pDemandElec[p,sc,n,nd]()):
            return Constraint.Skip
        return (sum(OptModel.vTotalOutput   [p,sc,n,g ] for g  in g2n[nd] if (p,g ) in mTEPES.pg )
              - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh)
              + OptModel.vENS[p,sc,n,nd]
              # a shunt with a non-zero conductance draws active power; pShuntG is empty for the usual Gshb = 0 case
              + sum(OptModel.vPShunt[p,sc,n,sh] for sh in sh2nd[nd] if pShuntG and (p,sc,n,sh) in mTEPES.psnsh)
              # AC branches: the near end injects vFlowElec, the far end vFlowElecBck, and their sum is the loss
              - sum(OptModel.vFlowElec   [(p,sc,n)+la] for la in acOut[nd])
              - sum(OptModel.vFlowElecBck[(p,sc,n)+la] for la in acIn [nd])
              # DC branches: a controllable link with the loss factor, exactly as the DC balance treats them
              - sum(OptModel.vFlowElec  [(p,sc,n)+la] for la in dcOut[nd])
              + sum(OptModel.vFlowElec  [(p,sc,n)+la] for la in dcIn [nd])
              - sum(OptModel.vLineLosses[(p,sc,n)+la] for la in dcOut[nd] if (p,)+la in mTEPES.pll)
              - sum(OptModel.vLineLosses[(p,sc,n)+la] for la in dcIn [nd] if (p,)+la in mTEPES.pll)
              == mTEPES.pDemandElec[p,sc,n,nd])
    setattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceElecAC, doc='electric load generation balance [GW]'))
    if pIndLogConsole:
        print('eBalanceElec (AC)         ... ', len(getattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}')), ' rows')

    # --- (12) reactive power balance -------------------------------------------------------------------------------------------------------------
    def eBalanceReact(OptModel, n, nd):
        # the demand test matters: a node fed only by an HVDC link has no AC branch and no reactive device, but it still has reactive demand, and
        # skipping here would drop that demand from the model altogether instead of surfacing it as vQNSPos
        if not (q2n[nd] or acOut[nd] or acIn[nd] or sh2nd[nd] or mTEPES.pReactiveDemand[p,sc,n,nd]()):
            return Constraint.Skip
        return (sum(OptModel.vReactiveTotalOutput[p,sc,n,gq] for gq in q2n[nd] if (p,gq) in mTEPES.pgq)
              + sum(OptModel.vQShunt[p,sc,n,sh] for sh in sh2nd[nd] if (p,sc,n,sh) in mTEPES.psnsh)
              + pFixedCharge[nd] * OptModel.vW[p,sc,n,nd] * pSBase
              # A switchable or candidate branch charges only while in service. The exact term would be Bsh/2 * vW * vLineCommit, a product of two
              # variables; the voltage is held at nominal instead, which keeps it linear at the cost of the voltage band's spread — at most about
              # +/-10% of the charging on a 0.95-1.05 band. This is the one place the reactive balance is not exact.
              + sum(mTEPES.pLineBsh[la]() / 2.0 * mTEPES.pVNom ** 2 * pSBase * OptModel.vLineCommit[(p,sc,n)+la] for la in pSwitchedChrg[nd])
              + OptModel.vQNSPos[p,sc,n,nd] - OptModel.vQNSNeg[p,sc,n,nd]
              - sum(OptModel.vFlowReactFrw[(p,sc,n)+la] for la in acOut[nd])
              - sum(OptModel.vFlowReactBck[(p,sc,n)+la] for la in acIn [nd])
              == mTEPES.pReactiveDemand[p,sc,n,nd])
    setattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceReact, doc='reactive load generation balance [Gvar]'))
    if pIndLogConsole:
        print('eBalanceReact             ... ', len(getattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}')), ' rows')

    # --- the far end of the branch, and the loss -------------------------------------------------------------------------------------------------
    # Power arriving at nf is what entered at ni less the series loss, so the power leaving nf into the branch is its negative. Chowdhury et al. write
    # (P_ij - r_ij l_ij) inline and carry no far-end variable; one is kept here so vLineLosses can be defined and every existing loss report stays
    # correct. Declaring it without these equations leaves it free, and the model then reports zero losses.
    def eFlowElecBck(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vFlowElecBck[p,sc,n,ni,nf,cc]
                == -OptModel.vFlowElec[p,sc,n,ni,nf,cc] + mTEPES.pLineR[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase)
    setattr(OptModel, f'eFlowElecBck_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eFlowElecBck, doc='active power leaving nf into the branch [GW]'))

    def eFlowReactBck(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vFlowReactBck[p,sc,n,ni,nf,cc]
                == -OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] + mTEPES.pLineX[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase)
    setattr(OptModel, f'eFlowReactBck_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eFlowReactBck, doc='reactive power leaving nf into the branch [Gvar]'))

    def eLineLossesAC(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)) or (p,ni,nf,cc) not in mTEPES.pll:
            return Constraint.Skip
        # vLineLosses is documented as HALF the branch loss, and the output layer multiplies by two
        return (OptModel.vLineLosses[p,sc,n,ni,nf,cc]
                == 0.5 * (OptModel.vFlowElec[p,sc,n,ni,nf,cc] + OptModel.vFlowElecBck[p,sc,n,ni,nf,cc]))
    setattr(OptModel, f'eLineLossesAC_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eLineLossesAC, doc='half the exact AC branch loss [GW]'))

    # --- (7) the thermal limit, gated on service -------------------------------------------------------------------------------------------------
    # A branch out of service carries no current, and with vCurr driven to zero the current definition — cone or staircase — forces both flows to zero
    # too, because vW is bounded below by a positive number. One constraint therefore gates P, Q and the loss together. vLineCommit is fixed at 1 for
    # a line that is neither switchable nor a candidate, so for those this is a plain thermal limit.
    def eCurrentLimit(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        pIMax = (mTEPES.pLineSmax[ni,nf,cc] / pSBase / _vlo_from(mTEPES, (ni,nf,cc))) ** 2
        return OptModel.vCurr[p,sc,n,ni,nf,cc] <= pIMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc]
    setattr(OptModel, f'eCurrentLimit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentLimit, doc='thermal limit, released out of service [p.u.]'))

    # --- (9) voltage drop ------------------------------------------------------------------------------------------------------------------------
    # The big-M is derived from the three terms of the expression rather than guessed. The flow term dominates and was omitted once, leaving an
    # arbitrary constant as the only thing keeping the relaxation valid.
    def _pDropExpr(n, ni, nf, cc):
        return (OptModel.vW[p,sc,n,nf] - OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))
                + 2.0 * (mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                       + mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                - mTEPES.pLineZ2[ni,nf,cc] * OptModel.vCurr[p,sc,n,ni,nf,cc])

    pDropM = {}
    for la in mTEPES.laa:
        ni, nf, cc = la
        pFlow = 2.0 * _z(mTEPES, la) * _smax_pu(mTEPES, la)                                                    # |2(rP+xQ)|/S, by Cauchy-Schwarz
        pLoss = mTEPES.pLineZ2[la] * (mTEPES.pLineSmax[la] / pSBase / _vlo_from(mTEPES, la)) ** 2
        pDropM[la] = (max((mTEPES.pVMaxBus[nf] ** 2 - _vlo_from(mTEPES, la) ** 2) + pFlow,         0.0),        # largest the expression can be
                      min((mTEPES.pVMinBus[nf] ** 2 - _vhi_from(mTEPES, la) ** 2) - pFlow - pLoss, 0.0))       # and the smallest

    def eVoltageDropUp(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return _pDropExpr(n,ni,nf,cc) <= pDropM[ni,nf,cc][0] * (1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc])
    setattr(OptModel, f'eVoltageDropUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eVoltageDropUp, doc='voltage drop along an AC branch, upper [p.u.]'))

    def eVoltageDropLo(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return _pDropExpr(n,ni,nf,cc) >= pDropM[ni,nf,cc][1] * (1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc])
    setattr(OptModel, f'eVoltageDropLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eVoltageDropLo, doc='voltage drop along an AC branch, lower [p.u.]'))
    if pIndLogConsole:
        print('eVoltageDrop              ... ', 2*len(getattr(OptModel, f'eVoltageDropUp_{p}_{sc}_{st}')), ' rows')

    # --- (16)/(17) the angle envelope ------------------------------------------------------------------------------------------------------------
    def eAngleEnvM(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vMPos[p,sc,n,ni,nf,cc] - OptModel.vMNeg[p,sc,n,ni,nf,cc]
                == (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                  + mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase)
    setattr(OptModel, f'eAngleEnvM_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvM, doc='signed parts of the envelope numerator [p.u.]'))

    # vMPos and vMNeg are only tied to their DIFFERENCE above, and adding the same amount to both relaxes BOTH envelope inequalities, because the two
    # appear with different voltage divisors. That is free slack — on a 0.95-1.05 band it comes to roughly 18% of the implied angle bound per branch,
    # which loosens how tightly the reported angles are tied to the flows. Capping the sum removes it without cutting anything off: the minimal split
    # (vMPos, vMNeg) = (max(M,0), max(-M,0)) always satisfies it, and the envelope is tightest at that split anyway.
    def eAngleEnvMSum(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vMPos[p,sc,n,ni,nf,cc] + OptModel.vMNeg[p,sc,n,ni,nf,cc]
                <= _z(mTEPES, (ni,nf,cc)) * _smax_pu(mTEPES, (ni,nf,cc)))
    setattr(OptModel, f'eAngleEnvMSum_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvMSum, doc='minimal split of the envelope numerator [p.u.]'))

    # Both sides carry the same release, so a branch out of service imposes no angle relation on the two buses it would have joined. Releasing only
    # one side leaves the other binding on an unbuilt candidate, which is a quiet way to force a build.
    def _pRelease(n, la):
        return math.pi * (1 - OptModel.vLineCommit[(p,sc,n)+la])

    def eAngleEnvUp(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        # the polyhedral envelope is derived for a symmetric band, so it takes the wider of the two sides: a wider envelope is still a valid
        # relaxation, while the true asymmetric limits are imposed by eAngleBandUp/Lo below.
        t = max(mTEPES.pMaxAngleDiff[ni,nf,cc], -mTEPES.pMinAngleDiff[ni,nf,cc])
        return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                <= ( OptModel.vMPos[p,sc,n,ni,nf,cc] / (_vlo_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMinBus[nf])
                   - OptModel.vMNeg[p,sc,n,ni,nf,cc] / (_vhi_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMaxBus[nf])) / math.cos(t/2)
                   + math.tan(t/2) - t/2 + _pRelease(n,(ni,nf,cc)))
    setattr(OptModel, f'eAngleEnvUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvUp, doc='upper envelope on the angle difference [rad]'))

    def eAngleEnvLo(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        # the polyhedral envelope is derived for a symmetric band, so it takes the wider of the two sides: a wider envelope is still a valid
        # relaxation, while the true asymmetric limits are imposed by eAngleBandUp/Lo below.
        t = max(mTEPES.pMaxAngleDiff[ni,nf,cc], -mTEPES.pMinAngleDiff[ni,nf,cc])
        return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                >= ( OptModel.vMPos[p,sc,n,ni,nf,cc] / (_vhi_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMaxBus[nf])
                   - OptModel.vMNeg[p,sc,n,ni,nf,cc] / (_vlo_from(mTEPES, (ni,nf,cc)) * mTEPES.pVMinBus[nf])) / math.cos(t/2)
                   - math.tan(t/2) + t/2 - _pRelease(n,(ni,nf,cc)))
    setattr(OptModel, f'eAngleEnvLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleEnvLo, doc='lower envelope on the angle difference [rad]'))

    # Two one-sided constraints rather than one banded one. The release term carries vLineCommit, so a ranged inequality would have a VARIABLE bound
    # on each side, and Pyomo refuses to normalise that: 'Ranged Inequality with a variable lower bound'. Only a case with a candidate or switchable
    # AC branch reaches it, which is why the bundled cases did not show it.
    def eAngleBandUp(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                <= mTEPES.pMaxAngleDiff[ni,nf,cc] + _pRelease(n,(ni,nf,cc)))
    setattr(OptModel, f'eAngleBandUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleBandUp, doc='tightened angle-difference band, upper [rad]'))

    def eAngleBandLo(OptModel, n, ni, nf, cc):
        if not _live((ni,nf,cc)):
            return Constraint.Skip
        return (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]
                >= mTEPES.pMinAngleDiff[ni,nf,cc] - _pRelease(n,(ni,nf,cc)))
    setattr(OptModel, f'eAngleBandLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eAngleBandLo, doc='tightened angle-difference band, lower [rad]'))

    # --- reactive capability ---------------------------------------------------------------------------------------------------------------------
    # A machine that is off supplies nothing, and one that is on supplies at most tan(acos(pf)) times its active output. Without this a unit that is
    # not running still delivers its full rated Mvar for free, which systematically understates how much compensation a system needs. Synchronous
    # condensers are excluded: reactive power at zero active power is their entire purpose, and vSynchInvest governs their availability.
    pTanInd    = math.tan(math.acos(min(max(mTEPES.pInductivePF(),  1e-3), 1.0)))
    pTanCap    = math.tan(math.acos(min(max(mTEPES.pCapacitivePF(), 1e-3), 1.0)))
    pCondenser = set(mTEPES.sq)

    def _pHasOutput(gq):
        return gq not in pCondenser and gq in mTEPES.g and (p, gq) in mTEPES.pg

    def eReactiveCapabilityUp(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq or not _pHasOutput(gq):
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] <=  pTanInd * OptModel.vTotalOutput[p,sc,n,gq]
    setattr(OptModel, f'eReactiveCapabilityUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gq, rule=eReactiveCapabilityUp, doc='lagging power factor limit [Gvar]'))

    def eReactiveCapabilityLo(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq or not _pHasOutput(gq):
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] >= -pTanCap * OptModel.vTotalOutput[p,sc,n,gq]
    setattr(OptModel, f'eReactiveCapabilityLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gq, rule=eReactiveCapabilityLo, doc='leading power factor limit [Gvar]'))

    # --- (6a-c) shunt reactive injection ---------------------------------------------------------------------------------------------------------
    if mTEPES.sh:
        def _pShuntM(sh):
            return abs(mTEPES.pBusBshb[sh]()) * mTEPES.pVMaxBus[mTEPES.sh2n[sh]] ** 2 * pSBase

        def eShuntQExisting(OptModel, n, sh):
            if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she:
                return Constraint.Skip
            return OptModel.vQShunt[p,sc,n,sh] == mTEPES.pBusBshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
        setattr(OptModel, f'eShuntQExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntQExisting, doc='reactive injection of an existing shunt [Gvar]'))

        if mTEPES.shc:
            # A candidate injects Bshb*vW when built and exactly nothing when not: two inequalities to pin it to the physics when built, two to force
            # it to zero when not. The device's own rating is the big-M, so the disjunction is as tight as the device.
            def _cand(rule_body, name, doc):
                def rule(OptModel, n, sh):
                    if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.shc:
                        return Constraint.Skip
                    return rule_body(OptModel, n, sh)
                setattr(OptModel, f'{name}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=rule, doc=doc))

            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    <=  _pShuntM(sh) * (1 - m.vShuntInvest[p,sh])), 'eShuntQCandUp', 'candidate shunt injection when built [Gvar]')
            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    >= -_pShuntM(sh) * (1 - m.vShuntInvest[p,sh])), 'eShuntQCandLo', 'candidate shunt injection when built [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] <=  _pShuntM(sh) * m.vShuntInvest[p,sh], 'eShuntQOffUp', 'an unbuilt shunt injects nothing [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] >= -_pShuntM(sh) * m.vShuntInvest[p,sh], 'eShuntQOffLo', 'an unbuilt shunt injects nothing [Gvar]')

        # the active side of the same device, present only when some shunt has a conductance
        if pShuntG:
            def _pShuntMG(sh):
                return abs(mTEPES.pBusGshb[sh]()) * mTEPES.pVMaxBus[mTEPES.sh2n[sh]] ** 2 * pSBase

            def eShuntPExisting(OptModel, n, sh):
                if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she:
                    return Constraint.Skip
                return OptModel.vPShunt[p,sc,n,sh] == -mTEPES.pBusGshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
            setattr(OptModel, f'eShuntPExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntPExisting, doc='active draw of an existing shunt [GW]'))

            if mTEPES.shc:
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        <=  _pShuntMG(sh) * (1 - m.vShuntInvest[p,sh])), 'eShuntPCandUp', 'candidate shunt draw when built [GW]')
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        >= -_pShuntMG(sh) * (1 - m.vShuntInvest[p,sh])), 'eShuntPCandLo', 'candidate shunt draw when built [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] <=  _pShuntMG(sh) * m.vShuntInvest[p,sh], 'eShuntPOffUp', 'an unbuilt shunt draws nothing [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] >= -_pShuntMG(sh) * m.vShuntInvest[p,sh], 'eShuntPOffLo', 'an unbuilt shunt draws nothing [GW]')

    # --- candidate synchronous condensers --------------------------------------------------------------------------------------------------------
    if mTEPES.sqc:
        def eSynchQOffUp(OptModel, n, sq):
            if (p,sq) not in mTEPES.psqc:
                return Constraint.Skip
            return OptModel.vReactiveTotalOutput[p,sc,n,sq] <= mTEPES.pMaxReactivePower[sq] * OptModel.vSynchInvest[p,sq]
        setattr(OptModel, f'eSynchQOffUp_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sqc, rule=eSynchQOffUp, doc='an unbuilt condenser injects nothing [Gvar]'))

        def eSynchQOffLo(OptModel, n, sq):
            if (p,sq) not in mTEPES.psqc:
                return Constraint.Skip
            return OptModel.vReactiveTotalOutput[p,sc,n,sq] >= mTEPES.pMinReactivePower[sq] * OptModel.vSynchInvest[p,sq]
        setattr(OptModel, f'eSynchQOffLo_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sqc, rule=eSynchQOffLo, doc='an unbuilt condenser absorbs nothing [Gvar]'))

    print('Generating AC network constraints      ... ', round(time.time() - StartTime), 's')


# ------------------------------------------------------------------------------------------------------------------------------------------------
# (13) the branch current: the only equation that differs between the AC formulations
# ------------------------------------------------------------------------------------------------------------------------------------------------

def NetworkACCurrentModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    """Supply ``vCurr = (P^2 + Q^2) / vW`` according to ``IndACModelType``.

      0  SOCP        ``vW_i * vCurr >= P^2 + Q^2``, a rotated second-order cone. The only variant whose objective is a valid bound on the true AC
                     optimum. Inside a MIP the cone is outer-approximated at nodes of the tree, which is what makes it scale worse than the linear
                     form as the horizon grows.
      1  piecewise   The square terms become a staircase of L segments, exact at the breakpoints and above the true square between them, so the
         linear      current is never under-estimated and the model is a RESTRICTION rather than a relaxation — a conservative, higher cost.
      2  exact NLP   The equation as written. Non-convex, so no mixed-integer solver takes it; for the validation pass with the binaries fixed.

    The staircase holds the voltage at nominal, because the exact equation divides by ``vW`` and that division is what makes the cone conic. Its range
    spans ``Smax*Vmax/Vmin``, matching what the other two admit: sizing it on ``Smax`` alone silently gives the piecewise variant a tighter feasible
    set than the formulation it approximates.
    """
    if not mTEPES.pIndACPowerFlow():
        return

    pModelType = mTEPES.pIndACModelType()
    print(f'AC current definition   ({["SOCP", "piecewise linear", "exact NLP"][pModelType]}) ****')
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    def _live(la):
        return (p, la[0], la[1], la[2]) in mTEPES.pla

    if pModelType == 0:
        def eCurrentSOC(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    <= OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentSOC_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentSOC, doc='rotated SOC relaxation of the branch current'))

    elif pModelType == 1:
        pSegments = RangeSet(1, PWL_SEGMENTS)
        setattr(OptModel, f'sACSeg_{p}_{sc}_{st}', pSegments)
        # divided by the tap factor so that PWL_SEGMENTS * pDelta reaches the same |P| the vFlowElec box allows, which carries the tap. Without
        # it a transformer with tap > 1 has a strictly smaller feasible set under IndACModelType 1 than under 0 and 2.
        pDelta = {la: _smax_pu(mTEPES, la) / mTEPES.pLineTapFactor[la] * pSBase / PWL_SEGMENTS for la in mTEPES.laa}

        vSegP = Var(mTEPES.n, mTEPES.laa, pSegments, within=NonNegativeReals, doc='active   power segment of the piecewise square [GW]'  )
        vSegQ = Var(mTEPES.n, mTEPES.laa, pSegments, within=NonNegativeReals, doc='reactive power segment of the piecewise square [Gvar]')
        vAbsP = Var(mTEPES.n, mTEPES.laa,            within=NonNegativeReals, doc='absolute active   power flow [GW]'  )
        vAbsQ = Var(mTEPES.n, mTEPES.laa,            within=NonNegativeReals, doc='absolute reactive power flow [Gvar]')
        for pName, pVar in (('vSegP',vSegP), ('vSegQ',vSegQ), ('vAbsP',vAbsP), ('vAbsQ',vAbsQ)):
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', pVar)
        for n in mTEPES.n:
            for la in mTEPES.laa:
                for k in pSegments:
                    vSegP[n, la, k].setub(pDelta[la])
                    vSegQ[n, la, k].setub(pDelta[la])

        # |P| >= P and |P| >= -P suffices: nothing rewards a larger |P|, because a larger |P| forces a larger vCurr and therefore a larger loss.
        def _abs_rule(pAbs, pFlow, pSign):
            def rule(OptModel, n, ni, nf, cc):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                return pAbs[n,ni,nf,cc] >= pSign * pFlow[p,sc,n,ni,nf,cc]
            return rule
        for pName, pAbs, pFlow, pSign in (('eAbsP1', vAbsP, OptModel.vFlowElec,      1), ('eAbsP2', vAbsP, OptModel.vFlowElec,     -1),
                                          ('eAbsQ1', vAbsQ, OptModel.vFlowReactFrw,  1), ('eAbsQ2', vAbsQ, OptModel.vFlowReactFrw, -1)):
            setattr(OptModel, f'{pName}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=_abs_rule(pAbs, pFlow, pSign), doc='absolute branch flow'))

        def eSegSumP(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return vAbsP[n,ni,nf,cc] == sum(vSegP[n,ni,nf,cc,k] for k in pSegments)
        setattr(OptModel, f'eSegSumP_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eSegSumP, doc='active flow split across the segments'))

        def eSegSumQ(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return vAbsQ[n,ni,nf,cc] == sum(vSegQ[n,ni,nf,cc,k] for k in pSegments)
        setattr(OptModel, f'eSegSumQ_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eSegSumQ, doc='reactive flow split across the segments'))

        def eCurrentPWL(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            # The staircase holds the voltage at nominal: the exact relation is P^2 + Q^2 = w * l * S^2, and this substitutes a constant reference
            # for the variable w. That reference is the TRANSFORMED nominal, (pVNom/tau)^2 — writing it as 1.0 is only correct when pVNom is 1.0 and
            # the branch has no tap, which is true of both bundled cases and of nothing else.
            pWRef = mTEPES.pVNom() ** 2 * _tap2(mTEPES, (ni,nf,cc))
            return (OptModel.vCurr[p,sc,n,ni,nf,cc] * pWRef * pSBase ** 2
                    >= sum((2*k - 1) * pDelta[ni,nf,cc] * (vSegP[n,ni,nf,cc,k] + vSegQ[n,ni,nf,cc,k]) for k in pSegments))
        setattr(OptModel, f'eCurrentPWL_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentPWL, doc='piecewise-linear branch current'))

    else:
        def eCurrentExact(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    == OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentExact_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.laa, rule=eCurrentExact, doc='exact branch current definition'))

    print('Generating AC current definition       ... ', round(time.time() - StartTime), 's')
