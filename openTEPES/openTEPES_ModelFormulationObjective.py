"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - August 01, 2026

openTEPES.openTEPES_ModelFormulationObjective — total-cost objective and the per-stage operation-cost accumulation constraints.
"""
from __future__ import annotations

import time
import math
from collections import defaultdict
from pyomo.environ import Constraint, Objective, minimize


def TotalObjectiveFunction(OptModel, mTEPES, pIndLogConsole):
    print('Total cost o.f.      model formulation ****')

    StartTime = time.time()

    def eTotalSCost(OptModel):
        return OptModel.vTotalSCost
    OptModel.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    pScenFactor = {(p,sc): mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() for p,sc in mTEPES.ps}

    def eTotalTCost(OptModel):
        vTotalTCost = OptModel.vTotalICost + sum(pScenFactor[p,sc] * (OptModel.vTotalGCost    [p,sc,n] +
                                                                      OptModel.vTotalCCost    [p,sc,n] +
                                                                      OptModel.vTotalECost    [p,sc,n] +
                                                                      OptModel.vTotalNCost    [p,sc,n] +
                                                                      OptModel.vTotalRElecCost[p,sc,n]) for p,sc,n in mTEPES.psn)
        if mTEPES.pIndHydrogen():
            vTotalTCost += sum(pScenFactor[p,sc] * OptModel.vTotalRH2Cost  [p,sc,n] for p,sc,n in mTEPES.psn)
        if mTEPES.pIndHeat():
            vTotalTCost += sum(pScenFactor[p,sc] * OptModel.vTotalRHeatCost[p,sc,n] for p,sc,n in mTEPES.psn)
        return OptModel.vTotalSCost == vTotalTCost
    OptModel.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system cost [MEUR]')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Total fixed and variable costs         ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationObjFunct(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Generation oper o.f. model formulation ****')

    StartTime = time.time()

    # the small tolerance pEpsilonCharge=1e-5 is added to avoid pumping/charging with curtailment/spillage
    pEpsilonCharge = 1e-5
    # the small tolerance pEpsilonLosses=1e-5 prices the ohmic losses so that the solver does not leave them slack
    pEpsilonLosses = 1e-5

    g2a = defaultdict(set)
    for ar,g in mTEPES.a2g:
        g2a[ar].add(g)

    nr2a = {ar: [nr for nr in mTEPES.nr if nr in g2a[ar] and (p,nr) in mTEPES.pnr] for ar in mTEPES.ar}
    bo2a = {ar: [bo for bo in mTEPES.bo if bo in g2a[ar] and (p,bo) in mTEPES.pbo] for ar in mTEPES.ar}

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

    def eTotalCCost(OptModel,n):
        return OptModel.vTotalCCost    [p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * sum((mTEPES.pLinearVarCost[p,sc,n,eh]+pEpsilonCharge) * OptModel.vESSTotalCharge[p,sc,n,eh] for eh in mTEPES.eh if (p,eh) in mTEPES.peh and eh not in mTEPES.el)
    setattr(OptModel, f'eTotalCCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,n):
        if not any(mTEPES.pEmissionVarCost[p,sc,n,g] for g in mTEPES.g if (p,g) in mTEPES.pg):
            return Constraint.Skip
        return OptModel.vTotalECost[p,sc,n] == sum(OptModel.vTotalECostArea[p,sc,n,ar] for ar in mTEPES.ar)
    setattr(OptModel, f'eTotalECost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    pIndEmissionArea = {ar: mTEPES.pEmission[p,ar] != math.inf and any(mTEPES.pEmissionRate[g] for g in g2a[ar] if (p,g) in mTEPES.pg) for ar in mTEPES.ar}

    def eTotalEmissionArea(OptModel,n,ar):
        if not pIndEmissionArea[ar]:
            return Constraint.Skip
        return OptModel.vTotalEmissionArea[p,sc,n,ar] == (mTEPES.pLoadLevelDuration[p,sc,n]() * 1e-3 * (sum(mTEPES.pEmissionRate[g ] * OptModel.vTotalOutput    [p,sc,n,g ] for g  in g2a [ar] if g not in mTEPES.bo)    # 1e-3 to convert from tCO2/MWh to MtCO2/GWh
                                                                                                     +  sum(mTEPES.pEmissionRate[bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in bo2a[ar]                      )))  # 1e-3 to convert from tCO2/MWh to MtCO2/GWh
    setattr(OptModel, f'eTotalEmissionArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalEmissionArea, doc='area total emission [MtCO2 eq]'))

    def eTotalECostArea(OptModel,n,ar):
        if not any(mTEPES.pEmissionVarCost[p,sc,n,g] for g in g2a[ar] if (p,g) in mTEPES.pg):
            return Constraint.Skip
        return OptModel.vTotalECostArea[p,sc,n,ar] == (mTEPES.pLoadLevelDuration[p,sc,n]() * (sum(mTEPES.pEmissionVarCost[p,sc,n,nr] * OptModel.vTotalOutput    [p,sc,n,nr] for nr in nr2a[ar])
                                                                                            + sum(mTEPES.pEmissionVarCost[p,sc,n,bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in bo2a[ar])))
    setattr(OptModel, f'eTotalECostArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalECostArea, doc='area emission cost [MEUR]'))

    def eTotalRESEnergyArea(OptModel,n,ar):
        if mTEPES.pRESEnergy[p,ar]() == 0.0 or st != mTEPES.Last_st:
            return Constraint.Skip
        return OptModel.vTotalRESEnergyArea[p,sc,n,ar] == mTEPES.pLoadLevelDuration[p,sc,n]() * sum(OptModel.vTotalOutput[p,sc,n,re] for re in mTEPES.re if re in g2a[ar] and (p,re) in mTEPES.pre)
    setattr(OptModel, f'eTotalRESEnergyArea_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ar, rule=eTotalRESEnergyArea, doc='area RES energy [GWh]'))

    def eTotalNCost(OptModel,n):
        if len(mTEPES.ll) == 0:
            return Constraint.Skip
        return OptModel.vTotalNCost[p,sc,n] == pEpsilonLosses * mTEPES.pLoadLevelDuration[p,sc,n]() * sum(OptModel.vLineLosses[p,sc,n,ni,nf,cc] for ni,nf,cc in mTEPES.ll if (p,ni,nf,cc) in mTEPES.pll)
    setattr(OptModel, f'eTotalNCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalNCost, doc='system variable network operation cost [MEUR]'))

    def eTotalRElecCost(OptModel,n):
        return OptModel.vTotalRElecCost[p,sc,n] == mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * sum(OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd)
    setattr(OptModel, f'eTotalRElecCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRElecCost, doc='elec system reliability cost [MEUR]'))

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Operation cost        o.f.             ... ', round(GeneratingTime), 's')
