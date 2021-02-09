# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - February 9, 2021

import time
from   collections   import defaultdict
from   pyomo.environ import Constraint, Objective, minimize

def InvestmentModelFormulation(mTEPES):
    print('Investment model formulation ****')

    StartTime = time.time()

    def eTotalTCost(mTEPES):
        return mTEPES.vTotalFCost + sum(mTEPES.pScenProb[sc] * (mTEPES.vTotalGCost[sc,p] + mTEPES.vTotalCCost[sc,p] + mTEPES.vTotalECost[sc,p] + mTEPES.vTotalRCost[sc,p]) for sc,p in mTEPES.sc*mTEPES.p)
    mTEPES.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')

    def eTotalFCost(mTEPES):
       return mTEPES.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * mTEPES.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pNetFixedCost[lc] * mTEPES.vNetworkInvest[lc] for lc in mTEPES.lc)
    mTEPES.eTotalFCost = Constraint(rule=eTotalFCost, doc='system fixed    cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    print('Generating investment o.f.            ... ', round(GeneratingOFTime), 's')

def OperationModelFormulation(mTEPES):
    print('Operation  model formulation ****')

    StartTime = time.time()

    def eTotalGCost(mTEPES,sc,p):
        return mTEPES.vTotalGCost[sc,p] == (sum(mTEPES.pLinearVarCost  [nr] * mTEPES.pDuration[n] * mTEPES.vTotalOutput[sc,p,n,nr]                                 +
                                                mTEPES.pConstantVarCost[nr] * mTEPES.pDuration[n] * mTEPES.vCommitment [sc,p,n,nr]                                 +
                                                mTEPES.pStartUpCost    [nr] *                       mTEPES.vStartUp    [sc,p,n,nr]                                 +
                                                mTEPES.pShutDownCost   [nr] *                       mTEPES.vShutDown   [sc,p,n,nr] for n,nr in mTEPES.n*mTEPES.nr) +
                                            sum(mTEPES.pLinearOMCost   [ r] * mTEPES.pDuration[n] * mTEPES.vTotalOutput[sc,p,n, r] for n, r in mTEPES.n*mTEPES.r ) )
    mTEPES.eTotalGCost = Constraint(mTEPES.sc, mTEPES.p, rule=eTotalGCost, doc='system variable generation operation cost [MEUR]')

    def eTotalCCost(mTEPES,sc,p):
        return mTEPES.vTotalCCost[sc,p] == sum(mTEPES.pLinearVarCost  [es] * mTEPES.vESSTotalCharge[sc,p,n,es] for sc,p,n,es in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.es)
    mTEPES.eTotalCCost = Constraint(mTEPES.sc, mTEPES.p, rule=eTotalCCost, doc='system variable consumption operation cost [MEUR]')

    def eTotalRCost(mTEPES,sc,p):
        return mTEPES.vTotalRCost[sc,p] == sum(mTEPES.pENSCost             * mTEPES.vENS           [sc,p,n,nd] for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)
    mTEPES.eTotalRCost = Constraint(mTEPES.sc, mTEPES.p, rule=eTotalRCost, doc='system reliability cost [MEUR]')

    def eTotalECost(mTEPES,sc,p):
        return mTEPES.vTotalECost[sc,p] == sum(mTEPES.pCO2EmissionCost[nr] * mTEPES.vTotalOutput[sc,p,n,nr] for sc,p,n,nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)
    mTEPES.eTotalECost = Constraint(mTEPES.sc, mTEPES.p, rule=eTotalECost, doc='system emission cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    print('Generating operation o.f.             ... ', round(GeneratingOFTime), 's')

    #%% constraints
    def eInstalGenComm(mTEPES,sc,p,n,gc):
        if gc == mTEPES.nr:
            return mTEPES.vCommitment[sc,p,n,gc] <= mTEPES.vGenerationInvest[gc]
        else:
            return Constraint.Skip
    mTEPES.eInstalGenComm = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenComm, doc='commitment  if installed unit [p.u.]')

    print('eInstalGenComm        ... ', len(mTEPES.eInstalGenComm), ' rows')

    def eInstalGenCap(mTEPES,sc,p,n,gc):
        if mTEPES.pMaxPower[sc,p,n,gc]:
            return mTEPES.vTotalOutput   [sc,p,n,gc] / mTEPES.pMaxPower[sc,p,n,gc] <= mTEPES.vGenerationInvest[gc]
        else:
            return mTEPES.vTotalOutput   [sc,p,n,gc]                               <= 0.0
    mTEPES.eInstalGenCap = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc, rule=eInstalGenCap, doc='output      if installed gen unit [p.u.]')

    print('eInstalGenCap         ... ', len(mTEPES.eInstalGenCap), ' rows')

    def eInstalConESS(mTEPES,sc,p,n,ec):
        return mTEPES.vESSTotalCharge[sc,p,n,ec] / mTEPES.pMaxCharge      [ec] <= mTEPES.vGenerationInvest[ec]
    mTEPES.eInstalConESS = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec, rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]')

    print('eInstalConESS         ... ', len(mTEPES.eInstalConESS), ' rows')

    #%%
    def eOperReserveUp(mTEPES,sc,p,n,ar):
        if mTEPES.pOperReserveUp[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(mTEPES.vReserveUp  [sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveUp  [sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveUp[sc,p,n,ar]
        else:
            return Constraint.Skip
    mTEPES.eOperReserveUp = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]')

    print('eOperReserveUp        ... ', len(mTEPES.eOperReserveUp), ' rows')

    def eOperReserveDw(mTEPES,sc,p,n,ar):
        if mTEPES.pOperReserveDw[sc,p,n,ar] and sum(1 for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(1 for es in mTEPES.es if (ar,es) in mTEPES.a2g):
            return sum(mTEPES.vReserveDown[sc,p,n,nr] for nr in mTEPES.nr if (ar,nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveDown[sc,p,n,es] for es in mTEPES.es if (ar,es) in mTEPES.a2g) == mTEPES.pOperReserveDw[sc,p,n,ar]
        else:
            return Constraint.Skip
    mTEPES.eOperReserveDw = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]')

    print('eOperReserveDw        ... ', len(mTEPES.eOperReserveDw), ' rows')

    #%%
    def eReserveUpIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
            return mTEPES.vReserveUp  [sc,p,n,es] <=                                  mTEPES.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    mTEPES.eReserveUpIfEnergy = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]')

    print('eReserveUpIfEnergy    ... ', len(mTEPES.eReserveUpIfEnergy), ' rows')

    def eReserveDwIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g):
            return mTEPES.vReserveDown[sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - mTEPES.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    mTEPES.eReserveDwIfEnergy = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eReserveDwIfEnergy, doc='down operating reserve if energy available [GW]')

    print('eReserveDwIfEnergy    ... ', len(mTEPES.eReserveDwIfEnergy), ' rows')

    def eESSReserveUpIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return mTEPES.vESSReserveUp  [sc,p,n,es] <= (mTEPES.pMaxStorage[sc,p,n,es] - mTEPES.vESSInventory[sc,p,n,es]) / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    mTEPES.eESSReserveUpIfEnergy = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveUpIfEnergy, doc='up   operating reserve if energy available [GW]')

    print('eESSReserveUpIfEnergy ... ', len(mTEPES.eESSReserveUpIfEnergy), ' rows')

    def eESSReserveDwIfEnergy(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return mTEPES.vESSReserveDown[sc,p,n,es] <=                                  mTEPES.vESSInventory[sc,p,n,es]  / mTEPES.pDuration[n]
        else:
            return Constraint.Skip
    mTEPES.eESSReserveDwIfEnergy = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSReserveDwIfEnergy, doc='down operating reserve if energy available [GW]')

    print('eESSReserveDwIfEnergy ... ', len(mTEPES.eESSReserveDwIfEnergy), ' rows')

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
    mTEPES.eBalance = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance, doc='load generation balance [GW]')

    print('eBalance              ... ', len(mTEPES.eBalance), ' rows')

    def eESSInventory(mTEPES,sc,p,n,es):
        if mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[sc,p,n,es]                                          + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - mTEPES.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*mTEPES.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        elif mTEPES.n.ord(n) > mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return mTEPES.vESSInventory[sc,p,mTEPES.n.prev(n,mTEPES.pCycleTimeStep[es]),es] + sum(mTEPES.pDuration[n2]*(mTEPES.pEnergyInflows[sc,p,n2,es] - mTEPES.vTotalOutput[sc,p,n2,es] + mTEPES.pEfficiency[es]*mTEPES.vESSTotalCharge[sc,p,n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        else:
            return Constraint.Skip
    mTEPES.eESSInventory = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [GWh]')

    print('eESSInventory         ... ', len(mTEPES.eESSInventory), ' rows')

    GeneratingRBITime = time.time() - StartTime
    StartTime         = time.time()
    print('Generating reserves/balance/inventory ... ', round(GeneratingRBITime), 's')

    #%%
    def eMaxCharge(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return (mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] + mTEPES.vESSReserveDown[sc,p,n,es]) / mTEPES.pMaxCharge[es] <= 1
        else:
            return Constraint.Skip
    mTEPES.eMaxCharge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]')

    print('eMaxCharge            ... ', len(mTEPES.eMaxCharge), ' rows')

    def eMinCharge(mTEPES,sc,p,n,es):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return (mTEPES.vESSCharge[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp  [sc,p,n,es] - mTEPES.vESSReserveUp  [sc,p,n,es]) / mTEPES.pMaxCharge[es] >= 0.0
        else:
            return Constraint.Skip
    mTEPES.eMinCharge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]')

    print('eMinCharge            ... ', len(mTEPES.eMinCharge), ' rows')

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
    mTEPES.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    print('eChargeDischarge      ... ', len(mTEPES.eChargeDischarge), ' rows')

    def eESSTotalCharge(mTEPES,sc,p,n,es):
        if mTEPES.pMaxCharge[es]:
            return mTEPES.vESSTotalCharge[sc,p,n,es] == mTEPES.vESSCharge[sc,p,n,es] + mTEPES.pUpReserveActivation * mTEPES.vESSReserveDown[sc,p,n,es] - mTEPES.pDwReserveActivation * mTEPES.vESSReserveUp[sc,p,n,es]
        else:
            return Constraint.Skip
    mTEPES.eESSTotalCharge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSTotalCharge, doc='total charge of a ESS unit [GW]')

    print('eESSTotalCharge       ... ', len(mTEPES.eESSTotalCharge), ' rows')

    #%%
    def eMaxOutput2ndBlock(mTEPES,sc,p,n,nr):
        if sum(mTEPES.pOperReserveUp[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp  [sc,p,n,nr] + mTEPES.vReserveUp  [sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] <= mTEPES.vCommitment[sc,p,n,nr]
        else:
            return Constraint.Skip
    mTEPES.eMaxOutput2ndBlock = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]')

    print('eMaxOutput2ndBlock    ... ', len(mTEPES.eMaxOutput2ndBlock), ' rows')

    def eMinOutput2ndBlock(mTEPES,sc,p,n,nr):
        if sum(mTEPES.pOperReserveDw[sc,p,n,ar] for ar in mTEPES.ar if (ar,nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pMaxPower2ndBlock[sc,p,n,nr] >= 0.0
        else:
            return Constraint.Skip
    mTEPES.eMinOutput2ndBlock = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]')

    print('eMinOutput2ndBlock    ... ', len(mTEPES.eMinOutput2ndBlock), ' rows')

    def eTotalOutput(mTEPES,sc,p,n,nr):
        if mTEPES.pMinPower[sc,p,n,nr] == 0.0 and mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return mTEPES.vTotalOutput[sc,p,n,nr]                               ==                                  mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr]
        elif                                      mTEPES.pMaxPower[sc,p,n,nr] and mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return mTEPES.vTotalOutput[sc,p,n,nr] / mTEPES.pMinPower[sc,p,n,nr] == mTEPES.vCommitment[sc,p,n,nr] + (mTEPES.vOutput2ndBlock[sc,p,n,nr] + mTEPES.pUpReserveActivation * mTEPES.vReserveUp[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pMinPower[sc,p,n,nr]
        else:
            return Constraint.Skip
    mTEPES.eTotalOutput = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]')

    print('eTotalOutput          ... ', len(mTEPES.eTotalOutput), ' rows')

    def eUCStrShut(mTEPES,sc,p,n,nr):
        if n == mTEPES.n.first() and mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr]:
            return mTEPES.vCommitment[sc,p,n,nr] - mTEPES.pInitialUC[nr]                        == mTEPES.vStartUp[sc,p,n,nr] - mTEPES.vShutDown[sc,p,n,nr]
        elif                         mTEPES.pMustRun[nr] == 0 and mTEPES.pMinPower[sc,p,n,nr]:
            return mTEPES.vCommitment[sc,p,n,nr] - mTEPES.vCommitment[sc,p,mTEPES.n.prev(n),nr] == mTEPES.vStartUp[sc,p,n,nr] - mTEPES.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    mTEPES.eUCStrShut = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eUCStrShut, doc='relation among commitment startup and shutdown')

    print('eUCStrShut            ... ', len(mTEPES.eUCStrShut), ' rows')

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
    mTEPES.eRampUp = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampUp, doc='maximum ramp up   [p.u.]')

    print('eRampUp               ... ', len(mTEPES.eRampUp), ' rows')

    def eRampDw(mTEPES,sc,p,n,nr):
        if   mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr] and n == mTEPES.n.first():
            return (- max(mTEPES.pInitialOutput[nr] - mTEPES.pMinPower[sc,p,n,nr],0.0)                                                               + mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.pInitialUC[nr]                                                                                           + mTEPES.vShutDown[sc,p,n,nr]
        elif mTEPES.pRampDw[nr] and mTEPES.pRampDw[nr] < mTEPES.pMaxPower2ndBlock[sc,p,n,nr]:
            return (- mTEPES.vOutput2ndBlock[sc,p,mTEPES.n.prev(n),nr] + mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,mTEPES.n.prev(n),nr] + mTEPES.vOutput2ndBlock[sc,p,n,nr] - mTEPES.pDwReserveActivation * mTEPES.vReserveDown[sc,p,n,nr] - mTEPES.vReserveDown[sc,p,n,nr]) / mTEPES.pDuration[n] / mTEPES.pRampDw[nr] >= - mTEPES.vCommitment[sc,p,mTEPES.n.prev(n),nr] + mTEPES.vShutDown[sc,p,n,nr]
        else:
            return Constraint.Skip
    mTEPES.eRampDw = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eRampDw, doc='maximum ramp down [p.u.]')

    print('eRampDw               ... ', len(mTEPES.eRampDw), ' rows')

    GeneratingRampsTime = time.time() - StartTime
    StartTime           = time.time()
    print('Generating ramps   up/down            ... ', round(GeneratingRampsTime), 's')

    #%%
    def eMinUpTime(mTEPES,sc,p,n,t):
        if mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(mTEPES.vStartUp [sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <=     mTEPES.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    mTEPES.eMinUpTime   = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinUpTime  , doc='minimum up   time [h]')

    print('eMinUpTime            ... ', len(mTEPES.eMinUpTime), ' rows')

    def eMinDownTime(mTEPES,sc,p,n,t):
        if mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(mTEPES.vShutDown[sc,p,n2,t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - mTEPES.vCommitment[sc,p,n,t]
        else:
            return Constraint.Skip
    mTEPES.eMinDownTime = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]')

    print('eMinDownTime          ... ', len(mTEPES.eMinDownTime), ' rows')

    GeneratingMinUDTime = time.time() - StartTime
    StartTime           = time.time()
    print('Generating minimum up/down time       ... ', round(GeneratingMinUDTime), 's')

    #%%
    def eInstalNetCap1(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) >= - mTEPES.vNetworkInvest[ni,nf,cc]
    mTEPES.eInstalNetCap1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eInstalNetCap1, doc='maximum flow by installed network capacity [p.u.]')

    print('eInstalNetCap1        ... ', len(mTEPES.eInstalNetCap1), ' rows')

    def eInstalNetCap2(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pLineNTCBck[ni,nf,cc],mTEPES.pLineNTCFrw[ni,nf,cc]) <=   mTEPES.vNetworkInvest[ni,nf,cc]
    mTEPES.eInstalNetCap2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eInstalNetCap2, doc='maximum flow by installed network capacity [p.u.]')

    print('eInstalNetCap2        ... ', len(mTEPES.eInstalNetCap2), ' rows')

    def eKirchhoff2ndLawExst(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / max(mTEPES.pBigMFlowBck[ni,nf,cc](),mTEPES.pBigMFlowFrw[ni,nf,cc]()) - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / max(mTEPES.pBigMFlowBck[ni,nf,cc](),mTEPES.pBigMFlowFrw[ni,nf,cc]()) * mTEPES.pSBase == 0.0
    mTEPES.eKirchhoff2ndLawExst = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lea, rule=eKirchhoff2ndLawExst, doc='flow for each AC existing  line [rad]')

    print('eKirchhoff2ndLawExst  ... ', len(mTEPES.eKirchhoff2ndLawExst), ' rows')

    def eKirchhoff2ndLawCnd1(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowBck[ni,nf,cc] * mTEPES.pSBase >= - 1 + mTEPES.vNetworkInvest[ni,nf,cc]
    mTEPES.eKirchhoff2ndLawCnd1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLawCnd1, doc='flow for each AC candidate line [rad]')

    print('eKirchhoff2ndLawCnd1  ... ', len(mTEPES.eKirchhoff2ndLawCnd1), ' rows')

    def eKirchhoff2ndLawCnd2(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vFlow[sc,p,n,ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] - (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf]) / mTEPES.pLineX[ni,nf,cc] / mTEPES.pBigMFlowFrw[ni,nf,cc] * mTEPES.pSBase <=   1 - mTEPES.vNetworkInvest[ni,nf,cc]
    mTEPES.eKirchhoff2ndLawCnd2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLawCnd2, doc='flow for each AC candidate line [rad]')

    print('eKirchhoff2ndLawCnd2  ... ', len(mTEPES.eKirchhoff2ndLawCnd2), ' rows')

    def eLineLosses1(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc,p,n,ni,nf,cc] >= - 0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * mTEPES.vFlow[sc,p,n,ni,nf,cc]
    mTEPES.eLineLosses1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses1, doc='ohmic losses for all the lines [GW]')

    print('eLineLosses1          ... ', len(mTEPES.eLineLosses1), ' rows')

    def eLineLosses2(mTEPES,sc,p,n,ni,nf,cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc,p,n,ni,nf,cc] >=   0.5 * mTEPES.pLineLossFactor[ni,nf,cc] * mTEPES.vFlow[sc,p,n,ni,nf,cc]
    mTEPES.eLineLosses2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll, rule=eLineLosses2, doc='ohmic losses for all the lines [GW]')

    print('eLineLosses2          ... ', len(mTEPES.eLineLosses2), ' rows')

    GeneratingNetConsTime = time.time() - StartTime
    StartTime             = time.time()
    print('Generating network    constraints     ... ', round(GeneratingNetConsTime), 's')
