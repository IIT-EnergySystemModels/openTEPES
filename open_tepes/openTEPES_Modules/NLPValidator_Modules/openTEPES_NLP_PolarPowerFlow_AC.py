# Open Generation and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 1.7.7 - July 29, 2020

import time
import math
import pandas as pd
import builtins
from   collections   import defaultdict
from   pyomo.environ import Objective, minimize, Param, Constraint, NonNegativeReals, Var, Reals, UnitInterval, Binary, AbstractModel, cos, sin
def NLP_PolarPowerFlow_AC(CaseName, mTEPES):
    StartTime = time.time()

    print('Model formulation           ****')

    builtins.mTEPES_NLP = AbstractModel('Open NLP model to validate the openTEPES results - Version 1.0.01 - August 19, 2020')

    mTEPES_NLP.pPdf              = Param(mTEPES.nd , within=Reals, initialize=0.0, doc='Active power demand', mutable=True)
    mTEPES_NLP.pQdf              = Param(mTEPES.nd , within=Reals, initialize=0.0, doc='Reactive power demand', mutable=True)

    mTEPES_NLP.pLineG            = Param(mTEPES.la, initialize=mTEPES.pLineG)
    mTEPES_NLP.pLineB            = Param(mTEPES.la, initialize=mTEPES.pLineB)
    mTEPES_NLP.pLineBsh          = Param(mTEPES.la, initialize=mTEPES.pLineBsh)
    mTEPES_NLP.pLineTAP          = Param(mTEPES.la, initialize=mTEPES.pLineTAP)
    mTEPES_NLP.pBusGshb          = Param(mTEPES.sh, initialize=mTEPES.pBusGshb)
    mTEPES_NLP.pBusBshb          = Param(mTEPES.sh, initialize=mTEPES.pBusBshb)

    ParametersDefTime= time.time() - StartTime
    StartTime        = time.time()
    print('Parameters definition                 ... ', round(ParametersDefTime), 's')

    mTEPES_NLP.vVoltage          = Var(mTEPES.nd , within=NonNegativeReals, initialize=1.0, doc='Voltage magnitude                         [p.u.]')
    mTEPES_NLP.vTheta            = Var(mTEPES.nd , within=Reals           , initialize=0.0, doc='Voltage angle                             [rad ]')
    mTEPES_NLP.vPger             = Var(mTEPES.g  , within=NonNegativeReals, initialize=0.0, doc='Active power generation                   [GW  ]')
    mTEPES_NLP.vQger             = Var(mTEPES.nr , within=Reals           , initialize=0.0, doc='Reactive power generation                 [Gvar]')
    mTEPES_NLP.vPpara            = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Active Power Flow from bus i to bus j     [GW  ]')
    mTEPES_NLP.vPde              = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Active Power Flow from bus j to bus i     [GW  ]')
    mTEPES_NLP.vQpara            = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Reactive Power Flow from bus i to bus j   [Gvar]')
    mTEPES_NLP.vQde              = Var(mTEPES.lei, within=Reals           , initialize=0.0, doc='Reactive Power Flow from bus j to bus i   [Gvar]')
    mTEPES_NLP.vESSCharge        = Var(mTEPES.es , within=NonNegativeReals, initialize=0.0, doc='Energy charge from energy storage systems [Gvar]')
    mTEPES_NLP.vENS              = Var(mTEPES.nd , within=NonNegativeReals, initialize=0.0, bounds=(0,1), doc='energy not served in node   [GW  ]')
    mTEPES_NLP.vSger             = Var(mTEPES.gq , within=Reals           , initialize=0.0, doc='Total output of synchronous condenser     [Gvar]')


    VariableDefTime  = time.time() - StartTime
    StartTime        = time.time()
    print('Variable definition                   ... ', round(VariableDefTime), 's')

    def eTotalTCost(mTEPES_NLP):
        return sum(mTEPES_NLP.pLineG[ni,nf,cc]*(mTEPES_NLP.pLineTAP[ni,nf,cc]**2 * mTEPES_NLP.vVoltage[ni]**2 + mTEPES_NLP.vVoltage[nf]**2 -
                                            2* mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni]*mTEPES_NLP.vVoltage[nf]*cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])) for ni,nf,cc in mTEPES.lei) + 1e3*sum(mTEPES_NLP.vENS[nd] for nd in mTEPES.nd)
    mTEPES_NLP.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')
    # def eTotalTCost(mTEPES_NLP):
    #     return sum(mTEPES_NLP.pLineG[ni,nf,cc]*(mTEPES_NLP.pLineTAP[ni,nf,cc]**2 * mTEPES_NLP.vVoltage[ni]**2 + mTEPES_NLP.vVoltage[nf]**2 -
    #                                         2* mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni]*mTEPES_NLP.vVoltage[ni]*cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])) for ni,nf,cc in mTEPES.lei)
    # mTEPES_NLP.eTotalTCost = Objective(rule=eTotalTCost, sense=minimize, doc='total system cost [MEUR]')
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
                # - mTEPES_NLP.pPdf[nd]
                - sum(mTEPES_NLP.vPpara[ni,nd,cc] for ni,cc in lin [nd])
                - sum(mTEPES_NLP.vPde[nd,lout ] for lout  in lout[nd])
                - sum((mTEPES_NLP.vVoltage[nd]**2) * mTEPES_NLP.pBusGshb[shei] for shei in mTEPES.shei if (nd,shei) in mTEPES.n2sh) ==  0)
    mTEPES_NLP.eBalance_P = Constraint(mTEPES.nd, rule=eBalance_P, doc='Active power generation balance [GW]')

    print('eBalance_P            ... ', len(mTEPES_NLP.eBalance_P), ' rows')

    def eBalance_Q(mTEPES_NLP,nd):
        return (sum(mTEPES_NLP.vQger[nr] for nr in mTEPES.nr if (nd,nr) in mTEPES.n2g) + sum(mTEPES_NLP.vSger[gq] for gq in mTEPES.gq if (nd,gq) in mTEPES.n2gq)
                - mTEPES_NLP.pQdf[nd]* (1 - mTEPES_NLP.vENS[nd])
                # - mTEPES_NLP.pQdf[nd]
                - sum(mTEPES_NLP.vQpara[ni,nd,cc] for ni,cc in lin [nd])
                - sum(mTEPES_NLP.vQde[nd,lout ] for lout  in lout[nd])
                + sum((mTEPES_NLP.vVoltage[nd]**2) * mTEPES_NLP.pBusBshb[shei] for shei in mTEPES.shei if (nd,shei) in mTEPES.n2sh) == 0)
    mTEPES_NLP.eBalance_Q = Constraint(mTEPES.nd, rule=eBalance_Q, doc='Reactive power generation balance [GVaR]')

    print('eBalance_Q            ... ', len(mTEPES_NLP.eBalance_Q), ' rows')

    AC_PowerBalance     = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Balance                      ... ', round(AC_PowerBalance), 's')

    def ePde(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vPde[ni,nf,cc] == mTEPES_NLP.pLineG[ni,nf,cc] * mTEPES_NLP.pLineTAP[ni,nf,cc]**2 * mTEPES_NLP.vVoltage[ni]**2
                - mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineG[ni,nf,cc] * cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])
                - mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineB[ni,nf,cc] * sin(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf]))
    mTEPES_NLP.ePde = Constraint(mTEPES.lei, rule=ePde, doc='Active power flow from bus i to bus j [GW]')

    print('ePde                  ... ', len(mTEPES_NLP.ePde), ' rows')

    def ePpara(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vPpara[ni,nf,cc] == mTEPES_NLP.pLineG[ni,nf,cc] * mTEPES_NLP.vVoltage[nf]**2
                - mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineG[ni,nf,cc] * cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])
                + mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineB[ni,nf,cc] * sin(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf]))
    mTEPES_NLP.ePpara = Constraint(mTEPES.lei, rule=ePpara, doc='Active power flow from bus j to bus i [GW]')

    print('ePpara                ... ', len(mTEPES_NLP.ePpara), ' rows')

    def eQde(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vQde[ni,nf,cc] == -(mTEPES_NLP.pLineB[ni,nf,cc] + mTEPES_NLP.pLineBsh[ni,nf,cc]) * mTEPES_NLP.pLineTAP[ni,nf,cc]**2 * mTEPES_NLP.vVoltage[ni]**2
                + mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineB[ni,nf,cc] * cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])
                - mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineG[ni,nf,cc] * sin(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf]))
    mTEPES_NLP.eQde = Constraint(mTEPES.lei, rule=eQde, doc='Reactive power flow from bus i to bus j [Gvar]')

    print('eQde                  ... ', len(mTEPES_NLP.eQde), ' rows')

    def eQpara(mTEPES_NLP,ni,nf,cc):
        return (mTEPES_NLP.vQpara[ni,nf,cc] == -(mTEPES_NLP.pLineB[ni,nf,cc] + mTEPES_NLP.pLineBsh[ni,nf,cc]) * mTEPES_NLP.vVoltage[nf]**2
                + mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineB[ni,nf,cc] * cos(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf])
                + mTEPES_NLP.pLineTAP[ni,nf,cc] * mTEPES_NLP.vVoltage[ni] * mTEPES_NLP.vVoltage[nf] * mTEPES_NLP.pLineG[ni,nf,cc] * sin(mTEPES_NLP.vTheta[ni]-mTEPES_NLP.vTheta[nf]))
    mTEPES_NLP.eQpara = Constraint(mTEPES.lei, rule=eQpara, doc='Reactive power flow from bus j to bus i [Gvar]')

    print('eQpara                ... ', len(mTEPES_NLP.eQpara), ' rows')

    AC_PowerFlow        = time.time() - StartTime
    StartTime           = time.time()
    print('AC Power Flow                         ... ', round(AC_PowerFlow), 's')
