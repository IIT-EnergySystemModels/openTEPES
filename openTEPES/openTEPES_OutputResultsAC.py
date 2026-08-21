"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 19, 2026

openTEPES.openTEPES_OutputResultsAC — results the AC optimal power flow adds: voltages, reactive flows, reactive marginals, and the relaxation diagnostic.

The diagnostic is the important one, and it is written first for that reason.

Under ``IndACModelType`` 0 and 1 the branch current enters as an inequality — a second-order cone or a piecewise staircase — so ``vCurr`` is bounded
below but not fixed. Where nothing pushes it down to the boundary the model reports a branch current, and therefore a loss and a loading, that the
flows do not support. Measured on the 9-bus case, seven of twelve branches sat at their thermal limit while carrying almost no flow, and the reported
losses were 74 % too high. Nothing in the solver output says so: the model is optimal, feasible, and wrong about the network.

``oT_Result_ACRelaxationGap`` reports ``vW_i * vCurr - P^2 - Q^2`` per branch and load level, normalised by the branch rating so the numbers are
comparable across a network, together with a per-branch summary. A user reading any other AC result should read this one first. See
doc/design/AC_OPF_Prototype_Results.md section 9.

The voltage magnitude is ``sqrt(vW)`` under every model type, because ``vW`` is the squared magnitude in all three — unlike the LPAC variant that was
considered and dropped, where it would have been an affine surrogate.
"""

import math
import os
import time

import pandas as pd

try:
    from          .openTEPES_OutputResultsCommon import _outdir
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from openTEPES.openTEPES_OutputResultsCommon import _outdir

# A branch whose normalised cone gap exceeds this is flagged in the console summary. It is a reporting threshold, not a model tolerance: 1 % of the
# branch rating squared is well beyond solver noise, which lands around 1e-8.
# A reactive slack below this at every single node and load level is solver residue, not a shortfall worth reporting [Mvar].
QNS_REPORT_THRESHOLD = 1e-3
GAP_REPORT_THRESHOLD = 0.01


# The index is built explicitly from the keys rather than handed the index set directly: pandas infers a MultiIndex from some
# list-likes of tuples and a flat Index of tuples from others, and which one it picks should not decide whether a result file
# can be written.
def _write(sKeys, pValues, pName, pNames, pColumns, pPath, CaseName, pFile):
    if not sKeys:
        return
    pFrame = pd.Series(data=pValues, index=pd.MultiIndex.from_tuples(sKeys, names=pNames)).to_frame(name=pName)
    (pd.pivot_table(pFrame, values=pName, index=['Period', 'Scenario', 'LoadLevel'], columns=pColumns, fill_value=0.0)
       .rename_axis([None] * len(pColumns), axis=1)
       .reset_index().oT.write(f'{pPath}/oT_Result_{pFile}_{CaseName}.csv', index=False, sep=','))


def _pivot_branch(sKeys, pValues, pName, pPath, CaseName, pFile):
    _write(sKeys, pValues, pName, ['Period', 'Scenario', 'LoadLevel', 'InitialNode', 'FinalNode', 'Circuit'],
           ['InitialNode', 'FinalNode', 'Circuit'], pPath, CaseName, pFile)


def _pivot_node(sKeys, pValues, pName, pPath, CaseName, pFile):
    _write(sKeys, pValues, pName, ['Period', 'Scenario', 'LoadLevel', 'Node'], ['Node'], pPath, CaseName, pFile)


def ACRelaxationDiagnostic(DirName, CaseName, OptModel, mTEPES):
    """The conic/piecewise relaxation gap, per branch and summarised.

    Split out of ACNetworkOperationResults so it can sit in a cheap output category of its own: it is two small files, while the
    operation results are eight hourly wide tables. This is the diagnostic that says whether the currents, losses and voltages in
    those tables mean anything, so it should be available in the minimal output mode without dragging the rest along.
    """
    if not mTEPES.pIndACPowerFlow():
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    # Pyomo variable access is costly, so evaluate each index once and reuse.
    pW     = {k: OptModel.vW           [k]() for k in mTEPES.psnnd }
    pPfr   = {k: OptModel.vFlowElec    [k]() for k in mTEPES.psnlaa}
    pQfr   = {k: OptModel.vFlowReactFrw[k]() for k in mTEPES.psnlaa}
    pMode  = mTEPES.pIndACPowerFlow()
    pCurr  = {k: OptModel.vCurr[k]() for k in mTEPES.psnlaa} if pMode == 1 else {}

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # the relaxation diagnostic: everything ACNetworkOperationResults writes depends on this being small
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    pGap = {}
    for k in mTEPES.psnlaa:
        p, sc, n, ni, nf, cc = k
        pNorm = max(mTEPES.pLineSmax[ni,nf,cc] ** 2, 1e-12)
        if pMode == 1:
            pGap[k] = (pW[p,sc,n,ni] * mTEPES.pLineTapFactor[ni,nf,cc] ** 2 * pCurr[k] * pSBase ** 2 - pPfr[k] ** 2 - pQfr[k] ** 2) / pNorm
        elif pMode == 2:
            # the slack in vWre^2 + vWim^2 <= vW_i vW_j, the same quantity the cone relaxes, normalised the same way
            pGap[k] = (pW[p,sc,n,ni] * pW[p,sc,n,nf]
                       - OptModel.vWre[k]() ** 2 - OptModel.vWim[k]() ** 2) * pSBase ** 2 / pNorm
        else:
            pGap[k] = 0.0                                      # rectangular carries the exact products; there is no relaxation to measure

    sBranch = list(mTEPES.psnlaa)
    _pivot_branch(sBranch, [pGap[k] for k in sBranch], 'p.u. of Smax^2', _path, CaseName, 'ACRelaxationGap')

    # per-branch summary, which is what a user actually scans
    pWorst = {}
    for k in mTEPES.psnlaa:
        la = k[3:]
        # seeded from the first value, not from 0.0: a branch whose gap is negative at every load level has the cone VIOLATED beyond
        # tolerance, and seeding at zero would report it as perfectly tight in the summary users are told to read first
        pWorst[la] = pGap[k] if la not in pWorst else max(pWorst[la], pGap[k])
    # Guard the gap report only. AC can be switched on for a case whose links are all DC, and the voltages, angles, currents, reactive flows and shunt
    # injections written below do not depend on there being a cone to measure.
    if pWorst:
        pSummary = pd.Series(pWorst).sort_values(ascending=False)
        pSummary.index.names = ['InitialNode', 'FinalNode', 'Circuit']
        pSummary.to_frame(name='WorstGap [p.u. of Smax^2]').reset_index().oT.write(
            f'{_path}/oT_Result_ACRelaxationGapSummary_{CaseName}.csv', index=False, sep=',')

        pLoose = [la for la, g in pWorst.items() if g > GAP_REPORT_THRESHOLD]
        if pLoose:
            print(f'### WARNING: the AC relaxation is not tight on {len(pLoose)} of {len(pWorst)} branches '
                  f'(worst {max(pWorst.values()):.3f} of Smax^2). On those branches the reported current, loss and loading are')
            print(f'###          not supported by the flows. See oT_Result_ACRelaxationGapSummary_{CaseName}.csv and run the '
                  f'validation pass before using them.')
        else:
            print(f'AC relaxation tight on all {len(pWorst)} branches (worst {max(pWorst.values(), default=0.0):.2e} of Smax^2)')

    print('Writing  AC relaxation diagnostic       ... ', round(time.time() - StartTime), 's')


def ACNetworkOperationResults(DirName, CaseName, OptModel, mTEPES):
    """Voltages, angles, reactive flows, currents, losses and shunt injections. A no-op when IndACPowerFlow is 0."""
    if not mTEPES.pIndACPowerFlow():
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()
    pSBase = mTEPES.pSBase

    pW     = {k: OptModel.vW           [k]() for k in mTEPES.psnnd }
    # vCurr exists only under branch flow; bus injection reports the flows and voltages it does have
    pCurr  = {k: OptModel.vCurr[k]() for k in mTEPES.psnlaa} if mTEPES.pIndACPowerFlow() == 1 else None
    pPfr   = {k: OptModel.vFlowElec    [k]() for k in mTEPES.psnlaa}
    pQfr   = {k: OptModel.vFlowReactFrw[k]() for k in mTEPES.psnlaa}
    pQbck  = {k: OptModel.vFlowReactBck[k]() for k in mTEPES.psnlaa}
    pPbck  = {k: OptModel.vFlowElecBck [k]() for k in mTEPES.psnlaa}
    sBranch = list(mTEPES.psnlaa)

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    sNode = list(mTEPES.psnnd)
    _pivot_node(sNode, [math.sqrt(max(pW[k], 0.0))               for k in sNode], 'p.u.', _path, CaseName, 'NetworkVoltageMagnitude')
    _pivot_node(sNode, [OptModel.vTheta[k]() * 180.0 / math.pi   for k in sNode], 'deg',  _path, CaseName, 'NetworkVoltageAngle')

    # The reactive slack, reported as a signed net value: positive where the node is short of reactive power, negative where it cannot absorb what the
    # line charging delivers. Without this the slack does its job in the solve and leaves no trace anywhere — a case whose reactive demand cannot be
    # met simply solves with a larger reliability cost and nothing says which node or how much. That is the failure it exists to make visible.
    pQNS = [(OptModel.vQNSPos[k]() - OptModel.vQNSNeg[k]()) * 1e3 for k in sNode]
    _pivot_node(sNode, pQNS, 'Mvar', _path, CaseName, 'NetworkReactiveNotServed')
    # Tested per entry, not on the sum. Summing |slack| over every node and every load level accumulates solver residue — about 2e-06 Mvar across
    # ~79k entries on a converged 9n_AC run — so a total-based test fires on essentially every run and prints a shortfall of 0.000 Mvar.
    if pQNS:
        pWorstQ = max(range(len(sNode)), key=lambda i: abs(pQNS[i]))
        if abs(pQNS[pWorstQ]) > QNS_REPORT_THRESHOLD:
            pShort = sum(abs(q) for q in pQNS)
            print(f'### WARNING: the reactive balance used slack at some nodes, worst {pQNS[pWorstQ]:+.3f} Mvar at {sNode[pWorstQ][3]} '
                  f'({pShort:.3f} Mvar summed over all nodes and load levels). See oT_Result_NetworkReactiveNotServed_{CaseName}.csv — the reactive '
                  f'demand there is not being met by the system, it is being met by the slack.')

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # reactive flows, current and the exact loss
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    _pivot_branch(sBranch, [pQfr [k] * 1e3 for k in sBranch], 'Mvar', _path, CaseName, 'NetworkFlowReactiveFrw')
    _pivot_branch(sBranch, [pQbck[k] * 1e3 for k in sBranch], 'Mvar', _path, CaseName, 'NetworkFlowReactiveBck')

    # Losses come straight from the two ends and need no loss factor. They are the same quantity vLineLosses carries, reported here per branch in MW
    # rather than as the half-loss the DC reports use.
    _pivot_branch(sBranch, [(pPfr[k] + pPbck[k]) * 1e3        for k in sBranch], 'MW',   _path, CaseName, 'NetworkLossesAC')
    if pCurr is not None:                                  # branch flow carries |I|^2 directly; bus injection does not
        _pivot_branch(sBranch, [math.sqrt(max(pCurr[k], 0.0)) for k in sBranch], 'p.u.', _path, CaseName, 'NetworkCurrent')

    # Apparent-power loading against the branch rating. This is the number the DC network map cannot produce, because under DC the binding limit is on
    # active power alone.
    pLoading = {}
    for k in mTEPES.psnlaa:
        ni, nf, cc = k[3:]
        pRating = mTEPES.pLineSmax[ni,nf,cc]
        pLoading[k] = 100.0 * math.hypot(pPfr[k], pQfr[k]) / pRating if pRating > 0.0 else 0.0
    _pivot_branch(sBranch, [pLoading[k] for k in sBranch], '%', _path, CaseName, 'NetworkUtilizationAC')

    # ---------------------------------------------------------------------------------------------------------------------------------------------
    # shunt devices
    # ---------------------------------------------------------------------------------------------------------------------------------------------
    if mTEPES.sh:
        sShunt = list(mTEPES.psnsh)
        _write(sShunt, [OptModel.vQShunt[k]() * 1e3 for k in sShunt], 'Mvar',
               ['Period', 'Scenario', 'LoadLevel', 'Shunt'], ['Shunt'], _path, CaseName, 'ShuntReactivePower')

        # the hourly in-service state, for the devices that have one. Q alone is ambiguous: a bank that is open and one that is closed on a bus
        # sitting at zero volts both report zero.
        if mTEPES.shw:
            sSwitch = list(mTEPES.psnshw)
            _write(sSwitch, [OptModel.vShuntSwitch[k]() for k in sSwitch], 'p.u.',
                   ['Period', 'Scenario', 'LoadLevel', 'Shunt'], ['Shunt'], _path, CaseName, 'ShuntCommitment')

    print('Writing  AC network operation results  ... ', round(time.time() - StartTime), 's')


def ACMarginalResults(DirName, CaseName, OptModel, mTEPES):
    """The reactive-power marginal, i.e. the dual of eBalanceReact. A no-op when IndACPowerFlow is 0 or no duals were collected."""
    if not mTEPES.pIndACPowerFlow():
        return
    if not (hasattr(mTEPES, 'pDuals') and mTEPES.pDuals):
        return

    _path = _outdir(DirName, CaseName, mTEPES)
    StartTime = time.time()

    # eBalanceReact is skipped at a node with no reactive unit, no branch and no shunt, so ask only for duals that exist. Keying on the node rather
    # than on position matters: mTEPES.nd is an unordered Set, so iteration order is not stable between runs.
    # The test has to match eBalanceReact, which also builds on a non-zero reactive demand alone — the HVDC-fed node it was written for has no AC
    # branch, no shunt and no reactive unit, and omitting it here drops the marginal for exactly the node the constraint exists to cover.
    pNodeHasBalance = {}
    for nd in mTEPES.nd:
        pHas = (any(nd == la[0] or nd == la[1] for la in mTEPES.laa)
                or any(mTEPES.pReactiveDemand[p,sc,n,nd]() for p,sc,n in mTEPES.psn)
                # a converter model puts a reactive term on an HVDC terminal, so eBalanceReact builds there too
                or (mTEPES.pIndACConverter() and any(nd == la[0] or nd == la[1] for la in mTEPES.lad)))
        if not pHas:
            # n2gq, not n2g filtered by gq: a synchronous condenser is not in mTEPES.g and so not in n2g, which would skip a node whose only reactive
            # device is a condenser and leave its marginal unwritten.
            pHas = any(nd == n2 for n2, sh in mTEPES.n2sh) or any(nd == n2 for n2, gq in mTEPES.n2gq)
        pNodeHasBalance[nd] = pHas

    sKeys, pValues = [], []
    for p, sc, st, n in mTEPES.s2n:
        if (p, sc, n) not in mTEPES.psn:
            continue
        for nd in mTEPES.nd:
            if not pNodeHasBalance[nd]:
                continue
            pKey = f"eBalanceReact_{p}_{sc}_{st}('{n}', '{nd}')"
            if pKey not in mTEPES.pDuals:
                continue
            sKeys.append((p, sc, n, nd))
            pValues.append(mTEPES.pDuals[pKey] / mTEPES.pPeriodProb[p,sc]() / mTEPES.pLoadLevelDuration[p,sc,n]() * 1e3)

    if not sKeys:
        print('Writing  AC marginal results           ...  no reactive duals were collected')
        return

    _pivot_node(sKeys, pValues, 'EUR/Mvarh', _path, CaseName, 'MarginalReactive')

    print('Writing  AC marginal results           ... ', round(time.time() - StartTime), 's')
