"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - December 27, 2023
"""

import time
import math
from   collections   import defaultdict
from   pyomo.environ import Constraint, Objective, minimize


def TotalObjectiveFunction(OptModel, mTEPES, pIndLogConsole):
    print('Total cost o.f.      model formulation ****')

    StartTime = time.time()

    def eTotalSCost(OptModel):
        return OptModel.vTotalSCost
    OptModel.eTotalSCost = Objective(rule=eTotalSCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalTCost(OptModel):
        return OptModel.vTotalSCost == OptModel.vTotalICost + sum(mTEPES.pDiscountedWeight[p] * mTEPES.pScenProb[p,sc] * (OptModel.vTotalGCost[p,sc,n] + OptModel.vTotalCCost[p,sc,n] + OptModel.vTotalECost[p,sc,n] + OptModel.vTotalRCost[p,sc,n]) for p,sc,n in mTEPES.psn)
    OptModel.eTotalTCost = Constraint(rule=eTotalTCost, doc='total system cost [MEUR]')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Total fixed and variable costs         ... ', round(GeneratingTime), 's')


def InvestmentModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment           model formulation ****')

    StartTime = time.time()

    def eTotalICost(OptModel):
        if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc):
            return OptModel.vTotalICost == sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFCost[p] for p in mTEPES.p)
        else:
            return Constraint.Skip
    OptModel.eTotalICost = Constraint(rule=eTotalICost, doc='system fixed    cost [MEUR]')

    def eTotalFCost(OptModel,p):
        if   len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc)                                   and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc)
        if   len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc)                  + len(mTEPES.pc) and mTEPES.pIndHydroTopology == 0 and mTEPES.pIndHydrogen == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc) + sum(mTEPES.pPipeFixedCost[ni,nf,cc] * OptModel.vPipelineInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc)
        elif len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn)                  and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 0:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc) +                                                                                                         sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn)
        elif len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc) and mTEPES.pIndHydroTopology == 1 and mTEPES.pIndHydrogen == 1:
            return OptModel.vTotalFCost[p] == sum(mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for gc in mTEPES.gc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for gd in mTEPES.gd) + sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc) + sum(mTEPES.pPipeFixedCost[ni,nf,cc] * OptModel.vPipelineInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc) + sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn)
        else:
            return Constraint.Skip
    OptModel.eTotalFCost = Constraint(mTEPES.p, rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    def eConsecutiveGenInvest(OptModel,p,gc):
        if p != mTEPES.p.first():
            return OptModel.vGenerationInvest[mTEPES.p.prev(p,1),gc      ] + OptModel.vGenerationInvPer[p,gc      ] == OptModel.vGenerationInvest[p,gc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenInvest = Constraint(mTEPES.p, mTEPES.gc, rule=eConsecutiveGenInvest, doc='generation investment in consecutive periods')

    def eConsecutiveGenRetire(OptModel,p,gd):
        if p != mTEPES.p.first():
            return OptModel.vGenerationRetire[mTEPES.p.prev(p,1),gd      ] + OptModel.vGenerationRetPer[p,gd      ] == OptModel.vGenerationRetire[p,gd      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenRetire = Constraint(mTEPES.p, mTEPES.gd, rule=eConsecutiveGenRetire, doc='generation retirement in consecutive periods')

    def eConsecutiveRsrInvest(OptModel,p,rc):
        if p != mTEPES.p.first():
            return OptModel.vReservoirInvest [mTEPES.p.prev(p,1),rc      ] + OptModel.vReservoirInvPer [p,rc      ] == OptModel.vReservoirInvest [p,rc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveRsrInvest = Constraint(mTEPES.p, mTEPES.rn, rule=eConsecutiveRsrInvest, doc='reservoir investment in consecutive periods')

    def eConsecutiveNetInvest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first():
            return OptModel.vNetworkInvest   [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vNetworkInvPer   [p,ni,nf,cc] == OptModel.vNetworkInvest   [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNetInvest = Constraint(mTEPES.p, mTEPES.lc, rule=eConsecutiveNetInvest, doc='electric network investment in consecutive periods')

    def eConsecutiveNet2Invest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first():
            return OptModel.vPipelineInvest  [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vPipelineInvPer  [p,ni,nf,cc] == OptModel.vPipelineInvest  [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNet2Invest = Constraint(mTEPES.p, mTEPES.pc, rule=eConsecutiveNet2Invest, doc='pipeline network investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Gen&transm investment o.f./constraints ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationObjFunct(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Generation oper model formulation o.f. ****')

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

    def eTotalGCost(OptModel,n):
        if (st,n) in mTEPES.s2n:
            return OptModel.vTotalGCost[p,sc,n] == (sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pLinearVarCost  [p,sc,n,nr] * OptModel.vTotalOutput   [p,sc,n,nr]                      +
                                                        mTEPES.pLoadLevelDuration[n] * mTEPES.pConstantVarCost[p,sc,n,nr] * OptModel.vCommitment    [p,sc,n,nr]                      +
                                                        mTEPES.pLoadLevelDuration[n] * mTEPES.pStartUpCost    [       nr] * OptModel.vStartUp       [p,sc,n,nr]                      +
                                                        mTEPES.pLoadLevelDuration[n] * mTEPES.pShutDownCost   [       nr] * OptModel.vShutDown      [p,sc,n,nr] for nr in mTEPES.nr) +
                                                    sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveUp     [p,sc,n,nr]                      +
                                                        mTEPES.pLoadLevelDuration[n] * mTEPES.pOperReserveCost[       nr] * OptModel.vReserveDown   [p,sc,n,nr] for nr in mTEPES.nr if mTEPES.pIndOperReserve[nr] == 0) +
                                                    sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pOperReserveCost[       es] * OptModel.vESSReserveUp  [p,sc,n,es]                      +
                                                        mTEPES.pLoadLevelDuration[n] * mTEPES.pOperReserveCost[       es] * OptModel.vESSReserveDown[p,sc,n,es] for es in mTEPES.es if mTEPES.pIndOperReserve[es] == 0) +
                                                    sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pLinearOMCost   [       re] * OptModel.vTotalOutput   [p,sc,n,re] for re in mTEPES.re) )
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalGCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    def eTotalCCost(OptModel,n):
        if (st,n) in mTEPES.s2n:
            return OptModel.vTotalCCost    [p,sc,n] == sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pLinearVarCost[p,sc,n,es] * OptModel.vESSTotalCharge[p,sc,n,es] for es in mTEPES.es)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalCCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,n):
        if (st,n) in mTEPES.s2n and sum(mTEPES.pEmissionVarCost[p,sc,n,nr] for nr in mTEPES.nr):
            return OptModel.vTotalECost[p,sc,n] == sum(OptModel.vTotalECostArea[p,sc,n,ar] for ar in mTEPES.ar)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalECost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalECostArea(OptModel,n,ar):
        if (st,n) in mTEPES.s2n and sum(mTEPES.pEmissionVarCost[p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g):
            return OptModel.vTotalECostArea[p,sc,n,ar] == sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pEmissionVarCost[p,sc,n,nr] * OptModel.vTotalOutput[p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalECostArea_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ar, rule=eTotalECostArea, doc='area emission cost [MEUR]'))

    def eTotalRCost(OptModel,n):
        if (st,n) in mTEPES.s2n:
            return OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelDuration[n] * mTEPES.pENSCost * OptModel.vENS[p,sc,n,nd] for nd in mTEPES.nd) + sum(mTEPES.pHNSCost * OptModel.vHNS[p,sc,n,nd] for nd in mTEPES.nd if sum(1 for el in e2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]))
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalRCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating operation  o.f.             ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationInvestment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Investment & operation var constraints ****')

    StartTime = time.time()

    def eInstalGenComm(OptModel,n,gc):
        if (st,n) in mTEPES.s2n and gc in mTEPES.nr and gc not in mTEPES.es and mTEPES.pMustRun[gc] == 0 and (mTEPES.pMinPower[p,sc,n,gc] > 0.0 or mTEPES.pConstantVarCost[p,sc,n,gc] > 0.0):
            return OptModel.vCommitment[p,sc,n,gc]                                 <= OptModel.vGenerationInvest[p,gc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment if installed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenComm        ... ', len(getattr(OptModel, 'eInstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInstalESSComm(OptModel,n,ec):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinStorInvest[ec]:
            return OptModel.vCommitment[p,sc,n,ec]                                 <= OptModel.vGenerationInvest[p,ec]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalESSComm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ec, rule=eInstalESSComm, doc='commitment if ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalESSComm        ... ', len(getattr(OptModel, 'eInstalESSComm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInstalGenCap(OptModel,n,gc):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxPower[p,sc,n,gc]:
            return OptModel.vTotalOutput   [p,sc,n,gc] / mTEPES.pMaxPower [p,sc,n,gc] <= OptModel.vGenerationInvest[p,gc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output if installed gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenCap         ... ', len(getattr(OptModel, 'eInstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInstalConESS(OptModel,n,ec):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxCharge[p,sc,n,ec]:
            return OptModel.vESSTotalCharge[p,sc,n,ec] / mTEPES.pMaxCharge[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalConESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalConESS         ... ', len(getattr(OptModel, 'eInstalConESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUninstalGenComm(OptModel,n,gd):
        if (st,n) in mTEPES.s2n and gd in mTEPES.nr and gd not in mTEPES.es and mTEPES.pMustRun[gd] == 0 and (mTEPES.pMinPower[p,sc,n,gd] > 0.0 or mTEPES.pConstantVarCost[p,sc,n,gd] > 0.0):
            return OptModel.vCommitment[p,sc,n,gd]                                <= 1 - OptModel.vGenerationRetire[p,gd]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUninstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.gd, rule=eUninstalGenComm, doc='commitment if uninstalled unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstalGenComm      ... ', len(getattr(OptModel, 'eUninstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUninstalGenCap(OptModel,n,gd):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxPower[p,sc,n,gd]:
            return OptModel.vTotalOutput[p,sc,n,gd] / mTEPES.pMaxPower[p,sc,n,gd] <= 1 - OptModel.vGenerationRetire[p,gd]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUninstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.gd, rule=eUninstalGenCap, doc='output if uninstalled gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstalGenCap       ... ', len(getattr(OptModel, 'eUninstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eAdequacyReserveMargin(OptModel,p,ar):
        if mTEPES.pReserveMargin[p,ar] and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g) and sum(mTEPES.pRatedMaxPower[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]) for g in mTEPES.g if (ar,g) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pPeakDemand[p,ar] * mTEPES.pReserveMargin[p,ar]:
            return ((sum(                                       mTEPES.pRatedMaxPower[g ] * mTEPES.pAvailability[g ]() / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if (ar,g ) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) +
                     sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPower[gc] * mTEPES.pAvailability[gc]() / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g                                      ) +
                     sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPower[gd] * mTEPES.pAvailability[gd]() / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if (ar,gd) in mTEPES.a2g                                      ) ) >= mTEPES.pPeakDemand[p,ar] * mTEPES.pReserveMargin[p,ar])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.ar, rule=eAdequacyReserveMargin, doc='system adequacy reserve margin [p.u.]'))

    if pIndLogConsole == 1:
        print('eAdequacyReserveMargin... ', len(getattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxSystemEmission(OptModel,p,ar):
        if mTEPES.pEmission[p,ar] < math.inf and sum(mTEPES.pEmissionVarCost[p,sc,n,nr] for n,nr in mTEPES.nn*mTEPES.nr if (st,n) in mTEPES.s2n and (ar,nr) in mTEPES.a2g):
            return sum(OptModel.vTotalECostArea[p,sc,n,ar]/mTEPES.pCO2Cost for n in mTEPES.nn if (st,n) in mTEPES.s2n) <= mTEPES.pEmission[p,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxSystemEmission_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.ar, rule=eMaxSystemEmission, doc='maximum CO2 emission [tCO2]'))

    if pIndLogConsole == 1:
        print('eMaxSystemEmission    ... ', len(getattr(OptModel, 'eMaxSystemEmission_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

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
    for nd,g  in mTEPES.n2g:
        g2n[nd].append(g)
    e2n = defaultdict(list)
    for nd,es in mTEPES.nd*mTEPES.es:
        if (nd,es) in mTEPES.n2g:
            e2n[nd].append(es)

    # generators to area (e2a) (n2a) and area to generators (a2e) (a2n)
    e2a = defaultdict(list)
    a2e = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            e2a[ar].append(es)
            a2e[es].append(ar)
    n2a = defaultdict(list)
    a2n = defaultdict(list)
    for ar,nr in mTEPES.ar*mTEPES.nr:
        if (ar,nr) in mTEPES.a2g:
            n2a[ar].append(nr)
            a2n[nr].append(ar)

    def eSystemInertia(OptModel,n,ar):
        if (st,n) in mTEPES.s2n and mTEPES.pSystemInertia[p,sc,n,ar] and sum(1 for nr in n2a[ar]):
            return sum(OptModel.vTotalOutput[p,sc,n,nr] * mTEPES.pInertia[nr] / mTEPES.pMaxPower[p,sc,n,nr] for nr in mTEPES.nr if mTEPES.pMaxPower[p,sc,n,nr] and (ar,nr) in mTEPES.a2g) >= mTEPES.pSystemInertia[p,sc,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSystemInertia_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ar, rule=eSystemInertia, doc='system inertia [s]'))

    if pIndLogConsole == 1:
        print('eSystemInertia        ... ', len(getattr(OptModel, 'eSystemInertia_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eOperReserveUp(OptModel,n,ar):
        if (st,n) in mTEPES.s2n and mTEPES.pOperReserveUp[p,sc,n,ar]:
            if sum(1 for nr in n2a[ar] if mTEPES.pIndOperReserve[nr] == 0) + sum(1 for es in e2a[ar] if mTEPES.pIndOperReserve[es] == 0):
                return sum(OptModel.vReserveUp  [p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserve[nr] == 0) + sum(OptModel.vESSReserveUp  [p,sc,n,es] for es in e2a[ar] if mTEPES.pIndOperReserve[es] == 0) == mTEPES.pOperReserveUp[p,sc,n,ar]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveUp        ... ', len(getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eOperReserveDw(OptModel,n,ar):
        if (st,n) in mTEPES.s2n and mTEPES.pOperReserveDw[p,sc,n,ar]:
            if sum(1 for nr in n2a[ar] if mTEPES.pIndOperReserve[nr] == 0) + sum(1 for es in e2a[ar] if mTEPES.pIndOperReserve[es] == 0):
                return sum(OptModel.vReserveDown[p,sc,n,nr] for nr in n2a[ar] if mTEPES.pIndOperReserve[nr] == 0) + sum(OptModel.vESSReserveDown[p,sc,n,es] for es in e2a[ar] if mTEPES.pIndOperReserve[es] == 0) == mTEPES.pOperReserveDw[p,sc,n,ar]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveDw        ... ', len(getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveMinRatioDwUp(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pMinRatioDwUp       and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2n[nr]) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pIndOperReserve[nr] == 0:
            return OptModel.vReserveDown[p,sc,n,nr] >= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMinRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveMinRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eReserveMinRatioDwUp, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMinRatioDwUp  ... ', len(getattr(OptModel, 'eReserveMinRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveMaxRatioDwUp(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxRatioDwUp < 1.0 and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2n[nr]) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pIndOperReserve[nr] == 0:
            return OptModel.vReserveDown[p,sc,n,nr] <= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMaxRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveMaxRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eReserveMaxRatioDwUp, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMaxRatioDwUp  ... ', len(getattr(OptModel, 'eReserveMaxRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRsrvMinRatioDwUpESS(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pMinRatioDwUp > 0.0 and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return OptModel.vESSReserveDown[p,sc,n,es] >= OptModel.vESSReserveUp[p,sc,n,es] * mTEPES.pMinRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRsrvMinRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eRsrvMinRatioDwUpESS, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMinRatioDwUpESS  ... ', len(getattr(OptModel, 'eRsrvMinRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRsrvMaxRatioDwUpESS(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxRatioDwUp < 1.0 and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return OptModel.vESSReserveDown[p,sc,n,es] <= OptModel.vESSReserveUp[p,sc,n,es] * mTEPES.pMaxRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRsrvMaxRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eRsrvMaxRatioDwUpESS, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMaxRatioDwUpESS  ... ', len(getattr(OptModel, 'eRsrvMaxRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveUpIfEnergy(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[es] == 0:
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxPower2ndBlock [p,sc,n,es]:
                return OptModel.vReserveUp  [p,sc,n,es] <=                                  OptModel.vESSInventory[p,sc,n,es]  / mTEPES.pDuration[n]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nesc, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveUpIfEnergy    ... ', len(getattr(OptModel, 'eReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveDwIfEnergy(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[es] == 0:
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxPower2ndBlock [p,sc,n,es]:
                return OptModel.vReserveDown[p,sc,n,es] <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[n]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nesc, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveDwIfEnergy    ... ', len(getattr(OptModel, 'eReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSReserveUpIfEnergy(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[es] == 0:
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
                return OptModel.vESSReserveUp  [p,sc,n,es] <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[n]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nesc, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveUpIfEnergy ... ', len(getattr(OptModel, 'eESSReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSReserveDwIfEnergy(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[es] == 0:
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
                return OptModel.vESSReserveDown[p,sc,n,es] <=                                  OptModel.vESSInventory[p,sc,n,es]  / mTEPES.pDuration[n]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nesc, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveDwIfEnergy ... ', len(getattr(OptModel, 'eESSReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eBalance(OptModel,n,nd):
        if (st,n) in mTEPES.s2n and sum(1 for g in g2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutput[p,sc,n,g] for g in g2n[nd]) - sum(OptModel.vESSTotalCharge[p,sc,n,es] for es in e2n[nd]) + OptModel.vENS[p,sc,n,nd] -
                    sum(OptModel.vLineLosses[p,sc,n,nd,lout ] for lout  in loutl[nd]) - sum(OptModel.vFlow[p,sc,n,nd,lout ] for lout  in lout[nd]) -
                    sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc] for ni,cc in linl [nd]) + sum(OptModel.vFlow[p,sc,n,ni,nd,cc] for ni,cc in lin [nd])) == mTEPES.pDemand[p,sc,n,nd]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nd, rule=eBalance, doc='electric load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalance              ... ', len(getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating inertia/reserves/balance    ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationStorage(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Storage   scheduling       constraints ****')

    StartTime = time.time()

    # area to generators (a2e)
    a2e = defaultdict(list)
    for ar,es in mTEPES.ar*mTEPES.es:
        if (ar,es) in mTEPES.a2g:
            a2e[es].append(ar)

    def eMaxInventory2Comm(OptModel,n,ec):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinStorInvest[ec]:
            if mTEPES.pMaxCharge[p,sc,n,ec] + mTEPES.pMaxPower[p,sc,n,ec] and mTEPES.pMaxStorage[p,sc,n,ec]:
                return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMaxStorage[p,sc,n,ec] <= OptModel.vCommitment[p,sc,n,ec]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxInventory2Comm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.necc, rule=eMaxInventory2Comm, doc='ESS maximum inventory limited by commitment [GWh]'))

    if pIndLogConsole == 1:
        print('eMaxInventory2Comm    ... ', len(getattr(OptModel, 'eMaxInventory2Comm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinInventory2Comm(OptModel,n,ec):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinStorInvest[ec]:
            if mTEPES.pMaxCharge[p,sc,n,ec] + mTEPES.pMaxPower[p,sc,n,ec] and mTEPES.pMinStorage[p,sc,n,ec]:
                return OptModel.vESSInventory[p,sc,n,ec] / mTEPES.pMinStorage[p,sc,n,ec] >= OptModel.vCommitment[p,sc,n,ec]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinInventory2Comm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.necc, rule=eMinInventory2Comm, doc='ESS minimum inventory limited by commitment [GWh]'))

    if pIndLogConsole == 1:
        print('eMinInventory2Comm    ... ', len(getattr(OptModel, 'eMinInventory2Comm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInflows2Comm(OptModel,n,ec):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinStorInvest[ec]:
            if mTEPES.pMaxCharge[p,sc,n,ec] + mTEPES.pMaxPower[p,sc,n,ec] and mTEPES.pEnergyInflows[p,sc,n,ec]():
                return OptModel.vEnergyInflows[p,sc,n,ec] / mTEPES.pEnergyInflows[p,sc,n,ec] <= OptModel.vCommitment[p,sc,n,ec]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInflows2Comm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.necc, rule=eInflows2Comm, doc='ESS inflows limited by commitment [p.u.]'))

    if pIndLogConsole == 1:
        print('eInflows2Comm         ... ', len(getattr(OptModel, 'eInflows2Comm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSInventory(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxCharge[p,sc,n,es] + mTEPES.pMaxPower[p,sc,n,es]:
            if   mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
                if es not in mTEPES.ec:
                    return mTEPES.pIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
                else:
                    return mTEPES.pIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[n2]*(mTEPES.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            elif mTEPES.n.ord(n) >  mTEPES.pCycleTimeStep[es]:
                if es not in mTEPES.ec:
                    return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
                else:
                    return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.vEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSInventory_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nesc, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole == 1:
        print('eESSInventory         ... ', len(getattr(OptModel, 'eESSInventory_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxShiftTime(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pShiftTime[es]:
            return mTEPES.pDuration[n]*mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n,es] <= sum(mTEPES.pDuration[n2]*OptModel.vTotalOutput[p,sc,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n):mTEPES.n.ord(n)+mTEPES.pShiftTime[es]])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxShiftTime_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eMaxShiftTime, doc='Maximum shift time [GWh]'))

    if pIndLogConsole == 1:
        print('eMaxShiftTime         ... ', len(getattr(OptModel, 'eMaxShiftTime_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCharge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return (OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCharge            ... ', len(getattr(OptModel, 'eMaxCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinCharge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2e[es]) and mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return (OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinCharge            ... ', len(getattr(OptModel, 'eMinCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    # def eChargeDischarge(OptModel,n,es):
    #     if (st,n) in mTEPES.s2n and mTEPES.pMaxCharge[p,sc,n,es]:
    #         return OptModel.vTotalOutput[p,sc,n,es] / mTEPES.pMaxPower[p,sc,n,es] + OptModel.vCharge2ndBlock[p,sc,n,es] / mTEPES.pMaxCharge[p,sc,n,es] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxPower2ndBlock [p,sc,n,es] and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            return ((OptModel.vOutput2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [p,sc,n,es]) / mTEPES.pMaxPower2ndBlock [p,sc,n,es] +
                    (OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eChargeDischarge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeDischarge      ... ', len(getattr(OptModel, 'eChargeDischarge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSTotalCharge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            if mTEPES.pMinCharge[p,sc,n,es] == 0.0:
                return OptModel.vESSTotalCharge[p,sc,n,es]                                ==        OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[p,sc,n,es]
            else:
                return OptModel.vESSTotalCharge[p,sc,n,es] / mTEPES.pMinCharge[p,sc,n,es] == 1.0 + (OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[p,sc,n,es]) / mTEPES.pMinCharge[p,sc,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSTotalCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eESSTotalCharge       ... ', len(getattr(OptModel, 'eESSTotalCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eChargeOutflows(OptModel,n,es):
        if (st,n) in mTEPES.s2n and (p,sc,es) in mTEPES.eo:
            if mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
                return (OptModel.vEnergyOutflows[p,sc,n,es] + OptModel.vCharge2ndBlock[p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eChargeOutflows_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eChargeOutflows, doc='incompatibility between charge and outflows use [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeOutflows       ... ', len(getattr(OptModel, 'eChargeOutflows_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eEnergyOutflows(OptModel,n,es):
        if (st,n) in mTEPES.s2n and (p,sc,es) in mTEPES.eo:
            return sum((OptModel.vEnergyOutflows[p,sc,n2,es] - mTEPES.pEnergyOutflows[p,sc,n2,es])*mTEPES.pDuration[n2] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)]) == 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eEnergyOutflows_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.neso, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eEnergyOutflows       ... ', len(getattr(OptModel, 'eEnergyOutflows_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinimumEnergy(OptModel,n,g):
        if (st,n) in mTEPES.s2n and (p,sc,g) in mTEPES.gm:
            return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMinEnergy[p,sc,n2,g])*mTEPES.pDuration[n2] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinimumEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.ngen, rule=eMinimumEnergy, doc='minimum energy of a unit [GWh]'))

    if pIndLogConsole == 1:
        print('eMinimumEnergy        ... ', len(getattr(OptModel, 'eMinimumEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaximumEnergy(OptModel,n,g):
        if (st,n) in mTEPES.s2n and (p,sc,g) in mTEPES.gM:
            return sum((OptModel.vTotalOutput[p,sc,n2,g] - mTEPES.pMaxEnergy[p,sc,n2,g])*mTEPES.pDuration[n2] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pEnergyTimeStep[g]:mTEPES.n.ord(n)]) <= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaximumEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.ngen, rule=eMaximumEnergy, doc='maximum energy of a unit [GWh]'))

    if pIndLogConsole == 1:
        print('eMaximumEnergy        ... ', len(getattr(OptModel, 'eMaximumEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

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
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinRsrInvest[rc]:
            if sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPower[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) and mTEPES.pMaxVolume[p,sc,n,rc]:
                return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMaxVolume[p,sc,n,rc] <= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxVolume2Comm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nrcc, rule=eMaxVolume2Comm, doc='Reservoir maximum volume limited by commitment [hm3]'))

    if pIndLogConsole == 1:
        print('eMaxVolume2Comm       ... ', len(getattr(OptModel, 'eMaxVolume2Comm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinVolume2Comm(OptModel,n,rc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinRsrInvest[rc]:
            if sum(mTEPES.pMaxCharge[p,sc,n,h] + mTEPES.pMaxPower[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h) and mTEPES.pMinVolume[p,sc,n,rc]:
                return OptModel.vReservoirVolume[p,sc,n,rc] / mTEPES.pMinVolume[p,sc,n,rc] >= sum(OptModel.vCommitment[p,sc,n,h] for h in mTEPES.h if (rc,h) in mTEPES.r2h)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinVolume2Comm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nrcc, rule=eMinVolume2Comm, doc='Reservoir minimum volume limited by commitment [hm3]'))

    if pIndLogConsole == 1:
        print('eMinVolume2Comm       ... ', len(getattr(OptModel, 'eMinVolume2Comm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eTrbReserveUpIfEnergy(OptModel,n,h):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[h] == 0:
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2h[h]) and mTEPES.pMaxPower2ndBlock [p,sc,n,h]:
                return OptModel.vReserveUp     [p,sc,n,h] <=  sum(                               OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h)  / mTEPES.pDuration[n] * mTEPES.pProductionFunction[h]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTrbReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nhc, rule=eTrbReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eTrbReserveUpIfEnergy ... ', len(getattr(OptModel, 'eTrbReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eTrbReserveDwIfEnergy(OptModel,n,h):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[h] == 0:
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2h[h]) and mTEPES.pMaxPower2ndBlock [p,sc,n,h]:
                return OptModel.vReserveDown   [p,sc,n,h] <= (sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2h)) / mTEPES.pDuration[n] * mTEPES.pProductionFunction[h]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTrbReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nhc, rule=eTrbReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eTrbReserveDwIfEnergy ... ', len(getattr(OptModel, 'eTrbReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def ePmpReserveUpIfEnergy(OptModel,n,h):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[h] == 0 and sum(1 for rs in mTEPES.rs if (h,rs) in mTEPES.p2r):
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2h[h]) and mTEPES.pMaxCharge2ndBlock[p,sc,n,h]:
                return OptModel.vESSReserveUp  [p,sc,n,h] <= (sum(mTEPES.pMaxVolume[p,sc,n,rs] - OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (h,rs) in mTEPES.p2r)) / mTEPES.pDuration[n] * mTEPES.pProductionFunction[h]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'ePmpReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.np2c, rule=ePmpReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('ePmpReserveUpIfEnergy ... ', len(getattr(OptModel, 'ePmpReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def ePmpReserveDwIfEnergy(OptModel,n,h):
        if (st,n) in mTEPES.s2n and mTEPES.pIndOperReserve[h] == 0 and sum(1 for rs in mTEPES.rs if (rs,h) in mTEPES.r2p):
            if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2h[h]) and mTEPES.pMaxCharge2ndBlock[p,sc,n,h]:
                return OptModel.vESSReserveDown[p,sc,n,h] <=  sum(                               OptModel.vReservoirVolume[p,sc,n,rs] for rs in mTEPES.rs if (rs,h) in mTEPES.r2p)  / mTEPES.pDuration[n] * mTEPES.pProductionFunction[h]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'ePmpReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.npc, rule=ePmpReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('ePmpReserveDwIfEnergy ... ', len(getattr(OptModel, 'ePmpReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eHydroInventory(OptModel,n,rs):
        if (st,n) in mTEPES.s2n and sum(1 for h in mTEPES.h if (rs,h) in mTEPES.r2h or (h,rs) in mTEPES.h2r or (rs,h) in mTEPES.r2p or (h,rs) in mTEPES.p2r):
            if   mTEPES.n.ord(n) == mTEPES.pCycleWaterStep[rs]:
                if rs not in mTEPES.rn:
                    return (mTEPES.pIniVolume[p,sc,n,rs]                                                   + sum(mTEPES.pDuration[n2]*(mTEPES.pHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleWaterStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
                else:
                    return (mTEPES.pIniVolume[p,sc,n,rs]                                                   + sum(mTEPES.pDuration[n2]*(mTEPES.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleWaterStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            elif mTEPES.n.ord(n) >  mTEPES.pCycleWaterStep[rs]:
                if rs not in mTEPES.rn:
                    return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pCycleWaterStep[rs]),rs] + sum(mTEPES.pDuration[n2]*(mTEPES.pHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleWaterStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
                else:
                    return (OptModel.vReservoirVolume[p,sc,mTEPES.n.prev(n,mTEPES.pCycleWaterStep[rs]),rs] + sum(mTEPES.pDuration[n2]*(mTEPES.vHydroInflows[p,sc,n2,rs]*0.0036 - OptModel.vHydroOutflows[p,sc,n2,rs]*0.0036 - sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2h) + sum(OptModel.vTotalOutput[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.h2r) + sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (rs,h) in mTEPES.r2p) - sum(mTEPES.pEfficiency[h]*OptModel.vESSTotalCharge[p,sc,n2,h]/mTEPES.pProductionFunction[h] for h in mTEPES.h if (h,rs) in mTEPES.p2r)) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleWaterStep[rs]:mTEPES.n.ord(n)]) == OptModel.vReservoirVolume[p,sc,n,rs] + OptModel.vReservoirSpillage[p,sc,n,rs] - sum(OptModel.vReservoirSpillage[p,sc,n,rsr] for rsr in mTEPES.rs if (rsr,rs) in mTEPES.r2r))
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eHydroInventory_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nrsc, rule=eHydroInventory, doc='Reservoir water inventory [hm3]'))

    if pIndLogConsole == 1:
        print('eHydroInventory       ... ', len(getattr(OptModel, 'eHydroInventory_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eHydroOutflows(OptModel,n,rs):
        if (st,n) in mTEPES.s2n and (p,sc,rs) in mTEPES.ro:
            return sum((OptModel.vHydroOutflows[p,sc,n2,rs] - mTEPES.pHydroOutflows[p,sc,n2,rs])*mTEPES.pDuration[n2] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pWaterOutTimeStep[rs]:mTEPES.n.ord(n)]) == 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eHydroOutflows_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.nrso, rule=eHydroOutflows, doc='hydro outflows of a reservoir [m3/s]'))

    if pIndLogConsole == 1:
        print('eHydroOutflows        ... ', len(getattr(OptModel, 'eHydroOutflows_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

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
        if (st,n) in mTEPES.s2n and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in a2n[nr]) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr])     / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxOutput2ndBlock    ... ', len(getattr(OptModel, 'eMaxOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinOutput2ndBlock(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in a2n[nr]) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr])     / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinOutput2ndBlock    ... ', len(getattr(OptModel, 'eMinOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eTotalOutput(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pMaxPower[p,sc,n,nr]:
            if mTEPES.pMinPower[p,sc,n,nr] == 0.0:
                return OptModel.vTotalOutput[p,sc,n,nr]                               ==                                    OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]
            else:
                return OptModel.vTotalOutput[p,sc,n,nr] / mTEPES.pMinPower[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr] + (OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pMinPower[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalOutput_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, 'eTotalOutput_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUCStrShut(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPower[p,sc,n,nr] or mTEPES.pConstantVarCost[p,sc,n,nr]) and nr not in mTEPES.es:
            if n == mTEPES.n.first():
                return OptModel.vCommitment[p,sc,n,nr] - mTEPES.pInitialUC[p,sc,n,nr]                   == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
            else:
                return OptModel.vCommitment[p,sc,n,nr] - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUCStrShut_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown'))

    if pIndLogConsole == 1:
        print('eUCStrShut            ... ', len(getattr(OptModel, 'eUCStrShut_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCommitment(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and len(mTEPES.g2g):
            if sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g):
                return OptModel.vCommitment[p,sc,n,nr]                            <= OptModel.vMaxCommitment[p,sc,nr]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitment_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eMaxCommitment, doc='maximum of all the commitments'))

    if pIndLogConsole == 1:
        print('eMaxCommitment        ... ', len(getattr(OptModel, 'eMaxCommitment_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCommitGen(OptModel,n,g):
        if (st,n) in mTEPES.s2n and len(mTEPES.g2g):
            if sum(1 for gg in mTEPES.g if (g,gg) in mTEPES.g2g or (gg,g) in mTEPES.g2g) and mTEPES.pMaxPower[p,sc,n,g]:
                return OptModel.vTotalOutput[p,sc,n,g]/mTEPES.pMaxPower[p,sc,n,g] <= OptModel.vMaxCommitment[p,sc,g]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitGen_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.g, rule=eMaxCommitGen, doc='maximum of all the capacity factors'))

    if pIndLogConsole == 1:
        print('eMaxCommitGen         ... ', len(getattr(OptModel, 'eMaxCommitGen_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eExclusiveGens(OptModel,n,g):
        if (st,n) in mTEPES.s2n and len(mTEPES.g2g):
            if sum(1 for gg in mTEPES.g if (gg,g) in mTEPES.g2g):
                return OptModel.vMaxCommitment[p,sc,g] + sum(OptModel.vMaxCommitment[p,sc,gg] for gg in mTEPES.g if (gg,g) in mTEPES.g2g) <= 1
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExclusiveGens_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.g, rule=eExclusiveGens, doc='mutually exclusive generators'))

    if pIndLogConsole == 1:
        print('eExclusiveGens        ... ', len(getattr(OptModel, 'eExclusiveGens_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationRampMinTime(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Ramp and min up/down time  constraints ****')

    StartTime = time.time()

    def eRampUp(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            if n == mTEPES.n.first():
                return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPower[p,sc,n,nr],0.0)                            + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
            else:
                return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveDown[p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUp               ... ', len(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampDw(OptModel,n,nr):
        if (st,n) in mTEPES.s2n and mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            if n == mTEPES.n.first():
                return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPower[p,sc,n,nr],0.0)                            + OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[p,sc,n,nr]                   + OptModel.vShutDown[p,sc,n,nr]
            else:
                return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] + OptModel.vReserveUp  [p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] + OptModel.vShutDown[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDw               ... ', len(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampUpCharge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pRampUp[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            if n == mTEPES.n.first():
                return (                                                                                                            OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
            else:
                return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),es] + OptModel.vESSReserveDown[p,sc,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUpChr_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpChr            ... ', len(getattr(OptModel, 'eRampUpChr_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampDwCharge(OptModel,n,es):
        if (st,n) in mTEPES.s2n and mTEPES.pRampDw[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge[p,sc,n,es]:
            if n == mTEPES.n.first():
                return (                                                                                                          + OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
            else:
                return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),es] - OptModel.vESSReserveUp  [p,sc,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampDwChr_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.es, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwChr            ... ', len(getattr(OptModel, 'eRampDwChr_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinUpTime(OptModel,n,t):
        if (st,n) in mTEPES.s2n and mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPower[p,sc,n,t] or mTEPES.pConstantVarCost[p,sc,n,t]) and t not in mTEPES.es and mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(OptModel.vStartUp [p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[p,sc,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinUpTime_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]'))

    if pIndLogConsole == 1:
        print('eMinUpTime            ... ', len(getattr(OptModel, 'eMinUpTime_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinDownTime(OptModel,n,t):
        if (st,n) in mTEPES.s2n and mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPower[p,sc,n,t] or mTEPES.pConstantVarCost[p,sc,n,t]) and t not in mTEPES.es and mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(OptModel.vShutDown[p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[p,sc,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinDownTime_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]'))

    if pIndLogConsole == 1:
        print('eMinDownTime          ... ', len(getattr(OptModel, 'eMinDownTime_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating ramps & minimum time        ... ', round(GeneratingTime), 's')


def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    switching model constraints ****')

    StartTime = time.time()

    def eLineStateCand(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] <= OptModel.vNetworkInvest[p,ni,nf,cc]
            else:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] == OptModel.vNetworkInvest[p,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineStateCand_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole == 1:
        print('eLineStateCand        ... ', len(getattr(OptModel, 'eLineStateCand_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eSWOnOff(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1):
                if n == mTEPES.n.first():
                    return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - mTEPES.pInitialSwitch[p,sc,n,ni,nf,cc]               == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
                else:
                    return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - OptModel.vLineCommit[p,sc,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSWOnOff_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole == 1:
        print('eSWOnOff              ... ', len(getattr(OptModel, 'eSWOnOff_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinSwOnState(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
                return sum(OptModel.vLineOnState [p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOnState_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOnState         ... ', len(getattr(OptModel, 'eMinSwOnState_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinSwOffState(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
                return sum(OptModel.vLineOffState[p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOffState_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOffState        ... ', len(getattr(OptModel, 'eMinSwOffState_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Switching minimum on/off state         ... ', round(GeneratingTime), 's')


def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    operation model constraints ****')

    StartTime = time.time()

    def eNetCapacity1(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pLineNTCMax[ni,nf,cc] >= - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eNetCapacity1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.la, rule=eNetCapacity1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity1         ... ', len(getattr(OptModel, 'eNetCapacity1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eNetCapacity2(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pLineNTCMax[ni,nf,cc] <=   OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eNetCapacity2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.la, rule=eNetCapacity2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity2         ... ', len(getattr(OptModel, 'eNetCapacity2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eKirchhoff2ndLaw1(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and mTEPES.pPeriodIniNet[ni,nf,cc] <= p and mTEPES.pPeriodFinNet[ni,nf,cc] >= p and mTEPES.pLineX[ni,nf,cc] > 0.0:
            if (ni,nf,cc) in mTEPES.lca:
                return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase ==   0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLaw1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw1, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw1     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eKirchhoff2ndLaw2(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and mTEPES.pPeriodIniNet[ni,nf,cc] <= p and mTEPES.pPeriodFinNet[ni,nf,cc] >= p and mTEPES.pLineX[ni,nf,cc] > 0.0:
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLaw2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLaw2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw2     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eLineLosses1(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses() and len(mTEPES.ll):
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses1          ... ', len(getattr(OptModel, 'eLineLosses1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eLineLosses2(OptModel,n,ni,nf,cc):
        if (st,n) in mTEPES.s2n and mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses() and len(mTEPES.ll):
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses2          ... ', len(getattr(OptModel, 'eLineLosses2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating network    constraints      ... ', round(GeneratingTime), 's')

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

    def eBalanceH2(OptModel,n,nd):
        if (st,n) in mTEPES.s2n and sum(1 for el in e2n[nd]) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vESSTotalCharge[p,sc,n,el]*mTEPES.pDuration[n]/mTEPES.pProductionFunctionH2[el] for el in e2n[nd]) + OptModel.vHNS[p,sc,n,nd] -
                    sum(OptModel.vFlowH2[p,sc,n,nd,lout] for lout in lout[nd]) + sum(OptModel.vFlowH2[p,sc,n,ni,nd,cc] for ni,cc in lin[nd])) == mTEPES.pDemandH2[p,sc,n,nd]*mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eBalanceH2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.n, mTEPES.nd, rule=eBalanceH2, doc='H2 load generation balance [tH2]'))

    if pIndLogConsole == 1:
        print('eBalanceH2            ... ', len(getattr(OptModel, 'eBalanceH2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating hydrogen  operation         ... ', round(GeneratingTime), 's')
