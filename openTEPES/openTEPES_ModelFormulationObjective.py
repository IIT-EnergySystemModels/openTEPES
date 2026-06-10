"""
openTEPES.openTEPES_ModelFormulationObjective — total-cost objective and the per-stage operation-cost accumulation constraints.
"""
from __future__ import annotations

import time
import math
from collections import defaultdict
from pyomo.environ import Constraint, Objective, minimize, Set


def TotalObjectiveFunction(OptModel, mTEPES, pIndLogConsole):
    print('Total cost o.f.      model formulation ****')

    StartTime = time.time()

    def eTotalSCost(OptModel):
        return OptModel.vTotalSCost
    OptModel.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalTCost(OptModel):
        return OptModel.vTotalSCost == OptModel.vTotalICost + (sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * (OptModel.vTotalGCost    [p,sc,n] +
                                                                                                                             OptModel.vTotalCCost    [p,sc,n] +
                                                                                                                             OptModel.vTotalECost    [p,sc,n] +
                                                                                                                             OptModel.vTotalNCost    [p,sc,n] +
                                                                                                                             OptModel.vTotalRElecCost[p,sc,n]) for p,sc,n in mTEPES.psn                       ) +
                                                               sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() *  OptModel.vTotalRH2Cost  [p,sc,n]  for p,sc,n in mTEPES.psn if mTEPES.pIndHydrogen) +
                                                               sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() *  OptModel.vTotalRHeatCost[p,sc,n]  for p,sc,n in mTEPES.psn if mTEPES.pIndHeat    ) )
    OptModel.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system cost [MEUR]')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Total fixed and variable costs         ... ', round(GeneratingTime), 's')


# @profile


