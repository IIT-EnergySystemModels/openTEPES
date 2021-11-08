"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - November 08, 2021
"""

import time
from   collections   import defaultdict
from   pyomo.environ import Set, Constraint, Objective, Block, minimize


def InvestmentModelFormulation(OptModel, mTEPES, pIndLogConsole):
    print('Investment           model formulation ****')

    StartTime = time.time()

    def eTotalTCost(OptModel):
        return OptModel.vTotalFCost + sum(mTEPES.pScenProb[sc] * (OptModel.vTotalGCost[sc,p,n] + OptModel.vTotalCCost[sc,p,n] + OptModel.vTotalECost[sc,p,n] + OptModel.vTotalRCost[sc,p,n]) for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    OptModel.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalFCost(OptModel):
       return OptModel.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * OptModel.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pGenRetireCost[gd] * OptModel.vGenerationRetire[gd] for gd in mTEPES.gd) + sum(mTEPES.pNetFixedCost[lc] * OptModel.vNetworkInvest[lc] for lc in mTEPES.lc)
    OptModel.eTotalFCost = Constraint(rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating investment o.f.             ... ', round(GeneratingOFTime), 's')


def GenerationOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Generation operation model formulation ****')

    StartTime = time.time()

    def eTotalGCost(OptModel,sc,p,n):
        return OptModel.vTotalGCost[sc,p,n] == (sum(mTEPES.pLinearVarCost  [nr] * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vTotalOutput[sc,p,n,nr]                      +
                                                    mTEPES.pConstantVarCost[nr] * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vCommitment [sc,p,n,nr]                      +
                                                    mTEPES.pStartUpCost    [nr] * mTEPES.pLoadLevelWeight[n] *                       OptModel.vStartUp    [sc,p,n,nr]                      +
                                                    mTEPES.pShutDownCost   [nr] * mTEPES.pLoadLevelWeight[n] *                       OptModel.vShutDown   [sc,p,n,nr] for nr in mTEPES.nr) +
                                                sum(mTEPES.pLinearOMCost   [ r] * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vTotalOutput[sc,p,n, r] for  r in mTEPES.r ) )
    setattr(OptModel, 'eTotalGCost_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    def eTotalCCost(OptModel,sc,p,n):
        if sum(mTEPES.pLinearVarCost  [es] for es in mTEPES.es):
            return OptModel.vTotalCCost[sc,p,n] == sum(mTEPES.pLinearVarCost  [es] * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vESSTotalCharge[sc,p,n,es] for es in mTEPES.es)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalCCost_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,sc,p,n):
        if sum(mTEPES.pCO2EmissionCost[nr] for nr in mTEPES.nr):
            return OptModel.vTotalECost[sc,p,n] == sum(mTEPES.pCO2EmissionCost[nr] * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vTotalOutput   [sc,p,n,nr] for nr in mTEPES.nr)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalECost_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalRCost(OptModel,sc,p,n):
        return     OptModel.vTotalRCost[sc,p,n] == sum(mTEPES.pENSCost             * mTEPES.pLoadLevelWeight[n] * mTEPES.pDuration[n] * OptModel.vENS           [sc,p,n,nd] for nd in mTEPES.nd)
    setattr(OptModel, 'eTotalRCost_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    if pIndLogConsole == 1:
        print('Generating operation  o.f.             ... ', round(GeneratingOFTime), 's')

    StartTime = time.time()

    #%% constraints

    def eInstalGenComm(OptModel,sc,p,n,gc):
        if gc in mTEPES.nr and gc not in mTEPES.es and mTEPES.pMustRun[gc] == 0 and (mTEPES.pMinPower[sc,p,n,gc] > 0.0 or mTEPES.pConstantVarCost[gc] > 0.0):
            return OptModel.vCommitment[sc,p,n,gc] <= OptModel.vGenerationInvest[gc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalGenComm_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment  if installed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenComm        ... ', len(getattr(OptModel, 'eInstalGenComm_'+st)), ' rows')

    def eInstalGenCap(OptModel,sc,p,n,gc):
        if mTEPES.pMaxPower[sc,p,n,gc]:
            return OptModel.vTotalOutput[sc,p,n,gc] / mTEPES.pMaxPower[sc,p,n,gc] <= OptModel.vGenerationInvest[gc]
        else:
            return OptModel.vTotalOutput[sc,p,n,gc]                               <= 0.0
    setattr(OptModel, 'eInstalGenCap_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output      if installed gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenCap         ... ', len(getattr(OptModel, 'eInstalGenCap_'+st)), ' rows')

    def eInstalConESS(OptModel,sc,p,n,ec):
        return OptModel.vESSTotalCharge [sc,p,n,ec] / mTEPES.pMaxCharge[sc,p,n,ec] <= OptModel.vGenerationInvest[ec]
    setattr(OptModel, 'eInstalConESS_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalConESS         ... ', len(getattr(OptModel, 'eInstalConESS_'+st)), ' rows')

    def eAdequacyReserveMargin(OptModel,ar):
        if mTEPES.pReserveMargin[ar] and sum(1 for g in mTEPES.g if (ar,g) in mTEPES.a2g):
            return ((sum(                                 mTEPES.pRatedMaxPower[g ] * mTEPES.pAvailability[g ] / (1.0-mTEPES.pEFOR[g ]) for g  in mTEPES.g  if (ar,g ) in mTEPES.a2g and g not in mTEPES.gc) +
                     sum(OptModel.vGenerationInvest[gc] * mTEPES.pRatedMaxPower[gc] * mTEPES.pAvailability[gc] / (1.0-mTEPES.pEFOR[gc]) for gc in mTEPES.gc if (ar,gc) in mTEPES.a2g                       ) ) >= mTEPES.pPeakDemand[ar] * mTEPES.pReserveMargin[ar])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eAdequacyReserveMargin_'+st, Constraint(mTEPES.ar, rule=eAdequacyReserveMargin, doc='system adequacy reserve margin [p.u.]'))

    if pIndLogConsole == 1:
        print('eAdequacyReserveMargin... ', len(getattr(OptModel, 'eAdequacyReserveMargin_'+st)), ' rows')

    def eSystemInertia(OptModel,sc,p,n,ar):
        if mTEPES.pSystemInertia[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vCommitment[sc,p,n,nr] * mTEPES.pInertia[nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) >= mTEPES.pSystemInertia[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSystemInertia_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eSystemInertia, doc='system inertia [s]'))

    if pIndLogConsole == 1:
        print('eSystemInertia        ... ', len(getattr(OptModel, 'eSystemInertia_'+st)), ' rows')

    #%%
    def eOperReserveUp(OptModel,sc,p,n,ar):
        if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vReserveUp  [sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(OptModel.vESSReserveUp  [sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveUp[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveUp_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveUp        ... ', len(getattr(OptModel, 'eOperReserveUp_'+st)), ' rows')

    def eOperReserveDw(OptModel,sc,p,n,ar):
        if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vReserveDown[sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(OptModel.vESSReserveDown[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveDw[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveDw_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveDw        ... ', len(getattr(OptModel, 'eOperReserveDw_'+st)), ' rows')

    #%%
    def eReserveUpIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,es]:
            return OptModel.vReserveUp  [sc,p,n,es] <=                                  OptModel.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveUpIfEnergy_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveUpIfEnergy    ... ', len(getattr(OptModel, 'eReserveUpIfEnergy_'+st)), ' rows')

    def eReserveDwIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,es]:
            return OptModel.vReserveDown[sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - OptModel.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveDwIfEnergy_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveDwIfEnergy    ... ', len(getattr(OptModel, 'eReserveDwIfEnergy_'+st)), ' rows')

    def eESSReserveUpIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return OptModel.vESSReserveUp  [sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - OptModel.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveUpIfEnergy_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveUpIfEnergy ... ', len(getattr(OptModel, 'eESSReserveUpIfEnergy_'+st)), ' rows')

    def eESSReserveDwIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return OptModel.vESSReserveDown[sc,p,n,es] <=                                  OptModel.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveDwIfEnergy_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveDwIfEnergy ... ', len(getattr(OptModel, 'eESSReserveDwIfEnergy_'+st)), ' rows')

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

    #%%
    def eBalance(OptModel,sc,p,n,nd):
        if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(OptModel.vTotalOutput[sc,p,n,g] for g in mTEPES.g if (nd,g) in mTEPES.n2g) - sum(OptModel.vESSTotalCharge[sc,p,n,es] for es in mTEPES.es if (nd,es) in mTEPES.n2g) + OptModel.vENS[sc,p,n,nd] == mTEPES.pDemand[sc,p,n,nd] +
                    sum(OptModel.vLineLosses[sc,p,n,nd,lout ] for lout  in loutl[nd]) + sum(OptModel.vFlow[sc,p,n,nd,lout ] for lout  in lout[nd]) +
                    sum(OptModel.vLineLosses[sc,p,n,ni,nd,cc] for ni,cc in linl [nd]) - sum(OptModel.vFlow[sc,p,n,ni,nd,cc] for ni,cc in lin [nd]))
        else:
            return Constraint.Skip
    setattr(OptModel, 'eBalance_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance, doc='load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalance              ... ', len(getattr(OptModel, 'eBalance_'+st)), ' rows')

    def eESSInventory(OptModel,sc,p,n,es):
        if   mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[sc,p,n,es]                                            + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - OptModel.vEnergyOutflows[sc,p,n2,es] - OptModel.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[sc,p,n,es] + OptModel.vESSSpillage[sc,p,n,es]
        elif mTEPES.n.ord(n) >  mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vESSInventory[sc,p,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - OptModel.vEnergyOutflows[sc,p,n2,es] - OptModel.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[sc,p,n,es] + OptModel.vESSSpillage[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSInventory_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole == 1:
        print('eESSInventory         ... ', len(getattr(OptModel, 'eESSInventory_'+st)), ' rows')

    GeneratingRBITime = time.time() - StartTime
    StartTime         = time.time()
    if pIndLogConsole == 1:
        print('Generating reserves/balance/inventory  ... ', round(GeneratingRBITime), 's')

    #%%
    def eMaxCharge(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[sc,p,n,es]:
            return (OptModel.vCharge2ndBlock[sc,p,n,es]+ OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge[sc,p,n,es] <= 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCharge_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCharge            ... ', len(getattr(OptModel, 'eMaxCharge_'+st)), ' rows')

    def eMinCharge(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[sc,p,n,es]:
            return (OptModel.vCharge2ndBlock[sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pMaxCharge[sc,p,n,es] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinCharge_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinCharge            ... ', len(getattr(OptModel, 'eMinCharge_'+st)), ' rows')

    # def eChargeDischarge(OptModel,sc,p,n,es):
    #     if mTEPES.pMaxCharge[sc,p,n,es]:
    #         return OptModel.vTotalOutput[sc,p,n,es] / mTEPES.pMaxPower[sc,p,n,es] + OptModel.vCharge2ndBlock[sc,p,n,es] / mTEPES.pMaxCharge[sc,p,n,es] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(OptModel,sc,p,n,es):
        if mTEPES.pMaxCharge[sc,p,n,es]:
            if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
                return ((OptModel.vOutput2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [sc,p,n,es]) / mTEPES.pMaxPower2ndBlock [sc,p,n,es] +
                        (OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge2ndBlock[sc,p,n,es] <= 1.0)
            else:
                return ((OptModel.vOutput2ndBlock[sc,p,n,es]                                                                    ) / mTEPES.pMaxPower2ndBlock [sc,p,n,es] +
                        (OptModel.vCharge2ndBlock[sc,p,n,es]                                                                    ) / mTEPES.pMaxCharge2ndBlock[sc,p,n,es] <= 1.0)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eChargeDischarge_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeDischarge      ... ', len(getattr(OptModel, 'eChargeDischarge_'+st)), ' rows')

    def eESSTotalCharge(OptModel,sc,p,n,es):
        if   mTEPES.pMaxCharge[sc,p,n,es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es] and mTEPES.pMinCharge[sc,p,n,es] == 0.0:
            return OptModel.vESSTotalCharge[sc,p,n,es]                                ==      OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[sc,p,n,es]
        elif mTEPES.pMaxCharge[sc,p,n,es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return OptModel.vESSTotalCharge[sc,p,n,es] / mTEPES.pMinCharge[sc,p,n,es] == 1 + (OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[sc,p,n,es]) / mTEPES.pMinCharge[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSTotalCharge_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eESSTotalCharge       ... ', len(getattr(OptModel, 'eESSTotalCharge_'+st)), ' rows')

    def eEnergyOutflows(OptModel,sc,p,n,es):
        if mTEPES.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0 and sum(mTEPES.pEnergyOutflows[sc,p,n2,es] for n2 in mTEPES.n2):
            return sum(OptModel.vEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - int(mTEPES.pOutflowsTimeStep[es]/mTEPES.pCycleTimeStep[es]):mTEPES.n.ord(n)]) == sum(mTEPES.pEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eEnergyOutflows_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eEnergyOutflows       ... ', len(getattr(OptModel, 'eEnergyOutflows_'+st)), ' rows')

    #%%
    def eMaxOutput2ndBlock(OptModel,sc,p,n,nr):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (OptModel.vOutput2ndBlock[sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] <= OptModel.vCommitment[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxOutput2ndBlock_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxOutput2ndBlock    ... ', len(getattr(OptModel, 'eMaxOutput2ndBlock_'+st)), ' rows')

    def eMinOutput2ndBlock(OptModel,sc,p,n,nr):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (OptModel.vOutput2ndBlock[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinOutput2ndBlock_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinOutput2ndBlock    ... ', len(getattr(OptModel, 'eMinOutput2ndBlock_'+st)), ' rows')

    def eTotalOutput(OptModel,sc,p,n,nr):
        if   mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMinPower[sc,p,n,nr] == 0.0:
            return OptModel.vTotalOutput[sc,p,n,nr]                               ==                                    OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr]
        elif mTEPES.pMaxPower[sc,p,n,nr]:
            return OptModel.vTotalOutput[sc,p,n,nr] / mTEPES.pMinPower[sc,p,n,nr] == OptModel.vCommitment[sc,p,n,nr] + (OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pMinPower[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalOutput_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, 'eTotalOutput_'+st)), ' rows')

    def eUCStrShut(OptModel,sc,p,n,nr):
        if   mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPower[sc,p,n,nr] or mTEPES.pConstantVarCost[nr]) and nr not in mTEPES.es and n == mTEPES.n.first():
            return OptModel.vCommitment[sc,p,n,nr] - mTEPES.pInitialUC[sc,p,n,nr]                   == OptModel.vStartUp[sc,p,n,nr] - OptModel.vShutDown[sc,p,n,nr]
        elif mTEPES.pMustRun[nr] == 0 and (mTEPES.pMinPower[sc,p,n,nr] or mTEPES.pConstantVarCost[nr]) and nr not in mTEPES.es:
            return OptModel.vCommitment[sc,p,n,nr] - OptModel.vCommitment[sc,p,mTEPES.n.prev(n),nr] == OptModel.vStartUp[sc,p,n,nr] - OptModel.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUCStrShut_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown'))

    if pIndLogConsole == 1:
        print('eUCStrShut            ... ', len(getattr(OptModel, 'eUCStrShut_'+st)), ' rows')

    def eMaxCommitment(OptModel,sc,p,n,nr):
        if sum(1 for g in mTEPES.nr if (nr,g) in mTEPES.g2g or (g,nr) in mTEPES.g2g):
            return OptModel.vCommitment[sc,p,n,nr] <= OptModel.vMaxCommitment[nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitment_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMaxCommitment, doc='maximum of all the commitments'))

    if pIndLogConsole == 1:
        print('eMaxCommitment        ... ', len(getattr(OptModel, 'eMaxCommitment_'+st)), ' rows')

    def eMaxCommitGen(OptModel,sc,p,n,g):
        if sum(1 for gg in mTEPES.gg if (g,gg) in mTEPES.g2g or (gg,g) in mTEPES.g2g) and mTEPES.pMaxPower[sc,p,n,g]:
            return OptModel.vTotalOutput[sc,p,n,g]/mTEPES.pMaxPower[sc,p,n,g] <= OptModel.vMaxCommitment[g]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCommitGen_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.g, rule=eMaxCommitGen, doc='maximum of all the capacity factors'))

    if pIndLogConsole == 1:
        print('eMaxCommitGen         ... ', len(getattr(OptModel, 'eMaxCommitGen_'+st)), ' rows')

    def eExclusiveGens(OptModel,g):
        if sum(1 for gg in mTEPES.gg if (gg,g) in mTEPES.g2g):
            return OptModel.vMaxCommitment[g] + sum(OptModel.vMaxCommitment[gg] for gg in mTEPES.gg if (gg,g) in mTEPES.g2g) <= 1
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExclusiveGens_'+st, Constraint(mTEPES.g, rule=eExclusiveGens, doc='mutually exclusive generators'))

    if pIndLogConsole == 1:
        print('eExclusiveGens        ... ', len(getattr(OptModel, 'eExclusiveGens_'+st)), ' rows')

    GeneratingGenConsTime = time.time() - StartTime
    StartTime             = time.time()
    if pIndLogConsole == 1:
        print('Generating generation constraints      ... ', round(GeneratingGenConsTime), 's')

    #%%
    def eRampUp(OptModel,sc,p,n,nr):
        if   mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[sc,p,n,nr]() - mTEPES.pMinPower[sc,p,n,nr],0.0)                            + OptModel.vOutput2ndBlock[sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[sc,p,n,nr] - OptModel.vStartUp[sc,p,n,nr]
        elif mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- OptModel.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] - OptModel.vReserveDown[sc,p,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[sc,p,n,nr] - OptModel.vStartUp[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUp_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUp               ... ', len(getattr(OptModel, 'eRampUp_'+st)), ' rows')

    def eRampDw(OptModel,sc,p,n,nr):
        if   mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[sc,p,n,nr]() - mTEPES.pMinPower[sc,p,n,nr],0.0)                            + OptModel.vOutput2ndBlock[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[sc,p,n,nr]                   + OptModel.vShutDown[sc,p,n,nr]
        elif mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- OptModel.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] + OptModel.vReserveUp  [sc,p,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[sc,p,mTEPES.n.prev(n),nr] + OptModel.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel,'eRampDw_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDw               ... ', len(getattr(OptModel, 'eRampDw_'+st)), ' rows')

    def eRampUpCharge(OptModel,sc,p,n,es):
        if   mTEPES.pRampUp[es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es] and n == mTEPES.n.first():
            return (                                                                                                          + OptModel.vCharge2ndBlock[sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        elif mTEPES.pRampUp[es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return (- OptModel.vCharge2ndBlock[sc,p,mTEPES.n.prev(n),es] + OptModel.vESSReserveDown[sc,p,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUpChr_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpChr            ... ', len(getattr(OptModel, 'eRampUpChr_'+st)), ' rows')

    def eRampDwCharge(OptModel,sc,p,n,es):
        if   mTEPES.pRampDw[es] and mTEPES.pMaxCharge[sc,p,n,es] and n == mTEPES.n.first():
            return (                                                                                                          + OptModel.vCharge2ndBlock[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <= 1.0
        elif mTEPES.pRampDw[es] and mTEPES.pMaxCharge[sc,p,n,es]:
            return (- OptModel.vCharge2ndBlock[sc,p,mTEPES.n.prev(n),es] - OptModel.vESSReserveUp  [sc,p,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <= 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampDwChr_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwChr            ... ', len(getattr(OptModel, 'eRampDwChr_'+st)), ' rows')

    GeneratingRampsTime = time.time() - StartTime
    StartTime           = time.time()
    if pIndLogConsole == 1:
        print('Generating ramps   up/down             ... ', round(GeneratingRampsTime), 's')

    #%%
    def eMinUpTime(OptModel,sc,p,n,t):
        if mTEPES.pMustRun[t] == 0 and (mTEPES.pMinPower[sc,p,n,t] or mTEPES.pConstantVarCost[t]) and t not in mTEPES.es and mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(OptModel.vStartUp [sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinUpTime_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]'))

    if pIndLogConsole == 1:
        print('eMinUpTime            ... ', len(getattr(OptModel, 'eMinUpTime_'+st)), ' rows')

    def eMinDownTime(OptModel,sc,p,n,t):
        if mTEPES.pMustRun[t] == 0 and (mTEPES.pMinPower[sc,p,n,t] or mTEPES.pConstantVarCost[t]) and t not in mTEPES.es and mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(OptModel.vShutDown[sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinDownTime_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]'))

    if pIndLogConsole == 1:
        print('eMinDownTime          ... ', len(getattr(OptModel, 'eMinDownTime_'+st)), ' rows')

    GeneratingMinUDTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating minimum up/down time        ... ', round(GeneratingMinUDTime), 's')


def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Network    switching model formulation ****')

    StartTime = time.time()
    #%%
    def eLineStateCand(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pLineSwitching[ni,nf,cc] == 1:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] <= OptModel.vNetworkInvest[ni,nf,cc]
        else:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] == OptModel.vNetworkInvest[ni,nf,cc]
    setattr(OptModel, 'eLineStateCand_' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole == 1:
        print('eLineStateCand        ... ', len(getattr(OptModel, 'eLineStateCand_' + str(st))), ' rows')

    def eLineSwtStageToLevel(OptModel,sc,p,ss,n,ni,nf,cc):
        if mTEPES.pLineSwitching[ni,nf,cc] == 1 and mTEPES.pIndSwitchingStage() == 1:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] == OptModel.vSwitchingStage[sc,p,ss,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineSwtStageToLevel_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.ss2n, rule=eLineSwtStageToLevel, doc='constraints between line commitment per load level and per stage'))

    if pIndLogConsole == 1:
        print('eLineSwtStageToLevel  ... ', len(getattr(OptModel, 'eLineSwtStageToLevel_'+st)), ' rows')

    def eSWOnOff(OptModel,sc,p,n,ni,nf,cc):
        if   mTEPES.pLineSwitching[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1) and n == mTEPES.n.first():
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] - mTEPES.pInitialSwitch[sc,p,n,ni,nf,cc]               == OptModel.vLineOnState[sc,p,n,ni,nf,cc] - OptModel.vLineOffState[sc,p,n,ni,nf,cc]
        elif mTEPES.pLineSwitching[ni,nf,cc] == 1 and (mTEPES.pSwOnTime[ni,nf,cc] > 1 or mTEPES.pSwOffTime[ni,nf,cc] > 1):
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] - OptModel.vLineCommit[sc,p,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[sc,p,n,ni,nf,cc] - OptModel.vLineOffState[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSWOnOff_' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole == 1:
        print('eSWOnOff              ... ', len(getattr(OptModel, 'eSWOnOff_'+st)), ' rows')

    SwitchingLogicalRelation = time.time() - StartTime
    StartTime                = time.time()
    if pIndLogConsole == 1:
        print('Switching logical relation             ... ', round(SwitchingLogicalRelation), 's')

    def eMinSwOnState(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pLineSwitching[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
            return sum(OptModel.vLineOnState [sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOnState_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOnState         ... ', len(getattr(OptModel, 'eMinSwOnState_'+st)), ' rows')

    def eMinSwOffState(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pLineSwitching[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
            return sum(OptModel.vLineOffState[sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOffState_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOffState        ... ', len(getattr(OptModel, 'eMinSwOffState_'+st)), ' rows')

    SwitchingMinStateTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Switching minimum on/off state         ... ', round(SwitchingMinStateTime), 's')


def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Network    operation model formulation ****')

    StartTime = time.time()
    #%%
    def eExistNetCap1(OptModel,sc,p,n,ni,nf,cc):
        if (ni,nf,cc) in mTEPES.lc or mTEPES.pLineSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExistNetCap1_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eExistNetCap1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eExistNetCap1         ... ', len(getattr(OptModel, 'eExistNetCap1_'+st)), ' rows')

    def eExistNetCap2(OptModel,sc,p,n,ni,nf,cc):
        if (ni,nf,cc) in mTEPES.lc or mTEPES.pLineSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExistNetCap2_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eExistNetCap2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eExistNetCap2         ... ', len(getattr(OptModel, 'eExistNetCap2_'+st)), ' rows')

    #%%
    def eKirchhoff2ndLaw1(OptModel,sc,p,n,ni,nf,cc):
        if (ni,nf,cc) in mTEPES.lca:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase ==   0
    setattr(OptModel, 'eKirchhoff2ndLaw1_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw1, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw1     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw1_'+st)), ' rows')

    def eKirchhoff2ndLaw2(OptModel,sc,p,n,ni,nf,cc):
        if (ni,nf,cc) in mTEPES.lca:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLaw2_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLaw2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLaw2     ... ', len(getattr(OptModel, 'eKirchhoff2ndLaw2_'+st)), ' rows')

    def eLineLosses1(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses() and len(mTEPES.ll):
            return OptModel.vLineLosses[sc,p,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses1_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses1          ... ', len(getattr(OptModel, 'eLineLosses1_'+st)), ' rows')

    def eLineLosses2(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses() and len(mTEPES.ll):
            return OptModel.vLineLosses[sc,p,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eLineLosses2_'+st, Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses2          ... ', len(getattr(OptModel, 'eLineLosses2_'+st)), ' rows')

    GeneratingNetConsTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating network    constraints      ... ', round(GeneratingNetConsTime), 's')
