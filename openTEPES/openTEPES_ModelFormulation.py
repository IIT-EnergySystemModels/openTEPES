"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - July 08, 2025
"""

import time
import math
import networkx as nx
import pandas   as pd
from   collections   import defaultdict
from   pyomo.environ import Constraint, Objective, minimize, Set, RangeSet, Param


def TotalObjectiveFunction(OptModel, mTEPES, pIndLogConsole):
    print('Total cost o.f.      model formulation ****')

    StartTime = time.time()

    def eTotalSCost(OptModel):
        return OptModel.vTotalSCost
    OptModel.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalTCost(OptModel):
        return OptModel.vTotalSCost == OptModel.vTotalICost + sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc]() * (OptModel.vTotalGCost[p,sc,n] + OptModel.vTotalCCost[p,sc,n] + OptModel.vTotalECost[p,sc,n] + OptModel.vTotalRCost[p,sc,n]) for p,sc,n in mTEPES.psn)
    OptModel.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system cost [MEUR]')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Total fixed and variable costs         ... ', round(GeneratingTime), 's')


def InvestmentModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment           model formulation ****')

    StartTime = time.time()

    def eTotalICost(OptModel):
        if len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc):
            return OptModel.vTotalICost == sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFCost[p] for p in mTEPES.p)
        else:
            return Constraint.Skip
    OptModel.eTotalICost = Constraint(rule=eTotalICost, doc='system fixed    cost [MEUR]')

    def eTotalFCost(OptModel,p):
        if   len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc)                                                    and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) +                                                                                                                 sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc)                  + len(mTEPES.pc)                  and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) +                                                                                                                 sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) + sum(mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn)                                   and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) +                                                                                                                 sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) +                                                                                                                                       sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn if (p,rc) in mTEPES.prc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc)                  and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) +                                                                                                                 sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) + sum(mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc) + sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn if (p,rc) in mTEPES.prc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc)                                   + len(mTEPES.hc) and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) + sum(mTEPES.pGenInvestCost[bc] * OptModel.vGenerationInvest[p,bc] for bc in mTEPES.bc if (p,bc) in mTEPES.pbc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc)                                                                                                                                                                                                                                                      + sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc)                  + len(mTEPES.pc) + len(mTEPES.hc) and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) + sum(mTEPES.pGenInvestCost[bc] * OptModel.vGenerationInvest[p,bc] for bc in mTEPES.bc if (p,bc) in mTEPES.pbc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) + sum(mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc)                                                                                                                + sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn)                  + len(mTEPES.hc) and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) + sum(mTEPES.pGenInvestCost[bc] * OptModel.vGenerationInvest[p,bc] for bc in mTEPES.bc if (p,bc) in mTEPES.pbc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) +                                                                                                                                       sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn if (p,rc) in mTEPES.prc) + sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc)
        elif len(mTEPES.gc) + len(mTEPES.bc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc) + len(mTEPES.hc) and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc if (p,gc) in mTEPES.pgc) + sum(mTEPES.pGenInvestCost[bc] * OptModel.vGenerationInvest[p,bc] for bc in mTEPES.bc if (p,bc) in mTEPES.pbc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd if (p,gd) in mTEPES.pgd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) + sum(mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc) + sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn if (p,rc) in mTEPES.prc) + sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc)
        else:
            return Constraint.Skip
    OptModel.eTotalFCost = Constraint(mTEPES.p, rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    def eConsecutiveGenInvest(OptModel,p,gc):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),gc) in mTEPES.pgc:
            return OptModel.vGenerationInvest    [mTEPES.p.prev(p,1),gc      ] + OptModel.vGenerationInvPer    [p,gc      ] == OptModel.vGenerationInvest    [p,gc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenInvest = Constraint(mTEPES.pgc, rule=eConsecutiveGenInvest, doc='generation investment in consecutive periods')

    def eConsecutiveGenRetire(OptModel,p,gd):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),gd) in mTEPES.gd:
            return OptModel.vGenerationRetire    [mTEPES.p.prev(p,1),gd      ] + OptModel.vGenerationRetPer    [p,gd      ] == OptModel.vGenerationRetire    [p,gd      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenRetire = Constraint(mTEPES.pgd, rule=eConsecutiveGenRetire, doc='generation retirement in consecutive periods')

    def eConsecutiveRsrInvest(OptModel,p,rc):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),rc) in mTEPES.prc:
            return OptModel.vReservoirInvest     [mTEPES.p.prev(p,1),rc      ] + OptModel.vReservoirInvPer     [p,rc      ] == OptModel.vReservoirInvest     [p,rc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveRsrInvest = Constraint(mTEPES.prc, rule=eConsecutiveRsrInvest, doc='reservoir investment in consecutive periods')

    def eConsecutiveNetInvest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),ni,nf,cc) in mTEPES.plc:
            return OptModel.vNetworkInvest       [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vNetworkInvPer       [p,ni,nf,cc] == OptModel.vNetworkInvest       [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNetInvest = Constraint(mTEPES.plc, rule=eConsecutiveNetInvest, doc='electric network investment in consecutive periods')

    def eConsecutiveNetH2Invest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),ni,nf,cc) in mTEPES.ppc:
            return OptModel.vH2PipeInvest        [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vH2PipeInvPer        [p,ni,nf,cc] == OptModel.vH2PipeInvest        [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNetH2Invest = Constraint(mTEPES.ppc, rule=eConsecutiveNetH2Invest, doc='H2 pipe network investment in consecutive periods')

    def eConsecutiveNetHeatInvest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first() and (mTEPES.p.prev(p,1),ni,nf,cc) in mTEPES.phc:
            return OptModel.vHeatPipeInvest     [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vHeatPipeInvPer       [p,ni,nf,cc] == OptModel.vHeatPipeInvest      [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNetHeatInvest = Constraint(mTEPES.phc, rule=eConsecutiveNetHeatInvest, doc='heat pipe network investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Gen&transm investment o.f./constraints ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationObjFunct(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Generation oper o.f. model formulation ****')

    StartTime = time.time()

    # incoming and outgoing electric lines, H2 and heat pipelines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))
    for ni,nf,cc in mTEPES.pa:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))
    for ni,nf,cc in mTEPES.ha:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to electrolyzers (e2n)
    e2n = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            e2n[nd].append(el)

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

    def eTotalGCost(OptModel,n):
        return OptModel.vTotalGCost[p,sc,n] == (sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput    [p,sc,n,nr]                                              +
                                                    mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment     [p,sc,n,nr]                                              +
                                                    mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp        [p,sc,n,nr]                                              +
                                                    mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown       [p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr) +
                                                sum(mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveUp      [p,sc,n,nr]                                              +
                                                    mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveDown    [p,sc,n,nr] for nr in mTEPES.nr if (p,nr) in mTEPES.pnr and mTEPES.pIndOperReserveGen[nr] == 0) +
                                                sum(mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveUp   [p,sc,n,eh]                                              +
                                                    mTEPES.pLoadLevelWeight  [p,sc,n]() * mTEPES.pOperReserveCost[       eh] * OptModel.vESSReserveDown [p,sc,n,eh] for eh in mTEPES.eh if (p,eh) in mTEPES.peh and mTEPES.pIndOperReserveCon[eh] == 0) +
                                                sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearVarCost  [p,sc,n,bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if (p,bo) in mTEPES.pbo) +
                                                sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pLinearOMCost   [       re] * OptModel.vTotalOutput    [p,sc,n,re] for re in mTEPES.re if (p,re) in mTEPES.pre) )
    setattr(OptModel, f'eTotalGCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    # the small tolerance pEpsilon=1e-5 is added to avoid pumping/charging with curtailment/spillage
    pEpsilon = 1e-5
    def eTotalCCost(OptModel,n):
        return OptModel.vTotalCCost    [p,sc,n] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * (mTEPES.pLinearVarCost[p,sc,n,eh]+pEpsilon) * OptModel.vESSTotalCharge[p,sc,n,eh] for eh in mTEPES.eh if (p,eh) in mTEPES.peh)
    setattr(OptModel, f'eTotalCCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,n):
        if sum(mTEPES.pEmissionVarCost[p,sc,n,g] for g in mTEPES.g if (p,g) in mTEPES.pg):
            return OptModel.vTotalECost[p,sc,n] == sum(OptModel.vTotalECostArea[p,sc,n,ar] for ar in mTEPES.ar)
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalECost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalEmissionArea(OptModel,n,ar):
        if sum(mTEPES.pEmissionRate[g] for g in mTEPES.g if (ar, g) in mTEPES.a2g and (p, g) in mTEPES.pg):
            return OptModel.vTotalEmissionArea[p,sc,n,ar] == (sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionRate[nr] * 1e-3 * OptModel.vTotalOutput    [p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and (p,nr) in mTEPES.pnr)    #1e-3 to change from tCO2/MWh to MtCO2/GWh
                                                            + sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionRate[bo] * 1e-3 * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if (ar,bo) in mTEPES.a2g and (p,bo) in mTEPES.pbo))   #1e-3 to change from tCO2/MWh to MtCO2/GWh
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalEmissionArea_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eTotalEmissionArea, doc='area total emission [MtCO2 eq]'))

    def eTotalECostArea(OptModel,n,ar):
        if sum(mTEPES.pEmissionVarCost[p,sc,n,g] for g in mTEPES.g if (ar,g) in mTEPES.a2g and (p,g) in mTEPES.pg):
            return OptModel.vTotalECostArea[p,sc,n,ar] == (sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,nr] * OptModel.vTotalOutput    [p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and (p,nr) in mTEPES.pnr)
                                                        +  sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pEmissionVarCost[p,sc,n,bo] * OptModel.vTotalOutputHeat[p,sc,n,bo] for bo in mTEPES.bo if (ar,bo) in mTEPES.a2g and (p,bo) in mTEPES.pbo))
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalECostArea_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eTotalECostArea, doc='area emission cost [MEUR]'))

    def eTotalRESEnergyArea(OptModel,n,ar):
        if mTEPES.pRESEnergy[p,ar] and st == mTEPES.Last_st:
            return OptModel.vTotalRESEnergyArea[p,sc,n,ar] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * OptModel.vTotalOutput[p,sc,n,re] for re in mTEPES.re if (ar,re) in mTEPES.a2g and (p,re) in mTEPES.pre)
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalRESEnergyArea_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eTotalRESEnergyArea, doc='area RES energy [GWh]'))

    def eTotalRCost(OptModel,n):
        if   mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd)
        elif mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 0:
            return OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd) + sum(mTEPES.pH2NSCost * OptModel.vH2NS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
        elif mTEPES.pIndHydrogen == 0 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd)                                                                                                                                                                  + sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pHeatNSCost * OptModel.vHeatNS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
        elif mTEPES.pIndHydrogen == 1 and mTEPES.pIndHeat == 1:
            return OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pENSCost * OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd) + sum(mTEPES.pH2NSCost * OptModel.vH2NS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd])) + sum(mTEPES.pLoadLevelDuration[p,sc,n]() * mTEPES.pHeatNSCost * OptModel.vHeatNS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for ch in c2n[nd]) + sum(1 for hp in h2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]))
    setattr(OptModel, f'eTotalRCost_{p}_{sc}_{st}', Constraint(mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Operation cost        o.f.             ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationInvestment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Investment & operation var constraints ****')

    StartTime = time.time()

    def eInstallGenComm(OptModel,n,gc):
        if gc in mTEPES.nr and gc not in mTEPES.eh and gc not in mTEPES.bc and mTEPES.pMustRun[gc] == 0 and (mTEPES.pMinPowerElec[p,sc,n,gc] or mTEPES.pConstantVarCost[p,sc,n,gc]):
            return OptModel.vCommitment[p,sc,n,gc]                                 <= OptModel.vGenerationInvest[p,gc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInstallGenComm_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.gc, rule=eInstallGenComm, doc='commitment if installed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstallGenComm       ... ', len(getattr(OptModel, f'eInstallGenComm_{p}_{sc}_{st}')), ' rows')

    def eInstallESSComm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec]:
            return OptModel.vCommitment[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInstallESSComm_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ec, rule=eInstallESSComm, doc='commitment if ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstallESSComm       ... ', len(getattr(OptModel, f'eInstallESSComm_{p}_{sc}_{st}')), ' rows')

    def eInstallGenCap(OptModel,n,gc):
        if (p,gc) in mTEPES.pgc:
            if mTEPES.pMaxPowerElec[p,sc,n,gc]:
                return OptModel.vTotalOutput   [p,sc,n,gc] / mTEPES.pMaxPowerElec [p,sc,n,gc] <= OptModel.vGenerationInvest[p,gc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInstallGenCap_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.gc, rule=eInstallGenCap, doc='output if installed gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstallGenCap        ... ', len(getattr(OptModel, f'eInstallGenCap_{p}_{sc}_{st}')), ' rows')

    def eInstallFHUCap(OptModel,n,bc):
        if (p,bc) in mTEPES.pbc:
            if mTEPES.pMaxPowerHeat[p,sc,n,bc]:
                return OptModel.vTotalOutputHeat[p,sc,n,bc] / mTEPES.pMaxPowerHeat[p,sc,n,bc] <= OptModel.vGenerationInvest[p,bc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInstallFHUCap_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.bc, rule=eInstallFHUCap, doc='heat production if installed fuel heating unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstallFHUCap        ... ', len(getattr(OptModel, f'eInstallFHUCap_{p}_{sc}_{st}')), ' rows')

    def eInstallConESS(OptModel,n,ec):
        if (p,ec) in mTEPES.pec:
            if mTEPES.pMaxCharge[p,sc,n,ec]:
                return OptModel.vESSTotalCharge[p,sc,n,ec] / mTEPES.pMaxCharge[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInstallConESS_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ec, rule=eInstallConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstallConESS        ... ', len(getattr(OptModel, f'eInstallConESS_{p}_{sc}_{st}')), ' rows')

    def eUninstallGenComm(OptModel,n,gd):
        if (p,gd) in mTEPES.pgd:
            if gd in mTEPES.nr and gd not in mTEPES.eh and mTEPES.pMustRun[gd] == 0 and (mTEPES.pMinPowerElec[p,sc,n,gd] or mTEPES.pConstantVarCost[p,sc,n,gd]):
                return OptModel.vCommitment[p,sc,n,gd]                                <= 1 - OptModel.vGenerationRetire[p,gd]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eUninstallGenComm_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.gd, rule=eUninstallGenComm, doc='commitment if uninstalled unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstallGenComm     ... ', len(getattr(OptModel, f'eUninstallGenComm_{p}_{sc}_{st}')), ' rows')

    def eUninstallGenCap(OptModel,n,gd):
        if (p,gd) in mTEPES.pgd:
            if mTEPES.pMaxPowerElec[p,sc,n,gd]:
                return OptModel.vTotalOutput[p,sc,n,gd] / mTEPES.pMaxPowerElec[p,sc,n,gd] <= 1 - OptModel.vGenerationRetire[p,gd]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eUninstallGenCap_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.gd, rule=eUninstallGenCap, doc='output if uninstalled gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstallGenCap      ... ', len(getattr(OptModel, f'eUninstallGenCap_{p}_{sc}_{st}')), ' rows')

    def eAdequacyReserveMarginElec(OptModel,ar):
        if mTEPES.pReserveMargin[p,ar] and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g) and sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (ar,g) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]:
            return ((sum(                                       mTEPES.pRatedMaxPowerElec[g ] * mTEPES.pAvailability[g ]() / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if (p,g ) in mTEPES.pg  and (ar,g ) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) +
                     sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPowerElec[gc] * mTEPES.pAvailability[gc]() / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if (p,gc) in mTEPES.pgc and (ar,gc) in mTEPES.a2g                                      ) +
                     sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPowerElec[gd] * mTEPES.pAvailability[gd]() / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if (p,gd) in mTEPES.pgd and (ar,gd) in mTEPES.a2g                                      ) ) >= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar])
        else:
            return Constraint.Skip
    setattr(OptModel, f'eAdequacyReserveMarginElec_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eAdequacyReserveMarginElec, doc='electricity system adequacy reserve margin [p.u.]'))

    if pIndLogConsole == 1:
        print('eAdeqReserveMarginElec... ', len(getattr(OptModel, f'eAdequacyReserveMarginElec_{p}_{sc}_{st}')), ' rows')

    def eAdequacyReserveMarginHeat(OptModel,ar):
        if mTEPES.pIndHeat == 1:
            if mTEPES.pReserveMarginHeat[p,ar] and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g) and sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g])  for g in mTEPES.g if (ar,g) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
                return ((sum(                                       mTEPES.pRatedMaxPowerHeat[g ] * mTEPES.pAvailability[g ]() / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if (p,g ) in mTEPES.pg  and (ar,g ) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) +
                         sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPowerHeat[gc] * mTEPES.pAvailability[gc]() / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if (p,gc) in mTEPES.pgc and (ar,gc) in mTEPES.a2g                                      ) +
                         sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPowerHeat[gd] * mTEPES.pAvailability[gd]() / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if (p,gd) in mTEPES.pgd and (ar,gd) in mTEPES.a2g                                      ) ) >= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar])
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eAdequacyReserveMarginHeat_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eAdequacyReserveMarginHeat, doc='heat system adequacy reserve margin [p.u.]'))

    if pIndLogConsole == 1:
        print('eAdeqReserveMarginHeat... ', len(getattr(OptModel, f'eAdequacyReserveMarginHeat_{p}_{sc}_{st}')), ' rows')

    def eMaxSystemEmission(OptModel,ar):
        if mTEPES.pEmission[p,ar] < math.inf  and sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) and st == mTEPES.Last_st:
            # There is an emission limit, there are generators with emissions in the Area and it is the last stage
            return sum(OptModel.vTotalEmissionArea[p,sc,na,ar] for na in mTEPES.na) <= mTEPES.pEmission[p,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxSystemEmission_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eMaxSystemEmission, doc='maximum CO2 emission [tCO2]'))

    if pIndLogConsole == 1:
        print('eMaxSystemEmission    ... ', len(getattr(OptModel, f'eMaxSystemEmission_{p}_{sc}_{st}')), ' rows')

    def eMinSystemRESEnergy(OptModel,ar):
        if mTEPES.pRESEnergy[p,ar] and st == mTEPES.Last_st:
            return sum(OptModel.vTotalRESEnergyArea[p,sc,na,ar] for na in mTEPES.na)/sum(mTEPES.pLoadLevelDuration[p,sc,na] for na in mTEPES.na) >= mTEPES.pRESEnergy[p,ar]/sum(mTEPES.pLoadLevelDuration[p,sc,na] for na in mTEPES.na)
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinSystemRESEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eMinSystemRESEnergy, doc='minimum RES energy [GW]'))

    if pIndLogConsole == 1:
        print('eMinSystemRESEnergy   ... ', len(getattr(OptModel, f'eMinSystemRESEnergy_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating operation & investment      ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationDemand(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Inertia, oper resr, demand constraints ****')

    StartTime = time.time()

    # incoming and outgoing lines (lin) (lout) and lines with losses (linl) (loutl)
    lin   = defaultdict(list)
    linl  = defaultdict(list)
    lout  = defaultdict(list)
    loutl = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin  [nf].append((ni,cc))
        lout [ni].append((nf,cc))
    for ni,nf,cc in mTEPES.ll:
        linl [nf].append((ni,cc))
        loutl[ni].append((nf,cc))

    # nodes to generators (g2n)
    g2n = defaultdict(list)
    for nd,g in mTEPES.n2g:
        g2n[nd].append(g)
    e2n = defaultdict(list)
    for nd,eh in mTEPES.nd*mTEPES.eh:
        if (nd,eh) in mTEPES.n2g:
            e2n[nd].append(eh)

    # generators to area (e2a) (n2a) and area to generators (a2e) (a2n)
    e2a = defaultdict(list)
    a2e = defaultdict(list)
    for ar,eh in mTEPES.ar*mTEPES.eh:
        if (ar,eh) in mTEPES.a2g:
            e2a[ar].append(eh)
            a2e[eh].append(ar)
    n2a = defaultdict(list)
    a2n = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
            a2n[nr].append(ar)

    def eSystemInertia(OptModel,n,ar):
        if mTEPES.pSystemInertia[p,sc,n,ar] and sum(1 for nr in n2a[ar]):
            return sum(OptModel.vCommitment[p,sc,n,nr] * mTEPES.pInertia[nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) >= mTEPES.pSystemInertia[p,sc,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eSystemInertia_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eSystemInertia, doc='system inertia [s]'))

    if pIndLogConsole == 1:
        print('eSystemInertia        ... ', len(getattr(OptModel, f'eSystemInertia_{p}_{sc}_{st}')), ' rows')

    def eOperReserveUp(OptModel,n,ar):
        # Skip if there are no upward operating reserves
        if not mTEPES.pOperReserveUp[p,sc,n,ar]:
            return Constraint.Skip
        # Skip if there are no generators in this area which can provide reserves
        if (sum(1 for nr in n2a[ar] if (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0 ))
          + sum(1 for eh in e2a[ar] if (mTEPES.pIndOperReserveGen[eh] == 0 or mTEPES.pIndOperReserveCon[eh] == 0 )) == 0):
            return Constraint.Skip

        return sum(OptModel.vReserveUp  [p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveUp  [p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveUp[p,sc,n,ar]

    setattr(OptModel, f'eOperReserveUp_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveUp        ... ', len(getattr(OptModel, f'eOperReserveUp_{p}_{sc}_{st}')), ' rows')

    def eOperReserveDw(OptModel,n,ar):
        # Skip if there are no downward operating reserves
        if not mTEPES.pOperReserveDw[p,sc,n,ar]:
            return Constraint.Skip
        # Skip if there are no generators in this area which can provide reserves
        if (sum(1 for nr in n2a[ar] if (mTEPES.pIndOperReserveGen[nr] == 0 or mTEPES.pIndOperReserveCon[nr] == 0 ))
          + sum(1 for eh in e2a[ar] if (mTEPES.pIndOperReserveGen[eh] == 0 or mTEPES.pIndOperReserveCon[eh] == 0 )) == 0):
            return Constraint.Skip

        return sum(OptModel.vReserveDown[p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserveGen[nr] == 0 and (p,nr) in mTEPES.pnr) + sum(OptModel.vESSReserveDown[p,sc,n,eh] for eh in e2a[ar] if mTEPES.pIndOperReserveCon[eh] == 0 and (p,eh) in mTEPES.peh) == mTEPES.pOperReserveDw[p,sc,n,ar]

    setattr(OptModel, f'eOperReserveDw_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveDw        ... ', len(getattr(OptModel, f'eOperReserveDw_{p}_{sc}_{st}')), ' rows')

    def eReserveMinRatioDwUp(OptModel,n,nr):
        # Skip if there is no minimum up/down reserve ratio
        if not mTEPES.pMinRatioDwUp:
            return Constraint.Skip
        # Skip if no reserves are needed in the Area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0:
            return Constraint.Skip
        # Skip if generator cannot provide reserves while generating power
        if mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0 or mTEPES.pIndOperReserveGen[nr]:
            return Constraint.Skip

        return OptModel.vReserveDown[p,sc,n,nr] >= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMinRatioDwUp

    setattr(OptModel, f'eReserveMinRatioDwUp_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eReserveMinRatioDwUp, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMinRatioDwUp  ... ', len(getattr(OptModel, f'eReserveMinRatioDwUp_{p}_{sc}_{st}')), ' rows')

    def eReserveMaxRatioDwUp(OptModel,n,nr):
        # Skip if there is no maximum up/down reserve ratio
        if mTEPES.pMaxRatioDwUp >= 1.0:
            return Constraint.Skip
        # Skip if no reserves are needed in the Area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0:
            return Constraint.Skip
        # Skip if generator cannot provide reserves while generating power
        if mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0 or mTEPES.pIndOperReserveGen[nr]:
            return Constraint.Skip

        return OptModel.vReserveDown[p,sc,n,nr] <= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMaxRatioDwUp

    setattr(OptModel, f'eReserveMaxRatioDwUp_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eReserveMaxRatioDwUp, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMaxRatioDwUp  ... ', len(getattr(OptModel, f'eReserveMaxRatioDwUp_{p}_{sc}_{st}')), ' rows')

    def eRsrvMinRatioDwUpESS(OptModel,n,eh):
        # Skip if there is no minimum up/down reserve ratio
        if not mTEPES.pMinRatioDwUp:
            return Constraint.Skip
        # Skip if no reserves are needed in the Area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0:
            return Constraint.Skip
        # Skip if generator cannot provide reserves while generating power
        if mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0 or mTEPES.pIndOperReserveCon[nr]:
            return Constraint.Skip

        return OptModel.vESSReserveDown[p,sc,n,eh] >= OptModel.vESSReserveUp[p,sc,n,eh] * mTEPES.pMinRatioDwUp
    setattr(OptModel, f'eRsrvMinRatioDwUpESS_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eRsrvMinRatioDwUpESS, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMinRatioDwUpESS  ... ', len(getattr(OptModel, f'eRsrvMinRatioDwUpESS_{p}_{sc}_{st}')), ' rows')

    def eRsrvMaxRatioDwUpESS(OptModel,n,eh):
        # Skip if there is no maximum up/down reserve ratio
        if mTEPES.pMaxRatioDwUp >= 1.0:
            return Constraint.Skip
        # Skip if no reserves are needed in the Area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) == 0:
            return Constraint.Skip
        # Skip if generator cannot provide reserves while generating power
        if mTEPES.pMaxPower2ndBlock[p,sc,n,nr] == 0 or mTEPES.pIndOperReserveCon[nr]:
            return Constraint.Skip

        return OptModel.vESSReserveDown[p,sc,n,eh] <= OptModel.vESSReserveUp[p,sc,n,eh] * mTEPES.pMaxRatioDwUp

    setattr(OptModel, f'eRsrvMaxRatioDwUpESS_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eRsrvMaxRatioDwUpESS, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMaxRatioDwUpESS  ... ', len(getattr(OptModel, f'eRsrvMaxRatioDwUpESS_{p}_{sc}_{st}')), ' rows')


    def eReserveUpIfEnergy(OptModel,n,es):
        # When ESS units offer operating reserves, they must be able to provide the corresponding energy
        # This means they must have enough stored energy to provide all reserves if they were to have 100% activation

        # Skip if generator is not available in the period
        if (p,es) not in mTEPES.pes:
            return Constraint.Skip
        # Skip if generator cannot provide operating reserves while generating power
        if mTEPES.pIndOperReserveGen[es] or mTEPES.pMaxPower2ndBlock [p,sc,n,es] == 0:
            return Constraint.Skip
        # Skip if no upward reserves are needed in the area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) == 0:
            return Constraint.Skip
        # Skip if the ESS has no charging capabilities and receives no Inflows
        if (mTEPES.pTotalMaxCharge[es] and mTEPES.pTotalEnergyInflows[es]) == 0:
            return Constraint.Skip
        # Skip if the duration of the LoadLevel is 0
        if not mTEPES.pDuration[p,sc,n]():
            return Constraint.Skip

        # Avoid division by 0 if unit has no minimum power
        if mTEPES.pMinPowerElec[p,sc,n,es] == 0:
            return ((OptModel.vOutput2ndBlock[p,sc,n,es] + OptModel.vReserveUp[p,sc,n,es])                                      ) / math.sqrt(mTEPES.pEfficiency[es])<= (OptModel.vESSInventory[p,sc,n,es] - mTEPES.pMinStorage[p,sc,n,es]) / mTEPES.pDuration[p,sc,n]()
        else:
            return ((OptModel.vOutput2ndBlock[p,sc,n,es] + OptModel.vReserveUp[p,sc,n,es]) / mTEPES.pMinPowerElec[p,sc,n,es] + 1) / math.sqrt(mTEPES.pEfficiency[es]) <= (OptModel.vESSInventory[p,sc,n,es] - mTEPES.pMinStorage[p,sc,n,es]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinPowerElec[p,sc,n,es]

    setattr(OptModel, f'eReserveUpIfEnergy_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveUpIfEnergy    ... ', len(getattr(OptModel, f'eReserveUpIfEnergy_{p}_{sc}_{st}')), ' rows')

    def eESSReserveDwIfEnergy(OptModel,n,es):
        # When ESS units offer operating reserves, they must be able to provide the corresponding energy
        # This means they must have enough stored energy to provide all reserves if they were to have 100% activation

        # Skip if generator is not available in the period
        if (p,es) not in mTEPES.pes:
            return Constraint.Skip
        # Skip if generator cannot provide operating reserves while generating power
        if mTEPES.pIndOperReserveGen[es] or mTEPES.pMaxPower2ndBlock [p,sc,n,es] == 0:
            return Constraint.Skip
        # Skip if no upward reserves are needed in the area where the generator is located
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) == 0:
            return Constraint.Skip
        # Skip if the duration of the LoadLevel is 0
        if not mTEPES.pDuration[p,sc,n]():
            return Constraint.Skip

        # Avoid division by 0 if unit has no minimum power
        if mTEPES.pMinCharge[p,sc,n,es] == 0:
            return  OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]                                       * math.sqrt(mTEPES.pEfficiency[es]) <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[p,sc,n]()
        else:
            return ((OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pMinCharge[p,sc,n,es] + 1) * math.sqrt(mTEPES.pEfficiency[es]) <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinCharge[p,sc,n,es]

    setattr(OptModel, f'eESSReserveDwIfEnergy_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveDwIfEnergy ... ', len(getattr(OptModel, f'eESSReserveDwIfEnergy_{p}_{sc}_{st}')), ' rows')

    def eBalanceElec(OptModel,n,nd):
        if sum(1 for g in g2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutput[p,sc,n,g] for g in g2n[nd] if (p,g) in mTEPES.pg) - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh) + OptModel.vENS[p,sc,n,nd] -
                    sum(OptModel.vLineLosses[p,sc,n,nd,nf,cc] for nf,cc in loutl[nd] if (p,nd,nf,cc) in mTEPES.pll) - sum(OptModel.vFlowElec[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pla) -
                    sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc] for ni,cc in linl [nd] if (p,ni,nd,cc) in mTEPES.pll) + sum(OptModel.vFlowElec[p,sc,n,ni,nd,cc] for ni,cc in lin [nd] if (p,ni,nd,cc) in mTEPES.pla)) == mTEPES.pDemandElec[p,sc,n,nd]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nd, rule=eBalanceElec, doc='electric load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalanceElec          ... ', len(getattr(OptModel, f'eBalanceElec_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating inertia/reserves/balance    ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationStorage(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Storage   scheduling       constraints ****')

    StartTime = time.time()

    # area to generators (a2e)
    a2e = defaultdict(list)
    for ar,eh in mTEPES.ar*mTEPES.eh:
        if (ar,eh) in mTEPES.a2g:
            a2e[eh].append(ar)

    def eMaxInventory2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] and (p,ec) in mTEPES.pec:
                if mTEPES.pMaxStorage[p,sc,n,ec]:
                    return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMaxStorage[p,sc,n,ec] <= OptModel.vCommitment[p,sc,n,ec]
                else:
                    return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxInventory2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eMaxInventory2Comm, doc='ESS maximum inventory limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxInventory2Comm    ... ', len(getattr(OptModel, f'eMaxInventory2Comm_{p}_{sc}_{st}')), ' rows')

    def eMinInventory2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] and (p,ec) in mTEPES.pec:
                if mTEPES.pMinStorage[p,sc,n,ec]:
                    return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMinStorage[p,sc,n,ec] >= OptModel.vCommitment[p,sc,n,ec]
                else:
                    return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinInventory2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eMinInventory2Comm, doc='ESS minimum inventory limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinInventory2Comm    ... ', len(getattr(OptModel, f'eMinInventory2Comm_{p}_{sc}_{st}')), ' rows')

    def eInflows2Comm(OptModel,n,ec):
        if mTEPES.pIndBinStorInvest[ec] and (p,ec) in mTEPES.pec:
            if mTEPES.pEnergyInflows[p,sc,n,ec]():
                return OptModel.vEnergyInflows[p,sc,n,ec] / mTEPES.pEnergyInflows[p,sc,n,ec]() <= OptModel.vCommitment[p,sc,n,ec]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eInflows2Comm_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eInflows2Comm, doc='ESS inflows limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eInflows2Comm         ... ', len(getattr(OptModel, f'eInflows2Comm_{p}_{sc}_{st}')), ' rows')

    def eESSInventory(OptModel,n,es):
        if (p,es) in mTEPES.pes and (mTEPES.pTotalMaxCharge[es] or mTEPES.pTotalEnergyInflows[es]):
            if   (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[es]:
                if es not in mTEPES.ec:
                    return mTEPES.pIniInventory[p,sc,n,es]()                                            + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) *OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
                else:
                    return OptModel.vIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) *OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            elif (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) >  mTEPES.pStorageTimeStep[es]:
                if es not in mTEPES.ec:
                    return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pEnergyInflows[p,sc,n2,es]() - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) *OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
                else:
                    return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pStorageTimeStep[es]),es] + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] / math.sqrt(mTEPES.pEfficiency[es]) + math.sqrt(mTEPES.pEfficiency[es]) *OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStorageTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eESSInventory_{p}_{sc}_{st}', Constraint(mTEPES.nesc, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole == 1:
        print('eESSInventory         ... ', len(getattr(OptModel, f'eESSInventory_{p}_{sc}_{st}')), ' rows')

    def eIniFinInventory(OptModel,n,ec):
        if (p,ec) in mTEPES.pec and (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[ec]:
            return OptModel.vIniInventory[p,sc,n,ec] == OptModel.vESSInventory[p,sc,mTEPES.n.last(),ec]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eIniFinInventory_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eIniFinInventory, doc='Initial equal to final inventory for ESS candidates [p.u.]'))

    if pIndLogConsole == 1:
        print('eIniFinInventory      ... ', len(getattr(OptModel, f'eIniFinInventory_{p}_{sc}_{st}')), ' rows')

    def eIniInventory(OptModel,n,ec):
        if (p,ec) in mTEPES.pec and (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.pStorageTimeStep[ec] and mTEPES.pIndBinStorInvest[ec]:
            return OptModel.vIniInventory[p,sc,n,ec] / mTEPES.pIniInventory[p,sc,n,ec]() <= OptModel.vCommitment[p,sc,n,ec]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eIniInventory_{p}_{sc}_{st}', Constraint(mTEPES.necc, rule=eIniInventory, doc='Initial inventory for ESS candidates [p.u.]'))

    if pIndLogConsole == 1:
        print('eIniInventory         ... ', len(getattr(OptModel, f'eIniInventory_{p}_{sc}_{st}')), ' rows')

    def eMaxShiftTime(OptModel,n,eh):
        if mTEPES.pShiftTime[eh] and (p,eh) in mTEPES.peh:
            return mTEPES.pDuration[p,sc,n]()*mTEPES.pEfficiency[eh]*OptModel.vESSTotalCharge[p,sc,n,eh] <= sum(mTEPES.pDuration[p,sc,n2]()*OptModel.vTotalOutput[p,sc,n2,eh] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n):mTEPES.n.ord(n)+mTEPES.pShiftTime[eh]])
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxShiftTime_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eMaxShiftTime, doc='Maximum shift time [GWh]'))

    if pIndLogConsole == 1:
        print('eMaxShiftTime         ... ', len(getattr(OptModel, f'eMaxShiftTime_{p}_{sc}_{st}')), ' rows')

    def eMaxCharge(OptModel,n,eh):
        # Check if generator is available in the period and has variable charging capacity
        if (p,eh) not in mTEPES.peh or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0:
            return Constraint.Skip

        # Hydro units have commitment while ESS units are implicitly always committed
        if eh not in mTEPES.h:
            # ESS units only need this constraint when they can offer operating reserves and the systems demands reserves
            if mTEPES.pIndOperReserveCon[eh] != 0 or not sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[eh]):
                return Constraint.Skip
            # ESS case equation
            return (OptModel.vCharge2ndBlock[p, sc, n, eh] + OptModel.vESSReserveDown[p, sc, n, eh]) / mTEPES.pMaxCharge2ndBlock[p, sc, n, eh] <= 1.0
        # Hydro case equation

        else:
            return (OptModel.vCharge2ndBlock[p, sc, n, eh] + OptModel.vESSReserveDown[p, sc, n, eh]) / mTEPES.pMaxCharge2ndBlock[p, sc, n, eh] <= OptModel.vCommitmentCons[p, sc, n, eh]
    setattr(OptModel, f'eMaxCharge_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCharge            ... ', len(getattr(OptModel, f'eMaxCharge_{p}_{sc}_{st}')), ' rows')

    def eMinCharge(OptModel, n, eh):
        # Skip if ESS is not available in the period
        if (p,eh) not in mTEPES.peh:
            return Constraint.Skip
        # Skip if ESS cannot provide reserves while consuming power
        if mTEPES.pIndOperReserveCon[eh]:
            return Constraint.Skip
        # Skip if no reserves are demanded in the area where the ESS is located
        if sum(mTEPES.pOperReserveUp[p, sc, n, ar] for ar in a2e[eh]) == 0:
            return Constraint.Skip
        # Skip if the ESS cannot consume at variable power
        if not mTEPES.pMaxCharge2ndBlock[p, sc, n, eh]:
            return Constraint.Skip

        return OptModel.vCharge2ndBlock[p, sc, n, eh] - OptModel.vESSReserveUp[p, sc, n, eh] >= 0.0

    setattr(OptModel, f'eMinCharge_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinCharge            ... ', len(getattr(OptModel, f'eMinCharge_{p}_{sc}_{st}')), ' rows')

    # def eChargeDischarge(OptModel,n,eh):
    #     if mTEPES.pMaxCharge[p,sc,n,eh]:
    #         return OptModel.vTotalOutput[p,sc,n,eh] / mTEPES.pMaxPowerElec[p,sc,n,eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] / mTEPES.pMaxCharge[p,sc,n,eh] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.n, mTEPES.eh, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    # Generators with consumption capability cannot be consuming and generating simultaneously
    def eChargeDischarge(OptModel,n,eh):
        # Check if generator is avaiable in the period
        if (p,eh) not in mTEPES.peh:
            return Constraint.Skip
        # Constraint only relevant to generators which can consume and generate power
        if mTEPES.pMaxPower2ndBlock [p,sc,n,eh] == 0 or mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0:
            return Constraint.Skip

        #Hydro generators can have binary commitment, energy modeled ESS do not have commitment

        # ESS Generator
        if eh not in mTEPES.h:
            return ((OptModel.vOutput2ndBlock[p,sc,n,eh] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [p,sc,n,eh]) / mTEPES.pMaxPower2ndBlock [p,sc,n,eh] +
                    (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0)
        # Hydro Generator
        else:
            return OptModel.vCommitment[p,sc,n,eh] + OptModel.vCommitmentCons[p,sc,n,eh] <= 1.0

    setattr(OptModel, f'eChargeDischarge_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeDischarge      ... ', len(getattr(OptModel, f'eChargeDischarge_{p}_{sc}_{st}')), ' rows')

    def eESSTotalCharge(OptModel,n,eh):
        # Check if generator is avaiable in the period
        if (p,eh) not in mTEPES.peh:
            return Constraint.Skip
        # Constraint only applies to generators with charging capabilities
        if mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] == 0:
            return Constraint.Skip

        # Hydro generators can have binary commitment, energy modeled ESS do not have commitment

        # ESS Generator
        if eh not in mTEPES.h:
            # Check minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==        OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]
            else:
                return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == 1.0 + (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]
        # Hydro generator
        else:
            # Check minimum charge to avoid dividing by 0. Dividing by MinCharge is more numerically stable
            if mTEPES.pMinCharge[p,sc,n,eh] == 0.0:
                return OptModel.vESSTotalCharge[p,sc,n,eh]                                ==        OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]
            else:
                return OptModel.vESSTotalCharge[p,sc,n,eh] / mTEPES.pMinCharge[p,sc,n,eh] == OptModel.vCommitmentCons[p,sc,n,eh] + (OptModel.vCharge2ndBlock[p,sc,n,eh] + mTEPES.pDwReserveActivation * OptModel.vESSReserveDown[p,sc,n,eh] - mTEPES.pUpReserveActivation * OptModel.vESSReserveUp[p,sc,n,eh]) / mTEPES.pMinCharge[p,sc,n,eh]

    setattr(OptModel, f'eESSTotalCharge_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eESSTotalCharge       ... ', len(getattr(OptModel, f'eESSTotalCharge_{p}_{sc}_{st}')), ' rows')

    def eChargeOutflows(OptModel,n,eh):
        if mTEPES.pIndOutflowIncomp[eh] == 1 and (p,eh) in mTEPES.peh and (p,sc,eh) in mTEPES.eo:
            if mTEPES.pMaxCharge2ndBlock[p,sc,n,eh]:
                return (OptModel.vEnergyOutflows[p,sc,n,eh] + OptModel.vCharge2ndBlock[p,sc,n,eh]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] <= 1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eChargeOutflows_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eChargeOutflows, doc='incompatibility between charge and outflows use [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeOutflows       ... ', len(getattr(OptModel, f'eChargeOutflows_{p}_{sc}_{st}')), ' rows')

    def eEnergyOutflows(OptModel,n,es):
        if (p,sc,es) in mTEPES.eo:
            return sum((OptModel.vEnergyOutflows[p,sc,n2,es] - mTEPES.pEnergyOutflows[p,sc,n2,es]())*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)]) == 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eEnergyOutflows_{p}_{sc}_{st}', Constraint(mTEPES.neso, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eEnergyOutflows       ... ', len(getattr(OptModel, f'eEnergyOutflows_{p}_{sc}_{st}')), ' rows')

    def eMinimumEnergy(OptModel,n,g):
        if (p,sc,g) in mTEPES.gm and (p,g) in mTEPES.pg:
            return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinimumEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ngen, rule=eMinimumEnergy, doc='minimum energy of a unit [GWh]'))

    if pIndLogConsole == 1:
        print('eMinimumEnergy        ... ', len(getattr(OptModel, f'eMinimumEnergy_{p}_{sc}_{st}')), ' rows')

    def eMaximumEnergy(OptModel,n,g):
        if (p,sc,g) in mTEPES.gM and (p,g) in mTEPES.pg:
            return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMaxEnergy[p,sc,n2,g])*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) <= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaximumEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ngen, rule=eMaximumEnergy, doc='maximum energy of a unit [GWh]'))

    if pIndLogConsole == 1:
        print('eMaximumEnergy        ... ', len(getattr(OptModel, f'eMaximumEnergy_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating storage operation           ... ', round(GeneratingTime), 's')

def GenerationOperationModelFormulationReservoir(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Reservoir scheduling       constraints ****')

    StartTime = time.time()

    # area to generators (a2e)
    a2h = defaultdict(list)
    for ar,h in mTEPES.ar*mTEPES.h:
        if (ar,h) in mTEPES.a2g:
            a2h[h].append(ar)

    def eMaxVolume2Comm(OptModel,n,rc):
        if mTEPES.pIndBinRsrInvest[rc]() and (p,rc) in mTEPES.prc:
            if sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPowerElec[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) and mTEPES.pMaxVolume[p,sc,n,rc]:
                return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMaxVolume[p,sc,n,rc] <= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxVolume2Comm_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eMaxVolume2Comm, doc='Reservoir maximum volume limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxVolume2Comm       ... ', len(getattr(OptModel, f'eMaxVolume2Comm_{p}_{sc}_{st}')), ' rows')

    def eMinVolume2Comm(OptModel,n,rc):
        if mTEPES.pIndBinRsrInvest[rc]() and (p,rc) in mTEPES.prc:
            if sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPowerElec[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) and mTEPES.pMinVolume[p,sc,n,rc]:
                return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMinVolume[p,sc,n,rc] >= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinVolume2Comm_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eMinVolume2Comm, doc='Reservoir minimum volume limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinVolume2Comm       ... ', len(getattr(OptModel, f'eMinVolume2Comm_{p}_{sc}_{st}')), ' rows')

    def eTrbReserveUpIfUpstream(OptModel,n,h):
        # There must be enough water upstream of the turbine to produce all the possible offered power (scheduled + reserves)

        # Skip if generator is not available in the period
        if (p,h) not in mTEPES.ph:
            return Constraint.Skip
        # Skip if turbine cannot provide reserves
        if mTEPES.pIndOperReserveGen[h]:
            return Constraint.Skip
        # Skip if no reserves are demanded in the area where the turbine is located
        if sum(mTEPES.pOperReserveUp[p, sc, n, ar] for ar in a2h[h]) == 0:
            return Constraint.Skip
        # Skip if turbine cannot generate at variable power
        if mTEPES.pMaxPower2ndBlock [p,sc,n,h] == 0:
            return Constraint.Skip
        # Skip if LoalLevel has duration 0
        if mTEPES.pDuration[p, sc, n]() == 0:
            return Constraint.Skip

        # Avoid division by 0 if turbine has no minimum power
        if mTEPES.pMinPowerElec[p, sc, n, h] == 0:
            return  OptModel.vOutput2ndBlock[p, sc, n, h] + OptModel.vReserveUp[p, sc, n, h]                                                                          <= sum(OptModel.vReservoirVolume[p, sc, n, rs] - mTEPES.pMinVolume[p, sc, n, rs] for rs in mTEPES.rs if (rs, h) in mTEPES.r2h) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]()
        else:
            return (OptModel.vOutput2ndBlock[p, sc, n, h] + OptModel.vReserveUp[p, sc, n, h]) / mTEPES.pMinPowerElec[p, sc, n, h] + OptModel.vCommitment[p, sc, n, h] <= sum(OptModel.vReservoirVolume[p, sc, n, rs] - mTEPES.pMinVolume[p, sc, n, rs] for rs in mTEPES.rs if (rs, h) in mTEPES.r2h) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]() / mTEPES.pMinPowerElec[p, sc, n, h]

    setattr(OptModel, f'eTrbReserveUpIfUpstream_{p}_{sc}_{st}', Constraint(mTEPES.nhc, rule=eTrbReserveUpIfUpstream, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eTrbReserveUpIfUpstream ... ', len(getattr(OptModel, f'eTrbReserveUpIfUpstream_{p}_{sc}_{st}')), ' rows')

    def eTrbReserveUpIfDownstream(OptModel,n,h):
        #There must be enough spare reservoir capacity downstream of a turbine to fit all the possible water (scheduled + reserves)

        # Skip if generator is not available in the period
        if (p,h) not in mTEPES.ph:
            return Constraint.Skip
        # Skip if turbine cannot provide reserves
        if mTEPES.pIndOperReserveGen[h]:
            return Constraint.Skip
        # Skip if no reserves are demanded in the area where the turbine is located
        if sum(mTEPES.pOperReserveUp[p, sc, n, ar] for ar in a2h[h]) == 0:
            return Constraint.Skip
        # Skip if turbine cannot generate at variable power
        if mTEPES.pMaxPower2ndBlock [p,sc,n,h] == 0:
            return Constraint.Skip
        # Skip if LoalLevel has duration 0
        if mTEPES.pDuration[p, sc, n]() == 0:
            return Constraint.Skip

        # Avoid division by 0 if turbine has no minimum power
        if mTEPES.pMinPowerElec[p, sc, n, h] == 0:
            return  OptModel.vOutput2ndBlock[p, sc, n, h] + OptModel.vReserveUp[p, sc, n, h]                                                                          <= sum(mTEPES.pMaxVolume[p, sc, n, rs] - OptModel.vReservoirVolume[p, sc, n, rs] for rs in mTEPES.rs if (h,rs) in mTEPES.h2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]()
        else:
            return (OptModel.vOutput2ndBlock[p, sc, n, h] + OptModel.vReserveUp[p, sc, n, h]) / mTEPES.pMinPowerElec[p, sc, n, h] + OptModel.vCommitment[p, sc, n, h] <= sum(mTEPES.pMaxVolume[p, sc, n, rs] - OptModel.vReservoirVolume[p, sc, n, rs] for rs in mTEPES.rs if (h,rs) in mTEPES.h2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]() / mTEPES.pMinPowerElec[p, sc, n, h]

    setattr(OptModel, f'eTrbReserveUpIfDownstream_{p}_{sc}_{st}', Constraint(mTEPES.nhc, rule=eTrbReserveUpIfDownstream, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eTrbReserveUpIfDownstream ... ', len(getattr(OptModel, f'eTrbReserveUpIfDownstream_{p}_{sc}_{st}')), ' rows')


    def ePmpReserveDwIfUpstream(OptModel,n,h):
        # There must be enough reservoir capacity upstream to store all the possible water (scheduled + reserves)

        # Skip if pump is not available in the period
        if (p, h) not in mTEPES.ph:
            return Constraint.Skip
        # Skip if pump cannot provide reserves
        if mTEPES.pIndOperReserveCon[h]:
            return Constraint.Skip
        # Skip if pump is not connected to any reservoir
        if sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) == 0:
            return Constraint.Skip
        # Skip if no reserves are demanded in the area where the turbine is located
        if sum(mTEPES.pOperReserveDw[p, sc, n, ar] for ar in a2h[h]) == 0:
            return Constraint.Skip
        # Skip if pump cannot consume at variable power
        if mTEPES.pMaxCharge2ndBlock[p, sc, n, h] == 0:
            return Constraint.Skip
        # Skip if LoalLevel has duration 0
        if mTEPES.pDuration[p, sc, n]() == 0:
            return Constraint.Skip

        # Avoid dividing by 0 if pump has no minimum charge
        if mTEPES.pMinCharge[p,sc,n,h] == 0:
            return  (OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]                                                                     ) * mTEPES.pEfficiency[h] <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]()
        else:
            return ((OptModel.vCharge2ndBlock[p,sc,n,h] + OptModel.vESSReserveDown[p,sc,n,h]) / mTEPES.pMinCharge[p,sc,n,h] + OptModel.vCommitmentCons[p,sc,n,h])  * mTEPES.pEfficiency[h] <= sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p,sc,n]() / mTEPES.pMinCharge[p,sc,n,h]

    setattr(OptModel, f'ePmpReserveDwIfUpstream_{p}_{sc}_{st}', Constraint(mTEPES.npc, rule=ePmpReserveDwIfUpstream, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('ePmpReserveDwIfUpstream ... ', len(getattr(OptModel, f'ePmpReserveDwIfUpstream_{p}_{sc}_{st}')), ' rows')

    def ePmpReserveDwIfDownstream(OptModel, n, h):
        # There must be enough water downstream for the pump to draw from in case it needs to operate at the maximum capacity offered (scheduled + reserves)

        # Skip if pump is not available in the period
        if (p, h) not in mTEPES.ph:
            return Constraint.Skip
        # Skip if pump cannot provide reserves
        if mTEPES.pIndOperReserveCon[h]:
            return Constraint.Skip
        # Skip if pump is not connected to any reservoir
        if sum(1 for rs in mTEPES.rs if (h, rs) in mTEPES.p2r) == 0:
            return Constraint.Skip
        # Skip if no reserves are demanded in the area where the turbine is located
        if sum(mTEPES.pOperReserveDw[p, sc, n, ar] for ar in a2h[h]) == 0:
            return Constraint.Skip
        # Skip if pump cannot consume at variable power
        if mTEPES.pMaxCharge2ndBlock[p, sc, n, h] == 0:
            return Constraint.Skip
        # Skip if LoalLevel has duration 0
        if mTEPES.pDuration[p, sc, n]() == 0:
            return Constraint.Skip

        # Avoid dividing by 0 if pump has no minimum charge
        if mTEPES.pMinCharge[p, sc, n, h] == 0:
            return  (OptModel.vCharge2ndBlock[p, sc, n, h] + OptModel.vESSReserveDown[p, sc, n, h]                                                                          ) * mTEPES.pEfficiency[h] <= sum(OptModel.vReservoirVolume[p, sc, n, rs] - mTEPES.pMinVolume[p, sc, n, rs] for rs in mTEPES.rs if (rs, h) in mTEPES.r2p) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]()
        else:
            return ((OptModel.vCharge2ndBlock[p, sc, n, h] + OptModel.vESSReserveDown[p, sc, n, h]) / mTEPES.pMinCharge[p, sc, n, h] + OptModel.vCommitmentCons[p, sc, n, h]) * mTEPES.pEfficiency[h] <= sum(OptModel.vReservoirVolume[p, sc, n, rs] - mTEPES.pMinVolume[p, sc, n, rs] for rs in mTEPES.rs if (rs, h) in mTEPES.r2p) * mTEPES.pProductionFunctionHydro[h] / mTEPES.pDuration[p, sc, n]() / mTEPES.pMinCharge[p, sc, n, h]

    setattr(OptModel, f'ePmpReserveDwIfDownstream_{p}_{sc}_{st}', Constraint(mTEPES.npc, rule=ePmpReserveDwIfDownstream, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('ePmpReserveDwIfDownstream ... ', len(getattr(OptModel, f'ePmpReserveDwIfDownstream_{p}_{sc}_{st}')), ' rows')

    def eHydroInventory(OptModel,n,rs):
        if (p,rs) in mTEPES.prs and sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r or (rs,h) in mTEPES.r2p or (h,rs) in mTEPES.p2r):
            if   (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.pReservoirTimeStep[rs]:
                if rs not in mTEPES.rn:
                    return (mTEPES.pIniVolume[p,sc,n,rs]()                                                    + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pHydroInflows[p,sc,n2,rs]()*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
                else:
                    return (OptModel.vIniVolume[p,sc,n,rs]                                                    + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            elif (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) >  mTEPES.pReservoirTimeStep[rs]:
                if rs not in mTEPES.rn:
                    return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pReservoirTimeStep[rs]),rs] + sum(mTEPES.pDuration[p,sc,n2]()*(mTEPES.pHydroInflows[p,sc,n2,rs]()*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
                else:
                    return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pReservoirTimeStep[rs]),rs] + sum(mTEPES.pDuration[p,sc,n2]()*(OptModel.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunctionHydro[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pReservoirTimeStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eHydroInventory_{p}_{sc}_{st}', Constraint(mTEPES.nrsc, rule=eHydroInventory, doc='Reservoir water inventory [hm3]'))

    if pIndLogConsole == 1:
        print('eHydroInventory       ... ', len(getattr(OptModel, f'eHydroInventory_{p}_{sc}_{st}')), ' rows')

    def eIniFinVolume(OptModel,n,rs):
        if (p,rs) in mTEPES.prs and (p,sc,st,n) in mTEPES.s2n and mTEPES.n.ord(n) == mTEPES.pReservoirTimeStep[rs]:
            return OptModel.vIniVolume[p,sc,n,rs] == OptModel.vHydroInventory[p,sc,mTEPES.n.last(),rs]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eIniFinVolume_{p}_{sc}_{st}', Constraint(mTEPES.nrcc, rule=eIniFinVolume, doc='Initial equal to final volume for reservoir candidates [p.u.]'))

    if pIndLogConsole == 1:
        print('eIniFinVolume         ... ', len(getattr(OptModel, f'eIniFinVolume_{p}_{sc}_{st}')), ' rows')

    def eHydroOutflows(OptModel,n,rs):
        if (p,sc,rs) in mTEPES.ro:
            return sum((OptModel.vHydroOutflows[p,sc,n2,rs] - mTEPES.pHydroOutflows[p,sc,n2,rs]())*mTEPES.pDuration[p,sc,n2]() for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pWaterOutTimeStep[rs]:mTEPES.n.ord(n)]) == 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eHydroOutflows_{p}_{sc}_{st}', Constraint(mTEPES.nrso, rule=eHydroOutflows, doc='hydro outflows of a reservoir [m3/s]'))

    if pIndLogConsole == 1:
        print('eHydroOutflows        ... ', len(getattr(OptModel, f'eHydroOutflows_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating reservoir operation         ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationCommitment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Unit commitment            constraints ****')

    StartTime = time.time()

    # area to generators (a2n)
    a2n = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            a2n[nr].append(ar)

    def eMaxOutput2ndBlock(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr]))):
            if   mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n != mTEPES.n.last():
                return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,mTEPES.n.next(n),nr]
            elif mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.last():
                return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMaxOutput2ndBlock_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxOutput2ndBlock    ... ', len(getattr(OptModel, f'eMaxOutput2ndBlock_{p}_{sc}_{st}')), ' rows')

    def eMinOutput2ndBlock(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr]))):
            if mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
                return  OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]                                        >= 0.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinOutput2ndBlock_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinOutput2ndBlock    ... ', len(getattr(OptModel, f'eMinOutput2ndBlock_{p}_{sc}_{st}')), ' rows')

    def eTotalOutput(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr]))):
            if mTEPES.pMaxPowerElec[p,sc,n,nr]:
                if mTEPES.pMinPowerElec[p,sc,n,nr] == 0.0:
                    return OptModel.vTotalOutput[p,sc,n,nr]                                   ==                                    OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]
                else:
                    return OptModel.vTotalOutput[p,sc,n,nr] / mTEPES.pMinPowerElec[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr] + (OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pMinPowerElec[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eTotalOutput_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, f'eTotalOutput_{p}_{sc}_{st}')), ' rows')

    def eUCStrShut(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr:
            if mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPowerElec[p,sc,n,nr] or mTEPES.pConstantVarCost[p,sc,n,nr]) and nr not in mTEPES.eh:
                if n == mTEPES.n.first():
                    return OptModel.vCommitment[p,sc,n,nr] - mTEPES.pInitialUC[p,sc,n,nr]()                 == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
                else:
                    return OptModel.vCommitment[p,sc,n,nr] - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eUCStrShut_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown [p.u.]'))

    if pIndLogConsole == 1:
        print('eUCStrShut            ... ', len(getattr(OptModel, f'eUCStrShut_{p}_{sc}_{st}')), ' rows')

    def eStableStates(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr:
            if mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
                return OptModel.vStableState[p,sc,n,nr] + OptModel.vRampUpState[p,sc,n,nr] + OptModel.vRampDwState[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eStableStates_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eStableStates, doc='relation among stable, ramp up and ramp down states [p.u.]'))

    if pIndLogConsole == 1:
        print('eStableStates         ... ', len(getattr(OptModel, f'eStableStates_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitmentYearly(OptModel,n,group,nr):
        # Skip if generator not available on period
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        # Skip if the generator is not part of the exclusive group
        if nr not in mTEPES.GeneratorsInYearlyGroup[group]:
            return Constraint.Skip
        # Skip if there are one or less generators in the group
        if len(mTEPES.GeneratorsInYearlyGroup[group] & {nr for (p,nr) in mTEPES.pnr}) <= 1:
            return Constraint.Skip

        return OptModel.vCommitment[p,sc,n,nr]                               <= OptModel.vMaxCommitmentYearly[p,sc,nr,group]

    setattr(OptModel, f'eMaxCommitmentYearly_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ExclusiveGroupsYearly, mTEPES.nr, rule=eMaxCommitmentYearly, doc='maximum of all the commitments [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCommitmentYearly        ... ', len(getattr(OptModel, f'eMaxCommitmentYearly_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitGenYearly(OptModel,n,group,nr):
        # Skip if generator not available on period
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        # Skip if the generator is not part of the exclusive group
        if nr not in mTEPES.GeneratorsInYearlyGroup[group]:
            return Constraint.Skip
        # Avoid division by 0. If Maximum power is 0 this equation is not needed anyways
        if mTEPES.pMaxPowerElec[p, sc, n, nr] == 0:
            return Constraint.Skip
        # Skip if there are one or less generators in the group
        if len(mTEPES.GeneratorsInYearlyGroup[group] & {nr for (p, nr) in mTEPES.pnr}) <= 1:
            return Constraint.Skip

        return OptModel.vTotalOutput[p,sc,n,nr]/mTEPES.pMaxPowerElec[p,sc,n,nr] <= OptModel.vMaxCommitmentYearly[p,sc,nr,group]

    setattr(OptModel, f'eMaxCommitGenYearly_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ExclusiveGroupsYearly,mTEPES.nr, rule=eMaxCommitGenYearly, doc='maximum of all the capacity factors'))

    if pIndLogConsole == 1:
        print('eMaxCommitGenYearly         ... ', len(getattr(OptModel, f'eMaxCommitGenYearly_{p}_{sc}_{st}')), ' rows')

    def eExclusiveGensYearly(OptModel,group):
        # Skip if there are one or less generators in the group
        if len(mTEPES.GeneratorsInYearlyGroup[group] & {nr for (p,nr) in mTEPES.pnr}) <= 1:
            return Constraint.Skip
        return sum(OptModel.vMaxCommitmentYearly[p, sc, nr, group] + (OptModel.vCommitmentCons[p, sc, nr] if nr in mTEPES.h else 0) for nr in mTEPES.GeneratorsInYearlyGroup[group] if (p, nr) in mTEPES.pnr ) <= 1
    setattr(OptModel, f'eExclusiveGensYearly_{p}_{sc}_{st}', Constraint(mTEPES.ExclusiveGroupsYearly, rule=eExclusiveGensYearly, doc='mutually exclusive generators'))

    if pIndLogConsole == 1:
        print('eExclusiveGensYearly        ... ', len(getattr(OptModel, f'eExclusiveGensYearly_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')

    def eMaxCommitmentHourly(OptModel,n,group,nr):
        # Skip if generator not available on period
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        # Skip if the generator is not part of the exclusive group
        if nr not in mTEPES.GeneratorsInHourlyGroup[group]:
            return Constraint.Skip
        # Skip if there are one or less generators in the group
        if len(mTEPES.GeneratorsInHourlyGroup[group] & {nr for (p,nr) in mTEPES.pnr}) <= 1:
            return Constraint.Skip

        return OptModel.vCommitment[p,sc,n,nr]                               <= OptModel.vMaxCommitmentHourly[p,sc,n,nr,group]

    setattr(OptModel, f'eMaxCommitmentHourly_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ExclusiveGroupsHourly, mTEPES.nr, rule=eMaxCommitmentHourly, doc='maximum of all the commitments [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCommitmentHourly        ... ', len(getattr(OptModel, f'eMaxCommitmentHourly_{p}_{sc}_{st}')), ' rows')

    def eMaxCommitGenHourly(OptModel,n,group,nr):
        # Skip if generator not available on period
        if (p,nr) not in mTEPES.pnr:
            return Constraint.Skip
        # Skip if the generator is not part of the exclusive group
        if nr not in mTEPES.GeneratorsInHourlyGroup[group]:
            return Constraint.Skip
        # Avoid division by 0. If Maximum power is 0 this equation is not needed anyways
        if mTEPES.pMaxPowerElec[p,sc,n,nr] == 0:
            return Constraint.Skip
        # Skip if there are one or less generators in the group
        if len(mTEPES.GeneratorsInHourlyGroup[group] & {nr for (p,nr) in mTEPES.pnr}) <= 1:
            return Constraint.Skip

        return OptModel.vTotalOutput[p,sc,n,nr]/mTEPES.pMaxPowerElec[p,sc,n,nr] <= OptModel.vMaxCommitmentHourly[p,sc,n,nr,group]

    setattr(OptModel, f'eMaxCommitGenHourly_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ExclusiveGroupsHourly,mTEPES.nr, rule=eMaxCommitGenHourly, doc='maximum of all the capacity factors'))

    if pIndLogConsole == 1:
        print('eMaxCommitGenHourly         ... ', len(getattr(OptModel, f'eMaxCommitGenHourly_{p}_{sc}_{st}')), ' rows')

    def eExclusiveGensHourly(OptModel,n,group):
        # Skip if there are one or less generators in the group
        # This is written in a different way to the rest of the code to avoid variable shadowing due to comprehension
        if len(mTEPES.GeneratorsInHourlyGroup[group] & {gen for (period, gen) in mTEPES.pnr if period == p}) <= 1:
            return Constraint.Skip

        return sum(OptModel.vMaxCommitmentHourly[p,sc,n,nr,group] + (OptModel.vCommitmentCons[p,sc,n,nr] if nr in mTEPES.h else 0) for nr in mTEPES.GeneratorsInHourlyGroup[group] if (p, nr) in mTEPES.pnr ) <= 1

    setattr(OptModel, f'eExclusiveGensHourly_{p}_{sc}_{st}', Constraint(mTEPES.n,mTEPES.ExclusiveGroupsHourly, rule=eExclusiveGensHourly, doc='mutually exclusive generators'))

    if pIndLogConsole == 1:
        print('eExclusiveGensHourly        ... ', len(getattr(OptModel, f'eExclusiveGensHourly_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')
def GenerationOperationModelFormulationRampMinTime(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Ramp and min up/down time  constraints ****')

    StartTime = time.time()

    def eRampUp(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr]))):
            if mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pDuration[p,sc,n]():
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr],0.0)                        + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveDown[p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampUp_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUp               ... ', len(getattr(OptModel, f'eRampUp_{p}_{sc}_{st}')), ' rows')

    def eRampDw(OptModel,n,nr):
        if (p,nr) in mTEPES.pnr and (nr not in mTEPES.es or (nr in mTEPES.es and (mTEPES.pTotalMaxCharge[nr] or mTEPES.pTotalEnergyInflows[nr]))):
            if mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pDuration[p,sc,n]():
                if n == mTEPES.n.first():
                    return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr],0.0)                        + OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[p,sc,n,nr]()                 + OptModel.vShutDown[p,sc,n,nr]
                else:
                    return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveUp  [p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] + OptModel.vShutDown[p,sc,n,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampDw_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDw               ... ', len(getattr(OptModel, f'eRampDw_{p}_{sc}_{st}')), ' rows')

    def eRampUpCharge(OptModel,n,eh):
        if (p,eh) in mTEPES.peh:
            if mTEPES.pRampUp[eh] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge2ndBlock[p,sc,n,eh] and mTEPES.pDuration[p,sc,n]():
                if n == mTEPES.n.first():
                    return (                                                                                                            OptModel.vCharge2ndBlock[p,sc,n,eh] - OptModel.vESSReserveUp  [p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[eh] >= - 1.0
                else:
                    return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),eh] + OptModel.vESSReserveDown[p,sc,mTEPES.n.prev(n),eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] - OptModel.vESSReserveUp  [p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[eh] >= - 1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampUpChr_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpChr            ... ', len(getattr(OptModel, f'eRampUpChr_{p}_{sc}_{st}')), ' rows')

    def eRampDwCharge(OptModel,n,eh):
        if (p,eh) in mTEPES.peh:
            if mTEPES.pRampDw[eh] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge[p,sc,n,eh] and mTEPES.pDuration[p,sc,n]():
                if n == mTEPES.n.first():
                    return (                                                                                                          + OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[eh] <=   1.0
                else:
                    return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),eh] - OptModel.vESSReserveUp  [p,sc,mTEPES.n.prev(n),eh] + OptModel.vCharge2ndBlock[p,sc,n,eh] + OptModel.vESSReserveDown[p,sc,n,eh]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[eh] <=   1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampDwChr_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.eh, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwChr            ... ', len(getattr(OptModel, f'eRampDwChr_{p}_{sc}_{st}')), ' rows')

    pIndSimplexFormulation = True  # Parameter to choose if minimum stable time should be physically accurate or computationally efficient. True for efficiency, False for accuracy
    pIndStableTimeDeadBand = True  # Parameter to choose if ramps below a certain threshold set by pEpsilon should not be restricted. True for having dead band, False for restricting all ramps

    if pIndStableTimeDeadBand:
        pEpsilon = 1e-2
    else:
        pEpsilon = 1e-4

    def eRampUpState(OptModel,n,nr):
        if mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and (p,nr) in mTEPES.pnr and mTEPES.pDuration[p,sc,n]():
            if pIndStableTimeDeadBand:
                if mTEPES.pRampUp[nr]:
                    if n == mTEPES.n.first():
                        return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                    else:
                        return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    if n == mTEPES.n.first():
                        return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                    else:
                        return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * (OptModel.vRampDwState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
            else:
                if mTEPES.pRampUp[nr]:
                    if n == mTEPES.n.first():
                        return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
                    else:
                        return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampUp[nr]                  <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
                else:
                    if n == mTEPES.n.first():
                        return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
                    else:
                        return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             + OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampUpState[p,sc,n,nr] - pEpsilon * OptModel.vRampDwState[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampUpState_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eRampUpState, doc='ramp up state  [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpState          ... ', len(getattr(OptModel, f'eRampUpState_{p}_{sc}_{st}')), ' rows')

    def eRampDwState(OptModel,n,nr):
        if mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and (p,nr) in mTEPES.pnr and mTEPES.pDuration[p,sc,n]():
            if pIndStableTimeDeadBand:
                if mTEPES.pRampDw[nr]:
                    if n == mTEPES.n.first():
                        return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                    else:
                        return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                else:
                    if n == mTEPES.n.first():
                        return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
                    else:
                        return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * (OptModel.vRampUpState[p,sc,n,nr] - OptModel.vStableState[p,sc,n,nr])
            else:
                if mTEPES.pRampDw[nr]:
                    if n == mTEPES.n.first():
                        return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
                    else:
                        return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pRampDw[nr]                  <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
                else:
                    if n == mTEPES.n.first():
                        return (max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPowerElec[p,sc,n,nr], 0.0) - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
                    else:
                        return (OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr]                             - OptModel.vOutput2ndBlock[p,sc,n,nr]) / mTEPES.pDuration[p,sc,n]() / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vRampDwState[p,sc,n,nr] - pEpsilon * OptModel.vRampUpState[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eRampDwState_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eRampDwState, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwState          ... ', len(getattr(OptModel, f'eRampDwState_{p}_{sc}_{st}')), ' rows')

    def eMinUpTime(OptModel,n,t):
        if (p,t) in mTEPES.pg:
            if mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPowerElec[p,sc,n,t] or mTEPES.pConstantVarCost[p,sc,n,t]) and t not in mTEPES.eh and mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
                return sum(OptModel.vStartUp [p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)+1-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[p,sc,n,t]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinUpTime_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinUpTime            ... ', len(getattr(OptModel, f'eMinUpTime_{p}_{sc}_{st}')), ' rows')

    def eMinDownTime(OptModel,n,t):
        if (p,t) in mTEPES.pg:
            if mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPowerElec[p,sc,n,t] or mTEPES.pConstantVarCost[p,sc,n,t]) and t not in mTEPES.eh and mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
                return sum(OptModel.vShutDown[p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)+1-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[p,sc,n,t]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinDownTime_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinDownTime          ... ', len(getattr(OptModel, f'eMinDownTime_{p}_{sc}_{st}')), ' rows')

    if pIndSimplexFormulation:
        def eMinStableTime(OptModel,n,nr):
            if (mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.n.ord(n) >= mTEPES.pStableTime[nr] + 2):
                return OptModel.vRampUpState[p,sc,n,nr] + sum(OptModel.vRampDwState[p,sc,n2,nr] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStableTime[nr]-1:mTEPES.n.ord(n)-1]) <= 1
            else:
                return Constraint.Skip
        setattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nr, rule=eMinStableTime, doc='minimum stable time [p.u.]'))
    else:
        MinStableTimeLoadLevels = []
        if sum(mTEPES.pStableTime[nr] for nr in mTEPES.nr):
            for n in mTEPES.n:
                for nr in mTEPES.nr:
                    if (mTEPES.pStableTime[nr] and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.n.ord(n) >= mTEPES.pStableTime[nr] + 2):
                        for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pStableTime[nr]-1:mTEPES.n.ord(n)-1]:
                            MinStableTimeLoadLevels.append((n,n2,nr))

        def eMinStableTime(OptModel,n,n2,nr):
            return OptModel.vRampUpState[p,sc,n,nr] + OptModel.vRampDwState[p,sc,n2,nr] <= 1
        setattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}', Constraint(MinStableTimeLoadLevels, rule=eMinStableTime, doc='minimum stable time [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinStableTime        ... ', len(getattr(OptModel, f'eMinStableTime_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating ramps & minimum time        ... ', round(GeneratingTime), 's')


def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    switching model constraints ****')

    StartTime = time.time()

    def eLineStateCand(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] <= OptModel.vNetworkInvest[p,ni,nf,cc]
            else:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] == OptModel.vNetworkInvest[p,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eLineStateCand_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole == 1:
        print('eLineStateCand        ... ', len(getattr(OptModel, f'eLineStateCand_{p}_{sc}_{st}')), ' rows')

    def eSWOnOff(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1):
                if n == mTEPES.n.first():
                    return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - mTEPES.pInitialSwitch[p,sc,n,ni,nf,cc]()             == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
                else:
                    return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - OptModel.vLineCommit[p,sc,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eSWOnOff_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole == 1:
        print('eSWOnOff              ... ', len(getattr(OptModel, f'eSWOnOff_{p}_{sc}_{st}')), ' rows')

    def eMinSwOnState(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
                return sum(OptModel.vLineOnState [p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinSwOnState_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOnState         ... ', len(getattr(OptModel, f'eMinSwOnState_{p}_{sc}_{st}')), ' rows')

    def eMinSwOffState(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
                return sum(OptModel.vLineOffState[p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, f'eMinSwOffState_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOffState        ... ', len(getattr(OptModel, f'eMinSwOffState_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Switching minimum on/off state         ... ', round(GeneratingTime), 's')


def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    operation model constraints ****')

    StartTime = time.time()

    def eNetCapacity1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] >= - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eNetCapacity1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eNetCapacity1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity1         ... ', len(getattr(OptModel, f'eNetCapacity1_{p}_{sc}_{st}')), ' rows')

    def eNetCapacity2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pMaxNTCMax[p,sc,n,ni,nf,cc] <=   OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eNetCapacity2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eNetCapacity2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity2         ... ', len(getattr(OptModel, f'eNetCapacity2_{p}_{sc}_{st}')), ' rows')

    def eKirchhoff2ndLaw1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pLineX[ni,nf,cc] and mTEPES.pIndPTDF == 0 and mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] + mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]:
            if (ni,nf,cc) in mTEPES.lca:
                return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc]() * mTEPES.pSBase ==   0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw1, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw1     ... ', len(getattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}')), ' rows')

    def eKirchhoff2ndLaw2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pLineX[ni,nf,cc] and mTEPES.pIndPTDF == 0 and mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc] + mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc]:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc]() - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc]() * mTEPES.pSBase <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLaw2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw2     ... ', len(getattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}')), ' rows')

    def eLineLosses1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses() and mTEPES.ll and mTEPES.pIndPTDF == 0:
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlowElec[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eLineLosses1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses1          ... ', len(getattr(OptModel, f'eLineLosses1_{p}_{sc}_{st}')), ' rows')

    def eLineLosses2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses() and mTEPES.ll and mTEPES.pIndPTDF == 0:
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlowElec[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eLineLosses2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses2          ... ', len(getattr(OptModel, f'eLineLosses2_{p}_{sc}_{st}')), ' rows')

    # nodes to generators (g2n)
    g2n = defaultdict(list)
    for nd,g in mTEPES.n2g:
        g2n[nd].append(g)
    e2n = defaultdict(list)
    for nd,eh in mTEPES.nd*mTEPES.eh:
        if (nd,eh) in mTEPES.n2g:
            e2n[nd].append(eh)

    def eNetPosition(OptModel,n,nd):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndPTDF == 1:
            """Net position NP_n = Σ P_g in node n − demand"""
            return (OptModel.vNetPosition[p,sc,n,nd] == sum(OptModel.vTotalOutput[p,sc,n,g] for g in g2n[nd] if (p,g) in mTEPES.pg) - sum(OptModel.vESSTotalCharge[p,sc,n,eh] for eh in e2n[nd] if (p,eh) in mTEPES.peh) + OptModel.vENS[p,sc,n,nd] - mTEPES.pDemandElec[p,sc,n,nd])
        else:
            return Constraint.Skip
    setattr(OptModel, f'eNetPosition_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nd, rule=eNetPosition, doc='net position [GW]'))

    def eFlowBasedCalcu1(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pIndPTDF == 1 and mTEPES.pIndBinLinePTDF[ni,nf,cc] == 1:
            if (ni,nf,cc) in mTEPES.lca:
                return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - sum(mTEPES.pPTDF[p,sc,n,ni,nf,cc,nd] * OptModel.vNetPosition[p,sc,n,nd] for nd in mTEPES.nd if (p,sc,n,ni,nf,cc,nd) in mTEPES.psnland) >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - sum(mTEPES.pPTDF[p,sc,n,ni,nf,cc,nd] * OptModel.vNetPosition[p,sc,n,nd] for nd in mTEPES.nd if (p,sc,n,ni,nf,cc,nd) in mTEPES.psnland) ==   0
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowBasedCalcu1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.la, rule=eFlowBasedCalcu1, doc='flow based calculation [p.u.]'))

    if pIndLogConsole == 1:
        print('eFlowBasedCalcu1      ... ', len(getattr(OptModel, f'eFlowBasedCalcu1_{p}_{sc}_{st}')), ' rows')

    def eFlowBasedCalcu2(OptModel,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pIndPTDF == 1 and mTEPES.pIndBinLinePTDF[ni,nf,cc] == 1:
            return OptModel.vFlowElec[p,sc,n,ni,nf,cc] - sum(mTEPES.pPTDF[p,sc,n,ni,nf,cc,nd] * OptModel.vNetPosition[p,sc,n,nd] for nd in mTEPES.nd if (p,sc,n,ni,nf,cc,nd) in mTEPES.psnland) <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowBasedCalcu2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lca, rule=eFlowBasedCalcu2, doc='flow based calculation [p.u.]'))

    if pIndLogConsole == 1:
        print('eFlowBasedCalcu2      ... ', len(getattr(OptModel, f'eFlowBasedCalcu2_{p}_{sc}_{st}')), ' rows')

    # def eSecurityMargingTTCFrw(OptModel,n,ni,nf,cc):
    #     if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pIndBinLinePTDF[ni,nf,cc] == 1 and mTEPES.pIndPTDF == 1:
    #         return OptModel.vFlowElec[p,sc,n,ni,nf,cc] <=   mTEPES.pVariableTTCFrw[p,sc,n,ni,nf,cc]
    #     else:
    #         return Constraint.Skip
    # setattr(OptModel, f'eSecurityMargingTTCFrw_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lca, rule=eSecurityMargingTTCFrw, doc='security margin TTC for flow based calculation [p.u.]'))
    #
    # if pIndLogConsole == 1:
    #     print('eSecurityMargingTTCFrw... ', len(getattr(OptModel, f'eSecurityMargingTTCFrw_{p}_{sc}_{st}')), ' rows')
    #
    # def eSecurityMargingTTCBck(OptModel,n,ni,nf,cc):
    #     if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pElecNetPeriodIni[ni,nf,cc] <= p and mTEPES.pElecNetPeriodFin[ni,nf,cc] >= p and mTEPES.pIndBinLinePTDF[ni,nf,cc] == 1 and mTEPES.pIndPTDF == 1:
    #         return OptModel.vFlowElec[p,sc,n,ni,nf,cc] >= - mTEPES.pVariableTTCBck[p,sc,n,ni,nf,cc]
    #     else:
    #         return Constraint.Skip
    # setattr(OptModel, f'eSecurityMargingTTCBck_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lca, rule=eSecurityMargingTTCBck, doc='security margin TTC for flow based calculation [p.u.]'))
    #
    # if pIndLogConsole == 1:
    #     print('eSecurityMargingTTCBck... ', len(getattr(OptModel, f'eSecurityMargingTTCBck_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating network    constraints      ... ', round(GeneratingTime), 's')

def NetworkCycles(mTEPES, pIndLogConsole):
    print('Network               Cycles Detection ****')

    StartTime = time.time()

    NetworkGraph = nx.Graph()
    NetworkGraph.add_nodes_from(mTEPES.nd)
    NetworkGraph.add_edges_from((ni,nf) for ni,nf,cc in mTEPES.lea)

    # cycles for AC existing lines and non-switchable lines
    # mTEPES.nce = nx.cycle_basis(NetworkGraph, list(mTEPES.rf)[0])
    mTEPES.nce = nx.cycle_basis(NetworkGraph)

    # determining the set of unique existing circuits (only one in case of several circuits in //) and the parallel circuits
    pUniqueCircuits = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.lea, names=('NodeI', 'NodeF', 'Circuit')), columns=['0/1'        ])
    pNoCircuits     = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.br , names=('NodeI', 'NodeF'           )), columns=['No.Circuits'])
    for ni,nf,cc in mTEPES.lea:
        pNoCircuits.loc[ni,nf] += 1
        if pNoCircuits.loc[ni,nf]['No.Circuits'] <= 1:
            pUniqueCircuits.at[(ni,nf,cc),'0/1'] = 1
    pNoCircuits     = pNoCircuits.replace(1,0)
    pNoCircuits     = pNoCircuits[pNoCircuits['No.Circuits'] >  0]
    pUniqueCircuits = pUniqueCircuits[pUniqueCircuits['0/1'] == 1]

    # unique and parallel circuits of existing lines
    mTEPES.ucte = Set(doc='unique   circuits', initialize=[lea for lea in mTEPES.lea if lea in pUniqueCircuits['0/1'    ]])
    mTEPES.pct  = Set(doc='parallel circuits', initialize=[br  for br  in mTEPES.br  if br  in pNoCircuits['No.Circuits']])
    mTEPES.cye  = RangeSet(0,len(mTEPES.nce)-1)

    # graph with all AC existing and candidate lines
    NetworkGraph.add_edges_from((ni,nf) for ni,nf,cc in mTEPES.laa)

    # cycles with AC existing and candidate lines
    mTEPES.ncc = nx.cycle_basis(NetworkGraph, list(mTEPES.rf)[0])

    # cycles added due to consider candidate lines
    mTEPES.ncd = [nc for nc in mTEPES.ncc if nc not in mTEPES.nce]

    # determining the set of unique existing and candidate circuits (only one in case of several circuits in //) and the parallel circuits
    pUniqueCircuits = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.laa, names=('NodeI', 'NodeF', 'Circuit')), columns=['0/1'        ])
    pNoCircuits     = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.br , names=('NodeI', 'NodeF'           )), columns=['No.Circuits'])
    for ni,nf,cc in mTEPES.laa:
        pNoCircuits.loc[ni,nf] += 1
        if pNoCircuits.loc[ni,nf]['No.Circuits'] <= 1:
            pUniqueCircuits.at[(ni,nf,cc),'0/1'] = 1
    pNoCircuits     = pNoCircuits.replace(1,0)
    pNoCircuits     = pNoCircuits[pNoCircuits['No.Circuits'] >  0]
    pUniqueCircuits = pUniqueCircuits[pUniqueCircuits['0/1'] == 1]

    # unique and parallel circuits of candidate lines
    mTEPES.uctc = Set(doc='unique   circuits', initialize=[laa for laa in mTEPES.laa if laa in pUniqueCircuits['0/1']])
    mTEPES.cyc  = RangeSet(0,len(mTEPES.ncd)-1)
    # candidate lines included in every cycle
    mTEPES.lcac = Set(doc='AC candidate circuits in a cycle', initialize=[(cyc,ni,nf,cc) for cyc,ni,nf,cc in mTEPES.cyc*mTEPES.lca if (ni,nf) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) or (nf,ni) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1]))])

    pBigMTheta = pd.DataFrame(0, index=pd.MultiIndex.from_tuples(mTEPES.cyc*mTEPES.lca, names=('No.Cycle', 'NodeI', 'NodeF', 'Circuit')), columns=['rad'])
    # for cyc,nii,nff,ccc in mTEPES.cyc*mTEPES.lca:
    #     if (nii,nff) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) or (nff,nii) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])):
    #         pBigMTheta.loc[cyc,nii,nff,ccc] = (sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) +
    #                                            sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) )
    for cyc,nii,nff,ccc in mTEPES.cyc*mTEPES.lca:
        if (nii,nff) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) or (nff,nii) in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])):
            pBigMTheta.loc[cyc,nii,nff,ccc] = (sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc and (ni!=nii or nf!=nff)) +
                                               sum(max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc and (ni!=nii or nf!=nff)) )

    mTEPES.pBigMTheta = Param(mTEPES.cyc, mTEPES.lca, initialize=pBigMTheta['rad'].to_dict(), doc='big M for an AC candidate line in a cycle [rad]')

    CyclesDetectionTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Cycles detection                      ... ', round(CyclesDetectionTime), 's')

def CycleConstraints(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network              cycle constraints ****')

    StartTime = time.time()

    # remove the Kirchhoff's second law for AC existing and candidate lines
    OptModel.del_component(getattr(OptModel, f'eKirchhoff2ndLaw1_{p}_{sc}_{st}'))
    OptModel.del_component(getattr(OptModel, f'eKirchhoff2ndLaw2_{p}_{sc}_{st}'))

    #%% cycle Kirchhoff's second law with some candidate lines
    # this equation is formulated for every AC candidate line included in the cycle
    def eCycleKirchhoff2ndLawCnd1(OptModel,p,sc,n,cyc,nii,nff,cc):
        if mTEPES.pIndPTDF == 0:
            return (sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) -
                    sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) ) / mTEPES.pBigMTheta[cyc,nii,nff,cc] <=   1 - OptModel.vLineCommit[p,sc,n,nii,nff,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eCycleKirchhoff2ndLawCnd1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lcac, rule=eCycleKirchhoff2ndLawCnd1, doc='cycle flow for with some AC candidate lines [rad]'))

    if pIndLogConsole == 1:
        print('eCycleKirchhoff2ndLC1 ... ', len(getattr(OptModel, f'eCycleKirchhoff2ndLawCnd1_{p}_{sc}_{st}')), ' rows')

    def eCycleKirchhoff2ndLawCnd2(OptModel,p,sc,n,cyc,nii,nff,cc):
        if mTEPES.pIndPTDF == 0:
            return (sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for ni,nf in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) -
                    sum(OptModel.vFlowElec[p,sc,n,ni,nf,cc] * mTEPES.pLineX[ni,nf,cc] / mTEPES.pSBase for nf,ni in list(zip(mTEPES.ncd[cyc], mTEPES.ncd[cyc][1:] + mTEPES.ncd[cyc][:1])) for cc in mTEPES.cc if (ni,nf,cc) in mTEPES.uctc) ) / mTEPES.pBigMTheta[cyc,nii,nff,cc] >= - 1 + OptModel.vLineCommit[p,sc,n,nii,nff,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eCycleKirchhoff2ndLawCnd2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.lcac, rule=eCycleKirchhoff2ndLawCnd2, doc='cycle flow for with some AC candidate lines [rad]'))

    if pIndLogConsole == 1:
        print('eCycleKirchhoff2ndLC2 ... ', len(getattr(OptModel, f'eCycleKirchhoff2ndLawCnd2_{p}_{sc}_{st}')), ' rows')

    def eFlowParallelCandidate1(OptModel,p,sc,n,ni,nf,cc,c2):
        if (cc < c2 and (ni,nf,cc) in mTEPES.lea and (ni,nf,c2) in mTEPES.lca) and mTEPES.pIndPTDF == 0:
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] - OptModel.vFlowElec[p,sc,n,ni,nf,c2] * mTEPES.pLineX[ni,nf,c2] / mTEPES.pLineX[ni,nf,cc]) / max(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc],mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]) <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,c2]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowParallelCandidate1_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.pct, mTEPES.cc, mTEPES.c2, rule=eFlowParallelCandidate1, doc='unitary flow for each AC candidate parallel circuit [p.u.]'))

    if pIndLogConsole == 1:
        print('eFlowParallelCnddate1 ... ', len(getattr(OptModel, f'eFlowParallelCandidate1_{p}_{sc}_{st}')), ' rows')

    def eFlowParallelCandidate2(OptModel,p,sc,n,ni,nf,cc,c2):
        if (cc < c2 and (ni,nf,cc) in mTEPES.lea and (ni,nf,c2) in mTEPES.lca) and mTEPES.pIndPTDF == 0:
            return (OptModel.vFlowElec[p,sc,n,ni,nf,cc] - OptModel.vFlowElec[p,sc,n,ni,nf,c2] * mTEPES.pLineX[ni,nf,c2] / mTEPES.pLineX[ni,nf,cc]) / max(mTEPES.pMaxNTCBck[p,sc,n,ni,nf,cc],mTEPES.pMaxNTCFrw[p,sc,n,ni,nf,cc]) >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,c2]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eFlowParallelCandidate2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.pct, mTEPES.cc, mTEPES.c2, rule=eFlowParallelCandidate2, doc='unitary flow for each AC candidate parallel circuit [p.u.]'))

    if pIndLogConsole == 1:
        print('eFlowParallelCnddate2 ... ', len(getattr(OptModel, f'eFlowParallelCandidate2_{p}_{sc}_{st}')), ' rows')

    CycleFlowTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating cycle flow constraints       ... ', round(CycleFlowTime), 's')

def NetworkH2OperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Hydrogen  scheduling       constraints ****')

    StartTime = time.time()

    # incoming and outgoing pipelines (lin) (lout)
    lin  = defaultdict(list)
    lout = defaultdict(list)
    for ni,nf,cc in mTEPES.pa:
        lin [nf].append((ni,cc))
        lout[ni].append((nf,cc))

    # nodes to electrolyzers (e2n)
    e2n = defaultdict(list)
    for nd,el in mTEPES.nd*mTEPES.el:
        if (nd,el) in mTEPES.n2g:
            e2n[nd].append(el)

    # nodes to fuel heater using H2 (b2n)
    b2n = defaultdict(list)
    for nd,hh in mTEPES.nd*mTEPES.hh:
        if (nd,hh) in mTEPES.n2g:
            b2n[nd].append(hh)

    def eBalanceH2(OptModel,n,nd):
        if sum(1 for el in e2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vESSTotalCharge[p,sc,n,el]*mTEPES.pDuration[p,sc,n]()/mTEPES.pProductionFunctionH2[el] for el in e2n[nd]) - sum(OptModel.vTotalOutputHeat[p,sc,n,hh]*mTEPES.pDuration[p,sc,n]()*mTEPES.pProductionFunctionH2ToHeat[hh] for hh in b2n[nd] if (p,hh) in mTEPES.phh and hh in mTEPES.hh) + OptModel.vH2NS[p,sc,n,nd] -
                    sum(OptModel.vFlowH2[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.ppa) + sum(OptModel.vFlowH2[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.ppa)) == mTEPES.pDemandH2[p,sc,n,nd]*mTEPES.pDuration[p,sc,n]()
        else:
            return Constraint.Skip
    setattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nd, rule=eBalanceH2, doc='H2 load generation balance [tH2]'))

    if pIndLogConsole == 1:
        print('eBalanceH2            ... ', len(getattr(OptModel, f'eBalanceH2_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating hydrogen  operation         ... ', round(GeneratingTime), 's')


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
    setattr(OptModel, f'eEnergy2Heat_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.chp, rule=eEnergy2Heat, doc='Energy to heat conversion [GW]'))

    if pIndLogConsole == 1:
        print('eEnergy2Heat          ... ', len(getattr(OptModel, f'eEnergy2Heat_{p}_{sc}_{st}')), ' rows')

    def eBalanceHeat(OptModel,n,nd):
        if sum(1 for ch in chp2n[nd]) + sum(1 for nf,cc in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutputHeat[p,sc,n,chp] for chp in chp2n[nd] if (p,chp) in mTEPES.pchp) + OptModel.vHeatNS[p,sc,n,nd] -
                    sum(OptModel.vFlowHeat[p,sc,n,nd,nf,cc] for nf,cc in lout[nd] if (p,nd,nf,cc) in mTEPES.pha) + sum(OptModel.vFlowHeat[p,sc,n,ni,nd,cc] for ni,cc in lin[nd] if (p,ni,nd,cc) in mTEPES.pha)) == mTEPES.pDemandHeat[p,sc,n,nd]
        else:
            return Constraint.Skip
    setattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}', Constraint(mTEPES.n, mTEPES.nd, rule=eBalanceHeat, doc='Heat load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalanceHeat          ... ', len(getattr(OptModel, f'eBalanceHeat_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating heat      operation         ... ', round(GeneratingTime), 's')
