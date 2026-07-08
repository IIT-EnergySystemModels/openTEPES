"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 08, 2026
openTEPES.openTEPES_ModelFormulationHeat — heat network operation: power-to-heat conversion, heat balance and heat-not-served cost.
"""
from __future__ import annotations

import time
from collections import defaultdict
from pyomo.environ import Constraint


def NetworkHeatOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Heat      scheduling       constraints ****')

    StartTime = time.time()

    # incoming and outgoing pipelines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.ha:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to CHPs (c2n)
    c2n = defaultdict(list)
    for nd,ch in mTEPES.nd*mTEPES.ch:
        if (nd,ch) in mTEPES.n2g:
            c2n[nd].append(ch)

    # nodes to heat pumps (h2n)
    h2n = defaultdict(list)
    for nd,hp in mTEPES.nd*mTEPES.hp:
        if (nd,hp) in mTEPES.n2g:
            h2n[nd].append(hp)

    # nodes to CHPs (chp2n)
    chp2n = defaultdict(list)
    for nd,chp in mTEPES.nd*mTEPES.chp:
        if (nd,chp) in mTEPES.n2g:
            chp2n[nd].append(chp)

    def eEnergy2Heat(OptModel,n,chp):
        if   (p,chp) in mTEPES.pchp and chp in mTEPES.ch and chp not in mTEPES.bo:
            return OptModel.vTotalOutputHeat[p,sc,n,chp] == OptModel.vTotalOutput   [p,sc,n,chp] / mTEPES.pPower2HeatRatio       [chp]
        elif (p,chp) in mTEPES.pchp and chp in mTEPES.hp:
            return OptModel.vTotalOutputHeat[p,sc,n,chp] == OptModel.vESSTotalCharge[p,sc,n,chp] / mTEPES.pProductionFunctionHeat[chp]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eEnergy2Heat_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.chp, rule=eEnergy2Heat, doc='Energy to heat conversion [GW]'))

    if pIndLogConsole:
        print('eEnergy2Heat              ... ', len(getattr(OptModel, f'eEnergy2Heat_{p}_{sc}_{st}')), ' rows')

    def eBalanceHeat(OptModel,n,nd):
        if sum(1 for ch in chp2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutputHeat[p,sc,n,chp] for chp in chp2n[nd] if (p,chp) in mTEPES.pchp) + OptModel.vHeatNS[p,sc,n,nd] -
                    sum(OptModel.vFlowHeat[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pha) + sum(OptModel.vFlowHeat[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.pha)) == mTEPES.pDemandHeat[p,sc,n,nd]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceHeat, doc='Heat load generation balance [GW]'))

    if pIndLogConsole:
        print('eBalanceHeat              ... ', len(getattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}')), ' rows')

    def eTotalRHeatCost(OptModel,n):
        return OptModel.vTotalRHeatCost[p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pHeatNSCost * sum(OptModel.vHeatNS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
    setattr(OptModel, f'eTotalRHeatCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRHeatCost, doc='system reliability cost [MEUR]'))

    if pIndLogConsole:
        print('eTotalRHeatCost           ... ', len(getattr(OptModel, f'eTotalRHeatCost_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating heat      operation         ... ', round(GeneratingTime), 's')
