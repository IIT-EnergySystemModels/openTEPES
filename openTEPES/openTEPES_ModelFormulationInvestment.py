"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - June 11, 2026

openTEPES.openTEPES_ModelFormulationInvestment — investment variables and constraints (electricity, hydro, H2, heat) plus the installed-capacity, adequacy-reserve-margin and emission / RES-energy limits.
"""
from __future__ import annotations

import time
import math
from collections import defaultdict
from pyomo.environ import Constraint, Set


def InvestmentElecModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment elec      model formulation ****')

    StartTime = time.time()

    def eTotalICost(OptModel):
        if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) + len(mTEPES.rn) + len(mTEPES.pc) + len(mTEPES.hc) == 0:
            return Constraint.Skip
        return OptModel.vTotalICost == (sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFElecCost [p] for p in mTEPES.p if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc)) +
                                        sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFHydroCost[p] for p in mTEPES.p if mTEPES.rn) +
                                        sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFH2Cost   [p] for p in mTEPES.p if mTEPES.pc) +
                                        sum(mTEPES.pDiscountedWeight[p] * OptModel.vTotalFHeatCost [p] for p in mTEPES.p if mTEPES.hc) )
    OptModel.eTotalICost = Constraint(rule=eTotalICost, doc='system fixed cost [MEUR]')

    def eTotalFElecCost(OptModel,p):
        if len(mTEPES.gc) + len(mTEPES.gd) + len(mTEPES.lc) == 0:
            return Constraint.Skip
        return (OptModel.vTotalFElecCost[p] == sum(mTEPES.pGenInvestCost     [gc] * OptModel.vGenerationInvest   [p,gc] for gc       in mTEPES.gc if       (p,gc) in mTEPES.pgc) +
                                               sum(mTEPES.pGenRetireCost     [gd] * OptModel.vGenerationRetire   [p,gd] for gd       in mTEPES.gd if       (p,gd) in mTEPES.pgd) +
                                               sum(mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.lc if (p,ni,nf,cc) in mTEPES.plc) )
    OptModel.eTotalFElecCost = Constraint(mTEPES.p, rule=eTotalFElecCost, doc='electricity system fixed cost [MEUR]')

    def eConsecutiveGenInvest(OptModel,p,gc):
        if len(mTEPES.gc) == 0 or p == mTEPES.p.first() or (mTEPES.p.prev(p,1),gc) not in mTEPES.pgc:
            return Constraint.Skip
        return OptModel.vGenerationInvest    [mTEPES.p.prev(p,1),gc      ] + OptModel.vGenerationInvPer    [p,gc      ] == OptModel.vGenerationInvest    [p,gc      ]
    OptModel.eConsecutiveGenInvest = Constraint(mTEPES.pgc, rule=eConsecutiveGenInvest, doc='generation investment in consecutive periods')

    def eConsecutiveGenRetire(OptModel,p,gd):
        if len(mTEPES.gd) == 0 or p == mTEPES.p.first() or (mTEPES.p.prev(p,1),gd) not in mTEPES.gd:
            return Constraint.Skip
        return OptModel.vGenerationRetire    [mTEPES.p.prev(p,1),gd      ] + OptModel.vGenerationRetPer    [p,gd      ] == OptModel.vGenerationRetire    [p,gd      ]
    OptModel.eConsecutiveGenRetire = Constraint(mTEPES.pgd, rule=eConsecutiveGenRetire, doc='generation retirement in consecutive periods')

    def eConsecutiveNetInvest(OptModel,p,ni,nf,cc):
        if len(mTEPES.lc) == 0 or p == mTEPES.p.first() or (mTEPES.p.prev(p,1),ni,nf,cc) not in mTEPES.plc:
            return Constraint.Skip
        return OptModel.vNetworkInvest       [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vNetworkInvPer       [p,ni,nf,cc] == OptModel.vNetworkInvest       [p,ni,nf,cc]
    OptModel.eConsecutiveNetInvest = Constraint(mTEPES.plc, rule=eConsecutiveNetInvest, doc='electric network investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('G&T electr investment o.f./constraints ... ', round(GeneratingTime), 's')


# @profile
def InvestmentHydroModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment hydro     model formulation ****')

    StartTime = time.time()

    def eTotalFHydroCost(OptModel,p):
        return OptModel.vTotalFHydroCost[p] == sum(mTEPES.pRsrInvestCost[rc] * OptModel.vReservoirInvest[p,rc] for rc in mTEPES.rn if (p,rc) in mTEPES.prc)
    OptModel.eTotalFHydroCost = Constraint(mTEPES.p, rule=eTotalFHydroCost, doc='system fixed hydro cost [MEUR]')

    def eConsecutiveRsrInvest(OptModel,p,rc):
        if p == mTEPES.p.first() or (mTEPES.p.prev(p,1),rc) not in mTEPES.prc:
            return Constraint.Skip
        return OptModel.vReservoirInvest     [mTEPES.p.prev(p,1),rc      ] + OptModel.vReservoirInvPer     [p,rc      ] == OptModel.vReservoirInvest     [p,rc      ]
    OptModel.eConsecutiveRsrInvest = Constraint(mTEPES.prc, rule=eConsecutiveRsrInvest, doc='reservoir investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Hydro      investment o.f./constraints ... ', round(GeneratingTime), 's')


# @profile
def InvestmentH2ModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment H2        model formulation ****')

    StartTime = time.time()

    def eTotalFH2Cost(OptModel,p):
        return OptModel.vTotalFH2Cost[p] == sum(mTEPES.pH2PipeFixedCost[ni,nf,cc] * OptModel.vH2PipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.pc if (p,ni,nf,cc) in mTEPES.ppc)
    OptModel.eTotalFH2Cost = Constraint(mTEPES.p, rule=eTotalFH2Cost, doc='system fixed H2 cost [MEUR]')

    def eConsecutiveNetH2Invest(OptModel,p,ni,nf,cc):
        if p == mTEPES.p.first() or (mTEPES.p.prev(p,1),ni,nf,cc) not in mTEPES.ppc:
            return Constraint.Skip
        return OptModel.vH2PipeInvest        [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vH2PipeInvPer        [p,ni,nf,cc] == OptModel.vH2PipeInvest        [p,ni,nf,cc]
    OptModel.eConsecutiveNetH2Invest = Constraint(mTEPES.ppc, rule=eConsecutiveNetH2Invest, doc='H2 pipe network investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('H2         investment o.f./constraints ... ', round(GeneratingTime), 's')


# @profile
def InvestmentHeatModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment heat      model formulation ****')

    StartTime = time.time()

    def eTotalFHeatCost(OptModel,p):
        return OptModel.vTotalFHeatCost[p] == sum(mTEPES.pHeatPipeFixedCost[ni,nf,cc] * OptModel.vHeatPipeInvest[p,ni,nf,cc] for ni,nf,cc in mTEPES.hc if (p,ni,nf,cc) in mTEPES.phc)
    OptModel.eTotalFHeatCost = Constraint(mTEPES.p, rule=eTotalFHeatCost, doc='system fixed heat cost [MEUR]')

    def eConsecutiveNetHeatInvest(OptModel,p,ni,nf,cc):
        if p == mTEPES.p.first() or (mTEPES.p.prev(p,1),ni,nf,cc) not in mTEPES.phc:
            return Constraint.Skip
        return OptModel.vHeatPipeInvest     [mTEPES.p.prev(p,1),ni,nf,cc] + OptModel.vHeatPipeInvPer       [p,ni,nf,cc] == OptModel.vHeatPipeInvest      [p,ni,nf,cc]
    OptModel.eConsecutiveNetHeatInvest = Constraint(mTEPES.phc, rule=eConsecutiveNetHeatInvest, doc='heat pipe network investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Heat       investment o.f./constraints ... ', round(GeneratingTime), 's')


# @profile


def GenerationOperationElecModelFormulationInvestment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Investment & operation var constraints ****')

    StartTime = time.time()

    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    def eInstallGenComm(OptModel,n,gc):
        if gc in mTEPES.eh or gc in mTEPES.bc or gc not in mTEPES.nr or (p,gc) not in mTEPES.pgc or (mTEPES.pMinPowerElec[p,sc,n,gc] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,gc] == 0.0):
            return Constraint.Skip
        if mTEPES.pMustRun[gc] == 0:
            return OptModel.vCommitment[p,sc,n,gc] <= OptModel.vGenerationInvest[p,gc]
        else:
            return OptModel.vCommitment[p,sc,n,gc] == OptModel.vGenerationInvest[p,gc]
    setattr(OptModel, f'eInstallGenComm_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gc, rule=eInstallGenComm, doc='commitment if installed unit [p.u.]'))

    if pIndLogConsole:
        print('eInstallGenComm           ... ', len(getattr(OptModel, f'eInstallGenComm_{p}_{sc}_{st}')), ' rows')

    def eInstallESSComm(OptModel,n,ec):
        if (p,ec) not in mTEPES.pec or mTEPES.pIndBinStorInvest[ec] == 0:
            return Constraint.Skip
        return OptModel.vCommitment[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
    setattr(OptModel, f'eInstallESSComm_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ec, rule=eInstallESSComm, doc='commitment if ESS unit [p.u.]'))

    if pIndLogConsole:
        print('eInstallESSComm           ... ', len(getattr(OptModel, f'eInstallESSComm_{p}_{sc}_{st}')), ' rows')

    def eInstallGenCap(OptModel,n,gc):
        if (p,gc) not in mTEPES.pgc or mTEPES.pMaxPowerElec[p,sc,n,gc] == 0.0:
            return Constraint.Skip
        return OptModel.vTotalOutput   [p,sc,n,gc] / mTEPES.pMaxPowerElec [p,sc,n,gc] <= OptModel.vGenerationInvest[p,gc]
    setattr(OptModel, f'eInstallGenCap_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gc, rule=eInstallGenCap, doc='output if installed gen unit [p.u.]'))

    if pIndLogConsole:
        print('eInstallGenCap            ... ', len(getattr(OptModel, f'eInstallGenCap_{p}_{sc}_{st}')), ' rows')

    def eInstallConESS(OptModel,n,ec):
        if (p,ec) not in mTEPES.pec or mTEPES.pMaxCharge[p,sc,n,ec] == 0.0:
            return Constraint.Skip
        return OptModel.vESSTotalCharge[p,sc,n,ec] / mTEPES.pMaxCharge[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
    setattr(OptModel, f'eInstallConESS_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.ec, rule=eInstallConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole:
        print('eInstallConESS            ... ', len(getattr(OptModel, f'eInstallConESS_{p}_{sc}_{st}')), ' rows')

    def eUninstallGenComm(OptModel,n,gd):
        if gd in mTEPES.eh or gd not in mTEPES.nr or (p,gd) not in mTEPES.pgd or mTEPES.pMustRun[gd] or (mTEPES.pMinPowerElec[p,sc,n,gd] == 0.0 and mTEPES.pConstantVarCost[p,sc,n,gd] == 0.0):
            return Constraint.Skip
        return OptModel.vCommitment[p,sc,n,gd]                                <= 1 - OptModel.vGenerationRetire[p,gd]
    setattr(OptModel, f'eUninstallGenComm_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gd, rule=eUninstallGenComm, doc='commitment if uninstalled unit [p.u.]'))

    if pIndLogConsole:
        print('eUninstallGenComm         ... ', len(getattr(OptModel, f'eUninstallGenComm_{p}_{sc}_{st}')), ' rows')

    def eUninstallGenCap(OptModel,n,gd):
        if (p,gd) not in mTEPES.pgd or mTEPES.pMaxPowerElec[p,sc,n,gd] == 0.0:
            return Constraint.Skip
        return OptModel.vTotalOutput[p,sc,n,gd] / mTEPES.pMaxPowerElec[p,sc,n,gd] <= 1 - OptModel.vGenerationRetire[p,gd]
    setattr(OptModel, f'eUninstallGenCap_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.gd, rule=eUninstallGenCap, doc='output if uninstalled gen unit [p.u.]'))

    if pIndLogConsole:
        print('eUninstallGenCap          ... ', len(getattr(OptModel, f'eUninstallGenCap_{p}_{sc}_{st}')), ' rows')

    def eAdequacyReserveMarginElec(OptModel,ar):
        if mTEPES.pReserveMargin[p,ar]() and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if gc in g2a[ar]) and sum(mTEPES.pRatedMaxPowerElec[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in mTEPES.g if g in g2a[ar] and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar]():
            return ((sum(                                       mTEPES.pRatedMaxPowerElec[g ] * mTEPES.pAvailability[g ]() / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if g  in g2a[ar] and (p,g ) in mTEPES.pg  and g not in (mTEPES.gc or mTEPES.gd)) +
                     sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPowerElec[gc] * mTEPES.pAvailability[gc]() / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if gc in g2a[ar] and (p,gc) in mTEPES.pgc                                      ) +
                     sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPowerElec[gd] * mTEPES.pAvailability[gd]() / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if gd in g2a[ar] and (p,gd) in mTEPES.pgd                                      ) ) >= mTEPES.pDemandElecPeak[p,ar] * mTEPES.pReserveMargin[p,ar])
        else:
            return Constraint.Skip
    setattr(OptModel, f'eAdequacyReserveMarginElec_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eAdequacyReserveMarginElec, doc='electricity system adequacy reserve margin [p.u.]'))

    if pIndLogConsole:
        print('eAdeqReserveMarginElec    ... ', len(getattr(OptModel, f'eAdequacyReserveMarginElec_{p}_{sc}_{st}')), ' rows')

    def eMaxSystemEmission(OptModel,ar):
        if mTEPES.pEmission[p,ar] == math.inf or st != mTEPES.Last_st or sum(mTEPES.pEmissionRate[nr] for nr in mTEPES.nr if nr in g2a[ar]) == 0.0:
            return Constraint.Skip
        # There is an emission limit, there are generators with emissions in the Area and it is the last stage
        return sum(OptModel.vTotalEmissionArea[p,sc,na,ar] for na in mTEPES.na) <= mTEPES.pEmission[p,ar]
    setattr(OptModel, f'eMaxSystemEmission_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eMaxSystemEmission, doc='maximum CO2 emission [tCO2]'))

    if pIndLogConsole:
        print('eMaxSystemEmission        ... ', len(getattr(OptModel, f'eMaxSystemEmission_{p}_{sc}_{st}')), ' rows')

    def eMinSystemRESEnergy(OptModel,ar):
        if mTEPES.pRESEnergy[p,ar]() == 0.0 or st != mTEPES.Last_st:
            return Constraint.Skip
        return sum(OptModel.vTotalRESEnergyArea[p,sc,na,ar] for na in mTEPES.na)/sum(mTEPES.pLoadLevelDuration[p,sc,na] for na in mTEPES.na) >= mTEPES.pRESEnergy[p,ar]/sum(mTEPES.pLoadLevelDuration[p,sc,na] for na in mTEPES.na)
    setattr(OptModel, f'eMinSystemRESEnergy_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eMinSystemRESEnergy, doc='minimum RES energy [GW]'))

    if pIndLogConsole:
        print('eMinSystemRESEnergy       ... ', len(getattr(OptModel, f'eMinSystemRESEnergy_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating operation & investment      ... ', round(GeneratingTime), 's')


# @profile
def GenerationOperationHeatModelFormulationInvestment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Investment & operation var constraints ****')

    StartTime = time.time()

    g2a = defaultdict(list)
    for ar,g in mTEPES.a2g:
        g2a[ar].append(g)

    def eInstallFHUCap(OptModel,n,bc):
        if (p,bc) not in mTEPES.pbc or mTEPES.pMaxPowerHeat[p,sc,n,bc] == 0.0:
            return Constraint.Skip
        return OptModel.vTotalOutputHeat[p,sc,n,bc] / mTEPES.pMaxPowerHeat[p,sc,n,bc] <= OptModel.vGenerationInvest[p,bc]
    setattr(OptModel, f'eInstallFHUCap_{p}_{sc}_{st}', Constraint(mTEPES.n*mTEPES.bc, rule=eInstallFHUCap, doc='heat production if installed fuel heating unit [p.u.]'))

    if pIndLogConsole:
        print('eInstallFHUCap            ... ', len(getattr(OptModel, f'eInstallFHUCap_{p}_{sc}_{st}')), ' rows')

    def eAdequacyReserveMarginHeat(OptModel,ar):
        if mTEPES.pReserveMarginHeat[p,ar] and st == mTEPES.Last_st and sum(1 for gc in mTEPES.gc if gc in g2a[ar]) and sum(mTEPES.pRatedMaxPowerHeat[g] * mTEPES.pAvailability[g]() / (1.0-mTEPES.pEFOR[g]()) for g in g2a[ar] and g not in (mTEPES.gc or mTEPES.gd)) <= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar]:
            return ((sum(                                       mTEPES.pRatedMaxPowerHeat[g ] * mTEPES.pAvailability[g ]() / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if g  in g2a[ar] and (p,g ) in mTEPES.pg  and g not in (mTEPES.gc or mTEPES.gd)) +
                     sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPowerHeat[gc] * mTEPES.pAvailability[gc]() / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if gc in g2a[ar] and (p,gc) in mTEPES.pgc                                      ) +
                     sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPowerHeat[gd] * mTEPES.pAvailability[gd]() / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if gd in g2a[ar] and (p,gd) in mTEPES.pgd                                      ) ) >= mTEPES.pDemandHeatPeak[p,ar] * mTEPES.pReserveMarginHeat[p,ar])
        else:
            return Constraint.Skip
    setattr(OptModel, f'eAdequacyReserveMarginHeat_{p}_{sc}_{st}', Constraint(mTEPES.ar, rule=eAdequacyReserveMarginHeat, doc='heat system adequacy reserve margin [p.u.]'))

    if pIndLogConsole:
        print('eAdeqReserveMarginHeat    ... ', len(getattr(OptModel, f'eAdequacyReserveMarginHeat_{p}_{sc}_{st}')), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole:
        print('Generating operation & investment      ... ', round(GeneratingTime), 's')


# @profile