def GenerationOperationModelFormulationObjFunct(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Generation oper o.f. model formulation ****')

    StartTime = time.time()

    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    def eTotalGCost(OptModel,n):
        return OptModel.vTotalGCost[p,sc,n] == (mTEPES.pLoadLevelDuration[p,sc,n]() * sum(mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput    [p,sc,n,nr]                                              +
                                                                                          mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment     [p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr) +
                                                mTEPES.pLoadLevelWeight  [p,sc,n]() * sum(mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp        [p,sc,n,nr]                                              +
                                                                                          mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown       [p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr) +
                                                mTEPES.pLoadLevelWeight  [p,sc,n]() * sum(mTEPES.pOperReserveCost[       nr] * OptModel.vReserveUp      [p,sc,n,nr]                                              +
                                                                                          mTEPES.pOperReserveCost[       nr] * OptModel.vReserveDown    [p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and mTEPES.pIndOperReserveGen[nr] == 0) +
                                                mTEPES.pLoadLevelWeight  [p,sc,n]() * sum(mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveUp   [p,sc,n,eh]                                              +
                                                                                          mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveDown [p,sc,n,eh] for eh in mTEPES.eh if (p,eh) in mTEPES.peh and mTEPES.pIndOperReserveCon[eh] == 0) +
                                                mTEPES.pLoadLevelDuration[p,sc,n]() * sum(mTEPES.pLinearVarCost  [p,sc,n,bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if (p,bo) in mTEPES.pbo) +
                                                mTEPES.pLoadLevelDuration[p,sc,n]() * sum(mTEPES.pLinearOMCost   [       re] * OptModel.vTotalOutput    [p,sc,n,re] for re in mTEPES.re if (p,re) in mTEPES.pre) )
    setattr(OptModel, f'eTotalGCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    # the small tolerance pEpsilon=1e-5 is added to avoid pumping/charging with curtailment/spillage
    pEpsilon = 1e-5
    def eTotalCCost(OptModel,n):
        return OptModel.vTotalCCost    [p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * sum((mTEPES.pLinearVarCost[p,sc,n,eh]+pEpsilon) * OptModel.vESSTotalCharge[p,sc,n,eh] for eh in mTEPES.eh if (p,eh) in mTEPES.peh and eh not in mTEPES.el)
    setattr(OptModel, f'eTotalCCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,n):
        if sum(mTEPES.pEmissionVarCost[p,sc,n,g] for g in mTEPES.g if (p,g) in mTEPES.pg) == 0.0:
            return Constraint.Skip
        return OptModel.vTotalECost[p,sc,n] == sum(OptModel.vTotalECostArea[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eTotalECost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalEmissionArea(OptModel,n,ar):
        if mTEPES.pEmission[p,ar] == math.inf or sum(mTEPES.pEmissionRate[g] for g in mTEPES.g if g in g2a[ar] and (p,g) in mTEPES.pg) == 0.0:
            return Constraint.Skip
        return OptModel.vTotalEmissionArea[p,sc,n,ar] == (mTEPES.pLoadLevelDuration[p,sc,n]() * 1e-3 * (sum(mTEPES.pEmissionRate[nr] * OptModel.vTotalOutput    [p,sc,n,nr] for nr in mTEPES.nr if nr in g2a[ar] and (p,nr) in mTEPES.pnr)    # 1e-3 to change from tCO2/MWh to MtCO2/GWh
                                                                                                     +  sum(mTEPES.pEmissionRate[bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if bo in g2a[ar] and (p,bo) in mTEPES.pbo)))  # 1e-3 to change from tCO2/MWh to MtCO2/GWh
    setattr(OptModel, f'eTotalEmissionArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalEmissionArea, doc='area total emission [MtCO2 eq]'))

    def eTotalECostArea(OptModel,n,ar):
        if sum(mTEPES.pEmissionVarCost[p,sc,n,g] for g in mTEPES.g if g in g2a[ar] and (p,g) in mTEPES.pg) == 0.0:
            return Constraint.Skip
        return OptModel.vTotalECostArea[p,sc,n,ar] == (mTEPES.pLoadLevelDuration[p,sc,n]() * (sum(mTEPES.pEmissionVarCost[p,sc,n, g] * OptModel.vTotalOutput    [p,sc,n, g] for  g in mTEPES.g  if  g in g2a[ar] and (p, g) in mTEPES.pg )
                                                                                            + sum(mTEPES.pEmissionVarCost[p,sc,n,bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if bo in g2a[ar] and (p,bo) in mTEPES.pbo)))
    setattr(OptModel, f'eTotalECostArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalECostArea, doc='area emission cost [MEUR]'))

    def eTotalRESEnergyArea(OptModel,n,ar):
        if mTEPES.pRESEnergy[p,ar] == 0.0 or st != mTEPES.Last_st:
            return Constraint.Skip
        return OptModel.vTotalRESEnergyArea[p,sc,n,ar] == mTEPES.pLoadLevelDuration[p,sc,n]() * sum(OptModel.vTotalOutput[p,sc,n,re] for re in mTEPES.re if re in g2a[ar] and (p,re) in mTEPES.pre)
    setattr(OptModel, f'eTotalRESEnergyArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalRESEnergyArea, doc='area RES energy [GWh]'))

    def eTotalNCost(OptModel,n):
        if len(mTEPES.ll) == 0:
            return Constraint.Skip
        return OptModel.vTotalNCost[p,sc,n] == pEpsilon * mTEPES.pLoadLevelDuration[p,sc,n]() * sum(OptModel.vLineLosses[p,sc,n,ni,nf,cc] for ni,nf,cc in mTEPES.ll if (p,ni,nf,cc) in mTEPES.pll)
    setattr(OptModel, f'eTotalNCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalNCost, doc='system variable network operation cost [MEUR]'))

    def eTotalRElecCost(OptModel,n):
        return OptModel.vTotalRElecCost[p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * sum(OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd)
    setattr(OptModel, f'eTotalRElecCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRElecCost, doc='elec system reliability cost [MEUR]'))

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Operation cost        o.f.             ... ', round(GeneratingTime), 's')


# @profile
