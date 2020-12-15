# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020

import time
import math
import pandas as pd
import builtins
from   collections   import defaultdict
from   pyomo.environ import Objective, minimize, Param, Constraint, NonNegativeReals, Var, Reals, UnitInterval, Binary, AbstractModel, acos, sin, tan
def NLP_BFrPowerFlow_AC(CaseName, mTEPES):
    StartTime = time.time()

    print('Model formulation           ****')

    builtins.mTEPES_NLP = AbstractModel('Open NLP model to validate the openTEPES results - Version 1.0.01 - August 19, 2020')

    mTEPES_NLP.pPdf              = Param(mTEPES.nd , within=Reals, initialize=0.0, doc='Active power demand', mutable=True)
    mTEPES_NLP.pQdf              = Param(mTEPES.nd , within=Reals, initialize=0.0, doc='Reactive power demand', mutable=True)

    mTEPES_NLP.pLineG            = Param(mTEPES.la, initialize=mTEPES.pLineG)
    mTEPES_NLP.pLineB            = Param(mTEPES.la, initialize=mTEPES.pLineB)
    mTEPES_NLP.pLineR            = Param(mTEPES.la, initialize=mTEPES.pLineR)
    mTEPES_NLP.pLineX            = Param(mTEPES.la, initialize=mTEPES.pLineX)
    mTEPES_NLP.pLineBsh          = Param(mTEPES.la, initialize=mTEPES.pLineBsh)
    mTEPES_NLP.pLineTAP          = Param(mTEPES.la, initialize=mTEPES.pLineTAP)
    mTEPES_NLP.pLineZ2           = Param(mTEPES.la, initialize=mTEPES.pLineZ2)
    mTEPES_NLP.pBusGshb          = Param(mTEPES.sh, initialize=mTEPES.pBusGshb)
    mTEPES_NLP.pBusBshb          = Param(mTEPES.sh, initialize=mTEPES.pBusBshb)

    ParametersDefTime= time.time() - StartTime
    StartTime        = time.time()
    print('Parameters definition                 ... ', round(ParametersDefTime), 's')

    mTEPES_NLP.vVsqr             = Var(mTEPES.nd , within=NonNegativeReals, initialize=1.0, doc='Voltage magnitude [p.u.]')
    mTEPES_NLP.vTheta            = Var(mTEPES.nd , within=Reals           , initialize=0.0, doc='Voltage angle                             [rad ]')
    mTEPES_NLP.vPger             = Var(mTEPES.g  , within=NonNegativeReals, initialize=0.0, doc='Active power generation                   [GW  ]')
    mTEPES_NLP.vQger             = Var(mTEPES.nr , within=Reals           , initialize=0.0, doc='Reactive power generation                 [Gvar]')
    mTEPES_NLP.vIsqr             = Var(mTEPES.lei, within=NonNegativeReals, initialize=0.0, doc='Current flow                              [GW  ]')
    mTEPES_NLP.vP                = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Active Power Flow from bus i to bus j     [GW  ]')
    mTEPES_NLP.vQ                = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Reactive Power Flow from bus i to bus j   [Gvar]')
    mTEPES_NLP.vESSCharge        = Var(mTEPES.es , within=NonNegativeReals, initialize=0.0, doc='Energy charge from energy storage systems [Gvar]')
    mTEPES_NLP.vENS              = Var(mTEPES.nd , within=NonNegativeReals, initialize=0.0, bounds=(0,1), doc='energy not served in node   [GW  ]')
    mTEPES_NLP.vSger             = Var(mTEPES.gq , within=Reals           , initialize=0.0, doc='Total output of synchronous condenser     [Gvar]')


    VariableDefTime  = time.time() - StartTime
    StartTime        = time.time()
    print('Variable definition                   ... ', round(VariableDefTime), 's')

    def eTotalTCost(mTEPES_NLP):
        return (sum(mTEPES_NLP.vIsqr[ni,nf,cc] * mTEPES_NLP.pLineR[ni,nf,cc] for ni,nf,cc in mTEPES.lei) + 1e3*sum(mTEPES_NLP.vENS[nd] for nd in mTEPES.nd))
    mTEPES_NLP.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')
    # def eTotalTCost(mTEPES_NLP):
    #     return sum(mTEPES_NLP.vPger[g] for g in mTEPES.g for nd in mTEPES.nd if (nd, g) in mTEPES.n2g if nd == mTEPES.rf.first()) + 1e3*sum(mTEPES_NLP.vENS[nd] for nd in mTEPES.nd)
    # mTEPES_NLP.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')


    GeneratingOFTime = time.time() - StartTime
    StartTime        = time.time()
    print('Generating objective function         ... ', round(GeneratingOFTime), 's')

    # incoming and outgoing lines (lin) (lout)
    lin   = defaultdict(list)
    lout  = defaultdict(list)
    for ni,nf,cc in mTEPES.lei:
        lin  [nf].append((ni,cc))
    for ni,nf,cc in mTEPES.lei:
        lout [ni].append((nf,cc))

    def eBalance_P(mTEPES_NLP,nd):
        return (sum(mTEPES_NLP.vPger[g] for g in mTEPES.g if (nd,g) in mTEPES.n2g) - sum(mTEPES_NLP.vESSCharge[es] for es in mTEPES.es if (nd,es) in mTEPES.n2g)
                - mTEPES_NLP.pPdf[nd]* (1 - mTEPES_NLP.vENS[nd])
                + sum(mTEPES_NLP.vP[ni,nd,cc] for ni,cc in lin [nd])
                - sum(mTEPES_NLP.vP[nd,lout ] + mTEPES_NLP.pLineR[nd,lout]*mTEPES_NLP.vIsqr[nd,lout] for lout  in lout[nd])
                - sum((mTEPES_NLP.vVsqr[nd]) * mTEPES_NLP.pBusGshb[shei] for shei in mTEPES.shei if (nd,shei) in mTEPES.n2sh) ==  0)
    mTEPES_NLP.eBalance_P = Constraint(mTEPES.nd, rule=eBalance_P, doc='Active power generation balance [GW]')

    print('eBalance_P            ... ', len(mTEPES_NLP.eBalance_P), ' rows')

    def eBalance_Q(mTEPES_NLP,nd):
        return (sum(mTEPES_NLP.vQger[nr] for nr in mTEPES.nr if (nd,nr) in mTEPES.n2g) + sum(mTEPES_NLP.vSger[gq] for gq in mTEPES.gq if (nd,gq) in mTEPES.n2gq)
                - mTEPES_NLP.pQdf[nd]* (1 - mTEPES_NLP.vENS[nd])
                + sum(mTEPES_NLP.vQ[ni,nd,cc] + mTEPES_NLP.pLineBsh[ni,nd,cc] * mTEPES_NLP.vVsqr[nd] for ni,cc in lin [nd])
                - sum(mTEPES_NLP.vQ[nd,lout ] - mTEPES_NLP.pLineBsh[nd,lout ] * mTEPES_NLP.vVsqr[nd] + mTEPES_NLP.pLineX[nd,lout] * mTEPES_NLP.vIsqr[nd,lout] for lout  in lout[nd])
                + sum(mTEPES_NLP.vVsqr[nd] * mTEPES_NLP.pBusBshb[shei] for shei in mTEPES.shei if (nd,shei) in mTEPES.n2sh) == 0)
    mTEPES_NLP.eBalance_Q = Constraint(mTEPES.nd, rule=eBalance_Q, doc='Reactive power generation balance [GVaR]')

    print('eBalance_Q            ... ', len(mTEPES_NLP.eBalance_Q), ' rows')

    AC_PowerBalance     = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Balance                      ... ', round(AC_PowerBalance), 's')

    def eVoltageDiff(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vVsqr[ni] * (mTEPES_NLP.pLineTAP[ni,nf,cc]**2)
                - 2 * (mTEPES_NLP.pLineR[ni,nf,cc] * mTEPES_NLP.vP[ni,nf,cc] + mTEPES_NLP.pLineX[ni,nf,cc] * mTEPES_NLP.vQ[ni,nf,cc])
                - mTEPES_NLP.pLineZ2[ni,nf,cc] * mTEPES_NLP.vIsqr[ni,nf,cc]
                - mTEPES_NLP.vVsqr[nf] == 0)
    mTEPES_NLP.eVoltageDiff = Constraint(mTEPES.lei, rule=eVoltageDiff, doc='Voltage difference from bus i to bus j [GW]')

    print('eVoltageDiff          ... ', len(mTEPES_NLP.eVoltageDiff), ' rows')

    def eAngleDiff(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.pLineTAP[ni,nf,cc] * (mTEPES_NLP.vVsqr[ni])**0.5 * (mTEPES_NLP.vVsqr[nf])**0.5 * sin(mTEPES_NLP.vTheta[ni] - mTEPES_NLP.vTheta[nf])
                == mTEPES_NLP.pLineX[ni,nf,cc] * mTEPES_NLP.vP[ni,nf,cc] -  mTEPES_NLP.pLineR[ni,nf,cc] * mTEPES_NLP.vQ[ni,nf,cc])
    mTEPES_NLP.eAngleDiff = Constraint(mTEPES.lei, rule=eAngleDiff, doc='Angle difference from bus j to bus i [GW]')

    print('eAngleDiff            ... ', len(mTEPES_NLP.eAngleDiff), ' rows')

    def eCurrentFlow(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vVsqr[nf] * mTEPES_NLP.vIsqr[ni,nf,cc] == mTEPES_NLP.vP[ni,nf,cc]**2 + mTEPES_NLP.vQ[ni,nf,cc]**2 )
    mTEPES_NLP.eCurrentFlow = Constraint(mTEPES.lei, rule=eCurrentFlow, doc='Reactive power flow from bus i to bus j [Gvar]')

    print('eCurrentFlow          ... ', len(mTEPES_NLP.eCurrentFlow), ' rows')

    # def eTotalOutput_Q_Capacitive(mTEPES_NLP,nr):
    #     return mTEPES_NLP.vQger[nr] <=  mTEPES_NLP.vPger[nr] * (tan(acos(mTEPES.pCapacitivePF)))
    # mTEPES_NLP.eTotalOutput_Q1 = Constraint(mTEPES.nr, rule=eTotalOutput_Q_Capacitive, doc='total output of reactive power by a unit in the capacitive side [Gvar]')
    #
    # print('eTotalOutput_Q1       ... ', len(mTEPES.eTotalOutput_Q1), ' rows')
    #
    # def eTotalOutput_Q_Inductive(mTEPES_NLP,nr):
    #     return mTEPES_NLP.vQger[nr] >= -mTEPES_NLP.vPger[nr] * (tan(acos(mTEPES.pInductivePF)))
    # mTEPES_NLP.eTotalOutput_Q2 = Constraint(mTEPES.nr, rule=eTotalOutput_Q_Inductive, doc='total output of reactive power by a unit in the inductive side [Gvar]')
    #
    # print('eTotalOutput_Q2       ... ', len(mTEPES.eTotalOutput_Q2), ' rows')

    AC_PowerGeneration  = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Generation                   ... ', round(AC_PowerGeneration), 's')

    AC_PowerFlow        = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Flow                         ... ', round(AC_PowerFlow), 's')
