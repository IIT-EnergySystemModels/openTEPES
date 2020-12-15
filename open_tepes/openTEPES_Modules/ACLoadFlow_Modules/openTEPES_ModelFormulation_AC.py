# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020

import time
from   collections   import defaultdict
from   pyomo.environ import Constraint, tan, acos, Objective, minimize
def ModelFormulation_AC(mTEPES):
    StartTime = time.time()

    # Deactivating constraints related to DC power flow
    mTEPES.eTotalTCost.deactivate()           # Deactivate all indices from eTotalTCost
    mTEPES.del_component(mTEPES.eTotalFCost)
    mTEPES.del_component(mTEPES.eTotalRCost)
    mTEPES.del_component(mTEPES.eBalance)
    mTEPES.del_component(mTEPES.eTotalOutput)
    mTEPES.del_component(mTEPES.eInstalNetCap1)
    mTEPES.del_component(mTEPES.eInstalNetCap2)
    mTEPES.del_component(mTEPES.eKirchhoff2ndLawExst)
    mTEPES.del_component(mTEPES.eKirchhoff2ndLawCnd1)
    mTEPES.del_component(mTEPES.eKirchhoff2ndLawCnd2)
    mTEPES.del_component(mTEPES.eLineLosses1)
    mTEPES.del_component(mTEPES.eLineLosses2)

    DeactivatingDCconstrainst = time.time() - StartTime
    StartTime        = time.time()
    print('Deactivating DC constraints           ... ', round(DeactivatingDCconstrainst), 's')

    def eTotalFCost(mTEPES):
        return mTEPES.vTotalFCost == sum(mTEPES.pGenFixedCost[gc] * mTEPES.vGenerationInvest[gc] for gc in mTEPES.gc) + sum(mTEPES.pNetFixedCost[lc] * mTEPES.vNetworkInvest[lc] for lc in mTEPES.lc) + sum(mTEPES.pShuntFixedCost[shc] * mTEPES.vShuntInvest[shc] for shc in mTEPES.shc)
    mTEPES.eTotalFCost = Constraint(rule=eTotalFCost, doc='total system fixed    cost [MEUR]')

    def eTotalRCost(mTEPES):
        return mTEPES.vTotalRCost == sum(mTEPES.pScenProb[sc] * mTEPES.pDuration[n] * mTEPES.pENSCost             * mTEPES.vENS        [sc,p,n,nd] * (mTEPES.pDemand[sc,p,n,nd] + mTEPES.pReactiveDemand[sc,p,n,nd]) for sc,p,n,nd in mTEPES.sc*mTEPES.p*mTEPES.n*mTEPES.nd)
    mTEPES.eTotalRCost = Constraint(rule=eTotalRCost, doc='system reliability cost [MEUR]')

    mTEPES.eTotalTCost.activate()         # Deactivate all indices from eTotalTCost

    GeneratingOFTime_AC = time.time() - StartTime
    StartTime           = time.time()
    print('Generating AC objective function      ... ', round(GeneratingOFTime_AC), 's')

    # incoming and outgoing lines (lin) (lout)
    lin   = defaultdict(list)
    linl  = defaultdict(list)
    lout  = defaultdict(list)
    loutl = defaultdict(list)
    for ni,nf,cc in mTEPES.la:
        lin  [nf].append((ni,cc))
    for ni,nf,cc in mTEPES.la:
        lout [ni].append((nf,cc))
    for ni,nf,cc in mTEPES.ll:
        linl [nf].append((ni,cc))
    for ni,nf,cc in mTEPES.ll:
        loutl[ni].append((nf,cc))

    def eBalance_P(mTEPES,sc,p,n,nd):
        return (sum(mTEPES.vTotalOutput[sc,p,n,g] for g in mTEPES.g if (nd,g) in mTEPES.n2g) - sum(mTEPES.vESSCharge[sc,p,n,es] for es in mTEPES.es if (nd,es) in mTEPES.n2g)
                - mTEPES.pDemand[sc,p,n,nd] * (1 - mTEPES.vENS[sc,p,n,nd])
                + sum(mTEPES.vP[sc, p, n, ni, nd, cc] for ni, cc in lin[nd])
                - sum(mTEPES.vP[sc,p,n,nd,lout ] + mTEPES.pLineR[nd,lout ] * mTEPES.vCurrentFlow_sqr[sc,p,n,nd,lout ] for lout  in lout[nd])
                - sum(mTEPES.vVoltageMag_sqr[sc,p,n,nd] * mTEPES.pBusGshb[sh] for sh in mTEPES.sh if (nd,sh) in mTEPES.n2sh) == 0)
    mTEPES.eBalance_P = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance_P, doc='Active power generation balance [GW]')

    print('eBalance_P            ... ', len(mTEPES.eBalance_P), ' rows')

    def eBalance_Q(mTEPES,sc,p,n,nd):
        return (sum(mTEPES.vReactiveTotalOutput[sc,p,n,tq] for tq in mTEPES.tq if (nd,tq) in mTEPES.n2g) + sum(mTEPES.vSynchTotalOutput[sc,p,n,sq] for sq in mTEPES.gq if (nd,sq) in mTEPES.n2gq)
                - mTEPES.pReactiveDemand[sc,p,n,nd] * (1 - mTEPES.vENS[sc,p,n,nd])
                + sum(mTEPES.vQ[sc, p, n, ni, nd, cc] + mTEPES.vQ_shl[sc, p, n, nd, ni, nd, cc] for ni, cc in lin[nd])
                - sum(mTEPES.vQ[sc,p,n,nd,lout ] - mTEPES.vQ_shl[sc,p,n,nd,nd,lout ] + mTEPES.pLineX[nd,lout] * mTEPES.vCurrentFlow_sqr[sc,p,n,nd,lout ] for lout  in lout[nd])
                + sum(mTEPES.vQ_shc[sc,p,n,sh] for sh in mTEPES.sh if (nd,sh) in mTEPES.n2sh) == 0)
    mTEPES.eBalance_Q = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, rule=eBalance_Q, doc='Reactive power generation balance [GVaR]')

    print('eBalance_Q            ... ', len(mTEPES.eBalance_Q), ' rows')

    AC_PowerBalance     = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Balance                      ... ', round(AC_PowerBalance), 's')

    def eTotalOutput_P(mTEPES,sc,p,n,nr):
        return mTEPES.vTotalOutput[sc,p,n,nr] == mTEPES.pMinPower[sc,p,n,nr] * mTEPES.vCommitment[sc,p,n,nr] + mTEPES.vOutput2ndBlock[sc,p,n,nr]
    mTEPES.eTotalOutput_P = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput_P, doc='total output of active power by a unit [GW]')

    print('eTotalOutput_P        ... ', len(mTEPES.eTotalOutput_P), ' rows')

    # def eTotalOutput_Q1(mTEPES,sc,p,n,nr):
    #     return mTEPES.vReactiveTotalOutput[sc,p,n,nr] <=  mTEPES.pMaxReactivePower[sc,p,n,nr]
    # mTEPES.eTotalOutput_Q1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput_Q1, doc='total output of reactive power by a unit in the capacitive side [Gvar]')
    #
    # print('eTotalOutput_Q1       ... ', len(mTEPES.eTotalOutput_Q1), ' rows')
    #
    # def eTotalOutput_Q2(mTEPES,sc,p,n,nr):
    #     return mTEPES.vReactiveTotalOutput[sc,p,n,nr] >=  mTEPES.pMinReactivePower[sc,p,n,nr]
    # mTEPES.eTotalOutput_Q2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput_Q2, doc='total output of reactive power by a unit in the inductive side [Gvar]')
    #
    # print('eTotalOutput_Q2       ... ', len(mTEPES.eTotalOutput_Q2), ' rows')

    # def eTotalOutput_Q_Capacitive(mTEPES,sc,p,n,nr):
    #     return mTEPES.vReactiveTotalOutput[sc,p,n,nr] <=  mTEPES.vTotalOutput[sc,p,n,nr] * (tan(acos(mTEPES.pCapacitivePF)))
    # mTEPES.eTotalOutput_Q1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput_Q_Capacitive, doc='total output of reactive power by a unit in the capacitive side [Gvar]')
    #
    # print('eTotalOutput_Q1       ... ', len(mTEPES.eTotalOutput_Q1), ' rows')
    #
    # def eTotalOutput_Q_Inductive(mTEPES,sc,p,n,nr):
    #     return mTEPES.vReactiveTotalOutput[sc,p,n,nr] >= -mTEPES.vTotalOutput[sc,p,n,nr] * (tan(acos(mTEPES.pInductivePF)))
    # mTEPES.eTotalOutput_Q2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nr, rule=eTotalOutput_Q_Inductive, doc='total output of reactive power by a unit in the inductive side [Gvar]')
    #
    # print('eTotalOutput_Q2       ... ', len(mTEPES.eTotalOutput_Q2), ' rows')

    AC_PowerGeneration  = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Generation                   ... ', round(AC_PowerGeneration), 's')

    def eInstalNetCap(mTEPES,sc,p,n,ni,nf,cc):
        return mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc] / (mTEPES.pLineSmax[ni,nf,cc] ** 2 / mTEPES.pVmax[sc,p,n,ni]**2) <= mTEPES.vNetworkInvest[ni,nf,cc]
    mTEPES.eInstalNetCap = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eInstalNetCap, doc='maximum flow by installed network capacity [p.u.]')

    print('eInstalNetCap         ... ', len(mTEPES.eInstalNetCap), ' rows')

    def eVoltageDiffExst(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vVoltageMag_sqr[sc,p,n,ni] * (mTEPES.pLineTAP[ni,nf,cc]**2) - mTEPES.vVoltageMag_sqr[sc,p,n,nf]
                - mTEPES.pLineZ2[ni,nf,cc] * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]
                - 2 * (mTEPES.pLineR[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc] + mTEPES.pLineX[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc]) == 0)
    mTEPES.eVoltageDiffExst = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lea, rule=eVoltageDiffExst, doc='Voltage difference between nodes considering existent lines [p.u.]')

    print('eVoltageDiffExst      ... ', len(mTEPES.eVoltageDiffExst), ' rows')

    def eVoltageDiffCand1(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vVoltageMag_sqr[sc,p,n,ni] * (mTEPES.pLineTAP[ni,nf,cc]**2) - mTEPES.vVoltageMag_sqr[sc,p,n,nf]
                - mTEPES.pLineZ2[ni,nf,cc] * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]
                - 2 * (mTEPES.pLineR[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc] + mTEPES.pLineX[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc])) <=  (mTEPES.pVmax[sc,p,n,nf]**2 - mTEPES.pVmin[sc,p,n,nf]**2) * (1-mTEPES.vNetworkInvest[ni,nf,cc])
    mTEPES.eVoltageDiffCand1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eVoltageDiffCand1, doc='Voltage difference between nodes considering existent lines [p.u.]')

    print('eVoltageDiffCand1     ... ', len(mTEPES.eVoltageDiffCand1), ' rows')

    def eVoltageDiffCand2(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vVoltageMag_sqr[sc,p,n,ni] * (mTEPES.pLineTAP[ni,nf,cc]**2) - mTEPES.vVoltageMag_sqr[sc,p,n,nf]
                - mTEPES.pLineZ2[ni,nf,cc] * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc]
                - 2 * (mTEPES.pLineR[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc] + mTEPES.pLineX[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc])) >= -(mTEPES.pVmax[sc,p,n,ni]**2 - mTEPES.pVmin[sc,p,n,ni]**2) * (1-mTEPES.vNetworkInvest[ni,nf,cc])
    mTEPES.eVoltageDiffCand2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eVoltageDiffCand2, doc='Voltage magnitude difference between nodes considering existent lines [p.u.]')

    print('eVoltageDiffCand2     ... ', len(mTEPES.eVoltageDiffCand2), ' rows')

    VoltageDifference_AC= time.time() - StartTime
    StartTime           = time.time()
    print('AC Voltage Magnitude Difference       ... ', round(VoltageDifference_AC), 's')

    # def eAngleDiffBounds(mTEPES,sc,p,n,ni,nf,cc):
    #     return (mTEPES.vThD[sc,p,n,ni,nf,cc]  == mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf])
    # mTEPES.eAngleDiffBounds = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eAngleDiffBounds, doc='Phase angle difference between nodes considering existent lines [p.u.]')
    #
    # print('eAngleDiffBounds      ... ', len(mTEPES.eAngleDiffBounds), ' rows')

    # def eCycleAngleDiffBounds(mTEPES,sc,p,n,ni,nf,cc):
    #     return (mTEPES.vThD[sc,p,n,ni,nf,cc]
    #             - mTEPES.pLineX[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc]
    #             + mTEPES.pLineR[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc] == 0)
    # mTEPES.eCycleAngleDiffBounds = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCycleAngleDiffBounds, doc='Phase angle difference between nodes considering existent lines [p.u.]')

    # print('eAngleDiffBounds      ... ', len(mTEPES.eCycleAngleDiffBounds), ' rows')

    def eAngleDiffExst(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.pLineTAP[ni,nf,cc] * mTEPES.pVnom[sc,p,n,ni] * mTEPES.pVnom[sc,p,n,nf] * (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf])
                - mTEPES.pLineX[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc]
                + mTEPES.pLineR[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc] == 0)
    mTEPES.eAngleDiffExst = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lea, rule=eAngleDiffExst, doc='Voltage angle difference between nodes considering existent lines [p.u.]')

    print('eAngleDiffExst        ... ', len(mTEPES.eAngleDiffExst), ' rows')

    def eAngleDiffCand1(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.pLineTAP[ni,nf,cc] * mTEPES.pVnom[sc,p,n,ni] * mTEPES.pVnom[sc,p,n,nf] * (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf])
                - mTEPES.pLineX[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc]
                + mTEPES.pLineR[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc]) <=  2 * mTEPES.pMaxTheta[sc,p,n,ni] * mTEPES.pVmax[sc,p,n,nf]**2 * (1-mTEPES.vNetworkInvest[ni,nf,cc])
    mTEPES.eAngleDiffCand1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eAngleDiffCand1, doc='Voltage angle difference between nodes considering candidate lines [p.u.]')

    print('eAngleDiffCand1       ... ', len(mTEPES.eAngleDiffCand1), ' rows')

    def eAngleDiffCand2(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.pLineTAP[ni,nf,cc] * mTEPES.pVnom[sc,p,n,ni] * mTEPES.pVnom[sc,p,n,nf] * (mTEPES.vTheta[sc,p,n,ni] - mTEPES.vTheta[sc,p,n,nf])
                - mTEPES.pLineX[ni,nf,cc] * mTEPES.vP[sc,p,n,ni,nf,cc]
                + mTEPES.pLineR[ni,nf,cc] * mTEPES.vQ[sc,p,n,ni,nf,cc]) >= -2 * mTEPES.pMaxTheta[sc,p,n,ni] * mTEPES.pVmax[sc,p,n,ni]**2 * (1-mTEPES.vNetworkInvest[ni,nf,cc])
    mTEPES.eAngleDiffCand2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.lc, rule=eAngleDiffCand2, doc='Voltage angle difference between nodes considering candidate lines [p.u.]')

    print('eAngleDiffCand2       ... ', len(mTEPES.eAngleDiffCand2), ' rows')

    AngleDifference_AC  = time.time() - StartTime
    StartTime           = time.time()
    print('AC Voltage Angle Difference           ... ', round(AngleDifference_AC), 's')

    # def eCurrentFlow(mTEPES,sc,p,n,ni,nf,cc):
    # #     return ((mTEPES.pVnom**2) * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc] >= (mTEPES.vP[sc,p,n,ni,nf,cc])**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc])**2)
    # # mTEPES.eCurrentFlow = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow, doc='Linear constraint for current flow  [p.u.]')
    #     return (mTEPES.vVoltageMag_sqr[sc,p,n,nf] * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc] >= (mTEPES.vP[sc,p,n,ni,nf,cc])**2 + (mTEPES.vQ[sc,p,n,ni,nf,cc])**2)
    # mTEPES.eCurrentFlow = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow, doc='Linear constraint for current flow  [p.u.]')

    def eCurrentFlow(mTEPES,sc,p,n,ni,nf,cc):
        return ((mTEPES.pVnom[sc,p,n,nf]**2) * mTEPES.vCurrentFlow_sqr[sc,p,n,ni,nf,cc] == sum(mTEPES.pLineM[ni,nf,cc,l] * mTEPES.vDelta_P[sc,p,n,ni,nf,cc,l] for l in mTEPES.L) + sum(mTEPES.pLineM[ni,nf,cc,l] * mTEPES.vDelta_Q[sc,p,n,ni,nf,cc,l] for l in mTEPES.L))
    mTEPES.eCurrentFlow = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow, doc='Linear constraint for current flow  [p.u.]')

    print('eCurrentFlow          ... ', len(mTEPES.eCurrentFlow), ' rows')

    def eCurrentFlow_LinearP1(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vP_max[sc,p,n,ni,nf,cc] - mTEPES.vP_min[sc,p,n,ni,nf,cc] == mTEPES.vP[sc,p,n,ni,nf,cc])
    mTEPES.eCurrentFlow_LinearP1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow_LinearP1, doc='Linear constraint for current flow relate to P [p.u.]')

    print('eCurrentFlow_LinearP1 ... ', len(mTEPES.eCurrentFlow_LinearP1), ' rows')

    def eCurrentFlow_LinearP2(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vP_max[sc,p,n,ni,nf,cc] + mTEPES.vP_min[sc,p,n,ni,nf,cc] == sum(mTEPES.vDelta_P[sc,p,n,ni,nf,cc,l] for l in mTEPES.L))
    mTEPES.eCurrentFlow_LinearP2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow_LinearP2, doc='Linear constraint for current flow relate to P [p.u.]')

    print('eCurrentFlow_LinearP2 ... ', len(mTEPES.eCurrentFlow_LinearP2), ' rows')

    def eCurrentFlow_LinearQ1(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vQ_max[sc,p,n,ni,nf,cc] - mTEPES.vQ_min[sc,p,n,ni,nf,cc] == mTEPES.vQ[sc,p,n,ni,nf,cc])
    mTEPES.eCurrentFlow_LinearQ1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow_LinearQ1, doc='Linear constraint for current flow relate to Q [p.u.]')

    print('eCurrentFlow_LinearQ1 ... ', len(mTEPES.eCurrentFlow_LinearQ1), ' rows')

    def eCurrentFlow_LinearQ2(mTEPES,sc,p,n,ni,nf,cc):
        return (mTEPES.vQ_max[sc,p,n,ni,nf,cc] + mTEPES.vQ_min[sc,p,n,ni,nf,cc] == sum(mTEPES.vDelta_Q[sc,p,n,ni,nf,cc,l] for l in mTEPES.L))
    mTEPES.eCurrentFlow_LinearQ2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.la, rule=eCurrentFlow_LinearQ2, doc='Linear constraint for current flow relate to Q [p.u.]')

    print('eCurrentFlow_LinearQ2 ... ', len(mTEPES.eCurrentFlow_LinearQ2), ' rows')

    CurrentFlowLinear_AC= time.time() - StartTime
    StartTime           = time.time()
    print('AC Current Flow Linearization         ... ', round(CurrentFlowLinear_AC), 's')

    def eLineQPowerInjExst(mTEPES,sc,p,n,k,ni,nf,cc):
        if k == ni or k == nf:
            return (mTEPES.vQ_shl[sc,p,n,k,ni,nf,cc] == mTEPES.pLineBsh[ni,nf,cc] * mTEPES.vVoltageMag_sqr[sc,p,n,k])
        else:
            return Constraint.Skip
    mTEPES.eLineQPowerInjExst = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.lea, rule=eLineQPowerInjExst, doc='Reactive power injection from shunt component of existing lines [Gvar]')

    print('eLineQPowerInjExst    ... ', len(mTEPES.eLineQPowerInjExst), ' rows')

    def eLineQPowerInjCand1_C1(mTEPES,sc,p,n,k,ni,nf,cc):
        if k == ni or k == nf:
            return (mTEPES.vQ_shl[sc,p,n,k,ni,nf,cc] - mTEPES.pLineBsh[ni,nf,cc] * mTEPES.vVoltageMag_sqr[sc,p,n,k] >= -(mTEPES.pVmax[sc,p,n,k]**2) * mTEPES.pLineBsh[ni,nf,cc] * (1-mTEPES.vNetworkInvest[ni,nf,cc]))
        else:
            return Constraint.Skip
    mTEPES.eLineQPowerInjCand1_C1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.lc, rule=eLineQPowerInjCand1_C1, doc='Reactive power injection from shunt component of candidate lines [Gvar]')

    print('eLineQPowerInjCand1_C1... ', len(mTEPES.eLineQPowerInjCand1_C1), ' rows')

    def eLineQPowerInjCand1_C2(mTEPES,sc,p,n,k,ni,nf,cc):
        if k == ni or k == nf:
            return (mTEPES.vQ_shl[sc,p,n,k,ni,nf,cc] - mTEPES.pLineBsh[ni,nf,cc] * mTEPES.vVoltageMag_sqr[sc,p,n,k] <= -(mTEPES.pVmin[sc,p,n,k]**2) * mTEPES.pLineBsh[ni,nf,cc] * (1-mTEPES.vNetworkInvest[ni,nf,cc]))
        else:
            return Constraint.Skip
    mTEPES.eLineQPowerInjCand1_C2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.lc, rule=eLineQPowerInjCand1_C2, doc='Reactive power injection from shunt component of candidate lines [Gvar]')

    print('eLineQPowerInjCand1_C2... ', len(mTEPES.eLineQPowerInjCand1_C2), ' rows')

    def eLineQPowerInjCand2_C1(mTEPES,sc,p,n,k,ni,nf,cc):
        if k == ni or k == nf:
            return (mTEPES.vQ_shl[sc,p,n,k,ni,nf,cc] >= (mTEPES.pVmin[sc,p,n,k]**2) * mTEPES.pLineBsh[ni,nf,cc] * mTEPES.vNetworkInvest[ni,nf,cc])
        else:
            return Constraint.Skip
    mTEPES.eLineQPowerInjCand2_C1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.lc, rule=eLineQPowerInjCand2_C1, doc='Reactive power injection from shunt component of candidate lines [Gvar]')

    print('eLineQPowerInjCand2_C1... ', len(mTEPES.eLineQPowerInjCand2_C1), ' rows')

    def eLineQPowerInjCand2_C2(mTEPES,sc,p,n,k,ni,nf,cc):
        if k == ni or k == nf:
            return (mTEPES.vQ_shl[sc,p,n,k,ni,nf,cc] <= (mTEPES.pVmax[sc,p,n,k]**2) * mTEPES.pLineBsh[ni,nf,cc] * mTEPES.vNetworkInvest[ni,nf,cc])
        else:
            return Constraint.Skip
    mTEPES.eLineQPowerInjCand2_C2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.nd, mTEPES.lc, rule=eLineQPowerInjCand2_C2, doc='Reactive power injection from shunt component of candidate lines [Gvar]')

    print('eLineQPowerInjCand2_C2... ', len(mTEPES.eLineQPowerInjCand2_C2), ' rows')

    LineQPowerInjection = time.time() - StartTime
    StartTime           = time.time()
    print('AC Reactive power injection from lines... ', round(LineQPowerInjection), 's')

    def eShuntQPowerInjExst(mTEPES,sc,p,n,sh):
        return (mTEPES.vQ_shc[sc,p,n,sh] == mTEPES.pBusBshb[sh] * mTEPES.vVoltageMag_sqr[sc,p,n,mTEPES.sh2n[sh]])
    mTEPES.eShuntQPowerInjExst = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.she, rule=eShuntQPowerInjExst, doc='Reactive power injection from existing shunt devices [Gvar]')

    print('eShuntQPowerInjExst   ... ', len(mTEPES.eShuntQPowerInjExst), ' rows')

    def eShuntQPowerInjCand1_C1(mTEPES,sc,p,n,sh):
        return (mTEPES.vQ_shc[sc,p,n,sh] - mTEPES.pBusBshb[sh] * mTEPES.vVoltageMag_sqr[sc,p,n,mTEPES.sh2n[sh]] >= -(mTEPES.pVmax[sc,p,n,mTEPES.sh2n[sh]]**2) * mTEPES.pBusBshb[sh] * (1-mTEPES.vShuntInvest[sh]))
    mTEPES.eShuntQPowerInjCand1_C1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.shc, rule=eShuntQPowerInjCand1_C1, doc='Reactive power injection from candidate shunt devices [Gvar]')

    print('eShuntQPowerInjCand1_C1... ', len(mTEPES.eShuntQPowerInjCand1_C1), ' rows')

    def eShuntQPowerInjCand1_C2(mTEPES,sc,p,n,sh):
        return (mTEPES.vQ_shc[sc,p,n,sh] - mTEPES.pBusBshb[sh] * mTEPES.vVoltageMag_sqr[sc,p,n,mTEPES.sh2n[sh]] <= -(mTEPES.pVmin[sc,p,n,mTEPES.sh2n[sh]]**2) * mTEPES.pBusBshb[sh] * (1-mTEPES.vShuntInvest[sh]))
    mTEPES.eShuntQPowerInjCand1_C2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.shc, rule=eShuntQPowerInjCand1_C2, doc='Reactive power injection from candidate shunt devices [Gvar]')

    print('eShuntQPowerInjCand1_C2... ', len(mTEPES.eShuntQPowerInjCand1_C2), ' rows')

    def eShuntQPowerInjCand2_C1(mTEPES,sc,p,n,sh):
        return (mTEPES.vQ_shc[sc,p,n,sh] >= (mTEPES.pVmin[sc,p,n,mTEPES.sh2n[sh]]**2) * mTEPES.pBusBshb[sh] * mTEPES.vShuntInvest[sh])
    mTEPES.eShuntQPowerInjCand2_C1 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.shc, rule=eShuntQPowerInjCand2_C1, doc='Reactive power injection from candidate shunt devices [Gvar]')

    print('eShuntQPowerInjCand2_C1... ', len(mTEPES.eShuntQPowerInjCand2_C1), ' rows')

    def eShuntQPowerInjCand2_C2(mTEPES,sc,p,n,sh):
        return (mTEPES.vQ_shc[sc,p,n,sh] <= (mTEPES.pVmax[sc,p,n,mTEPES.sh2n[sh]]**2) * mTEPES.pBusBshb[sh] * mTEPES.vShuntInvest[sh])
    mTEPES.eShuntQPowerInjCand2_C2 = Constraint(mTEPES.sc, mTEPES.p, mTEPES.n, mTEPES.shc, rule=eShuntQPowerInjCand2_C2, doc='Reactive power injection from candidate shunt devices [Gvar]')

    print('eShuntQPowerInjCand2_C2... ', len(mTEPES.eShuntQPowerInjCand2_C2), ' rows')

    ShuntQPowerInjection= time.time() - StartTime
    StartTime           = time.time()
    print('AC Reactive power injection from shunts...', round(ShuntQPowerInjection), 's')