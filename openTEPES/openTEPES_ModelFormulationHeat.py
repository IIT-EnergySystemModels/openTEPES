"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - September 18, 2026

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
    lin  = defaultdict(set)
    lout = defaultdict(set)
    for ni,nf,cc in mTEPES.ha:
        lin [nf].add((ni,cc))
        lout[ni].add((nf,cc))

    # nodes to CHPs (chp2n)
    chp2n = defaultdict(set)
    for nd,g in mTEPES.n2g:
        if g in mTEPES.chp:
            chp2n[nd].add(g)

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
        if len(chp2n[nd]) + len(lout[nd]) + len(lin[nd]) == 0:
            return Constraint.Skip
        return (sum(OptModel.vTotalOutputHeat[p,sc,n,chp] for chp in chp2n[nd] if (p,chp) in mTEPES.pchp) + OptModel.vHeatNS[p,sc,n,nd] -
                sum(OptModel.vFlowHeat[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pha) + sum(OptModel.vFlowHeat[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.pha)) == mTEPES.pDemandHeat[p,sc,n,nd]
    setattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.nd, rule=eBalanceHeat, doc='Heat load generation balance [GW]'))

    if pIndLogConsole:
        print('eBalanceHeat              ... ', len(getattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}')), ' rows')

    # a candidate pipe carries flow only once it is bought, as on the hydrogen side. vHeatPipeInvest appeared nowhere in this module at all, so the capacity of a
    # candidate heat pipe was free. Existing pipes are not in hc and keep the bounds set in openTEPES_SettingUpVariables
    def eHeatPipeCapacity1(OptModel,n,ni,nf,cc):
        if (p,ni,nf,cc) not in mTEPES.phc:
            return Constraint.Skip
        return OptModel.vFlowHeat[p,sc,n,ni,nf,cc] / mTEPES.pHeatPipeNTCBck[ni,nf,cc] >= - OptModel.vHeatPipeInvest[p,ni,nf,cc]
    setattr(OptModel, f'eHeatPipeCapacity1_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.hc, rule=eHeatPipeCapacity1, doc='maximum heat flow by candidate pipe capacity [p.u.]'))

    if pIndLogConsole:
        print('eHeatPipeCapacity1        ... ', len(getattr(OptModel, f'eHeatPipeCapacity1_{p}_{sc}_{st}')), ' rows')

    def eHeatPipeCapacity2(OptModel,n,ni,nf,cc):
        if (p,ni,nf,cc) not in mTEPES.phc:
            return Constraint.Skip
        return OptModel.vFlowHeat[p,sc,n,ni,nf,cc] / mTEPES.pHeatPipeNTCFrw[ni,nf,cc] <=   OptModel.vHeatPipeInvest[p,ni,nf,cc]
    setattr(OptModel, f'eHeatPipeCapacity2_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.hc, rule=eHeatPipeCapacity2, doc='maximum heat flow by candidate pipe capacity [p.u.]'))

    if pIndLogConsole:
        print('eHeatPipeCapacity2        ... ', len(getattr(OptModel, f'eHeatPipeCapacity2_{p}_{sc}_{st}')), ' rows')

    def eTotalRHeatCost(OptModel,n):
        return OptModel.vTotalRHeatCost[p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pHeatNSCost * sum(OptModel.vHeatNS[p,sc,n,nd] for nd in mTEPES.nd if len(chp2n[nd]) + len(lout[nd]) + len(lin[nd]))
    setattr(OptModel, f'eTotalRHeatCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRHeatCost, doc='system reliability cost [MEUR]'))

    if pIndLogConsole:
        print('eTotalRHeatCost           ... ', len(getattr(OptModel, f'eTotalRHeatCost_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating heat      operation         ... ', round(GeneratingTime), 's')
