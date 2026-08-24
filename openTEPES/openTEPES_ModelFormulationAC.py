"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_ModelFormulationAC — AC network constraints on the branch flow model. No-ops when ``IndACPowerFlow`` is 0.

Formulation: Chowdhury, Kamalasadan & Paudyal (IEEE TPWRS 39(1), 2024), embedded in expansion planning by Alvarez, Lopez, Olmos & Ramos
(SEGAN 39:101413, 2024).

  * ``NetworkACOperationModelFormulation`` — voltage drop, active and reactive balance, angle envelope, thermal limit, shunts, reactive capability,
    HVDC converters. ``eBalanceElec`` keeps its DC name and index: ten places read its dual back by string.
  * ``NetworkACCurrentModelFormulation``   — ``vCurr = (P^2 + Q^2) / vW`` as a cone, a staircase or the exact equation (``IndACModelType``).
  * ``ACRestorationPass``                  — re-solves the network at the exact current and angle equations on ipopt with the plan held fixed
    (``IndACRestore``), so the reported operating point satisfies the AC equations.

The angle relation is ``|V_i||V_j| sin(theta_ij) = x P - r Q``. MINUS; the derivation is at ``eAngleEnvM``. Written as a plus it costs 38 MW of branch
flow error and no self-consistency check can see it — ``prototypes/ac_formulations/validate.py`` can.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict

from pyomo.environ import Constraint, NonNegativeReals, Objective, RangeSet, SolverFactory, Var, sin, sqrt

# Segments in the piecewise linearisation of each square term. Ten is where the loss error stops improving materially on the bundled cases while the
# model is still an order of magnitude smaller than at twenty-five: 0.42 MW at L=4, 0.08 at L=10, 0.01 at L=25.
PWL_SEGMENTS = 10


