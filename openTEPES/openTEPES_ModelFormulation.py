"""
Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - April 24, 2021
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
       return OptModel.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * OptModel.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pNetFixedCost[lc] * OptModel.vNetworkInvest[lc] for lc in mTEPES.lc)
    OptModel.eTotalFCost = Constraint(rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating investment o.f.             ... ', round(GeneratingOFTime), 's')


def GenerationOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Generation operation model formulation ****')

    StartTime = time.time()

    def eTotalGCost(OptModel,sc,p,n):
        return OptModel.vTotalGCost[sc,p,n] == (sum(mTEPES.pLinearVarCost  [nr] * mTEPES.pDuration[n] * OptModel.vTotalOutput[sc,p,n,nr]                      +
                                                  mTEPES.pConstantVarCost[nr] * mTEPES.pDuration[n] * OptModel.vCommitment [sc,p,n,nr]                      +
                                                  mTEPES.pStartUpCost    [nr] *                       OptModel.vStartUp    [sc,p,n,nr]                      +
                                                  mTEPES.pShutDownCost   [nr] *                       OptModel.vShutDown   [sc,p,n,nr] for nr in mTEPES.nr) +
                                              sum(mTEPES.pLinearOMCost   [ r] * mTEPES.pDuration[n] * OptModel.vTotalOutput[sc,p,n, r] for  r in mTEPES.r ) )
    setattr(OptModel, 'eTotalGCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    def eTotalCCost(OptModel,sc,p,n):
        if sum(mTEPES.pLinearVarCost  [es] for es in mTEPES.es):
            return OptModel.vTotalCCost[sc,p,n] == sum(mTEPES.pLinearVarCost  [es] * mTEPES.pDuration[n] * OptModel.vESSTotalCharge[sc,p,n,es] for es in mTEPES.es)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalCCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(OptModel,sc,p,n):
        if sum(mTEPES.pCO2EmissionCost[nr] for nr in mTEPES.nr):
            return OptModel.vTotalECost[sc,p,n] == sum(mTEPES.pCO2EmissionCost[nr] * mTEPES.pDuration[n] * OptModel.vTotalOutput   [sc,p,n,nr] for nr in mTEPES.nr)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalECost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalRCost(OptModel,sc,p,n):
        return OptModel.vTotalRCost[sc,p,n] == sum(mTEPES.pENSCost             * mTEPES.pDuration[n] * OptModel.vENS           [sc,p,n,nd] for nd in mTEPES.nd)
    setattr(OptModel, 'eTotalRCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    if pIndLogConsole == 1:
        print('Generating operation  o.f.             ... ', round(GeneratingOFTime), 's')

    StartTime = time.time()

    #%% constraints
    def eInstalGenComm(OptModel,sc,p,n,gc):
        if gc == mTEPES.nr:
            return OptModel.vCommitment[sc,p,n,gc] <= OptModel.vGenerationInvest[gc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eInstalGenComm_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment  if installed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenComm        ... ', len(getattr(OptModel, 'eInstalGenComm_stage'+str(st))), ' rows')

    def eInstalGenCap(OptModel,sc,p,n,gc):
        if mTEPES.pMaxPower[sc,p,n,gc]:
            return OptModel.vTotalOutput[sc,p,n,gc] / mTEPES.pMaxPower[sc,p,n,gc] <= OptModel.vGenerationInvest[gc]
        else:
            return OptModel.vTotalOutput[sc,p,n,gc]                               <= 0.0
    setattr(OptModel, 'eInstalGenCap_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output      if installed gen unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalGenCap         ... ', len(getattr(OptModel, 'eInstalGenCap_stage'+str(st))), ' rows')

    def eInstalConESS(OptModel,sc,p,n,ec):
        return OptModel.vESSTotalCharge [sc,p,n,ec] / mTEPES.pMaxCharge[sc,p,n,ec] <= OptModel.vGenerationInvest[ec]
    setattr(OptModel, 'eInstalConESS_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eInstalConESS         ... ', len(getattr(OptModel, 'eInstalConESS_stage'+str(st))), ' rows')

    #%%
    def eOperReserveUp(OptModel,sc,p,n,ar):
        if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vReserveUp  [sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(OptModel.vESSReserveUp  [sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveUp[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveUp_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveUp        ... ', len(getattr(OptModel, 'eOperReserveUp_stage'+str(st))), ' rows')

    def eOperReserveDw(OptModel,sc,p,n,ar):
        if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(OptModel.vReserveDown[sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(OptModel.vESSReserveDown[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveDw[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eOperReserveDw_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    if pIndLogConsole == 1:
        print('eOperReserveDw        ... ', len(getattr(OptModel, 'eOperReserveDw_stage'+str(st))), ' rows')

    #%%
    def eReserveUpIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,es]:
            return OptModel.vReserveUp  [sc,p,n,es] <=                                  OptModel.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveUpIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveUpIfEnergy    ... ', len(getattr(OptModel, 'eReserveUpIfEnergy_stage'+str(st))), ' rows')

    def eReserveDwIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,es]:
            return OptModel.vReserveDown[sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - OptModel.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eReserveDwIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eReserveDwIfEnergy    ... ', len(getattr(OptModel, 'eReserveDwIfEnergy_stage'+str(st))), ' rows')

    def eESSReserveUpIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return OptModel.vESSReserveUp  [sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - OptModel.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveUpIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveUpIfEnergy ... ', len(getattr(OptModel, 'eESSReserveUpIfEnergy_stage'+str(st))), ' rows')

    def eESSReserveDwIfEnergy(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return OptModel.vESSReserveDown[sc,p,n,es] <=                                  OptModel.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSReserveDwIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    if pIndLogConsole == 1:
        print('eESSReserveDwIfEnergy ... ', len(getattr(OptModel, 'eESSReserveDwIfEnergy_stage'+str(st))), ' rows')

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
    setattr(OptModel, 'eBalance_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance, doc='load generation balance [GW]'))

    if pIndLogConsole == 1:
        print('eBalance              ... ', len(getattr(OptModel, 'eBalance_stage'+str(st))), ' rows')

    def eESSInventory(OptModel,sc,p,n,es):
        if   mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[sc,p,n,es]                                            + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - OptModel.vEnergyOutflows[sc,p,n2,es] - OptModel.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[sc,p,n,es] + OptModel.vESSSpillage[sc,p,n,es]
        elif mTEPES.n.ord(n) >  mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return OptModel.vESSInventory[sc,p,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - OptModel.vEnergyOutflows[sc,p,n2,es] - OptModel.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*OptModel.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == OptModel.vESSInventory[sc,p,n,es] + OptModel.vESSSpillage[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSInventory_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    if pIndLogConsole == 1:
        print('eESSInventory         ... ', len(getattr(OptModel, 'eESSInventory_stage'+str(st))), ' rows')

    GeneratingRBITime = time.time() - StartTime
    StartTime         = time.time()
    if pIndLogConsole == 1:
        print('Generating reserves/balance/inventory  ... ', round(GeneratingRBITime), 's')

    #%%
    def eMaxCharge(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[sc,p,n,es]:
            return (OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge[sc,p,n,es] <= 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxCharge            ... ', len(getattr(OptModel, 'eMaxCharge_stage'+str(st))), ' rows')

    def eMinCharge(OptModel,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[sc,p,n,es]:
            return (OptModel.vCharge2ndBlock[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp  [sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pMaxCharge[sc,p,n,es] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinCharge            ... ', len(getattr(OptModel, 'eMinCharge_stage'+str(st))), ' rows')

    # def eChargeDischarge(OptModel,sc,p,n,es):
    #     if mTEPES.pMaxCharge[sc,p,n,es]:
    #         return OptModel.vTotalOutput[sc,p,n,es] / mTEPES.pMaxPower[sc,p,n,es] + OptModel.vCharge2ndBlock[sc,p,n,es] / mTEPES.pMaxCharge[sc,p,n,es] <= 1
    #     else:
    #         return Constraint.Skip
    # OptModel.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(OptModel,sc,p,n,es):
        if mTEPES.pMaxCharge[sc,p,n,es]:
            if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
                return ((OptModel.vOutput2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vReserveUp     [sc,p,n,es] + OptModel.vReserveUp     [sc,p,n,es]) / mTEPES.pMaxPower2ndBlock [sc,p,n,es] +
                        (OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge2ndBlock[sc,p,n,es] <= 1.0)
            else:
                return ((OptModel.vOutput2ndBlock[sc,p,n,es]                                                                                                          ) / mTEPES.pMaxPower2ndBlock [sc,p,n,es] +
                        (OptModel.vCharge2ndBlock[sc,p,n,es]                                                                                                          ) / mTEPES.pMaxCharge2ndBlock[sc,p,n,es] <= 1.0)
        else:
            return Constraint.Skip
    setattr(OptModel, 'eChargeDischarge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    if pIndLogConsole == 1:
        print('eChargeDischarge      ... ', len(getattr(OptModel, 'eChargeDischarge_stage'+str(st))), ' rows')

    def eESSTotalCharge(OptModel,sc,p,n,es):
        if mTEPES.pMaxCharge[sc,p,n,es]:
            return OptModel.vESSTotalCharge[sc,p,n,es] == OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eESSTotalCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eESSTotalCharge       ... ', len(getattr(OptModel, 'eESSTotalCharge_stage'+str(st))), ' rows')

    def eEnergyOutflows(OptModel,sc,p,n,es):
        if mTEPES.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0 and sum(mTEPES.pEnergyOutflows[sc,p,n2,es] for n2 in mTEPES.n2):
            return sum(OptModel.vEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - int(mTEPES.pOutflowsTimeStep[es]/mTEPES.pCycleTimeStep[es]):mTEPES.n.ord(n)]) == sum(mTEPES.pEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)])
        else:
            return Constraint.Skip
    setattr(OptModel, 'eEnergyOutflows_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    if pIndLogConsole == 1:
        print('eEnergyOutflows       ... ', len(getattr(OptModel, 'eEnergyOutflows_stage'+str(st))), ' rows')

    #%%
    def eMaxOutput2ndBlock(OptModel,sc,p,n,nr):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp  [sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] <= OptModel.vCommitment[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMaxOutput2ndBlock_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMaxOutput2ndBlock    ... ', len(getattr(OptModel, 'eMaxOutput2ndBlock_stage'+str(st))), ' rows')

    def eMinOutput2ndBlock(OptModel,sc,p,n,nr):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (OptModel.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] >= 0.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinOutput2ndBlock_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    if pIndLogConsole == 1:
        print('eMinOutput2ndBlock    ... ', len(getattr(OptModel, 'eMinOutput2ndBlock_stage'+str(st))), ' rows')

    def eTotalOutput(OptModel,sc,p,n,nr):
        if mTEPES.pMinPower[sc,p,n,nr] == 0.0 and mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return OptModel.vTotalOutput[sc,p,n,nr]                               ==                                    OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr]
        elif                                      mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return OptModel.vTotalOutput[sc,p,n,nr] / mTEPES.pMinPower[sc,p,n,nr] == OptModel.vCommitment[sc,p,n,nr] + (OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pMinPower[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eTotalOutput_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, 'eTotalOutput_stage'+str(st))), ' rows')

    def eUCStrShut(OptModel,sc,p,n,nr):
        if n == mTEPES.n.first() and mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr] and nr not in mTEPES.es:
            return OptModel.vCommitment[sc,p,n,nr] - mTEPES.pInitialUC[sc,p,n,nr]                 == OptModel.vStartUp[sc,p,n,nr] - OptModel.vShutDown[sc,p,n,nr]
        elif                         mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr] and nr not in mTEPES.es:
            return OptModel.vCommitment[sc,p,n,nr] - OptModel.vCommitment[sc,p,mTEPES.n.prev(n),nr] == OptModel.vStartUp[sc,p,n,nr] - OptModel.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eUCStrShut_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown'))

    if pIndLogConsole == 1:
        print('eUCStrShut            ... ', len(getattr(OptModel, 'eUCStrShut_stage'+str(st))), ' rows')

    if pIndLogConsole == 1:
        print('eTotalOutput          ... ', len(getattr(OptModel, 'eTotalOutput_stage'+str(st))), ' rows')

    GeneratingGenConsTime = time.time() - StartTime
    StartTime             = time.time()
    if pIndLogConsole == 1:
        print('Generating generation constraints      ... ', round(GeneratingGenConsTime), 's')

    #%%
    def eRampUp(OptModel,sc,p,n,nr):
        if   mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[sc,p,n,nr]() - mTEPES.pMinPower[sc,p,n,nr],0.0)                                                          + OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp  [sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[sc,p,n,nr] - OptModel.vStartUp[sc,p,n,nr]
        elif mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- OptModel.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] - mTEPES.pUpReserveActivation * OptModel.vReserveUp  [sc,p,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * OptModel.vReserveUp  [sc,p,n,nr] + OptModel.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   OptModel.vCommitment[sc,p,n,nr] - OptModel.vStartUp[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUp_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUp               ... ', len(getattr(OptModel, 'eRampUp_stage'+str(st))), ' rows')

    def eRampDw(OptModel,sc,p,n,nr):
        if   mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[sc,p,n,nr]() - mTEPES.pMinPower[sc,p,n,nr],0.0)                                                          + OptModel.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[sc,p,n,nr]                                                                                           + OptModel.vShutDown[sc,p,n,nr]
        elif mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- OptModel.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] + mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,mTEPES.n.prev(n),nr] + OptModel.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * OptModel.vReserveDown[sc,p,n,nr] - OptModel.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - OptModel.vCommitment[sc,p,mTEPES.n.prev(n),nr] + OptModel.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(OptModel,'eRampDw_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDw               ... ', len(getattr(OptModel, 'eRampDw_stage'+str(st))), ' rows')

    def eRampUpCharge(OptModel,sc,p,n,es):
        if   mTEPES.pRampUp[es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es] and n == mTEPES.n.first():
            return (                                                                                                                                        + OptModel.vCharge2ndBlock[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp  [sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        elif mTEPES.pRampUp[es] and mTEPES.pMaxCharge2ndBlock[sc,p,n,es]:
            return (- OptModel.vCharge2ndBlock[sc,p,mTEPES.n.prev(n),es] + mTEPES.pDwReserveActivation * OptModel.vESSReserveUp  [sc,p,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[sc,p,n,es] - mTEPES.pDwReserveActivation * OptModel.vESSReserveUp  [sc,p,n,es] - OptModel.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampUpChr_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampUpChr            ... ', len(getattr(OptModel, 'eRampUpChr_stage'+str(st))), ' rows')

    def eRampDwCharge(OptModel,sc,p,n,es):
        if   mTEPES.pRampDw[es] and mTEPES.pMaxCharge[sc,p,n,es] and n == mTEPES.n.first():
            return (                                                                                                                                       + OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        elif mTEPES.pRampDw[es] and mTEPES.pMaxCharge[sc,p,n,es]:
            return (- OptModel.vCharge2ndBlock[sc,p,mTEPES.n.prev(n),es] - mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,mTEPES.n.prev(n),es] + OptModel.vCharge2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * OptModel.vESSReserveDown[sc,p,n,es] + OptModel.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        else:
            return Constraint.Skip
    setattr(OptModel, 'eRampDwChr_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    if pIndLogConsole == 1:
        print('eRampDwChr            ... ', len(getattr(OptModel, 'eRampDwChr_stage'+str(st))), ' rows')

    GeneratingRampsTime = time.time() - StartTime
    StartTime           = time.time()
    if pIndLogConsole == 1:
        print('Generating ramps   up/down             ... ', round(GeneratingRampsTime), 's')

    #%%
    def eMinUpTime(OptModel,sc,p,n,t):
        if mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(OptModel.vStartUp [sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     OptModel.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinUpTime_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]'))

    if pIndLogConsole == 1:
        print('eMinUpTime            ... ', len(getattr(OptModel, 'eMinUpTime_stage'+str(st))), ' rows')

    def eMinDownTime(OptModel,sc,p,n,t):
        if mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(OptModel.vShutDown[sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - OptModel.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinDownTime_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]'))

    if pIndLogConsole == 1:
        print('eMinDownTime          ... ', len(getattr(OptModel, 'eMinDownTime_stage'+str(st))), ' rows')

    GeneratingMinUDTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating minimum up/down time        ... ', round(GeneratingMinUDTime), 's')


def NetworkSwitchingModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Network    switching model formulation ****')

    StartTime = time.time()
    #%%
    def eLineStateCand(OptModel,sc,p,n,ni,nf,cc):
        if   mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] <= OptModel.vNetworkInvest[ni,nf,cc]
        else:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] == OptModel.vNetworkInvest[ni,nf,cc]
    setattr(OptModel, 'eLineStateCand_stage' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    if pIndLogConsole == 1:
        print('eLineStateCand        ... ', len(getattr(OptModel, 'eLineStateCand_stage' + str(st))), ' rows')

    def eSWOnOff(OptModel,sc,p,n,ni,nf,cc):
        if   n == mTEPES.n.first() and mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] - mTEPES.pInitialSwitch[sc,p,n,ni,nf,cc]             == OptModel.vLineOnState[sc,p,n,ni,nf,cc] - OptModel.vLineOffState[sc,p,n,ni,nf,cc]
        elif n != mTEPES.n.first() and mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vLineCommit[sc,p,n,ni,nf,cc] - OptModel.vLineCommit[sc,p,mTEPES.n.prev(n),ni,nf,cc] == OptModel.vLineOnState[sc,p,n,ni,nf,cc] - OptModel.vLineOffState[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eSWOnOff_stage' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    if pIndLogConsole == 1:
        print('eSWOnOff              ... ', len(getattr(OptModel, 'eSWOnOff_stage'+str(st))), ' rows')

    SwitchingLogicalRelation = time.time() - StartTime
    StartTime                = time.time()
    if pIndLogConsole == 1:
        print('Switching logical relation             ... ', round(SwitchingLogicalRelation), 's')

    def eMinSwOnState(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
            return sum(OptModel.vLineOnState [sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOnState_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOnState         ... ', len(getattr(OptModel, 'eMinSwOnState_stage'+str(st))), ' rows')

    def eMinSwOffState(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
            return sum(OptModel.vLineOffState[sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eMinSwOffState_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    if pIndLogConsole == 1:
        print('eMinSwOffState        ... ', len(getattr(OptModel, 'eMinSwOffState_stage'+str(st))), ' rows')

    SwitchingMinStateTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Switching minimum on/off state         ... ', round(SwitchingMinStateTime), 's')


def NetworkOperationModelFormulation(OptModel, mTEPES, pIndLogConsole, st):
    print('Network    operation model formulation ****')

    StartTime = time.time()
    #%%
    def eExistNetCap1(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExistNetCap1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.le, rule=eExistNetCap1, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eExistNetCap1         ... ', len(getattr(OptModel, 'eExistNetCap1_stage'+str(st))), ' rows')

    def eExistNetCap2(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eExistNetCap2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.le, rule=eExistNetCap2, doc='maximum flow by existing network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eExistNetCap2         ... ', len(getattr(OptModel, 'eExistNetCap2_stage'+str(st))), ' rows')

    def eCandNetCap1(OptModel,sc,p,n,ni,nf,cc):
        return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
    setattr(OptModel, 'eCandNetCap1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eCandNetCap1, doc='maximum flow by installed network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eCandNetCap1          ... ', len(getattr(OptModel, 'eCandNetCap1_stage'+str(st))), ' rows')

    def eCandNetCap2(OptModel,sc,p,n,ni,nf,cc):
        return OptModel.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   OptModel.vLineCommit[sc,p,n,ni,nf,cc]
    setattr(OptModel, 'eCandNetCap2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eCandNetCap2, doc='maximum flow by installed network capacity [p.u.]'))

    if pIndLogConsole == 1:
        print('eCandNetCap2          ... ', len(getattr(OptModel, 'eCandNetCap2_stage'+str(st))), ' rows')

    #%%
    def eKirchhoff2ndLawCnd1(OptModel,sc,p,n,ni,nf,cc):
        if   mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase == 0.0
    setattr(OptModel, 'eKirchhoff2ndLawCnd1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLawCnd1, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLawCnd1  ... ', len(getattr(OptModel, 'eKirchhoff2ndLawCnd1_stage'+str(st))), ' rows')

    def eKirchhoff2ndLawCnd2(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return OptModel.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (OptModel.vTheta[sc,p,n,ni] - OptModel.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - OptModel.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(OptModel, 'eKirchhoff2ndLawCnd2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLawCnd2, doc='flow for each AC candidate line [rad]'))

    if pIndLogConsole == 1:
        print('eKirchhoff2ndLawCnd2  ... ', len(getattr(OptModel, 'eKirchhoff2ndLawCnd2_stage'+str(st))), ' rows')

    def eLineLosses1(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return OptModel.vLineLosses[sc,p,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[sc,p,n,ni,nf,cc]
    setattr(OptModel, 'eLineLosses1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses1          ... ', len(getattr(OptModel, 'eLineLosses1_stage'+str(st))), ' rows')

    def eLineLosses2(OptModel,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return OptModel.vLineLosses[sc,p,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * OptModel.vFlow[sc,p,n,ni,nf,cc]
    setattr(OptModel, 'eLineLosses2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    if pIndLogConsole == 1:
        print('eLineLosses2          ... ', len(getattr(OptModel, 'eLineLosses2_stage'+str(st))), ' rows')

    GeneratingNetConsTime = time.time() - StartTime
    if pIndLogConsole == 1:
        print('Generating network    constraints      ... ', round(GeneratingNetConsTime), 's')
