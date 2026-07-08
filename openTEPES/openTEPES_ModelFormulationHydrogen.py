"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 10, 2026
openTEPES.openTEPES_ModelFormulationHydrogen — hydrogen network operation: H2 balance and hydrogen-not-served cost.
"""
from __future__ import annotations

import time
from collections import defaultdict
from pyomo.environ import Constraint, Set


def NetworkH2OperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Hydrogen  scheduling       constraints ****')

    StartTime = time.time()

    # incoming and outgoing pipelines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.pa:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to electrolyzers (l2n)
    l2n = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            l2n[nd].append(el)

    # nodes to fuel heater using H2 (b2n)
    b2n = defaultdict(list)
    for nd,hh in mTEPES.nd*mTEPES.hh:
        if (nd,hh) in mTEPES.n2g:
            b2n[nd].append(hh)

    def eBalanceH2(OptModel,n,nd):
        if sum(1 for el in l2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]) == 0:
            return Constraint.Skip
        return (mTEPES.pDuration[p,sc,n]()*sum(OptModel.vESSTotalCharge[p,sc,n,el]/mTEPES.pProductionFunctionH2[el] for el in l2n[nd] if (p,el) in mTEPES.peh) - mTEPES.pDuration[p,sc,n]()*sum(OptModel.vTotalOutputHeat[p,sc,n,hh]*mTEPES.pProductionFunctionH2ToHeat[hh] for hh in b2n[nd] if (p,hh) in mTEPES.phh) + OptModel.vH2NS[p,sc,n,nd] - OptModel.vH2Exc[p,sc,n,nd] -
                sum(OptModel.vFlowH2[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.ppa) + sum(OptModel.vFlowH2[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.ppa)) == mTEPES.pDemandH2[p,sc,n,nd]*mTEPES.pDuration[p,sc,n]()
    setattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceH2, doc='H2 load generation balance [tH2]'))

    if pIndLogConsole:
        print('eBalanceH2                ... ', len(getattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}')), ' rows')

    def eTotalRH2Cost(OptModel,n):
        return OptModel.vTotalRH2Cost[p,sc,n] == sum(mTEPES.pH2NSCost * OptModel.vH2NS[p,sc,n,nd] + mTEPES.pH2ExcCost * OptModel.vH2Exc[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for el in l2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
    setattr(OptModel, f'eTotalRH2Cost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRH2Cost, doc='H2 system reliability cost [MEUR]'))

    if pIndLogConsole:
        print('eTotalRH2Cost             ... ', len(getattr(OptModel, f'eTotalRH2Cost_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating hydrogen  operation         ... ', round(GeneratingTime), 's')


# @profile
