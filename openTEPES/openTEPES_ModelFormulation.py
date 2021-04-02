""" Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - April 2, 2021
"""

import time
from   collections   import defaultdict
from   pyomo.environ import Set, Constraint, Objective, Block, minimize


def InvestmentModelFormulation(mTEPES):
    print('Investment model formulation ****')

    StartTime = time.time()

    def eTotalTCost(mTEPES):
        return mTEPES.vTotalFCost + sum(mTEPES.pScenProb[sc] * (mTEPES.vTotalGCost[sc,p,n] + mTEPES.vTotalCCost[sc,p,n] + mTEPES.vTotalECost[sc,p,n] + mTEPES.vTotalRCost[sc,p,n]) for sc,p,n in mTEPES.sc*mTEPES.p*mTEPES.n)
    mTEPES.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalFCost(mTEPES):
       return mTEPES.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * mTEPES.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pNetFixedCost[lc] * mTEPES.vNetworkInvest[lc] for lc in mTEPES.lc)
    mTEPES.eTotalFCost = Constraint(rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    print('Generating investment o.f.            ... ', round(GeneratingOFTime), 's')


def GenerationOperationModelFormulation(mTEPES, st):
    print('Genr oper  model formulation ****')

    StartTime = time.time()

    def eTotalGCost(mTEPES,sc,p,n):
        return mTEPES.vTotalGCost[sc,p,n] == (sum(mTEPES.pLinearVarCost  [nr] * mTEPES.pDuration[n] * mTEPES.vTotalOutput[sc,p,n,nr]                      +
                                                  mTEPES.pConstantVarCost[nr] * mTEPES.pDuration[n] * mTEPES.vCommitment [sc,p,n,nr]                      +
                                                  mTEPES.pStartUpCost    [nr] *                       mTEPES.vStartUp    [sc,p,n,nr]                      +
                                                  mTEPES.pShutDownCost   [nr] *                       mTEPES.vShutDown   [sc,p,n,nr] for nr in mTEPES.nr) +
                                              sum(mTEPES.pLinearOMCost   [ r] * mTEPES.pDuration[n] * mTEPES.vTotalOutput[sc,p,n, r] for  r in mTEPES.r ) )
    setattr(mTEPES, 'eTotalGCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]'))

    def eTotalCCost(mTEPES,sc,p,n):
        if sum(mTEPES.pLinearVarCost  [es] for es in mTEPES.es):
            return mTEPES.vTotalCCost[sc,p,n] == sum(mTEPES.pLinearVarCost  [es] * mTEPES.pDuration[n] * mTEPES.vESSTotalCharge[sc,p,n,es] for es in mTEPES.es)
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eTotalCCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]'))

    def eTotalECost(mTEPES,sc,p,n):
        if sum(mTEPES.pCO2EmissionCost[nr] for nr in mTEPES.nr):
            return mTEPES.vTotalECost[sc,p,n] == sum(mTEPES.pCO2EmissionCost[nr] * mTEPES.pDuration[n] * mTEPES.vTotalOutput   [sc,p,n,nr] for nr in mTEPES.nr)
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eTotalECost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalECost, doc='system emission cost [MEUR]'))

    def eTotalRCost(mTEPES,sc,p,n):
        return mTEPES.vTotalRCost[sc,p,n] == sum(mTEPES.pENSCost             * mTEPES.pDuration[n] * mTEPES.vENS           [sc,p,n,nd] for nd in mTEPES.nd)
    setattr(mTEPES, 'eTotalRCost_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, rule=eTotalRCost, doc='system reliability cost [MEUR]'))

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    print('Generating operation  o.f.            ... ', round(GeneratingOFTime), 's')

    StartTime = time.time()

    #%% constraints
    def eInstalGenComm(mTEPES,sc,p,n,gc):
        if gc == mTEPES.nr:
            return mTEPES.vCommitment[sc,p,n,gc] <= mTEPES.vGenerationInvest[gc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eInstalGenComm_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment  if installed unit [p.u.]'))

    print('eInstalGenComm        ... ', len(getattr(mTEPES, 'eInstalGenComm_stage'+str(st))), ' rows')

    def eInstalGenCap(mTEPES,sc,p,n,gc):
        if mTEPES.pMaxPower[sc,p,n,gc]:
            return mTEPES.vTotalOutput   [sc,p,n,gc] / mTEPES.pMaxPower[sc,p,n,gc] <= mTEPES.vGenerationInvest[gc]
        else:
            return mTEPES.vTotalOutput   [sc,p,n,gc]                               <= 0.0
    setattr(mTEPES, 'eInstalGenCap_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output      if installed gen unit [p.u.]'))

    print('eInstalGenCap         ... ', len(getattr(mTEPES, 'eInstalGenCap_stage'+str(st))), ' rows')

    def eInstalConESS(mTEPES,sc,p,n,ec):
        return mTEPES.vESSTotalCharge[sc,p,n,ec] / mTEPES.pMaxCharge      [ec] <= mTEPES.vGenerationInvest[ec]
    setattr(mTEPES, 'eInstalConESS_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]'))

    print('eInstalConESS         ... ', len(getattr(mTEPES, 'eInstalConESS_stage'+str(st))), ' rows')

    #%%
    def eOperReserveUp(mTEPES,sc,p,n,ar):
        if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(mTEPES.vReserveUp  [sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveUp  [sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveUp[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eOperReserveUp_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]'))

    print('eOperReserveUp        ... ', len(getattr(mTEPES, 'eOperReserveUp_stage'+str(st))), ' rows')

    def eOperReserveDw(mTEPES,sc,p,n,ar):
        if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(mTEPES.vReserveDown[sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveDown[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveDw[sc,p,n,ar]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eOperReserveDw_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]'))

    print('eOperReserveDw        ... ', len(getattr(mTEPES, 'eOperReserveDw_stage'+str(st))), ' rows')

    #%%
    def eReserveUpIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
            return mTEPES.vReserveUp  [sc,p,n,es] <=                                  mTEPES.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eReserveUpIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    print('eReserveUpIfEnergy    ... ', len(getattr(mTEPES, 'eReserveUpIfEnergy_stage'+str(st))), ' rows')

    def eReserveDwIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
            return mTEPES.vReserveDown[sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - mTEPES.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eReserveDwIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    print('eReserveDwIfEnergy    ... ', len(getattr(mTEPES, 'eReserveDwIfEnergy_stage'+str(st))), ' rows')

    def eESSReserveUpIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return mTEPES.vESSReserveUp  [sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - mTEPES.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eESSReserveUpIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]'))

    print('eESSReserveUpIfEnergy ... ', len(getattr(mTEPES, 'eESSReserveUpIfEnergy_stage'+str(st))), ' rows')

    def eESSReserveDwIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return mTEPES.vESSReserveDown[sc,p,n,es] <=                                  mTEPES.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eESSReserveDwIfEnergy_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]'))

    print('eESSReserveDwIfEnergy ... ', len(getattr(mTEPES, 'eESSReserveDwIfEnergy_stage'+str(st))), ' rows')

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
    def eBalance(mTEPES,sc,p,n,nd):
        if sum(1 for g in mTEPES.g if (nd,g) in mTEPES.n2g) + sum(1 for lout in lout[nd]) + sum(1 for ni,cc in lin[nd]):
            return (sum(mTEPES.vTotalOutput[sc,p,n,g] for g in mTEPES.g if (nd,g) in mTEPES.n2g) - sum(mTEPES.vESSTotalCharge[sc,p,n,es] for es in mTEPES.es if (nd,es) in mTEPES.n2g) + mTEPES.vENS[sc,p,n,nd] == mTEPES.pDemand[sc,p,n,nd] +
                    sum(mTEPES.vLineLosses[sc,p,n,nd,lout ] for lout  in loutl[nd]) + sum(mTEPES.vFlow[sc,p,n,nd,lout ] for lout  in lout[nd]) +
                    sum(mTEPES.vLineLosses[sc,p,n,ni,nd,cc] for ni,cc in linl [nd]) - sum(mTEPES.vFlow[sc,p,n,ni,nd,cc] for ni,cc in lin [nd]))
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eBalance_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance, doc='load generation balance [GW]'))

    print('eBalance              ... ', len(getattr(mTEPES, 'eBalance_stage'+str(st))), ' rows')

    def eESSInventory(mTEPES,sc,p,n,es):
        if mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[sc,p,n,es]                                          + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - mTEPES.vEnergyOutflows[sc,p,n2,es] - mTEPES.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*mTEPES.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        elif mTEPES.n.ord(n) > mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return mTEPES.vESSInventory[sc,p,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - mTEPES.vEnergyOutflows[sc,p,n2,es] - mTEPES.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*mTEPES.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eESSInventory_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [GWh]'))

    print('eESSInventory         ... ', len(getattr(mTEPES, 'eESSInventory_stage'+str(st))), ' rows')

    GeneratingRBITime = time.time() - StartTime
    StartTime         = time.time()
    print('Generating reserves/balance/inventory ... ', round(GeneratingRBITime), 's')

    #%%
    def eMaxCharge(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return (mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] + mTEPES.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge[es] <= 1
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMaxCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]'))

    print('eMaxCharge            ... ', len(getattr(mTEPES, 'eMaxCharge_stage'+str(st))), ' rows')

    def eMinCharge(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return (mTEPES.vESSCharge[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp  [sc,p,n,es] - mTEPES.vESSReserveUp  [sc,p,n,es]) / mTEPES.pMaxCharge[es] >= 0.0
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]'))

    print('eMinCharge            ... ', len(getattr(mTEPES, 'eMinCharge_stage'+str(st))), ' rows')

    # def eChargeDischarge(mTEPES,sc,p,n,es):
    #     if mTEPES.pMaxCharge[es]:
    #         return mTEPES.vTotalOutput[sc,p,n,es] / mTEPES.pMaxPower[sc,p,n,es] + mTEPES.vESSCharge[sc,p,n,es] / mTEPES.pMaxCharge[es] <= 1
    #     else:
    #         return Constraint.Skip
    # mTEPES.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(mTEPES,sc,p,n,es):
        if mTEPES.pMaxCharge[es]:
            if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
                return ((mTEPES.vOutput2ndBlock[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp     [sc,p,n,es] + mTEPES.vReserveUp     [sc,p,n,es]) / mTEPES.pMaxPower2ndBlock[sc,p,n,es] +
                        (mTEPES.vESSCharge     [sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] + mTEPES.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge       [       es] <= 1)
            else:
                return ((mTEPES.vOutput2ndBlock[sc,p,n,es]                                                                                                      ) / mTEPES.pMaxPower2ndBlock[sc,p,n,es] +
                        (mTEPES.vESSCharge     [sc,p,n,es]                                                                                                      ) / mTEPES.pMaxCharge       [       es] <= 1)
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eChargeDischarge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]'))

    print('eChargeDischarge      ... ', len(getattr(mTEPES, 'eChargeDischarge_stage'+str(st))), ' rows')

    def eESSTotalCharge(mTEPES,sc,p,n,es):
        if mTEPES.pMaxCharge[es]:
            return mTEPES.vESSTotalCharge[sc,p,n,es] == mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp[sc,p,n,es]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eESSTotalCharge_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of an ESS unit [GW]'))

    print('eESSTotalCharge       ... ', len(getattr(mTEPES, 'eESSTotalCharge_stage'+str(st))), ' rows')

    def eEnergyOutflows(mTEPES,sc,p,n,es):
        if mTEPES.n.ord(n) % mTEPES.pOutflowsTimeStep[es] == 0:
            return sum(mTEPES.vEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - int(mTEPES.pOutflowsTimeStep[es]/mTEPES.pCycleTimeStep[es]):mTEPES.n.ord(n)]) == sum(mTEPES.pEnergyOutflows[sc,p,n2,es] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n) - mTEPES.pOutflowsTimeStep[es]:mTEPES.n.ord(n)])
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eEnergyOutflows_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eEnergyOutflows, doc='energy outflows of an ESS unit [GW]'))

    print('eEnergyOutflows       ... ', len(getattr(mTEPES, 'eEnergyOutflows_stage'+str(st))), ' rows')

    #%%
    def eMaxOutput2ndBlock(mTEPES,sc,p,n,nr):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp  [sc,p,n,nr] + mTEPES.vReserveUp  [sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] <= mTEPES.vCommitment[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMaxOutput2ndBlock_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]'))

    print('eMaxOutput2ndBlock    ... ', len(getattr(mTEPES, 'eMaxOutput2ndBlock_stage'+str(st))), ' rows')

    def eMinOutput2ndBlock(mTEPES,sc,p,n,nr):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] >= 0.0
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinOutput2ndBlock_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]'))

    print('eMinOutput2ndBlock    ... ', len(getattr(mTEPES, 'eMinOutput2ndBlock_stage'+str(st))), ' rows')

    def eTotalOutput(mTEPES,sc,p,n,nr):
        if mTEPES.pMinPower[sc,p,n,nr] == 0.0 and mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return mTEPES.vTotalOutput[sc,p,n,nr]                               ==                                  mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr]
        elif                                      mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return mTEPES.vTotalOutput[sc,p,n,nr] / mTEPES.pMinPower[sc,p,n,nr] == mTEPES.vCommitment[sc,p,n,nr] + (mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pMinPower[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eTotalOutput_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]'))

    print('eTotalOutput          ... ', len(getattr(mTEPES, 'eTotalOutput_stage'+str(st))), ' rows')

    def eUCStrShut(mTEPES,sc,p,n,nr):
        if n == mTEPES.n.first() and mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr]:
            return mTEPES.vCommitment[sc,p,n,nr] - mTEPES.pInitialUC[nr]                        == mTEPES.vStartUp[sc,p,n,nr] - mTEPES.vShutDown[sc,p,n,nr]
        elif                         mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr]:
            return mTEPES.vCommitment[sc,p,n,nr] - mTEPES.vCommitment[sc,p,mTEPES.n.prev(n),nr] == mTEPES.vStartUp[sc,p,n,nr] - mTEPES.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eUCStrShut_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown'))

    print('eUCStrShut            ... ', len(getattr(mTEPES, 'eUCStrShut_stage'+str(st))), ' rows')

    GeneratingGenConsTime = time.time() - StartTime
    StartTime             = time.time()
    print('Generating generation constraints     ... ', round(GeneratingGenConsTime), 's')

    #%%
    def eRampUp(mTEPES,sc,p,n,nr):
        if   mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[nr] - mTEPES.pMinPower[sc,p,n,nr],0.0)                                                               + mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp  [sc,p,n,nr] + mTEPES.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   mTEPES.vCommitment[sc,p,n,nr] - mTEPES.vStartUp[sc,p,n,nr]
        elif mTEPES.pRampUp[nr] and mTEPES.pRampUp[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- mTEPES.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] - mTEPES.pUpReserveActivation * mTEPES.vReserveUp  [sc,p,mTEPES.n.prev(n),nr] + mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp  [sc,p,n,nr] + mTEPES.vReserveUp  [sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampUp[nr] <=   mTEPES.vCommitment[sc,p,n,nr] - mTEPES.vStartUp[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eRampUp_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]'))

    print('eRampUp               ... ', len(getattr(mTEPES, 'eRampUp_stage'+str(st))), ' rows')

    def eRampDw(mTEPES,sc,p,n,nr):
        if   mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[nr] - mTEPES.pMinPower[sc,p,n,nr],0.0)                                                               + mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[nr]                                                                                           + mTEPES.vShutDown[sc,p,n,nr]
        elif mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- mTEPES.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] + mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,mTEPES.n.prev(n),nr] + mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.vCommitment[sc,p,mTEPES.n.prev(n),nr] + mTEPES.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    setattr(mTEPES,'eRampDw_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]'))

    print('eRampDw               ... ', len(getattr(mTEPES, 'eRampDw_stage'+str(st))), ' rows')

    def eRampUpCharge(mTEPES,sc,p,n,es):
        if   mTEPES.pRampUp[es] and n == mTEPES.n.first():
            return (                                                                                                                               + mTEPES.vESSCharge[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp  [sc,p,n,es] - mTEPES.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        elif mTEPES.pRampUp[es]:
            return (- mTEPES.vESSCharge[sc,p,mTEPES.n.prev(n),es] + mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp  [sc,p,mTEPES.n.prev(n),es] + mTEPES.vESSCharge[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp  [sc,p,n,es] - mTEPES.vESSReserveUp  [sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampUp[es] >= - 1.0
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eRampUpChr_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampUpCharge, doc='maximum ramp up   charge [p.u.]'))

    print('eRampUpChr            ... ', len(getattr(mTEPES, 'eRampUpChr_stage'+str(st))), ' rows')

    def eRampDwCharge(mTEPES,sc,p,n,es):
        if   mTEPES.pRampDw[es] and n == mTEPES.n.first():
            return (                                                                                                                               + mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] + mTEPES.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        elif mTEPES.pRampDw[es]:
            return (- mTEPES.vESSCharge[sc,p,mTEPES.n.prev(n),es] - mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,mTEPES.n.prev(n),es] + mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] + mTEPES.vESSReserveDown[sc,p,n,es]) / mTEPES.pDuration[n] / mTEPES.pRampDw[es] <=   1.0
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eRampDwChr_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eRampDwCharge, doc='maximum ramp down charge [p.u.]'))

    print('eRampDwChr            ... ', len(getattr(mTEPES, 'eRampDwChr_stage'+str(st))), ' rows')

    GeneratingRampsTime = time.time() - StartTime
    StartTime           = time.time()
    print('Generating ramps   up/down            ... ', round(GeneratingRampsTime), 's')

    #%%
    def eMinUpTime(mTEPES,sc,p,n,t):
        if mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(mTEPES.vStartUp [sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     mTEPES.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinUpTime_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]'))

    print('eMinUpTime            ... ', len(getattr(mTEPES, 'eMinUpTime_stage'+str(st))), ' rows')

    def eMinDownTime(mTEPES,sc,p,n,t):
        if mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(mTEPES.vShutDown[sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - mTEPES.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinDownTime_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]'))

    print('eMinDownTime          ... ', len(getattr(mTEPES, 'eMinDownTime_stage'+str(st))), ' rows')

    GeneratingMinUDTime = time.time() - StartTime
    StartTime           = time.time()
    print('Generating minimum up/down time       ... ', round(GeneratingMinUDTime), 's')


def NetworkDecisionModelFormulation(mTEPES, st):
    print('Netw decis model formulation ****')

    StartTime = time.time()
    #%%
    def eLineStateCand(mTEPES,sc,p,n,ni,nf,cc):
        if   mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vLineCommit[sc,p,n,ni,nf,cc] <= mTEPES.vNetworkInvest[ni,nf,cc]
        elif mTEPES.pIndBinSwitching[ni,nf,cc] == 0:
            return mTEPES.vLineCommit[sc,p,n,ni,nf,cc] == mTEPES.vNetworkInvest[ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eLineStateCand_stage' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eLineStateCand, doc='logical relation between investment and operation in candidates'))

    print('eLineStateCand        ... ', len(getattr(mTEPES, 'eLineStateCand_stage' + str(st))), ' rows')

    def eSWOnOff(mTEPES,sc,p,n,ni,nf,cc):
        if   n == mTEPES.n.first() and mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vLineCommit[sc,p,n,ni,nf,cc] - mTEPES.pInitialSwitch[ni,nf,cc]                    == mTEPES.vLineOnState[sc,p,n,ni,nf,cc] - mTEPES.vLineOffState[sc,p,n,ni,nf,cc]
        elif n != mTEPES.n.first() and mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vLineCommit[sc,p,n,ni,nf,cc] - mTEPES.vLineCommit[sc,p,mTEPES.n.prev(n),ni,nf,cc] == mTEPES.vLineOnState[sc,p,n,ni,nf,cc] - mTEPES.vLineOffState[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eSWOnOff_stage' + str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eSWOnOff, doc='relation among switching decision activate and deactivate state'))

    print('eSWOnOff              ... ', len(getattr(mTEPES, 'eSWOnOff_stage'+str(st))), ' rows')

    SwitchingLogicalRelation = time.time() - StartTime
    StartTime                = time.time()
    print('Switching logical relation            ... ', round(SwitchingLogicalRelation), 's')

    def eMinSwOnState(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1 and mTEPES.pSwOnTime [ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOnTime [ni,nf,cc]:
            return sum(mTEPES.vLineOnState [sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOnTime [ni,nf,cc]:mTEPES.n.ord(n)]) <=    mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinSwOnState_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOnState, doc='minimum switch on state [h]'))

    print('eMinSwOnState         ... ', len(getattr(mTEPES, 'eMinSwOnState_stage'+str(st))), ' rows')

    def eMinSwOffState(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1 and mTEPES.pSwOffTime[ni,nf,cc] > 1 and mTEPES.n.ord(n) >= mTEPES.pSwOffTime[ni,nf,cc]:
            return sum(mTEPES.vLineOffState[sc,p,n2,ni,nf,cc] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pSwOffTime[ni,nf,cc]:mTEPES.n.ord(n)]) <= 1 - mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eMinSwOffState_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eMinSwOffState, doc='minimum switch off state [h]'))

    print('eMinSwOffState        ... ', len(getattr(mTEPES, 'eMinSwOffState_stage'+str(st))), ' rows')

    SwitchingMinStateTime = time.time() - StartTime
    print('Switching minimum on/off state        ... ', round(SwitchingMinStateTime), 's')


def NetworkOperationModelFormulation(mTEPES, st):
    print('Netw oper  model formulation ****')

    StartTime = time.time()
    #%%
    def eExistNetCap1(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eExistNetCap1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.le, rule=eExistNetCap1, doc='maximum flow by existing network capacity [p.u.]'))

    print('eExistNetCap1         ... ', len(getattr(mTEPES, 'eExistNetCap1_stage'+str(st))), ' rows')

    def eExistNetCap2(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni, nf, cc] == 1:
            return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eExistNetCap2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.le, rule=eExistNetCap2, doc='maximum flow by existing network capacity [p.u.]'))

    print('eExistNetCap2         ... ', len(getattr(mTEPES, 'eExistNetCap2_stage'+str(st))), ' rows')

    def eCandNetCap1(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
    setattr(mTEPES, 'eCandNetCap1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eCandNetCap1, doc='maximum flow by installed network capacity [p.u.]'))

    print('eCandNetCap1          ... ', len(getattr(mTEPES, 'eCandNetCap1_stage'+str(st))), ' rows')

    def eCandNetCap2(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
    setattr(mTEPES, 'eCandNetCap2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eCandNetCap2, doc='maximum flow by installed network capacity [p.u.]'))

    print('eCandNetCap2          ... ', len(getattr(mTEPES, 'eCandNetCap2_stage'+str(st))), ' rows')

    #%%
    def eKirchhoff2ndLawCnd1(mTEPES,sc,p,n,ni,nf,cc):
        if   mTEPES.pIndBinSwitching[ni,nf,cc] == 0:
            return mTEPES.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase == 0.0
        elif mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eKirchhoff2ndLawCnd1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLawCnd1, doc='flow for each AC candidate line [rad]'))

    print('eKirchhoff2ndLawCnd1  ... ', len(getattr(mTEPES, 'eKirchhoff2ndLawCnd1_stage'+str(st))), ' rows')

    def eKirchhoff2ndLawCnd2(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndBinSwitching[ni,nf,cc] == 1:
            return mTEPES.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - mTEPES.vLineCommit[sc,p,n,ni,nf,cc]
        else:
            return Constraint.Skip
    setattr(mTEPES, 'eKirchhoff2ndLawCnd2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.laa, rule=eKirchhoff2ndLawCnd2, doc='flow for each AC candidate line [rad]'))

    print('eKirchhoff2ndLawCnd2  ... ', len(getattr(mTEPES, 'eKirchhoff2ndLawCnd2_stage'+str(st))), ' rows')

    def eLineLosses1(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc,p,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * mTEPES.vFlow[sc,p,n,ni,nf,cc]
    setattr(mTEPES, 'eLineLosses1_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]'))

    print('eLineLosses1          ... ', len(getattr(mTEPES, 'eLineLosses1_stage'+str(st))), ' rows')

    def eLineLosses2(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc,p,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * mTEPES.vFlow[sc,p,n,ni,nf,cc]
    setattr(mTEPES, 'eLineLosses2_stage'+str(st), Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]'))

    print('eLineLosses2          ... ', len(getattr(mTEPES, 'eLineLosses2_stage'+str(st))), ' rows')

    GeneratingNetConsTime = time.time() - StartTime
    StartTime             = time.time()
    print('Generating network    constraints     ... ', round(GeneratingNetConsTime), 's')
