# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.16 - September 11, 2020

import time
from   collections   import defaultdict
from   pyomo.environ import Constraint, Objective, minimize

def ModelFormulation(mTEPES):
    print('Model formulation           ****')

    StartTime = time.time()

    def eTotalFCost(mTEPES):
        return mTEPES.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * mTEPES.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pNetFixedCost[lc] * mTEPES.vNetworkInvest[lc] for lc in mTEPES.lc)
    mTEPES.eTotalFCost = Constraint(
        rule=eTotalFCost, doc='total system fixed    cost [MEUR]')

    def eTotalVCost(mTEPES):
        return mTEPES.vTotalVCost == (sum(mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pENSCost * mTEPES.vENS[sc, p, n, nd] for sc, p, n, nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd) +
                                      sum(mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pLinearVarCost[nr] * mTEPES.vTotalOutput[sc, p, n, nr] +
                                          mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pConstantVarCost[nr] * mTEPES.vCommitment[sc, p, n, nr] +
                                          mTEPES.pScenProb[sc] * mTEPES.pStartUpCost[nr] * mTEPES.vStartUp[sc, p, n, nr] +
                                          mTEPES.pScenProb[sc] * mTEPES.pShutDownCost[nr] * mTEPES.vShutDown[sc, p, n, nr] for sc, p, n, nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr))
    mTEPES.eTotalVCost = Constraint(
        rule=eTotalVCost, doc='total system variable cost [MEUR]')

    def eTotalECost(mTEPES):
        return mTEPES.vTotalECost == sum(mTEPES.pScenProb[sc] * mTEPES.pCO2Cost * mTEPES.pCO2EmissionRate[nr] * mTEPES.vTotalOutput[sc, p, n, nr] for sc, p, n, nr in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nr)
    mTEPES.eTotalECost = Constraint(
        rule=eTotalECost, doc='total system emission cost [MEUR]')

    def eTotalTCost(mTEPES):
        return mTEPES.vTotalFCost + mTEPES.vTotalVCost + mTEPES.vTotalECost
    mTEPES.eTotalTCost = Objective(
        rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')

    GeneratingOFTime = time.time() - StartTime
    StartTime = time.time()
    print('Generating objective function         ... ',
          round(GeneratingOFTime), 's')

    # %% constraints
    def eInstalGenCap(mTEPES, sc, p, n, gc):
        return mTEPES.vCommitment[sc, p, n, gc] <= mTEPES.vGenerationInvest[gc]
    mTEPES.eInstalGenCap = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.gc,
                                      rule=eInstalGenCap, doc='commitment  if installed unit [p.u.]')

    print('eInstalGenCap         ... ', len(mTEPES.eInstalGenCap), ' rows')

    def eInstalGenESS(mTEPES, sc, p, n, ec):
        return mTEPES.vTotalOutput[sc, p, n, ec] / mTEPES.pMaxPower[sc, p, n, ec] <= mTEPES.vGenerationInvest[ec]
    mTEPES.eInstalGenESS = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec,
                                      rule=eInstalGenESS, doc='output      if installed ESS unit [p.u.]')

    print('eInstalGenESS         ... ', len(mTEPES.eInstalGenESS), ' rows')

    def eInstalConESS(mTEPES, sc, p, n, ec):
        return mTEPES.vESSCharge[sc, p, n, ec] / mTEPES.pMaxCharge[ec] <= mTEPES.vGenerationInvest[ec]
    mTEPES.eInstalConESS = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ec,
                                      rule=eInstalConESS, doc='consumption if installed ESS unit [p.u.]')

    print('eInstalConESS         ... ', len(mTEPES.eInstalConESS), ' rows')

    # %%
    def eOperReserveUp(mTEPES, sc, p, n, ar):
        if mTEPES.pOperReserveUp[sc, p, n, ar]:
            return sum(mTEPES.vReserveUp[sc, p, n, nr] for nr in mTEPES.nr if (ar, nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveUp  [sc, p, n, es] for es in mTEPES.es if (ar, es) in mTEPES.a2g) >= mTEPES.pOperReserveUp[sc, p, n, ar]
        else:
            return Constraint.Skip
    mTEPES.eOperReserveUp = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveUp, doc='up   operating reserve [GW]')

    print('eOperReserveUp        ... ', len(mTEPES.eOperReserveUp), ' rows')

    def eOperReserveDw(mTEPES, sc, p, n, ar):
        if mTEPES.pOperReserveDw[sc, p, n, ar]:
            return sum(mTEPES.vReserveDown[sc, p, n, nr] for nr in mTEPES.nr if (ar, nr) in mTEPES.a2g) + sum(mTEPES.vESSReserveDown[sc, p, n, es] for es in mTEPES.es if (ar, es) in mTEPES.a2g) >= mTEPES.pOperReserveDw[sc, p, n, ar]
        else:
            return Constraint.Skip
    mTEPES.eOperReserveDw = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ar, rule=eOperReserveDw, doc='down operating reserve [GW]')

    print('eOperReserveDw        ... ', len(mTEPES.eOperReserveDw), ' rows')

    # incoming and outgoing lines (lin) (lout)
    lin = defaultdict(list)
    linl = defaultdict(list)
    lout = defaultdict(list)
    loutl = defaultdict(list)
    for ni, nf, cc in mTEPES.la:
        lin[nf].append((ni, cc))
        lout[ni].append((nf, cc))
    for ni, nf, cc in mTEPES.ll:
        linl[nf].append((ni, cc))
        loutl[ni].append((nf, cc))

    def eBalance(mTEPES, sc, p, n, nd):
        return (sum(mTEPES.vTotalOutput[sc, p, n, g] for g in mTEPES.g if (nd, g) in mTEPES.n2g) - sum(mTEPES.vESSCharge[sc, p, n, es] for es in mTEPES.es if (nd, es) in mTEPES.n2g) + mTEPES.vENS[sc, p, n, nd] == mTEPES.pDemand[sc, p,n,nd] +
                sum(mTEPES.vLineLosses[sc, p, n, nd, lout] for lout in loutl[nd]) + sum(mTEPES.vFlow[sc, p, n, nd, lout] for lout in lout[nd]) +
                sum(mTEPES.vLineLosses[sc, p, n, ni, nd, cc] for ni, cc in linl [nd]) - sum(mTEPES.vFlow[sc, p, n, ni, nd, cc] for ni, cc in lin [nd]))
    mTEPES.eBalance = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n,
                                 mTEPES.nd, rule=eBalance, doc='load generation balance [GW]')

    print('eBalance              ... ', len(mTEPES.eBalance), ' rows')

    def eESSInventory(mTEPES, sc, p, n, es):
        if mTEPES.n.ord(n) == mTEPES.pCycleTimeStep[es]:
            return mTEPES.pIniInventory[sc, p, n, es]                                          + sum(mTEPES.pDuration[n2]*1e-3*(mTEPES.pEnergyInflows[sc, p, n2, es] - mTEPES.vTotalOutput[sc, p, n2, es] + mTEPES.pEfficiency[es]*mTEPES.vESSCharge[sc, p, n2, es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        elif mTEPES.n.ord(n) > mTEPES.pCycleTimeStep[es] and mTEPES.n.ord(n) % mTEPES.pCycleTimeStep[es] == 0:
            return mTEPES.vESSInventory[sc, p, mTEPES.n.prev(n, mTEPES.pCycleTimeStep[es]), es] + sum(mTEPES.pDuration[n2]*1e-3*(mTEPES.pEnergyInflows[sc, p, n2, es] - mTEPES.vTotalOutput[sc, p, n2, es] + mTEPES.pEfficiency[es]*mTEPES.vESSCharge[sc, p, n2,es]) for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pCycleTimeStep[es]:mTEPES.n.ord(n)]) == mTEPES.vESSInventory[sc,p,n,es] + mTEPES.vESSSpillage[sc,p,n,es]
        else:
            return Constraint.Skip
    mTEPES.eESSInventory = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eESSInventory, doc='ESS inventory balance [TWh]')

    print('eESSInventory         ... ', len(mTEPES.eESSInventory), ' rows')

    GeneratingRBITime = time.time() - StartTime
    StartTime = time.time()
    print('Generating reserves/balance/inventory ... ',
          round(GeneratingRBITime), 's')

    # %%
    def eMaxOutput2ndBlock(mTEPES, sc, p, n, nr):
        if sum(mTEPES.pOperReserveUp[sc, p, n, ar] for ar in mTEPES.ar if (ar, nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc, p, n, nr]:
            return (mTEPES.vOutput2ndBlock[sc, p, n, nr] + mTEPES.vReserveUp  [sc, p, n, nr]) / mTEPES.pMaxPower2ndBlock[sc, p, n, nr] <= mTEPES.vCommitment[sc, p, n, nr]
        else:
            return Constraint.Skip
    mTEPES.eMaxOutput2ndBlock = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr,
                                           rule=eMaxOutput2ndBlock, doc='max output of the second block of a committed unit [p.u.]')

    print('eMaxOutput2ndBlock    ... ', len(
        mTEPES.eMaxOutput2ndBlock), ' rows')

    def eMinOutput2ndBlock(mTEPES, sc, p, n, nr):
        if sum(mTEPES.pOperReserveDw[sc, p, n, ar] for ar in mTEPES.ar if (ar, nr) in mTEPES.a2g) and mTEPES.pMaxPower2ndBlock[sc, p, n, nr]:
            return (mTEPES.vOutput2ndBlock[sc, p, n, nr] - mTEPES.vReserveDown[sc, p, n, nr]) / mTEPES.pMaxPower2ndBlock[sc, p, n, nr] >= 0
        else:
            return Constraint.Skip
    mTEPES.eMinOutput2ndBlock = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr,
                                           rule=eMinOutput2ndBlock, doc='min output of the second block of a committed unit [p.u.]')

    print('eMinOutput2ndBlock    ... ', len(
        mTEPES.eMinOutput2ndBlock), ' rows')

    # %%
    def eMaxCharge(mTEPES, sc, p, n, es):
        if sum(mTEPES.pOperReserveUp[sc, p, n, ar] for ar in mTEPES.ar if (ar, es) in mTEPES.a2g) and mTEPES.pMaxCharge[es]:
            return (mTEPES.vESSCharge[sc, p, n, es] + mTEPES.vESSReserveDown[sc, p, n, es]) / mTEPES.pMaxCharge[es] <= 1
        else:
            return Constraint.Skip
    mTEPES.eMaxCharge = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMaxCharge, doc='max charge of an ESS [p.u.]')

    print('eMaxCharge            ... ', len(mTEPES.eMaxCharge), ' rows')

    def eMinCharge(mTEPES, sc, p, n, es):
        if sum(mTEPES.pOperReserveDw[sc, p, n, ar] for ar in mTEPES.ar if (ar, es) in mTEPES.a2g and mTEPES.pMaxCharge[es]):
            return (mTEPES.vESSCharge[sc, p, n, es] - mTEPES.vESSReserveUp[sc, p, n, es]) / mTEPES.pMaxCharge[es] >= 0
        else:
            return Constraint.Skip
    mTEPES.eMinCharge = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eMinCharge, doc='min charge of an ESS [p.u.]')

    print('eMinCharge            ... ', len(mTEPES.eMinCharge), ' rows')

    # def eChargeDischarge(mTEPES,sc,p,n,es):
    #     if mTEPES.pMaxCharge[es]:
    #         return mTEPES.vTotalOutput[sc,p,n,es] / mTEPES.pMaxPower[sc,p,n,es] + mTEPES.vESSCharge[sc,p,n,es] / mTEPES.pMaxCharge[es] <= 1
    #     else:
    #         return Constraint.Skip
    # mTEPES.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es, rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    def eChargeDischarge(mTEPES, sc, p, n, es):
        if mTEPES.pMaxCharge[es]:
            return (mTEPES.vOutput2ndBlock[sc, p, n, es] + mTEPES.vReserveUp[sc, p, n, es]) / mTEPES.pMaxPower2ndBlock[sc, p, n, es] + (mTEPES.vESSCharge[sc, p, n, es] - mTEPES.vESSReserveUp[sc, p, n, es]) / mTEPES.pMaxCharge[es] <= 1
        else:
            return Constraint.Skip
    mTEPES.eChargeDischarge = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.es,
                                         rule=eChargeDischarge, doc='incompatibility between charge and discharge [p.u.]')

    print('eChargeDischarge      ... ', len(mTEPES.eChargeDischarge), ' rows')

    def eTotalOutput(mTEPES, sc, p, n, nr):
        if mTEPES.pMinPower[sc, p, n, nr] == 0:
            return mTEPES.vTotalOutput[sc, p, n, nr] == mTEPES.vOutput2ndBlock[sc, p, n, nr]
        else:
            return mTEPES.vTotalOutput[sc, p, n, nr] / mTEPES.pMinPower[sc, p, n, nr] == mTEPES.vCommitment[sc, p, n, nr] + mTEPES.vOutput2ndBlock[sc, p, n, nr] / mTEPES.pMinPower[sc, p, n, nr]
    mTEPES.eTotalOutput = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput, doc='total output of a unit [GW]')

    print('eTotalOutput          ... ', len(mTEPES.eTotalOutput), ' rows')

    def eUCStrShut(mTEPES, sc, p, n, nr):
        if n == mTEPES.n.first():
            return mTEPES.vCommitment[sc, p, n, nr] - mTEPES.pInitialUC[nr] == mTEPES.vStartUp[sc, p, n, nr] - mTEPES.vShutDown[sc, p, n, nr]
        else:
            return mTEPES.vCommitment[sc, p, n, nr] - mTEPES.vCommitment[sc, p, mTEPES.n.prev(n), nr] == mTEPES.vStartUp[sc, p, n, nr] - mTEPES.vShutDown[sc, p, n, nr]
    mTEPES.eUCStrShut = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr,
                                   rule=eUCStrShut, doc='relation among commitment startup and shutdown')

    print('eUCStrShut            ... ', len(mTEPES.eUCStrShut), ' rows')

    GeneratingGenConsTime = time.time() - StartTime
    StartTime = time.time()
    print('Generating generation constraints     ... ',
          round(GeneratingGenConsTime), 's')

    # %%
    def eRampUp(mTEPES, sc, p, n, t):
        if mTEPES.pRampUp[t] and mTEPES.pRampUp[t] < mTEPES.pMaxPower2ndBlock[sc, p, n, t] and n == mTEPES.n.first():
            return (mTEPES.vOutput2ndBlock[sc, p, n, t] - max(mTEPES.pInitialOutput[t]-mTEPES.pMinPower[sc, p, n, t], 0) + mTEPES.vReserveUp[sc, p, n, t]) / mTEPES.pDuration[n] / mTEPES.pRampUp[t] <= mTEPES.vCommitment[sc, p, n, t] - mTEPES.vStartUp[sc, p, n, t]
        elif mTEPES.pRampUp[t] and mTEPES.pRampUp[t] < mTEPES.pMaxPower2ndBlock[sc, p, n, t]:
            return (mTEPES.vOutput2ndBlock[sc, p, n, t] - mTEPES.vOutput2ndBlock[sc, p, mTEPES.n.prev(n), t] + mTEPES.vReserveUp[sc, p, n, t]) / mTEPES.pDuration[n] / mTEPES.pRampUp[t] <= mTEPES.vCommitment[sc, p, n, t] - mTEPES.vStartUp[sc, p, n, t]
        else:
            return Constraint.Skip
    mTEPES.eRampUp = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n,
                                mTEPES.t, rule=eRampUp, doc='maximum ramp up   [p.u.]')

    print('eRampUp               ... ', len(mTEPES.eRampUp), ' rows')

    def eRampDw(mTEPES, sc, p, n, t):
        if mTEPES.pRampDw[t] and mTEPES.pRampDw[t] < mTEPES.pMaxPower2ndBlock[sc, p, n, t] and n == mTEPES.n.first():
            return (mTEPES.vOutput2ndBlock[sc, p, n, t] - max(mTEPES.pInitialOutput[t]-mTEPES.pMinPower[sc, p, n, t], 0) - mTEPES.vReserveDown[sc, p, n, t]) / mTEPES.pDuration[n] / mTEPES.pRampDw[t] >= - mTEPES.pInitialUC[t] + mTEPES.vShutDown[sc, p, n, t]
        elif mTEPES.pRampDw[t] and mTEPES.pRampDw[t] < mTEPES.pMaxPower2ndBlock[sc, p, n, t]:
            return (mTEPES.vOutput2ndBlock[sc, p, n, t] - mTEPES.vOutput2ndBlock[sc, p, mTEPES.n.prev(n), t] - mTEPES.vReserveDown[sc, p, n, t]) / mTEPES.pDuration[n] / mTEPES.pRampDw[t] >= - mTEPES.vCommitment[sc, p, mTEPES.n.prev(n), t] + mTEPES.vShutDown[sc, p, n, t]
        else:
            return Constraint.Skip
    mTEPES.eRampDw = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n,
                                mTEPES.t, rule=eRampDw, doc='maximum ramp down [p.u.]')

    print('eRampDw               ... ', len(mTEPES.eRampDw), ' rows')

    GeneratingRampsTime = time.time() - StartTime
    StartTime = time.time()
    print('Generating ramps   up/down            ... ',
          round(GeneratingRampsTime), 's')

    # %%
    def eMinUpTime(mTEPES, sc, p, n, t):
        if mTEPES.pUpTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pUpTime[t]:
            return sum(mTEPES.vStartUp[sc, p, n2, t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pUpTime[t]:mTEPES.n.ord(n)]) <= mTEPES.vCommitment[sc, p, n, t]
        else:
            return Constraint.Skip
    mTEPES.eMinUpTime = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinUpTime, doc='minimum up   time [h]')

    print('eMinUpTime            ... ', len(mTEPES.eMinUpTime), ' rows')

    def eMinDownTime(mTEPES, sc, p, n, t):
        if mTEPES.pDwTime[t] > 1 and mTEPES.n.ord(n) >= mTEPES.pDwTime[t]:
            return sum(mTEPES.vShutDown[sc, p, n2, t] for n2 in list(mTEPES.n2)[mTEPES.n.ord(n)-mTEPES.pDwTime[t]:mTEPES.n.ord(n)]) <= 1 - mTEPES.vCommitment[sc, p, n, t]
        else:
            return Constraint.Skip
    mTEPES.eMinDownTime = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.t, rule=eMinDownTime, doc='minimum down time [h]')

    print('eMinDownTime          ... ', len(mTEPES.eMinDownTime), ' rows')

    GeneratingMinUDTime = time.time() - StartTime
    StartTime = time.time()
    print('Generating minimum up/down time       ... ',
          round(GeneratingMinUDTime), 's')

    # %%
    def eInstalNetCap1(mTEPES, sc, p, n, ni, nf, cc):
        return mTEPES.vFlow[sc, p, n, ni, nf, cc] / mTEPES.pLineNTC[ni, nf, cc] >= - mTEPES.vNetworkInvest[ni, nf, cc]
    mTEPES.eInstalNetCap1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc,
                                       rule=eInstalNetCap1, doc='maximum flow by installed network capacity [p.u.]')

    print('eInstalNetCap1        ... ', len(mTEPES.eInstalNetCap1), ' rows')

    def eInstalNetCap2(mTEPES, sc, p, n, ni, nf, cc):
        return mTEPES.vFlow[sc, p, n, ni, nf, cc] / mTEPES.pLineNTC[ni, nf, cc] <= mTEPES.vNetworkInvest[ni, nf, cc]
    mTEPES.eInstalNetCap2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc,
                                       rule=eInstalNetCap2, doc='maximum flow by installed network capacity [p.u.]')

    print('eInstalNetCap2        ... ', len(mTEPES.eInstalNetCap2), ' rows')

    def eKirchhoff2ndLawExst(mTEPES, sc, p, n, ni, nf, cc):
        return mTEPES.vFlow[sc, p, n, ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] - (mTEPES.vTheta[sc, p, n, ni] - mTEPES.vTheta[sc, p, n, nf]) / mTEPES.pLineX[ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] * mTEPES.pSBase == 0
    mTEPES.eKirchhoff2ndLawExst = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lea, rule=eKirchhoff2ndLawExst, doc='flow for each AC existing  line [rad]')

    print('eKirchhoff2ndLawExst  ... ', len(
        mTEPES.eKirchhoff2ndLawExst), ' rows')

    def eKirchhoff2ndLawCnd1(mTEPES, sc, p, n, ni, nf, cc):
        return mTEPES.vFlow[sc, p, n, ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] - (mTEPES.vTheta[sc, p, n, ni] - mTEPES.vTheta[sc, p, n, nf]) / mTEPES.pLineX[ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] * mTEPES.pSBase >= - 1 + mTEPES.vNetworkInvest[ni, nf,cc]
    mTEPES.eKirchhoff2ndLawCnd1 = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLawCnd1, doc='flow for each AC candidate line [rad]')

    print('eKirchhoff2ndLawCnd1  ... ', len(
        mTEPES.eKirchhoff2ndLawCnd1), ' rows')

    def eKirchhoff2ndLawCnd2(mTEPES, sc, p, n, ni, nf, cc):
        return mTEPES.vFlow[sc, p, n, ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] - (mTEPES.vTheta[sc, p, n, ni] - mTEPES.vTheta[sc, p, n, nf]) / mTEPES.pLineX[ni, nf, cc] / mTEPES.pBigMFlow[ni, nf, cc] * mTEPES.pSBase <=   1 - mTEPES.vNetworkInvest[ni, nf,cc]
    mTEPES.eKirchhoff2ndLawCnd2 = Constraint(
        mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lca, rule=eKirchhoff2ndLawCnd2, doc='flow for each AC candidate line [rad]')

    print('eKirchhoff2ndLawCnd2  ... ', len(
        mTEPES.eKirchhoff2ndLawCnd2), ' rows')

    def eLineLosses1(mTEPES, sc, p, n, ni, nf, cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc, p, n, ni, nf, cc] >= - 0.5 * mTEPES.pLineLossFactor[ni, nf, cc] * mTEPES.vFlow[sc, p, n, ni, nf, cc]
    mTEPES.eLineLosses1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll,
                                     rule=eLineLosses1, doc='ohmic losses for all the lines [GW]')

    print('eLineLosses1          ... ', len(mTEPES.eLineLosses1), ' rows')

    def eLineLosses2(mTEPES, sc, p, n, ni, nf, cc):
        if mTEPES.pIndNetLosses:
            return mTEPES.vLineLosses[sc, p, n, ni, nf, cc] >= 0.5 * mTEPES.pLineLossFactor[ni, nf, cc] * mTEPES.vFlow[sc, p, n, ni, nf, cc]
    mTEPES.eLineLosses2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.ll,
                                     rule=eLineLosses2, doc='ohmic losses for all the lines [GW]')

    print('eLineLosses2          ... ', len(mTEPES.eLineLosses2), ' rows')

    GeneratingNetConsTime = time.time() - StartTime
    StartTime = time.time()
    print('Generating network    constraints     ... ',
          round(GeneratingNetConsTime), 's')
