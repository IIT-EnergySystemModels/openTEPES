"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - March 25, 2022
"""

import time
from   collections   import defaultdict
from   pyomo.environ import Set, Constraint, Objective, Block, minimize


def TotalObjectiveFunction(OptModel, mTEPES, pIndLogConsole):
    print('Total cost o.f.      model formulation ****')

    StartTime = time.time()

    def eTotalTCost(OptModel):
        return OptModel.vTotalFCost + sum(mTEPES.pPeriodWeight[p] * mTEPES.pScenProb[p,sc] * (OptModel.vTotalGCost[p,sc,n] + OptModel.vTotalCCost[p,sc,n] + OptModel.vTotalECost[p,sc,n] + OptModel.vTotalRCost[p,sc,n]) for p,sc,n in mTEPES.p*mTEPES.sc*mTEPES.n)
    OptModel.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Total fixed and variable costs         ... ', round(GeneratingTime), 's')


def InvestmentModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment           model formulation ****')

    StartTime = time.time()

    def eTotalFCost(OptModel):
        return OptModel.vTotalFCost == sum(mTEPES.pPeriodWeight[p] * mTEPES.pGenInvestCost[gc] * OptModel.vGenerationInvest[p,gc] for p,gc in mTEPES.p*mTEPES.gc) + sum(mTEPES.pPeriodWeight[p] * mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[p,gd] for p,gd in mTEPES.p*mTEPES.gd) + sum(mTEPES.pPeriodWeight[p] * mTEPES.pNetFixedCost[ni,nf,cc] * OptModel.vNetworkInvest[p,ni,nf,cc] for p,ni,nf,cc in mTEPES.p*mTEPES.lc)
    OptModel.eTotalFCost = Constraint(rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    def eConsecutiveGenInvest(OptModel,p,gc):
        if p != mTEPES.p.first():
            return OptModel.vGenerationInvest[mTEPES.p.prev(p,1),gc      ] <= OptModel.vGenerationInvest[p,gc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenInvest = Constraint(mTEPES.p, mTEPES.gc, rule=eConsecutiveGenInvest, doc='generation investment in consecutive periods')

    def eConsecutiveGenRetire(OptModel,p,gc):
        if p != mTEPES.p.first():
            return OptModel.vGenerationRetire[mTEPES.p.prev(p,1),gc      ] <= OptModel.vGenerationRetire[p,gc      ]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveGenRetire = Constraint(mTEPES.p, mTEPES.gc, rule=eConsecutiveGenRetire, doc='generation retirement in consecutive periods')

    def eConsecutiveNetInvest(OptModel,p,ni,nf,cc):
        if p != mTEPES.p.first():
            return OptModel.vNetworkInvest   [mTEPES.p.prev(p,1),ni,nf,cc] <= OptModel.vNetworkInvest   [p,ni,nf,cc]
        else:
            return Constraint.Skip
    OptModel.eConsecutiveNetInvest = Constraint(mTEPES.p, mTEPES.lc, rule=eConsecutiveNetInvest, doc='network    investment in consecutive periods')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Gen&transm investment o.f./constraints ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationObjFunct(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Generation oper model formulation o.f. ****')

    StartTime = time.time()

    def eTotalGCost(OptModel,p,sc,n):
        return OptModel.vTotalGCost[p,sc,n] == (sum(mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pLinearVarCost  [nr] * OptModel.vTotalOutput   [p,sc,n,nr]                      +
                                                    mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pConstantVarCost[nr] * OptModel.vCommitment    [p,sc,n,nr]                      +
                                                    mTEPES.pLoadLevelWeight[n] *                       mTEPES.pStartUpCost    [nr] * OptModel.vStartUp       [p,sc,n,nr]                      +
                                                    mTEPES.pLoadLevelWeight[n] *                       mTEPES.pShutDownCost   [nr] * OptModel.vShutDown      [p,sc,n,nr] for nr in mTEPES.nr) +
                                                sum(mTEPES.pLoadLevelWeight[n] *                       mTEPES.pOperReserveCost[nr] * OptModel.vReserveUp     [p,sc,n,nr]                      +
                                                    mTEPES.pLoadLevelWeight[n] *                       mTEPES.pOperReserveCost[nr] * OptModel.vReserveDown   [p,sc,n,nr] for nr in mTEPES.nr if mTEPES.pIndOperReserve[nr] == 0) +
                                                sum(mTEPES.pLoadLevelWeight[n] *                       mTEPES.pOperReserveCost[es] * OptModel.vESSReserveUp  [p,sc,n,es]                      +
                                                    mTEPES.pLoadLevelWeight[n] *                       mTEPES.pOperReserveCost[es] * OptModel.vESSReserveDown[p,sc,n,es] for es in mTEPES.es if mTEPES.pIndOperReserve[es] == 0) +
                                                sum(mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pLinearOMCost   [r ] * OptModel.vTotalOutput   [p,sc,n,r ] for r  in mTEPES.r ) )
    setattr(OptModel, 'eTotalGCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    def eTotalCCost(OptModel,p,sc,n):
        return OptModel.vTotalCCost[p,sc,n] == sum(mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pLinearVarCost  [es] * OptModel.vESSTotalCharge[p,sc,n,es] for es in mTEPES.es)
    setattr(OptModel, 'eTotalCCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,p,sc,n):
        if sum(mTEPES.pCO2EmissionCost[nr] for nr in mTEPES.nr):
            return OptModel.vTotalECost[p,sc,n] == sum(mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pCO2EmissionCost[nr] * OptModel.vTotalOutput   [p,sc,n,nr] for nr in mTEPES.nr)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalECost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalRCost(OptModel,p,sc,n):
        return     OptModel.vTotalRCost[p,sc,n] == sum(mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * mTEPES.pENSCost             * OptModel.vENS           [p,sc,n,nd] for nd in mTEPES.nd)
    setattr(OptModel, 'eTotalRCost_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating operation  o.f.             ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationInvestment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Investment & operation var constraints ****')

    StartTime = time.time()

    def eInstalGenComm(OptModel,p,sc,n,gc):
        if gc in mTEPES.nr and gc not in mTEPES.es and mTEPES.pMustRun[gc] == 0 and (mTEPES.pMinPower[p,sc,n,gc] > 0.0 or mTEPES.pConstantVarCost[gc] > 0.0):
            return OptModel.vCommitment[p,sc,n,gc]                                 <= OptModel.vGenerationInvest[p,gc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment if installed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenComm        ... ', len(getattr(OptModel, 'eInstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInstalGenCap(OptModel,p,sc,n,gc):
        if mTEPES.pMaxPower[p,sc,n,gc]:
            return OptModel.vTotalOutput[p,sc,n,gc] / mTEPES.pMaxPower [p,sc,n,gc] <= OptModel.vGenerationInvest[p,gc]
        else:
            return OptModel.vTotalOutput[p,sc,n,gc]                               <= 0.0
    setattr(OptModel, 'eInstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output if installed gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenCap         ... ', len(getattr(OptModel, 'eInstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eInstalConESS(OptModel,p,sc,n,ec):
        return OptModel.vESSTotalCharge [p,sc,n,ec] / mTEPES.pMaxCharge[p,sc,n,ec] <= OptModel.vGenerationInvest[p,ec]
    setattr(OptModel, 'eInstalConESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalConESS         ... ', len(getattr(OptModel, 'eInstalConESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUninstalGenComm(OptModel,p,sc,n,gd):
        if gd in mTEPES.nr and gd not in mTEPES.es and mTEPES.pMustRun[gd] == 0 and (mTEPES.pMinPower[p,sc,n,gd] > 0.0 or mTEPES.pConstantVarCost[gd] > 0.0):
            return OptModel.vCommitment[p,sc,n,gd]                                <= 1 - OptModel.vGenerationRetire[p,gd]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUninstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.gd, rule=eUninstalGenComm, doc='commitment if uninstalled unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstalGenComm      ... ', len(getattr(OptModel, 'eUninstalGenComm_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUninstalGenCap(OptModel,p,sc,n,gd):
        if mTEPES.pMaxPower[p,sc,n,gd]:
            return OptModel.vTotalOutput[p,sc,n,gd] / mTEPES.pMaxPower[p,sc,n,gd] <= 1 - OptModel.vGenerationRetire[p,gd]
        else:
            return OptModel.vTotalOutput[p,sc,n,gd]                               <= 0.0
    setattr(OptModel, 'eUninstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.gd, rule=eUninstalGenCap, doc='output if uninstalled gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eUninstalGenCap       ... ', len(getattr(OptModel, 'eUninstalGenCap_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eAdequacyReserveMargin(OptModel,p,ar):
        if mTEPES.pReserveMargin[ar] and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g):
            return ((sum(                                       mTEPES.pRatedMaxPower[g ] * mTEPES.pAvailability[g ] / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if (ar,g ) in mTEPES.a2g and g not in (mTEPES.gc or mTEPES.gd)) +
                     sum(   OptModel.vGenerationInvest[p,gc]  * mTEPES.pRatedMaxPower[gc] * mTEPES.pAvailability[gc] / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g                                      ) +
                     sum((1-OptModel.vGenerationRetire[p,gd]) * mTEPES.pRatedMaxPower[gd] * mTEPES.pAvailability[gd] / (1.0-mTEPES.pEFOR[gd]) for gd in mTEPES.gd if (ar,gd) in mTEPES.a2g                                      ) ) >= mTEPES.pPeakDemand[ar] * mTEPES.pReserveMargin[ar])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.ar, rule=eAdequacyReserveMargin, doc='system adequacy reserve margin [p.u.]'))

    if pIndLogConsole == 1:
        print('eAdequacyReserveMargin... ', len(getattr(OptModel, 'eAdequacyReserveMargin_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating operation & investment      ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationDemand(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Inertia, oper resr, demand constraints ****')

    StartTime = time.time()

    def eSystemInertia(OptModel,p,sc,n,ar):
        if mTEPES.pSystemInertia[p,sc,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vTotalOutput[p,sc,n,nr] * mTEPES.pInertia[nr] / mTEPES.pMaxPower[p,sc,n,nr] for nr in mTEPES.nr if mTEPES.pMaxPower[p,sc,n,nr] and (ar,nr) in mTEPES.a2g) >= mTEPES.pSystemInertia[p,sc,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSystemInertia_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ar, rule=eSystemInertia, doc='system inertia [s]'))

    if pIndLogConsole == 1:
        print('eSystemInertia        ... ', len(getattr(OptModel, 'eSystemInertia_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eOperReserveUp(OptModel,p,sc,n,ar):
        if   mTEPES.pOperReserveUp[p,sc,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1                                   for es in mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0):
            return sum(OptModel.vReserveUp  [p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(OptModel.vESSReserveUp  [p,sc,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0) == mTEPES.pOperReserveUp[p,sc,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveUp        ... ', len(getattr(OptModel, 'eOperReserveUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eOperReserveDw(OptModel,p,sc,n,ar):
        if   mTEPES.pOperReserveDw[p,sc,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(1                                   for es in mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0):
            return sum(OptModel.vReserveDown[p,sc,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g and mTEPES.pIndOperReserve[nr] == 0) + sum(OptModel.vESSReserveDown[p,sc,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g and mTEPES.pIndOperReserve[es] == 0) == mTEPES.pOperReserveDw[p,sc,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveDw        ... ', len(getattr(OptModel, 'eOperReserveDw_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveMinRatioDwUp(OptModel,p,sc,n,nr):
        if mTEPES.pMinRatioDwUp       and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pIndOperReserve[nr] == 0:
            return OptModel.vReserveDown[p,sc,n,nr] >= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMinRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveMinRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eReserveMinRatioDwUp, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMinRatioDwUp  ... ', len(getattr(OptModel, 'eReserveMinRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveMaxRatioDwUp(OptModel,p,sc,n,nr):
        if mTEPES.pMaxRatioDwUp < 1.0 and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and mTEPES.pIndOperReserve[nr] == 0:
            return OptModel.vReserveDown[p,sc,n,nr] <= OptModel.vReserveUp[p,sc,n,nr] * mTEPES.pMaxRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveMaxRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eReserveMaxRatioDwUp, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eReserveMaxRatioDwUp  ... ', len(getattr(OptModel, 'eReserveMaxRatioDwUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRsrvMinRatioDwUpESS(OptModel,p,sc,n,es):
        if mTEPES.pMinRatioDwUp       and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return OptModel.vESSReserveDown[p,sc,n,es] >= OptModel.vESSReserveUp[p,sc,n,es] * mTEPES.pMinRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRsrvMinRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eRsrvMinRatioDwUpESS, doc='minimum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMinRatioDwUpESS  ... ', len(getattr(OptModel, 'eRsrvMinRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRsrvMaxRatioDwUpESS(OptModel,p,sc,n,es):
        if mTEPES.pMaxRatioDwUp < 1.0 and sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return OptModel.vESSReserveDown[p,sc,n,es] <= OptModel.vESSReserveUp[p,sc,n,es] * mTEPES.pMaxRatioDwUp
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRsrvMaxRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eRsrvMaxRatioDwUpESS, doc='maximum ratio down to up operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eRsrvMaxRatioDwUpESS  ... ', len(getattr(OptModel, 'eRsrvMaxRatioDwUpESS_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveUpIfEnergy(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0 and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vReserveUp  [p,sc,n,es] <=                                  OptModel.vESSInventory[p,sc,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveUpIfEnergy    ... ', len(getattr(OptModel, 'eReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eReserveDwIfEnergy(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0 and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vReserveDown[p,sc,n,es] <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveDwIfEnergy    ... ', len(getattr(OptModel, 'eReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSReserveUpIfEnergy(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0 and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vESSReserveUp  [p,sc,n,es] <= (mTEPES.pMaxStorage[p,sc,n,es] - OptModel.vESSInventory[p,sc,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveUpIfEnergy ... ', len(getattr(OptModel, 'eESSReserveUpIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSReserveDwIfEnergy(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0 and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vESSReserveDown[p,sc,n,es] <=                                  OptModel.vESSInventory[p,sc,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveDwIfEnergy ... ', len(getattr(OptModel, 'eESSReserveDwIfEnergy_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    # incoming and outgoing lines (lin) (lout)
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

    def eBalance(OptModel,p,sc,n,nd):
        if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutput[p,sc,n,g] for g in mTEPES.g if (nd,g) in mTEPES.n2g) - sum(OptModel.vESSTotalCharge[p,sc,n,es] for es in mTEPES.es if (nd,es) in mTEPES.n2g) + OptModel.vENS[p,sc,n,nd] == mTEPES.pDemand[p,sc,n,nd] +
                    sum(OptModel.vLineLosses[p,sc,n,nd,lout ] for lout  in loutl[nd]) + sum(OptModel.vFlow[p,sc,n,nd,lout ] for lout  in lout[nd]) +
                    sum(OptModel.vLineLosses[p,sc,n,ni,nd,cc] for ni,cc in linl [nd]) - sum(OptModel.vFlow[p,sc,n,ni,nd,cc] for ni,cc in lin [nd]))
        else:
            return Constraint.Skip
    setattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nd, rule=eBalance, doc='load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalance              ... ', len(getattr(OptModel, 'eBalance_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating inertia/reserves/balance    ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationStorage(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Storage scheduling         constraints ****')

    StartTime = time.time()

    def eESSInventory(OptModel,p,sc,n,es):
        if   mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[p,sc,n,es]                                            + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
        elif mTEPES.n.ord(n) > mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vESSInventory[p,sc,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[p,sc,n2,es] - OptModel.vEnergyOutflows[p,sc,n2,es] - OptModel.vTotalOutput[p,sc,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[p,sc,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[p,sc,n,es] + OptModel.vESSSpillage[p,sc,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSInventory_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole == 1:
        print('eESSInventory         ... ', len(getattr(OptModel, 'eESSInventory_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCharge(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return (OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCharge            ... ', len(getattr(OptModel, 'eMaxCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinCharge(OptModel,p,sc,n,es):
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pIndOperReserve[es] == 0:
            return (OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinCharge            ... ', len(getattr(OptModel, 'eMinCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    # def eChargeDischarge(OptModel,p,sc,n,es):
    #     if mTEPES.pMaxCharge[p,sc,n,es]:
    #         return OptModel.vTotalOutput[p,sc,n,es] / mTEPES.pMaxPower[p,sc,n,es] + OptModel.vCharge2ndBlock[p,sc,n,es] / mTEPES.pMaxCharge[p,sc,n,es] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(OptModel,p,sc,n,es):
        if mTEPES.pMaxPower2ndBlock [p,sc,n,es] and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            if sum(mTEPES.pOperReserveUp[p,sc,n,ar] + mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
                return ((OptModel.vOutput2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [p,sc,n,es]) / mTEPES.pMaxPower2ndBlock [p,sc,n,es] +
                        (OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0)
            else:
                return ((OptModel.vOutput2ndBlock[p,sc,n,es]                                                                    ) / mTEPES.pMaxPower2ndBlock [p,sc,n,es] +
                        (OptModel.vCharge2ndBlock[p,sc,n,es]                                                                    ) / mTEPES.pMaxCharge2ndBlock[p,sc,n,es] <= 1.0)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eChargeDischarge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeDischarge      ... ', len(getattr(OptModel, 'eChargeDischarge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eESSTotalCharge(OptModel,p,sc,n,es):
        if   mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pMaxCharge2ndBlock[p,sc,n,es] and mTEPES.pMinCharge[p,sc,n,es] == 0.0:
            return OptModel.vESSTotalCharge[p,sc,n,es]                                ==      OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[p,sc,n,es]
        elif mTEPES.pMaxCharge[p,sc,n,es] and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            return OptModel.vESSTotalCharge[p,sc,n,es] / mTEPES.pMinCharge[p,sc,n,es] == 1 + (OptModel.vCharge2ndBlock[p,sc,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[p,sc,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[p,sc,n,es]) / mTEPES.pMinCharge[p,sc,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSTotalCharge_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eESSTotalCharge       ... ', len(getattr(OptModel, 'eESSTotalCharge_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eEnergyOutflows(OptModel,p,sc,n,es):
        if mTEPES.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0 and sum(mTEPES.pEnergyOutflows[p,sc,n2,es] for n2 in mTEPES.n2):
            return sum(OptModel.vEnergyOutflows[p,sc,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - int(mTEPES.pOutflowsTimeStep[es]/mTEPES.pCycleTimeStep[es]):mTEPES.n.ord(n)]) == sum(mTEPES.pEnergyOutflows[p,sc,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eEnergyOutflows_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eEnergyOutflows       ... ', len(getattr(OptModel, 'eEnergyOutflows_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating storage operation           ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationCommitment(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Unit commitment            constraints ****')

    StartTime = time.time()

    def eMaxOutput2ndBlock(OptModel,p,sc,n,nr):
        if sum(mTEPES.pOperReserveUp[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] <= OptModel.vCommitment[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxOutput2ndBlock    ... ', len(getattr(OptModel, 'eMaxOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinOutput2ndBlock(OptModel,p,sc,n,nr):
        if sum(mTEPES.pOperReserveDw[p,sc,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pMaxPower2ndBlock[p,sc,n,nr] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinOutput2ndBlock    ... ', len(getattr(OptModel, 'eMinOutput2ndBlock_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eTotalOutput(OptModel,p,sc,n,nr):
        if   mTEPES.pMaxPower[p,sc,n,nr] and mTEPES.pMinPower[p,sc,n,nr] == 0.0:
            return OptModel.vTotalOutput[p,sc,n,nr]                               ==                                    OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]
        elif mTEPES.pMaxPower[p,sc,n,nr]:
            return OptModel.vTotalOutput[p,sc,n,nr] / mTEPES.pMinPower[p,sc,n,nr] == OptModel.vCommitment[p,sc,n,nr] + (OptModel.vOutput2ndBlock[p,sc,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[p,sc,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pMinPower[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalOutput_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, 'eTotalOutput_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eUCStrShut(OptModel,p,sc,n,nr):
        if   mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPower[p,sc,n,nr] or mTEPES.pConstantVarCost[nr]) and nr not in mTEPES.es and n == mTEPES.n.first():
            return OptModel.vCommitment[p,sc,n,nr] - mTEPES.pInitialUC[p,sc,n,nr]                   == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
        elif mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPower[p,sc,n,nr] or mTEPES.pConstantVarCost[nr]) and nr not in mTEPES.es:
            return OptModel.vCommitment[p,sc,n,nr] - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] == OptModel.vStartUp[p,sc,n,nr] - OptModel.vShutDown[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUCStrShut_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown'))

    if pIndLogConsole == 1:
        print('eUCStrShut            ... ', len(getattr(OptModel, 'eUCStrShut_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCommitment(OptModel,p,sc,n,nr):
        if len(mTEPES.g2g) and sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g):
            return OptModel.vCommitment[p,sc,n,nr]                            <= OptModel.vMaxCommitment[nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitment_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eMaxCommitment, doc='maximum of all the commitments'))

    if pIndLogConsole == 1:
        print('eMaxCommitment        ... ', len(getattr(OptModel, 'eMaxCommitment_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMaxCommitGen(OptModel,p,sc,n,g):
        if len(mTEPES.g2g) and sum(1 for gg in mTEPES.g if (g,gg) in mTEPES.g2g or (gg,g) in mTEPES.g2g) and mTEPES.pMaxPower[p,sc,n,g]:
            return OptModel.vTotalOutput[p,sc,n,g]/mTEPES.pMaxPower[p,sc,n,g] <= OptModel.vMaxCommitment[g]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitGen_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.g, rule=eMaxCommitGen, doc='maximum of all the capacity factors'))

    if pIndLogConsole == 1:
        print('eMaxCommitGen         ... ', len(getattr(OptModel, 'eMaxCommitGen_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eExclusiveGens(OptModel,g):
        if len(mTEPES.g2g) and sum(1 for gg in mTEPES.g if (gg,g) in mTEPES.g2g):
            return OptModel.vMaxCommitment[g] + sum(OptModel.vMaxCommitment[gg] for gg in mTEPES.g if (gg,g) in mTEPES.g2g) <= 1
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExclusiveGens_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.g, rule=eExclusiveGens, doc='mutually exclusive generators'))

    if pIndLogConsole == 1:
        print('eExclusiveGens        ... ', len(getattr(OptModel, 'eExclusiveGens_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating generation commitment       ... ', round(GeneratingTime), 's')


def GenerationOperationModelFormulationRampMinTime(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Ramp and min up/down time  constraints ****')

    StartTime = time.time()

    def eRampUp(OptModel,p,sc,n,nr):
        if   mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPower[p,sc,n,nr],0.0)                            + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
        elif mTEPES.pRampUp[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] - OptModel.vReserveDown[p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] + OptModel.vReserveUp  [p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[p,sc,n,nr] - OptModel.vStartUp[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUp               ... ', len(getattr(OptModel, 'eRampUp_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampDw(OptModel,p,sc,n,nr):
        if   mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[p,sc,n,nr]() - mTEPES.pMinPower[p,sc,n,nr],0.0)                            + OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[p,sc,n,nr]                   + OptModel.vShutDown[p,sc,n,nr]
        elif mTEPES.pRampDw[nr] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[p,sc,n,nr]:
            return (- OptModel.vOutput2ndBlock[p,sc,mTEPES.n.prev(n),nr] + OptModel.vReserveUp  [p,sc,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[p,sc,n,nr] - OptModel.vReserveDown[p,sc,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[p,sc,mTEPES.n.prev(n),nr] + OptModel.vShutDown[p,sc,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel,'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDw               ... ', len(getattr(OptModel, 'eRampDw_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampUpCharge(OptModel,p,sc,n,es):
        if   mTEPES.pRampUp[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge2ndBlock[p,sc,n,es] and n == mTEPES.n.first():
            return (                                                                                                            OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        elif mTEPES.pRampUp[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge2ndBlock[p,sc,n,es]:
            return (                                                                                                            OptModel.vCharge2ndBlock[p,sc,n,es] - OptModel.vESSReserveUp  [p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUpChr_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpChr            ... ', len(getattr(OptModel, 'eRampUpChr_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eRampDwCharge(OptModel,p,sc,n,es):
        if   mTEPES.pRampDw[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge[p,sc,n,es] and n == mTEPES.n.first():
            return (                                                                                                          + OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        elif mTEPES.pRampDw[es] and mTEPES.pIndBinGenRamps() == 1 and mTEPES.pMaxCharge[p,sc,n,es]:
            return (- OptModel.vCharge2ndBlock[p,sc,mTEPES.n.prev(n),es] - OptModel.vESSReserveUp  [p,sc,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[p,sc,n,es] + OptModel.vESSReserveDown[p,sc,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampDwChr_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.es, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwChr            ... ', len(getattr(OptModel, 'eRampDwChr_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinUpTime(OptModel,p,sc,n,t):
        if mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPower[p,sc,n,t] or mTEPES.pConstantVarCost[t]) and t not in mTEPES.es and mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(OptModel.vStartUp [p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[p,sc,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinUpTime_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]'))

    if pIndLogConsole == 1:
        print('eMinUpTime            ... ', len(getattr(OptModel, 'eMinUpTime_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinDownTime(OptModel,p,sc,n,t):
        if mTEPES.pMustRun[t] == 0 and mTEPES.pIndBinGenMinTime() == 1 and (mTEPES.pMinPower[p,sc,n,t] or mTEPES.pConstantVarCost[t]) and t not in mTEPES.es and mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(OptModel.vShutDown[p,sc,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[p,sc,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinDownTime_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]'))

    if pIndLogConsole == 1:
        print('eMinDownTime          ... ', len(getattr(OptModel, 'eMinDownTime_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating ramps & minimum time        ... ', round(GeneratingTime), 's')


def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    switching model constraints ****')

    StartTime = time.time()

    def eLineStateCand(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0:
            if mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] <= OptModel.vNetworkInvest[p,ni,nf,cc]
            else:
                return OptModel.vLineCommit[p,sc,n,ni,nf,cc] == OptModel.vNetworkInvest[p,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineStateCand_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole == 1:
        print('eLineStateCand        ... ', len(getattr(OptModel, 'eLineStateCand_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eSWOnOff(OptModel,p,sc,n,ni,nf,cc):
        if   mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1) and n == mTEPES.n.first():
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - mTEPES.pInitialSwitch[p,sc,n,ni,nf,cc]               == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
        elif mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1):
            return OptModel.vLineCommit[p,sc,n,ni,nf,cc] - OptModel.vLineCommit[p,sc,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[p,sc,n,ni,nf,cc] - OptModel.vLineOffState[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSWOnOff_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole == 1:
        print('eSWOnOff              ... ', len(getattr(OptModel, 'eSWOnOff_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinSwOnState(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
            return sum(OptModel.vLineOnState [p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOnState_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOnState         ... ', len(getattr(OptModel, 'eMinSwOnState_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eMinSwOffState(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
            return sum(OptModel.vLineOffState[p,sc,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOffState_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOffState        ... ', len(getattr(OptModel, 'eMinSwOffState_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Switching minimum on/off state         ... ', round(GeneratingTime), 's')


def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, p, sc, st):
    print('Network    operation model constraints ****')

    StartTime = time.time()

    def eNetCapacity1(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eNetCapacity1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.la, rule=eNetCapacity1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity1         ... ', len(getattr(OptModel, 'eNetCapacity1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eNetCapacity2(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and ((ni,nf,cc) in mTEPES.lc or mTEPES.pIndBinLineSwitch[ni,nf,cc] == 1):
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eNetCapacity2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.la, rule=eNetCapacity2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eNetCapacity2         ... ', len(getattr(OptModel, 'eNetCapacity2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eKirchhoff2ndLaw1(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pPeriodIniNet[ni,nf,cc] <= p and mTEPES.pPeriodFinNet[ni,nf,cc] >= p:
            if (ni,nf,cc) in mTEPES.lca and mTEPES.pLineX[ni,nf,cc] > 0.0:
                return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[p,sc,n,ni,nf,cc]
            else:
                return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase ==   0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLaw1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw1, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw1     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eKirchhoff2ndLaw2(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and (ni,nf,cc) in mTEPES.lca and mTEPES.pLineX[ni,nf,cc] > 0.0 and mTEPES.pPeriodIniNet[ni,nf,cc] <= p and mTEPES.pPeriodFinNet[ni,nf,cc] >= p:
            return OptModel.vFlow[p,sc,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (OptModel.vTheta[p,sc,n,ni] - OptModel.vTheta[p,sc,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - OptModel.vLineCommit[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLaw2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw2     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eLineLosses1(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses and len(mTEPES.ll):
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses1_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses1          ... ', len(getattr(OptModel, 'eLineLosses1_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    def eLineLosses2(OptModel,p,sc,n,ni,nf,cc):
        if mTEPES.pIndBinSingleNode() == 0 and mTEPES.pIndBinNetLosses and len(mTEPES.ll):
            return OptModel.vLineLosses[p,sc,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[p,sc,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses2_'+str(p)+'_'+str(sc)+'_'+str(st), Constraint(mTEPES.p, mTEPES.sc, mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses2          ... ', len(getattr(OptModel, 'eLineLosses2_'+str(p)+'_'+str(sc)+'_'+str(st))), ' rows')

    GeneratingTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating network    constraints      ... ', round(GeneratingTime), 's')