# Tangent lines used to approximate the converter capability disc. Twelve leaves the bound loose by 1/cos(pi/12), i.e. 3.5%.
CONV_CUTS = 12

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
    """Add the AC network constraints for one (period, scenario, stage).

    The nodal balances, the shunts, the reactive capability and the HVDC converters are shared by every AC formulation and are built here for all of
    them. Only the branch flow relations -- the voltage drop, the far-end flow definitions, the current limit and the angle envelope -- are specific
    to mode 1; bus injection supplies its own in openTEPES_ModelFormulationBIM. Guarding the WHOLE function on mode 1 left modes 2 and 3 with no
    power balance at all, because the DC balance is already skipped whenever AC is on.
    """
    if not mTEPES.pIndACPowerFlow():
        return
    pBFM = mTEPES.pIndACPowerFlow() == 1

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

    # HVDC converter model, if any. pConvTan is tan(acos(pf)): the reactive power a station draws per unit of active power it carries (LCC), or the
    # most it can supply or absorb at its rating (VSC).
    pConvLCC = mTEPES.pIndACConverter() == 1 and bool(mTEPES.lad)
    pConvVSC = mTEPES.pIndACConverter() == 2 and bool(mTEPES.lad)
    pConvTan = math.tan(math.acos(min(max(mTEPES.pConverterPF(), 1e-3), 1.0)))

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

    # The two halves of |P_dc|. Pinning only the difference is NOT conservative: the draw enters the reactive balance with a MINUS, so a node whose
    # charging exceeds its demand gains by inflating both halves, absorbing the surplus for free and hiding it from the results. vDCFlowDir fixes it.
    if pConvLCC:
        def eDCFlowSplit(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return (OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] - OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc]
                    == OptModel.vFlowElec[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eDCFlowSplit_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowSplit, doc='signed parts of the DC link flow [GW]'))

        # Only one half may be non-zero, so pos + neg is exactly |P|. Without this the pair can both be inflated, and because the converter draw enters
        # the reactive balance with a minus, a node with surplus reactive power gains by doing so: the converter becomes a free reactive sink and the
        # surplus never appears in oT_Result_NetworkReactiveNotServed.
        def eDCFlowDirPos(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] <= mTEPES.pLineNTCMax[ni,nf,cc] * OptModel.vDCFlowDir[p,sc,n,ni,nf,cc]
        setattr(OptModel, f'eDCFlowDirPos_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowDirPos, doc='forward part only when the flow is forward [GW]'))

        def eDCFlowDirNeg(OptModel, n, ni, nf, cc):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            return OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc] <= mTEPES.pLineNTCMax[ni,nf,cc] * (1 - OptModel.vDCFlowDir[p,sc,n,ni,nf,cc])
        setattr(OptModel, f'eDCFlowDirNeg_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.lad, rule=eDCFlowDirNeg, doc='reverse part only when the flow is reverse [GW]'))

    # A converter that is not there supplies nothing. vLineCommit is fixed at 1 for a DC link that is neither switchable nor a candidate, so for those
    # this is slack; for a candidate it is what stops the model taking free reactive support from a link it never builds.
    if pConvVSC:
        def _eQConvOff(vVar, pName):
            def rule(OptModel, n, ni, nf, cc, s=+1):
                if not _live((ni,nf,cc)):
                    return Constraint.Skip
                pQMax = pConvTan * mTEPES.pLineNTCMax[ni,nf,cc]
                return (vVar[p,sc,n,ni,nf,cc] <=  pQMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc]) if s > 0 else \
                       (vVar[p,sc,n,ni,nf,cc] >= -pQMax * OptModel.vLineCommit[p,sc,n,ni,nf,cc])
            return rule

        for vVar, pStem in ((OptModel.vQConvFrw, 'eQConvFrw'), (OptModel.vQConvBck, 'eQConvBck')):
            setattr(OptModel, f'{pStem}OffUp_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc, v=vVar: _eQConvOff(v, '')(m, n, ni, nf, cc, +1),
                               doc='an out-of-service converter injects nothing [Gvar]'))
            setattr(OptModel, f'{pStem}OffLo_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc, v=vVar: _eQConvOff(v, '')(m, n, ni, nf, cc, -1),
                               doc='an out-of-service converter absorbs nothing [Gvar]'))

    # --- converter capability: the station rating is on the APPARENT power ------------------------------------------------------------------------
    # Active and reactive power were bounded separately, so a station could sit at P = NTC and Q = tan(acos(pf)) NTC at the same time and deliver
    # |S| = NTC / pf. At the default power factor of 0.85 that is 17.6% more apparent power than the converter has, and 5.3% at 0.95.
    #
    # The limit is a disc, P^2 + Q^2 <= S^2, and it is written as a ring of linear cuts rather than as that disc. Two reasons. A quadratic constraint
    # would put a cone into IndACModelType = 1, whose whole purpose is to stay a MILP that an LP/MIP solver can take, and on a tightly rated link the
    # disc made the barrier stop with "numerical trouble" where the same case solved without it.
    #
    # CONV_CUTS tangent lines circumscribe the disc, so the bound is loose by 1/cos(pi/CONV_CUTS): 3.5% at 12 cuts. That is an approximation, and it
    # is a fifth of the 17.6% it replaces.
    if pConvLCC or pConvVSC:
        def eConvSLimit(OptModel, n, ni, nf, cc, k=0, pSide=+1):
            if not _live((ni,nf,cc)):
                return Constraint.Skip
            pSmax = mTEPES.pLineNTCMax[ni,nf,cc]
            if pConvVSC:
                pQ = OptModel.vQConvFrw[p,sc,n,ni,nf,cc] if pSide > 0 else OptModel.vQConvBck[p,sc,n,ni,nf,cc]
                pAng = 2.0 * math.pi * k / CONV_CUTS
                return (math.cos(pAng) * OptModel.vFlowElec[p,sc,n,ni,nf,cc] + math.sin(pAng) * pQ <= pSmax)
            # An LCC draws tan(acos(pf)) |P|, so P^2 + Q^2 = P^2 (1 + tan^2) and the disc collapses to a linear bound on |P|, exactly and with no
            # cuts. |P| is already split for the reactive draw.
            return (OptModel.vDCFlowPos[p,sc,n,ni,nf,cc] + OptModel.vDCFlowNeg[p,sc,n,ni,nf,cc]
                    <= pSmax * min(max(mTEPES.pConverterPF(), 1e-3), 1.0))

        if pConvLCC:
            setattr(OptModel, f'eConvSLimit_{p}_{sc}_{st}',
                    Constraint(mTEPES.n*mTEPES.lad, rule=lambda m, n, ni, nf, cc: eConvSLimit(m, n, ni, nf, cc),
                               doc='converter apparent power within its rating [GVA]'))
        else:
            for pSide, pTag in ((+1, 'Frw'), (-1, 'Bck')):
                for k in range(CONV_CUTS):
                    setattr(OptModel, f'eConvSLimit{pTag}{k}_{p}_{sc}_{st}',
                            Constraint(mTEPES.n*mTEPES.lad,
                                       rule=lambda m, n, ni, nf, cc, kk=k, t=pSide: eConvSLimit(m, n, ni, nf, cc, kk, t),
                                       doc='converter apparent power within its rating [GVA]'))

    # --- (12) reactive power balance -------------------------------------------------------------------------------------------------------------
    def eBalanceReact(OptModel, n, nd):
        # the demand test matters: a node fed only by an HVDC link has no AC branch and no reactive device, but it still has reactive demand, and
        # skipping here would drop that demand from the model altogether instead of surfacing it as vQNSPos
        # DC terminals count too once a converter model is on: a node whose only connection is an HVDC link still has a converter sitting on it,
        # and skipping here would drop that reactive draw or supply from the model entirely.
        if not (q2n[nd] or acOut[nd] or acIn[nd] or sh2nd[nd] or mTEPES.pReactiveDemand[p,sc,n,nd]()
                or ((pConvLCC or pConvVSC) and (dcOut[nd] or dcIn[nd]))):
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
              # HVDC converters. An LCC station DRAWS reactive power at both terminals, proportional to the active power it transfers; a VSC station
              # supplies or absorbs it within its rating. The two enter with opposite signs, which is exactly why a single loss factor cannot stand in
              # for either of them.
              - (pConvTan * sum(OptModel.vDCFlowPos[(p,sc,n)+la] + OptModel.vDCFlowNeg[(p,sc,n)+la] for la in dcOut[nd] + dcIn[nd]) if pConvLCC else 0.0)
              + (             sum(OptModel.vQConvFrw[(p,sc,n)+la] for la in dcOut[nd])
                            + sum(OptModel.vQConvBck[(p,sc,n)+la] for la in dcIn [nd])                                             if pConvVSC else 0.0)
              == mTEPES.pReactiveDemand[p,sc,n,nd])
    setattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceReact, doc='reactive load generation balance [Gvar]'))
    if pIndLogConsole:
        print('eBalanceReact             ... ', len(getattr(OptModel, f'eBalanceReact_{p}_{sc}_{st}')), ' rows')

    # ONLY the branch flow relations are mode 1. Everything after this block -- the reactive capability limits, the idle-unit gate, the
    # shunt definitions and the condenser investment gates -- is shared by every AC formulation, so it must not sit behind this guard.
    # An earlier version returned here instead of wrapping, which left bus injection with no reactive capability limit at all: generators
    # supplied their full nameplate Mvar untied to any active output, and used eight times the reactive power branch flow did.
    if pBFM:
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
            # MINUS, not plus. With y = (r - jx)/z^2, P = [(v_i^2 - v_i v_j cos th) r + (v_i v_j sin th) x]/z^2 and Q the same with x and -r, so
            # x P - r Q = v_i v_j sin th. Written as a plus it costs 38 MW of branch flow error and closes no network loop, and no self-consistency
            # check can see it: the envelope, the band and the gap all measure the model against its own definition of this relation.
            return (OptModel.vMPos[p,sc,n,ni,nf,cc] - OptModel.vMNeg[p,sc,n,ni,nf,cc]
                    == (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase)
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
        # vTheta is bounded at +/- pi/2, so the difference spans [-pi, pi] and a release of pi alone is not always enough: for a branch whose limits sit
        # on ONE side, say +5 to +30 degrees, eAngleBandLo would still read theta_ij >= 0.087 - pi, which is tighter than the variable range and so keeps
        # coupling two buses joined only by an unbuilt candidate. Adding the branch's own widest limit clears it in every case.
        pBandM = {la: math.pi + max(abs(mTEPES.pMaxAngleDiff[la]), abs(mTEPES.pMinAngleDiff[la])) for la in mTEPES.laa}

        def _pRelease(n, la):
            return pBandM[la] * (1 - OptModel.vLineCommit[(p,sc,n)+la])

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

    # A unit derated to nothing (EFOR = 1.0) has a non-zero NAMEPLATE rating, so it is not a reactive-only device and not in sq; and it has zero
    # available power, so it is not in g either. It therefore escapes both the capability constraints below and the condenser gate, and would deliver
    # its full rated Mvar at every load level for free. It cannot run, so it supplies nothing.
    pIdleReactive = [gq for gq in mTEPES.gq if gq not in pCondenser and gq not in mTEPES.g]

    def eReactiveIdle(OptModel, n, gq):
        if (p,gq) not in mTEPES.pgq:
            return Constraint.Skip
        return OptModel.vReactiveTotalOutput[p,sc,n,gq] == 0.0
    if pIdleReactive:
        setattr(OptModel, f'eReactiveIdle_{p}_{sc}_{st}',
                Constraint(mTEPES.n*pIdleReactive, rule=eReactiveIdle, doc='a unit with no available power supplies no reactive power [Gvar]'))

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

        # Devices split three ways. A fixed existing shunt is wired in and always injects, so it gets a plain equality. A switchable device has an
        # hourly on/off state and a candidate a per-period build decision; both are the SAME disjunction and differ only in which variable plays the
        # state, so they share one set of constraints. A device that is both is switched hourly and may only close in an hour once it has been built.
        pDisj = [sh for sh in mTEPES.sh if sh in mTEPES.shc or sh in mTEPES.shw]

        def _state(m, n, sh):
            return m.vShuntSwitch[p,sc,n,sh] if sh in mTEPES.shw else m.vShuntInvest[p,sh]

        def eShuntQExisting(OptModel, n, sh):
            if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she or sh in mTEPES.shw:
                return Constraint.Skip
            return OptModel.vQShunt[p,sc,n,sh] == mTEPES.pBusBshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
        setattr(OptModel, f'eShuntQExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntQExisting, doc='reactive injection of an existing shunt [Gvar]'))

        if pDisj:
            # A device in service injects Bshb*vW and out of service exactly nothing: two inequalities to pin it to the physics when in, two to force
            # it to zero when out. The device's own rating is the big-M, so the disjunction is as tight as the device.
            def _cand(rule_body, name, doc, pSub=None):
                pOn = pDisj if pSub is None else pSub
                def rule(OptModel, n, sh):
                    if (p,sc,n,sh) not in mTEPES.psnsh or sh not in pOn:
                        return Constraint.Skip
                    return rule_body(OptModel, n, sh)
                setattr(OptModel, f'{name}_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=rule, doc=doc))

            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    <=  _pShuntM(sh) * (1 - _state(m, n, sh))), 'eShuntQCandUp', 'shunt injection when in service [Gvar]')
            _cand(lambda m, n, sh: (m.vQShunt[p,sc,n,sh] - mTEPES.pBusBshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                    >= -_pShuntM(sh) * (1 - _state(m, n, sh))), 'eShuntQCandLo', 'shunt injection when in service [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] <=  _pShuntM(sh) * _state(m, n, sh), 'eShuntQOffUp', 'a shunt out of service injects nothing [Gvar]')
            _cand(lambda m, n, sh: m.vQShunt[p,sc,n,sh] >= -_pShuntM(sh) * _state(m, n, sh), 'eShuntQOffLo', 'a shunt out of service injects nothing [Gvar]')

            # a candidate that is also switchable may only close in an hour if the investment was made
            pBoth = [sh for sh in mTEPES.shc if sh in mTEPES.shw]
            if pBoth:
                _cand(lambda m, n, sh: m.vShuntSwitch[p,sc,n,sh] <= m.vShuntInvest[p,sh], 'eShuntSwitchInvest',
                      'a switchable candidate shunt closes only once built [0,1]', pBoth)

        # Units of one bank are identical, so on their own the states would let branch and bound walk every permutation of the same answer: three
        # units of a four unit bank can be in service in four different ways that cost the same. Requiring a unit to follow the one before it leaves
        # exactly one of those, and turns the states of a bank into the count that are in service.
        if mTEPES.shp:
            def eShuntStepOrder(OptModel, n, sh, sn):
                if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.shw:
                    return Constraint.Skip
                return OptModel.vShuntSwitch[p,sc,n,sn] <= OptModel.vShuntSwitch[p,sc,n,sh]
            setattr(OptModel, f'eShuntStepOrder_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.shp, rule=eShuntStepOrder,
                    doc='a bank unit is in service only if the one before it is [0,1]'))

            # The same for the build decision, which has no hour index. It repeats identically for each scenario and stage; the rows are redundant
            # rather than wrong, and an AC case normally carries one of each.
            def eShuntBuildOrder(OptModel, sh, sn):
                if sh not in mTEPES.shc or (p,sh) not in mTEPES.pshc:
                    return Constraint.Skip
                return OptModel.vShuntInvest[p,sn] <= OptModel.vShuntInvest[p,sh]
            setattr(OptModel, f'eShuntBuildOrder_{p}_{sc}_{st}', Constraint(mTEPES.shp, rule=eShuntBuildOrder,
                    doc='a bank unit is built only if the one before it is [0,1]'))

        # the active side of the same device, present only when some shunt has a conductance
        if pShuntG:
            def _pShuntMG(sh):
                return abs(mTEPES.pBusGshb[sh]()) * mTEPES.pVMaxBus[mTEPES.sh2n[sh]] ** 2 * pSBase

            def eShuntPExisting(OptModel, n, sh):
                if (p,sc,n,sh) not in mTEPES.psnsh or sh not in mTEPES.she or sh in mTEPES.shw:
                    return Constraint.Skip
                return OptModel.vPShunt[p,sc,n,sh] == -mTEPES.pBusGshb[sh] * OptModel.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
            setattr(OptModel, f'eShuntPExisting_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.sh, rule=eShuntPExisting, doc='active draw of an existing shunt [GW]'))

            if pDisj:
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        <=  _pShuntMG(sh) * (1 - _state(m, n, sh))), 'eShuntPCandUp', 'shunt draw when in service [GW]')
                _cand(lambda m, n, sh: (m.vPShunt[p,sc,n,sh] + mTEPES.pBusGshb[sh] * m.vW[p,sc,n,mTEPES.sh2n[sh]] * pSBase
                                        >= -_pShuntMG(sh) * (1 - _state(m, n, sh))), 'eShuntPCandLo', 'shunt draw when in service [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] <=  _pShuntMG(sh) * _state(m, n, sh), 'eShuntPOffUp', 'a shunt out of service draws nothing [GW]')
                _cand(lambda m, n, sh: m.vPShunt[p,sc,n,sh] >= -_pShuntMG(sh) * _state(m, n, sh), 'eShuntPOffLo', 'a shunt out of service draws nothing [GW]')

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
    if mTEPES.pIndACPowerFlow() != 1:
        return

    pModelType = mTEPES.pIndACModelType()

    # Record which blocks carry a relaxed current definition. ACRestorationPass needs this and cannot recover it by pulling constraint names apart,
    # because a period label is free-form and may itself contain an underscore.
    if not hasattr(mTEPES, 'pACCurrentBlocks'):
        mTEPES.pACCurrentBlocks = []
    if (p, sc, st) not in mTEPES.pACCurrentBlocks:
        mTEPES.pACCurrentBlocks.append((p, sc, st))

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


# Decisions held at their relaxed values through the restoration: the point of the pass is to recover the physical operating point behind a plan, not
# to let the plan move. Continuous operation — output, flows, voltages — stays free, because it has to absorb the true losses.
#
# The names are checked against the model at run time and a miss is reported. An earlier version listed 'vMaxCommitment', which is not a variable in
# this codebase at all (the real ones are vMaxCommitmentYearly, vMaxCommitmentConsYearly and vMaxCommitmentHourly), and getattr simply returned None,
# so the entry did nothing and said nothing. A stale name here means the plan quietly moves and the pass silently becomes a re-optimisation.
# Of the list below, only these exist on every model. The rest depend on options the case may not use, so their absence is not a defect.
RESTORE_ALWAYS = ('vCommitment', 'vStartUp', 'vShutDown')

RESTORE_FIXED = ('vCommitment', 'vCommitmentCons', 'vStartUp', 'vShutDown',
                 'vStableState', 'vRampUpState', 'vRampDwState',
                 'vMaxCommitmentYearly', 'vMaxCommitmentConsYearly', 'vMaxCommitmentHourly',
                 'vLineCommit', 'vLineOnState', 'vLineOffState',
                 'vGenerationInvest', 'vGenerationRetire', 'vNetworkInvest', 'vReservoirInvest',
                 'vShuntInvest', 'vSynchInvest', 'vH2PipeInvest', 'vHeatPipeInvest',
                 'vShuntSwitch')


def ACRestorationPass(OptModel, mTEPES, SolverName='ipopt', pIndLogConsole=0):
    """Re-solve a relaxed AC solution at the exact current equality, with the discrete decisions held fixed.

    The cone and the staircase both leave ``vCurr`` free above the value the flows imply. Where the cone is tight that costs nothing — measured on
    9n_AC the relaxed and exact optima agree to four decimal places. Where it is loose it costs a great deal: on a 24 hour RTS-GMLC window the
    relaxed total was 15.37 MEUR against 18.01 MEUR exact, so the relaxation understated the true cost by 14.7%.

    This pass keeps the plan and corrects the physics. Commitment, switching and every investment stay where the relaxed solve put them; the current
    definition becomes the equality; the network re-solves on a non-linear solver. The result is an operating point that satisfies the AC equations,
    and the difference between the two objectives is what the relaxation was hiding.

    Returns a dict of before/after figures, or None when there is nothing to do.
    """
    if mTEPES.pIndACPowerFlow() != 1:                          # it swaps the branch flow current and angle relations
        return None
    if mTEPES.pIndACModelType() == 2:
        print('AC restoration                         ...  skipped, the model already uses the exact current definition')
        return None

    pBlocks = getattr(mTEPES, 'pACCurrentBlocks', [])
    if not pBlocks:
        print('### WARNING: AC restoration found no current-definition blocks to restore; nothing was done.')
        return None

    StartTime = time.time()
    pSBase    = mTEPES.pSBase
    pBefore   = OptModel.vTotalSCost()

    # The stage loop deactivates each block's constraints once it has moved past them, so the whole model has to be live again before re-solving.
    # Only the blocks recorded above are touched: constraints deactivated for other reasons are left alone.
    nWoken = 0
    for p, sc, st in pBlocks:
        pSuffix = f'_{p}_{sc}_{st}'
        for c in OptModel.component_objects(Constraint):
            if c.name.endswith(pSuffix) and not c.active:
                c.activate()
                nWoken += 1

    # Hold the plan, in two passes.
    #
    # First by DOMAIN: ipopt cannot accept a discrete variable at all, so every binary or integer column is fixed whatever it is called. This is the
    # backstop that makes the pass safe against a variable being added or renamed later.
    nFixed = 0
    for vVar in OptModel.component_objects(Var, active=True):
        for idx in vVar:
            vData = vVar[idx]
            if vData.fixed or vData.value is None:
                continue
            if vData.is_binary() or vData.is_integer():
                vData.fix(vData.value)
                nFixed += 1

    # Then by NAME, for the decisions that must not move even when they have been relaxed to a continuous range: a relaxed commitment or investment
    # variable is not discrete, so the sweep above leaves it free, and the pass would re-optimise the plan instead of restoring it.
    # Most of these are declared conditionally -- a case with no hydrogen has no vH2PipeInvest, a case with no switching has no vLineOnState -- so
    # "absent" is normal and only vCommitment is present on every run. Warning about every optional name told the user the plan was free to move on
    # essentially every run, which was false and trained them to ignore the message.
    pMissing = []
    for pName in RESTORE_FIXED:
        vVar = getattr(OptModel, pName, None)
        if vVar is None:
            if pName in RESTORE_ALWAYS:
                pMissing.append(pName)
            continue
        for idx in vVar:
            if vVar[idx].value is not None and not vVar[idx].fixed:
                vVar[idx].fix(vVar[idx].value)
                nFixed += 1
    if pMissing:
        print(f'### WARNING: AC restoration expected to hold {pMissing} but no such variables exist on this model. If they were renamed, the plan is '
              f'free to move and this pass is re-optimising rather than restoring.')

    # Swap the relaxation for the equality, on the relaxed constraint's OWN index set so the two cover exactly the same branches and load levels.
    nRows = 0
    for p, sc, st in pBlocks:
        pRelaxed = None
        for pStem in ('eCurrentSOC', 'eCurrentPWL'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                pRelaxed = c
        if pRelaxed is None:
            continue
        # the staircase carries its own segment machinery, which has to go with it
        for pStem in ('eCurrentSOC', 'eCurrentPWL', 'eSegSumP', 'eSegSumQ'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                c.deactivate()

        pKeys = list(pRelaxed.keys())

        # The angle envelope has to go too, and this is the half that matters most.
        #
        # vTheta is a node potential, so the sum of (theta_i - theta_j) around any cycle is identically zero and a "cycle constraint" on it would say
        # nothing. What is loose is the tie between the angles and the FLOWS: the envelope only brackets it. Recovering each branch's angle from its
        # own flows and summing around the cycles of 9n_AC gave a mismatch of 0.634 degrees, which means no set of bus angles reproduces those flows —
        # the solution was not an AC operating point at all, however tight the cone was. Imposing the relation exactly closes the loops by
        # construction, because the angles are node potentials and now genuinely carry the flows.
        for pStem in ('eAngleEnvUp', 'eAngleEnvLo', 'eAngleEnvM', 'eAngleEnvMSum'):
            c = getattr(OptModel, f'{pStem}_{p}_{sc}_{st}', None)
            if c is not None:
                c.deactivate()

        # An out-of-service branch must be released here exactly as eAngleEnvUp/Lo release it. Without that, a candidate inside its period window gets
        # a bare equality: eCurrentLimit drives its current to zero, hence P = Q = 0, and the equality then reads sin(theta_i - theta_j) = 0 and pins
        # two buses together through a line that was never built. Written as a pair of inequalities because the release carries vLineCommit and Pyomo
        # will not take a ranged inequality with a variable bound.
        # The band is recomputed here rather than borrowed: pBandM is a local of NetworkACOperationModelFormulation and is not in scope in this
        # function. Referencing it across the two was a NameError that only the restoration tests could see.
        pBandM = {la: math.pi + max(abs(mTEPES.pMaxAngleDiff[la]), abs(mTEPES.pMinAngleDiff[la])) for la in mTEPES.laa}

        def _pReleasedBand(OptModel, n, la):
            return pBandM[la] * (1 - OptModel.vLineCommit[(p,sc,n)+la])

        def eAngleRestoredUp(OptModel, n, ni, nf, cc, p=p, sc=sc):
            # |Vi/tau| |Vj| sin(theta_i - theta_j) = (x P - r Q) / S, the exact series relation. MINUS: see the derivation at eAngleEnvM. vW is bounded below by a positive number, so the
            # square roots are safe. eAngleBandUp/Lo stay active: they are valid bounds on the angle and they help the solver.
            return (sqrt(OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))) * sqrt(OptModel.vW[p,sc,n,nf])
                    * sin(OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf])
                    <= (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                      + _pReleasedBand(OptModel, n, (ni,nf,cc)))
        setattr(OptModel, f'eAngleRestoredUp_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eAngleRestoredUp, doc='exact angle-to-flow relation, upper, restoration pass'))

        def eAngleRestoredLo(OptModel, n, ni, nf, cc, p=p, sc=sc):
            return (sqrt(OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc))) * sqrt(OptModel.vW[p,sc,n,nf])
                    * sin(OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf])
                    >= (mTEPES.pLineX[ni,nf,cc] * OptModel.vFlowElec    [p,sc,n,ni,nf,cc]
                      - mTEPES.pLineR[ni,nf,cc] * OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc]) / pSBase
                      - _pReleasedBand(OptModel, n, (ni,nf,cc)))
        setattr(OptModel, f'eAngleRestoredLo_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eAngleRestoredLo, doc='exact angle-to-flow relation, lower, restoration pass'))

        def eCurrentRestored(OptModel, n, ni, nf, cc, p=p, sc=sc):
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] ** 2 + OptModel.vFlowReactFrw[p,sc,n,ni,nf,cc] ** 2
                    == OptModel.vW[p,sc,n,ni] * _tap2(mTEPES, (ni,nf,cc)) * OptModel.vCurr[p,sc,n,ni,nf,cc] * pSBase ** 2)
        setattr(OptModel, f'eCurrentRestored_{p}_{sc}_{st}',
                Constraint(pKeys, rule=eCurrentRestored, doc='exact branch current, restoration pass'))
        nRows += len(pKeys)

    if not nRows:
        print('### WARNING: AC restoration found no relaxed current constraints to replace; nothing was done.')
        return None

    # Exactly one objective may be active for the solve.
    pObjectives = [o for o in OptModel.component_objects(Objective) if o.active]
    if len(pObjectives) != 1:
        for o in pObjectives:
            o.deactivate()
        OptModel.eTotalSCost.activate()

    print(f'AC restoration                         ...  {nRows} branch-hours at the exact equality, {nFixed} decisions held, '
          f'{nWoken} constraints reactivated')

    Solver  = SolverFactory(SolverName)
    Results = Solver.solve(OptModel, tee=bool(pIndLogConsole))
    pStatus = str(Results.solver.termination_condition)

    if pStatus not in ('optimal', 'locallyOptimal', 'feasible'):
        print(f'### WARNING: the AC restoration did not converge ({pStatus}). The relaxed solution is unchanged in the results, and it is a LOWER '
              f'bound on the true cost, not the true cost.')
        return {'status': pStatus, 'before': pBefore, 'after': None, 'seconds': time.time() - StartTime}

    pAfter = OptModel.vTotalSCost()
    pGap   = 100.0 * (pAfter - pBefore) / abs(pAfter) if pAfter else 0.0

    # The duals in mTEPES.pDuals belong to the relaxed solve and describe a solution that no longer exists. Reporting them beside the restored primal
    # values would publish locational prices from one operating point and voltages, flows and costs from another, differing by exactly the amount this
    # pass just moved. Clearing them makes the marginal writers skip: OutputResultsEconomic guards on pHasDuals and ACMarginalResults on key presence,
    # so an absent price is reported as absent rather than as a wrong number.
    if getattr(mTEPES, 'pDuals', None):
        mTEPES.pDuals = {}
        print('AC restoration                         ...  marginal prices dropped: the duals were the relaxed solve\'s and do not describe the '
              'restored operating point. Re-run with IndACRestore = 0 if you need them.')
    print(f'AC restoration                         ...  {pStatus}, total cost {pBefore:.4f} -> {pAfter:.4f} MEUR '
          f'({pGap:+.2f}% the relaxation was understating), {round(time.time() - StartTime)} s')
    return {'status': pStatus, 'before': pBefore, 'after': pAfter, 'gap_percent': pGap, 'rows': nRows,
            'fixed': nFixed, 'seconds': time.time() - StartTime}
